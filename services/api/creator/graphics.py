"""Versioned, local graphic cards. Preview and export share the same image files."""

import io
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError
from pydantic import Field, ValidationError, model_validator
from sqlalchemy import update

from .domains import digest, file_path, font, owned, serialize, store_file
from .errors import DomainError
from .models import Asset, Brand, Content, Creator, uid
from .schemas import DTO, Short

SIZES = {"portrait": (1080, 1440), "square": (1080, 1080), "landscape": (1920, 1080)}
THEMES = {
    "midnight": ("#101923", "#ecf1f5", "#9cabbc", "#8cdbc4", "#213b39"),
    "paper": ("#f6f1e8", "#202a34", "#5b6874", "#245bcb", "#e4e8ed"),
    "sage": ("#e8eeea", "#19372e", "#50665c", "#236850", "#d5e1d8"),
}


class GraphicPage(DTO):
    page_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    template: Literal["editorial", "checklist", "screenshot"] = "editorial"
    heading: str = Field(default="", max_length=180)
    text: str = Field(default="", max_length=600)
    asset_id: Short | None = None

    @model_validator(mode="after")
    def image_reference(self):
        if (self.template == "screenshot") != bool(self.asset_id):
            raise ValueError("截图版式须选择图片，其他版式不绑定图片")
        return self


class GraphicDocument(DTO):
    schema_version: Literal["1.0"] = "1.0"
    renderer_version: Literal["graphic_cards@1"] = "graphic_cards@1"
    size: Literal["portrait", "square", "landscape"] = "portrait"
    theme: Literal["midnight", "paper", "sage"] = "midnight"
    pages: list[GraphicPage] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def unique_pages(self):
        if len({p.page_id for p in self.pages}) != len(self.pages):
            raise ValueError("每一页需要唯一标识")
        return self


class GraphicSave(DTO):
    expected_revision: int = Field(ge=1)
    document: GraphicDocument


class GraphicRender(DTO):
    expected_revision: int = Field(ge=1)


def load_document(value):
    try:
        return GraphicDocument.model_validate(value)
    except ValidationError:
        raise DomainError("GRAPHIC_SCHEMA_INVALID", "图文工程版本或字段无效，请重新保存", 422) from None


def lock_content(db, content, expected_revision=None):
    db.execute(update(Content).where(Content.id == content.id).values(revision=Content.revision))
    db.refresh(content)
    if expected_revision is not None and content.revision != expected_revision:
        raise DomainError("CONTENT_REVISION_CONFLICT", "内容已被更新，请刷新后再保存或生成预览")


def validate_graphics(db, content, document):
    creator = db.get(Creator, content.creator_id)
    brand = db.get(Brand, creator.brand_id)
    db.refresh(brand)
    verified = {f["id"]: f for f in brand.facts if f["verified"]}
    if not content.fact_refs or not set(content.fact_refs) <= verified.keys():
        raise DomainError("GRAPHIC_FACTS_STALE", "引用事实已失效，请先依据当前事实重新准备内容")
    assets = {}
    for page in document.pages:
        if page.asset_id:
            asset = owned(db, Asset, page.asset_id, content.workspace_id)
            db.refresh(asset)
            if asset.brand_id != brand.id or not asset.verified or asset.kind != "image":
                raise DomainError("GRAPHIC_ASSET_UNVERIFIED", "仅能使用本品牌已核实来源与授权的图片")
            source = file_path(content.workspace_id, asset.sha256, asset.suffix)
            if not source.is_file():
                raise DomainError("GRAPHIC_ASSET_MISSING", "图片文件缺失，请重新上传")
            if source.stat().st_size > 50 * 1024 * 1024 or digest(source.read_bytes()) != asset.sha256:
                raise DomainError(
                    "GRAPHIC_ASSET_INTEGRITY", "图片文件与已核实的哈希不一致，请核对来源并重新上传"
                )
            assets[page.asset_id] = asset
    return brand, [verified[ref] for ref in dict.fromkeys(content.fact_refs)], assets


def font_receipt():
    face = font(24)
    path = getattr(face, "path", None)
    return {
        "name": list(face.getname()),
        "sha256": digest(Path(path).read_bytes()) if path and Path(path).is_file() else "pillow-default",
    }


def render_key(content, document, brand, assets, face):
    return digest(
        {
            "document": document.model_dump(),
            "content_revision": content.revision,
            "title": content.title,
            "brand_name": brand.name,
            "brand_revision": brand.revision,
            "facts": brand.facts,
            "assets": {key: serialize(asset) for key, asset in assets.items()},
            "font": face,
        }
    )


def valid_receipt(content, key):
    receipt = content.graphics_render
    if not receipt or receipt.get("cache_key") != key or receipt.get("content_revision") != content.revision:
        return False
    for page in receipt["pages"]:
        for suffix in ("png", "jpg"):
            target = file_path(content.workspace_id, page[suffix + "_sha256"], "." + suffix)
            if not target.is_file() or digest(target.read_bytes()) != page[suffix + "_sha256"]:
                return False
    return True


def current_receipt(db, content):
    document = load_document(content.graphics)
    brand, _, assets = validate_graphics(db, content, document)
    key = render_key(content, document, brand, assets, font_receipt())
    if not valid_receipt(content, key):
        raise DomainError("GRAPHIC_RENDER_STALE", "请先生成当前版本的真实预览，再人工审核和导出")
    return content.graphics_render


def wrap_text(draw, text, face, width):
    lines, line = [], ""
    for char in text:
        if char == "\n":
            lines.append(line)
            line = ""
        elif line and draw.textlength(line + char, font=face) > width:
            lines.append(line)
            line = char
        else:
            line += char
    lines.append(line)
    return lines


