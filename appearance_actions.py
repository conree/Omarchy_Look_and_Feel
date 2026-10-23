#!/usr/bin/env python3
"""Journaled Omarchy theme, wallpaper, and unlock apply/undo actions."""

from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from transaction import (
    TransactionError,
    _fsync_dir,
    _locked,
    _mkdir_private,
    transactions_path,
)


ACTION_KINDS = {"theme", "background", "unlock"}
ACTION_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$")
MAX_JOURNAL_BYTES = 64 * 1024
KEEP_RECENT = 20
MIN_RETENTION = 30 * 24 * 60 * 60
CURRENT_DIR = Path.home() / ".local/state/omarchy/current"
THEME_SET = CURRENT_DIR / "theme"


def _action_root() -> Path:
    root = transactions_path() / "appearance-actions"
    _mkdir_private(root)
    return root


def _kind_root(kind: str) -> Path:
    if kind not in ACTION_KINDS:
        raise TransactionError(f"unknown appearance action: {kind}")
    root = _action_root() / kind
    _mkdir_private(root)
    return root


def _journal_path(directory: Path) -> Path:
    return directory / "action.json"


def _write_journal(path: Path, journal: dict[str, object]) -> None:
    payload = json.dumps(journal, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(payload) > MAX_JOURNAL_BYTES:
        raise TransactionError("appearance action journal is too large")
    fd, temporary = tempfile.mkstemp(prefix=".appearance-action-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_dir(path.parent)
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


def _read_journal(directory: Path, kind: str) -> dict[str, object]:
    path = _journal_path(directory)
    if path.is_symlink() or not path.is_file():
        raise TransactionError(f"invalid appearance action journal path: {path}")
    raw = path.read_bytes()
    if len(raw) > MAX_JOURNAL_BYTES:
        raise TransactionError(f"appearance action journal is too large: {path}")
    journal = json.loads(raw)
    allowed_states = {"prepared", "applying", "committed", "rolling_back", "rolled_back", "recovery_required"}
    if (
        not isinstance(journal, dict)
        or type(journal.get("schemaVersion")) is not int
        or journal.get("schemaVersion") != 1
        or journal.get("id") != directory.name
        or journal.get("kind") != kind
        or journal.get("state") not in allowed_states
        or not isinstance(journal.get("before"), str)
        or not isinstance(journal.get("after"), str)
    ):
        raise TransactionError(f"invalid appearance action journal: {path}")
    return journal


def _records(kind: str) -> list[tuple[float, Path, dict[str, object]]]:
    root = _kind_root(kind)
    result = []
    for directory in root.iterdir():
        if directory.is_symlink() or not directory.is_dir() or not ACTION_ID_RE.fullmatch(directory.name):
            continue
        journal = _read_journal(directory, kind)
        result.append((directory.stat().st_mtime, directory, journal))
    return sorted(result, key=lambda item: item[0])


def _omarchy(*args: str, env: dict[str, str] | None = None, timeout: int = 60) -> str:
    command = shutil.which("omarchy") or ("/usr/bin/omarchy" if Path("/usr/bin/omarchy").is_file() else None)
    if not command:
        raise TransactionError("the Omarchy command is not available")
    child_env = os.environ.copy() if env is None else env.copy()
    child_env["OMARCHY_PATH"] = _omarchy_root()
    try:
        result = subprocess.run([command, *args], capture_output=True, text=True, env=child_env, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TransactionError(f"Omarchy {' '.join(args[:3])} failed to run: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise TransactionError(detail[:1000] or f"Omarchy {' '.join(args[:3])} exited with {result.returncode}")
    return result.stdout.strip()


def _omarchy_root() -> str:
    configured = os.environ.get("OMARCHY_PATH", "").strip()
    if configured and Path(configured).is_absolute() and Path(configured).is_dir():
        return configured
    config_file = Path("/etc/omarchy.conf")
    try:
        match = re.fullmatch(r'export OMARCHY_PATH="([^"]+)"\s*', config_file.read_text(encoding="utf-8").strip())
        if match and Path(match.group(1)).is_absolute() and Path(match.group(1)).is_dir():
            return match.group(1)
    except OSError:
        pass
    return "/usr/share/omarchy"


def _theme_state() -> str | None:
    path = CURRENT_DIR / "theme.name"
    try:
        if path.is_symlink() or not path.is_file():
            return None
        value = path.read_text(encoding="utf-8").strip().casefold()
        return value if value and re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value) else None
    except OSError:
        return None


def _set_theme(value: str) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value):
        raise TransactionError("invalid Omarchy theme slug")
    env = os.environ.copy()
    env["OMARCHY_THEME_SKIP_BACKGROUND"] = "1"
    _omarchy("theme", "set", value, env=env, timeout=240)


def _copy_background_backup(directory: Path, background: str) -> str:
    source = Path(background)
    try:
        source.relative_to(THEME_SET)
    except ValueError:
        return background
    suffix = source.suffix.lower() if source.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"} else ".img"
    backup = directory / ("background-before" + suffix)
    with source.open("rb") as incoming, backup.open("xb") as outgoing:
        os.fchmod(outgoing.fileno(), 0o600)
        shutil.copyfileobj(incoming, outgoing)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    _fsync_dir(directory)
    return str(backup)


def _file_digest(path: str) -> str | None:
    try:
        digest = hashlib.sha256()
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        return None


def _set_theme_background(value: str) -> None:
    _set_background(value)


def _restore_theme(journal: dict[str, object]) -> None:
    _set_theme(str(journal["before"]))
    prior = str(journal.get("backgroundBefore", ""))
    backup = str(journal.get("backgroundBackup", ""))
    prior_digest = journal.get("backgroundDigest")
    restore = prior if prior and Path(prior).is_file() and _file_digest(prior) == prior_digest else backup
    if restore:
        _set_theme_background(restore)


def _apply_theme(journal: dict[str, object]) -> None:
    _set_theme(str(journal["after"]))
    preserved = str(journal.get("backgroundAfter", ""))
    if preserved:
        _set_theme_background(preserved)


def _background_state() -> str | None:
    path = CURRENT_DIR / "background"
    try:
        info = path.lstat()
        if not stat.S_ISLNK(info.st_mode):
            return None
        resolved = path.resolve(strict=True)
        return str(resolved) if resolved.is_file() else None
    except OSError:
        return None


def _background_link_target() -> str | None:
    path = CURRENT_DIR / "background"
    try:
        info = path.lstat()
        if not stat.S_ISLNK(info.st_mode):
            return None
        target = Path(os.readlink(path))
        if not target.is_absolute():
            target = path.parent / target
        return os.path.abspath(target)
    except OSError:
        return None


def _journal_background_target(journal: dict[str, object]) -> str | None:
    current = _background_state()
    return current if current is not None else _background_link_target()


def _theme_background_targets(journal: dict[str, object]) -> set[str]:
    return {
        str(journal.get("backgroundBefore")),
        str(journal.get("backgroundAfter")),
        str(journal.get("backgroundBackup")),
    }


def _set_background(value: str) -> None:
    path = Path(value)
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise TransactionError("the selected wallpaper is no longer a regular file")
    _omarchy("theme", "bg", "set", str(path), timeout=45)


def _unlock_state() -> str | None:
    value = _omarchy("plymouth", "current", timeout=30).strip().casefold().replace(" ", "-")
    if not value or value == "unknown":
        return None
    if value != "default" and not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value):
        return None
    return value


def _set_unlock(value: str) -> None:
    if value == "default":
        _omarchy("plymouth", "reset", timeout=900)
    elif re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value):
        _omarchy("plymouth", "set-by-theme", value, timeout=900)
    else:
        raise TransactionError("invalid Omarchy unlock design slug")


