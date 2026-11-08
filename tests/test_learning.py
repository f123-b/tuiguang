from datetime import date, timedelta
import pytest

from creator.db import SessionLocal
from creator.models import Content, Creator, Run
from creator.observability import release_manifest
from test_workflow import run_content

pytestmark = pytest.mark.usefixtures("historical_learning_evidence")


def test_historical_report_excludes_out_of_window_feedback(client, creator_profile, user):
    from creator.models import Feedback

    content = run_content(client, creator_profile)
    with SessionLocal() as db:
        row = Feedback(
            workspace_id=db.get(Content, content["id"]).workspace_id,
            content_id=content["id"],
            content_revision=1,
            reason_tag="too_advertising",
            note="outside fixture",
            recorded_by=user["id"],
            created_at="2026-10-30T12:00:00+00:00",
        )
        db.add(row)
        db.commit()
    response = client.post(
        "/api/v1/creators/" + creator_profile["id"] + "/learning-reports",
        json={"period_start": "2026-11-01", "period_end": "2026-11-07"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["report"]["feedback_count"] == 0


def metric(c, value=100, **extra):
    return {
        "content_id": c["id"],
        "platform": "xiaohongshu",
        "views": value,
        "period_start": "2026-11-01",
        "period_end": "2026-11-07",
        "observed_at": "2026-11-08T00:00:00Z",
        "data_source": "显式标注的合成验收数据",
        **extra,
    }


def test_report_missing_data_feedback_strategy_and_rollback(client, creator_profile):
    c = run_content(client, creator_profile)
    root = "/api/v1/creators/" + creator_profile["id"]
    empty = client.post(
        root + "/learning-reports", json={"period_start": "2026-11-01", "period_end": "2026-11-07"}
    )
    assert empty.status_code == 201, empty.text
    assert (
        empty.json()["report"]["metric_sample_count"] == 0
        and empty.json()["report"]["confidence"] == "insufficient"
    )
    for _ in range(3):
        assert (
            client.post(
                "/api/v1/analytics/feedback",
                json={
                    "content_id": c["id"],
                    "expected_revision": c["revision"],
                    "reason_tag": "too_advertising",
                    "note": "人工反馈：希望克制，非平台数据",
                },
            ).status_code
            == 201
        )
    report = client.post(
        root + "/learning-reports", json={"period_start": "2026-11-01", "period_end": "2026-11-07"}
    ).json()
    assert report["report"]["feedback_count"] == 3 and report["id"] != empty.json()["id"]
    same = client.post(
        root + "/learning-reports", json={"period_start": "2026-11-01", "period_end": "2026-11-07"}
    ).json()
    assert same["id"] == report["id"]
    proposals = client.get(root + "/strategy-proposals").json()
    assert len(proposals) == 1
    p = proposals[0]
    decide = root + "/strategy-proposals/" + p["id"] + "/decide"
    assert (
        client.post(
            decide, json={"decision": "accept", "confirmed": True, "expected_active_id": None}
        ).status_code
        == 200
    )
    # Only new days use accepted preference; existing user-approved entries stay frozen.
    from creator.editorial import ensure_plan

    with SessionLocal() as db:
        creator = db.get(Creator, creator_profile["id"])
        future = ensure_plan(db, creator, date.today() + timedelta(days=30))
        assert all(e.strategy_snapshot["strategy_id"] == p["id"] for e in future)
        db.commit()
    assert (
        client.post(
            decide, json={"decision": "accept", "confirmed": True, "expected_active_id": p["id"]}
        ).status_code
        == 409
    )
    assert (
        client.post(
            root + "/strategy-proposals/" + p["id"] + "/rollback",
            json={"confirmed": True, "expected_active_id": p["id"]},
        ).status_code
        == 200
    )
    assert client.get(root + "/strategy-proposals").json()[0]["status"] == "rolled_back"


def test_fourteen_sources_and_withdrawal_rebuild_report(client, creator_profile, brand):
    c = run_content(client, creator_profile)
    contents = [c]
    with SessionLocal() as db:
        first = db.get(Content, c["id"])
        for index in range(13):
            run = Run(
                workspace_id=first.workspace_id,
                creator_id=first.creator_id,
                operational_date=(date(2026, 12, 1) + timedelta(days=index)).isoformat(),
                idempotency_key=f"synthetic-{index}",
                release=release_manifest(),
                status="completed",
            )
            db.add(run)
            db.flush()
            content = Content(
                workspace_id=first.workspace_id,
                creator_id=first.creator_id,
                run_id=run.id,
                title="合成内容样本",
                body="有来源的测试样本",
                platform="xiaohongshu",
                generation_source="template",
                fact_refs=first.fact_refs,
            )
            db.add(content)
            db.flush()
            contents.append({"id": content.id})
        db.commit()
    for index, content in enumerate(contents):
        response = client.post("/api/v1/analytics/manual", json=metric(content, value=100 + index))
        assert response.status_code == 201, response.text
    # same report from the same raw facts is idempotent
    root = "/api/v1/creators/" + creator_profile["id"] + "/learning-reports"
    r = client.post(root, json={"period_start": "2026-11-01", "period_end": "2026-11-07"}).json()
    assert r["report"]["metric_sample_count"] == 14
    group = r["report"]["groups"][0]
    assert group["metrics"]["views"]["known_count"] == 14 and group["metrics"]["likes"]["mean"] is None
    assert len(r["report"]["metric_evidence"]) == 14
    metric_row = client.get("/api/v1/analytics").json()["groups"][0]["snapshots"][0]
    withdrawn = client.post(
        "/api/v1/analytics/batches/" + metric_row["batch_id"] + "/withdraw", json={"confirmed": True}
    )
    assert withdrawn.status_code == 200
    updated = client.post(root, json={"period_start": "2026-11-01", "period_end": "2026-11-07"}).json()
    assert updated["id"] != r["id"] and updated["report"]["metric_sample_count"] == 13
    assert client.get(root + "/" + r["id"]).json()["report"]["metric_sample_count"] == 14
    client.post(
        "/api/v1/auth/register",
        json={"name": "其他", "email": "other@example.org", "password": "OtherPassword987!"},
    )
    assert client.get(root + "/" + r["id"]).status_code == 404
