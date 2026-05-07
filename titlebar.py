"""macOS-Titelleiste in das App-Window integrieren.

Macht die Titelleiste transparent und farblich passend zum Hintergrund.
Die Schließen/Minimieren/Maximieren-Buttons bleiben sichtbar.

Nutzt pyobjc nur ohne `NSApp.windows()` (das hat GIL-Konflikte mit Tk).
Stattdessen: NSApp.mainWindow() für ein einzelnes Window.
"""

from __future__ import annotations

import logging
import tkinter as tk


def integrate(root: tk.Tk, bg_hex: str = "#0e1024") -> bool:
    """Setzt Titelleiste auf transparent + Window-Background auf bg_hex.

    Returns True bei Erfolg.
    """
    # Window erst real machen, sonst gibt's noch keine NSWindow
    root.update_idletasks()
    root.update()

    try:
        from AppKit import (
            NSApp,
            NSApplication,
            NSColor,
        )
    except ImportError:
        logging.warning("pyobjc-framework-Cocoa nicht verfügbar.")
        return False

    try:
        NSApplication.sharedApplication()
        win = NSApp.mainWindow()
        if win is None:
            win = NSApp.keyWindow()
        if win is None:
            logging.warning("Kein NSWindow gefunden.")
            return False

        # Background auf App-Hintergrund setzen
        r = int(bg_hex[1:3], 16) / 255.0
        g = int(bg_hex[3:5], 16) / 255.0
        b = int(bg_hex[5:7], 16) / 255.0
        color = NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, 1.0)
        win.setBackgroundColor_(color)

        # Titelleiste transparent + Titel-Text ausblenden
        win.setTitlebarAppearsTransparent_(True)
        win.setTitleVisibility_(1)  # NSWindowTitleHidden

        # Drag des Fensters von überall im Hintergrund
        win.setMovableByWindowBackground_(True)

        logging.info("Titelleiste integriert (bg=%s).", bg_hex)
        return True
    except Exception as e:
        logging.warning("Titelleisten-Integration fehlgeschlagen: %s", e)
        return False
