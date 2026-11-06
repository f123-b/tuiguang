import json

from sqlalchemy import select, update

from .domains import owned
from .errors import DomainError
from .models import RenderJob, Video, VideoRevision


def lock_video(db, video, expected=None):
    db.execute(update(Video).where(Video.id == video.id).values(revision=Video.revision))
    db.refresh(video)
    if expected is not None and video.revision != expected:
        raise DomainError("VID_REVISION_CONFLICT", "视频工程已经变化，请刷新后重新编辑")


def checkpoint(db, video, editor):
    if not db.scalar(
        select(VideoRevision.id).where(
            VideoRevision.video_id == video.id, VideoRevision.revision == video.revision
        )
    ):
        db.add(
            VideoRevision(
                workspace_id=video.workspace_id,
                video_id=video.id,
                revision=video.revision,
                document=json.loads(json.dumps(video.ir)),
                editor_id=editor,
            )
        )
        db.flush()


def current_output(db, video):
    from .config import DATA_DIR
    from .domains import digest
    from .video import validate_ir

    validate_ir(db, video.workspace_id, video.ir)
    if not video.output_hash or video.rendered_revision != video.revision:
        raise DomainError("VID_OUTPUT_NOT_READY", "当前版本尚未完成真实渲染")
    if video.preview_required:
        from .quality import require_review

        require_review(db, video)
    path = DATA_DIR / video.workspace_id / "cache" / (video.output_hash + ".mp4")
    if not path.is_file() or digest(path.read_bytes()) != video.output_hash:
        raise DomainError("VID_OUTPUT_HASH_MISMATCH", "视频文件缺失或已改变，请重新渲染")
    return path


def attachment(db, content):
    saved = content.video_attachment
    if not saved:
        return None
    video = owned(db, Video, saved["video_id"], content.workspace_id)
    if video.revision != saved["revision"] or video.output_hash != saved["sha256"]:
        raise DomainError("VID_ATTACHMENT_STALE", "绑定的视频已修改，请重新渲染并绑定内容")
    path = current_output(db, video)
    job = db.scalar(
        select(RenderJob)
        .where(
            RenderJob.video_id == video.id,
            RenderJob.revision == video.revision,
            RenderJob.purpose == "final",
            RenderJob.status == "completed",
        )
        .order_by(RenderJob.created_at.desc())
    )
    if not job:
        raise DomainError("VID_OUTPUT_NOT_READY", "没有当前视频的完成回执")
    return video, path, job.receipt


def subtitles_srt(ir):
    def stamp(frame):
        ms = round(frame * 1000 / ir["fps"])
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    return (
        "\n\n".join(
            f"{i + 1}\n{stamp(c['start_frame'])} --> {stamp(c['end_frame'])}\n{c['text']}"
            for i, c in enumerate(ir.get("subtitles", []))
        )
        + "\n"
    )
