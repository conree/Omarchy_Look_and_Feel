"""Real blur transactions in an isolated HOME; compositor commands are mocked."""
from pathlib import Path
from unittest.mock import patch
import os, subprocess, sys, tempfile

SOURCE = Path(__file__).resolve().parents[1]
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-blur-') as home:
        subprocess.run([sys.executable, '-B', __file__, 'run'], check=True,
                       env=dict(os.environ, HOME=home, XDG_CONFIG_HOME=home+'/.config', XDG_STATE_HOME=home+'/.state'))
    raise SystemExit()
sys.path.insert(0, str(SOURCE))
import appearance_policy as policy
import blur_actions as blur
import transaction as tx

path = Path.home()/tx.FILE_TARGETS['terminal-blur-config']
path.parent.mkdir(parents=True)
original = '-- User appearance settings\nhl.config({decoration={rounding=8}})\n'
path.write_text(original)
with patch.object(blur, '_command', side_effect=lambda *a: 'bool: true' if a[0]=='getoption' else '') as runtime:
    blur.apply(False)
    assert policy.read()['blur'] is False and 'no_blur = true' in path.read_text()
    runtime.assert_any_call('reload'); runtime.assert_any_call('configerrors')
    # The default opacity policy is untouched; unrelated Lua edits survive Undo.
    assert policy.read().get('opacity') is None
    with path.open('a') as out: out.write('-- unrelated edit\n')
    blur.undo()
    assert path.read_text()==original+'-- unrelated edit\n' and policy.read().get('blur') is None
    # On, repeated no-op Apply, drift repair and grouped Undo keep the baseline.
    path.write_text(original)
    blur.apply(True); baseline=path.read_bytes(); blur.apply(True)
    path.write_text(path.read_text().replace('no_blur = false', 'no_blur = true'))
    blur.apply(True, automatic=True); blur.undo()
    assert path.read_bytes()==baseline and policy.read()['blur'] is True
    blur.undo(); assert path.read_text()==original
    blur.apply(False); blur.apply(False, automatic=True)
    assert policy.read()['blur'] is False
    blur.undo()
    # A failed compositor reload must retry even when saved files are unchanged.
    with patch.object(blur, 'reload', side_effect=[RuntimeError('reload failed'), None]) as reload:
        try: blur.apply(False)
        except RuntimeError: pass
        else: raise AssertionError('Failed runtime reload reported success')
        blur.apply(False, automatic=True)
        assert reload.call_count == 2
        blur.apply(False, automatic=True)
        assert reload.call_count == 2
    blur.undo()
    for invalid in ('off',0,None):
        try: blur.apply(invalid)
        except ValueError: pass
        else: raise AssertionError('Invalid blur value accepted')
with patch.object(blur, '_command', return_value='bool: false'):
    try: blur.apply(True)
    except RuntimeError: pass
    else: raise AssertionError('Unavailable compositor blur accepted')
assert path.read_text()==original
print('Terminal blur passed: On/Off, independent policy, runtime reload/validation, unrelated edits, no-op drift and grouped Undo.')
