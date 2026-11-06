from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from .auth import current_user
from .db import get_db
from .domains import digest, owned, parse_metric_rows, serialize
from .editorial import lock_creator
from .errors import DomainError
from .learning import build_report, invalidate_evidence
from .models import Content, Creator, Feedback, ImportBatch, LearningReport, Metric, Strategy, User, now_iso
from .schemas import DTO, Platform
from .observability import record

router = APIRouter(prefix="/api/v1")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


class Period(DTO):
    period_start: date
    period_end: date


class ManualMetric(Period):
    content_revision: int | None = Field(default=None, ge=1)
    content_id: str = Field(min_length=1, max_length=120)
    platform: Platform
    observed_at: datetime
    data_source: str = Field(min_length=1, max_length=180)
    views: int | None = Field(default=None, ge=0, le=999999999999)
    likes: int | None = Field(default=None, ge=0, le=999999999999)
    saves: int | None = Field(default=None, ge=0, le=999999999999)
    clicks: int | None = Field(default=None, ge=0, le=999999999999)
    conversions: int | None = Field(default=None, ge=0, le=999999999999)


class FeedbackInput(DTO):
    content_id: str = Field(min_length=1, max_length=120)
    expected_revision: int = Field(ge=1)
    reason_tag: Literal[
        "too_advertising", "inaccurate", "too_fast", "more_real", "inconsistent", "shorter", "useful", "other"
    ]
    note: str = Field(default="", max_length=2000)


class Confirm(DTO):
    confirmed: Literal[True]


class Decision(Confirm):
    decision: Literal["accept", "reject"]
    expected_active_id: str | None = Field(max_length=120)


class Rollback(Confirm):
    expected_active_id: str = Field(min_length=1, max_length=120)


@router.post("/analytics/manual", status_code=201)
def manual(data: ManualMetric, db: DB, user: Actor, request: Request):
    raw = data.model_dump(mode="json", exclude={"data_source"})
    row = parse_metric_rows(db, user.workspace_id, [raw], data.data_source)[0]
    fingerprint = digest({"row": row, "source": data.data_source})
    existing = db.scalar(
        select(Metric).where(Metric.workspace_id == user.workspace_id, Metric.fingerprint == fingerprint)
    )
    if existing:
        if not existing.active:
            raise DomainError("METRICS_ROW_WITHDRAWN", "相同记录已停用，请核对值与来源后重新登记")
        return serialize(existing)
    batch = ImportBatch(
        workspace_id=user.workspace_id,
        data_source=data.data_source,
        rows=[row],
        fingerprint=digest({"manual": fingerprint}),
        committed=True,
    )
    db.add(batch)
    db.flush()
    m = Metric(
        workspace_id=user.workspace_id,
        batch_id=batch.id,
        content_id=data.content_id,
        platform=data.platform,
        values={k: row[k] for k in ("views", "likes", "saves", "clicks", "conversions")},
        period_start=row["period_start"],
        period_end=row["period_end"],
        observed_at=row["observed_at"],
        data_source=data.data_source,
        fingerprint=fingerprint,
        content_revision=row.get("content_revision"),
    )
    db.add(m)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "metrics.manual",
        "ok",
        content_id=data.content_id,
        source="user_reported",
    )
    db.commit()
    return serialize(m)


@router.post("/analytics/batches/{batch_id}/withdraw")
def withdraw(batch_id: str, data: Confirm, db: DB, user: Actor, request: Request):
    batch = owned(db, ImportBatch, batch_id, user.workspace_id)
    db.execute(update(Metric).where(Metric.batch_id == batch.id).values(active=False))
    invalidate_evidence(db, user.workspace_id, "batch", batch.id)
    record(db, user.workspace_id, request.state.trace_id, "metrics.withdraw", "ok", source="user_reported")
    db.commit()
    return {"withdrawn": True, "batch_id": batch.id}


@router.get("/analytics/batches")
def batches(db: DB, user: Actor):
    result = []
    for batch in db.scalars(
        select(ImportBatch)
        .where(ImportBatch.workspace_id == user.workspace_id)
        .order_by(ImportBatch.created_at.desc())
    ):
        row = serialize(batch)
        row["row_count"] = len(row.pop("rows"))
        row["active_count"] = db.scalar(
            select(func.count())
            .select_from(Metric)
            .where(Metric.batch_id == batch.id, Metric.active.is_(True))
        )
        row["withdrawn"] = batch.committed and row["active_count"] == 0
        result.append(row)
    return result


@router.post("/analytics/feedback", status_code=201)
def feedback(data: FeedbackInput, db: DB, user: Actor, request: Request):
    content = owned(db, Content, data.content_id, user.workspace_id)
    if content.revision != data.expected_revision:
        raise DomainError("CONTENT_REVISION_CONFLICT", "反馈针对旧版本，请刷新")
    f = Feedback(
        workspace_id=user.workspace_id,
        content_id=content.id,
        content_revision=content.revision,
        reason_tag=data.reason_tag,
        note=data.note,
        recorded_by=user.id,
    )
    db.add(f)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "learning.feedback",
        "ok",
        content_id=content.id,
        revision=content.revision,
    )
    db.commit()
    return serialize(f)


