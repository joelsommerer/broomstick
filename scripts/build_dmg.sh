#!/bin/bash
# Baut ein .dmg-Disk-Image für die Distribution.
# Voraussetzung: dist/Broomstick.app existiert (vorher build_app.sh laufen).

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP="dist/Broomstick.app"
VERSION=$(plutil -extract CFBundleShortVersionString raw -o - "$APP/Contents/Info.plist" 2>/dev/null || echo "0.0.0")
DMG="dist/Broomstick-${VERSION}.dmg"
STAGE="dist/dmg-stage"

if [[ ! -d "$APP" ]]; then
    echo "FEHLER: $APP nicht gefunden. Erst ./scripts/build_app.sh ausführen."
    exit 1
fi

# Staging-Ordner mit App und /Applications-Symlink (Drag-Target)
rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

# DMG bauen
hdiutil create \
    -volname "Broomstick" \
    -srcfolder "$STAGE" \
    -ov -format UDZO \
    "$DMG"

rm -rf "$STAGE"

echo ""
echo "✓ Fertig: $DMG"
echo "  Größe: $(du -sh "$DMG" | cut -f1)"
