"""Narrow codecs for application-owned preferences and the desired policy.

The transaction journal records only changed owned fields. Undo merges those
fields into fresh data, so an application can update its window/history state.
No plugin or arbitrary JSON path is accepted from a journal.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import os
import subprocess
import configparser
import re
from contextvars import ContextVar

AUTOMATIC = ContextVar("automatic_appearance_operation", default=False)

FIELDS = {
    'fontconfig-monospace': {'monospace-rule'},
    "hypr-qt-integration": {"integration"},
    'wezterm-config': {'fonts', 'theme', 'opacity'},
    'typora-base-user-css': {'body', 'fonts'},
    'typora-profile': {'theme', 'darkTheme', 'useSeparateDarkTheme'},
    'appearance-policy': {'fonts', 'theme', 'background', 'icons', 'opacity', 'blur'},
    'terminal-blur-config': {'blur'},
}
INI_FIELDS = {
    'wezterm-config': {'fonts', 'theme'},
    "onlyoffice-settings": {"General/titlebar"},
    'gtk3-settings': {'Settings/gtk-font-name', 'Settings/gtk-theme-name', 'Settings/gtk-application-prefer-dark-theme', 'Settings/gtk-icon-theme-name'},
    'gtk4-settings': {'Settings/gtk-font-name', 'Settings/gtk-theme-name', 'Settings/gtk-application-prefer-dark-theme', 'Settings/gtk-icon-theme-name'},
    'qt5ct-settings': {'Fonts/general', 'Fonts/fixed', 'Appearance/custom_palette', 'Appearance/color_scheme_path', 'Appearance/icon_theme'},
    'qt6ct-settings': {'Fonts/general', 'Fonts/fixed', 'Appearance/custom_palette', 'Appearance/color_scheme_path', 'Appearance/icon_theme'},
}
FIELDS.update(INI_FIELDS)
# WezTerm has its own Lua block codec rather than an INI codec.
FIELDS['wezterm-config'] = {'fonts', 'theme', 'opacity'}
from terminal_preferences import FIELDS as TERMINAL_FIELDS
FIELDS.update(TERMINAL_FIELDS)


def _ini_decode(target, raw):
    text = raw.decode('utf-8')
    parser = configparser.RawConfigParser(strict=True)
    try:
        parser.read_string(text)
    except configparser.Error as exc:
        raise ValueError('unsupported INI syntax: ' + str(exc)) from exc
    data = {'_text': text}
    for key in INI_FIELDS[target]:
        section, option = key.split('/')
        if parser.has_option(section, option):
            data[key] = parser.get(section, option)
    return data


def _ini_encode(target, data):
    from global_font_actions import _replace_ini_value
    text = data['_text']
    old = _ini_decode(target, text.encode())
    for key in sorted(INI_FIELDS[target]):
        if old.get(key) == data.get(key):
            continue
        section, option = key.split('/')
        if key in data:
            text = _replace_ini_value(text, section, option, data[key])
        else:
            current_section, lines = '', []
            for line in text.splitlines(keepends=True):
                heading = re.fullmatch(r'\s*\[([^\]]+)\]\s*', line)
                if heading:
                    current_section = heading[1]
                if current_section == section and re.match(r'\s*' + re.escape(option) + r'\s*=', line, re.I):
                    continue
                lines.append(line)
            text = ''.join(lines)
    return text.encode()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate preference key')
        result[key] = value
    return result


def decode(target, raw):
    if target == 'terminal-blur-config':
        from blur_actions import decode as decode_blur
        return decode_blur(raw)
    if target not in FIELDS:
        raise ValueError('unknown preference codec')
    if target in TERMINAL_FIELDS:
        from terminal_preferences import decode as terminal_decode
        return terminal_decode(target, raw)
    if target == 'fontconfig-monospace':
        from fontconfig_policy import decode as decode_fontconfig
        return decode_fontconfig(raw.decode('utf-8'))
    if target == 'hypr-qt-integration':
        from qt_integration import decode as decode_qt
        return decode_qt(raw.decode('utf-8'))
    if target == 'wezterm-config':
        from wezterm_blocks import decode as decode_lua
        return decode_lua(raw.decode('utf-8'))
    if target == 'typora-base-user-css':
        from app_font_actions import BEGIN, END
        text = raw.decode('utf-8')
        if BEGIN not in text and END not in text:
            return {'body': text.rstrip(), 'fonts': None}
        if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
            raise ValueError('malformed managed CSS font block')
        a, b = text.index(BEGIN), text.index(END) + len(END)
        return {'body': (text[:a] + text[b:]).rstrip(), 'fonts': text[a:b]}
    if target in INI_FIELDS:
        return _ini_decode(target, raw)
    if target == 'typora-profile':
        raw = bytes.fromhex(raw.decode('ascii'))
    data = json.loads(raw, object_pairs_hook=_unique)
    if not isinstance(data, dict):
        raise ValueError('preference document must be an object')
    if target == 'typora-profile':
        for key, kind in [('theme', str), ('darkTheme', str), ('useSeparateDarkTheme', bool)]:
            if key not in data or type(data[key]) is not kind:
                raise ValueError('unsupported Typora appearance schema')
    else:
        from appearance_policy import validate
        validate(data)
    return data


def encode(target, data):
    if target == 'terminal-blur-config':
        from blur_actions import encode as encode_blur
        return encode_blur(data)
    if target in TERMINAL_FIELDS:
        from terminal_preferences import encode as terminal_encode
        return terminal_encode(target, data)
    if target == 'fontconfig-monospace':
        from fontconfig_policy import encode as encode_fontconfig
        return encode_fontconfig(data).encode('utf-8')
    if target == 'hypr-qt-integration':
        from qt_integration import encode as encode_qt
        return encode_qt(data).encode()
    if target == 'wezterm-config':
        from wezterm_blocks import encode as encode_lua
        return encode_lua(data).encode()
    if target == 'typora-base-user-css':
        body = data.get('body') or ''
        fonts = data.get('fonts')
        return (body.rstrip() + ('\n\n' + fonts if fonts else '') + '\n').encode()
    if target in INI_FIELDS:
        return _ini_encode(target, data)
    raw = (json.dumps(data, ensure_ascii=False, separators=(',', ':'), sort_keys=True) + '\n').encode()
    return raw.hex().encode('ascii') if target == 'typora-profile' else raw


def edits(target, before, after, *, owned_fields=None):
    old = decode(target, before) if before is not None else {}
    if target == 'appearance-policy' and before is None:
        old = {'fonts': None, 'theme': None, 'background': None}
    if target == 'typora-base-user-css' and before is None:
        old = {'body': '', 'fonts': None}
    if target == 'wezterm-config' and before is None:
        old = {'fonts': None, 'theme': None}
    new = decode(target, after)
    if target == 'fontconfig-monospace':
        # Anchor the first Apply's rule even when it was already correct. A
        # later automatic repair must not redefine Undo's baseline as the
        # intervening external rule merely because the first Apply was a no-op.
        return {'monospace-rule': {'before': [old['monospace-rule']] if 'monospace-rule' in old else [],
                                  'after': [new['monospace-rule']]}}
    # Wrapped values distinguish an absent field from a JSON null.
    owner = FIELDS[target] if owned_fields is None else owned_fields
    changes = {key: {'before': [old[key]] if key in old else [],
                     'after': [new[key]] if key in new else []}
               for key in sorted(owner)
               if (key in old, old.get(key)) != (key in new, new.get(key))}
    if target == 'terminal-blur-config':
        changes.setdefault('blur', {'before': [old['blur']] if 'blur' in old else [],
                                    'after': [new['blur']]})
    from terminal_preferences import OPACITY_FIELDS
    # Preserve the first Apply's baseline even if opacity was already correct.
    # Automatic repair must belong to that baseline, never to intervening drift.
    if target in OPACITY_FIELDS and owner <= OPACITY_FIELDS[target]:
        for key in owner:
            changes.setdefault(key, {'before': [old[key]] if key in old else [],
                                     'after': [new[key]] if key in new else []})
    if target in {'qt5ct-settings', 'qt6ct-settings'}:
        # Fonts Apply owns its initial baseline even if it was already equal.
        # Palette/icon operations must not acquire ownership of those fonts.
        owner = FIELDS[target] if owned_fields is None else owned_fields
        for key in {'Fonts/general', 'Fonts/fixed'} & owner:
            changes.setdefault(key, {'before': [old[key]] if key in old else [],
                                     'after': [new[key]] if key in new else []})
    return changes


def validate_edits(target, changes):
    if target not in FIELDS or not isinstance(changes, dict) or set(changes) - FIELDS[target]:
        raise ValueError('invalid managed preference metadata')
    for row in changes.values():
        if (not isinstance(row, dict) or set(row) != {'before', 'after'}
                or any(not isinstance(row[k], list) or len(row[k]) > 1 for k in row)):
            raise ValueError('invalid managed preference value')
        if target == 'fontconfig-monospace':
            from fontconfig_policy import validate_rules
            for wrapped in row.values():
                if wrapped:
                    validate_rules(wrapped[0])


def restore(target, current, changes):
    validate_edits(target, changes)
    data = decode(target, current)
    for key, row in changes.items():
        actual = [data[key]] if key in data else []
        if actual != row['before'] and actual != row['after']:
            raise ValueError(f'{target}: {key} changed independently; preserving it')
    result = copy.deepcopy(data)
    for key, row in changes.items():
        if row['before']:
            result[key] = row['before'][0]
        else:
            result.pop(key, None)
    # An initially absent policy still has its schema marker when unrelated
    # sections have subsequently been saved. Never remove those sections.
    return encode(target, result)


def assert_closed(target, path):
    if target == 'onlyoffice-settings':
        from transaction import _ensure_home_path
        _ensure_home_path(path, allow_missing_parents=True)
        found = subprocess.run(['pgrep', '--euid', str(os.getuid()), '--exact', 'DesktopEditors'],
                               capture_output=True, timeout=5, check=False)
        if found.returncode != 1:
            raise RuntimeError('Close OnlyOffice while its native window frame setting is updated.')
        return
    if target != 'typora-profile':
        return
    from transaction import _ensure_home_path
    _ensure_home_path(path, allow_missing_leaf=False)
    lock = Path(path).parent / 'SingletonLock'
    if lock.exists() or lock.is_symlink():
        raise RuntimeError('Close Typora; its profile is locked.')
    found = subprocess.run(['pgrep', '--euid', str(os.getuid()), '--exact', '[Tt]ypora'],
                           capture_output=True, timeout=5, check=False)
    if found.returncode != 1:
        raise RuntimeError('Close Typora while its appearance preferences are updated.')


def guard_paths(paths):
    from transaction import FILE_TARGETS
    wanted = Path.home() / FILE_TARGETS['typora-profile']
    office = Path.home() / FILE_TARGETS['onlyoffice-settings']
    offline = {wanted, office, Path.home() / FILE_TARGETS['brave-default-preferences']}
    for path in paths:
        if AUTOMATIC.get() and Path(path) in offline:
            raise RuntimeError('An offline application profile needs an explicit Apply or Undo while its application stays closed.')
        if Path(path) == office:
            assert_closed('onlyoffice-settings', office)
        if Path(path) == wanted:
            assert_closed('typora-profile', wanted)
