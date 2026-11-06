from creator.db import SessionLocal
from creator.video import process_render_jobs
import pytest
from test_video_workspace import project
from test_workflow import run_content


def test_preview_review_then_final_and_edit_invalidates(client, brand):
    data = project(brand, preview_required=True)
    v = client.post("/api/v1/videos/projects", json=data)
    assert v.status_code == 201, v.text
    v = v.json()
    root = "/api/v1/videos/" + v["id"]
    assert client.post(root + "/render").status_code == 409
    report = client.post(root + "/quality", json={"confirmed": True}).json()
    queued = client.post(root + "/preview", json={"expected_revision": 1, "confirmed": True})
    assert queued.status_code == 201, queued.text
    with SessionLocal() as db:
        process_render_jobs(db)
    preview = client.get(root + "/render-jobs").json()[0]
    assert preview["status"] == "completed", preview
    assert preview["receipt"]["purpose"] == "preview"
    assert preview["receipt"]["width"] == 360
    assert preview["receipt"]["watermark"] is True
    assert client.get(root + "/preview/download").status_code == 200
    assert client.get(root + "/download").status_code != 200
    reviewed = client.post(
        root + "/quality-review",
        json={
            "expected_revision": 1,
            "confirmed": True,
            "preview_job_id": preview["id"],
            "report_id": report["id"],
            "decision": "accept",
            "note": "已播放并核对字幕和事实来源",
        },
    )
    assert reviewed.status_code == 201, reviewed.text
    assert client.post(root + "/render").status_code == 201
    with SessionLocal() as db:
        process_render_jobs(db)
    final = client.get(root + "/render-jobs").json()[0]
    assert final["receipt"]["purpose"] == "final" and final["receipt"]["width"] == 1080
    assert client.get(root + "/download").status_code == 200
    data["shots"][0]["caption"] = "修改后必须重新预览"
    data["preview_required"] = False
    saved = client.put(root + "/project", json={"expected_revision": 1, "document": data})
    assert saved.status_code == 200
    assert saved.json()["preview_required"] is True
    assert client.post(root + "/render").status_code == 409
    assert client.get(root + "/preview/download").status_code != 200


def test_quality_immutable_duplicate_evidence_and_tenant(client, creator_profile):
    c = run_content(client, creator_profile)
    root = "/api/v1/content/packages/" + c["id"]
    first = client.post(root + "/quality", json={"confirmed": True})
    assert first.status_code == 201, first.text
    same = client.post(root + "/quality", json={"confirmed": True})
    assert same.json()["id"] == first.json()["id"]
    client.patch(root, json={"expected_revision": c["revision"], "title": "新的内容标题"})
    second = client.post(root + "/quality", json={"confirmed": True})
    assert second.json()["id"] != first.json()["id"]
    reports = client.get(root + "/quality").json()
    assert len(reports) == 2 and reports[-1]["subject_revision"] == 1
    assert any(x["status"] == "unknown" for x in first.json()["report"]["checks"])
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-quality@example.org",
            "password": "OtherPassword987!",
            "name": "另一工作区",
        },
    )
    assert client.get(root + "/quality").status_code == 404


def test_corrupt_preview_and_brand_change_cancel_confirmation(client, brand):
    from creator.config import DATA_DIR
    from creator.models import Brand

    v = client.post("/api/v1/videos/projects", json=project(brand, preview_required=True)).json()
    root = "/api/v1/videos/" + v["id"]
    r = client.post(root + "/quality", json={"confirmed": True}).json()
    client.post(root + "/preview", json={"expected_revision": 1, "confirmed": True})
    with SessionLocal() as db:
        process_render_jobs(db)
    j = client.get(root + "/render-jobs").json()[0]
    payload = {
        "expected_revision": 1,
        "confirmed": True,
        "preview_job_id": j["id"],
        "report_id": r["id"],
        "decision": "accept",
        "note": "已逐项复核预览",
    }
    assert client.post(root + "/quality-review", json=payload).status_code == 201
    with SessionLocal() as db:
        db.get(Brand, brand["id"]).revision += 1
        db.commit()
    assert client.post(root + "/render").status_code == 409
    assert client.post(root + "/quality-review", json=payload).status_code == 409
    from creator.models import RenderJob

    with SessionLocal() as db:
        workspace = db.get(RenderJob, j["id"]).workspace_id
    path = DATA_DIR / workspace / "cache" / (j["receipt"]["sha256"] + ".mp4")
    path.write_bytes(b"corrupted preview")
    assert client.get(root + "/preview/download").status_code == 409
    assert (
        client.post(root + "/preview", json={"expected_revision": 1, "confirmed": True}).json()["id"]
        != j["id"]
    )


