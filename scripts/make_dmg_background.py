#!/usr/bin/env python3
"""Erzeugt assets/dmg-background.png — das Hintergrund-Bild für die DMG.

600×400 mit Lila-Gradient, Pfeil zwischen App-Position und Applications-Icon
und einem dezenten Hinweistext.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).parent.parent
OUT = ROOT / "assets" / "dmg-background.png"

W, H = 600, 400
BG_TOP = (148, 114, 255)
BG_BOTTOM = (90, 62, 255)


def gradient(size_w: int, size_h: int) -> Image.Image:
    img = Image.new("RGB", (size_w, size_h), BG_TOP)
    px = img.load()
    for y in range(size_h):
        t = y / (size_h - 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        for x in range(size_w):
            px[x, y] = (r, g, b)
    return img


def main():
    img = gradient(W, H).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Pfeil von App-Position (175, 190) zu Applications (425, 190)
    arrow_y = 195
    arrow_start_x = 245
    arrow_end_x = 355
    # Linie
    draw.line([(arrow_start_x, arrow_y), (arrow_end_x, arrow_y)],
               fill=(255, 255, 255, 200), width=4)
    # Pfeilspitze
    tip = arrow_end_x + 18
    draw.polygon(
        [(arrow_end_x, arrow_y - 12),
         (tip, arrow_y),
         (arrow_end_x, arrow_y + 12)],
        fill=(255, 255, 255, 220),
    )

    # Hinweis-Text oben
    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/SFNS.ttf", 22)
    except Exception:
        font = ImageFont.load_default()

    draw.text((W / 2, 50), "Install Broomstick",
               fill=(255, 255, 255, 230), font=font, anchor="mm")
    try:
        font2 = ImageFont.truetype(
            "/System/Library/Fonts/SFNS.ttf", 14)
    except Exception:
        font2 = ImageFont.load_default()
    draw.text((W / 2, 78), "Drag the app to your Applications folder",
               fill=(255, 255, 255, 180), font=font2, anchor="mm")

    img.save(OUT)
    print(f"✓ {OUT}")

    # Außerdem: 2x-Variante für Retina (1200x800)
    out_2x = OUT.with_name("dmg-background@2x.png")
    img2 = gradient(W * 2, H * 2).convert("RGBA")
    d2 = ImageDraw.Draw(img2)
    d2.line([(arrow_start_x * 2, arrow_y * 2),
              (arrow_end_x * 2, arrow_y * 2)],
             fill=(255, 255, 255, 200), width=8)
    d2.polygon(
        [(arrow_end_x * 2, (arrow_y - 12) * 2),
         (tip * 2, arrow_y * 2),
         (arrow_end_x * 2, (arrow_y + 12) * 2)],
        fill=(255, 255, 255, 220),
    )
    try:
        font_big = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 44)
        font_small = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 28)
    except Exception:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
    d2.text((W, 100), "Install Broomstick",
             fill=(255, 255, 255, 230), font=font_big, anchor="mm")
    d2.text((W, 156), "Drag the app to your Applications folder",
             fill=(255, 255, 255, 180), font=font_small, anchor="mm")
    img2.save(out_2x)
    print(f"✓ {out_2x}")


if __name__ == "__main__":
    main()
