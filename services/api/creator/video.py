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
from .models import Asset, RenderJob, Video, VideoGenerationJob, uid
from .film import render_scene, scene_layout
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
        "version": "8",
    },
    {
        "id": "ffmpeg_media",
        "name": "真实素材 / 录屏混剪",
        "available": bool(shutil.which("ffmpeg")),
        "types": ["screen_demo", "montage"],
        "editability": "clip_level",
        "requires_gpu": False,
        "license": "depends-on-local-build",
        "version": "8",
    },
    {
        "id": "comfy_wan",
        "name": "AI 生成片段 / 真人与动漫",
        "available": bool(shutil.which("ffmpeg")),
        "types": ["ai_creative_scene"],
        "editability": "regenerate",
        "requires_gpu": False,
        "license": "model-apache-2.0; input-and-output-require-review",
        "version": "wan_comfy_local@1",
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


def ffmpeg(arguments, timeout=180, cwd=None):
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-protocol_whitelist",
                "file,pipe",
                "-y",
                *arguments,
            ],
            check=True,
            capture_output=True,
            timeout=timeout,
            cwd=cwd,
        )
    except (OSError, subprocess.SubprocessError):
        raise DomainError("VID_COMPOSE_FAILED", "渲染失败，请检查素材格式、FFmpeg 和可用磁盘空间") from None


