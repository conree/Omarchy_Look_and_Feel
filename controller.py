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

from font_application_inventory import TERMINALS, installed_font_applications, persist_font_application_inventory, shell_font_surfaces
from appearance_audit import audit_appearance
from appearance_audit import _theme_mode_expected
from appearance_actions import action_status, apply_action, rollback_action
from global_font_actions import TERMINAL_COMMANDS, build_global_font_targets
from app_font_actions import build_app_targets
from browser_font_actions import build as build_browser_targets
from terminal_reload import reload_terminals
from manual_app_inspector import inspect_app
from manual_app_registry import clear_registry as clear_manual_app_registry, register_audit_result, registry_status, validated_apply_status
from transaction import FILE_TARGETS, TransactionError, apply_file_targets, has_committed_transaction, recover_pending, rollback_latest, transaction_status


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
    if entry.get("applyMethod") == "installed-icon":
        from icon_actions import selectable
        return entry.get("kind") == "icon" and selectable(entry.get("name", ""), entry.get("source", []))
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
    from appearance_previews import theme_preview
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
            "preview": theme_preview(sources),
            "review": "omarchy-managed-theme" if palette_compatible else "missing-theme-palette",
            "licenseEvidence": None, "provenanceVerified": True,
            "compatibility": "verified" if palette_compatible else "pending", "developmentOnly": False,
            "applyMethod": "omarchy",
            "selectable": False,
        })
    return entries


