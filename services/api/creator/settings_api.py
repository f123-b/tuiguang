import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Annotated, Literal

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import Field, SecretStr
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .models import QualityReport, QualityReview, CreationBrief, BriefPlan, NarrationJob
from .auth import current_user
from .db import get_db
from .domains import verified_file, owned, serialize
from .errors import DomainError
from .model_config import cipher, config, public_config, validate_base_url
from .models import (
    Asset,
    Brand,
    BrandChange,
    BudgetEntry,
    Content,
    ContentRevision,
    Creator,
    EditorialEntry,
    Feedback,
    Handoff,
    ImportBatch,
    LearningReport,
    Metric,
    ModelConfig,
    ModelCheck,
    ProductSource,
    ProductSnapshot,
    ProductEvent,
    ProductCheck,
    Notification,
    Preferences,
    Publication,
    Reminder,
    RenderJob,
    Run,
    Strategy,
    User,
    Video,
    VideoRevision,
    now_iso,
)
from .notifications import sync
from .observability import record
from .schemas import DTO, CreatorInput
from .models import HandoffOutcome

router = APIRouter(prefix="/api/v1")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


def admin(user):
    if user.role not in ("owner", "admin"):
        raise DomainError("AUTH_FORBIDDEN", "仅工作区管理员可修改此设置", 403)


class ModelInput(DTO):
    expected_revision: int = Field(ge=0)
    mode: Literal["template", "openai"]
    model_id: str = Field(default="", max_length=120)
    model_revision: str | None = Field(default=None, max_length=120)
    base_url: str = Field(default="https://api.openai.com/v1", max_length=1000)
    input_price: int = Field(ge=0, le=100000000)
    output_price: int = Field(ge=0, le=100000000)
    max_tokens: int = Field(default=1800, ge=128, le=8000)
    price_source: str = Field(min_length=1, max_length=2000)
    endpoint_confirmed: bool = False
    json_mode: bool = True
    token_parameter: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    api_key: SecretStr | None = Field(default=None, max_length=4000)
    clear_key: bool = False


class PreferenceInput(DTO):
    notification_mode: Literal["instant", "daily", "off"]
    timezone: str = "Asia/Shanghai"
    digest_hour: int = Field(default=9, ge=0, le=23)


class ReminderInput(DTO):
    package_id: str = Field(min_length=1, max_length=120)
    due_at: datetime
    confirmed: Literal[True]


class OutcomeInput(DTO):
    outcome: Literal["pending", "postponed", "platform_rejected", "abandoned"]
    notes: str = Field(default="", max_length=2000)
    confirmed: Literal[True]


@router.get("/manual-publication/outcomes")
def outcomes(db: DB, user: Actor):
    return [
        serialize(o)
        for o in db.scalars(select(HandoffOutcome).where(HandoffOutcome.workspace_id == user.workspace_id))
    ]


@router.post("/manual-publication/packages/{package_id}/outcome")
def set_outcome(package_id: str, data: OutcomeInput, db: DB, user: Actor, request: Request):
    package = owned(db, Handoff, package_id, user.workspace_id)
    content = owned(db, Content, package.content_id, user.workspace_id)
    if content.status == "user_reported_published":
        raise DomainError("CONTENT_ALREADY_REPORTED", "已登记发布的作品须先撤销发布登记")
    db.execute(update(User).where(User.workspace_id == user.workspace_id).values(role=User.role))
    result = db.scalar(select(HandoffOutcome).where(HandoffOutcome.package_id == package.id))
    if not result:
        result = HandoffOutcome(workspace_id=user.workspace_id, package_id=package.id, recorded_by=user.id)
        db.add(result)
    result.outcome, result.notes = data.outcome, data.notes
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "handoff.outcome",
        "ok",
        content_id=content.id,
        source="user_reported",
    )
    db.commit()
    return serialize(result)


@router.get("/settings/models")
def model_settings(db: DB, user: Actor):
    return public_config(db, user.workspace_id)


