"""Phosphor-Duotone-Icons für Broomstick.

Lädt die `Phosphor-Duotone.ttf` aus `./assets/` zur Laufzeit über
CoreText (kein systemweites Font-Install nötig). Bietet eine `Icon`-Klasse,
die zwei Glyphen übereinander rendert (helle Hintergrund-Schicht +
dunkle Vordergrund-Schicht) — das ergibt den echten Duotone-Effekt.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import sys
from ctypes import byref, c_int, c_long, c_void_p
from pathlib import Path

import customtkinter as ctk


def _resolve_assets_dir() -> Path:
    """Findet assets/ sowohl im Source-Lauf als auch im py2app-Bundle."""
    if getattr(sys, "frozen", False):
        # py2app: Resources/assets liegt zwei Ebenen über sys.executable
        # sys.executable = …/Broomstick.app/Contents/MacOS/Broomstick
        return Path(sys.executable).parent.parent / "Resources" / "assets"
    return Path(__file__).parent / "assets"


ASSETS_DIR = _resolve_assets_dir()
DUOTONE_TTF = ASSETS_DIR / "Phosphor-Duotone.ttf"
FILL_TTF = ASSETS_DIR / "Phosphor-Fill.ttf"

FAMILY_DUOTONE = "Phosphor-Duotone"
FAMILY_FILL = "Phosphor-Fill"


# ─────────────────────────────────────────────────────────────────────
#  Font-Registrierung (macOS / CoreText, kein Reboot nötig)
# ─────────────────────────────────────────────────────────────────────

_REGISTERED = False


def _register_font(ttf_path: Path) -> bool:
    if not ttf_path.exists():
        return False
    try:
        cf_lib = ctypes.util.find_library("CoreFoundation")
        ct_lib = ctypes.util.find_library("CoreText")
        if not cf_lib or not ct_lib:
            return False
        cf = ctypes.CDLL(cf_lib)
        ct = ctypes.CDLL(ct_lib)

        cf.CFURLCreateFromFileSystemRepresentation.restype = c_void_p
        cf.CFURLCreateFromFileSystemRepresentation.argtypes = [
            c_void_p, ctypes.c_char_p, c_long, c_int,
        ]
        ct.CTFontManagerRegisterFontsForURL.restype = c_int
        ct.CTFontManagerRegisterFontsForURL.argtypes = [
            c_void_p, c_int, c_void_p,
        ]

        path_b = str(ttf_path).encode("utf-8")
        url = cf.CFURLCreateFromFileSystemRepresentation(
            None, path_b, len(path_b), 0,
        )
        if not url:
            return False
        err = c_void_p()
        # kCTFontManagerScopeProcess = 1
        return bool(ct.CTFontManagerRegisterFontsForURL(url, 1, byref(err)))
    except Exception:
        return False


def register_fonts() -> bool:
    """Registriert die Phosphor-TTFs im aktuellen Prozess. Idempotent."""
    global _REGISTERED
    if _REGISTERED:
        return True
    ok1 = _register_font(DUOTONE_TTF)
    ok2 = _register_font(FILL_TTF)
    _REGISTERED = ok1 or ok2
    return _REGISTERED


# ─────────────────────────────────────────────────────────────────────
#  Icon-Codepoints (before = helle Schicht, after = volle Schicht)
# ─────────────────────────────────────────────────────────────────────

ICONS: dict[str, dict[str, str]] = {
    # Sidebar / Hauptnavigation
    "overview":      {"before": "", "after": ""},  # gauge
    "cleanup":       {"before": "", "after": ""},  # broom
    "speedup":       {"before": "", "after": ""},  # rocket
    "manage":        {"before": "", "after": ""},  # folder-open
    "duplicates":    {"before": "", "after": ""},  # copy
    "applications":  {"before": "", "after": ""},  # app-store-logo
    "biggest":       {"before": "", "after": ""},  # chart-bar
    "utilities":     {"before": "", "after": ""},  # toolbox

    # Cleanup-Kategorien
    "caches":        {"before": "", "after": ""},  # cpu
    "downloads":     {"before": "", "after": ""},  # download
    "installers":    {"before": "", "after": ""},  # package
    "screenshots":   {"before": "", "after": ""},  # image
    "languages":     {"before": "", "after": ""},  # flag
    "trash":         {"before": "", "after": ""},  # trash
    "mail":          {"before": "", "after": ""},  # envelope
    "saved_state":   {"before": "", "after": ""},  # floppy-disk

    # SpeedUp-Kategorien
    "startup":       {"before": "", "after": ""},  # rocket
    "heavy":         {"before": "", "after": ""},  # fire
    "ram":           {"before": "", "after": ""},  # memory
    "extensions":    {"before": "", "after": ""},  # puzzle-piece

    # Manage-Files-Kategorien
    "documents":     {"before": "", "after": ""},  # file-text
    "movies":        {"before": "", "after": ""},  # film-strip
    "music":         {"before": "", "after": ""},  # music-notes
    "pictures":      {"before": "", "after": ""},  # image-square
    "desktop":       {"before": "", "after": ""},  # desktop
    "archives":      {"before": "", "after": ""},  # file-zip

    # Utilities
    "activity":      {"before": "", "after": ""},  # chart-line
    "disk":          {"before": "", "after": ""},  # hard-drives
    "hard_drive":    {"before": "", "after": ""},  # hard-drive
    "console":       {"before": "", "after": ""},  # terminal
    "spotlight":     {"before": "", "after": ""},  # magnifying-glass
    "globe":         {"before": "", "after": ""},  # globe
    "folder":        {"before": "", "after": ""},  # folder
    "settings":      {"before": "", "after": ""},  # gear

    # Allgemein
    "search":        {"before": "", "after": ""},  # magnifying-glass
    "logo":          {"before": "", "after": ""},  # broom
    "computer":      {"before": "", "after": ""},  # monitor
    "refresh":       {"before": "", "after": ""},  # arrows-clockwise
    "info":          {"before": "", "after": ""},  # info
    "warning":       {"before": "", "after": ""},  # warning
    "check":         {"before": "", "after": ""},  # check
    "xmark":         {"before": "", "after": ""},  # x
    "chevron_right": {"before": "", "after": ""},  # caret-right
    "lightning":     {"before": "", "after": ""},  # lightning
    "shield":        {"before": "", "after": ""},  # shield-check
}


# ─────────────────────────────────────────────────────────────────────
#  Farb-Helfer (Mix für Hintergrund-Schicht)
# ─────────────────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def blend(color: str, target: str, factor: float) -> str:
    """Mischt color in Richtung target. factor=0 → color, factor=1 → target."""
    cr, cg, cb = _hex_to_rgb(color)
    tr, tg, tb = _hex_to_rgb(target)
    r = int(cr + (tr - cr) * factor)
    g = int(cg + (tg - cg) * factor)
    b = int(cb + (tb - cb) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


# ─────────────────────────────────────────────────────────────────────
#  Icon-Widget (Duotone)
# ─────────────────────────────────────────────────────────────────────

class Icon(ctk.CTkFrame):
    """Stapelt zwei Glyphen für den Duotone-Effekt.

    Args:
        master: Parent-Widget
        name: Key aus ICONS (z.B. "speedup")
        size: Schriftgröße (px)
        color: Hauptfarbe (Vordergrund-Schicht)
        bg_color: Frame-Hintergrund (für korrekte Mix-Berechnung der hellen Schicht)
        muted_factor: 0..1 — wie stark die Hintergrund-Schicht zur bg_color tendiert (0.55 = Default)
    """

    def __init__(
        self,
        master,
        name: str,
        size: int = 24,
        color: str = "#7c5cff",
        bg_color: str = "#0e1024",
        muted_factor: float = 0.55,
        **kwargs,
    ):
        # Frame transparent — keine sichtbare Hintergrundfläche
        super().__init__(master, fg_color="transparent", **kwargs)

        cp = ICONS.get(name, {"before": "", "after": ""})  # warning fallback
        family = FAMILY_DUOTONE
        font = (family, size)

        muted = blend(color, bg_color, muted_factor)

        # Hintergrund-Schicht (abgedunkelt/heller)
        self.bg_lbl = ctk.CTkLabel(
            self, text=cp["before"], font=font,
            text_color=muted, fg_color="transparent",
        )
        self.bg_lbl.place(relx=0.5, rely=0.5, anchor="center")

        # Vordergrund-Schicht (volle Farbe)
        self.fg_lbl = ctk.CTkLabel(
            self, text=cp["after"], font=font,
            text_color=color, fg_color="transparent",
        )
        self.fg_lbl.place(relx=0.5, rely=0.5, anchor="center")

        # Frame-Größe an Icon-Größe koppeln
        box = int(size * 1.25)
        self.configure(width=box, height=box)
        self.grid_propagate(False)
        self.pack_propagate(False)

    def set_color(self, color: str, bg_color: str = "#0e1024",
                   muted_factor: float = 0.55):
        muted = blend(color, bg_color, muted_factor)
        self.bg_lbl.configure(text_color=muted)
        self.fg_lbl.configure(text_color=color)


# Vereinfachter Konstruktor — lazy registriert die Schrift wenn Icon erstellt wird
_AUTO_REGISTERED = False


def _ensure_registered():
    global _AUTO_REGISTERED
    if not _AUTO_REGISTERED:
        register_fonts()
        _AUTO_REGISTERED = True


def make_icon(parent, name, size=24, color="#7c5cff", bg_color="#0e1024", **kw):
    """Convenience-Wrapper: stellt Font-Registrierung sicher und erzeugt Icon."""
    _ensure_registered()
    return Icon(parent, name, size=size, color=color, bg_color=bg_color, **kw)


# ─────────────────────────────────────────────────────────────────────
#  Klickbarer Icon-Button (z.B. für Refresh)
# ─────────────────────────────────────────────────────────────────────

class IconButton(ctk.CTkFrame):
    """Quadratischer Button, der nur ein Icon zeigt. Hovert mit Hintergrund.

    Args:
        master: Parent
        name: Icon-Key
        command: Callback bei Klick
        size: Frame-Größe in px (Icon ist size*0.55)
        color: Icon-Farbe
        bg_color: Hintergrund der Umgebung (für Duotone-Mix)
        hover_color: Farbe beim Hover
    """

    def __init__(
        self,
        master,
        name: str,
        command,
        size: int = 36,
        color: str = "#9ca3c4",
        bg_color: str = "#0e1024",
        hover_color: str = "#232651",
        **kwargs,
    ):
        super().__init__(
            master, fg_color="transparent",
            corner_radius=8, width=size, height=size,
            cursor="pointinghand", **kwargs,
        )
        self.pack_propagate(False)
        self.grid_propagate(False)
        self._command = command
        self._bg_color = bg_color
        self._hover_color = hover_color
        self._icon_color = color

        icon_size = int(size * 0.55)
        self.icon = make_icon(self, name, size=icon_size,
                                color=color, bg_color=bg_color)
        self.icon.place(relx=0.5, rely=0.5, anchor="center")

        for w in (self, self.icon, self.icon.bg_lbl, self.icon.fg_lbl):
            w.bind("<Button-1>", lambda e: self._command())
            w.bind("<Enter>", self._hover_in)
            w.bind("<Leave>", self._hover_out)

    def _hover_in(self, _):
        self.configure(fg_color=self._hover_color)
        self.icon.set_color(self._icon_color, self._hover_color)

    def _hover_out(self, _):
        self.configure(fg_color="transparent")
        self.icon.set_color(self._icon_color, self._bg_color)
