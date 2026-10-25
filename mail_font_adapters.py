"""Catalog mail clients and resolve their user-level font configuration."""

from __future__ import annotations

import configparser
import os
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


def writable_betterbird_profile() -> str | None:
    """Require profile provenance from the actual installed Betterbird path."""
    executable = shutil.which("betterbird")
    if not executable:
        return None
    app_dir = Path(executable).resolve().parent
    resolved = []
    for item in discover_mail_profiles():
        if item.get("name") != "Betterbird" or not item.get("prefsPath"):
            continue
        prefs = HOME / item["prefsPath"]
        compatibility = prefs.parent / "compatibility.ini"
        if compatibility.is_symlink() or not compatibility.is_file():
            continue
        ini = configparser.RawConfigParser(interpolation=None)
        try:
            ini.read(compatibility, encoding="utf-8")
            last_app = ini.get("Compatibility", "LastAppDir", fallback="")
            if last_app and Path(last_app).resolve() == app_dir:
                resolved.append(item["prefsPath"])
        except (OSError, configparser.Error):
            continue
    return resolved[0] if len(resolved) == 1 else None
