import pytest

from creator.db import SessionLocal
from creator.domains import file_path
from creator.models import Asset, Handoff
from test_graphics import upload
from test_workflow import run_content


@pytest.mark.parametrize("missing", [False, True])
def test_handoff_does_not_serve_missing_or_corrupt_bytes(client, creator_profile, missing):
    content = run_content(client, creator_profile)
    client.post(f"/api/v1/content/packages/{content['id']}/approve", json={"confirmed": True})
    package = client.post("/api/v1/manual-publication/packages", json={"content_id": content["id"]}).json()
    with SessionLocal() as db:
        stored = db.get(Handoff, package["id"])
        path = file_path(stored.workspace_id, stored.sha256, ".zip")
        if missing:
            path.unlink()
        else:
            path.write_bytes(b"corrupt acceptance file")
    response = client.get(f"/api/v1/manual-publication/packages/{package['id']}/download")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ARTIFACT_INTEGRITY_FAILED"


def test_asset_and_private_export_reject_corruption(client, brand):
    asset = upload(client, brand)
    with SessionLocal() as db:
        stored = db.get(Asset, asset["id"])
        file_path(stored.workspace_id, stored.sha256, stored.suffix).write_bytes(b"corrupt image")
    assert client.get(f"/api/v1/assets/{asset['id']}/download").status_code == 422
    assert client.get("/api/v1/settings/export?include_files=true").status_code == 422
