"""Production modes must compile differently and produce real, gated media."""

import io

import pytest
from PIL import Image, ImageDraw

from creator.db import SessionLocal
from creator.video import process_render_jobs
import test_narration_pipeline


@pytest.fixture
def recipe_voice(monkeypatch):
    return test_narration_pipeline.local_voice.__wrapped__(monkeypatch)


def image_asset(client, brand):
    image = Image.new("RGB", (640, 360), "#a94723")
    ImageDraw.Draw(image).rectangle((200, 40, 560, 320), fill="#18b8bd")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    response = client.post(
        f"/api/v1/brands/{brand['id']}/assets",
        files={"file": ("original-illustration.png", buf.getvalue())},
        data={"source": "original test illustration", "license_note": "test-generated", "verified": "true"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def recipe(brand, mode="mg", asset=None, **extra):
    return {
        "brand_id": brand["id"],
        "name": "其他视频类型验收",
        "recipe_id": "tutorial",
        "mode": mode,
        "scenes": [
            {
                "headline": "支持本地文件整理",
                "narration": "先把文件整理清楚。",
                "points": ["准备资料", "逐项核对", "查看结果"],
                "duration_frames": 30,
                "asset_id": asset if mode in ("screen_demo", "montage", "illustrated") else None,
            },
            {
                "headline": "请结合实际版本体验",
                "narration": "再按实际版本体验。",
                "duration_frames": 30,
                "asset_id": asset if mode != "mg" else None,
            },
        ],
        **extra,
    }


def create(client, data, key="recipe-one"):
    return client.post("/api/v1/videos/from-recipe", json=data, headers={"Idempotency-Key": key})


def test_catalog_exposes_real_capabilities_and_six_structures(client, user):
    r = client.get("/api/v1/videos/recipes")
    assert r.status_code == 200, r.text
    catalog = r.json()
    assert catalog["version"] == "video_recipes@2"
    assert len(catalog["recipes"]) == 6
    assert {m["id"] for m in catalog["modes"] if m["available"]} == {
        "mg",
        "screen_demo",
        "montage",
        "illustrated",
        "mixed",
        "generative",
    }
    assert all(not m["available"] for m in catalog["modes"] if m["id"] == "three_d")


@pytest.mark.parametrize(
    "mode,layout",
    [
        ("mg", "diagram"),
        ("screen_demo", "screen"),
        ("montage", "montage"),
        ("illustrated", "comic"),
        ("mixed", "diagram"),
    ],
)
def test_each_mode_renders_real_preview_with_correct_layout(client, brand, mode, layout, tmp_path):
    asset = image_asset(client, brand)
    data = recipe(brand, mode, asset["id"])
    response = create(client, data)
    assert response.status_code == 201, response.text
    video = response.json()
    assert video["ir"]["shots"][0]["design"]["layout"] == layout
    assert video["ir"]["shots"][1]["asset_id"] == (None if mode == "mg" else asset["id"])
    assert create(client, data).json()["id"] == video["id"]
    with SessionLocal() as db:
        process_render_jobs(db)
    root = "/api/v1/videos/" + video["id"]
    job = client.get(root + "/render-jobs").json()[0]
    assert job["status"] == "completed", job
    assert job["receipt"]["shots"][0]["scene_layout"] == layout
    assert client.get(root + "/preview/download").content[4:8] == b"ftyp"
    assert client.post(root + "/render").status_code == 409
    report = client.post(root + "/quality", json={"confirmed": True}).json()
    accepted = client.post(
        root + "/quality-review",
        json={
            "expected_revision": 1,
            "confirmed": True,
            "preview_job_id": job["id"],
            "report_id": report["id"],
            "decision": "accept",
            "note": "合成素材的受控流程测试，不是真实用户艺术审批",
        },
    )
    assert accepted.status_code == 201, accepted.text
    assert client.post(root + "/render").status_code == 201
    with SessionLocal() as db:
        process_render_jobs(db)
    final = client.get(root + "/download")
    assert final.status_code == 200, final.text[:200]
    path = tmp_path / "final.mp4"
    path.write_bytes(final.content)
    from creator.video import probe

    stream = next(s for s in probe(path)["streams"] if s["codec_type"] == "video")
    assert (stream["width"], stream["height"]) == (1920, 1080)
    changed = {**data, "name": "changed"}
    conflict = create(client, changed)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "VID_RECIPE_KEY_CONFLICT"


@pytest.mark.parametrize("mode", ["screen_demo", "montage", "illustrated", "mixed"])
def test_material_modes_do_not_silently_fall_back_to_text(client, brand, mode):
    r = create(client, recipe(brand, mode))
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "VID_RECIPE_ASSETS_REQUIRED"


def test_source_expiry_and_cross_workspace_are_blocked(client, brand):
    from creator.models import Asset

    asset = image_asset(client, brand)
    with SessionLocal() as db:
        db.get(Asset, asset["id"]).applicability_status = "needs_review"
        db.commit()
    r = create(client, recipe(brand, "illustrated", asset["id"]))
    assert r.status_code == 422
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/register",
        json={"email": "other-recipe@example.org", "password": "OtherPassword987!", "name": "other"},
    )
    assert create(client, recipe(brand)).status_code == 404


def test_invalid_or_unavailable_modes_do_not_create_jobs(client, brand):
    assert create(client, recipe(brand, "generative")).status_code == 422
    assert create(client, recipe(brand, scenes=[])).status_code == 422
    data = recipe(brand)
    data["scenes"][0]["headline"] = "世界第一"
    assert create(client, data).status_code == 422


@pytest.mark.parametrize("recipe_id", ["feature", "qa", "tutorial", "story", "release", "brand"])
def test_six_structures_bind_creation_provenance_and_survive_edit(client, brand, recipe_id):
    response = create(client, recipe(brand, recipe_id=recipe_id))
    assert response.status_code == 201, response.text
    video = response.json()
    ir = video["ir"]
    assert ir["production_recipe"]["recipe_id"] == recipe_id
    original = ir.pop("production_recipe")
    ir.pop("schema_version")
    ir["name"] = "手动修订"
    response = client.put(
        f"/api/v1/videos/{video['id']}/project", json={"expected_revision": 1, "document": ir}
    )
    assert response.status_code == 200, response.text
    assert response.json()["ir"]["production_recipe"] == original
    replay = create(client, recipe(brand, recipe_id=recipe_id))
    assert replay.json()["revision"] == 2 and replay.json()["name"] == "手动修订"


@pytest.mark.parametrize("mode", ["mg", "screen_demo", "montage", "illustrated", "mixed"])
def test_each_mode_accepts_narration_and_keeps_hd_review_gate(client, brand, recipe_voice, mode):
    from creator.narration import process_narration_jobs

    asset = image_asset(client, brand)
    data = recipe(
        brand,
        mode,
        asset["id"],
        narration={
            "voice_id": "test-local",
            "fit_mode": "extend",
            "subtitles": True,
            "usage_confirmed": True,
        },
    )
    response = create(client, data)
    assert response.status_code == 201, response.text
    video = response.json()
    with SessionLocal() as db:
        process_narration_jobs(db)
        process_render_jobs(db)
    root = "/api/v1/videos/" + video["id"]
    job = client.get(root + "/narration-jobs").json()[0]
    assert job["status"] == "completed", job
    result = client.get("/api/v1/videos/projects/" + video["id"]).json()
    assert len(result["ir"]["audio_tracks"]) == 1 and len(result["ir"]["subtitles"]) == 2
    assert result["ir"]["production_recipe"]["mode"] == mode
    assert client.get(root + "/preview/download").status_code == 200
    assert client.post(root + "/render").status_code == 409
    assert create(client, data).json()["id"] == video["id"]
    assert len(recipe_voice) == 2


@pytest.mark.parametrize("width,height", [(1920, 1080), (1080, 1920), (1080, 1080)])
@pytest.mark.parametrize("layout", ["diagram", "montage", "comic"])
def test_type_compositions_fit_canvas_and_safe_title_areas(width, height, layout):
    from creator.film import layers_for

    background, layers, viewport = layers_for(
        {
            "caption": "先整理，再讲清楚",
            "asset_id": "fixture" if layout != "diagram" else None,
            "design": {
                "layout": layout,
                "headline": "先整理，再讲清楚",
                "supporting": "情景演绎，结合实际版本体验",
                "points": ["项目背景", "我的选择", "验证过程"],
            },
        },
        {"width": width, "height": height, "presentation": {"style": "studio", "brand_label": "有招"}},
    )
    assert background.size == (width, height)
    assert all(image.size == (width, height) for image in layers)
    if viewport:
        x, y, w, h = viewport
        assert 0 <= x < x + w <= width and 0 <= y < y + h <= height


def test_video_inpoints_and_illustration_format_are_validated(client, brand, tmp_path):
    from creator.video import ffmpeg

    path = tmp_path / "short.mp4"
    ffmpeg(["-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30", "-t", "1", "-c:v", "libx264", str(path)])
    asset = client.post(
        f"/api/v1/brands/{brand['id']}/assets",
        files={"file": ("short.mp4", path.read_bytes())},
        data={"source": "original test pattern", "license_note": "test-generated", "verified": "true"},
    ).json()
    data = recipe(brand, "montage", asset["id"])
    data["scenes"][0]["trim_start_frame"] = 20
    response = create(client, data)
    assert response.status_code == 422 and response.json()["error"]["code"] == "VID_MEDIA_TOO_SHORT"
    response = create(client, recipe(brand, "illustrated", asset["id"]))
    assert response.status_code == 422 and response.json()["error"]["code"] == "VID_RECIPE_ASSET_KIND"


@pytest.mark.parametrize("mode", ["mg", "screen_demo", "montage", "illustrated", "mixed"])
def test_directed_script_builds_through_same_type_compiler(client, brand, mode):
    from test_creation_briefs import brief_data

    asset = image_asset(client, brand)
    visual_mode = "mg" if mode == "mg" else "mixed" if mode == "mixed" else "screen_demo"
    data = brief_data(brand, visual_mode=visual_mode, asset_ids=[] if mode == "mg" else [asset["id"]])
    response = client.post("/api/v1/creation-briefs", json=data)
    assert response.status_code == 201, response.text
    root = "/api/v1/creation-briefs/" + response.json()["id"]
    plan = client.post(root + "/plans/manual", json={"expected_revision": 1, "confirmed": True}).json()
    built = client.post(
        root + "/plans/" + plan["id"] + "/build",
        json={
            "expected_revision": 1,
            "confirmed": True,
            "production_mode": mode,
            "recipe_id": "tutorial",
        },
    )
    assert built.status_code == 201, built.text
    video = client.get("/api/v1/videos/projects/" + built.json()["video_id"]).json()
    assert video["ir"]["production_recipe"]["mode"] == mode
    assert video["ir"]["creation_brief"]["plan_id"] == plan["id"]
    assert [s["narration_text"] for s in video["ir"]["shots"]] == [
        s["narration"] for s in plan["document"]["shots"]
    ]


@pytest.mark.parametrize("layout", ["diagram", "montage", "comic"])
def test_supplementary_text_reserves_bottom_subtitle_area(layout):
    from creator.film import palette
    from creator.film_types import type_layers

    boxes = []

    def record(image, text, box, *args):
        if text == "SUPPORT-MARKER":
            boxes.append(box)

    type_layers(
        {"caption": "Title", "design": {"layout": layout, "supporting": "SUPPORT-MARKER"}},
        {"width": 1080, "height": 1080},
        palette({}),
        record,
    )
    assert boxes and all(y + h <= 1080 * 0.83 for x, y, w, h in boxes)


def test_diagram_marker_continues_moving_after_node_entrances(tmp_path):
    import subprocess
    from PIL import ImageChops
    from creator.film import render_scene

    path = tmp_path / "diagram.mp4"
    render_scene(
        {
            "duration_frames": 60,
            "caption": "Process",
            "design": {
                "layout": "diagram",
                "points": ["Context", "Choice", "Validation"],
            },
        },
        {"width": 640, "height": 360, "fps": 30, "presentation": {"style": "studio"}},
        path,
    )
    frames = []
    for stamp in (1.4, 1.6):
        payload = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                str(stamp),
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "-",
            ]
        )
        frames.append(Image.open(io.BytesIO(payload)).convert("RGB").crop((90, 212, 550, 240)))
    assert ImageChops.difference(*frames).getbbox(), "After entrances, the process marker must still move"
