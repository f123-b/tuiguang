import hashlib
import io
import json
import re
import zipfile
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select

from .config import DATA_DIR
from .errors import DomainError
from .models import Brand, Content, Creator, Handoff, Metric, uid

PLATFORM_HOSTS = {
    "xiaohongshu": {"www.xiaohongshu.com", "xiaohongshu.com", "xhslink.com"},
    "douyin": {"www.douyin.com", "douyin.com", "v.douyin.com"},
    "bilibili": {"www.bilibili.com", "bilibili.com", "b23.tv"},
}


def owned(db, cls, object_id, workspace_id):
    obj = db.scalar(select(cls).where(cls.id == object_id, cls.workspace_id == workspace_id))
    if obj is None:
        raise DomainError("RESOURCE_NOT_FOUND", "内容不存在或无权访问", 404)
    return obj


def serialize(obj):
    result = {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
    for key in ("workspace_id", "password_hash", "lease_until", "encrypted_key"):
        result.pop(key, None)
    return result


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value).encode()).hexdigest()


def store_file(workspace_id, data, suffix):
    sha = digest(data)
    directory = DATA_DIR / workspace_id / "files"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{sha}{suffix}"
    if not target.exists():
        tmp = target.with_suffix(".tmp-" + uid())
        tmp.write_bytes(data)
        tmp.replace(target)
    return sha


def file_path(workspace_id, sha, suffix):
    return DATA_DIR / workspace_id / "files" / f"{sha}{suffix}"


