import io
import math
import struct
import wave

import pytest

from creator.db import SessionLocal
from creator.domains import store_file
from creator.models import Asset
from creator.video import process_render_jobs


@pytest.fixture
def local_voice(monkeypatch):
    from creator import speech

    monkeypatch.setattr(speech, "voices", lambda: [{"id": "test-local", "language": "zh-CN"}])
    calls = []

    def speak(workspace, brand, text, voice, rate=0):
        calls.append(text)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
            wav.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(i * 0.12))) for i in range(22050)))
        sha = store_file(workspace, buf.getvalue(), ".wav")
        return Asset(
            workspace_id=workspace,
            brand_id=brand,
            name="test.wav",
            sha256=sha,
            suffix=".wav",
            kind="audio",
            source="synthetic test tone, not speech",
            license_note="test-generated",
            verified=False,
        )

    monkeypatch.setattr(speech, "synthesize", speak)
    return calls


def project(client, brand):
    r = client.post(
        "/api/v1/videos/projects",
        json={
            "brand_id": brand["id"],
            "name": "配音制作验收",
            "preview_required": True,
            "shots": [
                {
                    "shot_id": "s1",
                    "provider": "pillow_mg",
                    "kind": "motion_graphics",
                    "duration_frames": 15,
                    "caption": "本地整理",
                },
                {
                    "shot_id": "s2",
                    "provider": "pillow_mg",
                    "kind": "motion_graphics",
                    "duration_frames": 15,
                    "caption": "实际体验",
                },
            ],
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def payload(**changes):
    return {
        "expected_revision": 1,
        "lines": [{"shot_id": "s1", "text": "支持本地文件整理。"}, {"shot_id": "s2", "text": "请实际体验。"}],
        "voice_id": "test-local",
        "rate": 0,
        "fit_mode": "extend",
        "subtitles": True,
        "usage_confirmed": True,
        **changes,
    }


def start(client, video, data=None, key="one"):
    return client.post(
        f"/api/v1/videos/{video['id']}/narration-jobs",
        json=data or payload(),
        headers={"Idempotency-Key": key},
    )


def process():
    from creator.narration import process_narration_jobs

    with SessionLocal() as db:
        process_narration_jobs(db)
        process_render_jobs(db)


def test_real_audio_composition_preview_and_idempotency(client, brand, local_voice):
    v = project(client, brand)
    r = start(client, v)
    assert r.status_code == 201, r.text
    assert start(client, v).json()["id"] == r.json()["id"]
    process()
    job = client.get(f"/api/v1/videos/{v['id']}/narration-jobs").json()[0]
    assert job["status"] == "completed", job
    result = client.get(f"/api/v1/videos/projects/{v['id']}").json()
    assert result["revision"] == 2
    assert len(result["ir"]["audio_tracks"]) == 1 and len(result["ir"]["subtitles"]) == 2
    assert all(s["duration_frames"] >= 36 for s in result["ir"]["shots"])
    assert client.get(f"/api/v1/videos/{v['id']}/narration-jobs/{job['id']}/audio").content[:4] == b"RIFF"
    assert client.get(f"/api/v1/videos/{v['id']}/preview/download").status_code == 200
    assert client.get(f"/api/v1/videos/{v['id']}/download").status_code != 200
    assert start(client, v).json()["id"] == r.json()["id"]
    assert len(local_voice) == 2

    # The full workflow ends in a reviewed HD file and an actual local export.
    root = f"/api/v1/videos/{v['id']}"
    assert (
        client.post(root + "/export-local", json={"expected_revision": 2, "confirmed": True}).status_code
        == 409
    )
    preview = client.get(root + "/render-jobs").json()[0]
    report = client.get(root + "/quality").json()[0]
    review = client.post(
        root + "/quality-review",
        json={
            "expected_revision": 2,
            "confirmed": True,
            "preview_job_id": preview["id"],
            "report_id": report["id"],
            "decision": "accept",
            "note": "受控音调及视频文件完整流程测试，不是真实发布审核",
        },
    )
    assert review.status_code == 201, review.text
    assert client.post(root + "/render").status_code == 201
    with SessionLocal() as db:
        process_render_jobs(db)
    exported = client.post(root + "/export-local", json={"expected_revision": 2, "confirmed": True})
    assert exported.status_code == 201, exported.text
    from pathlib import Path
    from creator.domains import digest

    target = Path(exported.json()["path"])
    assert target.is_file() and digest(target.read_bytes()) == exported.json()["sha256"]
    assert (target.parent / "audio-1.wav").is_file() and (target.parent / "subtitles.srt").is_file()
    # Making another video must not revoke this unchanged, reviewed final file.
    project(client, brand)
    assert client.get(root + "/download").status_code == 200
    assert (
        client.post(root + "/export-local", json={"expected_revision": 2, "confirmed": True}).status_code
        == 201
    )


def test_fixed_duration_never_truncates_voice(client, brand, local_voice):
    v = project(client, brand)
    start(client, v, payload(fit_mode="fixed"))
    process()
    job = client.get(f"/api/v1/videos/{v['id']}/narration-jobs").json()[0]
    assert job["status"] == "failed" and job["error_code"] == "TTS_DURATION_TOO_LONG"
    result = client.get(f"/api/v1/videos/projects/{v['id']}").json()
    assert result["revision"] == 1 and not result["ir"]["audio_tracks"]


def test_stale_project_does_not_synthesize_or_overwrite(client, brand, local_voice):
    from creator.models import Video

    v = project(client, brand)
    start(client, v)
    with SessionLocal() as db:
        db.get(Video, v["id"]).revision = 2
        db.commit()
    process()
    job = client.get(f"/api/v1/videos/{v['id']}/narration-jobs").json()[0]
    assert job["status"] == "failed" and job["error_code"] == "VID_REVISION_CONFLICT"
    assert not local_voice


def test_requires_voice_consent_and_correct_shots(client, brand, local_voice):
    v = project(client, brand)
    assert start(client, v, payload(usage_confirmed=False)).status_code == 422
    assert start(client, v, payload(voice_id="missing")).status_code == 422
    assert start(client, v, payload(lines=[{"shot_id": "other", "text": "错误镜头"}])).status_code == 422


def test_cannot_overwrite_mid_synthesis_edit(client, brand, local_voice, monkeypatch):
    from creator import speech
    from creator.models import Video

    v = project(client, brand)
    original = speech.synthesize

    def editing(*args, **kwargs):
        with SessionLocal() as db:
            db.get(Video, v["id"]).revision = 2
            db.commit()
        return original(*args, **kwargs)

    monkeypatch.setattr(speech, "synthesize", editing)
    start(client, v)
    process()
    job = client.get(f"/api/v1/videos/{v['id']}/narration-jobs").json()[0]
    assert job["status"] == "failed" and job["error_code"] == "VID_REVISION_CONFLICT"
    assert not client.get(f"/api/v1/videos/projects/{v['id']}").json()["ir"]["audio_tracks"]


def test_brief_build_runs_narration_and_reuses_completed_job(client, brand, local_voice):
    from test_creation_briefs import create

    brief = create(client, brand)
    root = f"/api/v1/creation-briefs/{brief['id']}"
    plan = client.post(root + "/plans/manual", json={"expected_revision": 1, "confirmed": True}).json()
    body = {
        "expected_revision": 1,
        "confirmed": True,
        "narration": {k: v for k, v in payload().items() if k not in ("expected_revision", "lines")},
    }
    endpoint = root + f"/plans/{plan['id']}/build"
    build = client.post(endpoint, json=body)
    assert build.status_code == 201, build.text
    assert build.json()["narration_job_id"] and not build.json()["render_job_id"]
    process()
    again = client.post(endpoint, json=body)
    assert again.json()["narration_job_id"] == build.json()["narration_job_id"]
    assert len(local_voice) == 2


def test_recording_extends_last_frame_for_full_voice(client, brand, local_voice, tmp_path):
    from creator.video import ffmpeg

    path = tmp_path / "recording.mp4"
    ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=160x90:r=30:d=0.5",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ]
    )
    asset = client.post(
        f"/api/v1/brands/{brand['id']}/assets",
        files={"file": (path.name, path.read_bytes())},
        data={"source": "synthetic QA recording", "license_note": "test-generated", "verified": "true"},
    )
    assert asset.status_code == 201, asset.text
    v = client.post(
        "/api/v1/videos/projects",
        json={
            "brand_id": brand["id"],
            "name": "录屏旁白验收",
            "preview_required": True,
            "shots": [
                {
                    "shot_id": "s1",
                    "provider": "ffmpeg_media",
                    "kind": "screen_demo",
                    "duration_frames": 15,
                    "caption": "实际体验",
                    "asset_id": asset.json()["id"],
                }
            ],
        },
    ).json()
    assert (
        start(client, v, payload(lines=[{"shot_id": "s1", "text": "保留完整的本地测试配音。"}])).status_code
        == 201
    )
    process()
    result = client.get(f"/api/v1/videos/projects/{v['id']}").json()
    assert result["ir"]["shots"][0]["freeze_end_frames"] >= 21
    assert client.get(f"/api/v1/videos/{v['id']}/preview/download").status_code == 200


def test_narration_is_workspace_private(client, brand, local_voice):
    v = project(client, brand)
    job = start(client, v).json()
    process()
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/register",
        json={"email": "voice-other@example.org", "password": "OtherPassword987!", "name": "另一个工作区"},
    )
    assert client.get(f"/api/v1/videos/{v['id']}/narration-jobs").status_code == 404
    assert client.get(f"/api/v1/videos/{v['id']}/narration-jobs/{job['id']}/audio").status_code == 404
    assert start(client, v, key="other").status_code == 404


