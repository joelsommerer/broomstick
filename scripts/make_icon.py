#!/usr/bin/env python3
"""Erzeugt assets/icon.icns für das App-Bundle.

Design:
- Lila-Squircle-Hintergrund mit Top-Light-Gradient
- Phosphor "broom" Icon weiß zentriert (Duotone via zwei Layer)
- Subtiler innerer Highlight oben (macOS-Look)
- Soft drop-shadow unter dem Icon

Schritte:
1. Render Master 1024×1024 mit PIL
2. Skaliert via `sips` runter auf alle iconset-Größen
3. Konvertiert mit `iconutil` zum .icns
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).parent.parent
ASSETS = ROOT / "assets"
FONT = ASSETS / "Phosphor-Duotone.ttf"
ICONSET_TMP = ASSETS / "icon.iconset"
ICNS_OUT = ASSETS / "icon.icns"
MASTER_OUT = ASSETS / "icon-master.png"

# Phosphor "broom" Codepoints (Duotone)
BROOM_BEFORE = ""   # helle Schicht
BROOM_AFTER = ""    # volle Schicht

# Farben
BG_TOP = (148, 114, 255)       # #9472ff helleres Lila oben
BG_BOTTOM = (90, 62, 255)      # #5a3eff dunkleres Lila unten
ICON_WHITE = (255, 255, 255)
ICON_TINT = (220, 200, 255)    # leicht-violett tönender Vordergrund-Akzent


def make_gradient(size: int, top: tuple, bottom: tuple) -> Image.Image:
    """Vertikaler Linear-Gradient als RGB-Image."""
    img = Image.new("RGB", (size, size), top)
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        for x in range(size):
            px[x, y] = (r, g, b)
    return img


def squircle_mask(size: int, radius: int) -> Image.Image:
    """Schwarz-weiße Maske für abgerundetes Quadrat (macOS-Squircle)."""
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=radius, fill=255,
    )
    return mask


def add_top_highlight(img: Image.Image, intensity: int = 35):
    """Subtile helle Linie ganz oben — macOS Squircle-Highlight."""
    size = img.size[0]
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    # Top-Highlight: 4% Höhe, weiß mit Verlauf
    h = int(size * 0.04)
    for y in range(h):
        alpha = int(intensity * (1 - y / h))
        odraw.line([(0, y), (size, y)], fill=(255, 255, 255, alpha))
    img.paste(overlay, (0, 0), overlay)


def render_icon(size: int = 1024) -> Image.Image:
    """Erzeugt das Master-Icon."""
    radius = int(size * 0.224)  # macOS Standard

    # Lila-Gradient-Hintergrund + Squircle-Maske
    grad = make_gradient(size, BG_TOP, BG_BOTTOM).convert("RGBA")
    mask = squircle_mask(size, radius)
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg.paste(grad, (0, 0), mask)

    add_top_highlight(bg, intensity=50)

    # Broom-Icon Schichten
    icon_size = int(size * 0.58)
    font = ImageFont.truetype(str(FONT), icon_size)

    bbox = font.getbbox(BROOM_AFTER)
    glyph_w = bbox[2] - bbox[0]
    glyph_h = bbox[3] - bbox[1]
    x = (size - glyph_w) / 2 - bbox[0]
    y = (size - glyph_h) / 2 - bbox[1]

    # Drop Shadow (weicher Schatten unter dem Icon)
    shadow_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_layer)
    sd.text((x, y + 12), BROOM_AFTER, font=font, fill=(0, 0, 0, 80))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=12))
    bg.alpha_composite(shadow_layer)

    # Background-Schicht (helles Lila-Tint, leicht versetzt für Tiefe)
    layer1 = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(layer1).text(
        (x, y), BROOM_BEFORE, font=font, fill=ICON_TINT + (200,),
    )
    bg.alpha_composite(layer1)

    # Vordergrund-Schicht (weiß)
    layer2 = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(layer2).text(
        (x, y), BROOM_AFTER, font=font, fill=ICON_WHITE + (255,),
    )
    bg.alpha_composite(layer2)

    return bg


def make_iconset(master: Image.Image):
    if ICONSET_TMP.exists():
        shutil.rmtree(ICONSET_TMP)
    ICONSET_TMP.mkdir(parents=True)
    sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]
    for sz, name in sizes:
        master.resize((sz, sz), Image.LANCZOS).save(ICONSET_TMP / name, "PNG")
    print(f"  iconset: {len(sizes)} Größen")


def make_icns():
    subprocess.run(
        ["iconutil", "-c", "icns", str(ICONSET_TMP), "-o", str(ICNS_OUT)],
        check=True,
    )
    shutil.rmtree(ICONSET_TMP)
    print(f"  ✓ {ICNS_OUT}")


def main():
    if not FONT.exists():
        print(f"FEHLER: {FONT} fehlt.", file=sys.stderr)
        sys.exit(1)
    print("→ Rendering Master 1024×1024 …")
    master = render_icon(1024)
    master.save(MASTER_OUT)
    print(f"  Master: {MASTER_OUT}")
    print("→ Erzeuge .iconset …")
    make_iconset(master)
    print("→ Konvertiere zu .icns …")
    make_icns()
    print("\nFertig.")


if __name__ == "__main__":
    main()
