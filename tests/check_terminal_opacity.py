"""Real transactions and native config parsers in a disposable HOME only."""
from pathlib import Path
from unittest.mock import patch
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib

SOURCE = Path(__file__).resolve().parents[1]
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-opacity-') as home:
        env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=home+'/.config',
                   XDG_DATA_HOME=home+'/.local/share', XDG_STATE_HOME=home+'/.state',
                   XDG_CACHE_HOME=home+'/.cache', PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True, timeout=40)
    raise SystemExit()

sys.path.insert(0, str(SOURCE))
import appearance_policy as policy
import opacity_actions as opacity
import terminal_preferences as prefs
import transaction as tx
import wezterm_blocks as blocks
import global_font_actions as fonts

originals = {
    'ghostty-config': 'font-size = 11\nbackground-opacity = 0.6\ncommand = /bin/sh\n',
    'kitty-config': 'font_family Old\nfont_size 11\nbackground_opacity 0.6\nscrollback_lines 1234\n',
    'foot-config': '[main]\nfont=Old:size=11\ninclude=/missing-optional-fixture\ninclude=/another-fixture\n[colors-dark]\nalpha=0.6\n',
    'alacritty-config': '[font]\nnormal = { family = "Old" }\nsize = 11\n[window]\nopacity = 0.6\npadding.x = 12\n',
    'wezterm-config': 'local config = {}\nconfig.scrollback_lines = 1234\nreturn config\n',
}


def path(target):
    return Path.home() / tx.FILE_TARGETS[target]


def put(target, text):
    result = path(target)
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(text)


def reset():
    for target, text in originals.items():
        put(target, text)


def assert_opacity(percent):
    assert f'background-opacity = {percent/100:g}' in path('ghostty-config').read_text()
    assert 'background-opacity-cells = false' in path('ghostty-config').read_text()
    assert f'background_opacity {percent/100:g}' in path('kitty-config').read_text()
    assert tomllib.loads(path('alacritty-config').read_text())['window']['opacity'] == percent/100
    assert f'alpha={percent/100:g}' in path('foot-config').read_text()
    assert f'= {percent/100:g}\n' in blocks.decode(path('wezterm-config').read_text())['opacity']


