"""Durable local image-to-video jobs; generated clips require explicit source review."""

from datetime import datetime, timedelta, timezone
import io
import math
import os
from pathlib import Path
import time
from typing import Literal

from filelock import FileLock, Timeout
from PIL import Image
from pydantic import Field, model_validator
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError

from . import wan_comfy
from .config import DATA_DIR
from .domains import digest, owned, serialize, store_file, verified_file
from .errors import DomainError
from .models import Asset, Brand, VideoGenerationJob
from .observability import record
from .schemas import DTO, Short
from .video import ffmpeg, probe


class GenerationInput(DTO):
    brand_id: Short
    reference_asset_id: Short
    prompt: str = Field(min_length=10, max_length=1600)
    style: Literal["realistic", "anime"] = "realistic"
    seed: int = Field(default=37, ge=0, le=4294967295)
    width: int = Field(default=1280, ge=256, le=1280)
    height: int = Field(default=704, ge=256, le=1280)
    frames: Literal[49, 73, 97, 121] = 121
    usage_confirmed: Literal[True]

    @model_validator(mode="after")
    def dimensions(self):
        if self.width % 32 or self.height % 32 or self.width * self.height > 901120:
            raise ValueError("尺寸须为32的倍数，本地生成最多901120像素")
        return self


def reference(db, job_or_data, workspace):
    asset = owned(db, Asset, job_or_data.reference_asset_id, workspace)
    db.refresh(asset)
    if (
        asset.brand_id != job_or_data.brand_id
        or not asset.verified
        or asset.kind != "image"
        or asset.applicability_status != "current"
    ):
        raise DomainError("GEN_REFERENCE_INVALID", "请选择当前品牌已核实授权且有效的角色参考图", 422)
    path = verified_file(workspace, asset.sha256, asset.suffix)
    return asset, path


def enqueue(db, data, user, key, trace):
    owned(db, Brand, data.brand_id, user.workspace_id)
    request_hash = digest(data.model_dump())
    old = db.scalar(
        select(VideoGenerationJob).where(
            VideoGenerationJob.workspace_id == user.workspace_id, VideoGenerationJob.idempotency_key == key
        )
    )
    if old:
        if old.request_hash != request_hash:
            raise DomainError("GEN_KEY_CONFLICT", "同一生成请求已用于不同内容，请使用新请求", 409)
        return old
    asset, path = reference(db, data, user.workspace_id)
    count = db.scalar(
        select(func.count())
        .select_from(VideoGenerationJob)
        .where(VideoGenerationJob.status.in_(["queued", "submitting", "running", "unknown"]))
    )
    if count >= 12:
        raise DomainError("GEN_QUEUE_FULL", "本机生成队列已满，请等待已有镜头完成", 409)
    model = wan_comfy.snapshot()
    job = VideoGenerationJob(
        workspace_id=user.workspace_id,
        brand_id=data.brand_id,
        reference_asset_id=asset.id,
        requested_by=user.id,
        idempotency_key=key,
        request_hash=request_hash,
        document=data.model_dump(),
        source={"reference_sha256": asset.sha256, "model": model},
        trace_id=trace,
    )
    db.add(job)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        old = db.scalar(
            select(VideoGenerationJob).where(
                VideoGenerationJob.workspace_id == user.workspace_id,
                VideoGenerationJob.idempotency_key == key,
            )
        )
        if not old or old.request_hash != request_hash:
            raise DomainError("GEN_KEY_CONFLICT", "并发生成请求内容不一致，请刷新", 409) from None
        return old
    record(
        db,
        user.workspace_id,
        trace,
        "generation.enqueue",
        "ok",
        generation_job_id=job.id,
        provider="comfy_wan",
        asset_id=asset.id,
    )
    return job


def public_job(db, job):
    result = serialize(job)
    result.pop("source", None)
    if job.output_asset_id:
        asset = owned(db, Asset, job.output_asset_id, job.workspace_id)
        result["output_asset"] = serialize(asset)
    return result