@router.put("/settings/models")
def save_model(data: ModelInput, db: DB, user: Actor, request: Request):
    admin(user)
    db.execute(update(User).where(User.workspace_id == user.workspace_id).values(role=User.role))
    current = config(db, user.workspace_id)
    if current:
        db.refresh(current)
    if (current.revision if current else 0) != data.expected_revision:
        raise DomainError("MODEL_REVISION_CONFLICT", "模型设置已变化，请刷新")
    same_endpoint = bool(current and current.base_url == data.base_url.rstrip("/"))
    approved = data.endpoint_confirmed or bool(same_endpoint and current.endpoint_approved)
    base = validate_base_url(data.base_url, approved)
    if current and not same_endpoint and current.encrypted_key and not data.api_key and data.mode == "openai":
        raise DomainError("MODEL_CONFIG_INVALID", "更换网关须重新输入密钥，不能把原密钥发送给新地址", 422)
    encrypted = current.encrypted_key if current else None
    if data.clear_key:
        encrypted = None
    if data.api_key is not None:
        if (
            not data.api_key.get_secret_value().strip()
            or data.api_key.get_secret_value() != data.api_key.get_secret_value().strip()
        ):
            raise DomainError("MODEL_CONFIG_INVALID", "密钥不能为空或含首尾空白", 422)
        if data.clear_key:
            raise DomainError("MODEL_CONFIG_INVALID", "不能同时清除和设置密钥", 422)
        encrypted = cipher().encrypt(data.api_key.get_secret_value().encode()).decode()
    if data.mode == "openai":
        if not data.model_id or not encrypted:
            raise DomainError("AGENT_MODEL_UNCONFIGURED", "启用模型需要模型名称与本工作区密钥", 422)
        try:
            cipher().decrypt(encrypted.encode())
        except InvalidToken:
            raise DomainError("MODEL_ENCRYPTION_UNAVAILABLE", "密钥无法解密，配置未保存", 503) from None
    if not current:
        current = ModelConfig(workspace_id=user.workspace_id, revision=0)
        db.add(current)
    for key, value in data.model_dump(
        exclude={"expected_revision", "api_key", "clear_key", "endpoint_confirmed"}
    ).items():
        setattr(current, key, value)
    current.base_url, current.encrypted_key = base, encrypted
    current.endpoint_approved = approved
    current.revision += 1
    record(db, user.workspace_id, request.state.trace_id, "settings.model", "ok", revision=current.revision)
    db.commit()
    return public_config(db, user.workspace_id)


@router.get("/settings/preferences")
def preferences(db: DB, user: Actor):
    pref = db.scalar(select(Preferences).where(Preferences.workspace_id == user.workspace_id))
    return (
        serialize(pref)
        if pref
        else {"notification_mode": "instant", "timezone": "Asia/Shanghai", "digest_hour": 9}
    )


@router.put("/settings/preferences")
def save_preferences(data: PreferenceInput, db: DB, user: Actor):
    try:
        CreatorInput.valid_zone(data.timezone)
    except ValueError:
        raise DomainError("VALIDATION_ERROR", "时区无效", 422) from None
    db.execute(update(User).where(User.workspace_id == user.workspace_id).values(role=User.role))
    pref = db.scalar(select(Preferences).where(Preferences.workspace_id == user.workspace_id))
    if not pref:
        pref = Preferences(workspace_id=user.workspace_id)
        db.add(pref)
    for key, value in data.model_dump().items():
        setattr(pref, key, value)
    db.commit()
    return serialize(pref)


@router.get("/notifications")
def notifications(db: DB, user: Actor):
    return [
        serialize(n)
        for n in db.scalars(
            select(Notification)
            .where(Notification.workspace_id == user.workspace_id)
            .order_by(Notification.created_at.desc())
            .limit(200)
        )
    ]


@router.post("/notifications/sync")
def sync_own(db: DB, user: Actor):
    sync(db, user.workspace_id)
    db.commit()
    return {"ok": True}


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: str, db: DB, user: Actor):
    note = owned(db, Notification, notification_id, user.workspace_id)
    note.read_at = note.read_at or now_iso()
    db.commit()
    return serialize(note)


@router.post("/notifications/read-all")
def read_all(db: DB, user: Actor):
    db.execute(
        update(Notification)
        .where(Notification.workspace_id == user.workspace_id, Notification.read_at.is_(None))
        .values(read_at=now_iso())
    )
    db.commit()
    return {"ok": True}


@router.post("/notifications/reminders", status_code=201)
def create_reminder(data: ReminderInput, db: DB, user: Actor):
    owned(db, Handoff, data.package_id, user.workspace_id)
    if not data.due_at.tzinfo:
        raise DomainError("REMINDER_DATE_INVALID", "提醒时间必须包含时区", 422)
    due = data.due_at.astimezone(timezone.utc).isoformat()
    db.execute(update(User).where(User.workspace_id == user.workspace_id).values(role=User.role))
    reminder = db.scalar(
        select(Reminder).where(Reminder.package_id == data.package_id, Reminder.due_at == due)
    )
    if not reminder:
        reminder = Reminder(workspace_id=user.workspace_id, package_id=data.package_id, due_at=due)
        db.add(reminder)
    db.commit()
    return serialize(reminder)


