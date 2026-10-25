"""Native Lua and PTY regressions, with isolated HOME and no live terminal edits."""
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import json
from unittest.mock import patch

if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-terminal-test-') as root:
        subprocess.run([sys.executable, '-B', __file__, 'run'], check=True,
                       env=dict(os.environ, HOME=root, XDG_CONFIG_HOME=root+'/.config', XDG_STATE_HOME=root+'/.state', PYTHONDONTWRITEBYTECODE='1'))
    raise SystemExit()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wezterm_blocks as w
import transaction as tx
import managed_preferences as prefs
import application_themes as themes

original = '''local wezterm = require 'wezterm'
local config = wezterm.config_builder()
config.keys = {{ key = 'a', action = function() return 'return config' end }}
config.font = wezterm.font_with_fallback({'Old', 'Fallback'})
config.font_size = 9
config.colors = { foreground = '#000000', background = '#000000' }
config.color_scheme = 'Old Scheme'
return config
'''
palette = dict(background='#fafafa', foreground='#101020', selection='#002233', selection_foreground='#ffffff', muted='#555555', accent='#334455')
new = w.theme(w.fonts(original, 'Test Sans', 12), palette)
assert w.decode(new)['body'] == original
assert w.theme(new,palette) == new and w.fonts(new,'Test Sans',12) == new
# Evaluate only this synthetic configuration in real Lua with a small WezTerm API stub.
script = Path.home()/'case.lua'
script.write_text('''package.preload.wezterm = function() return { config_builder = function() return {} end, font = function(name) return name end, font_with_fallback = function(names) return names[1] end } end
local c = (function()
''' + new + '''end)()
assert(c.font == 'Test Sans' and c.font_size == 12)
assert(c.colors.background == '#fafafa' and c.colors.foreground == '#101020')
assert(c.color_scheme == nil and c.keys[1].key == 'a')
''')
subprocess.run(['lua',str(script)],check=True)
# Real managed blocks can never be moved out of a Lua string/comment/function.
for bad in (
    "local config = {}\nreturn { config }\n",
    "local config = {}\nif true then return config end\n",
    "local config = {}\nreturn config\nprint('later')\n",
    "local config = {}\nlocal s = [[-- Look and Feel fonts BEGIN\nprint('oops')\n-- Look and Feel fonts END\n]]\nreturn config\n",
    "local config = {}\n--[[\n-- Look and Feel fonts BEGIN\nprint('oops')\n-- Look and Feel fonts END\n]]\nreturn config\n",
    "local config = {}\nlocal f = function()\n-- Look and Feel fonts BEGIN\nprint('oops')\n-- Look and Feel fonts END\nend\nreturn config\n",
):
    try: w.theme(bad,palette)
    except ValueError: pass
    else: raise AssertionError('Unsafe Lua accepted: '+bad)
# Shared file ownership survives unrelated edits and either Undo order.
path = Path.home()/tx.FILE_TARGETS['wezterm-config']
path.parent.mkdir(parents=True)
for initially_present in (True, False):
    path.unlink(missing_ok=True)
    if initially_present: path.write_text(original)
    before = path.read_text() if path.exists() else ''
    parent=tx.apply_file_targets({'wezterm-config': w.theme(before,palette).encode()},label='terminal-theme', owned_fields={'wezterm-config':{'theme'}})
    tx.apply_file_targets({'wezterm-config':w.fonts(path.read_text(),'Test Sans',12).encode()},label='terminal-font',owned_fields={'wezterm-config':{'fonts'}})
    data=w.decode(path.read_text()); data['body']=data['body'].replace('\nreturn config\n','\nconfig.scrollback_lines = 3210\nreturn config\n'); path.write_text(w.encode(data))
    # Repair a managed field; this must not acquire ownership of unrelated Lua.
    data=w.decode(path.read_text()); data['theme']=data['theme'].replace('#fafafa','#eeeeee'); path.write_text(w.encode(data))
    tx.apply_file_targets({'wezterm-config':w.theme(path.read_text(),palette).encode()},label='auto-terminal',parent_transaction=parent,owned_fields={'wezterm-config':{'theme'}})
    tx.rollback_latest(label='terminal-theme')
    data=w.decode(path.read_text())
    assert data['theme'] is None and 'Test Sans' in data['fonts'] and '3210' in data['body']
    tx.rollback_latest(label='terminal-font')
    data=w.decode(path.read_text())
    assert data['fonts'] is None and data['theme'] is None and '3210' in data['body']

# Real PTY transport. Process discovery is mocked to this test process only.
import pty, select
import terminal_reload
master, slave = pty.openpty()
try:
    tty=os.ttyname(slave)
    answer=subprocess.CompletedProcess([],0,str(os.getpid())+'\n','')
    with patch.object(terminal_reload.subprocess,'run',return_value=answer) as calls, patch.object(terminal_reload.os,'readlink',return_value=tty):
        result=terminal_reload.recolor_foot(palette)
    assert result['requested'] and not result['failed']
    assert all('--euid' in c.args[0] for c in calls.call_args_list)
    assert select.select([master],[],[],1)[0]
    actual=os.read(master,8192)
    assert b'\x1b]10;#101020\x07' in actual and b'\x1b]11;#fafafa\x07' in actual
    assert b'\x1b]4;15;' in actual
finally:
    os.close(master); os.close(slave)
print('Terminal themes passed: native Lua, literal-injection refusal, independent Undo and drift, preserved user Lua, native PTY color transport.')
