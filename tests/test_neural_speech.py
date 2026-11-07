import hashlib
import subprocess

import pytest

from creator import speech
from creator.errors import DomainError


@pytest.fixture
def configured_kokoro(tmp_path, monkeypatch):
    runtime = tmp_path / "python.exe"
    runtime.write_bytes(b"test runtime path")
    model = tmp_path / "model"
    model.mkdir()
    for name in ["model.onnx", "voices.bin", "tokens.txt", "lexicon-us-en.txt", "lexicon-zh.txt"]:
        (model / name).write_bytes(name.encode())
    (model / "espeak-ng-data").mkdir()
    monkeypatch.setenv("KOKORO_PYTHON", str(runtime))
    monkeypatch.setenv("KOKORO_MODEL_DIR", str(model))
    return model


def test_unconfigured_voice_is_not_advertised(monkeypatch):
    monkeypatch.delenv("KOKORO_PYTHON", raising=False)
    monkeypatch.delenv("KOKORO_MODEL_DIR", raising=False)
    monkeypatch.setattr(speech, "powershell", lambda *args: "[]")
    assert not any(v["id"].startswith("kokoro:") for v in speech.voices())


def test_neural_voice_has_real_model_identity(configured_kokoro, monkeypatch):
    monkeypatch.setattr(speech, "powershell", lambda *args: "[]")
    assert any(v["id"] == "kokoro:45" for v in speech.voices())
    before = speech.voice_snapshot("kokoro:45")
    assert before["provider"] == "kokoro_local@1"
    assert before["model_id"] == "kokoro-multi-lang-v1_0"
    assert before["model_sha256"] == hashlib.sha256(b"model.onnx").hexdigest()
    (configured_kokoro / "model.onnx").write_bytes(b"changed weights")
    assert speech.voice_snapshot("kokoro:45") != before


def test_neural_failure_never_switches_to_sapi(configured_kokoro, monkeypatch):
    monkeypatch.setattr(speech, "powershell", lambda *args: "[]")

    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired("test", 120)

    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(DomainError) as error:
        speech.synthesize("fixture", "brand", "一条测试旁白", "kokoro:45")
    assert error.value.code == "TTS_PROVIDER_UNAVAILABLE"
