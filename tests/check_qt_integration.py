"""Isolated session integration ownership and truthful application notices."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch
SOURCE = Path(__file__).resolve().parents[1]
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-qt-session-') as root:
        env = dict(os.environ, HOME=root, XDG_CONFIG_HOME=root+'/config', XDG_STATE_HOME=root+'/state', XDG_DATA_HOME=root+'/data', QT_QPA_PLATFORMTHEME='gtk3', HYPRLAND_INSTANCE_SIGNATURE='test-session', PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True)
    raise SystemExit()
sys.path.insert(0, str(SOURCE))
import application_themes as themes
import qt_integration as qt
import transaction as tx
import managed_preferences as prefs

def put(key, raw):
    path = Path.home()/tx.FILE_TARGETS[key]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path

base='-- untouched\nrequire("default.hypr.omarchy")\nlocal user = { a = "unchanged" }'
p=put('hypr-qt-integration',base.encode())
plugins={5:{'qt5ct','qt6ct'},6:{'qt6ct','qt5ct'}}
with patch.object(qt,'plugins',return_value=plugins):
    plan=themes.Plan();assert qt.prepare(plan,automatic=True) is None
    assert not plan.targets and plan.pending[0]['action']=='apply-integration'
    plan=themes.Plan();assert qt.prepare(plan,automatic=False)=='qt6ct'
    assert plan.pending[0]['action']=='login'
    original=p.read_bytes()
    tx.apply_file_targets(plan.targets,label='qt-session')
    assert p.read_text().startswith(base) and qt.decode(p.read_text())['integration']['selector']=='qt6ct'
    plan2=themes.Plan();qt.prepare(plan2,automatic=True)
    assert plan2.targets==plan.targets and plan2.pending[0]['action']=='login'
    with patch.dict(os.environ,QT_QPA_PLATFORMTHEME='qt6ct'):
        assert qt.active(5) and qt.active(6)
        stable=themes.Plan();qt.prepare(stable,automatic=True);assert stable.pending[0]['action']=='login'
        with patch.dict(os.environ,HYPRLAND_INSTANCE_SIGNATURE='new-session'):
            stable=themes.Plan();qt.prepare(stable,automatic=True);assert not stable.pending
    # An unrelated edit must survive removal of the managed selector.
    p.write_text(p.read_text().replace('unchanged','new user edit'))
    tx.rollback_latest(label='qt-session')
    assert p.read_bytes()==original.replace(b'unchanged',b'new user edit')
    # Changed owned block is a conflict, not a reason to overwrite it.
    tx.apply_file_targets(plan.targets,label='qt-conflict')
    p.write_text(p.read_text().replace('"qt6ct"','"qt5ct"'))
    try:tx.rollback_latest(label='qt-conflict')
    except tx.TransactionError:pass
    else:raise AssertionError('changed owned selector overwritten')

with patch.object(qt,'plugins',return_value={5:{'qt5ct'}}):
    unavailable=themes.Plan();assert qt.prepare(unavailable,automatic=False) is None
    assert not unavailable.targets and unavailable.pending[0]['action']=='integration-unavailable'

# Malformed/literal markers, top-level returns, and shadowed APIs cannot receive code.
for raw in (base+'\nlocal hl', base+'\nlocal x, hl', base+'\nlocal hl <const> = nil', base+'\nif true then return end', 'local require = function(_) end\n'+base, 'local hl, other = {}, {}\n'+base, 'return {}\n', 'local hl = {}\n'+base, base+'\nreturn nil\n', 'local s=[['+qt.encode({'body':base,'integration':{'selector':'qt6ct','session':'test-session'}})+']]', 'if true then\n'+base):
    try:qt.checked_config(raw)
    except ValueError:pass
    else:raise AssertionError('unsafe Lua accepted: '+raw)

colors={'mode':'dark','background':'#111111','foreground':'#eeeeee','accent':'#7744ee','selection':'#7744ee','muted':'#999999','lighter_background':'#222222','selection_foreground':'#ffffff'}
put('qt5ct-settings',b'[Appearance]\n')
put('qt6ct-settings',b'[Appearance]\n')
put('onlyoffice-settings',b'[General]\ntitlebar=system\n')
launcher=b'[Desktop Entry]\nExec=onlyoffice-desktopeditors --system-title-bar %U\n'
put('onlyoffice-launcher',launcher)
with patch.object(qt,'plugins',return_value={}), patch.object(qt,'gtk_palette_supported',side_effect=lambda v: v == 6), patch.object(prefs,'assert_closed',side_effect=RuntimeError('running')):
    plan=themes.build(colors,colors,'dark','dark',{'onlyoffice-desktopeditors.desktop'})
    assert not any(r['app'] in {'OnlyOffice','Qt 6'} for r in plan.pending),plan.pending
    assert any(r['app']=='Qt 5' for r in plan.pending)
    put('onlyoffice-launcher',launcher.replace(b' --system-title-bar',b''))
    plan=themes.build(colors,colors,'dark','dark',{'onlyoffice-desktopeditors.desktop'})
    assert any(r['app']=='OnlyOffice' and r['action']=='reopen' for r in plan.pending)
with patch.object(qt,'plugins',return_value={}), patch.object(prefs,'assert_closed'):
    plan=themes.build(colors,colors,'dark','dark',{'onlyoffice-desktopeditors.desktop'})
    assert not any(r['app']=='OnlyOffice' for r in plan.pending)
print('Qt session tests passed: shared aliases, explicit opt-in, login boundary, byte-preserving Undo, unrelated edits, conflict refusal, unsafe Lua refusal, GTK/qtct notices, and OnlyOffice reload notices.')
