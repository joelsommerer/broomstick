"""Logging-Setup für Broomstick.

Schreibt nach ~/Library/Logs/Broomstick/broomstick.log mit Rotation.
Fängt unhandled Exceptions in Main- und Worker-Threads ab, damit ein
Crash zumindest dokumentiert ist.

Lookup für den Nutzer:
    /usr/bin/open ~/Library/Logs/Broomstick/broomstick.log
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import threading
import traceback
from pathlib import Path


LOG_DIR = Path.home() / "Library" / "Logs" / "Broomstick"
LOG_FILE = LOG_DIR / "broomstick.log"

_INSTALLED = False


def setup_logging(level: int = logging.INFO) -> Path:
    """Initialisiert Datei-Logging und Exception-Hooks. Idempotent.

    Returns: Pfad zur aktuellen Logdatei.
    """
    global _INSTALLED
    if _INSTALLED:
        return LOG_FILE

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotation: max 1 MB pro Datei, 3 Backups
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Stderr für Dev-Läufe
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(logging.WARNING)

    root = logging.getLogger()
    root.setLevel(level)
    # Doppel-Handler vermeiden bei wiederholtem Aufruf
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(file_handler)
    root.addHandler(stderr_handler)

    # Unhandled Exceptions im Main-Thread
    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.error("Uncaught exception",
                       exc_info=(exc_type, exc_value, exc_tb))
    sys.excepthook = _excepthook

    # Thread-Exceptions (Python 3.8+)
    def _thread_excepthook(args):
        logging.error("Thread-Exception in %r",
                       args.thread.name if args.thread else "?",
                       exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
    threading.excepthook = _thread_excepthook

    _INSTALLED = True

    logging.info("=" * 70)
    logging.info("Broomstick gestartet")
    logging.info("Python %s | frozen=%s | platform=%s",
                  sys.version.split()[0],
                  getattr(sys, "frozen", False),
                  sys.platform)
    logging.info("Log-Datei: %s", LOG_FILE)

    return LOG_FILE


def log_path() -> Path:
    """Pfad zur aktuellen Logdatei."""
    return LOG_FILE
