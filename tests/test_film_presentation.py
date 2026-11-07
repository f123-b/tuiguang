import io
import math
import struct
import subprocess
import wave

import pytest

from PIL import Image

from creator.db import SessionLocal
from creator.video import process_render_jobs


def film(brand, **extra):
    return {
        "brand_id": brand["id"],
        "name": "软件发布片验收",
        "preview_required": True,
        "presentation": {
            "style": "studio",
            "theme": "ink",
            "accent": "#B7F56B",
            "brand_label": "产品验收",
            "transition": "clean",
            "audio_finish": True,
        },
        "shots": [
            {
                "shot_id": "s1",
                "provider": "pillow_mg",
                "kind": "motion_graphics",
                "duration_frames": 30,
                "caption": "支持本地文件整理",
                "design": {
                    "layout": "hero",
                    "kicker": "把资料整理清楚",
                    "headline": "让工作更有条理",
                    "supporting": "支持本地文件整理",
                },
            },
            {
                "shot_id": "s2",
                "provider": "pillow_mg",
                "kind": "motion_graphics",
                "duration_frames": 30,
                "caption": "结合实际版本体验",
                "design": {
                    "layout": "closing",
                    "headline": "亲自体验，再作判断",
                    "supporting": "结合实际版本体验",
                },
            },
        ],
        **extra,
    }


def test_studio_project_produces_distinct_native_scenes(client, brand, tmp_path):
    r = client.post("/api/v1/videos/projects", json=film(brand))
    assert r.status_code == 201, r.text
    video = r.json()
    root = "/api/v1/videos/" + video["id"]
    assert client.post(root + "/preview", json={"expected_revision": 1, "confirmed": True}).status_code == 201
    with SessionLocal() as db:
        process_render_jobs(db)
    job = client.get(root + "/render-jobs").json()[0]
    assert job["status"] == "completed", job
    assert job["receipt"]["presentation_version"] == "video_presentation@1"
    assert [s["scene_layout"] for s in job["receipt"]["shots"]] == ["hero", "closing"]
    assert client.get(root + "/preview/download").status_code == 200


def test_scene_design_validation_and_hard_claims(client, brand):
    data = film(brand)
    data["shots"][0]["design"]["crop"] = {"x": 80, "y": 0, "width": 50, "height": 100}
    assert client.post("/api/v1/videos/projects", json=data).status_code == 422
    data = film(brand)
    data["shots"][0]["design"]["headline"] = "世界第一"
    r = client.post("/api/v1/videos/projects", json=data)
    assert r.status_code == 422 and r.json()["error"]["code"] == "QA_CONTENT_BLOCKED"


@pytest.mark.parametrize("width,height", [(1920, 1080), (1080, 1920), (1080, 1080)])
@pytest.mark.parametrize("layout", ["hero", "screen", "focus"])
def test_real_screenshot_focus_and_layout(client, brand, width, height, layout):
    image = Image.new("RGB", (600, 360), "#245b90")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    a = client.post(
        f"/api/v1/brands/{brand['id']}/assets",
        files={"file": ("test-screen.png", buffer.getvalue())},
        data={"source": "synthetic screenshot fixture", "license_note": "test-generated", "verified": "true"},
    ).json()
    data = film(brand)
    data.update(width=width, height=height)
    data["shots"] = [
        {
            "shot_id": "screen",
            "provider": "ffmpeg_media",
            "kind": "screen_demo",
            "duration_frames": 30,
            "caption": "查看真实素材",
            "asset_id": a["id"],
            "design": {
                "layout": layout,
                "headline": "把重点看清楚",
                "crop": {"x": 20, "y": 10, "width": 60, "height": 80},
            },
        }
    ]
    r = client.post("/api/v1/videos/projects", json=data)
    assert r.status_code == 201, r.text
    root = "/api/v1/videos/" + r.json()["id"]
    client.post(root + "/preview", json={"expected_revision": 1, "confirmed": True})
    with SessionLocal() as db:
        process_render_jobs(db)
    j = client.get(root + "/render-jobs").json()[0]
    assert j["status"] == "completed", j
    assert (
        j["receipt"]["shots"][0]["asset_sha256"] == a["sha256"]
        and j["receipt"]["shots"][0]["scene_layout"] == layout
    )


@pytest.mark.parametrize("width,height", [(1920, 1080), (1080, 1920), (1080, 1080)])
def test_titles_and_cards_fit_all_supported_aspects(width, height):
    from creator.film import layers_for

    for layout in ("hero", "features", "steps", "closing"):
        background, layers, _ = layers_for(
            {
                "caption": "把产品内容整理清楚",
                "design": {
                    "layout": layout,
                    "supporting": "从真实内容开始，逐镜头核对，再导出成片。",
                    "points": ["编辑图文与视频工程", "核对素材与字幕", "自行下载并手动发布"],
                },
            },
            {"width": width, "height": height, "presentation": {"style": "studio"}},
        )
        assert background.size == (width, height)
        assert all(layer.getbbox() and layer.getbbox()[3] < height * 0.89 for layer in layers)


