import json

import httpx
from sqlalchemy import select

from creator.db import SessionLocal
from creator.jobs import process_pending
from creator.models import BudgetEntry, Creator, Run
from test_model_workspace import configure
from test_workflow import run_content


def prepare(client, creator):
    content = run_content(client, creator)
    configure(client)
    with SessionLocal() as db:
        db.get(Creator, creator["id"]).model_consent = True
        db.commit()
    return content


def request_review(client, creator, key="analysis-1", **extra):
    return client.post(
        "/api/v1/creators/" + creator["id"] + "/learning-reports/ai",
        headers={"Idempotency-Key": key},
        json={
            "period_start": "2026-11-01",
            "period_end": "2026-11-07",
            "confirmed": True,
            "private_data_consent": True,
            **extra,
        },
    )


def test_paid_review_is_idempotent_and_does_not_become_a_daily_task(client, creator_profile, monkeypatch):
    c = prepare(client, creator_profile)
    denied = request_review(client, creator_profile, private_data_consent=False)
    assert denied.status_code == 422
    queued = request_review(client, creator_profile)
    assert queued.status_code == 201, queued.text
    assert request_review(client, creator_profile).json()["id"] == queued.json()["id"]
    calls = []

    def reply(self, url, **kwargs):
        calls.append(kwargs)
        assert "test-private-model-value" not in json.dumps(kwargs["json"])
        narrative = {
            "summary": "这里只有标题证据，指标仍然缺失。",
            "observations": ["可比较表达方式，不能推断流量。"],
            "hypotheses": ["建议作为待验证实验。"],
            "experiments": ["保持来源与窗口一致。"],
            "evidence_refs": [c["id"]],
            "preferred_angles": ["使用前检查"],
            "tone": "restrained",
            "concise": False,
            "near_duplicate_groups": [],
        }
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [{"message": {"content": json.dumps(narrative)}}],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 200},
                "model": "qa-model",
            },
        )

    with monkeypatch.context() as m:
        m.setattr(httpx.Client, "post", reply)
        with SessionLocal() as db:
            process_pending(db)
    assert len(calls) == 1
    reports = client.get("/api/v1/creators/" + creator_profile["id"] + "/learning-reports").json()
    ai = next(r for r in reports if r.get("ai_run_id"))
    assert ai["report"]["metric_sample_count"] == 0
    assert ai["report"]["ai_narrative"]["evidence_refs"] == [c["id"]]
    with SessionLocal() as db:
        run = db.get(Run, queued.json()["id"])
        assert run.status == "completed" and run.slot != "daily"
        assert db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == run.id)).actual_cents == 1
    calendar = client.get("/api/v1/creators/" + creator_profile["id"] + "/calendar").json()
    assert all(row.get("run_id") != queued.json()["id"] for row in calendar)


def test_unknown_review_cost_never_retries_and_can_be_reconciled_by_user(
    client, creator_profile, monkeypatch
):
    prepare(client, creator_profile)
    queued = request_review(client, creator_profile)
    assert queued.status_code == 201, queued.text
    calls = []

    def timeout(*args, **kwargs):
        calls.append(1)
        raise httpx.ReadTimeout("synthetic unknown receipt")

    with monkeypatch.context() as m:
        m.setattr(httpx.Client, "post", timeout)
        with SessionLocal() as db:
            process_pending(db)
            process_pending(db)
    assert len(calls) == 1
    with SessionLocal() as db:
        run = db.get(Run, queued.json()["id"])
        assert run.error_code == "AGENT_PROVIDER_RESULT_UNKNOWN"
        ledger = db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == run.id))
        ledger_id = ledger.id
        assert ledger.actual_cents is None
    assert client.post("/api/v1/creators/" + creator_profile["id"] + "/resume").status_code == 409
    result = client.post(
        "/api/v1/settings/billing/" + ledger_id + "/reconcile",
        json={
            "confirmed": True,
            "actual_cents": 0,
            "provider_receipt_source": "合成验收：用户自行核对提供者账单未收费",
            "result": "not_charged",
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["reconciliation"]["source"] == "user_reported"
    assert client.post("/api/v1/creators/" + creator_profile["id"] + "/resume").status_code == 200
    assert request_review(client, creator_profile).json()["id"] == queued.json()["id"]


def test_metric_revision_is_explicit_and_unknown_stays_unknown(client, creator_profile):
    c = run_content(client, creator_profile)
    data = {
        "content_id": c["id"],
        "platform": "xiaohongshu",
        "views": 100,
        "period_start": "2026-11-01",
        "period_end": "2026-11-07",
        "observed_at": "2026-11-08T00:00:00Z",
        "data_source": "合成版本验收",
    }
    unknown = client.post("/api/v1/analytics/manual", json=data)
    assert unknown.status_code == 201 and unknown.json().get("content_revision") is None
    known = client.post("/api/v1/analytics/manual", json={**data, "content_revision": 1})
    assert known.status_code == 201, known.text
    assert known.json()["content_revision"] == 1
    assert client.post("/api/v1/analytics/manual", json={**data, "content_revision": 999}).status_code == 422


def test_stale_review_and_zero_budget_prevent_external_call(client, creator_profile, monkeypatch):
    from creator.models import Content

    c = prepare(client, creator_profile)
    queued = request_review(client, creator_profile).json()
    with SessionLocal() as db:
        db.get(Content, c["id"]).revision += 1
        db.commit()

    def forbidden(*args, **kwargs):
        raise AssertionError("must not call provider")

    with monkeypatch.context() as m:
        m.setattr(httpx.Client, "post", forbidden)
        with SessionLocal() as db:
            process_pending(db)
            assert db.get(Run, queued["id"]).error_code == "LEARNING_EVIDENCE_STALE"
            assert db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == queued["id"])) is None
    new = request_review(client, creator_profile, key="new-version").json()
    with SessionLocal() as db:
        db.get(Creator, creator_profile["id"]).daily_budget_cents = 0
        db.commit()
    with monkeypatch.context() as m:
        m.setattr(httpx.Client, "post", forbidden)
        with SessionLocal() as db:
            process_pending(db)
            assert db.get(Run, new["id"]).error_code == "BUDGET_LIMIT_REACHED"


def test_review_rejects_foreign_evidence_without_retry(client, creator_profile, monkeypatch):
    prepare(client, creator_profile)
    queued = request_review(client, creator_profile).json()
    calls = []

    def reply(self, url, **kwargs):
        calls.append(1)
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"summary": "untrusted", "evidence_refs": ["foreign-content"]}
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 10},
            },
        )

    with monkeypatch.context() as m:
        m.setattr(httpx.Client, "post", reply)
        with SessionLocal() as db:
            process_pending(db)
            process_pending(db)
            assert db.get(Run, queued["id"]).error_code == "AGENT_PROVIDER_RESULT_UNKNOWN"
    assert len(calls) == 1
    assert not any(
        r.get("ai_run_id")
        for r in client.get("/api/v1/creators/" + creator_profile["id"] + "/learning-reports").json()
    )
