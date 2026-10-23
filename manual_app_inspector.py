"""On-demand app lookup kept separate from the automatic startup census."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from font_application_inventory import (
    ADDITIONAL_APPLICATION_DIRS,
    APPLICATION_DIRS,
    _app_record,
    _desktop_fields,
    _exec_command,
    _appimage_files,
    _package_inventory,
    _pacman_owners,
    _resolved_exec,
)


def _query_matches(query: str, value: str) -> bool:
    return query.casefold() in value.casefold()


def inspect_app(query: str) -> dict[str, object]:
    """Look up one user-requested app without merging it into the startup audit."""
    cleaned = " ".join(query.strip().split())
    if len(cleaned) < 2:
        return {"query": cleaned, "status": "query-too-short", "matches": [], "message": "Enter at least two characters."}

    desktop_matches: list[tuple[int, str, dict[str, str], Path]] = []
    for root in tuple(dict.fromkeys((*APPLICATION_DIRS, *ADDITIONAL_APPLICATION_DIRS))):
        if not root.is_dir():
            continue
        try:
            paths = root.rglob("*.desktop")
            for path in paths:
                fields = _desktop_fields(path)
                if fields.get("Type", "Application") != "Application":
                    continue
                app_id = path.relative_to(root).as_posix().replace("/", "-")
                command = _exec_command(fields.get("Exec", ""))
                values = (fields.get("Name", ""), app_id, command, fields.get("TryExec", ""))
                if not any(_query_matches(cleaned, value) for value in values if value):
                    continue
                score = 100 if fields.get("Name", "").casefold() == cleaned.casefold() else 80
                if command.casefold() == cleaned.casefold() or app_id.casefold() == cleaned.casefold():
                    score = max(score, 95)
                desktop_matches.append((score, app_id, fields, path))
        except OSError:
            continue
    desktop_matches.sort(key=lambda item: (-item[0], item[2].get("Name", item[1]).casefold()))
    desktop_matches = desktop_matches[:12]
    resolved = {_resolved_exec(fields.get("Exec", "")) for _, _, fields, _ in desktop_matches}
    owner_map = _pacman_owners({str(path) for path in resolved if path})
    package_sources = _package_inventory()
    foreign_packages = set(package_sources["pacman"]["foreignPackageNames"])
    records = []
    for _, app_id, fields, source in desktop_matches:
        executable = _resolved_exec(fields.get("Exec", ""))
        owner = owner_map.get(str(executable)) if executable else None
        record = _app_record(app_id, fields, source, owner, foreign_packages)
        records.append({key: record[key] for key in (
            "id", "name", "execCommand", "installationSource", "pacmanPackage", "framework",
            "fontRoles", "controlPoints", "review", "launchable",
        )})

    package_matches: list[dict[str, str]] = []
    if not records:
        pacman = shutil.which("pacman") or ("/usr/bin/pacman" if Path("/usr/bin/pacman").is_file() else None)
        if pacman:
            try:
                result = subprocess.run([pacman, "-Q"], capture_output=True, text=True, timeout=8, check=False)
                if result.returncode == 0:
                    package_matches.extend({"name": line.rsplit(" ", 1)[0], "version": line.rsplit(" ", 1)[1], "source": "pacman-installed"}
                                           for line in result.stdout.splitlines() if " " in line and _query_matches(cleaned, line.rsplit(" ", 1)[0]))
            except (OSError, subprocess.TimeoutExpired):
                pass
        flatpak = shutil.which("flatpak") or ("/usr/bin/flatpak" if Path("/usr/bin/flatpak").is_file() else None)
        if flatpak:
            try:
                result = subprocess.run([flatpak, "list", "--app", "--columns=application"], capture_output=True, text=True, timeout=8, check=False)
                if result.returncode == 0:
                    package_matches.extend({"name": line.strip(), "version": "", "source": "flatpak"}
                                           for line in result.stdout.splitlines() if line.strip() and _query_matches(cleaned, line.strip()))
            except (OSError, subprocess.TimeoutExpired):
                pass
        snap = shutil.which("snap") or ("/usr/bin/snap" if Path("/usr/bin/snap").is_file() else None)
        if snap:
            try:
                result = subprocess.run([snap, "list"], capture_output=True, text=True, timeout=8, check=False)
                if result.returncode == 0:
                    package_matches.extend({"name": fields[0], "version": fields[1] if len(fields) > 1 else "", "source": "snap"}
                                           for line in result.stdout.splitlines()[1:] if (fields := line.split()) and _query_matches(cleaned, fields[0]))
            except (OSError, subprocess.TimeoutExpired):
                pass
        package_matches.extend({"name": Path(path).name, "version": "", "source": "AppImage"}
                               for path in _appimage_files() if _query_matches(cleaned, Path(path).name))
        executable = shutil.which(cleaned)
        if executable:
            package_matches.append({"name": Path(executable).name, "version": "", "source": "PATH executable"})

    if records:
        status = "launcher-found"
        message = f"Found {len(records)} launcher match(es). Review each app's framework and font controls below; this request was not added to the startup inventory."
    elif package_matches:
        status = "installed-item-found-no-launcher"
        message = "Found installed package or standalone binary matches but no desktop launcher. Their UI font control needs app-specific review."
    else:
        status = "not-found"
        message = "No matching desktop launcher or installed pacman/Flatpak app was found. Try its launcher name, executable, or package name."
    return {"query": cleaned, "status": status, "matches": records, "packageMatches": package_matches[:12], "message": message}
