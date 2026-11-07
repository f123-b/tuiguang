"""Opt-in external local runtime; no model download or network in this adapter."""

import hashlib
import json
import os
import subprocess
from functools import lru_cache
from pathlib import Path

from .config import ROOT
from .errors import DomainError

VERSION = "kokoro_local@1"
SPEAKERS = {45: "晓贝 · 女声", 46: "晓妮 · 女声", 49: "云健 · 男声", 50: "云希 · 男声"}
FILES = ("model.onnx", "voices.bin", "tokens.txt", "lexicon-us-en.txt", "lexicon-zh.txt")


def configuration():
    runtime, directory = os.getenv("KOKORO_PYTHON", ""), os.getenv("KOKORO_MODEL_DIR", "")
    if not runtime or not directory:
        return None
    model = Path(directory)
    if not Path(runtime).is_file() or not all((model / f).is_file() for f in FILES):
        return None
    if not (model / "espeak-ng-data").is_dir():
        return None
    return runtime, model


def voices():
    if not configuration():
        return []
    return [
        {"id": f"kokoro:{sid}", "label": f"本地神经配音 · {name}", "language": "zh-CN"}
        for sid, name in SPEAKERS.items()
    ]


@lru_cache(maxsize=32)
def checksum(path, size, modified):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def snapshot(voice):
    config = configuration()
    if not config or voice not in {v["id"] for v in voices()}:
        raise DomainError("TTS_PROVIDER_UNAVAILABLE", "本地神经配音未安装完整，请检查本机配置", 422)
    _, model = config
    hashes = {}
    for name in FILES:
        path = model / name
        stat = path.stat()
        hashes[name] = checksum(str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    return {
        "provider": VERSION,
        "model_id": "kokoro-multi-lang-v1_0",
        "voice_id": voice,
        "model_sha256": hashes["model.onnx"],
        "file_hashes": hashes,
    }


def synthesize(target, text, voice, rate):
    identity = snapshot(voice)
    runtime, directory = configuration()
    try:
        result = subprocess.run(
            [runtime, str(ROOT / "scripts" / "kokoro-speech.py")],
            input=json.dumps(
                {
                    "directory": str(directory),
                    "output": str(target),
                    "text": text,
                    "speaker": int(voice.split(":")[1]),
                    "speed": 1 + rate * 0.075,
                }
            ),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=120,
            check=True,
        )
        receipt = json.loads(result.stdout.strip().splitlines()[-1])
        if (
            receipt["samples"] <= 0
            or receipt["model_sha256"] != identity["model_sha256"]
            or snapshot(voice) != identity
        ):
            raise ValueError("model changed or empty audio")
        return {**identity, "runtime_version": receipt["runtime_version"]}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError):
        raise DomainError(
            "TTS_PROVIDER_UNAVAILABLE", "本地神经配音失败；请检查运行时与模型，未切换音色或调用云服务", 422
        ) from None
