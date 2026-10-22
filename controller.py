#!/usr/bin/env python3
"""Read-only source and application inventory for Omarchy Look & Feel."""

from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import subprocess
import sys
from urllib.parse import urlparse
from pathlib import Path

from transaction import TransactionError, recover_pending, rollback_latest, transaction_status


HOME = Path.home()
THEME_DIRS = (Path("/usr/share/omarchy/themes"), HOME / ".config/omarchy/themes")
_xdg_data_home = Path(os.environ.get("XDG_DATA_HOME", ""))
XDG_DATA_HOME = _xdg_data_home if _xdg_data_home.is_absolute() else HOME / ".local/share"
_xdg_data_dirs = os.environ.get("XDG_DATA_DIRS", "") or "/usr/local/share:/usr/share"
XDG_DATA_DIRS = tuple(
    Path(path) for path in _xdg_data_dirs.split(":")
    if path and Path(path).is_absolute()
)
ICON_DIRS = tuple(path / "icons" for path in (XDG_DATA_HOME, *XDG_DATA_DIRS))
CURRENT_BACKGROUND_PATH = HOME / ".local/state/omarchy/current/background"
WEATHER_SETTINGS_PATH = HOME / ".local/state/omarchy/settings/weather.json"
LOCALTIME_PATH = Path("/etc/localtime")
BACKGROUND_DIRS = (
    HOME / "Documents/Fonts_Icons_Wallpaper/Backgrounds",
    HOME / ".config/omarchy/backgrounds",
    Path("/usr/share/omarchy/backgrounds"),
)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
FONT_REVIEW_PATH = Path(__file__).with_name("font-reviews.json")
DEVELOPMENT_THEME_NAMES = {"dracula-pro-alucard", "dracula-pro-van-helsing"}

APPLICATIONS = (
    ("Hey", ("hey", "omarchy-webapp-handler-hey")),
    ("LibreOffice Fresh", ("libreoffice", "soffice")),
    ("OnlyOffice Desktop Editors", ("onlyoffice-desktopeditors",)),
    ("PCManFM", ("pcmanfm",)),
    ("Terminal: Alacritty", ("alacritty",)),
    ("Terminal: Foot", ("foot",)),
    ("Terminal: Ghostty", ("ghostty",)),
    ("Terminal: Kitty", ("kitty",)),
    ("Terminal: WezTerm", ("wezterm",)),
    ("Browser: Brave", ("brave", "brave-browser")),
)


def direct_dirs(paths: tuple[Path, ...]) -> list[str]:
    names: set[str] = set()
    for base in paths:
        if not base.is_dir():
            continue
        try:
            names.update(p.name for p in base.iterdir() if p.is_dir() and not p.name.startswith("."))
        except OSError:
            continue
    return sorted(names, key=str.casefold)


def stable_id(kind: str, identity: str) -> str:
    """Build a readable, deterministic ID without depending on display order."""
    slug = re.sub(r"[^a-z0-9]+", "-", identity.casefold()).strip("-") or "item"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"{kind}:{slug[:48]}-{digest}"


def display_words(value: str) -> str:
    """Turn hyphen/underscore-separated catalog slugs into readable names."""
    return " ".join(part[:1].upper() + part[1:] for part in re.split(r"[-_]+", value) if part)


def catalog_entry_eligible(entry: dict[str, object]) -> bool:
    """Require reviewed evidence, or an explicit development-only approval."""
    compatibility = entry.get("compatibility")
    compatibility_ok = compatibility == "verified" if entry.get("kind") == "theme" else compatibility == "not-required"
    if entry.get("developmentOnly") is True:
        return entry.get("review") == "development-approved" and compatibility_ok
    license_name = entry.get("license")
    evidence = entry.get("licenseEvidence")
    parsed = urlparse(evidence) if isinstance(evidence, str) else None
    evidence_ok = bool(parsed and parsed.scheme in {"https", "file"} and parsed.path)
    return bool(
        entry.get("review") == "verified"
        and entry.get("provenanceVerified") is True
        and isinstance(license_name, str) and license_name.strip()
        and evidence_ok
        and compatibility_ok
    )


def themes() -> list[str]:
    # A user overlay and its package theme share one selector entry.
    return direct_dirs(THEME_DIRS)


def theme_entries() -> list[dict[str, object]]:
    entries = []
    for name in themes():
        sources = [str(base / name) for base in THEME_DIRS if (base / name).is_dir()]
        development_only = name in DEVELOPMENT_THEME_NAMES
        entries.append({
            "id": stable_id("theme", name), "kind": "theme", "name": name,
            "displayName": display_words(name),
            "source": sources, "license": None,
            "review": "needs-compatibility-review" if development_only else "needs-compatibility-and-license-review",
            "licenseEvidence": None, "provenanceVerified": False,
            "compatibility": "pending", "developmentOnly": development_only,
            "selectable": False,
        })
    return entries


