#!/usr/bin/env python3
"""Discover desktop applications and map them to font-control surfaces."""

from __future__ import annotations

import os
import re
import shutil
import json
import stat
import tempfile
import shlex
import functools
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from mail_font_adapters import discover_mail_profiles, mail_client_definition


HOME = Path.home()
_data_home = Path(os.environ.get("XDG_DATA_HOME", str(HOME / ".local/share")))
DATA_HOME = _data_home if _data_home.is_absolute() else HOME / ".local/share"
_data_dirs = os.environ.get("XDG_DATA_DIRS", "") or "/usr/local/share:/usr/share"
DATA_DIRS = tuple(Path(part) for part in _data_dirs.split(":") if part and Path(part).is_absolute())
APPLICATION_DIRS = (DATA_HOME / "applications", *(root / "applications" for root in DATA_DIRS))
APPSTREAM_DIRS = (DATA_HOME / "metainfo", DATA_HOME / "appdata", *(root / name for root in DATA_DIRS for name in ("metainfo", "appdata")))
ADDITIONAL_APPLICATION_DIRS = (
    Path("/var/lib/flatpak/exports/share/applications"),
    HOME / ".local/share/flatpak/exports/share/applications",
    Path("/var/lib/snapd/desktop/applications"),
)

TERMINALS = {
    "Alacritty.desktop": ("Alacritty", "~/.config/alacritty/alacritty.toml"),
    "foot.desktop": ("Foot", "~/.config/foot/foot.ini"),
    "footclient.desktop": ("Foot", "~/.config/foot/foot.ini"),
    "foot-server.desktop": ("Foot", "~/.config/foot/foot.ini"),
    "com.mitchellh.ghostty.desktop": ("Ghostty", "~/.config/ghostty/config"),
    "kitty.desktop": ("Kitty", "~/.config/kitty/kitty.conf"),
    "kitty-open.desktop": ("Kitty", "~/.config/kitty/kitty.conf"),
    "org.wezfurlong.wezterm.desktop": ("WezTerm", "~/.config/wezterm/wezterm.lua"),
}

APP_OVERRIDES: dict[str, dict[str, object]] = {
    "cursor.desktop": {
        "framework": "Electron/Chromium",
        "monospaceUse": "primary-and-integrated-terminal",
        "fontRoles": ["system-ui", "editor-monospace", "integrated-terminal-monospace", "chat-ui-font", "chat-code-font"],
        "controlPoints": [
            "~/.config/Cursor/User/settings.json: editor.fontFamily, editor.fontSize",
            "~/.config/Cursor/User/settings.json: terminal.integrated.fontFamily, terminal.integrated.fontSize",
            "~/.config/Cursor/User/settings.json: chat.fontFamily and chat.editor.fontFamily (chat UI/code surfaces; verify Cursor version support)",
        ],
        "localEvidence": ["Cursor editor, integrated terminal, and chat surfaces have separate font settings; current values are read from User/settings.json."],
        "review": "app-settings-located; UI-chrome-control-unconfirmed",
    },
    "typora.desktop": {
        "framework": "Electron/Chromium",
        "monospaceUse": "entire-markdown-editor-and-code",
        "fontRoles": ["system-ui", "markdown-editor-monospace", "markdown-code-monospace"],
        "controlPoints": [
            "~/.config/Typora/conf/conf.user.json: defaultFontFamily.standard/serif/sansSerif/monospace",
            "~/.config/Typora/themes/alucard.css: active local theme candidate with body font-family declarations",
            "~/.config/Typora/themes/dracula.css: installed theme CSS with --monospace and code-block overrides",
            "~/.config/Typora/themes/base.user.css: reversible cross-theme prose and code font override",
            "Typora theme CSS: body/font-family and --monospace; base.user.css and <theme>.user.css override theme CSS",
        ],
        "localEvidence": ["Typora configuration, active theme CSS, and user CSS are inspected as separate font layers; current rules are listed from local files."],
        "review": "user-font-override-recorded; runtime-after-restart-pending",
    },
    "obsidian.desktop": {
        "framework": "Electron/Chromium",
        "monospaceUse": "markdown-code-and-editor",
        "fontRoles": ["system-ui", "markdown-body-font", "markdown-code-monospace"],
        "controlPoints": [
            "Vault .obsidian/appearance.json: interfaceFontFamily, textFontFamily, monospaceFontFamily",
            "Vault .obsidian/snippets/*.css and community themes can override CSS font-family",
        ],
        "localEvidence": ["App profile is present; active vault appearance files were not identified in this scan."],
        "review": "control-points-identified; active-vault-pending",
    },
    "brave-browser.desktop": {
        "framework": "Chromium browser",
        "monospaceUse": "web-content-fixed-width",
        "fontRoles": ["browser-ui-system", "web-standard-font", "web-monospace-font"],
        "controlPoints": [
            "~/.config/BraveSoftware/Brave-Browser/Default/Preferences: webkit.webprefs.fonts and default_font_size",
            "Brave profile Preferences: webkit.webprefs.fonts and default_font_size",
            "Site CSS can override browser defaults; browser chrome is a separate surface.",
        ],
        "localEvidence": ["Default profile font keys are inspected without copying the browser Preferences file into the inventory."],
        "review": "profile-preferences-inspected; site-css-remains-independent",
    },
    "com.obsproject.Studio.desktop": {
        "framework": "Qt 6 application",
        "monospaceUse": "not-primary-in-default-ui",
        "fontRoles": ["system-ui"],
        "controlPoints": [
            "Qt 6 application font from the active Qt platform-theme integration (qt6ct general font when that integration is active)",
            "~/.config/obs-studio/user.ini [Appearance]: FontScale controls UI font size; OBS Appearance has no font-family selector",
            "OBS theme/style can affect colors and widget appearance independently of the font family",
        ],
        "localEvidence": [
            "Installed OBS binary links Qt 6 Widgets/Gui/Core.",
            "Local OBS user.ini stores Appearance FontScale=10 and no font family setting; the Appearance UI exposes Theme, Style, Font Size, and Density.",
            "Whether this running desktop session supplies qt6ct as the active Qt platform theme is not established.",
        ],
        "review": "qt6-font-inheritance; platform-theme-reach-pending",
    },
    "gparted.desktop": {
        "framework": "GTK 3 application (privileged launcher)",
        "monospaceUse": "not-primary-in-default-ui",
        "fontRoles": ["system-ui"],
        "controlPoints": [
            "GTK 3 user settings apply only if the privileged process retains the user's session settings; the launcher may cross a pkexec/root boundary",
            "~/.config/gtk-3.0/settings.ini: gtk-font-name for unprivileged GTK 3 apps",
            "Root's separate GTK settings may control privileged UI if the privilege launcher resets the user environment",
        ],
        "localEvidence": ["GParted's desktop entry invokes a privileged launcher; the effective font source depends on its runtime privilege environment."],
        "review": "privileged-runtime-font-source-unverified",
    },
    "nvim.desktop": {
        "framework": "terminal TUI",
        "monospaceUse": "inherited-from-host-terminal",
        "fontRoles": ["terminal-monospace"],
        "controlPoints": [
            "~/.config/nvim/init.lua: GUI font options if a GUI frontend is used",
            "Neovim TUI has no independent glyph font; the host terminal draws its cells.",
            "GUI frontends can expose guifont, but the installed desktop launcher runs nvim in a terminal.",
        ],
        "localEvidence": ["~/.config/nvim/init.lua has no guifont setting; the active launcher is nvim %F."],
        "review": "terminal-inheritance-confirmed",
    },
    "walker.desktop": {
        "framework": "GTK 4 launcher",
        "monospaceUse": "search-results-and-optional-terminal-provider",
        "fontRoles": ["system-ui", "theme-css-fonts", "optional-monospace-content"],
        "controlPoints": [
            "~/.config/walker/config.toml: selected theme",
            "~/.config/walker/themes/<theme>/style.css: GTK CSS font-family/font-size",
            "~/.config/walker/themes/<theme>/*.xml: provider-specific layout and labels",
        ],
        "localEvidence": ["Walker is not installed on this machine; its support surface is catalogued for future discovery."],
        "review": "not-installed; official-theme-control-points-reviewed",
        "reference": "https://walkerlauncher.com/docs/theming",
    },
}

