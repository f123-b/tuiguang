import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, File, Form, Header, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from opentelemetry import propagate
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from PIL import Image, UnidentifiedImageError
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import schemas as s
from .auth import current_user, issue_token, password_hash, verify_password
from .config import COOKIE_SECURE, WEB_ORIGIN
from .db import get_db
from .domains import (
    analytics_summary,
    canonical,
    compliance_report,
    digest,
    file_path,
    verified_file,
    make_handoff,
    owned,
    parse_metric_rows,
    serialize,
    store_file,
    valid_publication_url,
)
from .errors import DomainError
from .editorial import ensure_plan, lock_creator, serialize_creator
from .editorial_api import router as editorial_router
from .graphics_api import router as graphics_router
from .evidence_api import router as evidence_router
from .video_edit_api import router as video_edit_router
from .learning_api import router as learning_router
from .settings_api import router as settings_router
from .analysis_api import router as analysis_router
from .model_diagnostics import router as model_diagnostics_router
from .video_edit import lock_video, checkpoint as video_checkpoint, current_output
from .evidence import checkpoint
from .graphics import lock_content
from .jobs import budget_used, enqueue
from .models import (
    Asset,
    Brand,
    Content,
    Creator,
    EditorialEntry,
    Event,
    Handoff,
    ImportBatch,
    LoginSession,
    Metric,
    Publication,
    RenderJob,
    Run,
    User,
    uid,
)
from .observability import record, release_manifest, tracer
from .video import PROVIDERS, probe, validate_ir

app = FastAPI(
    title="叙流 · AI 持续创作者",
    version=release_manifest()["application_version"],
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/docs",
    redoc_url=None,
)
app.include_router(editorial_router)
app.include_router(graphics_router)
app.include_router(evidence_router)
app.include_router(video_edit_router)
app.include_router(learning_router)
app.include_router(settings_router)
app.include_router(analysis_router)
app.include_router(model_diagnostics_router)
FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]


def error_response(code, message, status, request):
    return JSONResponse(
        {
            "error": {
                "code": code,
                "message": message,
                "trace_id": request.state.trace_id,
                "request_id": request.state.request_id,
            }
        },
        status_code=status,
    )


@app.middleware("http")
async def context_middleware(request, call_next):
    with tracer.start_as_current_span(
        "api.request", context=propagate.extract(dict(request.headers))
    ) as span:
        trace_id = format(span.get_span_context().trace_id, "032x")
        return await request_with_context(request, call_next, trace_id)


