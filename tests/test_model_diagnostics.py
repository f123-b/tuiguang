import json
import httpx
from sqlalchemy import select
from creator.db import SessionLocal
from creator.jobs import process_pending
from creator.models import BudgetEntry, Creator, Run
from test_model_workspace import configure


def test_custom_gateway_requires_trust_and_never_moves_old_key(client, user):
    payload = {
        "expected_revision": 0,
        "mode": "openai",
        "model_id": "qa-model",
        "base_url": "https://gateway.example.org/v1",
        "input_price": 100,
        "output_price": 200,
        "max_tokens": 512,
        "price_source": "合成联调价格",
        "api_key": "synthetic-secret-only",
        "json_mode": False,
        "token_parameter": "max_completion_tokens",
    }
    assert client.put("/api/v1/settings/models", json=payload).status_code == 422
    r = client.put("/api/v1/settings/models", json={**payload, "endpoint_confirmed": True})
    assert r.status_code == 200, r.text
    assert r.json()["endpoint_approved"] and "synthetic-secret-only" not in r.text
    payload.update(expected_revision=1, base_url="https://another.example.org/v1", endpoint_confirmed=True)
    payload.pop("api_key")
    assert client.put("/api/v1/settings/models", json=payload).status_code == 422
    payload.update(base_url="https://127.0.0.1/v1", api_key="new-synthetic-key")
    assert client.put("/api/v1/settings/models", json=payload).status_code == 422


def test_model_list_is_explicit_and_saved_as_revision_receipt(client, user, monkeypatch):
    configure(client)
    calls = []

    def get(self, url, **kwargs):
        calls.append(url)
        return httpx.Response(
            200, request=httpx.Request("GET", url), json={"data": [{"id": "qa-model"}, {"id": "other"}]}
        )

    with monkeypatch.context() as m:
        m.setattr(httpx.Client, "get", get)
        assert (
            client.post(
                "/api/v1/settings/models/check", json={"expected_revision": 1, "confirmed": False}
            ).status_code
            == 422
        )
        r = client.post("/api/v1/settings/models/check", json={"expected_revision": 1, "confirmed": True})
    assert r.status_code == 201, r.text
    assert r.json()["result"]["models"] == ["other", "qa-model"]
    assert len(calls) == 1 and "test-private-model-value" not in r.text
    assert (
        client.post(
            "/api/v1/settings/models/check", json={"expected_revision": 0, "confirmed": True}
        ).status_code
        == 409
    )


def test_generation_probe_uses_creator_budget_and_new_token_parameter(client, creator_profile, monkeypatch):
    configure(client)
    payload = client.get("/api/v1/settings/models").json()
    change = {
        k: payload[k]
        for k in [
            "mode",
            "model_id",
            "model_revision",
            "base_url",
            "input_price",
            "output_price",
            "max_tokens",
            "price_source",
        ]
    }
    assert (
        client.put(
            "/api/v1/settings/models",
            json={
                **change,
                "expected_revision": 1,
                "json_mode": False,
                "token_parameter": "max_completion_tokens",
            },
        ).status_code
        == 200
    )
    with SessionLocal() as db:
        db.get(Creator, creator_profile["id"]).model_consent = True
        db.commit()
    data = {
        "expected_revision": 2,
        "creator_id": creator_profile["id"],
        "max_cost_cents": 10,
        "confirmed": True,
    }
    r = client.post("/api/v1/settings/models/probe", json=data, headers={"Idempotency-Key": "probe-1"})
    assert r.status_code == 201, r.text
    assert (
        client.post(
            "/api/v1/settings/models/probe", json=data, headers={"Idempotency-Key": "probe-1"}
        ).json()["id"]
        == r.json()["id"]
    )
    calls = []

    def reply(self, url, **kwargs):
        calls.append(kwargs["json"])
        assert (
            "max_completion_tokens" in calls[-1]
            and "max_tokens" not in calls[-1]
            and "response_format" not in calls[-1]
        )
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "model": "qa-model",
                "choices": [{"message": {"content": json.dumps({"connection": "ok"})}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10},
            },
        )

    with monkeypatch.context() as m:
        m.setattr(httpx.Client, "post", reply)
        with SessionLocal() as db:
            process_pending(db)
    checks = client.get("/api/v1/settings/models/checks").json()
    probe = next(x for x in checks if x["id"] == r.json()["id"])
    assert probe["status"] == "completed" and probe["result"]["actual_cents"] == 1
    assert len(calls) == 1
    with SessionLocal() as db:
        run = db.get(Run, probe["run_id"])
        assert len(run.slot) <= Run.__table__.c.slot.type.length
        assert (
            run.slot != "daily"
            and db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == run.id)).status == "settled"
        )


def test_probe_unknown_response_never_retries(client, creator_profile, monkeypatch):
    configure(client)
    with SessionLocal() as db:
        db.get(Creator, creator_profile["id"]).model_consent = True
        db.commit()
    r = client.post(
        "/api/v1/settings/models/probe",
        json={
            "expected_revision": 1,
            "creator_id": creator_profile["id"],
            "max_cost_cents": 10,
            "confirmed": True,
        },
        headers={"Idempotency-Key": "unknown-probe"},
    )
    calls = []

    def timeout(*args, **kwargs):
        calls.append(1)
        raise httpx.ReadTimeout("synthetic timeout")

    with monkeypatch.context() as m:
        m.setattr(httpx.Client, "post", timeout)
        with SessionLocal() as db:
            process_pending(db)
            process_pending(db)
    assert len(calls) == 1
    row = next(x for x in client.get("/api/v1/settings/models/checks").json() if x["id"] == r.json()["id"])
    assert row["status"] == "failed" and row["result"]["error_code"] == "AGENT_PROVIDER_RESULT_UNKNOWN"
    with SessionLocal() as db:
        ledger = db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == row["run_id"]))
        assert ledger.status == "reserved" and ledger.actual_cents is None


def test_model_list_provider_errors_are_redacted(client, user, monkeypatch):
    configure(client)

    def rejected(self, url, **kwargs):
        return httpx.Response(
            401,
            request=httpx.Request("GET", url),
            json={"error": "test-private-model-value synthetic provider echo"},
        )

    with monkeypatch.context() as m:
        m.setattr(httpx.Client, "get", rejected)
        r = client.post("/api/v1/settings/models/check", json={"expected_revision": 1, "confirmed": True})
    assert r.status_code == 201 and r.json()["result"]["error_code"] == "MODEL_KEY_REJECTED"
    assert "test-private-model-value" not in r.text
