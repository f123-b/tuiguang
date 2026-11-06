from creator.db import SessionLocal
from creator.video import process_render_jobs


def brief_data(brand, **extra):
    return {
        "brand_id": brand["id"],
        "topic": "文件整理功能介绍",
        "content": "介绍已经核实的本地整理能力，结尾邀请亲自体验。",
        "audience": "独立开发者",
        "tone": "清楚、克制",
        "verbatim_script": "先看看本地文件整理\n请结合实际版本体验",
        "required_phrases": ["本地文件整理"],
        "forbidden_phrases": ["世界第一"],
        "call_to_action": "请结合实际版本体验",
        "duration_sec": 4,
        "size": "wide",
        "visual_mode": "mg",
        "fact_refs": [brand["facts"][0]["id"]],
        "asset_ids": [],
        **extra,
    }


def create(client, brand, **extra):
    r = client.post("/api/v1/creation-briefs", json=brief_data(brand, **extra))
    assert r.status_code == 201, r.text
    return r.json()


def test_verbatim_script_creates_real_preview_and_is_idempotent(client, brand):
    b = create(client, brand)
    root = "/api/v1/creation-briefs/" + b["id"]
    plan = client.post(root + "/plans/manual", json={"expected_revision": 1, "confirmed": True})
    assert plan.status_code == 201, plan.text
    p = plan.json()
    assert [s["caption"] for s in p["document"]["shots"]] == brief_data(brand)["verbatim_script"].splitlines()
    assert sum(s["duration_frames"] for s in p["document"]["shots"]) == 120
    build = client.post(
        root + "/plans/" + p["id"] + "/build", json={"expected_revision": 1, "confirmed": True}
    )
    assert build.status_code == 201, build.text
    same = client.post(
        root + "/plans/" + p["id"] + "/build", json={"expected_revision": 1, "confirmed": True}
    )
    assert same.json()["video_id"] == build.json()["video_id"]
    video = "/api/v1/videos/" + build.json()["video_id"]
    with SessionLocal() as db:
        process_render_jobs(db)
    assert client.get(video + "/preview/download").status_code == 200
    assert client.get(video + "/download").status_code != 200
    assert client.post(video + "/render").status_code == 409


def test_changed_brief_rejects_old_plan_and_does_not_change_it(client, brand):
    b = create(client, brand)
    root = "/api/v1/creation-briefs/" + b["id"]
    p = client.post(root + "/plans/manual", json={"expected_revision": 1, "confirmed": True}).json()
    r = client.put(root, json={"expected_revision": 1, "document": brief_data(brand, topic="新主题")})
    assert r.status_code == 200, r.text
    assert (
        client.post(
            root + "/plans/" + p["id"] + "/build", json={"expected_revision": 2, "confirmed": True}
        ).status_code
        == 409
    )
    assert client.get(root).json()["plans"][0]["document"] == p["document"]


def test_brief_constraints_need_revision_and_tenant_isolation(client, brand):
    b = create(client, brand, required_phrases=["必须出现这段文字"])
    root = "/api/v1/creation-briefs/" + b["id"]
    p = client.post(root + "/plans/manual", json={"expected_revision": 1, "confirmed": True}).json()
    assert p["review"]["status"] == "needs_revision"
    assert (
        client.post(
            root + "/plans/" + p["id"] + "/build", json={"expected_revision": 1, "confirmed": True}
        ).status_code
        == 422
    )
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/register",
        json={"email": "brief-other@example.org", "password": "OtherPassword987!", "name": "别的工作区"},
    )
    assert client.get(root).status_code == 404


def ai_setup(client, creator_profile, brand):
    from test_model_workspace import configure
    from creator.models import Creator

    configure(client)
    with SessionLocal() as db:
        db.get(Creator, creator_profile["id"]).model_consent = True
        db.commit()
    b = create(client, brand)
    root = "/api/v1/creation-briefs/" + b["id"]
    payload = {
        "expected_revision": 1,
        "confirmed": True,
        "creator_id": creator_profile["id"],
        "max_cost_cents": 10,
    }
    return b, root, payload


