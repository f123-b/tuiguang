import os

import pytest


@pytest.mark.skipif(os.name != "nt", reason="Windows offline system voice unavailable on this OS")
def test_offline_voice_produces_real_unverified_asset(client, brand):
    voices = client.get("/api/v1/videos/voices").json()["voices"]
    if not voices:
        pytest.skip("No local voice installed")
    response = client.post(
        "/api/v1/videos/speech",
        json={
            "brand_id": brand["id"],
            "voice_id": voices[0]["id"],
            "text": "这是叙流离线语音功能的开发验收样例。",
            "confirmed": True,
        },
    )
    assert response.status_code == 201, response.text
    asset = response.json()
    assert asset["kind"] == "audio" and not asset["verified"]
    data = client.get(f"/api/v1/assets/{asset['id']}/download").content
    assert data[:4] == b"RIFF" and data[8:12] == b"WAVE" and len(data) > 10000