def _source_current(db, job, check_model=False):
    asset, path = reference(db, job, job.workspace_id)
    if asset.sha256 != job.source["reference_sha256"]:
        raise DomainError("GEN_SOURCE_CHANGED", "角色参考图已变化，请重新检查后提交新任务", 422)
    if check_model and wan_comfy.snapshot() != job.source["model"]:
        raise DomainError("GEN_MODEL_CHANGED", "模型或工作流版本已变化，没有提交新生成", 422)
    return path


def _run(db, job):
    path = _source_current(db, job, check_model=not job.provider_request_id)
    client = wan_comfy.Client()
    directory = DATA_DIR / job.workspace_id / "generation-tmp"
    directory.mkdir(exist_ok=True, parents=True)
    raw, output = directory / (job.id + ".webm"), directory / (job.id + ".mp4")
    try:
        if not job.provider_request_id:
            if job.status in ("submitting", "unknown"):
                raise DomainError(
                    "GEN_SUBMISSION_UNKNOWN", "提交回执未知，不会自动重复生成；请检查本地任务队列", 409
                )
            with Image.open(path) as image:
                image = image.convert("RGB")
                image.thumbnail((1536, 1536))
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
            image_name = client.upload(job.id, buffer.getvalue())
            graph = wan_comfy.workflow(job.document, image_name, job.id)
            job.receipt = {
                "workflow_sha256": digest(graph),
                "normalized_reference_sha256": digest(buffer.getvalue()),
                "model": job.source["model"],
                "seed": job.document["seed"],
                "device_metrics_before": client.metrics(),
            }
            job.status, job.stage = "submitting", "generation.submitting"
            db.commit()  # Durable intent precedes the only submission attempt.
            job.provider_request_id = client.submit(graph, job.id)
            job.status, job.stage = "running", "generation.sampling"
            db.commit()
        started = time.monotonic()
        while True:
            history = client.history(job.provider_request_id)
            if history and history.get("status", {}).get("status_str") == "error":
                raise DomainError(
                    "GEN_INFERENCE_FAILED", "本地模型推理失败；没有用静态图替代，请检查显存与服务日志", 422
                )
            if history and history.get("status", {}).get("completed"):
                break
            if time.monotonic() - started > 3600:
                raise DomainError(
                    "GEN_STATUS_UNKNOWN", "本地生成超过一小时，保留回执等待检查，不重复提交", 409
                )
            job.lease_until = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
            db.commit()
            time.sleep(3)
        items = history.get("outputs", {}).get("save", {}).get("images", [])
        if len(items) != 1:
            raise DomainError("GEN_OUTPUT_INVALID", "本地服务没有返回唯一生成片段", 422)
        job.stage = "generation.encoding"
        db.commit()
        client.download(items[0], raw, job.id)
        ffmpeg(
            [
                "-i",
                str(raw),
                "-map_metadata",
                "-1",
                "-an",
                "-c:v",
                "libx264",
                "-crf",
                "18",
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output),
            ]
        )
        media = probe(output)
        video = next(s for s in media["streams"] if s["codec_type"] == "video")
        if (
            (video["width"], video["height"]) != (job.document["width"], job.document["height"])
            or int(video.get("nb_frames", 0)) != job.document["frames"]
            or not math.isfinite(float(media["format"]["duration"]))
        ):
            raise DomainError("GEN_OUTPUT_INVALID", "生成片段的帧数或尺寸与请求不一致", 422)
        _source_current(db, job)
        sha = store_file(job.workspace_id, output.read_bytes(), ".mp4")
        asset = Asset(
            workspace_id=job.workspace_id,
            brand_id=job.brand_id,
            name="AI生成镜头-" + job.id[:8] + ".mp4",
            sha256=sha,
            suffix=".mp4",
            kind="video",
            verified=False,
            source="AI生成 / Wan2.2 TI2V-5B / job " + job.id + " / seed " + str(job.document["seed"]),
            license_note="本地模型生成，保留参考图与模型来源；待用户核实人物、动作、内容与使用权，不是商业许可认证。",
        )
        db.add(asset)
        db.flush()
        job.output_asset_id = asset.id
        job.receipt = {
            **job.receipt,
            "provider_request_id": job.provider_request_id,
            "output_sha256": sha,
            "width": video["width"],
            "height": video["height"],
            "frames": int(video["nb_frames"]),
            "fps": video["r_frame_rate"],
            "duration_sec": float(media["format"]["duration"]),
            "technical_qa": "probe_passed",
            "art_review": "requires_user",
            "silent": True,
            "device_metrics_after": client.metrics(),
            "provider_timeline": [
                {"stage": name, "timestamp": details.get("timestamp")}
                for name, details in history.get("status", {}).get("messages", [])
                if name in ("execution_start", "execution_success")
            ],
        }
        job.status, job.stage = "completed", "generation.awaiting_review"
        job.error_code = job.error_message = None
        record(
            db,
            job.workspace_id,
            job.trace_id,
            "generation.complete",
            "ok",
            generation_job_id=job.id,
            provider_request_id=job.provider_request_id,
            asset_id=asset.id,
            sha256=sha,
        )
        db.commit()
    finally:
        if job.provider_request_id:
            client.free_models()
        client.close()
        raw.unlink(missing_ok=True)
        output.unlink(missing_ok=True)


