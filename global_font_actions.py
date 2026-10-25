"""Build reversible font targets for global desktop and terminal controls."""

from __future__ import annotations

import json
import math
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
    result = "\n".join(lines).rstrip() + "\n"
    return _replace_ini_value(result, "main", "dpi-aware", "no")


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
    from wezterm_blocks import fonts
    try:
        return fonts(text, family, size)
    except ValueError as exc:
        raise TransactionError(str(exc)) from exc


def _parse_qt_font(original: str, version: int):
    """Preserve valid QFont attributes, repairing malformed native values.

    QFont.fromString silently coerces some malformed fields. A missing style
    hint can turn weight 400 into an invalid hint and shift another value into
    stretch, collapsing all text. Validate field domains before native parsing.
    """
    try:
        from PySide6.QtGui import QFont
    except ImportError as exc:
        raise TransactionError("Qt font validation requires pyside6; install it before applying fonts") from exc

    parts = original.strip('"').split(',') if original else []
    extended = len(parts) >= 16
    valid = bool(parts) and (len(parts) in (10, 11) or (version == 6 and len(parts) >= 16))

    def number(index):
        value = float(parts[index])
        if not math.isfinite(value):
            raise ValueError('non-finite QFont field')
        return value

    def integer(index):
        if not re.fullmatch(r'[+-]?[0-9]+', parts[index].strip()):
            raise ValueError('non-integral QFont field')
        return int(parts[index])

    font = QFont()
    try:
        if valid:
            valid = (bool(parts[0]) and (number(1) == -1 or number(1) > 0)
                     and (integer(2) == -1 or integer(2) > 0)
                     and integer(3) in {item.value for item in QFont.StyleHint}
                     and (1 <= integer(4) <= 1000 if extended else 0 <= integer(4) <= 99)
                     and integer(5) in {item.value for item in QFont.Style}
                     and all(integer(i) in (0, 1) for i in (6, 7, 8, 9)))
        if valid and extended:
            strategy_mask = 0
            for flag in QFont.StyleStrategy:
                strategy_mask |= flag.value
            valid = (integer(10) in {item.value for item in QFont.Capitalization}
                     and integer(11) in {item.value for item in QFont.SpacingType}
                     and math.isfinite(number(12)) and math.isfinite(number(13))
                     and 0 <= integer(14) <= 4000
                     and integer(15) > 0 and not integer(15) & ~strategy_mask)
            # Qt 6.12 appends counted OpenType feature and variable-axis
            # records after styleName. Earlier Qt 6 writes 16 or 17 fields.
            # https://github.com/qt/qtbase/blob/6.12/src/gui/text/qfont.cpp
            if valid and len(parts) > 17:
                at = 17
                for is_axis in (False, True):
                    count = integer(at)
                    if not 0 <= count <= 256:
                        raise ValueError('invalid QFont feature count')
                    at += 1
                    seen = set()
                    for _ in range(count):
                        tag, separator, value = parts[at].partition('=')
                        if (not separator or len(tag) != 4 or tag in seen
                                or any(not 32 <= ord(char) <= 126 for char in tag)):
                            raise ValueError('invalid QFont feature tag')
                        seen.add(tag)
                        if is_axis:
                            if not math.isfinite(float(value)):
                                raise ValueError('invalid QFont variable axis')
                        elif not value.isascii() or not value.isdecimal() or not 0 <= int(value) <= 0xffffffff:
                            raise ValueError('invalid QFont feature value')
                        at += 1
                valid = at == len(parts)
        if valid:
            valid = font.fromString(','.join(parts))
            valid = valid and (font.styleHint().value == integer(3) and font.style().value == integer(5))
            if extended:
                valid = valid and (font.weight().value == integer(4) and font.stretch() == integer(14))
    except (ValueError, OverflowError, IndexError):
        valid = False
    return font if valid else None