async def request_with_context(request, call_next, trace_id):
    request.state.trace_id, request.state.request_id = trace_id, uid()
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin != WEB_ORIGIN:
            return error_response("CSRF_ORIGIN_DENIED", "请求来源不受信任", 403, request)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return error_response("CSRF_ORIGIN_DENIED", "跨站请求被阻止", 403, request)
    try:
        response = await call_next(request)
    except Exception:
        # Do not expose SQL, paths, credentials or raw provider failures.
        response = error_response("INTERNAL_ERROR", "操作未完成，请保留诊断编号后重试", 500, request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Trace-ID"] = trace_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(DomainError)
async def domain_error(request, error):
    return error_response(error.code, error.message, error.status, request)


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    # Never echo rejected input values (e.g. passwords).
    fields = ", ".join(".".join(map(str, e["loc"][1:])) for e in error.errors())
    return error_response("VALIDATION_ERROR", "请检查字段：" + fields, 422, request)


@app.get("/health")
def health():
    return {"status": "ok", "version": release_manifest()["application_version"]}


def set_session(response, token):
    response.set_cookie(
        "creator_session",
        token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        max_age=43200,
        path="/",
    )


@app.post("/api/v1/auth/register", status_code=201)
def register(data: s.Register, response: Response, db: DB):
    user = User(email=data.email.lower(), password_hash=password_hash(data.password), name=data.name)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError("AUTH_INVALID", "无法创建账号，请检查信息或尝试登录", 409) from None
    set_session(response, issue_token(db, user))
    return serialize(user)


@app.post("/api/v1/auth/login")
def login(data: s.Credentials, response: Response, db: DB):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    # Same expensive verification on a missing account to reduce enumeration timing differences.
    dummy = "00" * 16 + ":" + "00" * 64
    valid = verify_password(data.password, user.password_hash if user else dummy)
    if not user or not valid:
        raise DomainError("AUTH_INVALID", "邮箱或密码不正确", 401)
    set_session(response, issue_token(db, user))
    return serialize(user)


@app.post("/api/v1/auth/logout")
def logout(request: Request, response: Response, db: DB, user: Actor):
    db.execute(delete(LoginSession).where(LoginSession.id == request.state.session_id))
    db.commit()
    response.delete_cookie("creator_session", path="/")
    return {"ok": True}


@app.get("/api/v1/auth/me")
def me(user: Actor):
    return serialize(user)


@app.get("/api/v1/brands")
def brands(db: DB, user: Actor):
    return [serialize(b) for b in db.scalars(select(Brand).where(Brand.workspace_id == user.workspace_id))]


@app.post("/api/v1/brands", status_code=201)
def create_brand(data: s.BrandInput, db: DB, user: Actor):
    if db.scalar(select(Brand).where(Brand.workspace_id == user.workspace_id)):
        raise DomainError("BRAND_LIMIT_REACHED", "首版每个工作区支持一个品牌，可编辑现有资料")
    brand = Brand(
        workspace_id=user.workspace_id,
        **data.model_dump(exclude={"facts"}),
        facts=[{"id": uid(), **f.model_dump(), "locked": True} for f in data.facts],
    )
    db.add(brand)
    db.commit()
    return serialize(brand)


@app.patch("/api/v1/brands/{brand_id}")
def edit_brand(brand_id: str, data: s.BrandInput, db: DB, user: Actor):
    brand = owned(db, Brand, brand_id, user.workspace_id)
    for key, value in data.model_dump(exclude={"facts"}).items():
        setattr(brand, key, value)
    brand.facts = [{"id": uid(), **f.model_dump(), "locked": True} for f in data.facts]
    brand.revision += 1
    creator_ids = select(Creator.id).where(Creator.brand_id == brand.id)
    for content in db.scalars(
        select(Content).where(
            Content.creator_id.in_(creator_ids), Content.status != "user_reported_published"
        )
    ):
        content.revision += 1
        content.approved_revision = None
        content.status = "awaiting_user_review"
    db.commit()
    return serialize(brand)


@app.get("/api/v1/assets")
def assets(db: DB, user: Actor):
    return [serialize(a) for a in db.scalars(select(Asset).where(Asset.workspace_id == user.workspace_id))]


@app.post("/api/v1/brands/{brand_id}/assets", status_code=201)
async def upload_asset(
    brand_id: str,
    db: DB,
    user: Actor,
    file: UploadFile = File(),
    source: str = Form(min_length=1, max_length=2000),
    license_note: str = Form(min_length=1, max_length=2000),
    verified: bool = Form(False),
):
    owned(db, Brand, brand_id, user.workspace_id)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".wav", ".mp3", ".m4a", ".ogg"):
        raise DomainError("ASSET_FORMAT_INVALID", "支持 PNG/JPG/WebP/MP4/MOV/WAV/MP3/M4A/OGG", 422)
    data = await file.read(50 * 1024 * 1024 + 1)
    if not data or len(data) > 50 * 1024 * 1024:
        raise DomainError("ASSET_SIZE_INVALID", "文件须小于 50 MB 且不能为空", 422)
    kind = (
        "video"
        if suffix in (".mp4", ".mov")
        else "audio"
        if suffix in (".wav", ".mp3", ".m4a", ".ogg")
        else "image"
    )
    if kind == "image":
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.width * image.height > 30_000_000:
                    raise ValueError("size")
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise DomainError("ASSET_FORMAT_INVALID", "图片损坏或尺寸过大", 422) from None
    sha = store_file(user.workspace_id, data, suffix)
    if kind in ("video", "audio"):
        metadata = probe(file_path(user.workspace_id, sha, suffix))
        if not any(stream["codec_type"] == kind for stream in metadata["streams"]):
            raise DomainError("ASSET_FORMAT_INVALID", "文件缺少所需的音频或视频流", 422)
    asset = Asset(
        workspace_id=user.workspace_id,
        brand_id=brand_id,
        name=Path(file.filename).name[:180],
        sha256=sha,
        suffix=suffix,
        source=source,
        license_note=license_note,
        verified=verified,
        kind=kind,
    )
    db.add(asset)
    db.commit()
    return serialize(asset)


