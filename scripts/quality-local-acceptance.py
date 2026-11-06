"""Operate only the explicitly created synthetic local QA workspace.

Reads its private authenticated state; never reads or prints model credentials.
Produces a 30-second mixed preview and tests source-version invalidation.
"""

import io
import json
from pathlib import Path

import httpx
from PIL import Image, ImageDraw


def main():
    state = json.loads(Path(".data/final-qa-state.json").read_text(encoding="utf-8"))
    c = httpx.Client(base_url="http://localhost:8000/api/v1", cookies=state["cookies"], timeout=60)

    def req(method, path, **kwargs):
        result = c.request(method, path, **kwargs)
        assert result.is_success, (path, result.status_code, result.text)
        return result.json()

    brand_id = state["brand"]["id"]
    assert req("GET", "/auth/me")["name"] == "叙流最终验收（合成测试工作区）"
    source = req(
        "POST",
        f"/brands/{brand_id}/product-sources",
        json={
            "name": "本地验收版本说明（合成资料）",
            "kind": "uploaded_notes",
            "authorized": True,
        },
    )
    root = "/product-sources/" + source["id"]
    req(
        "POST",
        root + "/upload",
        files={"file": ("v1.md", "# 测试 v1\n合成资料，不是产品事实。".encode())},
        data={"version": "qa-v1", "confirmed": "true"},
    )
    image = Image.new("RGB", (320, 180), "#183f4c")
    ImageDraw.Draw(image).text((20, 70), "SYNTHETIC SOURCE QA", fill="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    asset = req(
        "POST",
        f"/brands/{brand_id}/assets",
        files={"file": ("source-qa.png", buffer.getvalue())},
        data={"source": "本脚本生成的合成验收图", "license_note": "本地测试自产素材", "verified": "true"},
    )
    req(
        "PUT",
        f"/assets/{asset['id']}/applicability",
        json={"confirmed": True, "source_id": source["id"], "product_version": "qa-v1"},
    )
    before = req("GET", "/brands")[0]["facts"]
    req(
        "POST",
        root + "/upload",
        files={"file": ("v2.md", "# 测试 v2\n这是待核实的测试变更，不自动批准新功能。".encode())},
        data={"version": "qa-v2", "confirmed": "true"},
    )
    events = req("GET", root + "/events")
    updated = next(a for a in req("GET", "/assets") if a["id"] == asset["id"])
    assert updated["applicability_status"] == "needs_review" and not updated["verified"]
    assert len(events) == 1 and req("GET", "/brands")[0]["facts"] == before
    req("PATCH", root, json={"expected_revision": 1, "enabled": False, "confirmed": True})
    existing = req("GET", "/videos/projects/9a9bea54e0f744aa9e3a603f978961e4")
    document = {
        k: existing["ir"][k]
        for k in ("brand_id", "width", "height", "fps", "shots", "audio_tracks", "subtitles")
    }
    document.update(name="质量流程验收 · 30 秒混合视频", preview_required=True)
    video = req("POST", "/videos/projects", json=document)
    root = "/videos/" + video["id"]
    assert c.post(root + "/render").status_code == 409
    report = req("POST", root + "/quality", json={"confirmed": True})
    preview = req("POST", root + "/preview", json={"expected_revision": 1, "confirmed": True})
    result = {
        "source": source["id"],
        "source_event": events[0]["id"],
        "asset": asset["id"],
        "video": video["id"],
        "report": report["id"],
        "preview_job": preview["id"],
    }
    Path(".data/quality-qa-state.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Source change invalidation passed; 30-second preview queued:", result)


if __name__ == "__main__":
    main()
