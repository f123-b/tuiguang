import io
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from creator.db import SessionLocal
from creator.jobs import enqueue, process_pending
from creator.main import app
from creator.models import BudgetEntry, Creator, Run
from test_workflow import run_content


def test_no_external_network_in_complete_handoff(client, creator_profile, monkeypatch):
    # FastAPI TestClient uses httpx too; deny actual socket connections at httpcore, not the client itself.
    def forbid_network(*args, **kwargs):
        raise AssertionError("Business workflow attempted an external network call")

    monkeypatch.setattr("socket.create_connection", forbid_network)
    content = run_content(client, creator_profile)
    client.post(f"/api/v1/content/packages/{content['id']}/approve", json={"confirmed": True})
    package = client.post("/api/v1/manual-publication/packages", json={"content_id": content["id"]}).json()
    assert client.get(f"/api/v1/manual-publication/packages/{package['id']}/download").status_code == 200
    assert (
        client.post(
            "/api/v1/manual-publication/records",
            json={
                "package_id": package["id"],
                "published_at": "2026-11-04T12:00:00Z",
                "checklist": [True] * 5,
            },
        ).status_code
        == 201
    )


def test_concurrent_enqueue_is_unique(client, creator_profile):
    def create(i):
        with SessionLocal() as db:
            creator = db.get(Creator, creator_profile["id"])
            return enqueue(db, creator, "2026-11-08", f"parallel-{i}")[0].id

    with ThreadPoolExecutor(max_workers=3) as pool:
        assert len(set(pool.map(create, range(3)))) == 1


def test_stale_handoff_invalidated_after_edit(client, creator_profile):
    content = run_content(client, creator_profile)
    cid = content["id"]
    client.post(f"/api/v1/content/packages/{cid}/approve", json={"confirmed": True})
    package = client.post("/api/v1/manual-publication/packages", json={"content_id": cid}).json()
    client.patch(f"/api/v1/content/packages/{cid}", json={"title": "更新后需要重新审核"})
    assert client.get(f"/api/v1/manual-publication/packages/{package['id']}/download").status_code == 409


def test_bad_import_is_atomic_and_missing_stays_null(client, creator_profile):
    content = run_content(client, creator_profile)
    header = "content_id,platform,views,likes,period_start,period_end,observed_at\n"
    row = f"{content['id']},xiaohongshu,10,,2026-11-03,2026-11-04,2026-11-05T00:00:00Z\n"
    bad_row = f"{content['id']},xiaohongshu,-3,,2026-11-03,2026-11-04,2026-11-05T00:00:00Z\n"
    r = client.post(
        "/api/v1/analytics/import/preview",
        files={"file": ("test.csv", header + row + bad_row)},
        data={"data_source": "测试文件"},
    )
    assert r.status_code == 422
    assert client.get("/api/v1/analytics").json()["snapshot_count"] == 0


def test_xlsx_import(client, creator_profile):
    import openpyxl

    content = run_content(client, creator_profile)
    wb = openpyxl.Workbook()
    wb.active.append(
        ["content_id", "platform", "views", "likes", "period_start", "period_end", "observed_at"]
    )
    wb.active.append(
        [content["id"], "xiaohongshu", 33, None, "2026-11-03", "2026-11-04", "2026-11-05T00:00:00Z"]
    )
    file = io.BytesIO()
    wb.save(file)
    r = client.post(
        "/api/v1/analytics/import/preview",
        files={"file": ("test.xlsx", file.getvalue())},
        data={"data_source": "测试 XLSX"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["rows"][0]["likes"] is None


def configure_model(monkeypatch):
    for key, value in {
        "GENERATION_MODE": "openai",
        "MODEL_API_KEY": "test-key-never-sent",
        "MODEL_ID": "test-model",
        "MODEL_INPUT_CENTS_PER_MILLION": "1000000",
        "MODEL_OUTPUT_CENTS_PER_MILLION": "1000000",
    }.items():
        monkeypatch.setenv(key, value)


def test_budget_blocks_model_before_request(client, creator_profile, monkeypatch):
    configure_model(monkeypatch)
    with SessionLocal() as db:
        creator = db.get(Creator, creator_profile["id"])
        creator.model_consent = True
        creator.daily_budget_cents = 1
        db.commit()

    def no_post(*a, **kw):
        pytest.fail("Should not call model above budget")

    monkeypatch.setattr(httpx.Client, "post", no_post)
    with SessionLocal() as db:
        creator = db.get(Creator, creator_profile["id"])
        enqueue(db, creator, "2026-11-04", "budget-test")
        process_pending(db)
        run = db.scalar(select(Run))
        assert run.error_code == "BUDGET_LIMIT_REACHED"
        assert db.get(Creator, creator.id).status == "paused_by_budget"


def test_model_unknown_result_never_auto_retries(client, creator_profile, monkeypatch):
    configure_model(monkeypatch)
    calls = []

    def timeout(*args, **kwargs):
        calls.append(1)
        raise httpx.ReadTimeout("unknown billing")

    monkeypatch.setattr(httpx.Client, "post", timeout)
    with SessionLocal() as db:
        creator = db.get(Creator, creator_profile["id"])
        creator.model_consent, creator.daily_budget_cents, creator.monthly_budget_cents = (
            True,
            100000,
            1000000,
        )
        db.commit()
        enqueue(db, creator, "2026-11-04", "unknown-test")
        process_pending(db)
        process_pending(db)
        assert db.scalar(select(Run)).error_code == "AGENT_PROVIDER_RESULT_UNKNOWN"
        assert db.scalar(select(BudgetEntry)).actual_cents is None
        assert db.get(Creator, creator.id).status == "paused_by_error"
    assert len(calls) == 1


def test_worker_crash_recovery_for_safe_draft(client, creator_profile):
    client.post(f"/api/v1/creators/{creator_profile['id']}/run-today", headers={"Idempotency-Key": "crash"})
    with SessionLocal() as db:
        run = db.scalar(select(Run))
        run.status, run.lease_until = (
            "running",
            (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        )
        db.commit()
    with SessionLocal() as db:
        process_pending(db)
    assert len(client.get("/api/v1/content/packages").json()) == 1


def test_logout_revokes_copied_token(client, user):
    token = client.cookies.get("creator_session")
    client.post("/api/v1/auth/logout")
    with TestClient(app) as other:
        other.cookies.set("creator_session", token)
        assert other.get("/api/v1/auth/me").status_code == 401


def test_traceparent_propagates_and_no_secret_in_errors(client):
    trace = "1234567890abcdef1234567890abcdef"
    r = client.get("/api/v1/brands", headers={"traceparent": f"00-{trace}-1234567890abcdef-01"})
    assert r.headers["x-trace-id"] == trace
    assert r.json()["error"]["trace_id"] == trace
    secret = "secret-password-short"
    r = client.post("/api/v1/auth/register", json={"password": secret})
    assert secret not in r.text