def font(size):
    from pathlib import Path
    import os

    candidates = [
        os.getenv("CREATOR_FONT", ""),
        "C:/Windows/Fonts/msyh.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


def cover_png(title, brand_name):
    image = Image.new("RGB", (1080, 1440), "#101722")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((64, 65, 360, 132), radius=28, fill="#223a38")
    draw.text((92, 78), "产品创作笔记", font=font(30), fill="#89d3c3")
    lines = [title[i : i + 12] for i in range(0, min(len(title), 60), 12)]
    for index, line in enumerate(lines):
        draw.text((76, 360 + index * 96), line, font=font(64), fill="#f0f3f6")
    draw.line((80, 1050, 1000, 1050), fill="#354254", width=2)
    draw.text((80, 1100), brand_name[:22], font=font(36), fill="#9badbf")
    draw.text((80, 1280), "AI 辅助制作 · 发布前请核对事实与标识", font=font(24), fill="#78899c")
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def compliance_report(db, content):
    creator = db.get(Creator, content.creator_id)
    brand = db.get(Brand, creator.brand_id)
    verified = {f["id"] for f in brand.facts if f["verified"]}
    issues = []
    text = content.title + "\n" + content.body
    for variant in (content.variants or {}).values():
        text += "\n" + variant["title"] + "\n" + variant["body"] + "\n" + " ".join(variant.get("tags", []))
    if content.video_attachment:
        from .video_edit import attachment
        try:
            attachment(db, content)
        except DomainError as error:
            issues.append({"level":"blocked","message":error.message,"code":error.code})
    if content.graphics:
        from .graphics import current_receipt, load_document

        try:
            document = load_document(content.graphics)
            text += "\n" + "\n".join(p.heading + "\n" + p.text for p in document.pages)
            current_receipt(db, content)
        except DomainError as error:
            issues.append({"level": "blocked", "message": error.message, "code": error.code})
    if re.search(r"世界第一|保证.{0,8}成功|100[%％]|保证不封号|绝对安全|虚构好评", text):
        issues.append({"level": "blocked", "message": "含无法证实的绝对化承诺，请修改"})
    if not content.fact_refs or not set(content.fact_refs) <= verified:
        issues.append({"level": "blocked", "message": "引用事实缺失或已失效，请重新生成"})
    issues.append({"level": "human_review", "message": "请人工复核事实、素材授权、AI 标识及平台最新要求"})
    return {
        "status": "blocked" if any(i["level"] == "blocked" for i in issues) else "needs_human_review",
        "rule_version": "internal_precheck@1",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "issues": issues,
        "platform_verification": False,
    }


def make_handoff(db, content):
    from .graphics import current_receipt, lock_content

    lock_content(db, content)
    if content.approved_revision != content.revision or compliance_report(db, content)["status"] == "blocked":
        raise DomainError("QA_CONTENT_BLOCKED", "请先完成内容预审和人工审核")
    existing = db.scalar(
        select(Handoff).where(Handoff.content_id == content.id, Handoff.content_revision == content.revision)
    )
    if existing:
        return existing
    creator = db.get(Creator, content.creator_id)
    brand = db.get(Brand, creator.brand_id)
    provenance = {
        "content_id": content.id,
        "revision": content.revision,
        "brand_revision": brand.revision,
        "generation_source": content.generation_source,
        "facts": [f for f in brand.facts if f["id"] in content.fact_refs],
        "manual_publish_only": True,
        "ai_marking_review_required": True,
    }
    snapshot = {
        "title": content.title,
        "body": content.body,
        "platform": content.platform,
        "revision": content.revision,
    }
    output = io.BytesIO()
    graphics = current_receipt(db, content) if content.graphics else None
    if graphics:
        provenance["graphics"] = graphics
        snapshot["graphics"] = {"document": content.graphics, "render": graphics}
    from .video_edit import attachment, subtitles_srt
    bound_video = attachment(db, content)
    if bound_video:
        provenance["video"] = {"binding": content.video_attachment, "receipt": bound_video[2]}
        snapshot["video"] = content.video_attachment
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        if bound_video:
            video, path, receipt = bound_video
            z.write(path, "video.mp4")
            z.writestr("video-project.json", json.dumps(video.ir, ensure_ascii=False, indent=2))
            z.writestr("subtitles.srt", subtitles_srt(video.ir))
        z.writestr("copy.txt", content.title + "\n\n" + content.body)
        for platform, variant in (content.variants or {}).items():
            z.writestr(f"variants/{platform}.txt", variant["title"] + "\n\n" + variant["body"] + "\n\n" + " ".join(variant.get("tags", [])))
        if graphics:
            for index, page in enumerate(graphics["pages"]):
                for suffix in ("png", "jpg"):
                    data = file_path(
                        content.workspace_id, page[suffix + "_sha256"], "." + suffix
                    ).read_bytes()
                    z.writestr(f"images/{index + 1:02d}.{suffix}", data)
                    if index == 0 and suffix == "png":
                        z.writestr("cover.png", data)
            z.writestr(
                "graphics-project.json",
                json.dumps(
                    {"document": content.graphics, "content_revision": content.revision},
                    ensure_ascii=False,
                    indent=2,
                ),
            )
        else:
            z.writestr("cover.png", cover_png(content.title, brand.name))
        z.writestr("provenance.json", json.dumps(provenance, ensure_ascii=False, indent=2))
        z.writestr(
            "checklist.md",
            "# 人工发布检查清单\n\n- [ ] 产品事实准确\n- [ ] 素材和字体有使用权\n"
            "- [ ] 已检查平台当前规则\n- [ ] 已按要求声明 AI 内容\n- [ ] 我已在官方平台亲自上传发布\n\n"
            "内部预审不代表平台批准。登记结果为用户自报，未经平台核验。\n",
        )
    sha = store_file(content.workspace_id, output.getvalue(), ".zip")
    package = Handoff(
        workspace_id=content.workspace_id,
        content_id=content.id,
        content_revision=content.revision,
        sha256=sha,
        platform=content.platform,
        snapshot=snapshot,
    )
    db.add(package)
    content.status = "awaiting_manual_publication"
    db.commit()
    return package


def valid_publication_url(url, platform):
    if not url:
        return
    try:
        parts = urlsplit(url)
        valid = (
            parts.scheme == "https"
            and parts.hostname in PLATFORM_HOSTS[platform]
            and parts.username is None
            and parts.password is None
            and parts.port in (None, 443)
        )
    except ValueError:
        valid = False
    if not valid:
        raise DomainError("HANDOFF_URL_INVALID", "请填写所选平台的 HTTPS 作品链接，或留空", 422)


def parse_metric_rows(db, workspace_id, rows, source):
    if not source.strip() or len(source) > 180:
        raise DomainError("METRICS_SOURCE_UNVERIFIED", "请提供真实的数据来源说明", 422)
    if not rows or len(rows) > 5000:
        raise DomainError("METRICS_FORMAT_INVALID", "报表须有 1–5000 行数据", 422)
    result = []
    for number, row in enumerate(rows, 2):
        try:
            content = owned(db, Content, str(row["content_id"]), workspace_id)
            platform = str(row["platform"])
            if platform != content.platform:
                raise ValueError("平台与作品不一致")
            start, end = (
                date.fromisoformat(str(row["period_start"])),
                date.fromisoformat(str(row["period_end"])),
            )
            observed = datetime.fromisoformat(str(row["observed_at"]).replace("Z", "+00:00"))
            if start > end or observed.tzinfo is None or observed.date() < end:
                raise ValueError("时间窗口或观察日期无效")
            values = {}
            for name in ("views", "likes", "saves", "clicks", "conversions"):
                value = row.get(name)
                if value in (None, ""):
                    values[name] = None
                else:
                    if not re.fullmatch(r"\d{1,12}", str(value)):
                        raise ValueError("指标必须是非负整数，缺失请留空")
                    values[name] = int(value)
            if all(value is None for value in values.values()):
                raise ValueError("至少提供一项指标")
            if row.get("content_revision") not in (None,"") and not 1 <= int(row["content_revision"]) <= content.revision:
                raise ValueError("指标版本必须为该作品已有版本；不确定请留空")
            result.append(
                {
                    **({"content_revision":int(row["content_revision"])} if row.get("content_revision") not in (None,"") else {}),
                    "content_id": content.id,
                    "platform": platform,
                    **values,
                    "period_start": start.isoformat(),
                    "period_end": end.isoformat(),
                    "observed_at": observed.astimezone(timezone.utc).isoformat(),
                }
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DomainError("METRICS_FORMAT_INVALID", f"第 {number} 行校验失败：{e}", 422) from None
    return result


def analytics_summary(db, workspace_id):
    metrics = db.scalars(select(Metric).where(Metric.workspace_id == workspace_id, Metric.active.is_(True))).all()
    # Never combine unlike windows/platforms or turn missing observations into zeros.
    groups = {}
    for m in metrics:
        key = (m.platform, m.period_start, m.period_end, m.data_source)
        group = groups.setdefault(
            key,
            {
                "platform": m.platform,
                "period_start": m.period_start,
                "period_end": m.period_end,
                "data_source": m.data_source,
                "snapshots": [],
            },
        )
        group["snapshots"].append(serialize(m))
    return {
        "snapshot_count": len(metrics),
        "groups": list(groups.values()),
        "conclusion": "尚未导入真实数据，无法判断内容效果"
        if not metrics
        else "以下为用户提供的观察值；尚不能证明因果或平台偏好",
    }
