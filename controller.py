#!/usr/bin/env python3
"""Discover appearance sources and installed application font surfaces."""

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

from font_application_inventory import installed_font_applications, persist_font_application_inventory, shell_font_surfaces
from appearance_audit import audit_appearance
from appearance_audit import _theme_mode_expected
from appearance_actions import action_status, apply_action, rollback_action
from mail_font_adapters import betterbird_font_target
from manual_app_inspector import inspect_app
from transaction import FILE_TARGETS, TransactionError, apply_file_targets, recover_pending, rollback_latest, transaction_status


HOME = Path.home()


def omarchy_root() -> Path:
    configured = os.environ.get("OMARCHY_PATH", "").strip()
    if configured:
        path = Path(configured)
        if path.is_absolute() and path.is_dir():
            return path
    config_file = Path("/etc/omarchy.conf")
    try:
        match = re.fullmatch(r'export OMARCHY_PATH="([^"]+)"\s*', config_file.read_text(encoding="utf-8").strip())
        if match:
            path = Path(match.group(1))
            if path.is_absolute() and path.is_dir():
                return path
    except OSError:
        pass
    return Path("/usr/share/omarchy")


OMARCHY_ROOT = omarchy_root()
THEME_DIRS = (OMARCHY_ROOT / "themes", HOME / ".config/omarchy/themes")
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
    OMARCHY_ROOT / "backgrounds",
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
    if entry.get("applyMethod") == "omarchy":
        if entry.get("review") == "ambiguous-plymouth-logo-readback":
            return False
        return entry.get("compatibility") in {"verified", "not-required"}
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
        user_dir = HOME / ".config/omarchy/themes" / name
        palette_compatible = any(
            (base / name / filename).is_file()
            for base in THEME_DIRS for filename in ("colors.toml", "alacritty.toml")
        )
        entries.append({
            "id": stable_id("theme", name), "kind": "theme", "name": name,
            "displayName": display_words(name),
            "source": sources, "license": None,
            "review": "omarchy-managed-theme" if palette_compatible else "missing-theme-palette",
            "licenseEvidence": None, "provenanceVerified": True,
            "compatibility": "verified" if palette_compatible else "pending", "developmentOnly": False,
            "applyMethod": "omarchy",
            "selectable": False,
        })
    return entries


def unlock_designs() -> list[dict[str, object]]:
    """Discover exactly the theme directory Omarchy's unlock setter resolves."""
    candidates: list[dict[str, object]] = []
    names = set(direct_dirs(THEME_DIRS))
    default_logo = OMARCHY_ROOT / "default/plymouth/logo.png"
    try:
        default_digest = hashlib.sha256(default_logo.read_bytes()).hexdigest() if default_logo.is_file() and not default_logo.is_symlink() else None
    except OSError:
        default_digest = None
    for name in sorted(names, key=str.casefold):
        user_dir = HOME / ".config/omarchy/themes" / name
        theme_dir = user_dir if user_dir.is_dir() else OMARCHY_ROOT / "themes" / name
        unlock_image = theme_dir / "unlock.png"
        preview = theme_dir / "preview-unlock.png"
        if not theme_dir.is_dir() or unlock_image.is_symlink() or preview.is_symlink() or not unlock_image.is_file() or not preview.is_file():
            continue
        try:
            digest = hashlib.sha256(unlock_image.read_bytes()).hexdigest()
        except OSError:
            continue
        candidates.append({
            "id": stable_id("unlock", name), "kind": "unlock", "name": name,
            "displayName": display_words(name), "source": [str(unlock_image)],
            "preview": str(preview), "license": None,
            "review": "omarchy-theme-unlock", "licenseEvidence": None,
            "provenanceVerified": True, "compatibility": "not-required",
            "developmentOnly": False, "applyMethod": "omarchy", "selectable": True,
            "_logoDigest": digest,
        })
    digest_counts: dict[str, int] = {}
    for entry in candidates:
        digest = str(entry.pop("_logoDigest"))
        digest_counts[digest] = digest_counts.get(digest, 0) + 1
        entry["_logoDigest"] = digest
    for entry in candidates:
        digest = str(entry.pop("_logoDigest"))
        if digest_counts[digest] > 1 or digest == default_digest:
            entry["review"] = "ambiguous-plymouth-logo-readback"
            entry["selectable"] = False
    return candidates


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
            "compatibility": "not-required", "applyMethod": "omarchy", "selectable": False,
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


