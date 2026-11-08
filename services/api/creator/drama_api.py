from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import current_user
from .briefs import private_summary
from .db import get_db
from .domains import owned
from .drama import (
    DramaBrief,
    DramaPlan,
    approved,
    confirm,
    evidence,
    lock,
    production_recipe,
    public,
    queue_shot,
    save_plan,
    shot_request,
)
from .drama_skills import registry
from .errors import DomainError
from .models import Brand, DramaProject, Run, User
from .narration import NarrationOptions
from .observability import record
from .schemas import DTO

router = APIRouter(prefix="/api/v1/dramas")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


class Revision(DTO):
    expected_revision: int = Field(ge=1)


class Edit(Revision):
    document: DramaPlan


class Confirm(Revision):
    confirmed: Literal[True]
    note: str = Field(min_length=5, max_length=1000)


class PlanAI(Revision):
    confirmed: Literal[True]
    creator_id: str = Field(min_length=1, max_length=120)
    max_cost_cents: int = Field(ge=1, le=10000)


class Build(Revision):
    confirmed: Literal[True]
    narration: NarrationOptions | None = None


class Generate(Revision):
    confirmed: Literal[True]
    take_key: str | None = Field(default=None, min_length=1, max_length=120)


@router.get("/skills")
def skills(user: Actor):
    return registry()


@router.get("")
def projects(db: DB, user: Actor):
    return [
        {"id": p.id, "revision": p.revision, "document": p.document, "created_at": p.created_at}
        for p in db.scalars(
            select(DramaProject)
            .where(DramaProject.workspace_id == user.workspace_id)
            .order_by(DramaProject.created_at.desc())
            .limit(100)
        )
    ]


@router.post("", status_code=201)
def create(data: DramaBrief, db: DB, user: Actor, request: Request):
    owned(db, Brand, data.brand_id, user.workspace_id)
    item = DramaProject(workspace_id=user.workspace_id, brand_id=data.brand_id, document=data.model_dump())
    db.add(item)
    db.flush()
    evidence(db, item)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "drama.save",
        "ok",
        drama_project_id=item.id,
        revision=item.revision,
    )
    db.commit()
    return public(db, item)


@router.get("/{identifier}")
def detail(identifier: str, db: DB, user: Actor):
    item = owned(db, DramaProject, identifier, user.workspace_id)
    runs = db.scalars(
        select(Run)
        .where(
            Run.workspace_id == user.workspace_id,
            Run.release["job_kind"].as_string() == "drama_plan",
            Run.input_snapshot["drama_id"].as_string() == item.id,
        )
        .order_by(Run.created_at.desc())
        .limit(20)
    )
    return {"project": public(db, item), "runs": [private_summary(r) for r in runs]}


@router.put("/{identifier}/plan")
def edit(identifier: str, data: Edit, db: DB, user: Actor, request: Request):
    item = owned(db, DramaProject, identifier, user.workspace_id)
    lock(db, item, data.expected_revision)
    save_plan(db, item, data.document.model_dump(), user.id)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "drama.plan",
        "ok",
        drama_project_id=item.id,
        revision=item.revision,
    )
    db.commit()
    return public(db, item)


@router.post("/{identifier}/confirm")
def accept(identifier: str, data: Confirm, db: DB, user: Actor, request: Request):
    item = owned(db, DramaProject, identifier, user.workspace_id)
    lock(db, item, data.expected_revision)
    confirm(db, item, user.id, data.note)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "drama.confirm",
        "ok",
        drama_project_id=item.id,
        revision=item.revision,
    )
    db.commit()
    return public(db, item)


@router.post("/{identifier}/plan-ai", status_code=201)
def plan_ai(
    identifier: str,
    data: PlanAI,
    db: DB,
    user: Actor,
    request: Request,
    idempotency_key: str = Header(min_length=1, max_length=160),
):
    from .drama_jobs import enqueue

    if user.role not in ("owner", "admin"):
        raise DomainError("AUTH_FORBIDDEN", "仅管理员可提交付费模型请求", 403)
    item = owned(db, DramaProject, identifier, user.workspace_id)
    lock(db, item, data.expected_revision)
    return private_summary(
        enqueue(
            db, item, data.creator_id, data.max_cost_cents, idempotency_key, request.state.trace_id, user.id
        )
    )


@router.get("/{identifier}/shots/{shot_id}/request")
def preview_request(identifier: str, shot_id: str, db: DB, user: Actor):
    item = owned(db, DramaProject, identifier, user.workspace_id)
    approved(db, item)
    shot = next((s for s in item.plan["shots"] if s["id"] == shot_id), None)
    if not shot:
        raise DomainError("RESOURCE_NOT_FOUND", "镜头不存在", 404)
    return shot_request(db, item, shot).model_dump()


@router.post("/{identifier}/shots/{shot_id}/generate", status_code=201)
def generate(identifier: str, shot_id: str, data: Generate, db: DB, user: Actor, request: Request):
    from .video_generation import public_job

    item = owned(db, DramaProject, identifier, user.workspace_id)
    lock(db, item, data.expected_revision)
    job = queue_shot(db, item, shot_id, user, request.state.trace_id, data.take_key)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "drama.shot",
        "ok",
        drama_project_id=item.id,
        shot_id=shot_id,
        generation_job_id=job.id,
    )
    db.commit()
    return public_job(db, job)


@router.post("/{identifier}/build", status_code=201)
def build(identifier: str, data: Build, db: DB, user: Actor, request: Request):
    from .video_recipes import create_from_recipe

    item = owned(db, DramaProject, identifier, user.workspace_id)
    lock(db, item, data.expected_revision)
    if data.narration and data.narration.fit_mode != "fixed":
        raise DomainError("DRAMA_FIXED_DURATION", "短剧配音使用固定时长，避免停帧拉长表演", 422)
    # Preserve silent reaction shots. The generic recipe's spoken-caption
    # fallback is appropriate for explainers, not a drama's quiet moments.
    recipe = production_recipe(db, item, data.narration)
    video = create_from_recipe(
        db,
        user,
        recipe,
        "drama-film:" + item.id + ":" + str(item.revision),
        request.state.trace_id,
        narration_lines=[s["narration"] for s in item.plan["shots"]],
    )
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "drama.build",
        "ok",
        drama_project_id=item.id,
        video_project_id=video.id,
    )
    db.commit()
    return {"video_id": video.id}