def unlock_designs() -> list[dict[str, object]]:
    """Discover boot-unlock designs directly from live Omarchy theme trees."""
    found: dict[str, dict[str, object]] = {}
    for base in THEME_DIRS:
        if not base.is_dir():
            continue
        try:
            for theme_dir in base.iterdir():
                unlock_image = theme_dir / "unlock.png"
                preview = theme_dir / "preview-unlock.png"
                if theme_dir.name.startswith(".") or not theme_dir.is_dir() or not unlock_image.is_file() or not preview.is_file():
                    continue
                record = found.setdefault(theme_dir.name, {
                    "id": stable_id("unlock", theme_dir.name),
                    "kind": "unlock",
                    "name": theme_dir.name,
                    "displayName": display_words(theme_dir.name),
                    "source": [],
                    "preview": str(preview),
                    "license": None,
                    "review": "provenance-unverified",
                    "licenseEvidence": None,
                    "provenanceVerified": False,
                    "compatibility": "not-required",
                    "developmentOnly": False,
                    "selectable": False,
                })
                record["source"].append(str(unlock_image))
                # THEME_DIRS is ordered system first, then user overrides.
                record["preview"] = str(preview)
        except OSError:
            continue
    return [found[name] for name in sorted(found, key=str.casefold)]


def icon_themes() -> list[str]:
    names: set[str] = set()
    for base in ICON_DIRS:
        if not base.is_dir():
            continue
        try:
            for item in base.iterdir():
                if item.is_dir() and (item / "index.theme").is_file():
                    names.add(item.name)
        except OSError:
            continue
    return sorted(names, key=str.casefold)


def icon_entries() -> list[dict[str, object]]:
    entries = []
    for name in icon_themes():
        sources = [str(base / name) for base in ICON_DIRS if (base / name / "index.theme").is_file()]
        entries.append({
            "id": stable_id("icon", name), "kind": "icon", "name": name,
            "displayName": display_words(name),
            "source": sources, "license": None, "review": "metadata-unverified",
            "licenseEvidence": None, "provenanceVerified": False,
            "compatibility": "not-required", "selectable": False,
        })
    return entries


def backgrounds() -> list[str]:
    candidates: list[Path] = []
    seen_paths: set[str] = set()

    def add_candidate(path: Path) -> None:
        try:
            resolved = path.resolve(strict=True)
            if resolved.is_file() and resolved.suffix.lower() in IMAGE_SUFFIXES:
                source = str(resolved)
                if source not in seen_paths:
                    seen_paths.add(source)
                    candidates.append(resolved)
        except OSError:
            return

    background_dirs = list(BACKGROUND_DIRS)
    for theme_root in THEME_DIRS:
        if not theme_root.is_dir():
            continue
        try:
            background_dirs.extend(
                theme_dir / "backgrounds"
                for theme_dir in theme_root.iterdir()
                if theme_dir.is_dir() and (theme_dir / "backgrounds").is_dir()
            )
        except OSError:
            continue
    for base in background_dirs:
        if not base.is_dir():
            continue
        try:
            for path in base.rglob("*"):
                if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                    add_candidate(path)
        except OSError:
            continue
    add_candidate(CURRENT_BACKGROUND_PATH)

    # Prefer the first source path, while collapsing byte-identical copies
    # that share a filename and size (common for the active theme wallpaper).
    groups: dict[tuple[str, int], list[Path]] = {}
    for path in candidates:
        try:
            groups.setdefault((path.name, path.stat().st_size), []).append(path)
        except OSError:
            continue
    found: set[str] = set()
    for paths in groups.values():
        if len(paths) == 1:
            found.add(str(paths[0]))
            continue
        hashes: set[str] = set()
        for path in paths:
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
            if digest not in hashes:
                hashes.add(digest)
                found.add(str(path))
    return sorted(found, key=str.casefold)


def background_entries() -> list[dict[str, object]]:
    entries = []
    for path_string in backgrounds():
        path = Path(path_string)
        try:
            identity = path.relative_to(HOME).as_posix()
        except ValueError:
            identity = path.as_posix()
        entries.append({
            "id": stable_id("background", identity), "kind": "background",
            "name": path.name, "source": str(path), "license": None,
            "review": "provenance-unverified", "licenseEvidence": None,
            "provenanceVerified": False,
            "compatibility": "not-required", "selectable": False,
        })
    return entries


