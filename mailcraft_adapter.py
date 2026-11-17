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


def _percent(value):
    return value if type(value) is int and 0 <= value <= 100 else None


def appearance(colors: dict, family: str | None, size_pt: int | None = None, opacity: int | None = None) -> bytes:
    """The appearance file for an Omarchy palette (`application_themes.palette`)
    and the system font. `size_pt` is accepted for the callers and not written:
    MailCraft's interface size is its own setting. `opacity` is the percent the
    plugin keeps for apps without an opacity setting of their own (`fleaOpacity`);
    absent, MailCraft stays solid."""
    out = {'mode': colors['mode'], 'colors': {}}
    for key, sources in _COLORS:
        value = next((colors[s] for s in sources if isinstance(colors.get(s), str)), None)
        if value:
            out['colors'][key] = value.lower()
    # The system font drives MailCraft's own text: menus, lists and the mail you read. The font
    # outgoing mail is written in is MailCraft's own setting (File > Options > Compose > Message
    # body) and is never sent from here.
    family = _family(family)
    if family:
        out['interfaceFont'] = {'family': family}
    opacity = _percent(opacity)
    if opacity is not None:
        out['opacity'] = opacity
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


def saved_opacity():
    """The opacity for apps without a setting of their own (`fleaOpacity` in the
    plugin's policy), or None when none was applied."""
    import appearance_policy
    try:
        return _percent(appearance_policy.read().get('fleaOpacity'))
    except (OSError, ValueError, AttributeError):
        return None


def present() -> bool:
    """Whether MailCraft has a settings folder here (it has been run)."""
    from transaction import FILE_TARGETS
    return (Path.home() / FILE_TARGETS[TARGET]).parent.is_dir()


def current_colors():
    """The palette of the theme Omarchy has in force."""
    from appearance_actions import CURRENT_DIR
    from application_themes import palette
    return palette(CURRENT_DIR / 'theme')
