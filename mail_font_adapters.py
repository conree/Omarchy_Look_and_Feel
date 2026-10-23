"""Catalog mail clients and resolve their user-level font configuration."""

from __future__ import annotations

import configparser
import os
import re
import shutil
from pathlib import Path


HOME = Path.home()
MAIL_CLIENTS = {
    "eu.betterbird.Betterbird.desktop": {
        "name": "Betterbird", "engine": "Gecko", "profileRoot": ".thunderbird",
        "profileName": "default-default", "fontPrefs": [
            "font.name.sans-serif.x-western", "font.size.variable.x-western", "msgcompose.font_face",
        ],
    },
    "thunderbird.desktop": {
        "name": "Thunderbird", "engine": "Gecko", "profileRoot": ".thunderbird",
        "profileName": "default", "fontPrefs": [
            "font.name.sans-serif.x-western", "font.size.variable.x-western", "msgcompose.font_face",
        ],
    },
    "org.gnome.Evolution.desktop": {
        "name": "Evolution", "engine": "GTK", "profileRoot": None,
        "fontPrefs": [],
    },
    "geary.desktop": {
        "name": "Geary", "engine": "GTK", "profileRoot": None,
        "fontPrefs": [],
    },
}
MAIL_CLIENT_ALIASES = {
    "org.mozilla.Thunderbird.desktop": "thunderbird.desktop",
    "org.gnome.Geary.desktop": "geary.desktop",
}


def mail_client_definition(desktop_id: str) -> dict[str, object] | None:
    canonical = MAIL_CLIENT_ALIASES.get(desktop_id, desktop_id)
    value = MAIL_CLIENTS.get(canonical)
    if value is None:
        return None
    return {**value, "canonicalId": canonical}


def discover_mail_profiles() -> list[dict[str, str]]:
    """Resolve only the selected Gecko profile for installed mail clients."""
    root = HOME / ".thunderbird"
    ini_path = root / "profiles.ini"
    parser = configparser.RawConfigParser(interpolation=None)
    if ini_path.is_file() and not ini_path.is_symlink():
        try:
            parser.read(ini_path, encoding="utf-8")
        except (OSError, configparser.Error):
            parser = configparser.RawConfigParser(interpolation=None)

    profiles: list[dict[str, str]] = []
    install_defaults = set()
    for section in parser.sections():
        if section.startswith("Install"):
            install_default = parser.get(section, "Default", fallback="")
            if install_default and "/" not in install_default and ".." not in Path(install_default).parts:
                install_defaults.add(install_default)
    for section in parser.sections():
        if not section.startswith("Profile"):
            continue
        name = parser.get(section, "Name", fallback="")
        raw_path = parser.get(section, "Path", fallback="")
        if not raw_path:
            continue
        profile = Path(raw_path)
        if parser.getboolean(section, "IsRelative", fallback=True):
            if profile.is_absolute() or ".." in profile.parts or len(profile.parts) != 1:
                continue
            resolved = root / profile
        else:
            if ".." in profile.parts or not profile.is_absolute():
                continue
            resolved = profile
        try:
            relative = resolved.relative_to(HOME)
        except ValueError:
            continue
        profiles.append({"name": name, "path": str(relative), "isDefault": parser.get(section, "Default", fallback=""),
                         "selectedByInstall": str(profile) in install_defaults})

    # Desktop IDs are also collected from the effective XDG application set.
    installed = set()
    data_home = Path(os.environ.get("XDG_DATA_HOME", str(HOME / ".local/share")))
    data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":")
    for directory in (data_home / "applications", *(Path(part) / "applications" for part in data_dirs if Path(part).is_absolute())):
        if directory.is_dir():
            try:
                installed.update(path.name for path in directory.glob("*.desktop"))
            except OSError:
                pass
    results = []
    for desktop_id, client in MAIL_CLIENTS.items():
        command = {"eu.betterbird.Betterbird.desktop": "betterbird", "thunderbird.desktop": "thunderbird",
                   "org.gnome.Evolution.desktop": "evolution", "geary.desktop": "geary"}[desktop_id]
        aliases = [alias for alias, canonical in MAIL_CLIENT_ALIASES.items() if canonical == desktop_id]
        present = desktop_id in installed or any(alias in installed for alias in aliases) or shutil.which(command) is not None
        result = {"desktopId": desktop_id, "name": client["name"], "engine": client["engine"],
                  "installed": str(present).lower(), "profile": "", "prefsPath": ""}
        if present and client["profileRoot"]:
            expected_name = str(client["profileName"])
            candidates = [p for p in profiles if p["name"] == expected_name]
            if desktop_id == "eu.betterbird.Betterbird.desktop":
                selected = [p for p in candidates if p["selectedByInstall"]]
                candidates = selected
            elif desktop_id == "thunderbird.desktop":
                defaults = [p for p in profiles if p["isDefault"] == "1"]
                if len(defaults) == 1:
                    candidates = defaults
            if len(candidates) == 1 and (HOME / candidates[0]["path"] / "prefs.js").is_file():
                result["profile"] = candidates[0]["path"]
                result["prefsPath"] = f"{candidates[0]['path']}/prefs.js"
        results.append(result)
    return results


