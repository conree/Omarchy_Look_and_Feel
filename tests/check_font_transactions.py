"""Exercise real transactions only inside disposable homes."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import stat
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import transaction as tx
import global_font_actions as fonts


def fixture(stack, tmp):
    home = Path(tmp)
    stack.enter_context(patch.object(tx, '_home', return_value=home))
    stack.enter_context(patch.object(fonts, 'HOME', home))
    stack.enter_context(patch.object(fonts, 'CONFIG', home / '.config'))
    # This fixture represents an unconfigured desktop. Do not inherit the
    # operator's active qtct selector and create extra Qt targets accidentally.
    stack.enter_context(patch.dict(os.environ, {'XDG_CONFIG_HOME': str(home / '.config'), 'XDG_STATE_HOME': str(home / '.local/state'), 'QT_QPA_PLATFORMTHEME': ''}))
    return home


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
