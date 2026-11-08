"""Story-level contracts, continuity checks and controlled production handoff."""

from collections import Counter
from typing import Annotated, Literal

from pydantic import Field
from sqlalchemy import update

from .domains import canonical, digest, owned, serialize, verified_file
from .drama_skills import registry, validate_script
from .errors import DomainError
from .models import Asset, Brand, DramaProject, VideoGenerationJob, now_iso
from .schemas import DTO, Short

Text = Annotated[str, Field(min_length=1, max_length=700)]
Position = Literal["left", "center", "right", "offscreen"]


class DramaBrief(DTO):
    brand_id: Short
    title: str = Field(min_length=1, max_length=120)
    story: str = Field(min_length=10, max_length=6000)
    theme: str = Field(min_length=1, max_length=400)
    genre: str = Field(default="职场剧情", min_length=1, max_length=100)
    duration_sec: int = Field(default=30, ge=10, le=60)
    style: Literal["realistic", "anime"] = "realistic"
    size: Literal["wide", "portrait"] = "wide"
    fact_refs: list[Short] = Field(default_factory=list, max_length=20)
    rights_confirmed: Literal[True]


class Character(DTO):
    id: str = Field(pattern=r"^C\d{2}$")
    name: Short
    goal: Text
    flaw: Text
    appearance: Text
    voice_hint: Text


class Scene(DTO):
    id: str = Field(pattern=r"^S\d{2}$")
    name: Short
    description: Text
    lighting: Text
    axis: Text
    palette: Text


class Beat(DTO):
    id: Short
    cause_id: Short | None = None
    character_id: Short
    role: Literal["hook", "setup", "choice", "payoff", "cliff"]
    action: Text
    obstacle: Text
    result: Text


class DramaShot(DTO):
    id: Short
    beat_id: Short
    scene_id: Short
    character_ids: list[Short] = Field(max_length=3)
    action: Text
    frame_prompt: Text
    motion_prompt: Text
    framing: Literal["wide", "medium", "close", "insert"]
    camera: Text
    start_positions: dict[Short, Position]
    end_positions: dict[Short, Position]
    transition_reason: str = Field(default="", max_length=500)
    narration: str = Field(default="", max_length=120)
    delivery: str = Field(default="平静自然", max_length=200)
    frames: Literal[49, 73, 97, 121] = 121
    reference_asset_id: Short | None = None


class DramaPlan(DTO):
    title: str = Field(min_length=1, max_length=120)
    logline: Text
    hook: Text
    characters: list[Character] = Field(min_length=1, max_length=3)
    scenes: list[Scene] = Field(min_length=1, max_length=4)
    beats: list[Beat] = Field(min_length=3, max_length=12)
    shots: list[DramaShot] = Field(min_length=3, max_length=12)
    uncertainties: list[Text] = Field(default_factory=list, max_length=12)


