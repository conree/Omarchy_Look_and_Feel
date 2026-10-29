"""Exercise real transactions only inside disposable homes."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import stat
import sys
import tomllib

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import transaction as tx
import global_font_actions as fonts


for original in (
    '[font]\nsize = 12\n[font.normal]\nfamily = "Old"\nstyle = "Regular"\n[window]\nopacity = 0.7\n',
    '[font]\nbold = { family = "Old", style = "Bold" }\nsize = 12\n[window]\nopacity = 0.7\n',
    '[font.normal]\nstyle = "Regular"\n[window]\nopacity = 0.7\n',
    '[font]\nnormal = {}\n[window]\nopacity = 0.7\n',
    '[font]\nsize = 12\n[[keyboard.bindings]]\nkey = "A"\naction = "Copy"\n[window]\nopacity = 0.7\n',
    '[font.normal]\nfamily = "Old"\n[font.bold]\nfamily = "Old"\nstyle = "Bold"\n[font.italic]\nfamily = "Old"\nstyle = "Italic"\n[window]\nopacity = 0.7\n',
    '[font]\nnormal = { family = "Old" }\nbold_italic = { family = "Old", style = "Bold Italic" }\n[window]\nopacity = 0.7\n',
    '[font.normal]\nfamily = "Old"\n[font.bold_italic]\nfamily = "Old"\nstyle = "Bold Italic"\n[window]\nopacity = 0.7\n',
):
    changed = fonts._replace_alacritty(original, 'Comic Code', 14)
    parsed = tomllib.loads(changed)
    assert parsed['font']['normal']['family'] == 'Comic Code'
    assert parsed['font']['size'] == 14 and parsed['window']['opacity'] == 0.7
    if 'style = "Regular"' in original:
        assert parsed['font']['normal']['style'] == 'Regular'
    if 'style = "Bold"' in original:
        assert parsed['font']['bold']['style'] == 'Bold'
        assert parsed['font']['bold']['family'] == 'Comic Code'
    if '[font.italic]' in original:
        assert parsed['font']['italic'] == {'family': 'Comic Code', 'style': 'Italic'}
    if 'bold_italic' in original:
        assert parsed['font']['bold_italic'] == {'family': 'Comic Code', 'style': 'Bold Italic'}
    if '[[keyboard.bindings]]' in original:
        assert parsed['keyboard']['bindings'] == [{'key': 'A', 'action': 'Copy'}]

# Exercise production target building and transaction/undo with a nested font
# table, including an independently edited setting outside the font section.
with TemporaryDirectory(prefix='laf-alacritty-nested-') as tmp, ExitStack() as stack:
    home = Path(tmp)
    stack.enter_context(patch.object(tx, '_home', return_value=home))
    stack.enter_context(patch.object(fonts, 'HOME', home))
    stack.enter_context(patch.object(fonts, 'CONFIG', home / '.config'))
    stack.enter_context(patch.dict(os.environ, {'XDG_CONFIG_HOME': str(home / '.config'), 'XDG_STATE_HOME': str(home / '.local/state'), 'QT_QPA_PLATFORMTHEME': ''}))
    stack.enter_context(patch.object(fonts.shutil, 'which', return_value='/fixture/alacritty'))
    path = home / tx.FILE_TARGETS['alacritty-config']
    path.parent.mkdir(parents=True)
    original = b'[font]\nsize = 12\n[font.normal]\nfamily = "Old"\nstyle = "Regular"\n[font.bold_italic]\nfamily = "Old"\nstyle = "Bold Italic"\n[[keyboard.bindings]]\nkey = "A"\naction = "Copy"\n[window]\nopacity = 0.7\n'
    path.write_bytes(original)
    targets, _ = fonts.build_global_font_targets('Avenir Next', 12, 'Comic Code', 14, {'Alacritty.desktop'})
    tx.apply_file_targets(targets, label='Alacritty font test')
    assert tomllib.loads(path.read_text())['font']['normal']['family'] == 'Comic Code'
    assert tomllib.loads(path.read_text())['font']['bold_italic'] == {'family': 'Comic Code', 'style': 'Bold Italic'}
    path.write_text(path.read_text().replace('opacity = 0.7', 'opacity = 0.8').replace('action = "Copy"', 'action = "Paste"'))
    tx.rollback_latest(label='Alacritty font test')
    result = tomllib.loads(path.read_text())
    assert result['font']['normal']['family'] == 'Old' and result['window']['opacity'] == 0.8
    assert result['font']['bold_italic'] == {'family': 'Old', 'style': 'Bold Italic'}
    assert result['keyboard']['bindings'] == [{'key': 'A', 'action': 'Paste'}]


def fixture(stack, tmp):
    home = Path(tmp)
    stack.enter_context(patch.object(tx, '_home', return_value=home))
    stack.enter_context(patch.object(fonts, 'HOME', home))
    stack.enter_context(patch.object(fonts, 'CONFIG', home / '.config'))
    # This fixture represents an unconfigured desktop. Do not inherit the
    # operator's active qtct selector and create extra Qt targets accidentally.
    stack.enter_context(patch.dict(os.environ, {'XDG_CONFIG_HOME': str(home / '.config'), 'XDG_STATE_HOME': str(home / '.local/state'), 'QT_QPA_PLATFORMTHEME': ''}))
    return home


# Font builders must not follow symlinks, hang on FIFOs, or consume oversized
# files after an earlier preflight. Missing paths are optional only when asked.
with TemporaryDirectory(prefix='laf-font-safe-read-') as tmp, ExitStack() as stack:
    home = fixture(stack, tmp)
    directory = home / 'config'
    directory.mkdir()
    target = directory / 'font.conf'
    assert fonts._read(target, allow_missing=True) == ''
    try: fonts._read(target)
    except tx.TransactionError: pass
    else: raise AssertionError('missing required file accepted')
    target.write_text('unchanged')
    assert fonts._read(target) == 'unchanged'
    target.chmod(0o4600)
    try: fonts._read(target)
    except tx.TransactionError: pass
    else: raise AssertionError('special permission bits accepted')
    target.chmod(0o600)
    target.write_bytes(b'x' * (tx.MAX_TARGET_BYTES + 1))
    try: fonts._read(target)
    except tx.TransactionError: pass
    else: raise AssertionError('oversized file accepted')
    target.unlink()
    os.mkfifo(target)
    try: fonts._read(target)
    except tx.TransactionError: pass
    else: raise AssertionError('FIFO accepted')
    target.unlink()
    sentinel = home / 'sentinel'
    sentinel.write_text('must not be read')
    target.symlink_to(sentinel)
    try: fonts._read(target)
    except tx.TransactionError: pass
    else: raise AssertionError('symlink target accepted')
    target.unlink()
    parent_link = home / 'parent-link'
    parent_link.symlink_to(directory, target_is_directory=True)
    try: fonts._read(parent_link / 'font.conf', allow_missing=True)
    except tx.TransactionError: pass
    else: raise AssertionError('symlink parent accepted')
    fontconfig = home / tx.FILE_TARGETS['fontconfig-monospace']
    fontconfig.parent.mkdir(parents=True, exist_ok=True)
    fontconfig.write_bytes(b'x' * (tx.MAX_TARGET_BYTES + 1))
    try: fonts.build_global_font_targets('Avenir Next', 12, 'Comic Code', 12, set())
    except tx.TransactionError: pass
    else: raise AssertionError('oversized shared fontconfig accepted')


# First use has no settings, shell override, GTK, or terminal directories.
with TemporaryDirectory(prefix='laf-font-first-use-') as tmp, ExitStack() as stack:
    home = fixture(stack, tmp)
    stack.enter_context(patch.object(fonts.shutil, 'which', return_value='/fixture/terminal'))
    targets, count = fonts.build_global_font_targets('Avenir Next', 12, 'Comic Code', 12, set(fonts.TERMINAL_COMMANDS))
    assert count == 5 and len(targets) == 12
    transaction_id = tx.apply_file_targets(targets, label='Global font settings')
    paths = {key: home / tx.FILE_TARGETS[key] for key in targets}
    assert all(path.read_bytes() == targets[key] for key, path in paths.items())
    assert json.loads(paths['global-font-selection'].read_text())['terminalFontFamily'] == 'Comic Code'
    assert all(stat.S_IMODE(path.parent.stat().st_mode) == 0o700 for path in paths.values())
    assert tx.rollback_latest(label='Global font settings') == transaction_id
    assert all(not path.exists() for path in paths.values())

# Existing files, unrelated content and directory permissions survive Apply/Undo.
with TemporaryDirectory(prefix='laf-font-existing-') as tmp, ExitStack() as stack:
    home = fixture(stack, tmp)
    gtk = home / tx.FILE_TARGETS['gtk3-settings']
    gtk.parent.mkdir(parents=True, mode=0o755)
    gtk.parent.chmod(0o755)
    original = b'[Settings]\ngtk-font-name=Old 10\ngtk-icon-theme-name=Keep\n'
    gtk.write_bytes(original)
    gtk.chmod(0o640)
    targets, _ = fonts.build_global_font_targets('Avenir Next', 12, 'Comic Code', 12, set())
    tx.apply_file_targets(targets, label='test')
    assert b'gtk-icon-theme-name=Keep' in gtk.read_bytes()
    assert stat.S_IMODE(gtk.stat().st_mode) == 0o640
    assert stat.S_IMODE(gtk.parent.stat().st_mode) == 0o755
    tx.rollback_latest(label='test')
    assert gtk.read_bytes() == original
    assert stat.S_IMODE(gtk.parent.stat().st_mode) == 0o755

# Unsafe destinations refuse the entire batch before any target directory creation.
for bad_kind in ('symlink-parent', 'file-parent', 'directory-leaf', 'symlink-leaf'):
    with TemporaryDirectory(prefix='laf-font-unsafe-') as tmp, ExitStack() as stack:
        home = fixture(stack, tmp)
        config = home / '.config'
        config.mkdir()
        outside = home / 'sentinel'
        outside.mkdir()
        gtkdir = config / 'gtk-3.0'
        if bad_kind == 'symlink-parent': gtkdir.symlink_to(outside, target_is_directory=True)
        elif bad_kind == 'file-parent': gtkdir.write_text('keep')
        else:
            gtkdir.mkdir()
            if bad_kind == 'directory-leaf': (gtkdir / 'settings.ini').mkdir()
            else: (gtkdir / 'settings.ini').symlink_to(outside / 'untouched')
        try:
            tx.apply_file_targets({'global-font-selection': b'{}', 'gtk3-settings': b'new'}, label='unsafe')
        except (tx.TransactionError, NotADirectoryError): pass
        else: raise AssertionError(bad_kind)
        assert not (config / 'omarchy-look-and-feel').exists()
        assert not list(outside.iterdir())

# A mid-write error restores earlier writes and removes newly created files.
with TemporaryDirectory(prefix='laf-font-failure-') as tmp, ExitStack() as stack:
    home = fixture(stack, tmp)
    gtk = home / tx.FILE_TARGETS['gtk3-settings']
    gtk.parent.mkdir(parents=True)
    gtk.write_bytes(b'[Settings]\ngtk-font-name=Original 10\n')
    failed_path = home / tx.FILE_TARGETS['global-font-selection']
    original_write = tx._atomic_write
    def fail_once(path, payload, mode):
        if path == failed_path and payload == b'new selection':
            raise OSError('injected write failure')
        return original_write(path, payload, mode)
    with patch.object(tx, '_atomic_write', side_effect=fail_once):
        try:
            tx.apply_file_targets({'gtk3-settings': b'[Settings]\ngtk-font-name=Changed 12\n', 'global-font-selection': b'new selection'}, label='failure')
        except tx.TransactionError as exc: assert 'was rolled back' in str(exc), str(exc)
        else: raise AssertionError('failure accepted')
    assert gtk.read_bytes() == b'[Settings]\ngtk-font-name=Original 10\n'
    assert not failed_path.exists()
print('7 isolated font transaction scenarios passed (12-target first Apply/Undo, permissions, 4 unsafe paths, failure rollback).')
