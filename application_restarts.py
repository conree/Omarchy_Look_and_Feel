"""Track appearance changes seen by running PCManFM instances, without signals.

This observes settings, not rendered windows. A process's first observation is
its baseline; changes predating that observation cannot be detected.
"""
from pathlib import Path
import configparser
import hashlib
import json
import os

import transaction as tx

PROC = Path('/proc')
GTK_KEYS = ('gtk-font-name', 'gtk-theme-name', 'gtk-application-prefer-dark-theme',
            'gtk-icon-theme-name')
DESKTOP_KEYS = ('font-name', 'text-scaling-factor', 'icon-theme')


def processes():
    """PID reuse and reboot must not retain an old instance's notice."""
    boot = (PROC / 'sys/kernel/random/boot_id').read_text().strip()
    found = set()
    for path in PROC.iterdir():
        if not path.name.isdecimal():
            continue
        try:
            if path.stat().st_uid != os.geteuid():
                continue
            # comm is matched exactly: PCManFM-Qt has a different integration.
            if (path / 'comm').read_text().strip() != 'pcmanfm':
                continue
            fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            if fields[0] in ('Z', 'X'):
                continue
            found.add(f'{boot}:{path.name}:{int(fields[19])}')
        except (FileNotFoundError, ProcessLookupError):
            continue  # The process exited during the scan.
    return found


def appearance():
    """Content and relevant values only; an unchanged rewrite is not a change."""
    def read(target):
        path = tx._ensure_home_path(Path.home() / tx.FILE_TARGETS[target], allow_missing_parents=True)
        try:
            with path.open('rb') as stream:
                raw = stream.read(tx.MAX_SETTINGS_BYTES + 1)
        except FileNotFoundError:
            return b''
        if len(raw) > tx.MAX_SETTINGS_BYTES:
            raise ValueError('appearance configuration is too large')
        return raw

    parser = configparser.RawConfigParser(strict=True)
    parser.read_string(read('gtk3-settings').decode())
    values = {key: parser.get('Settings', key, fallback=None) for key in GTK_KEYS}
    values['css'] = hashlib.sha256(read('gtk3-css')).hexdigest()
    import desktop_fonts
    _, settings = desktop_fonts._settings()
    values['desktop'] = {key: desktop_fonts.effective(settings, key) for key in DESKTOP_KEYS}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def observe():
    """Return current notices, or None when observation must be retried.

    Called under the controller's operation lock. Observation failure preserves
    the previous cache and UI notices and never changes an Apply's outcome.
    """
    try:
        live = processes()
        directory = tx._ensure_home_path(tx.transactions_path().parent, allow_missing_parents=True)
        path = tx._ensure_home_path(directory / 'application-restarts.json', allow_missing_parents=True)
        saved = {}
        if path.exists():
            if path.stat().st_size > tx.MAX_SETTINGS_BYTES:
                raise ValueError('restart observations are too large')
            saved = json.loads(path.read_bytes())
            if not isinstance(saved, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                                 for k, v in saved.items()):
                raise ValueError('invalid restart observations')
        current = appearance() if live else None
        updated = {identity: saved.get(identity, current) for identity in sorted(live)}
        if updated != saved:
            tx._mkdir_private(directory)
            tx._atomic_write(path, (json.dumps(updated, sort_keys=True) + '\n').encode(), 0o600)
        if any(baseline != current for baseline in updated.values()):
            return [{'app': 'PCManFM', 'action': 'reopen',
                     'reason': 'Appearance settings changed while PCManFM was running. '
                               'Fully quit and reopen PCManFM to load them; closing a window may leave it running.'}]
        return []
    except (OSError, RuntimeError, ValueError, ImportError, IndexError, configparser.Error):
        return None


def add_to_result(result):
    notices = observe()
    if notices is not None:
        result['restartApplications'] = notices
    return result
