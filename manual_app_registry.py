"""Private registry for explicitly audited, safely shared app font surfaces."""

from __future__ import annotations

import hashlib
import fcntl
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from font_application_inventory import TERMINALS, installed_font_applications
from global_font_actions import TERMINAL_COMMANDS
from manual_app_inspector import inspect_app
from transaction import TransactionError


SCHEMA_VERSION = 1
MAX_RECORDS = 128
MAX_BYTES = 64 * 1024
SUPPORTED_TERMINAL_REVIEWS = {"terminal-inheritance-confirmed", "terminal-launcher-font-inherited"}


def _state_path() -> Path:
    home = Path.home().resolve(strict=True)
    state_home = Path(os.environ.get("XDG_STATE_HOME", str(home / ".local/state")))
    if not state_home.is_absolute():
        state_home = home / ".local/state"
    if ".." in state_home.parts:
        raise TransactionError("XDG_STATE_HOME cannot contain parent-directory components")
    try:
        relative = state_home.relative_to(home)
    except ValueError as exc:
        raise TransactionError("manual audit state must stay inside the user's home directory") from exc
    current = home
    parts = (*relative.parts, "omarchy-look-and-feel")
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            current.mkdir(mode=0o700)
            info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            raise TransactionError("manual audit state directory is unsafe")
        if index == len(parts) - 1:
            os.chmod(current, 0o700)
    return current / "manual-app-controls.json"


def _read() -> dict[str, Any]:
    path = _state_path()
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"schemaVersion": SCHEMA_VERSION, "entries": []}
    if (
        stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > MAX_BYTES
    ):
        raise TransactionError("manual audit registry is unsafe")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransactionError("manual audit registry could not be read") from exc
    if not isinstance(data, dict) or data.get("schemaVersion") != SCHEMA_VERSION or not isinstance(data.get("entries"), list):
        raise TransactionError("manual audit registry has an unsupported format")
    entries = data["entries"]
    if len(entries) > MAX_RECORDS or any(
        not isinstance(item, dict)
        or not isinstance(item.get("key"), str)
        or len(str(item.get("key", ""))) > 80
        or item.get("state") not in {"registered", "unsupported"}
        or item.get("fontSurface") not in {"gtk3", "gtk4", "terminal-inherited", "terminal-emulator", "unsupported"}
        or ("appId" in item and (
            not isinstance(item.get("appId"), str) or not item["appId"] or len(item["appId"]) > 512
            or "/" in item["appId"] or "\\" in item["appId"]
        ))
        for item in entries
    ):
        raise TransactionError("manual audit registry contains invalid entries")
    return data


