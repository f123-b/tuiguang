"""Private version evidence, kept separately from public diagnostics."""

import json

from sqlalchemy import select

from .models import Content, ContentRevision, Video

SNAPSHOT_FIELDS = ("title", "body", "fact_refs", "graphics", "variants", "video_attachment")


def snapshot(content):
    return json.loads(json.dumps({key: getattr(content, key) for key in SNAPSHOT_FIELDS}, ensure_ascii=False))


def checkpoint(db, content, editor_id, reason="edit"):
    if not db.scalar(
        select(ContentRevision.id).where(
            ContentRevision.content_id == content.id, ContentRevision.revision == content.revision
        )
    ):
        db.add(
            ContentRevision(
                workspace_id=content.workspace_id,
                content_id=content.id,
                revision=content.revision,
                snapshot=snapshot(content),
                editor_id=editor_id,
                reason_tag=reason,
            )
        )
        db.flush()


def invalidate_content(db, content, editor_id, reason):
    checkpoint(db, content, editor_id)
    content.revision += 1
    content.approved_revision = None
    content.graphics_render = None
    content.status = "awaiting_user_review"
    checkpoint(db, content, editor_id, reason)


def invalidate_asset(db, asset, editor_id, reason="asset_revoked"):
    affected = set()
    for video in db.scalars(select(Video).where(Video.workspace_id == asset.workspace_id)):
        if any(s.get("asset_id") == asset.id for s in video.ir["shots"] + video.ir.get("audio_tracks", [])):
            affected.add(video.id)
            video.status, video.rendered_revision = "draft", None
    for content in db.scalars(
        select(Content).where(
            Content.workspace_id == asset.workspace_id, Content.status != "user_reported_published"
        )
    ):
        uses_image = content.graphics and any(
            p.get("asset_id") == asset.id for p in content.graphics.get("pages", [])
        )
        uses_video = content.video_attachment and content.video_attachment.get("video_id") in affected
        if uses_image or uses_video:
            from .graphics import lock_content

            lock_content(db, content)
            invalidate_content(db, content, editor_id, reason)
