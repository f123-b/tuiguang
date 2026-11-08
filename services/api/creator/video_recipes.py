"""Local production recipes compile user-authored scenes into the existing Shot IR."""

from typing import Annotated, Literal

from pydantic import Field
from sqlalchemy.exc import IntegrityError

from .domains import digest, owned
from .errors import DomainError
from .models import Asset, Brand, RenderJob, Video
from .narration import NarrationOptions, NarrationRequest
from .schemas import DTO, FrameCrop, Presentation, Short, VideoInput

VERSION = "video_recipes@1"
Mode = Literal["mg", "screen_demo", "montage", "illustrated", "mixed"]
RecipeID = Literal["feature", "qa", "tutorial", "story", "release", "brand"]
RECIPES = [
    {"id": "feature", "name": "功能讲解", "roles": ["具体问题", "功能原理", "真实示例", "下一步"]},
    {"id": "qa", "name": "用户问答", "roles": ["观众提问", "直接回答", "依据与边界", "动手验证"]},
    {"id": "tutorial", "name": "操作教程", "roles": ["目标与准备", "第一步", "第二步", "结果与检查"]},
    {"id": "story", "name": "品牌故事", "roles": ["遇到的问题", "当时的选择", "行动与变化", "回到观众"]},
    {"id": "release", "name": "版本更新", "roles": ["版本与来源", "本次变化", "界面证据", "限制与升级提示"]},
    {"id": "brand", "name": "品牌形象", "roles": ["核心主张", "使用情境", "产品依据", "品牌落点"]},
]
MODES = [
    {"id": "mg", "name": "MG 图解", "description": "流程节点、步骤与动态文字，不需要素材", "available": True},
    {
        "id": "screen_demo",
        "name": "录屏教程",
        "description": "逐镜选录屏或截图，完整保留界面比例",
        "available": True,
    },
    {
        "id": "montage",
        "name": "素材混剪",
        "description": "全画幅素材、独立入点与旁白，不伪装成产品实录",
        "available": True,
    },
    {
        "id": "illustrated",
        "name": "插画故事",
        "description": "授权插画、分镜框与气泡；不生成角色表演",
        "available": True,
    },
    {"id": "mixed", "name": "混合制作", "description": "同片组合图解、实录、实拍和插画", "available": True},
    {
        "id": "generative",
        "name": "AI 动态场景生成",
        "description": "服务未接入；已有授权生成素材可导入混剪",
        "available": False,
    },
    {
        "id": "three_d",
        "name": "3D / CG 渲染",
        "description": "三维引擎未接入；已有渲染片段可导入混剪",
        "available": False,
    },
]


class RecipeScene(DTO):
    headline: str = Field(min_length=1, max_length=80)
    narration: str = Field(default="", max_length=600)
    supporting: str = Field(default="", max_length=240)
    points: list[Annotated[str, Field(min_length=1, max_length=90)]] = Field(
        default_factory=list, max_length=3
    )
    duration_frames: int = Field(default=150, ge=15, le=1800)
    asset_id: Short | None = None
    trim_start_frame: int = Field(default=0, ge=0, le=216000)
    motion: Literal["still", "push", "pan"] = "push"
    treatment: Literal["auto", "screen", "montage", "comic", "diagram"] = "auto"
    crop: FrameCrop = Field(default_factory=FrameCrop)


class RecipeInput(DTO):
    brand_id: Short
    name: Short
    recipe_id: RecipeID = "feature"
    mode: Mode = "mg"
    size: Literal["wide", "portrait", "square"] = "wide"
    scenes: list[RecipeScene] = Field(min_length=1, max_length=12)
    presentation: Presentation = Field(default_factory=lambda: Presentation(style="studio"))
    narration: NarrationOptions | None = None


def catalog():
    import shutil

    ready = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
    return {
        "version": VERSION,
        "recipes": RECIPES,
        "modes": [{**m, "available": m["available"] and ready} for m in MODES],
        "cost": "本地合成无外部接口调用；素材、声音和硬件使用权须自行核实",
        "requires_preview_review": True,
    }