@router.get("/analytics/feedback")
def list_feedback(db: DB, user: Actor):
    return [
        serialize(f)
        for f in db.scalars(
            select(Feedback)
            .where(Feedback.workspace_id == user.workspace_id)
            .order_by(Feedback.created_at.desc())
        )
    ]


@router.post("/analytics/feedback/{feedback_id}/withdraw")
def withdraw_feedback(feedback_id: str, data: Confirm, db: DB, user: Actor, request: Request):
    f = owned(db, Feedback, feedback_id, user.workspace_id)
    f.active = False
    invalidate_evidence(db, user.workspace_id, "feedback", f.id)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "learning.feedback.withdraw",
        "ok",
        content_id=f.content_id,
    )
    db.commit()
    return serialize(f)


@router.post("/creators/{creator_id}/learning-reports", status_code=201)
def generate(creator_id: str, data: Period, db: DB, user: Actor, request: Request):
    creator = owned(db, Creator, creator_id, user.workspace_id)
    if not 0 <= (data.period_end - data.period_start).days <= 31:
        raise DomainError("LEARNING_PERIOD_INVALID", "复盘窗口需为 1–32 天", 422)
    report = build_report(db, creator, data.period_start.isoformat(), data.period_end.isoformat())
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "learning.report",
        "ok",
        count=report.report["metric_sample_count"],
        source="deterministic_evidence_report",
    )
    db.commit()
    return serialize(report)


@router.get("/creators/{creator_id}/learning-reports")
def reports(creator_id: str, db: DB, user: Actor):
    creator = owned(db, Creator, creator_id, user.workspace_id)
    return [
        serialize(r)
        for r in db.scalars(
            select(LearningReport)
            .where(LearningReport.creator_id == creator.id)
            .order_by(LearningReport.created_at.desc())
        )
    ]


@router.get("/creators/{creator_id}/learning-reports/{report_id}")
def report(creator_id: str, report_id: str, db: DB, user: Actor):
    owned(db, Creator, creator_id, user.workspace_id)
    r = owned(db, LearningReport, report_id, user.workspace_id)
    if r.creator_id != creator_id:
        raise DomainError("RESOURCE_NOT_FOUND", "报告不存在", 404)
    return serialize(r)


@router.get("/creators/{creator_id}/strategy-proposals")
def strategies(creator_id: str, db: DB, user: Actor):
    creator = owned(db, Creator, creator_id, user.workspace_id)
    return [
        serialize(s)
        for s in db.scalars(
            select(Strategy).where(Strategy.creator_id == creator.id).order_by(Strategy.created_at.desc())
        )
    ]


def owned_strategy(db, user, creator_id, strategy_id):
    creator = owned(db, Creator, creator_id, user.workspace_id)
    lock_creator(db, creator)
    strategy = owned(db, Strategy, strategy_id, user.workspace_id)
    if strategy.creator_id != creator.id:
        raise DomainError("RESOURCE_NOT_FOUND", "策略不存在", 404)
    return creator, strategy


@router.post("/creators/{creator_id}/strategy-proposals/{strategy_id}/decide")
def decide(creator_id: str, strategy_id: str, data: Decision, db: DB, user: Actor, request: Request):
    creator, strategy = owned_strategy(db, user, creator_id, strategy_id)
    if strategy.status != "proposed" or creator.active_strategy_id != data.expected_active_id:
        raise DomainError("STRATEGY_REVISION_CONFLICT", "策略状态已变化，请刷新")
    # Review input revocations before enabling a stale proposal.
    old = db.get(LearningReport, strategy.report_id)
    current = build_report(db, creator, old.period_start, old.period_end)
    if data.decision == "accept" and current.source_digest != old.report.get(
        "evidence_digest", old.source_digest
    ):
        raise DomainError("STRATEGY_EVIDENCE_STALE", "复盘依据已变化，请查看新版报告")
    if data.decision == "accept":
        for title in old.report.get("title_evidence", []):
            source = owned(db, Content, title["content_id"], user.workspace_id)
            if source.revision != title["revision"]:
                raise DomainError("STRATEGY_EVIDENCE_STALE", "模型解释引用的内容已变化，请先重新复盘")
    strategy.status = "accepted" if data.decision == "accept" else "rejected"
    strategy.decided_at, strategy.decided_by = now_iso(), user.id
    if data.decision == "accept":
        strategy.parent_id = creator.active_strategy_id
        creator.active_strategy_id = strategy.id
    record(db, user.workspace_id, request.state.trace_id, "learning.strategy", "ok", decision=strategy.status)
    db.commit()
    return serialize(strategy)


@router.post("/creators/{creator_id}/strategy-proposals/{strategy_id}/rollback")
def rollback(creator_id: str, strategy_id: str, data: Rollback, db: DB, user: Actor, request: Request):
    creator, strategy = owned_strategy(db, user, creator_id, strategy_id)
    if (
        creator.active_strategy_id != strategy.id
        or data.expected_active_id != strategy.id
        or strategy.status != "accepted"
    ):
        raise DomainError("STRATEGY_REVISION_CONFLICT", "只能回滚当前生效的策略")
    creator.active_strategy_id = strategy.parent_id
    strategy.status = "rolled_back"
    strategy.decided_at = now_iso()
    strategy.decided_by = user.id
    record(db, user.workspace_id, request.state.trace_id, "learning.strategy", "ok", decision=strategy.status)
    db.commit()
    return serialize(strategy)
