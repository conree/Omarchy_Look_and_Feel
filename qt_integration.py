"""Detect Qt theme plugins and journal a single Omarchy session override.

Plugin metadata is read without loading its library. We never change the
activation environment or restart applications. A fresh login is required when
changing the selector; Omarchy imports the compositor environment at startup.
"""
from functools import lru_cache
from pathlib import Path
import os
import re

BEGIN = '\n-- Look and Feel Qt integration BEGIN\n'
END = '-- Look and Feel Qt integration END\n'


@lru_cache(maxsize=1)
def plugins():
    try:
        from PySide6.QtCore import QLibraryInfo, QPluginLoader
    except ImportError:
        return {}
    roots = {5: Path('/usr/lib/qt/plugins'),
             6: Path(QLibraryInfo.path(QLibraryInfo.PluginsPath))}
    result = {}
    for version, root in roots.items():
        path = root / f'platformthemes/libqt{version}ct.so'
        if path.is_file():
            keys = QPluginLoader(str(path)).metaData().get('MetaData', {}).get('Keys', [])
            result[version] = set(keys) & {'qt5ct', 'qt6ct'}
    return result


def gtk_palette_supported(version):
    if version != 6 or os.environ.get("QT_QPA_PLATFORMTHEME") != "gtk3":
        return False
    try:
        from PySide6.QtCore import QLibraryInfo, QPluginLoader
        version = QLibraryInfo.version()
        plugin = Path(QLibraryInfo.path(QLibraryInfo.PluginsPath)) / 'platformthemes/libqgtk3.so'
        keys = QPluginLoader(str(plugin)).metaData().get('MetaData', {}).get('Keys', [])
        return (version.majorVersion(), version.minorVersion()) >= (6, 10) and 'gtk3' in keys
    except ImportError:
        return False


def active(version):
    return os.environ.get('QT_QPA_PLATFORMTHEME', '').split(':')[0] in plugins().get(version, set())


def decode(text):
    from wezterm_blocks import _tokens
    body, selector = text, None
    if BEGIN in text or END in text:
        if text.count(BEGIN) != 1 or text.count(END) != 1 or not text.endswith(END):
            raise ValueError('Qt integration block was edited; preserving the Hyprland configuration.')
        at = text.index(BEGIN)
        comments = {a for kind, a, _ in _tokens(text, comments=True) if kind == 'COMMENT'}
        if at + 1 not in comments or text.index(END) not in comments:
            raise ValueError('Qt integration marker is inside a Lua literal.')
        value = text[at + len(BEGIN):-len(END)]
        match = re.fullmatch(r'-- Applied in session: ([A-Za-z0-9_.-]{1,200})\nhl.env\("QT_QPA_PLATFORMTHEME", "(qt5ct|qt6ct)"\)\n', value)
        if not match:
            raise ValueError('Qt integration block was edited; preserving it.')
        body, selector = text[:at], {'session': match[1], 'selector': match[2]}
    return {'body': body, 'integration': selector}


def encode(data):
    selector = data.get('integration')
    if selector is not None and (not isinstance(selector, dict) or set(selector) != {'selector', 'session'}
            or selector['selector'] not in {'qt5ct', 'qt6ct'}
            or not re.fullmatch(r'[A-Za-z0-9_.-]{1,200}', selector['session'])):
        raise ValueError('Unsupported Qt selector')
    body = data.get('body', '')
    return body + (BEGIN + f'-- Applied in session: {selector["session"]}\nhl.env("QT_QPA_PLATFORMTHEME", "{selector["selector"]}")\n' + END if selector else '')


