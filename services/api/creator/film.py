"""Native-size product-film scenes made from editable text and real media."""

from PIL import Image, ImageDraw, ImageColor

from .domains import file_path, font
from .errors import DomainError
from .graphics import wrap_text

VERSION = "video_presentation@1"


def scene_layout(shot):
    layout = shot.get("design", {}).get("layout", "auto")
    return ("screen" if shot.get("asset_id") else "hero") if layout == "auto" else layout


def palette(presentation):
    if presentation.get("theme") == "paper":
        return {
            "bg": "#F1F2ED",
            "fg": "#16272A",
            "muted": "#536368",
            "panel": "#FFFFFF",
            "line": "#CED6D0",
            "accent": presentation.get("accent", "#356A37"),
        }
    return {
        "bg": "#0B1419",
        "fg": "#F4F5EF",
        "muted": "#A6B4B9",
        "panel": "#17242B",
        "line": "#2E3D42",
        "accent": presentation.get("accent", "#B7F56B"),
    }


def text_block(image, text, box, size, minimum, fill):
    if not text:
        return
    x, y, width, height = box
    draw = ImageDraw.Draw(image)
    size, minimum = max(9, round(size)), max(8, round(minimum))
    for selected in range(size, minimum - 1, -1):
        face = font(selected)
        lines = wrap_text(draw, text, face, width)
        if len(lines) * selected * 1.42 <= height:
            for i, line in enumerate(lines):
                draw.text((x, y + i * selected * 1.42), line, fill=fill, font=face)
            return
    raise DomainError(
        "VID_DESIGN_TEXT_OVERFLOW", "当前版式文字过长，请缩短主标题或将说明移到补充文案/要点", 422
    )


