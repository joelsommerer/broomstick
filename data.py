"""Datenfunktionen für MacCleaner — Scans, Listen, Helpers.

Hier liegt die ganze Logik, die das Dateisystem / System abfragt.
Die UI in app.py importiert von hier.
"""

from __future__ import annotations

import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path


HOME = Path.home()

APP_DIRS = [Path("/Applications"), HOME / "Applications"]

LIBRARY_SEARCH_DIRS = [
    HOME / "Library/Application Support",
    HOME / "Library/Caches",
    HOME / "Library/Preferences",
    HOME / "Library/Logs",
    HOME / "Library/Containers",
    HOME / "Library/Group Containers",
    HOME / "Library/Saved Application State",
    HOME / "Library/HTTPStorages",
    HOME / "Library/WebKit",
    HOME / "Library/Cookies",
    HOME / "Library/LaunchAgents",
    HOME / "Library/Application Scripts",
    Path("/Library/Application Support"),
    Path("/Library/Caches"),
    Path("/Library/Preferences"),
    Path("/Library/LaunchAgents"),
    Path("/Library/LaunchDaemons"),
    Path("/Library/PrivilegedHelperTools"),
]

PROTECTED_PATHS = [
    HOME / "Library/Mail",
    HOME / "Library/Calendars",
    HOME / "Library/Messages",
    HOME / "Library/Keychains",
    HOME / "Library/Mobile Documents",
    HOME / "Library/CloudStorage",
    HOME / "Library/IdentityServices",
    HOME / "Library/Reminders",
    HOME / "Library/Suggestions",
    HOME / "Library/PersonalizationPortrait",
    HOME / "Library/Safari",
]

ARCHIVE_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz", ".dmg", ".iso", ".pkg"}
INSTALLER_EXTS = {".dmg", ".pkg", ".mpkg"}
SCREENSHOT_PATTERNS = [
    "Bildschirmfoto*.png", "Bildschirmfoto*.jpg",
    "Screen Shot*.png", "Screenshot*.png", "Screen Recording*.mov",
    "Bildschirmaufnahme*.mov",
]


# ─────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────

