import io
import zipfile

from test_workflow import run_content
from test_graphics import upload


def test_product_claim_requires_released_confirmation(client, creator_profile, brand):
    path = f"/api/v1/brands/{brand['id']}/changes"
    result = client.post(
        path, json={"claim": "新增未上线能力", "source": "用户上传的 2.0 规划说明", "product_version": "2.0"}
    )
    assert result.status_code == 201, result.text
    proposal = result.json()
    assert not any(f["claim"] == proposal["claim"] for f in client.get("/api/v1/brands").json()[0]["facts"])
    decision = path + "/" + proposal["id"] + "/decide"
    assert (
        client.post(
            decision,
            json={"decision": "verified", "released": False, "confirmed": True, "expected_brand_revision": 1},
        ).status_code
        == 422
    )
    accepted = client.post(
        decision,
        json={"decision": "verified", "released": True, "confirmed": True, "expected_brand_revision": 1},
    )
    assert accepted.status_code == 200, accepted.text
    current = client.get("/api/v1/brands").json()[0]
    assert current["revision"] == 2 and current["facts"][-1]["verified"]
    assert (
        client.post(
            decision,
            json={"decision": "verified", "released": True, "confirmed": True, "expected_brand_revision": 2},
        ).status_code
        == 409
    )


def test_history_restores_as_new_revision_and_variants_are_reviewed(client, creator_profile):
    c = run_content(client, creator_profile)
    root = "/api/v1/content/packages/" + c["id"]
    changed = client.patch(
        root,
        json={
            "expected_revision": 1,
            "title": "克制的新版",
            "reason_tag": "too_advertising",
            "variants": {"douyin": {"title": "功能记录", "body": "仅介绍已核实的信息", "tags": ["软件笔记"]}},
        },
    )
    assert changed.status_code == 200, changed.text
    history = client.get(root + "/history").json()
    assert [h["revision"] for h in history] == [2, 1]
    assert history[0]["reason_tag"] == "too_advertising"
    assert (
        client.post(root + "/restore/1", json={"expected_revision": 1, "confirmed": True}).status_code == 409
    )
    restored = client.post(root + "/restore/1", json={"expected_revision": 2, "confirmed": True})
    assert restored.status_code == 200, restored.text
    assert restored.json()["revision"] == 3 and restored.json()["title"] == c["title"]
    invalid = client.patch(
        root, json={"expected_revision": 3, "variants": {"douyin": {"title": "世界第一", "body": "绝对安全"}}}
    )
    assert invalid.status_code == 200
    assert client.post(root + "/approve", json={"confirmed": True, "expected_revision": 4}).status_code == 409
    client.patch(
        root,
        json={"expected_revision": 4, "variants": {"douyin": {"title": "功能介绍", "body": "有来源的信息"}}},
    )
    assert client.post(root + "/approve", json={"confirmed": True}).status_code == 200
    package = client.post("/api/v1/manual-publication/packages", json={"content_id": c["id"]}).json()
    data = client.get(f"/api/v1/manual-publication/packages/{package['id']}/download")
    with zipfile.ZipFile(io.BytesIO(data.content)) as z:
        assert "variants/douyin.txt" in z.namelist()


def test_asset_revoke_and_history_are_tenant_scoped(client, creator_profile, brand):
    c = run_content(client, creator_profile)
    a = upload(client, brand)
    revoked = client.patch("/api/v1/assets/" + a["id"], json={"verified": False, "reason": "版本已过期"})
    assert revoked.status_code == 200 and not revoked.json()["verified"]
    client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.org", "password": "OtherPassword123!", "name": "其他工作区"},
    )
    assert client.get("/api/v1/content/packages/" + c["id"] + "/history").status_code == 404
    assert (
        client.patch("/api/v1/assets/" + a["id"], json={"verified": True, "reason": "无权操作"}).status_code
        == 404
    )