def test_automatic_video_stops_at_preview_until_manual_review(client, creator_profile):
    from test_continuous_media import configure
    from creator.models import Run

    configure(client, creator_profile, video=True, review_preview_before_final=True)
    c = run_content(client, creator_profile)
    root = "/api/v1/videos/" + c["video_attachment"]["video_id"]
    with SessionLocal() as db:
        process_render_jobs(db)
        run = db.get(Run, c["run_id"])
        assert run.status == "awaiting_review"
    updated = client.get("/api/v1/content/packages/" + c["id"]).json()
    assert updated["status"] == "needs_preview_review" and updated["video_attachment"]["sha256"] is None
    assert (
        client.post("/api/v1/content/packages/" + c["id"] + "/approve", json={"confirmed": True}).status_code
        == 409
    )
    report = client.post(root + "/quality", json={"confirmed": True}).json()
    preview = client.get(root + "/render-jobs").json()[0]
    assert (
        client.post(
            root + "/quality-review",
            json={
                "expected_revision": 1,
                "confirmed": True,
                "preview_job_id": preview["id"],
                "report_id": report["id"],
                "decision": "accept",
                "note": "已播放并核对字幕和功能事实",
            },
        ).status_code
        == 201
    )
    assert client.post(root + "/render").status_code == 201
    with SessionLocal() as db:
        process_render_jobs(db)
        assert db.get(Run, c["run_id"]).status == "completed"
    assert client.get("/api/v1/content/packages/" + c["id"]).json()["video_attachment"]["sha256"]


def test_model_critique_is_opt_in_budgeted_and_does_not_edit(client, creator_profile, monkeypatch):
    import json
    import httpx
    from sqlalchemy import select
    from creator.jobs import process_pending
    from creator.models import BudgetEntry, Creator, Run
    from test_model_workspace import configure

    c = run_content(client, creator_profile)
    configure(client)
    root = "/api/v1/content/packages/" + c["id"]
    data = {
        "creator_id": creator_profile["id"],
        "expected_revision": c["revision"],
        "confirmed": True,
        "max_cost_cents": 100,
    }
    assert (
        client.post(root + "/quality/ai", json=data, headers={"Idempotency-Key": "quality-one"}).status_code
        == 409
    )
    with SessionLocal() as db:
        db.get(Creator, creator_profile["id"]).model_consent = True
        db.commit()
    queued = client.post(root + "/quality/ai", json=data, headers={"Idempotency-Key": "quality-one"})
    assert queued.status_code == 201, queued.text
    assert (
        client.post(root + "/quality/ai", json=data, headers={"Idempotency-Key": "quality-one"}).json()["id"]
        == queued.json()["id"]
    )
    calls = []

    def reply(self, url, **kwargs):
        calls.append(kwargs["json"])
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "opening": "不确定，需要人工判断",
                                    "focus": "请保留一个收益点",
                                    "audience": "核对目标受众",
                                    "purpose": "核对行动引导",
                                    "suggestions": ["增加真实操作示例"],
                                    "evidence_refs": [c["id"]],
                                    "decision": "human_review",
                                }
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10},
            },
        )

    monkeypatch.setattr(httpx.Client, "post", reply)
    with SessionLocal() as db:
        process_pending(db)
        process_pending(db)
        run = db.get(Run, queued.json()["id"])
        assert run.status == "completed" and len(run.slot) <= 30
        assert db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == run.id)).actual_cents == 1
    assert len(calls) == 1
    reports = client.get(root + "/quality").json()
    assert reports[0]["report"]["method"] == "model_suggestion"
    current = client.get(root).json()
    assert (
        current["title"] == c["title"]
        and current["revision"] == c["revision"]
        and current["approved_revision"] is None
    )


