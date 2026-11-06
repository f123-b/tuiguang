"""Persistent editorial planning. No model calls or publishing side effects."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, update

from .agent import ANGLES
from .domains import serialize
from .errors import DomainError
from .models import Brand, Creator, EditorialEntry, Run

EDITABLE = {"approved", "planned", "rest", "skipped", "needs_review", "expired"}


def lock_creator(db, creator):
    db.execute(update(Creator).where(Creator.id == creator.id).values(status=Creator.status))
    db.refresh(creator)


def local_today(creator, now=None):
    return (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(creator.timezone)).date()


def due_at(creator, day):
    local = datetime.combine(date.fromisoformat(day), time(creator.hour), ZoneInfo(creator.timezone))
    # Normalize nonexistent spring-forward wall times; fold=0 runs once in autumn.
    return local.astimezone(timezone.utc).astimezone(ZoneInfo(creator.timezone))


def entries(db, creator, start=None):
    start = start or local_today(creator)
    return db.scalars(
        select(EditorialEntry)
        .where(
            EditorialEntry.creator_id == creator.id,
            EditorialEntry.date >= start.isoformat(),
            EditorialEntry.date < (start + timedelta(days=14)).isoformat(),
        )
        .order_by(EditorialEntry.date)
    ).all()


def ensure_plan(db, creator, start=None):
    lock_creator(db, creator)
    start = start or local_today(creator)
    brand = db.get(Brand, creator.brand_id)
    facts = [f for f in brand.facts if f["verified"]]
    from .learning import strategy_snapshot

    strategy = strategy_snapshot(db, creator)
    current = {e.date: e for e in entries(db, creator, start)}
    for offset in range(14):
        day = start + timedelta(days=offset)
        scheduled = day.weekday() in creator.weekdays
        existing = current.get(day.isoformat())
        if existing:
            # Frequency edits affect untouched rule plans only; never override user choices.
            if (
                existing.source == "rule_based_plan"
                and not existing.locked
                and existing.status in {"approved", "rest"}
            ):
                target = "approved" if scheduled else "rest"
                if existing.status != target:
                    existing.status, existing.revision = target, existing.revision + 1
            continue
        preferred = (strategy or {}).get("settings", {}).get("preferred_angles") or ANGLES
        angle = preferred[day.toordinal() % len(preferred)]
        fact = facts[day.toordinal() % len(facts)] if facts else None
        db.add(
            EditorialEntry(
                workspace_id=creator.workspace_id,
                creator_id=creator.id,
                date=day.isoformat(),
                title=f"{brand.name[:120]} · {angle}",
                angle=angle,
                fact_refs=[fact["id"]] if fact else [],
                brand_revision=brand.revision,
                status=("approved" if scheduled else "rest") if facts else "needs_review",
                strategy_snapshot=strategy,
                rationale=(
                    "使用用户确认策略 "
                    + strategy["strategy_id"]
                    + "，依据报告 "
                    + strategy["report_id"]
                    + "；仅待验证偏好，不代表平台规律。"
                )
                if strategy
                else "依据创作者频率和已核实事实轮换角度；本地规则计划，未进行模型或热度分析。",
            )
        )
    db.flush()
    return entries(db, creator, start)


def validate_facts(db, creator, entry):
    brand = db.get(Brand, creator.brand_id)
    # Worker sessions may process several drafts; expire cached brand evidence
    # before each execution so updates in another API session are observed.
    db.refresh(brand)
    if entry.strategy_snapshot:
        from .models import Strategy

        strategy = db.get(Strategy, entry.strategy_snapshot["strategy_id"])
        if not strategy or strategy.status != "accepted":
            raise DomainError("EDITORIAL_FACTS_STALE", "计划引用的策略已停用，请重新核对计划")
    verified = {f["id"]: f for f in brand.facts if f["verified"]}
    if (
        entry.brand_revision != brand.revision
        or not entry.fact_refs
        or not set(entry.fact_refs) <= verified.keys()
    ):
        raise DomainError("EDITORIAL_FACTS_STALE", "事实或品牌版本已变化，请重新选择事实并确认选题")
    return [verified[ref] for ref in entry.fact_refs]


def validate_edit(db, creator, entry, revision):
    lock_creator(db, creator)
    db.refresh(entry)
    if entry.revision != revision:
        raise DomainError("EDITORIAL_REVISION_CONFLICT", "选题已被更新，请刷新后重试")
    if entry.status not in EDITABLE or db.scalar(
        select(Run.id).where(
            Run.creator_id == creator.id,
            Run.operational_date == entry.date,
        )
    ):
        raise DomainError("EDITORIAL_ALREADY_EXECUTED", "该日期已创建任务，不能改写执行依据")


def snapshot(entry):
    return {
        **({"strategy_snapshot": entry.strategy_snapshot} if entry.strategy_snapshot else {}),
        "entry_id": entry.id,
        "revision": entry.revision,
        "title": entry.title,
        "angle": entry.angle,
        "fact_refs": list(entry.fact_refs),
        "brand_revision": entry.brand_revision,
    }


def serialize_entry(db, creator, entry):
    result = serialize(entry)
    run = db.scalar(select(Run).where(Run.creator_id == creator.id, Run.operational_date == entry.date))
    brand = db.get(Brand, creator.brand_id)
    result.update(
        status=(entry.status if entry.status == "needs_review" or not run else run.status),
        kind="article",
        scheduled=entry.status not in {"rest", "skipped", "expired"},
        due_at=due_at(creator, entry.date).isoformat(),
        fact_evidence=[f for f in brand.facts if f["id"] in entry.fact_refs],
        available_facts=[f for f in brand.facts if f["verified"]],
        facts_stale=entry.brand_revision != brand.revision,
        run_id=run.id if run else None,
    )
    return result


def serialize_creator(db, creator):
    result = serialize(creator)
    next_time = None
    if creator.status == "active":
        for entry in entries(db, creator):
            if entry.status == "approved" and not db.scalar(
                select(Run.id).where(
                    Run.creator_id == creator.id,
                    Run.operational_date == entry.date,
                )
            ):
                try:
                    validate_facts(db, creator, entry)
                except DomainError:
                    continue
                next_time = due_at(creator, entry.date).isoformat()
                break
    result["next_run_at"] = next_time
    return result