def is_protected(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path
    for protected in PROTECTED_PATHS:
        try:
            resolved.relative_to(protected)
            return True
        except ValueError:
            continue
    return False


def human_size(num_bytes: int | float) -> str:
    if num_bytes is None or num_bytes < 0:
        return "—"
    n = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def get_size_bytes(path: Path) -> int:
    """Größe in Bytes via `du -sk` (auch für Verzeichnisse)."""
    if not path.exists():
        return 0
    try:
        if path.is_file():
            return path.stat().st_size
        r = subprocess.run(
            ["du", "-sk", str(path)],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0 and r.stdout:
            return int(r.stdout.split()[0]) * 1024
    except Exception:
        pass
    return 0


def disk_usage_root() -> tuple[int, int]:
    """(used_bytes, total_bytes) für /."""
    try:
        st = shutil.disk_usage("/")
        return st.total - st.free, st.total
    except Exception:
        return 0, 0


def disk_breakdown() -> dict:
    """Stack-Bar-Daten: bytes pro Kategorie + total."""
    used, total = disk_usage_root()
    cats = {
        "Applications": get_size_bytes(Path("/Applications")),
        "Documents": get_size_bytes(HOME / "Documents"),
        "Movies": get_size_bytes(HOME / "Movies"),
        "Music": get_size_bytes(HOME / "Music"),
        "Pictures": get_size_bytes(HOME / "Pictures"),
        "Downloads": get_size_bytes(HOME / "Downloads"),
    }
    categorized = sum(cats.values())
    cats["System"] = max(0, used - categorized)
    return {"categories": cats, "used": used, "total": total, "free": total - used}


def memory_info() -> dict:
    """RAM-Status: total, used%, free%, etc."""
    try:
        total = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
    except Exception:
        return {"total": 0, "used": 0, "used_pct": 0}

    try:
        out = subprocess.check_output(["vm_stat"], text=True)
        page_size = 16384  # macOS arm64 default; korrigiert per Header falls vorhanden
        m = re.search(r"page size of (\d+) bytes", out)
        if m:
            page_size = int(m.group(1))

        def get(label: str) -> int:
            mm = re.search(rf"{label}:\s+(\d+)", out)
            return int(mm.group(1)) if mm else 0

        free = get(r"Pages free") * page_size
        active = get(r"Pages active") * page_size
        wired = get(r"Pages wired down") * page_size
        compressed = get(r"Pages occupied by compressor") * page_size
        used = active + wired + compressed
        return {
            "total": total,
            "used": used,
            "free": free,
            "used_pct": round(used / total * 100) if total else 0,
        }
    except Exception:
        return {"total": total, "used": 0, "used_pct": 0}


def move_to_trash(paths: list[Path]) -> tuple[list[Path], list[tuple[Path, str]]]:
    succeeded: list[Path] = []
    failed: list[tuple[Path, str]] = []
    for p in paths:
        if not p.exists():
            succeeded.append(p)
            continue
        escaped = str(p).replace("\\", "\\\\").replace('"', '\\"')
        script = f'tell application "Finder" to delete (POSIX file "{escaped}" as alias)'
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if r.returncode == 0:
            succeeded.append(p)
        else:
            err = r.stderr.strip() or r.stdout.strip() or "unbekannter Fehler"
            failed.append((p, err))
    return succeeded, failed


def reveal_in_finder(paths: list[Path]) -> None:
    existing = [str(p) for p in paths if p.exists() or p.parent.exists()]
    if existing:
        subprocess.run(["open", "-R", *existing], check=False)


def open_path(path: Path) -> None:
    if path.exists():
        subprocess.run(["open", str(path)], check=False)
    elif path.parent.exists():
        subprocess.run(["open", "-R", str(path)], check=False)


# ─────────────────────────────────────────────────────────────────────
#  Apps & Reste
# ─────────────────────────────────────────────────────────────────────

def list_installed_apps() -> list[dict]:
    apps: list[dict] = []
    for base in APP_DIRS:
        if not base.exists():
            continue
        for entry in base.iterdir():
            if entry.suffix == ".app" and entry.is_dir():
                info = read_bundle_info(entry)
                apps.append({
                    "path": entry,
                    "name": info.get("name") or entry.stem,
                    "bundle_id": info.get("bundle_id") or "",
                })
    apps.sort(key=lambda a: a["name"].lower())
    return apps


def read_bundle_info(app_path: Path) -> dict:
    plist = app_path / "Contents" / "Info.plist"
    if not plist.exists():
        return {}
    try:
        r = subprocess.run(
            ["plutil", "-convert", "json", "-o", "-", str(plist)],
            capture_output=True, text=True, check=True, timeout=10,
        )
        data = json.loads(r.stdout)
        return {
            "bundle_id": data.get("CFBundleIdentifier", ""),
            "name": data.get("CFBundleName") or data.get("CFBundleDisplayName") or app_path.stem,
        }
    except Exception:
        return {}


def name_matches_app(entry_name: str, bundle_id: str, app_name: str) -> bool:
    n = entry_name.lower()
    n_base = os.path.splitext(n)[0]
    if bundle_id:
        bid = bundle_id.lower()
        if n == bid or n.startswith(bid + ".") or n_base == bid:
            return True
    if app_name:
        an = app_name.lower()
        for v in {an, an.replace(" ", ""), an.replace(" ", "-"), an.replace(" ", "_")}:
            if v and n_base == v:
                return True
    return False


def find_leftovers(bundle_id: str, app_name: str) -> list[Path]:
    found: list[Path] = []
    for base in LIBRARY_SEARCH_DIRS:
        if not base.exists():
            continue
        try:
            entries = list(base.iterdir())
        except (PermissionError, OSError):
            continue
        for entry in entries:
            if is_protected(entry):
                continue
            if name_matches_app(entry.name, bundle_id, app_name):
                found.append(entry)
    return found


# ─────────────────────────────────────────────────────────────────────
#  Clean Up — Kategorien
# ─────────────────────────────────────────────────────────────────────

CLEANUP_CATEGORIES = [
    {
        "key": "caches", "icon": "caches", "name": "Caches",
        "desc": "Temporäre Cache-Dateien von Apps und Browsern",
        "subcategories": [
            {"name": "Safari-Cache", "paths": [HOME / "Library/Caches/com.apple.Safari"], "children": True},
            {"name": "Chrome-Cache", "paths": [
                HOME / "Library/Caches/Google/Chrome",
                HOME / "Library/Application Support/Google/Chrome/Default/Cache",
                HOME / "Library/Application Support/Google/Chrome/Default/Code Cache",
            ], "children": True},
            {"name": "Firefox-Cache", "paths": [HOME / "Library/Caches/Firefox"], "children": True},
            {"name": "App-Caches (gesamt)", "paths": [HOME / "Library/Caches"], "children": True, "exclude_subdirs": ["com.apple.Safari", "Google", "Firefox"]},
            {"name": "App-Logs", "paths": [HOME / "Library/Logs"], "children": True},
            {"name": "Xcode DerivedData", "paths": [HOME / "Library/Developer/Xcode/DerivedData"], "children": True},
            {"name": "Crash Reports", "paths": [HOME / "Library/Logs/DiagnosticReports"], "children": True},
        ],
    },
    {
        "key": "downloads", "icon": "downloads", "name": "Downloads",
        "desc": "Dateien aus dem Download-Ordner",
        "scan": "downloads",
    },
    {
        "key": "installers", "icon": "installers", "name": "Installer-Dateien",
        "desc": ".dmg und .pkg in Downloads",
        "scan": "installers",
    },
    {
        "key": "screenshots", "icon": "screenshots", "name": "Screenshots",
        "desc": "Bildschirmfotos auf Desktop und in ~/Pictures/Screenshots",
        "scan": "screenshots",
    },
    {
        "key": "languages", "icon": "languages", "name": "Sprach-Dateien",
        "desc": "Anzeige (nur Information — Löschen kann Apps beeinträchtigen)",
        "scan": "languages",
        "readonly": True,
    },
    {
        "key": "trash", "icon": "trash", "name": "Papierkorb",
        "desc": "Inhalt von ~/.Trash",
        "subcategories": [
            {"name": "Papierkorb", "paths": [HOME / ".Trash"], "children": True},
        ],
    },
    {
        "key": "mail_attachments", "icon": "mail", "name": "Mail-Attachments",
        "desc": "Heruntergeladene Mail-Anhänge",
        "subcategories": [
            {"name": "Mail Downloads", "paths": [
                HOME / "Library/Containers/com.apple.mail/Data/Library/Mail Downloads",
            ], "children": True},
        ],
    },
    {
        "key": "saved_state", "icon": "saved_state", "name": "Saved Application States",
        "desc": "Gespeicherte App-Zustände",
        "subcategories": [
            {"name": "Saved States", "paths": [HOME / "Library/Saved Application State"], "children": True},
        ],
    },
]


def collect_subcategory_items(sub: dict) -> list[Path]:
    items: list[Path] = []
    exclude = set(sub.get("exclude_subdirs", []))
    for base in sub["paths"]:
        if not base.exists():
            continue
        if sub.get("children"):
            try:
                for child in base.iterdir():
                    if child.name in exclude or is_protected(child):
                        continue
                    items.append(child)
            except (PermissionError, OSError):
                continue
        else:
            if not is_protected(base):
                items.append(base)
    return items


def scan_downloads(min_age_days: int = 0) -> list[Path]:
    """Alle Files/Folders in ~/Downloads. min_age_days=0 → alle."""
    base = HOME / "Downloads"
    if not base.exists():
        return []
    items = []
    import time
    cutoff = time.time() - min_age_days * 86400
    try:
        for entry in base.iterdir():
            if entry.name.startswith("."):
                continue
            try:
                if entry.stat().st_mtime <= cutoff:
                    items.append(entry)
            except Exception:
                continue
    except (PermissionError, OSError):
        pass
    return items


def scan_installers() -> list[Path]:
    base = HOME / "Downloads"
    if not base.exists():
        return []
    items = []
    try:
        for entry in base.iterdir():
            if entry.suffix.lower() in INSTALLER_EXTS:
                items.append(entry)
    except (PermissionError, OSError):
        pass
    return items


def scan_screenshots() -> list[Path]:
    items = []
    locations = [HOME / "Desktop", HOME / "Pictures" / "Screenshots", HOME / "Pictures"]
    seen = set()
    for loc in locations:
        if not loc.exists():
            continue
        try:
            for entry in loc.iterdir():
                if entry.is_dir():
                    continue
                name = entry.name
                if (name.startswith("Bildschirmfoto") or
                    name.startswith("Screen Shot") or
                    name.startswith("Screenshot") or
                    name.startswith("Screen Recording") or
                    name.startswith("Bildschirmaufnahme")):
                    if entry not in seen:
                        items.append(entry)
                        seen.add(entry)
        except (PermissionError, OSError):
            continue
    return items


def scan_language_files() -> list[Path]:
    """Findet .lproj-Ordner in /Applications. Nur zur Anzeige!"""
    items = []
    keep = {"Base.lproj", "en.lproj", "de.lproj", "English.lproj", "German.lproj"}
    for base in APP_DIRS:
        if not base.exists():
            continue
        try:
            for app in base.iterdir():
                if app.suffix != ".app":
                    continue
                resources = app / "Contents" / "Resources"
                if not resources.exists():
                    continue
                try:
                    for entry in resources.iterdir():
                        if entry.suffix == ".lproj" and entry.name not in keep:
                            items.append(entry)
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            continue
    return items


# ─────────────────────────────────────────────────────────────────────
#  Speed Up
# ─────────────────────────────────────────────────────────────────────

def list_login_items() -> list[dict]:
    """Login Items via osascript + LaunchAgents."""
    items: list[dict] = []
    # Login Items (System Events)
    try:
        r = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get the name of every login item'],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and r.stdout.strip():
            for name in [n.strip() for n in r.stdout.split(",")]:
                if name:
                    items.append({"type": "login", "name": name, "enabled": True, "path": ""})
    except Exception:
        pass

    # User LaunchAgents
    for base, scope in [
        (HOME / "Library/LaunchAgents", "user"),
        (Path("/Library/LaunchAgents"), "system"),
    ]:
        if not base.exists():
            continue
        try:
            for plist in base.glob("*.plist"):
                try:
                    with open(plist, "rb") as f:
                        data = plistlib.load(f)
                    label = data.get("Label", plist.stem)
                    run_at_load = data.get("RunAtLoad", False)
                    items.append({
                        "type": "agent",
                        "name": label,
                        "enabled": run_at_load,
                        "path": str(plist),
                        "scope": scope,
                    })
                except Exception:
                    continue
        except (PermissionError, OSError):
            continue
    return items


def heavy_running_apps(top_n: int = 15) -> list[dict]:
    """Laufende Prozesse mit höchstem RAM, nur 'echte' Apps."""
    try:
        r = subprocess.run(
            ["ps", "-axo", "pid,rss,comm"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            return []
        rows = []
        for line in r.stdout.strip().split("\n")[1:]:
            parts = line.strip().split(None, 2)
            if len(parts) < 3:
                continue
            try:
                pid = int(parts[0])
                rss_kb = int(parts[1])
            except ValueError:
                continue
            comm = parts[2]
            # Bevorzugt App-Bundles und sichtbare Apps
            if ".app/" in comm or comm.startswith("/Applications"):
                # Extract app name
                m = re.search(r"/([^/]+)\.app/", comm)
                name = m.group(1) if m else os.path.basename(comm)
                rows.append({
                    "pid": pid,
                    "name": name,
                    "rss_bytes": rss_kb * 1024,
                    "command": comm,
                })
        # Aggregiere pro App-Name
        by_name = defaultdict(lambda: {"name": "", "rss_bytes": 0, "pids": []})
        for r in rows:
            agg = by_name[r["name"]]
            agg["name"] = r["name"]
            agg["rss_bytes"] += r["rss_bytes"]
            agg["pids"].append(r["pid"])
        sorted_apps = sorted(by_name.values(), key=lambda x: -x["rss_bytes"])
        return sorted_apps[:top_n]
    except Exception:
        return []


def list_browser_extensions() -> list[dict]:
    """Browser-Extensions auflisten (Chrome, Firefox, Safari)."""
    extensions: list[dict] = []

    # Chrome
    chrome_base = HOME / "Library/Application Support/Google/Chrome"
    if chrome_base.exists():
        try:
            for profile in chrome_base.iterdir():
                ext_dir = profile / "Extensions"
                if not ext_dir.exists():
                    continue
                for ext in ext_dir.iterdir():
                    if ext.is_dir():
                        # Try to find latest version manifest
                        try:
                            versions = [v for v in ext.iterdir() if v.is_dir()]
                            if not versions:
                                continue
                            latest = sorted(versions)[-1]
                            manifest = latest / "manifest.json"
                            name = ext.name[:8]
                            if manifest.exists():
                                try:
                                    md = json.loads(manifest.read_text())
                                    name = md.get("name", name)
                                    if name.startswith("__MSG_"):
                                        name = ext.name[:8]
                                except Exception:
                                    pass
                            extensions.append({
                                "browser": "Chrome",
                                "name": name,
                                "id": ext.name,
                                "path": ext,
                                "size": get_size_bytes(ext),
                            })
                        except Exception:
                            continue
        except (PermissionError, OSError):
            pass

    # Firefox
    ff_base = HOME / "Library/Application Support/Firefox/Profiles"
    if ff_base.exists():
        try:
            for profile in ff_base.iterdir():
                ext_dir = profile / "extensions"
                if not ext_dir.exists():
                    continue
                for ext in ext_dir.iterdir():
                    extensions.append({
                        "browser": "Firefox",
                        "name": ext.stem,
                        "id": ext.name,
                        "path": ext,
                        "size": get_size_bytes(ext),
                    })
        except (PermissionError, OSError):
            pass

    # Safari extensions (über Container)
    safari_ext = HOME / "Library/Containers/com.apple.Safari/Data/Library/Safari/AppExtensions"
    if safari_ext.exists():
        try:
            for ext in safari_ext.iterdir():
                extensions.append({
                    "browser": "Safari",
                    "name": ext.stem,
                    "id": ext.name,
                    "path": ext,
                    "size": get_size_bytes(ext),
                })
        except (PermissionError, OSError):
            pass

    return extensions


# ─────────────────────────────────────────────────────────────────────
#  Manage Files — Kategorien
# ─────────────────────────────────────────────────────────────────────

MANAGE_CATEGORIES = [
    {"key": "documents", "icon": "documents", "name": "Dokumente", "path": HOME / "Documents"},
    {"key": "movies",    "icon": "movies",    "name": "Filme",     "path": HOME / "Movies"},
    {"key": "music",     "icon": "music",     "name": "Musik",     "path": HOME / "Music"},
    {"key": "pictures",  "icon": "pictures",  "name": "Bilder",    "path": HOME / "Pictures"},
    {"key": "downloads", "icon": "downloads", "name": "Downloads", "path": HOME / "Downloads"},
    {"key": "desktop",   "icon": "desktop",   "name": "Schreibtisch", "path": HOME / "Desktop"},
    {"key": "archives",  "icon": "archives",  "name": "Archive",   "scan": "archives"},
]


def list_files_in(path: Path, max_files: int = 1000) -> list[dict]:
    """Top-Level Dateien/Ordner in einem Verzeichnis, sortiert nach Größe."""
    if not path.exists():
        return []
    items = []
    try:
        for entry in path.iterdir():
            if entry.name.startswith("."):
                continue
            try:
                size = get_size_bytes(entry)
                items.append({
                    "name": entry.name,
                    "path": entry,
                    "size": size,
                    "is_dir": entry.is_dir(),
                    "mtime": entry.stat().st_mtime,
                })
            except Exception:
                continue
            if len(items) >= max_files:
                break
    except (PermissionError, OSError):
        pass
    items.sort(key=lambda x: -x["size"])
    return items


def find_archives() -> list[dict]:
    """Sucht Archiv-Dateien in Home-Subfoldern."""
    items = []
    bases = [HOME / "Downloads", HOME / "Documents", HOME / "Desktop"]
    for base in bases:
        if not base.exists():
            continue
        try:
            for root, dirs, files in os.walk(base):
                # Geschützte Pfade überspringen
                if any(p in root for p in ("Library/Mobile Documents", ".Trash")):
                    dirs.clear()
                    continue
                for f in files:
                    if Path(f).suffix.lower() in ARCHIVE_EXTS:
                        full = Path(root) / f
                        try:
                            items.append({
                                "name": f,
                                "path": full,
                                "size": full.stat().st_size,
                                "is_dir": False,
                                "mtime": full.stat().st_mtime,
                            })
                        except Exception:
                            continue
                if len(items) > 2000:
                    break
        except (PermissionError, OSError):
            continue
    items.sort(key=lambda x: -x["size"])
    return items


# ─────────────────────────────────────────────────────────────────────
#  Tools — Duplicates, Biggest Files
# ─────────────────────────────────────────────────────────────────────

def find_biggest_files(min_size_mb: int = 50, max_results: int = 200,
                        bases: list[Path] | None = None) -> list[dict]:
    """Findet die größten Dateien unter den angegebenen Basisordnern."""
    if bases is None:
        bases = [HOME / "Documents", HOME / "Movies", HOME / "Music",
                  HOME / "Pictures", HOME / "Downloads", HOME / "Desktop"]
    threshold = min_size_mb * 1024 * 1024
    files = []
    for base in bases:
        if not base.exists():
            continue
        try:
            for root, dirs, fnames in os.walk(base, followlinks=False):
                if "Library/Mobile Documents" in root or ".Trash" in root:
                    dirs.clear()
                    continue
                for fn in fnames:
                    full = Path(root) / fn
                    try:
                        st = full.stat()
                        if st.st_size >= threshold:
                            files.append({
                                "name": fn,
                                "path": full,
                                "size": st.st_size,
                                "mtime": st.st_mtime,
                            })
                    except Exception:
                        continue
        except (PermissionError, OSError):
            continue
    files.sort(key=lambda x: -x["size"])
    return files[:max_results]


def find_duplicates(bases: list[Path] | None = None,
                     min_size_kb: int = 100,
                     max_files: int = 5000) -> list[list[dict]]:
    """Findet Duplikate per Größe → Hash. Returnt Gruppen."""
    if bases is None:
        bases = [HOME / "Documents", HOME / "Downloads", HOME / "Desktop", HOME / "Pictures"]
    threshold = min_size_kb * 1024

    by_size: dict[int, list[Path]] = defaultdict(list)
    count = 0
    for base in bases:
        if not base.exists():
            continue
        try:
            for root, dirs, fnames in os.walk(base, followlinks=False):
                if "Library/Mobile Documents" in root or ".Trash" in root:
                    dirs.clear()
                    continue
                for fn in fnames:
                    if fn.startswith("."):
                        continue
                    full = Path(root) / fn
                    try:
                        sz = full.stat().st_size
                    except Exception:
                        continue
                    if sz < threshold:
                        continue
                    by_size[sz].append(full)
                    count += 1
                    if count >= max_files:
                        break
                if count >= max_files:
                    break
        except (PermissionError, OSError):
            continue
        if count >= max_files:
            break

    groups: list[list[dict]] = []
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        by_hash: dict[str, list[Path]] = defaultdict(list)
        for p in paths:
            try:
                h = hashlib.md5()
                with open(p, "rb") as f:
                    while chunk := f.read(1024 * 1024):
                        h.update(chunk)
                        # nur ersten MB hashen für Speed (wenn Datei >5MB)
                        if size > 5 * 1024 * 1024:
                            break
                by_hash[h.hexdigest()].append(p)
            except Exception:
                continue
        for h, ps in by_hash.items():
            if len(ps) < 2:
                continue
            groups.append([{"path": p, "size": size} for p in ps])

    groups.sort(key=lambda g: -g[0]["size"] * (len(g) - 1))
    return groups
