from creator.db import SessionLocal
from creator.video import process_render_jobs
from test_continuous_media import configure
from test_workflow import run_content


def test_manual_video_edit_cannot_refresh_an_already_approved_content_binding(client, creator_profile):
    configure(client, creator_profile, graphics=False, video=True)
    c = run_content(client, creator_profile)
    with SessionLocal() as db:
        process_render_jobs(db)
    c = client.get("/api/v1/content/packages/" + c["id"]).json()
    video_id = c["video_attachment"]["video_id"]
    assert (
        client.post("/api/v1/content/packages/" + c["id"] + "/approve", json={"confirmed": True}).status_code
        == 200
    )
    video = client.get("/api/v1/videos/projects/" + video_id).json()
    shot = video["ir"]["shots"][2]
    shot["caption"] = "用户手动修改了第三镜头"
    assert client.patch("/api/v1/videos/" + video_id + "/scenes/s3", json=shot).status_code == 200
    assert client.post("/api/v1/videos/" + video_id + "/render").status_code == 201
    with SessionLocal() as db:
        process_render_jobs(db)
    current = client.get("/api/v1/content/packages/" + c["id"]).json()
    assert current["video_attachment"]["revision"] == 1
    assert client.post("/api/v1/manual-publication/packages", json={"content_id": c["id"]}).status_code == 409
