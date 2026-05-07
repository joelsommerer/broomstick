#!/bin/bash
# Baut ein gestyltes .dmg mit create-dmg.
# Voraussetzung: dist/Broomstick.app existiert (vorher build_app.sh laufen).

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Homebrew-Pfad ergänzen, damit create-dmg gefunden wird
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

APP="dist/Broomstick.app"
VERSION=$(plutil -extract CFBundleShortVersionString raw -o - "$APP/Contents/Info.plist" 2>/dev/null || echo "0.0.0")
DMG="dist/Broomstick-${VERSION}.dmg"
BG="assets/dmg-background.png"
ICON="assets/icon.icns"

if [[ ! -d "$APP" ]]; then
    echo "FEHLER: $APP nicht gefunden. Erst ./scripts/build_app.sh laufen lassen."
    exit 1
fi

# DMG-Background bei Bedarf erzeugen
if [[ ! -f "$BG" ]]; then
    echo "→ Erzeuge DMG-Background …"
    "$ROOT/.venv/bin/python" "$ROOT/scripts/make_dmg_background.py"
fi

# Alte DMG entfernen
rm -f "$DMG"

# create-dmg installiert?
if ! command -v create-dmg &>/dev/null; then
    echo "WARNUNG: create-dmg nicht installiert. Falle zurück auf einfaches hdiutil."
    STAGE="dist/dmg-stage"
    rm -rf "$STAGE"
    mkdir -p "$STAGE"
    cp -R "$APP" "$STAGE/"
    ln -s /Applications "$STAGE/Applications"
    hdiutil create -volname "Broomstick" -srcfolder "$STAGE" \
        -ov -format UDZO "$DMG"
    rm -rf "$STAGE"
else
    echo "→ Baue gestyltes DMG mit create-dmg …"
    create-dmg \
        --volname "Broomstick ${VERSION}" \
        --volicon "$ICON" \
        --background "$BG" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "Broomstick.app" 175 190 \
        --hide-extension "Broomstick.app" \
        --app-drop-link 425 190 \
        --no-internet-enable \
        "$DMG" \
        "$APP" || {
            echo "create-dmg fehlgeschlagen, versuche einfachen Fallback …"
            STAGE="dist/dmg-stage"
            rm -rf "$STAGE"
            mkdir -p "$STAGE"
            cp -R "$APP" "$STAGE/"
            ln -s /Applications "$STAGE/Applications"
            hdiutil create -volname "Broomstick" -srcfolder "$STAGE" \
                -ov -format UDZO "$DMG"
            rm -rf "$STAGE"
        }
fi

echo ""
echo "✓ Fertig: $DMG"
echo "  Größe: $(du -sh "$DMG" | cut -f1)"
