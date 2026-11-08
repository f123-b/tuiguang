"""Independent local dialogue recording; does not modify workspace voice settings."""

import hashlib
import json
import os
import time
from pathlib import Path

os.environ.update(
    HF_HUB_OFFLINE="1",
    TRANSFORMERS_OFFLINE="1",
    HF_HUB_DISABLE_TELEMETRY="1",
    DO_NOT_TRACK="1",
    GRADIO_ANALYTICS_ENABLED="False",
)

import soundfile as sf
import torch
from filelock import FileLock
from qwen_tts import Qwen3TTSModel

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / ".data/有招那个选择-本地成片-20261108"
MODEL = ROOT / ".data/qwen-model"
SCRIPT = json.loads(Path(__file__).with_name("dialogue.json").read_text(encoding="utf-8"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    directory = OUT / "dialogue"
    directory.mkdir(exist_ok=True)
    sources = {
        p.relative_to(MODEL).as_posix(): sha(p)
        for p in sorted(MODEL.rglob("*"))
        if p.is_file() and p.suffix in (".json", ".safetensors", ".txt")
    }
    torch.set_num_threads(4)
    receipts = []
    with FileLock(str(MODEL / ".inference.lock"), timeout=600):
        model = Qwen3TTSModel.from_pretrained(
            str(MODEL),
            device_map="cuda:0",
            dtype=torch.bfloat16,
            attn_implementation="sdpa",
            local_files_only=True,
        )
        for i, cue in enumerate(SCRIPT["cues"]):
            target = directory / (cue["id"] + ".wav")
            if target.exists():
                raise RuntimeError("Use a new take directory; do not overwrite recorded dialogue")
            seed = 71 + i
            torch.manual_seed(seed)
            torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            wavs, sample_rate = model.generate_custom_voice(
                text=cue["text"],
                language="Chinese",
                speaker=SCRIPT["voices"][cue["role"]],
                instruct=cue["direction"],
                do_sample=True,
                top_p=0.9,
                temperature=0.8,
                max_new_tokens=800,
            )
            sf.write(str(target), wavs[0], sample_rate, subtype="PCM_16")
            row = {
                **cue,
                "speaker": SCRIPT["voices"][cue["role"]],
                "seed": seed,
                "file": str(target),
                "sample_rate": sample_rate,
                "samples": len(wavs[0]),
                "duration_sec": len(wavs[0]) / sample_rate,
                "elapsed_sec": time.perf_counter() - started,
                "gpu_peak_bytes": torch.cuda.max_memory_allocated(),
                "sha256": sha(target),
            }
            receipts.append(row)
            print(json.dumps({k: row[k] for k in ("id", "duration_sec", "elapsed_sec")}), flush=True)
            (OUT / "dialogue-receipts.json").write_text(
                json.dumps(
                    {
                        "version": "choice_edit@1",
                        "provider": "qwen_local@1",
                        "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
                        "model_revision": "0c0e3051f131929182e2c023b9537f8b1c68adfe",
                        "model_files": sources,
                        "torch": torch.__version__,
                        "cues": receipts,
                        "voice_clone": False,
                        "cloud_requests": 0,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    main()
