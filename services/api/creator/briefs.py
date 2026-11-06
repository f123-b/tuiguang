"""Versioned user intent, bounded scripts and independent video projects."""

import re
import unicodedata
from typing import Annotated, Literal

from pydantic import Field, field_validator
from sqlalchemy import select, update

from .domains import digest, file_path, owned, serialize
from .errors import DomainError
from .models import Asset, Brand, BriefPlan, CreationBrief, RenderJob, Video
from .schemas import DTO, Short, VideoInput

VERSION = "directed_video@1"
Phrase = Annotated[str, Field(min_length=1, max_length=120)]


class BriefInput(DTO):
    brand_id: Short
    topic: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1, max_length=6000)
    audience: str = Field(default="", max_length=1000)
    tone: str = Field(default="清楚、克制、不夸张", max_length=500)
    verbatim_script: str = Field(default="", max_length=2400)
    required_phrases: list[Phrase] = Field(default_factory=list, max_length=8)
    forbidden_phrases: list[Phrase] = Field(default_factory=list, max_length=8)
    call_to_action: str = Field(default="", max_length=120)
    duration_sec: int = Field(default=30, ge=3, le=60)
    size: Literal["wide", "portrait", "square"] = "wide"
    visual_mode: Literal["mg", "mixed", "screen_demo"] = "mg"
    fact_refs: list[Short] = Field(default_factory=list, max_length=30)
    asset_ids: list[Short] = Field(default_factory=list, max_length=12)

    @field_validator("fact_refs", "asset_ids", "required_phrases", "forbidden_phrases")
    @classmethod
    def unique(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("列表不可重复")
        return value


class ScriptShot(DTO):
    duration_frames: int = Field(ge=15, le=1800)
    caption: str = Field(min_length=1, max_length=180)
    narration: str = Field(default="", max_length=600)
    visual_note: str = Field(default="", max_length=500)
    asset_id: Short | None = None


class ScriptInput(DTO):
    title: str = Field(min_length=1, max_length=180)
    fact_refs: list[Short] = Field(default_factory=list, max_length=30)
    shots: list[ScriptShot] = Field(min_length=1, max_length=12)
    uncertainties: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        default_factory=list, max_length=8
    )


def lock_brief(db, brief, revision):
    db.execute(
        update(CreationBrief).where(CreationBrief.id == brief.id).values(revision=CreationBrief.revision)
    )
    db.refresh(brief)
    if brief.revision != revision:
        raise DomainError("BRIEF_REVISION_CONFLICT", "创作要求已变化，请刷新后重新确认")


def snapshot(db, brief):
    brand = owned(db, Brand, brief.brand_id, brief.workspace_id)
    db.refresh(brand)
    doc = BriefInput.model_validate(brief.document).model_dump()
    facts = [f for f in brand.facts if f["id"] in doc["fact_refs"] and f["verified"]]
    if set(doc["fact_refs"]) != {f["id"] for f in facts}:
        raise DomainError("BRIEF_FACTS_STALE", "所选事实缺失或尚未核实，请重新选择", 422)
    assets = []
    for identifier in doc["asset_ids"]:
        asset = owned(db, Asset, identifier, brief.workspace_id)
        db.refresh(asset)
        if (
            asset.brand_id != brand.id
            or not asset.verified
            or asset.kind not in ("image", "video")
            or asset.applicability_status != "current"
        ):
            raise DomainError(
                "ASSET_LICENSE_UNVERIFIED", "仅可使用本品牌已核实授权且版本有效的图片或视频", 422
            )
        path = file_path(asset.workspace_id, asset.sha256, asset.suffix)
        if not path.is_file() or digest(path.read_bytes()) != asset.sha256:
            raise DomainError("ASSET_HASH_MISMATCH", "所选素材缺失或已变化", 422)
        assets.append(
            {
                k: getattr(asset, k)
                for k in (
                    "id",
                    "name",
                    "sha256",
                    "kind",
                    "product_version",
                    "product_source_id",
                    "source",
                    "license_note",
                )
            }
        )
    if doc["visual_mode"] != "mg" and not assets:
        raise DomainError("BRIEF_ASSETS_REQUIRED", "实录或混合制作请先选择授权素材", 422)
    return {
        "version": VERSION,
        "brief_id": brief.id,
        "brief_revision": brief.revision,
        "document": doc,
        "brand": {"id": brand.id, "name": brand.name, "revision": brand.revision, "facts": facts},
        "assets": assets,
    }


