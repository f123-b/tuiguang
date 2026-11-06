"""Authorized product snapshots. Changes are observations, never verified facts."""

import difflib
import json
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit

from sqlalchemy import or_, select, update

from . import source_http
from .domains import digest
from .errors import DomainError
from .evidence import invalidate_asset
from .models import Asset, ProductCheck, ProductEvent, ProductSnapshot, ProductSource, now_iso, uid
from .observability import record


class ReadableHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def lock_source(db, source):
    db.execute(
        update(ProductSource).where(ProductSource.id == source.id).values(revision=ProductSource.revision)
    )
    db.refresh(source)


def normalize(text):
    if len(text.encode()) > source_http.LIMIT or any(ord(c) < 32 and c not in "\r\n\t" for c in text):
        raise DomainError("SOURCE_FORMAT_UNSUPPORTED", "来源内容须为不超过 512 KiB 的可读 UTF-8 文本", 422)
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def remote_document(source):
    url = source.url
    if source.kind == "github_releases":
        path = urlsplit(url).path.strip("/").removesuffix(".git")
        url = "https://api.github.com/repos/" + path + "/releases"
    text, content_type = source_http.fetch(url)
    version = None
    if source.kind == "github_releases":
        try:
            releases = json.loads(text)
            if not isinstance(releases, list):
                raise ValueError("release list")
            release = next((r for r in releases if isinstance(r, dict) and not r.get("draft")), None)
            if release:
                version = str(release["tag_name"])[:100]
                text = "\n".join(
                    str(release.get(k) or "") for k in ("tag_name", "name", "published_at", "body")
                )
            else:
                text = "当前来源尚无公开发布记录。"
        except (ValueError, KeyError, TypeError):
            raise DomainError("SOURCE_FORMAT_UNSUPPORTED", "GitHub Release 数据格式无法核对", 422) from None
    elif content_type == "text/html":
        parser = ReadableHTML()
        parser.feed(text)
        text = "\n".join(parser.parts)
    if not text.strip():
        raise DomainError("SOURCE_FORMAT_UNSUPPORTED", "来源没有可读正文，保留上次快照", 422)
    return normalize(text), version


def store_snapshot(db, source, text, version, trace_id):
    lock_source(db, source)
    if not source.enabled or not source.authorized:
        raise DomainError("SOURCE_DISABLED", "来源已停用，未更新快照")
    text = normalize(text)
    if not text:
        raise DomainError("SOURCE_FORMAT_UNSUPPORTED", "版本说明不能为空", 422)
    fingerprint = digest({"text": text, "version": version})
    old = db.get(ProductSnapshot, source.current_snapshot_id) if source.current_snapshot_id else None
    result = {"changed": False, "baseline": not bool(old), "snapshot_id": old.id if old else None}
    if not old or old.sha256 != fingerprint:
        snapshot = ProductSnapshot(
            workspace_id=source.workspace_id,
            source_id=source.id,
            version=version,
            sha256=fingerprint,
            text=text,
        )
        db.add(snapshot)
        db.flush()
        source.current_snapshot_id = snapshot.id
        result["snapshot_id"] = snapshot.id
        if old:
            diff = "\n".join(
                difflib.unified_diff(
                    old.text.splitlines(),
                    text.splitlines(),
                    fromfile=old.version or "原快照",
                    tofile=version or "新快照",
                    n=3,
                )
            )
            event = ProductEvent(
                workspace_id=source.workspace_id,
                source_id=source.id,
                previous_snapshot_id=old.id,
                snapshot_id=snapshot.id,
                diff=diff[:60000] or "版本标识发生变化，正文未变。",
            )
            db.add(event)
            db.flush()
            result.update(changed=True, event_id=event.id)
            for asset in db.scalars(select(Asset).where(Asset.product_source_id == source.id)):
                asset.applicability_status, asset.verified = "needs_review", False
                asset.review_note = "产品来源有更新，请重新核对素材适用版本及使用权。"
                invalidate_asset(db, asset, source.recorded_by, "asset_version_changed")
    source.last_checked_at, source.last_error_code = now_iso(), None
    source.next_check_at = (
        datetime.now(timezone.utc) + timedelta(minutes=source.interval_minutes)
    ).isoformat()
    db.add(
        ProductCheck(
            workspace_id=source.workspace_id,
            source_id=source.id,
            status="completed",
            trace_id=trace_id,
            result=result,
        )
    )
    record(
        db,
        source.workspace_id,
        trace_id,
        "product.source",
        "ok",
        source="authorized_source",
        sha256=fingerprint,
    )
    db.flush()
    return result


def check_source(db, source, trace_id=None):
    trace_id = trace_id or uid()
    lock_source(db, source)
    if not source.enabled or not source.authorized:
        raise DomainError("SOURCE_DISABLED", "来源已停用，未访问外部地址")
    if source.kind == "uploaded_notes":
        raise DomainError("SOURCE_UPLOAD_REQUIRED", "此来源请主动上传版本说明", 422)
    now = datetime.now(timezone.utc)
    lease = (now + timedelta(minutes=2)).isoformat()
    revision = source.revision
    claimed = db.execute(
        update(ProductSource)
        .where(
            ProductSource.id == source.id,
            or_(ProductSource.lease_until.is_(None), ProductSource.lease_until < now.isoformat()),
        )
        .values(lease_until=lease)
    )
    db.commit()
    if claimed.rowcount != 1:
        raise DomainError("SOURCE_CHECK_IN_PROGRESS", "此来源正在检查，请稍后查看回执")
    try:
        text, version = remote_document(source)
        lock_source(db, source)
        if (
            source.revision != revision
            or source.lease_until != lease
            or not source.enabled
            or not source.authorized
        ):
            db.add(
                ProductCheck(
                    workspace_id=source.workspace_id,
                    source_id=source.id,
                    status="cancelled",
                    trace_id=trace_id,
                    result={"reason": "authorization_or_config_changed"},
                )
            )
            if source.lease_until == lease:
                source.lease_until = None
            db.commit()
            return {"cancelled": True}
        result = store_snapshot(db, source, text, version, trace_id)
        source.lease_until = None
        db.commit()
        return result
    except DomainError as error:
        db.rollback()
        lock_source(db, source)
        if source.lease_until == lease:
            source.lease_until = None
            source.last_checked_at, source.last_error_code = now_iso(), error.code
            source.next_check_at = (now + timedelta(minutes=source.interval_minutes)).isoformat()
        db.add(
            ProductCheck(
                workspace_id=source.workspace_id,
                source_id=source.id,
                status="failed",
                error_code=error.code,
                trace_id=trace_id,
                result={},
            )
        )
        record(db, source.workspace_id, trace_id, "product.source", "error", error_code=error.code)
        db.commit()
        raise


def poll_sources(db, now=None):
    now = now or datetime.now(timezone.utc)
    sources = db.scalars(
        select(ProductSource).where(
            ProductSource.enabled.is_(True),
            ProductSource.authorized.is_(True),
            ProductSource.kind != "uploaded_notes",
            or_(ProductSource.next_check_at.is_(None), ProductSource.next_check_at <= now.isoformat()),
        )
    ).all()
    for source in sources:
        try:
            check_source(db, source)
        except DomainError:
            db.rollback()
