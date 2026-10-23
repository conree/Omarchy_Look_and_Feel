"""Read-only comparison of selected look-and-feel values with live state."""

from __future__ import annotations

import configparser
import hashlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any

from solar_schedule import SolarScheduleError, solar_events


HOME = Path.home()


def _config_home() -> Path:
    configured = Path(os.environ.get("XDG_CONFIG_HOME", str(HOME / ".config")))
    return configured if configured.is_absolute() else HOME / ".config"


def _omarchy_root() -> Path:
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


def _run(command: list[str], timeout: float = 5) -> str | None:
    executable = shutil.which(command[0])
    if not executable:
        fallback = Path("/usr/bin") / command[0]
        executable = str(fallback) if fallback.is_file() and os.access(fallback, os.X_OK) else None
    if not executable:
        return None
    try:
        child_env = os.environ.copy()
        child_env["OMARCHY_PATH"] = str(_omarchy_root())
        result = subprocess.run([executable, *command[1:]], capture_output=True, text=True, env=child_env, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _read_text(path: Path, limit: int = 1024 * 1024) -> str | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _file_sha256(path: Path) -> str | None:
    try:
        if not path.is_file():
            return None
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        return None


def _ini_value(path: Path, section: str, key: str) -> str | None:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read(path, encoding="utf-8")
        return parser.get(section, key, fallback=None)
    except (OSError, configparser.Error):
        return None


def _check(
    group: str,
    surface: str,
    expected: Any,
    actual: Any,
    evidence: str,
    *,
    available: bool = True,
    effective_setting: bool = False,
    pending_restart: bool = False,
) -> dict[str, Any]:
    if not available or actual is None:
        status = "unobservable"
        state = "unobservable"
    elif expected == actual:
        status = "match"
        state = "pending-restart" if pending_restart else ("effective-setting" if effective_setting else "persisted")
    else:
        status = "mismatch"
        state = "mismatched"
    return {
        "group": group,
        "surface": surface,
        "status": status,
        "state": state,
        "expected": expected,
        "actual": actual,
        "evidence": evidence,
        "runtimeProof": "configuration readback only; an open app may need restart and rendered glyphs are not inspected",
    }


def _process_started_before(path: Path, *names: str) -> bool:
    """Check whether a matching process started before a config file's last write."""
    try:
        modified = path.stat().st_mtime
        boot_line = next(line for line in Path("/proc/stat").read_text().splitlines() if line.startswith("btime "))
        boot_time = int(boot_line.split()[1])
        ticks_per_second = os.sysconf("SC_CLK_TCK")
    except (OSError, StopIteration, ValueError):
        return False
    wanted = {name.casefold() for name in names}
    try:
        entries = os.scandir("/proc")
    except OSError:
        return False
    with entries:
        for entry in entries:
            if not entry.name.isdigit():
                continue
            process = Path(entry.path)
            try:
                comm = (process / "comm").read_text(encoding="utf-8", errors="replace").strip().casefold()
                raw_stat = (process / "stat").read_text(encoding="utf-8", errors="replace")
                args = (process / "cmdline").read_bytes().split(b"\0")
                fields_after_comm = raw_stat[raw_stat.rfind(")") + 1:].split()
                start_ticks = int(fields_after_comm[19])
            except (OSError, ValueError, IndexError):
                continue
            matches = comm in wanted or any(Path(arg.decode("utf-8", "replace")).name.casefold() in wanted for arg in args if arg)
            start_time = boot_time + start_ticks / ticks_per_second
            if matches and start_time < modified:
                return True
    return False


def _fontconfig_family(pattern: str) -> str | None:
    value = _run(["fc-match", "--format", "%{family[0]}", pattern])
    return value.strip() if value else None


def _gsettings(key: str) -> str | None:
    value = _run(["gsettings", "get", "org.gnome.desktop.interface", key])
    if value is None:
        return None
    match = re.fullmatch(r"'((?:[^'\\]|\\.)*)'", value)
    return match.group(1).replace("\\'", "'") if match else value.strip('"')


def _gtk_font(path: Path) -> str | None:
    return _ini_value(path, "Settings", "gtk-font-name")


def _qt_font(path: Path, key: str) -> dict[str, Any] | None:
    raw = _ini_value(path, "Fonts", key)
    if not raw:
        return None
    fields = raw.split(",")
    if len(fields) < 2:
        return {"raw": raw}
    try:
        size = float(fields[1])
    except ValueError:
        size = None
    return {"family": fields[0].strip().strip('"'), "sizePt": size}


def _gecko_pref(path: Path, key: str) -> str | int | None:
    text = _read_text(path)
    if text is None:
        return None
    match = re.search(r'^\s*user_pref\("' + re.escape(key) + r'",\s*("(?:[^"\\]|\\.)*"|[0-9]+)\);\s*$', text, re.MULTILINE)
    if not match:
        return None
    value = match.group(1)
    if value.startswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return int(value)


def _json_file(path: Path) -> dict[str, Any] | None:
    raw = _read_text(path)
    if raw is None:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _nested(mapping: dict[str, Any] | None, *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _terminal_font_checks(expected_family: str, expected_size: float, app_inventory: dict[str, Any] | None) -> list[dict[str, Any]]:
    checks = []
    config = _config_home()
    terminal_ids = {
        "Alacritty": "Alacritty.desktop",
        "Foot": "foot.desktop",
        "Ghostty": "com.mitchellh.ghostty.desktop",
        "Kitty": "kitty.desktop",
        "WezTerm": "org.wezfurlong.wezterm.desktop",
    }
    installed_ids = {
        str(app.get("id")) for app in (app_inventory or {}).get("desktopApplications", [])
        if app.get("launchable") is not False and not app.get("hidden") and not app.get("noDisplay")
    }

    def record(name: str, actual: Any, evidence: str) -> None:
        # The startup inventory is authoritative when supplied. Avoid reporting
        # irrelevant config files for terminal emulators this user does not have.
        if app_inventory is not None and terminal_ids[name] not in installed_ids:
            return
        checks.append(_check("terminal", name, {"family": expected_family, "sizePt": expected_size}, actual, evidence,
                             pending_restart=False))

    ghostty_dir = config / "ghostty"
    ghostty_path = ghostty_dir / ("config.ghostty" if (ghostty_dir / "config.ghostty").is_file() else "config")
    ghostty = _read_text(ghostty_path) or ""
    overlay = _read_text(config / "ghostty/look-and-feel-font.conf") or ""
    overlay_family = None
    for line in overlay.splitlines():
        match = re.fullmatch(r'\s*font-family\s*=\s*"(.*)"\s*', line)
        if match:
            overlay_family = match.group(1)
    size_match = re.findall(r"^\s*font-size\s*=\s*([0-9.]+)", ghostty + "\n" + overlay, re.MULTILINE)
    size = float(size_match[-1]) if size_match else None
    imported = "config-file = look-and-feel-font.conf" in ghostty.splitlines()
    record("Ghostty", {"family": overlay_family, "sizePt": size} if imported and overlay_family else None,
           f"{ghostty_path} and look-and-feel-font.conf (managed configuration readback)")

    foot = _ini_value(config / "foot/foot.ini", "main", "font")
    foot_family = foot_size = None
    if foot:
        size_match = re.search(r"size=([0-9.]+)", foot)
        foot_family = foot.split(":size=", 1)[0].strip()
        foot_size = float(size_match.group(1)) if size_match else None
    record("Foot", {"family": foot_family, "sizePt": foot_size} if foot else None,
           f"{config}/foot/foot.ini [main] font")

    kitty_text = _read_text(config / "kitty/kitty.conf") or ""
    kitty_family = re.search(r"^\s*font_family\s+(.+?)\s*$", kitty_text, re.MULTILINE)
    kitty_size = re.search(r"^\s*font_size\s+([0-9.]+)", kitty_text, re.MULTILINE)
    record("Kitty", {"family": kitty_family.group(1) if kitty_family else None,
                      "sizePt": float(kitty_size.group(1)) if kitty_size else None} if kitty_family or kitty_size else None,
           f"{config}/kitty/kitty.conf")

    alacritty_path = config / "alacritty/alacritty.toml"
    alacritty_actual = None
    try:
        with alacritty_path.open("rb") as stream:
            data = tomllib.load(stream)
        font = data.get("font", {})
        normal = font.get("normal", {}) if isinstance(font, dict) else {}
        family = normal.get("family") if isinstance(normal, dict) else None
        size = font.get("size") if isinstance(font, dict) else None
        if family is not None or size is not None:
            alacritty_actual = {"family": family, "sizePt": float(size) if size is not None else None}
    except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError):
        pass
    record("Alacritty", alacritty_actual, f"{config}/alacritty/alacritty.toml [font]")

    wezterm = _read_text(config / "wezterm/wezterm.lua") or ""
    wez_family = re.search(r"\bfamily\s*=\s*['\"]([^'\"]+)", wezterm)
    wez_size = re.search(r"config\.font_size\s*=\s*([0-9.]+)", wezterm)
    record("WezTerm", {"family": wez_family.group(1) if wez_family else None,
                        "sizePt": float(wez_size.group(1)) if wez_size else None} if wez_family or wez_size else None,
           f"{config}/wezterm/wezterm.lua")
    return checks


def _theme_mode_expected(mode: str, light: str, dark: str) -> tuple[str | None, str]:
    if mode == "light":
        return light, "selected light theme"
    if mode == "dark":
        return dark, "selected dark theme"
    if mode != "automatic":
        return None, "unknown theme mode"
    try:
        weather = json.loads((HOME / ".local/state/omarchy/settings/weather.json").read_text(encoding="utf-8"))
        latitude, longitude = float(weather["latitude"]), float(weather["longitude"])
        zone_path = Path("/etc/localtime").resolve(strict=True)
        zoneinfo = Path("/usr/share/zoneinfo").resolve(strict=True)
        zone = zone_path.relative_to(zoneinfo).as_posix()
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo(zone))
        events = solar_events(now.date(), latitude, longitude, zone)
        is_light = events.sunrise <= now < events.sunset
        return (light if is_light else dark), "solar schedule expected at current local time"
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, SolarScheduleError):
        return None, "automatic mode cannot be evaluated without valid location and time-zone settings"


