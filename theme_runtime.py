"""Explicit desktop refresh after Omarchy's offline palette generation.

Do not call the normal post-theme hook chain: it invokes a privileged browser
policy writer and arbitrary user hooks. The calls here are user-session APIs.
"""
from pathlib import Path
import base64
import shutil
import re
import subprocess
import json

LAST_REFRESH = {}


def needs_refresh():
    from appearance_actions import CURRENT_DIR
    from application_themes import palette
    from desktop_fonts import _settings
    colors = palette(CURRENT_DIR / 'theme')
    _, settings = _settings()
    from transaction import transactions_path
    status = transactions_path().parent / 'runtime-refresh.json'
    if status.exists():
        try:
            saved = json.loads(status.read_bytes())
            if saved.get('refreshPending') or saved.get('terminalReload', {}).get('failed'):
                return True
        except (ValueError, AttributeError):
            return True
    return (settings.get_string('color-scheme') != 'prefer-' + colors['mode']
            or settings.get_string('gtk-theme') != 'Adwaita' + ('-dark' if colors['mode'] == 'dark' else ''))


def _run(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[:800] or 'Desktop refresh failed: ' + command[0])


def require_offline_support(root):
    candidates = [Path(root) / 'bin/omarchy-theme-set', Path('/usr/bin/omarchy-theme-set')]
    script = next((path for path in candidates if path.is_file()), None)
    text = '\n'.join(line for line in script.read_text().splitlines() if not line.lstrip().startswith('#')) if script else ''
    supported = ('${OMARCHY_THEME_HEADLESS:-}' in text and 'THEME_HEADLESS=1' in text
                 and re.search(r'if \[\[ \$THEME_HEADLESS != "1" \]\]; then\s+run_parallel', text))
    if not supported:
        raise RuntimeError('This Omarchy version needs an offline theme-generation adapter before automatic Apply is available.')


def refresh():
    from appearance_actions import CURRENT_DIR
    from application_themes import palette
    from desktop_fonts import _settings
    from terminal_reload import reload_terminals, recolor_foot
    global LAST_REFRESH
    from transaction import transactions_path, _atomic_write
    status_path = transactions_path().parent / 'runtime-refresh.json'
    _atomic_write(status_path, b'{"refreshPending":true}\n', 0o600)
    colors = palette(CURRENT_DIR / 'theme')
    Gio, settings = _settings()
    values = {'color-scheme': 'prefer-' + colors['mode'],
              'gtk-theme': 'Adwaita' + ('-dark' if colors['mode'] == 'dark' else '')}
    for key in values:
        if not settings.is_writable(key):
            raise RuntimeError('A desktop appearance setting is locked: ' + key)
    settings.delay()
    for key, value in values.items():
        if not settings.set_string(key, value):
            settings.revert()
            raise RuntimeError('The desktop refused appearance setting: ' + key)
    settings.apply()
    Gio.Settings.sync()
    _, actual = _settings()
    if any(actual.get_string(key) != value for key, value in values.items()):
        raise RuntimeError('Desktop appearance readback did not match')
    shell = shutil.which('omarchy-shell')
    if shell:
        encoded = []
        for filename in ('colors.toml', 'shell.toml'):
            path = CURRENT_DIR / 'theme' / filename
            encoded.append(base64.b64encode(path.read_bytes()).decode() if path.is_file() else '')
        _run([shell, 'shell', 'applyTheme', *encoded])
    reload_status = reload_terminals({'ghostty-config', 'kitty-config'})
    foot_status = recolor_foot(colors)
    for key in ('requested', 'failed'):
        reload_status[key].extend(foot_status[key])
    from transaction import FILE_TARGETS, _ensure_home_path, require_wezterm_location, TransactionError
    for target in ('alacritty-config', 'wezterm-config'):
        try:
            if target == 'wezterm-config':
                require_wezterm_location()
            config = _ensure_home_path(Path.home() / FILE_TARGETS[target], allow_missing_parents=True)
            if config.exists():
                config.touch()
        except (OSError, TransactionError):
            reload_status['failed'].append(target.removesuffix('-config'))
    hyprctl = shutil.which('hyprctl')
    if hyprctl:
        _run([hyprctl, 'reload'])
    LAST_REFRESH = {'desktopThemeVerified': True, 'shellRefreshRequested': bool(shell),
                    'terminalReload': reload_status, 'renderedAppearanceVerified': False,
                    'browserPolicyWritten': False, 'arbitraryThemeHooksRun': False}
    _atomic_write(status_path,
                  (json.dumps(LAST_REFRESH, sort_keys=True) + '\n').encode(), 0o600)
    return LAST_REFRESH
