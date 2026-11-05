import io
import zipfile
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import pytest

from sqlalchemy import select

from creator.db import SessionLocal
from creator.jobs import process_pending, schedule_due
from creator.models import Brand, Creator, Run


def test_future_batch_uses_execution_day_budget(client, creator_profile):
    from creator.jobs import enqueue, reserve_budget
    from creator.errors import DomainError
    from creator.editorial import local_today

    with SessionLocal() as db:
        creator = db.get(Creator, creator_profile["id"])
        today = local_today(creator)
        first, _ = enqueue(db, creator, (today + timedelta(days=1)).isoformat(), "future-1")
        ledger = reserve_budget(db, creator, first, 60)
        assert ledger.billing_date == today.isoformat()
        ledger.status, ledger.actual_cents = "settled", 60
        db.commit()
        second, _ = enqueue(db, creator, (today + timedelta(days=2)).isoformat(), "future-2")
        with pytest.raises(DomainError) as error:
            reserve_budget(db, creator, second, 60)
        assert error.value.code == "BUDGET_LIMIT_REACHED"
        assert creator.status == "paused_by_budget"


def test_concurrent_plan_keeps_unique_rows(client, creator_profile):
    from creator.editorial import ensure_plan

    def create(_):
        with SessionLocal() as db:
            ids = [e.id for e in ensure_plan(db, db.get(Creator, creator_profile["id"]))]
            db.commit()
            return ids

    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(create, range(3)))
    assert len(rows[0]) == 14 and rows[0] == rows[1] == rows[2]


def test_stale_swap_and_unverified_fact_leave_plan_unchanged(client, creator_profile):
    days = plan(client, creator_profile)
    left, right = days[0], days[1]
    response = client.post(
        f"/api/v1/topics/{left['id']}/reschedule",
        json={
            "date": right["date"],
            "expected_revision": left["revision"],
            "swap_revision": 999,
        },
    )
    assert response.status_code == 409
    assert client.get(f"/api/v1/topics/{left['id']}").json()["date"] == left["date"]
    assert (
        client.patch(
            f"/api/v1/topics/{left['id']}",
            json={
                "expected_revision": left["revision"],
                "fact_refs": ["unverified-or-foreign"],
            },
        ).status_code
        == 409
    )
    assert client.get(f"/api/v1/topics/{left['id']}").json()["fact_refs"] == left["fact_refs"]


def test_timezone_dst_and_frequency_preserve_manual_plan(client, creator_profile):
    from creator.editorial import due_at, ensure_plan

    with SessionLocal() as db:
        creator = db.get(Creator, creator_profile["id"])
        creator.timezone, creator.hour = "America/New_York", 2
        assert due_at(creator, "2026-03-08").hour == 3
        assert due_at(creator, "2026-11-01").hour == 2
        creator.weekdays = [0]
        db.commit()
        rows = ensure_plan(db, creator, date(2026, 11, 9))
        manual = rows[1]
        manual.source, manual.status, manual.locked = "user", "approved", True
        creator.weekdays = [4]
        db.commit()
        rows = ensure_plan(db, creator, date(2026, 11, 9))
        db.commit()
        assert rows[0].status == "rest" and rows[4].status == "approved"
        assert rows[1].status == "approved" and rows[1].locked


def plan(client, creator_profile):
    r = client.post(f"/api/v1/creators/{creator_profile['id']}/plan")
    assert r.status_code == 200, r.text
    return r.json()


def preparation(*entries, confirmed=True):
    return {
        "entry_ids": [e["id"] for e in entries],
        "expected_revisions": {e["id"]: e["revision"] for e in entries},
        "confirmed": confirmed,
    }


