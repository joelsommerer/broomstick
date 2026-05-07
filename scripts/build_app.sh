#!/bin/bash
# Baut das standalone .app-Bundle mit py2app.
# Resultat: dist/Broomstick.app (etwa 30–50 MB, enthält Python + alle Deps)

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Venv-Python finden
if [[ ! -d .venv ]]; then
    echo "→ Erstelle Virtual Environment …"
    /opt/homebrew/bin/python3.13 -m venv .venv 2>/dev/null \
        || /usr/bin/python3 -m venv .venv
fi
PY=".venv/bin/python"

# Dev-Deps installieren
echo "→ Installiere Build-Abhängigkeiten …"
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r requirements-dev.txt

# Icon erzeugen falls noch nicht da
if [[ ! -f assets/icon.icns ]]; then
    echo "→ Erzeuge App-Icon …"
    "$PY" scripts/make_icon.py
fi

# Alte Build-Artefakte aufräumen
echo "→ Räume vorherige Builds auf …"
rm -rf build dist

# py2app läuft am stabilsten mit "alias"-Builds zum Testen,
# "--no-strip" für saubere Releases:
echo "→ Baue Broomstick.app …"
"$PY" setup.py py2app

# Ad-hoc-Signatur (sonst Gatekeeper-Warnung „beschädigt“ auf manchen Macs)
echo "→ Signiere Bundle (ad-hoc) …"
codesign --force --deep --sign - dist/Broomstick.app

# Quarantäne-Flag entfernen (lokal getesteter Build)
xattr -dr com.apple.quarantine dist/Broomstick.app 2>/dev/null || true

echo ""
echo "✓ Fertig: $ROOT/dist/Broomstick.app"
echo "  Größe: $(du -sh dist/Broomstick.app | cut -f1)"
echo ""
echo "Test:  open dist/Broomstick.app"
echo "DMG bauen: ./scripts/build_dmg.sh"
