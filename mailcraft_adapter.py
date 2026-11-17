"""MailCraft adapter: the appearance file MailCraft follows while its interface
theme is "Follow appearance file" (File > Options > General).

MailCraft re-reads ~/.config/mailcraft/appearance.json about once a second, so
a theme or font change reaches an open window without a restart. This module
only builds the file's bytes; the transaction layer writes them.
"""
from __future__ import annotations

import json
from pathlib import Path

DESKTOP_ID = 'io.github.billsecond.mailcraft.desktop'
TARGET = 'mailcraft-appearance'
# Keys MailCraft takes from an Omarchy palette, and where each comes from.
_COLORS = (
    ('background', ('background',)),
    ('raised', ('lighter_background', 'background')),
    ('text', ('foreground',)),
    ('muted', ('muted', 'foreground')),
    ('accent', ('accent',)),
    ('selection', ('selection_background', 'selection', 'accent')),
    ('red', ('red',)),
    ('green', ('green',)),
    ('yellow', ('yellow',)),
    ('orange', ('orange', 'yellow')),
    ('blue', ('blue',)),
    ('purple', ('magenta',)),
)
# Characters MailCraft refuses in a family name.
_BAD_FAMILY = set('"\';,{}<>\\')


def installed(desktop_ids) -> bool:
    return DESKTOP_ID in desktop_ids


def _family(name):
    if not isinstance(name, str):
        return None
    name = name.strip()
    if not name or len(name) > 64 or any(c in _BAD_FAMILY or ord(c) < 32 for c in name):
        return None
    return name


def appearance(colors: dict, family: str | None, size_pt: int | None = None) -> bytes:
    """The appearance file for an Omarchy palette (`application_themes.palette`)
    and the system font. `size_pt` is the composition font's size."""
    out = {'mode': colors['mode'], 'colors': {}}
    for key, sources in _COLORS:
        value = next((colors[s] for s in sources if isinstance(colors.get(s), str)), None)
        if value:
            out['colors'][key] = value.lower()
    family = _family(family)
    if family:
        out['interfaceFont'] = {'family': family}
        if isinstance(size_pt, int) and not isinstance(size_pt, bool) and 6 <= size_pt <= 48:
            out['composeFont'] = {'family': family, 'sizePt': size_pt}
    return (json.dumps(out, indent=2, sort_keys=True) + '\n').encode()


def saved_font():
    """The system font the plugin last applied, as (family, size) or (None, None)."""
    from transaction import FILE_TARGETS
    path = Path.home() / FILE_TARGETS['global-font-selection']
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None, None
    if not isinstance(data, dict):
        return None, None
    size = data.get('systemFontSizePt')
    return _family(data.get('systemFontFamily')), size if isinstance(size, int) else None


def current_colors():
    """The palette of the theme Omarchy has in force."""
    from appearance_actions import CURRENT_DIR
    from application_themes import palette
    return palette(CURRENT_DIR / 'theme')