def probe(path):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
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
    if ir.get("schema_version") not in ("1.0", "1.1"):
        raise DomainError("VID_IR_INVALID", "视频工程版本不兼容", 422)
    import re

    text = "\n".join(
        [
            value
            for s in ir["shots"]
            for value in [
                s.get("caption", ""),
                s.get("narration_text", ""),
                s.get("design", {}).get("headline", ""),
                s.get("design", {}).get("kicker", ""),
                s.get("design", {}).get("supporting", ""),
                *s.get("design", {}).get("points", []),
            ]
        ]
        + [c["text"] for c in ir.get("subtitles", [])]
        + [ir.get("presentation", {}).get("brand_label", "")]
    )
    if re.search(r"世界第一|保证.{0,8}成功|100[%％]|保证不封号|绝对安全|虚构好评", text):
        raise DomainError("QA_CONTENT_BLOCKED", "镜头或字幕含未经证实的绝对化声明", 422)

    def asset_for(asset_id, kinds):
        asset = owned(db, Asset, asset_id, workspace_id)
        if asset.brand_id != ir["brand_id"] or not asset.verified or asset.applicability_status != "current":
            raise DomainError("ASSET_LICENSE_UNVERIFIED", "请选用当前品牌已核实授权素材", 422)
        if asset.kind not in kinds:
            raise DomainError("VID_IR_INVALID", "素材格式与轨道不匹配", 422)
        path = file_path(workspace_id, asset.sha256, asset.suffix)
        if not path.is_file() or digest(path.read_bytes()) != asset.sha256:
            raise DomainError("ASSET_HASH_MISMATCH", "源素材缺失或字节已改变", 422)
        return asset

    for shot in ir["shots"]:
        if ir.get("presentation", {}).get("style") == "studio":
            layout = shot.get("design", {}).get("layout", "auto")
            allowed = (
                ("auto", "hero", "screen", "focus", "montage", "comic", "cinema")
                if shot.get("asset_id")
                else ("auto", "hero", "features", "steps", "closing", "diagram")
            )
            if layout not in allowed:
                raise DomainError(
                    "VID_IR_INVALID", "界面版式需要真实素材；文字镜头请选择开场、要点、步骤或收尾", 422
                )
        provider = next((p for p in PROVIDERS if p["id"] == shot["provider"]), None)
        if not provider or not provider["available"]:
            raise DomainError("VID_PROVIDER_UNSUPPORTED", "所选引擎尚未接入，本轮不替换视觉方案", 422)
        if shot["kind"] not in provider["types"]:
            raise DomainError("VID_IR_INVALID", "镜头类型与引擎不兼容", 422)
        if shot["provider"] in ("ffmpeg_media", "comfy_wan"):
            if not shot.get("asset_id"):
                raise DomainError("ASSET_MISSING", "素材镜头需要真实素材", 422)
            asset = asset_for(shot["asset_id"], ("image", "video"))
            generated = db.scalar(
                select(VideoGenerationJob).where(
                    VideoGenerationJob.workspace_id == workspace_id,
                    VideoGenerationJob.output_asset_id == asset.id,
                )
            )
            if shot["provider"] == "comfy_wan":
                if (
                    not generated
                    or generated.id != shot.get("generation_job_id")
                    or generated.status != "completed"
                ):
                    raise DomainError("GEN_PROVENANCE_REQUIRED", "AI镜头需要对应的已完成生成回执", 422)
                from .video_generation import _source_current

                _source_current(db, generated)
                if (
                    generated.receipt.get("output_sha256") != asset.sha256
                    or generated.receipt.get("art_review") != "user_confirmed"
                ):
                    raise DomainError("GEN_OUTPUT_INVALID", "生成回执与素材字节不一致", 422)
                if shot.get("design", {}).get("layout") in ("screen", "focus"):
                    raise DomainError("GEN_NOT_PRODUCT_EVIDENCE", "AI画面不能作为真实产品操作实录", 422)
            elif generated or shot.get("generation_job_id"):
                raise DomainError("GEN_PROVENANCE_REQUIRED", "内部生成片段须保留AI引擎及生成回执", 422)
            if asset.kind == "video":
                media = probe(file_path(workspace_id, asset.sha256, asset.suffix))
                required = (
                    shot.get("trim_start_frame", 0)
                    + (shot["duration_frames"] - shot.get("freeze_end_frames", 0))
                    * shot.get("speed_percent", 100)
                    / 100
                ) / ir["fps"]
                if required > float(media["format"]["duration"]) + 0.1:
                    raise DomainError(
                        "VID_MEDIA_TOO_SHORT", "录屏或视频长度不足，请缩短镜头或调整入点/速度", 422
                    )
        elif shot.get("asset_id") or shot.get("generation_job_id"):
            raise DomainError("VID_IR_INVALID", "MG 镜头不接受未使用的素材引用", 422)
        hold = shot.get("freeze_end_frames", 0)
        if hold and (hold >= shot["duration_frames"] or not shot.get("asset_id") or asset.kind != "video"):
            raise DomainError("VID_IR_INVALID", "末帧停留只用于视频素材且必须保留实际画面", 422)
    total = sum(s["duration_frames"] for s in ir["shots"])
    for key, id_key in (("audio_tracks", "track_id"), ("subtitles", "cue_id")):
        items = ir.get(key, [])
        if len({item[id_key] for item in items}) != len(items):
            raise DomainError("VID_IR_INVALID", "音轨或字幕 ID 重复", 422)
    ordered = sorted(ir.get("subtitles", []), key=lambda c: c["start_frame"])
    for index, cue in enumerate(ordered):
        if not 0 <= cue["start_frame"] < cue["end_frame"] <= total or (
            index and cue["start_frame"] < ordered[index - 1]["end_frame"]
        ):
            raise DomainError("VID_SUBTITLE_INVALID", "字幕不得重叠或超出视频范围", 422)
    for track in ir.get("audio_tracks", []):
        if track["start_frame"] + track["duration_frames"] > total or (
            track.get("loop") and track["role"] != "music"
        ):
            raise DomainError("VID_AUDIO_INVALID", "音轨超出全片范围，只有配乐允许循环", 422)
        asset = asset_for(track["asset_id"], ("audio",))
        media = probe(file_path(workspace_id, asset.sha256, asset.suffix))
        source_duration = float(media["format"]["duration"])
        source_start = track.get("source_start_frame", 0) / ir["fps"]
        if source_start >= source_duration or (
            not track.get("loop")
            and source_start + track["duration_frames"] / ir["fps"] > source_duration + 0.1
        ):
            raise DomainError("VID_AUDIO_INVALID", "音频长度不足，请调整源入点或轨道时长", 422)