def test_plan_persists_and_preserves_user_lock(client, creator_profile):
    days = plan(client, creator_profile)
    assert len(days) == 14 and len({d["id"] for d in days}) == 14
    entry = days[2]
    edited = client.patch(
        f"/api/v1/topics/{entry['id']}",
        json={
            "expected_revision": entry["revision"],
            "title": "用户确认的独立选题",
            "locked": True,
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["status"] == "planned"
    again = plan(client, creator_profile)
    saved = next(d for d in again if d["id"] == entry["id"])
    assert saved["title"] == "用户确认的独立选题" and saved["locked"]
    assert saved["revision"] == edited.json()["revision"]
    assert client.get(f"/api/v1/topics/{entry['id']}").json()["fact_evidence"]
    stale = client.patch(
        f"/api/v1/topics/{entry['id']}",
        json={
            "expected_revision": entry["revision"],
            "title": "过期页面不能覆盖新稿",
        },
    )
    assert stale.status_code == 409


def test_batch_validation_is_atomic_and_queued_skip_updates_plan(client, creator_profile):
    left, right = plan(client, creator_profile)[:2]
    skipped = client.post(
        f"/api/v1/topics/{right['id']}/skip", json={"expected_revision": right["revision"]}
    ).json()
    endpoint = f"/api/v1/creators/{creator_profile['id']}/prepare"
    assert client.post(endpoint, json=preparation(left, skipped)).status_code == 409
    assert client.get("/api/v1/creator-runs").json() == []
    queued = client.post(endpoint, json=preparation(left)).json()["runs"][0]
    assert client.post(f"/api/v1/creator-runs/{queued['id']}/skip").status_code == 200
    assert client.get(f"/api/v1/topics/{left['id']}").json()["status"] == "skipped"
    with SessionLocal() as db:
        process_pending(db)
    assert client.get("/api/v1/content/packages").json() == []


def test_edit_requires_approval_and_snapshot_drives_content(client, creator_profile):
    entry = plan(client, creator_profile)[0]
    changed = client.patch(
        f"/api/v1/topics/{entry['id']}",
        json={
            "expected_revision": entry["revision"],
            "title": "只使用我确认过的这个标题",
        },
    ).json()
    payload = preparation(changed)
    endpoint = f"/api/v1/creators/{creator_profile['id']}/prepare"
    assert client.post(endpoint, json=payload).status_code == 409
    approved = client.post(
        f"/api/v1/topics/{entry['id']}/approve",
        json={
            "expected_revision": changed["revision"],
            "confirmed": True,
        },
    )
    assert approved.status_code == 200, approved.text
    assert client.post(endpoint, json=payload).status_code == 409
    payload = preparation(approved.json())
    for _ in range(2):
        response = client.post(endpoint, json=payload)
        assert response.status_code == 200, response.text
    with SessionLocal() as db:
        process_pending(db)
    contents = client.get("/api/v1/content/packages").json()
    assert len(contents) == 1 and contents[0]["title"] == changed["title"]
    runs = client.get("/api/v1/creator-runs").json()
    assert len(runs) == 1
    assert runs[0]["input_snapshot"]["entry_id"] == entry["id"]
    assert runs[0]["input_snapshot"]["title"] == changed["title"]
    assert (
        client.patch(
            f"/api/v1/topics/{entry['id']}",
            json={
                "expected_revision": approved.json()["revision"],
                "title": "不可改写已执行计划",
            },
        ).status_code
        == 409
    )


def test_skip_and_reschedule_are_real_and_atomic(client, creator_profile):
    days = plan(client, creator_profile)
    left, right = days[0], days[1]
    moved = client.post(
        f"/api/v1/topics/{left['id']}/reschedule",
        json={
            "expected_revision": left["revision"],
            "date": right["date"],
            "swap_revision": right["revision"],
        },
    )
    assert moved.status_code == 200, moved.text
    assert client.get(f"/api/v1/topics/{left['id']}").json()["date"] == right["date"]
    other = client.get(f"/api/v1/topics/{right['id']}").json()
    assert other["date"] == left["date"] and other["status"] == "planned"
    assert (
        client.post(
            f"/api/v1/topics/{right['id']}/skip",
            json={
                "expected_revision": other["revision"],
            },
        ).status_code
        == 200
    )
    # Restart-like fresh session: skipped day never produces a daily run.
    due = datetime.fromisoformat(left["date"] + "T23:00:00+08:00")
    with SessionLocal() as db:
        schedule_due(db, due)
        process_pending(db)
        assert db.scalar(select(Run).where(Run.operational_date == left["date"])) is None


def test_seven_different_drafts_can_be_reviewed_and_exported(client, creator_profile):
    entries = plan(client, creator_profile)[:7]
    endpoint = f"/api/v1/creators/{creator_profile['id']}/prepare"
    assert client.post(endpoint, json=preparation(*entries, confirmed=False)).status_code == 422
    r = client.post(endpoint, json=preparation(*entries))
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        process_pending(db)
    contents = client.get("/api/v1/content/packages").json()
    assert len(contents) == 7
    assert len({c["title"] for c in contents}) == 7
    assert len({c["body"] for c in contents}) == 7
    for content in contents:
        assert "未上线功能" not in content["body"]
        assert (
            client.post(
                f"/api/v1/content/packages/{content['id']}/approve", json={"confirmed": True}
            ).status_code
            == 200
        )
        package = client.post(
            "/api/v1/manual-publication/packages", json={"content_id": content["id"]}
        ).json()
        archive = client.get(f"/api/v1/manual-publication/packages/{package['id']}/download")
        with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
            assert content["title"] in z.read("copy.txt").decode()


def test_plan_permissions_and_fact_freshness(client, creator_profile):
    entry = plan(client, creator_profile)[0]
    endpoint = f"/api/v1/creators/{creator_profile['id']}/prepare"
    response = client.post(endpoint, json=preparation(entry))
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        creator = db.get(Creator, creator_profile["id"])
        brand = db.get(Brand, creator.brand_id)
        brand.revision += 1
        db.commit()
        process_pending(db)
    assert client.get("/api/v1/content/packages").json() == []
    run = client.get("/api/v1/creator-runs").json()[0]
    assert run["error_code"] == "EDITORIAL_FACTS_STALE"
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-plan@example.org",
            "name": "其他租户",
            "password": "OtherAccountOnly123!",
        },
    )
    assert client.get(f"/api/v1/topics/{entry['id']}").status_code == 404
    assert client.post(f"/api/v1/topics/{entry['id']}/skip", json={"expected_revision": 1}).status_code == 404


