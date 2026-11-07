"""Measure actual decoded motion, including the low-resolution preview."""

import subprocess
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from creator import film, video


@pytest.mark.parametrize("motion", ["pan", "push"])
@pytest.mark.parametrize("width,height", [(640, 360), (1920, 1080)])
def test_slow_camera_changes_each_decoded_frame(tmp_path, monkeypatch, motion, width, height):
    source = tmp_path / "screen.png"
    image = Image.new("RGB", (960, 600), "#fff9ed")
    draw = ImageDraw.Draw(image)
    for x in range(0, 960, 23):
        draw.rectangle((x, 0, x + 9, 600), fill=(x % 230, 90, 170))
    image.save(source)
    monkeypatch.setattr(film, "file_path", lambda *args: source)
    # Lossless encoding makes repeated pixels measurable, without codec noise.
    real_ffmpeg = video.ffmpeg
    monkeypatch.setattr(video, "ffmpeg", lambda args: real_ffmpeg([*args[:-1], "-crf", "0", args[-1]]))
    target = tmp_path / "motion.mp4"
    film.render_scene(
        {"asset_id": "fixture", "duration_frames": 180, "design": {"layout": "screen", "motion": motion}},
        {"width": width, "height": height, "fps": 30, "presentation": {"style": "studio"}},
        target,
        SimpleNamespace(workspace_id="fixture", sha256="fixture", suffix=".png", kind="image"),
    )
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(target), "-pix_fmt", "gray", "-f", "framemd5", "pipe:1"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    # Ignore entrance motion; measure the camera while all captions are settled.
    hashes = [line.split(",")[-1].strip() for line in result.splitlines() if not line.startswith("#")][30:180]
    assert len(hashes) == 150
    changed = sum(a != b for a, b in zip(hashes, hashes[1:]))
    assert changed >= 140, f"only {changed}/149 frame transitions move ({motion})"


@pytest.mark.parametrize("motion", ["pan", "still"])
def test_real_clip_keeps_trim_timing_and_source_changes(tmp_path, monkeypatch, motion):
    source = tmp_path / "recording.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=red:s=320x180:r=30:d=2",
            "-f",
            "lavfi",
            "-i",
            "color=lime:s=320x180:r=30:d=2",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    monkeypatch.setattr(film, "file_path", lambda *args: source)
    target = tmp_path / "trimmed.mp4"
    film.render_scene(
        {
            "asset_id": "fixture",
            "duration_frames": 60,
            "trim_start_frame": 30,
            "design": {"layout": "screen", "motion": motion},
        },
        {"width": 640, "height": 360, "fps": 30, "presentation": {"style": "studio"}},
        target,
        SimpleNamespace(workspace_id="fixture", sha256="fixture", suffix=".mp4", kind="video"),
    )
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(target), "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"],
        capture_output=True,
        check=True,
    ).stdout
    size = 640 * 360 * 3
    assert len(raw) == 60 * size
    pixel = (190 * 640 + 320) * 3
    first = raw[10 * size + pixel : 10 * size + pixel + 3]
    last = raw[50 * size + pixel : 50 * size + pixel + 3]
    assert first[0] > first[1] + 100  # source second 1: red
    assert last[1] > last[0] + 100  # source second 2: green, not a frozen still
