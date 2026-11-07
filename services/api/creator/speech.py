"""Installed local voices. No cloud calls or bundled model weights."""

import json
import os
import subprocess

from .config import DATA_DIR
from .domains import store_file
from .errors import DomainError
from .models import Asset, uid


def powershell(script, payload=None):
    if os.name != "nt":
        raise DomainError("TTS_PROVIDER_UNAVAILABLE", "本机没有已接通的离线语音服务", 422)
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-Command",
                "[Console]::InputEncoding = [Text.Encoding]::UTF8; [Console]::OutputEncoding = [Text.Encoding]::UTF8; Add-Type -AssemblyName System.Speech; "
                + script,
            ],
            input=json.dumps(payload, ensure_ascii=False) if payload else "",
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=90,
            check=True,
        )
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        raise DomainError(
            "TTS_PROVIDER_UNAVAILABLE", "离线语音合成未完成，请检查系统已安装的语音；未调用云端服务", 422
        ) from None


def voices():
    from . import expressive_speech, neural_speech

    local = expressive_speech.voices() + neural_speech.voices()
    if os.name != "nt":
        return local
    try:
        result = powershell(
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; try { @($s.GetInstalledVoices() | Where-Object Enabled | ForEach-Object { @{ id=$_.VoiceInfo.Name; language=$_.VoiceInfo.Culture.Name } }) | ConvertTo-Json -Compress } finally { $s.Dispose() }"
        )
        data = json.loads(result or "[]")
        return local + (data if isinstance(data, list) else [data])
    except (DomainError, ValueError):
        return local


def voice_snapshot(voice):
    if voice.startswith("qwen:"):
        from .expressive_speech import snapshot

        return snapshot(voice)
    if voice.startswith("kokoro:"):
        from .neural_speech import snapshot

        return snapshot(voice)
    return {"provider": "windows_sapi", "voice_id": voice}


def delivery_snapshot(voice, style="plain"):
    if style == "plain":
        return voice_snapshot(voice)
    if not voice.startswith("qwen:"):
        raise DomainError("TTS_STYLE_UNSUPPORTED", "此声音不支持语气指导，请选择原声表达或语气配音", 422)
    from .expressive_speech import snapshot

    return snapshot(voice, style)


def synthesize(workspace_id, brand_id, text, voice, rate=0, delivery_style="plain"):
    if voice.startswith("qwen:") and len(text) > 600:
        raise DomainError("TTS_SCRIPT_INVALID", "语气配音每段最多 600 字，请拆分镜头", 422)
    if voice not in {v["id"] for v in voices()}:
        raise DomainError("TTS_PROVIDER_UNAVAILABLE", "请选择本机真实安装的语音", 422)
    directory = DATA_DIR / workspace_id / "speech-tmp"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (uid() + ".wav")
    try:
        identity = delivery_snapshot(voice, delivery_style)
        if voice.startswith("qwen:"):
            from .expressive_speech import synthesize as expressive_synthesize

            identity = expressive_synthesize(target, text, voice, rate, delivery_style)
        elif voice.startswith("kokoro:"):
            from .neural_speech import synthesize as neural_synthesize

            identity = neural_synthesize(target, text, voice, rate)
        else:
            powershell(
                "$d = [Console]::In.ReadToEnd() | ConvertFrom-Json; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; try { $s.SelectVoice($d.voice); $s.Rate = [int]$d.rate; $s.SetOutputToWaveFile($d.path); $s.Speak($d.text) } finally { $s.Dispose() }",
                {"text": text, "voice": voice, "rate": rate, "path": str(target)},
            )
        data = target.read_bytes()
        if not 44 < len(data) <= 50 * 1024 * 1024:
            raise DomainError("TTS_RESULT_INVALID", "离线语音没有产生有效文件", 422)
        sha = store_file(workspace_id, data, ".wav")
        asset = Asset(
            workspace_id=workspace_id,
            brand_id=brand_id,
            name="离线配音.wav",
            sha256=sha,
            suffix=".wav",
            kind="audio",
            source="用户提交文本 / " + json.dumps(identity, ensure_ascii=False, sort_keys=True),
            license_note="本地语音输出；请按实际系统声音或所用模型/运行时许可核实用途，不代表商业授权认证。",
            verified=False,
        )
        asset.synthesis_receipt = identity
        return asset
    finally:
        target.unlink(missing_ok=True)