CLI_TUIS = (
    ("nvim", "Neovim", "inherited-from-host-terminal"),
    ("vim", "Vim", "inherited-from-host-terminal"),
    ("nano", "GNU nano", "inherited-from-host-terminal"),
    ("emacs", "Emacs terminal UI", "inherited-from-host-terminal"),
    ("hx", "Helix", "inherited-from-host-terminal"),
    ("micro", "Micro", "inherited-from-host-terminal"),
    ("btop", "btop", "inherited-from-host-terminal"),
    ("yazi", "Yazi", "inherited-from-host-terminal"),
    ("rmpc", "rmpc", "inherited-from-host-terminal"),
    ("tmux", "tmux", "inherited-from-host-terminal"),
    ("opencode", "OpenCode TUI", "inherited-from-host-terminal"),
    ("bluetui", "Bluetui", "inherited-from-host-terminal"),
    ("lazydocker", "lazydocker", "inherited-from-host-terminal"),
    ("lazygit", "lazygit", "inherited-from-host-terminal"),
    ("impala", "Impala Bluetooth TUI", "inherited-from-host-terminal"),
    ("cava", "CAVA audio visualizer", "inherited-from-host-terminal"),
    ("caligula", "Caligula disk imaging TUI", "inherited-from-host-terminal"),
)

# Applications whose launchers deliberately hide the actual UI runtime behind
# shell scripts, terminal wrappers, or package-specific names. Keep this list
# about framework identity; font-control confidence remains a separate review.
EXEC_FRAMEWORKS = {
    "blender": "Blender custom UI",
    "dua": "terminal TUI",
    "element-desktop": "Electron/Chromium",
    "fluid1.3": "FLTK application",
    "freecad": "Qt application",
    "freerouting": "Java desktop application",
    "gscan2pdf": "GTK 3 application",
    "gerbview": "wxWidgets application",
    "pcb_calculator": "wxWidgets application",
    "pcbnew": "wxWidgets application",
    "eeschema": "wxWidgets application",
    "imv": "Wayland image viewer",
    "jconsole": "Java desktop application",
    "jshell": "terminal TUI",
    "lstopo": "native graphical application",
    "mpv": "native media-player UI",
    "mplab_ipe": "Java desktop application",
    "mullvad-vpn": "Electron/Chromium",
    "omarchy-launch-docker-tui": "terminal TUI",
    "onlyoffice-desktopeditors": "Electron/Chromium application",
    "phoronix-test-suite": "browser-based application",
    "rmpc": "terminal TUI",
    "spotify": "Electron/Chromium",
    "vncviewer": "native X11 application",
    "yazi-remote": "terminal TUI",
    "yazi-file-manager": "terminal TUI",
}


def _desktop_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    in_entry = False
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return fields
    for line in lines:
        if line.startswith("["):
            in_entry = line == "[Desktop Entry]"
            continue
        if not in_entry or not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in {"Name", "Exec", "TryExec", "Categories", "Type", "Terminal", "NoDisplay", "Hidden"}:
            fields[key] = value
    return fields


def _terminal_exec_target(parts: list[str]) -> list[str]:
    """Unwrap xdg-terminal-exec's command while respecting its option values."""
    index = 1
    while index < len(parts):
        token = parts[index]
        if token == "--":
            return parts[index + 1:]
        if token in {"-e", "--exec", "--command"}:
            return parts[index + 1:]
        if token in {"--app-id", "--title", "--working-directory", "--dir"}:
            index += 2
        elif token.startswith(("--app-id=", "--title=", "--working-directory=", "--dir=")):
            index += 1
        elif token.startswith("-"):
            index += 1
        else:
            # xdg-terminal-exec accepts a command without an explicit -e.
            return parts[index:]
    return []


def _exec_command(exec_line: str) -> str:
    """Keep the launcher executable while omitting arguments, URLs, and paths."""
    try:
        parts = shlex.split(exec_line)
    except ValueError:
        parts = exec_line.split()
    index = 0
    while index < len(parts):
        part = parts[index]
        if Path(part).name in {"env", "pkexec", "sudo", "doas", "exec"} or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", part) or part.startswith("%"):
            index += 1
            continue
        if part in {"-u", "--unset", "-C", "--chdir"}:
            index += 2
            continue
        if part.startswith("-") and index == 1 and Path(parts[0]).name == "env":
            index += 1
            continue
        if part == "--":
            index += 1
            continue
        if part == "xdg-terminal-exec":
            tail = _terminal_exec_target(parts[index:])
            return _exec_command(shlex.join(tail)) if tail else "xdg-terminal-exec"
        if part in {"sh", "bash", "dash"} and index + 2 < len(parts) and parts[index + 1] in {"-c", "-lc", "-ec"}:
            try:
                nested = shlex.split(parts[index + 2])
            except ValueError:
                nested = []
            while nested and Path(nested[0]).name in {"exec", "env"}:
                nested.pop(0)
            return _exec_command(shlex.join(nested)) if nested else Path(part).name
        return Path(part).name
    return ""


def _resolved_exec(exec_line: str) -> Path | None:
    """Resolve a simple desktop Exec target, unwrapping common env/pkexec/shell launchers."""
    try:
        parts = shlex.split(exec_line)
    except ValueError:
        parts = exec_line.split()
    index = 0
    while index < len(parts):
        part = parts[index]
        if Path(part).name in {"env", "pkexec", "sudo", "doas", "exec"}:
            index += 1
            continue
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", part) or part.startswith("%"):
            index += 1
            continue
        if part in {"-u", "--unset", "-C", "--chdir"}:
            index += 2
            continue
        if part.startswith("-") and index == 1 and Path(parts[0]).name == "env":
            index += 1
            continue
        if part == "--":
            index += 1
            continue
        if part == "xdg-terminal-exec":
            tail = _terminal_exec_target(parts[index:])
            return _resolved_exec(shlex.join(tail)) if tail else None
        if part in {"sh", "bash", "dash"} and index + 2 < len(parts) and parts[index + 1] in {"-c", "-lc", "-ec"}:
            try:
                nested = shlex.split(parts[index + 2])
            except ValueError:
                nested = []
            while nested and Path(nested[0]).name in {"exec", "env"}:
                nested.pop(0)
            if not nested:
                return None
            return _resolved_exec(shlex.join(nested))
        if part == "flatpak":
            return None
        candidate = Path(part)
        resolved = candidate if candidate.is_absolute() else (Path(shutil.which(part)) if shutil.which(part) else None)
        return resolved if resolved and resolved.is_file() else None
    return None


