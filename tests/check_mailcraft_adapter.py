"""MailCraft appearance-file adapter, with an isolated HOME and no live edits."""
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import json

if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-mailcraft-test-') as root:
        subprocess.run([sys.executable, '-B', __file__, 'run'], check=True,
                       env=dict(os.environ, HOME=root, XDG_CONFIG_HOME=root + '/.config', XDG_STATE_HOME=root + '/.state', PYTHONDONTWRITEBYTECODE='1'))
    raise SystemExit()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mailcraft_adapter as mc
import transaction as tx

assert tx.FILE_TARGETS[mc.TARGET] == '.config/mailcraft/appearance.json', tx.FILE_TARGETS[mc.TARGET]
assert mc.installed({mc.DESKTOP_ID}) and not mc.installed({'eu.betterbird.Betterbird.desktop'})

full = dict(mode='dark', background='#17191B', lighter_background='#2E3236', foreground='#D2D0CB', muted='#9EA4AC',
            accent='#B3A6BC', selection_background='#2E3236', red='#FF7D6C', green='#9BAF84', yellow='#F2C861',
            orange='#C9A273', blue='#8CA3B5', magenta='#C28FA3')
out = json.loads(mc.appearance(full, 'Montserrat', 11))
assert out['mode'] == 'dark'
assert out['colors'] == {'background': '#17191b', 'raised': '#2e3236', 'text': '#d2d0cb', 'muted': '#9ea4ac',
                         'accent': '#b3a6bc', 'selection': '#2e3236', 'red': '#ff7d6c', 'green': '#9baf84',
                         'yellow': '#f2c861', 'orange': '#c9a273', 'blue': '#8ca3b5', 'purple': '#c28fa3'}, out['colors']
assert out['interfaceFont'] == {'family': 'Montserrat'}
assert out['composeFont'] == {'family': 'Montserrat', 'sizePt': 11}

# A minimal palette takes its stand-ins.
small = dict(mode='light', background='#fafafa', foreground='#101020', accent='#334455')
out = json.loads(mc.appearance(small, None))
assert out['colors']['raised'] == '#fafafa' and out['colors']['muted'] == '#101020' and out['colors']['selection'] == '#334455'
assert 'red' not in out['colors'] and 'interfaceFont' not in out and 'composeFont' not in out

# A family MailCraft would refuse is left out rather than written.
for bad in ['', ' ', 'A;B', 'A"B', "A'B", 'A,B', 'x' * 65, 'A\nB', 7, None]:
    assert 'interfaceFont' not in json.loads(mc.appearance(full, bad, 11)), bad
# An out-of-range size keeps the interface font and drops the composition one.
for size in [5, 49, True, '11', None]:
    out = json.loads(mc.appearance(full, 'Montserrat', size))
    assert out['interfaceFont'] == {'family': 'Montserrat'} and 'composeFont' not in out, size

# The saved font selection is read when present and valid.
assert mc.saved_font() == (None, None)
selection = Path.home() / tx.FILE_TARGETS['global-font-selection']
selection.parent.mkdir(parents=True, exist_ok=True)
selection.write_text(json.dumps({'systemFontFamily': 'Montserrat', 'systemFontSizePt': 11}))
assert mc.saved_font() == ('Montserrat', 11)
selection.write_text('not json')
assert mc.saved_font() == (None, None)
print('mailcraft adapter: ok')
