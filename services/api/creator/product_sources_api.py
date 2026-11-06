import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import current_user
from .db import get_db
from .domains import owned, serialize
from .errors import DomainError
from .models import (
    Asset,
    Brand,
    BrandChange,
    ProductCheck,
    ProductEvent,
    ProductSnapshot,
    ProductSource,
    User,
)
from .product_monitor import check_source, lock_source, store_snapshot
from .schemas import DTO
from .source_http import LIMIT, validate_url

router = APIRouter(prefix="/api/v1")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


class SourceInput(DTO):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["github_releases", "url_text", "uploaded_notes"]
    url: str | None = Field(default=None, max_length=1000)
    authorized: Literal[True]
    enabled: bool = True
    interval_minutes: int = Field(default=120, ge=15, le=10080)


class SourceEdit(DTO):
    expected_revision: int = Field(ge=1)
    enabled: bool
    confirmed: Literal[True]


class Confirm(DTO):
    confirmed: Literal[True]


class ProposeInput(Confirm):
    claim: str = Field(min_length=1, max_length=1000)
    product_version: str = Field(min_length=1, max_length=100)


class Applicability(Confirm):
    source_id: str | None = Field(default=None, min_length=1, max_length=120)
    product_version: str | None = Field(default=None, min_length=1, max_length=100)


@router.get("/brands/{brand_id}/product-sources")
def sources(brand_id: str, db: DB, user: Actor):
    owned(db, Brand, brand_id, user.workspace_id)
    rows = []
    for source in db.scalars(
        select(ProductSource)
        .where(ProductSource.brand_id == brand_id)
        .order_by(ProductSource.created_at.desc())
    ):
        row = serialize(source)
        snapshot = db.get(ProductSnapshot, source.current_snapshot_id) if source.current_snapshot_id else None
        row["current_version"] = snapshot.version if snapshot else None
        rows.append(row)
    return rows


@router.post("/brands/{brand_id}/product-sources", status_code=201)
def create(brand_id: str, data: SourceInput, db: DB, user: Actor):
    owned(db, Brand, brand_id, user.workspace_id)
    if data.kind != "uploaded_notes":
        if not data.url:
            raise DomainError("SOURCE_ADDRESS_DENIED", "请填写公开来源地址", 422)
        parts, host = validate_url(data.url)
        if data.kind == "github_releases" and (
            host != "github.com" or not re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?", parts.path)
        ):
            raise DomainError("SOURCE_ADDRESS_DENIED", "Release 来源须为 https://github.com/所有者/仓库", 422)
    elif data.url:
        raise DomainError("SOURCE_ADDRESS_DENIED", "上传来源不接受网络地址", 422)
    source = ProductSource(
        workspace_id=user.workspace_id, brand_id=brand_id, recorded_by=user.id, **data.model_dump()
    )
    db.add(source)
    db.commit()
    return serialize(source)


@router.patch("/product-sources/{source_id}")
def edit(source_id: str, data: SourceEdit, db: DB, user: Actor):
    source = owned(db, ProductSource, source_id, user.workspace_id)
    lock_source(db, source)
    if source.revision != data.expected_revision:
        raise DomainError("SOURCE_REVISION_CONFLICT", "来源设置已经变化，请刷新")
    source.enabled = data.enabled
    source.revision += 1
    db.commit()
    return serialize(source)


@router.post("/product-sources/{source_id}/check")
def check(source_id: str, data: Confirm, db: DB, user: Actor, request: Request):
    return check_source(db, owned(db, ProductSource, source_id, user.workspace_id), request.state.trace_id)


