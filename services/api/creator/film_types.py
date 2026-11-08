"""Type-specific editable compositions, using only supplied media and text."""

from PIL import Image, ImageDraw


def type_layers(shot, canvas, colors, text_block):
    w, h = canvas["width"], canvas["height"]
    portrait = h > w
    unit = min(w, h) / 1080
    layout = shot["design"]["layout"]
    design = shot["design"]
    p = colors
    background = Image.new("RGB", (w, h), p["bg"])
    layers = []

    def layer():
        result = Image.new("RGBA", (w, h))
        layers.append(result)
        return result

    title = design.get("headline") or shot.get("caption", "")
    brand = canvas.get("presentation", {}).get("brand_label", "")
    if layout == "cinema":
        # Drama keeps the actor unobstructed; dialogue belongs on the subtitle track.
        overlay = layer()
        draw = ImageDraw.Draw(overlay)
        draw.rounded_rectangle(
            (w * 0.04, h * 0.035, w * 0.31, h * 0.12), radius=max(2, round(8 * unit)), fill=(5, 12, 18, 155)
        )
        label = "AI剧情演绎" if shot.get("kind") == "ai_creative_scene" else brand or "素材镜头"
        text_block(
            overlay, label, (w * 0.055, h * 0.05, w * 0.24, h * 0.055), 25 * unit, 16 * unit, "#FFFFFF"
        )
        return background, layers, (0, 0, w, h)
    if layout == "montage":
        # Full-bleed footage with a graduated title scrim, not a floating UI card.
        overlay = layer()
        draw = ImageDraw.Draw(overlay)
        for y in range(h):
            bottom = max(0, (y / h - 0.42) / 0.58)
            top = max(0, 1 - y / (h * 0.22))
            draw.line((0, y, w, y), fill=(5, 12, 18, round(max(bottom * 230, top * 130))))
        text_block(overlay, brand, (w * 0.06, h * 0.05, w * 0.8, h * 0.06), 26 * unit, 18 * unit, "#FFFFFF")
        text_block(layer(), title, (w * 0.06, h * 0.55, w * 0.86, h * 0.17), 70 * unit, 30 * unit, "#FFFFFF")
        text_block(
            layer(),
            design.get("supporting", ""),
            (w * 0.06, h * 0.75, w * 0.86, h * 0.06),
            30 * unit,
            18 * unit,
            "#EDF3F6",
        )
        return background, layers, (0, 0, w, h)
    if layout == "comic":
        background.paste("#EEE8DC", (0, 0, w, h))
        bd = ImageDraw.Draw(background)
        for y in range(0, h, max(8, round(22 * unit))):
            for x in range(0, w, max(8, round(22 * unit))):
                bd.ellipse((x, y, x + 1, y + 1), fill="#D4CABB")
        viewport = (round(w * 0.055), round(h * 0.16), round(w * 0.89) // 2 * 2, round(h * 0.44) // 2 * 2)
        x, y, vw, vh = viewport
        bd.rectangle((x + 8, y + 8, x + vw + 8, y + vh + 8), fill="#2A3438")
        bd.rectangle((x - 3, y - 3, x + vw + 3, y + vh + 3), fill="#111B20")
        bubble = layer()
        draw = ImageDraw.Draw(bubble)
        bx, by, bw, bh = w * 0.09, h * 0.57, w * 0.82, h * 0.18
        draw.rounded_rectangle(
            (bx, by, bx + bw, by + bh),
            radius=round(24 * unit),
            fill="#FFFEFA",
            outline="#17272D",
            width=max(1, round(3 * unit)),
        )
        draw.polygon(
            [(bx + bw * 0.12, by), (bx + bw * 0.19, by - h * 0.045), (bx + bw * 0.23, by)], fill="#FFFEFA"
        )
        text_block(
            bubble,
            title,
            (bx + bw * 0.05, by + bh * 0.17, bw * 0.90, bh * 0.68),
            58 * unit,
            27 * unit,
            "#17272D",
        )
        text_block(
            layer(),
            brand + " · " + design.get("kicker", "分镜"),
            (w * 0.055, h * 0.055, w * 0.89, h * 0.06),
            27 * unit,
            17 * unit,
            "#17272D",
        )
        text_block(
            layer(),
            design.get("supporting", ""),
            (w * 0.09, h * 0.76, w * 0.82, h * 0.045),
            27 * unit,
            17 * unit,
            "#3D4B50",
        )
        return background, layers, viewport

    # A process diagram: separately timed nodes, arrows and an animated travelling marker.
    draw = ImageDraw.Draw(background)
    draw.rectangle((0, 0, w, round(h * 0.014)), fill=p["accent"])
    text_block(background, brand, (w * 0.06, h * 0.05, w * 0.84, h * 0.055), 25 * unit, 16 * unit, p["muted"])
    text_block(
        layer(),
        design.get("kicker", ""),
        (w * 0.06, h * 0.15, w * 0.88, h * 0.06),
        25 * unit,
        16 * unit,
        p["accent"],
    )
    text_block(layer(), title, (w * 0.06, h * 0.25, w * 0.88, h * 0.17), 72 * unit, 32 * unit, p["fg"])
    points = design.get("points") or [title]
    count = len(points)
    if count > 1:
        if portrait:
            draw.line(
                (w * 0.14, h * 0.4875, w * 0.14, h * 0.7175), fill=p["accent"], width=max(2, round(3 * unit))
            )
        else:
            draw.line(
                (w * 0.16, h * 0.63, w * 0.84, h * 0.63), fill=p["accent"], width=max(2, round(3 * unit))
            )
    for i, point in enumerate(points):
        node = layer()
        nd = ImageDraw.Draw(node)
        if portrait:
            x, y, cw, ch = w * 0.065, h * (0.44 + 0.115 * i), w * 0.87, h * 0.095
        else:
            cw, ch = w * 0.255, h * 0.25
            x, y = w * 0.065 + i * w * 0.3075, h * 0.50
        nd.rounded_rectangle(
            (x, y, x + cw, y + ch),
            radius=max(5, round(22 * unit)),
            fill=p["panel"],
            outline=p["accent"],
            width=max(1, round(2 * unit)),
        )
        text_block(
            node,
            f"{i + 1:02d}",
            (x + cw * 0.07, y + ch * 0.1, cw * 0.25, ch * 0.23),
            28 * unit,
            17 * unit,
            p["accent"],
        )
        text_block(
            node, point, (x + cw * 0.07, y + ch * 0.38, cw * 0.86, ch * 0.53), 36 * unit, 18 * unit, p["fg"]
        )
    if design.get("supporting"):
        text_block(
            layer(),
            design["supporting"],
            (w * 0.065, h * 0.78, w * 0.87, h * 0.04),
            30 * unit,
            17 * unit,
            p["muted"],
        )
    return background, layers, None
