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


def main() -> int:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        print("Pillow not available — skipping og.png (kept existing if any)")
        return 0
    try:
        data = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
        count = data.get("count", 0)
        cats = len(data.get("categories", []))
    except Exception:
        count, cats = 0, 0

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
    f_h1 = _font(serif, 86)
    f_stat = _font(mono, 30)

    # frame rule
    d.rectangle([40, 40, W - 40, H - 40], outline=ink, width=3)
    d.line([40, 120, W - 40, 120], fill=ink, width=2)

    d.text((70, 70), "THE  SKILL  INDEX", font=f_kick, fill=amber)
    d.text((70, 180), "Every skill", font=f_h1, fill=ink)
    d.text((70, 280), "worth knowing,", font=f_h1, fill=ink)
    d.text((70, 380), "ranked by ", font=f_h1, fill=ink)
    # "momentum." in amber, on same baseline
    w = d.textlength("ranked by ", font=f_h1)
    d.text((70 + w, 380), "momentum.", font=f_h1, fill=amber)

    d.line([70, 500, W - 70, 500], fill=teal, width=2)
    d.text((70, 525), f"{count} skills  ·  {cats} categories  ·  recomputed daily from live GitHub signals",
           font=f_stat, fill=(109, 100, 82))

    img.save(os.path.join(HERE, "og.png"))
    print(f"wrote og.png ({count} skills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
