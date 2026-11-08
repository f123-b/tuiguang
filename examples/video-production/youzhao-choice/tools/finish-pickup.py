import hashlib
import json
import bisect
import math
import subprocess
from pathlib import Path
from PIL import Image

root = Path.cwd() / ".data" / "有招剧情制作-20261108"
manifest = json.loads((root / "ui-pickup-v1.json").read_text(encoding="utf-8"))
frames = manifest["frames"]
discarded = []
while frames and Image.open(frames[0]["file"]).size != (1920, 1080):
    discarded.append(frames.pop(0))
assert all(Image.open(f["file"]).size == (1920, 1080) for f in frames)
assert len(frames) > 100
assert all(b["timestamp"] > a["timestamp"] for a, b in zip(frames, frames[1:]))
out = root / "交付资料"
out.mkdir(exist_ok=True)
concat = root / "ui-pickup-v1.ffconcat"
lines = ["ffconcat version 1.0"]
for i, frame in enumerate(frames):
    duration = (
        (frames[i + 1]["timestamp"] - frame["timestamp"])
        if i + 1 < len(frames)
        else max(0.04, manifest["duration"] - frame["wall"])
    )
    assert duration > 0
    lines += [
        "file '" + Path(frame["file"]).as_posix() + "'",
        "option framerate 1000",
        "duration " + str(duration),
    ]
lines += ["file '" + Path(frames[-1]["file"]).as_posix() + "'", "option framerate 1000"]
concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
target = out / "有招-项目备注-真实补录素材.mp4"
duration_sec = manifest["duration"] - frames[0]["wall"]
frame_count = math.ceil(duration_sec * 30)
native_times = [f["timestamp"] - frames[0]["timestamp"] for f in frames]
process = subprocess.Popen(
    [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        "1920x1080",
        "-framerate",
        "30",
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libx264",
        "-crf",
        "16",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(target),
    ],
    stdin=subprocess.PIPE,
)
previous = -1
for i in range(frame_count):
    selected = max(0, bisect.bisect_right(native_times, i / 30) - 1)
    if selected != previous:
        pixels = Image.open(frames[selected]["file"]).convert("RGB").tobytes()
        previous = selected
    process.stdin.write(pixels)
process.stdin.close()
assert process.wait() == 0
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
            str(target),
        ],
        encoding="utf-8",
    )
)
stream = probe["streams"][0]
assert (stream["width"], stream["height"], stream["r_frame_rate"]) == (1920, 1080, "30/1")
assert int(stream["nb_read_frames"]) == frame_count
assert abs(float(probe["format"]["duration"]) - duration_sec) < 1 / 30 + 0.002
receipt = {
    "capture_method": manifest["capture_method"],
    "source_frames": len(frames),
    "leading_viewport_transition_frames_trimmed": len(discarded),
    "source_native_duration_sec": frames[-1]["timestamp"] - frames[0]["timestamp"],
    "source_cadence": "variable; includes unchanged screen intervals; not 30 unique images per second",
    "resampling": "hold latest source frame by native timestamp at 30fps; no optical-flow interpolation or altered operation speed",
    "output": str(target),
    "bytes": target.stat().st_size,
    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    "width": stream["width"],
    "height": stream["height"],
    "output_rate": stream["r_frame_rate"],
    "decoded_frames": int(stream["nb_read_frames"]),
    "duration_sec": float(probe["format"]["duration"]),
    "contains_audio": False,
    "saved_note_verified": any(e["name"] == "saved_value_verified" for e in manifest["events"]),
    "creative_approval": "not_reviewed",
    "note": "真实隔离演示操作素材，尚未剪入新片；恒定帧率封装不等于艺术质量或每秒30个独立采集帧。",
}
(out / "ui-pickup-receipt.json").write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(receipt, ensure_ascii=False))
