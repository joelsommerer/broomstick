# Broomstick for Mac

> A clean, fast macOS cleanup utility — uninstall apps with all their leftovers, clear caches, find duplicates, manage big files.

![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)
![macOS](https://img.shields.io/badge/macOS-11%2B-000000?logo=apple)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)

Broomstick is an open-source alternative to commercial Mac cleaners like CleanMyMac and MacCleaner Pro. No subscriptions, no telemetry, no nag screens — just a clean tool that does the job and respects your machine.

## Features

- **Overview** — disk usage breakdown by category, junk-files total, memory usage at a glance
- **Clean Up** — caches, downloads, installer files, screenshots, mail attachments, trash, saved app states
- **Speed Up** — startup items, heavy running apps, RAM stats, browser extensions
- **Manage Files** — browse Documents/Movies/Music/Pictures/Archives, sortable by size
- **Duplicates** — find identical files via hash comparison
- **Applications** — uninstall apps and find their leftovers in `~/Library` (containers, caches, preferences, etc.)
- **Biggest Files** — find files >50 MB anywhere in your home folder
- **Utilities** — quick access to Activity Monitor, Disk Utility, DNS flush, Spotlight reindex, etc.

### Safety first

- Everything goes to the **Trash** via Finder — nothing is deleted with `rm -rf`
- Confirmation dialog before every action
- Sandboxed paths (Mail, Calendars, Keychains, iCloud, Safari bookmarks) are explicitly blocklisted
- Strict matching rules when scanning for app leftovers — no greedy substring matches
- macOS sandbox-protected paths that fail to delete are revealed in Finder so you can remove them manually with admin password

## Screenshots

> _Coming soon — drop yours into `docs/screenshots/` and reference here._

## Install

### Pre-built `.app` (recommended)

1. Download the latest `Broomstick-x.y.z.dmg` from the [Releases page](https://github.com/joelsommerer/broomstick/releases)
2. Open the DMG, drag **Broomstick** to your **Applications** folder
3. Launch from Spotlight or Launchpad

The first time you launch, macOS will warn that the app is from an unidentified developer (Broomstick is not yet notarized — that requires a paid Apple Developer account). Workaround:

- **Right-click the app → Open**, then click _Open_ in the dialog (only needed once)
- Or: System Settings → Privacy & Security → scroll down, "Allow Anyway"

### Build from source

Requires Python 3.10+ and Homebrew (for Tk):

```bash
brew install python-tk@3.13
git clone https://github.com/joelsommerer/broomstick.git
cd broomstick
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

### Build a `.app` bundle yourself

```bash
./scripts/build_app.sh           # → dist/Broomstick.app
./scripts/build_dmg.sh           # → dist/Broomstick-0.1.0.dmg (optional)
```

## How does it know which leftovers belong to an app?

When uninstalling an app, Broomstick reads the app's `Info.plist` and gets the **bundle identifier** (e.g. `com.apple.Safari`). It then searches 18 standard `~/Library` and `/Library` locations for files and folders whose name **exactly equals or starts with** the bundle ID, or whose basename **exactly matches** the app name.

This avoids common false positives in tools that do greedy substring matching — Broomstick won't suggest deleting your `Music/` folder when uninstalling an app called "Music Editor".

## Why "Broomstick"?

The Phosphor Icons broom matched the cleanup theme. The name sticks.

## Architecture

- `app.py` — Tkinter / CustomTkinter UI with Sidebar layout, 8 pages
- `data.py` — All scanning logic (apps, leftovers, disk usage, duplicates, files, processes, login items, browser extensions, RAM)
- `icons.py` — Phosphor Duotone icon system with in-process CoreText font loading and a stacked-glyph duotone widget
- `setup.py` — py2app build configuration
- `scripts/` — build helpers and icon generator

The data layer is pure Python with no UI dependencies — easy to script without the GUI.

## Permissions

Broomstick requires no special permissions on first run. macOS will prompt you to grant **Apple Events / Finder control** the first time you move something to the Trash (this is how Broomstick uses the Trash instead of `rm`). Grant it.

For deleting items inside `~/Library/Containers/<bundle-id>/`, macOS sandbox protection requires either:
- The app having **Full Disk Access** (System Settings → Privacy & Security → Full Disk Access → add Broomstick), **or**
- Manually deleting via Finder, which prompts for your login password

When sandbox-protected paths can't be deleted, Broomstick shows a dialog with a "Reveal in Finder" button so you can finish manually.

## Roadmap

- [ ] App icon (a real `.icns`, not the generated one)
- [ ] Code signing & notarization (requires Apple Developer account)
- [ ] Homebrew Cask submission
- [ ] Light theme toggle
- [ ] Localization (currently German + English mixed)
- [ ] Schedule periodic cleanups
- [ ] Memory cleaner (`purge` button with sudo prompt)
- [ ] Browser extensions: enable/disable directly
- [ ] Login items: toggle on/off (requires `sfltool` or AppleScript)

## Contributing

PRs welcome! See `CONTRIBUTING.md` (TODO).

For bug reports, please include:
- macOS version (`sw_vers`)
- Python version (`python3 --version`)
- Steps to reproduce
- Output / error message

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Trademarks

"Mac" and "macOS" are trademarks of Apple Inc., used here solely descriptively to indicate the platform Broomstick runs on. Broomstick is not affiliated with or endorsed by Apple.

## Credits

- Icon set: [Phosphor Icons](https://phosphoricons.com/) (MIT)
- UI framework: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (MIT)
