import io
import json
import zipfile

import pytest
from PIL import Image

from creator.db import SessionLocal
from creator.models import Asset
from test_workflow import run_content


def document(*pages, size="portrait", theme="midnight"):
    return {
        "schema_version": "1.0",
        "renderer_version": "graphic_cards@1",
        "size": size,
        "theme": theme,
        "pages": list(pages)
        or [
            {
                "page_id": "cover",
                "template": "editorial",
                "heading": "真实功能笔记",
                "text": "只介绍已核实的产品信息",
            }
        ],
    }


def save(client, content, design):
    response = client.put(
        f"/api/v1/content/packages/{content['id']}/graphics",
        json={
            "expected_revision": content["revision"],
            "document": design,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def upload(client, brand, verified=True):
    image = Image.new("RGB", (600, 200), "#e74b63")
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    response = client.post(
        f"/api/v1/brands/{brand['id']}/assets",
        files={"file": ("test-synthetic.png", buffer.getvalue())},
        data={
            "source": "程序生成的测试色卡，不是真实软件界面",
            "license_note": "仅测试",
            "verified": str(verified).lower(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def render(client, content):
    response = client.post(
        f"/api/v1/content/packages/{content['id']}/graphics/render",
        json={"expected_revision": content["revision"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(
    "size,dimensions", [("portrait", (1080, 1440)), ("square", (1080, 1080)), ("landscape", (1920, 1080))]
)
def test_real_cards_preview_and_approved_handoff(client, creator_profile, brand, size, dimensions):
    content = run_content(client, creator_profile)
    asset = upload(client, brand)
    design = document(
        {
            "page_id": "a",
            "template": "editorial",
            "heading": "功能记录",
            "text": "已核实的信息与实际版本一起核对",
        },
        {"page_id": "b", "template": "checklist", "heading": "事实与来源"},
        {"page_id": "c", "template": "screenshot", "heading": "测试色卡", "asset_id": asset["id"]},
        size=size,
    )
    content = save(client, content, design)
    receipt = render(client, content)
    assert len(receipt["pages"]) == 3
    for index, page in enumerate(receipt["pages"]):
        preview = client.get(
            f"/api/v1/content/packages/{content['id']}/graphics/pages/{index}/preview",
            params={"revision": content["revision"]},
        )
        assert preview.status_code == 200
        image = Image.open(io.BytesIO(preview.content))
        assert image.size == dimensions and image.format == "PNG"
        assert len(page["png_sha256"]) == 64
    assert receipt["pages"][2]["asset"]["sha256"] == asset["sha256"]
    assert not receipt["cached"]
    cached = render(client, content)
    assert cached["cache_key"] == receipt["cache_key"] and cached["cached"]
    screenshot = receipt["pages"][2]
    rect = screenshot["layout"]["image_rect"]
    assert abs((rect[2] - rect[0]) / (rect[3] - rect[1]) - 3) < 0.02
    preview = client.get(
        f"/api/v1/content/packages/{content['id']}/graphics/pages/2/preview",
        params={"revision": content["revision"]},
    )
    image = Image.open(io.BytesIO(preview.content))
    assert image.getpixel(((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)) == (231, 75, 99)
    endpoint = f"/api/v1/content/packages/{content['id']}/graphics/pages/0/download"
    assert client.get(endpoint, params={"revision": content["revision"]}).status_code == 409
    assert (
        client.post(f"/api/v1/content/packages/{content['id']}/approve", json={"confirmed": True}).status_code
        == 200
    )
    jpg = client.get(endpoint, params={"revision": content["revision"], "format": "jpg"})
    assert jpg.status_code == 200 and Image.open(io.BytesIO(jpg.content)).format == "JPEG"
    package = client.post("/api/v1/manual-publication/packages", json={"content_id": content["id"]}).json()
    archive = client.get(f"/api/v1/manual-publication/packages/{package['id']}/download")
    with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
        assert {
            "cover.png",
            "images/01.png",
            "images/03.jpg",
            "graphics-project.json",
            "provenance.json",
        } <= set(z.namelist())
        provenance = json.loads(z.read("provenance.json"))
        assert provenance["graphics"]["pages"][2]["asset"]["source"].startswith("程序生成")
        assert z.read("cover.png") == z.read("images/01.png")


def test_graphic_save_invalidates_review_old_package_and_stale_editor(client, creator_profile):
    content = run_content(client, creator_profile)
    client.post(f"/api/v1/content/packages/{content['id']}/approve", json={"confirmed": True})
    package = client.post("/api/v1/manual-publication/packages", json={"content_id": content["id"]}).json()
    saved = save(client, content, document())
    assert saved["revision"] == content["revision"] + 1 and saved["approved_revision"] is None
    assert client.get(f"/api/v1/manual-publication/packages/{package['id']}/download").status_code == 409
    assert (
        client.put(
            f"/api/v1/content/packages/{content['id']}/graphics",
            json={"expected_revision": content["revision"], "document": document()},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/content/packages/{content['id']}/graphics/render",
            json={"expected_revision": content["revision"]},
        ).status_code
        == 409
    )


def test_graphic_claims_assets_permissions_and_freshness(client, creator_profile, brand):
    content = run_content(client, creator_profile)
    unverified = upload(client, brand, False)
    unsafe = document(
        {"page_id": "a", "template": "screenshot", "heading": "截图", "asset_id": unverified["id"]}
    )
    assert (
        client.put(
            f"/api/v1/content/packages/{content['id']}/graphics",
            json={"expected_revision": content["revision"], "document": unsafe},
        ).status_code
        == 409
    )
    content = save(
        client, content, document({"page_id": "a", "template": "editorial", "heading": "保证不封号"})
    )
    assert (
        client.post(f"/api/v1/content/packages/{content['id']}/approve", json={"confirmed": True}).status_code
        == 409
    )
    asset = upload(client, brand)
    content = save(
        client,
        content,
        document({"page_id": "a", "template": "screenshot", "heading": "测试图", "asset_id": asset["id"]}),
    )
    render(client, content)
    with SessionLocal() as db:
        db.get(Asset, asset["id"]).verified = False
        db.commit()
    assert (
        client.post(f"/api/v1/content/packages/{content['id']}/approve", json={"confirmed": True}).status_code
        == 409
    )
    assert (
        client.get(
            f"/api/v1/content/packages/{content['id']}/graphics/pages/0/preview",
            params={"revision": content["revision"]},
        ).status_code
        == 409
    )
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/register",
        json={"name": "其他工作区", "email": "graphic-other@example.org", "password": "TestGraphicOther123!"},
    )
    assert client.get(f"/api/v1/content/packages/{content['id']}/graphics").status_code == 404


def test_long_title_and_invalid_schema_are_not_silently_cut(client, creator_profile):
    content = run_content(client, creator_profile)
    content = save(
        client,
        content,
        document(
            {
                "page_id": "a",
                "template": "editorial",
                "heading": "中文长标题核对" * 22 + "完成",
                "text": "长标题应自适应字号，不得截掉结尾。",
            }
        ),
    )
    receipt = render(client, content)
    assert receipt["pages"][0]["heading"] == content["graphics"]["pages"][0]["heading"]
    invalid = document({"page_id": "a", "template": "editorial"}, {"page_id": "a", "template": "editorial"})
    assert (
        client.put(
            f"/api/v1/content/packages/{content['id']}/graphics",
            json={"expected_revision": content["revision"], "document": invalid},
        ).status_code
        == 422
    )


def test_changed_source_bytes_are_not_mislabeled_with_old_hash(client, creator_profile, brand):
    from creator.domains import file_path

    content = run_content(client, creator_profile)
    asset = upload(client, brand)
    content = save(
        client, content, document({"page_id": "a", "template": "screenshot", "asset_id": asset["id"]})
    )
    with SessionLocal() as db:
        stored = db.get(Asset, asset["id"])
        path = file_path(stored.workspace_id, stored.sha256, stored.suffix)
        Image.new("RGB", (600, 200), "#112233").save(path, "PNG")
    response = client.post(
        f"/api/v1/content/packages/{content['id']}/graphics/render",
        json={"expected_revision": content["revision"]},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GRAPHIC_ASSET_INTEGRITY"


def test_revoked_asset_blocks_existing_unreported_bundle(client, creator_profile, brand):
    content = run_content(client, creator_profile)
    asset = upload(client, brand)
    content = save(
        client, content, document({"page_id": "a", "template": "screenshot", "asset_id": asset["id"]})
    )
    render(client, content)
    assert (
        client.post(f"/api/v1/content/packages/{content['id']}/approve", json={"confirmed": True}).status_code
        == 200
    )
    package = client.post("/api/v1/manual-publication/packages", json={"content_id": content["id"]}).json()
    with SessionLocal() as db:
        db.get(Asset, asset["id"]).verified = False
        db.commit()
    assert client.get(f"/api/v1/manual-publication/packages/{package['id']}/download").status_code == 409
    assert (
        client.post(
            "/api/v1/manual-publication/records",
            json={
                "package_id": package["id"],
                "published_at": "2026-11-05T09:00:00Z",
                "checklist": [True] * 5,
            },
        ).status_code
        == 409
    )


def test_preview_cache_recovers_missing_file_and_document_matches_schema(client, creator_profile):
    from creator.domains import file_path, digest
    from creator.graphics import GraphicDocument
    from jsonschema import validate

    content = save(client, run_content(client, creator_profile), document())
    receipt = render(client, content)
    with SessionLocal() as db:
        from creator.models import Content

        stored = db.get(Content, content["id"])
        target = file_path(stored.workspace_id, receipt["pages"][0]["png_sha256"], ".png")
        target.write_bytes(b"damaged-cache-test")
    assert (
        client.get(
            f"/api/v1/content/packages/{content['id']}/graphics/pages/0/preview",
            params={"revision": content["revision"]},
        ).status_code
        == 409
    )
    repaired = render(client, content)
    assert repaired["cache_key"] == receipt["cache_key"] and not repaired["cached"]
    assert digest(target.read_bytes()) == receipt["pages"][0]["png_sha256"]
    project = client.get(f"/api/v1/content/packages/{content['id']}/graphics/project").json()
    validate(project["document"], GraphicDocument.model_json_schema())
    assert not project["reviewed"] and project["manual_publish_only"]


def test_overflow_does_not_commit_partial_preview_and_reported_history_is_locked(
    client, creator_profile, brand
):
    content = run_content(client, creator_profile)
    asset = upload(client, brand)
    content = save(
        client,
        content,
        document(
            {"page_id": "a", "template": "editorial"},
            {"page_id": "b", "template": "screenshot", "asset_id": asset["id"], "text": "文字" * 300},
        ),
    )
    response = client.post(
        f"/api/v1/content/packages/{content['id']}/graphics/render",
        json={"expected_revision": content["revision"]},
    )
    assert response.status_code == 422 and response.json()["error"]["code"] == "GRAPHIC_TEXT_OVERFLOW"
    assert client.get(f"/api/v1/content/packages/{content['id']}").json()["graphics_render"] is None
    content = save(client, content, document())
    render(client, content)
    client.post(f"/api/v1/content/packages/{content['id']}/approve", json={"confirmed": True})
    package = client.post("/api/v1/manual-publication/packages", json={"content_id": content["id"]}).json()
    response = client.post(
        "/api/v1/manual-publication/records",
        json={"package_id": package["id"], "published_at": "2026-11-05T09:00:00Z", "checklist": [True] * 5},
    )
    assert response.status_code == 201
    assert (
        client.put(
            f"/api/v1/content/packages/{content['id']}/graphics",
            json={"expected_revision": content["revision"], "document": document()},
        ).status_code
        == 409
    )
    assert (
        client.post(f"/api/v1/content/packages/{content['id']}/approve", json={"confirmed": True}).status_code
        == 409
    )
    assert (
        client.get(f"/api/v1/content/packages/{content['id']}").json()["status"] == "user_reported_published"
    )
