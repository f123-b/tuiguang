from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import current_user
from .db import get_db
from .domains import owned, verified_file
from .errors import DomainError
from .models import Asset, NarrationJob, User, Video
from .narration import NarrationRequest, enqueue, public_job

router = APIRouter(prefix="/api/v1/videos")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


@router.post("/{video_id}/narration-jobs", status_code=201)
def create(
    video_id: str,
    data: NarrationRequest,
    db: DB,
    user: Actor,
    request: Request,
    idempotency_key: str = Header(min_length=1, max_length=160),
):
    video = owned(db, Video, video_id, user.workspace_id)
    job = enqueue(db, video, data, idempotency_key, user.id, request.state.trace_id)
    db.commit()
    return public_job(job)


@router.get("/{video_id}/narration-jobs")
def jobs(video_id: str, db: DB, user: Actor):
    owned(db, Video, video_id, user.workspace_id)
    return [
        public_job(j)
        for j in db.scalars(
            select(NarrationJob)
            .where(NarrationJob.video_id == video_id)
            .order_by(NarrationJob.created_at.desc())
            .limit(30)
        )
    ]


@router.get("/{video_id}/narration-jobs/{job_id}/audio")
def audio(video_id: str, job_id: str, db: DB, user: Actor):
    job = owned(db, NarrationJob, job_id, user.workspace_id)
    if job.video_id != video_id or job.status != "completed":
        raise DomainError("TTS_OUTPUT_NOT_READY", "没有此视频已完成的配音", 404)
    asset = owned(db, Asset, job.receipt["audio_asset_id"], user.workspace_id)
    return FileResponse(
        verified_file(asset.workspace_id, asset.sha256, asset.suffix),
        media_type="audio/wav",
        filename="narration.wav",
    )
