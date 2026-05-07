#!/usr/bin/env python3
"""Generiert assets/icon.icns aus dem Phosphor-Broom-Icon.

Schritte:
1. Rendert das Broom-Icon mit PIL bei 1024×1024 in zwei Schichten (Duotone-Look)
2. Skaliert via macOS `sips` runter auf alle iconset-Größen
3. Konvertiert mit `iconutil` zum .icns

Voraussetzungen: Pillow, das Phosphor-Duotone-TTF in assets/.
Lauf: `python scripts/make_icon.py`
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).parent.parent
ASSETS = ROOT / "assets"
FONT = ASSETS / "Phosphor-Duotone.ttf"
ICONSET_TMP = ASSETS / "icon.iconset"
ICNS_OUT = ASSETS / "icon.icns"

# Codepoints: Phosphor "broom"
BROOM_BEFORE = ""  # 
BROOM_AFTER = ""   # 

BG_COLOR = "#7c5cff"      # Lila (Frame-Hintergrund)
BG_GRADIENT = "#5a3eff"   # Lila etwas dunkler unten
ICON_FG = "#ffffff"        # Weiß für Vordergrund-Schicht
ICON_BG = "#bfb0ff"        # Helleres Lila für Hintergrund-Schicht


def render_master(size: int = 1024) -> Image.Image:
    """Erzeugt das Hochauflösungs-Master-Bild."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Abgerundeter Hintergrund (macOS-Squircle-ish)
    radius = int(size * 0.224)  # macOS Big-Sur+ Standard
    draw.rounded_rectangle(
        (0, 0, size, size),
        radius=radius,
        fill=BG_COLOR,
    )

    # Sanfter Vertikal-Verlauf (oben heller)
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for y in range(size):
        # Linear: oben 0%, unten 25% mehr Schwarz
        alpha = int(y / size * 60)
        odraw.line([(0, y), (size, y)], fill=(0, 0, 0, alpha))
    # Auf den abgerundeten Bereich maskieren
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
    img.paste(overlay, (0, 0), mask)

    # Icon-Schichten
    icon_size = int(size * 0.62)
    font = ImageFont.truetype(str(FONT), icon_size)

    # Vordergrund-Schicht zuerst messen (für Zentrierung)
    bbox = font.getbbox(BROOM_AFTER)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (size - w) / 2 - bbox[0]
    y = (size - h) / 2 - bbox[1]

    # Hintergrund-Schicht (helleres Lila, leicht versetzt für mehr Tiefe)
    draw.text((x, y), BROOM_BEFORE, font=font, fill=ICON_BG)
    # Vordergrund-Schicht
    draw.text((x, y), BROOM_AFTER, font=font, fill=ICON_FG)

    return img


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
        resized = master.resize((sz, sz), Image.LANCZOS)
        resized.save(ICONSET_TMP / name, "PNG")
    print(f"  iconset: {len(sizes)} Größen geschrieben → {ICONSET_TMP}")


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
    print(f"→ Rendering Master 1024×1024 …")
    master = render_master(1024)
    master.save(ASSETS / "icon-master.png")
    print(f"  Master: assets/icon-master.png")

    print(f"→ Erzeuge .iconset …")
    make_iconset(master)

    print(f"→ Konvertiere zu .icns …")
    make_icns()

    print(f"\nFertig.")


if __name__ == "__main__":
    main()