def review_script(frozen, script):
    doc = frozen["document"]
    captions = "\n".join(s["caption"] for s in script["shots"])
    spoken = "\n".join(s["narration"] for s in script["shots"])
    text = script["title"] + "\n" + captions + "\n" + spoken
    normalized = unicodedata.normalize("NFKC", text).casefold()
    issues = []
    total = sum(s["duration_frames"] for s in script["shots"])
    if total != doc["duration_sec"] * 30:
        issues.append("分镜总时长与指定时长不一致，请调整或均分时长")
    for phrase in doc["required_phrases"] + ([doc["call_to_action"]] if doc["call_to_action"] else []):
        if phrase not in captions:
            issues.append("画面文字缺少必现原文：" + phrase)
    for phrase in doc["forbidden_phrases"]:
        if unicodedata.normalize("NFKC", phrase).casefold() in normalized:
            issues.append("出现用户禁用词：" + phrase)
    if re.search(r"世界第一|保证.{0,8}成功|100[%％]|保证不封号|绝对安全|虚构好评", text):
        issues.append("含无法证实的绝对化承诺")
    allowed_facts = {f["id"] for f in frozen["brand"]["facts"]}
    if not set(script["fact_refs"]) <= allowed_facts:
        issues.append("脚本引用了未选择或未核实的事实")
    if allowed_facts and not script["fact_refs"]:
        issues.append("脚本没有引用所选已核实事实")
    asset_ids = {a["id"] for a in frozen["assets"]}
    selected = [s.get("asset_id") for s in script["shots"]]
    if any(i and i not in asset_ids for i in selected):
        issues.append("脚本引用了未授权给本次创作的素材")
    mode = doc["visual_mode"]
    if mode == "mg" and any(selected):
        issues.append("MG 形式不应引用实录素材")
    if mode == "screen_demo" and not all(selected):
        issues.append("实录形式的每个镜头都须指定授权素材")
    if mode == "mixed" and (not any(selected) or all(selected)):
        issues.append("混合形式需要同时包含 MG 和实录镜头")
    return {
        "status": "needs_revision" if issues else "needs_confirmation",
        "issues": issues,
        "human_review": [
            "请核对主题、内容准确性、受众与表达目的",
            "旁白仅为文字脚本，画面说明仅为建议，均不代表已生成音频或新画面",
        ],
        "uncertainties": script["uncertainties"],
        "not_verified_facts": True,
    }


def save_plan(db, brief, frozen, script, method, run_id=None, parent_id=None, usage=None):
    script = ScriptInput.model_validate(script).model_dump()
    key = digest(
        {
            "input": digest(frozen),
            "script": script,
            "method": method,
            "run_id": run_id,
            "parent_id": parent_id,
        }
    )
    old = db.scalar(select(BriefPlan).where(BriefPlan.brief_id == brief.id, BriefPlan.plan_hash == key))
    if old:
        return old
    review = review_script(frozen, script)
    if usage is not None:
        review["model_usage"] = usage
    plan = BriefPlan(
        workspace_id=brief.workspace_id,
        brief_id=brief.id,
        brief_revision=frozen["brief_revision"],
        source_digest=digest(frozen),
        plan_hash=key,
        method=method,
        document=script,
        review=review,
        evidence=frozen,
        run_id=run_id,
        parent_id=parent_id,
    )
    db.add(plan)
    db.flush()
    return plan


