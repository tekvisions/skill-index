#!/usr/bin/env python3
"""Render og.png (1200x630) for The Skill Index — editorial almanac card. Pillow only.
Falls back to a clean solid card if a font isn't found, so CI never fails on fonts."""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def _font(paths, size):
    from PIL import ImageFont
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _fit_font(draw, paths, lines, size, width):
    font = _font(paths, size)
    while max(draw.textlength(line, font=font) for line in lines) > width and size > 12:
        size -= 1
        font = _font(paths, size)
    return font


def main() -> int:
    try:
        from PIL import Image, ImageDraw
        from PIL.PngImagePlugin import PngInfo
    except Exception:
        raise RuntimeError("Pillow is required to rebuild the reviewed-count share card")
    try:
        data = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
        count = data.get("count", 0)
        cats = len(data.get("categories", []))
    except Exception:
        raise ValueError("A valid curated catalog snapshot is required for the share card")

    W, H = 1200, 630
    bg = (246, 241, 231)
    ink = (27, 24, 18)
    amber = (179, 101, 31)
    teal = (47, 111, 96)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    serif = ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
             "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
             "/Library/Fonts/Georgia.ttf"]
    mono = ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.ttf"]
    f_kick = _font(mono, 26)
    f_h1 = _fit_font(d, serif, ["Agent skills,", "in one catalog,", "ranked by momentum."], 86, W - 140)
    f_stat = _font(mono, 30)

    # frame rule
    d.rectangle([40, 40, W - 40, H - 40], outline=ink, width=3)
    d.line([40, 120, W - 40, 120], fill=ink, width=2)

    d.text((70, 70), "THE  SKILL  INDEX", font=f_kick, fill=amber)
    d.text((70, 180), "Agent skills,", font=f_h1, fill=ink)
    d.text((70, 280), "in one catalog,", font=f_h1, fill=ink)
    d.text((70, 380), "ranked by ", font=f_h1, fill=ink)
    # "momentum." in amber, on same baseline
    w = d.textlength("ranked by ", font=f_h1)
    d.text((70 + w, 380), "momentum.", font=f_h1, fill=amber)

    d.line([70, 500, W - 70, 500], fill=teal, width=2)
    footer = f"{count} ranked skills  ·  {cats} categories  ·  snapshot {data['generated_at'][:10]}"
    f_stat = _fit_font(d, mono, [footer], 30, W - 140)
    d.text((70, 525), footer, font=f_stat, fill=(109, 100, 82))

    metadata = PngInfo()
    metadata.add_text("CatalogCount", str(count))
    metadata.add_text("CatalogScope", "ranked core entries; unranked review references excluded")
    metadata.add_text("SourceSnapshot", data["generated_at"])
    metadata.add_text("FooterText", footer)
    metadata.add_text("FooterWidth", str(d.textlength(footer, font=f_stat)))
    img.save(os.path.join(HERE, "og.png"), pnginfo=metadata)
    print(f"wrote og.png ({count} skills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
