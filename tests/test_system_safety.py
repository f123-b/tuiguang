from sqlalchemy import select

from creator.db import SessionLocal
from creator.jobs import process_pending
from creator.models import Run, User
from test_model_workspace import configure
from test_workflow import run_content


def test_changed_model_revision_blocks_old_job_and_member_cannot_set_key(client, creator_profile):
    configure(client)
    client.post(
        "/api/v1/creators/" + creator_profile["id"] + "/run-today",
        headers={"Idempotency-Key": "frozen-config"},
    )
    updated = client.put(
        "/api/v1/settings/models",
        json={
            "expected_revision": 1,
            "mode": "template",
            "model_id": "qa-model",
            "base_url": "https://api.openai.com/v1",
            "input_price": 100,
            "output_price": 200,
            "max_tokens": 1800,
            "price_source": "测试配置修订",
        },
    )
    assert updated.status_code == 200
    with SessionLocal() as db:
        process_pending(db)
        run = db.scalar(select(Run))
        assert run.status == "blocked" and run.error_code == "RUN_VERSION_UNSUPPORTED"
        db.scalar(select(User)).role = "viewer"
        db.commit()
    assert (
        client.put(
            "/api/v1/settings/models",
            json={
                "expected_revision": 2,
                "mode": "template",
                "input_price": 0,
                "output_price": 0,
                "price_source": "测试",
            },
        ).status_code
        == 403
    )
    assert client.get("/api/v1/settings/export").status_code == 403


def test_manual_outcome_never_claims_platform_verification(client, creator_profile):
    c = run_content(client, creator_profile)
    client.post("/api/v1/content/packages/" + c["id"] + "/approve", json={"confirmed": True})
    p = client.post("/api/v1/manual-publication/packages", json={"content_id": c["id"]}).json()
    r = client.post(
        "/api/v1/manual-publication/packages/" + p["id"] + "/outcome",
        json={"outcome": "platform_rejected", "notes": "合成验收自报，未真实发布", "confirmed": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["source"] == "user_reported"
    assert client.get("/api/v1/manual-publication/records").json() == []
    assert client.post("/api/v1/notifications/sync").status_code == 200
    assert not any(n["kind"] == "manual_publication" for n in client.get("/api/v1/notifications").json())
    assert (
        client.put(
            "/api/v1/settings/preferences",
            json={"notification_mode": "daily", "timezone": "invalid/place", "digest_hour": 9},
        ).status_code
        == 422
    )