def model_reply(brand, caption="先看看本地文件整理"):
    import json

    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "title": "文件整理功能介绍",
                            "fact_refs": [brand["facts"][0]["id"]],
                            "shots": [
                                {
                                    "duration_frames": 60,
                                    "caption": caption,
                                    "narration": "已核实的本地文件整理",
                                    "visual_note": "MG 文字",
                                    "asset_id": None,
                                },
                                {
                                    "duration_frames": 60,
                                    "caption": "请结合实际版本体验",
                                    "narration": "请核对版本",
                                    "visual_note": "结束文字",
                                    "asset_id": None,
                                },
                            ],
                            "uncertainties": [],
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10},
    }


def test_ai_brief_is_budgeted_frozen_and_not_automatically_rendered(
    client, creator_profile, brand, monkeypatch
):
    import httpx
    import json
    from sqlalchemy import select
    from creator.jobs import process_pending
    from creator.models import BudgetEntry, Run, Video

    b, root, payload = ai_setup(client, creator_profile, brand)
    queued = client.post(root + "/plans/ai", json=payload, headers={"Idempotency-Key": "brief-ai-one"})
    assert queued.status_code == 201, queued.text
    assert (
        client.post(root + "/plans/ai", json=payload, headers={"Idempotency-Key": "brief-ai-one"}).json()[
            "id"
        ]
        == queued.json()["id"]
    )
    calls = []

    def reply(self, url, **kwargs):
        body = json.loads(kwargs["json"]["messages"][1]["content"])
        assert body["brief"]["topic"] == b["topic"] and body["required_total_frames"] == 120
        assert "test-private-model-value" not in json.dumps(kwargs["json"])
        calls.append(1)
        return httpx.Response(200, request=httpx.Request("POST", url), json=model_reply(brand))

    monkeypatch.setattr(httpx.Client, "post", reply)
    with SessionLocal() as db:
        process_pending(db)
        process_pending(db)
        run = db.get(Run, queued.json()["id"])
        assert run.status == "completed" and len(run.slot) <= 30
        assert db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == run.id)).actual_cents == 1
        assert db.scalar(select(Video)) is None
    assert len(calls) == 1
    data = client.get(root).json()
    assert data["plans"][0]["review"]["status"] == "needs_confirmation"
    assert (
        "input_snapshot"
        not in client.get("/api/v1/creator-runs/" + queued.json()["id"] + "/diagnostic").json()["run"]
    )


def test_valid_model_script_with_missing_phrase_is_saved_for_editing(
    client, creator_profile, brand, monkeypatch
):
    import httpx
    from creator.jobs import process_pending

    b, root, payload = ai_setup(client, creator_profile, brand)
    client.post(root + "/plans/ai", json=payload, headers={"Idempotency-Key": "brief-needs-edit"})

    def reply(self, url, **kwargs):
        return httpx.Response(
            200, request=httpx.Request("POST", url), json=model_reply(brand, "不含必现文字的开场")
        )

    monkeypatch.setattr(httpx.Client, "post", reply)
    with SessionLocal() as db:
        process_pending(db)
    plan = client.get(root).json()["plans"][0]
    assert plan["review"]["status"] == "needs_revision"
    doc = plan["document"]
    doc["shots"][0]["caption"] = "本地文件整理"
    revised = client.post(
        root + "/plans/" + plan["id"] + "/revisions", json={"expected_revision": 1, "document": doc}
    )
    assert revised.status_code == 201, revised.text
    assert revised.json()["review"]["status"] == "needs_confirmation"
    old = next(p for p in client.get(root).json()["plans"] if p["id"] == plan["id"])
    assert old["document"]["shots"][0]["caption"] == "不含必现文字的开场"


def test_change_during_model_call_preserves_script_and_known_cost(
    client, creator_profile, brand, monkeypatch
):
    import httpx
    from sqlalchemy import select
    from creator.jobs import process_pending
    from creator.models import BudgetEntry, Run

    b, root, payload = ai_setup(client, creator_profile, brand)
    queued = client.post(root + "/plans/ai", json=payload, headers={"Idempotency-Key": "brief-race"}).json()

    def reply(self, url, **kwargs):
        r = client.put(
            root, json={"expected_revision": 1, "document": brief_data(brand, topic="调用期间的新主题")}
        )
        assert r.status_code == 200, r.text
        return httpx.Response(200, request=httpx.Request("POST", url), json=model_reply(brand))

    monkeypatch.setattr(httpx.Client, "post", reply)
    with SessionLocal() as db:
        process_pending(db)
        assert db.get(Run, queued["id"]).status == "completed"
        assert db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == queued["id"])).status == "settled"
    p = client.get(root).json()["plans"][0]
    assert p["stale"] and p["review"]["input_stale"]
    assert (
        client.post(
            root + "/plans/" + p["id"] + "/build", json={"expected_revision": 2, "confirmed": True}
        ).status_code
        == 409
    )


