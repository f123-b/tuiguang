"""Independent, review-only film edit using actual generated shots and verified product footage."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".data/ai-drama-quality-v2"


def run(args):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *args],
        cwd=OUT,
        check=True,
        timeout=300,
    )


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp(seconds):
    centiseconds = round(seconds * 100)
    return f"{centiseconds // 360000}:{centiseconds // 6000 % 60:02}:{centiseconds // 100 % 60:02}.{centiseconds % 100:02}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--take", default="v2-a")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]{1,40}", args.take):
        raise ValueError("invalid take name")
    target = OUT / ("youzhao-choice-" + args.take + "-review.mp4")
    if target.exists():
        raise RuntimeError("Use a new take name; preserve reviewed cuts")
    for name in (
        "native.webm",
        "closeup.webm",
        "comparison-history.json",
        "closeup-history.json",
        "voices/receipts.json",
    ):
        if not (OUT / name).is_file():
            raise RuntimeError("Required real generation output not available: " + name)
    for name in ("comparison-history.json", "closeup-history.json"):
        assert json.loads((OUT / name).read_text(encoding="utf-8"))["status"]["completed"]
    ui = ROOT / "examples/video-production/youzhao-choice/assets/youzhao-note-pickup-v1.mp4"
    assert sha(ui) == "faf11b6936c4b90ce16552994ec7f6b7c2203d5d5fc19aed5be79610c1fbe61b"
    face = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 56)
    small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
    card = Image.new("RGB", (1280, 720), "#101818")
    draw = ImageDraw.Draw(card)
    draw.text((640, 300), "有招", font=face, fill="#EAF3E9", anchor="mm")
    draw.text(
        (640, 390),
        "把你做过的，讲清楚。",
        font=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 32),
        fill="#B9D7C7",
        anchor="mm",
    )
    draw.text((640, 655), "AI 剧情演绎 · 合成配音 · 本地审看版本", font=small, fill="#819589", anchor="mm")
    card.save(OUT / "brand-card.png")
    common = "scale=1280:720:force_original_aspect_ratio=increase:flags=lanczos,crop=1280:720,setsar=1,fps=30"
    scenes = [
        ("s01", OUT / "native.webm", 0, 61, common),
        ("s02", OUT / "closeup.webm", 0, 45, common),
        ("s03", ui, 3.6, 189, "crop=480:270:1440:184,scale=1280:720:flags=lanczos,setsar=1,fps=30"),
        ("s04", OUT / "closeup.webm", 1.5, 106, common),
    ]
    manifest = []
    for identifier, source, start, frames, filters in scenes:
        run(
            [
                "-ss",
                str(start),
                "-i",
                str(source),
                "-vf",
                filters,
                "-frames:v",
                str(frames),
                "-an",
                "-c:v",
                "libx264",
                "-crf",
                "17",
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                identifier + ".mp4",
            ]
        )
        manifest.append(
            {
                "shot_id": identifier,
                "source": str(source.relative_to(ROOT)),
                "source_sha256": sha(source),
                "source_start_sec": start,
                "duration_frames": frames,
                "fps": 30,
                "kind": "screen_demo" if identifier == "s03" else "ai_creative_scene",
                "clip_editability": "trim_and_regenerate",
                "source_is_actual_product": identifier == "s03",
            }
        )
    run(
        [
            "-loop",
            "1",
            "-i",
            "brand-card.png",
            "-vf",
            "fps=30,fade=t=in:st=0:d=0.25,fade=t=out:st=2.35:d=0.35",
            "-frames:v",
            "81",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
            "s05.mp4",
        ]
    )
    (OUT / "concat.txt").write_text(
        "\n".join("file '" + name + ".mp4'" for name in ["s01", "s02", "s03", "s04", "s05"]), encoding="utf-8"
    )
    run(["-f", "concat", "-safe", "1", "-i", "concat.txt", "-c", "copy", "picture.mp4"])
    duration = 482 / 30
    cues = [
        ("question", 0.25, "当时，为什么没选另一个方案？"),
        ("thought", 3.25, "我记得。我把它写下来了。"),
        ("choice", 8.8, "先让人找到，再继续看。"),
        ("brand", 12.2, "有招，把你做过的，讲清楚。"),
    ]
    voices = json.loads((OUT / "voices/receipts.json").read_text(encoding="utf-8"))
    inputs = ["-i", "picture.mp4"]
    for identifier, _, _ in cues:
        inputs.extend(["-i", str(OUT / "voices" / (identifier + ".wav"))])
    inputs.extend(
        [
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=pink:amplitude=0.012:sample_rate=48000:duration={duration}:seed=37",
        ]
    )
    filters = []
    for index, (_, start, _) in enumerate(cues, 1):
        filters.append(
            f"[{index}:a]aresample=48000,highpass=f=70,loudnorm=I=-18:TP=-2:LRA=8,adelay={round(start * 1000)}:all=1[a{index}]"
        )
    filters.extend(
        [
            "[5:a]highpass=f=180,lowpass=f=5500,volume=0.45[room]",
            "[a1][a2][a3][a4][room]amix=inputs=5:normalize=0:duration=longest,alimiter=limit=0.79:level=0,afade=t=out:st=15.45:d=0.6[aout]",
        ]
    )
    header = """[Script Info]\nScriptType: v4.00+\nPlayResX: 1280\nPlayResY: 720\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Default,Microsoft Yahei,32,&H00FFFFFF,&H00FFFFFF,&HAA0C1216,&H00000000,0,0,0,0,100,100,0,0,1,1.5,0,2,60,60,36,1\nStyle: Label,Microsoft Yahei,17,&H00D8E8E2,&H00FFFFFF,&HAA0C1216,&H00000000,0,0,0,0,100,100,0,0,1,1,0,7,24,24,18,1\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"""
    events = []
    for identifier, start, text in cues:
        length = next(v["duration"] for v in voices if v["id"] == identifier)
        events.append(f"Dialogue: 1,{timestamp(start)},{timestamp(start + length)},Default,,0,0,0,,{text}")
    events.extend(
        [
            "Dialogue: 0,0:00:00.00,0:00:03.53,Label,,0,0,0,,AI剧情演绎 · 合成声音",
            "Dialogue: 0,0:00:03.53,0:00:09.83,Label,,0,0,0,,有招真实界面 · 虚构项目练习",
            "Dialogue: 0,0:00:09.83,0:00:13.37,Label,,0,0,0,,AI剧情演绎 · 合成声音",
        ]
    )
    (OUT / "subtitles.ass").write_text(header + "\n".join(events), encoding="utf-8-sig")
    filters.append("[0:v]subtitles=filename=subtitles.ass[vout]")
    run(
        [
            *inputs,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-t",
            str(duration),
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
            "-ar",
            "48000",
            "-map_metadata",
            "-1",
            "-movflags",
            "+faststart",
            str(target),
        ]
    )
    document = {
        "version": "choice_ai_review@2",
        "take": args.take,
        "art_review": "requires_user",
        "not_an_approved_publication_package": True,
        "video_ir_schema_version": "1.1",
        "shots": manifest,
        "sources": {
            "comparison": "comparison-receipt.json",
            "closeup": "closeup-receipt.json",
            "voices": "voices/receipts.json",
        },
        "sound_effects": "Original procedural pink-noise room/rain texture, no stock music",
        "frames": 482,
        "fps": 30,
        "output": target.name,
        "output_sha256": sha(target),
        "duration_sec": duration,
    }
    (OUT / (args.take + "-edit-receipt.json")).write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    from creator.schemas import VideoInput

    generation = {
        name: json.loads((OUT / name).read_text(encoding="utf-8"))
        for name in ("comparison-receipt.json", "closeup-receipt.json")
    }
    assets = {
        row["source_sha256"][:32]: {"path": row["source"], "sha256": row["source_sha256"]} for row in manifest
    }
    card_sha = sha(OUT / "brand-card.png")
    assets[card_sha[:32]] = {"path": str((OUT / "brand-card.png").relative_to(ROOT)), "sha256": card_sha}
    shots = []
    for row in manifest:
        generated = row["kind"] == "ai_creative_scene"
        record = (
            generation["comparison-receipt.json" if row["shot_id"] == "s01" else "closeup-receipt.json"]
            if generated
            else None
        )
        shots.append(
            {
                "shot_id": row["shot_id"],
                "provider": "comfy_wan" if generated else "ffmpeg_media",
                "kind": row["kind"],
                "asset_id": row["source_sha256"][:32],
                **({"generation_job_id": record["job_id"]} if record else {}),
                "duration_frames": row["duration_frames"],
                "trim_start_frame": round(row["source_start_sec"] * 30),
                "caption": "人物反应" if generated else "有招真实项目备注操作",
                "design": {
                    "layout": "cinema",
                    "motion": "still",
                    **({"crop": {"x": 75, "y": 17, "width": 25, "height": 25}} if not generated else {}),
                },
            }
        )
    shots.append(
        {
            "shot_id": "s05",
            "provider": "ffmpeg_media",
            "kind": "montage",
            "asset_id": card_sha[:32],
            "duration_frames": 81,
            "caption": "有招，把你做过的，讲清楚。",
            "design": {"layout": "cinema", "motion": "still"},
        }
    )
    tracks, subtitles = [], []
    for identifier, start, text in cues:
        path = OUT / "voices" / (identifier + ".wav")
        asset_sha = sha(path)
        assets[asset_sha[:32]] = {"path": str(path.relative_to(ROOT)), "sha256": asset_sha}
        frames = int(next(v["duration"] for v in voices if v["id"] == identifier) * 30)
        tracks.append(
            {
                "track_id": identifier,
                "asset_id": asset_sha[:32],
                "role": "voiceover",
                "start_frame": round(start * 30),
                "duration_frames": frames,
            }
        )
        subtitles.append(
            {
                "cue_id": identifier,
                "start_frame": round(start * 30),
                "end_frame": round(start * 30) + frames,
                "text": text,
            }
        )
    ir = VideoInput(
        brand_id="youzhao-fictional-review",
        name="那个选择·AI重拍审看",
        width=1920,
        height=1080,
        shots=shots,
        audio_tracks=tracks,
        subtitles=subtitles,
        preview_required=True,
        presentation={"style": "studio", "brand_label": "有招 / 审看版本"},
    ).model_dump()
    ir.update(
        schema_version="1.1",
        offline_scope="independent_review_edit; requires real brand/asset/job ID mapping before app import",
        offline_assets=assets,
        edit_receipt=args.take + "-edit-receipt.json",
        export_adapter="choice_ai_review@2",
        technical_preview_canvas={"width": 1280, "height": 720},
        user_approval=False,
    )
    (OUT / (args.take + "-video-project-ir.json")).write_text(
        json.dumps(ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(target)


if __name__ == "__main__":
    main()