@app.get("/api/v1/assets/{asset_id}/download")
def download_asset(asset_id: str, db: DB, user: Actor):
    asset = owned(db, Asset, asset_id, user.workspace_id)
    return FileResponse(verified_file(user.workspace_id, asset.sha256, asset.suffix), filename=asset.name)


@app.get("/api/v1/creators")
def creators(db: DB, user: Actor):
    return [
        serialize_creator(db, c)
        for c in db.scalars(select(Creator).where(Creator.workspace_id == user.workspace_id))
    ]


@app.post("/api/v1/creators", status_code=201)
def create_creator(data: s.CreatorInput, db: DB, user: Actor):
    owned(db, Brand, data.brand_id, user.workspace_id)
    if db.scalar(select(Creator).where(Creator.workspace_id == user.workspace_id)):
        raise DomainError("CREATOR_LIMIT_REACHED", "首版支持一个持续创作者，可编辑现有设置")
    from .production import options_snapshot
    from types import SimpleNamespace

    if data.render_options:
        options_snapshot(
            db,
            SimpleNamespace(brand_id=data.brand_id, workspace_id=user.workspace_id),
            data.render_options.model_dump(),
        )
    creator = Creator(workspace_id=user.workspace_id, **data.model_dump())
    db.add(creator)
    db.flush()
    ensure_plan(db, creator)
    db.commit()
    return serialize_creator(db, creator)


@app.get("/api/v1/creators/{creator_id}")
def get_creator(creator_id: str, db: DB, user: Actor):
    return serialize_creator(db, owned(db, Creator, creator_id, user.workspace_id))


@app.patch("/api/v1/creators/{creator_id}")
def edit_creator(creator_id: str, data: s.CreatorInput, db: DB, user: Actor):
    creator = owned(db, Creator, creator_id, user.workspace_id)
    owned(db, Brand, data.brand_id, user.workspace_id)
    lock_creator(db, creator)
    from .production import options_snapshot

    if data.render_options:
        options_snapshot(db, creator, data.render_options.model_dump())
    for key, value in data.model_dump().items():
        setattr(creator, key, value)
    ensure_plan(db, creator)
    db.commit()
    return serialize_creator(db, creator)


@app.post("/api/v1/creators/{creator_id}/pause")
def pause_creator(creator_id: str, db: DB, user: Actor, request: Request):
    creator = owned(db, Creator, creator_id, user.workspace_id)
    lock_creator(db, creator)
    creator.status = "paused_by_user"
    record(db, user.workspace_id, request.state.trace_id, "creator.pause", "ok")
    db.commit()
    return serialize_creator(db, creator)


@app.post("/api/v1/creators/{creator_id}/resume")
def resume_creator(creator_id: str, db: DB, user: Actor):
    from .models import BudgetEntry

    creator = owned(db, Creator, creator_id, user.workspace_id)
    lock_creator(db, creator)
    unresolved = db.scalar(
        select(BudgetEntry).where(BudgetEntry.creator_id == creator.id, BudgetEntry.status == "reserved")
    )
    if unresolved:
        raise DomainError("AGENT_PROVIDER_RESULT_UNKNOWN", "有未核对的模型费用，暂不能恢复")
    creator.status = "active"
    db.commit()
    ensure_plan(db, creator)
    db.commit()
    return serialize_creator(db, creator)


@app.post("/api/v1/creators/{creator_id}/run-today")
def run_today(
    creator_id: str,
    response: Response,
    request: Request,
    db: DB,
    user: Actor,
    idempotency_key: str = Header(min_length=1, max_length=160),
):
    creator = owned(db, Creator, creator_id, user.workspace_id)
    day = datetime.now(ZoneInfo(creator.timezone)).date().isoformat()
    run, created = enqueue(db, creator, day, idempotency_key, request.state.trace_id)
    response.status_code = 201 if created else 200
    return serialize(run)


@app.get("/api/v1/creator-runs")
def runs(db: DB, user: Actor):
    return [
        serialize(r)
        for r in db.scalars(
            select(Run)
            .where(Run.workspace_id == user.workspace_id)
            .order_by(Run.created_at.desc())
            .limit(100)
        )
    ]


