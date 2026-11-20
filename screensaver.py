"""Themed screensaver owned by the plugin.

Omarchy's own screensaver hard-codes its ttfx colours. The plugin runs its own
copy of the launcher and renderer (``screensaver/``) and fills each effect's
colour options from the active Omarchy theme every time an effect starts, so
theme changes made anywhere are followed without an Apply.

While the plugin's screensaver is on, Omarchy's ``screensaver-off`` toggle is
held so Omarchy's idle service does not start the stock screensaver as well.
The toggle is released again only if the plugin was the one that set it.
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import tomllib
from pathlib import Path

DEFAULTS = {'enabled': False, 'idleSeconds': 600, 'effect': 'matrix'}
IDLE_CHOICES = (60, 120, 300, 600, 900, 1200, 1800, 3600)

# Colour options per ttfx effect (ttfx 0.x, `ttfx <effect> --help`).
# Options ending in -colors/-stops/-gradient take a list; -color takes one.
EFFECTS = {
    'beams': ('--beam-gradient-stops', '--final-gradient-stops'),
    'binarypath': ('--binary-colors', '--final-gradient-stops'),
    'blackhole': ('--blackhole-color', '--star-colors', '--final-gradient-stops'),
    'bouncyballs': ('--ball-colors', '--final-gradient-stops'),
    'bubbles': ('--bubble-colors', '--pop-color', '--final-gradient-stops'),
    'burn': ('--starting-color', '--burn-colors', '--final-gradient-stops'),
    'colorshift': ('--final-gradient-stops',),
    'crumble': ('--final-gradient-stops',),
    'decrypt': ('--ciphertext-colors', '--final-gradient-stops'),
    'errorcorrect': ('--error-color', '--correct-color', '--final-gradient-stops'),
    'expand': ('--final-gradient-stops',),
    'fireworks': ('--firework-colors', '--final-gradient-stops'),
    'highlight': ('--final-gradient-stops',),
    'laseretch': ('--cool-gradient-stops', '--laser-gradient-stops', '--spark-gradient-stops', '--final-gradient-stops'),
    'matrix': ('--rain-color-gradient', '--highlight-color', '--final-gradient-stops'),
    'middleout': ('--starting-color', '--final-gradient-stops'),
    'orbittingvolley': ('--final-gradient-stops',),
    'overflow': ('--overflow-gradient-stops', '--final-gradient-stops'),
    'pour': ('--starting-color', '--final-gradient-stops'),
    'print': ('--final-gradient-stops',),
    'rain': ('--rain-colors', '--final-gradient-stops'),
    'randomsequence': ('--final-gradient-stops',),
    'rings': ('--ring-colors', '--final-gradient-stops'),
    'scattered': ('--final-gradient-stops',),
    'slice': ('--final-gradient-stops',),
    'slide': ('--final-gradient-stops',),
    'smoke': ('--starting-color', '--smoke-gradient-stops', '--final-gradient-stops'),
    'spotlights': ('--final-gradient-stops',),
    'spray': ('--final-gradient-stops',),
    'swarm': ('--base-color', '--flash-color', '--final-gradient-stops'),
    'sweep': ('--final-gradient-stops',),
    'synthgrid': ('--grid-gradient-stops', '--text-gradient-stops'),
    'thunderstorm': ('--lightning-color', '--glowing-text-color', '--spark-glow-color', '--final-gradient-stops'),
    'unstable': ('--unstable-color', '--final-gradient-stops'),
    'vhstape': ('--glitch-line-colors', '--glitch-wave-colors', '--noise-colors', '--final-gradient-stops'),
    'waves': ('--wave-gradient-stops', '--final-gradient-stops'),
    'wipe': ('--final-gradient-stops',),
}
CHOICES = ('matrix', 'random', *sorted(set(EFFECTS) - {'matrix'}))


def _config_dir() -> Path:
    raw = os.environ.get('XDG_CONFIG_HOME', '')
    return (Path(raw) if raw.startswith('/') else Path.home() / '.config') / 'omarchy-look-and-feel'


def settings_path() -> Path:
    return _config_dir() / 'screensaver.json'


def toggle_path() -> Path:
    # Omarchy's omarchy-toggle hard-codes this location.
    return Path.home() / '.local/state/omarchy/toggles/screensaver-off'


def validate(data) -> dict:
    if not isinstance(data, dict) or not set(data) <= {*DEFAULTS, 'holdsOmarchyToggle'}:
        raise ValueError('Invalid screensaver settings')
    merged = {**DEFAULTS, 'holdsOmarchyToggle': False, **data}
    if type(merged['enabled']) is not bool or type(merged['holdsOmarchyToggle']) is not bool:
        raise ValueError('Screensaver must be On or Off')
    if type(merged['idleSeconds']) is not int or merged['idleSeconds'] not in IDLE_CHOICES:
        raise ValueError('Unsupported screensaver idle time')
    if merged['effect'] not in CHOICES:
        raise ValueError('Unsupported screensaver effect')
    return merged


def load() -> dict:
    try:
        raw = settings_path().read_bytes()
    except FileNotFoundError:
        return validate({})
    if len(raw) > 4096:
        raise ValueError('Invalid screensaver settings')
    return validate(json.loads(raw))


def save(enabled: bool, idle_seconds: int, effect: str) -> dict:
    import transaction as tx
    # Only the hold is carried over, so an unrecognised stored value (from an
    # older or newer version, or a hand edit) never blocks saving or Off.
    try:
        held = json.loads(settings_path().read_bytes()[:4096]).get('holdsOmarchyToggle') is True
    except (OSError, ValueError, AttributeError):
        held = False
    wanted = validate({'enabled': enabled, 'idleSeconds': idle_seconds, 'effect': effect,
                       'holdsOmarchyToggle': held})
    flag = toggle_path()
    path = tx._ensure_home_path(settings_path(), allow_missing_parents=True)
    tx._mkdir_private(path.parent)
    path = tx._ensure_home_path(path)

    def write():
        tx._atomic_write(path, json.dumps(wanted, sort_keys=True).encode() + b'\n', 0o600)

    # Record a hold before taking it, and release it before recording that, so
    # a failure never leaves Omarchy's screensaver disabled with no owner.
    if enabled and not flag.exists():
        wanted['holdsOmarchyToggle'] = True
        write()
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.touch()
    elif not enabled and held:
        flag.unlink(missing_ok=True)
        wanted['holdsOmarchyToggle'] = False
        write()
    else:
        write()
    return wanted


def _luminance(color: str) -> float:
    channels = [int(color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
    return sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))


def palette(theme_dir: Path | None = None) -> dict:
    """Theme colours as bare hex, kept visible on the screensaver's black."""
    theme_dir = theme_dir or Path.home() / '.local/state/omarchy/current/theme'
    data = tomllib.loads((theme_dir / 'colors.toml').read_text())
    hexes = {k: v[1:].lower() for k, v in data.items()
             if isinstance(v, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', v)}
    if 'accent' not in hexes or 'foreground' not in hexes:
        raise ValueError('theme has no complete colour palette')

    def pick(*names):
        color = next(hexes[n] for n in (*names, 'accent') if n in hexes)
        # Light themes can use near-black colours that vanish on black.
        return color if _luminance(color) >= .04 else hexes['foreground'] if _luminance(hexes['foreground']) >= .04 else 'ffffff'

    return {
        'primary': pick('color2'), 'accent': pick('accent'), 'secondary': pick('color5'),
        'dim': next((hexes[n] for n in ('color8', 'muted') if n in hexes), pick('accent')),
        'text': pick('foreground'), 'error': pick('color1'),
    }


def effect_args(effect: str, colors: dict) -> list[str]:
    if effect not in EFFECTS:
        raise ValueError('Unsupported screensaver effect')
    gradient = [colors['primary'], colors['accent'], colors['secondary']]
    special = {
        '--rain-color-gradient': [colors['primary'], colors['dim']],
        '--highlight-color': [colors['secondary']],
        '--grid-gradient-stops': [colors['dim'], colors['accent']],
        '--starting-color': [colors['text']],
        '--error-color': [colors['error']],
        '--correct-color': [colors['primary']],
    }
    args = [effect]
    for option in EFFECTS[effect]:
        values = special.get(option)
        if values is None:
            values = [colors['secondary']] if option.endswith('-color') else gradient
        args += [option, *values]
    return args


def ttfx_args(choice: str | None = None) -> list[str]:
    choice = choice or load()['effect']
    if choice not in CHOICES:
        raise ValueError('Unsupported screensaver effect')
    effect = random.choice(sorted(EFFECTS)) if choice == 'random' else choice
    return effect_args(effect, palette())


def status() -> dict:
    data = load()
    data.pop('holdsOmarchyToggle')
    data.update(choices=list(CHOICES), idleChoices=list(IDLE_CHOICES))
    return data


def main(argv: list[str]) -> int:
    if len(argv) in (1, 2) and argv[0] == 'args':
        # NUL-separated for `mapfile -d ''` in the renderer.
        sys.stdout.write('\0'.join(ttfx_args(argv[1] if len(argv) == 2 else None)) + '\0')
        return 0
    if argv == ['status']:
        print(json.dumps(status()))
        return 0
    print('usage: screensaver.py args [effect] | status', file=sys.stderr)
    return 2


if __name__ == '__main__':
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, KeyError, tomllib.TOMLDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