def test_locked_shot_is_not_extended(client, brand, local_voice):
    from creator.models import Video

    v = project(client, brand)
    with SessionLocal() as db:
        item = db.get(Video, v["id"])
        item.ir = {**item.ir, "shots": [{**s, "locked": True} for s in item.ir["shots"]]}
        db.commit()
    start(client, v)
    process()
    job = client.get(f"/api/v1/videos/{v['id']}/narration-jobs").json()[0]
    assert job["error_code"] == "VID_SHOT_LOCKED"


def test_manual_narration_detaches_automatic_creator_state(client, brand, creator_profile, local_voice):
    from creator.models import Video, Creator

    v = project(client, brand)
    with SessionLocal() as db:
        item = db.get(Video, v["id"])
        item.ir = {**item.ir, "source_creator_id": creator_profile["id"]}
        db.get(Creator, creator_profile["id"]).status = "paused_by_user"
        db.commit()
    start(client, v)
    process()
    result = client.get(f"/api/v1/videos/projects/{v['id']}").json()
    assert "source_creator_id" not in result["ir"]
    assert client.get(f"/api/v1/videos/{v['id']}/preview/download").status_code == 200


def test_expired_local_job_recovers_without_duplicate_output(client, brand, local_voice):
    from creator.models import NarrationJob

    v = project(client, brand)
    job = start(client, v).json()
    with SessionLocal() as db:
        item = db.get(NarrationJob, job["id"])
        item.status, item.lease_until = "running", "2020-01-01T00:00:00+00:00"
        db.commit()
    process()
    process()
    result = client.get(f"/api/v1/videos/{v['id']}/narration-jobs").json()
    assert len(result) == 1 and result[0]["status"] == "completed"
    assert len(local_voice) == 2
