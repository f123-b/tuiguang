import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from .auth import current_user
from .db import get_db
from .domains import compliance_report, file_path, owned, serialize
from .errors import DomainError
from .graphics import (
    GraphicRender,
    GraphicSave,
    current_receipt,
    lock_content,
    render_graphics,
    validate_graphics,
)
from .models import Content, User
from .observability import record

router = APIRouter(prefix="/api/v1/content/packages")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


@router.get("/{content_id}/graphics")
def get_graphics(content_id: str, db: DB, user: Actor):
    content = owned(db, Content, content_id, user.workspace_id)
    return {
        "content_revision": content.revision,
        "document": content.graphics,
        "render": content.graphics_render,
    }


@router.put("/{content_id}/graphics")
def save_graphics(content_id: str, data: GraphicSave, db: DB, user: Actor, request: Request):
    content = owned(db, Content, content_id, user.workspace_id)
    lock_content(db, content, data.expected_revision)
    if content.status == "user_reported_published":
        raise DomainError("CONTENT_ALREADY_REPORTED", "已登记内容保留历史快照，须先撤销登记再编辑")
    validate_graphics(db, content, data.document)
    content.graphics, content.graphics_render = data.document.model_dump(), None
    content.revision += 1
    content.approved_revision, content.status = None, "awaiting_user_review"
    content.compliance = compliance_report(db, content)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "graphics.save",
        "ok",
        content_id=content.id,
        revision=content.revision,
    )
    db.commit()
    return serialize(content)


@router.post("/{content_id}/graphics/render")
def preview_graphics(content_id: str, data: GraphicRender, db: DB, user: Actor, request: Request):
    content = owned(db, Content, content_id, user.workspace_id)
    lock_content(db, content, data.expected_revision)
    if content.status == "user_reported_published":
        raise DomainError("CONTENT_ALREADY_REPORTED", "已登记作品保留原始图文与审核记录，不能重新生成")
    receipt = render_graphics(db, content)
    content.compliance = compliance_report(db, content)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "graphics.render",
        "ok",
        content_id=content.id,
        revision=content.revision,
        cached=receipt["cached"],
        sha256=receipt["cache_key"],
    )
    db.commit()
    return receipt


def page_file(db, content, index, revision, fmt):
    if revision != content.revision:
        raise DomainError("CONTENT_REVISION_CONFLICT", "图片对应旧版内容，请刷新")
    receipt = current_receipt(db, content)
    if not 0 <= index < len(receipt["pages"]):
        raise DomainError("RESOURCE_NOT_FOUND", "图文页不存在", 404)
    return file_path(content.workspace_id, receipt["pages"][index][fmt + "_sha256"], "." + fmt)


@router.get("/{content_id}/graphics/pages/{index}/preview")
def get_preview(content_id: str, index: int, db: DB, user: Actor, revision: int = Query(ge=1)):
    content = owned(db, Content, content_id, user.workspace_id)
    return FileResponse(page_file(db, content, index, revision, "png"), media_type="image/png")


@router.get("/{content_id}/graphics/pages/{index}/download")
def download_graphic(
    content_id: str,
    index: int,
    db: DB,
    user: Actor,
    revision: int = Query(ge=1),
    format: Literal["png", "jpg"] = "png",
):
    content = owned(db, Content, content_id, user.workspace_id)
    if content.approved_revision != content.revision or compliance_report(db, content)["status"] == "blocked":
        raise DomainError("QA_CONTENT_BLOCKED", "请先生成真实预览，复核图文并完成人工审核")
    path = page_file(db, content, index, revision, format)
    return FileResponse(
        path,
        filename=f"graphic-{index + 1:02d}-v{revision}.{format}",
        media_type="image/png" if format == "png" else "image/jpeg",
    )


@router.get("/{content_id}/graphics/project")
def download_project(content_id: str, db: DB, user: Actor):
    content = owned(db, Content, content_id, user.workspace_id)
    data = {
        "content_id": content.id,
        "content_revision": content.revision,
        "document": content.graphics,
        "reviewed": content.approved_revision == content.revision,
        "manual_publish_only": True,
    }
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="graphic-project-v{content.revision}.json"'},
    )
