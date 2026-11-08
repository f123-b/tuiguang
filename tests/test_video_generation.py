"""Local image-to-video requests are private, durable and never fake readiness."""

import io

from PIL import Image
import pytest
from sqlalchemy import select

from creator.db import SessionLocal
from creator.models import Asset, VideoGenerationJob
from creator.errors import DomainError
from creator import wan_comfy
from creator.video_generation import process_generation_jobs


@pytest.fixture(autouse=True)
def no_real_gpu(monkeypatch):
    monkeypatch.delenv("VIDEO_GEN_BASE_URL", raising=False)
    monkeypatch.delenv("VIDEO_GEN_MODEL_DIR", raising=False)
    monkeypatch.delenv("QWEN_TTS_MODEL_DIR", raising=False)


@pytest.fixture
def local_engine(monkeypatch):
    """A synthetic transport fixture tests queue safety, never AI image quality."""
    from creator.video import ffmpeg

    calls = []

    class Client:
        def upload(self, identifier, image):
            return "creator_ref_" + identifier + ".png"

        def submit(self, graph, identifier):
            calls.append(identifier)
            return "known-provider-id"

        def history(self, identifier):
            return {
                "status": {"completed": True},
                "outputs": {"save": {"images": [{"filename": "synthetic.webm"}]}},
            }

        def download(self, item, path, identifier):
            ffmpeg(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=s=512x288:r=24",
                    "-frames:v",
                    "49",
                    "-c:v",
                    "libvpx-vp9",
                    "-deadline",
                    "realtime",
                    str(path),
                ]
            )

        def free_models(self):
            pass

        def metrics(self):
            return [{"type": "synthetic-test-device", "vram_free": 0}]

        def close(self):
            pass

    monkeypatch.setattr(
        wan_comfy, "snapshot", lambda: {"model_id": "synthetic-contract-model", "version": wan_comfy.VERSION}
    )
    monkeypatch.setattr(wan_comfy, "Client", Client)
    return calls


def create(client, brand, asset, key="generation-one", **extra):
    return client.post(
        "/api/v1/video-generation/jobs", json=payload(brand, asset, **extra), headers={"Idempotency-Key": key}
    )


