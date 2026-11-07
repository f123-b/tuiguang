import json

import pytest

from creator.briefs import BriefInput
from creator.brief_jobs import messages


def source(mode="story"):
    return {
        "document": {
            "brand_id": "b",
            "topic": "项目怎么讲清楚",
            "content": "一个项目准备场景",
            "duration_sec": 40,
            "narrative_mode": mode,
        },
        "brand": {"name": "有招", "facts": [{"id": "f1", "claim": "支持项目资料整理", "verified": True}]},
        "assets": [],
    }


def test_narrative_mode_is_explicit_and_backward_compatible():
    assert BriefInput.model_validate(source()["document"]).narrative_mode == "story"
    assert (
        BriefInput.model_validate({"brand_id": "b", "topic": "旧要求", "content": "原始资料"}).narrative_mode
        == "overview"
    )


def test_story_contract_is_frozen_with_facts_and_stays_advisory():
    output = messages(source())
    payload = json.loads(output[1]["content"])
    direction = payload["direction"]
    assert direction["mode"] == "story"
    assert direction["arc"] == ["hook", "friction", "turn", "evidence", "payoff"]
    assert direction["require_concrete_example"]
    assert direction["fiction_must_be_labeled"]
    assert payload["brand"]["facts"] == source()["brand"]["facts"]
    assert payload["required_total_frames"] == 1200
    assert direction["quality_status"] == "requires_human_judgment"


def test_contrast_and_overview_do_not_invent_assets_or_claims():
    for mode in ("contrast", "documentary", "overview"):
        payload = json.loads(messages(source(mode))[1]["content"])
        assert payload["direction"]["mode"] == mode
        assert payload["authorized_assets"] == []
        assert payload["direction"]["allow_unverified_product_claims"] is False


def test_old_queued_prompt_is_not_changed_by_new_direction():
    payload = json.loads(messages(source(), None)[1]["content"])
    assert "direction" not in payload


def test_unknown_future_direction_never_uses_legacy_prompt():
    from creator.errors import DomainError

    with pytest.raises(DomainError) as error:
        messages(source(), "story_direction@999")
    assert error.value.code == "RUN_VERSION_UNSUPPORTED"


def test_old_brief_snapshot_does_not_gain_a_field_or_invalidate_plan(client, brand):
    from test_creation_briefs import create
    from creator.db import SessionLocal
    from creator.models import CreationBrief
    from creator.briefs import snapshot

    brief = create(client, brand)
    with SessionLocal() as db:
        row = db.get(CreationBrief, brief["id"])
        row.document = {k: v for k, v in row.document.items() if k != "narrative_mode"}
        db.commit()
        assert "narrative_mode" not in snapshot(db, row)["document"]
    root = "/api/v1/creation-briefs/" + brief["id"]
    plan = client.post(root + "/plans/manual", json={"expected_revision": 1, "confirmed": True})
    assert plan.status_code == 201, plan.text
    built = client.post(
        root + "/plans/" + plan.json()["id"] + "/build", json={"expected_revision": 1, "confirmed": True}
    )
    assert built.status_code == 201, built.text
