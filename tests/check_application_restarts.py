"""Restart notice lifecycle and controller delivery, entirely in a temporary HOME."""
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
import json
import os
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-restarts-') as home:
        env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=home + '/config',
                   XDG_STATE_HOME=home + '/state', XDG_DATA_HOME=home + '/data',
                   GSETTINGS_BACKEND='keyfile', PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True)
    raise SystemExit()

sys.path.insert(0, str(SOURCE))
import application_restarts as restarts
import controller
import desktop_fonts as desktop
import transaction as tx

home = Path.home()
restarts.PROC = home / 'proc'
boot = restarts.PROC / 'sys/kernel/random/boot_id'
boot.parent.mkdir(parents=True)
boot.write_text('boot-one')


def process(pid, start, name='pcmanfm', state='S'):
    path = restarts.PROC / str(pid)
    path.mkdir(exist_ok=True)
    (path / 'comm').write_text(name + '\n')
    (path / 'stat').write_text(f'{pid} ({name}) ' + ' '.join([state] + ['0'] * 18 + [str(start)]))
    return path


def put(target, content):
    path = home / tx.FILE_TARGETS[target]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


put('gtk3-settings', '[Settings]\ngtk-font-name=Old 12\ngtk-theme-name=Adwaita\n')
put('gtk3-css', 'window { color: black; }')
Gio, settings = desktop._settings()
settings.set_string('font-name', 'Old 12')
Gio.Settings.sync()
instance = process(123, 100)
process(124, 100, 'pcmanfm-qt')
process(125, 100, 'pcmanfm-helper')
assert restarts.processes() == {'boot-one:123:100'}
assert restarts.observe() == []
state = tx.transactions_path().parent / 'application-restarts.json'
assert state.stat().st_mode & 0o777 == 0o600
original = state.read_bytes()

# Rewrites/unrelated settings never count as an appearance change.
put('gtk3-settings', '[Settings]\ngtk-theme-name=Adwaita\ngtk-font-name=Old 12\nkeep=changed\n')
put('gtk3-css', 'window { color: black; }')
assert restarts.observe() == [] and state.read_bytes() == original
put('gtk4-css', 'window { color: red; }')
assert restarts.observe() == []

# A theme/font/icon change persists through no-op checks and a newly opened instance.
put('gtk3-css', 'window { color: white; }')
pending = restarts.observe()
assert len(pending) == 1 and pending[0]['app'] == 'PCManFM' and pending[0]['action'] == 'reopen'
assert restarts.observe() == pending and state.read_bytes() == original
process(126, 110)
assert restarts.observe() == pending
process(123, 120)  # Same PID, new start time: original instance was restarted.
assert restarts.observe() == []
put('gtk3-settings', '[Settings]\ngtk-font-name=New 14\ngtk-theme-name=Adwaita\n')
assert restarts.observe() == pending
put('gtk3-settings', '[Settings]\ngtk-font-name=Old 12\ngtk-theme-name=Adwaita\n')
assert restarts.observe() == []  # Undo back to the instance's baseline.
settings.set_string('icon-theme', 'ChangedIcons')
Gio.Settings.sync()
assert restarts.observe() == pending

# Failed scans/snapshots neither erase the cache nor publish an empty list.
saved = state.read_bytes()
for function in ('processes', 'appearance'):
    with patch.object(restarts, function, side_effect=PermissionError('fixture')):
        assert restarts.observe() is None
        assert 'restartApplications' not in restarts.add_to_result({'state': 'committed'})
    assert state.read_bytes() == saved
gtk_settings = home / tx.FILE_TARGETS['gtk3-settings']
original_settings = gtk_settings.read_bytes()
gtk_settings.unlink()
os.mkfifo(gtk_settings)
assert restarts.observe() is None and state.read_bytes() == saved
gtk_settings.unlink()
gtk_settings.symlink_to(home / 'unrelated')
assert restarts.observe() is None and state.read_bytes() == saved
gtk_settings.unlink()
gtk_settings.write_bytes(original_settings)
boot.write_text('boot-two')
assert restarts.observe() == []
process(123, 120, state='Z')
process(126, 110, state='X')
assert restarts.observe() == [] and json.loads(state.read_bytes()) == {}

# Controller samples before changes and adds notices to the successful response.
process(123, 200)
def apply_fonts(*args):
    put('gtk3-settings', '[Settings]\ngtk-font-name=Applied 16\n')
    return {'transaction': 'fixture', 'targetCount': 1, 'pendingApplications': []}

output = StringIO()
with patch('requirements.require'), patch.object(controller, 'recover_pending'), \
        patch('appearance_policy.recover_theme_undos'), \
        patch.object(controller, 'apply_global_fonts', side_effect=apply_fonts), redirect_stdout(output):
    assert controller.main(['apply-global-fonts', 'font:test', '16', 'font:mono', '12']) == 0
result = json.loads(output.getvalue())
assert result['transaction'] == 'fixture' and result['restartApplications'] == pending
assert result['pendingApplications'] == []

# A later reconciliation clears exited instances even with no managed policy.
process(123, 210)
output = StringIO()
with patch.object(controller, 'recover_pending'), patch('appearance_policy.recover_theme_undos'), redirect_stdout(output):
    assert controller.main(['reconcile']) == 0
assert json.loads(output.getvalue())['restartApplications'] == []
assert restarts.observe() == []
print('PCManFM restart notices passed: real isolated GTK/GSettings changes, unchanged Apply, process identity, exit, Undo, failure preservation and controller/reconciliation delivery.')