def check_plan(plan, target):
    issues = []

    def add(code, location, message):
        issues.append({"code": code, "location": location, "message": message})

    for key in ("characters", "scenes", "beats", "shots"):
        ids = [p["id"] for p in plan[key]]
        if len(ids) != len(set(ids)):
            add("DRAMA_DUPLICATE_ID", key, "编号必须唯一")
    characters = {c["id"] for c in plan["characters"]}
    scenes = {s["id"] for s in plan["scenes"]}
    beats = {b["id"] for b in plan["beats"]}
    previous = set()
    for i, beat in enumerate(plan["beats"]):
        if (i == 0 and beat["cause_id"] is not None) or (i > 0 and beat["cause_id"] not in previous):
            add("DRAMA_CAUSAL_LINK", beat["id"], "首拍不引用原因；后续节拍必须引用此前节拍，解释行动与后果")
        if beat["character_id"] not in characters:
            add("DRAMA_CHARACTER_UNKNOWN", beat["id"], "动机归属的角色不存在")
        previous.add(beat["id"])
    if (
        plan["beats"][0]["role"] != "hook"
        or not any(b["role"] == "choice" for b in plan["beats"])
        or plan["beats"][-1]["role"] not in ("payoff", "cliff")
    ):
        add("DRAMA_STORY_ARC", "beats", "需要开场钩子、人物选择和收束/悬念")
    claims = Counter(s["beat_id"] for s in plan["shots"])
    if set(claims) != beats or any(v != 1 for v in claims.values()):
        add("DRAMA_BEAT_COVERAGE", "shots", "每个节拍恰好由一镜承载，不可漏拍或重复认领")
    if [s["beat_id"] for s in plan["shots"]] != [b["id"] for b in plan["beats"]]:
        add("DRAMA_BEAT_ORDER", "shots", "镜头必须按节拍顺序展开")
    for i, shot in enumerate(plan["shots"]):
        cid = set(shot["character_ids"])
        if not cid <= characters or shot["scene_id"] not in scenes:
            add("DRAMA_REFERENCE_UNKNOWN", shot["id"], "镜头引用了未定义的角色或场景")
        if set(shot["start_positions"]) != cid or set(shot["end_positions"]) != cid:
            add("DRAMA_BLOCKING_REQUIRED", shot["id"], "每位出镜角色都需起止站位")
        if (
            i
            and plan["shots"][i - 1]["scene_id"] == shot["scene_id"]
            and not shot["transition_reason"].strip()
        ):
            prev = plan["shots"][i - 1]["end_positions"]
            if any(
                prev.get(c) != shot["start_positions"][c]
                for c in prev.keys() & shot["start_positions"].keys()
            ):
                add("DRAMA_CONTINUITY", shot["id"], "同场前镜结束与本镜开场站位冲突；需补过渡动作及理由")
        chars = len("".join(shot["narration"].split()))
        if chars > 35 or chars / 4.5 + 0.4 > shot["frames"] / 24:
            add("DRAMA_LINE_TOO_LONG", shot["id"], "旁白预计说不完，缩短或拆镜；实测配音仍需固定时长复核")
    seconds = sum(s["frames"] for s in plan["shots"]) / 24
    if abs(seconds - target) > target * 0.15:
        add("DRAMA_DURATION", "shots", "镜头总时长需在目标±15%内")
    upstream = validate_script(plan, target)
    for error in upstream["errors"]:
        add("DRAMA_SCRIPT_GATE", "script/" + error["code"], error["message"] + "：" + error["detail"])
    return {
        "status": "needs_revision" if issues else "needs_confirmation",
        "issues": issues,
        "duration_sec": round(seconds, 3),
        "upstream": upstream,
        "human_checks": [
            "行动是否由前一拍的后果推动？人物为什么改变选择？",
            "镜头是否讲出信息变化、反应与结果，而不是复述文案？",
            "角色、道具、视线与场景轴线是否连续？",
            "画面细节、表演和声音是否自然？这些不能由结构检查证明",
        ],
        "art_quality": "unreviewed",
        "lip_sync": "unsupported",
    }


def lock(db, item, revision):
    db.execute(update(DramaProject).where(DramaProject.id == item.id).values(revision=DramaProject.revision))
    db.refresh(item)
    if item.revision != revision:
        raise DomainError("DRAMA_REVISION_CONFLICT", "短剧计划已变化，请刷新再操作", 409)


def evidence(db, item):
    brand = owned(db, Brand, item.brand_id, item.workspace_id)
    db.refresh(brand)
    facts = [f for f in brand.facts if f["id"] in item.document["fact_refs"] and f["verified"]]
    if set(item.document["fact_refs"]) != {f["id"] for f in facts}:
        raise DomainError("DRAMA_FACTS_STALE", "选择的产品事实尚未核实或已撤销", 409)
    return {
        "brief": item.document,
        "revision": item.revision,
        "brand": {"id": brand.id, "name": brand.name, "revision": brand.revision, "facts": facts},
        "skills": registry(),
    }


