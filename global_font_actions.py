"""Build reversible font targets for global desktop and terminal controls."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

from font_application_inventory import TERMINALS
from transaction import FILE_TARGETS, TransactionError


HOME = Path.home()
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", str(HOME / ".config")))
if not CONFIG.is_absolute():
    CONFIG = HOME / ".config"
try:
    CONFIG.relative_to(HOME)
except ValueError as exc:
    raise TransactionError("XDG config directory is outside the managed home boundary") from exc

TERMINAL_COMMANDS = {
    "Alacritty.desktop": ("alacritty", "alacritty-config"),
    "foot.desktop": ("foot", "foot-config"),
    "footclient.desktop": ("footclient", "foot-config"),
    "foot-server.desktop": ("foot", "foot-config"),
    "com.mitchellh.ghostty.desktop": ("ghostty", "ghostty-config"),
    "kitty.desktop": ("kitty", "kitty-config"),
    "kitty-open.desktop": ("kitty", "kitty-config"),
    "org.wezfurlong.wezterm.desktop": ("wezterm", "wezterm-config"),
}


def _read(path: Path, *, allow_missing: bool = False) -> str:
    if path.is_symlink():
        raise TransactionError("a managed font configuration is a symlink; refusing to replace it")
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if allow_missing:
            return ""
        raise TransactionError("a managed font configuration is missing")
    except (OSError, UnicodeError) as exc:
        raise TransactionError("a managed font configuration could not be read safely") from exc


def _replace_ini_value(text: str, section: str, key: str, value: str) -> str:
    lines = text.splitlines()
    section_start = next((i for i, line in enumerate(lines) if line.strip().casefold() == f"[{section}]".casefold()), None)
    if section_start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([f"[{section}]", f"{key}={value}"])
    else:
        section_end = next((i for i in range(section_start + 1, len(lines)) if re.match(r"\s*\[.+\]\s*$", lines[i])), len(lines))
        key_re = re.compile(rf"^(\s*{re.escape(key)}\s*=\s*).*$", re.IGNORECASE)
        match_index = next((i for i in range(section_start + 1, section_end) if key_re.match(lines[i])), None)
        if match_index is None:
            lines.insert(section_end, f"{key}={value}")
        else:
            lines[match_index] = key_re.sub(rf"\g<1>{value}", lines[match_index])
    return "\n".join(lines).rstrip() + "\n"


def _quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _replace_alacritty(text: str, family: str, size: int) -> str:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "[font]"), None)
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["[font]", f"normal = {{ family = {_quoted(family)} }}", f"size = {size}"])
    else:
        end = next((i for i in range(start + 1, len(lines)) if re.match(r"\s*\[.+\]\s*$", lines[i])), len(lines))
        found_family = False
        found_size = False
        for i in range(start + 1, end):
            if re.match(r"\s*(normal|bold|italic)\s*=", lines[i]):
                if re.search(r"\bfamily\s*=", lines[i]):
                    lines[i] = re.sub(r"(\bfamily\s*=\s*)(\"(?:\\.|[^\"])*\"|'(?:\\.|[^'])*')", lambda m: m.group(1) + _quoted(family), lines[i], count=1)
                    found_family = True
            if re.match(r"\s*size\s*=", lines[i]):
                lines[i] = re.sub(r"^(\s*size\s*=\s*).*$", rf"\g<1>{size}", lines[i])
                found_size = True
        if not found_family:
            lines.insert(end, f"normal = {{ family = {_quoted(family)} }}")
            end += 1
        if not found_size:
            lines.insert(end, f"size = {size}")
    return "\n".join(lines).rstrip() + "\n"


def _replace_foot(text: str, family: str, size: int) -> str:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "[main]"), None)
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["[main]", f"font={family}:size={size}"])
    else:
        end = next((i for i in range(start + 1, len(lines)) if re.match(r"\s*\[.+\]\s*$", lines[i])), len(lines))
        key_re = re.compile(r"^\s*font\s*=.*$", re.IGNORECASE)
        at = next((i for i in range(start + 1, end) if key_re.match(lines[i])), None)
        if at is None:
            lines.insert(start + 1, f"font={family}:size={size}")
        else:
            lines[at] = f"font={family}:size={size}"
    return "\n".join(lines).rstrip() + "\n"


def _replace_kitty(text: str, family: str, size: int) -> str:
    lines = text.splitlines()
    found_family = found_size = False
    for i, line in enumerate(lines):
        if re.match(r"\s*font_family\s+", line):
            lines[i] = f"font_family {family}"
            found_family = True
        elif re.match(r"\s*font_size\s+", line):
            lines[i] = f"font_size {size}.0"
            found_size = True
    if not found_family:
        lines.append(f"font_family {family}")
    if not found_size:
        lines.append(f"font_size {size}.0")
    return "\n".join(lines).rstrip() + "\n"


def _replace_wezterm(text: str, family: str, size: int) -> str:
    lines = text.splitlines()

    def ensure_wezterm_binding() -> None:
        binding = re.compile(r"^\s*(?:local\s+)?wezterm\s*=\s*require\s*(?:\(\s*)?['\"]wezterm['\"]")
        if not any(binding.match(line) for line in lines):
            lines.insert(0, 'local wezterm = require "wezterm"')

    if not lines:
        return "\n".join([
            'local wezterm = require "wezterm"',
            "local config = {}",
            f'config.font = wezterm.font({_quoted(family)}, {{ weight = "Regular" }})',
            f"config.font_size = {size}",
            "return config",
            "",
        ])
    ensure_wezterm_binding()
    start = next((i for i, line in enumerate(lines) if re.match(r"\s*config\.font\s*=", line)), None)
    if start is None:
        if not any(re.match(r"\s*(local\s+)?config\s*=", line) for line in lines):
            raise TransactionError("the terminal font config has an unsupported structure")
        replacement = [f'config.font = wezterm.font({_quoted(family)}, {{ weight = "Regular" }})', f"config.font_size = {size}"]
        return_index = next((i for i, line in enumerate(lines) if re.match(r"\s*return\s+config\b", line)), len(lines))
        lines[return_index:return_index] = replacement
    else:
        end = start + 1
        if "font_with_fallback" in lines[start]:
            while end < len(lines) and lines[end].strip() != "})":
                if re.match(r"\s*(config\.|return\s+config\b)", lines[end]):
                    raise TransactionError("the terminal font table has an unsupported structure")
                end += 1
            if end >= len(lines):
                raise TransactionError("the terminal font table has an unsupported structure")
            end += 1
        elif not re.search(r"wezterm\.font\s*\(", lines[start]):
            raise TransactionError("the terminal font assignment has an unsupported structure")
        lines[start:end] = [f'config.font = wezterm.font({_quoted(family)}, {{ weight = "Regular" }})']
        size_line = next((i for i, line in enumerate(lines) if re.match(r"\s*config\.font_size\s*=", line)), None)
        if size_line is None:
            lines.insert(start + 1, f"config.font_size = {size}")
        else:
            lines[size_line] = f"config.font_size = {size}"
    return "\n".join(lines).rstrip() + "\n"


def build_global_font_targets(system_family: str, system_size: int, terminal_family: str, terminal_size: int,
                              terminal_ids: set[str] | None = None) -> tuple[dict[str, bytes], int]:
    """Build reversible file targets for desktop, shell, and detected terminals."""
    if any(isinstance(size, bool) or not isinstance(size, int) or not 6 <= size <= 48 for size in (system_size, terminal_size)):
        raise TransactionError("font sizes must be whole points between 6 and 48")

    targets: dict[str, bytes] = {}
    for target_id, path in (
        ("gtk3-settings", CONFIG / "gtk-3.0/settings.ini"),
        ("gtk4-settings", CONFIG / "gtk-4.0/settings.ini"),
    ):
        targets[target_id] = _replace_ini_value(_read(path, allow_missing=True), "Settings", "gtk-font-name", f"{system_family} {system_size}").encode()

    shell_font_path = CONFIG / "omarchy/shell-font.json"
    shell_font_text = _read(shell_font_path, allow_missing=True)
    try:
        shell_font = json.loads(shell_font_text) if shell_font_text else {"enabled": True, "weight": "regular"}
    except json.JSONDecodeError as exc:
        raise TransactionError("the shell font configuration is not valid JSON") from exc
    if not isinstance(shell_font, dict):
        raise TransactionError("the shell font configuration has an unsupported shape")
    shell_font["enabled"] = True
    shell_font["family"] = system_family
    targets["omarchy-shell-font"] = (json.dumps(shell_font, indent=2, sort_keys=True) + "\n").encode()

    shell_style_path = CONFIG / "omarchy/shell.toml"
    shell_style = _read(shell_style_path)
    lines = shell_style.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "[font]"), None)
    if start is None:
        lines.extend(["", "[font]", f"base-size = {system_size}"])
    else:
        end = next((i for i in range(start + 1, len(lines)) if re.match(r"\s*\[.+\]\s*$", lines[i])), len(lines))
        active = next((i for i in range(start + 1, end) if re.match(r"\s*base-size\s*=", lines[i])), None)
        if active is None:
            lines.insert(end, f"base-size = {system_size}")
        else:
            lines[active] = re.sub(r"^(\s*base-size\s*=\s*).*$", rf"\g<1>{system_size}", lines[active])
    targets["omarchy-shell-style"] = ("\n".join(lines).rstrip() + "\n").encode()

    global_selection = {
        "schemaVersion": 1,
        "systemFontFamily": system_family,
        "systemFontSizePt": system_size,
        "terminalFontFamily": terminal_family,
        "terminalFontSizePt": terminal_size,
    }
    targets["global-font-selection"] = (json.dumps(global_selection, indent=2, sort_keys=True) + "\n").encode()

    updaters = {
        "alacritty-config": _replace_alacritty,
        "foot-config": _replace_foot,
        "kitty-config": _replace_kitty,
        "wezterm-config": _replace_wezterm,
    }
    selected_ids = terminal_ids if terminal_ids is not None else {
        desktop_id for desktop_id, (command, _) in TERMINAL_COMMANDS.items() if shutil.which(command)
    }
    terminal_targets: set[str] = set()
    for desktop_id in sorted(selected_ids):
        adapter = TERMINAL_COMMANDS.get(desktop_id)
        if desktop_id not in TERMINALS or adapter is None:
            raise TransactionError("an installed terminal has no reviewed font adapter")
        command, target_id = adapter
        if target_id not in updaters and target_id != "ghostty-config":
            raise TransactionError("an installed terminal adapter has no supported configuration target")
        if target_id not in FILE_TARGETS:
            raise TransactionError("an installed terminal adapter has no managed configuration path")
        if not shutil.which(command):
            raise TransactionError("an installed terminal could not be matched to its font adapter executable")
        if target_id in terminal_targets:
            continue
        config_path = HOME / FILE_TARGETS[target_id]
        if target_id == "ghostty-config":
            text = _read(config_path, allow_missing=True)
            lines = text.splitlines()
            import_line = "config-file = look-and-feel-font.conf"
            if import_line not in lines:
                lines.append(import_line)
            targets[target_id] = ("\n".join(lines).rstrip() + "\n").encode()
            escaped = terminal_family.replace("\\", "\\\\").replace('"', '\\"')
            overlay = f'font-family = "{escaped}"\nfont-size = {terminal_size}\n'
            targets["ghostty-font-overlay"] = overlay.encode()
        else:
            text = _read(config_path, allow_missing=True)
            updated = updaters[target_id](text, terminal_family, terminal_size)
            targets[target_id] = updated.encode()
        terminal_targets.add(target_id)

    return targets, len(terminal_targets)