def compile_recipe(db, workspace, data):
    brand = owned(db, Brand, data.brand_id, workspace)
    selected = [bool(s.asset_id) for s in data.scenes]
    if (
        (data.mode == "mg" and any(selected))
        or (data.mode == "mixed" and (not any(selected) or all(selected)))
        or (data.mode in ("screen_demo", "montage", "illustrated") and not all(selected))
    ):
        raise DomainError(
            "VID_RECIPE_ASSETS_REQUIRED", "MG 只用图解；素材形式逐镜选素材；混合形式须同时有图解和素材", 422
        )
    roles = next(r["roles"] for r in RECIPES if r["id"] == data.recipe_id)
    shots = []
    for index, scene in enumerate(data.scenes):
        if scene.asset_id:
            asset = owned(db, Asset, scene.asset_id, workspace)
            if asset.brand_id != brand.id or not asset.verified or asset.applicability_status != "current":
                raise DomainError("ASSET_LICENSE_UNVERIFIED", "请先核实本品牌当前有效的素材与许可", 422)
            if data.mode == "illustrated" and asset.kind != "image":
                raise DomainError("VID_RECIPE_ASSET_KIND", "插画故事需要图片；实拍或录屏视频请选择混剪", 422)
        layout = {"screen_demo": "screen", "montage": "montage", "illustrated": "comic"}.get(data.mode)
        if data.mode == "mixed":
            layout = "montage" if scene.asset_id else "diagram"
            if scene.treatment != "auto":
                layout = scene.treatment
        if not layout:
            layout = (
                "diagram"
                if scene.points or data.recipe_id == "tutorial"
                else ("closing" if index == len(data.scenes) - 1 else "hero")
            )
        if layout == "comic" and scene.asset_id and asset.kind != "image":
            raise DomainError("VID_RECIPE_ASSET_KIND", "插画分镜需要图片素材", 422)
        shots.append(
            {
                "shot_id": f"s{index + 1}",
                "provider": "ffmpeg_media" if scene.asset_id else "pillow_mg",
                "kind": "screen_demo"
                if layout in ("screen", "focus")
                else "montage"
                if scene.asset_id
                else "motion_graphics",
                "duration_frames": scene.duration_frames,
                "caption": scene.headline,
                "narration_text": scene.narration,
                "asset_id": scene.asset_id,
                "trim_start_frame": scene.trim_start_frame,
                "design": {
                    "layout": layout,
                    "motion": scene.motion,
                    "headline": scene.headline,
                    "supporting": scene.supporting,
                    "points": scene.points,
                    "kicker": roles[min(index, len(roles) - 1)],
                    "crop": scene.crop.model_dump(),
                },
            }
        )
    width, height = {"wide": (1920, 1080), "portrait": (1080, 1920), "square": (1080, 1080)}[data.size]
    presentation = data.presentation.model_dump()
    # Recipes require their type-specific layouts; the legacy route retains classic mode.
    presentation.update(style="studio", brand_label=presentation["brand_label"] or brand.name[:40])
    return {
        "schema_version": "1.1",
        **VideoInput(
            brand_id=brand.id,
            name=data.name,
            width=width,
            height=height,
            shots=shots,
            preview_required=True,
            presentation=presentation,
        ).model_dump(),
    }


def create_from_recipe(db, user, data, key, trace):
    from .narration import enqueue
    from .observability import record
    from .video import validate_ir
    from .video_edit import checkpoint

    owned(db, Brand, data.brand_id, user.workspace_id)
    identifier = digest({"workspace": user.workspace_id, "recipe_request_key": key})[:32]
    request_digest = digest(data.model_dump())

    def existing():
        video = owned(db, Video, identifier, user.workspace_id)
        if video.ir.get("production_recipe", {}).get("request_digest") != request_digest:
            raise DomainError("VID_RECIPE_KEY_CONFLICT", "同一制作请求已用于不同内容，请重新提交新请求", 409)
        return video

    if db.get(Video, identifier):
        return existing()
    ir = compile_recipe(db, user.workspace_id, data)
    validate_ir(db, user.workspace_id, ir)
    ir["production_recipe"] = {
        "version": VERSION,
        "recipe_id": data.recipe_id,
        "mode": data.mode,
        "request_digest": request_digest,
        "scope": "creation_provenance",
    }
    video = Video(
        id=identifier,
        workspace_id=user.workspace_id,
        brand_id=data.brand_id,
        name=data.name,
        ir=ir,
        preview_required=True,
        status="queued",
    )
    db.add(video)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return existing()
    checkpoint(db, video, user.id)
    if data.narration:
        enqueue(
            db,
            video,
            NarrationRequest(
                **data.narration.model_dump(),
                expected_revision=1,
                lines=[
                    {"shot_id": s["shot_id"], "text": s["narration_text"] or s["caption"]}
                    for s in ir["shots"]
                ],
            ),
            "recipe-voice:" + identifier,
            user.id,
            trace,
        )
    else:
        job = RenderJob(
            workspace_id=user.workspace_id,
            video_id=video.id,
            revision=1,
            ir=ir,
            purpose="preview",
            trace_id=trace,
        )
        db.add(job)
        db.flush()
        record(
            db,
            user.workspace_id,
            trace,
            "video.recipe",
            "ok",
            video_project_id=video.id,
            render_job_id=job.id,
            revision=1,
        )
    db.commit()
    return video