@pytest.mark.parametrize("failure_kind", ["timeout", "empty_choices"])
def test_quality_unknown_response_is_not_retried_or_free(client, creator_profile, monkeypatch, failure_kind):
    import httpx
    from sqlalchemy import select
    from creator.jobs import process_pending
    from creator.models import BudgetEntry, Creator, Run
    from test_model_workspace import configure

    c = run_content(client, creator_profile)
    configure(client)
    with SessionLocal() as db:
        db.get(Creator, creator_profile["id"]).model_consent = True
        db.commit()
    queued = client.post(
        "/api/v1/content/packages/" + c["id"] + "/quality/ai",
        json={
            "creator_id": creator_profile["id"],
            "expected_revision": 1,
            "confirmed": True,
            "max_cost_cents": 100,
        },
        headers={"Idempotency-Key": "quality-timeout"},
    ).json()
    calls = []

    def timeout(*args, **kwargs):
        calls.append(1)
        if failure_kind == "empty_choices":
            return httpx.Response(
                200,
                request=httpx.Request("POST", args[1]),
                json={
                    "choices": [],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 0},
                },
            )
        raise httpx.ReadTimeout("synthetic timeout")

    monkeypatch.setattr(httpx.Client, "post", timeout)
    with SessionLocal() as db:
        process_pending(db)
        process_pending(db)
        run = db.get(Run, queued["id"])
        ledger = db.scalar(select(BudgetEntry).where(BudgetEntry.run_id == run.id))
        assert run.error_code == "AGENT_PROVIDER_RESULT_UNKNOWN"
        assert ledger.actual_cents is None and ledger.reserved_cents > 0
    assert len(calls) == 1


def test_duplicate_title_and_shot_structure_show_real_peer_ids(client, creator_profile, brand):
    from creator.models import Content, Run
    from creator.observability import release_manifest

    c = run_content(client, creator_profile)
    with SessionLocal() as db:
        run = Run(
            workspace_id=db.get(Content, c["id"]).workspace_id,
            creator_id=creator_profile["id"],
            operational_date="2026-11-01",
            slot="quality-test",
            idempotency_key="duplicate-evidence",
            release=release_manifest(),
        )
        db.add(run)
        db.flush()
        peer = Content(
            workspace_id=run.workspace_id,
            creator_id=creator_profile["id"],
            run_id=run.id,
            title=c["title"],
            body=c["body"],
            platform=c["platform"],
            generation_source="template",
            fact_refs=c["fact_refs"],
        )
        db.add(peer)
        db.commit()
        peer_id = peer.id
    report = client.post("/api/v1/content/packages/" + c["id"] + "/quality", json={"confirmed": True}).json()[
        "report"
    ]
    duplicates = next(x for x in report["checks"] if x["key"] == "duplicates")
    assert duplicates["status"] == "needs_review" and duplicates["evidence"]["matches"][0]["id"] == peer_id
    v1 = client.post("/api/v1/videos/projects", json=project(brand)).json()
    v2 = client.post("/api/v1/videos/projects", json=project(brand)).json()
    report = client.post("/api/v1/videos/" + v2["id"] + "/quality", json={"confirmed": True}).json()["report"]
    shots = next(x for x in report["checks"] if x["key"] == "shots")
    assert shots["evidence"]["same_structure"] == [v1["id"]]


def test_official_deepseek_json_adapter_does_not_change_other_gateways():
    from creator.model_gateway import payload

    settings = {"base_url": "https://api.deepseek.com", "model": "deepseek-flash", "max_tokens": 512}
    assert payload(settings, [])["thinking"] == {"type": "disabled"}
    settings["base_url"] = "https://gateway.example.org/v1"
    assert "thinking" not in payload(settings, [])


def test_edit_during_final_render_cannot_publish_old_bytes(client, brand, monkeypatch):
    import creator.video as engine

    data = project(brand, preview_required=True)
    v = client.post("/api/v1/videos/projects", json=data).json()
    root = "/api/v1/videos/" + v["id"]
    report = client.post(root + "/quality", json={"confirmed": True}).json()
    client.post(root + "/preview", json={"expected_revision": 1, "confirmed": True})
    with SessionLocal() as db:
        process_render_jobs(db)
    j = client.get(root + "/render-jobs").json()[0]
    assert (
        client.post(
            root + "/quality-review",
            json={
                "expected_revision": 1,
                "confirmed": True,
                "preview_job_id": j["id"],
                "report_id": report["id"],
                "decision": "accept",
                "note": "合成验收已核对",
            },
        ).status_code
        == 201
    )
    client.post(root + "/render")
    original = engine.render_project

    def render_then_edit(db, job):
        result = original(db, job)
        data["shots"][0]["caption"] = "渲染期间保存的新版本"
        saved = client.put(root + "/project", json={"expected_revision": 1, "document": data})
        assert saved.status_code == 200, saved.text
        return result

    monkeypatch.setattr(engine, "render_project", render_then_edit)
    with SessionLocal() as db:
        process_render_jobs(db)
    current = client.get("/api/v1/videos/projects/" + v["id"]).json()
    assert current["revision"] == 2 and current["status"] == "draft"
    assert client.get(root + "/download").status_code != 200
    final = client.get(root + "/render-jobs").json()[0]
    assert final["status"] == "failed" and final["error_code"] == "QUALITY_REVIEW_REQUIRED"
