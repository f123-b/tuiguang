from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError

from .agent import estimated_reservation, graph, select_facts
from .domains import compliance_report, serialize
from .editorial import ensure_plan, local_today, lock_creator, snapshot, validate_facts
from .errors import DomainError
from .models import Brand, BudgetEntry, Content, Creator, EditorialEntry, Run
from .observability import record, tracer, trace_context
from .model_config import workspace_release, execution_config


def enqueue(db, creator, day, key, trace_id=None, entry=None, commit=True):
    lock_creator(db, creator)
    if creator.status != "active":
        raise DomainError("CREATOR_SCHEDULE_PAUSED", "创作者已暂停，未执行新任务")
    existing = db.scalar(
        select(Run).where(Run.creator_id == creator.id, Run.operational_date == day, Run.slot == "daily")
    )
    if existing:
        return existing, False
    entry = entry or db.scalar(
        select(EditorialEntry).where(
            EditorialEntry.creator_id == creator.id,
            EditorialEntry.date == day,
        )
    )
    if entry:
        db.refresh(entry)
        if entry.status != "approved":
            raise DomainError("EDITORIAL_APPROVAL_REQUIRED", "该选题尚未确认或已跳过")
        validate_facts(db, creator, entry)
    from .production import options_snapshot

    release = workspace_release(db, creator.workspace_id)
    release["production_options"] = options_snapshot(db, creator)
    run = Run(
        workspace_id=creator.workspace_id,
        creator_id=creator.id,
        operational_date=day,
        idempotency_key=key,
        release=release,
        editorial_entry_id=entry.id if entry else None,
        input_snapshot=snapshot(entry) if entry else None,
    )
    if trace_id:
        run.trace_id = trace_id
    db.add(run)
    try:
        if entry:
            entry.status = "queued"
        db.flush()
        record(
            db,
            creator.workspace_id,
            run.trace_id,
            "scheduled",
            "ok",
            run.id,
            release_id=run.release["release_id"],
        )
        if commit:
            db.commit()
        return run, True
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(Run).where(Run.creator_id == creator.id, Run.operational_date == day, Run.slot == "daily")
        )
        if existing:
            return existing, False
        raise DomainError("IDEMPOTENCY_KEY_CONFLICT", "该幂等键已用于其他任务") from None


def schedule_due(db, now=None):
    now = now or datetime.now(timezone.utc)
    for creator in db.scalars(select(Creator).where(Creator.status == "active")).all():
        local = now.astimezone(ZoneInfo(creator.timezone))
        plan = ensure_plan(db, creator, local.date())
        for old in db.scalars(
            select(EditorialEntry).where(
                EditorialEntry.creator_id == creator.id,
                EditorialEntry.date < local.date().isoformat(),
                EditorialEntry.status.in_(["approved", "planned", "rest"]),
            )
        ):
            old.status = "expired"
        db.commit()
        entry = next((e for e in plan if e.date == local.date().isoformat()), None)
        if entry and entry.status == "approved" and local.hour >= creator.hour:
            try:
                enqueue(db, creator, entry.date, f"daily:{creator.id}:{local.date()}", entry=entry)
            except DomainError as error:
                db.rollback()
                if error.code == "EDITORIAL_FACTS_STALE":
                    db.refresh(entry)
                    entry.status = "needs_review"
                    db.commit()
                elif error.code != "CREATOR_SCHEDULE_PAUSED":
                    raise


