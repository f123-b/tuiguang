"""Opt-in local media production after a draft and its known cost are durable."""

from copy import deepcopy

from .domains import compliance_report, owned, file_path, digest
from .errors import DomainError
from .graphics import GraphicDocument, lock_content, render_graphics
from .models import Asset, Brand, Content, Creator, RenderJob, Run, Video
from .observability import record
from .schemas import VideoInput


def options_snapshot(db, creator, options=None):
    value = deepcopy(options if options is not None else creator.render_options)
    if not value:
        return None
    if value.get("video") and value.get("video_mode") != "mg":
        asset = owned(db, Asset, value.get("asset_id"), creator.workspace_id)
        if asset.brand_id != creator.brand_id or not asset.verified or asset.kind not in ("image", "video"):
            raise DomainError("ASSET_LICENSE_UNVERIFIED", "自动素材镜头需要本品牌已核实的图片或视频", 422)
        path = file_path(asset.workspace_id, asset.sha256, asset.suffix)
        if (
            value.get("asset_sha256") not in (None, asset.sha256)
            or not path.is_file()
            or digest(path.read_bytes()) != asset.sha256
        ):
            raise DomainError("ASSET_HASH_MISMATCH", "已冻结的素材缺失或字节发生变化", 422)
        if asset.kind == "video":
            from .video import probe

            if float(probe(path)["format"]["duration"]) + 0.1 < value["duration_sec"] / 5:
                raise DomainError(
                    "VID_MEDIA_TOO_SHORT", "所选视频不足一个镜头时长，请调整素材或制作时长", 422
                )
        value["asset_sha256"] = asset.sha256
    return value


def video_document(db, content, creator, options):
    brand = db.get(Brand, creator.brand_id)
    facts = [f for f in brand.facts if f["id"] in content.fact_refs and f["verified"]]
    captions = [
        content.title,
        "这次介绍的产品功能",
        facts[0]["claim"] if facts and len(facts[0]["claim"]) <= 180 else "完整功能与来源请见正文",
        "请结合实际产品版本核对",
        "发布前复核事实、授权与 AI 标识",
    ]
    total = options["duration_sec"] * 30
    base = total // 5
    shots = []
    mode = options["video_mode"]
    if mode != "mg":
        asset = owned(db, Asset, options["asset_id"], content.workspace_id)
        if asset.sha256 != options.get("asset_sha256"):
            raise DomainError("ASSET_HASH_MISMATCH", "已冻结的制作素材发生变化")
    for i, caption in enumerate(captions):
        media = mode in ("screen_demo", "montage") or (mode == "mixed" and i in (1, 3))
        shots.append(
            {
                "shot_id": f"s{i + 1}",
                "provider": "ffmpeg_media" if media else "pillow_mg",
                "kind": ("screen_demo" if mode == "screen_demo" else "montage")
                if media
                else "motion_graphics",
                "duration_frames": base if i < 4 else total - base * 4,
                "caption": caption,
                "asset_id": options.get("asset_id") if media else None,
            }
        )
    width, height = {"wide": (1920, 1080), "portrait": (1080, 1920), "square": (1080, 1080)}[options["size"]]
    document = VideoInput(
        brand_id=creator.brand_id,
        name=content.title if len(content.title) <= 120 else "日任务视频 · " + content.id[:8],
        width=width,
        height=height,
        shots=shots,
        preview_required=options.get("review_preview_before_final", False),
    ).model_dump()
    return {
        "schema_version": "1.1",
        **document,
        "source_creator_id": creator.id,
        "source_run_id": content.run_id,
        "source_content_id": content.id,
        "source_content_revision": content.revision,
        "source_brand_revision": brand.revision,
    }


