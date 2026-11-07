"""Offline narration -> measured timeline -> audio/subtitles -> real preview."""

import copy
import math
import re
from datetime import datetime, timedelta, timezone

from pydantic import Field
from sqlalchemy import or_, select, update

from . import speech
from .config import DATA_DIR
from .domains import digest, file_path, owned, serialize, store_file
from .errors import DomainError
from .models import Asset, Brand, NarrationJob, RenderJob, Video
from .observability import record
from .schemas import DTO, Short
from .video import ffmpeg, probe, validate_ir
from .video_edit import checkpoint, lock_video

from typing import Literal

VERSION = "narration_pipeline@2"


class NarrationOptions(DTO):
    voice_id: str = Field(min_length=1, max_length=120)
    rate: int = Field(default=0, ge=-5, le=5)
    fit_mode: Literal["extend", "fixed"] = "extend"
    subtitles: bool = True
    usage_confirmed: Literal[True]


class NarrationLine(DTO):
    shot_id: Short
    text: str = Field(default="", max_length=600)


class NarrationRequest(NarrationOptions):
    expected_revision: int = Field(ge=1)
    lines: list[NarrationLine] = Field(min_length=1, max_length=12)


def snapshot(db, video):
    db.refresh(video)
    validate_ir(db, video.workspace_id, video.ir)
    brand = owned(db, Brand, video.brand_id, video.workspace_id)
    db.refresh(brand)
    assets = []
    ids = {s.get("asset_id") for s in video.ir["shots"] + video.ir.get("audio_tracks", [])} - {None}
    for identifier in sorted(ids):
        a = owned(db, Asset, identifier, video.workspace_id)
        db.refresh(a)
        if a.applicability_status != "current":
            raise DomainError("ASSET_LICENSE_UNVERIFIED", "素材适用版本待复核", 422)
        assets.append(
            {
                k: getattr(a, k)
                for k in (
                    "id",
                    "sha256",
                    "verified",
                    "applicability_status",
                    "product_version",
                    "license_note",
                )
            }
        )
    return {
        "revision": video.revision,
        "ir": copy.deepcopy(video.ir),
        "brand_revision": brand.revision,
        "facts": brand.facts,
        "assets": assets,
    }


def enqueue(db, video, data, key, user_id, trace):
    document = data.model_dump()
    request_hash = digest({"video_id": video.id, "document": document})
    old = db.scalar(
        select(NarrationJob).where(
            NarrationJob.workspace_id == video.workspace_id, NarrationJob.idempotency_key == key
        )
    )
    if old:
        if old.request_hash != request_hash:
            raise DomainError("IDEMPOTENCY_KEY_CONFLICT", "该请求编号已用于其他制作")
        return old
    lock_video(db, video, data.expected_revision)
    if db.scalar(
        select(NarrationJob.id).where(
            NarrationJob.video_id == video.id, NarrationJob.status.in_(["queued", "running"])
        )
    ):
        raise DomainError("TTS_JOB_PENDING", "该视频已有配音制作任务，请等待完成")
    if data.voice_id not in {v["id"] for v in speech.voices()}:
        raise DomainError("TTS_PROVIDER_UNAVAILABLE", "所选本机语音不可用，请重新选择", 422)
    document["voice_source"] = speech.voice_snapshot(data.voice_id)
    ids = [s["shot_id"] for s in video.ir["shots"]]
    if [line.shot_id for line in data.lines] != ids:
        raise DomainError("TTS_SCRIPT_INVALID", "旁白必须按当前镜头顺序逐镜填写", 422)
    text = "\n".join(line.text for line in data.lines)
    if not text.strip() or len(text) > 4000:
        raise DomainError("TTS_SCRIPT_INVALID", "旁白不能为空，总计最多 4000 字", 422)
    if re.search(r"世界第一|保证.{0,8}成功|100[%％]|保证不封号|绝对安全|虚构好评", text):
        raise DomainError("QA_CONTENT_BLOCKED", "旁白含未经证实的绝对化承诺", 422)
    if data.subtitles and video.ir.get("subtitles"):
        raise DomainError("TTS_SUBTITLES_EXIST", "当前已有字幕，请取消自动字幕以保留原字幕", 422)
    job = NarrationJob(
        workspace_id=video.workspace_id,
        video_id=video.id,
        base_revision=video.revision,
        requested_by=user_id,
        idempotency_key=key,
        request_hash=request_hash,
        document=document,
        source=snapshot(db, video),
        trace_id=trace,
    )
    db.add(job)
    video.status = "queued"
    db.flush()
    record(
        db,
        video.workspace_id,
        trace,
        "narration.queued",
        "ok",
        video_project_id=video.id,
        narration_job_id=job.id,
    )
    return job


