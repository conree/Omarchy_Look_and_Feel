"""Early, user-owned generic font preferences; the loader is installed once."""
from pathlib import Path
import subprocess
from xml.sax.saxutils import escape

LOADER = Path('/etc/fonts/conf.d/00-look-and-feel.conf')
LOADER_SOURCE = Path(__file__).resolve().parent / 'assets/00-look-and-feel.conf'


def build(system_family, terminal_family):
    lines = ['<?xml version="1.0"?>',
             '<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">',
             '<fontconfig>',
             '  <!-- Managed by Look and Feel. Change fonts in the plugin. -->']
    for generic, family in (('sans-serif', system_family), ('monospace', terminal_family)):
        if (not isinstance(family, str) or not family.strip() or len(family) > 300
                or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in family)
                or family.casefold() in {'sans-serif', 'serif', 'monospace'}):
            raise ValueError('Generic font preferences require a concrete installed font family')
        lines.extend([
            '  <match target="pattern">',
            f'    <test name="family" qual="first"><string>{generic}</string></test>',
            '    <edit name="family" mode="prepend_first" binding="strong">',
            f'      <string>{escape(family)}</string>',
            '    </edit>', '  </match>',
        ])
    return ('\n'.join(lines + ['</fontconfig>', ''])).encode('utf-8')


def status(system_family, terminal_family):
    """Distinguish saved preferences from an active, effective loader."""
    try:
        installed = LOADER.read_bytes() == LOADER_SOURCE.read_bytes()
    except OSError:
        installed = False
    if not installed:
        return {'app': 'Generic fonts', 'action': 'setup',
                'reason': 'The early Fontconfig loader needs one-time administrator installation; '
                          'see README: Generic font preferences. Selected preferences are saved.'}
    try:
        actual = []
        for generic in ('sans-serif', 'monospace'):
            result = subprocess.run(['fc-match', '-f', '%{family[0]}', generic],
                                    capture_output=True, text=True, timeout=10, check=True)
            actual.append(result.stdout.strip())
        if actual == [system_family, terminal_family]:
            return None
    except (OSError, subprocess.SubprocessError):
        pass
    return {'app': 'Generic fonts', 'action': 'review',
            'reason': 'Fontconfig did not resolve both generic families to the saved choices. '
                      'A competing configuration or font environment needs review.'}
