import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError

from .agent import estimated_reservation, graph, select_facts
from .domains import compliance_report, serialize
from .errors import DomainError
from .models import Brand, BudgetEntry, Content, Creator, Run
from .observability import record, release_manifest, tracer, trace_context


def enqueue(db, creator, day, key, trace_id=None):
    if creator.status != "active":
        raise DomainError("CREATOR_SCHEDULE_PAUSED", "创作者已暂停，未执行新任务")
    existing = db.scalar(select(Run).where(Run.creator_id == creator.id, Run.operational_date == day))
    if existing:
        return existing, False
    run = Run(
        workspace_id=creator.workspace_id,
        creator_id=creator.id,
        operational_date=day,
        idempotency_key=key,
        release=release_manifest(),
    )
    if trace_id:
        run.trace_id = trace_id
    db.add(run)
    try:
        db.commit()
        record(
            db,
            creator.workspace_id,
            run.trace_id,
            "scheduled",
            "ok",
            run.id,
            release_id=run.release["release_id"],
        )
        db.commit()
        return run, True
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Run).where(Run.creator_id == creator.id, Run.operational_date == day))
        if existing:
            return existing, False
        raise DomainError("IDEMPOTENCY_KEY_CONFLICT", "该幂等键已用于其他任务") from None


def schedule_due(db, now=None):
    now = now or datetime.now(timezone.utc)
    for creator in db.scalars(select(Creator).where(Creator.status == "active")).all():
        local = now.astimezone(ZoneInfo(creator.timezone))
        if local.weekday() in creator.weekdays and local.hour >= creator.hour:
            enqueue(db, creator, local.date().isoformat(), f"daily:{creator.id}:{local.date()}")


def reserve_budget(db, creator, run, amount):
    # Acquire a write lock before reading the ledger (also serializes SQLite writers).
    db.execute(update(Creator).where(Creator.id == creator.id).values(status=Creator.status))
    db.refresh(creator)
    if creator.status != "active":
        raise DomainError("CREATOR_SCHEDULE_PAUSED", "创作者已暂停")
    prior = db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == run.id))
    if prior:
        if prior.reserved_cents == 0 or prior.status == "cancelled":
            prior.status, prior.reserved_cents, prior.actual_cents = "reserved", amount, None
            db.commit()
            return prior
        raise DomainError("AGENT_PROVIDER_RESULT_UNKNOWN", "存在费用预留记录，须人工核对后继续")
    entries = db.scalars(
        select(BudgetEntry).where(
            BudgetEntry.creator_id == creator.id,
            BudgetEntry.operational_date.like(run.operational_date[:7] + "%"),
        )
    ).all()
    month_total = sum(e.actual_cents if e.actual_cents is not None else e.reserved_cents for e in entries)
    day_total = sum(
        e.actual_cents if e.actual_cents is not None else e.reserved_cents
        for e in entries
        if e.operational_date == run.operational_date
    )
    if amount + day_total > creator.daily_budget_cents or amount + month_total > creator.monthly_budget_cents:
        creator.status = "paused_by_budget"
        db.commit()
        raise DomainError("BUDGET_LIMIT_REACHED", "已达到创作预算上限")
    ledger = BudgetEntry(
        workspace_id=creator.workspace_id,
        creator_id=creator.id,
        run_id=run.id,
        operational_date=run.operational_date,
        reserved_cents=amount,
    )
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
        current_release = release_manifest()
        if run.release["agent_graph_version"] != "creator_graph@1" or any(
            run.release.get(k) != current_release.get(k)
            for k in ("generation_mode", "model_id", "model_revision")
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
            existing = db.scalar(select(Content).where(Content.run_id == run.id))
            if existing:
                run.status = "completed"
                db.commit()
                continue
            brand = db.get(Brand, creator.brand_id)
            state = {"brand": serialize(brand), "creator": serialize(creator), "day": run.operational_date}
            run.stage = "content.script"
            db.commit()
            state.update(select_facts(state))
            paid = os.getenv("GENERATION_MODE", "template") == "openai"
            if paid and not creator.model_consent:
                raise DomainError("MODEL_CONSENT_REQUIRED", "请先授权将核实事实发送到模型服务")
            ledger = reserve_budget(db, creator, run, estimated_reservation(state) if paid else 0)
            # Pause is checked once more at the side-effect boundary.
            db.refresh(creator)
            if creator.status != "active":
                ledger.status, ledger.actual_cents = "cancelled", 0
                run.status = "queued"
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
            content.compliance = compliance_report(db, content)
            ledger.status, ledger.actual_cents = "settled", result["actual_cents"]
            run.status, run.stage, run.error_code = "completed", "awaiting_user_review", None
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
        except DomainError as error:
            db.rollback()
            run = db.get(Run, run.id)
            run.status, run.error_code = "failed", error.code
            if error.code == "AGENT_PROVIDER_RESULT_UNKNOWN":
                creator = db.get(Creator, run.creator_id)
                creator.status = "paused_by_error"
            record(db, run.workspace_id, run.trace_id, "content.script", "error", run.id, error.code)
            db.commit()


def budget_used(db, workspace_id):
    # Reserved/unknown usage remains counted until it is reconciled.
    amount = db.scalar(
        select(func.sum(func.coalesce(BudgetEntry.actual_cents, BudgetEntry.reserved_cents))).where(
            BudgetEntry.workspace_id == workspace_id
        )
    )
    return int(amount or 0)
