"""Hand-directed local edit: actual footage, explanatory animation and real product UI."""

import bisect
import hashlib
import json
import math
import subprocess
import sys
import uuid
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / ".data/有招那个选择-本地成片-20261108"
DELIVERY = OUT / "交付文件"
DELIVERY.mkdir(exist_ok=True)
W, H, FPS = 1920, 1080, 30
INK, CREAM, TEAL = "#253d36", "#eee9df", "#3a6b5b"
VOICE = json.loads((OUT / "dialogue-receipts.json").read_text(encoding="utf-8"))
MINIMUMS = [3.6, 3.1, 2.3, 3.1, 3.6, 5.2, 4.4, 3.5, 4.6, 3.2, 3, 4.4]
SHOTS = []
frame = 0
for i, cue in enumerate(VOICE["cues"]):
    length = math.ceil(max(MINIMUMS[i], cue["duration_sec"] + cue["tail_sec"] + 0.18) * FPS)
    lead = -0.12 if i in (2, 9, 11) else 0.18
    SHOTS.append(
        {
            **cue,
            "start_frame": frame,
            "duration_frames": length,
            "voice_start_frame": frame + round(lead * FPS),
        }
    )
    frame += length
TOTAL = frame
DURATION = TOTAL / FPS
UI = json.loads((OUT / "ui/ui-pickup-v1.json").read_text(encoding="utf-8"))
UI_TIMES = [f["wall"] for f in UI["frames"]]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for data in iter(lambda: source.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def clamp(x):
    return max(0, min(1, x))


def ease(x):
    x = clamp(x)
    return x * x * x * (10 + x * (-15 + 6 * x))


@lru_cache(maxsize=50)
def font(size, bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/" + ("msyhbd.ttc" if bold else "msyh.ttc"), size)


@lru_cache(maxsize=100)
def lettering(words, size, color, bold=False):
    f = font(size, bold)
    box = f.getbbox(words)
    im = Image.new("RGBA", (box[2] + 12, box[3] - box[1] + 14))
    ImageDraw.Draw(im).text((6, 5 - box[1]), words, fill=color, font=f)
    return im


def text(im, words, x, y, size=48, color=INK, bold=False, alpha=1, center=False):
    layer = lettering(words, size, color, bold)
    if alpha < 1:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda n: round(n * clamp(alpha))))
    if center:
        x -= layer.width / 2
    im.paste(layer, (round(x), round(y)), layer)


@lru_cache(maxsize=12)
def image(path):
    return Image.open(path).convert("RGB")


