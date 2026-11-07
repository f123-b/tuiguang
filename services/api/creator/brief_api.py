from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import current_user
from .briefs import (
    BriefInput,
    ScriptInput,
    assert_current,
    build_video,
    lock_brief,
    manual_plan,
    private_summary,
    save_plan,
    snapshot,
)
from .db import get_db
from .domains import owned, serialize
from .errors import DomainError
from .models import Brand, BriefPlan, CreationBrief, Run, User
from .observability import record
from .schemas import DTO, Short, Presentation
from .narration import NarrationOptions, NarrationRequest

router = APIRouter(prefix="/api/v1/creation-briefs")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


class Revision(DTO):
    expected_revision: int = Field(ge=1)


class Save(Revision):
    document: BriefInput


class Confirm(Revision):
    confirmed: Literal[True]


class ScriptEdit(Revision):
    document: ScriptInput


class ModelRequest(Confirm):
    creator_id: Short
    max_cost_cents: int = Field(ge=1, le=10000)


class Build(Confirm):
    narration: NarrationOptions | None = None
    presentation: Presentation | None = None


@router.get("")
def briefs(db: DB, user: Actor):
    return [
        serialize(b)
        for b in db.scalars(
            select(CreationBrief)
            .where(CreationBrief.workspace_id == user.workspace_id)
            .order_by(CreationBrief.created_at.desc())
            .limit(100)
        )
    ]


@router.post("", status_code=201)
def create(data: BriefInput, db: DB, user: Actor, request: Request):
    owned(db, Brand, data.brand_id, user.workspace_id)
    brief = CreationBrief(
        workspace_id=user.workspace_id, brand_id=data.brand_id, topic=data.topic, document=data.model_dump()
    )
    db.add(brief)
    db.flush()
    snapshot(db, brief)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "brief.save",
        "ok",
        brief_id=brief.id,
        revision=brief.revision,
    )
    db.commit()
    return serialize(brief)


@router.get("/{brief_id}")
def detail(brief_id: str, db: DB, user: Actor):
    brief = owned(db, CreationBrief, brief_id, user.workspace_id)
    plans = db.scalars(
        select(BriefPlan)
        .where(BriefPlan.brief_id == brief.id)
        .order_by(BriefPlan.created_at.desc())
        .limit(50)
    ).all()
    rows = []
    for p in plans:
        row = serialize(p)
        try:
            assert_current(db, brief, p)
            row["stale"] = False
        except DomainError:
            row["stale"] = True
        rows.append(row)
    runs = db.scalars(
        select(Run)
        .where(
            Run.workspace_id == user.workspace_id,
            Run.release["job_kind"].as_string() == "brief_video",
            Run.input_snapshot["brief_id"].as_string() == brief.id,
        )
        .order_by(Run.created_at.desc())
        .limit(30)
    ).all()
    return {"brief": serialize(brief), "plans": rows, "runs": [private_summary(r) for r in runs]}


@router.put("/{brief_id}")
def save(brief_id: str, data: Save, db: DB, user: Actor, request: Request):
    brief = owned(db, CreationBrief, brief_id, user.workspace_id)
    lock_brief(db, brief, data.expected_revision)
    if data.document.brand_id != brief.brand_id:
        raise DomainError("AUTH_FORBIDDEN", "需求不能移动到其他品牌", 403)
    brief.document, brief.topic, brief.revision = (
        data.document.model_dump(),
        data.document.topic,
        brief.revision + 1,
    )
    snapshot(db, brief)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "brief.save",
        "ok",
        brief_id=brief.id,
        revision=brief.revision,
    )
    db.commit()
    return serialize(brief)


@router.post("/{brief_id}/plans/manual", status_code=201)
def prepare_manual(brief_id: str, data: Confirm, db: DB, user: Actor, request: Request):
    brief = owned(db, CreationBrief, brief_id, user.workspace_id)
    lock_brief(db, brief, data.expected_revision)
    plan = manual_plan(db, brief)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "brief.manual",
        "ok",
        brief_id=brief.id,
        plan_id=plan.id,
    )
    db.commit()
    return serialize(plan)


@router.post("/{brief_id}/plans/ai", status_code=201)
def prepare_ai(
    brief_id: str,
    data: ModelRequest,
    db: DB,
    user: Actor,
    request: Request,
    idempotency_key: str = Header(min_length=1, max_length=160),
):
    from .brief_jobs import enqueue

    if user.role not in ("owner", "admin"):
        raise DomainError("AUTH_FORBIDDEN", "仅管理员可以提交付费模型请求", 403)
    brief = owned(db, CreationBrief, brief_id, user.workspace_id)
    lock_brief(db, brief, data.expected_revision)
    return private_summary(
        enqueue(
            db, brief, data.creator_id, data.max_cost_cents, idempotency_key, request.state.trace_id, user.id
        )
    )


def plan_for(db, brief, plan_id, workspace):
    plan = owned(db, BriefPlan, plan_id, workspace)
    if plan.brief_id != brief.id:
        raise DomainError("RESOURCE_NOT_FOUND", "该需求下没有这份脚本", 404)
    return plan


@router.post("/{brief_id}/plans/{plan_id}/revisions", status_code=201)
def edit_script(brief_id: str, plan_id: str, data: ScriptEdit, db: DB, user: Actor, request: Request):
    brief = owned(db, CreationBrief, brief_id, user.workspace_id)
    lock_brief(db, brief, data.expected_revision)
    parent = plan_for(db, brief, plan_id, user.workspace_id)
    assert_current(db, brief, parent)
    plan = save_plan(db, brief, parent.evidence, data.document.model_dump(), "user_edit", parent_id=parent.id)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "brief.script_edit",
        "ok",
        brief_id=brief.id,
        plan_id=plan.id,
    )
    db.commit()
    return serialize(plan)


@router.post("/{brief_id}/plans/{plan_id}/build", status_code=201)
def build(brief_id: str, plan_id: str, data: Build, db: DB, user: Actor, request: Request):
    brief = owned(db, CreationBrief, brief_id, user.workspace_id)
    lock_brief(db, brief, data.expected_revision)
    plan = plan_for(db, brief, plan_id, user.workspace_id)
    result = build_video(
        db,
        brief,
        plan,
        user.id,
        request.state.trace_id,
        queue_preview=data.narration is None,
        presentation=data.presentation.model_dump() if data.presentation else None,
    )
    if data.narration:
        from .models import NarrationJob, Video
        from .narration import enqueue
        from .domains import digest

        voice_options = data.narration.model_dump()
        if voice_options["delivery_style"] == "plain":
            voice_options.pop("delivery_style")
        key = "brief-voice:" + plan.id + ":" + digest(voice_options)[:32]
        existing = db.scalar(
            select(NarrationJob).where(
                NarrationJob.workspace_id == user.workspace_id, NarrationJob.idempotency_key == key
            )
        )
        if not existing:
            video = owned(db, Video, result["video_id"], user.workspace_id)
            lines = [
                {"shot_id": "s" + str(i + 1), "text": s["narration"] or s["caption"]}
                for i, s in enumerate(plan.document["shots"])
            ]
            existing = enqueue(
                db,
                video,
                NarrationRequest(
                    **data.narration.model_dump(), expected_revision=video.revision, lines=lines
                ),
                key,
                user.id,
                request.state.trace_id,
            )
        result["narration_job_id"] = existing.id
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "brief.build",
        "ok",
        plan.run_id,
        brief_id=brief.id,
        plan_id=plan.id,
        video_project_id=result["video_id"],
    )
    db.commit()
    return result