def test_unknown_model_receipt_does_not_retry_or_create_a_plan(client, creator_profile, brand, monkeypatch):
    import httpx
    from sqlalchemy import select
    from creator.jobs import process_pending
    from creator.models import BudgetEntry, Run

    b, root, payload = ai_setup(client, creator_profile, brand)
    queued = client.post(
        root + "/plans/ai", json=payload, headers={"Idempotency-Key": "brief-timeout"}
    ).json()
    calls = []

    def timeout(*args, **kwargs):
        calls.append(1)
        raise httpx.ReadTimeout("synthetic")

    monkeypatch.setattr(httpx.Client, "post", timeout)
    with SessionLocal() as db:
        process_pending(db)
        process_pending(db)
        assert db.get(Run, queued["id"]).error_code == "AGENT_PROVIDER_RESULT_UNKNOWN"
        assert db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == queued["id"])).actual_cents is None
    assert len(calls) == 1 and client.get(root).json()["plans"] == []


def test_queued_brief_revision_change_stops_before_any_paid_request(client, creator_profile, brand):
    from sqlalchemy import select
    from creator.jobs import process_pending
    from creator.models import BudgetEntry, Run

    b, root, payload = ai_setup(client, creator_profile, brand)
    queued = client.post(
        root + "/plans/ai", json=payload, headers={"Idempotency-Key": "brief-stale-before-call"}
    ).json()
    client.put(
        root, json={"expected_revision": 1, "document": brief_data(brand, content="调用前已经改写要求")}
    )
    with SessionLocal() as db:
        process_pending(db)
        assert db.get(Run, queued["id"]).error_code == "BRIEF_PLAN_STALE"
        assert db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == queued["id"])) is None


def test_ai_authorization_and_request_cap_prevent_any_model_call(client, creator_profile, brand, monkeypatch):
    import httpx
    from sqlalchemy import select
    from creator.jobs import process_pending
    from creator.models import BudgetEntry, Creator, Run, User

    b, root, payload = ai_setup(client, creator_profile, brand)
    with SessionLocal() as db:
        db.get(Creator, creator_profile["id"]).model_consent = False
        db.commit()
    assert (
        client.post(root + "/plans/ai", json=payload, headers={"Idempotency-Key": "no-consent"}).status_code
        == 409
    )
    actor = client.get("/api/v1/auth/me").json()
    with SessionLocal() as db:
        db.get(Creator, creator_profile["id"]).model_consent = True
        db.get(User, actor["id"]).role = "member"
        db.commit()
    assert (
        client.post(root + "/plans/ai", json=payload, headers={"Idempotency-Key": "member"}).status_code
        == 403
    )
    from creator.models import ModelConfig

    with SessionLocal() as db:
        db.get(User, actor["id"]).role = "owner"
        db.scalar(select(ModelConfig)).output_price = 1000000
        db.commit()
    queued = client.post(
        root + "/plans/ai",
        json={**payload, "max_cost_cents": 1},
        headers={"Idempotency-Key": "too-expensive"},
    ).json()

    def forbidden(*args, **kwargs):
        raise AssertionError("model must not be called")

    monkeypatch.setattr(httpx.Client, "post", forbidden)
    with SessionLocal() as db:
        process_pending(db)
        assert db.get(Run, queued["id"]).error_code == "BRIEF_BUDGET_EXCEEDED"
        assert db.scalar(select(BudgetEntry)) is None


def test_asset_revocation_invalidates_a_script_before_build(client, brand):
    from test_graphics import upload

    asset = upload(client, brand)
    b = create(client, brand, visual_mode="screen_demo", asset_ids=[asset["id"]])
    root = "/api/v1/creation-briefs/" + b["id"]
    plan = client.post(root + "/plans/manual", json={"expected_revision": 1, "confirmed": True}).json()
    assert plan["review"]["status"] == "needs_confirmation"
    client.patch("/api/v1/assets/" + asset["id"], json={"verified": False, "reason": "验收撤销"})
    assert client.get(root).json()["plans"][0]["stale"]
    assert (
        client.post(
            root + "/plans/" + plan["id"] + "/build", json={"expected_revision": 1, "confirmed": True}
        ).status_code
        == 422
    )
