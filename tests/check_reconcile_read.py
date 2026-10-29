"""Binary comparisons and post-validation path swaps in an isolated home."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import appearance_policy as policy
import transaction as tx

with TemporaryDirectory(prefix='laf-reconcile-read-') as tmp:
    root = Path(tmp)
    home = root / 'home'
    home.mkdir()
    config = home / 'config'
    config.mkdir()
    path = config / 'state'
    external = root / 'external'
    external.mkdir()
    (external / 'state').write_bytes(b'outside-match')
    with patch.object(Path, 'home', return_value=home), patch.object(tx, '_home', return_value=home), \
         patch.dict(tx.FILE_TARGETS, {'test-target': 'config/state'}):
        assert policy.changed_targets({'test-target': b''}) == {'test-target': b''}
        path.write_bytes(b'\x00\xff')
        assert policy.changed_targets({'test-target': b'\x00\xff'}) == {}
        assert policy.changed_targets({'test-target': b'\x00\xfe'}) == {'test-target': b'\x00\xfe'}
        path.unlink()
        os.mkfifo(path)
        try:
            policy.changed_targets({'test-target': b'value'})
        except tx.TransactionError:
            pass
        else:
            raise AssertionError('FIFO comparison allowed')
        path.unlink()
        path.write_bytes(b'local')
        original = tx._ensure_home_path
        def swap_after_check(p, **kwargs):
            checked = original(p, **kwargs)
            config.rename(home / 'original-config')
            config.symlink_to(external, target_is_directory=True)
            return checked
        with patch.object(tx, '_ensure_home_path', side_effect=swap_after_check):
            try:
                policy.changed_targets({'test-target': b'outside-match'})
            except tx.TransactionError:
                pass
            else:
                raise AssertionError('parent symlink swap was followed')
        assert (external / 'state').read_bytes() == b'outside-match'
print('Reconciliation comparison: missing, binary, FIFO and parent swap checks passed.')