def _qt_font_value(original: str, family: str, size: int, version: int) -> str:
    if any(char in family for char in ',\n\r\x00'):
        raise TransactionError("Qt font family cannot be represented without ambiguity")
    font = _parse_qt_font(original, version)
    from PySide6.QtGui import QFont

    if version == 5:
        # Qt 5 uses the old 0..99 weight scale and ten fields plus an optional
        # style name. Qt 6's longer wire format is not compatible with it.
        if font is None:
            parts = [family, str(size), '-1', '5', '50', '0', '0', '0', '0', '0']
        else:
            parts = original.strip('"').split(',')
        parts[0], parts[1], parts[2] = family, str(size), '-1'
        return ','.join(parts)

    if font is None:
        font = QFont(family, size)
        font.setStyleHint(QFont.StyleHint.AnyStyle)
        font.setWeight(QFont.Weight.Normal)
        font.setStretch(100)
    font.setFamily(family)
    font.setPointSize(size)
    result = font.toString()
    check = QFont()
    if (not check.fromString(result) or check.family() != family or check.pointSize() != size
            or check.weight() != font.weight() or check.stretch() != font.stretch()
            or check.styleHint() != font.styleHint()):
        raise TransactionError("Qt font serialization failed native readback")
    return result


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

    # Omarchy's qual=any monospace override also captures explicit families
    # whose fallback list contains monospace. Repair only the reviewed rule.
    from fontconfig_policy import build as fontconfig_policy
    from transaction import _ensure_home_path
    fontconfig_path = _ensure_home_path(HOME / FILE_TARGETS['fontconfig-monospace'], allow_missing_parents=True)
    try:
        fontconfig_text = fontconfig_path.read_bytes().decode('utf-8') if fontconfig_path.exists() else ''
        targets['fontconfig-monospace'] = fontconfig_policy(fontconfig_text, terminal_family).encode()
    except (OSError, ValueError) as exc:
        raise TransactionError(str(exc)) from exc

    # qtct stores version-specific QFont::toString values. Preserve valid
    # custom attributes; repair malformed values before Qt can inherit them.
    from application_themes import ini
    from managed_preferences import decode
    for version in (5, 6):
        target = f"qt{version}ct-settings"
        path = HOME / FILE_TARGETS[target]
        from qt_integration import active as qt_active
        active = qt_active(version)
        if not path.is_file() and not active:
            continue
        text = _read(path, allow_missing=True)
        data = decode(target, text.encode())
        for role, family, size in (("general", system_family, system_size), ("fixed", terminal_family, terminal_size)):
            value = _qt_font_value(data.get("Fonts/" + role, ""), family, size, version)
            text = ini(text, "Fonts", role, '"' + value + '"')
        targets[target] = text.encode()

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
    shell_style = _read(shell_style_path, allow_missing=True)
    # The chooser uses points; Omarchy shell tokens use logical pixels.
    shell_size = round(system_size * 96 / 72)
    lines = shell_style.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "[font]"), None)
    if start is None:
        lines.extend(["", "[font]", f"base-size = {shell_size}"])
    else:
        end = next((i for i in range(start + 1, len(lines)) if re.match(r"\s*\[.+\]\s*$", lines[i])), len(lines))
        active = next((i for i in range(start + 1, end) if re.match(r"\s*base-size\s*=", lines[i])), None)
        if active is None:
            lines.insert(end, f"base-size = {shell_size}")
        else:
            lines[active] = re.sub(r"^(\s*base-size\s*=\s*).*$", rf"\g<1>{shell_size}", lines[active])
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
        if target_id == "wezterm-config":
            from transaction import require_wezterm_location
            require_wezterm_location()
        config_path = HOME / FILE_TARGETS[target_id]
        if target_id == "ghostty-config":
            text = _read(config_path, allow_missing=True)
            lines = text.splitlines()
            import_line = "config-file = look-and-feel-font.conf"
            if import_line not in lines:
                lines.append(import_line)
            targets[target_id] = ("\n".join(lines).rstrip() + "\n").encode()
            escaped = terminal_family.replace("\\", "\\\\").replace('"', '\\"')
            # Ghostty accumulates font-family settings across imports. Reset
            # the previous list before selecting the requested terminal font.
            overlay = f'font-family = ""\nfont-family = "{escaped}"\nfont-size = {terminal_size}\n'
            # A contrast floor keeps terminal input legible when a running
            # program retains its old background during a light/dark switch.
            existing_overlay = _read(HOME / FILE_TARGETS["ghostty-font-overlay"], allow_missing=True)
            contrast = [float(value) for value in re.findall(r"(?m)^\s*minimum-contrast\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*$", text + "\n" + existing_overlay)]
            overlay += f"minimum-contrast = {max([4.5, *contrast]):g}\n"
            targets["ghostty-font-overlay"] = overlay.encode()
        else:
            text = _read(config_path, allow_missing=True)
            updated = updaters[target_id](text, terminal_family, terminal_size)
            targets[target_id] = updated.encode()
        terminal_targets.add(target_id)

    return targets, len(terminal_targets)
