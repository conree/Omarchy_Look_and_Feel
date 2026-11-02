"""Flea's native background alpha, independent of terminal opacity and fonts."""
import json
import shutil
import subprocess
import time
from pathlib import Path
import tomllib

import transaction as tx
import shell_preferences

LABEL = 'Flea opacity settings'
TARGET = 'omarchy-shell-style'
FIELD = 'flea/background-alpha'


def validate_percent(value):
    if type(value) is not int or not 0 <= value <= 100:
        raise ValueError('Flea opacity must be an integer from 0 to 100 percent')
    return value


def read():
    from opacity_actions import _read_terminal
    path = tx._ensure_home_path(Path.home() / tx.FILE_TARGETS[TARGET], allow_missing_parents=True)
    return _read_terminal(path)


def build(percent):
    validate_percent(percent)
    if not shutil.which('flea'):
        raise tx.TransactionError('Flea is not installed')
    data = shell_preferences.decode(read())
    data[FIELD] = f'background-alpha = {percent / 100:g}\n'
    return {TARGET: shell_preferences.encode(data)}


def pending(percent, *, wait=False):
    """Read the real Flea surface; never close windows or reload file operations."""
    if percent is None:
        return []
    try:
        result = subprocess.run(['hyprctl', 'clients', '-j'], capture_output=True, text=True,
                                timeout=3, check=True)
        pids = {c['pid'] for c in json.loads(result.stdout) if c.get('class') == 'com.thisisgm.flea'}
        expected = int(percent / 100 * 255 + 0.5) / 255
        deadline = time.monotonic() + (0.6 if wait else 0)
        for pid in pids:
            while True:
                result = subprocess.run(['quickshell', 'ipc', '--pid', str(pid), 'call', 'flea', 'glass'],
                                        capture_output=True, text=True, timeout=3, check=True)
                glass = json.loads(result.stdout)
                if abs(float(glass['alpha']) - expected) < 0.0001:
                    break
                if expected < 1 and glass.get('clear') is False:
                    return [{'app': 'Flea', 'action': 'reopen',
                             'reason': 'Reopen Flea to enable transparency; this window started fully opaque.'}]
                if time.monotonic() >= deadline:
                    return [{'app': 'Flea', 'action': 'reopen',
                             'reason': 'Opacity is saved; reopen Flea to load the background setting.'}]
                time.sleep(0.1)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return [{'app': 'Flea', 'action': 'check',
                 'reason': 'Opacity is saved, but the running window could not be checked. Reopen Flea if needed.'}]
    return []


def apply(percent, *, automatic=False):
    import appearance_policy as policy
    targets = build(percent)
    parent = policy.latest(LABEL) if automatic else None
    if automatic and parent is None:
        raise tx.TransactionError('Saved Flea opacity has no original Apply transaction')
    if automatic:
        targets = policy.changed_targets(targets)
    else:
        targets['appearance-policy'] = policy.update('fleaOpacity', percent)
    identity = tx.apply_file_targets(
        targets, label='Automatic Flea opacity reconciliation' if automatic else LABEL,
        parent_transaction=parent[1].name if parent else None,
        owned_fields={TARGET: {FIELD}, 'appearance-policy': {'fleaOpacity'}}) if targets else None
    return {'kind': 'fleaOpacity', 'state': 'committed' if identity else 'already-current',
            'transaction': identity, 'after': f'{percent}%', 'readback': f'{percent}%',
            'opacityPercent': percent, 'pendingApplications': pending(percent, wait=bool(identity)),
            'undoAvailable': True, 'renderedAppearanceVerified': False}


def status():
    import appearance_policy as policy
    return {'undoAvailable': policy.latest(LABEL) is not None,
            'savedPercent': policy.read().get('fleaOpacity')}


def undo():
    identity = tx.rollback_latest(label=LABEL)
    restored = tomllib.loads(read().decode()).get('flea', {}).get('background-alpha')
    percent = round(restored * 100) if restored is not None else None
    result = status()
    return {'kind': 'fleaOpacity', 'rolledBack': identity, **result,
            'pendingApplications': pending(percent, wait=True), 'renderedAppearanceVerified': False}
