#!/usr/bin/env python3
"""Durable, reversible file transaction core for Omarchy Look & Feel."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import stat
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Mapping


SCHEMA_VERSION = 2
MAX_SETTINGS_BYTES = 256 * 1024
MAX_TARGET_BYTES = 16 * 1024 * 1024
MAX_JOURNAL_BYTES = 2 * 1024 * 1024
KEEP_RECENT_TRANSACTIONS = 20
MIN_RETENTION_SECONDS = 30 * 24 * 60 * 60
TRANSACTION_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$")
TARGET_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")

# Application targets are exact, user-level paths relative to HOME.
# Absolute paths are not accepted by the transaction core.
_configured_home = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
if not _configured_home.is_absolute():
    _configured_home = Path.home() / ".config"
try:
    _configured_home_rel = _configured_home.relative_to(Path.home())
except ValueError:
    _configured_home_rel = Path(".config")
_data_home = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
if not _data_home.is_absolute():
    _data_home = Path.home() / ".local/share"
try:
    _data_home_rel = _data_home.relative_to(Path.home())
except ValueError:
    _data_home_rel = Path(".local/share")
_ghostty_dir = _configured_home / "ghostty"
_ghostty_filename = "config.ghostty" if (_ghostty_dir / "config.ghostty").exists() else "config"
# Follow WezTerm's documented config lookup; the transaction boundary rejects
# symlinks and paths outside this user's home before any read/write.
_wezterm_override = os.environ.get('WEZTERM_CONFIG_FILE')
_wezterm_candidates = [_configured_home / 'wezterm/wezterm.lua', Path.home() / '.config/wezterm/wezterm.lua', Path.home() / '.wezterm.lua']
_wezterm_path = Path(_wezterm_override) if _wezterm_override else next((p for p in _wezterm_candidates if p.exists() or p.is_symlink()), _wezterm_candidates[0])
try:
    _wezterm_rel = _wezterm_path.relative_to(Path.home()).as_posix()
except ValueError:
    # Keep the unsupported override as a boundary violation, never silently
    # edit a different configuration that the application won't load.
    _wezterm_rel = str(_wezterm_path)
FILE_TARGETS: dict[str, str] = {
    "hypr-qt-integration": (_configured_home_rel / "hypr" / "hyprland.lua").as_posix(),
    "ghostty-config": (_configured_home_rel / "ghostty" / _ghostty_filename).as_posix(),
    "ghostty-font-overlay": (_configured_home_rel / "ghostty" / "look-and-feel-font.conf").as_posix(),
    "ghostty-opacity-css": (_configured_home_rel / "ghostty" / "look-and-feel-opacity.css").as_posix(),
    "terminal-blur-config": (_configured_home_rel / "hypr" / "looknfeel.lua").as_posix(),
    "terminal-font-selection": (_configured_home_rel / "ghostty" / "look-and-feel-font-selection.json").as_posix(),
    "gtk3-settings": (_configured_home_rel / "gtk-3.0" / "settings.ini").as_posix(),
    "gtk4-settings": (_configured_home_rel / "gtk-4.0" / "settings.ini").as_posix(),
    "qt5ct-settings": (_configured_home_rel / "qt5ct" / "qt5ct.conf").as_posix(),
    "qt6ct-settings": (_configured_home_rel / "qt6ct" / "qt6ct.conf").as_posix(),
    "fontconfig-monospace": (_configured_home_rel / "fontconfig" / "fonts.conf").as_posix(),
    "omarchy-shell-font": (_configured_home_rel / "omarchy" / "shell-font.json").as_posix(),
    "omarchy-shell-style": (_configured_home_rel / "omarchy" / "shell.toml").as_posix(),
    "global-font-selection": (_configured_home_rel / "omarchy-look-and-feel" / "font-selection.json").as_posix(),
    "alacritty-config": (_configured_home_rel / "alacritty" / "alacritty.toml").as_posix(),
    "kitty-config": (_configured_home_rel / "kitty" / "kitty.conf").as_posix(),
    "foot-config": (_configured_home_rel / "foot" / "foot.ini").as_posix(),
    "wezterm-config": _wezterm_rel,
    "cursor-settings": (_configured_home_rel / "Cursor" / "User" / "settings.json").as_posix(),
    "brave-flags": (_configured_home_rel / "brave-flags.conf").as_posix(),
    "onlyoffice-settings": (_configured_home_rel / "onlyoffice" / "DesktopEditors.conf").as_posix(),
    "onlyoffice-launcher": (_data_home_rel / "applications" / "onlyoffice-desktopeditors.desktop").as_posix(),
    "gtk3-css": (_configured_home_rel / "gtk-3.0" / "gtk.css").as_posix(),
    "gtk4-css": (_configured_home_rel / "gtk-4.0" / "gtk.css").as_posix(),
    "typora-active-css": (_configured_home_rel / "Typora" / "themes" / "look-and-feel.css").as_posix(),
    "appearance-policy": (_configured_home_rel / "omarchy-look-and-feel" / "policy.json").as_posix(),
    "typora-profile": (_configured_home_rel / "Typora" / "profile.data").as_posix(),
    "typora-light-css": (_configured_home_rel / "Typora" / "themes" / "look-and-feel-light.css").as_posix(),
    "typora-dark-css": (_configured_home_rel / "Typora" / "themes" / "look-and-feel-dark.css").as_posix(),
    "qt5ct-colors": (_configured_home_rel / "qt5ct" / "colors" / "look-and-feel.conf").as_posix(),
    "qt6ct-colors": (_configured_home_rel / "qt6ct" / "colors" / "look-and-feel.conf").as_posix(),
    "typora-settings": (_configured_home_rel / "Typora" / "conf" / "conf.user.json").as_posix(),
    "typora-base-user-css": (_configured_home_rel / "Typora" / "themes" / "base.user.css").as_posix(),
    "brave-default-preferences": (_configured_home_rel / "BraveSoftware" / "Brave-Browser" / "Default" / "Preferences").as_posix(),
}
# Profile discovery returns no target when selection is ambiguous.
from mail_font_adapters import writable_betterbird_profile
_betterbird_prefs = writable_betterbird_profile()
if _betterbird_prefs:
    FILE_TARGETS["betterbird-prefs"] = _betterbird_prefs


class TransactionError(RuntimeError):
    """A transaction could not safely complete or recover."""


def _home() -> Path:
    return Path.home().resolve(strict=True)


def _xdg_dir(variable: str, fallback: str) -> Path:
    raw = os.environ.get(variable, "")
    path = Path(raw) if raw else _home() / fallback
    if not path.is_absolute():
        raise TransactionError(f"{variable} must be an absolute path")
    _check_home_destination(path)
    return path


def settings_path() -> Path:
    return _xdg_dir("XDG_CONFIG_HOME", ".config") / "omarchy-look-and-feel" / "settings.json"


def transactions_path() -> Path:
    return _xdg_dir("XDG_STATE_HOME", ".local/state") / "omarchy-look-and-feel" / "transactions"


def _check_home_destination(path: Path) -> Path:
    """Check containment and existing path components without following links."""
    home = _home()
    try:
        relative = path.relative_to(home)
    except ValueError as exc:
        raise TransactionError(f"managed path is outside the home directory: {path}") from exc
    if ".." in relative.parts:
        raise TransactionError(f"managed path contains a parent traversal: {path}")
    current = home
    for part in relative.parts:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise TransactionError(f"managed paths may not contain symlinks: {current}")
        if current != path and not stat.S_ISDIR(info.st_mode):
            raise TransactionError(f"managed parent is not a directory: {current}")
    return path


def _mkdir_private(path: Path) -> None:
    """Create a private directory beneath HOME without following symlinks."""
    _check_home_destination(path)
    relative = path.relative_to(_home())
    current = _home()
    for part in relative.parts:
        current = current / part
        try:
            current.mkdir(mode=0o700)
        except FileExistsError:
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise TransactionError(f"unsafe directory component: {current}")
    os.chmod(path, 0o700)


def _ensure_home_path(path: Path, *, allow_missing_leaf: bool = True,
                      allow_missing_parents: bool = False) -> Path:
    """Reject paths outside HOME, symlink components, and non-regular leaves."""
    home = _home()
    absolute = path if path.is_absolute() else home / path
    try:
        relative = absolute.relative_to(home)
    except ValueError as exc:
        raise TransactionError(f"managed path is outside the home directory: {absolute}") from exc
    if ".." in relative.parts:
        raise TransactionError(f"managed path contains a parent traversal: {absolute}")
    current = home
    parts = relative.parts
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            is_parent = index < len(parts) - 1
            if (is_parent and not allow_missing_parents) or (not is_parent and not allow_missing_leaf):
                raise TransactionError(f"managed path component does not exist: {current}")
            continue
        if stat.S_ISLNK(info.st_mode):
            raise TransactionError(f"managed paths may not contain symlinks: {current}")
        if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise TransactionError(f"managed parent is not a directory: {current}")
        if index == len(parts) - 1 and not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise TransactionError(f"managed target is not a regular file: {current}")
    return absolute


def require_wezterm_location():
    if _wezterm_override and not Path(_wezterm_override).is_absolute():
        raise TransactionError('Relative WEZTERM_CONFIG_FILE is ambiguous; use an absolute configuration path')


def _target_paths(target_contents: Mapping[str, bytes]) -> dict[str, Path]:
    if not target_contents:
        raise TransactionError("no application target is enabled; refusing a settings-only Apply")
    if 'wezterm-config' in target_contents:
        require_wezterm_location()
    unknown = set(target_contents) - set(FILE_TARGETS)
    if unknown:
        raise TransactionError("unregistered application target(s): " + ", ".join(sorted(unknown)))
    paths: dict[str, Path] = {}
    reserved = settings_path()
    for target_id, relative in FILE_TARGETS.items():
        if target_id not in target_contents:
            continue
        if not TARGET_ID_RE.fullmatch(target_id):
            raise TransactionError(f"invalid target ID in allowlist: {target_id}")
        if target_id == "settings":
            raise TransactionError("settings is a reserved transaction target ID")
        rel = Path(relative)
        if rel.is_absolute() or ".." in rel.parts or not rel.parts:
            raise TransactionError(f"invalid relative path in allowlist for {target_id}")
        payload = target_contents[target_id]
        if not isinstance(payload, bytes):
            raise TransactionError(f"target content for {target_id} must be bytes")
        if len(payload) > MAX_TARGET_BYTES:
            raise TransactionError(f"target content for {target_id} exceeds the size limit")
        target_path = _ensure_home_path(_home() / rel, allow_missing_parents=True)
        if target_path.exists() and target_path.is_dir():
            raise TransactionError(f"managed target is not a regular file: {target_path}")
        if target_path == reserved or target_path in paths.values():
            raise TransactionError(f"duplicate or reserved path in target allowlist: {target_id}")
        paths[target_id] = target_path
    return paths


def _create_target_parents(paths: Mapping[str, Path]) -> None:
    """Prepare allowlisted destinations without changing existing permissions."""
    # Validate every destination before creating any directories. The ordinary
    # snapshot/write checks still require these parents to exist afterward.
    for path in paths.values():
        _ensure_home_path(path, allow_missing_parents=True)
        if path.exists() and path.is_dir():
            raise TransactionError(f"managed target is not a regular file: {path}")
    home = _home()
    for path in paths.values():
        current = home
        for part in path.parent.relative_to(home).parts:
            current = current / part
            try:
                current.mkdir(mode=0o700)
            except FileExistsError:
                info = current.lstat()
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                    raise TransactionError(f"unsafe managed directory: {current}")
            else:
                _fsync_dir(current.parent)
        _ensure_home_path(path)


def validate_settings(settings: object) -> dict[str, object]:
    """Validate the version 2 settings contract using only the Python stdlib."""
    if not isinstance(settings, dict):
        raise TransactionError("settings must be a JSON object")
    expected = {"schemaVersion", "typography", "theme", "unlock", "background", "icons"}
    if set(settings) != expected or type(settings.get("schemaVersion")) is not int or settings.get("schemaVersion") != SCHEMA_VERSION:
        raise TransactionError("settings fields or schemaVersion do not match schema version 2")

    typography = settings["typography"]
    if not isinstance(typography, dict) or set(typography) != {"system", "terminal"}:
        raise TransactionError("typography must contain exactly system and terminal")
    for label, face in typography.items():
        if not isinstance(face, dict) or set(face) != {"fontId", "sizePt"}:
            raise TransactionError(f"typography.{label} must contain fontId and sizePt")
        font_id = face["fontId"]
        size = face["sizePt"]
        if font_id is not None and (not isinstance(font_id, str) or not font_id):
            raise TransactionError(f"typography.{label}.fontId must be a non-empty string or null")
        if isinstance(size, bool) or not isinstance(size, (int, float)) or not math.isfinite(size) or not 6 <= size <= 48:
            raise TransactionError(f"typography.{label}.sizePt must be between 6 and 48")

    theme = settings["theme"]
    if not isinstance(theme, dict) or set(theme) != {"mode", "light", "dark"}:
        raise TransactionError("theme must contain mode, light, and dark")
    if not isinstance(theme["mode"], str) or theme["mode"] not in {"light", "dark", "automatic"}:
        raise TransactionError("theme.mode must be light, dark, or automatic")
    for key in ("light", "dark"):
        if theme[key] is not None and (not isinstance(theme[key], str) or not theme[key]):
            raise TransactionError(f"theme.{key} must be a non-empty string or null")

    for key in ("unlock", "background", "icons"):
        value = settings[key]
        if value is not None and (not isinstance(value, str) or not value):
            raise TransactionError(f"{key} must be a non-empty string or null")

    if theme["mode"] == "automatic" and (theme["light"] is None or theme["dark"] is None):
        raise TransactionError("automatic mode requires both themes")

    return settings


def validate_for_apply(settings: object, catalog_ids: Mapping[str, set[str]]) -> dict[str, object]:
    """Require complete, currently available selections before any writes."""
    validated = validate_settings(settings)
    required = {
        "fonts": [validated["typography"]["system"]["fontId"], validated["typography"]["terminal"]["fontId"]],
        "themes": [validated["theme"]["light"], validated["theme"]["dark"]]
        if validated["theme"]["mode"] == "automatic"
        else [validated["theme"][validated["theme"]["mode"]]],
        "backgrounds": [validated["background"]],
        "icons": [validated["icons"]],
    }
    if validated["unlock"] is not None:
        required["unlocks"] = [validated["unlock"]]
    for catalog, selected in required.items():
        available = catalog_ids.get(catalog)
        if not isinstance(available, set):
            raise TransactionError(f"current {catalog} catalog IDs were not provided")
        if any(not isinstance(item, str) or not item for item in selected):
            raise TransactionError(f"select an available {catalog} item before Apply")
        missing = [item for item in selected if item not in available]
        if missing:
            raise TransactionError(f"selected {catalog} item is no longer available: {', '.join(missing)}")
    return validated


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fsync_dir(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write(path: Path, payload: bytes, mode: int) -> None:
    from managed_preferences import guard_paths
    guard_paths([path])
    if path.name == "Preferences" and str(path.relative_to(_home())) == FILE_TARGETS.get("brave-default-preferences"):
        from browser_font_actions import assert_closed_default
        assert_closed_default(path)
    parent = path.parent
    if not parent.is_dir():
        raise TransactionError(f"target parent directory does not exist: {parent}")
    fd, temporary = tempfile.mkstemp(prefix=".omlf-", dir=parent)
    try:
        os.fchmod(fd, mode & 0o777)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_dir(parent)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _write_journal(path: Path, journal: dict[str, object]) -> None:
    payload = json.dumps(journal, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(payload) > MAX_JOURNAL_BYTES:
        raise TransactionError("transaction journal exceeds the size limit")
    _atomic_write(path, payload, 0o600)


def _snapshot(path: Path, snapshot_dir: Path, snapshot_name: str) -> dict[str, object]:
    _ensure_home_path(path)
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return {"exists": False, "mode": None, "sha256": None, "snapshot": None}
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise TransactionError(f"only regular files can be managed: {path}")
        if info.st_uid != os.getuid():
            raise TransactionError(f"refusing to replace a file not owned by the current user: {path}")
        data = source.read(MAX_TARGET_BYTES + 1)
    if stat.S_IMODE(info.st_mode) & ~0o777:
        raise TransactionError(f"refusing a target with special permission bits: {path}")
    if len(data) > MAX_TARGET_BYTES:
        raise TransactionError(f"refusing to snapshot a file larger than {MAX_TARGET_BYTES} bytes: {path}")
    target = snapshot_dir / snapshot_name
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {"exists": True, "mode": stat.S_IMODE(info.st_mode), "sha256": _sha256(data), "snapshot": snapshot_name}


def _current_file_state(path: Path) -> dict[str, object]:
    """Read a regular file without following a symlink, or report absence."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return {"exists": False, "mode": None, "sha256": None}
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise TransactionError(f"managed target stopped being a regular file: {path}")
        data = stream.read(MAX_TARGET_BYTES + 1)
    if len(data) > MAX_TARGET_BYTES:
        raise TransactionError(f"managed target exceeds the size limit: {path}")
    return {"exists": True, "mode": stat.S_IMODE(info.st_mode), "sha256": _sha256(data)}