def reference(client, brand):
    image = Image.new("RGB", (512, 288), "#28456b")
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    response = client.post(
        f"/api/v1/brands/{brand['id']}/assets",
        files={"file": ("synthetic-reference.png", stream.getvalue())},
        data={
            "source": "original synthetic test reference",
            "license_note": "test-generated",
            "verified": "true",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def payload(brand, asset, **extra):
    return {
        "brand_id": brand["id"],
        "reference_asset_id": asset["id"],
        "prompt": "A fictional character turns toward the window and pauses.",
        "style": "realistic",
        "seed": 37,
        "width": 512,
        "height": 288,
        "frames": 49,
        "usage_confirmed": True,
        **extra,
    }


def test_unconfigured_capability_is_explicit_and_authenticated(client, user):
    response = client.get("/api/v1/video-generation/capabilities")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["version"] == "wan_comfy_local@1"
    assert data["available"] is False
    assert data["styles"] == ["realistic", "anime"]
    assert data["reason"]
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/video-generation/capabilities").status_code == 401


@pytest.mark.parametrize(
    "extra", [{"usage_confirmed": False}, {"frames": 50}, {"width": 513}, {"style": "unknown"}]
)
def test_generation_contract_rejects_unsafe_or_unsupported_requests(client, brand, extra):
    asset = reference(client, brand)
    response = client.post(
        "/api/v1/video-generation/jobs",
        json=payload(brand, asset, **extra),
        headers={"Idempotency-Key": "generation-one"},
    )
    assert response.status_code == 422, response.text


def test_idempotency_preserves_seed_reference_and_private_source(client, brand, local_engine):
    asset = reference(client, brand)
    r = create(client, brand, asset)
    assert r.status_code == 201, r.text
    job = r.json()
    assert job["status"] == "queued" and job["trace_id"]
    assert job["document"]["seed"] == 37 and "source" not in job
    assert create(client, brand, asset).json()["id"] == job["id"]
    assert create(client, brand, asset, seed=38).status_code == 409
    assert local_engine == []
    with SessionLocal() as db:
        saved = db.get(VideoGenerationJob, job["id"])
        assert saved.source["reference_sha256"] == asset["sha256"]


def test_native_size_and_five_second_scene_contract(client, brand, local_engine):
    asset = reference(client, brand)
    response = create(client, brand, asset, width=1280, height=704, frames=121)
    assert response.status_code == 201, response.text
    graph = wan_comfy.workflow(response.json()["document"], "creator_ref_" + "a" * 32 + ".png", "a" * 32)
    assert graph["decode"]["class_type"] == "VAEDecode"
    assert graph["latent"]["inputs"]["width"] == 1280
    assert graph["latent"]["inputs"]["length"] == 121


def test_unverified_or_withdrawn_reference_never_submits(client, brand, local_engine):
    asset = reference(client, brand)
    with SessionLocal() as db:
        db.get(Asset, asset["id"]).verified = False
        db.commit()
    assert create(client, brand, asset).status_code == 422
    assert not local_engine


def test_real_media_pipeline_keeps_generated_clip_gated_and_traceable(
    client, brand, local_engine, monkeypatch
):
    asset = reference(client, brand)
    job = create(client, brand, asset).json()
    with SessionLocal() as db:
        process_generation_jobs(db)
    completed = client.get("/api/v1/video-generation/jobs").json()[0]
    assert completed["status"] == "completed", completed
    assert completed["receipt"]["frames"] == 49
    assert completed["receipt"]["art_review"] == "requires_user"
    assert completed["output_asset"]["verified"] is False
    assert client.get(f"/api/v1/video-generation/jobs/{job['id']}/video").content[:4] != b""
    recipe = {
        "brand_id": brand["id"],
        "name": "AI contract test",
        "mode": "generative",
        "recipe_id": "story",
        "scenes": [
            {
                "headline": "Fictional test scene",
                "asset_id": completed["output_asset"]["id"],
                "generation_job_id": job["id"],
                "duration_frames": 60,
            }
        ],
    }

    def make(key):
        return client.post("/api/v1/videos/from-recipe", json=recipe, headers={"Idempotency-Key": key})

    assert make("before-review").status_code == 422
    verified = client.post(
        f"/api/v1/video-generation/jobs/{job['id']}/verify",
        json={"confirmed": True, "note": "Synthetic pipeline fixture, not human artistic approval"},
    )
    assert verified.status_code == 200, verified.text
    project = make("after-review")
    assert project.status_code == 201, project.text
    shot = project.json()["ir"]["shots"][0]
    assert shot["provider"] == "comfy_wan" and shot["kind"] == "ai_creative_scene"
    assert shot["generation_job_id"] == job["id"]
    assert shot["design"]["layout"] == "cinema"
    from creator.video import process_render_jobs
    from creator.narration import process_narration_jobs
    import test_narration_pipeline

    with SessionLocal() as db:
        process_render_jobs(db)
    video_id = project.json()["id"]
    preview = client.get(f"/api/v1/videos/projects/{video_id}")
    assert preview.status_code == 200, preview.text
    assert preview.json()["status"] == "preview_ready", preview.text
    assert client.get(f"/api/v1/videos/{video_id}/download").status_code == 409
    test_narration_pipeline.local_voice.__wrapped__(monkeypatch)
    recipe["narration"] = {
        "voice_id": "test-local",
        "rate": 0,
        "fit_mode": "fixed",
        "subtitles": True,
        "usage_confirmed": True,
    }
    recipe["scenes"][0]["narration"] = "Synthetic narration contract"
    voiced = make("voiced-ai")
    assert voiced.status_code == 201, voiced.text
    with SessionLocal() as db:
        process_narration_jobs(db)
        process_render_jobs(db)
    voiced_project = client.get(f"/api/v1/videos/projects/{voiced.json()['id']}").json()
    assert voiced_project["status"] == "preview_ready", voiced_project
    assert voiced_project["ir"]["audio_tracks"] and voiced_project["ir"]["subtitles"]
    assert voiced_project["ir"]["shots"][0]["generation_job_id"] == job["id"]
    recipe.pop("narration")
    recipe["scenes"][0].pop("generation_job_id")
    assert make("missing-provenance").status_code == 422
    recipe["scenes"][0]["generation_job_id"] = job["id"]
    recipe["mode"] = "screen_demo"
    assert make("fake-real-ui").status_code == 422
    assert local_engine == [job["id"]]
    with SessionLocal() as db:
        process_generation_jobs(db)
        db.get(Asset, asset["id"]).applicability_status = "withdrawn"
        db.commit()
    assert (
        client.post(
            f"/api/v1/video-generation/jobs/{job['id']}/verify",
            json={"confirmed": True, "note": "Check withdrawn source"},
        ).status_code
        == 422
    )
    assert len(local_engine) == 1


def test_unknown_submission_never_repeats_and_known_receipt_can_be_read(
    client, brand, local_engine, monkeypatch
):
    asset = reference(client, brand)
    job = create(client, brand, asset).json()

    def uncertain(self, graph, identifier):
        local_engine.append(identifier)
        raise DomainError("GEN_SUBMISSION_UNKNOWN", "uncertain", 409)

    monkeypatch.setattr(wan_comfy.Client, "submit", uncertain)
    with SessionLocal() as db:
        process_generation_jobs(db)
        process_generation_jobs(db)
    result = client.get("/api/v1/video-generation/jobs").json()[0]
    assert result["status"] == "unknown"
    assert len(local_engine) == 1
    assert client.post(f"/api/v1/video-generation/jobs/{job['id']}/check-existing").status_code == 409
    with SessionLocal() as db:
        row = db.get(VideoGenerationJob, job["id"])
        row.provider_request_id = "known-provider-id"
        db.commit()
    assert client.post(f"/api/v1/video-generation/jobs/{job['id']}/check-existing").status_code == 200
    with SessionLocal() as db:
        process_generation_jobs(db)
        assert db.get(VideoGenerationJob, job["id"]).status == "completed"
    assert len(local_engine) == 1


def test_reference_and_model_rechecked_before_submission(client, brand, local_engine, monkeypatch):
    asset = reference(client, brand)
    create(client, brand, asset)
    monkeypatch.setattr(wan_comfy, "snapshot", lambda: {"version": "changed"})
    with SessionLocal() as db:
        process_generation_jobs(db)
        result = db.scalar(select(VideoGenerationJob))
        assert result.status == "failed" and result.error_code == "GEN_MODEL_CHANGED"
    assert not local_engine


def test_live_lease_cannot_be_claimed_by_another_worker(client, brand, local_engine):
    from datetime import datetime, timedelta, timezone

    asset = reference(client, brand)
    create(client, brand, asset)
    with SessionLocal() as db:
        row = db.scalar(select(VideoGenerationJob))
        row.lease_until = (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat()
        db.commit()
        process_generation_jobs(db)
    assert not local_engine


def test_generation_jobs_are_workspace_private(client, brand, local_engine):
    asset = reference(client, brand)
    job = create(client, brand, asset).json()
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.org", "password": "OtherPassword99!", "name": "Other workspace"},
    )
    assert client.get("/api/v1/video-generation/jobs").json() == []
    assert client.get(f"/api/v1/video-generation/jobs/{job['id']}/video").status_code == 404
    assert create(client, brand, asset).status_code == 404


def test_only_unclaimed_jobs_can_be_cancelled(client, brand, local_engine):
    asset = reference(client, brand)
    job = create(client, brand, asset).json()
    url = f"/api/v1/video-generation/jobs/{job['id']}/cancel"
    assert client.post(url).json()["status"] == "cancelled"
    assert client.post(url).status_code == 409
    with SessionLocal() as db:
        process_generation_jobs(db)
    assert not local_engine


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8188",
        "http://localhost:8188",
        "http://127.0.0.1:8188/path",
        "http://[broken",
        "http://127.0.0.1:8188@evil.test",
        "http://127.0.0.1:8188?x=1",
    ],
)
def test_adapter_rejects_remote_ambiguous_and_malformed_urls(monkeypatch, url):
    monkeypatch.setenv("VIDEO_GEN_BASE_URL", url)
    with pytest.raises(DomainError):
        wan_comfy.base_url()


def test_both_styles_share_fixed_whitelisted_native_graph():
    identifier = "a" * 32
    for style in ("realistic", "anime"):
        graph = wan_comfy.workflow(
            {
                "style": style,
                "prompt": "A person blinks",
                "seed": 37,
                "width": 512,
                "height": 288,
                "frames": 49,
            },
            "creator_ref_" + identifier + ".png",
            identifier,
        )
        assert graph["sample"]["inputs"]["seed"] == 37
        assert graph["latent"]["inputs"]["length"] == 49
        assert not any("url" in v["inputs"] for v in graph.values())
        assert graph["save"]["inputs"]["filename_prefix"] == "creator_jobs/" + identifier
