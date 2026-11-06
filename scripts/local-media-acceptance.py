"""Opt-in acceptance against an isolated, authenticated synthetic workspace.

Requires a private .data/final-qa-state.json created by the operator and actual
docs/evidence/final-source-recording.mp4 plus docs/evidence/final-dashboard.png.
Never discovers user credentials or enables a model. All calls use localhost.
"""

import hashlib
import io
import json
import math
import struct
import time
import wave
from pathlib import Path

import httpx

STATE = Path(".data/final-qa-state.json")
OUT = Path("docs/evidence")
state = json.loads(STATE.read_text(encoding="utf-8"))
client = httpx.Client(base_url="http://localhost:3000/api/v1", cookies=state["cookies"], timeout=120)


def request(method, path, **kwargs):
    response = client.request(method, path, **kwargs)
    assert response.is_success, (path, response.status_code, response.text[:500])
    return response.json()


def save():
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def upload(path, source):
    with path.open("rb") as stream:
        return request(
            "POST",
            f"/brands/{state['brand']['id']}/assets",
            files={"file": (path.name, stream)},
            data={"source": source, "license_note": "自行制作，仅本软件合成验收使用", "verified": "true"},
        )


def download(path, target):
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code)
    target.write_bytes(response.content)
    return {"bytes": len(response.content), "sha256": hashlib.sha256(response.content).hexdigest()}


def wait_render(video_id):
    for _ in range(180):
        jobs = request("GET", f"/videos/{video_id}/render-jobs")
        if jobs and jobs[0]["status"] in ("completed", "failed"):
            assert jobs[0]["status"] == "completed", jobs[0]
            return jobs[0]
        time.sleep(2)
    raise AssertionError("render timeout")


assert "合成测试" in request("GET", "/auth/me")["name"]
recording = state.get("recording")
if not recording:
    state["recording"] = upload(
        Path("docs/evidence/final-source-recording.mp4"),
        "2026-11-06 agent-browser 真实本地工作台操作录屏，30 秒，无界面重绘",
    )
    state["screenshot"] = upload(OUT / "final-dashboard.png", "同次真实工作台截图，合成测试工作区")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        wav.writeframes(
            b"".join(
                struct.pack("<h", int(600 * math.sin(2 * math.pi * 220 * i / 16000))) for i in range(32000)
            )
        )
    state["audio"] = request(
        "POST",
        f"/brands/{state['brand']['id']}/assets",
        files={"file": ("acceptance-tone.wav", buffer.getvalue())},
        data={
            "source": "程序生成 220Hz 验收音调，不是人声或第三方音乐",
            "license_note": "自行生成，仅验收",
            "verified": "true",
        },
    )
    save()

captions = [
    "叙流 · 本地开发验收",
    "先核实产品事实与来源",
    "编辑图文和视频工程",
    "人工复核后下载发布包",
    "由用户在官方页面手动发布",
]
state.setdefault("videos", {})
for mode in ("mg", "screen", "mixed"):
    if mode not in state["videos"]:
        shots = []
        for index, caption in enumerate(captions):
            media = mode == "screen" or (mode == "mixed" and index in (1, 3))
            shot = {
                "shot_id": f"s{index + 1}",
                "provider": "ffmpeg_media" if media else "pillow_mg",
                "kind": "screen_demo" if media else "motion_graphics",
                "duration_frames": 180,
                "caption": caption,
            }
            if media:
                shot.update(asset_id=state["recording"]["id"], trim_start_frame=index * 180)
            shots.append(shot)
        document = {
            "brand_id": state["brand"]["id"],
            "name": "30秒最终验收 · " + mode,
            "width": 1920,
            "height": 1080,
            "shots": shots,
            "subtitles": [
                {
                    "cue_id": f"c{i}",
                    "start_frame": i * 180,
                    "end_frame": (i + 1) * 180,
                    "text": "合成工作区验收 · " + text,
                }
                for i, text in enumerate(captions)
            ],
            "audio_tracks": [
                {
                    "track_id": "tone",
                    "asset_id": state["audio"]["id"],
                    "role": "music",
                    "start_frame": 0,
                    "duration_frames": 900,
                    "loop": True,
                    "volume_percent": 20,
                }
            ],
        }
        video = request("POST", "/videos/projects", json=document)
        state["videos"][mode] = video
        save()
        request("POST", f"/videos/{video['id']}/render")
    video = state["videos"][mode]
    job = wait_render(video["id"])
    receipt = job["receipt"]
    output = download(f"/videos/{video['id']}/download", OUT / f"final-{mode}-30s.mp4")
    assert output["sha256"] == receipt["sha256"]
    (OUT / f"final-{mode}-project.json").write_text(
        json.dumps(video["ir"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / f"final-{mode}-receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(mode, "PASS", json.dumps(output), flush=True)

# Changing one visual shot must reuse the other four clips, even with global subtitles/audio.
video = state["videos"]["mixed"]
if not state.get("cache_verified"):
    original = wait_render(video["id"])["receipt"]
    shot = {**video["ir"]["shots"][2], "caption": "只修改第三镜头，其他镜头复用"}
    changed = request("PATCH", f"/videos/{video['id']}/scenes/s3", json=shot)
    request("POST", f"/videos/{video['id']}/render")
    receipt = wait_render(video["id"])["receipt"]
    flags = [s["cached"] for s in receipt["shots"]]
    assert flags == [True, True, False, True, True], flags
    state["cache_verified"] = {"before": original, "after": receipt, "flags": flags}
    state["videos"]["mixed"] = changed
    save()
    (OUT / "final-local-cache.json").write_text(
        json.dumps(state["cache_verified"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Single-shot cache PASS", flags, flush=True)

print("All media acceptance checks completed. Synthetic evidence only; no paid call or publication.")