def assert_current(db, job, video):
    live = snapshot(db, video)
    if video.revision != job.base_revision or digest(live) != digest(job.source):
        raise DomainError("VID_REVISION_CONFLICT", "工程或依据已改变，本次制作没有覆盖新版本")


def subtitle_chunks(text):
    return [text[i : i + 45] for i in range(0, len(text), 45)]


def produce(db, job):
    video = owned(db, Video, job.video_id, job.workspace_id)
    assert_current(db, job, video)
    doc = job.document
    ir = copy.deepcopy(job.source["ir"])
    clips, segments, cues = [], [], []
    cursor = 0
    voice_source = doc.get("voice_source")
    voice_receipts = []
    for i, (shot, line) in enumerate(zip(ir["shots"], doc["lines"], strict=True)):
        job.stage = "narration.synthesizing"
        job.receipt = {"completed_shots": i, "total_shots": len(ir["shots"])}
        db.commit()
        frames = shot["duration_frames"]
        text = line["text"].strip()
        seconds = 0
        if text:
            if voice_source and speech.voice_snapshot(doc["voice_id"]) != voice_source:
                raise DomainError("TTS_PROVIDER_CHANGED", "本地声音或模型文件已变化，请重新提交配音任务", 422)
            # This is a local safe operation: restart may repeat synthesis, never a paid model request.
            asset = speech.synthesize(job.workspace_id, video.brand_id, text, doc["voice_id"], doc["rate"])
            receipt = getattr(asset, "synthesis_receipt", voice_source)
            if voice_source and {k: (receipt or {}).get(k) for k in voice_source} != voice_source:
                raise DomainError("TTS_PROVIDER_CHANGED", "合成回执与任务声音来源不符，请重新提交", 422)
            voice_receipts.append(receipt)
            path = file_path(asset.workspace_id, asset.sha256, asset.suffix)
            media = probe(path)
            seconds = float(media["format"]["duration"])
            if (
                not math.isfinite(seconds)
                or seconds <= 0
                or not any(s["codec_type"] == "audio" for s in media["streams"])
            ):
                raise DomainError("TTS_RESULT_INVALID", "配音未生成有效音频", 422)
            needed = math.ceil(seconds * ir["fps"]) + 6
            if needed > frames:
                if doc["fit_mode"] == "fixed":
                    raise DomainError(
                        "TTS_DURATION_TOO_LONG",
                        f"镜头 {i + 1} 配音需至少 {needed / 30:.2f} 秒，超过镜头时长。请缩短旁白或选择自动延长",
                        422,
                    )
                if shot.get("locked"):
                    raise DomainError(
                        "VID_SHOT_LOCKED", f"镜头 {i + 1} 已锁定，无法延长；请解锁或缩短旁白", 422
                    )
                frames = needed
            clips.append({"path": path, "start_frame": cursor, "sha256": asset.sha256})
        if frames > 1800 or cursor + frames > 3600:
            raise DomainError(
                "VID_DURATION_INVALID", "配音适配后单镜超过 60 秒或全片超过 120 秒，请缩短旁白", 422
            )
        if frames > shot["duration_frames"] and shot.get("asset_id"):
            asset = owned(db, Asset, shot["asset_id"], job.workspace_id)
            if asset.kind == "video":
                shot["freeze_end_frames"] = (
                    shot.get("freeze_end_frames", 0) + frames - shot["duration_frames"]
                )
        shot["duration_frames"] = frames
        segments.append(
            {
                "shot_id": shot["shot_id"],
                "start_frame": cursor,
                "duration_frames": frames,
                "speech_sec": seconds,
                "text": text,
            }
        )
        if doc["subtitles"] and text:
            chunks = subtitle_chunks(text)
            end = cursor + max(len(chunks), math.ceil(seconds * ir["fps"]))
            for n, chunk in enumerate(chunks):
                cues.append(
                    {
                        "cue_id": f"n{i}-{n}",
                        "start_frame": cursor + (end - cursor) * n // len(chunks),
                        "end_frame": cursor + (end - cursor) * (n + 1) // len(chunks),
                        "text": chunk,
                    }
                )
        cursor += frames
    if len(cues) > 100:
        raise DomainError("VID_SUBTITLE_INVALID", "自动字幕超过 100 条，请缩短旁白", 422)
    if not doc["subtitles"] and ir.get("subtitles") and doc["fit_mode"] == "extend":

        def remap(frame):
            original_cursor = 0
            for old, new in zip(job.source["ir"]["shots"], segments, strict=True):
                if frame <= original_cursor + old["duration_frames"]:
                    return new["start_frame"] + round(
                        (frame - original_cursor) * new["duration_frames"] / old["duration_frames"]
                    )
                original_cursor += old["duration_frames"]
            return cursor

        for cue in ir["subtitles"]:
            cue["start_frame"], cue["end_frame"] = remap(cue["start_frame"]), remap(cue["end_frame"])
    job.stage = "narration.aligning"
    job.receipt = {"completed_shots": len(segments), "total_shots": len(segments)}
    db.commit()
    temp = DATA_DIR / job.workspace_id / "speech-tmp"
    temp.mkdir(parents=True, exist_ok=True)
    output = temp / (job.id + "-aligned.wav")
    args = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    filters = []
    for i, clip in enumerate(clips, 1):
        args.extend(["-i", str(clip["path"])])
        ms = round(clip["start_frame"] * 1000 / ir["fps"])
        filters.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{i}]")
    filters.append(
        "[0:a]"
        + "".join(f"[a{i}]" for i in range(1, len(clips) + 1))
        + f"amix=inputs={len(clips) + 1}:duration=first:normalize=0[a]"
    )
    try:
        ffmpeg(
            [
                *args,
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[a]",
                "-t",
                str(cursor / ir["fps"]),
                "-c:a",
                "pcm_s16le",
                str(output),
            ]
        )
        sha = store_file(job.workspace_id, output.read_bytes(), ".wav")
    finally:
        output.unlink(missing_ok=True)
    # External synthesis/FFmpeg ran without a long database write lock.
    if voice_source and speech.voice_snapshot(doc["voice_id"]) != voice_source:
        raise DomainError("TTS_PROVIDER_CHANGED", "制作期间声音或模型文件已变化，没有覆盖工程", 422)
    lock_video(db, video, job.base_revision)
    assert_current(db, job, video)
    # This explicit production action starts a manual revision, like editor save.
    # It must not inherit automatic creator pause/dependency state.
    ir = {k: v for k, v in ir.items() if not k.startswith("source_")}
    audio = Asset(
        workspace_id=job.workspace_id,
        brand_id=video.brand_id,
        name="逐镜头配音.wav",
        sha256=sha,
        suffix=".wav",
        kind="audio",
        source=f"用户确认文本 / {voice_source or doc['voice_id']} / {VERSION}",
        license_note="操作者明确确认本次使用权；本地语音输出，不代表本软件认证其商业许可。",
        verified=True,
    )
    db.add(audio)
    db.flush()
    tracks = [t for t in ir.get("audio_tracks", []) if t["role"] != "voiceover"]
    if len(tracks) >= 8:
        raise DomainError("VID_AUDIO_INVALID", "配乐轨道已满，请先移除一条再加入配音", 422)
    ir["audio_tracks"] = tracks + [
        {
            "track_id": "voice-" + job.id[:20],
            "asset_id": audio.id,
            "role": "voiceover",
            "start_frame": 0,
            "duration_frames": cursor,
            "source_start_frame": 0,
            "volume_percent": 100,
            "loop": False,
        }
    ]
    if doc["subtitles"]:
        ir["subtitles"] = cues
    ir["narration"] = {
        "version": VERSION,
        "job_id": job.id,
        "voice_id": doc["voice_id"],
        "rate": doc["rate"],
        "segments": segments,
        "usage_confirmed_by": job.requested_by,
    }
    validate_ir(db, video.workspace_id, ir)
    checkpoint(db, video, job.requested_by)
    video.ir, video.revision, video.status = ir, video.revision + 1, "queued"
    video.preview_required = True
    video.ir = {**ir, "preview_required": True}
    checkpoint(db, video, job.requested_by)
    from .quality import build_report

    report = build_report(db, "video", video)
    render = RenderJob(
        workspace_id=video.workspace_id,
        video_id=video.id,
        revision=video.revision,
        ir=video.ir,
        purpose="preview",
        trace_id=job.trace_id,
    )
    db.add(render)
    db.flush()
    job.status, job.stage = "completed", "narration.preview_queued"
    job.receipt = {
        "version": VERSION,
        "voice_source": voice_source,
        "voice_receipts": voice_receipts,
        "completed_shots": len(segments),
        "total_shots": len(segments),
        "duration_sec": cursor / ir["fps"],
        "original_duration_sec": sum(s["duration_frames"] for s in job.source["ir"]["shots"]) / ir["fps"],
        "audio_asset_id": audio.id,
        "audio_sha256": sha,
        "segments": segments,
        "video_revision": video.revision,
        "preview_job_id": render.id,
        "quality_report_id": report.id,
    }
    record(
        db,
        job.workspace_id,
        job.trace_id,
        "narration.complete",
        "ok",
        video_project_id=video.id,
        narration_job_id=job.id,
        render_job_id=render.id,
    )
    db.commit()