def manual_plan(db, brief):
    frozen = snapshot(db, brief)
    doc = frozen["document"]
    lines = [line.strip() for line in doc["verbatim_script"].splitlines() if line.strip()]
    frames = doc["duration_sec"] * 30
    if not 1 <= len(lines) <= 12 or any(len(line) > 180 for line in lines) or frames // len(lines) < 15:
        raise DomainError(
            "BRIEF_SCRIPT_INVALID", "原文每个非空行作为一镜：1–12 行、每行最多 180 字，每镜至少半秒", 422
        )
    shots = []
    for i, line in enumerate(lines):
        asset = None
        if doc["visual_mode"] == "screen_demo" or (doc["visual_mode"] == "mixed" and i % 2 == 1):
            asset = doc["asset_ids"][i % len(doc["asset_ids"])]
        shots.append(
            {
                "caption": line,
                "narration": line,
                "visual_note": "按用户原文制作",
                "asset_id": asset,
                "duration_frames": frames // len(lines) + (1 if i < frames % len(lines) else 0),
            }
        )
    return save_plan(
        db, brief, frozen, {"title": doc["topic"], "fact_refs": doc["fact_refs"], "shots": shots}, "user_text"
    )


def assert_current(db, brief, plan):
    if (
        plan.brief_id != brief.id
        or brief.revision != plan.brief_revision
        or digest(snapshot(db, brief)) != plan.source_digest
    ):
        raise DomainError("BRIEF_PLAN_STALE", "要求、事实或素材依据已变化，请基于当前要求重新准备脚本")


def build_video(db, brief, plan, user_id, trace, queue_preview=True):
    from .video import validate_ir
    from .video_edit import checkpoint
    from .quality import build_report

    if plan.video_id:
        return {"video_id": plan.video_id, "plan_id": plan.id, "already_created": True}
    assert_current(db, brief, plan)
    review = review_script(plan.evidence, plan.document)
    if review["issues"]:
        raise DomainError("BRIEF_SCRIPT_INVALID", "请先修正脚本中未满足的时长、文字、事实或素材要求", 422)
    doc = brief.document
    width, height = {"wide": (1920, 1080), "portrait": (1080, 1920), "square": (1080, 1080)}[doc["size"]]
    ir = {
        "schema_version": "1.1",
        **VideoInput(
            brand_id=brief.brand_id,
            name=plan.document["title"][:120],
            width=width,
            height=height,
            preview_required=True,
            shots=[
                {
                    "shot_id": "s" + str(i + 1),
                    "provider": "ffmpeg_media" if s["asset_id"] else "pillow_mg",
                    "kind": ("screen_demo" if doc["visual_mode"] == "screen_demo" else "montage")
                    if s["asset_id"]
                    else "motion_graphics",
                    "duration_frames": s["duration_frames"],
                    "caption": s["caption"],
                    "asset_id": s["asset_id"],
                }
                for i, s in enumerate(plan.document["shots"])
            ],
        ).model_dump(),
        "creation_brief": {
            "brief_id": brief.id,
            "brief_revision": brief.revision,
            "plan_id": plan.id,
            "script": plan.document,
            "input_digest": plan.source_digest,
            "user_confirmed_script": True,
        },
    }
    validate_ir(db, brief.workspace_id, ir)
    if plan.run_id:
        ir["source_run_id"] = plan.run_id
    video = Video(
        workspace_id=brief.workspace_id,
        brand_id=brief.brand_id,
        name=ir["name"],
        ir=ir,
        preview_required=True,
        status="queued",
    )
    db.add(video)
    db.flush()
    checkpoint(db, video, user_id)
    build_report(db, "video", video)
    job = RenderJob(
        workspace_id=brief.workspace_id,
        video_id=video.id,
        revision=video.revision,
        ir=ir,
        purpose="preview",
        trace_id=trace,
    )
    if queue_preview:
        db.add(job)
    plan.video_id = video.id
    db.flush()
    return {"video_id": video.id, "plan_id": plan.id, "render_job_id": job.id if queue_preview else None, "already_created": False}


def private_summary(run):
    row = serialize(run)
    row.pop("input_snapshot", None)
    return row