@router.post("/product-sources/{source_id}/upload")
async def upload(
    source_id: str,
    db: DB,
    user: Actor,
    request: Request,
    file: UploadFile = File(),
    version: str = Form(min_length=1, max_length=100),
    confirmed: bool = Form(),
):
    source = owned(db, ProductSource, source_id, user.workspace_id)
    if source.kind != "uploaded_notes" or not confirmed:
        raise DomainError("SOURCE_UPLOAD_REQUIRED", "请选择上传来源并确认该份版本说明", 422)
    if not (file.filename or "").lower().endswith((".txt", ".md")):
        raise DomainError("SOURCE_FORMAT_UNSUPPORTED", "请上传 UTF-8 TXT/Markdown 版本说明", 422)
    content = await file.read(LIMIT + 1)
    if len(content) > LIMIT:
        raise DomainError("SOURCE_TOO_LARGE", "版本说明超过 512 KiB", 422)
    try:
        text = content.decode("utf-8-sig")
    except UnicodeError:
        raise DomainError("SOURCE_FORMAT_UNSUPPORTED", "版本说明须使用 UTF-8 编码", 422) from None
    result = store_snapshot(db, source, text, version.strip(), request.state.trace_id)
    db.commit()
    return result


@router.get("/product-sources/{source_id}/snapshots")
def snapshots(source_id: str, db: DB, user: Actor):
    owned(db, ProductSource, source_id, user.workspace_id)
    return [
        serialize(r)
        for r in db.scalars(
            select(ProductSnapshot)
            .where(ProductSnapshot.source_id == source_id)
            .order_by(ProductSnapshot.created_at.desc())
            .limit(30)
        )
    ]


@router.get("/product-sources/{source_id}/checks")
def checks(source_id: str, db: DB, user: Actor):
    owned(db, ProductSource, source_id, user.workspace_id)
    return [
        serialize(r)
        for r in db.scalars(
            select(ProductCheck)
            .where(ProductCheck.source_id == source_id)
            .order_by(ProductCheck.created_at.desc())
            .limit(30)
        )
    ]


@router.get("/product-sources/{source_id}/events")
def events(source_id: str, db: DB, user: Actor):
    owned(db, ProductSource, source_id, user.workspace_id)
    return [
        serialize(r)
        for r in db.scalars(
            select(ProductEvent)
            .where(ProductEvent.source_id == source_id)
            .order_by(ProductEvent.created_at.desc())
            .limit(50)
        )
    ]


@router.post("/product-sources/{source_id}/events/{event_id}/propose", status_code=201)
def propose(source_id: str, event_id: str, data: ProposeInput, db: DB, user: Actor):
    source = owned(db, ProductSource, source_id, user.workspace_id)
    lock_source(db, source)
    event = owned(db, ProductEvent, event_id, user.workspace_id)
    if event.source_id != source.id:
        raise DomainError("RESOURCE_NOT_FOUND", "变更事件不存在", 404)
    if event.proposal_id:
        return serialize(db.get(BrandChange, event.proposal_id))
    snapshot = db.get(ProductSnapshot, event.snapshot_id)
    proposal = BrandChange(
        workspace_id=user.workspace_id,
        brand_id=source.brand_id,
        claim=data.claim,
        product_version=data.product_version,
        source=f"{source.url or source.name}\n事件 {event.id} / 快照 {snapshot.sha256}",
    )
    db.add(proposal)
    db.flush()
    event.proposal_id = proposal.id
    db.commit()
    return serialize(proposal)


@router.put("/assets/{asset_id}/applicability")
def applicability(asset_id: str, data: Applicability, db: DB, user: Actor):
    asset = owned(db, Asset, asset_id, user.workspace_id)
    if data.source_id:
        source = owned(db, ProductSource, data.source_id, user.workspace_id)
        lock_source(db, source)
        if source.brand_id != asset.brand_id or not data.product_version:
            raise DomainError("ASSET_VERSION_MISMATCH", "素材和来源须属于同一品牌，并填写适用版本", 422)
        snapshot = db.get(ProductSnapshot, source.current_snapshot_id) if source.current_snapshot_id else None
        if snapshot and snapshot.version and snapshot.version != data.product_version:
            raise DomainError("ASSET_VERSION_MISMATCH", "填写版本与当前来源版本不一致，请复核", 422)
    elif asset.applicability_status == "needs_review":
        raise DomainError("ASSET_VERSION_REVIEW_REQUIRED", "有待复核的素材须先确认来源与适用版本", 422)
    asset.product_source_id, asset.product_version, asset.applicability_status = (
        data.source_id,
        data.product_version,
        "current",
    )
    db.commit()
    return serialize(asset)
