from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import current_user
from .db import get_db
from .domains import compliance_report, owned, serialize
from .errors import DomainError
from .evidence import checkpoint as content_checkpoint, invalidate_content
from .graphics import lock_content
from .models import Content, Creator, User, Video, VideoRevision
from .models import Brand
from .schemas import DTO, VideoInput
from .video import validate_ir
from .video_edit import checkpoint, current_output, lock_video, subtitles_srt

router = APIRouter(prefix="/api/v1")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


class SaveProject(DTO):
    expected_revision: int = Field(ge=1)
    document: VideoInput


class Restore(DTO):
    expected_revision: int = Field(ge=1)
    confirmed: Literal[True]


class LockShot(DTO):
    expected_revision: int = Field(ge=1)
    locked: bool


class AttachVideo(Restore):
    video_id: str | None = Field(default=None, max_length=120)


class SpeechInput(DTO):
    brand_id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=4000)
    voice_id: str = Field(min_length=1, max_length=120)
    confirmed: Literal[True]


@router.get("/videos/voices")
def system_voices(user: Actor):
    from .speech import voices

    return {"provider": "windows_sapi_offline", "voices": voices(), "license_verified": False}


@router.post("/videos/speech", status_code=201)
def create_speech(data: SpeechInput, db: DB, user: Actor):
    from .speech import synthesize

    owned(db, Brand, data.brand_id, user.workspace_id)
    asset = synthesize(user.workspace_id, data.brand_id, data.text, data.voice_id)
    db.add(asset)
    db.commit()
    return serialize(asset)


def save(db, video, ir, editor):
    # A manual edit starts a private revision; it must be explicitly rebound and reviewed.
    ir = {key: value for key, value in ir.items() if not key.startswith("source_")}
    ir["preview_required"] = video.preview_required
    if ir["brand_id"] != video.brand_id:
        raise DomainError("VID_IR_INVALID", "视频不能移动到其他品牌", 422)
    validate_ir(db, video.workspace_id, ir)
    checkpoint(db, video, editor)
    video.ir, video.name, video.status = ir, ir["name"], "draft"
    video.revision += 1
    checkpoint(db, video, editor)
    db.commit()
    return serialize(video)


@router.put("/videos/{video_id}/project")
def save_project(video_id: str, data: SaveProject, db: DB, user: Actor):
    video = owned(db, Video, video_id, user.workspace_id)
    lock_video(db, video, data.expected_revision)
    ir = {"schema_version": "1.1", **data.document.model_dump()}
    new = {s["shot_id"]: s for s in ir["shots"]}
    for old in video.ir["shots"]:
        if old["locked"] and new.get(old["shot_id"]) != old:
            raise DomainError("VID_SHOT_LOCKED", "先主动解锁镜头，再修改或删除")
    for shot in ir["shots"]:
        old = next((s for s in video.ir["shots"] if s["shot_id"] == shot["shot_id"]), None)
        if old:
            visual_old = {k: v for k, v in old.items() if k not in ("shot_revision", "locked")}
            visual_new = {k: v for k, v in shot.items() if k not in ("shot_revision", "locked")}
            shot["shot_revision"] = old["shot_revision"] + (visual_old != visual_new)
    return save(db, video, ir, user.id)


@router.get("/videos/{video_id}/history")
def history(video_id: str, db: DB, user: Actor):
    video = owned(db, Video, video_id, user.workspace_id)
    rows = [
        serialize(r)
        for r in db.scalars(
            select(VideoRevision)
            .where(VideoRevision.video_id == video.id)
            .order_by(VideoRevision.revision.desc())
        )
    ]
    if not any(r["revision"] == video.revision for r in rows):
        rows.insert(0, {"revision": video.revision, "document": video.ir})
    return rows


@router.post("/videos/{video_id}/restore/{revision}")
def restore(video_id: str, revision: int, data: Restore, db: DB, user: Actor):
    video = owned(db, Video, video_id, user.workspace_id)
    lock_video(db, video, data.expected_revision)
    old = db.scalar(
        select(VideoRevision).where(VideoRevision.video_id == video.id, VideoRevision.revision == revision)
    )
    if not old:
        raise DomainError("RESOURCE_NOT_FOUND", "视频版本不存在", 404)
    # Explicit user recovery; no agent tool can silently rewrite a locked shot.
    return save(db, video, old.document, user.id)


@router.post("/videos/{video_id}/shots/{shot_id}/lock")
def lock_shot(video_id: str, shot_id: str, data: LockShot, db: DB, user: Actor):
    import copy

    video = owned(db, Video, video_id, user.workspace_id)
    lock_video(db, video, data.expected_revision)
    ir = copy.deepcopy(video.ir)
    shot = next((s for s in ir["shots"] if s["shot_id"] == shot_id), None)
    if not shot:
        raise DomainError("RESOURCE_NOT_FOUND", "镜头不存在", 404)
    shot["locked"] = data.locked
    return save(db, video, ir, user.id)


@router.get("/videos/{video_id}/subtitles")
def download_subtitles(video_id: str, db: DB, user: Actor):
    video = owned(db, Video, video_id, user.workspace_id)
    return Response(
        subtitles_srt(video.ir),
        media_type="application/x-subrip",
        headers={"Content-Disposition": f'attachment; filename="subtitles-v{video.revision}.srt"'},
    )


@router.post("/content/packages/{content_id}/video")
def attach_video(content_id: str, data: AttachVideo, db: DB, user: Actor):
    content = owned(db, Content, content_id, user.workspace_id)
    lock_content(db, content, data.expected_revision)
    if content.status == "user_reported_published":
        raise DomainError("CONTENT_ALREADY_REPORTED", "已登记历史保持只读")
    binding = None
    if data.video_id:
        video = owned(db, Video, data.video_id, user.workspace_id)
        if video.brand_id != db.get(Creator, content.creator_id).brand_id:
            raise DomainError("VID_IR_INVALID", "请选择同一品牌的视频", 422)
        current_output(db, video)
        binding = {"video_id": video.id, "revision": video.revision, "sha256": video.output_hash}
    content_checkpoint(db, content, user.id)
    content.video_attachment = binding
    invalidate_content(db, content, user.id, "video_attachment")
    content.compliance = compliance_report(db, content)
    db.commit()
    return serialize(content)