def draw_fit(draw, text, box, maximum, minimum, fill):
    x, y, right, bottom = box
    for size in range(maximum, minimum - 1, -2):
        face = font(size)
        lines = wrap_text(draw, text, face, right - x)
        step = round(size * 1.42)
        if len(lines) * step <= bottom - y and all(
            draw.textlength(line, font=face) <= right - x for line in lines
        ):
            for index, line in enumerate(lines):
                draw.text((x, y + index * step), line, font=face, fill=fill)
            return {"font_size": size, "line_count": len(lines), "box": list(box)}
    raise DomainError("GRAPHIC_TEXT_OVERFLOW", "文字在当前版式中放不下，请减少文字、增加页数或调整尺寸", 422)


def draw_page(content, document, page, index, brand, facts, assets):
    width, height = SIZES[document.size]
    bg, ink, muted, accent, panel = THEMES[document.theme]
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    margin = 76 if width == 1080 else 112
    right = width - margin
    heading = page.heading or content.title
    draw.rounded_rectangle((margin, 76, margin + 258, 135), radius=28, fill=panel)
    draw.text(
        (margin + 26, 86),
        {"editorial": "产品创作笔记", "checklist": "事实与来源", "screenshot": "授权素材记录"}[page.template],
        font=font(28),
        fill=accent,
    )
    draw.text((right - 85, 90), f"{index + 1:02d} / {len(document.pages):02d}", font=font(22), fill=muted)
    title_bottom = int(height * (0.48 if page.template == "editorial" else 0.34))
    layout = {
        "heading": draw_fit(
            draw,
            heading,
            (margin, 208, right, title_bottom),
            76 if page.template == "editorial" else 60,
            24,
            ink,
        )
    }
    body_top, body_bottom = title_bottom + 35, height - 195
    if page.template == "editorial":
        draw.rectangle((margin, title_bottom + 8, margin + 90, title_bottom + 15), fill=accent)
        if page.text:
            layout["text"] = draw_fit(
                draw, page.text, (margin, body_top + 28, right, body_bottom), 40, 22, muted
            )
    elif page.template == "checklist":
        evidence = "\n\n".join(f"{i + 1:02d}  {fact['claim']}" for i, fact in enumerate(facts))
        text = (page.text + "\n\n" if page.text else "") + evidence
        layout["text"] = draw_fit(draw, text, (margin, body_top, right, body_bottom), 38, 20, ink)
    else:
        asset = assets[page.asset_id]
        if page.text:
            layout["text"] = draw_fit(
                draw, page.text, (margin, body_top, right, body_top + 116), 30, 20, muted
            )
            body_top += 136
        try:
            with Image.open(file_path(content.workspace_id, asset.sha256, asset.suffix)) as source:
                if source.width * source.height > 30_000_000:
                    raise ValueError("size")
                source = ImageOps.exif_transpose(source).convert("RGB")
                fitted = ImageOps.contain(
                    source, (right - margin - 28, body_bottom - body_top - 28), Image.Resampling.LANCZOS
                )
                x, y = (
                    margin + (right - margin - fitted.width) // 2,
                    body_top + (body_bottom - body_top - fitted.height) // 2,
                )
                draw.rounded_rectangle((margin, body_top, right, body_bottom), radius=20, fill=panel)
                image.paste(fitted, (x, y))
                layout["image_rect"] = [x, y, x + fitted.width, y + fitted.height]
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            raise DomainError("GRAPHIC_ASSET_INVALID", "图片无法读取，请重新上传有效图片", 422) from None
    draw.line((margin, height - 148, right, height - 148), fill=panel, width=2)
    draw_fit(draw, brand.name, (margin, height - 124, right - 70, height - 70), 28, 18, ink)
    draw.text((margin, height - 58), "AI 辅助制作 · 发布前核对事实、授权与标识", font=font(22), fill=muted)
    return image, heading, layout


def store_image(content, data, suffix):
    sha = store_file(content.workspace_id, data, suffix)
    target = file_path(content.workspace_id, sha, suffix)
    if digest(target.read_bytes()) != sha:
        tmp = target.with_suffix(".repair-" + uid())
        tmp.write_bytes(data)
        tmp.replace(target)
    return sha


def render_graphics(db, content):
    document = load_document(content.graphics)
    brand, facts, assets = validate_graphics(db, content, document)
    face = font_receipt()
    key = render_key(content, document, brand, assets, face)
    if valid_receipt(content, key):
        return {**content.graphics_render, "cached": True}
    if content.approved_revision == content.revision:
        raise DomainError("GRAPHIC_RENDER_STALE", "审核后的渲染依据已变化，请重新保存、预览并审核")
    pages = []
    for index, page in enumerate(document.pages):
        image, heading, layout = draw_page(content, document, page, index, brand, facts, assets)
        entry = {
            "page_id": page.page_id,
            "template": page.template,
            "heading": heading,
            "width": image.width,
            "height": image.height,
            "layout": layout,
            "asset": None,
        }
        for fmt, suffix in (("PNG", ".png"), ("JPEG", ".jpg")):
            buffer = io.BytesIO()
            image.save(buffer, fmt, **({"quality": 94, "subsampling": 0} if fmt == "JPEG" else {}))
            entry[suffix[1:] + "_sha256"] = store_image(content, buffer.getvalue(), suffix)
        if page.asset_id:
            asset = assets[page.asset_id]
            entry["asset"] = {
                k: getattr(asset, k) for k in ("id", "sha256", "source", "license_note", "verified")
            }
        pages.append(entry)
    receipt = {
        "schema_version": "1.0",
        "renderer_version": "graphic_cards@1",
        "content_revision": content.revision,
        "cache_key": key,
        "font": face,
        "brand_revision": brand.revision,
        "pages": pages,
    }
    content.graphics_render = receipt
    return {**receipt, "cached": False}