HANDLERS: dict[str, tuple[Callable[[], str | None], Callable[[str], None]]] = {
    "theme": (_theme_state, _set_theme),
    "background": (_background_state, _set_background),
    "unlock": (_unlock_state, _set_unlock),
}


def _recover_pending_locked() -> list[str]:
    recovered: list[str] = []
    for kind in sorted(ACTION_KINDS):
        getter, setter = HANDLERS[kind]
        for _, directory, journal in _records(kind):
            if journal["state"] not in {"prepared", "applying", "rolling_back", "recovery_required"}:
                continue
            current = getter()
            before, after = str(journal["before"]), str(journal["after"])
            if current not in {before, after}:
                journal["state"] = "recovery_required"
                journal["recoveryError"] = f"state drifted to {current!r}; preserving external change"
                _write_journal(_journal_path(directory), journal)
                raise TransactionError(f"{kind} recovery required; state changed independently to {current!r}")
            if kind == "theme" and journal.get("backgroundBefore"):
                observed_background = _journal_background_target(journal)
                if observed_background not in _theme_background_targets(journal):
                    journal["state"] = "recovery_required"
                    journal["recoveryError"] = f"background changed independently to {observed_background!r}; preserving external change"
                    _write_journal(_journal_path(directory), journal)
                    raise TransactionError("theme recovery required; background changed independently and was preserved")
            journal["state"] = "rolling_back"
            journal["updatedAt"] = datetime.now(timezone.utc).isoformat()
            _write_journal(_journal_path(directory), journal)
            try:
                # Reapply the prior state even if the primary marker already
                # matches; theme and unlock commands update runtime assets too.
                if kind == "theme":
                    _restore_theme(journal)
                else:
                    setter(before)
                restored = getter()
                if restored != before:
                    raise TransactionError(f"readback after recovery was {restored!r}, expected {before!r}")
                if kind == "theme" and journal.get("backgroundBefore") and _background_state() not in {
                    str(journal.get("backgroundBefore")), str(journal.get("backgroundBackup"))
                }:
                    raise TransactionError("background readback after theme recovery did not match the previous wallpaper")
                journal["state"] = "rolled_back"
                journal["recoveredAt"] = datetime.now(timezone.utc).isoformat()
                journal.pop("recoveryError", None)
                recovered.append(directory.name)
            except Exception as exc:
                journal["state"] = "recovery_required"
                journal["recoveryError"] = str(exc)[:1000]
                _write_journal(_journal_path(directory), journal)
                raise TransactionError(f"{kind} recovery failed: {exc}") from exc
            _write_journal(_journal_path(directory), journal)
    return recovered