@app.get("/api/v1/creator-runs/{run_id}/diagnostic")
def run_diagnostic(run_id: str, db: DB, user: Actor):
    run = owned(db, Run, run_id, user.workspace_id)
    events = db.scalars(
        select(Event)
        .where(Event.workspace_id == user.workspace_id, Event.run_id == run.id)
        .order_by(Event.created_at)
    ).all()
    receipts = [
        {
            "schema_version": "1.0",
            "event_time": e.created_at,
            "trace_id": e.trace_id,
            "request_id": None,
            "creator_run_id": run.id,
            "stage": e.stage,
            "status": e.status,
            "error_code": e.error_code,
            "content_id": e.context.get("content_id"),
            "video_project_id": e.context.get("video_project_id"),
            "shot_id": e.context.get("shot_id"),
            "render_job_id": e.context.get("render_job_id"),
            "provider": e.context.get("provider"),
            "release_id": run.release["release_id"],
            "retry_count": 0,
            "model_revision": run.release.get("model_revision"),
            "prompt_version": run.release["prompt_version"],
            "artifact_sha256": e.context.get("sha256"),
        }
        for e in events
    ]
    return {
        "run": serialize(run),
        "receipts": receipts,
        "observed": "已定位失败阶段" if run.error_code else "见实际运行事件",
        "hypothesis": None,
    }


@app.post("/api/v1/creator-runs/{run_id}/skip")
def skip_run(run_id: str, db: DB, user: Actor):
    run = owned(db, Run, run_id, user.workspace_id)
    changed = db.execute(
        update(Run)
        .where(Run.id == run.id, Run.status == "queued")
        .values(status="skipped", stage="user_skipped")
    )
    if changed.rowcount != 1:
        raise DomainError("RUN_NOT_SKIPPABLE", "只能跳过尚未开始的任务")
    if run.editorial_entry_id:
        db.get(EditorialEntry, run.editorial_entry_id).status = "skipped"
    db.commit()
    return serialize(run)


@app.get("/api/v1/content/packages")
def contents(db: DB, user: Actor):
    return [
        serialize(c)
        for c in db.scalars(
            select(Content)
            .where(Content.workspace_id == user.workspace_id)
            .order_by(Content.created_at.desc())
            .limit(200)
        )
    ]


@app.get("/api/v1/content/packages/{content_id}")
def get_content(content_id: str, db: DB, user: Actor):
    return serialize(owned(db, Content, content_id, user.workspace_id))


@app.patch("/api/v1/content/packages/{content_id}")
def edit_content(content_id: str, data: s.ContentPatch, db: DB, user: Actor):
    content = owned(db, Content, content_id, user.workspace_id)
    lock_content(db, content, data.expected_revision)
    if content.status == "user_reported_published":
        raise DomainError("CONTENT_ALREADY_REPORTED", "已登记内容保持历史快照，请先撤销登记再修改")
    checkpoint(db, content, user.id)
    for key, value in data.model_dump(exclude_none=True, exclude={"expected_revision", "reason_tag"}).items():
        setattr(content, key, value)
    content.revision += 1
    content.approved_revision = None
    content.graphics_render = None
    content.status = "awaiting_user_review"
    content.compliance = compliance_report(db, content)
    checkpoint(db, content, user.id, data.reason_tag)
    db.commit()
    return serialize(content)


@app.post("/api/v1/content/packages/{content_id}/approve")
def approve_content(content_id: str, data: s.Approve, db: DB, user: Actor):
    content = owned(db, Content, content_id, user.workspace_id)
    lock_content(db, content, data.expected_revision)
    if content.status == "user_reported_published":
        raise DomainError("CONTENT_ALREADY_REPORTED", "已登记内容保留历史审核状态")
    content.compliance = compliance_report(db, content)
    if content.compliance["status"] == "blocked":
        db.commit()
        raise DomainError("QA_CONTENT_BLOCKED", "预审有阻断项，请修改后重新检查")
    content.approved_revision = content.revision
    content.status = "approved_for_handoff"
    db.commit()
    return serialize(content)


@app.get("/api/v1/manual-publication/packages")
def handoffs(db: DB, user: Actor):
    return [
        serialize(p)
        for p in db.scalars(
            select(Handoff)
            .where(Handoff.workspace_id == user.workspace_id)
            .order_by(Handoff.created_at.desc())
        )
    ]