def audit_appearance(expected: dict[str, Any], app_inventory: dict[str, Any] | None = None) -> dict[str, Any]:
    """Audit selected values against read-only configuration and Omarchy state."""
    system_family = str(expected.get("systemFont", ""))
    terminal_family = str(expected.get("terminalFont", ""))
    system_size = float(expected.get("systemSizePt", 12))
    terminal_size = float(expected.get("terminalSizePt", 12))
    if not system_family or not terminal_family:
        raise ValueError("select both a system font and a terminal font before auditing")

    checks: list[dict[str, Any]] = []
    config = _config_home()
    checks.append(_check("font", "GTK 3", f"{system_family} {system_size:g}",
                         _gtk_font(config / "gtk-3.0/settings.ini"), f"{config}/gtk-3.0/settings.ini [Settings] gtk-font-name"))
    checks.append(_check("font", "GTK 4", f"{system_family} {system_size:g}",
                         _gtk_font(config / "gtk-4.0/settings.ini"), f"{config}/gtk-4.0/settings.ini [Settings] gtk-font-name"))
    for key, suffix, family, size in (
        ("font-name", "system", system_family, system_size),
        ("document-font-name", "document", system_family, system_size),
        ("monospace-font-name", "monospace", terminal_family, terminal_size),
    ):
        checks.append(_check("font", f"GSettings {suffix}", f"{family} {size:g}", _gsettings(key),
                             f"gsettings org.gnome.desktop.interface {key}", effective_setting=True))

    qt_apps = [app for app in (app_inventory or {}).get("desktopApplications", [])
               if not app.get("hidden") and not app.get("noDisplay") and app.get("launchable") is not False
               and str(app.get("framework", "")).startswith("Qt")]
    active_qt_theme = os.environ.get("QT_QPA_PLATFORMTHEME", "").casefold()
    for qt_version, major in (("qt5ct", "5"), ("qt6ct", "6")):
        if app_inventory is not None and not any(
            str(app.get("framework", "")).startswith(f"Qt {major}")
            or str(app.get("framework", "")) == "Qt"
            for app in qt_apps
        ):
            continue
        qt_path = config / f"{qt_version}/{qt_version}.conf"
        active = active_qt_theme == qt_version or active_qt_theme.startswith(qt_version + ":")
        for key, role, family, size in (
            ("general", "system", system_family, system_size),
            ("fixed", "monospace", terminal_family, terminal_size),
        ):
            checks.append(_check("font", f"{qt_version} {role}", {"family": family, "sizePt": size},
                                 _qt_font(qt_path, key) if active else None,
                                 f"{qt_path} [Fonts] {key}; active platform theme={active_qt_theme or 'not set'}",
                                 available=active))

    for role, family in (("system", system_family), ("monospace", terminal_family)):
        resolution = _check("font", f"Fontconfig {role} resolution", family,
                            _fontconfig_family(family if role == "system" else "monospace"),
                            f"fc-match {'monospace' if role == 'monospace' else family}", effective_setting=True)
        resolution["runtimeProof"] = "live Fontconfig resolution only; does not prove an application requests or renders this family"
        checks.append(resolution)
    checks.extend(_terminal_font_checks(terminal_family, terminal_size, app_inventory))

    visible_ids = {
        str(app.get("id", "")).casefold() for app in (app_inventory or {}).get("desktopApplications", [])
        if app.get("launchable") is not False and not app.get("hidden") and not app.get("noDisplay")
    }
    if "gparted.desktop" in visible_ids:
        checks.append(_check(
            "font", "GParted privileged UI font", f"{system_family} {system_size:g}", None,
            "GParted is launched across a privilege boundary; user GTK settings may not reach its process, and the root/session font source is not read",
            available=False,
        ))
    if "com.obsproject.studio.desktop" in visible_ids:
        checks.append(_check(
            "font", "OBS Studio UI font family", system_family, None,
            "OBS has no family selector; this audit cannot read the per-process Qt platform-theme integration or rendered widget font",
            available=False,
        ))
    editor_size_px = round(system_size * 4 / 3)
    mono_size_px = round(terminal_size * 4 / 3)
    cursor_path = _config_home() / "Cursor/User/settings.json"
    if "cursor.desktop" in visible_ids:
        cursor = _json_file(cursor_path)
        for key, label, family, size in (
            ("editor.fontFamily", "Cursor editor font family", terminal_family, None),
            ("terminal.integrated.fontFamily", "Cursor integrated terminal font family", terminal_family, None),
        ):
            actual = cursor.get(key) if cursor else None
            if isinstance(actual, str):
                actual = actual.split(",", 1)[0].strip().strip("'\"")
            checks.append(_check("font", label, family, actual, f"{cursor_path}: {key}",
                                 pending_restart=False))
        for key, label, size in (
            ("editor.fontSize", "Cursor editor size (CSS px; 12 pt ≈ 16 px)", editor_size_px),
            ("terminal.integrated.fontSize", "Cursor integrated terminal size (CSS px)", mono_size_px),
        ):
            actual = cursor.get(key) if cursor else None
            checks.append(_check("font", label, size, actual, f"{cursor_path}: {key}; absent values use Cursor defaults",
                                 pending_restart=False))
        for key, label, family in (
            ("chat.fontFamily", "Cursor chat UI font family", system_family),
            ("chat.editor.fontFamily", "Cursor chat code font family", terminal_family),
        ):
            configured = cursor.get(key) if cursor else None
            check = _check("font", label, family, configured,
                           f"{cursor_path}: {key}; Cursor-version support/effect is not verified",
                           available=False)
            check["runtimeProof"] = "saved configuration value read; Cursor-version support and runtime effect are not verified"
            checks.append(check)

    typora_path = _config_home() / "Typora/themes/base.user.css"
    if "typora.desktop" in visible_ids:
        css = _read_text(typora_path) or ""
        for selector, label, family in (
            (r"body\s*\{([^}]*)\}", "Typora document font family", system_family),
            (r"#write\s*,\s*#write\s*\*\s*\{([^}]*)\}", "Typora writing canvas font family", terminal_family),
        ):
            block = re.search(selector, css, re.IGNORECASE | re.DOTALL)
            family_match = re.search(r"font-family\s*:\s*['\"]?([^;'\"]+)", block.group(1), re.IGNORECASE) if block else None
            actual = family_match.group(1).strip() if family_match else None
            checks.append(_check("font", label, family, actual, f"{typora_path}: {selector}",
                                 pending_restart=False))
        size_match = re.search(r"#write\s*,\s*#write\s*\*\s*\{([^}]*)\}", css, re.IGNORECASE | re.DOTALL)
        size_value = re.search(r"font-size\s*:\s*([0-9.]+)\s*(pt|px)", size_match.group(1), re.IGNORECASE) if size_match else None
        actual_size = None
        if size_value:
            amount = float(size_value.group(1))
            actual_size = amount if size_value.group(2).casefold() == "pt" else amount * 0.75
        checks.append(_check("font", "Typora writing canvas size (pt)", terminal_size, actual_size,
                             f"{typora_path}: no explicit writing-canvas point size means app/theme default",
                             pending_restart=False))

    brave_path = _config_home() / "BraveSoftware/Brave-Browser/Default/Preferences"
    if "brave-browser.desktop" in visible_ids:
        brave = _json_file(brave_path)
        for role, label, family in (
            ("standard", "Brave web standard font family", system_family),
            ("sansserif", "Brave web sans-serif font family", system_family),
            ("fixed", "Brave web fixed-width font family", terminal_family),
        ):
            actual = _nested(brave, "webkit", "webprefs", "fonts", role, "Zyyy")
            checks.append(_check("font", label, family, actual, f"{brave_path}: webkit.webprefs.fonts.{role}.Zyyy",
                                 pending_restart=False))
        for key, label, size in (
            ("default_font_size", "Brave default web text size (CSS px; 12 pt ≈ 16 px)", editor_size_px),
            ("default_fixed_font_size", "Brave fixed-width web text size (CSS px)", mono_size_px),
        ):
            actual = _nested(brave, "webkit", "webprefs", key)
            checks.append(_check("font", label, size, actual, f"{brave_path}: webkit.webprefs.{key}",
                                 pending_restart=False))

    if "obsidian.desktop" in visible_ids:
        for label, family in (
            ("Obsidian interface font family", system_family),
            ("Obsidian note font family", system_family),
            ("Obsidian monospace font family", terminal_family),
        ):
            checks.append(_check(
                "font", label, family, None,
                "active Obsidian vault .obsidian/appearance.json; no active vault or appearance file was resolved",
                available=False,
            ))

    for client in (app_inventory or {}).get("mailClients", []):
        if client.get("name") != "Betterbird" or client.get("status") != "installed":
            continue
        prefs_name = str(client.get("prefsPath") or "")
        prefs_path = HOME / prefs_name
        if not prefs_name or prefs_path.is_symlink():
            prefs_path = Path("/") / "__look_and_feel_missing_betterbird_prefs__"
        evidence = f"~/{prefs_name} (selected Betterbird profile preferences)"
        betterbird_pending_restart = _process_started_before(prefs_path, "betterbird", "betterbird-bin")
        for key, label, wanted in (
            ("font.name.sans-serif.x-western", "Betterbird message font family", system_family),
            ("font.size.variable.x-western", "Betterbird variable font size (pt)", int(system_size)),
            ("msgcompose.font_face", "Betterbird composition font family", system_family),
        ):
            check = _check("font", label, wanted, _gecko_pref(prefs_path, key), f"{evidence}: {key}",
                           pending_restart=betterbird_pending_restart)
            if check["state"] == "pending-restart":
                check["stateDetail"] = "prefs.js timestamp is newer than process start; Betterbird may have reloaded or written it, so restart may be needed"
                check["runtimeProof"] = "timestamp comparison only; process reload and rendered text are not inspected"
            checks.append(check)

    if str(expected.get("themeMode", "")) == "automatic" and expected.get("appliedTheme"):
        selected_theme = str(expected["appliedTheme"])
        theme_reason = "last one-time Omarchy theme Apply; future automatic transitions are not scheduled"
    else:
        selected_theme, theme_reason = _theme_mode_expected(
            str(expected.get("themeMode", "")),
            str(expected.get("lightTheme", "")),
            str(expected.get("darkTheme", "")),
        )
    actual_theme = _read_text(HOME / ".local/state/omarchy/current/theme.name")
    expected_theme = selected_theme.casefold().replace(" ", "-") if selected_theme else None
    actual_theme_value = actual_theme.strip().casefold() if actual_theme else None
    theme_check = _check("theme", "active Omarchy theme", expected_theme, actual_theme_value,
                          "~/.local/state/omarchy/current/theme.name", available=expected_theme is not None, effective_setting=True)
    theme_check["detail"] = theme_reason
    checks.append(theme_check)
    current_theme_path = HOME / ".local/state/omarchy/current/theme"
    active_palette = _read_text(current_theme_path / "colors.toml")
    active_palette_digest = hashlib.sha256(active_palette.encode("utf-8")).hexdigest() if active_palette is not None else None
    expected_target = None
    if selected_theme:
        theme_slug = selected_theme.casefold().replace(" ", "-")
        # omarchy-theme-set copies the system tree first and then overlays the
        # user's same-name theme, so a user colors.toml takes precedence.
        for base in (_config_home() / "omarchy/themes", _omarchy_root() / "themes"):
            candidate = base / theme_slug
            if candidate.is_dir():
                expected_palette = _read_text(candidate / "colors.toml")
                if expected_palette is not None:
                    expected_target = hashlib.sha256(expected_palette.encode("utf-8")).hexdigest()
                    break
    palette_check = _check("theme", "active theme palette", expected_target, active_palette_digest,
                           "SHA-256 of selected theme colors.toml vs ~/.local/state/omarchy/current/theme/colors.toml",
                           available=expected_target is not None)
    palette_check["runtimeProof"] = "active palette-file readback only; not proof all theme hooks or application setters succeeded"
    checks.append(palette_check)

    expected_background_path = str(expected.get("background", ""))
    background_link = HOME / ".local/state/omarchy/current/background"
    try:
        actual_background_path = str(background_link.resolve(strict=True)) if background_link.is_symlink() else None
    except OSError:
        actual_background_path = None
    expected_background_digest = _file_sha256(Path(expected_background_path)) if expected_background_path else None
    actual_background_digest = _file_sha256(Path(actual_background_path)) if actual_background_path else None
    background_check = _check(
        "background", "active Omarchy background", expected_background_digest,
        actual_background_digest,
        f"{background_link} resolved image SHA-256; compares image content so theme-switch preservation copies remain equivalent",
        available=expected_background_digest is not None,
        effective_setting=True,
    )
    background_check["expectedPath"] = expected_background_path or None
    background_check["actualPath"] = actual_background_path
    background_check["runtimeProof"] = "active background symlink and image content readback; rendered wallpaper is not inspected"
    checks.append(background_check)

    unlock = str(expected.get("unlockTheme", ""))
    current_unlock = _run(["omarchy-plymouth-current"])
    expected_unlock = unlock.casefold().replace(" ", "-") if unlock else None
    checks.append(_check("unlock", "active Plymouth unlock design", expected_unlock,
                         current_unlock.casefold() if current_unlock else None,
                         "omarchy-plymouth-current (compares active Plymouth logo image with Omarchy unlock designs)"))
    checks[-1]["runtimeProof"] = "installed Plymouth logo readback only; initramfs and next-boot image are not inspected"

    states = ("effective-setting", "persisted", "pending-restart", "mismatched", "unobservable")
    counts = {group: {state: 0 for state in states} for group in ("font", "terminal", "theme", "background", "unlock")}
    for check in checks:
        counts[check["group"]][check["state"]] += 1
    summaries = {}
    for group, values in counts.items():
        total = sum(values.values())
        summaries[group] = f"{total} checks"
        details = [f"{values[state]} {state}" for state in states if values[state]]
        if details:
            summaries[group] += ": " + ", ".join(details)
    visible = [
        app for app in (app_inventory or {}).get("desktopApplications", [])
        if app.get("launchable") is not False and not app.get("hidden") and not app.get("noDisplay")
    ]
    framework_identified = sum(app.get("framework") != "not-yet-identified" for app in visible)
    inferred = sum(app.get("review") == "shared-surface-inferred" for app in visible)
    coverage = {
        "scope": "unique launchable visible desktop entries in the scanned XDG application directories; excludes unlaunched package executables and hidden helpers",
        "identified": framework_identified,
        "denominator": len(visible),
        "percent": round(100 * framework_identified / len(visible), 1) if visible else 0.0,
        "unidentified": len(visible) - framework_identified,
        "inferredSharedSurface": inferred,
        "meaning": "launcher framework labels only; not installed-app discovery coverage, font-control coverage, or proof that a font is applied/rendered",
    }
    candidate_coverage = (app_inventory or {}).get("applicationCandidateCoverage", {})
    state_totals = {state: sum(values[state] for values in counts.values()) for state in states}
    if state_totals["mismatched"]:
        overall = "mismatched"
    elif state_totals["unobservable"]:
        overall = "unobservable"
    elif state_totals["pending-restart"]:
        overall = "pending-restart"
    elif state_totals["effective-setting"]:
        overall = "effective-setting"
    elif state_totals["persisted"]:
        overall = "persisted"
    else:
        overall = "unobservable"
    return {
        "schemaVersion": 1,
        "checkedAt": datetime.now().astimezone().isoformat(),
        "overall": overall,
        "summary": summaries,
        "stateCounts": state_totals,
        "launcherFrameworkIdentification": coverage,
        "applicationCandidateCoverage": candidate_coverage,
        "checks": checks,
        "caveat": "This compares selected values with readable configuration and installed Omarchy/Plymouth state; it does not prove the plugin caused those values, inspect rendered pixels, or confirm an initramfs/next-boot image. Open applications may need restart.",
    }