def prepare():
    sources = {
        "erasing": OUT / "assets/erasing.mp4",
        "coffee": OUT / "assets/coffee.mp4",
        "notebook": ROOT / ".data/story-assets/8519332.mp4",
    }
    provenance = []
    urls = {
        "erasing": (
            "Coverr",
            "https://coverr.co/videos/pencil-writing-and-erasing-boh8dalgsz",
            "https://coverr.co/license",
        ),
        "coffee": (
            "Cup of Couple / Pexels",
            "https://www.pexels.com/video/working-on-a-laptop-and-drinking-coffee-8472301/",
            "https://www.pexels.com/license/",
        ),
        "notebook": (
            "Artem Podrez / Pexels",
            "https://www.pexels.com/video/a-person-writing-on-a-notebook-8519332/",
            "https://www.pexels.com/license/",
        ),
    }
    for name, source in sources.items():
        dest = OUT / (name + "-frames")
        dest.mkdir(exist_ok=True)
        if not (dest / "00001.jpg").exists():
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(source),
                    "-vf",
                    "fps=30,scale=1920:1080,eq=saturation=0.76:contrast=1.025:brightness=-0.008,colorbalance=rs=0.008:bs=-0.008",
                    "-q:v",
                    "2",
                    str(dest / "%05d.jpg"),
                ],
                check=True,
            )
        probe = json.loads(
            subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(source)]
            )
        )
        author, page, license_url = urls[name]
        provenance.append(
            {
                "id": name,
                "source": str(source),
                "author": author,
                "page": page,
                "license": license_url,
                "retrieved": "2026-11-08",
                "sha256": sha(source),
                "bytes": source.stat().st_size,
                "duration_sec": float(probe["format"]["duration"]),
                "source_fps": probe["streams"][0]["r_frame_rate"],
                "use": "edited illustrative hands only; no identity, customer story or endorsement implied",
            }
        )
    (DELIVERY / "素材来源.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "version": "choice_edit@1",
        "origin": "independent_local_editor_not_application_worker",
        "trace_id": uuid.uuid4().hex,
        "video_project_id": uuid.uuid4().hex,
        "render_job_id": uuid.uuid4().hex,
        "creator_run_id": None,
        "content_id": None,
        "application_release": json.loads((ROOT / "release_manifest.json").read_text()),
        "duration_frames": TOTAL,
        "fps": FPS,
        "width": W,
        "height": H,
        "engine": "offline_choice_compositor@1",
        "shot_provider": "ffmpeg_media (rendered local source assets)",
        "diagram_engine": "three@0.187.0",
        "voice_receipt_sha256": sha(OUT / "dialogue-receipts.json"),
        "ui_capture_sha256": sha(OUT / "ui/ui-pickup-v1.json"),
        "artistic_review": "awaiting_user",
        "cloud_video_used": False,
        "cloud_requests": 0,
        "shots": SHOTS,
    }
    (OUT / "edit-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"duration": DURATION, "frames": TOTAL, "shots": len(SHOTS)}), flush=True)


def stock(name, t, shade=0, crop=None):
    files = sorted((OUT / (name + "-frames")).glob("*.jpg"))
    index = min(len(files) - 1, max(0, int(t * FPS)))
    im = image(str(files[index]))
    if crop:
        im = im.transform((W, H), Image.Transform.EXTENT, crop, Image.Resampling.BICUBIC)
    else:
        im = im.copy()
    if shade:
        im = Image.blend(im, Image.new("RGB", im.size, "#142820"), shade)
    return im


@lru_cache(maxsize=1)
def left_scrim():
    alpha = np.tile((np.clip(1 - np.arange(W) / 1060, 0, 1) ** 1.7 * 145).astype("uint8"), (H, 1))
    layer = Image.new("RGBA", (W, H), "#14231c")
    layer.putalpha(Image.fromarray(alpha))
    return layer


def readable_stock(name, t, shade=0):
    im = stock(name, t, shade).convert("RGBA")
    im.alpha_composite(left_scrim())
    return im.convert("RGB")


def ui_frame(seconds, box, saved_still=False):
    index = max(0, bisect.bisect_right(UI_TIMES, seconds) - 1)
    original = image(str(OUT / "ui/saved-note-hq.png")) if saved_still else image(UI["frames"][index]["file"])
    sx, sy = original.width / 1280, original.height / 720
    x, y, width, height = box
    return original.transform(
        (W, H),
        Image.Transform.EXTENT,
        (x * sx, y * sy, (x + width) * sx, (y + height) * sy),
        Image.Resampling.BICUBIC,
    )


def draw(shot, u):
    i = int(shot["id"][1:]) - 1
    duration = shot["duration_frames"] / FPS
    if i == 0:
        im = readable_stock("notebook", 0.15 + u, shade=0.08)
        text(im, "那个选择", 118, 675 + (1 - ease(u / 0.6)) * 25, 104, CREAM, True, ease(u / 0.35))
        text(im, "一次把经历讲具体的练习", 124, 810, 32, CREAM, alpha=ease((u - 0.7) / 0.5))
    elif i == 1:
        im = readable_stock("coffee", 1 + u, shade=0.12)
        text(im, "因为……", 120, 650, 54, CREAM, alpha=ease(u / 0.4))
        text(im, "大家都这么做。", 116, 729, 82, CREAM, True, ease((u - 0.5) / 0.4))
    elif i == 2:
        im = stock("erasing", 6.1 + u)
        layer = lettering("大家都这么做。", 86, "#4e5550", True).copy()
        remove = ease((u - 0.2) / 1.05)
        mask = layer.getchannel("A")
        ImageDraw.Draw(mask).rectangle(
            (round(layer.width * (1 - remove)), 0, layer.width, layer.height), fill=0
        )
        layer.putalpha(mask)
        im.paste(layer, (180, 700), layer)
        if u > 1:
            text(im, "重来。", 182, 700, 84, TEAL, True, ease((u - 1) / 0.35))
    elif i == 3:
        im = readable_stock("coffee", 8.2 + min(u, 3.7), shade=0.1)
        text(im, "问题，先讲具体。", 116, 715, 62, CREAM, True, ease((u - 0.35) / 0.4))
    elif i in (4, 5):
        offset = 0 if i == 4 else 180
        n = min(179, int(ease(u / duration) * 179))
        im = image(str(OUT / "diagram-frames" / f"{offset + n:05d}.png")).copy()
    elif i == 6:
        im = readable_stock("notebook", 3.4 + u, shade=0.16)
        text(im, "我怎么验证？", 116, 180, 64, CREAM, True, ease(u / 0.4))
        for j, words in enumerate(["加载时间", "滚动体验"]):
            a = ease((u - 0.65 - j * 1.0) / 0.45)
            text(im, words, 125, 300 + j * 105, 49, CREAM, alpha=a)
            ImageDraw.Draw(im).line(
                (125, 370 + j * 105, 125 + 310 * a, 370 + j * 105), fill="#b3c8a0", width=3
            )
    elif i == 7:
        p = ease(u / 0.8)
        start, end = (0, 0, 1280, 720), (520, 35, 760, 427.5)
        box = tuple(a + (b - a) * p for a, b in zip(start, end))
        im = ui_frame(3.05 + u, box)
    elif i == 8:
        if u < 0.65:
            im = ui_frame(8.4 + u, (520, 35, 760, 427.5))
        else:
            p = ease((u - 0.65) / 0.7)
            start, end = (520, 35, 760, 427.5), (820, 150, 460, 258.75)
            box = tuple(a + (b - a) * p for a, b in zip(start, end))
            im = ui_frame(12, box, saved_still=True)
    elif i == 9:
        im = readable_stock("coffee", 8.7 + u, shade=0.12)
        text(im, "再问一次。", 120, 730, 72, CREAM, True, ease((u - 0.25) / 0.4))
    elif i == 10:
        im = stock("erasing", 0.2 + u)
        text(im, "这次，我测过。", W / 2, 735, 86, TEAL, True, ease((u - 0.45) / 0.5), True)
    else:
        im = stock("coffee", 3.0 + u, shade=0.72)
        text(im, "有招", W / 2, 270, 148, CREAM, True, ease(u / 0.35), True)
        text(im, "把做过的，讲到点上。", W / 2, 490, 62, CREAM, alpha=ease((u - 0.35) / 0.5), center=True)
        text(
            im,
            "先整理一个你真实做过的项目。",
            W / 2,
            650,
            32,
            "#c6d3c1",
            alpha=ease((u - 1) / 0.5),
            center=True,
        )
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 58), fill="#111b17")
    d.rectangle((0, H - 70, W, H), fill="#111b17")
    text(im, "有招 / 那个选择", 70, 17, 21, "#d8dfd1")
    label = "真实界面 · 演示资料" if i in (7, 8) else "情景演绎 · 虚构练习 · 合成配音"
    text(im, label, W - lettering(label, 20, CREAM).width - 65, 18, 20, "#c4cec0")
    absolute = shot["start_frame"] / FPS + u
    fade = min(clamp(absolute / 0.13), clamp((DURATION - absolute) / 0.4))
    if fade < 1:
        im = ImageEnhance.Brightness(im).enhance(fade)
    return im