@app.post("/api/v1/manual-publication/packages", status_code=201)
def prepare_handoff(data: s.HandoffInput, db: DB, user: Actor, request: Request):
    content = owned(db, Content, data.content_id, user.workspace_id)
    lock_content(db, content, data.expected_revision)
    package = make_handoff(db, content)
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "handoff.prepare",
        "ok",
        content_id=content.id,
        sha256=package.sha256,
    )
    db.commit()
    return serialize(package)


@app.get("/api/v1/manual-publication/packages/{package_id}")
def get_handoff(package_id: str, db: DB, user: Actor):
    return serialize(owned(db, Handoff, package_id, user.workspace_id))


def current_package(db, package):
    content = db.get(Content, package.content_id)
    if package.content_revision != content.revision or content.approved_revision != content.revision:
        raise DomainError("HANDOFF_PACKAGE_STALE", "资料包对应旧版内容，请重新审核并准备")
    if (
        (content.graphics or content.video_attachment)
        and content.status != "user_reported_published"
        and compliance_report(db, content)["status"] == "blocked"
    ):
        raise DomainError("QA_CONTENT_BLOCKED", "图文依据或素材已变化，请重新复核后导出或登记")
    return content


@app.get("/api/v1/manual-publication/packages/{package_id}/download")
def download_handoff(package_id: str, db: DB, user: Actor):
    package = owned(db, Handoff, package_id, user.workspace_id)
    current_package(db, package)
    return FileResponse(
        verified_file(user.workspace_id, package.sha256, ".zip"),
        filename=f"manual-package-{package.id[:8]}.zip",
        media_type="application/zip",
    )


@app.get("/api/v1/manual-publication/records")
def publications(db: DB, user: Actor):
    return [
        serialize(p)
        for p in db.scalars(select(Publication).where(Publication.workspace_id == user.workspace_id))
    ]


@app.post("/api/v1/manual-publication/records", status_code=201)
def record_publication(data: s.PublicationInput, db: DB, user: Actor, request: Request):
    package = owned(db, Handoff, data.package_id, user.workspace_id)
    content = current_package(db, package)
    valid_publication_url(data.url, package.platform)
    if data.published_at > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise DomainError("HANDOFF_DATE_INVALID", "不能将未来时间登记为已发布", 422)
    existing = db.scalar(select(Publication).where(Publication.package_id == package.id))
    if existing:
        return serialize(existing)
    record_obj = Publication(
        workspace_id=user.workspace_id,
        package_id=package.id,
        source="user_reported",
        published_at=data.published_at.astimezone(timezone.utc).isoformat(),
        url=data.url,
        notes=data.notes,
        recorded_by=user.id,
    )
    db.add(record_obj)
    content.status = "user_reported_published"
    record(
        db,
        user.workspace_id,
        request.state.trace_id,
        "handoff.user_reported",
        "ok",
        content_id=content.id,
        source="user_reported",
    )
    db.commit()
    return serialize(record_obj)


@app.delete("/api/v1/manual-publication/records/{record_id}")
def revoke_publication(record_id: str, db: DB, user: Actor):
    publication = owned(db, Publication, record_id, user.workspace_id)
    package = db.get(Handoff, publication.package_id)
    db.get(Content, package.content_id).status = "awaiting_manual_publication"
    db.delete(publication)
    db.commit()
    return {"ok": True, "message": "已撤销本软件中的登记，第三方作品由用户自行管理"}


@app.get("/api/v1/analytics")
def analytics(db: DB, user: Actor):
    return analytics_summary(db, user.workspace_id)


@app.get("/api/v1/analytics/import/template")
def import_template(user: Actor):
    return Response(
        "content_id,platform,views,likes,saves,clicks,conversions,period_start,period_end,observed_at\n",
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=metrics-template.csv"},
    )


@app.post("/api/v1/analytics/import/columns")
async def metric_columns(user: Actor, file: UploadFile = File()):
    from .metrics_io import read_upload, FIELDS

    header, rows = await read_upload(file)
    return {"columns": header, "fields": FIELDS, "preview": rows[:3]}


