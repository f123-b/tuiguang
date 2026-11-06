import json

import httpx
from sqlalchemy import select

from creator.db import SessionLocal
from creator.jobs import process_pending
from creator.models import BudgetEntry, Run


def configure(client):
    r = client.put(
        "/api/v1/settings/models",
        json={
            "expected_revision": 0,
            "mode": "openai",
            "model_id": "qa-model",
            "base_url": "https://api.openai.com/v1",
            "input_price": 100,
            "output_price": 200,
            "max_tokens": 1800,
            "api_key": "test-private-model-value",
            "price_source": "合成测试报价",
        },
    )
    assert r.status_code == 200, r.text


def test_workspace_model_obeys_consent_before_any_request(client, creator_profile):
    configure(client)
    client.post(
        "/api/v1/creators/" + creator_profile["id"] + "/run-today",
        headers={"Idempotency-Key": "consent-test"},
    )
    with SessionLocal() as db:
        process_pending(db)
        run = db.scalar(select(Run))
        assert run.status == "failed" and run.error_code == "MODEL_CONSENT_REQUIRED"
        assert db.scalar(select(BudgetEntry)) is None


def test_workspace_model_freezes_config_and_uses_only_authorized_key(
    client, creator_profile, brand, monkeypatch
):
    configure(client)
    from creator.models import Creator

    with SessionLocal() as db:
        db.get(Creator, creator_profile["id"]).model_consent = True
        db.commit()
    client.post(
        "/api/v1/creators/" + creator_profile["id"] + "/run-today", headers={"Idempotency-Key": "paid-mock"}
    )
    calls = []

    def respond(self, url, **kwargs):
        calls.append(kwargs)
        assert kwargs["headers"]["Authorization"] == "Bearer test-private-model-value"
        assert "test-private-model-value" not in json.dumps(kwargs["json"])
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "title": "事实笔记",
                                    "body": "只陈述核实功能",
                                    "fact_refs": [brand["facts"][0]["id"]],
                                }
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 100},
            },
        )

    with monkeypatch.context() as m:
        m.setattr(httpx.Client, "post", respond)
        with SessionLocal() as db:
            process_pending(db)
    assert len(calls) == 1
    with SessionLocal() as db:
        run = db.scalar(select(Run))
        ledger = db.scalar(select(BudgetEntry))
        assert run.status == "completed" and run.release["workspace_model_revision"] == 1
        assert ledger.actual_cents == 1
        assert "test-private-model-value" not in json.dumps(run.release)
