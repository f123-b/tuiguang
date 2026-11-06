from sqlalchemy import select

from creator.db import SessionLocal
from creator.jobs import process_pending
from creator.models import BudgetEntry, RenderJob, Run
from creator.video import process_render_jobs
from test_continuous_media import configure
from test_graphics import upload
from test_workflow import run_content


def test_content_edit_blocks_automatic_video_without_overwriting_user_work(client, creator_profile):
    configure(client, creator_profile, graphics=False, video=True)
    c = run_content(client, creator_profile)
    response = client.patch(
        "/api/v1/content/packages/" + c["id"], json={"expected_revision": 1, "title": "用户已修改的新稿"}
    )
    assert response.status_code == 200
    with SessionLocal() as db:
        process_render_jobs(db)
        assert db.scalar(select(RenderJob)).error_code == "VID_AUTOMATION_SOURCE_STALE"
        assert db.scalar(select(Run)).status == "failed"
        assert db.scalar(select(BudgetEntry)).status == "settled"
    latest = client.get("/api/v1/content/packages/" + c["id"]).json()
    assert latest["revision"] == 2 and latest["title"] == "用户已修改的新稿"


def test_revoked_frozen_source_is_not_silently_replaced_by_mg(client, creator_profile, brand, monkeypatch):
    asset = upload(client, brand)
    configure(client, creator_profile, video=True, video_mode="mixed", asset_id=asset["id"])
    client.post(
        "/api/v1/creators/" + creator_profile["id"] + "/run-today",
        headers={"Idempotency-Key": "source-revoked"},
    )
    client.patch("/api/v1/assets/" + asset["id"], json={"verified": False, "reason": "验收时撤销授权"})
    from creator.jobs import graph

    calls = []
    original = graph.invoke

    def spy(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(graph, "invoke", spy)
    with SessionLocal() as db:
        process_pending(db)
        run = db.scalar(select(Run))
        assert run.status == "failed" and run.error_code == "ASSET_LICENSE_UNVERIFIED"
        assert db.scalar(select(RenderJob)) is None
        assert db.scalar(select(BudgetEntry)) is None
    assert calls == []