@app.post("/api/v1/analytics/import/preview")
async def preview_import(
    db: DB,
    user: Actor,
    file: UploadFile = File(),
    data_source: str = Form(),
    column_mapping: str = Form(default="{}", max_length=8000),
):
    from .metrics_io import read_upload, map_columns

    header, rows = await read_upload(file)
    rows = map_columns(header, rows, column_mapping)
    parsed = parse_metric_rows(db, user.workspace_id, rows, data_source)
    fingerprint = digest({"rows": parsed, "data_source": data_source})
    batch = db.scalar(
        select(ImportBatch).where(
            ImportBatch.workspace_id == user.workspace_id, ImportBatch.fingerprint == fingerprint
        )
    )
    if batch is None:
        batch = ImportBatch(
            workspace_id=user.workspace_id, fingerprint=fingerprint, data_source=data_source, rows=parsed
        )
        db.add(batch)
        db.commit()
    return serialize(batch)


@app.post("/api/v1/analytics/import/commit")
def commit_import(data: s.ImportCommit, db: DB, user: Actor, request: Request):
    batch = owned(db, ImportBatch, data.preview_id, user.workspace_id)
    if not batch.committed:
        for row in batch.rows:
            fingerprint = digest({"row": row, "source": batch.data_source})
            if not db.scalar(
                select(Metric.id).where(
                    Metric.workspace_id == user.workspace_id, Metric.fingerprint == fingerprint
                )
            ):
                db.add(
                    Metric(
                        workspace_id=user.workspace_id,
                        batch_id=batch.id,
                        content_id=row["content_id"],
                        platform=row["platform"],
                        values={k: row[k] for k in ("views", "likes", "saves", "clicks", "conversions")},
                        period_start=row["period_start"],
                        period_end=row["period_end"],
                        observed_at=row["observed_at"],
                        data_source=batch.data_source,
                        fingerprint=fingerprint,
                        content_revision=row.get("content_revision"),
                    )
                )
        batch.committed = True
        record(db, user.workspace_id, request.state.trace_id, "metrics.import", "ok", count=len(batch.rows))
        db.commit()
    return {"id": batch.id, "committed": True, "rows": len(batch.rows)}


@app.get("/api/v1/videos/providers")
def providers(user: Actor):
    return PROVIDERS


@app.get("/api/v1/videos/projects")
def videos(db: DB, user: Actor):
    from .models import Video

    return [serialize(v) for v in db.scalars(select(Video).where(Video.workspace_id == user.workspace_id))]


@app.post("/api/v1/videos/projects", status_code=201)
def create_video(data: s.VideoInput, db: DB, user: Actor):
    from .models import Video

    owned(db, Brand, data.brand_id, user.workspace_id)
    ir = {"schema_version": "1.1", **data.model_dump()}
    validate_ir(db, user.workspace_id, ir)
    video = Video(workspace_id=user.workspace_id, brand_id=data.brand_id, name=data.name, ir=ir)
    db.add(video)
    db.flush()
    video_checkpoint(db, video, user.id)
    db.commit()
    return serialize(video)


@app.get("/api/v1/videos/projects/{video_id}")
def get_video(video_id: str, db: DB, user: Actor):
    from .models import Video

    return serialize(owned(db, Video, video_id, user.workspace_id))


@app.patch("/api/v1/videos/{video_id}/scenes/{shot_id}")
def edit_shot(video_id: str, shot_id: str, data: s.Shot, db: DB, user: Actor):
    from .models import Video

    video = owned(db, Video, video_id, user.workspace_id)
    lock_video(db, video)
    video_checkpoint(db, video, user.id)
    ir = {
        key: value for key, value in json.loads(canonical(video.ir)).items() if not key.startswith("source_")
    }
    shot = next((s for s in ir["shots"] if s["shot_id"] == shot_id), None)
    if not shot or data.shot_id != shot_id:
        raise DomainError("VID_SHOT_NOT_FOUND", "镜头不存在", 404)
    if shot["locked"]:
        raise DomainError("VID_SHOT_LOCKED", "镜头已锁定")
    ir["schema_version"] = "1.1"
    ir.setdefault("audio_tracks", [])
    ir.setdefault("subtitles", [])
    new = data.model_dump()
    new["shot_revision"] = shot["shot_revision"] + 1
    ir["shots"][ir["shots"].index(shot)] = new
    validate_ir(db, user.workspace_id, ir)
    video.ir, video.revision, video.status = ir, video.revision + 1, "draft"
    video_checkpoint(db, video, user.id)
    db.commit()
    return serialize(video)


