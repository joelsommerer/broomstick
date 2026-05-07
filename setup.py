"""py2app setup for Broomstick.

Build a standalone .app bundle that other macOS users can install
without needing Python or any dependencies on their system.

Usage:
    pip install -r requirements-dev.txt
    python setup.py py2app
    # → creates dist/Broomstick.app
"""

from setuptools import setup
from pathlib import Path

ROOT = Path(__file__).parent

APP = ["app.py"]
DATA_FILES = [
    ("assets", [
        str(ROOT / "assets" / "Phosphor-Duotone.ttf"),
        str(ROOT / "assets" / "Phosphor-Fill.ttf"),
    ]),
]

ICON_FILE = ROOT / "assets" / "icon.icns"

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Broomstick",
        "CFBundleDisplayName": "Broomstick for Mac",
        "CFBundleIdentifier": "com.broomstick.app",
        "CFBundleVersion": "0.1.3",
        "CFBundleShortVersionString": "0.1.3",
        "CFBundleExecutable": "Broomstick",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
        "LSApplicationCategoryType": "public.app-category.utilities",
        "NSHumanReadableCopyright": "© 2026 Joel Sommerer. Apache License 2.0.",
        "NSAppleEventsUsageDescription":
            "Broomstick needs to control Finder to move items to the Trash.",
    },
    "packages": ["customtkinter"],
    "includes": ["tkinter", "data", "icons"],
    "excludes": ["matplotlib", "numpy", "scipy", "pandas", "PyQt5", "PyQt6", "PySide6"],
    "optimize": 2,
}

if ICON_FILE.exists():
    OPTIONS["iconfile"] = str(ICON_FILE)

setup(
    name="Broomstick",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