@functools.lru_cache(maxsize=256)
def _binary_toolkit(path: str) -> str | None:
    """Infer toolkit from ELF NEEDED metadata without launching the application."""
    readelf = shutil.which("readelf")
    if not readelf:
        return None
    try:
        result = subprocess.run([readelf, "-d", path], capture_output=True, text=True, timeout=2, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return _script_toolkit(Path(path))
    needed = result.stdout
    if "libflutter_linux_gtk.so" in needed:
        return "Flutter"
    if "libgtk-4.so" in needed:
        return "GTK 4"
    if "libgtk-3.so" in needed:
        return "GTK 3"
    if "libgtk-x11-2.0.so" in needed or "libgtk-2.0.so" in needed:
        return "GTK 2"
    if "libQt6Widgets.so" in needed or "libQt6Gui.so" in needed:
        return "Qt 6"
    if "libQt5Widgets.so" in needed or "libQt5Gui.so" in needed:
        return "Qt 5"
    return _script_toolkit(Path(path))


@functools.lru_cache(maxsize=256)
def _script_toolkit(path: Path) -> str | None:
    """Read short launcher scripts for explicit toolkit/runtime imports."""
    try:
        if path.stat().st_size > 1024 * 1024:
            return None
        raw = path.read_bytes()
        if b"\0" in raw:
            return None
        text = raw.decode("utf-8", "replace")
    except OSError:
        return None
    if re.search(r"(?:gi://Gtk\?version=4\.0|Gtk-4\.0|PySide6|PyQt6)", text, re.IGNORECASE):
        return "GTK 4" if "Gtk" in text else "Qt 6"
    if re.search(r"(?:Gtk3::|Gtk-3\.0|gi://Gtk\?version=3\.0|PySide2|PyQt5)", text, re.IGNORECASE):
        return "GTK 3" if "Gtk" in text else "Qt 5"
    if re.search(r"\bjava\b.*(?:-jar|--module|--class-path)", text):
        return "Java"
    return None


def _framework(app_id: str, name: str, exec_line: str, categories: set[str]) -> str:
    if app_id in TERMINALS or "TerminalEmulator" in categories:
        return "terminal-emulator"
    if app_id in APP_OVERRIDES:
        return str(APP_OVERRIDES[app_id]["framework"])
    if "ConsoleOnly" in categories or fields_terminal(exec_line):
        return "terminal TUI"
    if _exec_command(exec_line).casefold() == "omarchy-launch-browser":
        return "browser dispatcher"
    if "omarchy-launch-webapp" in exec_line or "omarchy-webapp-handler" in exec_line:
        return "Chromium web app"
    if "--app-id=" in exec_line and "brave" in exec_line.casefold():
        return "Chromium web app"
    command = _exec_command(exec_line).casefold()
    if command in EXEC_FRAMEWORKS and not EXEC_FRAMEWORKS[command].startswith(("Qt", "GTK")):
        return EXEC_FRAMEWORKS[command]
    if command in {"electron", "teams-for-linux", "signal-desktop", "obsidian", "cursor"} or re.fullmatch(r"electron[0-9]+", command):
        return "Electron/Chromium"
    executable = _resolved_exec(exec_line)
    if executable:
        try:
            executable = executable.resolve(strict=True)
        except (OSError, RuntimeError):
            executable = None
    if executable and ((executable.parent / "resources/app.asar").is_file()
                       or (executable.parent / "lib/resources/app.asar").is_file()):
        return "Electron/Chromium"
    toolkit = _binary_toolkit(str(executable)) if executable else None
    if toolkit:
        return f"{toolkit} application"
    command = _exec_command(exec_line).casefold()
    if command in EXEC_FRAMEWORKS:
        return EXEC_FRAMEWORKS[command]
    if command == "flatpak" or "flatpak run" in exec_line.casefold():
        lowered = app_id.casefold()
        if lowered.startswith(("org.kde.", "io.github.ra3xdh.qucs_s")):
            return "Qt 6 application"
        if lowered.startswith("org.gnome."):
            return "GTK 4 application"
    if "GTK" in categories or app_id in {"pcmanfm.desktop", "typora.desktop"}:
        return "GTK/GTK-derived"
    if "Qt" in categories or "KDE" in categories:
        return "Qt"
    lowered = (app_id + " " + name + " " + exec_line).casefold()
    if any(term in lowered for term in ("electron", "teams-for-linux", "signal-desktop", "obsidian", "cursor")):
        return "Electron/Chromium"
    return "not-yet-identified"


def fields_terminal(exec_line: str) -> bool:
    command = _exec_command(exec_line).casefold()
    return command in EXEC_FRAMEWORKS and EXEC_FRAMEWORKS[command] == "terminal TUI"


def _generic_surface(framework: str) -> tuple[str, list[str]]:
    if framework.startswith("GTK"):
        label = framework if framework != "GTK/GTK-derived" else "GTK"
        return f"{label} system font + Fontconfig generic monospace", [
            "~/.config/gtk-3.0/settings.ini: gtk-font-name",
            "~/.config/gtk-4.0/settings.ini: gtk-font-name",
            "GSettings org.gnome.desktop.interface font-name/monospace-font-name",
            "~/.config/gtk-3.0/gtk.css and GTK theme CSS may override scoped widgets",
        ]
    if framework.startswith("Qt"):
        label = framework if framework != "Qt" else "Qt"
        return f"{label} application font + Fontconfig fallback", [
            "~/.config/qt5ct/qt5ct.conf [Fonts]: general/fixed when qt5ct is active",
            "~/.config/qt6ct/qt6ct.conf [Fonts]: general/fixed when qt6ct is active",
            "Application QFont/QSS can override platform defaults; active integration is per-process",
        ]
    if framework == "Chromium web app":
        return "underlying browser profile + site CSS", [
            "Browser standard/fixed font preferences affect web content defaults",
            "Web application CSS can override browser font defaults",
        ]
    if framework == "Chromium browser":
        return "browser profile + site CSS", [
            "Profile webprefs controls standard/serif/sans-serif/fixed content fonts",
            "Browser UI and page content are separate; page CSS can override defaults",
        ]
    if framework == "browser dispatcher":
        return "configured default browser", [
            "Omarchy routes this hidden launcher to the current x-scheme-handler/https browser; inspect that browser's own profile for font settings.",
            "This dispatcher has no independent browser rendering surface.",
        ]
    if framework == "Electron/Chromium":
        return "application-specific Electron settings or CSS", [
            "Inspect app settings for editor.fontFamily/fontSize and app-owned CSS",
            "Electron chrome does not imply that the GTK system font controls app content",
        ]
    if framework.startswith("Electron/Chromium"):
        return "application-specific Electron settings or CSS", [
            "Inspect app settings for editor.fontFamily/fontSize and app-owned CSS",
            "Electron chrome does not imply that the GTK system font controls app content",
        ]
    if framework.startswith("Flutter"):
        return "application-owned Flutter widgets", ["Flutter text styles need an application-specific adapter; GTK linkage only supplies the window shell."]
    if framework == "terminal TUI":
        return "host terminal font", ["The host terminal draws all text for this terminal UI."]
    if framework == "Java desktop application":
        return "Java UI toolkit plus Fontconfig", [
            "Java Swing/JavaFX may use app-specific UI defaults; inspect the application's own font preferences",
            "Fontconfig provides glyph fallback; toolkit identification alone does not prove family/size inheritance",
        ]
    if framework == "wxWidgets application":
        return "wxWidgets platform-native controls", [
            "On Linux, wxWidgets commonly uses GTK controls; runtime backend and app-specific editor fonts still require review",
        ]
    if framework == "FLTK application":
        return "FLTK application font settings", [
            "FLTK UI fonts can be selected by the application; no shared GTK/Qt font adapter is assumed",
        ]
    if framework == "Blender custom UI":
        return "Blender preferences", [
            "Blender Preferences > Interface > Resolution Scale and custom interface font slots",
        ]
    if framework == "native media-player UI":
        return "application OSD font settings", ["mpv config: osd-font and osd-font-size; subtitle font is a separate role"]
    if framework in {"Wayland image viewer", "native X11 application", "native graphical application"}:
        return "application-specific graphical controls", [
            "The display backend is identified; inspect the app's own font controls before claiming family/size support",
        ]
    if framework == "browser-based application":
        return "browser-rendered application", [
            "Browser font defaults may be inherited; web content CSS can override them",
        ]
    if framework == "terminal-emulator":
        return "terminal-specific configuration", []
    return "platform/app-specific control point not yet identified", [
        "Inspect the application UI toolkit and its own font settings before enabling an adapter",
    ]


def _local_config_files(controls: list[str]) -> list[dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    for control in controls:
        candidate = control.split(":", 1)[0].strip()
        if not candidate.startswith("~/") or "<" in candidate:
            continue
        path = HOME / candidate[2:]
        if str(path) in found:
            continue
        try:
            info = path.lstat()
        except OSError:
            found[str(path)] = {"path": candidate, "exists": False, "fontLines": []}
            continue
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_size > 1024 * 1024:
            continue
        if path.name == "Preferences":
            found[str(path)] = {"path": candidate, "exists": True, "fontLines": ["Profile JSON inspected via selected font keys; raw profile data omitted."]}
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        font_lines = [line.strip()[:240] for line in lines if re.search(r"font|monospace|fixed", line, re.IGNORECASE)][:24]
        found[str(path)] = {"path": candidate, "exists": True, "fontLines": font_lines}
    return list(found.values())


def _font_line_evidence(paths: tuple[Path, ...]) -> list[str]:
    evidence: list[str] = []
    for path in paths:
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_size > 1024 * 1024:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if re.search(r"font|monospace|fixed", line, re.IGNORECASE):
                evidence.append(f"{path}: {line.strip()[:180]}")
                if len(evidence) >= 32:
                    return evidence
    return evidence


def _gsettings_font_evidence() -> list[str]:
    result = []
    for key in ("font-name", "document-font-name", "monospace-font-name"):
        try:
            probe = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", key], capture_output=True, text=True, timeout=2, check=False)
        except (OSError, subprocess.TimeoutExpired):
            result.append(f"gsettings {key}: unavailable")
            continue
        value = probe.stdout.strip() if probe.returncode == 0 else "unavailable"
        result.append(f"gsettings {key}: {value}")
    return result


def _run_readonly(command: str, *args: str, timeout: float = 8) -> subprocess.CompletedProcess[str] | None:
    executable = shutil.which(command)
    if not executable:
        fallback = Path("/usr/bin") / command
        executable = str(fallback) if fallback.is_file() and os.access(fallback, os.X_OK) else None
    if not executable:
        return None
    try:
        return subprocess.run([executable, *args], capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _package_inventory() -> dict[str, object]:
    """Read local pacman and available cross-package-manager app inventories."""
    all_result = _run_readonly("pacman", "-Q", timeout=15)
    foreign_result = _run_readonly("pacman", "-Qm", timeout=15)
    packages = []
    if all_result and all_result.returncode == 0:
        for line in all_result.stdout.splitlines():
            fields = line.rsplit(" ", 1)
            if len(fields) == 2:
                packages.append({"name": fields[0], "version": fields[1]})
    foreign = set(foreign_result.stdout.splitlines()) if foreign_result and foreign_result.returncode == 0 else set()
    # pacman -Qm emits "package version" lines, while pacman -Qo below
    # returns only the package name. Keep the display records and compare names.
    foreign_names = {line.rsplit(" ", 1)[0] for line in foreign if " " in line}
    flatpak_result = _run_readonly("flatpak", "list", "--app", "--columns=application,name", timeout=15)
    snap_result = _run_readonly("snap", "list", timeout=15)
    flatpak_apps = []
    flatpak_lines = [line for line in flatpak_result.stdout.splitlines() if line.strip()] if flatpak_result and flatpak_result.returncode == 0 else []
    seen_flatpak_ids: set[str] = set()
    for line in flatpak_lines:
        fields = line.split("\t", 1) if "\t" in line else line.split(None, 1)
        app_id = fields[0].strip()
        identity = app_id.casefold().removesuffix(".desktop")
        if not app_id or identity == "application" or identity in seen_flatpak_ids:
            continue
        seen_flatpak_ids.add(identity)
        app_name = fields[1].strip() if len(fields) > 1 else app_id
        if app_name.casefold() == "name":
            app_name = app_id
        flatpak_apps.append({"id": app_id, "name": app_name})
    snap_names = []
    if snap_result and snap_result.returncode == 0:
        snap_names = [line.split()[0] for line in snap_result.stdout.splitlines()[1:] if line.split()]
    return {
        "pacman": {
            "status": "available" if all_result and all_result.returncode == 0 else "unavailable",
            "installedPackageCount": len(packages),
            "foreignPackageCount": len(foreign),
            "foreignPackages": sorted(foreign),
            "foreignPackageNames": sorted(foreign_names),
            "packages": packages,
            "foreignMeaning": "not found in currently configured sync repositories; may include AUR/yay, pacman -U, manually built, or formerly official packages; exact install method is not retained by pacman",
        },
        "flatpak": {
            "status": "available" if flatpak_result and flatpak_result.returncode == 0 else "unavailable",
            "applications": flatpak_apps,
        },
        "snap": {
            "status": "available" if snap_result and snap_result.returncode == 0 else "unavailable",
            "applications": snap_names,
        },
    }


def _pacman_owners(paths: set[str]) -> dict[str, str]:
    pacman = shutil.which("pacman") or ("/usr/bin/pacman" if Path("/usr/bin/pacman").is_file() else None)
    if not pacman or not paths:
        return {}
    result: dict[str, str] = {}
    ordered = sorted(paths)
    for start in range(0, len(ordered), 100):
        chunk = ordered[start:start + 100]
        try:
            output = subprocess.run([pacman, "-Qo", *chunk], capture_output=True, text=True, timeout=12, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        for line in output.stdout.splitlines():
            match = re.match(r"^(.*?) is owned by (\S+) (\S+)$", line)
            if match:
                result[match.group(1)] = match.group(2)
    return result


def _package_desktop_appstream_candidates(foreign_packages: set[str]) -> dict[str, object]:
    """Find installed pacman desktop-app metadata not represented by a launcher ID."""
    paths: set[str] = set()
    for root in APPSTREAM_DIRS:
        if not root.is_dir():
            continue
        try:
            for suffix in ("*.metainfo.xml", "*.appdata.xml"):
                paths.update(str(path) for path in root.rglob(suffix) if path.is_file())
        except OSError:
            continue
    owners = _pacman_owners(paths)
    records: dict[str, dict[str, object]] = {}
    for raw_path in sorted(paths):
        owner = owners.get(raw_path)
        if not owner:
            continue
        try:
            if Path(raw_path).stat().st_size > 2 * 1024 * 1024:
                continue
            root = ET.parse(raw_path).getroot()
        except (OSError, ET.ParseError):
            continue
        components = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "component"]
        for component in components:
            if component.get("type", "") not in {"desktop", "desktop-application"}:
                continue
            app_id = ""
            app_name = ""
            launch_ids: list[str] = []
            for node in component.iter():
                tag = node.tag.rsplit("}", 1)[-1]
                if tag == "id" and node.text and not app_id:
                    app_id = node.text.strip()
                elif tag == "name" and node.text and not app_name:
                    app_name = node.text.strip()
                elif tag == "launchable" and node.get("type") == "desktop-id" and node.text:
                    launch_ids.append(node.text.strip())
            identity = app_id or next(iter(launch_ids), "")
            if not identity:
                continue
            canonical = identity.casefold().removesuffix(".desktop")
            if canonical in records:
                continue
            records[canonical] = {
                "id": app_id or identity,
                "name": app_name or identity,
                "installationSource": "pacman-foreign" if owner in foreign_packages else "pacman-sync",
                "pacmanPackage": owner,
                "framework": "not-yet-identified",
                "review": "package-owned-appstream-app-without-matched-launcher; toolkit-needs-identification",
                "appstreamId": app_id or identity,
                "launchableIds": sorted(set(launch_ids)),
                "metadataFile": raw_path,
            }
    return {
        "status": "scanned" if shutil.which("pacman") or Path("/usr/bin/pacman").is_file() else "unavailable",
        "applications": list(records.values()),
        "metadataFilesFound": len(paths),
        "packageOwnedComponents": len(records),
    }


def _app_record(app_id: str, fields: dict[str, str], source: Path, package_owner: str | None = None, foreign_packages: set[str] | None = None) -> dict[str, object]:
    name = fields.get("Name") or app_id.removesuffix(".desktop")
    categories = {value for value in fields.get("Categories", "").split(";") if value}
    exec_line = fields.get("Exec", "")
    mail = mail_client_definition(app_id)
    if mail:
        client_name = str(mail["name"])
        if mail["engine"] == "Gecko":
            profile = next((item for item in discover_mail_profiles() if item["desktopId"] == mail["canonicalId"]), None)
            prefs = profile.get("prefsPath") if profile else ""
            control = f"~/{prefs}: font.name.sans-serif.x-western (General default) and msgcompose.font_face (HTML Style)" if prefs else f"~/.thunderbird/profiles.ini: resolve the selected {client_name} profile before applying"
            override = {
                "framework": f"Gecko mail client ({client_name})",
                "monospaceUse": "message-body-fixed-width-font-only",
                "fontRoles": ["system-ui", "mail-message-body-font", "html-composition-font"],
                "controlPoints": [control, "Potential Gecko fixed-width family preference: font.name.monospace.x-western (not currently managed)", "Message-authored HTML may supply its own font styling."],
                "localEvidence": [f"{client_name} profile discovery {('resolved ' + prefs) if prefs else 'did not resolve a unique supported profile'}; preference values are not copied into the inventory."],
                "review": "profile-font-adapter-ready" if prefs else "profile-unresolved; adapter-not-applied",
            }
        else:
            override = {
                "framework": f"GTK mail client ({client_name})",
                "monospaceUse": "message-fixed-width-inherits-fontconfig-monospace",
                "fontRoles": ["system-ui", "mail-message-body-font", "mail-fixed-width-font"],
                "controlPoints": ["GSettings org.gnome.desktop.interface font-name for application/message defaults", "Fontconfig generic monospace for fixed-width message content", "Message-authored HTML may supply its own font styling."],
                "localEvidence": [f"{client_name} uses GTK system font integration; app-specific message preferences can override it."],
                "review": "gtk-system-font-surface; app-specific-overrides-pending",
            }
    else:
        override = APP_OVERRIDES.get(app_id)
    framework = str(override["framework"]) if override else _framework(app_id, name, exec_line, categories)
    if override:
        roles = list(override["fontRoles"])
        mono_use = str(override["monospaceUse"])
        controls = list(override["controlPoints"])
        evidence = list(override["localEvidence"])
        review = str(override["review"])
    elif app_id in TERMINALS:
        label, path = TERMINALS[app_id]
        roles = ["terminal-monospace", "system-ui"]
        mono_use = "primary-terminal-font"
        controls = [f"{path}: terminal font family and size"]
        if app_id == "com.mitchellh.ghostty.desktop":
            controls.append("~/.config/ghostty/look-and-feel-font.conf: managed font override")
        evidence = [f"Terminal app has a direct font config surface ({label})."]
        review = "direct-config-located"
    elif "TerminalEmulator" in categories:
        roles = ["terminal-monospace", "system-ui"]
        mono_use = "primary-terminal-font"
        controls = ["Application-specific terminal font configuration; inspect before adapter support."]
        evidence = []
        review = "terminal-app-needs-config-path-review"
    elif framework == "terminal TUI":
        roles = ["terminal-monospace"]
        mono_use = "inherited-from-host-terminal"
        controls = ["The host terminal draws this app's text; its family and size come from the terminal emulator."]
        evidence = ["Launcher command or desktop metadata identifies an interactive terminal UI."]
        review = "terminal-inheritance-confirmed"
    elif app_id.casefold().startswith("brave-") and "--app-id=" in exec_line:
        roles = ["browser-ui-system", "web-content-system", "web-content-monospace"]
        mono_use = "web-content-monospace"
        controls = ["Underlying Brave profile font preferences; web app CSS can override them."]
        evidence = ["PWA launcher resolves to Brave with a profile app-id."]
        review = "browser-inherited; web-content-css-independent"
    elif framework == "terminal TUI" or "ConsoleOnly" in categories or fields.get("Terminal", "false").casefold() == "true":
        roles = ["terminal-monospace"]
        mono_use = "inherited-from-host-terminal"
        controls = ["The application is launched in a terminal; the host terminal controls glyph family and size."]
        evidence = []
        review = "terminal-launcher-font-inherited"
    elif categories.intersection({"TextEditor", "IDE", "Development", "Programming"}):
        roles = ["system-ui", "editor-monospace"]
        mono_use = "editor-monospace"
        controls = ["App-specific editor font setting; shared toolkit controls app chrome only."]
        evidence = []
        review = "editor-font-setting-needs-app-specific-review"
    elif framework in {
        "Blender custom UI", "Java desktop application", "wxWidgets application",
        "FLTK application", "Wayland image viewer", "native X11 application",
        "native graphical application", "native media-player UI", "browser-based application",
    }:
        roles = ["system-ui"]
        mono_use = "app-specific-or-not-primary"
        generic, controls = _generic_surface(framework)
        evidence = [f"Application surface identified as {generic}; exact font controls are not yet verified."]
        review = "app-specific-font-control-needs-review"
    else:
        roles = ["system-ui"]
        mono_use = "not-primary-in-default-ui"
        generic, controls = _generic_surface(framework)
        evidence = [f"Shared surface: {generic}."]
        review = "shared-surface-inferred" if framework != "not-yet-identified" else "toolkit-needs-identification"
    if override and (framework.startswith("GTK") or framework.startswith("Qt")):
        # Keep explicit app-owned surfaces together with the inherited toolkit path.
        _, shared = _generic_surface(framework)
        controls.extend(shared)
    hidden = fields.get("Hidden", "false").casefold() == "true"
    no_display = fields.get("NoDisplay", "false").casefold() == "true"
    resolved = _resolved_exec(exec_line)
    if "omarchy-launch-webapp" in exec_line or "omarchy-webapp-handler" in exec_line or ("--app-id=" in exec_line and "brave" in exec_line.casefold()):
        installation_source = "web-app"
    elif "flatpak run" in exec_line.casefold() or "flatpak/exports" in str(source):
        installation_source = "flatpak"
    elif "snap run" in exec_line.casefold() or "/snap/" in str(source) or "snapd/desktop" in str(source):
        installation_source = "snap"
    elif re.search(r"\.appimage(?:\s|$)", exec_line, re.IGNORECASE):
        installation_source = "AppImage"
    elif package_owner:
        installation_source = "pacman-foreign" if package_owner in (foreign_packages or set()) else "pacman-sync"
    elif resolved and (str(resolved).startswith((str(HOME / ".local"), "/usr/local/", "/opt/"))):
        installation_source = "local-or-source-installed"
    else:
        installation_source = "unknown"
    return {
        "id": app_id,
        "name": name,
        "execCommand": _exec_command(exec_line),
        "installationSource": installation_source,
        "pacmanPackage": package_owner,
        "categories": sorted(categories),
        "sourceDesktopFile": str(source),
        "launchable": _try_exec_available(fields.get("TryExec", "")),
        "hidden": hidden,
        "noDisplay": no_display,
        "framework": framework,
        "fontRoles": roles,
        "monospaceUse": mono_use,
        "controlPoints": controls,
        "localConfigFiles": _local_config_files(controls),
        "localEvidence": evidence,
        "review": review,
    }


def _try_exec_available(value: str) -> bool | None:
    if not value:
        return True
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.is_file() and os.access(candidate, os.X_OK)
    return shutil.which(value) is not None


def _appimage_files() -> list[str]:
    roots = (HOME / "Applications", HOME / "AppImages", HOME / "Downloads", Path("/opt"))
    skipped = {".git", ".cache", "node_modules", ".venv", "venv", "vendor", "target"}
    found = set()
    for root in roots:
        if not root.is_dir():
            continue
        try:
            for directory, names, files in os.walk(root):
                current = Path(directory)
                depth = len(current.relative_to(root).parts)
                names[:] = [name for name in names if name not in skipped and depth < 8]
                for name in files:
                    path = current / name
                    if name.casefold().endswith(".appimage") and path.is_file() and os.access(path, os.X_OK):
                        found.add(str(path))
        except OSError:
            continue
    return sorted(found)


def _appimage_matches_launcher(path: str, launchers: list[dict[str, object]]) -> bool:
    """Avoid counting an AppImage again when a visible launcher names that app."""
    stem = re.sub(r"\.appimage$", "", Path(path).name, flags=re.IGNORECASE)
    appimage_name = re.sub(r"[^a-z0-9]", "", stem.casefold())
    for launcher in launchers:
        name = re.sub(r"[^a-z0-9]", "", str(launcher.get("name", "")).casefold())
        if not name:
            continue
        if appimage_name == name:
            return True
        if appimage_name.startswith(name):
            # Require a visible separator before a version or architecture tag.
            # This avoids treating a distinct name such as "Foo2Bar" as Foo.
            consumed = 0
            boundary = 0
            for boundary, character in enumerate(stem):
                if character.isalnum():
                    consumed += 1
                if consumed == len(name):
                    boundary += 1
                    break
            remainder = stem[boundary:]
            if re.fullmatch(r"[-_. ]+(?:v?\d+(?:[-_. ].*)?|x86_64|amd64|aarch64|arm64)", remainder, re.IGNORECASE):
                return True
    return False


def installed_font_applications() -> dict[str, object]:
    """Return all discovered desktop launchers plus installed terminal TUIs."""
    effective: dict[str, tuple[dict[str, str], Path]] = {}
    raw_count = 0
    roots = tuple(dict.fromkeys((*APPLICATION_DIRS, *ADDITIONAL_APPLICATION_DIRS)))
    for root in roots:
        if not root.is_dir():
            continue
        try:
            paths = sorted(root.rglob("*.desktop"))
        except OSError:
            continue
        raw_count += len(paths)
        for path in paths:
            app_id = path.relative_to(root).as_posix().replace("/", "-")
            effective.setdefault(app_id, (_desktop_fields(path), path))

    owners = _pacman_owners({str(resolved) for fields, _ in effective.values() if (resolved := _resolved_exec(fields.get("Exec", "")))})
    package_sources = _package_inventory()
    foreign_packages = set(package_sources["pacman"]["foreignPackageNames"])
    apps = [
        _app_record(app_id, fields, source, owners.get(str(_resolved_exec(fields.get("Exec", "")))) if _resolved_exec(fields.get("Exec", "")) else None, foreign_packages)
        for app_id, (fields, source) in sorted(effective.items(), key=lambda item: (item[1][0].get("Name", item[0]).casefold(), item[0]))
        if fields.get("Type", "Application") == "Application"
    ]
    launcher_keys = {
        app_id.casefold().removesuffix(".desktop")
        for app_id in effective
    }
    appstream_inventory = _package_desktop_appstream_candidates(foreign_packages)
    appstream_candidates = []
    for record in appstream_inventory["applications"]:
        identities = {str(record.get("appstreamId", "")).casefold().removesuffix(".desktop")}
        identities.update(str(value).casefold().removesuffix(".desktop") for value in record.get("launchableIds", []))
        if identities & launcher_keys:
            continue
        appstream_candidates.append(record)
    package_sources["pacman"]["desktopApplicationMetadata"] = {
        **appstream_inventory,
        "applications": appstream_candidates,
        "matchedLauncherRecords": len(appstream_inventory["applications"]) - len(appstream_candidates),
    }
    visible_apps = [app for app in apps if not app["hidden"] and not app["noDisplay"] and app["launchable"] is not False]
    identified_visible_apps = [app for app in visible_apps if app["framework"] != "not-yet-identified"]
    desktop_execs = {str(record["execCommand"]) for record in apps if record["execCommand"]}
    cli_apps = []
    for command, name, mono_use in CLI_TUIS:
        resolved = shutil.which(command)
        if resolved and command not in desktop_execs:
            cli_apps.append({
                "id": f"cli:{command}", "name": name, "command": resolved,
                "framework": "terminal TUI", "fontRoles": ["terminal-monospace"],
                "monospaceUse": mono_use,
                "controlPoints": ["Host terminal emulator controls glyph family and size."],
                "review": "terminal-inheritance-confirmed",
            })

    counts: dict[str, int] = {}
    for app in apps:
        state = str(app["review"])
        counts[state] = counts.get(state, 0) + 1
    candidates = list(visible_apps)
    candidate_keys = {str(app["id"]).casefold().removesuffix(".desktop") for app in candidates}
    for app in cli_apps:
        candidates.append({**app, "installationSource": "curated-cli-tui"})
        candidate_keys.add(str(app["id"]).casefold())
    source_only_apps = []
    for source, records in (("flatpak", package_sources["flatpak"]["applications"]),):
        for record in records:
            app_id = str(record.get("id", ""))
            name = str(record.get("name") or app_id)
            if app_id.casefold().removesuffix(".desktop") in candidate_keys:
                continue
            source_only_apps.append({"id": app_id, "name": name, "installationSource": source,
                                     "framework": "not-yet-identified", "review": "toolkit-needs-identification"})
            candidate_keys.add(app_id.casefold().removesuffix(".desktop"))
    if package_sources["snap"]["status"] == "available":
        for name in package_sources["snap"]["applications"]:
            if name.casefold().removesuffix(".desktop") in candidate_keys:
                continue
            source_only_apps.append({"id": name, "name": name, "installationSource": "snap",
                                     "framework": "not-yet-identified", "review": "toolkit-needs-identification"})
            candidate_keys.add(name.casefold().removesuffix(".desktop"))
    all_appimage_files = _appimage_files()
    duplicate_appimage_files = [path for path in all_appimage_files if _appimage_matches_launcher(path, visible_apps)]
    appimages = [
        {"id": f"appimage:{Path(path).name.casefold()}", "name": Path(path).stem,
         "path": path, "installationSource": "AppImage", "framework": "not-yet-identified",
         "review": "standalone-binary-found; font-controls-need-review"}
        for path in all_appimage_files if path not in duplicate_appimage_files
    ]
    candidates.extend(source_only_apps)
    candidates.extend(appstream_candidates)
    candidates.extend(appimages)
    candidate_identified = sum(app.get("framework") != "not-yet-identified" for app in candidates)
    candidate_sources: dict[str, int] = {}
    for candidate in candidates:
        source = str(candidate.get("installationSource", "unknown"))
        candidate_sources[source] = candidate_sources.get(source, 0) + 1
    candidate_coverage = {
        "discovered": len(candidates),
        "frameworkIdentified": candidate_identified,
        "percent": round(100 * candidate_identified / len(candidates), 1) if candidates else 0.0,
        "bySource": candidate_sources,
        "sourceStatus": {
            "pacman": package_sources["pacman"]["status"],
            "pacmanAppstream": package_sources["pacman"]["desktopApplicationMetadata"]["status"],
            "flatpak": package_sources["flatpak"]["status"],
            "snap": package_sources["snap"]["status"],
            "AppImage": "scanned",
        },
        "scope": "candidate records from visible XDG launcher IDs, curated CLI/TUI commands, Flatpak/Snap app IDs and pacman-owned AppStream desktop-app metadata without exact-ID launcher duplicates, plus AppImage files not matched to a visible launcher by normalized app name/version; multiple standalone copies may still appear separately, and package-only executables without desktop-app metadata, services, hidden helpers, and apps missed by these sources are excluded",
        "appImageLauncherDuplicatesExcluded": len(duplicate_appimage_files),
    }
    return {
        "schemaVersion": 3,
        "scope": "user-facing launcher census from XDG desktop entries and supported exports, plus curated installed CLI/TUI tools and pacman-owned AppStream desktop-app metadata not already represented by a launcher; AppImage files matching visible launchers by normalized app name/version are counted once; package-only executables without desktop-app metadata are not counted",
        "desktopEntryFilesFound": raw_count,
        "effectiveDesktopApplications": len(apps),
        "visibleDesktopApplications": len(visible_apps),
        "frameworkIdentifiedVisibleApplications": len(identified_visible_apps),
        "frameworkIdentificationPercent": round(100 * len(identified_visible_apps) / len(visible_apps), 1) if visible_apps else 0.0,
        "frameworkIdentificationScope": "unique visible launchable desktop entries in scanned XDG application directories; this does not include package-only commands without a launcher",
        "applicationCandidateCoverage": candidate_coverage,
        "applicationCandidates": candidates,
        "hiddenOrNoDisplayEntries": len(apps) - len(visible_apps),
        "unavailableTryExecEntries": sum(1 for app in apps if app["launchable"] is False),
        "additionalInstalledCliTuis": len(cli_apps),
        "desktopApplications": apps,
        "installationSources": package_sources,
        "webApplications": [app for app in apps if app["installationSource"] == "web-app"],
        "standaloneApplications": appimages,
        "mailClients": [
            {**client, "profilePath": "~/.thunderbird/profiles.ini" if client["engine"] == "Gecko" else None,
             "fontSurface": "Gecko profile preferences" if client["engine"] == "Gecko" else "GTK system font and Fontconfig monospace",
             "status": "installed" if client["installed"] == "true" else "known-not-installed"}
            for client in discover_mail_profiles()
        ],
        "cliTuis": cli_apps,
        "reviewCounts": counts,
        "sharedFontSurfaces": {
            "GTK": {
                "controls": _generic_surface("GTK/GTK-derived")[1],
                "localEvidence": [*_font_line_evidence((HOME / ".config/gtk-3.0/settings.ini", HOME / ".config/gtk-4.0/settings.ini")), *_gsettings_font_evidence()],
            },
            "Qt": {
                "controls": _generic_surface("Qt")[1],
                "localEvidence": _font_line_evidence((HOME / ".config/qt5ct/qt5ct.conf", HOME / ".config/qt6ct/qt6ct.conf")) + ["Whether the relevant Qt platform-theme integration is active must be established per process."],
            },
            "Fontconfig": {
                "controls": ["~/.config/fontconfig/fonts.conf and conf.d rules resolve generic-family aliases/fallbacks."],
                "localEvidence": _font_line_evidence((HOME / ".config/fontconfig/fonts.conf", *(HOME / ".config/fontconfig/conf.d").glob("*.conf"))),
            },
            "Chromium browser and web apps": {
                "controls": _generic_surface("Chromium browser")[1],
                "localEvidence": ["Brave profile font values are inspected on demand; raw Preferences data is excluded from the inventory record."],
            },
            "Electron/Chromium apps": _generic_surface("Electron/Chromium")[1],
            "Terminal TUIs": ["Neovim/Vim/nano/Helix and other terminal UIs inherit the host terminal's font."],
        },
        "knownNotInstalled": [
            {"name": "Visual Studio Code", "command": "code", "status": "not found on PATH and no desktop entry",
             "controlPoints": ["User settings.json: editor.fontFamily/fontSize and terminal.integrated.fontFamily/fontSize"]}
            for _ in [0] if not shutil.which("code") and not any("visual studio code" in str(app["name"]).casefold() for app in apps)
        ] + [
            {"name": name, "command": command, "status": "not installed",
             "controlPoints": controls, "reference": reference}
            for name, command, controls, reference in (
                ("Walker", "walker", ["~/.config/walker/themes/<theme>/style.css", "GTK4 XML layouts"], "https://walkerlauncher.com/docs/theming"),
                ("Waybar", "waybar", ["~/.config/waybar/style.css: font-family/font-size"], None),
                ("Wofi", "wofi", ["~/.config/wofi/style.css: font-family/font-size"], None),
                ("Fuzzel", "fuzzel", ["~/.config/fuzzel/fuzzel.ini: font"], None),
                ("Rofi", "rofi", ["~/.config/rofi/config.rasi: configuration font and theme CSS"], None),
                ("Eww", "eww", ["~/.config/eww/eww.scss: CSS font-family/font-size"], None),
                ("AGS", "ags", ["AGS stylesheet CSS and widget-specific Pango markup"], None),
                ("nwg-dock-hyprland", "nwg-dock-hyprland", ["GTK CSS/theme settings"], None),
            ) if not shutil.which(command)
        ],
        "limitations": [
            "A desktop entry identifies a launcher, not every feature or embedded view in that app; TryExec is checked, while environment-specific OnlyShowIn/NotShowIn launcher visibility is not inferred.",
            "The CLI/TUI list is curated and does not enumerate every executable or package command on PATH.",
            "Apps marked needs-review require inspection of their own settings, themes, and runtime before an adapter is enabled.",
            "Document-authored fonts and site CSS remain separate from application chrome and editor defaults.",
        ],
    }


def shell_font_surfaces() -> dict[str, object]:
    """Inventory the active Quickshell bar and plugins that render text."""
    shell_path = HOME / ".config/omarchy/shell.json"
    try:
        shell = json.loads(shell_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        shell = {}
    bar = shell.get("bar", {}) if isinstance(shell, dict) else {}
    layout = bar.get("layout", {}) if isinstance(bar, dict) else {}
    widget_ids = sorted({
        str(item["id"])
        for row in layout.values() if isinstance(row, list)
        for item in row if isinstance(item, dict) and isinstance(item.get("id"), str)
    }) if isinstance(layout, dict) else []
    service_ids = sorted({
        str(item["id"]) for item in shell.get("plugins", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }) if isinstance(shell, dict) and isinstance(shell.get("plugins"), list) else []

    modules = []
    plugin_root = HOME / ".config/omarchy/plugins"
    for module_id in widget_ids + service_ids:
        root = plugin_root / module_id
        if not root.is_dir():
            continue
        matches = []
        for source in root.rglob("*.qml"):
            if ".git" in source.parts or "node_modules" in source.parts:
                continue
            try:
                lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, 1):
                if re.search(r"font\.family|Style\.font|fontFamily|font\.(pointSize|pixelSize)", line):
                    matches.append({"file": str(source.relative_to(root)), "line": number, "excerpt": line.strip()[:180]})
                    if len(matches) >= 20:
                        break
            if len(matches) >= 20:
                break
        modules.append({
            "id": module_id,
            "source": str(root),
            "fontEvidence": matches,
            "fontReview": "qml-font-references-found" if matches else "no-qml-font-reference-found",
        })

    font_config_path = HOME / ".config/omarchy/shell-font.json"
    try:
        shell_font_config = json.loads(font_config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        shell_font_config = None
    return {
        "shell": "Omarchy Quickshell",
        "runningComponents": {
            "quickshell": shutil.which("quickshell"),
            "omarchy-shell": shutil.which("omarchy-shell"),
            "walker": shutil.which("walker"),
            "waybar": shutil.which("waybar"),
            "wofi": shutil.which("wofi"),
            "fuzzel": shutil.which("fuzzel"),
            "rofi": shutil.which("rofi"),
            "eww": shutil.which("eww"),
            "ags": shutil.which("ags"),
            "nwg-dock-hyprland": shutil.which("nwg-dock-hyprland"),
        },
        "barFontSurface": {
            "fontOwnerPlugin": "skuthus.shell-font" if "skuthus.shell-font" in widget_ids else None,
            "configPath": "~/.config/omarchy/shell-font.json",
            "config": shell_font_config if isinstance(shell_font_config, dict) else None,
            "mechanism": "Quickshell Style.fontFamily, propagated to bar widgets through bar.fontFamily/Style.font.family",
        },
        "activeBarWidgetIds": widget_ids,
        "enabledServicePluginIds": service_ids,
        "widgetFontEvidence": modules,
        "classification": "Quickshell widgets are a separate font surface from GTK/Qt desktop apps; each active widget may inherit the bar font or declare its own QML font family/size.",
    }


def persist_font_application_inventory(record: dict[str, object]) -> str:
    """Atomically keep the latest first-run/app-change inventory in XDG state."""
    state_home = Path(os.environ.get("XDG_STATE_HOME", str(HOME / ".local/state")))
    if not state_home.is_absolute():
        state_home = HOME / ".local/state"
    try:
        state_home.relative_to(HOME)
    except ValueError as exc:
        raise ValueError("XDG_STATE_HOME is outside the user's home directory") from exc

    directory = state_home / "omarchy-look-and-feel"
    target = directory / "font-application-inventory.json"
    current = HOME
    for part in directory.relative_to(HOME).parts:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            current.mkdir(mode=0o700)
            continue
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"unsafe inventory state directory: {current}")

    prior: dict[str, object] | None = None
    try:
        info = target.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError(f"unsafe inventory record: {target}")
        try:
            prior = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError):
            prior = None
    except FileNotFoundError:
        pass
    if isinstance(prior, dict):
        prior_data = {key: value for key, value in prior.items() if key != "scanCompletedAt"}
        if prior_data == record:
            return str(target)

    saved = dict(record)
    saved["scanCompletedAt"] = datetime.now(timezone.utc).isoformat()
    payload = (json.dumps(saved, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=".font-inventory-", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        dir_fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return str(target)
