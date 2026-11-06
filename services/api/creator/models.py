import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def uid():
    return uuid.uuid4().hex


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    workspace_id: Mapped[str] = mapped_column(String(32), index=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="owner")


class LoginSession(Base):
    __tablename__ = "login_sessions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[str] = mapped_column(String(40))


class TenantRecord:
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class Brand(TenantRecord, Base):
    __tablename__ = "brands"
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    audience: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str] = mapped_column(Text, default="")
    facts: Mapped[list] = mapped_column(JSON, default=list)
    revision: Mapped[int] = mapped_column(Integer, default=1)


class Creator(TenantRecord, Base):
    __tablename__ = "creator_profiles"
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"))
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), default="active")
    timezone: Mapped[str] = mapped_column(String(80), default="Asia/Shanghai")
    hour: Mapped[int] = mapped_column(Integer, default=9)
    weekdays: Mapped[list] = mapped_column(JSON, default=lambda: list(range(7)))
    style: Mapped[str] = mapped_column(Text, default="简洁、可信、不夸张")
    platform: Mapped[str] = mapped_column(String(30), default="xiaohongshu")
    daily_budget_cents: Mapped[int] = mapped_column(Integer, default=500)
    monthly_budget_cents: Mapped[int] = mapped_column(Integer, default=10000)
    model_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (CheckConstraint("daily_budget_cents >= 0 AND monthly_budget_cents >= 0"),)


class EditorialEntry(TenantRecord, Base):
    __tablename__ = "editorial_entries"
    creator_id: Mapped[str] = mapped_column(ForeignKey("creator_profiles.id"))
    date: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(180))
    angle: Mapped[str] = mapped_column(String(40))
    fact_refs: Mapped[list] = mapped_column(JSON, default=list)
    brand_revision: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(30), default="rule_based_plan")
    rationale: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="approved")
    __table_args__ = (UniqueConstraint("creator_id", "date"),)


class Run(TenantRecord, Base):
    __tablename__ = "creator_runs"
    creator_id: Mapped[str] = mapped_column(ForeignKey("creator_profiles.id"))
    operational_date: Mapped[str] = mapped_column(String(10))
    slot: Mapped[str] = mapped_column(String(30), default="daily")
    idempotency_key: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(30), default="queued")
    stage: Mapped[str] = mapped_column(String(60), default="scheduled")
    trace_id: Mapped[str] = mapped_column(String(32), default=uid)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    release: Mapped[dict] = mapped_column(JSON)
    lease_until: Mapped[str | None] = mapped_column(String(40), nullable=True)
    editorial_entry_id: Mapped[str | None] = mapped_column(
        ForeignKey("editorial_entries.id"), nullable=True, unique=True
    )
    input_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    __table_args__ = (
        UniqueConstraint("creator_id", "operational_date", "slot"),
        UniqueConstraint("workspace_id", "idempotency_key"),
    )


class Content(TenantRecord, Base):
    __tablename__ = "content_packages"
    creator_id: Mapped[str] = mapped_column(ForeignKey("creator_profiles.id"))
    run_id: Mapped[str] = mapped_column(ForeignKey("creator_runs.id"), unique=True)
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(50), default="awaiting_user_review")
    generation_source: Mapped[str] = mapped_column(String(30))
    fact_refs: Mapped[list] = mapped_column(JSON, default=list)
    compliance: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    approved_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    graphics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    graphics_render: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    variants: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    video_attachment: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ContentRevision(TenantRecord, Base):
    __tablename__ = "content_revisions"
    content_id: Mapped[str] = mapped_column(ForeignKey("content_packages.id"))
    revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    editor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    reason_tag: Mapped[str] = mapped_column(String(40), default="edit")
    __table_args__ = (UniqueConstraint("content_id", "revision"),)


class BrandChange(TenantRecord, Base):
    __tablename__ = "brand_changes"
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"))
    claim: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    product_version: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="proposed")
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Asset(TenantRecord, Base):
    __tablename__ = "brand_assets"
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"))
    name: Mapped[str] = mapped_column(String(180))
    sha256: Mapped[str] = mapped_column(String(64))
    suffix: Mapped[str] = mapped_column(String(10))
    source: Mapped[str] = mapped_column(Text)
    license_note: Mapped[str] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    kind: Mapped[str] = mapped_column(String(30), default="image")
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Video(TenantRecord, Base):
    __tablename__ = "video_projects"
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"))
    name: Mapped[str] = mapped_column(String(180))
    ir: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    output_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rendered_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RenderJob(TenantRecord, Base):
    __tablename__ = "render_jobs"
    video_id: Mapped[str] = mapped_column(ForeignKey("video_projects.id"))
    revision: Mapped[int] = mapped_column(Integer)
    ir: Mapped[dict] = mapped_column(JSON)
    trace_id: Mapped[str] = mapped_column(String(32), default=uid)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    receipt: Mapped[dict] = mapped_column(JSON, default=dict)
    lease_until: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Handoff(TenantRecord, Base):
    __tablename__ = "manual_publish_packages"
    content_id: Mapped[str] = mapped_column(ForeignKey("content_packages.id"))
    content_revision: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    platform: Mapped[str] = mapped_column(String(30))
    snapshot: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("content_id", "content_revision"),)


class Publication(TenantRecord, Base):
    __tablename__ = "manual_publish_records"
    package_id: Mapped[str] = mapped_column(ForeignKey("manual_publish_packages.id"), unique=True)
    source: Mapped[str] = mapped_column(String(30), default="user_reported")
    published_at: Mapped[str] = mapped_column(String(40))
    url: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class ImportBatch(TenantRecord, Base):
    __tablename__ = "metric_import_batches"
    fingerprint: Mapped[str] = mapped_column(String(64))
    data_source: Mapped[str] = mapped_column(String(180))
    rows: Mapped[list] = mapped_column(JSON)
    committed: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("workspace_id", "fingerprint"),)


class Metric(TenantRecord, Base):
    __tablename__ = "metric_snapshots"
    batch_id: Mapped[str] = mapped_column(ForeignKey("metric_import_batches.id"))
    content_id: Mapped[str] = mapped_column(ForeignKey("content_packages.id"))
    platform: Mapped[str] = mapped_column(String(30))
    values: Mapped[dict] = mapped_column(JSON)
    period_start: Mapped[str] = mapped_column(String(10))
    period_end: Mapped[str] = mapped_column(String(10))
    observed_at: Mapped[str] = mapped_column(String(40))
    data_source: Mapped[str] = mapped_column(String(180))
    fingerprint: Mapped[str] = mapped_column(String(64))
    __table_args__ = (UniqueConstraint("workspace_id", "fingerprint"),)


class Event(TenantRecord, Base):
    __tablename__ = "job_events"
    trace_id: Mapped[str] = mapped_column(String(32), index=True)
    run_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stage: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30))
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)


class BudgetEntry(TenantRecord, Base):
    __tablename__ = "budget_ledgers"
    creator_id: Mapped[str] = mapped_column(ForeignKey("creator_profiles.id"))
    run_id: Mapped[str] = mapped_column(ForeignKey("creator_runs.id"), unique=True)
    operational_date: Mapped[str] = mapped_column(String(10))
    billing_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    reserved_cents: Mapped[int] = mapped_column(Integer)
    actual_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="reserved")


class VideoRevision(TenantRecord, Base):
    __tablename__ = "video_revisions"
    video_id: Mapped[str] = mapped_column(ForeignKey("video_projects.id"))
    revision: Mapped[int] = mapped_column(Integer)
    document: Mapped[dict] = mapped_column(JSON)
    editor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (UniqueConstraint("video_id", "revision"),)
