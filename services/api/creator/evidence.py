"""Private version evidence, kept separately from public diagnostics."""

import json

from sqlalchemy import select

from .models import ContentRevision

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
