from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .auth import current_user
from .db import get_db
from .domains import compliance_report, owned, serialize
from .errors import DomainError
from .evidence import checkpoint, invalidate_content, snapshot
from .graphics import lock_content
from .models import Asset, Brand, BrandChange, Content, ContentRevision, Creator, User, Video, now_iso, uid
from .observability import record
from .schemas import DTO

router = APIRouter(prefix="/api/v1")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


class ChangeInput(DTO):
    claim: str = Field(min_length=1, max_length=1000)
    source: str = Field(min_length=1, max_length=2000)
    product_version: str = Field(min_length=1, max_length=100)


class ChangeDecision(DTO):
    decision: Literal["verified", "rejected"]
    released: bool = False
    confirmed: Literal[True]
    expected_brand_revision: int = Field(ge=1)


class Restore(DTO):
    confirmed: Literal[True]
    expected_revision: int = Field(ge=1)


class AssetReview(DTO):
    verified: bool
    reason: str = Field(min_length=1, max_length=1000)


@router.get("/brands/{brand_id}/changes")
def changes(brand_id: str, db: DB, user: Actor):
    owned(db, Brand, brand_id, user.workspace_id)
    return [
        serialize(c)
        for c in db.scalars(
            select(BrandChange)
            .where(BrandChange.brand_id == brand_id)
            .order_by(BrandChange.created_at.desc())
        )
    ]


@router.post("/brands/{brand_id}/changes", status_code=201)
def propose(brand_id: str, data: ChangeInput, db: DB, user: Actor):
    owned(db, Brand, brand_id, user.workspace_id)
    proposal = BrandChange(workspace_id=user.workspace_id, brand_id=brand_id, **data.model_dump())
    db.add(proposal)
    db.commit()
    return serialize(proposal)


@router.post("/brands/{brand_id}/changes/{change_id}/decide")
def decide(brand_id: str, change_id: str, data: ChangeDecision, db: DB, user: Actor, request: Request):
    brand = owned(db, Brand, brand_id, user.workspace_id)
    db.execute(update(Brand).where(Brand.id == brand.id).values(revision=Brand.revision))
    db.refresh(brand)
    change = owned(db, BrandChange, change_id, user.workspace_id)
    db.refresh(change)
    if change.brand_id != brand.id:
        raise DomainError("RESOURCE_NOT_FOUND", "提案不存在", 404)
    if brand.revision != data.expected_brand_revision or change.status != "proposed":
        raise DomainError("BRAND_REVISION_CONFLICT", "资料已变化或提案已处理，请刷新")
    if data.decision == "verified" and not data.released:
        raise DomainError("BRAND_CHANGE_NOT_RELEASED", "未上线功能只能保留为待核实提案", 422)
    change.status, change.reviewed_by, change.reviewed_at = data.decision, user.id, now_iso()
    if data.decision == "verified":
        brand.facts = [
            *brand.facts,
            {
                "id": uid(),
                "claim": change.claim,
                "source": change.source,
                "verified": True,
                "locked": True,
                "product_version": change.product_version,
                "change_id": change.id,
            },
        ]
        brand.revision += 1
        creators = select(Creator.id).where(Creator.brand_id == brand.id)
        for content in db.scalars(
            select(Content).where(
                Content.creator_id.in_(creators), Content.status != "user_reported_published"
            )
        ):
            lock_content(db, content)
            invalidate_content(db, content, user.id, "brand_change")
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "brand.change.review",
        "ok",
        change_id=change.id,
        decision=change.status,
    )
    db.commit()
    return serialize(change)


@router.get("/content/packages/{content_id}/history")
def history(content_id: str, db: DB, user: Actor):
    content = owned(db, Content, content_id, user.workspace_id)
    rows = [
        serialize(c)
        for c in db.scalars(
            select(ContentRevision)
            .where(ContentRevision.content_id == content.id)
            .order_by(ContentRevision.revision.desc())
        )
    ]
    if not any(c["revision"] == content.revision for c in rows):
        rows.insert(
            0,
            {
                "revision": content.revision,
                "snapshot": snapshot(content),
                "reason_tag": "current",
                "created_at": content.created_at,
            },
        )
    return rows


@router.post("/content/packages/{content_id}/restore/{revision}")
def restore(content_id: str, revision: int, data: Restore, db: DB, user: Actor):
    content = owned(db, Content, content_id, user.workspace_id)
    lock_content(db, content, data.expected_revision)
    if content.status == "user_reported_published":
        raise DomainError("CONTENT_ALREADY_REPORTED", "已登记历史不可恢复覆盖")
    old = db.scalar(
        select(ContentRevision).where(
            ContentRevision.content_id == content.id, ContentRevision.revision == revision
        )
    )
    if not old:
        raise DomainError("RESOURCE_NOT_FOUND", "历史版本不存在", 404)
    checkpoint(db, content, user.id)
    for key, value in old.snapshot.items():
        setattr(content, key, value)
    invalidate_content(db, content, user.id, "restore")
    content.compliance = compliance_report(db, content)
    db.commit()
    return serialize(content)


@router.patch("/assets/{asset_id}")
def review_asset(asset_id: str, data: AssetReview, db: DB, user: Actor, request: Request):
    asset = owned(db, Asset, asset_id, user.workspace_id)
    asset.verified, asset.review_note = data.verified, data.reason
    if not data.verified:
        for content in db.scalars(
            select(Content).where(
                Content.workspace_id == user.workspace_id, Content.status != "user_reported_published"
            )
        ):
            if content.graphics and any(
                p.get("asset_id") == asset.id for p in content.graphics.get("pages", [])
            ):
                lock_content(db, content)
                invalidate_content(db, content, user.id, "asset_revoked")
                content.compliance = compliance_report(db, content)
        for video in db.scalars(select(Video).where(Video.workspace_id == user.workspace_id)):
            if any(
                s.get("asset_id") == asset.id for s in video.ir["shots"] + video.ir.get("audio_tracks", [])
            ):
                video.status, video.rendered_revision = "draft", None
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "asset.review",
        "ok",
        asset_id=asset.id,
        verified=data.verified,
    )
    db.commit()
    return serialize(asset)