def selected_terminal_font(font_records: list[dict[str, object]]) -> str | None:
    """Read the saved dropdown choice, falling back to the managed Ghostty font."""
    xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", str(HOME / ".config")))
    if not xdg_config.is_absolute():
        xdg_config = HOME / ".config"
    try:
        xdg_config.relative_to(HOME)
    except ValueError:
        return None
    by_name = {str(item["name"]): str(item["id"]) for item in font_records}
    preference_path = xdg_config / "ghostty/look-and-feel-font-selection.json"
    if preference_path.is_file() and not preference_path.is_symlink():
        try:
            saved = json.loads(preference_path.read_text(encoding="utf-8"))
            family = saved.get("fontFamily") if isinstance(saved, dict) and saved.get("schemaVersion") in {1, 2} else None
            if isinstance(family, str) and family in by_name:
                expected_id = stable_id("font", family)
                if saved.get("terminalFontId") == expected_id:
                    return expected_id
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    overlay_path = xdg_config / "ghostty/look-and-feel-font.conf"
    try:
        if overlay_path.is_file() and not overlay_path.is_symlink():
            for line in reversed(overlay_path.read_text(encoding="utf-8").splitlines()):
                match = re.fullmatch(r'\s*font-family\s*=\s*"(.*)"\s*', line)
                if match and match.group(1):
                    family = match.group(1).replace('\\"', '"').replace('\\\\', '\\')
                    return by_name.get(family)
    except (OSError, UnicodeError):
        pass
    return None


def selected_terminal_font_size() -> int | None:
    xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", str(HOME / ".config")))
    if not xdg_config.is_absolute():
        xdg_config = HOME / ".config"
    path = xdg_config / "ghostty/look-and-feel-font-selection.json"
    if not path.is_file() or path.is_symlink():
        return None
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        size = saved.get("fontSizePt") if isinstance(saved, dict) and saved.get("schemaVersion") == 2 else None
        return size if isinstance(size, int) and not isinstance(size, bool) and 6 <= size <= 48 else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def inventory() -> dict[str, object]:
    fonts = font_entries()
    font_applications = installed_font_applications()
    shell_fonts = shell_font_surfaces()
    font_applications["shellSurfaces"] = shell_fonts
    try:
        font_application_record_path = persist_font_application_inventory(font_applications)
        font_application_record_error = None
    except (OSError, ValueError) as exc:
        font_application_record_path = None
        font_application_record_error = str(exc)
    entries = {
        "themes": theme_entries(),
        "unlocks": unlock_designs(),
        "fonts": fonts,
        "icons": icon_entries(),
        "backgrounds": background_entries(),
    }
    for records in entries.values():
        for record in records:
            record["selectable"] = catalog_entry_eligible(record)
    return {
        "application_configs_modified": False,
        "font_application_inventory": font_applications,
        "shell_font_surfaces": shell_fonts,
        "font_application_inventory_record": font_application_record_path,
        "font_application_inventory_record_error": font_application_record_error,
        "preferences": {
            "terminalFontId": selected_terminal_font(fonts),
            "terminalFontSizePt": selected_terminal_font_size(),
        },
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
        "appearance_action_status": action_status(),
        "catalog_sources": {
            "source_policy": "live canonical system and user locations; no plugin snapshot required",
            "themes": [str(path) for path in THEME_DIRS],
            "unlocks": [str(path / "<theme>/{unlock.png,preview-unlock.png}") for path in THEME_DIRS],
            "fonts": ["fontconfig system and user font directories"],
            "icons": [str(path) for path in ICON_DIRS],
            "backgrounds": [str(CURRENT_BACKGROUND_PATH), *(str(path) for path in BACKGROUND_DIRS), *(str(root / "<theme>/backgrounds") for root in THEME_DIRS)],
        },
    }


