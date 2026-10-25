"""Regression tests confined to temporary homes and mock terminal processes."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch,Mock
from contextlib import ExitStack
import os,sys,subprocess
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import transaction as tx
import app_font_actions as app
import terminal_reload as reload

old='user_pref("msgcompose.font_face", "Aileron");\nuser_pref("font.name.sans-serif.x-western", "Aileron");\nuser_pref("font.size.variable.x-western", 12);\nuser_pref("keep.other", "original");\n'
for bad in ['user_pref(\n"msgcompose.font_face", "Old");\n', 'user_pref("msgcompose.font_face", "Old"); // comment\n',old+'user_pref("msgcompose.font_face", "Again");\n']:
    try:app.mail_font_values(bad)
    except ValueError:pass
    else:raise AssertionError('ambiguous preference accepted')
# Commented preferences must stay comments; escaped active keys must retain
# their actual identity through Apply, application canonicalization and Undo.
commented = '/*\nuser_pref("msgcompose.font_face", "Inactive Family");\n*/\n'
escaped = r'user_pref("msgcompose.font_\u0066ace", "Old Family");' + '\n'
assert app.mail_font_values(commented)['msgcompose.font_face'] is None
assert app.mail_font_values(escaped)['msgcompose.font_face'] == 'Old Family'
merged = app.mail_preferences(commented + escaped, 'Avenir Next', 12)
assert commented in merged
assert app.mail_font_values(merged)['msgcompose.font_face'] == 'Avenir Next'
restored = app.merge_mail_fonts(merged, app.mail_font_values(commented + escaped))
assert commented in restored and app.mail_font_values(restored)['msgcompose.font_face'] == 'Old Family'
for bad in [escaped + 'user_pref("msgcompose.font_face", "Duplicate");\n',
            "user_pref('msgcompose.font_face', 'Old');\n",
            'user_pref ("msgcompose.font_face", "Old");\n']:
    try: app.mail_font_values(bad)
    except ValueError: pass
    else: raise AssertionError('ambiguous or unsupported preference accepted')
with TemporaryDirectory(prefix='laf-app-fonts-') as tmp,ExitStack() as stack:
    home=Path(tmp);relative='.thunderbird/test/prefs.js';path=home/relative;path.parent.mkdir(parents=True);path.write_text(old)
    stack.enter_context(patch.object(tx,'_home',return_value=home))
    stack.enter_context(patch.dict(tx.FILE_TARGETS,{'betterbird-prefs':relative}))
    stack.enter_context(patch.dict(os.environ,{'XDG_CONFIG_HOME':str(home/'.config'),'XDG_STATE_HOME':str(home/'.local/state')}))
    payload=app.mail_preferences(path.read_text(),'Avenir Next',12).encode()
    path.write_text(old+'user_pref("saved.before.lock", true);\n')
    tid=tx.apply_file_targets({'betterbird-prefs':payload},label='mail')
    assert 'saved.before.lock' in path.read_text()
    assert app.mail_font_values(path.read_text())['msgcompose.font_face']=='Avenir Next'
    # Simulate application startup/save, changing unrelated preferences.
    path.write_text(path.read_text().replace('"original"','"changed by application"')+'user_pref("after.startup", 7);\n')
    assert tx.rollback_latest(label='mail')==tid
    assert app.mail_font_values(path.read_text())==app.mail_font_values(old)
    assert 'changed by application' in path.read_text() and 'after.startup' in path.read_text()
    # Nested recovery locks must retain exclusivity until the outermost exit.
    probe='import fcntl,sys; f=open(sys.argv[1],"r+");\ntry: fcntl.lockf(f,fcntl.LOCK_EX|fcntl.LOCK_NB)\nexcept BlockingIOError: sys.exit(11)\n'
    def locked():return subprocess.run([sys.executable,'-B','-c',probe,str(path.parent/'.parentlock')]).returncode==11
    with app.lock_mail_paths([path]):
        assert locked()
        with app.lock_mail_paths([path]):assert locked()
        assert locked()
    assert not locked()
    # A running profile is skipped without changing any settings.
    (path.parent/'lock').symlink_to('localhost:+999')
    before=path.read_bytes()
    try:tx.apply_file_targets({'betterbird-prefs':payload},label='busy')
    except RuntimeError:pass
    else:raise AssertionError('running mail profile accepted')
    assert path.read_bytes()==before
    (path.parent/'lock').unlink()
    # Symlink parents refuse before creating a lock at the redirected destination.
    outside=home/'outside';outside.mkdir();(outside/'prefs.js').write_text(old)
    linked=home/'linked';linked.symlink_to(outside,target_is_directory=True)
    try:
        with app.lock_mail_paths([linked/'prefs.js']):pass
    except tx.TransactionError:pass
    else:raise AssertionError('symlink parent accepted')
    assert not (outside/'.parentlock').exists()

with patch.object(reload.subprocess,'run',return_value=Mock(returncode=0)) as run:
    result=reload.reload_terminals({'ghostty-config','kitty-config'})
    assert result['requested']==['ghostty','kitty']
    for call in run.call_args_list:
        assert '--require-handler' in call.args[0] and '--euid' in call.args[0] and '--exact' in call.args[0]
with patch.object(reload.subprocess,'run',side_effect=[Mock(returncode=1),Mock(returncode=0)]):
    assert reload.reload_terminals({'ghostty-config'})['failed']==['ghostty']
with patch.object(reload.subprocess,'run',side_effect=OSError('failure')):
    assert reload.reload_terminals({'ghostty-config'})['failed']==['ghostty']
legacy='''/* Look & Feel font profile: preserve theme styling while sharing font roles. */
body {font-family: "Old", sans-serif !important;}
#write, #write * {font-family: "Old Mono", monospace !important;}
#write code,
#write .CodeMirror * {font-family: "Old Mono", monospace !important;}
.keep-custom { color: red; }
'''
css=app.typora_css(legacy,'Avenir Next',12,'Comic Code Ligatures',12)
assert '#write *' not in css and '.keep-custom' in css
assert app.typora_css(css,'Avenir Next',12,'Comic Code Ligatures',12)==css
assert '#typora-source' in css and '--monospace:' in css
print('Application tests passed: mail locking/stale payload/Undo merge/path refusal, strict prefs parsing, safe reload selection, Typora preservation/idempotence.')
