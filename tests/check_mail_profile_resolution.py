"""Resolve the Betterbird profile from the installed executable, not its name."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mail_font_adapters as mail


def write_profile(root, name, app_dir, install_id):
    profile = root / name
    profile.mkdir(parents=True)
    (profile / 'prefs.js').write_text('')
    (profile / 'compatibility.ini').write_text(
        '[Compatibility]\nLastVersion=153.6.0_20261027103258/20261027103258\n'
        f'LastAppDir={app_dir}\n'
    )


def which_for(executable):
    def which(name):
        return executable if name == 'betterbird' else None
    return which


with TemporaryDirectory(prefix='laf-mail-profile-') as tmp:
    home = Path(tmp)
    root = home / '.thunderbird'
    root.mkdir()
    write_profile(root, 'mpsjivab.default-default', '/opt/betterbird', 'F72D9E66FA3C07ED')
    write_profile(root, 'u1f22xee.default-beta', '/opt/thunderbird-beta', '88BD99BFBD84E00F')
    (root / 'profiles.ini').write_text(
        '[Profile2]\nName=default-default\nIsRelative=1\nPath=mpsjivab.default-default\n\n'
        '[Profile0]\nName=default-beta\nIsRelative=1\nPath=u1f22xee.default-beta\n\n'
        '[InstallF72D9E66FA3C07ED]\nDefault=mpsjivab.default-default\nLocked=1\n\n'
        '[Install88BD99BFBD84E00F]\nDefault=u1f22xee.default-beta\nLocked=1\n'
    )
    with patch.object(mail, 'HOME', home), \
         patch.object(mail.shutil, 'which', side_effect=which_for('/opt/betterbird/betterbird')), \
         patch.dict(os.environ, {'XDG_DATA_HOME': str(home / '.local/share'), 'XDG_DATA_DIRS': ''}):
        assert mail.writable_betterbird_profile() == '.thunderbird/mpsjivab.default-default/prefs.js'
        result = [row for row in mail.discover_mail_profiles() if row['desktopId'] == 'eu.betterbird.Betterbird.desktop'][0]
        assert result['prefsPath'] == '.thunderbird/mpsjivab.default-default/prefs.js'

    with patch.object(mail, 'HOME', home), \
         patch.object(mail.shutil, 'which', side_effect=which_for('/opt/thunderbird-beta/thunderbird')), \
         patch.dict(os.environ, {'XDG_DATA_HOME': str(home / '.local/share'), 'XDG_DATA_DIRS': ''}):
        assert mail.writable_betterbird_profile() == '.thunderbird/u1f22xee.default-beta/prefs.js'

    # A second profile last used by the same executable is ambiguous: refuse.
    write_profile(root, 'third.default', '/opt/betterbird', 'AAAAAAAAAAAAAAAA')
    (root / 'profiles.ini').write_text((root / 'profiles.ini').read_text() + '\n[Profile3]\nName=default\nIsRelative=1\nPath=third.default\n\n[InstallAAAAAAAAAAAAAAAA]\nDefault=third.default\nLocked=1\n')
    with patch.object(mail, 'HOME', home), \
         patch.object(mail.shutil, 'which', side_effect=which_for('/opt/betterbird/betterbird')), \
         patch.dict(os.environ, {'XDG_DATA_HOME': str(home / '.local/share'), 'XDG_DATA_DIRS': ''}):
        assert mail.writable_betterbird_profile() is None

print('Active Betterbird profile resolution passed: install/compatibility match, executable switch, ambiguous refusal.')

# Compatibility metadata alone is authoritative: a matching profile works
# without an [Install] section, and two matching profiles are ambiguous.
with TemporaryDirectory(prefix='laf-mail-profile-no-install-') as tmp:
    home = Path(tmp)
    root = home / '.thunderbird'
    root.mkdir()
    write_profile(root, 'only.default', '/opt/betterbird', '')
    (root / 'profiles.ini').write_text(
        '[Profile0]\nName=default\nIsRelative=1\nPath=only.default\n'
    )
    with patch.object(mail, 'HOME', home), \
         patch.object(mail.shutil, 'which', side_effect=which_for('/opt/betterbird/betterbird')), \
         patch.dict(os.environ, {'XDG_DATA_HOME': str(home / '.local/share'), 'XDG_DATA_DIRS': ''}):
        assert mail.writable_betterbird_profile() == '.thunderbird/only.default/prefs.js'
        row = [item for item in mail.discover_mail_profiles() if item['desktopId'] == 'eu.betterbird.Betterbird.desktop'][0]
        assert row['prefsPath'] == '.thunderbird/only.default/prefs.js'
    write_profile(root, 'second.default', '/opt/betterbird', '')
    (root / 'profiles.ini').write_text(
        '[Profile0]\nName=default\nIsRelative=1\nPath=only.default\n\n'
        '[Profile1]\nName=default\nIsRelative=1\nPath=second.default\n'
    )
    with patch.object(mail, 'HOME', home), \
         patch.object(mail.shutil, 'which', side_effect=which_for('/opt/betterbird/betterbird')), \
         patch.dict(os.environ, {'XDG_DATA_HOME': str(home / '.local/share'), 'XDG_DATA_DIRS': ''}):
        assert mail.writable_betterbird_profile() is None
        row = [item for item in mail.discover_mail_profiles() if item['desktopId'] == 'eu.betterbird.Betterbird.desktop'][0]
        assert row['prefsPath'] == ''