def unlock_designs() -> list[dict[str, object]]:
    """Installed logo artwork; colours match the existing Plymouth background."""
    import boot_unlock
    background = boot_unlock.preview_background()
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
            "preview": str(unlock_image), "backgroundColor": background, "license": None,
            "review": "verified-plymouth-artwork", "licenseEvidence": None,
            "provenanceVerified": True, "compatibility": "not-required",
            "developmentOnly": False, "applyMethod": "omarchy", "selectable": True,
            "_logoDigest": digest,
        })
    if default_digest:
        candidates.insert(0, {"id": stable_id("unlock", "default"), "kind": "unlock", "name": "default",
            "displayName": "Default", "source": [str(default_logo)], "preview": str(default_logo),
            "backgroundColor": background, "review": "verified-plymouth-artwork",
            "compatibility": "not-required", "applyMethod": "omarchy", "selectable": True,
            "_logoDigest": default_digest})
    digest_counts: dict[str, int] = {}
    for entry in candidates:
        digest = str(entry.pop("_logoDigest"))
        digest_counts[digest] = digest_counts.get(digest, 0) + 1
        entry["_logoDigest"] = digest
    for entry in candidates:
        digest = str(entry.pop("_logoDigest"))
        if entry["name"] != "default" and (digest_counts[digest] > 1 or digest == default_digest):
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
    from appearance_previews import IconPreviews
    previews = IconPreviews(ICON_DIRS)
    entries = []
    for name in icon_themes():
        sources = [str(base / name) for base in ICON_DIRS if (base / name / "index.theme").is_file()]
        entries.append({
            "id": stable_id("icon", name), "kind": "icon", "name": name,
            "displayName": display_words(name),
            "previewIcons": previews.samples(name),
            "source": sources, "license": None, "review": "metadata-unverified",
            "licenseEvidence": None, "provenanceVerified": False,
            "compatibility": "not-required", "applyMethod": "installed-icon", "selectable": False,
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


def font_family_spacing() -> dict[str, set[str]]:
    """Collect installed faces' spacing metadata for each family and alias."""
    if not shutil.which("fc-list"):
        return {}
    try:
        result = subprocess.run(
            ["fc-list", "--format", "%{family}\t%{spacing}\n"],
            check=True,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    families: dict[str, set[str]] = {}
    for line in result.stdout.splitlines():
        family, _, spacing = line.partition("\t")
        # Fontconfig can return aliases separated by commas.
        for name in (part.strip() for part in family.split(",")):
            if name:
                families.setdefault(name, set()).update(value.strip() for value in spacing.split(","))
    return families


def font_families() -> list[str]:
    return sorted(font_family_spacing(), key=str.casefold)


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
    spacing_by_family = font_family_spacing()
    for name in sorted(spacing_by_family, key=str.casefold):
        # FC_MONO=100 and FC_CHARCELL=110 both use fixed character widths.
        # Unknown or mixed spacing is not a positive monospace classification.
        monospace = spacing_by_family[name] <= {"100", "110"}
        entry = reviewed.get(name)
        if entry is not None:
            # Curated metadata applies only to the exact family currently
            # reported by fontconfig; discovery alone never grants review.
            entries.append({**entry, "id": stable_id("font", name), "kind": "font", "monospace": monospace, "selectable": False})
        else:
            entries.append({
                "id": stable_id("font", name), "kind": "font", "name": name,
                "monospace": monospace,
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


def _global_font_selection() -> dict[str, object]:
    xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", str(HOME / ".config")))
    if not xdg_config.is_absolute():
        xdg_config = HOME / ".config"
    try:
        xdg_config.relative_to(HOME)
    except ValueError:
        return {}
    path = xdg_config / "omarchy-look-and-feel/font-selection.json"
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        return saved if isinstance(saved, dict) and saved.get("schemaVersion") == 1 else {}
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _selected_global_font_id(font_records: list[dict[str, object]], key: str) -> str | None:
    family = _global_font_selection().get(key)
    names = {str(item["name"]) for item in font_records}
    return stable_id("font", family) if isinstance(family, str) and family in names else None


def _selected_global_font_size(key: str) -> int | None:
    size = _global_font_selection().get(key)
    return size if isinstance(size, int) and not isinstance(size, bool) and 6 <= size <= 48 else None


def selected_terminal_font(font_records: list[dict[str, object]]) -> str | None:
    """Read the global saved choice, falling back to the legacy managed value."""
    xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", str(HOME / ".config")))
    if not xdg_config.is_absolute():
        xdg_config = HOME / ".config"
    try:
        xdg_config.relative_to(HOME)
    except ValueError:
        return None
    by_name = {str(item["name"]): str(item["id"]) for item in font_records}
    saved_family = _global_font_selection().get("terminalFontFamily")
    if isinstance(saved_family, str) and saved_family in by_name:
        return stable_id("font", saved_family)
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
    global_size = _selected_global_font_size("terminalFontSizePt")
    if global_size is not None:
        return global_size
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
    import appearance_policy
    policy = appearance_policy.read()
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
    status = action_status()
    import boot_unlock
    status["unlock"].update(boot_unlock.status())
    import icon_actions
    status["icons"] = icon_actions.status()
    import opacity_actions
    status["opacity"] = opacity_actions.status()
    import blur_actions
    status["blur"] = blur_actions.status()
    saved_theme = appearance_policy.latest(appearance_policy.LABEL_THEME)
    if any(row[2].get("label") == appearance_policy.LABEL_THEME for row in appearance_policy.records()):
        status["theme"]["undoAvailable"] = saved_theme is not None
    if saved_theme:
        status["theme"]["undoAvailable"] = True
        status["theme"]["previousValue"] = saved_theme[2]["appearanceContext"]["themeBefore"]
    return {
        "application_configs_modified": False,
        "desiredAppearance": policy,
        "font_application_inventory": font_applications,
        "shell_font_surfaces": shell_fonts,
        "font_application_inventory_record": font_application_record_path,
        "font_application_inventory_record_error": font_application_record_error,
        "preferences": {
            "systemFontId": _selected_global_font_id(fonts, "systemFontFamily"),
            "systemFontSizePt": _selected_global_font_size("systemFontSizePt"),
            "terminalFontId": selected_terminal_font(fonts),
            "terminalFontSizePt": selected_terminal_font_size(),
        },
        "global_font_undo_available": has_committed_transaction(label="Global font settings"),
        "applications": application_inventory(),
        "catalogs": {
            "themes": themes(),
            "unlocks": [entry["name"] for entry in entries["unlocks"]],
            "fonts": [entry["name"] for entry in fonts],
            "icons": icon_themes(),
            "backgrounds": [entry["source"] for entry in entries["backgrounds"]],
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
        "appearance_action_status": status,
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
    from appearance_policy import apply_theme
    return apply_theme(mode, light_name.casefold().replace(" ", "-"), dark_name.casefold().replace(" ", "-"))


def apply_catalog_action(kind: str, entry_id: str) -> dict[str, object]:
    if kind == "icons":
        from icon_actions import apply
        return apply(entry_id)
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
        import boot_unlock
        return boot_unlock.apply(str(entry["name"]), entry["source"][0], action_status()["unlock"].get("observedValue"))
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


def apply_global_fonts(system_font_id: str, system_size: int, terminal_font_id: str, terminal_size: int, *, automatic=False) -> dict[str, object]:
    fonts = {str(entry["id"]): str(entry["name"]) for entry in font_entries()}
    system_family = fonts.get(system_font_id)
    terminal_family = fonts.get(terminal_font_id)
    if not system_family or not terminal_family:
        raise TransactionError("a selected font is no longer available")
    census = installed_font_applications()
    terminal_apps = [app for app in census.get("desktopApplications", []) if isinstance(app, dict)
                     and str(app.get("framework", "")).casefold() == "terminal-emulator"]
    terminal_ids = {str(app.get("id", "")) for app in terminal_apps}
    for app_id in terminal_ids:
        adapter = TERMINAL_COMMANDS.get(app_id)
        if app_id not in TERMINALS or adapter is None:
            raise TransactionError("an installed terminal needs a reviewed font adapter before global Apply")
        if not shutil.which(adapter[0]):
            raise TransactionError("an installed terminal could not be matched to its font adapter executable")
    targets, terminal_count = build_global_font_targets(system_family, system_size, terminal_family, terminal_size, terminal_ids)
    desktop_ids = {str(app.get("id", "")) for app in census.get("desktopApplications", []) if isinstance(app, dict)}
    app_targets, pending = build_app_targets(system_family, system_size, terminal_family, terminal_size, desktop_ids)
    targets.update(app_targets)
    browser_targets, browser_pending = build_browser_targets(system_family, system_size, terminal_family, terminal_size, desktop_ids)
    targets.update(browser_targets)
    pending.extend(browser_pending)
    manual = validated_apply_status(set(targets))
    if manual["unsupportedCount"]:
        return {
            "blocked": True,
            "unsupportedManualCount": manual["unsupportedCount"],
            "registeredManualCount": manual["registeredCount"],
        }
    import appearance_policy as policy
    import desktop_fonts
    values = {"font-name": f"{system_family} {system_size}",
              "document-font-name": f"{system_family} {system_size}",
              "monospace-font-name": f"{terminal_family} {terminal_size}", "text-scaling-factor": 1.0}
    parent = policy.latest(policy.LABEL_FONTS) if automatic else None
    if automatic:
        if parent is None:
            raise TransactionError("saved fonts have no original Apply transaction")
        targets = policy.changed_targets(targets)
        if "brave-default-preferences" in targets:
            del targets["brave-default-preferences"]
            pending.append({"app": "Brave", "action": "apply-when-closed", "reason": "Close Brave and press Apply to update its saved fonts. Its profile has no application-respected external writer lock."})
        snapshot = desktop_fonts.capture(values)
        desktop_changed = any(row["effectiveBefore"] != row["after"] for row in snapshot)
        if desktop_changed and not targets:
            # A stable harmless target lets the existing journal carry a
            # GSettings-only repair without creating a new settings subsystem.
            targets["global-font-selection"] = (HOME / FILE_TARGETS["global-font-selection"]).read_bytes()
    else:
        desktop_changed = True
        targets["appearance-policy"] = policy.update("fonts", {"systemId": system_font_id, "systemSize": system_size,
                                                                "terminalId": terminal_font_id, "terminalSize": terminal_size})
    ownership = {
        'fontconfig-monospace': {'monospace-rule'},
        'wezterm-config': {'fonts'},
        'appearance-policy': {'fonts'},
        'gtk3-settings': {'Settings/gtk-font-name'},
        'gtk4-settings': {'Settings/gtk-font-name'},
        'qt5ct-settings': {'Fonts/general', 'Fonts/fixed'},
        'qt6ct-settings': {'Fonts/general', 'Fonts/fixed'},
        'typora-base-user-css': {'fonts'},
    }
    from terminal_preferences import FONT_FIELDS
    ownership.update(FONT_FIELDS)
    css_path = HOME / FILE_TARGETS['typora-base-user-css']
    if css_path.is_file() and '/* Look & Feel font profile: preserve theme styling while sharing font roles. */' in css_path.read_text():
        ownership['typora-base-user-css'].add('body')
    transaction_id = apply_file_targets(targets, label="Automatic font reconciliation" if automatic else policy.LABEL_FONTS,
                                        desktop_font_values=values if desktop_changed else None,
                                        parent_transaction=parent[1].name if parent else None, owned_fields=ownership) if targets else None
    from terminal_reload import reload_fonts
    reload_status = reload_fonts(set(targets), retry=automatic)
    from browser_font_actions import family_notes
    return {
        "transaction": transaction_id,
        "desktopFontsVerified": True,
        "terminalReload": reload_status,
        "pendingApplications": pending,
        "fontNotes": family_notes(system_family, terminal_family, desktop_ids),
        "targetCount": len(targets),
        "terminalCount": terminal_count,
        "registeredManualCount": manual["registeredCount"],
        "unsupportedManualCount": 0,
    }


def audit_manual_app(query: str) -> dict[str, object]:
    result = inspect_app(query)
    return register_audit_result(query, result)


def write_action_result(result):
    from application_restarts import add_to_result
    json.dump(add_to_result(result), sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")


def main(argv: list[str]) -> int:
    mutation = argv and argv[0] in {"apply-global-fonts", "rollback-global-fonts", "apply-theme", "apply-opacity", "apply-blur", "apply-catalog-action", "rollback-appearance", "recover-unlock", "reconcile"}
    if not mutation:
        return _main(argv)
    import appearance_policy
    try:
        with appearance_policy.operation_lock():
            from managed_preferences import AUTOMATIC
            token = AUTOMATIC.set(argv == ["reconcile"])
            try:
                import requirements
                if argv[0] == "apply-global-fonts":
                    requirements.require('fonts')
                elif argv[0] == "apply-theme":
                    requirements.require('theme')
                elif argv[0] == "apply-opacity" or argv == ["rollback-appearance", "opacity"]:
                    requirements.require('opacity')
                elif argv[:2] == ["apply-catalog-action", "icons"]:
                    requirements.require('icons')
                elif argv[:2] == ["apply-catalog-action", "background"]:
                    requirements.require('background')
                elif argv == ["rollback-global-fonts"]:
                    requirements.require('desktop')
                    requirements.require('font-restore')
                elif argv == ["rollback-appearance", "icons"]:
                    requirements.require('desktop')
                elif argv == ["rollback-appearance", "theme"]:
                    requirements.require('theme')
                elif argv == ["rollback-appearance", "background"]:
                    requirements.require('background')
                elif argv == ["reconcile"]:
                    saved = appearance_policy.read()
                    for area in ('theme', 'fonts', 'icons', 'opacity', 'blur'):
                        if saved.get(area) is not None:
                            requirements.require(area)
                import application_restarts
                application_restarts.observe()
                recover_pending()
                appearance_policy.recover_theme_undos()
                return _main(argv)
            finally:
                AUTOMATIC.reset(token)
    except appearance_policy.OperationBusy as exc:
        if argv == ["reconcile"]:
            print(json.dumps({"schemaVersion": 1, "skipped": "busy"}))
            return 0
        print(str(exc), file=sys.stderr)
        return 1
    except (TransactionError, OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _main(argv: list[str]) -> int:
    if argv == ["recover-unlock"]:
        import boot_unlock
        json.dump(boot_unlock.recover(), sys.stdout)
        sys.stdout.write("\n")
        return 0

    if argv == ["doctor"]:
        import requirements
        result = requirements.inspect()
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0 if result["ready"] else 2

    if argv == ["reconcile"]:
        import appearance_policy
        json.dump(appearance_policy.reconcile(), sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    if len(argv) == 2 and argv[0] == 'apply-opacity':
        from opacity_actions import apply as apply_opacity
        write_action_result(apply_opacity(int(argv[1])))
        return 0

    if len(argv) == 2 and argv[0] == 'apply-blur':
        from blur_actions import apply as apply_blur
        if argv[1] not in {'on', 'off'}:
            raise ValueError('Terminal blur must be On or Off')
        write_action_result(apply_blur(argv[1] == 'on'))
        return 0

    if len(argv) == 5 and argv[0] == "apply-global-fonts":
        try:
            result = apply_global_fonts(argv[1], int(argv[2]), argv[3], int(argv[4]))
        except (TransactionError, ValueError, OSError, RuntimeError) as exc:
            print(f"Global font Apply failed: {exc}", file=sys.stderr)
            return 1
        write_action_result(result)
        return 0
    if argv == ["rollback-global-fonts"]:
        try:
            result = {"rolledBack": rollback_latest(label="Global font settings"),
                      "terminalReload": reload_terminals({"ghostty-config", "kitty-config"})}
        except (TransactionError, RuntimeError, OSError) as exc:
            print(f"Global font Undo failed: {exc}", file=sys.stderr)
            return 1
        write_action_result(result)
        return 0
    if len(argv) == 2 and argv[0] == "appearance-action-status" and argv[1] in {"theme", "background", "unlock"}:
        status = action_status()[argv[1]]
        if argv[1] == "unlock":
            import boot_unlock
            status.update(boot_unlock.status())
        json.dump(status, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if len(argv) == 4 and argv[0] == "apply-theme":
        try:
            result = apply_selected_theme(argv[1], argv[2], argv[3])
        except (TransactionError, OSError, ValueError) as exc:
            print(f"Theme Apply failed: {exc}", file=sys.stderr)
            return 1
        write_action_result(result)
        return 0
    if len(argv) == 3 and argv[0] == "apply-catalog-action":
        try:
            result = apply_catalog_action(argv[1], argv[2])
        except (TransactionError, OSError, ValueError) as exc:
            print(f"Appearance Apply failed: {exc}", file=sys.stderr)
            return 1
        write_action_result(result)
        return 0
    if len(argv) == 2 and argv[0] == "rollback-appearance":
        try:
            if argv[1] == "theme":
                from appearance_policy import undo_theme
                result = undo_theme()
            elif argv[1] == "unlock":
                import boot_unlock
                result = boot_unlock.undo()
            elif argv[1] == "icons":
                from icon_actions import undo
                result = undo()
            elif argv[1] == "opacity":
                from opacity_actions import undo
                result = undo()
            elif argv[1] == "blur":
                from blur_actions import undo
                result = undo()
            else:
                result = rollback_action(argv[1])
        except (TransactionError, OSError, ValueError) as exc:
            print(f"Appearance Undo failed: {exc}", file=sys.stderr)
            return 1
        write_action_result(result)
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
    if len(argv) == 2 and argv[0] == "audit-app":
        try:
            result = audit_manual_app(argv[1])
        except (TransactionError, OSError, ValueError) as exc:
            print(f"App audit could not be saved safely: {exc}", file=sys.stderr)
            return 1
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if argv == ["clear-manual-app-audit"]:
        try:
            clear_manual_app_registry()
        except (TransactionError, OSError, ValueError) as exc:
            print(f"App audit registry could not be cleared safely: {exc}", file=sys.stderr)
            return 1
        json.dump({"cleared": True}, sys.stdout)
        sys.stdout.write("\n")
        return 0
    if argv in (["inventory"], ["panel-inventory"]):
        result = inventory()
        if argv == ["panel-inventory"]:
            import panel_preview_cache
            try:
                panel_preview_cache.save(result)
            except OSError:
                pass  # A read-only/full cache directory must not block live settings.
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
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
            transaction_id = apply_file_targets(ghostty_font_target(str(entry["id"]), str(entry["name"]), font_size), label="Ghostty font",
                                                owned_fields={'ghostty-config': {'font-import'}})
        except (TransactionError, ValueError) as exc:
            print(f"Ghostty font Apply failed: {exc}", file=sys.stderr)
            return 1
        json.dump({"transaction": transaction_id, "font": entry["name"], "sizePt": font_size}, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    print("Usage: controller.py inventory | audit-appearance JSON | transaction {status|recover|rollback}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
