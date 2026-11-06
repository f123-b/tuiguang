import io
import json
import zipfile
from datetime import datetime, timedelta, timezone

from creator.db import SessionLocal
from test_workflow import run_content


def test_model_secret_is_encrypted_and_missing_master_fails_closed(client, user, monkeypatch):
    key = "test-private-model-value-never-return"
    payload = {
        "expected_revision": 0,
        "mode": "openai",
        "model_id": "qa-model",
        "base_url": "https://api.openai.com/v1",
        "input_price": 100,
        "output_price": 200,
        "max_tokens": 1800,
        "api_key": key,
        "price_source": "仅合成测试价格，不是真实报价",
    }
    response = client.put("/api/v1/settings/models", json=payload)
    assert response.status_code == 200, response.text
    assert key not in response.text and response.json()["key_configured"]
    from creator.models import ModelConfig

    with SessionLocal() as db:
        row = db.query(ModelConfig).first()
        assert row.encrypted_key and key not in row.encrypted_key
    assert key not in client.get("/api/v1/settings/models").text
    payload["expected_revision"] = 0
    assert client.put("/api/v1/settings/models", json=payload).status_code == 409
    payload["expected_revision"] = 1
    payload["base_url"] = "https://127.0.0.1/private"
    assert client.put("/api/v1/settings/models", json=payload).status_code == 422
    monkeypatch.setenv("MODEL_ENCRYPTION_KEY", "invalid-key")
    payload["base_url"] = "https://api.openai.com/v1"
    assert client.put("/api/v1/settings/models", json=payload).status_code == 503
    with SessionLocal() as db:
        assert db.query(ModelConfig).first().revision == 1


def test_notifications_preferences_read_reminders_and_private_export(client, creator_profile):
    c = run_content(client, creator_profile)
    assert client.post("/api/v1/notifications/sync").status_code == 200
    notes = client.get("/api/v1/notifications").json()
    assert notes and any(n["kind"] == "content_review" for n in notes)
    assert client.post("/api/v1/notifications/sync").status_code == 200
    assert len(client.get("/api/v1/notifications").json()) == len(notes)
    assert client.post("/api/v1/notifications/" + notes[0]["id"] + "/read").json()["read_at"]
    assert (
        client.post("/api/v1/content/packages/" + c["id"] + "/approve", json={"confirmed": True}).status_code
        == 200
    )
    package = client.post("/api/v1/manual-publication/packages", json={"content_id": c["id"]}).json()
    due = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    remind = client.post(
        "/api/v1/notifications/reminders",
        json={"package_id": package["id"], "due_at": due, "confirmed": True},
    )
    assert remind.status_code == 201, remind.text
    client.post("/api/v1/notifications/sync")
    assert any(n["kind"] == "manual_reminder" for n in client.get("/api/v1/notifications").json())
    exported = client.get("/api/v1/settings/export")
    assert exported.status_code == 200, exported.text
    with zipfile.ZipFile(io.BytesIO(exported.content)) as z:
        data = json.loads(z.read("workspace.json"))
        assert len(data["content_packages"]) == 1
        raw = z.read("workspace.json").decode()
        assert "password_hash" not in raw and "encrypted_key" not in raw and "creator_session" not in raw
    preferences = client.put(
        "/api/v1/settings/preferences",
        json={"notification_mode": "off", "timezone": "Asia/Shanghai", "digest_hour": 9},
    )
    assert preferences.status_code == 200
    client.post(
        "/api/v1/auth/register",
        json={"name": "另一个", "email": "other@example.org", "password": "OtherPassword987!"},
    )
    assert client.post("/api/v1/notifications/" + notes[0]["id"] + "/read").status_code == 404
