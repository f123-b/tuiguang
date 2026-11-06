import io
import math
import struct
import wave

from creator.db import SessionLocal
from creator.video import process_render_jobs
from test_workflow import run_content


def audio_asset(client, brand, verified=True):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        wav.writeframes(
            b"".join(
                struct.pack("<h", int(5000 * math.sin(2 * math.pi * 440 * i / 16000))) for i in range(32000)
            )
        )
    return client.post(
        f"/api/v1/brands/{brand['id']}/assets",
        files={"file": ("test-tone.wav", buffer.getvalue())},
        data={
            "source": "程序生成测试音调，不是配音或第三方音乐",
            "license_note": "仅验收使用",
            "verified": str(verified).lower(),
        },
    )


def project(brand, **extra):
    return {
        "brand_id": brand["id"],
        "name": "可编辑音视频验收",
        "width": 1080,
        "height": 1080,
        "shots": [
            {
                "shot_id": "s1",
                "provider": "pillow_mg",
                "kind": "motion_graphics",
                "duration_frames": 60,
                "caption": "有来源的产品信息",
            }
        ],
        **extra,
    }


def test_real_audio_subtitles_and_project_history(client, brand):
    audio = audio_asset(client, brand)
    assert audio.status_code == 201, audio.text
    data = project(
        brand,
        audio_tracks=[
            {
                "track_id": "voice",
                "asset_id": audio.json()["id"],
                "role": "voiceover",
                "start_frame": 0,
                "duration_frames": 60,
            }
        ],
        subtitles=[{"cue_id": "c1", "start_frame": 0, "end_frame": 60, "text": "这是验收字幕"}],
    )
    created = client.post("/api/v1/videos/projects", json=data)
    assert created.status_code == 201, created.text
    v = created.json()
    root = "/api/v1/videos/" + v["id"]
    assert v["ir"]["schema_version"] == "1.1"
    for i in range(3):
        data["shots"][0]["caption"] = "修订版本" + str(i)
        changed = client.put(root + "/project", json={"expected_revision": i + 1, "document": data})
        assert changed.status_code == 200, changed.text
    assert len(client.get(root + "/history").json()) == 4
    assert client.put(root + "/project", json={"expected_revision": 1, "document": data}).status_code == 409
    restored = client.post(root + "/restore/1", json={"expected_revision": 4, "confirmed": True})
    assert restored.status_code == 200 and restored.json()["revision"] == 5
    queued = client.post(root + "/render")
    with SessionLocal() as db:
        process_render_jobs(db)
    job = client.get(root + "/render-jobs").json()[0]
    assert queued.status_code == 201 and job["status"] == "completed", job
    assert job["receipt"]["audio"] == "mixed_authorized_assets"
    assert job["receipt"]["subtitles"] == 1
    assert job["receipt"]["audio_sources"][0]["sha256"] == audio.json()["sha256"]
    assert "00:00:00,000 --> 00:00:02,000" in client.get(root + "/subtitles").text
    assert client.get(root + "/download").status_code == 200
    client.patch("/api/v1/assets/" + audio.json()["id"], json={"verified": False, "reason": "授权撤销"})
    assert client.get(root + "/download").status_code == 422


def test_locked_shot_and_invalid_tracks_do_not_silently_change(client, brand):
    data = project(brand)
    data["shots"][0]["locked"] = True
    v = client.post("/api/v1/videos/projects", json=data).json()
    root = "/api/v1/videos/" + v["id"]
    data["shots"][0]["caption"] = "不能改写锁定镜头"
    assert client.put(root + "/project", json={"expected_revision": 1, "document": data}).status_code == 409
    assert (
        client.post(root + "/shots/s1/lock", json={"expected_revision": 1, "locked": False}).status_code
        == 200
    )
    assert client.put(root + "/project", json={"expected_revision": 2, "document": data}).status_code == 200
    data["subtitles"] = [{"cue_id": "bad", "start_frame": 0, "end_frame": 90, "text": "超出全片"}]
    assert client.post("/api/v1/videos/projects", json=data).status_code == 422
    data["subtitles"] = []
    a = audio_asset(client, brand, False).json()
    data["audio_tracks"] = [
        {"track_id": "bad", "asset_id": a["id"], "start_frame": 0, "duration_frames": 60, "role": "music"}
    ]
    assert client.post("/api/v1/videos/projects", json=data).status_code == 422


def test_video_attachment_rechecks_revision_and_exports_real_mp4(client, creator_profile, brand):
    c = run_content(client, creator_profile)
    v = client.post("/api/v1/videos/projects", json=project(brand)).json()
    root = "/api/v1/videos/" + v["id"]
    client.post(root + "/render")
    with SessionLocal() as db:
        process_render_jobs(db)
    attached = client.post(
        "/api/v1/content/packages/" + c["id"] + "/video",
        json={"video_id": v["id"], "expected_revision": c["revision"], "confirmed": True},
    )
    assert attached.status_code == 200, attached.text
    approved = client.post("/api/v1/content/packages/" + c["id"] + "/approve", json={"confirmed": True})
    assert approved.status_code == 200
    pkg = client.post("/api/v1/manual-publication/packages", json={"content_id": c["id"]}).json()
    import zipfile

    with zipfile.ZipFile(
        io.BytesIO(client.get("/api/v1/manual-publication/packages/" + pkg["id"] + "/download").content)
    ) as z:
        assert "video.mp4" in z.namelist() and len(z.read("video.mp4")) > 1000
    shot = v["ir"]["shots"][0]
    shot["caption"] = "变化后的镜头"
    client.patch(root + "/scenes/s1", json=shot)
    assert client.get("/api/v1/manual-publication/packages/" + pkg["id"] + "/download").status_code == 409
