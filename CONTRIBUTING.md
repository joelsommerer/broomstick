# Contributing to Broomstick

Thanks for considering a contribution!

## Quick start

```bash
git clone https://github.com/joelsommerer/broomstick.git
cd broomstick
python3.13 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python app.py            # run from source
./scripts/build_app.sh             # build .app bundle
```

## Project layout

```
broomstick/
├── app.py              # UI / pages / Sidebar / main entry
├── data.py             # Pure-data layer: scanners, helpers
├── icons.py            # Phosphor Duotone icon system
├── assets/             # Fonts and icon
├── scripts/            # build_app.sh, build_dmg.sh, make_icon.py
├── setup.py            # py2app config
├── pyproject.toml      # project metadata
└── README.md
```

The data layer (`data.py`) is **pure Python with no UI**. Run any function
from a REPL or test without spinning up Tk.

## Coding style

- Plain Python 3.10+ — no abstract base classes, no over-engineering
- Type hints on public functions, lowercase + underscore for names
- ~80–100 col soft limit
- Comments only when *why* is non-obvious; the code itself documents *what*

## Adding a new cleanup category

1. Add an entry to `CLEANUP_CATEGORIES` in `data.py` with key/icon/name/desc
2. Either provide `subcategories` (list of paths) or a `scan` function
3. Add the matching scan function in `data.py`
4. (Optional) add a Phosphor icon key in `icons.py` if a new one is needed

## Adding a new page

1. Create a `class FooPage(ctk.CTkFrame)` in `app.py`
2. Add it to the `App.pages` dict
3. Add a `SidebarItem` in either the main-nav or tools section in `App.__init__`
4. Add the icon key to `icons.py` `ICONS` dict

## Testing

Currently no automated tests — for now, smoke-test by running `python app.py`
and clicking through every page. Verify that:

- Sidebar values populate
- Each page scans without error
- Right-click "Im Finder zeigen" works on at least one file in the cleanup view
- "Move to Trash" actually moves to Trash (check `~/.Trash`)

## Building & releasing

Local build:
```bash
./scripts/build_app.sh
./scripts/build_dmg.sh
```

For a release:
1. Bump version in `pyproject.toml`, `setup.py`, and `data.py` (if referenced)
2. `git tag -a v0.x.y -m "v0.x.y"`
3. `git push --tags`
4. The GitHub Actions workflow (TODO) will produce a release with the DMG attached

## Reporting bugs

Please include:
- macOS version (`sw_vers`)
- Python version (`python3 --version`)
- Steps to reproduce
- Output / traceback if any

Open an issue at https://github.com/joelsommerer/broomstick/issues

## Code of Conduct

Be excellent to each other. Don't be a jerk in PRs, issues, or anywhere
else this project lives.