@app.post("/api/v1/videos/{video_id}/render", status_code=201)
def render_video(video_id: str, db: DB, user: Actor, request: Request):
    from .models import Video

    video = owned(db, Video, video_id, user.workspace_id)
    lock_video(db, video)
    if video.ir.get("source_content_id"):
        from .production import source_context

        source_context(db, video)
    validate_ir(db, user.workspace_id, video.ir)
    existing = db.scalar(
        select(RenderJob)
        .where(
            RenderJob.video_id == video.id,
            RenderJob.revision == video.revision,
            RenderJob.status.in_(["queued", "running", "completed"]),
        )
        .order_by(RenderJob.created_at.desc())
    )
    if existing:
        if existing.status in ("queued", "running"):
            return serialize(existing)
        try:
            current_output(db, video)
            return serialize(existing)
        except DomainError as error:
            if error.code not in ("VID_OUTPUT_NOT_READY", "VID_OUTPUT_HASH_MISMATCH"):
                raise
    if video.ir.get("schema_version") == "1.0":
        raise DomainError("VID_IR_UPGRADE_REQUIRED", "旧工程请先保存为 1.1，再使用新版渲染器")

    job = RenderJob(
        workspace_id=user.workspace_id,
        video_id=video.id,
        revision=video.revision,
        ir=video.ir,
        trace_id=request.state.trace_id,
    )
    db.add(job)
    video.status = "queued"
    db.commit()
    return serialize(job)


@app.get("/api/v1/videos/{video_id}/render-jobs")
def render_jobs(video_id: str, db: DB, user: Actor):
    from .models import Video

    owned(db, Video, video_id, user.workspace_id)
    return [
        serialize(j)
        for j in db.scalars(
            select(RenderJob).where(RenderJob.video_id == video_id).order_by(RenderJob.created_at.desc())
        )
    ]


@app.get("/api/v1/videos/{video_id}/download")
def download_video(video_id: str, db: DB, user: Actor):
    from .models import Video

    video = owned(db, Video, video_id, user.workspace_id)
    return FileResponse(
        current_output(db, video),
        media_type="video/mp4",
        filename=f"video-{video.id[:8]}.mp4",
    )


@app.get("/api/v1/videos/{video_id}/project")
def export_video_project(video_id: str, db: DB, user: Actor):
    from .models import Video

    video = owned(db, Video, video_id, user.workspace_id)
    return Response(
        json.dumps(
            {"project_id": video.id, "revision": video.revision, **video.ir}, ensure_ascii=False, indent=2
        ),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="project-{video.id[:8]}.json"'},
    )


@app.get("/api/v1/dashboard")
def dashboard(db: DB, user: Actor):
    creator_list = creators(db, user)
    content_list = contents(db, user)
    return {
        "creators": creator_list,
        "contents": content_list[:6],
        "runs": runs(db, user)[:6],
        "counts": {
            "contents": len(content_list),
            "awaiting_review": sum(c["status"] == "awaiting_user_review" for c in content_list),
            "awaiting_manual": sum(c["status"] == "awaiting_manual_publication" for c in content_list),
            "user_reported": sum(c["status"] == "user_reported_published" for c in content_list),
        },
        "spent_cents": budget_used(db, user.workspace_id),
        "analytics": analytics_summary(db, user.workspace_id),
        "generation_mode": __import__("creator.model_config", fromlist=["public_config"]).public_config(
            db, user.workspace_id
        )["mode"],
    }


@app.get("/api/v1/ops/diagnostics")
def diagnostics(db: DB, user: Actor):
    if user.role not in ("owner", "admin"):
        raise DomainError("AUTH_FORBIDDEN", "仅管理员可查看诊断", 403)
    return [
        serialize(e)
        for e in db.scalars(
            select(Event)
            .where(Event.workspace_id == user.workspace_id)
            .order_by(Event.created_at.desc())
            .limit(200)
        )
    ]


@app.get("/api/v1/releases/current")
def release(user: Actor):
    return release_manifest()


@app.get("/api/v1/settings")
def settings(db: DB, user: Actor):

    from .model_config import public_config

    public = public_config(db, user.workspace_id)
    return {
        "generation_mode": public["mode"],
        "model_id": public["model_id"],
        "model_key_configured": public["key_configured"],
        "timezone": "Asia/Shanghai",
        "storage": "workspace_local_disk",
        "application_version": release_manifest()["application_version"],
    }