def process_generation_jobs(db):
    now = datetime.now(timezone.utc)
    expired = or_(VideoGenerationJob.lease_until.is_(None), VideoGenerationJob.lease_until < now.isoformat())
    eligible = VideoGenerationJob.status.in_(["queued", "running", "submitting"]) & expired
    jobs = db.scalars(
        select(VideoGenerationJob).where(eligible).order_by(VideoGenerationJob.created_at)
    ).all()
    for job in jobs:
        model_dir = os.getenv("QWEN_TTS_MODEL_DIR")
        lock_path = Path(model_dir) / ".inference.lock" if model_dir else DATA_DIR / "local-gpu.lock"
        try:
            with FileLock(str(lock_path), timeout=0):
                claim = db.execute(
                    update(VideoGenerationJob)
                    .where(VideoGenerationJob.id == job.id, eligible)
                    .values(lease_until=(now + timedelta(minutes=30)).isoformat())
                )
                db.commit()
                if claim.rowcount != 1:
                    continue
                try:
                    _run(db, job)
                except DomainError as exc:
                    db.rollback()
                    db.refresh(job)
                    job.status = (
                        "unknown"
                        if exc.code
                        in ("GEN_SUBMISSION_UNKNOWN", "GEN_STATUS_UNKNOWN", "GEN_OUTPUT_UNAVAILABLE")
                        else "failed"
                    )
                    job.error_code, job.error_message = exc.code, exc.message
                    job.stage = "generation." + job.status
                    record(
                        db,
                        job.workspace_id,
                        job.trace_id,
                        "generation.error",
                        "error",
                        generation_job_id=job.id,
                        error_code=exc.code,
                    )
                    db.commit()
                except Exception:
                    db.rollback()
                    db.refresh(job)
                    # An unexpected failure after durable submission intent may have side effects.
                    job.status = "unknown" if job.status in ("submitting", "running") else "failed"
                    interrupted = DomainError(
                        "GEN_WORKER_INTERRUPTED",
                        "本地生成执行异常，保留回执；请检查服务后读取已有任务，不会自动重复提交",
                        409,
                    )
                    job.error_code, job.error_message = interrupted.code, interrupted.message
                    job.stage = "generation." + job.status
                    record(
                        db,
                        job.workspace_id,
                        job.trace_id,
                        "generation.error",
                        "error",
                        generation_job_id=job.id,
                        error_code=job.error_code,
                    )
                    db.commit()
        except Timeout:
            break


def verify_output(db, job, note, reviewer):
    if job.status != "completed" or not job.output_asset_id:
        raise DomainError("GEN_OUTPUT_NOT_READY", "请先等待动态片段完成并检查画面", 409)
    _source_current(db, job)
    asset = owned(db, Asset, job.output_asset_id, job.workspace_id)
    verified_file(asset.workspace_id, asset.sha256, asset.suffix)
    asset.verified = True
    asset.license_note = "用户确认本次生成素材用途 / " + note
    job.receipt = {
        **job.receipt,
        "art_review": "user_confirmed",
        "reviewed_by": reviewer,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    return asset