@pytest.mark.parametrize("with_music", [True, False])
def test_voice_ducks_music_in_actual_output(client, brand, tmp_path, with_music, monkeypatch):
    from creator.config import DATA_DIR
    from creator import video as renderer

    real_ffmpeg = renderer.ffmpeg
    monkeypatch.setattr(renderer, "ffmpeg", lambda arguments, **kw: real_ffmpeg(arguments, timeout=15, **kw))

    def tone(name, hz, seconds):
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
            wav.writeframes(
                b"".join(
                    struct.pack("<h", round(9000 * math.sin(i * hz * 2 * math.pi / 48000)))
                    for i in range(seconds * 48000)
                )
            )
        response = client.post(
            f"/api/v1/brands/{brand['id']}/assets",
            files={"file": (name, buffer.getvalue())},
            data={
                "source": "synthetic test tone, not speech or licensed music",
                "license_note": "test-generated",
                "verified": "true",
            },
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    music, voice = tone("music.wav", 220, 6), tone("voice.wav", 880, 2)
    data = film(brand)
    for shot in data["shots"]:
        shot["duration_frames"] = 90
    data["audio_tracks"] = [
        {"track_id": "music", "asset_id": music, "role": "music", "start_frame": 0, "duration_frames": 180},
        {
            "track_id": "voice",
            "asset_id": voice,
            "role": "voiceover",
            "start_frame": 60,
            "duration_frames": 60,
        },
    ]
    if not with_music:
        data["audio_tracks"] = data["audio_tracks"][1:]
    video = client.post("/api/v1/videos/projects", json=data).json()
    root = "/api/v1/videos/" + video["id"]
    client.post(root + "/preview", json={"expected_revision": 1, "confirmed": True})
    with SessionLocal() as db:
        process_render_jobs(db)
    job = client.get(root + "/render-jobs").json()[0]
    assert job["status"] == "completed", job
    assert job["receipt"]["audio_finishing"]["music_ducking"] is with_music
    target = next(DATA_DIR.glob("*/cache/" + job["receipt"]["sha256"] + ".mp4"))
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(target), "-f", "s16le", "-ac", "1", "-ar", "48000", "pipe:1"],
        capture_output=True,
        check=True,
    ).stdout
    values = struct.unpack("<" + "h" * (len(raw) // 2), raw)
    assert abs(len(values) / 48000 - 6) < 0.1

    def magnitude(second, hz):
        sample = values[round(second * 48000) : round((second + 0.2) * 48000)]
        a = sum(v * math.sin(i * hz * 2 * math.pi / 48000) for i, v in enumerate(sample))
        b = sum(v * math.cos(i * hz * 2 * math.pi / 48000) for i, v in enumerate(sample))
        return math.hypot(a, b) / len(sample)

    if with_music:
        assert magnitude(3, 220) < magnitude(1, 220) * 0.5
    assert magnitude(3, 880) > 100


def test_studio_edit_roundtrip_and_preview_invalidation(client, brand):
    video = client.post("/api/v1/videos/projects", json=film(brand)).json()
    root = "/api/v1/videos/" + video["id"]
    client.post(root + "/preview", json={"expected_revision": 1, "confirmed": True})
    with SessionLocal() as db:
        process_render_jobs(db)
    first = client.get(root + "/render-jobs").json()[0]
    doc = film(brand)
    doc["presentation"]["theme"] = "paper"
    doc["presentation"]["accent"] = "#356A37"
    doc["shots"][0]["design"]["headline"] = "现在查看本地整理"
    r = client.put(root + "/project", json={"expected_revision": 1, "document": doc})
    assert r.status_code == 200, r.text
    edited = client.get("/api/v1/videos/projects/" + video["id"]).json()
    assert edited["revision"] == 2 and edited["ir"]["presentation"]["theme"] == "paper"
    assert client.get(root + "/preview/download").status_code != 200
    client.post(root + "/preview", json={"expected_revision": 2, "confirmed": True})
    with SessionLocal() as db:
        process_render_jobs(db)
    second = client.get(root + "/render-jobs").json()[0]
    assert second["status"] == "completed", second
    assert first["receipt"]["sha256"] != second["receipt"]["sha256"]
    assert (
        first["receipt"]["shots"][0]["render_cache_key"] != second["receipt"]["shots"][0]["render_cache_key"]
    )


def test_brief_build_preserves_script_and_existing_project(client, brand):
    from test_creation_briefs import create

    brief = create(client, brand)
    root = "/api/v1/creation-briefs/" + brief["id"]
    plan = client.post(root + "/plans/manual", json={"expected_revision": 1, "confirmed": True}).json()
    endpoint = root + "/plans/" + plan["id"] + "/build"
    result = client.post(
        endpoint,
        json={
            "expected_revision": 1,
            "confirmed": True,
            "presentation": {"style": "studio", "brand_label": "用户署名"},
        },
    )
    assert result.status_code == 201, result.text
    project = "/api/v1/videos/projects/" + result.json()["video_id"]
    video = client.get(project).json()
    assert video["ir"]["presentation"]["style"] == "studio"
    assert [s["narration_text"] for s in video["ir"]["shots"]] == [
        s["narration"] for s in plan["document"]["shots"]
    ]
    assert video["ir"]["shots"][-1]["design"]["layout"] == "closing"
    same = client.post(
        endpoint, json={"expected_revision": 1, "confirmed": True, "presentation": {"style": "classic"}}
    )
    assert same.json()["already_created"] is True
    assert client.get(project).json()["ir"]["presentation"]["style"] == "studio"
