"""Real Gio keyfile-backend tests; every setting and file stays in a temp home."""
from pathlib import Path
import os,sys,tempfile,subprocess,json
from unittest.mock import patch
sys.dont_write_bytecode=True
source=Path(__file__).resolve().parents[1]
if len(sys.argv)==1:
    with tempfile.TemporaryDirectory(prefix='laf-desktop-font-test-') as tmp:
        env=dict(os.environ,HOME=tmp,XDG_CONFIG_HOME=tmp+'/.config',XDG_STATE_HOME=tmp+'/.local/state',GSETTINGS_BACKEND='keyfile',PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable,'-B',__file__,'run'],env=env,check=True)
    raise SystemExit()
sys.path.insert(0,str(source))
import desktop_fonts as desktop
import transaction as tx
Gio,settings=desktop._settings()
values={'font-name':'Avenir Next 12','document-font-name':'Avenir Next 12','monospace-font-name':'Comic Code Ligatures 12'}
settings.set_string('font-name','Aileron 14');Gio.Settings.sync()
original={key:desktop._user_value(settings,key) for key in desktop.KEYS}
target=Path.home()/tx.FILE_TARGETS['global-font-selection']
label='test desktop fonts'
id=tx.apply_file_targets({'global-font-selection':b'new'},label=label,desktop_font_values=values)
assert all(settings.get_string(k)==v for k,v in values.items())
assert tx.rollback_latest(label=label)==id
assert {k:desktop._user_value(settings,k) for k in desktop.KEYS}==original
assert not target.exists()
# Simulate failure immediately after the real settings write; all files/settings restore.
real_apply=desktop.apply
def failing_apply(rows):
    real_apply(rows)
    raise RuntimeError('injected post-settings failure')
with patch.object(desktop,'apply',side_effect=failing_apply):
    try:tx.apply_file_targets({'global-font-selection':b'new'},label=label,desktop_font_values=values)
    except tx.TransactionError as e: assert 'rolled back' in str(e)
    else:raise AssertionError('failure accepted')
assert {k:desktop._user_value(settings,k) for k in desktop.KEYS}==original
assert not target.exists()
# Undo preserves independent changes and marks recovery required.
id=tx.apply_file_targets({'global-font-selection':b'new'},label=label,desktop_font_values=values)
settings.set_string('font-name','Independent Font 18');Gio.Settings.sync()
try:tx.rollback_latest(label=label)
except tx.TransactionError as e:assert 'recovery' in str(e)
else:raise AssertionError('drift overwritten')
assert settings.get_string('font-name')=='Independent Font 18'
assert json.loads((tx.transactions_path()/id/'transaction.json').read_text())['state']=='recovery_required'
settings.set_string('font-name',values['font-name']);Gio.Settings.sync()
assert id in tx.recover_pending()
assert {k:desktop._user_value(settings,k) for k in desktop.KEYS}==original
# An abruptly terminated writer must leave a recoverable journal.
child='''import sys,os
sys.path.insert(0,sys.argv[1])
import transaction as tx
real=tx._write_journal
def crash(path,journal):
 if journal['state']=='committed':os._exit(23)
 return real(path,journal)
tx._write_journal=crash
tx.apply_file_targets({'global-font-selection':b'crashed'},label='crash',desktop_font_values={'font-name':'Avenir Next 12','document-font-name':'Avenir Next 12','monospace-font-name':'Comic Code Ligatures 12'})
'''
r=subprocess.run([sys.executable,'-B','-c',child,str(source)],env=os.environ)
assert r.returncode==23
# Fresh processes read keyfile changes consistently (no stale Gio instance cache).
recovery='''import sys,json
sys.path.insert(0,sys.argv[1])
import transaction as tx,desktop_fonts as d
assert tx.recover_pending()
_,s=d._settings()
assert {k:d._user_value(s,k) for k in d.KEYS}==json.loads(sys.argv[2])
'''
subprocess.run([sys.executable,'-B','-c',recovery,str(source),json.dumps(original)],env=os.environ,check=True)
print('Real isolated Gio Apply/Undo, unset restoration, write-failure rollback, drift preservation and abrupt-exit recovery passed.')
