"""Media acceptance only; an exported film still needs the user's creative review."""

import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / ".data/有招那个选择-本地成片-20261108"
DELIVERY = OUT / "交付文件"


def main():
    film = DELIVERY / "有招-那个选择-完整版.mp4"
    if not film.is_file():
        raise RuntimeError("FILM_MISSING: no completed video file")
    manifest = json.loads((OUT / "edit-manifest.json").read_text(encoding="utf-8"))
    ir = json.loads((DELIVERY / "VideoProjectIR.json").read_text(encoding="utf-8"))
    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-count_frames",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(film),
            ]
        )
    )
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    expected = manifest["duration_frames"]
    assert (video["width"], video["height"], video["r_frame_rate"]) == (1920, 1080, "30/1")
    assert int(video["nb_read_frames"]) == expected
    assert abs(float(probe["format"]["duration"]) - expected / 30) < 0.05
    assert audio["channels"] == 2 and audio["sample_rate"] == "48000"
    assert sum(s["duration_frames"] for s in ir["shots"]) == expected
    assert len(ir["shots"]) == 12 and len(ir["subtitles"]) == 12
    previous = 0
    for cue in ir["subtitles"]:
        assert 0 <= previous <= cue["start_frame"] < cue["end_frame"] <= expected
        previous = cue["end_frame"]
    raw = subprocess.check_output(
        ["ffmpeg", "-v", "error", "-i", str(film), "-vn", "-ar", "48000", "-ac", "2", "-f", "f32le", "pipe:1"]
    )
    samples = np.frombuffer(raw, dtype="<f4")
    peak = float(np.max(np.abs(samples)))
    rms = math.sqrt(float(np.mean(samples * samples)))
    assert 0.01 < rms < 0.4 and peak < 1
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-i", str(film), "-f", "null", "-"], check=True)
    loudness = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(film),
            "-filter_complex",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stderr
    integrated = float(re.findall(r"I:\s*(-?[\d.]+) LUFS", loudness)[-1])
    true_peak = float(re.findall(r"Peak:\s*(-?[\d.]+) dBFS", loudness)[-1])
    assert -18 <= integrated <= -14 and true_peak <= -0.8
    result = {
        "file": str(film),
        "bytes": film.stat().st_size,
        "sha256": hashlib.sha256(film.read_bytes()).hexdigest(),
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "frames": expected,
        "duration_sec": expected / 30,
        "dialogue_cues": 12,
        "stereo_rms": rms,
        "sample_peak": peak,
        "integrated_lufs": integrated,
        "true_peak_dbfs": true_peak,
        "full_decode": "passed",
        "artistic_review": "awaiting_user",
        "cloud_video_used": False,
    }
    (DELIVERY / "成片技术回执.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