reset()
# Old policies remain valid; invalid input never enters a transaction.
assert policy.validate({'schemaVersion': 1, 'fonts': None, 'theme': None, 'background': None})
for invalid in (None, True, -1, 101, 70.0, '70'):
    try:
        opacity.validate_percent(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError(invalid)

# Both interleavings of independent Fonts/Opacity Undo preserve each other.
with patch.object(opacity.shutil, 'which', return_value='/fixture/terminal'), patch.object(opacity, '_refresh', return_value=({}, [])):
    for undo_opacity_first in (True, False):
        for apply_opacity_first in (True, False):
            reset()
            def apply_fonts():
                targets, _ = fonts.build_global_font_targets('Test Sans', 12, 'Test Mono', 14,
                                                            set(fonts.TERMINAL_COMMANDS))
                targets = {key: value for key, value in targets.items()
                           if key in originals or key == 'ghostty-font-overlay'}
                tx.apply_file_targets(targets, label='opacity-test-fonts', owned_fields=prefs.FONT_FIELDS)
            if apply_opacity_first:
                opacity.apply(70); apply_fonts()
            else:
                apply_fonts(); opacity.apply(70)
            assert_opacity(70)
            if undo_opacity_first:
                opacity.undo()
                assert 'Test Mono' in path('kitty-config').read_text()
                tx.rollback_latest(label='opacity-test-fonts')
            else:
                tx.rollback_latest(label='opacity-test-fonts')
                assert_opacity(70)
                opacity.undo()
            for key, text in originals.items():
                if key == 'wezterm-config':
                    assert path(key).read_text() == text
                else:
                    actual, expected = prefs.decode(key, path(key).read_bytes()), prefs.decode(key, text.encode())
                    assert all(actual[field] == expected[field] for field in prefs.FIELDS[key]), (key, actual, expected)
    # Undo must preserve unrelated user changes.
    reset(); opacity.apply(70)
    with path('kitty-config').open('a') as stream:
        stream.write('enable_audio_bell no\n')
    opacity.undo()
    assert path('kitty-config').read_text() == originals['kitty-config'] + 'enable_audio_bell no\n'

    # A terminal installed later belongs to the original Apply's grouped Undo.
    reset()
    with patch.object(opacity.shutil, 'which', side_effect=lambda exe: '/fixture/terminal' if exe == 'ghostty' else None):
        opacity.apply(65)
    opacity.apply(65, automatic=True)
    with patch.object(opacity, 'refresh', return_value=({}, [])) as refresh:
        opacity.undo()
        assert 'kitty-config' in refresh.call_args.args[0]
    # First no-op Apply still owns the original baseline after drift/repair.
    reset(); opacity.apply(70)
    baseline = {key: path(key).read_bytes() for key in originals}
    opacity.apply(70)
    path('kitty-config').write_text(path('kitty-config').read_text().replace('background_opacity 0.7', 'background_opacity 0.4'))
    opacity.apply(70, automatic=True)
    opacity.undo()
    assert all(path(key).read_bytes() == raw for key, raw in baseline.items())
    opacity.undo()

    # First-use font ownership must not acquire absent opacity fields.
    for key in originals:
        path(key).unlink()
    apply_fonts()
    opacity.apply(70)
    tx.rollback_latest(label='opacity-test-fonts')
    assert_opacity(70)
    opacity.undo()

    # The 0% and 100% endpoints use native floating-point configuration values.
    for percent in (0, 100):
        reset(); opacity.apply(percent)
        assert tomllib.loads(path('alacritty-config').read_text())['window']['opacity'] == percent / 100
        opacity.undo()

    # Restoring only the helper CSS must also refresh an already-open Ghostty.
    reset(); opacity.apply(50)
    expected_css = path('ghostty-opacity-css').read_bytes()
    path('ghostty-opacity-css').write_bytes(b'/* previous helper CSS */\n')
    opacity.apply(50)
    with patch.object(opacity, 'refresh', return_value=({}, [])) as refresh:
        opacity.undo()
        assert 'ghostty-config' in refresh.call_args.args[0]
        assert path('ghostty-opacity-css').read_bytes() == b'/* previous helper CSS */\n'
    # Undo preserved the intentional external edit; remove that fixture edit
    # before cleaning up the preceding, independently owned operation.
    path('ghostty-opacity-css').write_bytes(expected_css)
    opacity.undo()

# Native parsers consume generated files without opening windows.
reset()
with patch.object(opacity.shutil, 'which', return_value='/fixture/terminal'):
    planned = opacity.build(70)
for target, raw in planned.items():
    if target != 'foot-config':
        path(target).write_bytes(raw)
if shutil.which('ghostty'):
    subprocess.run(['ghostty', '+validate-config', '--config-file='+str(path('ghostty-config'))], check=True, capture_output=True)
if shutil.which('foot'):
    # Includes above test duplicate directives, but point at deliberately absent files.
    native = planned['foot-config'].decode().replace('include=/missing-optional-fixture\n', '').replace('include=/another-fixture\n', '')
    path('foot-config').write_text(native)
    subprocess.run(['foot', '--check-config', '--config='+str(path('foot-config'))], check=True, capture_output=True)
if shutil.which('alacritty'):
    subprocess.run(['alacritty', 'migrate', '--dry-run', '--skip-imports', '--config-file', str(path('alacritty-config'))], check=True, capture_output=True)
if shutil.which('lua'):
    case = Path.home()/'opacity.lua'
    case.write_text('local c = (function()\n' + path('wezterm-config').read_text()
                    + 'end)()\nassert(c.window_background_opacity == 0.7)\nassert(c.scrollback_lines == 1234)\n')
    subprocess.run(['lua', str(case)], check=True)

# Persistent notices survive no-op ticks, clear on restart/Undo; reloads retry.
live = {'foot': {'boot:1:100'}, 'kitty': {'boot:2:100'}}
with patch('application_restarts.processes', side_effect=lambda name: live[name]), \
     patch('terminal_reload.reload_terminals', return_value={'requested': [], 'failed': ['ghostty']}) as reload:
    before = {key: opacity._hash(key) for key in ('foot-config', 'kitty-config', 'ghostty-config')}
    with patch.object(opacity.shutil, 'which', return_value='/fixture/terminal'):
        for target, raw in opacity.build(80).items():
            path(target).write_bytes(raw)
    _, notices = opacity._refresh(before)
    assert {row['app'] for row in notices} == {'Foot', 'Kitty', 'ghostty'}
    _, again = opacity._refresh({})
    assert again == notices and 'ghostty-config' in reload.call_args.args[0]
    live = {'foot': {'boot:1:200'}, 'kitty': set()}
    with patch('terminal_reload.reload_terminals', return_value={'requested': ['ghostty'], 'failed': []}):
        assert opacity._refresh({})[1] == []
        state = tx.transactions_path().parent / 'opacity-reload.json'
        for malformed in ('[]', '{broken', '{"failedTargets":[{}]}'):
            state.write_text(malformed)
            opacity._refresh({})
            assert isinstance(json.loads(state.read_text()), dict)

for target, malformed in [('ghostty-config', 'background-opacity=0.5\nbackground-opacity=0.7\n'),
                          ('alacritty-config', 'window={opacity=0.5}\n')]:
    try:
        prefs.decode(target, malformed.encode())
    except ValueError:
        pass
    else:
        raise AssertionError('Ambiguous config accepted')
print('Terminal opacity passed: all 5 adapters, 4 Apply/Undo orders, drift/no-op repair, unrelated edits, native parsers/Lua, pending lifecycle and reload retries.')