def save_plan(db, item, plan, actor, run_id=None):
    plan = DramaPlan.model_validate(plan).model_dump()
    if len(canonical(plan).encode()) > 60000:
        raise DomainError("DRAMA_PLAN_TOO_LARGE", "短剧计划超过60KB，请精简场景和镜头说明", 422)
    if item.plan:
        item.history = (
            item.history
            + [
                {
                    "revision": item.revision,
                    "plan": item.plan,
                    "evidence": item.evidence,
                    "confirmation": item.confirmation,
                    "bindings": item.bindings,
                    "run_id": item.run_id,
                }
            ]
        )[-20:]
    item.revision += 1
    item.plan, item.evidence = plan, evidence(db, item)
    item.report = check_plan(plan, item.document["duration_sec"])
    item.confirmation, item.bindings, item.run_id = {}, {}, run_id
    return item


def assert_current(db, item):
    if not item.plan or digest(evidence(db, item)) != digest(item.evidence):
        raise DomainError("DRAMA_PLAN_STALE", "故事、事实或技能已变化，请重新保存并检查计划", 409)


def confirm(db, item, actor, note):
    assert_current(db, item)
    item.report = check_plan(item.plan, item.document["duration_sec"])
    if item.report["issues"]:
        raise DomainError("DRAMA_PLAN_BLOCKED", "计划检查未通过，请按具体位置修订", 409)
    item.confirmation = {
        "revision": item.revision,
        "plan_hash": digest(item.plan),
        "by": actor,
        "note": note,
        "at": now_iso(),
    }


def approved(db, item):
    assert_current(db, item)
    if (
        item.confirmation.get("plan_hash") != digest(item.plan)
        or item.confirmation.get("revision") != item.revision
    ):
        raise DomainError("DRAMA_CONFIRMATION_REQUIRED", "先核对并确认当前故事与分镜", 409)


def shot_request(db, item, shot):
    from PIL import Image
    from .video_generation import GenerationInput

    if not shot["reference_asset_id"]:
        raise DomainError("DRAMA_REFERENCE_REQUIRED", "请为此镜头选择已核实的首帧参考图", 422)
    asset = owned(db, Asset, shot["reference_asset_id"], item.workspace_id)
    if (
        asset.brand_id != item.brand_id
        or not asset.verified
        or asset.kind != "image"
        or asset.applicability_status != "current"
    ):
        raise DomainError("ASSET_LICENSE_UNVERIFIED", "首帧须是本品牌当前已核实图片", 422)
    path = verified_file(asset.workspace_id, asset.sha256, asset.suffix)
    width, height = (1280, 704) if item.document["size"] == "wide" else (704, 1280)
    with Image.open(path) as im:
        if im.width < width or im.height < height or abs(im.width / im.height - width / height) > 0.12:
            raise DomainError(
                "DRAMA_SOURCE_RESOLUTION",
                "首帧原始尺寸或比例不足；请上传对应横/竖构图的高清源图，不能靠导出放大",
                422,
            )
    scene = next(s for s in item.plan["scenes"] if s["id"] == shot["scene_id"])
    cast = [c for c in item.plan["characters"] if c["id"] in shot["character_ids"]]
    prompt = "；".join(
        [
            scene["description"],
            scene["lighting"],
            scene["axis"],
            scene["palette"],
            *[c["appearance"] for c in cast],
            shot["frame_prompt"],
            shot["action"],
            shot["motion_prompt"],
            shot["camera"],
            "站位" + str(shot["start_positions"]) + "到" + str(shot["end_positions"]),
            "保持身份、服装、道具和背景连续。自然克制动作，无口型要求。",
        ]
    )
    if len(prompt) > 1600:
        raise DomainError(
            "DRAMA_PROMPT_TOO_LONG", "本镜头的场景、角色和动作说明合计超过1600字，请精简后重新保存确认", 422
        )
    return GenerationInput(
        brand_id=item.brand_id,
        reference_asset_id=asset.id,
        prompt=prompt,
        style=item.document["style"],
        width=width,
        height=height,
        frames=shot["frames"],
        seed=int(digest({"plan": item.plan, "shot": shot["id"]})[:8], 16),
        usage_confirmed=True,
    )


