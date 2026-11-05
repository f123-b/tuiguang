import json
import math
import shutil
import subprocess
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw
from sqlalchemy import or_, select, update

from .config import DATA_DIR
from .domains import digest, file_path, font, owned
from .errors import DomainError
from .models import Asset, RenderJob, Video, uid
from .observability import record

PROVIDERS = [
    {
        "id": "pillow_mg",
        "name": "本地 MG 动画",
        "available": True,
        "types": ["motion_graphics"],
        "editability": "parametric",
        "requires_gpu": False,
        "license": "MIT-CMU",
        "version": "1",
    },
    {
        "id": "ffmpeg_media",
        "name": "真实素材 / 录屏混剪",
        "available": bool(shutil.which("ffmpeg")),
        "types": ["screen_demo", "montage"],
        "editability": "clip_level",
        "requires_gpu": False,
        "license": "depends-on-local-build",
        "version": "1",
    },
    {
        "id": "comfy_wan",
        "name": "AI 创意 / 卡通镜头",
        "available": False,
        "types": ["ai_creative_scene"],
        "editability": "regenerate",
        "requires_gpu": True,
        "license": "unverified",
        "version": None,
    },
    {
        "id": "blender",
        "name": "3D / CG",
        "available": False,
        "types": ["three_d"],
        "editability": "parametric",
        "requires_gpu": True,
        "license": "unverified",
        "version": None,
    },
]


def ffmpeg(arguments, timeout=180):
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *arguments],
            check=True,
            capture_output=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        raise DomainError("VID_COMPOSE_FAILED", "渲染失败，请检查素材格式、FFmpeg 和可用磁盘空间") from None