def _same_saved_state(current: dict[str, object], saved: dict[str, object]) -> bool:
    return (
        current.get("exists") == saved.get("exists")
        and current.get("mode") == saved.get("mode")
        and current.get("sha256") == saved.get("sha256")
    )


def _assert_unchanged(path: Path, saved: dict[str, object]) -> None:
    current = _current_file_state(path)
    if not _same_saved_state(current, saved):
        raise TransactionError(f"target changed after its snapshot; preserving the external change: {path}")


def _restore(path: Path, transaction_dir: Path, snapshot: dict[str, object]) -> None:
    checked = _ensure_home_path(path)
    if snapshot["exists"] is False:
        try:
            info = checked.lstat()
        except FileNotFoundError:
            return
        if not stat.S_ISREG(info.st_mode):
            raise TransactionError(f"cannot remove non-regular managed target: {checked}")
        checked.unlink()
        _fsync_dir(checked.parent)
        if checked.exists():
            raise TransactionError(f"restore verification failed; target still exists: {checked}")
        return
    name = snapshot.get("snapshot")
    if not isinstance(name, str) or Path(name).name != name:
        raise TransactionError("invalid snapshot reference in journal")
    source = transaction_dir / "before" / name
    _ensure_home_path(source, allow_missing_leaf=False)
    data = source.read_bytes()
    if _sha256(data) != snapshot.get("sha256"):
        raise TransactionError(f"snapshot integrity check failed for {checked}")
    mode = snapshot.get("mode")
    if isinstance(mode, bool) or not isinstance(mode, int) or mode & ~0o777:
        raise TransactionError(f"invalid saved file mode for {checked}")
    _atomic_write(checked, data, mode)
    if _sha256(checked.read_bytes()) != snapshot.get("sha256") or stat.S_IMODE(checked.stat().st_mode) != mode:
        raise TransactionError(f"restore verification failed for {checked}")


