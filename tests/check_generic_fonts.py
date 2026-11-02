"""Real Fontconfig ordering with the installed rules and journaled preferences."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-generic-fonts-') as home:
        env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=home + '/config',
                   XDG_STATE_HOME=home + '/state', XDG_DATA_HOME=home + '/data',
                   XDG_CACHE_HOME=home + '/cache', PYTHONDONTWRITEBYTECODE='1')
        for key in ('FONTCONFIG_FILE', 'FONTCONFIG_PATH', 'FONTCONFIG_SYSROOT'):
            env.pop(key, None)
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True)
    raise SystemExit()

sys.path.insert(0, str(SOURCE))
import generic_fonts as adapter
import transaction as tx

home = Path.home()
rules = home / 'system-rules'
rules.mkdir()
for source in Path('/etc/fonts/conf.d').iterdir():
    if source.name != adapter.LOADER.name:
        (rules / source.name).symlink_to(source)
loader = rules / adapter.LOADER.name
loader.write_bytes(adapter.LOADER_SOURCE.read_bytes())
config = home / 'native.conf'
text, count = re.subn(r'(<include\b[^>]*>)\s*conf\.d\s*(</include>)',
                     lambda m: m[1] + str(rules) + m[2], Path('/etc/fonts/fonts.conf').read_text())
assert count == 1
config.write_text(text)
os.environ['FONTCONFIG_FILE'] = str(config)


def match(family):
    result = subprocess.run(['fc-match', '-f', '%{family[0]}', family],
                            capture_output=True, text=True, check=True)
    assert not result.stderr.strip(), result.stderr
    return result.stdout


available = set(subprocess.check_output(['fc-list', '-f', '%{family[0]}\n'], text=True).splitlines())
sans = [f for f in ('DejaVu Sans', 'Liberation Sans', 'Adwaita Sans') if f in available]
mono = [f for f in ('DejaVu Sans Mono', 'Liberation Mono', 'JetBrainsMono Nerd Font') if f in available]
assert len(sans) >= 2 and len(mono) >= 2
requests = ['sans-serif', 'monospace', 'serif', 'sans-serif,monospace', 'monospace,sans-serif']
explicit = sans + mono
explicit += [f + ',' + generic for f in sans + mono for generic in ('monospace', 'sans-serif')]
baseline = {f: match(f) for f in requests + explicit}
target = home / tx.FILE_TARGETS['fontconfig-generics']
assert not target.exists()  # Missing user file is harmless, with no warnings.
with patch.object(adapter, 'LOADER', loader):
    first = tx.apply_file_targets({'fontconfig-generics': adapter.build(sans[0], mono[0])}, label='Generic test')
    assert adapter.status(sans[0], mono[0]) is None
    assert match('sans-serif') == sans[0] and match('monospace') == mono[0]
    assert match('sans-serif,monospace') == sans[0]
    assert match('monospace,sans-serif') == mono[0]
    assert match('serif') == baseline['serif']
    assert all(match(f) == baseline[f] for f in explicit)
    saved = target.read_bytes()
    tx.apply_file_targets({'fontconfig-generics': adapter.build(sans[1], mono[1])}, label='Generic test')
    assert adapter.status(sans[1], mono[1]) is None
    assert match('sans-serif') == sans[1] and match('monospace') == mono[1]
    tx.rollback_latest(label='Generic test')
    assert target.read_bytes() == saved and adapter.status(sans[0], mono[0]) is None
    tx.rollback_latest(label='Generic test')
    assert not target.exists()
    assert all(match(f) == before for f, before in baseline.items())
    assert adapter.status(sans[0], mono[0])['action'] == 'review'
    loader.unlink()
    assert adapter.status(sans[0], mono[0])['action'] == 'setup'

assert b'A &amp; B &lt;C&gt;' in adapter.build('A & B <C>', mono[0])
for invalid in ('', 'monospace', 'sans-serif', 'bad\nfont', 'bad\x00font', 'x' * 301):
    try:
        adapter.build(invalid, mono[0])
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid family accepted')
print('Generic fonts passed: full installed rule ordering, both generic priorities, explicit fonts, serif, '
      'changed selections, transaction Undo, missing loader/preferences, and conflicting effective match.')