def probe(path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        raise DomainError("VID_MEDIA_INVALID", "媒体文件无法解析", 422) from None


def validate_ir(db, workspace_id, ir):
    if sum(shot["duration_frames"] for shot in ir["shots"]) > 3600:
        raise DomainError("VID_DURATION_INVALID", "本地版本最多支持 120 秒", 422)
    if len({s["shot_id"] for s in ir["shots"]}) != len(ir["shots"]):
        raise DomainError("VID_IR_INVALID", "镜头 ID 不可重复", 422)
    for shot in ir["shots"]:
        provider = next(p for p in PROVIDERS if p["id"] == shot["provider"])
        if not provider["available"]:
            raise DomainError("VID_PROVIDER_UNSUPPORTED", "所选引擎尚未接入，本轮不替换视觉方案", 422)
        if shot["kind"] not in provider["types"]:
            raise DomainError("VID_IR_INVALID", "镜头类型与引擎不兼容", 422)
        if shot["provider"] == "ffmpeg_media":
            if not shot.get("asset_id"):
                raise DomainError("ASSET_MISSING", "素材镜头需要真实素材", 422)
            asset = owned(db, Asset, shot["asset_id"], workspace_id)
            if asset.brand_id != ir["brand_id"] or not asset.verified:
                raise DomainError("ASSET_LICENSE_UNVERIFIED", "请选用当前品牌已确认授权的素材", 422)


def render_mg(shot, canvas, target):
    w, h, fps = canvas["width"], canvas["height"], canvas["fps"]
    frames = shot["duration_frames"]
    # Render at half resolution, upscale at encoding; typography remains parametric in IR.
    rw, rh = w // 2, h // 2
    title_font, small_font = font(max(20, rw // 22)), font(max(12, rw // 48))
    args = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{rw}x{rh}",
        "-r",
        str(fps),
        "-i",
        "pipe:0",
        "-vf",
        f"scale={w}:{h}",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "21",
        "-pix_fmt",
        "yuv420p",
        str(target),
    ]
    try:
        with subprocess.Popen(
            args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        ) as process:
            try:
                for frame in range(frames):
                    progress = min(1, frame / max(1, fps * 0.7))
                    eased = 1 - (1 - progress) ** 3
                    image = Image.new("RGB", (rw, rh), "#0c1520")
                    draw = ImageDraw.Draw(image)
                    center = (rw * 0.78, rh * 0.28)
                    for index in range(3):
                        radius = int(min(rw, rh) * (0.16 + index * 0.08) * eased)
                        offset = math.sin(frame / 28 + index) * 8
                        draw.ellipse(
                            (
                                center[0] - radius + offset,
                                center[1] - radius,
                                center[0] + radius + offset,
                                center[1] + radius,
                            ),
                            outline="#254a52",
                            width=2,
                        )
                    draw.rounded_rectangle(
                        (int(rw * 0.08), int(rh * 0.16), int(rw * 0.37), int(rh * 0.23)),
                        radius=10,
                        fill="#24433d",
                    )
                    draw.text(
                        (int(rw * 0.1), int(rh * 0.17)), "PRODUCT NOTES", fill="#88d2bc", font=small_font
                    )
                    caption = shot["caption"] or "创作，让产品被看见"
                    line_size = max(10, int(rw / max(20, rw // 22)) - 4)
                    lines = [
                        caption[i : i + line_size]
                        for i in range(0, min(len(caption), line_size * 4), line_size)
                    ]
                    for index, line in enumerate(lines):
                        draw.text(
                            (int(rw * 0.08), int(rh * 0.4 + index * rh * 0.1 + (1 - eased) * 30)),
                            line,
                            font=title_font,
                            fill="#e9f0f4",
                        )
                    draw.text(
                        (int(rw * 0.08), int(rh * 0.87)),
                        "AI 辅助制作 · 发布前请复核标识",
                        font=small_font,
                        fill="#78969c",
                    )
                    draw.rectangle(
                        (
                            int(rw * 0.08),
                            int(rh * 0.78),
                            int(rw * (0.08 + 0.7 * frame / max(1, frames - 1))),
                            int(rh * 0.785),
                        ),
                        fill="#81cfb5",
                    )
                    process.stdin.write(image.tobytes())
                process.stdin.close()
                process.wait(timeout=180)
                if process.returncode:
                    raise OSError("encoder failed")
            except BaseException:
                process.kill()
                process.wait()
                raise
    except (OSError, subprocess.SubprocessError):
        raise DomainError("VID_COMPOSE_FAILED", "MG 编码失败，请检查本地编码器") from None


def render_media(asset, shot, canvas, target):
    path = file_path(asset.workspace_id, asset.sha256, asset.suffix)
    if not path.is_file() or digest(path.read_bytes()) != asset.sha256:
        raise DomainError("ASSET_HASH_MISMATCH", "源素材缺失或哈希不一致")
    w, h, fps = canvas["width"], canvas["height"], canvas["fps"]
    input_args = (
        ["-loop", "1", "-i", str(path)] if asset.kind == "image" else ["-stream_loop", "-1", "-i", str(path)]
    )
    filters = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x101722,fps={fps},setsar=1"
    ffmpeg(
        [
            *input_args,
            "-vf",
            filters,
            "-frames:v",
            str(shot["duration_frames"]),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            str(target),
        ]
    )


def render_project(db, job):
    ir = job.ir
    validate_ir(db, job.workspace_id, ir)
    cache = DATA_DIR / job.workspace_id / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    canvas = {k: ir[k] for k in ("width", "height", "fps")}
    clips, receipts = [], []
    for shot in ir["shots"]:
        asset = owned(db, Asset, shot["asset_id"], job.workspace_id) if shot.get("asset_id") else None
        key = digest(
            {
                "shot": shot,
                "canvas": canvas,
                "asset_sha256": asset.sha256 if asset else None,
                "provider_adapter_version": "pillow_ffmpeg@1",
            }
        )
        target = cache / f"{key}.mp4"
        cached = target.is_file()
        if not cached:
            tmp = cache / f"{key}-{uid()}.mp4"
            if shot["provider"] == "pillow_mg":
                render_mg(shot, canvas, tmp)
            else:
                render_media(asset, shot, canvas, tmp)
            tmp.replace(target)
        clips.append(target)
        output_hash = digest(target.read_bytes())
        receipts.append(
            {
                "shot_id": shot["shot_id"],
                "shot_revision": shot["shot_revision"],
                "provider": shot["provider"],
                "cached": cached,
                "sha256": output_hash,
                "render_cache_key": key,
                "asset_sha256": asset.sha256 if asset else None,
            }
        )
        record(
            db,
            job.workspace_id,
            job.trace_id,
            "shot.render",
            "ok",
            shot_id=shot["shot_id"],
            provider=shot["provider"],
            render_job_id=job.id,
            cached=cached,
            sha256=output_hash,
            video_project_id=job.video_id,
        )
        db.commit()
    concat = cache / f"{job.id}.txt"
    concat.write_text("\n".join("file '" + path.name + "'" for path in clips), encoding="utf-8")
    temp_out = cache / f"assembled-{job.id}.mp4"
    duration = sum(s["duration_frames"] for s in ir["shots"]) / ir["fps"]
    try:
        ffmpeg(
            [
                "-f",
                "concat",
                "-safe",
                "1",
                "-i",
                str(concat),
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=48000:cl=stereo",
                "-map",
                "0:v",
                "-map",
                "1:a",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-t",
                str(duration),
                "-movflags",
                "+faststart",
                str(temp_out),
            ]
        )
        metadata = probe(temp_out)
        video_stream = next(s for s in metadata["streams"] if s["codec_type"] == "video")
        if (video_stream["width"], video_stream["height"]) != (ir["width"], ir["height"]) or abs(
            float(metadata["format"]["duration"]) - duration
        ) > 0.15:
            raise DomainError("QA_MEDIA_INVALID", "输出视频尺寸或时长不符合工程")
        sha = digest(temp_out.read_bytes())
        final = cache / f"{sha}.mp4"
        temp_out.replace(final)
        return {
            "sha256": sha,
            "shots": receipts,
            "duration_sec": duration,
            "width": ir["width"],
            "height": ir["height"],
            "fps": ir["fps"],
            "audio": "silent_track_no_voiceover",
            "qa": "technical_probe_passed",
            "revision": job.revision,
        }
    finally:
        concat.unlink(missing_ok=True)


def process_render_jobs(db):
    now = datetime.now(timezone.utc)
    pending = db.scalars(
        select(RenderJob).where(
            or_(
                RenderJob.status == "queued",
                (RenderJob.status == "running") & (RenderJob.lease_until < now.isoformat()),
            )
        )
    ).all()
    for job in pending:
        claim = db.execute(
            update(RenderJob)
            .where(
                RenderJob.id == job.id,
                or_(
                    RenderJob.status == "queued",
                    (RenderJob.status == "running") & (RenderJob.lease_until < now.isoformat()),
                ),
            )
            .values(status="running", lease_until=(now + timedelta(minutes=30)).isoformat())
        )
        db.commit()
        if claim.rowcount != 1:
            continue
        try:
            receipt = render_project(db, job)
            video = db.get(Video, job.video_id)
            job.receipt, job.status = receipt, "completed"
            if video.revision == job.revision:
                video.output_hash, video.rendered_revision, video.status = (
                    receipt["sha256"],
                    job.revision,
                    "ready",
                )
            record(
                db,
                job.workspace_id,
                job.trace_id,
                "video.compose",
                "ok",
                render_job_id=job.id,
                video_project_id=video.id,
                sha256=receipt["sha256"],
            )
            db.commit()
        except DomainError as e:
            db.rollback()
            job = db.get(RenderJob, job.id)
            job.status, job.error_code = "failed", e.code
            db.get(Video, job.video_id).status = "failed"
            record(
                db,
                job.workspace_id,
                job.trace_id,
                "video.compose",
                "error",
                error_code=e.code,
                render_job_id=job.id,
                video_project_id=job.video_id,
            )
            db.commit()