def _load_journal(transaction_dir: Path) -> dict[str, object]:
    path = transaction_dir / "transaction.json"
    raw = path.read_bytes()
    if len(raw) > MAX_JOURNAL_BYTES:
        raise TransactionError(f"journal too large: {path}")
    journal = json.loads(raw)
    if (
        not isinstance(journal, dict)
        or type(journal.get("schemaVersion")) is not int
        or journal.get("schemaVersion") != 1
        or journal.get("id") != transaction_dir.name
        or journal.get("state") not in {"prepared", "applying", "committed", "rolling_back", "rolled_back", "recovery_required"}
    ):
        raise TransactionError(f"invalid transaction journal: {path}")
    return journal


def _journal_targets(journal: dict[str, object]) -> list[dict[str, object]]:
    targets = journal.get("targets")
    if not isinstance(targets, list):
        raise TransactionError("transaction journal has no target list")
    parsed: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for item in targets:
        required = {"id", "relativePath", "before"}
        optional = {"appliedSha256", "appliedMode", "mailFontsAfter", "browserFontsAfter", "managedEdits"}
        if not isinstance(item, dict) or not required.issubset(item) or set(item) - required - optional:
            raise TransactionError("invalid target entry in transaction journal")
        target_id, relative = item["id"], item["relativePath"]
        if not isinstance(target_id, str) or not isinstance(relative, str):
            raise TransactionError("invalid target identity in transaction journal")
        if target_id in seen_ids:
            raise TransactionError("duplicate target ID in transaction journal")
        seen_ids.add(target_id)
        before = item["before"]
        if not isinstance(before, dict) or set(before) != {"exists", "mode", "sha256", "snapshot"}:
            raise TransactionError("invalid snapshot metadata in transaction journal")
        if type(before["exists"]) is not bool:
            raise TransactionError("invalid snapshot existence flag in transaction journal")
        if before["exists"]:
            mode, digest, snapshot_name = before["mode"], before["sha256"], before["snapshot"]
            if isinstance(mode, bool) or not isinstance(mode, int) or mode & ~0o777:
                raise TransactionError("invalid snapshot mode in transaction journal")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise TransactionError("invalid snapshot hash in transaction journal")
            if not isinstance(snapshot_name, str) or Path(snapshot_name).name != snapshot_name:
                raise TransactionError("invalid snapshot filename in transaction journal")
        elif any(before[key] is not None for key in ("mode", "sha256", "snapshot")):
            raise TransactionError("absent snapshot has unexpected metadata")
        if "appliedSha256" in item and (
            not isinstance(item["appliedSha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", item["appliedSha256"])
        ):
            raise TransactionError("invalid applied hash in transaction journal")
        if "appliedMode" in item and (
            isinstance(item["appliedMode"], bool)
            or not isinstance(item["appliedMode"], int)
            or item["appliedMode"] & ~0o777
        ):
            raise TransactionError("invalid applied mode in transaction journal")
        if target_id != "settings" and FILE_TARGETS.get(target_id) != relative and not _historical_mail_target(target_id, relative) and not (target_id == "wezterm-config" and relative in {".wezterm.lua", ".config/wezterm/wezterm.lua", (_configured_home_rel / "wezterm/wezterm.lua").as_posix()}):
            raise TransactionError(f"journal target is no longer in the allowlist: {target_id}")
        if target_id == "settings" and relative != str(settings_path().relative_to(_home())):
            raise TransactionError("settings path changed since the transaction was prepared")
        if "mailFontsAfter" in item:
            if target_id != "betterbird-prefs":
                raise TransactionError("mail font metadata on an unrelated target")
            from app_font_actions import validate_mail_font_values
            validate_mail_font_values(item["mailFontsAfter"])
        if "browserFontsAfter" in item:
            if target_id != "brave-default-preferences":
                raise TransactionError("browser font metadata on an unrelated target")
            from browser_font_actions import validate
            validate(item["browserFontsAfter"])
        if "managedEdits" in item:
            from managed_preferences import validate_edits
            validate_edits(target_id, item["managedEdits"])
        parsed.append(item)
    if "settings" in seen_ids and sum(item["id"] == "settings" for item in parsed) != 1:
        raise TransactionError("transaction journal must contain exactly one settings snapshot")
    if not parsed:
        raise TransactionError("transaction journal must contain at least one target")
    return parsed


def _historical_mail_target(target_id: str, relative: str) -> bool:
    """Keep legacy Betterbird snapshots rollback-eligible without allowing new targets."""
    if target_id != "betterbird-prefs":
        return False
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts or rel.parts[-1] != "prefs.js":
        return False
    if any(part in {"", "."} for part in rel.parts):
        return False
    profile_root = (".thunderbird",) if rel.parts[0] == ".thunderbird" else (".mozilla", "thunderbird")
    return rel.parts[:len(profile_root)] == profile_root and len(rel.parts) > len(profile_root) + 1


def _require_qt_restore(transaction_dir, journal, snapshot_sources=None):
    """Do not put known-invalid saved Qt fonts back into a fresh desktop.

    Inspect only fields the actual restore branch will replace. Icon/palette
    Undo therefore remains available when its untouched font fields are bad.
    The caller invokes this before recording intent or writing any target.
    """
    from managed_preferences import decode
    for item in _journal_targets(journal):
        if item['id'] not in {'qt5ct-settings', 'qt6ct-settings'}:
            continue
        changes = item.get('managedEdits')
        fields = {'Fonts/general', 'Fonts/fixed'}
        if changes is not None:
            fields &= changes.keys()
            if not fields:
                continue
        target = _ensure_home_path(_home() / item['relativePath'])
        current = _current_file_state(target)
        before = item['before']
        if _same_saved_state(current, before):
            continue
        merging = changes is not None and (current.get('sha256') != item.get('appliedSha256')
                                           or item['id'] in journal.get('groupTouched', []))
        try:
            if merging:
                values = [changes[field]['before'][0] for field in fields if changes[field]['before']]
            elif before['exists']:
                snapshot = (snapshot_sources or {}).get(item['id'], transaction_dir / 'before' / before['snapshot'])
                raw = _ensure_home_path(snapshot, allow_missing_leaf=False).read_bytes()
                if _sha256(raw) != before['sha256']:
                    raise TransactionError('Qt font snapshot integrity check failed')
                old = decode(item['id'], raw)
                values = [old[field] for field in fields if field in old]
            else:
                values = []
            if values:
                from global_font_actions import _parse_qt_font
                version = 5 if item['id'] == 'qt5ct-settings' else 6
                if any(not isinstance(value, str) or _parse_qt_font(value, version) is None for value in values):
                    raise ValueError('invalid saved QFont fields')
        except (ValueError, OSError) as exc:
            raise TransactionError(
                f"Undo/recovery stopped: {item['id']} has a malformed saved font. "
                f"Keep the repaired fonts and review {transaction_dir / 'transaction.json'} "
                "before retrying; no restore files were changed.") from exc


def _require_restore(journal, *, check_qt=True):
    # Recovery can also be invoked directly, outside the controller preflight.
    # Missing infrastructure must not cause a predictable partial restoration.
    if "desktopFonts" in journal:
        import desktop_fonts
        desktop_fonts.validate(journal["desktopFonts"])
        try:
            desktop_fonts._settings()
        except (ImportError, ValueError, RuntimeError) as exc:
            raise TransactionError('Desktop recovery needs python-gobject and gsettings-desktop-schemas.') from exc
    if journal.get("themeUndoPending"):
        import requirements
        try:
            requirements.require('theme')
        except RuntimeError as exc:
            raise TransactionError(str(exc)) from exc
    if check_qt:
        _require_qt_restore(transactions_path() / journal['id'], journal)


def _restore_transaction(transaction_dir: Path, journal: dict[str, object]) -> None:
    _require_restore(journal)
    from app_font_actions import lock_mail_paths
    paths = [_ensure_home_path(_home() / str(row["relativePath"])) for row in _journal_targets(journal)]
    from browser_font_actions import lock_paths
    from managed_preferences import guard_paths
    guard_paths(paths)
    with lock_mail_paths(paths), lock_paths(paths):
        journal["state"] = "rolling_back"
        journal["updatedAt"] = datetime.now(timezone.utc).isoformat()
        _write_journal(transaction_dir / "transaction.json", journal)
        entries = _journal_targets(journal)
        errors: list[str] = []
        if "desktopFonts" in journal:
            try:
                import desktop_fonts
                desktop_fonts.restore(journal["desktopFonts"])
            except Exception as exc:
                errors.append(f"desktop fonts: {exc}")
        for item in reversed(entries):
            try:
                target = _ensure_home_path(_home() / str(item["relativePath"]))
                before = item["before"]
                if not isinstance(before, dict):
                    raise TransactionError("invalid target snapshot record")
                current = _current_file_state(target)
                if _same_saved_state(current, before):
                    continue
                if "managedEdits" in item and (current.get("sha256") != item.get("appliedSha256") or item["id"] in journal.get("groupTouched", [])):
                    from managed_preferences import restore
                    restored = restore(item["id"], target.read_bytes(), item["managedEdits"])
                    _assert_unchanged(target, current)
                    _atomic_write(target, restored, current["mode"])
                    if target.read_bytes() != restored:
                        raise TransactionError("managed preference restoration readback failed")
                    continue
                if "mailFontsAfter" in item and (current.get("sha256") != item.get("appliedSha256") or item["id"] in journal.get("groupTouched", [])):
                    from app_font_actions import mail_font_values, merge_mail_fonts
                    name = before.get("snapshot")
                    if not before.get("exists") or not isinstance(name, str):
                        raise TransactionError("mail preference snapshot is missing")
                    snapshot = _ensure_home_path(transaction_dir / "before" / name, allow_missing_leaf=False)
                    prior = snapshot.read_bytes()
                    if _sha256(prior) != before["sha256"]:
                        raise TransactionError("mail font snapshot integrity check failed")
                    old_values = mail_font_values(prior.decode("utf-8"))
                    live = target.read_bytes()
                    current_values = mail_font_values(live.decode("utf-8"))
                    if any(current_values[key] not in (old_values[key], item["mailFontsAfter"][key]) for key in old_values):
                        raise TransactionError("mail fonts changed independently; preserving them")
                    restored = merge_mail_fonts(live.decode("utf-8"), old_values).encode()
                    _assert_unchanged(target, current)
                    _atomic_write(target, restored, current["mode"])
                    if mail_font_values(target.read_text()) != old_values:
                        raise TransactionError("mail font restoration readback failed")
                    continue
                if "browserFontsAfter" in item and (current.get("sha256") != item.get("appliedSha256") or item["id"] in journal.get("groupTouched", [])):
                    from browser_font_actions import values, merge
                    name = before.get("snapshot")
                    if not before.get("exists") or not isinstance(name, str):
                        raise TransactionError("browser preference snapshot is missing")
                    snapshot = _ensure_home_path(transaction_dir / "before" / name, allow_missing_leaf=False)
                    prior = snapshot.read_bytes()
                    if _sha256(prior) != before["sha256"]:
                        raise TransactionError("browser font snapshot integrity check failed")
                    old_values = values(json.loads(prior))
                    live = json.loads(target.read_bytes())
                    current_values = values(live)
                    if any(current_values[key] not in (old_values[key], item["browserFontsAfter"][key]) for key in old_values):
                        raise TransactionError("browser fonts changed independently; preserving them")
                    restored = (json.dumps(merge(live, old_values), ensure_ascii=False, separators=(",", ":")) + "\n").encode()
                    _assert_unchanged(target, current)
                    _atomic_write(target, restored, current["mode"])
                    if values(json.loads(target.read_bytes())) != old_values:
                        raise TransactionError("browser font restoration readback failed")
                    continue
                expected_hash = item.get("appliedSha256")
                expected_mode = item.get("appliedMode")
                if (
                    not isinstance(expected_hash, str)
                    or current.get("sha256") != expected_hash
                    or current.get("mode") != expected_mode
                ):
                    raise TransactionError(f"target changed independently; preserving it for manual recovery: {target}")
                _restore(target, transaction_dir, before)
            except Exception as exc:  # Keep restoring the remaining targets.
                errors.append(f"{item.get('id')}: {exc}")
        journal["updatedAt"] = datetime.now(timezone.utc).isoformat()
        if errors:
            journal["state"] = "recovery_required"
            journal["recoveryErrors"] = errors
            _write_journal(transaction_dir / "transaction.json", journal)
            raise TransactionError("rollback incomplete; recovery required: " + "; ".join(errors))
        journal["state"] = "rolled_back"
        journal.pop("recoveryErrors", None)
        _write_journal(transaction_dir / "transaction.json", journal)


@contextmanager
def _locked(transactions_dir: Path) -> Iterator[None]:
    _mkdir_private(transactions_dir)
    lock_path = transactions_dir / ".lock"
    _ensure_home_path(lock_path)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    os.fchmod(fd, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise TransactionError("another apply or rollback operation is in progress") from exc
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _pending_transactions(transactions_dir: Path) -> list[Path]:
    pending: list[Path] = []
    if not transactions_dir.is_dir():
        return pending
    for candidate in transactions_dir.iterdir():
        if candidate.is_symlink() or not candidate.is_dir() or not TRANSACTION_ID_RE.fullmatch(candidate.name):
            continue
        journal_file = candidate / "transaction.json"
        if not journal_file.exists():
            # The journal is written before the first managed target changes.
            # An incomplete snapshot-only directory is therefore safe to drop.
            shutil.rmtree(candidate)
            continue
        journal = _load_journal(candidate)
        if journal.get("state") in {"prepared", "applying", "rolling_back", "recovery_required"}:
            pending.append(candidate)
    return sorted(pending)


def recover_pending() -> list[str]:
    """Roll back interrupted or previously incomplete transactions."""
    directory = transactions_path()
    _check_home_destination(directory)
    if not directory.exists():
        return []
    with _locked(directory):
        recovered: list[str] = _recover_group_undos(directory)
        for transaction_dir in _pending_transactions(directory):
            journal = _load_journal(transaction_dir)
            _restore_transaction(transaction_dir, journal)
            recovered.append(transaction_dir.name)
        return recovered


def apply_settings(settings: object, target_contents: Mapping[str, bytes], catalog_ids: Mapping[str, set[str]]) -> str:
    """Apply registered file targets and commit canonical settings last.

    Target IDs must be present in FILE_TARGETS. As shipped, that allowlist is
    empty, so an Apply attempt is rejected before any files are created.
    """
    validated = validate_for_apply(settings, catalog_ids)
    paths = _target_paths(target_contents)
    config_file = settings_path()
    encoded_settings = (json.dumps(validated, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if len(encoded_settings) > MAX_SETTINGS_BYTES:
        raise TransactionError("settings document exceeds the size limit")

    directory = transactions_path()
    with _locked(directory):
        recovered_before_apply: list[str] = []
        for pending_dir in _pending_transactions(directory):
            pending_journal = _load_journal(pending_dir)
            _restore_transaction(pending_dir, pending_journal)
            recovered_before_apply.append(pending_dir.name)
        _create_target_parents(paths)
        _mkdir_private(config_file.parent)
        _ensure_home_path(config_file)
        transaction_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
        transaction_dir = directory / transaction_id
        transaction_dir.mkdir(mode=0o700)
        before_dir = transaction_dir / "before"
        before_dir.mkdir(mode=0o700)
        entries: list[dict[str, object]] = []
        all_targets = {"settings": config_file, **paths}
        try:
            for target_id, path in all_targets.items():
                relative = str(path.relative_to(_home()))
                snapshot = _snapshot(path, before_dir, target_id + ".before")
                entries.append({"id": target_id, "relativePath": relative, "before": snapshot})
            _fsync_dir(before_dir)
            journal: dict[str, object] = {
                "schemaVersion": 1,
                "id": transaction_id,
                "state": "prepared",
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat(),
                "settingsSha256": _sha256(encoded_settings),
                "targets": entries,
                "recoveredBeforeApply": recovered_before_apply,
            }
            _write_journal(transaction_dir / "transaction.json", journal)
            _fsync_dir(transaction_dir)
        except BaseException:
            shutil.rmtree(transaction_dir, ignore_errors=True)
            raise

        try:
            journal["state"] = "applying"
            _write_journal(transaction_dir / "transaction.json", journal)
            for target_id, payload in target_contents.items():
                path = paths[target_id]
                _ensure_home_path(path)
                entry = next(item for item in entries if item["id"] == target_id)
                before = entry["before"]
                if not isinstance(before, dict):
                    raise TransactionError(f"invalid target snapshot for {target_id}")
                _assert_unchanged(path, before)
                old_mode = before["mode"] if before["exists"] else 0o600
                entry["appliedSha256"] = _sha256(payload)
                entry["appliedMode"] = old_mode
                journal["currentTarget"] = target_id
                _write_journal(transaction_dir / "transaction.json", journal)
                _atomic_write(path, payload, old_mode)
                state = _current_file_state(path)
                if state.get("sha256") != _sha256(payload) or state.get("mode") != old_mode:
                    raise TransactionError(f"readback mismatch for target {target_id}")
                del journal["currentTarget"]
                journal["updatedAt"] = datetime.now(timezone.utc).isoformat()
                _write_journal(transaction_dir / "transaction.json", journal)

            settings_entry = next(item for item in entries if item["id"] == "settings")
            settings_before = settings_entry["before"]
            if not isinstance(settings_before, dict):
                raise TransactionError("invalid canonical settings snapshot")
            _assert_unchanged(config_file, settings_before)
            settings_entry["appliedSha256"] = _sha256(encoded_settings)
            settings_entry["appliedMode"] = 0o600
            journal["currentTarget"] = "settings"
            _write_journal(transaction_dir / "transaction.json", journal)
            _atomic_write(config_file, encoded_settings, 0o600)
            settings_state = _current_file_state(config_file)
            if settings_state.get("sha256") != _sha256(encoded_settings) or settings_state.get("mode") != 0o600:
                raise TransactionError("canonical settings readback mismatch")
            del journal["currentTarget"]
            journal["state"] = "committed"
            journal["committedAt"] = datetime.now(timezone.utc).isoformat()
            journal["updatedAt"] = journal["committedAt"]
            _write_journal(transaction_dir / "transaction.json", journal)
        except BaseException as exc:
            try:
                _restore_transaction(transaction_dir, journal)
            except Exception as rollback_exc:
                raise TransactionError(f"Apply failed ({exc}); {rollback_exc}") from exc
            raise TransactionError(f"Apply failed and was rolled back: {exc}") from exc

        # Retention is housekeeping. A pruning problem must never turn a
        # verified, committed Apply into a rollback of the user's new choice.
        try:
            _prune_committed(directory)
        except Exception as exc:
            journal["maintenanceWarning"] = f"snapshot pruning was deferred: {exc}"
            try:
                _write_journal(transaction_dir / "transaction.json", journal)
            except Exception:
                pass
        return transaction_id


def apply_file_targets(target_contents: Mapping[str, bytes], *, label: str,
                       desktop_font_values: Mapping[str, str | float] | None = None,
                       parent_transaction: str | None = None,
                       appearance_context: dict | None = None,
                       owned_fields: Mapping[str, set[str]] | None = None) -> str:
    """Apply only declared application files, with durable snapshots and rollback."""
    paths = _target_paths(target_contents)
    directory = transactions_path()
    if parent_transaction is not None and not TRANSACTION_ID_RE.fullmatch(parent_transaction):
        raise TransactionError("invalid parent transaction")
    if appearance_context is not None:
        if not isinstance(appearance_context, dict) or set(appearance_context) != {"themeBefore", "themeAfter"} or any(
                not isinstance(v, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", v) for v in appearance_context.values()):
            raise TransactionError("invalid appearance operation context")
    from managed_preferences import guard_paths
    guard_paths(paths.values())
    from app_font_actions import lock_mail_paths
    from browser_font_actions import lock_paths
    with _locked(directory), lock_mail_paths(paths.values()), lock_paths(paths.values()):
        _recover_group_undos(directory)
        recovered_before_apply: list[str] = []
        for pending_dir in _pending_transactions(directory):
            pending_journal = _load_journal(pending_dir)
            _restore_transaction(pending_dir, pending_journal)
            recovered_before_apply.append(pending_dir.name)
        _recover_group_undos(directory)
        from managed_preferences import FIELDS, decode, encode
        if owned_fields is not None:
            for name, fields in owned_fields.items():
                if name not in FIELDS or not isinstance(fields, set) or fields - FIELDS[name]:
                    raise TransactionError("invalid owned preference fields")
        target_contents = dict(target_contents)
        for target_id in set(target_contents) & set(FIELDS):
            path = paths[target_id]
            if path.exists():
                current = decode(target_id, path.read_bytes())
                wanted = decode(target_id, target_contents[target_id])
                for key in (owned_fields or {}).get(target_id, FIELDS[target_id]):
                    if key in wanted:
                        current[key] = wanted[key]
                    else:
                        current.pop(key, None)
                target_contents[target_id] = encode(target_id, current)
        _target_paths(target_contents)
        if "betterbird-prefs" in target_contents:
            from app_font_actions import mail_font_values, merge_mail_fonts
            target_contents = dict(target_contents)
            wanted = mail_font_values(target_contents["betterbird-prefs"].decode("utf-8"))
            current_mail = paths["betterbird-prefs"].read_text(encoding="utf-8")
            target_contents["betterbird-prefs"] = merge_mail_fonts(current_mail, wanted).encode()
            _target_paths(target_contents)  # Recheck size/path limits after the fresh merge.
        if "brave-default-preferences" in target_contents:
            from browser_font_actions import values, merge
            target_contents = dict(target_contents)
            wanted = values(json.loads(target_contents["brave-default-preferences"]))
            current_browser = json.loads(paths["brave-default-preferences"].read_text())
            target_contents["brave-default-preferences"] = (json.dumps(merge(current_browser, wanted), ensure_ascii=False, separators=(",", ":")) + "\n").encode()
            _target_paths(target_contents)
        desktop_snapshot = None
        if desktop_font_values is not None:
            import desktop_fonts
            desktop_snapshot = desktop_fonts.capture(desktop_font_values)
        _create_target_parents(paths)
        _mkdir_private(directory)
        transaction_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
        transaction_dir = directory / transaction_id
        transaction_dir.mkdir(mode=0o700)
        before_dir = transaction_dir / "before"
        before_dir.mkdir(mode=0o700)
        entries: list[dict[str, object]] = []
        try:
            for target_id, path in paths.items():
                snapshot = _snapshot(path, before_dir, target_id + ".before")
                entries.append({"id": target_id, "relativePath": str(path.relative_to(_home())), "before": snapshot})
            _fsync_dir(before_dir)
            journal: dict[str, object] = {
                "schemaVersion": 1, "id": transaction_id, "state": "prepared",
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat(),
                "label": label[:80], "targets": entries,
                "recoveredBeforeApply": recovered_before_apply,
            }
            if appearance_context is not None:
                journal["appearanceContext"] = appearance_context
            if parent_transaction is not None:
                parent_journal = _load_journal(directory / parent_transaction)
                if parent_journal["state"] != "committed" or parent_journal.get("parentTransaction"):
                    raise TransactionError("automatic reconciliation has no committed parent")
                journal["parentTransaction"] = parent_transaction
            if desktop_snapshot is not None:
                journal["desktopFonts"] = desktop_snapshot
            _write_journal(transaction_dir / "transaction.json", journal)
            _fsync_dir(transaction_dir)
        except BaseException:
            shutil.rmtree(transaction_dir, ignore_errors=True)
            raise

        try:
            journal["state"] = "applying"
            _write_journal(transaction_dir / "transaction.json", journal)
            for target_id, payload in target_contents.items():
                path = paths[target_id]
                entry = next(item for item in entries if item["id"] == target_id)
                before = entry["before"]
                if not isinstance(before, dict):
                    raise TransactionError(f"invalid target snapshot for {target_id}")
                _ensure_home_path(path)
                _assert_unchanged(path, before)
                old_mode = before["mode"] if before["exists"] else 0o600
                entry["appliedSha256"] = _sha256(payload)
                entry["appliedMode"] = old_mode
                from managed_preferences import FIELDS, edits
                if target_id in FIELDS:
                    prior = (transaction_dir / "before" / before["snapshot"]).read_bytes() if before["exists"] else None
                    entry["managedEdits"] = edits(target_id, prior, payload,
                                                  owned_fields=(owned_fields or {}).get(target_id, FIELDS[target_id]))
                if target_id == "betterbird-prefs":
                    from app_font_actions import mail_font_values
                    entry["mailFontsAfter"] = mail_font_values(payload.decode("utf-8"))
                if target_id == "brave-default-preferences":
                    from browser_font_actions import values
                    entry["browserFontsAfter"] = values(json.loads(payload))
                journal["currentTarget"] = target_id
                _write_journal(transaction_dir / "transaction.json", journal)
                _atomic_write(path, payload, old_mode)
                state = _current_file_state(path)
                if state.get("sha256") != _sha256(payload) or state.get("mode") != old_mode:
                    raise TransactionError(f"readback mismatch for target {target_id}")
                del journal["currentTarget"]
                journal["updatedAt"] = datetime.now(timezone.utc).isoformat()
                _write_journal(transaction_dir / "transaction.json", journal)
            if desktop_snapshot is not None:
                import desktop_fonts
                desktop_fonts.apply(desktop_snapshot)
            if "brave-default-preferences" in paths:
                from browser_font_actions import assert_closed_default
                assert_closed_default(paths["brave-default-preferences"])
            guard_paths(paths.values())
            journal["state"] = "committed"
            journal["committedAt"] = datetime.now(timezone.utc).isoformat()
            journal["updatedAt"] = journal["committedAt"]
            _write_journal(transaction_dir / "transaction.json", journal)
        except BaseException as exc:
            try:
                _restore_transaction(transaction_dir, journal)
            except Exception as rollback_exc:
                journal["state"] = "recovery_required"
                journal["recoveryErrors"] = [str(rollback_exc)[:1000]]
                try:
                    _write_journal(transaction_dir / "transaction.json", journal)
                except Exception:
                    pass
                raise TransactionError(f"Apply failed ({exc}); {rollback_exc}") from exc
            raise TransactionError(f"Apply failed and was rolled back: {exc}") from exc
        try:
            _prune_committed(directory)
        except Exception as exc:
            journal["maintenanceWarning"] = f"snapshot pruning was deferred: {exc}"
            try:
                _write_journal(transaction_dir / "transaction.json", journal)
            except Exception:
                pass
        return transaction_id


def rollback_latest(*, label: str | None = None) -> str:
    """Restore the snapshots from the newest committed transaction."""
    directory = transactions_path()
    _check_home_destination(directory)
    if not directory.exists():
        raise TransactionError("there is no committed transaction to roll back")
    with _locked(directory):
        pending = _pending_transactions(directory)
        if pending:
            raise TransactionError("recover pending transactions before user rollback")
        committed: list[tuple[float, Path]] = []
        for candidate in directory.iterdir():
            if candidate.is_symlink() or not candidate.is_dir() or not TRANSACTION_ID_RE.fullmatch(candidate.name):
                continue
            journal = _load_journal(candidate)
            if journal.get("state") == "committed" and (label is None or journal.get("label") == label):
                committed.append((candidate.stat().st_mtime, candidate))
        if not committed:
            raise TransactionError("there is no committed transaction to roll back")
        _, transaction_dir = max(committed, key=lambda item: item[0])
        journal = _load_journal(transaction_dir)
        _restore_group(directory, transaction_dir, journal)
        try:
            _prune_committed(directory)
        except Exception:
            pass
        return transaction_dir.name


def _prepare_group_undo(directory, transaction_dir, journal):
    """Preflight a group before recording Undo intent or changing app files."""
    if journal.get("groupUndoPrepared"):
        return
    children = []
    for candidate in directory.iterdir():
        if candidate.is_symlink() or not candidate.is_dir() or not TRANSACTION_ID_RE.fullmatch(candidate.name):
            continue
        if not (candidate / "transaction.json").exists():
            continue
        child = _load_journal(candidate)
        if child.get("parentTransaction") == transaction_dir.name and child["state"] == "committed":
            children.append((child.get("createdAt", ""), candidate, child))
    _require_restore(journal, check_qt=False)
    for _, _, child in children:
        _require_restore(child, check_qt=False)
    import copy
    merged = {row["id"]: copy.deepcopy(row) for row in _journal_targets(journal)}
    desktop_merged = {row["key"]: copy.deepcopy(row) for row in journal.get("desktopFonts", [])}
    touched = set()
    unowned_drift = set()
    snapshot_copies = []
    snapshot_sources = {}
    for _, child_dir, child in sorted(children):
        for row in child.get("desktopFonts", []):
            if row["key"] not in desktop_merged:
                desktop_merged[row["key"]] = copy.deepcopy(row)
            else:
                desktop_merged[row["key"]]["after"] = copy.deepcopy(row["after"])
        for row in _journal_targets(child):
            key = row["id"]
            touched.add(key)
            if key not in merged:
                merged[key] = copy.deepcopy(row)
                before = merged[key]["before"]
                if before["exists"]:
                    src = _ensure_home_path(child_dir / "before" / before["snapshot"], allow_missing_leaf=False)
                    raw = src.read_bytes()
                    if _sha256(raw) != before["sha256"]:
                        raise TransactionError("child snapshot integrity check failed")
                    name = "group-" + child_dir.name + "-" + key + ".before"
                    snapshot_copies.append((transaction_dir / "before" / name, raw))
                    snapshot_sources[key] = src
                    before["snapshot"] = name
            else:
                first = merged[key]
                if not any(field in first for field in ("managedEdits", "mailFontsAfter", "browserFontsAfter")) and (row["before"].get("sha256") != first.get("appliedSha256") or row["before"].get("mode") != first.get("appliedMode")):
                    unowned_drift.add(key)
                for field in ("appliedSha256", "appliedMode", "mailFontsAfter", "browserFontsAfter"):
                    if field in row:
                        first[field] = copy.deepcopy(row[field])
                if "managedEdits" in row:
                    changes = first.setdefault("managedEdits", {})
                    for field, change in row["managedEdits"].items():
                        if field not in changes:
                            changes[field] = copy.deepcopy(change)
                        else:
                            changes[field]["after"] = copy.deepcopy(change["after"])
    if unowned_drift:
        raise TransactionError("Undo requires a field-aware adapter for intervening changes; preserving: " + ", ".join(sorted(unowned_drift)))
    _require_qt_restore(transaction_dir, {**journal, 'targets': list(merged.values()),
                                         'groupTouched': sorted(touched)}, snapshot_sources)
    if desktop_merged:
        import desktop_fonts
        desktop_fonts.validate(list(desktop_merged.values()))
        journal["desktopFonts"] = list(desktop_merged.values())
    for snapshot_path, raw in snapshot_copies:
        _atomic_write(snapshot_path, raw, 0o600)
    journal["targets"] = list(merged.values())
    journal["groupTouched"] = sorted(touched)
    journal["groupChildren"] = [child_dir.name for _, child_dir, _ in sorted(children)]
    journal["groupUndoPrepared"] = True


def _restore_group(directory, transaction_dir, journal):
    _require_restore(journal, check_qt=False)
    _prepare_group_undo(directory, transaction_dir, journal)
    _require_qt_restore(transaction_dir, journal)
    journal["groupUndoPending"] = True
    _write_journal(transaction_dir / "transaction.json", journal)
    if journal["state"] != "rolled_back":
        _restore_transaction(transaction_dir, journal)
    for name in journal.get("groupChildren", []):
        if not isinstance(name, str) or not TRANSACTION_ID_RE.fullmatch(name):
            raise TransactionError("invalid child operation identity")
        path = directory / name
        child = _load_journal(path)
        if child.get("parentTransaction") != transaction_dir.name:
            raise TransactionError("child operation parent mismatch")
        child["state"] = "rolled_back"
        _write_journal(path / "transaction.json", child)
    journal["groupUndoPending"] = False
    _write_journal(transaction_dir / "transaction.json", journal)


def _recover_group_undos(directory):
    recovered = []
    for candidate in directory.iterdir():
        if candidate.is_symlink() or not candidate.is_dir() or not TRANSACTION_ID_RE.fullmatch(candidate.name):
            continue
        if not (candidate / "transaction.json").exists():
            continue
        journal = _load_journal(candidate)
        if journal.get("groupUndoPending"):
            _restore_group(directory, candidate, journal)
            recovered.append(candidate.name)
    return recovered


def _prune_committed(directory: Path) -> None:
    """Keep at least 30 days and the 20 most recent completed snapshots."""
    completed: list[tuple[float, Path, dict[str, object]]] = []
    for candidate in directory.iterdir():
        if candidate.is_symlink() or not candidate.is_dir() or not TRANSACTION_ID_RE.fullmatch(candidate.name):
            continue
        journal_path = candidate / "transaction.json"
        if not journal_path.is_file():
            continue
        journal = _load_journal(candidate)
        if journal.get("state") in {"committed", "rolled_back"}:
            completed.append((candidate.stat().st_mtime, candidate, journal))
    completed.sort(key=lambda item: item[0], reverse=True)
    now = time.time()
    for index, (modified, candidate, journal) in enumerate(completed):
        if index < KEEP_RECENT_TRANSACTIONS or now - modified < MIN_RETENTION_SECONDS:
            continue
        if any(item["id"] == "appearance-policy" for item in journal["targets"]) or journal.get("parentTransaction") or journal.get("appearanceContext") or any(
                item[2].get("parentTransaction") == candidate.name for item in completed):
            continue
        entries = _journal_targets(journal)
        for item in entries:
            before = item["before"]
            if not isinstance(before, dict) or before.get("exists") is False:
                continue
            name = before.get("snapshot")
            if not isinstance(name, str) or Path(name).name != name:
                raise TransactionError("invalid snapshot reference; refusing to prune")
            snapshot = candidate / "before" / name
            if snapshot.is_symlink() or not snapshot.is_file() or _sha256(snapshot.read_bytes()) != before.get("sha256"):
                raise TransactionError("snapshot integrity check failed; refusing to prune")
        shutil.rmtree(candidate)


def transaction_status() -> list[dict[str, str]]:
    """Return transaction IDs and states without changing application files."""
    directory = transactions_path()
    _check_home_destination(directory)
    if not directory.is_dir():
        return []
    result: list[dict[str, str]] = []
    for candidate in sorted(directory.iterdir()):
        if not candidate.is_dir() or not TRANSACTION_ID_RE.fullmatch(candidate.name):
            continue
        journal = _load_journal(candidate)
        result.append({"id": candidate.name, "state": str(journal.get("state", "unknown"))})
    return result


def has_committed_transaction(*, label: str) -> bool:
    """Report whether a matching transaction can be undone without changing files."""
    directory = transactions_path()
    _check_home_destination(directory)
    if not directory.is_dir():
        return False
    for candidate in directory.iterdir():
        if candidate.is_symlink() or not candidate.is_dir() or not TRANSACTION_ID_RE.fullmatch(candidate.name):
            continue
        journal = _load_journal(candidate)
        if journal.get("state") == "committed" and journal.get("label") == label:
            return True
    return False
