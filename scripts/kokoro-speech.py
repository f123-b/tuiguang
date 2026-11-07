"""Run only with the optional isolated sherpa-onnx runtime; JSON via stdin."""

import hashlib
import json
from pathlib import Path
import sys
import wave


def main():
    # Parent and optional runtime may have different Windows code pages.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    import sherpa_onnx
    import numpy as np

    data = json.load(sys.stdin)
    if not 1 <= len(data["text"]) <= 4000 or data["speaker"] not in (45, 46, 49, 50):
        raise ValueError("invalid text or speaker")
    if not 0.625 <= data["speed"] <= 1.375:
        raise ValueError("invalid speed")
    directory = Path(data["directory"])
    kokoro = sherpa_onnx.OfflineTtsKokoroModelConfig(
        model=str(directory / "model.onnx"),
        voices=str(directory / "voices.bin"),
        tokens=str(directory / "tokens.txt"),
        data_dir=str(directory / "espeak-ng-data"),
        lexicon=",".join(str(directory / f) for f in ("lexicon-us-en.txt", "lexicon-zh.txt")),
    )
    config = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(kokoro=kokoro, num_threads=2, provider="cpu"),
        max_num_sentences=1,
    )
    if not config.validate():
        raise ValueError("invalid model configuration")
    engine = sherpa_onnx.OfflineTts(config)
    generation = sherpa_onnx.GenerationConfig()
    generation.sid, generation.speed, generation.silence_scale = data["speaker"], data["speed"], 0.25
    audio = engine.generate(data["text"], generation)
    with wave.open(data["output"], "wb") as output:
        output.setparams((1, 2, audio.sample_rate, 0, "NONE", "not compressed"))
        output.writeframes((np.clip(audio.samples, -1, 1) * 32767).astype("<i2").tobytes())
    with (directory / "model.onnx").open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    print(
        json.dumps(
            {
                "samples": len(audio.samples),
                "sample_rate": audio.sample_rate,
                "runtime_version": sherpa_onnx.__version__,
                "model_sha256": sha,
            }
        )
    )


if __name__ == "__main__":
    main()
