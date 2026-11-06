"""Measured checks with immutable provenance; semantic judgments stay uncertain."""

import re
from difflib import SequenceMatcher

from sqlalchemy import select

from .domains import digest, owned, serialize
from .errors import DomainError
from .models import Asset, Brand, Content, Creator, QualityReport, QualityReview, RenderJob, Video

VERSION = "creative_quality@1"


def subject(db, kind, identifier, workspace):
    return owned(db, Content if kind == "content" else Video, identifier, workspace)


def snapshot(db, kind, item):
    creator = db.get(Creator, item.creator_id) if kind == "content" else None
    brand = db.get(Brand, creator.brand_id if creator else item.brand_id)
    # SessionLocal keeps identities after commit; external calls can span edits.
    db.refresh(brand)
    peers = db.scalars(
        select(Content)
        .join(Creator)
        .where(
            Creator.brand_id == brand.id,
            Content.id != item.id,
            Content.workspace_id == item.workspace_id,
        )
        .order_by(Content.created_at.desc(), Content.id)
        .limit(30)
        .execution_options(populate_existing=True)
    ).all()
    titles = [{"id": c.id, "revision": c.revision, "title": c.title} for c in peers]
    ir = item.ir if kind == "video" else {}
    body = "\n".join(s.get("caption", "") for s in ir["shots"]) if kind == "video" else item.body
    if kind == "content":
        body += "\n" + "\n".join(v["title"] + "\n" + v["body"] for v in (item.variants or {}).values())
        body += "\n" + "\n".join(
            p.get("heading", "") + "\n" + p.get("text", "") for p in (item.graphics or {}).get("pages", [])
        )
    asset_ids = {s.get("asset_id") for s in ir.get("shots", []) + ir.get("audio_tracks", [])} - {None}
    assets = []
    for identifier in sorted(asset_ids):
        asset = owned(db, Asset, identifier, item.workspace_id)
        db.refresh(asset)
        assets.append(serialize(asset))
    videos = (
        db.scalars(
            select(Video)
            .where(Video.brand_id == brand.id, Video.id != item.id, Video.workspace_id == item.workspace_id)
            .order_by(Video.created_at.desc(), Video.id)
            .limit(10)
            .execution_options(populate_existing=True)
        ).all()
        if kind == "video"
        else []
    )
    return {
        "version": VERSION,
        "subject_type": kind,
        "id": item.id,
        "revision": item.revision,
        "brand": {
            "id": brand.id,
            "name": brand.name,
            "revision": brand.revision,
            "audience": brand.audience,
            "facts": brand.facts,
        },
        "title": item.title if kind == "content" else item.name,
        "body": body,
        "fact_refs": item.fact_refs if kind == "content" else [],
        "ir": ir,
        "assets": assets,
        "titles": titles,
        "shot_history": [
            {
                "id": v.id,
                "revision": v.revision,
                "pattern": [(s["provider"], s["kind"], s.get("asset_id")) for s in v.ir["shots"]],
            }
            for v in videos
        ],
    }


def measure(frozen):
    checks = []

    def add(key, label, status, evidence):
        checks.append({"key": key, "label": label, "status": status, "evidence": evidence})

    title, body = frozen["title"], frozen["body"]
    add(
        "opening",
        "开场长度",
        "pass" if 4 <= len(title) <= 40 else "needs_review",
        {"characters": len(title), "rule": "标题 4–40 字为长度提示，吸引力需人工判断"},
    )
    verified = {f["id"] for f in frozen["brand"]["facts"] if f["verified"]}
    refs = set(frozen["fact_refs"])
    add(
        "facts",
        "已核实事实引用",
        "blocked" if refs - verified else ("pass" if refs else "unknown"),
        {
            "refs": sorted(refs),
            "invalid_refs": sorted(refs - verified),
            "limit": "引用有效不代表所有句子已核实",
        },
    )
    risky = re.findall(r"世界第一|保证.{0,8}成功|100[%％]|保证不封号|绝对安全|虚构好评", title + body)
    add("claims", "绝对化声明", "blocked" if risky else "pass", {"matches": risky})
    advertising = re.findall(r"限时|立即购买|错过|闭眼入|必买|颠覆|神器", title + body)
    add("advertising", "广告表达提示", "needs_review" if advertising else "pass", {"matches": advertising})

    def normalize(value):
        return re.sub(r"\W", "", value.replace(frozen["brand"]["name"], "")).casefold()

    normalized = normalize(title)
    matches = [
        {**t, "similarity": round(SequenceMatcher(None, normalized, normalize(t["title"])).ratio(), 3)}
        for t in frozen["titles"]
        if normalized and normalize(t["title"])
    ]
    matches = [t for t in matches if t["similarity"] >= 0.88]
    add(
        "duplicates",
        "近 30 条标题相似度",
        "needs_review" if matches else "pass",
        {
            "matches": matches,
            "compared": len(frozen["titles"]),
            "threshold": 0.88,
            "limit": "字面相似提示，不能判定语义重复",
        },
    )
    if frozen["subject_type"] == "video":
        pattern = [(s["provider"], s["kind"], s.get("asset_id")) for s in frozen["ir"]["shots"]]
        repeats = [v["id"] for v in frozen["shot_history"] if v["pattern"] == pattern]
        add(
            "shots",
            "近 10 条镜头结构",
            "needs_review" if repeats else "pass",
            {"same_structure": repeats, "limit": "仅比较引擎、镜头类型和素材，需播放确认视觉重复"},
        )
        bad = [
            a["id"] for a in frozen["assets"] if not a["verified"] or a["applicability_status"] != "current"
        ]
        add("assets", "素材授权与版本", "blocked" if bad else "pass", {"invalid_assets": bad})
    for key, label in (("focus", "单一收益点"), ("audience", "受众价值"), ("purpose", "表达目的与行动引导")):
        add(
            key,
            label,
            "unknown",
            {"audience": frozen["brand"]["audience"], "limit": "需要人工语义判断；可单独授权模型提供建议"},
        )
    return {
        "version": VERSION,
        "method": "rules",
        "checks": checks,
        "decision": "blocked" if any(c["status"] == "blocked" for c in checks) else "human_review",
        "limits": [
            "不预测流量，不证明内容质量或平台偏好。",
            "人工负责核对事实、单一主题、真实画面和表达目的。",
        ],
    }


