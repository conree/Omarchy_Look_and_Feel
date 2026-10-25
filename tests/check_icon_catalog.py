"""Installed icon metadata discovery/refusal, without desktop writes or rendering."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-icon-catalog-') as home:
        env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=home+'/.config',
                   XDG_DATA_HOME=home+'/.local/share', XDG_STATE_HOME=home+'/.local/state',
                   PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True)
    raise SystemExit()

sys.path.insert(0, str(SOURCE))
import controller
import icon_actions as icons

first, second = Path.home()/'first', Path.home()/'second'
controller.ICON_DIRS = (first, second)
valid = '[Icon Theme]\nName=Display name\nInherits=hicolor\nDirectories=16x16/apps,\n[16x16/apps]\nSize=16\nType=Fixed\n'

def write(base, name, text):
    directory = base/name
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'index.theme').write_text(text)

write(first, 'Valid', valid)
write(first, 'HiddenFallback', valid.replace('Inherits=hicolor', 'Hidden=true'))
write(first, 'CursorOnly', '[Icon Theme]\nName=Cursor theme\nInherits=Adwaita\n')
write(first, 'MissingSection', valid.split('[16x16/apps]')[0])
write(first, 'InvalidSize', valid.replace('Size=16', 'Size=zero'))
write(first, 'UnsafeDirectory', valid.replace('16x16/apps', '../apps'))
write(first, 'Unsupported Name', valid)
write(first, 'Shadowed', '[Icon Theme]\nName=Cursor override\n')
write(second, 'Shadowed', valid)
write(second, 'LaterOnly', valid)

entries = controller.icon_entries()
available = {entry['name'] for entry in entries if controller.catalog_entry_eligible(entry)}
assert available == {'Valid', 'LaterOnly'}, available
for entry in entries:
    if entry['name'] in available:
        assert icons.resolve(entry['id']) == entry['name']
    else:
        try:
            icons.resolve(entry['id'])
        except ValueError:
            pass
        else:
            raise AssertionError('Unavailable catalog entry accepted by Apply: '+entry['name'])

fallback = icons.metadata('HiddenFallback', [first/'HiddenFallback'])
assert fallback == {'name': 'Display name', 'hidden': True}
assert not icons.supported_name('Theme With Spaces')
assert icons.supported_name('Theme_1.2+dark')
assert not icons.supported_name(None)
print('Icon catalog passed: valid metadata, hidden fallback recognition, cursor-only refusal, directory metadata, identifiers, and first-index precedence.')
