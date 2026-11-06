from creator.db import SessionLocal
from creator.models import Content, Creator
from creator.production import video_document
from test_workflow import run_content


def test_long_content_title_is_preserved_without_overflowing_project_name(client, creator_profile):
    c = run_content(client, creator_profile)
    with SessionLocal() as db:
        content = db.get(Content, c["id"])
        content.title = "完整标题" * 40
        creator = db.get(Creator, creator_profile["id"])
        ir = video_document(db, content, creator, {"duration_sec": 30, "video_mode": "mg", "size": "wide"})
        assert len(ir["name"]) <= 120
        assert ir["shots"][0]["caption"] == content.title