def process_narration_jobs(db):
    now = datetime.now(timezone.utc)
    eligible = or_(
        NarrationJob.status == "queued",
        (NarrationJob.status == "running") & (NarrationJob.lease_until < now.isoformat()),
    )
    jobs = db.scalars(select(NarrationJob).where(eligible).order_by(NarrationJob.created_at)).all()
    for job in jobs:
        claim = db.execute(
            update(NarrationJob)
            .where(NarrationJob.id == job.id, eligible)
            .values(status="running", lease_until=(now + timedelta(minutes=30)).isoformat())
        )
        db.commit()
        if claim.rowcount != 1:
            continue
        try:
            produce(db, job)
        except (DomainError, OSError, ValueError) as error:
            db.rollback()
            db.refresh(job)
            job.status, job.stage = "failed", "narration.failed"
            job.error_code = error.code if isinstance(error, DomainError) else "TTS_RESULT_INVALID"
            job.error_message = (
                error.message
                if isinstance(error, DomainError)
                else "本地配音文件处理失败，请检查磁盘和语音后重试"
            )
            video = db.get(Video, job.video_id)
            db.refresh(video)
            if video.revision == job.base_revision:
                video.status = "draft"
            record(
                db,
                job.workspace_id,
                job.trace_id,
                "narration.failed",
                "error",
                error_code=job.error_code,
                narration_job_id=job.id,
                video_project_id=job.video_id,
            )
            db.commit()


def public_job(job):
    row = serialize(job)
    row.pop("source", None)
    return row