def apply_action(kind: str, target: str, allowed_targets: set[str]) -> dict[str, object]:
    if kind not in ACTION_KINDS:
        raise TransactionError(f"unknown appearance action: {kind}")
    if not isinstance(target, str) or target not in allowed_targets:
        raise TransactionError(f"selected {kind} is no longer available")
    directory = transactions_path()
    with _locked(directory):
        _recover_pending_locked()
        getter, setter = HANDLERS[kind]
        before = getter()
        if before is None:
            raise TransactionError(f"the current {kind} cannot be read, so a reversible change is unavailable")
        background_before = _background_state() if kind == "theme" else None
        if kind == "theme" and background_before is None:
            raise TransactionError("the current background cannot be read, so theme Apply cannot preserve it")
        if before == target:
            return {"kind": kind, "state": "already-current", "before": before, "after": target, "undoAvailable": False}
        transaction_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
        transaction_dir = _kind_root(kind) / transaction_id
        transaction_dir.mkdir(mode=0o700)
        journal: dict[str, object] = {
            "schemaVersion": 1, "id": transaction_id, "kind": kind,
            "state": "prepared", "before": before, "after": target,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        if kind == "theme" and background_before is not None:
            journal["backgroundBefore"] = background_before
            journal["backgroundDigest"] = _file_digest(background_before)
            try:
                Path(background_before).relative_to(THEME_SET)
                backup_path = transaction_dir / ("background-before" + Path(background_before).suffix.lower())
                journal["backgroundAfter"] = str(backup_path)
                journal["backgroundBackup"] = str(backup_path)
            except ValueError:
                journal["backgroundAfter"] = background_before
        _write_journal(_journal_path(transaction_dir), journal)
        try:
            if kind == "theme" and journal.get("backgroundBackup"):
                _copy_background_backup(transaction_dir, str(journal["backgroundBefore"]))
            journal["state"] = "applying"
            journal["updatedAt"] = datetime.now(timezone.utc).isoformat()
            _write_journal(_journal_path(transaction_dir), journal)
            if kind == "theme":
                _apply_theme(journal)
            else:
                setter(target)
            actual = getter()
            if actual != target:
                raise TransactionError(f"{kind} readback mismatch: expected {target!r}, observed {actual!r}")
            if kind == "theme" and _background_state() != journal.get("backgroundAfter"):
                raise TransactionError("theme Apply changed the independently selected background")
            journal["state"] = "committed"
            journal["committedAt"] = datetime.now(timezone.utc).isoformat()
            _write_journal(_journal_path(transaction_dir), journal)
        except BaseException as exc:
            journal["state"] = "rolling_back"
            journal["updatedAt"] = datetime.now(timezone.utc).isoformat()
            _write_journal(_journal_path(transaction_dir), journal)
            try:
                current = getter()
                if current not in {before, target}:
                    raise TransactionError(f"state drifted to {current!r}; preserving external change")
                if kind == "theme":
                    background_current = _journal_background_target(journal)
                    if background_current not in _theme_background_targets(journal):
                        raise TransactionError(f"background changed independently to {background_current!r}; preserving external change")
                if kind == "theme":
                    _restore_theme(journal)
                else:
                    setter(before)
                restored = getter()
                if restored != before:
                    raise TransactionError(f"rollback readback was {restored!r}, expected {before!r}")
                if kind == "theme" and journal.get("backgroundBefore") and _background_state() not in {
                    str(journal.get("backgroundBefore")), str(journal.get("backgroundBackup"))
                }:
                    raise TransactionError("background rollback readback did not match its prior target")
                journal["state"] = "rolled_back"
                journal["rolledBackAt"] = datetime.now(timezone.utc).isoformat()
            except Exception as rollback_error:
                journal["state"] = "recovery_required"
                journal["recoveryError"] = str(rollback_error)[:1000]
                _write_journal(_journal_path(transaction_dir), journal)
                raise TransactionError(f"Apply failed ({exc}); rollback needs recovery: {rollback_error}") from exc
            _write_journal(_journal_path(transaction_dir), journal)
            raise TransactionError(f"Apply failed and the previous {kind} was restored: {exc}") from exc
        _prune_action_history(kind)
        return {
            "transaction": transaction_id, "kind": kind, "state": "committed",
            "before": before, "after": target, "readback": actual, "undoAvailable": True,
            **({"backgroundReadback": _background_state()} if kind == "theme" else {}),
        }


def _prune_action_history(kind: str) -> None:
    records = sorted(_records(kind), key=lambda item: item[0], reverse=True)
    now = time.time()
    protected: list[Path] = []
    current_background = _background_state()
    if current_background:
        protected.append(Path(current_background))
    for index, (modified, directory, journal) in enumerate(records):
        if index < KEEP_RECENT or now - modified < MIN_RETENTION:
            continue
        if journal["state"] in {"committed", "rolled_back"}:
            referenced_elsewhere = list(protected)
            for other_directory, other_journal in ((item[1], item[2]) for item in records if item[1] != directory):
                if other_journal["state"] not in {"committed", "prepared", "applying", "rolling_back", "recovery_required"}:
                    continue
                for key in ("backgroundBefore", "backgroundAfter", "backgroundBackup"):
                    value = other_journal.get(key)
                    if isinstance(value, str) and value:
                        referenced_elsewhere.append(Path(value))
            if any(path == directory or directory in path.parents for path in referenced_elsewhere):
                continue
            shutil.rmtree(directory)


def rollback_action(kind: str) -> dict[str, object]:
    if kind not in ACTION_KINDS:
        raise TransactionError(f"unknown appearance action: {kind}")
    with _locked(transactions_path()):
        _recover_pending_locked()
        records = _records(kind)
        committed = [item for item in records if item[2]["state"] == "committed"]
        if not committed:
            raise TransactionError(f"there is no committed {kind} action to undo")
        _, directory, journal = committed[-1]
        getter, setter = HANDLERS[kind]
        before, after = str(journal["before"]), str(journal["after"])
        current = getter()
        if current != after:
            raise TransactionError(f"current {kind} is {current!r}, not the value this action applied; preserving the intervening change")
        if kind == "theme" and _background_state() != journal.get("backgroundAfter"):
            raise TransactionError("background changed since this theme action; preserving the intervening change")
        journal["state"] = "rolling_back"
        journal["updatedAt"] = datetime.now(timezone.utc).isoformat()
        _write_journal(_journal_path(directory), journal)
        try:
            if kind == "theme":
                if _background_state() != journal.get("backgroundAfter"):
                    raise TransactionError("background changed since this theme action; preserving the intervening change")
                _restore_theme(journal)
            else:
                setter(before)
            actual = getter()
            if actual != before:
                raise TransactionError(f"undo readback was {actual!r}, expected {before!r}")
            if kind == "theme" and journal.get("backgroundBefore") and _background_state() not in {
                str(journal.get("backgroundBefore")), str(journal.get("backgroundBackup"))
            }:
                raise TransactionError("background undo readback did not match its prior target")
            journal["state"] = "rolled_back"
            journal["rolledBackAt"] = datetime.now(timezone.utc).isoformat()
            _write_journal(_journal_path(directory), journal)
        except Exception as exc:
            journal["state"] = "recovery_required"
            journal["recoveryError"] = str(exc)[:1000]
            _write_journal(_journal_path(directory), journal)
            raise TransactionError(f"undo failed; recovery is required: {exc}") from exc
        _prune_action_history(kind)
        return {"rolledBack": directory.name, "kind": kind, "restored": before, "readback": actual}


def action_status() -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for kind in sorted(ACTION_KINDS):
        try:
            committed = [item for item in _records(kind) if item[2]["state"] == "committed"]
            if not committed:
                result[kind] = {"undoAvailable": False, "state": "none", "observedValue": HANDLERS[kind][0]()}
                continue
            _, directory, journal = committed[-1]
            current = HANDLERS[kind][0]()
            matches = current == journal["after"]
            if kind == "theme":
                matches = matches and _background_state() == journal.get("backgroundAfter")
            result[kind] = {
                "transaction": directory.name,
                "state": "applied" if matches else "drifted",
                "expectedValue": journal["after"],
                "previousValue": journal["before"],
                "observedValue": current,
                "undoAvailable": matches,
            }
        except Exception as exc:
            result[kind] = {"undoAvailable": False, "state": "unobservable", "detail": str(exc)[:500]}
    return result
