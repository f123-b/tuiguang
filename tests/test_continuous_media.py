import io
import zipfile
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from creator.db import SessionLocal
from creator.errors import DomainError
from creator.jobs import process_pending, schedule_due
from creator.models import BudgetEntry, Content, Creator, RenderJob, Run
from creator.video import process_render_jobs
from test_graphics import upload
from test_workflow import run_content


def configure(client, creator, **options):
    keys = (
        "brand_id",
        "name",
        "timezone",
        "hour",
        "weekdays",
        "style",
        "platform",
        "daily_budget_cents",
        "monthly_budget_cents",
        "model_consent",
    )
    payload = {k: creator[k] for k in keys}
    payload["render_options"] = {
        "graphics": True,
        "video": False,
        "duration_sec": 3,
        "video_mode": "mg",
        "size": "wide",
        "asset_id": None,
        **options,
    }
    result = client.patch("/api/v1/creators/" + creator["id"], json=payload)
    assert result.status_code == 200, result.text


def test_scheduled_media_pause_and_real_handoff(client, creator_profile, brand):
    asset = upload(client, brand)
    configure(client, creator_profile, video=True, video_mode="mixed", asset_id=asset["id"])
    c = run_content(client, creator_profile)
    assert c["graphics"] and c["graphics_render"] and c["video_attachment"]
    assert c["approved_revision"] is None and c["status"] == "asset_rendering"
    video_id = c["video_attachment"]["video_id"]
    client.post("/api/v1/creators/" + creator_profile["id"] + "/pause")
    with SessionLocal() as db:
        process_render_jobs(db)
        assert db.scalar(select(RenderJob)).status == "queued"
    client.post("/api/v1/creators/" + creator_profile["id"] + "/resume")
    with SessionLocal() as db:
        process_render_jobs(db)
    done = client.get("/api/v1/content/packages/" + c["id"]).json()
    assert done["status"] == "awaiting_user_review" and len(done["video_attachment"]["sha256"]) == 64
    assert client.get("/api/v1/videos/" + video_id + "/download").status_code == 200
    assert (
        client.post("/api/v1/content/packages/" + c["id"] + "/approve", json={"confirmed": True}).status_code
        == 200
    )
    package = client.post("/api/v1/manual-publication/packages", json={"content_id": c["id"]}).json()
    with zipfile.ZipFile(
        io.BytesIO(client.get("/api/v1/manual-publication/packages/" + package["id"] + "/download").content)
    ) as z:
        assert {
            "images/01.png",
            "graphics-project.json",
            "video.mp4",
            "video-project.json",
            "subtitles.srt",
        } <= set(z.namelist())


def test_failed_media_keeps_known_cost_and_never_repeats_draft(client, creator_profile, monkeypatch):
    configure(client, creator_profile)
    import creator.production as production

    calls = []
    from creator.jobs import graph

    original = graph.invoke

    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    def fail(*args, **kwargs):
        raise DomainError("QA_TEST_RENDER_FAILURE", "故障注入测试")

    monkeypatch.setattr(graph, "invoke", counted)
    monkeypatch.setattr(production, "render_graphics", fail)
    run_content(client, creator_profile)
    with SessionLocal() as db:
        process_pending(db)
        assert db.scalar(select(BudgetEntry)).status == "settled"
        assert db.scalar(select(BudgetEntry)).actual_cents == 0
        assert db.scalar(select(Run)).status == "failed"
        assert len(db.scalars(select(Content)).all()) == 1
    assert len(calls) == 1


def test_fourteen_day_virtual_clock_produces_reviewable_cards(client, creator_profile):
    configure(client, creator_profile)
    with SessionLocal() as db:
        for offset in range(14):
            schedule_due(db, datetime(2026, 12, 1, 3, tzinfo=timezone.utc) + timedelta(days=offset))
            process_pending(db)
        contents = db.scalars(select(Content)).all()
        assert len(contents) == 14
        assert all(c.graphics_render and c.approved_revision is None for c in contents)
        assert len({c.title for c in contents}) == 14
        assert db.get(Creator, creator_profile["id"]).status == "active"