def render():
    target = OUT / "silent-master.mp4"
    process = subprocess.Popen(
        [
            "ffmpeg",
            "-hide_banner",
            "-v",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgb24",
            "-video_size",
            f"{W}x{H}",
            "-framerate",
            str(FPS),
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
    try:
        for shot in SHOTS:
            for n in range(shot["duration_frames"]):
                process.stdin.write(draw(shot, n / FPS).tobytes())
            print("rendered", shot["id"], flush=True)
    finally:
        process.stdin.close()
    if process.wait():
        raise RuntimeError("video encoder failed")


def read_audio(path, sr=48000):
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ar", str(sr), "-ac", "1", "pipe:1"],
        check=True,
        capture_output=True,
    )
    return np.frombuffer(result.stdout, dtype="<f4").astype(np.float64)


def wav(path, a, sr=48000):
    with wave.open(str(path), "wb") as f:
        f.setparams((2, 2, sr, 0, "NONE", "not compressed"))
        f.writeframes((np.clip(a, -0.999, 0.999) * 32767).astype("<i2").tobytes())


def audio():
    sr = 48000
    count = round(DURATION * sr)
    voice = np.zeros((count, 2))
    music = np.zeros_like(voice)
    effects = np.zeros_like(voice)
    rng = np.random.default_rng(103)
    for shot in SHOTS:
        a = read_audio(shot["file"])
        peak = max(0.001, np.max(np.abs(a)))
        rms = math.sqrt(np.mean(a * a))
        a *= min(0.83 / peak, 0.16 / max(0.001, rms))
        fade = min(240, len(a) // 4)
        a[:fade] *= np.linspace(0, 1, fade)
        a[-fade:] *= np.linspace(1, 0, fade)
        start = round(shot["voice_start_frame"] / FPS * sr)
        voice[start : start + len(a)] += a[:, None]
    # Original musical phrase: muted plucked keys, Dm9 / Bbmaj7 / Fadd9 / C6.
    chords = [(50, 57, 60, 64, 69), (46, 53, 57, 60, 65), (41, 53, 57, 60, 67), (48, 55, 57, 64, 67)]
    music_start = SHOTS[3]["start_frame"] / FPS
    beat = 60 / 86
    for n in range(int((DURATION - music_start) / (beat / 2))):
        chord = chords[(n // 8) % len(chords)]
        midi = chord[[0, 2, 3, 1, 4, 2, 3, 4][n % 8]] + (12 if n % 4 else 0)
        frequency = 440 * 2 ** ((midi - 69) / 12)
        when = music_start + n * beat / 2
        start = round(when * sr)
        length = min(count - start, round(2.8 * sr))
        t = np.arange(length) / sr
        envelope = (1 - np.exp(-t / 0.006)) * np.exp(-t / (0.65 if n % 4 else 1.3))
        note = np.zeros(length)
        for h in range(1, 7):
            note += (
                np.sin(2 * np.pi * frequency * h * (1 + 0.0001 * h * h) * t) * np.exp(-t * h * 0.65) / h**1.7
            )
        note *= envelope * (0.022 if n % 4 else 0.035)
        pan = 0.3 if n % 2 else 0.7
        music[start : start + length, 0] += note * math.cos(pan * math.pi / 2)
        music[start : start + length, 1] += note * math.sin(pan * math.pi / 2)

    def rustle(when, length=0.2, level=0.02, pan=0.5):
        start = round(when * sr)
        size = min(count - start, round(length * sr))
        if size <= 0:
            return
        a = rng.normal(size=size)
        a = np.convolve(a, np.ones(7) / 7, mode="same")
        a *= np.sin(np.pi * np.linspace(0, 1, size)) ** 2 * level
        effects[start : start + size, 0] += a * math.cos(pan * math.pi / 2)
        effects[start : start + size, 1] += a * math.sin(pan * math.pi / 2)

    for j in range(5):
        rustle(SHOTS[2]["start_frame"] / FPS + 0.12 + j * 0.23, 0.19, 0.035)
    for j in range(10):
        rustle(SHOTS[4]["start_frame"] / FPS + 0.35 + j * 0.1, 0.065, 0.05, j / 12)
    for j in range(6):
        rustle(SHOTS[5]["start_frame"] / FPS + 0.35 + j * 0.24, 0.09, 0.045, 0.45 + j * 0.07)
    for j in range(24):
        rustle(SHOTS[7]["start_frame"] / FPS + 0.1 + j * 0.12, 0.018, 0.022)
    rustle(SHOTS[8]["start_frame"] / FPS + 0.28, 0.035, 0.05)
    # Quiet original room texture, not claimed to be source-location audio.
    room = rng.normal(size=count)
    room = np.convolve(room, np.ones(29) / 29, mode="same") * 0.0018
    effects += room[:, None]
    level = np.max(np.abs(voice), axis=1)
    blocks = (
        np.max(level.reshape(-1, 480), axis=1)
        if count % 480 == 0
        else np.array([max(level[i : i + 480]) for i in range(0, count, 480)])
    )
    duck = []
    gain = 1.0
    for value in blocks:
        desired = 0.3 if value > 0.015 else 1.0
        gain += (desired - gain) * (0.65 if desired < gain else 0.045)
        duck.append(gain)
    music *= np.repeat(duck, 480)[:count, None]
    fade = np.minimum(1, np.arange(count) / sr / 0.3) * np.minimum(1, (count - np.arange(count)) / sr / 0.7)
    music *= fade[:, None]
    effects *= fade[:, None]
    for name, a in [
        ("对白", voice),
        ("原创音乐", music),
        ("原创动作与环境声", effects),
        ("混音", voice + music + effects),
    ]:
        wav(DELIVERY / (name + ".wav"), a)


def timestamp(seconds, ass=False):
    units = round(seconds * (100 if ass else 1000))
    if ass:
        return f"{units // 360000}:{units // 6000 % 60:02d}:{units // 100 % 60:02d}.{units % 100:02d}"
    return f"{units // 3600000:02d}:{units // 60000 % 60:02d}:{units // 1000 % 60:02d},{units % 1000:03d}"


def finish():
    srt = []
    events = []
    subtitles = []
    for i, s in enumerate(SHOTS):
        begin = s["voice_start_frame"] / FPS
        end = begin + s["duration_sec"]
        srt.append(f"{i + 1}\n{timestamp(begin)} --> {timestamp(end)}\n{s['text']}\n")
        events.append(
            f"Dialogue: 0,{timestamp(begin, True)},{timestamp(end, True)},Default,,0,0,0,,{s['text']}"
        )
        subtitles.append(
            {
                "cue_id": s["id"],
                "start_frame": s["voice_start_frame"],
                "end_frame": math.ceil(end * FPS),
                "text": s["text"],
            }
        )
    (DELIVERY / "字幕.srt").write_text("\n".join(srt), encoding="utf-8")
    header = """[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 2\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Microsoft YaHei,35,&H00F3F1E9,&H00FFFFFF,&H00131C17,&H00131C17,0,0,0,0,100,100,0,0,1,1,0,2,80,80,22,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
    (DELIVERY / "subtitles.ass").write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    target = DELIVERY / "有招-那个选择-完整版.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-v",
            "error",
            "-y",
            "-i",
            str(OUT / "silent-master.mp4"),
            "-i",
            str(DELIVERY / "混音.wav"),
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
            str(DURATION),
            "-movflags",
            "+faststart",
            str(target),
        ],
        cwd=DELIVERY,
        check=True,
    )
    master = OUT / "silent-master.mp4"
    sources = [
        ("master", master),
        ("voice", DELIVERY / "对白.wav"),
        ("music", DELIVERY / "原创音乐.wav"),
        ("fx", DELIVERY / "原创动作与环境声.wav"),
    ]
    assets = {
        name: {"id": sha(p)[:32], "file": str(p), "sha256": sha(p), "bytes": p.stat().st_size}
        for name, p in sources
    }
    ir = {
        "schema_version": "1.1",
        "brand_id": "offline-youzhao",
        "name": "有招·那个选择",
        "width": W,
        "height": H,
        "fps": FPS,
        "preview_required": True,
        "presentation": {"style": "classic", "audio_finish": False},
        "shots": [
            {
                "shot_id": s["id"],
                "shot_revision": 1,
                "provider": "ffmpeg_media",
                "kind": "screen_demo" if i in (7, 8) else "montage",
                "duration_frames": s["duration_frames"],
                "asset_id": assets["master"]["id"],
                "trim_start_frame": s["start_frame"],
                "caption": "",
                "narration_text": s["text"],
                "locked": False,
            }
            for i, s in enumerate(SHOTS)
        ],
        "audio_tracks": [
            {
                "track_id": name,
                "asset_id": assets[name]["id"],
                "role": "voiceover" if name == "voice" else "music",
                "start_frame": 0,
                "duration_frames": TOTAL,
                "volume_percent": 100,
            }
            for name in ("voice", "music", "fx")
        ],
        "subtitles": subtitles,
    }
    (DELIVERY / "VideoProjectIR.json").write_text(
        json.dumps(ir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (DELIVERY / "本地资产映射.json").write_text(
        json.dumps(
            {
                "status": "offline_assets_not_registered_in_application",
                "assets": assets,
                "note": "上传到工作台前须核实素材并映射实际资产ID；既有预览、人审与导出门槛不变。",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"file": str(target), "frames": TOTAL, "duration": DURATION, "sha256": sha(target)},
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    prepare()
    if "--prepare" not in sys.argv:
        if "--finish-only" not in sys.argv:
            render()
        audio()
        finish()