def layers_for(shot, canvas):
    w, h = canvas["width"], canvas["height"]
    p = palette(canvas.get("presentation", {}))
    design = shot.get("design", {})
    layout = scene_layout(shot)
    portrait = h > w
    unit = min(w, h) / 1080
    margin = round(w * 0.065)
    background = Image.new("RGB", (w, h), p["bg"])
    draw = ImageDraw.Draw(background)
    grid_color = tuple(
        round(a * 0.75 + b * 0.25)
        for a, b in zip(ImageColor.getrgb(p["bg"]), ImageColor.getrgb(p["line"]), strict=True)
    )
    # A quiet grid anchors scene changes without inventing product UI or charts.
    for i in range(1, 9):
        x = round(w * i / 9)
        draw.line((x, 0, x, h), fill=grid_color, width=1)
    draw.rectangle((0, 0, w, round(h * 0.015)), fill=p["accent"])
    draw.rectangle((0, round(h * 0.89), w, h), fill=p["bg"])
    brand = canvas.get("presentation", {}).get("brand_label", "")
    text_block(background, brand, (margin, h * 0.045, w * 0.67, h * 0.06), 25 * unit, 16 * unit, p["muted"])
    chapter = f"{canvas.get('chapter', 1):02d} / {canvas.get('chapters', 1):02d}"
    text_block(
        background, chapter, (w * 0.84, h * 0.045, w * 0.13, h * 0.05), 21 * unit, 14 * unit, p["muted"]
    )
    layers = []

    def layer():
        image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        layers.append(image)
        return image

    headline = design.get("headline") or shot.get("caption") or ""
    supporting = design.get("supporting", "")
    kicker = design.get("kicker", "")
    points = design.get("points", [])
    viewport = None
    if shot.get("asset_id"):
        # The framed surface is explicitly the supplied recording/screenshot.
        if layout == "hero":
            viewport = (
                round(w * (0.065 if portrait else 0.52)),
                round(h * (0.48 if portrait else 0.23)),
                round(w * (0.87 if portrait else 0.445)),
                round(h * (0.36 if portrait else 0.56)),
            )
            title_box = (
                margin,
                h * (0.17 if portrait else 0.32),
                w * (0.87 if portrait else 0.39),
                h * (0.24 if portrait else 0.29),
            )
        elif layout == "focus":
            viewport = (round(w * 0.045), round(h * 0.13), round(w * 0.91), round(h * 0.67))
            title_box = (margin, h * 0.805, w * 0.83, h * 0.065)
        else:
            viewport = (
                round(w * 0.065),
                round(h * (0.36 if portrait else 0.26)),
                round(w * 0.87),
                round(h * (0.44 if portrait else 0.55)),
            )
            title_box = (margin, h * 0.15, w * 0.86, h * (0.17 if portrait else 0.095))
        frame = ImageDraw.Draw(background)
        x, y, vw, vh = viewport
        vw, vh = max(2, vw // 2 * 2), max(2, vh // 2 * 2)
        viewport = x, y, vw, vh
        frame.rounded_rectangle(
            (x - 5, y - 24 * unit, x + vw + 5, y + vh + 5),
            radius=max(4, round(16 * unit)),
            fill=p["panel"],
            outline=p["line"],
            width=2,
        )
        title_layer = layer()
        text_block(
            title_layer,
            headline,
            title_box,
            (82 if layout == "hero" else 48 if layout == "focus" else 56) * unit,
            26 * unit,
            p["fg"],
        )
        if kicker:
            text_block(
                title_layer,
                kicker,
                (margin, h * 0.105, w * 0.82, h * 0.045),
                23 * unit,
                15 * unit,
                p["accent"],
            )
        if supporting and layout != "focus":
            text_block(
                layer(),
                supporting,
                (
                    margin,
                    h * (0.64 if layout == "hero" and not portrait else 0.85),
                    w * (0.38 if layout == "hero" and not portrait else 0.86),
                    h * (0.15 if layout == "hero" and not portrait else 0.045),
                ),
                29 * unit,
                15 * unit,
                p["muted"],
            )
    elif layout in ("features", "steps") and points:
        title_layer = layer()
        text_block(
            title_layer, kicker, (margin, h * 0.15, w * 0.86, h * 0.055), 24 * unit, 16 * unit, p["accent"]
        )
        text_block(
            title_layer, headline, (margin, h * 0.24, w * 0.85, h * 0.20), 74 * unit, 35 * unit, p["fg"]
        )
        count = len(points)
        for i, point in enumerate(points):
            card = layer()
            if portrait:
                x, y, cw, ch = margin, h * (0.47 + i * 0.12), w * 0.87, h * 0.10
            else:
                gap = w * 0.025
                cw = (w * 0.87 - gap * (count - 1)) / count
                x, y, ch = margin + i * (cw + gap), h * 0.51, h * 0.28
            cd = ImageDraw.Draw(card)
            cd.rounded_rectangle(
                (x, y, x + cw, y + ch),
                radius=max(5, round(18 * unit)),
                fill=p["panel"],
                outline=p["line"],
                width=max(1, round(2 * unit)),
            )
            cd.rectangle((x + cw * 0.06, y + ch * 0.1, x + cw * 0.08, y + ch * 0.28), fill=p["accent"])
            text_block(
                card,
                f"{i + 1:02d}",
                (x + cw * 0.13, y + ch * 0.10, cw * 0.7, ch * 0.19),
                27 * unit,
                17 * unit,
                p["accent"],
            )
            text_block(
                card,
                point,
                (x + cw * 0.08, y + ch * 0.37, cw * 0.84, ch * 0.55),
                37 * unit,
                19 * unit,
                p["fg"],
            )
    else:
        first = layer()
        text_block(first, kicker, (margin, h * 0.22, w * 0.85, h * 0.07), 27 * unit, 18 * unit, p["accent"])
        text_block(
            first,
            headline,
            (margin, h * 0.34, w * 0.84, h * 0.30),
            (92 if layout != "closing" else 100) * unit,
            40 * unit,
            p["fg"],
        )
        second = layer()
        text_block(
            second, supporting, (margin, h * 0.69, w * 0.76, h * 0.15), 35 * unit, 21 * unit, p["muted"]
        )
        sd = ImageDraw.Draw(second)
        sd.rounded_rectangle(
            (margin, h * 0.64, margin + w * (0.23 if layout == "closing" else 0.12), h * 0.647),
            radius=max(1, round(3 * unit)),
            fill=p["accent"],
        )
    return background, layers, viewport


def render_scene(shot, canvas, target, asset=None):
    from .video import ffmpeg

    w, h, fps = canvas["width"], canvas["height"], canvas["fps"]
    frames = shot["duration_frames"]
    duration = frames / fps
    background, layers, viewport = layers_for(shot, canvas)
    files = []
    args, filters = [], []

    def png_input(image, suffix):
        path = target.with_name(target.stem + suffix + ".png")
        image.save(path)
        files.append(path)
        args.extend(["-loop", "1", "-framerate", str(fps), "-i", str(path)])

    png_input(background, "-background")
    base = "0:v"
    input_index = 1
    if asset:
        source = file_path(asset.workspace_id, asset.sha256, asset.suffix)
        if asset.kind == "image":
            args.extend(["-loop", "1", "-framerate", str(fps), "-i", str(source)])
        else:
            args.extend(["-ss", str(shot.get("trim_start_frame", 0) / fps), "-i", str(source)])
        crop = shot.get("design", {}).get("crop", {})
        x, y, vw, vh = viewport
        # Numeric, validated frame percentages; user text never enters filter syntax.
        chain = f"crop=iw*{crop.get('width', 100)}/100:ih*{crop.get('height', 100)}/100:iw*{crop.get('x', 0)}/100:ih*{crop.get('y', 0)}/100,setpts=PTS/{shot.get('speed_percent', 100) / 100},fps={fps}"
        if shot.get("freeze_end_frames"):
            chain += f",trim=end_frame={frames - shot['freeze_end_frames']},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop={shot['freeze_end_frames']}"
        chain += f",scale={vw}:{vh}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos,pad={vw}:{vh}:(ow-iw)/2:(oh-ih)/2:color=0x111A20,setsar=1[media]"
        motion = shot.get("design", {}).get("motion", "push")
        if motion != "still":
            chain = chain.removesuffix("[media]")
            progress = f"min(1,on/{max(1, frames - 1)})"
            zoom = f"1+0.06*{progress}" if motion == "push" else "1.06"
            left = f"(iw-iw/zoom)*{progress}" if motion == "pan" else "(iw-iw/zoom)/2"
            chain += f",zoompan=z='{zoom}':x='{left}':y='(ih-ih/zoom)/2':d=1:s={vw}x{vh}:fps={fps}[media]"
        filters.append(f"[1:v]{chain}")
        filters.append(f"[0:v][media]overlay=x={x}:y={y}:eof_action=repeat[screen]")
        base = "screen"
        input_index += 1
    for i, image in enumerate(layers):
        png_input(image, f"-layer-{i}")
        delay = min(0.35, i * 0.12)
        fade = min(0.32, duration / 4)
        filters.append(f"[{input_index}:v]format=rgba,fade=t=in:st={delay}:d={fade}:alpha=1[layer{i}]")
        offset = round(25 * min(w, h) / 1080)
        filters.append(
            f"[{base}][layer{i}]overlay=x=0:y='{offset}*max(0,1-(t-{delay})/0.6)^3':eof_action=repeat[v{i}]"
        )
        base = f"v{i}"
        input_index += 1
    if canvas.get("presentation", {}).get("transition") == "dip":
        length = min(0.18, duration / 5)
        filters.append(
            f"[{base}]fade=t=in:st=0:d={length},fade=t=out:st={duration - length}:d={length}[final]"
        )
        base = "final"
    try:
        ffmpeg(
            [
                *args,
                "-filter_complex_threads",
                "1",
                "-filter_complex",
                ";".join(filters),
                "-map",
                f"[{base}]",
                "-frames:v",
                str(frames),
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                str(target),
            ]
        )
    finally:
        for path in files:
            path.unlink(missing_ok=True)
