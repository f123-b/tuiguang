import io
import json
import os
from pathlib import Path

from PIL import Image

from creator.db import SessionLocal
from creator.video import process_render_jobs, probe


def test_two_engine_video_and_local_revision_cache(client, brand):
    screenshot = os.getenv("POC_SCREENSHOT")
    if screenshot:
        data = Path(screenshot).read_bytes()
    else:
        image = Image.new("RGB", (1280, 720), "#234138")
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        data = buffer.getvalue()
    asset = client.post(
        f"/api/v1/brands/{brand['id']}/assets",
        files={"file": ("authorized-test-asset.png", data)},
        data={
            "source": "本软件真实截图" if screenshot else "程序生成的测试色卡，不代表真实产品 UI",
            "license_note": "仅用于当前工程验收",
            "verified": "true",
        },
    ).json()
    seconds = int(os.getenv("POC_DURATION", "3"))
    frames = seconds * 30
    video = client.post(
        "/api/v1/videos/projects",
        json={
            "brand_id": brand["id"],
            "name": "MG 与真实素材混合视频验收",
            "width": 1920,
            "height": 1080,
            "shots": [
                {
                    "shot_id": "s1",
                    "provider": "pillow_mg",
                    "kind": "motion_graphics",
                    "duration_frames": frames // 3,
                    "caption": "产品故事，持续发生",
                },
                {
                    "shot_id": "s2",
                    "provider": "ffmpeg_media",
                    "kind": "screen_demo",
                    "duration_frames": frames // 3,
                    "asset_id": asset["id"],
                    "caption": "授权素材画面",
                },
                {
                    "shot_id": "s3",
                    "provider": "pillow_mg",
                    "kind": "motion_graphics",
                    "duration_frames": frames - 2 * (frames // 3),
                    "caption": "内容准备，由你分享",
                },
            ],
        },
    ).json()
    vid = video["id"]
    job = client.post(f"/api/v1/videos/{vid}/render").json()
    with SessionLocal() as db:
        process_render_jobs(db)
    first = client.get(f"/api/v1/videos/{vid}/render-jobs").json()[0]
    assert first["status"] == "completed", first
    assert first["receipt"]["duration_sec"] == seconds
    result = client.get(f"/api/v1/videos/{vid}/download")
    assert result.status_code == 200 and len(result.content) > 1000
    out = Path("artifacts/video-poc" if os.getenv("POC_DURATION") else "artifacts/video-smoke")
    out.mkdir(parents=True, exist_ok=True)
    (out / "mixed.mp4").write_bytes(result.content)
    metadata = probe(out / "mixed.mp4")
    stream = next(s for s in metadata["streams"] if s["codec_type"] == "video")
    assert (stream["width"], stream["height"]) == (1920, 1080)
    assert stream["r_frame_rate"] == "30/1"
    assert any(s["codec_type"] == "audio" for s in metadata["streams"])
    shot = video["ir"]["shots"][2]
    shot["caption"] = "仅修改第三镜头"
    assert client.patch(f"/api/v1/videos/{vid}/scenes/s3", json=shot).status_code == 200
    assert client.get(f"/api/v1/videos/{vid}/download").status_code == 409
    client.post(f"/api/v1/videos/{vid}/render")
    with SessionLocal() as db:
        process_render_jobs(db)
    second = client.get(f"/api/v1/videos/{vid}/render-jobs").json()[0]
    assert second["status"] == "completed"
    before, after = first["receipt"]["shots"], second["receipt"]["shots"]
    assert [s["cached"] for s in after] == [True, True, False]
    assert [s["sha256"] for s in before[:2]] == [s["sha256"] for s in after[:2]]
    assert before[2]["sha256"] != after[2]["sha256"]
    (out / "revised.mp4").write_bytes(client.get(f"/api/v1/videos/{vid}/download").content)
    (out / "project.json").write_text(json.dumps(video["ir"], ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "receipts.json").write_text(
        json.dumps(
            {
                "first": first["receipt"],
                "second": second["receipt"],
                "probe": metadata,
                "render_job_id": job["id"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_unavailable_provider_and_cross_brand_asset_denied(client, brand):
    r = client.post(
        "/api/v1/videos/projects",
        json={
            "brand_id": brand["id"],
            "name": "未接入引擎",
            "shots": [
                {"shot_id": "s1", "provider": "comfy_wan", "kind": "ai_creative_scene", "duration_frames": 30}
            ],
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VID_PROVIDER_UNSUPPORTED"