def checked_config(text):
    """Reject ambiguous control flow before appending executable configuration."""
    from wezterm_blocks import _tokens
    data = decode(text)
    tokens = list(_tokens(data['body']))
    stack, default_loaded = [], False
    for index, (word, a, b) in enumerate(tokens):
        if 'function' not in stack:
            if word == 'local':
                rest = tokens[index + 1:]
                if rest and rest[0][0] == 'function':
                    rest = rest[1:]
                expect_name = True
                for token, _, _ in rest:
                    if expect_name:
                        if token in {'hl', 'require'}:
                            raise ValueError('Custom Hyprland API binding needs a reviewed integration adapter.')
                        expect_name = False
                    elif token == ',':
                        expect_name = True
                    else:
                        break
            if word == 'return':
                raise ValueError('Custom Hyprland return needs a reviewed integration adapter.')
            following = [t[0] for t in tokens[index:index+5]]
            if (word in {'hl', 'require'} and index + 1 < len(tokens) and tokens[index + 1][0] in {'=', ','}
                    or following[:4] == ['hl', '.', 'env', '=']
                    or following[:4] == ['function', 'hl', '.', 'env']
                    or following[:2] == ['function', 'require']):
                raise ValueError('Custom Hyprland hl binding needs a reviewed integration adapter.')
            if not stack and word == 'require' and [t[0] for t in tokens[index:index+4]] == ['require', '(', 'STRING', ')']:
                literal = data['body'][tokens[index+2][1]:tokens[index+2][2]]
                default_loaded |= literal in ('"default.hypr.omarchy"', "'default.hypr.omarchy'")
        if word in ('(', '[', '{', 'function', 'if', 'do', 'repeat'):
            stack.append(word)
        elif word in (')', ']', '}', 'end', 'until'):
            allowed = {')': {'('}, ']': {'['}, '}': {'{'}, 'end': {'function', 'if', 'do'}, 'until': {'repeat'}}
            if not stack or stack.pop() not in allowed[word]:
                raise ValueError('Unsupported Hyprland Lua structure')
    if stack or not default_loaded:
        raise ValueError('Qt integration requires the standard Omarchy Lua configuration.')
    return data


def prepare(plan, *, automatic):
    from application_themes import read
    available = plugins()
    if 5 not in available:
        if Path('/usr/lib/qt/plugins/platformthemes/libqt5ct.so').is_file():
            plan.wait('Qt', 'detector-unavailable', 'Could not inspect the installed Qt 5 integration. PySide6 and readable qtct plugin metadata are required.')
        return None
    if not {5, 6}.issubset(available):
        plan.wait('Qt', 'integration-unavailable', 'Both qt5ct and qt6ct must be installed before enabling the shared Qt integration.')
        return None
    common = available[5] & available[6]
    if not common:
        plan.wait('Qt', 'integration-unavailable', 'Installed Qt integrations have no shared selector; both qt5ct and qt6ct need compatible versions.')
        return None
    selected = 'qt6ct' if 'qt6ct' in common else 'qt5ct'
    try:
        raw = read('hypr-qt-integration', missing=False).decode()
        data = checked_config(raw)
        # Do not introduce a new desktop integration from the background timer.
        if data['integration'] is None and all(active(v) for v in available):
            return os.environ['QT_QPA_PLATFORMTHEME'].split(':')[0]
        previous = data['integration']
        if (previous or {}).get('selector') != selected and automatic:
            plan.wait('Qt', 'apply-integration', 'Press Apply once to enable the shared Qt font and palette integration.')
            return None
        session = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,200}', session):
            raise ValueError('Apply Qt integration from the active Omarchy desktop session.')
        data['integration'] = previous if (previous or {}).get('selector') == selected else {'selector': selected, 'session': session}
        plan.targets['hypr-qt-integration'] = encode(data).encode()
        plan.surfaces.append('Qt desktop integration for the next login')
        if data['integration']['session'] == session or not all(active(v) for v in available):
            plan.wait('Qt', 'login', 'Qt integration is saved. Sign out and back in once so launchers and newly opened Qt applications use it.')
        return selected
    except (OSError, ValueError, RuntimeError) as exc:
        plan.wait('Qt', 'integration-conflict', str(exc))
        return None