def test_legacy_run_can_continue_and_future_not_auto_run(client, creator_profile):
    days = plan(client, creator_profile)
    with SessionLocal() as db:
        creator = db.get(Creator, creator_profile["id"])
        from creator.observability import release_manifest

        manifest = release_manifest()
        manifest["agent_graph_version"] = "creator_graph@1"
        legacy = Run(
            workspace_id=creator.workspace_id,
            creator_id=creator.id,
            operational_date=days[0]["date"],
            idempotency_key="old-task",
            release=manifest,
        )
        db.add(legacy)
        db.commit()
        process_pending(db)
    assert len(client.get("/api/v1/content/packages").json()) == 1
    with SessionLocal() as db:
        schedule_due(db, datetime.fromisoformat(days[0]["date"] + "T23:00:00+08:00"))
    assert len(client.get("/api/v1/creator-runs").json()) == 1


def test_timezone_next_run_and_pause_block_batch(client, creator_profile):
    plan(client, creator_profile)
    next_time = client.get(f"/api/v1/creators/{creator_profile['id']}").json()["next_run_at"]
    assert next_time is not None
    client.post(f"/api/v1/creators/{creator_profile['id']}/pause")
    entry = plan(client, creator_profile)[0]
    response = client.post(
        f"/api/v1/creators/{creator_profile['id']}/prepare",
        json=preparation(entry),
    )
    assert response.status_code == 409
    assert client.get(f"/api/v1/creators/{creator_profile['id']}").json()["next_run_at"] is None