def reserve_budget(db, creator, run, amount):
    # Acquire a write lock before reading the ledger (also serializes SQLite writers).
    lock_creator(db, creator)
    if creator.status != "active":
        raise DomainError("CREATOR_SCHEDULE_PAUSED", "创作者已暂停")
    prior = db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == run.id))
    if prior and prior.reserved_cents != 0 and prior.status != "cancelled":
        raise DomainError("AGENT_PROVIDER_RESULT_UNKNOWN", "存在费用预留记录，须人工核对后继续")
    billing_day = local_today(creator).isoformat()
    entries = db.scalars(
        select(BudgetEntry).where(
            BudgetEntry.creator_id == creator.id,
            func.coalesce(BudgetEntry.billing_date, BudgetEntry.operational_date).like(billing_day[:7] + "%"),
            BudgetEntry.run_id != run.id,
        )
    ).all()
    month_total = sum(e.actual_cents if e.actual_cents is not None else e.reserved_cents for e in entries)
    day_total = sum(
        e.actual_cents if e.actual_cents is not None else e.reserved_cents
        for e in entries
        if (e.billing_date or e.operational_date) == billing_day
    )
    if amount + day_total > creator.daily_budget_cents or amount + month_total > creator.monthly_budget_cents:
        creator.status = "paused_by_budget"
        db.commit()
        raise DomainError("BUDGET_LIMIT_REACHED", "已达到创作预算上限")
    ledger = prior or BudgetEntry(
        workspace_id=creator.workspace_id,
        creator_id=creator.id,
        run_id=run.id,
        operational_date=run.operational_date,
        reserved_cents=amount,
    )
    ledger.billing_date = billing_day
    ledger.status, ledger.reserved_cents, ledger.actual_cents = "reserved", amount, None
    db.add(ledger)
    db.commit()
    return ledger