def build_report(db, kind, item):
    frozen = snapshot(db, kind, item)
    sha = digest(frozen)
    existing = db.scalar(
        select(QualityReport).where(
            QualityReport.workspace_id == item.workspace_id,
            QualityReport.subject_type == kind,
            QualityReport.subject_id == item.id,
            QualityReport.source_digest == sha,
        )
    )
    if existing:
        return existing
    row = QualityReport(
        workspace_id=item.workspace_id,
        subject_type=kind,
        subject_id=item.id,
        subject_revision=item.revision,
        source_digest=sha,
        report={**measure(frozen), "evidence": frozen},
    )
    db.add(row)
    db.flush()
    return row


def preview_file(db, video, job=None):
    from .config import DATA_DIR
    from .video import validate_ir

    validate_ir(db, video.workspace_id, video.ir)
    job = job or db.scalar(
        select(RenderJob)
        .where(
            RenderJob.video_id == video.id,
            RenderJob.revision == video.revision,
            RenderJob.purpose == "preview",
            RenderJob.status == "completed",
        )
        .order_by(RenderJob.created_at.desc(), RenderJob.id)
    )
    if (
        not job
        or job.video_id != video.id
        or job.revision != video.revision
        or job.purpose != "preview"
        or job.status != "completed"
        or digest(job.ir) != digest(video.ir)
    ):
        raise DomainError("QUALITY_PREVIEW_REQUIRED", "请先生成并播放当前版本的低清预览")
    sha = job.receipt.get("sha256", "")
    path = DATA_DIR / video.workspace_id / "cache" / (sha + ".mp4")
    if not re.fullmatch(r"[a-f0-9]{64}", sha) or not path.is_file() or digest(path.read_bytes()) != sha:
        raise DomainError("VID_OUTPUT_HASH_MISMATCH", "预览缺失或字节变化，请重新生成")
    return path, job


def require_review(db, video):
    if not video.preview_required:
        return
    frozen = snapshot(db, "video", video)
    if measure(frozen)["decision"] == "blocked":
        raise DomainError("QA_CONTENT_BLOCKED", "质量检查存在硬性阻断项", 422)
    review = db.scalar(
        select(QualityReview)
        .where(QualityReview.video_id == video.id, QualityReview.revision == video.revision)
        .order_by(QualityReview.created_at.desc(), QualityReview.id)
    )
    if not review or review.decision != "accept":
        raise DomainError("QUALITY_REVIEW_REQUIRED", "请核对当前质量报告和低清预览，再记录人工确认")
    report = db.get(QualityReport, review.report_id)

    # Similarity comparisons describe the history at review time; creating or
    # editing another work must not revoke an unchanged reviewed output.
    def binding(evidence):
        return {k: v for k, v in evidence.items() if k not in ("titles", "shot_history")}

    if (
        not report
        or report.workspace_id != video.workspace_id
        or report.subject_type != "video"
        or report.subject_id != video.id
        or report.subject_revision != video.revision
        or report.report.get("method") != "rules"
        or digest(binding(report.report.get("evidence", {}))) != digest(binding(frozen))
    ):
        raise DomainError("QUALITY_REVIEW_REQUIRED", "当前作品、事实或素材依据变化，请重新检查预览并确认")
    preview_file(db, video, db.get(RenderJob, review.preview_job_id))