def prepare(db, run, content):
    options = run.release.get("production_options") or {}
    if not (options.get("graphics") or options.get("video")):
        run.status, run.stage = "completed", "awaiting_user_review"
        db.commit()
        return
    creator = db.get(Creator, run.creator_id)
    db.refresh(creator)
    if creator.status != "active":
        # Already submitted model work may finish; do not start new media while paused.
        run.status, run.stage = "queued", "asset_rendering"
        db.commit()
        return
    try:
        lock_content(db, content)
        if content.revision != 1:
            raise DomainError("VID_AUTOMATION_SOURCE_STALE", "草稿已被手动修改，请在工作室显式制作媒体")
        if options.get("graphics"):
            if not content.graphics:
                content.graphics = GraphicDocument.model_validate(
                    {
                        "schema_version": "1.0",
                        "renderer_version": "graphic_cards@1",
                        "theme": "midnight",
                        "size": {"wide": "landscape", "portrait": "portrait", "square": "square"}[
                            options["size"]
                        ],
                        "pages": [
                            {
                                "page_id": "cover",
                                "template": "editorial",
                                "heading": content.title,
                                "text": "有来源的产品信息，发布前请人工核对。",
                            },
                            {
                                "page_id": "facts",
                                "template": "checklist",
                                "heading": "本次引用的已核实资料",
                                "text": "",
                            },
                        ],
                    }
                ).model_dump()
                db.commit()
            graphic_receipt = render_graphics(db, content)
            record(
                db,
                run.workspace_id,
                run.trace_id,
                "graphics.render",
                "ok",
                run.id,
                content_id=content.id,
                sha256=graphic_receipt["pages"][0]["png_sha256"],
            )
        if options.get("video") and not content.video_attachment:
            from .video import validate_ir

            ir = video_document(db, content, creator, options)
            validate_ir(db, content.workspace_id, ir)
            video = Video(
                workspace_id=content.workspace_id,
                brand_id=creator.brand_id,
                name=content.title,
                ir=ir,
                status="queued",
                preview_required=ir["preview_required"],
            )
            db.add(video)
            db.flush()
            db.add(
                RenderJob(
                    workspace_id=content.workspace_id,
                    video_id=video.id,
                    revision=video.revision,
                    ir=ir,
                    trace_id=run.trace_id,
                    purpose="preview" if video.preview_required else "final",
                )
            )
            content.video_attachment = {"video_id": video.id, "revision": video.revision, "sha256": None}
            content.status = "asset_rendering"
        content.compliance = compliance_report(db, content)
        rendering = bool(content.video_attachment and not content.video_attachment.get("sha256"))
        run.status, run.stage = (
            ("rendering", "asset_rendering") if rendering else ("completed", "awaiting_user_review")
        )
        record(db, run.workspace_id, run.trace_id, "production.prepare", "ok", run.id, content_id=content.id)
        db.commit()
    except DomainError as error:
        db.rollback()
        db.refresh(content)
        db.refresh(run)
        run.status, run.stage, run.error_code = "failed", "media_failed", error.code
        content.status = "awaiting_user_review"
        content.compliance = compliance_report(db, content)
        record(
            db,
            run.workspace_id,
            run.trace_id,
            "production.prepare",
            "error",
            run.id,
            error.code,
            content_id=content.id,
        )
        db.commit()


def source_context(db, job):
    if not job.ir.get("source_content_id"):
        return None
    content = owned(db, Content, job.ir["source_content_id"], job.workspace_id)
    creator = owned(db, Creator, job.ir["source_creator_id"], job.workspace_id)
    db.refresh(content)
    if content.status == "user_reported_published":
        raise DomainError("CONTENT_ALREADY_REPORTED", "已登记作品保持历史快照，不能重新执行自动媒体步骤")
    db.refresh(creator)
    if content.approved_revision == content.revision:
        raise DomainError(
            "QA_CONTENT_BLOCKED", "已审核内容需要先显式保存工程并重新绑定审核，不能自动替换成片"
        )
    brand = db.get(Brand, creator.brand_id)
    db.refresh(brand)
    if (
        content.creator_id != creator.id
        or content.revision != job.ir["source_content_revision"]
        or brand.revision != job.ir["source_brand_revision"]
    ):
        raise DomainError("VID_AUTOMATION_SOURCE_STALE", "自动制作的源内容或品牌已变化，请人工重新保存工程")
    return content, creator, db.get(Run, content.run_id)


def finish(db, job, receipt):
    context = source_context(db, job)
    if not context:
        return
    content, creator, run = context
    lock_content(db, content, job.ir["source_content_revision"])
    if content.status == "user_reported_published":
        raise DomainError("CONTENT_ALREADY_REPORTED", "已登记作品不改写媒体审核记录")
    if not content.video_attachment or content.video_attachment["video_id"] != job.video_id:
        raise DomainError("VID_AUTOMATION_SOURCE_STALE", "用户已调整视频绑定，未覆盖用户选择")
    content.video_attachment = {
        "video_id": job.video_id,
        "revision": job.revision,
        "sha256": receipt["sha256"],
    }
    content.status = "awaiting_user_review"
    content.compliance = compliance_report(db, content)
    run.status, run.stage, run.error_code = "completed", "awaiting_user_review", None


def failed(db, job, code):
    if not job.ir.get("source_content_id"):
        return
    content = db.get(Content, job.ir["source_content_id"])
    if content and content.workspace_id == job.workspace_id and content.status != "user_reported_published":
        run = db.get(Run, content.run_id)
        run.status, run.stage, run.error_code = "failed", "media_failed", code
        if content.revision == job.ir["source_content_revision"]:
            content.status = "awaiting_user_review"
            content.compliance = compliance_report(db, content)


def preview_ready(db, job):
    context = source_context(db, job)
    if context:
        content, creator, run = context
        content.status = "needs_preview_review"
        run.status, run.stage = "awaiting_review", "preview.ready"
