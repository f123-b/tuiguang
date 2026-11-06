from creator.config import DATA_DIR
from creator.db import SessionLocal
from creator.models import Video
from creator.video import process_render_jobs
from test_video_workspace import project


def test_corrupt_final_output_can_be_rerendered_without_losing_shot_cache(client, brand):
    v = client.post("/api/v1/videos/projects", json=project(brand)).json()
    root = "/api/v1/videos/" + v["id"]
    first = client.post(root + "/render").json()
    with SessionLocal() as db:
        process_render_jobs(db)
    with SessionLocal() as db:
        current = db.get(Video, v["id"])
        target = DATA_DIR / current.workspace_id / "cache" / (current.output_hash + ".mp4")
        target.write_bytes(b"broken output")
    assert client.get(root + "/download").status_code == 409
    new = client.post(root + "/render").json()
    assert new["id"] != first["id"]
    with SessionLocal() as db:
        process_render_jobs(db)
    result = client.get(root + "/render-jobs").json()[0]
    assert result["status"] == "completed" and result["receipt"]["shots"][0]["cached"]
    assert client.get(root + "/download").status_code == 200
