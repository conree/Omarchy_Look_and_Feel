"""Exercise missing-wallpaper repair, recovery, Undo and drift with real files."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import appearance_actions as a
import transaction as tx


with TemporaryDirectory() as tmp, ExitStack() as stack:
    home = Path(tmp)
    current = home / 'current'
    current.mkdir()
    link = current / 'background'
    missing = home / 'deleted.jpg'
    selected = home / 'selected.jpg'
    selected.write_bytes(b'new wallpaper')
    other = home / 'other.jpg'
    other.write_bytes(b'other wallpaper')
    link.symlink_to(missing)
    stack.enter_context(patch.object(tx, '_home', return_value=home))
    stack.enter_context(patch.object(a, 'CURRENT_DIR', current))
    stack.enter_context(patch.object(a, 'transactions_path', return_value=home / 'transactions'))
    stack.enter_context(patch.object(a, '_unlock_state', return_value='default'))

    def set_image(*args, **kwargs):
        assert args[:3] == ('theme', 'bg', 'set')
        link.unlink()
        link.symlink_to(args[3])

    command = stack.enter_context(patch.object(a, '_omarchy', side_effect=set_image))
    assert a._background_state() is None
    assert a._background_action_state() == str(missing)
    try:
        a.apply_action('background', str(missing), {str(missing)})
    except tx.TransactionError as exc:
        assert 'selected wallpaper file is missing' in str(exc)
    else:
        raise AssertionError('stale missing selection reported as already current')
    # A command failure after changing the link restores its prior broken state.
    def fail(*args, **kwargs):
        set_image(*args, **kwargs)
        raise RuntimeError('renderer failed')
    command.side_effect = fail
    try:
        a.apply_action('background', str(selected), {str(selected)})
    except tx.TransactionError as exc:
        assert 'previous background was restored' in str(exc)
    else:
        raise AssertionError('failed command accepted')
    assert link.readlink() == missing and not link.exists()
    # A successful command must still leave a readable image, not just a link.
    def disappear(*args, **kwargs):
        set_image(*args, **kwargs)
        selected.unlink()
    command.side_effect = disappear
    try:
        a.apply_action('background', str(selected), {str(selected)})
    except tx.TransactionError as exc:
        assert 'readback mismatch' in str(exc)
    else:
        raise AssertionError('dangling selected image reported as saved')
    assert link.readlink() == missing and not link.exists()
    selected.write_bytes(b'new wallpaper')
    command.side_effect = set_image
    result = a.apply_action('background', str(selected), {str(selected)})
    assert result['readback'] == str(selected) and not result['undoAvailable']
    assert a.action_status()['background']['observedValue'] == str(selected)
    assert not a.action_status()['background']['undoAvailable']
    try:
        a.rollback_action('background')
    except tx.TransactionError as exc:
        assert 'no image to restore' in str(exc)
    else:
        raise AssertionError('Undo offered a deleted wallpaper')
    # Interrupted repair restores the dangling link; external drift is preserved.
    directory = a._kind_root('background') / result['transaction']
    journal = a._read_journal(directory, 'background')
    journal['state'] = 'applying'
    a._write_journal(directory / 'action.json', journal)
    a._recover_pending_locked()
    assert link.readlink() == missing
    journal['state'] = 'applying'
    a._write_journal(directory / 'action.json', journal)
    link.unlink()
    link.symlink_to(other)
    try:
        a._recover_pending_locked()
    except tx.TransactionError as exc:
        assert 'changed independently' in str(exc)
    else:
        raise AssertionError('external change overwritten')
    assert link.readlink() == other
    journal['state'] = 'rolled_back'
    a._write_journal(directory / 'action.json', journal)
    # Ordinary Apply and Undo retain their existing behavior.
    result = a.apply_action('background', str(selected), {str(selected)})
    assert result['undoAvailable']
    assert a.rollback_action('background')['readback'] == str(other)
    assert link.readlink() == other

print('Missing wallpaper repair, failed/interrupted recovery, drift and ordinary Undo passed.')