def render_mg(shot, canvas, target):
    w, h, fps = canvas["width"], canvas["height"], canvas["fps"]
    frames = shot["duration_frames"]
    # Render at half resolution, upscale at encoding; typography remains parametric in IR.
    rw, rh = w // 2, h // 2
    small_font = font(max(6 if w <= 640 else 12, rw // 48))
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
                    from .graphics import draw_fit

                    draw_fit(
                        draw,
                        caption,
                        (int(rw * 0.08), int(rh * 0.35 + (1 - eased) * 15), int(rw * 0.92), int(rh * 0.73)),
                        max(20, rw // 22),
                        12,
                        "#e9f0f4",
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
        ["-loop", "1", "-i", str(path)]
        if asset.kind == "image"
        else ["-ss", str(shot.get("trim_start_frame", 0) / fps), "-i", str(path)]
    )
    filters = f"setpts=PTS/{shot.get('speed_percent', 100) / 100},scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x101722,fps={fps},setsar=1"
    if shot.get("freeze_end_frames"):
        filters += f",trim=end_frame={shot['duration_frames'] - shot['freeze_end_frames']},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop={shot['freeze_end_frames']}"
    subtitle = target.with_suffix(".ass")
    try:
        if shot.get("caption"):
            from .video_audio import ass_subtitles

            subtitle.write_text(
                ass_subtitles(
                    {
                        **canvas,
                        "subtitles": [
                            {"start_frame": 0, "end_frame": shot["duration_frames"], "text": shot["caption"]}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            filters += ",subtitles=" + subtitle.name
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
            ],
            cwd=target.parent,
        )
    finally:
        subtitle.unlink(missing_ok=True)


def render_project(db, job):
    ir = job.ir
    if ir.get("schema_version") != "1.1":
        raise DomainError("VID_IR_UPGRADE_REQUIRED", "旧版未完成渲染已阻断，请显式保存升级工程后重试")
    validate_ir(db, job.workspace_id, ir)
    cache = DATA_DIR / job.workspace_id / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    canvas = {k: ir[k] for k in ("width", "height", "fps")}
    canvas["presentation"] = ir.get("presentation", {"style": "classic"})
    studio = canvas["presentation"].get("style") == "studio"
    preview = job.purpose == "preview"
    if preview:
        canvas.update(
            width=640 if ir["width"] > ir["height"] else 360,
            height=640 if ir["height"] > ir["width"] else 360,
        )
    from .graphics import font_receipt

    face = font_receipt()
    clips, receipts = [], []
    for index, shot in enumerate(ir["shots"]):
        if studio:
            canvas.update(chapter=index + 1, chapters=len(ir["shots"]))
        asset = owned(db, Asset, shot["asset_id"], job.workspace_id) if shot.get("asset_id") else None
        key = digest(
            {
                "shot": {k: v for k, v in shot.items() if k not in ("shot_revision", "locked")},
                "canvas": canvas,
                "asset_sha256": asset.sha256 if asset else None,
                "provider_adapter_version": "pillow_ffmpeg@8",
                "font": face,
            }
        )
        target = cache / f"{key}.mp4"
        checksum = target.with_suffix(".sha256")
        cached = (
            target.is_file()
            and checksum.is_file()
            and digest(target.read_bytes()) == checksum.read_text().strip()
        )
        if not cached:
            tmp = cache / f"{key}-{uid()}.mp4"
            if studio:
                render_scene(shot, canvas, tmp, asset)
            elif shot["provider"] == "pillow_mg":
                render_mg(shot, canvas, tmp)
            else:
                render_media(asset, shot, canvas, tmp)
            tmp.replace(target)
            checksum.write_text(digest(target.read_bytes()), encoding="ascii")
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
                "asset_source": asset.source if asset else None,
                "asset_license_note": asset.license_note if asset else None,
                **({"generation_job_id": shot["generation_job_id"]} if shot.get("generation_job_id") else {}),
                **(
                    {
                        "scene_layout": scene_layout(shot),
                        "native_typography": True,
                    }
                    if studio
                    else {}
                ),
            }
        )
        record(
            db,
            job.workspace_id,
            job.trace_id,
            "shot.render",
            "ok",
            run_id=job.ir.get("source_run_id"),
            content_id=job.ir.get("source_content_id"),
            shot_id=shot["shot_id"],
            provider=shot["provider"],
            render_job_id=job.id,
            cached=cached,
            sha256=output_hash,
            video_project_id=job.video_id,
            generation_job_id=shot.get("generation_job_id"),
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
        from .video_audio import finish

        from types import SimpleNamespace

        scaled_job = SimpleNamespace(id=job.id, workspace_id=job.workspace_id, ir={**ir, **canvas})
        audio_sources = finish(db, scaled_job, temp_out)
        if preview:
            watermark = cache / (job.id + "-watermark.png")
            marked = cache / (job.id + "-preview.mp4")
            overlay = Image.new("RGBA", (canvas["width"], canvas["height"]), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            draw.rectangle((0, 0, canvas["width"], 38), fill=(0, 0, 0, 190))
            draw.text((12, 8), "内部预览 · 待人工确认", font=font(18), fill="white")
            overlay.save(watermark)
            try:
                ffmpeg(
                    [
                        "-i",
                        str(temp_out),
                        "-i",
                        str(watermark),
                        "-filter_complex",
                        "[0:v][1:v]overlay=0:0[v]",
                        "-map",
                        "[v]",
                        "-map",
                        "0:a",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "25",
                        "-c:a",
                        "copy",
                        "-movflags",
                        "+faststart",
                        str(marked),
                    ]
                )
                marked.replace(temp_out)
            finally:
                watermark.unlink(missing_ok=True)
                marked.unlink(missing_ok=True)
        metadata = probe(temp_out)
        video_stream = next(s for s in metadata["streams"] if s["codec_type"] == "video")
        if (video_stream["width"], video_stream["height"]) != (canvas["width"], canvas["height"]) or abs(
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
            "width": canvas["width"],
            "height": canvas["height"],
            "purpose": job.purpose,
            "watermark": preview,
            "ir_sha256": digest(ir),
            "fps": ir["fps"],
            "audio": "mixed_authorized_assets" if audio_sources else "silent_track_no_voiceover",
            "audio_sources": audio_sources,
            "subtitles": len(ir.get("subtitles", [])),
            "provider_adapter_version": "pillow_ffmpeg@8",
            "production_recipe": ir.get("production_recipe"),
            "presentation_version": "video_presentation@1" if studio else "classic@1",
            "audio_finishing": {
                "normalization_target_lufs": -16,
                "true_peak_target_db": -1.5,
                "music_ducking": {a["role"] for a in audio_sources} == {"music", "voiceover"},
                "fades": True,
            }
            if studio and audio_sources and canvas["presentation"].get("audio_finish", True)
            else None,
            "font": face,
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
        from .production import source_context, finish, failed

        if job.ir.get("source_creator_id"):
            from .models import Creator

            owner = db.get(Creator, job.ir["source_creator_id"])
            if owner:
                db.refresh(owner)
                if owner.status != "active":
                    continue
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
            source_context(db, job)
            if job.purpose == "final":
                from .quality import require_review

                current = db.get(Video, job.video_id)
                if current.revision != job.revision or digest(current.ir) != digest(job.ir):
                    raise DomainError("QUALITY_REPORT_STALE", "排队后工程已变化，请重新提交")
                require_review(db, current)
            receipt = render_project(db, job)
            video = db.get(Video, job.video_id)
            db.refresh(video)
            job.receipt, job.status = receipt, "completed"
            if job.purpose == "preview":
                if video.revision == job.revision:
                    video.status = "ready" if video.rendered_revision == video.revision else "preview_ready"
                from .production import preview_ready

                preview_ready(db, job)
            elif video.revision == job.revision:
                video.output_hash, video.rendered_revision, video.status = (
                    receipt["sha256"],
                    job.revision,
                    "ready",
                )
            if job.purpose == "final":
                from .quality import require_review

                require_review(db, video)
                finish(db, job, receipt)
            record(
                db,
                job.workspace_id,
                job.trace_id,
                "video.compose",
                "ok",
                run_id=job.ir.get("source_run_id"),
                content_id=job.ir.get("source_content_id"),
                render_job_id=job.id,
                video_project_id=video.id,
                sha256=receipt["sha256"],
            )
            db.commit()
        except DomainError as e:
            db.rollback()
            job = db.get(RenderJob, job.id)
            job.status, job.error_code = "failed", e.code
            failed(db, job, e.code)
            current_video = db.get(Video, job.video_id)
            if current_video.revision == job.revision:
                current_video.status = "failed"
            record(
                db,
                job.workspace_id,
                job.trace_id,
                "video.compose",
                "error",
                run_id=job.ir.get("source_run_id"),
                content_id=job.ir.get("source_content_id"),
                error_code=e.code,
                render_job_id=job.id,
                video_project_id=job.video_id,
            )
            db.commit()