def apply_selected_theme(mode: str, light_name: str, dark_name: str) -> dict[str, object]:
    available = {
        str(entry["name"]).casefold().replace(" ", "-")
        for entry in theme_entries() if catalog_entry_eligible(entry)
    }
    light = light_name.casefold().replace(" ", "-")
    dark = dark_name.casefold().replace(" ", "-")
    if light not in available or dark not in available:
        raise TransactionError("one of the selected themes is no longer installed")
    if mode not in {"light", "dark", "automatic"}:
        raise TransactionError("select Light, Dark, or Automatic theme mode")
    selected, reason = _theme_mode_expected(mode, display_words(light), display_words(dark))
    if not selected:
        raise TransactionError(reason)
    target = selected.casefold().replace(" ", "-")
    result = apply_action("theme", target, available)
    result["selectionReason"] = reason
    result["automaticFutureSwitching"] = "not-scheduled"
    return result


def apply_catalog_action(kind: str, entry_id: str) -> dict[str, object]:
    if kind == "background":
        records = [entry for entry in background_entries() if catalog_entry_eligible(entry)]
        entry = next((item for item in records if item["id"] == entry_id), None)
        if entry is None:
            raise TransactionError("selected background is no longer available")
        target = str(entry["source"])
        allowed = {str(item["source"]) for item in records}
    elif kind == "unlock":
        records = [entry for entry in unlock_designs() if catalog_entry_eligible(entry)]
        entry = next((item for item in records if item["id"] == entry_id), None)
        if entry is None:
            raise TransactionError("selected unlock design is no longer available")
        target = str(entry["name"])
        allowed = {str(item["name"]) for item in records}
    else:
        raise TransactionError("unknown catalog action")
    return apply_action(kind, target, allowed)


