"""Read-only previews from real isolated palette/index/icon metadata fixtures."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-previews-') as home:
        env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=home+'/.config',
                   XDG_DATA_HOME=home+'/.local/share', XDG_DATA_DIRS=home+'/system',
                   XDG_STATE_HOME=home+'/.local/state', OMARCHY_PATH=home,
                   PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True)
    raise SystemExit()

sys.path.insert(0, str(SOURCE))
import controller
import appearance_previews as previews
from application_themes import palette

HOME = Path.home()
stock, user = HOME/'themes', HOME/'.config/omarchy/themes'
controller.THEME_DIRS = (stock, user)
first, second = HOME/'icons-first', HOME/'icons-second'
controller.ICON_DIRS = (first, second)


def put(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw)
    return path


def colors(root, name, background='#101020', accent='#aaccee'):
    return put(root/name/'colors.toml', f'background="{background}"\nforeground="#ffffff"\n'
               f'accent="{accent}"\nred="#aa0011"\ngreen="#00aa11"\nblue="{accent}"\n')


def icon_theme(root, name, inherits='', directories=('32x32/places',), extra=''):
    return put(root/name/'index.theme', '[Icon Theme]\nName='+name+'\nDirectories='+','.join(directories)
               +'\nInherits='+inherits+'\n'+extra+''.join('\n['+d+']\nSize=32\nType=Fixed\n' for d in directories))


def icon(root, theme, name, directory='32x32/places'):
    return put(root/theme/directory/(name+'.svg'),
               '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
               '<rect width="32" height="32" fill="#f00"/></svg>')


def files():
    return {str(p.relative_to(HOME)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mode)
            for p in HOME.rglob('*') if p.is_file()}


colors(stock, 'shadowed')
colors(user, 'shadowed', '#eeeeee', '#1133aa')
colors(stock, 'bad-overlay')
put(user/'bad-overlay/colors.toml', 'background = "no color"\n')
colors(stock, 'invalid-mode')
with (stock/'invalid-mode/colors.toml').open('a') as handle:
    handle.write('mode = "night"\n')
put(stock/'legacy/alacritty.toml', '[colors.primary]\nbackground="#ffffff"\nforeground="#101010"\n'
    '[colors.normal]\nblue="#2255aa"\nred="#aa0011"\n')
(stock/'absent').mkdir()
colors(stock, 'oversized')
with (stock/'oversized/colors.toml').open('a') as handle:
    handle.write('#'*(previews.MAX_METADATA_BYTES+1))

# First index wins, but images may be supplied in any same-name XDG root.
icon_theme(first, 'Selected', 'Parent,hicolor')
icon_theme(second, 'Selected', 'Wrong')
direct = icon(first, 'Selected', 'folder')
icon(second, 'Selected', 'folder')
document = icon(second, 'Selected', 'text-x-generic')
icon_theme(first, 'Parent', 'Selected', extra='Hidden=true\n')
settings = icon(first, 'Parent', 'preferences-system')
icon_theme(first, 'Wrong')
icon(first, 'Wrong', 'preferences-system')
icon_theme(first, 'hicolor')
fallback = icon(first, 'hicolor', 'folder')
icon_theme(first, 'Empty')
icon_theme(first, 'Invalid', directories=('../escape',))
icon_theme(second, 'Invalid')
icon(second, 'Invalid', 'folder')
icon_theme(first, 'CycleA', 'CycleB')
icon_theme(first, 'CycleB', 'CycleA')
cycle_icon = icon(first, 'CycleB', 'text-x-generic')
icon_theme(first, 'NoLooseFiles')
icon(first, 'NoLooseFiles', 'preferences-system', directory='unlisted')
icon_theme(first, 'Escape')
external = icon(HOME/'outside', 'Elsewhere', 'preferences-system')
link = first/'Escape/32x32/places/preferences-system.svg'
link.parent.mkdir(parents=True, exist_ok=True)
link.symlink_to(external)
icon_theme(first, 'RelativeLink')
linked = icon(first, 'RelativeLink', 'target')
(linked.parent/'text-x-generic.svg').symlink_to('target.svg')
put(first/'BadParent/index.theme', '[Icon Theme]\nName=Bad\nDirectories=32x32/places\nInherits=../../outside\n'
    '[32x32/places]\nSize=32\n')
icon_theme(first, 'Sized', directories=('16x16/apps', '32x32/apps'))
p = first/'Sized/index.theme'
p.write_text(p.read_text().replace('[16x16/apps]\nSize=32', '[16x16/apps]\nSize=16'))
icon(first, 'Sized', 'folder', '16x16/apps')
sized = icon(second, 'Sized', 'folder', '32x32/apps')
for number in range(previews.MAX_DEPTH+3):
    icon_theme(first, 'Chain'+str(number), 'Chain'+str(number+1))
icon(first, 'Chain'+str(previews.MAX_DEPTH+2), 'preferences-system')
icon_theme(first, 'TooMany', directories=tuple('32x32/part'+str(i) for i in range(previews.MAX_DIRECTORIES+1)))
icon_theme(first, 'OversizedIcon')
large = icon(first, 'OversizedIcon', 'preferences-system')
with large.open('a') as handle:
    handle.write(' ' * previews.MAX_ICON_BYTES)

before = files()
with patch('subprocess.run', side_effect=AssertionError('Preview must not run a command')), \
     patch('subprocess.check_output', side_effect=AssertionError('Preview must not run a command')), \
     patch('subprocess.Popen', side_effect=AssertionError('Preview must not run a command')):
    themes = {entry['name']: entry for entry in controller.theme_entries()}
    actual = themes['shadowed']['preview']
    effective = palette(user/'shadowed')
    assert all(actual[key] == effective[key] for key in ('background', 'foreground', 'accent', 'mode'))
    assert actual['background'] == '#eeeeee' and actual['mode'] == 'light'
    assert actual['swatches'] == ['#aa0011', '#00aa11', '#1133aa']
    assert themes['legacy']['preview']['accent'] == '#2255aa'
    assert themes['legacy']['preview']['mode'] == 'light'
    for name in ('bad-overlay', 'invalid-mode', 'absent', 'oversized'):
        assert themes[name]['preview'] is None, name
    entries = {entry['name']: entry for entry in controller.icon_entries()}
    def samples(name):
        return {item['name']: item['source'] for item in entries[name]['previewIcons']}
    assert samples('Selected') == {'folder': str(direct), 'text-x-generic': str(document),
                                   'preferences-system': str(settings)}
    assert samples('Empty') == {'folder': str(fallback)}
    assert samples('CycleA') == {'folder': str(fallback), 'text-x-generic': str(cycle_icon)}
    assert samples('Invalid') == {} and samples('BadParent') == {}
    assert 'preferences-system' not in samples('NoLooseFiles')
    assert 'preferences-system' not in samples('Escape')
    assert samples('RelativeLink')['text-x-generic'] == str(linked)
    assert samples('Sized')['folder'] == str(sized)
    assert 'preferences-system' not in samples('Chain0')
    assert samples('TooMany') == {}
    assert 'preferences-system' not in samples('OversizedIcon')
    # Resource exhaustion produces an unavailable/partial preview, not an
    # unbounded metadata walk or a replacement icon from another theme.
    with patch.object(previews, 'MAX_FILE_PROBES', 1):
        assert previews.IconPreviews((first, second)).samples('Selected') == []
assert before == files(), 'Preview lookup changed fixture files'

# Validate only the changed schema fields: the full catalog contract predates
# several existing unrelated inventory fields and is not rewritten by this UI work.
schema = json.loads((SOURCE/'catalog-entry.schema.json').read_text())
try:
    import jsonschema
except ImportError:
    print('Optional jsonschema unavailable; schema parsed, field validation skipped.')
else:
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(actual, schema['properties']['preview'])
    jsonschema.validate(None, schema['properties']['preview'])
    jsonschema.validate('/existing/unlock.png', schema['properties']['preview'])
    jsonschema.validate(entries['Selected']['previewIcons'], schema['properties']['previewIcons'])
    for value in ({**actual, 'background': 'red'}, {**actual, 'mode': 'unknown'}):
        try:
            jsonschema.validate(value, schema['properties']['preview'])
        except jsonschema.ValidationError:
            pass
        else:
            raise AssertionError('Invalid palette accepted by preview schema')

print('Appearance previews passed: effective palettes, legacy data, unavailable colors, XDG precedence, inherited files, bounded cycles, safe paths, sample sizing and no writes/commands.')
