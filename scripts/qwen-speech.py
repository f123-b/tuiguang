"""Run only in the optional local Qwen runtime. No voice clone or network."""

import contextlib
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
import time


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    os.environ.update(
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        DO_NOT_TRACK="1",
        GRADIO_ANALYTICS_ENABLED="False",
    )
    data = json.load(sys.stdin)
    if data["speaker"] not in ("serena", "dylan", "uncle_fu", "vivian") or not 1 <= len(data["text"]) <= 600:
        raise ValueError("invalid speaker or text")
    if len(data["instruction"]) > 200 or data["seed"] != 37:
        raise ValueError("invalid delivery")
    directory = Path(data["directory"])
    # Other local jobs wait for this GPU rather than loading a second full model.
    with contextlib.redirect_stdout(sys.stderr):
        import torch
        import soundfile as sf
        from filelock import FileLock
        from qwen_tts import Qwen3TTSModel

        if not torch.cuda.is_available():
            raise ValueError("local CUDA runtime required")
        with FileLock(str(directory / ".inference.lock"), timeout=60):
            start = time.perf_counter()
            torch.set_num_threads(4)
            torch.manual_seed(37)
            torch.cuda.reset_peak_memory_stats()
            model = Qwen3TTSModel.from_pretrained(
                str(directory),
                device_map="cuda:0",
                dtype=torch.bfloat16,
                attn_implementation="sdpa",
                local_files_only=True,
            )
            waves, sr = model.generate_custom_voice(
                text=data["text"],
                language="Chinese",
                speaker=data["speaker"],
                instruct=data["instruction"],
                do_sample=True,
                top_p=0.9,
                temperature=0.8,
                max_new_tokens=2048,
            )
            if len(waves[0]) / sr >= (2048 - 4) / 12:
                raise ValueError("possible generation limit reached; split text")
            sf.write(data["output"], waves[0], sr, subtype="PCM_16")
            receipt = {
                "samples": len(waves[0]),
                "sample_rate": sr,
                "runtime_version": "qwen-tts@" + version("qwen-tts"),
                "torch_version": torch.__version__,
                "elapsed_seconds": round(time.perf_counter() - start, 3),
                "gpu_peak_bytes": torch.cuda.max_memory_allocated(),
            }
    with (directory / "model.safetensors").open("rb") as stream:
        receipt["model_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