def ghostty_font_target(font_id: str, font_name: str, font_size: int = 12) -> dict[str, bytes]:
    """Build the Ghostty config, font overlay, and saved selection payloads."""
    if isinstance(font_size, bool) or not isinstance(font_size, int) or not 6 <= font_size <= 48:
        raise TransactionError("Ghostty font size must be an integer between 6 and 48 pt")
    if font_name not in font_families():
        raise TransactionError("selected font is not currently available through fontconfig")
    xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", str(HOME / ".config")))
    if not xdg_config.is_absolute():
        xdg_config = HOME / ".config"
    try:
        xdg_config.relative_to(HOME)
    except ValueError as exc:
        raise TransactionError("Ghostty's XDG config directory is outside the managed home boundary") from exc
    ghostty_dir = xdg_config / "ghostty"
    config_path = ghostty_dir / ("config.ghostty" if (ghostty_dir / "config.ghostty").exists() else "config")
    if not config_path.is_file():
        raise TransactionError("Ghostty config file is missing; refusing to create an unverified config")
    try:
        original = config_path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise TransactionError(f"cannot safely read Ghostty config: {exc}") from exc
    import_line = "config-file = look-and-feel-font.conf"
    lines = original.splitlines()
    if import_line not in lines:
        lines.append(import_line)
    updated_config = ("\n".join(lines).rstrip("\n") + "\n").encode("utf-8")
    escaped = font_name.replace("\\", "\\\\").replace('"', '\\"')
    overlay = f'font-family = ""\nfont-family = "{escaped}"\nfont-size = {font_size}\n'.encode("utf-8")
    preference = (json.dumps({
        "schemaVersion": 2,
        "terminalFontId": font_id,
        "fontFamily": font_name,
        "fontSizePt": font_size,
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return {
        "ghostty-config": updated_config,
        "ghostty-font-overlay": overlay,
        "terminal-font-selection": preference,
    }


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "appearance-action-status" and argv[1] in {"theme", "background", "unlock"}:
        json.dump(action_status()[argv[1]], sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if len(argv) == 4 and argv[0] == "apply-theme":
        try:
            result = apply_selected_theme(argv[1], argv[2], argv[3])
        except (TransactionError, OSError, ValueError) as exc:
            print(f"Theme Apply failed: {exc}", file=sys.stderr)
            return 1
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if len(argv) == 3 and argv[0] == "apply-catalog-action":
        try:
            result = apply_catalog_action(argv[1], argv[2])
        except (TransactionError, OSError, ValueError) as exc:
            print(f"Appearance Apply failed: {exc}", file=sys.stderr)
            return 1
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if len(argv) == 2 and argv[0] == "rollback-appearance":
        try:
            result = rollback_action(argv[1])
        except (TransactionError, OSError, ValueError) as exc:
            print(f"Appearance Undo failed: {exc}", file=sys.stderr)
            return 1
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if len(argv) == 2 and argv[0] == "audit-appearance":
        try:
            expected = json.loads(argv[1])
            if not isinstance(expected, dict):
                raise ValueError("expected audit values must be an object")
            result = audit_appearance(expected, installed_font_applications())
        except (ValueError, OSError, TypeError) as exc:
            print(f"Appearance audit failed: {exc}", file=sys.stderr)
            return 1
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if len(argv) == 2 and argv[0] == "inspect-app":
        json.dump(inspect_app(argv[1]), sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if argv == ["inventory"]:
        json.dump(inventory(), sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if len(argv) == 1 and argv[0] == "rollback-ghostty-font":
        try:
            result = {"rolledBack": rollback_latest(label="Ghostty font")}
        except TransactionError as exc:
            print(f"Ghostty font rollback failed: {exc}", file=sys.stderr)
            return 1
        json.dump(result, sys.stdout)
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
    if len(argv) == 3 and argv[0] == "apply-ghostty-font":
        try:
            entry = next((item for item in font_entries() if item["id"] == argv[1]), None)
            if entry is None:
                raise TransactionError("selected font is no longer in the current catalog")
            font_size = int(argv[2])
            transaction_id = apply_file_targets(ghostty_font_target(str(entry["id"]), str(entry["name"]), font_size), label="Ghostty font")
        except (TransactionError, ValueError) as exc:
            print(f"Ghostty font Apply failed: {exc}", file=sys.stderr)
            return 1
        json.dump({"transaction": transaction_id, "font": entry["name"], "sizePt": font_size}, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    if len(argv) == 3 and argv[0] == "apply-mail-system-font":
        try:
            entry = next((item for item in font_entries() if item["id"] == argv[1]), None)
            if entry is None:
                raise TransactionError("selected font is no longer in the current catalog")
            size_pt = int(argv[2])
            target = betterbird_font_target(str(entry["name"]), size_pt)
            transaction_id = apply_file_targets(target, label="Mail application system font")
        except (TransactionError, ValueError, OSError) as exc:
            print(f"Mail application font Apply failed: {exc}", file=sys.stderr)
            return 1
        json.dump({"transaction": transaction_id, "font": entry["name"], "sizePt": size_pt, "application": "Betterbird"}, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    if len(argv) == 1 and argv[0] == "rollback-mail-system-font":
        try:
            transaction_id = rollback_latest(label="Mail application system font")
        except TransactionError as exc:
            print(f"Mail application font rollback failed: {exc}", file=sys.stderr)
            return 1
        json.dump({"rolledBack": transaction_id}, sys.stdout)
        sys.stdout.write("\n")
        return 0
    print("Usage: controller.py inventory | audit-appearance JSON | transaction {status|recover|rollback}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
