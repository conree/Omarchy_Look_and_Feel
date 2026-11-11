"""Flea's UI text-size override follows Omarchy through a journaled target."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import transaction as tx
import global_font_actions as fonts
import flea_preferences as flea
from managed_preferences import decode, encode


def fixture(stack, home):
    home = Path(home)
    stack.enter_context(patch.object(tx, '_home', return_value=home))
    stack.enter_context(patch.object(fonts, 'HOME', home))
    stack.enter_context(patch.object(fonts, 'CONFIG', home / '.config'))
    stack.enter_context(patch.dict(os.environ, {
        'XDG_CONFIG_HOME': str(home / '.config'),
        'XDG_STATE_HOME': str(home / '.local/state'),
    }))
    return home


with TemporaryDirectory(prefix='laf-flea-ui-') as tmp, ExitStack() as stack:
    home = fixture(stack, tmp)
    path = home / tx.FILE_TARGETS['flea-ui-state']
    path.parent.mkdir(parents=True)
    original = b'{"display":{"textSize":{"mode":12},"hyprlandIcons":false},"keep":1}\n'
    path.write_bytes(original)
    target = flea.build()
    assert json.loads(target)['display']['textSize'] == {'mode': 'system'}
    assert json.loads(target)['display']['hyprlandIcons'] is False
    assert json.loads(target)['keep'] == 1
    tx.apply_file_targets({'flea-ui-state': target}, label='Flea UI text',
                          owned_fields={'flea-ui-state': {'display/textSize'}})
    assert json.loads(path.read_text())['display']['textSize'] == {'mode': 'system'}
    tx.rollback_latest(label='Flea UI text')
    assert path.read_bytes() == original

    # A pinned 20 px stop is replaced too.
    path.write_text('{"display":{"textSize":{"mode":20}}}\n')
    tx.apply_file_targets({'flea-ui-state': flea.build()}, label='Flea UI text',
                          owned_fields={'flea-ui-state': {'display/textSize'}})
    assert json.loads(path.read_text())['display']['textSize'] == {'mode': 'system'}
    tx.rollback_latest(label='Flea UI text')
    assert json.loads(path.read_text())['display']['textSize'] == {'mode': 20}

    # Missing state file: Apply creates Follow Omarchy, Undo removes it.
    path.unlink()
    tx.apply_file_targets({'flea-ui-state': flea.build()}, label='Flea UI text',
                          owned_fields={'flea-ui-state': {'display/textSize'}})
    assert json.loads(path.read_text())['display']['textSize'] == {'mode': 'system'}
    tx.rollback_latest(label='Flea UI text')
    assert not path.exists()

    # Malformed state is refused instead of overwritten.
    path.write_text('{bad')
    try:
        flea.build()
    except ValueError:
        pass
    else:
        raise AssertionError('malformed Flea state accepted')
    for raw in (b'{"display":{"textSize":{"mode":8}}}', b'{"display":{"textSize":{"mode":"big"}}}',
                b'[]', b'{"display":[]}'):
        try:
            decode('flea-ui-state', raw)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid Flea state accepted: ' + raw.decode())

print('Flea UI-state adapter passed: pinned-to-system, other keys preserved, exact Undo, missing-file restore, malformed refusal.')

# An XDG_STATE_HOME outside HOME must not be silently redirected to
# ~/.local/state; the target becomes absolute and fails the home boundary.
with TemporaryDirectory(prefix='laf-flea-ui-outside-') as tmp:
    home = Path(tmp)
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'),
               XDG_STATE_HOME='/var/tmp/laf-outside-state',
               PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    result = subprocess.run(
        [sys.executable, '-B', '-c',
         "import transaction; print(transaction.FILE_TARGETS['flea-ui-state'])"],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert os.path.isabs(result.stdout.strip()), result.stdout
print('Out-of-home XDG_STATE_HOME is not silently redirected.')
