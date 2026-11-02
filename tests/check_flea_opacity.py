"""Flea opacity transactions, shared shell ownership, and runtime notices."""
from pathlib import Path
from unittest.mock import patch
import json
import os
import subprocess
import sys
import tempfile
import tomllib

SOURCE = Path(__file__).resolve().parents[1]
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-flea-opacity-') as home:
        env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=home+'/.config',
                   XDG_STATE_HOME=home+'/.state', XDG_DATA_HOME=home+'/.data',
                   XDG_CACHE_HOME=home+'/.cache', PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True)
    raise SystemExit()

sys.path.insert(0, str(SOURCE))
import appearance_policy as policy
import flea_opacity as flea
import shell_preferences as prefs
import transaction as tx

path = Path.home() / tx.FILE_TARGETS[flea.TARGET]
path.parent.mkdir(parents=True)
original = b'# preserve\n[font]\nbase-size = 16\n[flea]\nbackground-alpha = 0.7\n[bar]\nsize = 31\n'
path.write_bytes(original)


def size(value):
    data = prefs.decode(path.read_bytes())
    data['font/base-size'] = f'base-size = {value}\n'
    return tx.apply_file_targets({flea.TARGET: prefs.encode(data)}, label='Font ownership test',
                                owned_fields={flea.TARGET: {'font/base-size'}})


def values():
    return tomllib.loads(path.read_text())


with patch.object(flea.shutil, 'which', return_value='/usr/bin/flea'), patch.object(flea, 'pending', return_value=[]):
    # Both Undo orders preserve the other control and unrelated values.
    size(20)
    flea.apply(30)
    tx.rollback_latest(label='Font ownership test')
    assert values()['font']['base-size'] == 16 and values()['flea']['background-alpha'] == .3
    flea.undo()
    assert values()['flea']['background-alpha'] == .7 and values()['bar']['size'] == 31
    flea.apply(40)
    size(22)
    flea.undo()
    assert values()['font']['base-size'] == 22 and values()['flea']['background-alpha'] == .7
    tx.rollback_latest(label='Font ownership test')

    # No-op Apply owns the original baseline across drift repair.
    path.write_bytes(original)
    parent = flea.apply(70)['transaction']
    data = prefs.decode(path.read_bytes()); data[flea.FIELD] = 'background-alpha = 0.2\n'
    path.write_bytes(prefs.encode(data))
    child = flea.apply(70, automatic=True)['transaction']
    assert child and values()['flea']['background-alpha'] == .7
    assert json.loads((tx.transactions_path()/child/'transaction.json').read_text())['parentTransaction'] == parent
    assert flea.apply(70, automatic=True)['transaction'] is None
    flea.undo()
    assert values()['flea']['background-alpha'] == .7

    # The same baseline protection for an initially unchanged font size.
    size(16)
    data = prefs.decode(path.read_bytes()); data['font/base-size'] = 'base-size = 24\n'
    path.write_bytes(prefs.encode(data))
    parent = policy.latest('Font ownership test')
    data['font/base-size'] = 'base-size = 16\n'
    tx.apply_file_targets({flea.TARGET: prefs.encode(data)}, label='Font repair',
                         parent_transaction=parent[1].name, owned_fields={flea.TARGET: {'font/base-size'}})
    tx.rollback_latest(label='Font ownership test')
    assert values()['font']['base-size'] == 16

    for percent in (0, 75, 100):
        flea.apply(percent)
        assert values()['flea']['background-alpha'] == percent / 100
        assert policy.read()['fleaOpacity'] == percent
        flea.undo()
    path.unlink()
    flea.apply(50); flea.undo()
    assert not path.exists()

for text in ('[flea]', '[font]\nbase-size = 16\n[flea]', '[font]\nbase-size = 16'):
    data = prefs.decode(text.encode()); data[flea.FIELD] = 'background-alpha = 0.5\n'
    assert tomllib.loads(prefs.encode(data).decode())['flea']['background-alpha'] == .5
for text in ('[flea]\nbackground-alpha = 2\n', 'flea.background-alpha = 0.5\n', '[flea]\nbackground-alpha = "0.5"', '[flea]\nbackground-alpha = nan', 'x = """\n[flea]\n"""'):
    try:
        prefs.decode(text.encode())
    except ValueError:
        pass
    else:
        raise AssertionError('Unsafe/unsupported TOML accepted: ' + text)
for bad in (True, -1, 101, 70.0, '70', None):
    try:
        flea.validate_percent(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(bad)

def reply(value):
    return subprocess.CompletedProcess([], 0, json.dumps(value), '')

with patch.object(flea.subprocess, 'run', side_effect=[reply([{'class':'com.thisisgm.flea','pid':123}]), reply({'alpha':1, 'clear':False})]):
    assert 'started fully opaque' in flea.pending(50)[0]['reason']
with patch.object(flea.subprocess, 'run', side_effect=[reply([{'class':'com.thisisgm.flea','pid':123}]), reply({'alpha':128/255, 'clear':True})]):
    assert flea.pending(50) == []
print('Flea opacity passed: independent Font/Opacity Undo, no-op baseline and repair, 0/75/100%, missing file restoration, TOML guards, and opaque-launch notice.')
