"""Real Gio settings and file transactions, entirely in an isolated home."""
from pathlib import Path
import os, sys, tempfile, subprocess, json
from unittest.mock import patch
SOURCE = Path(__file__).resolve().parents[1]
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-icons-') as home:
        env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=home+'/.config', XDG_STATE_HOME=home+'/.local/state', XDG_DATA_HOME=home+'/.local/share', GSETTINGS_BACKEND='keyfile', PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True)
    raise SystemExit()
sys.path.insert(0, str(SOURCE))
import controller, icon_actions as icons, transaction as tx, desktop_fonts as desktop, appearance_policy as policy
from managed_preferences import decode
home=Path.home(); root=home/'icons'
for name in ('TestIcons', 'Broken,Icons'):
    (root/name).mkdir(parents=True)
    (root/name/'index.theme').write_text('[Icon Theme]\nName='+name+'\nInherits=hicolor\nDirectories=16x16/apps\n[16x16/apps]\nSize=16\n')
controller.ICON_DIRS=(root,)
identity=controller.stable_id('icon','TestIcons')
Gio, settings=desktop._settings(); original=desktop._user_value(settings,'icon-theme')
def path(key): return home/tx.FILE_TARGETS[key]
for key in ('gtk3-settings','gtk4-settings'):
    path(key).parent.mkdir(parents=True)
    path(key).write_text('[Settings]\ngtk-font-name=Old 10\ncustom=retain\n')
# Include both real INI codecs without depending on host Qt detection.
with patch('qt_integration.plugins', return_value={5:{'qt5ct'},6:{'qt5ct'}}):
    result=icons.apply(identity)
    assert result['state']=='committed'
    assert settings.get_string('icon-theme')=='TestIcons'
    assert policy.read()['icons']==identity
    for key in ('gtk3-settings','gtk4-settings'):
        assert decode(key,path(key).read_bytes())['Settings/gtk-icon-theme-name']=='TestIcons'
    for key in ('qt5ct-settings','qt6ct-settings'):
        assert decode(key,path(key).read_bytes())['Appearance/icon_theme']=='TestIcons'
    # Later font choice survives both an automatic icon repair and icon Undo.
    tx.apply_file_targets({'gtk3-settings':path('gtk3-settings').read_bytes().replace(b'Old 10',b'New 14')},label='later-font')
    settings.set_string('icon-theme','Independent'); Gio.Settings.sync()
    child=icons.apply(identity,automatic=True)['transaction']
    assert child and icons.apply(identity,automatic=True)['state']=='already-current'
    icons.undo()
assert desktop._user_value(settings,'icon-theme')==original
assert decode('gtk3-settings',path('gtk3-settings').read_bytes())['Settings/gtk-font-name']=='New 14'
assert 'custom=retain' in path('gtk3-settings').read_text()
assert 'Settings/gtk-icon-theme-name' not in decode('gtk3-settings',path('gtk3-settings').read_bytes())
assert not path('qt5ct-settings').exists() and not path('qt6ct-settings').exists()
assert policy.read().get('icons') is None
assert json.loads((tx.transactions_path()/child/'transaction.json').read_text())['state']=='rolled_back'
# Missing or ambiguous installed names fail before writing.
for name in ('Missing','Broken,Icons'):
    try: icons.apply(controller.stable_id('icon',name))
    except ValueError: pass
    else: raise AssertionError('unsupported icon accepted')
assert not icons.supported_name(' Icon') and not icons.supported_name('Icon ')
assert controller.catalog_entry_eligible(next(e for e in controller.icon_entries() if e['id']==identity))
# Unsafe target refusal is atomic.
path('gtk4-settings').unlink(); outside=home/'untouched'; outside.write_text('sentinel')
path('gtk4-settings').symlink_to(outside)
before=path('gtk3-settings').read_bytes()
try: icons.apply(identity)
except tx.TransactionError: pass
else: raise AssertionError('symlink destination accepted')
assert outside.read_text()=='sentinel' and path('gtk3-settings').read_bytes()==before
assert desktop._user_value(settings,'icon-theme')==original
print('Icon Apply/Undo, real GSettings, grouped drift repair, independent font preservation, portable identifiers and atomic refusal passed.')
