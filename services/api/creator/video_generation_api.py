from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import FileResponse
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import current_user
from .db import get_db
from .domains import owned, serialize, verified_file
from .errors import DomainError
from .models import Asset, User, VideoGenerationJob
from .observability import record
from .schemas import DTO
from .video_generation import GenerationInput, enqueue, public_job, verify_output
from .wan_comfy import capabilities

router = APIRouter(prefix="/api/v1/video-generation")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


@router.get("/capabilities")
def capability(user: Actor):
    return capabilities()


@router.post("/jobs", status_code=201)
def create(
    data: GenerationInput,
    db: DB,
    user: Actor,
    request: Request,
    idempotency_key: str = Header(min_length=1, max_length=160),
):
    job = enqueue(db, data, user, idempotency_key, request.state.trace_id)
    db.commit()
    return public_job(db, job)


@router.get("/jobs")
def jobs(db: DB, user: Actor):
    return [
        public_job(db, j)
        for j in db.scalars(
            select(VideoGenerationJob)
            .where(VideoGenerationJob.workspace_id == user.workspace_id)
            .order_by(VideoGenerationJob.created_at.desc())
            .limit(100)
        )
    ]


@router.get("/jobs/{job_id}/video")
def preview(job_id: str, db: DB, user: Actor):
    job = owned(db, VideoGenerationJob, job_id, user.workspace_id)
    if job.status != "completed" or not job.output_asset_id:
        raise DomainError("GEN_OUTPUT_NOT_READY", "此片段尚未完成", 409)
    asset = owned(db, Asset, job.output_asset_id, user.workspace_id)
    return FileResponse(
        verified_file(asset.workspace_id, asset.sha256, asset.suffix),
        media_type="video/mp4",
        filename="ai-shot-" + job.id[:8] + ".mp4",
    )


@router.post("/jobs/{job_id}/cancel")
def cancel(job_id: str, db: DB, user: Actor, request: Request):
    from sqlalchemy import update

    job = owned(db, VideoGenerationJob, job_id, user.workspace_id)
    result = db.execute(
        update(VideoGenerationJob)
        .where(
            VideoGenerationJob.id == job.id,
            VideoGenerationJob.status == "queued",
            VideoGenerationJob.lease_until.is_(None),
        )
        .values(status="cancelled", stage="generation.cancelled")
    )
    if result.rowcount != 1:
        raise DomainError("GEN_ALREADY_CLAIMED", "镜头已开始处理，不能把已提交的生成伪装成撤回", 409)
    record(db, user.workspace_id, request.state.trace_id, "generation.cancel", "ok", generation_job_id=job.id)
    db.commit()
    db.refresh(job)
    return public_job(db, job)


class Verify(DTO):
    confirmed: Literal[True]
    note: str = Field(min_length=5, max_length=1000)


@router.post("/jobs/{job_id}/check-existing")
def check_existing(job_id: str, db: DB, user: Actor):
    job = owned(db, VideoGenerationJob, job_id, user.workspace_id)
    if job.status != "unknown" or not job.provider_request_id:
        raise DomainError("GEN_RECEIPT_REQUIRED", "没有可安全读取的已有生成回执；不会重新提交", 409)
    job.status, job.stage, job.lease_until = "running", "generation.checking_existing", None
    db.commit()
    return public_job(db, job)


@router.post("/jobs/{job_id}/verify")
def verify(job_id: str, data: Verify, db: DB, user: Actor, request: Request):
    job = owned(db, VideoGenerationJob, job_id, user.workspace_id)
    asset = verify_output(db, job, data.note, user.id)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "generation.review",
        "ok",
        generation_job_id=job.id,
        asset_id=asset.id,
        verified=True,
    )
    db.commit()
    return serialize(asset)
