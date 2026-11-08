import json
import pytest

from test_workflow import run_content

pytestmark = pytest.mark.usefixtures("historical_learning_evidence")


def test_withdrawn_feedback_disables_approved_preference(client, creator_profile):
    c = run_content(client, creator_profile)
    notes = []
    for i in range(3):
        notes.append(
            client.post(
                "/api/v1/analytics/feedback",
                json={
                    "content_id": c["id"],
                    "expected_revision": 1,
                    "reason_tag": "too_advertising",
                    "note": f"验收反馈 {i}",
                },
            ).json()
        )
    root = "/api/v1/creators/" + creator_profile["id"]
    client.post(root + "/learning-reports", json={"period_start": "2026-11-01", "period_end": "2026-11-07"})
    strategy = client.get(root + "/strategy-proposals").json()[0]
    client.post(
        root + "/strategy-proposals/" + strategy["id"] + "/decide",
        json={"decision": "accept", "confirmed": True, "expected_active_id": None},
    )
    assert client.get("/api/v1/creators").json()[0]["active_strategy_id"] == strategy["id"]
    client.post("/api/v1/analytics/feedback/" + notes[0]["id"] + "/withdraw", json={"confirmed": True})
    assert client.get("/api/v1/creators").json()[0]["active_strategy_id"] is None
    assert client.get(root + "/strategy-proposals").json()[0]["status"] == "needs_review"


def test_user_column_mapping_is_validated_before_import(client, creator_profile):
    c = run_content(client, creator_profile)
    csv = f"作品,平台,播放,起始,结束,观察\n{c['id']},xiaohongshu,55,2026-11-01,2026-11-07,2026-11-08T00:00:00Z\n"
    columns = client.post("/api/v1/analytics/import/columns", files={"file": ("sample.csv", csv)})
    assert columns.status_code == 200, columns.text
    assert "作品" in columns.json()["columns"]
    mapping = {
        "content_id": "作品",
        "platform": "平台",
        "views": "播放",
        "period_start": "起始",
        "period_end": "结束",
        "observed_at": "观察",
    }
    preview = client.post(
        "/api/v1/analytics/import/preview",
        files={"file": ("sample.csv", csv)},
        data={"data_source": "自定义列名测试", "column_mapping": json.dumps(mapping)},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["rows"][0]["views"] == 55 and preview.json()["rows"][0]["likes"] is None
    mapping["platform"] = "不存在"
    assert (
        client.post(
            "/api/v1/analytics/import/preview",
            files={"file": ("sample.csv", csv)},
            data={"data_source": "测试", "column_mapping": json.dumps(mapping)},
        ).status_code
        == 422
    )