def queue_shot(db, item, shot_id, user, trace, take_key=None):
    from .video_generation import enqueue

    approved(db, item)
    shot = next((s for s in item.plan["shots"] if s["id"] == shot_id), None)
    if not shot:
        raise DomainError("RESOURCE_NOT_FOUND", "镜头不存在", 404)
    data = shot_request(db, item, shot)
    key = "drama:" + item.id + ":" + str(item.revision) + ":" + digest(shot["id"])[:20]
    if take_key:
        previous = item.bindings.get(shot_id)
        if previous:
            old = owned(db, VideoGenerationJob, previous, item.workspace_id)
            # Replaying this same explicit take is safe even while it runs.
            new_key = key + ":take:" + digest(take_key)[:24]
            if old.idempotency_key != new_key and old.status not in ("completed", "failed", "cancelled"):
                raise DomainError(
                    "DRAMA_TAKE_NOT_SAFE", "本镜头仍在运行或回执未知，请核对已有任务；不会重复提交", 409
                )
        key += ":take:" + digest(take_key)[:24]
    job = enqueue(db, data, user, key, trace)
    job.source = {
        **job.source,
        "drama": {
            "project_id": item.id,
            "revision": item.revision,
            "shot_id": shot_id,
            "creator_run_id": item.run_id,
        },
    }
    if take_key or not item.bindings.get(shot_id) or item.bindings.get(shot_id) == job.id:
        item.bindings = {**item.bindings, shot_id: job.id}
    return job


def production_recipe(db, item, narration=None):
    from .video_recipes import RecipeInput, RecipeScene
    from .video import probe

    approved(db, item)
    scenes = []
    for shot in item.plan["shots"]:
        identifier = item.bindings.get(shot["id"])
        if not identifier:
            raise DomainError("DRAMA_MEDIA_REQUIRED", "尚有镜头未生成，请逐镜制作并审看", 409)
        job = owned(db, VideoGenerationJob, identifier, item.workspace_id)
        from .video_generation import _source_current

        _source_current(db, job)
        expected = shot_request(db, item, shot).model_dump()
        if job.document != expected or job.status != "completed" or not job.output_asset_id:
            raise DomainError("DRAMA_MEDIA_REQUIRED", "镜头未完成或与当前计划不一致", 409)
        asset = owned(db, Asset, job.output_asset_id, item.workspace_id)
        if not asset.verified or job.receipt.get("art_review") != "user_confirmed":
            raise DomainError("DRAMA_MEDIA_REVIEW_REQUIRED", "请在动态镜头页审看角色、动作和画面细节", 409)
        path = verified_file(asset.workspace_id, asset.sha256, asset.suffix)
        video = next(s for s in probe(path)["streams"] if s["codec_type"] == "video")
        if video["width"] < expected["width"] or video["height"] < expected["height"]:
            raise DomainError(
                "DRAMA_SOURCE_RESOLUTION", "生成源片段未达到计划尺寸，不能通过成片放大补足", 409
            )
        scenes.append(
            RecipeScene(
                headline="AI剧情演绎",
                narration=shot["narration"],
                duration_frames=round(shot["frames"] / 24 * 30),
                asset_id=asset.id,
                generation_job_id=job.id,
                motion="still",
            )
        )
    return RecipeInput(
        brand_id=item.brand_id,
        name=item.plan["title"],
        recipe_id="story",
        mode="generative",
        size=item.document["size"],
        scenes=scenes,
        narration=narration,
    )


def public(db, item):
    result = serialize(item)
    try:
        assert_current(db, item)
        result["stale"] = False
    except DomainError:
        result["stale"] = True
    return result
