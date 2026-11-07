"""CPU composition of user-authorized audio and measured subtitle layouts."""

from PIL import Image, ImageDraw

from .domains import file_path, font, owned
from .graphics import wrap_text
from .models import Asset


def ass_subtitles(ir):
    def stamp(frame):
        cs = round(frame * 100 / ir["fps"])
        return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"

    studio = ir.get("presentation", {}).get("style") == "studio"
    scale = min(1, ir["width"] / 1080, ir["height"] / 1080)
    initial_size, min_size = max(12, round(36 * scale)), max(8, round(24 * scale))
    margin, margin_v = round(80 * scale), round(70 * scale)
    if studio:
        scale = min(ir["width"], ir["height"]) / 1080
        initial_size, min_size = max(12, round(44 * scale)), max(10, round(34 * scale))
        margin, margin_v = round(ir["width"] * 0.10), round(ir["height"] * 0.06)
    face = font(initial_size)
    family = face.getname()[0].replace(",", " ").replace("\n", " ")
    width, height = ir["width"], ir["height"]
    out = [
        f"[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{family},{initial_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,2,1,2,{margin},{margin},{margin_v},1",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for cue in ir.get("subtitles", []):
        size = initial_size
        while (
            size > min_size
            and len(wrap_text(draw, cue["text"], font(size), width - 2 * margin)) * size * 1.42
            > height * 0.25
        ):
            size -= 2
        lines = wrap_text(draw, cue["text"], font(size), width - 2 * margin)
        # User text cannot inject ASS tags or create additional dialogue records.
        text = r"\N".join(
            line.replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\r", "") for line in lines
        )
        out.append(
            f"Dialogue: 0,{stamp(cue['start_frame'])},{stamp(cue['end_frame'])},Default,,0,0,0,,{{\\fs{size}}}{text}"
        )
    return "\n".join(out) + "\n"


def finish(db, job, target):
    from .video import ffmpeg

    ir = job.ir
    tracks = ir.get("audio_tracks", [])
    cues = ir.get("subtitles", [])
    studio_audio = ir.get("presentation", {}).get("style") == "studio" and ir.get("presentation", {}).get(
        "audio_finish", True
    )
    if not tracks and not cues:
        return []
    args, filters, sources = ["-i", str(target)], [], []
    for index, track in enumerate(tracks, 1):
        asset = owned(db, Asset, track["asset_id"], job.workspace_id)
        if track.get("loop"):
            args.extend(["-stream_loop", "-1"])
        args.extend(["-i", str(file_path(asset.workspace_id, asset.sha256, asset.suffix))])
        start = track.get("source_start_frame", 0) / ir["fps"]
        duration = track["duration_frames"] / ir["fps"]
        delay = round(track["start_frame"] * 1000 / ir["fps"])
        volume = track.get("volume_percent", 100) / 100
        filters.append(
            f"[{index}:a]atrim=start={start}:duration={duration},asetpts=PTS-STARTPTS,volume={volume},aresample=48000,aformat=channel_layouts=stereo,adelay={delay}|{delay}[a{index}]"
        )
        sources.append(
            {
                "track_id": track["track_id"],
                "role": track["role"],
                "asset_id": asset.id,
                "sha256": asset.sha256,
                "source": asset.source,
                "license_note": asset.license_note,
            }
        )
    if tracks and studio_audio:
        voice = [f"[a{i}]" for i, t in enumerate(tracks, 1) if t["role"] == "voiceover"]
        music = [f"[a{i}]" for i, t in enumerate(tracks, 1) if t["role"] == "music"]
        mixed = ["[0:a]"]
        if voice:
            filters.append(
                "".join(voice)
                + f"amix=inputs={len(voice)}:normalize=0:duration=longest,apad"
                + (",asplit=2[voice][side]" if music else "[voice]")
            )
            mixed.append("[voice]")
        if music:
            filters.append(
                "".join(music) + f"amix=inputs={len(music)}:normalize=0:duration=longest,apad[bgm]"
            )
            if voice:
                filters.append(
                    "[bgm][side]sidechaincompress=threshold=0.025:ratio=6:attack=15:release=350[ducked]"
                )
                mixed.append("[ducked]")
            else:
                mixed.append("[bgm]")
        length = sum(s["duration_frames"] for s in ir["shots"]) / ir["fps"]
        filters.append(
            "".join(mixed)
            + f"amix=inputs={len(mixed)}:normalize=0:duration=first,afade=t=in:d=0.06,afade=t=out:st={max(0, length - 0.35)}:d=0.35,loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000[audio]"
        )
        args.extend(
            [
                "-filter_complex_threads",
                "1",
                "-filter_complex",
                ";".join(filters),
                "-map",
                "0:v",
                "-map",
                "[audio]",
            ]
        )
    elif tracks:
        inputs = "[0:a]" + "".join(f"[a{i}]" for i in range(1, len(tracks) + 1))
        filters.append(
            f"{inputs}amix=inputs={len(tracks) + 1}:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[audio]"
        )
        args.extend(["-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[audio]"])
    else:
        args.extend(["-map", "0:v", "-map", "0:a"])
    subtitle_file = target.parent / (job.id + ".ass")
    output = target.with_name("mix-" + job.id + ".mp4")
    try:
        if cues:
            subtitle_file.write_text(ass_subtitles(ir), encoding="utf-8")
            args.extend(
                [
                    "-vf",
                    "subtitles=" + subtitle_file.name,
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "18" if studio_audio else "21",
                    "-pix_fmt",
                    "yuv420p",
                ]
            )
        else:
            args.extend(["-c:v", "copy"])
        ffmpeg(
            [
                *args,
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-t",
                str(sum(s["duration_frames"] for s in ir["shots"]) / ir["fps"]),
                "-movflags",
                "+faststart",
                str(output),
            ],
            cwd=target.parent,
        )
        output.replace(target)
    finally:
        subtitle_file.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
    return sources
