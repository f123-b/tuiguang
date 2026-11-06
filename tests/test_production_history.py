from creator.db import SessionLocal
from creator.video import process_render_jobs
from test_continuous_media import configure
from test_workflow import run_content


def test_automatic_media_trace_and_reported_history_stay_frozen(client, creator_profile):
    configure(client, creator_profile, video=True)
    c = run_content(client, creator_profile)
    with SessionLocal() as db:
        process_render_jobs(db)
    content = client.get("/api/v1/content/packages/" + c["id"]).json()
    video_id = content["video_attachment"]["video_id"]
    diagnostic = client.get("/api/v1/creator-runs/" + content["run_id"] + "/diagnostic").json()
    assert sum(r["stage"] == "shot.render" for r in diagnostic["receipts"]) == 5
    client.post("/api/v1/content/packages/" + c["id"] + "/approve", json={"confirmed": True})
    package = client.post("/api/v1/manual-publication/packages", json={"content_id": c["id"]}).json()
    reported = client.post(
        "/api/v1/manual-publication/records",
        json={
            "package_id": package["id"],
            "published_at": "2026-11-06T09:00:00+08:00",
            "checklist": [True] * 5,
        },
    )
    assert reported.status_code == 201, reported.text
    before = client.get("/api/v1/content/packages/" + c["id"]).json()
    assert client.post("/api/v1/videos/" + video_id + "/render").status_code == 409
    after = client.get("/api/v1/content/packages/" + c["id"]).json()
    assert after == before
