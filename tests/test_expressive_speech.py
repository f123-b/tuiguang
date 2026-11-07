import pytest
import json
import subprocess

from creator import speech
from creator.errors import DomainError
from creator.narration import NarrationOptions


def test_style_is_explicit_and_old_requests_default_to_plain():
    options = NarrationOptions(voice_id="old-system", usage_confirmed=True)
    assert options.delivery_style == "plain"
    warm = NarrationOptions(voice_id="qwen:serena", delivery_style="warm", usage_confirmed=True)
    assert warm.delivery_style == "warm"


def test_non_expressive_voice_never_silently_ignores_style():
    with pytest.raises(DomainError) as error:
        speech.delivery_snapshot("Microsoft Huihui Desktop", "warm")
    assert error.value.code == "TTS_STYLE_UNSUPPORTED"


def test_uninstalled_qwen_voice_is_not_advertised(monkeypatch):
    monkeypatch.delenv("QWEN_TTS_PYTHON", raising=False)
    monkeypatch.delenv("QWEN_TTS_MODEL_DIR", raising=False)
    monkeypatch.setattr(speech, "powershell", lambda *args: "[]")
    assert not any(v["id"].startswith("qwen:") for v in speech.voices())


@pytest.fixture
def configured_qwen(tmp_path, monkeypatch):
    from creator.expressive_speech import FILES

    runtime = tmp_path / "python.exe"
    runtime.write_bytes(b"test runtime")
    directory = tmp_path / "model"
    for name in FILES:
        file = directory / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(name.encode())
    (directory / "config.json").write_text(
        json.dumps({"tts_model_size": "1b7", "tts_model_type": "custom_voice"})
    )
    monkeypatch.setenv("QWEN_TTS_PYTHON", str(runtime))
    monkeypatch.setenv("QWEN_TTS_MODEL_DIR", str(directory))
    return directory


def test_style_and_tokenizer_are_frozen(configured_qwen):
    warm = speech.delivery_snapshot("qwen:serena", "warm")
    plain = speech.delivery_snapshot("qwen:serena")
    assert warm["instruction"] and not plain["instruction"]
    assert warm["seed"] == 37 and warm["delivery_version"] == "spoken_delivery@1"
    (configured_qwen / "speech_tokenizer/model.safetensors").write_bytes(b"changed")
    assert speech.delivery_snapshot("qwen:serena", "warm") != warm


def test_expressive_failure_never_falls_back(configured_qwen, monkeypatch, tmp_path):
    from creator.expressive_speech import synthesize

    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired("local test", 600)

    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(DomainError) as error:
        synthesize(tmp_path / "test.wav", "测试", "qwen:serena", 0, "warm")
    assert error.value.code == "TTS_PROVIDER_UNAVAILABLE"


def test_qwen_does_not_accept_artificial_speed_or_long_paragraph(configured_qwen, tmp_path):
    from creator.expressive_speech import synthesize

    with pytest.raises(DomainError) as error:
        synthesize(tmp_path / "test.wav", "测试", "qwen:serena", 2, "warm")
    assert error.value.code == "TTS_RATE_UNSUPPORTED"
    with pytest.raises(DomainError) as error:
        speech.synthesize("fixture", "brand", "字" * 601, "qwen:serena")
    assert error.value.code == "TTS_SCRIPT_INVALID"
