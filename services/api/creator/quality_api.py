from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import FileResponse
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import current_user
from .db import get_db
from .domains import digest, owned, serialize
from .errors import DomainError
from .models import QualityReport, QualityReview, RenderJob, User, Video
from .quality import build_report, preview_file, subject
from .schemas import DTO
from .observability import record
from .video_edit import lock_video

router = APIRouter(prefix="/api/v1")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


class Confirm(DTO):
    confirmed: Literal[True]


class Preview(Confirm):
    expected_revision: int = Field(ge=1)


class Review(Preview):
    preview_job_id: str = Field(min_length=1, max_length=32)
    report_id: str = Field(min_length=1, max_length=32)
    decision: Literal["accept", "needs_rework"]
    note: str = Field(min_length=4, max_length=2000)


class AIReview(Confirm):
    creator_id: str = Field(min_length=1, max_length=32)
    expected_revision: int = Field(ge=1)
    max_cost_cents: int = Field(ge=1, le=10000)


def report_list(db, user, kind, identifier):
    subject(db, kind, identifier, user.workspace_id)
    return [
        serialize(r)
        for r in db.scalars(
            select(QualityReport)
            .where(
                QualityReport.workspace_id == user.workspace_id,
                QualityReport.subject_type == kind,
                QualityReport.subject_id == identifier,
            )
            .order_by(QualityReport.created_at.desc(), QualityReport.id)
            .limit(30)
        )
    ]


@router.get("/content/packages/{content_id}/quality")
def content_reports(content_id: str, db: DB, user: Actor):
    return report_list(db, user, "content", content_id)


@router.get("/videos/{video_id}/quality")
def video_reports(video_id: str, db: DB, user: Actor):
    return report_list(db, user, "video", video_id)


def check(db, user, kind, identifier, trace):
    row = build_report(db, kind, subject(db, kind, identifier, user.workspace_id))
    record(
        db,
        user.workspace_id,
        trace,
        "quality.rules",
        "ok",
        revision=row.subject_revision,
        content_id=identifier if kind == "content" else None,
        video_project_id=identifier if kind == "video" else None,
    )
    db.commit()
    return serialize(row)


@router.post("/content/packages/{content_id}/quality", status_code=201)
def content_check(content_id: str, data: Confirm, db: DB, user: Actor, request: Request):
    return check(db, user, "content", content_id, request.state.trace_id)


@router.post("/videos/{video_id}/quality", status_code=201)
def video_check(video_id: str, data: Confirm, db: DB, user: Actor, request: Request):
    return check(db, user, "video", video_id, request.state.trace_id)


@router.post("/videos/{video_id}/preview", status_code=201)
def preview(video_id: str, data: Preview, db: DB, user: Actor, request: Request):
    from .video import validate_ir

    video = owned(db, Video, video_id, user.workspace_id)
    lock_video(db, video, data.expected_revision)
    validate_ir(db, user.workspace_id, video.ir)
    existing = db.scalar(
        select(RenderJob)
        .where(
            RenderJob.video_id == video.id,
            RenderJob.revision == video.revision,
            RenderJob.purpose == "preview",
            RenderJob.status.in_(["queued", "running", "completed"]),
        )
        .order_by(RenderJob.created_at.desc())
    )
    if existing:
        if existing.status != "completed":
            return serialize(existing)
        try:
            preview_file(db, video, existing)
            return serialize(existing)
        except DomainError as error:
            if error.code != "VID_OUTPUT_HASH_MISMATCH":
                raise
    job = RenderJob(
        workspace_id=user.workspace_id,
        video_id=video.id,
        revision=video.revision,
        ir=video.ir,
        purpose="preview",
        trace_id=request.state.trace_id,
    )
    db.add(job)
    video.status = "queued"
    db.commit()
    return serialize(job)


@router.get("/videos/{video_id}/preview/download")
def preview_download(video_id: str, db: DB, user: Actor):
    video = owned(db, Video, video_id, user.workspace_id)
    path, job = preview_file(db, video)
    return FileResponse(path, media_type="video/mp4", filename=f"internal-preview-v{job.revision}.mp4")


@router.get("/videos/{video_id}/quality-reviews")
def reviews(video_id: str, db: DB, user: Actor):
    owned(db, Video, video_id, user.workspace_id)
    return [
        serialize(r)
        for r in db.scalars(
            select(QualityReview)
            .where(QualityReview.video_id == video_id)
            .order_by(QualityReview.created_at.desc(), QualityReview.id)
            .limit(30)
        )
    ]


@router.post("/videos/{video_id}/quality-review", status_code=201)
def review(video_id: str, data: Review, db: DB, user: Actor, request: Request):
    video = owned(db, Video, video_id, user.workspace_id)
    lock_video(db, video, data.expected_revision)
    job = owned(db, RenderJob, data.preview_job_id, user.workspace_id)
    preview_file(db, video, job)
    report = owned(db, QualityReport, data.report_id, user.workspace_id)
    current = build_report(db, "video", video)
    if report.id != current.id or digest(job.ir) != digest(video.ir):
        raise DomainError("QUALITY_REPORT_STALE", "报告或预览已过期，请重新检查")
    if data.decision == "accept" and report.report["decision"] == "blocked":
        raise DomainError("QA_CONTENT_BLOCKED", "不能确认有硬性阻断项的工程", 422)
    row = QualityReview(
        workspace_id=user.workspace_id,
        video_id=video.id,
        revision=video.revision,
        preview_job_id=job.id,
        report_id=report.id,
        decision=data.decision,
        note=data.note,
        recorded_by=user.id,
    )
    db.add(row)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "quality.human_review",
        "ok",
        video_project_id=video.id,
        render_job_id=job.id,
        revision=video.revision,
        decision=data.decision,
    )
    db.commit()
    return serialize(row)


def enqueue_ai(db, user, kind, identifier, data, key, trace_id):
    from .quality_jobs import enqueue

    if user.role not in ("owner", "admin"):
        raise DomainError("AUTH_FORBIDDEN", "仅管理员可提交使用模型预算的质量复核", 403)
    item = subject(db, kind, identifier, user.workspace_id)
    if item.revision != data.expected_revision:
        raise DomainError("QUALITY_REPORT_STALE", "作品已变化，请刷新")
    return serialize(enqueue(db, item, kind, data.creator_id, data.max_cost_cents, key, trace_id, user.id))


@router.post("/content/packages/{content_id}/quality/ai", status_code=201)
def content_ai(
    content_id: str,
    data: AIReview,
    db: DB,
    user: Actor,
    request: Request,
    idempotency_key: str = Header(min_length=1, max_length=160),
):
    return enqueue_ai(db, user, "content", content_id, data, idempotency_key, request.state.trace_id)


@router.post("/videos/{video_id}/quality/ai", status_code=201)
def video_ai(
    video_id: str,
    data: AIReview,
    db: DB,
    user: Actor,
    request: Request,
    idempotency_key: str = Header(min_length=1, max_length=160),
):
    return enqueue_ai(db, user, "video", video_id, data, idempotency_key, request.state.trace_id)
