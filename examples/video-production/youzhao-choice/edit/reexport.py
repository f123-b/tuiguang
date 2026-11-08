"""Re-export the delivered picture, mix and editable ASS without models or stock files."""

import json
import subprocess
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    target = root / "有招-那个选择-重新导出.mp4"
    if target.exists():
        raise RuntimeError("OUTPUT_EXISTS: choose a new output name; existing video is preserved")
    ir = json.loads((root / "VideoProjectIR.json").read_text(encoding="utf-8"))
    frames = sum(s["duration_frames"] for s in ir["shots"])
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-v",
            "error",
            "-n",
            "-i",
            "静音画面.mp4",
            "-i",
            "混音.wav",
            "-vf",
            "ass=subtitles.ass",
            "-af",
            "highpass=f=70,loudnorm=I=-16:TP=-2:LRA=8",
            "-c:v",
            "libx264",
            "-crf",
            "17",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-t",
            str(frames / ir["fps"]),
            "-movflags",
            "+faststart",
            str(target),
        ],
        cwd=root,
        check=True,
    )
    print(target)


if __name__ == "__main__":
    main()