def process_pending(db):
    now = datetime.now(timezone.utc)
    runs = db.scalars(
        select(Run)
        .where(or_(Run.status == "queued", (Run.status == "running") & (Run.lease_until < now.isoformat())))
        .order_by(Run.created_at)
    ).all()
    for run in runs:
        creator = db.get(Creator, run.creator_id)
        db.refresh(creator)
        if creator.status != "active":
            continue
        current_release = workspace_release(db, creator.workspace_id)
        if run.release["agent_graph_version"] not in {"creator_graph@1", "creator_graph@2"} or any(
            run.release.get(k) != current_release.get(k)
            for k in (
                "generation_mode",
                "model_id",
                "model_revision",
                "workspace_model_revision",
                "model_config_hash",
            )
        ):
            run.status, run.error_code = "blocked", "RUN_VERSION_UNSUPPORTED"
            db.commit()
            continue
        claimed = db.execute(
            update(Run)
            .where(
                Run.id == run.id,
                or_(Run.status == "queued", (Run.status == "running") & (Run.lease_until < now.isoformat())),
            )
            .values(status="running", lease_until=(now + timedelta(minutes=5)).isoformat())
        )
        db.commit()
        if claimed.rowcount != 1:
            continue
        db.refresh(run)
        try:
            if run.release.get("job_kind") == "drama_plan":
                from .drama_jobs import process

                process(db, run, creator)
                continue
            if run.release.get("job_kind") == "brief_video":
                from .brief_jobs import process

                process(db, run, creator)
                continue
            if run.release.get("job_kind") == "quality_review":
                from .quality_jobs import process

                process(db, run, creator)
                continue
            if run.release.get("job_kind") == "model_probe":
                from .model_diagnostics import process_probe

                process_probe(db, run, creator)
                continue
            if run.release.get("job_kind") == "learning_review":
                from .analysis_jobs import process

                process(db, run, creator)
                continue
            existing = db.scalar(select(Content).where(Content.run_id == run.id))
            if existing:
                from .production import prepare

                prepare(db, run, existing)
                if run.editorial_entry_id:
                    db.get(EditorialEntry, run.editorial_entry_id).status = "completed"
                db.commit()
                continue
            brand = db.get(Brand, creator.brand_id)
            plan = None
            if run.input_snapshot:
                entry = db.get(EditorialEntry, run.editorial_entry_id)
                if not entry or snapshot(entry) != run.input_snapshot:
                    raise DomainError("EDITORIAL_REVISION_CONFLICT", "执行计划版本不一致，任务已停止")
                validate_facts(db, creator, entry)
                plan = run.input_snapshot
            else:
                db.refresh(brand)
            state = {
                "brand": serialize(brand),
                "creator": serialize(creator),
                "day": run.operational_date,
                "generation_mode": current_release["generation_mode"],
            }
            if plan:
                state["plan"] = plan
                preference = (plan.get("strategy_snapshot") or {}).get("settings", {})
                if preference.get("tone") == "restrained":
                    state["creator"]["style"] += "；用户已确认：表达克制，避免夸张广告开场"
                if preference.get("concise"):
                    state["creator"]["style"] += "；用户已确认：简短表达"
            run.stage = "content.script"
            db.commit()
            from .production import options_snapshot

            if run.release.get("production_options"):
                options_snapshot(db, creator, run.release["production_options"])
            state.update(select_facts(state))
            paid = current_release["generation_mode"] == "openai"
            if paid and not creator.model_consent:
                raise DomainError("MODEL_CONSENT_REQUIRED", "请先授权将核实事实发送到模型服务")
            state["model_config"] = (
                execution_config(db, creator.workspace_id, run.release.get("workspace_model_revision"))
                if paid
                else None
            )
            ledger = reserve_budget(db, creator, run, estimated_reservation(state) if paid else 0)
            # Pause is checked once more at the side-effect boundary.
            db.refresh(creator)
            if creator.status != "active":
                ledger.status, ledger.actual_cents = "cancelled", 0
                run.status = "queued"
                db.commit()
                continue
            live_release = workspace_release(db, creator.workspace_id)
            if paid and not creator.model_consent:
                ledger.status, ledger.actual_cents = "cancelled", 0
                db.commit()
                raise DomainError("MODEL_CONSENT_REQUIRED", "模型授权已撤销，未发起请求")
            if paid and any(
                live_release.get(k) != run.release.get(k)
                for k in ("workspace_model_revision", "model_config_hash")
            ):
                ledger.status, ledger.actual_cents = "cancelled", 0
                run.status, run.error_code = "blocked", "RUN_VERSION_UNSUPPORTED"
                db.commit()
                continue
            record(db, creator.workspace_id, run.trace_id, "content.script", "running", run.id)
            db.commit()
            from langsmith import tracing_context

            with tracer.start_as_current_span("creator.daily_draft", context=trace_context(run.trace_id)):
                # External tracing may be globally enabled in a developer's environment.
                # Brand documents and prompts are never sent to a third-party trace service here.
                with tracing_context(enabled=False):
                    result = graph.invoke(state)["draft"]
            content = Content(
                workspace_id=creator.workspace_id,
                creator_id=creator.id,
                run_id=run.id,
                title=result["title"],
                body=result["body"],
                platform=creator.platform,
                generation_source=result["generation_source"],
                fact_refs=result["fact_refs"],
            )
            db.add(content)
            db.flush()
            from .quality import build_report

            build_report(db, "content", content)
            content.compliance = compliance_report(db, content)
            ledger.status, ledger.actual_cents = "settled", result["actual_cents"]
            media_options = run.release.get("production_options") or {}
            media_requested = media_options.get("graphics") or media_options.get("video")
            run.status, run.stage, run.error_code = (
                ("running", "asset_rendering", None)
                if media_requested
                else ("completed", "awaiting_user_review", None)
            )
            if run.editorial_entry_id:
                db.get(EditorialEntry, run.editorial_entry_id).status = "completed"
            record(
                db,
                creator.workspace_id,
                run.trace_id,
                "content.script",
                "ok",
                run.id,
                content_id=content.id,
                actual_cents=ledger.actual_cents,
                source=content.generation_source,
            )
            db.commit()
            from .production import prepare

            prepare(db, run, content)
        except DomainError as error:
            db.rollback()
            run = db.get(Run, run.id)
            run.status, run.error_code = "failed", error.code
            if run.editorial_entry_id:
                entry = db.get(EditorialEntry, run.editorial_entry_id)
                entry.status = "needs_review" if error.code == "EDITORIAL_FACTS_STALE" else "failed"
            if error.code == "AGENT_PROVIDER_RESULT_UNKNOWN":
                creator = db.get(Creator, run.creator_id)
                creator.status = "paused_by_error"
            stage = {
                "model_probe": "model.probe",
                "quality_review": "quality.model",
                "brief_video": "brief.model",
                "drama_plan": "drama.model",
                "learning_review": "learning.model",
            }.get(run.release.get("job_kind"), "content.script")
            record(db, run.workspace_id, run.trace_id, stage, "error", run.id, error.code)
            db.commit()


def budget_used(db, workspace_id):
    # Reserved/unknown usage remains counted until it is reconciled.
    amount = db.scalar(
        select(func.sum(func.coalesce(BudgetEntry.actual_cents, BudgetEntry.reserved_cents))).where(
            BudgetEntry.workspace_id == workspace_id
        )
    )
    return int(amount or 0)
