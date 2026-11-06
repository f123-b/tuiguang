from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .agent import ANGLES
from .auth import current_user
from .db import get_db
from .domains import owned, serialize
from .editorial import (
    ensure_plan,
    entries,
    local_today,
    lock_creator,
    serialize_entry,
    validate_edit,
    validate_facts,
)
from .errors import DomainError
from .jobs import enqueue
from .models import Brand, Creator, EditorialEntry, Run, User
from .observability import record
from .schemas import DTO, Short

router = APIRouter(prefix="/api/v1")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


class TopicRevision(DTO):
    expected_revision: int = Field(ge=1)


class TopicPatch(TopicRevision):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    angle: str | None = None
    fact_refs: list[Short] | None = Field(default=None, min_length=1, max_length=100)
    locked: bool | None = None

    @field_validator("angle")
    @classmethod
    def known_angle(cls, value):
        if value not in ANGLES:
            raise ValueError("请选择受支持的创作角度")
        return value


class TopicApproval(TopicRevision):
    confirmed: Literal[True]


class TopicReschedule(TopicRevision):
    date: date
    swap_revision: int | None = Field(default=None, ge=1)


class Prepare(DTO):
    entry_ids: list[Short] = Field(min_length=1, max_length=7)
    expected_revisions: dict[Short, Annotated[int, Field(ge=1)]] = Field(max_length=7)
    confirmed: Literal[True]

    @field_validator("entry_ids")
    @classmethod
    def unique_ids(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("请勿重复选择同一选题")
        return value


def topic_context(db, user, entry_id):
    entry = owned(db, EditorialEntry, entry_id, user.workspace_id)
    return entry, owned(db, Creator, entry.creator_id, user.workspace_id)


def save(db, creator, entry, request, stage):
    record(db, creator.workspace_id, request.state.trace_id, stage, "ok", revision=entry.revision)
    db.commit()
    return serialize_entry(db, creator, entry)


@router.post("/creators/{creator_id}/plan")
def create_plan(creator_id: str, db: DB, user: Actor):
    creator = owned(db, Creator, creator_id, user.workspace_id)
    result = ensure_plan(db, creator)
    db.commit()
    return [serialize_entry(db, creator, e) for e in result]


@router.get("/creators/{creator_id}/calendar")
def calendar(creator_id: str, db: DB, user: Actor):
    creator = owned(db, Creator, creator_id, user.workspace_id)
    return [serialize_entry(db, creator, e) for e in entries(db, creator)]


@router.get("/topics/{entry_id}")
def get_topic(entry_id: str, db: DB, user: Actor):
    entry, creator = topic_context(db, user, entry_id)
    return serialize_entry(db, creator, entry)


@router.patch("/topics/{entry_id}")
def edit_topic(entry_id: str, data: TopicPatch, db: DB, user: Actor, request: Request):
    entry, creator = topic_context(db, user, entry_id)
    validate_edit(db, creator, entry, data.expected_revision)
    changes = data.model_dump(exclude_unset=True, exclude={"expected_revision"})
    if not changes or any(v is None for v in changes.values()):
        raise DomainError("EDITORIAL_PATCH_INVALID", "请提供有效的修改字段", 422)
    for key, value in changes.items():
        setattr(entry, key, value)
    entry.brand_revision = db.get(Brand, creator.brand_id).revision
    from .learning import strategy_snapshot
    entry.strategy_snapshot = strategy_snapshot(db, creator)
    validate_facts(db, creator, entry)
    entry.status, entry.source, entry.revision = "planned", "user", entry.revision + 1
    return save(db, creator, entry, request, "editorial.edit")


@router.post("/topics/{entry_id}/approve")
def approve_topic(entry_id: str, data: TopicApproval, db: DB, user: Actor, request: Request):
    entry, creator = topic_context(db, user, entry_id)
    validate_edit(db, creator, entry, data.expected_revision)
    if date.fromisoformat(entry.date) < local_today(creator):
        raise DomainError("EDITORIAL_DATE_EXPIRED", "日期已过，请先改期")
    validate_facts(db, creator, entry)
    entry.status, entry.revision = "approved", entry.revision + 1
    return save(db, creator, entry, request, "editorial.approve")


@router.post("/topics/{entry_id}/skip")
def skip_topic(entry_id: str, data: TopicRevision, db: DB, user: Actor, request: Request):
    entry, creator = topic_context(db, user, entry_id)
    validate_edit(db, creator, entry, data.expected_revision)
    entry.status, entry.source, entry.revision = "skipped", "user", entry.revision + 1
    return save(db, creator, entry, request, "editorial.skip")


@router.post("/topics/{entry_id}/reschedule")
def reschedule_topic(entry_id: str, data: TopicReschedule, db: DB, user: Actor, request: Request):
    entry, creator = topic_context(db, user, entry_id)
    validate_edit(db, creator, entry, data.expected_revision)
    if not local_today(creator) <= data.date <= local_today(creator) + timedelta(days=13):
        raise DomainError("EDITORIAL_DATE_INVALID", "请选择当前 14 天计划内的日期", 422)
    target_day = data.date.isoformat()
    if target_day == entry.date:
        return serialize_entry(db, creator, entry)
    if db.scalar(select(Run.id).where(Run.creator_id == creator.id, Run.operational_date == target_day)):
        raise DomainError("EDITORIAL_ALREADY_EXECUTED", "目标日期已经创建任务，不能交换")
    other = db.scalar(
        select(EditorialEntry).where(
            EditorialEntry.creator_id == creator.id,
            EditorialEntry.date == target_day,
        )
    )
    original = entry.date
    if other:
        validate_edit(db, creator, other, data.swap_revision)
        # Reserved sentinel outside the allowed date range, in the same locked transaction.
        entry.date = "0001-01-01"
        db.flush()
        other.date, other.status, other.source = original, "planned", "user"
        other.revision += 1
        db.flush()
    entry.date, entry.status, entry.source = target_day, "planned", "user"
    entry.revision += 1
    return save(db, creator, entry, request, "editorial.reschedule")


@router.post("/creators/{creator_id}/prepare")
def prepare_topics(creator_id: str, data: Prepare, db: DB, user: Actor, request: Request):
    creator = owned(db, Creator, creator_id, user.workspace_id)
    lock_creator(db, creator)
    if creator.status != "active":
        raise DomainError("CREATOR_SCHEDULE_PAUSED", "创作者已暂停，请先恢复")
    selected = [owned(db, EditorialEntry, i, user.workspace_id) for i in data.entry_ids]
    for entry in selected:
        db.refresh(entry)
        if entry.creator_id != creator.id:
            raise DomainError("NOT_FOUND", "选题不存在", 404)
        if data.expected_revisions.get(entry.id) != entry.revision:
            raise DomainError("EDITORIAL_REVISION_CONFLICT", "所选选题版本已变化，请刷新并重新确认")
        if entry.status not in {"approved", "queued", "completed", "failed"}:
            raise DomainError("EDITORIAL_APPROVAL_REQUIRED", "请先确认全部所选选题")
        if date.fromisoformat(entry.date) < local_today(creator):
            raise DomainError("EDITORIAL_DATE_EXPIRED", "已过期选题需要先改期")
        validate_facts(db, creator, entry)
    result = [
        enqueue(db, creator, e.date, f"editorial:{e.id}", request.state.trace_id, entry=e, commit=False)[0]
        for e in selected
    ]
    db.commit()
    return {"runs": [serialize(r) for r in result], "count": len(result)}
