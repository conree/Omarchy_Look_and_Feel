"""Screensaver settings, Omarchy toggle hold/release and themed ttfx options.

Runs in an isolated HOME. Every effect's generated options are also checked
against the installed ttfx when it is available.
"""
from pathlib import Path
import os, shutil, subprocess, sys, tempfile

SOURCE = Path(__file__).resolve().parents[1]
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-screensaver-') as home:
        subprocess.run([sys.executable, '-B', __file__, 'run'], check=True,
                       env=dict(os.environ, HOME=home, XDG_CONFIG_HOME=home + '/.config', XDG_STATE_HOME=home + '/.state'))
    raise SystemExit()
sys.path.insert(0, str(SOURCE))
import screensaver as ss

home = Path.home()
theme = home / '.local/state/omarchy/current/theme'
theme.mkdir(parents=True)
(theme / 'colors.toml').write_text(
    'accent = "#9580FF"\nforeground = "#F8F8F2"\nbackground = "#0B0D0F"\n'
    'color1 = "#FF9580"\ncolor2 = "#8AFF80"\ncolor5 = "#FF80BF"\ncolor8 = "#364049"\n')

# Defaults without a settings file; Van Helsing matrix matches the owner's
# hand-picked colours exactly.
assert ss.load() == {'enabled': False, 'idleSeconds': 600, 'effect': 'matrix', 'holdsOmarchyToggle': False}
assert ss.ttfx_args('matrix') == ['matrix', '--rain-color-gradient', '8aff80', '364049', '--highlight-color', 'ff80bf',
                                  '--final-gradient-stops', '8aff80', '9580ff', 'ff80bf']

# Turning on holds Omarchy's screensaver-off toggle; turning off releases it.
flag = ss.toggle_path()
ss.save(True, 300, 'random')
assert flag.exists() and ss.load()['holdsOmarchyToggle'] and ss.load()['effect'] == 'random'
ss.save(True, 600, 'beams')  # changing settings while on keeps the hold
assert flag.exists() and ss.load()['holdsOmarchyToggle']
ss.save(False, 600, 'beams')
assert not flag.exists() and not ss.load()['holdsOmarchyToggle']

# A toggle the user set themselves is never released by the plugin.
flag.touch()
ss.save(True, 600, 'matrix')
assert not ss.load()['holdsOmarchyToggle']
ss.save(False, 600, 'matrix')
assert flag.exists()
flag.unlink()

for bad in ((True, 59, 'matrix'), (True, 600, 'nope'), (True, 600, '--bogus')):
    try:
        ss.save(*bad)
    except ValueError:
        pass
    else:
        raise AssertionError(bad)
assert (ss.settings_path().stat().st_mode & 0o777) == 0o600

# An unrecognised stored value (hand edit, other version) never blocks saving,
# and the recorded hold is still released by Off.
ss.save(True, 600, 'matrix')
assert flag.exists()
ss.settings_path().write_text('{"enabled": true, "idleSeconds": 700, "effect": "future", "holdsOmarchyToggle": true}')
ss.save(False, 600, 'matrix')
assert not flag.exists() and ss.load()['enabled'] is False

# Near-black theme colours (light themes) are replaced so they stay visible on black.
(theme / 'colors.toml').write_text('accent = "#000000"\nforeground = "#202020"\nbackground = "#ffffff"\ncolor2 = "#050505"\n')
assert set(ss.palette().values()) <= {'ffffff', '000000'} and ss.palette()['primary'] == 'ffffff'

ttfx = shutil.which('ttfx')
if ttfx:
    (theme / 'colors.toml').write_text('accent = "#9580FF"\nforeground = "#F8F8F2"\nbackground = "#0B0D0F"\n')
    sample = home / 'sample.txt'
    sample.write_text('Omarchy\n')
    for effect in ss.EFFECTS:
        try:
            result = subprocess.run([ttfx, '-i', str(sample), *ss.ttfx_args(effect)], stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=1)
            assert result.returncode == 0, (effect, result.stderr[:200])
        except subprocess.TimeoutExpired:
            pass  # accepted and still animating
print(f'Screensaver passed: settings, toggle hold/release, validation, palette, {len(ss.EFFECTS)} effects'
      + (' accepted by ttfx' if ttfx else ' (ttfx not installed)'))