def font_families() -> list[str]:
    if not shutil.which("fc-list"):
        return []
    try:
        result = subprocess.run(
            ["fc-list", "--format", "%{family}\n"],
            check=True,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    names = set()
    for line in result.stdout.splitlines():
        # Fontconfig can return aliases separated by commas.
        names.update(part.strip() for part in line.split(",") if part.strip())
    return sorted(names, key=str.casefold)


def font_entries() -> list[dict[str, object]]:
    reviewed: dict[str, dict[str, object]] = {}
    try:
        records = json.loads(FONT_REVIEW_PATH.read_text(encoding="utf-8"))
        if isinstance(records, list):
            reviewed = {
                record["name"]: record for record in records
                if isinstance(record, dict) and isinstance(record.get("name"), str)
            }
    except (OSError, json.JSONDecodeError):
        pass

    entries = []
    for name in font_families():
        entry = reviewed.get(name)
        if entry is not None:
            # Curated metadata applies only to the exact family currently
            # reported by fontconfig; discovery alone never grants review.
            entries.append({**entry, "id": stable_id("font", name), "kind": "font", "selectable": False})
        else:
            entries.append({
                "id": stable_id("font", name), "kind": "font", "name": name,
                "source": "fontconfig; package/source not yet verified", "license": None,
                "review": "needs-provenance-and-license-review", "licenseEvidence": None,
                "provenanceVerified": False,
                "compatibility": "not-required", "selectable": False,
            })
    return entries


def application_inventory() -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for name, commands in APPLICATIONS:
        path = next((shutil.which(command) for command in commands if shutil.which(command)), None)
        entries.append({"name": name, "available": path is not None, "path": path or ""})
    return entries


def automatic_schedule_context() -> dict[str, object]:
    """Read solar coordinates and the IANA zone from existing system settings."""
    result: dict[str, object] = {
        "location": None,
        "timeZone": None,
        "locationSource": str(WEATHER_SETTINGS_PATH),
        "timeZoneSource": str(LOCALTIME_PATH),
    }
    try:
        weather = json.loads(WEATHER_SETTINGS_PATH.read_text(encoding="utf-8"))
        latitude, longitude = weather["latitude"], weather["longitude"]
        if (isinstance(latitude, bool) or not isinstance(latitude, (int, float))
                or not -90 <= latitude <= 90
                or isinstance(longitude, bool) or not isinstance(longitude, (int, float))
                or not -180 <= longitude <= 180):
            raise ValueError("invalid latitude or longitude")
        result["location"] = {
            "name": weather.get("name"),
            "latitude": latitude,
            "longitude": longitude,
        }
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        pass

    try:
        zone_path = LOCALTIME_PATH.resolve(strict=True)
        zone_root = Path("/usr/share/zoneinfo").resolve(strict=True)
        result["timeZone"] = zone_path.relative_to(zone_root).as_posix()
    except (OSError, ValueError):
        pass
    return result


def inventory() -> dict[str, object]:
    entries = {
        "themes": theme_entries(),
        "unlocks": unlock_designs(),
        "fonts": font_entries(),
        "icons": icon_entries(),
        "backgrounds": background_entries(),
    }
    for records in entries.values():
        for record in records:
            record["selectable"] = catalog_entry_eligible(record)
    return {
        "read_only": True,
        "applications": application_inventory(),
        "catalogs": {
            "themes": themes(),
            "unlocks": [entry["name"] for entry in entries["unlocks"]],
            "fonts": font_families(),
            "icons": icon_themes(),
            "backgrounds": backgrounds(),
        },
        "catalog_entries": entries,
        "automatic_schedule_context": automatic_schedule_context(),
        "catalog_review": {
            kind: {
                "total": len(records),
                "selectable": sum(1 for record in records if record["selectable"]),
                "pending_review": sum(1 for record in records if not record["selectable"]),
            }
            for kind, records in entries.items()
        },
        "catalog_sources": {
            "source_policy": "live canonical system and user locations; no plugin snapshot required",
            "themes": [str(path) for path in THEME_DIRS],
            "unlocks": [str(path / "<theme>/{unlock.png,preview-unlock.png}") for path in THEME_DIRS],
            "fonts": ["fontconfig system and user font directories"],
            "icons": [str(path) for path in ICON_DIRS],
            "backgrounds": [str(CURRENT_BACKGROUND_PATH), *(str(path) for path in BACKGROUND_DIRS), *(str(root / "<theme>/backgrounds") for root in THEME_DIRS)],
        },
    }


def main(argv: list[str]) -> int:
    if argv == ["inventory"]:
        json.dump(inventory(), sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if len(argv) == 2 and argv[0] == "transaction":
        action = argv[1]
        try:
            if action == "status":
                result: object = {"transactions": transaction_status()}
            elif action == "recover":
                result = {"recovered": recover_pending()}
            elif action == "rollback":
                result = {"rolledBack": rollback_latest()}
            else:
                raise ValueError
        except ValueError:
            print("Usage: controller.py transaction {status|recover|rollback}", file=sys.stderr)
            return 2
        except TransactionError as exc:
            print(f"Transaction action failed: {exc}", file=sys.stderr)
            return 1
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    print("Usage: controller.py inventory | transaction {status|recover|rollback}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
