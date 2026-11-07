"""Optional local Qwen CustomVoice; fixed speakers and delivery presets only."""

import json
import os
import subprocess
from pathlib import Path

from .config import ROOT
from .errors import DomainError
from .neural_speech import checksum

VERSION = "qwen_local@1"
STYLES = {
    "plain": ("原声表达", ""),
    "conversational": (
        "轻松聊天",
        "用自然的普通话，像朋友随口聊天，有一点笑意和思考的停顿，亲切、松弛，不要广告腔或夸张表演。",
    ),
    "warm": (
        "温和讲述",
        "像和朋友聊天一样，用自然、温和的普通话讲述，语气有一点好奇，语速适中，不要朗诵或播报。",
    ),
    "explainer": (
        "清楚解释",
        "用清晰自然的普通话解释给一个人听，重点适当重读，句间自然停顿，不要逐字顿读，不要播报腔。",
    ),
}
SPEAKERS = {"serena": "温和女声", "dylan": "松弛男声", "uncle_fu": "低沉男声", "vivian": "明亮女声"}
FILES = (
    "model.safetensors",
    "config.json",
    "generation_config.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "preprocessor_config.json",
    "speech_tokenizer/model.safetensors",
    "speech_tokenizer/config.json",
    "speech_tokenizer/configuration.json",
    "speech_tokenizer/preprocessor_config.json",
)


def configuration():
    runtime, model = os.getenv("QWEN_TTS_PYTHON", ""), os.getenv("QWEN_TTS_MODEL_DIR", "")
    if not runtime or not model or not Path(runtime).is_file():
        return None
    directory = Path(model).resolve()
    if not all((directory / name).is_file() for name in FILES):
        return None
    try:
        config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
        if config.get("tts_model_size") != "1b7" or config.get("tts_model_type") != "custom_voice":
            return None
    except (OSError, ValueError):
        return None
    return runtime, directory


def voices():
    if not configuration():
        return []
    return [
        {
            "id": "qwen:" + sid,
            "label": "语气配音 · " + label,
            "language": "zh-CN",
            "max_text_length": 600,
            "delivery_styles": [{"id": s, "label": label} for s, (label, _) in STYLES.items()],
        }
        for sid, label in SPEAKERS.items()
    ]


def snapshot(voice, style="plain"):
    config = configuration()
    if not config or voice.removeprefix("qwen:") not in SPEAKERS:
        raise DomainError("TTS_PROVIDER_UNAVAILABLE", "本地语气模型未完整安装或声音不可用", 422)
    if style not in STYLES:
        raise DomainError("TTS_STYLE_UNSUPPORTED", "请选择支持的配音语气", 422)
    _, directory = config
    hashes = {}
    for name in FILES:
        file = directory / name
        stat = file.stat()
        hashes[name] = checksum(str(file), stat.st_size, stat.st_mtime_ns)
    return {
        "provider": VERSION,
        "model_id": "Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "voice_id": voice,
        "model_sha256": hashes["model.safetensors"],
        "file_hashes": hashes,
        "delivery_version": "spoken_delivery@1",
        "delivery_style": style,
        "instruction": STYLES[style][1],
        "seed": 37,
        "generation": {
            "language": "Chinese",
            "do_sample": True,
            "temperature": 0.8,
            "top_p": 0.9,
            "max_new_tokens": 2048,
            "attention": "sdpa",
            "dtype": "bfloat16",
        },
    }


def synthesize(target, text, voice, rate, style="plain"):
    if rate != 0:
        raise DomainError("TTS_RATE_UNSUPPORTED", "语气模型保留自然语速，请选择正常语速并用语气调整表达", 422)
    identity = snapshot(voice, style)
    runtime, directory = configuration()
    try:
        result = subprocess.run(
            [runtime, str(ROOT / "scripts/qwen-speech.py")],
            input=json.dumps(
                {
                    "directory": str(directory),
                    "output": str(target),
                    "text": text,
                    "speaker": voice.split(":")[1],
                    "instruction": identity["instruction"],
                    "seed": 37,
                }
            ),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=True,
            timeout=600,
            env={
                **os.environ,
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "HF_HUB_DISABLE_TELEMETRY": "1",
            },
        )
        receipt = json.loads(result.stdout.strip().splitlines()[-1])
        if (
            receipt["samples"] <= 0
            or receipt["model_sha256"] != identity["model_sha256"]
            or snapshot(voice, style) != identity
        ):
            raise ValueError("source mismatch")
        return {
            **identity,
            **{
                k: receipt[k]
                for k in (
                    "runtime_version",
                    "torch_version",
                    "elapsed_seconds",
                    "gpu_peak_bytes",
                    "samples",
                    "sample_rate",
                )
            },
        }
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError):
        raise DomainError(
            "TTS_PROVIDER_UNAVAILABLE", "本地语气配音失败，请检查独立环境和显存；未切换声音或调用云服务", 422
        ) from None