@router.get("/notifications/reminders")
def reminders(db: DB, user: Actor):
    return [
        serialize(r)
        for r in db.scalars(
            select(Reminder)
            .where(Reminder.workspace_id == user.workspace_id)
            .order_by(Reminder.due_at.desc())
        )
    ]


@router.post("/notifications/reminders/{reminder_id}/dismiss")
def dismiss_reminder(reminder_id: str, db: DB, user: Actor):
    reminder = owned(db, Reminder, reminder_id, user.workspace_id)
    reminder.state = "dismissed"
    db.commit()
    return serialize(reminder)


@router.get("/settings/billing")
def billing(db: DB, user: Actor):
    ledgers = [
        serialize(b)
        for b in db.scalars(
            select(BudgetEntry)
            .where(BudgetEntry.workspace_id == user.workspace_id)
            .order_by(BudgetEntry.created_at.desc())
        )
    ]
    return {
        "currency": "CNY",
        "unit": "cents",
        "subscription": "not_connected_no_payments",
        "actual_cents": sum(b["actual_cents"] or 0 for b in ledgers),
        "unsettled_reserved_cents": sum(b["reserved_cents"] for b in ledgers if b["actual_cents"] is None),
        "ledgers": ledgers,
    }


@router.get("/settings/export")
def export_workspace(db: DB, user: Actor, include_files: bool = False):
    admin(user)
    models = (
        Brand,
        BrandChange,
        Creator,
        EditorialEntry,
        Run,
        Content,
        ContentRevision,
        Asset,
        Video,
        VideoRevision,
        RenderJob,
        Handoff,
        Publication,
        ImportBatch,
        Metric,
        Feedback,
        LearningReport,
        Strategy,
        BudgetEntry,
        Preferences,
        Notification,
        Reminder,
        HandoffOutcome,
        ModelCheck,
        ProductSource,
        ProductSnapshot,
        ProductEvent,
        ProductCheck,
        QualityReport,
        QualityReview,
        CreationBrief,
        BriefPlan,
        NarrationJob,
    )
    document = {
        cls.__tablename__: [
            serialize(row) for row in db.scalars(select(cls).where(cls.workspace_id == user.workspace_id))
        ]
        for cls in models
    }
    document["model_settings"] = public_config(db, user.workspace_id)
    document["export"] = {
        "created_at": now_iso(),
        "private_archive": True,
        "not_a_publication_package": True,
        "includes_files": include_files,
        "secrets_included": False,
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("workspace.json", json.dumps(document, ensure_ascii=False, indent=2))
        if include_files:
            total = 0
            seen = set()
            for asset in db.scalars(select(Asset).where(Asset.workspace_id == user.workspace_id)):
                path = verified_file(user.workspace_id, asset.sha256, asset.suffix)
                if path.name in seen:
                    continue
                total += path.stat().st_size
                if total > 200 * 1024 * 1024:
                    raise DomainError(
                        "EXPORT_SIZE_LIMIT", "素材超过 200 MB，请选择仅导出记录并单独下载媒体", 422
                    )
                seen.add(path.name)
                archive.write(path, "assets/" + path.name)
    return Response(
        buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="private-workspace.zip"'},
    )


@router.get("/ops/maintenance")
def maintenance(db: DB, user: Actor):
    import shutil
    from sqlalchemy import inspect, text
    from .config import DATA_DIR
    from .observability import release_manifest
    from .video import PROVIDERS

    admin(user)
    actual = (
        db.scalar(text("select version_num from alembic_version"))
        if inspect(db.get_bind()).has_table("alembic_version")
        else None
    )
    usage = shutil.disk_usage(DATA_DIR)
    manifest = release_manifest()
    return {
        "database_migration_actual": actual,
        "database_migration_expected": manifest["database_migration"],
        "disk_free_bytes": usage.free,
        "disk_total_bytes": usage.total,
        "providers": PROVIDERS,
        "backup_restore": "requires_operator_verification",
        "production_monitoring": "not_deployed",
        "license_inventory_revision": manifest["license_inventory_revision"],
        "application_version": manifest["application_version"],
    }