def betterbird_prefs_relative_path() -> str | None:
    for client in discover_mail_profiles():
        if client["desktopId"] == "eu.betterbird.Betterbird.desktop" and client["installed"] == "true" and client["prefsPath"]:
            return client["prefsPath"]
    return None


def betterbird_font_target(family: str, size_pt: int = 12) -> dict[str, bytes]:
    """Build a strict Gecko prefs.js update, retaining all unrelated profile prefs."""
    if isinstance(size_pt, bool) or not isinstance(size_pt, int) or not 6 <= size_pt <= 48:
        raise ValueError("Betterbird font size must be an integer between 6 and 48 pt")
    relative = betterbird_prefs_relative_path()
    if not relative:
        raise ValueError("Betterbird is not installed or its selected profile could not be resolved")
    proc = Path("/proc")
    try:
        processes = list(proc.iterdir())
    except OSError as exc:
        raise ValueError("cannot inspect running processes safely; refusing to edit Betterbird preferences") from exc
    for process in processes:
        if not process.name.isdigit():
            continue
        try:
            comm = (process / "comm").read_text(encoding="utf-8", errors="replace").strip().casefold()
            cmdline = (process / "cmdline").read_bytes().split(b"\0")
        except (OSError, PermissionError):
            continue
        args = [Path(arg.decode("utf-8", "replace")).name.casefold() for arg in cmdline if arg]
        if comm in {"betterbird", "betterbird-bin"} or any(arg in {"betterbird", "betterbird-bin"} for arg in args):
            raise ValueError("close Betterbird before applying profile preferences so its running process cannot overwrite them")
    target = HOME / relative
    if target.is_symlink() or not target.is_file():
        raise ValueError("Betterbird profile prefs.js is missing or unsafe")
    original = target.read_bytes()
    text = original.decode("utf-8")
    updates = {
        "font.name.sans-serif.x-western": family,
        "font.size.variable.x-western": str(size_pt),
        "msgcompose.font_face": family,
    }
    for key, value in updates.items():
        if key == "font.size.variable.x-western":
            pattern = re.compile(r'^(\s*user_pref\("' + re.escape(key) + r'",\s*)(?:[0-9]+)(\);\s*)$', re.MULTILINE)
            replacement = lambda m: m.group(1) + value + m.group(2)
        else:
            pattern = re.compile(r'^(\s*user_pref\("' + re.escape(key) + r'",\s*)"(?:[^"\\]|\\.)*("\);\s*)$', re.MULTILINE)
            replacement = lambda m: m.group(1) + '"' + value.replace("\\", "\\\\").replace('"', '\\"') + m.group(2)
        text, count = pattern.subn(replacement, text)
        if count != 1:
            raise ValueError(f"expected exactly one existing Betterbird preference: {key}")
    return {"betterbird-prefs": text.encode("utf-8")}
