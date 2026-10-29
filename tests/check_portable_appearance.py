"""Behavioral regressions for portable ownership, drift, recovery, and adapters.

Run in an isolated HOME; no Omarchy command, host app, or host setting is used.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-portable-test-') as directory:
        env = dict(os.environ, HOME=directory, XDG_CONFIG_HOME=directory + '/config',
                   XDG_STATE_HOME=directory + '/state', XDG_DATA_HOME=directory + '/data',
                   GSETTINGS_BACKEND='keyfile', PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True)
    raise SystemExit()

sys.path.insert(0, str(SOURCE))
import transaction as tx
import managed_preferences as prefs
import appearance_policy as policy
import application_themes as themes
from app_font_actions import typora_css
from css_takeover import strip_appearance


def path(key):
    return Path.home() / tx.FILE_TARGETS[key]


def put(key, raw):
    dest = path(key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)


def journal(identity):
    return json.loads((tx.transactions_path() / identity / 'transaction.json').read_bytes())


def apply(targets, label, parent=None):
    return tx.apply_file_targets(targets, label=label, parent_transaction=parent)


# First-save policy ownership: Theme and Fonts can be undone independently.
theme = {'mode': 'light', 'light': 'one', 'dark': 'two'}
font = {'systemId': 'font:a', 'systemSize': 12, 'terminalId': 'font:b', 'terminalSize': 12}
first = apply({'appearance-policy': policy.update('theme', theme)}, 'policy-theme')
apply({'appearance-policy': policy.update('fonts', font)}, 'policy-font')
tx.rollback_latest(label='policy-theme')
assert policy.read()['theme'] is None and policy.read()['fonts'] == font
tx.rollback_latest(label='policy-font')
assert policy.read()['fonts'] is None

# Shared INI fields: later font writes survive Theme Undo, including a repair
# whose bytes contain the later font value.
put('gtk3-settings', b'[Settings]\ngtk-theme-name=old\ngtk-font-name=Old 10\ncustom=keep\n')
parent = apply({'gtk3-settings': b'[Settings]\ngtk-theme-name=new\ngtk-font-name=Old 10\ncustom=keep\n'}, 'theme-ini')
apply({'gtk3-settings': b'[Settings]\ngtk-theme-name=new\ngtk-font-name=New 12\ncustom=keep\n'}, 'font-ini')
put('gtk3-settings', b'[Settings]\ngtk-theme-name=drift\ngtk-font-name=New 12\ncustom=keep\n')
child = apply({'gtk3-settings': b'[Settings]\ngtk-theme-name=new\ngtk-font-name=New 12\ncustom=keep\n'}, 'auto-theme', parent)
tx.rollback_latest(label='theme-ini')
actual = prefs.decode('gtk3-settings', path('gtk3-settings').read_bytes())
assert actual['Settings/gtk-theme-name'] == 'old' and actual['Settings/gtk-font-name'] == 'New 12'
assert 'custom=keep' in actual['_text'] and journal(child)['state'] == 'rolled_back'

# A managed CSS font block is independent of the theme's competing-color repair.
for initially_present in (False, True):
    path('typora-base-user-css').unlink(missing_ok=True)
    original = b'body { color: black; padding: 7px; }\n' if initially_present else b''
    if initially_present:
        put('typora-base-user-css', original)
    cleaned = strip_appearance(original.decode()).encode()
    label = f'css-theme-{initially_present}'
    apply({'typora-base-user-css': cleaned}, label)
    fonts = typora_css(cleaned.decode(), 'Test Sans', 12, 'Test Mono', 13).encode()
    apply({'typora-base-user-css': fonts}, f'css-font-{initially_present}')
    tx.rollback_latest(label=label)
    actual = prefs.decode('typora-base-user-css', path('typora-base-user-css').read_bytes())
    assert actual['body'] == original.decode().rstrip() and 'Test Sans' in actual['fonts']

# Group finalization survives a process stopping after parent restore, before
# child bookkeeping. Recovery must never leave that child available for Undo.
put('gtk4-settings', b'[Settings]\ngtk-theme-name=old\n')
parent = apply({'gtk4-settings': b'[Settings]\ngtk-theme-name=new\n'}, 'crash-group')
put('gtk4-settings', b'[Settings]\ngtk-theme-name=drift\n')
child = apply({'gtk4-settings': b'[Settings]\ngtk-theme-name=new\n'}, 'auto-crash-group', parent)
real_write = tx._write_journal


def crash_on_child(destination, record):
    if destination.parent.name == child and record['state'] == 'rolled_back':
        raise SystemExit(23)
    return real_write(destination, record)


with patch.object(tx, '_write_journal', side_effect=crash_on_child):
    try:
        tx.rollback_latest(label='crash-group')
    except SystemExit as exc:
        assert exc.code == 23
    else:
        raise AssertionError('crash injection did not run')
assert journal(parent)['state'] == 'rolled_back' and journal(child)['state'] == 'committed'
assert parent in tx.recover_pending()
assert journal(child)['state'] == 'rolled_back' and journal(parent)['groupUndoPending'] is False

# Field-aware terminal Undo restores fonts while preserving external opacity.
put('kitty-config', b'font_family Old\nbackground_opacity .5\n')
parent = apply({'kitty-config': b'font_family New\nbackground_opacity .5\n'}, 'plain-drift')
put('kitty-config', b'font_family Drift\nbackground_opacity .8\n')
apply({'kitty-config': b'font_family New\nbackground_opacity .8\n'}, 'auto-plain', parent)
with path('kitty-config').open('ab') as stream:
    stream.write(b'scrollback_lines 2000\n')
tx.rollback_latest(label='plain-drift')
assert b'font_family Old' in path('kitty-config').read_bytes()
assert b'background_opacity .8' in path('kitty-config').read_bytes()
assert b'scrollback_lines 2000' in path('kitty-config').read_bytes()

# CSS syntax/layout preservation and idempotence, including nested functions,
# quoted semicolons, @font-face, and the plugin's separately owned font block.
css = '''/* keep */ @font-face { font-family: Icons; src: url("a;b.woff"); }
@media screen { #write p { color: rgb(0, 0, 0) !important; padding: calc(2px + 1em); } }
.icon { font-family: Icons; color: red; }
'''
cleaned = strip_appearance(css)
assert 'font-family: Icons' in cleaned and 'calc(2px + 1em)' in cleaned
assert 'color: rgb' not in cleaned and cleaned == strip_appearance(cleaned)
for invalid in ('@import "outside.css";', 'body { color: "unterminated; }', 'body { color: red;'):
    try:
        strip_appearance(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError('ambiguous CSS accepted')

theme_dir = Path.home() / 'themes/portable'
theme_dir.mkdir(parents=True)
(theme_dir / 'colors.toml').write_text('mode="light"\nbackground="#ffffff"\nforeground="#fefefe"\naccent="#123456"\n')
colors = themes.palette(theme_dir)
assert colors['foreground'] == '#000000'
qt_colors = themes.qt_palette(colors).decode().splitlines()[1].split('=', 1)[1].split(', ')
assert len(qt_colors) == 21 and qt_colors[20] != qt_colors[9]
gtk = themes.gtk_stylesheet(css.replace('@media screen', '@binding-set unused'), colors)
assert gtk == themes.gtk_stylesheet(gtk.decode(), colors)
solid = next(line.split('{', 1)[0] for line in gtk.decode().splitlines()
             if 'window.background' in line and 'background-color:' in line)
assert all(selector.strip().startswith('window.background') for selector in solid.split(','))
assert 'dracula' not in themes.typora_stylesheet(colors).decode().lower()

# Browser flags remove only an actual theme extension; no other extension or
# policy file is touched or even requested as a transaction target.
extension = Path.home() / 'theme-extension'
extension.mkdir()
(extension / 'manifest.json').write_text('{"name":"Example", "theme":{"colors":{}}}')
flags = f'--load-extension=/keep/extension,{extension},/keep/second\n--safe-option\n'.encode()
assert themes.brave_theme_flags(flags) == b'--load-extension=/keep/extension,/keep/second\n--safe-option\n'
launcher = b'[Desktop Entry]\nExec=/usr/bin/onlyoffice-desktopeditors %U\nName=Office\n'
assert themes.onlyoffice_launcher(launcher) == b'[Desktop Entry]\nExec=/usr/bin/onlyoffice-desktopeditors --system-title-bar %U\nName=Office\n'

# Automatic recovery is subject to the same offline-profile exclusion as Apply.
token = prefs.AUTOMATIC.set(True)
try:
    for target in ('typora-profile', 'brave-default-preferences'):
        try:
            prefs.guard_paths([path(target)])
        except RuntimeError as exc:
            assert 'explicit Apply or Undo' in str(exc)
        else:
            raise AssertionError('automatic offline-profile write was allowed')
finally:
    prefs.AUTOMATIC.reset(token)

print('Portable appearance regressions passed: independent policy/INI/CSS Undo, drift consolidation, crash finalization, CSS syntax/layout, contrast, extension preservation, and offline-profile exclusion.')