@contextmanager
def _registry_lock():
    directory = _state_path().parent
    lock_path = directory / "manual-app-controls.lock"
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise TransactionError("manual audit registry lock is unsafe")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _write(data: dict[str, Any]) -> None:
    path = _state_path()
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(payload) > MAX_BYTES:
        raise TransactionError("manual audit registry is too large")
    try:
        prior = path.lstat()
    except FileNotFoundError:
        prior = None
    if prior is not None and (
        stat.S_ISLNK(prior.st_mode) or not stat.S_ISREG(prior.st_mode) or prior.st_uid != os.getuid()
    ):
        raise TransactionError("manual audit registry file is unsafe")
    fd, temporary = tempfile.mkstemp(prefix=".manual-app-controls-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
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


def _classify(record: dict[str, Any]) -> str:
    framework = str(record.get("framework", ""))
    review = str(record.get("review", ""))
    control_points = [str(value) for value in record.get("controlPoints", [])]
    roles = [str(value) for value in record.get("fontRoles", [])]
    if record.get("launchable") is False:
        return "unsupported"
    if framework == "GTK 3 application" and "system-ui" in roles and any(
        ".config/gtk-3.0/settings.ini" in value and "gtk-font-name" in value for value in control_points
    ):
        return "gtk3"
    if framework == "GTK 4 application" and "system-ui" in roles and any(
        ".config/gtk-4.0/settings.ini" in value and "gtk-font-name" in value for value in control_points
    ):
        return "gtk4"
    app_id = str(record.get("id", ""))
    if (
        framework == "terminal-emulator" and app_id in TERMINALS and app_id in TERMINAL_COMMANDS
        and "terminal-monospace" in roles
        and any("terminal font family and size" in value for value in control_points)
    ):
        return "terminal-emulator"
    if (
        framework == "terminal TUI" and review in SUPPORTED_TERMINAL_REVIEWS
        and "terminal-monospace" in roles
        and any("host terminal" in value.casefold() for value in control_points)
    ):
        return "terminal-inherited"
    return "unsupported"


def _app_key(app_id: str) -> str:
    return "app:" + hashlib.sha256(app_id.encode("utf-8")).hexdigest()


def _query_key(query: str) -> str:
    normalized = " ".join(query.strip().split()).casefold()
    return "query:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _public_framework(value: object) -> str:
    framework = str(value or "")
    if framework.startswith("GTK"):
        return "GTK application"
    if framework.startswith("Qt"):
        return "Qt application"
    if framework == "terminal TUI":
        return "terminal UI"
    if framework == "terminal-emulator":
        return "terminal emulator"
    if framework.startswith(("Electron", "Chromium")):
        return "web-based application"
    return "other application surface"


def _register_audit_result_unlocked(query: str, result: dict[str, Any]) -> dict[str, Any]:
    """Persist only adapter IDs and generic status; never persist names or paths."""
    data = _read()
    query_key = _query_key(query)
    entries = [item for item in data["entries"] if item.get("key") != query_key]
    matches = [item for item in result.get("matches", []) if isinstance(item, dict)]
    package_matches = [item for item in result.get("packageMatches", []) if isinstance(item, dict)]
    findings: list[dict[str, str]] = []

    if len(matches) == 1:
        record = matches[0]
        app_id = str(record.get("id", ""))
        surface = _classify(record)
        if app_id:
            key = _app_key(app_id)
            entries = [item for item in entries if item.get("key") != key]
            entries = [item for item in entries if item.get("key") != query_key]
            entries.append({"key": key, "appId": app_id, "state": "registered" if surface != "unsupported" else "unsupported", "fontSurface": surface})
        else:
            entries.append({"key": query_key, "state": "unsupported", "fontSurface": "unsupported"})
        findings.append({
            "framework": _public_framework(record.get("framework")),
            "roles": ", ".join(str(role) for role in record.get("fontRoles", [])[:3]) or "control surface unknown",
            "fontStatus": "registered" if surface != "unsupported" else "unsupported",
        })
    elif matches or package_matches:
        entries.append({"key": query_key, "state": "unsupported", "fontSurface": "unsupported"})
        findings.append({"framework": "ambiguous or package-only result", "roles": "control surface unresolved", "fontStatus": "unsupported"})

    if len(entries) > MAX_RECORDS:
        raise TransactionError("too many manual audit records; clear the audit registry before adding more")
    data["entries"] = entries
    _write(data)
    return {
        "status": str(result.get("status", "not-found")),
        "matchCount": len(matches) + len(package_matches),
        "findings": findings,
        "registeredCount": sum(item["state"] == "registered" for item in entries),
        "unsupportedCount": sum(item["state"] == "unsupported" for item in entries),
        "themeUnsupportedCount": len(entries),
    }


def register_audit_result(query: str, result: dict[str, Any]) -> dict[str, Any]:
    with _registry_lock():
        return _register_audit_result_unlocked(query, result)


def registry_status() -> dict[str, int]:
    with _registry_lock():
        entries = _read()["entries"]
        return {
            "registeredCount": sum(item["state"] == "registered" for item in entries),
            "unsupportedCount": sum(item["state"] == "unsupported" for item in entries),
            # The targeted audit identifies font surfaces only; it has no verified app-theme adapter metadata.
            "themeUnsupportedCount": len(entries),
        }


def validated_apply_status(target_ids: set[str] | None = None) -> dict[str, int]:
    """Revalidate registered IDs and prove every shared surface is in the target set."""
    with _registry_lock():
        entries = list(_read()["entries"])
    if not entries:
        return {"registeredCount": 0, "unsupportedCount": 0, "themeUnsupportedCount": 0}
    current = installed_font_applications()
    current_by_id = {str(item.get("id", "")): item for item in current.get("desktopApplications", []) if isinstance(item, dict)}
    registered = 0
    unsupported = 0
    for item in entries:
        app_id = item.get("appId")
        if item.get("state") != "registered" or not isinstance(app_id, str):
            unsupported += 1
            continue
        record = current_by_id.get(app_id)
        if record is None:
            result = inspect_app(app_id)
            matches = [match for match in result.get("matches", []) if isinstance(match, dict) and match.get("id") == app_id]
            record = matches[0] if len(matches) == 1 else None
        surface = _classify(record) if record else "unsupported"
        included = True
        if target_ids is not None:
            if surface == "gtk3":
                included = "gtk3-settings" in target_ids
            elif surface == "gtk4":
                included = "gtk4-settings" in target_ids
            elif surface == "terminal-inherited":
                included = any(adapter[1] in target_ids for adapter in TERMINAL_COMMANDS.values())
            elif surface == "terminal-emulator":
                adapter = TERMINAL_COMMANDS.get(app_id)
                included = bool(adapter and adapter[1] in target_ids)
        if surface != item.get("fontSurface") or not included:
            unsupported += 1
        else:
            registered += 1
    return {"registeredCount": registered, "unsupportedCount": unsupported, "themeUnsupportedCount": len(entries)}


def clear_registry() -> None:
    with _registry_lock():
        data = {"schemaVersion": SCHEMA_VERSION, "entries": []}
        _write(data)
