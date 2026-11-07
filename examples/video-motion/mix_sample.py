import json
import subprocess
import wave
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

p = Path.cwd() / ".data/有招动效试片-20261108"
d = p / "交付文件"
d.mkdir(exist_ok=True)
sr = 48000
duration = 30
n = sr * duration
t = np.arange(n) / sr
voice = np.zeros((n, 2))
music = np.zeros((n, 2))
fx = np.zeros((n, 2))
raw = subprocess.run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(p / "完整旁白-温和讲述.wav"),
        "-f",
        "f32le",
        "-ar",
        str(sr),
        "-ac",
        "1",
        "pipe:1",
    ],
    check=True,
    capture_output=True,
).stdout
a = np.frombuffer(raw, dtype="<f4").astype(float)
assert len(a) / sr < 29 and np.max(np.abs(a)) < 0.9999
start = round(0.6 * sr)
voice[start : start + len(a), :] = a[:, None] * 0.8 / max(0.001, np.max(np.abs(a)))
chords = [(130.81, 196, 293.66), (174.61, 220, 329.63), (110, 164.81, 246.94), (130.81, 196, 261.63)]
for k, chord in enumerate(chords):
    pos = k * 7 * sr
    sample_count = min(n - pos, 9 * sr)
    tt = np.arange(sample_count) / sr
    envelope = np.sin(np.pi * np.minimum(1, tt / 1.8) / 2) ** 2 * np.minimum(
        1, (sample_count / sr - tt) / 2.5
    )
    for j, f in enumerate(chord):
        for channel in (0, 1):
            phase = channel * 0.3 + j * 0.2
            music[pos : pos + sample_count, channel] += (
                0.006 * envelope * np.sin(2 * np.pi * f * (1 + channel * 0.0006) * tt + phase)
            )
            music[pos : pos + sample_count, channel] += (
                0.002 * envelope * np.sin(2 * np.pi * f * 2 * tt + phase)
            )
rng = np.random.default_rng(37)
for when, length in [(2.1, 0.95), (10.7, 1.2), (16.5, 0.8), (24, 0.9)]:
    pos = round(when * sr)
    sample_count = round(length * sr)
    q = np.linspace(0, 1, sample_count)
    noise = rng.normal(size=sample_count)
    noise = np.convolve(noise, np.ones(19) / 19, mode="same")
    env = np.sin(np.pi * q) ** 2
    fx[pos : pos + sample_count, 0] += 0.021 * noise * env * np.cos(q * np.pi / 2)
    fx[pos : pos + sample_count, 1] += 0.021 * noise * env * np.sin(q * np.pi / 2)
music *= np.minimum(1, t / 0.8)[:, None] * np.minimum(1, (duration - t) / 2)[:, None]
for name, audio in [("旁白", voice), ("原创氛围与音效", music + fx), ("混音", voice + music + fx)]:
    with wave.open(str(d / (name + ".wav")), "wb") as w:
        w.setparams((2, 2, sr, 0, "NONE", "not compressed"))
        w.writeframes((np.clip(audio, -0.99, 0.99) * 32767).astype("<i2").tobytes())
target = d / "有招-把经历串起来-连续镜头试片.mp4"
subprocess.run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-framerate",
        "30",
        "-i",
        str(p / "frames/%05d.png"),
        "-i",
        str(d / "混音.wav"),
        "-af",
        "highpass=f=70,loudnorm=I=-16:TP=-1.5:LRA=9",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "17",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-t",
        "30",
        "-movflags",
        "+faststart",
        str(target),
    ],
    check=True,
)
sheet = Image.new("RGB", (1440, 1010), "#e6e7e2")
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 23)
for i, seconds in enumerate([1, 3, 6, 9, 12.5, 15, 18.5, 22, 28]):
    im = Image.open(p / f"frames/{round(seconds * 30):05d}.png")
    im.thumbnail((480, 270))
    x = i % 3 * 480
    y = i // 3 * 335
    sheet.paste(im, (x, y))
    draw.text((x + 12, y + 280), f"{seconds}s", font=font, fill="#15372e")
sheet.save(p / "连续镜头-抽帧.jpg", quality=93)
print(
    json.dumps(
        {
            "file": str(target),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "bytes": target.stat().st_size,
            "voice_duration": len(raw) / 4 / sr,
        },
        ensure_ascii=False,
    )
)
