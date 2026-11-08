import os

import pytest


@pytest.mark.skipif(os.name != "nt", reason="Windows offline system voice unavailable on this OS")
def test_offline_voice_produces_real_unverified_asset(client, brand):
    voices = client.get("/api/v1/videos/voices").json()["voices"]
    # This Windows smoke test exercises SAPI, without contending with optional GPU jobs.
    system_voices = [v for v in voices if not v["id"].startswith(("qwen:", "kokoro:"))]
    if not system_voices:
        pytest.skip("No Windows system voice installed")
    response = client.post(
        "/api/v1/videos/speech",
        json={
            "brand_id": brand["id"],
            "voice_id": system_voices[0]["id"],
            "text": "这是叙流离线语音功能的开发验收样例。",
            "confirmed": True,
        },
    )
    assert response.status_code == 201, response.text
    asset = response.json()
    assert asset["kind"] == "audio" and not asset["verified"]
    data = client.get(f"/api/v1/assets/{asset['id']}/download").content
    assert data[:4] == b"RIFF" and data[8:12] == b"WAVE" and len(data) > 10000
