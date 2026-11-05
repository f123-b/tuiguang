import io
import zipfile
from datetime import datetime, timedelta, timezone

from creator.db import SessionLocal
from creator.jobs import process_pending, schedule_due


def run_content(client, creator_profile):
    r = client.post(
        f"/api/v1/creators/{creator_profile['id']}/run-today", headers={"Idempotency-Key": "test-run"}
    )
    assert r.status_code == 201, r.text
    with SessionLocal() as db:
        process_pending(db)
    return client.get("/api/v1/content/packages").json()[0]


def test_real_handoff_and_metrics(client, creator_profile):
    content = run_content(client, creator_profile)
    assert content["generation_source"] == "template"
    assert "未上线功能" not in content["body"]
    assert content["status"] == "awaiting_user_review"
    cid = content["id"]
    assert client.post("/api/v1/manual-publication/packages", json={"content_id": cid}).status_code == 409
    assert client.post(f"/api/v1/content/packages/{cid}/approve", json={"confirmed": True}).status_code == 200
    r = client.post("/api/v1/manual-publication/packages", json={"content_id": cid})
    assert r.status_code == 201, r.text
    package = r.json()
    archive = client.get(f"/api/v1/manual-publication/packages/{package['id']}/download")
    with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
        assert {"copy.txt", "checklist.md", "provenance.json", "cover.png"} <= set(z.namelist())
    record = client.post(
        "/api/v1/manual-publication/records",
        json={
            "package_id": package["id"],
            "published_at": "2026-11-05T09:00:00+08:00",
            "checklist": [True] * 5,
            "url": "",
            "notes": "测试来源，不代表真实发帖",
        },
    )
    assert record.status_code == 201, record.text
    assert record.json()["source"] == "user_reported"
    body = f"content_id,platform,views,likes,period_start,period_end,observed_at\n{cid},xiaohongshu,100,,2026-11-05,2026-11-06,2026-11-07T00:00:00Z\n"
    r = client.post(
        "/api/v1/analytics/import/preview",
        files={"file": ("sample.csv", body)},
        data={"data_source": "用户上传测试报表"},
    )
    assert r.status_code == 200, r.text
    preview = r.json()
    assert preview["rows"][0]["likes"] is None
    for _ in range(2):
        r = client.post("/api/v1/analytics/import/commit", json={"preview_id": preview["id"]})
        assert r.status_code == 200, r.text
    assert client.get("/api/v1/analytics").json()["snapshot_count"] == 1
    assert client.get("/api/v1/content/packages").json()[0]["status"] == "user_reported_published"


def test_pause_idempotency_and_restart(client, creator_profile):
    cid = creator_profile["id"]
    for _ in range(3):
        r = client.post(f"/api/v1/creators/{cid}/run-today", headers={"Idempotency-Key": "same"})
        assert r.status_code in (200, 201)
    assert len(client.get("/api/v1/creator-runs").json()) == 1
    client.post(f"/api/v1/creators/{cid}/pause")
    with SessionLocal() as db:
        process_pending(db)
    assert client.get("/api/v1/content/packages").json() == []
    assert (
        client.post(f"/api/v1/creators/{cid}/run-today", headers={"Idempotency-Key": "other"}).status_code
        == 409
    )
    client.post(f"/api/v1/creators/{cid}/resume")
    with SessionLocal() as db:
        process_pending(db)
    assert len(client.get("/api/v1/content/packages").json()) == 1


def test_seven_day_schedule_survives_new_sessions(client, creator_profile):
    start = datetime(2026, 11, 6, 2, tzinfo=timezone.utc)
    for day in range(7):
        now = start + timedelta(days=day)
        for _ in range(2):
            with SessionLocal() as db:
                schedule_due(db, now)
        with SessionLocal() as db:
            process_pending(db)
    assert len(client.get("/api/v1/creator-runs").json()) == 7
    assert len(client.get("/api/v1/content/packages").json()) == 7


def test_cross_tenant_and_csrf(client, creator_profile):
    cid = creator_profile["id"]
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.org", "password": "AnotherPassword678!", "name": "其他租户"},
    )
    assert client.get(f"/api/v1/creators/{cid}").status_code == 404
    assert client.post(f"/api/v1/creators/{cid}/pause").status_code == 404
    r = client.post(
        "/api/v1/brands", json={"name": "非法跨站请求"}, headers={"Origin": "https://evil.invalid"}
    )
    assert r.status_code == 403
    assert "trace_id" in r.json()["error"]


def test_unverified_and_misleading_content_blocked(client, creator_profile):
    content = run_content(client, creator_profile)
    cid = content["id"]
    client.patch(f"/api/v1/content/packages/{cid}", json={"body": "保证100%成功，世界第一"})
    r = client.post(f"/api/v1/content/packages/{cid}/approve", json={"confirmed": True})
    assert r.status_code == 409
    report = client.get(f"/api/v1/content/packages/{cid}").json()["compliance"]
    assert report["status"] == "blocked"


def test_url_and_checklist_are_enforced(client, creator_profile):
    content = run_content(client, creator_profile)
    client.post(f"/api/v1/content/packages/{content['id']}/approve", json={"confirmed": True})
    package = client.post("/api/v1/manual-publication/packages", json={"content_id": content["id"]}).json()
    payload = {"package_id": package["id"], "published_at": "2026-11-05T09:00:00Z", "checklist": [True] * 5}
    for url in [
        "javascript:alert(1)",
        "http://127.0.0.1/",
        "https://example.com/",
        "https://evil.xiaohongshu.com.evil.com/a",
    ]:
        assert (
            client.post("/api/v1/manual-publication/records", json={**payload, "url": url}).status_code == 422
        )
    assert (
        client.post("/api/v1/manual-publication/records", json={**payload, "checklist": [True]}).status_code
        == 422
    )
