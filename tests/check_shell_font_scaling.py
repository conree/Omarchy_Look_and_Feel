"""Scaled shell typography for themes that pin every [font] token."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os
import sys
import tomllib

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import transaction as tx
import global_font_actions as fonts
import shell_preferences


def fixture(stack, home):
    home = Path(home)
    stack.enter_context(patch.object(tx, '_home', return_value=home))
    stack.enter_context(patch.object(fonts, 'HOME', home))
    stack.enter_context(patch.object(fonts, 'CONFIG', home / '.config'))
    stack.enter_context(patch.dict(os.environ, {
        'XDG_CONFIG_HOME': str(home / '.config'),
        'XDG_STATE_HOME': str(home / '.local/state'),
        'QT_QPA_PLATFORMTHEME': '',
    }))
    return home


with TemporaryDirectory(prefix='laf-shell-font-scale-') as tmp, ExitStack() as stack:
    home = fixture(stack, tmp)
    theme = home / '.local/state/omarchy/current/theme'
    theme.mkdir(parents=True)
    (theme / 'shell.toml').write_text(
        '[font]\nbase-size = 12\ncaption = 10\nbody-small = 11\nbody = 12\n'
        'subtitle = 13\ntitle = 15\nheading = 18\ndisplay = 26\n'
        'display-large = 31\nicon-small = 11\nicon = 14\nicon-large = 19\n'
    )
    targets, _ = fonts.build_global_font_targets('Montserrat', 12, 'Comic Code', 12, set())
    values = tomllib.loads(targets['omarchy-shell-style'].decode())['font']
    assert values['base-size'] == 16
    assert values['caption'] == 13 and values['body-small'] == 15
    assert values['body'] == 16 and values['subtitle'] == 17
    assert values['title'] == 20 and values['heading'] == 24
    assert values['display'] == 35 and values['display-large'] == 41
    assert values['icon-small'] == 15 and values['icon'] == 19 and values['icon-large'] == 25

    # Rebuilding from the same theme must not compound the scale.
    again, _ = fonts.build_global_font_targets('Montserrat', 12, 'Comic Code', 12, set())
    assert again['omarchy-shell-style'] == targets['omarchy-shell-style']

    user = home / '.config/omarchy/shell.toml'
    user.parent.mkdir(parents=True)
    original = b'[font]\nbase-size = 13\n[flea]\nbackground-alpha = 0.4\n[bar]\nsize = 31\n'
    user.write_bytes(original)
    tx.apply_file_targets(
        {'omarchy-shell-style': targets['omarchy-shell-style']},
        label='shell font scale test',
        owned_fields={'omarchy-shell-style': set(shell_preferences.FONT_FIELDS)},
    )
    applied = tomllib.loads(user.read_text())
    assert applied['font']['body'] == 16 and applied['font']['heading'] == 24
    assert applied['flea']['background-alpha'] == 0.4 and applied['bar']['size'] == 31
    tx.rollback_latest(label='shell font scale test')
    assert user.read_bytes() == original

with TemporaryDirectory(prefix='laf-shell-font-derived-') as tmp, ExitStack() as stack:
    home = fixture(stack, tmp)
    theme = home / '.local/state/omarchy/current/theme'
    theme.mkdir(parents=True)
    (theme / 'shell.toml').write_text('[bar]\nsize-horizontal = 30\n')
    targets, _ = fonts.build_global_font_targets('Montserrat', 12, 'Comic Code', 12, set())
    values = tomllib.loads(targets['omarchy-shell-style'].decode())['font']
    assert values['base-size'] == 16 and values['body'] == 16
    assert values['title'] == 19 and values['heading'] == 21

with TemporaryDirectory(prefix='laf-shell-font-icons-') as tmp, ExitStack() as stack:
    home = fixture(stack, tmp)
    theme = home / '.local/state/omarchy/current/theme'
    theme.mkdir(parents=True)
    (theme / 'shell.toml').write_text('[font]\nbase-size = 12.0\nbody-small = 12\ntitle = 16\n')
    targets, _ = fonts.build_global_font_targets('Montserrat', 12, 'Comic Code', 12, set())
    values = tomllib.loads(targets['omarchy-shell-style'].decode())['font']
    assert values['body-small'] == 16 and values['title'] == 21
    assert values['icon-small'] == values['body-small'] == 16
    assert values['icon'] == values['title'] == 21
    assert values['icon-large'] == 24

with TemporaryDirectory(prefix='laf-shell-font-fourth-') as tmp, ExitStack() as stack:
    home = fixture(stack, tmp)
    theme = home / '.local/state/omarchy/current/theme'
    theme.mkdir(parents=True)
    (theme / 'shell.toml').write_text('[font]\nbase-size = 14\nbody = 14\n')
    targets, _ = fonts.build_global_font_targets('Montserrat', 14, 'Comic Code', 14, set())
    values = tomllib.loads(targets['omarchy-shell-style'].decode())['font']
    assert values['base-size'] == 19 and values['body'] == 19
    assert values['heading'] == 25

print('4 shell typography scaling scenarios passed (pinned theme, derived theme, partial pin with derived icons, non-12 px theme; Apply/Undo preserved unrelated TOML).')
