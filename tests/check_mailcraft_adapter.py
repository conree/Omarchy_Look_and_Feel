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
# The font outgoing mail is written in is MailCraft's own setting, never sent from here.
assert 'composeFont' not in out

# A minimal palette takes its stand-ins.
small = dict(mode='light', background='#fafafa', foreground='#101020', accent='#334455')
out = json.loads(mc.appearance(small, None))
assert out['colors']['raised'] == '#fafafa' and out['colors']['muted'] == '#101020' and out['colors']['selection'] == '#334455'
assert 'red' not in out['colors'] and 'interfaceFont' not in out and 'composeFont' not in out

# A family MailCraft would refuse is left out rather than written.
for bad in ['', ' ', 'A;B', 'A"B', "A'B", 'A,B', 'x' * 65, 'A\nB', 7, None]:
    assert 'interfaceFont' not in json.loads(mc.appearance(full, bad, 11)), bad
for size in [5, 49, True, '11', None, 11]:
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
# The opacity for apps without their own setting: written when it is a percent, else left out.
assert json.loads(mc.appearance(full, 'Montserrat', 11, 60))['opacity'] == 60
for bad in [None, -1, 101, 60.5, True, '60']:
    assert 'opacity' not in json.loads(mc.appearance(full, 'Montserrat', 11, bad)), bad
assert mc.saved_opacity() is None
policy_path = Path.home() / tx.FILE_TARGETS['appearance-policy']
policy_path.parent.mkdir(parents=True, exist_ok=True)
import appearance_policy
policy_path.write_bytes(appearance_policy.update('fleaOpacity', 60))
assert mc.saved_opacity() == 60
policy_path.write_text('not json')
assert mc.saved_opacity() is None
# MailCraft's folder decides whether a Flea opacity Apply writes its file too.
assert not mc.present()
(Path.home() / '.config' / 'mailcraft').mkdir(parents=True)
assert mc.present()

# A Flea opacity change reaches MailCraft's file in a transaction of its own, so a theme Apply
# in between never jams Flea's Undo (or any later Apply); with no readable theme, or a broken
# one, Flea's change goes ahead and MailCraft's file is left alone.
from unittest.mock import patch
import flea_opacity
policy_path.unlink()
shell = Path.home() / tx.FILE_TARGETS[flea_opacity.TARGET]
shell.parent.mkdir(parents=True, exist_ok=True)
shell.write_bytes(b'[flea]\nbackground-alpha = 0.7\n')
mailcraft_file = Path.home() / tx.FILE_TARGETS[mc.TARGET]
with patch.object(flea_opacity.shutil, 'which', return_value='/usr/bin/flea'), patch.object(flea_opacity, 'pending', return_value=[]):
    assert mc.TARGET not in flea_opacity.build(40)
    for broken in [OSError('gone'), TypeError('mode=[1]')]:
        with patch.object(mc, 'current_colors', side_effect=broken):
            flea_opacity.apply(40)
        assert not mailcraft_file.exists(), broken
    with patch.object(mc, 'current_colors', return_value=full):
        flea_opacity.apply(30)
        assert json.loads(mailcraft_file.read_bytes())['opacity'] == 30
        # A theme (or font) Apply rewrites MailCraft's file; Flea's Undo still works and the
        # next Apply is not blocked.
        theme = lambda bg: tx.apply_file_targets({mc.TARGET: mc.appearance(dict(full, background=bg), 'Montserrat', None, 30)},
                                                 label='Theme test', owned_fields={mc.TARGET: {'mode', 'colors'}})
        font = lambda family: tx.apply_file_targets({mc.TARGET: mc.appearance(full, family, None, 30)},
                                                    label='Font test', owned_fields={mc.TARGET: {'interfaceFont'}})
        look = lambda: json.loads(mailcraft_file.read_bytes())
        # App opacity, then a theme, then App opacity's Undo: the theme stays, the opacity goes back.
        theme('#000000')
        flea_opacity.undo()
        assert (look()['opacity'], look()['colors']['background']) == (40, '#000000'), look()
        # A theme, then App opacity, then the theme's Undo: the opacity stays, the colours go back.
        theme('#111111')
        flea_opacity.apply(20)
        tx.rollback_latest(label='Theme test')
        assert (look()['opacity'], look()['colors']['background']) == (20, '#000000'), look()
        # A font after a theme, then the theme's Undo: the font stays.
        theme('#222222')
        font('Fira Sans')
        tx.rollback_latest(label='Theme test')
        assert (look()['interfaceFont'], look()['colors']['background']) == ({'family': 'Fira Sans'}, '#000000'), look()
        # And nothing is left jammed: every kind of Apply still goes through.
        theme('#333333'); font('Montserrat'); flea_opacity.apply(50)
        assert (look()['opacity'], look()['interfaceFont']['family'], look()['colors']['background']) == (50, 'Montserrat', '#333333'), look()
print('mailcraft adapter: ok')
