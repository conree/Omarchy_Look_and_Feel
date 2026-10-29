"""Independent terminal background opacity Apply, repair, and Undo."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat

import transaction as tx
from terminal_preferences import OPACITY_FIELDS, decode, encode

LABEL = 'Terminal opacity settings'
TERMINALS = {'ghostty-config': 'ghostty', 'kitty-config': 'kitty',
             'alacritty-config': 'alacritty', 'foot-config': 'foot',
             'wezterm-config': 'wezterm'}


def validate_percent(value):
    if type(value) is not int or not 0 <= value <= 100:
        raise ValueError('Terminal opacity must be an integer from 0 to 100 percent')
    return value


def build(percent, pending=None):
    amount = str(validate_percent(percent) / 100)
    targets = {}
    for target, executable in TERMINALS.items():
        if not shutil.which(executable):
            continue
        try:
            candidate = _build_terminal(target, amount)
            _preflight_terminal(candidate)
            targets.update(candidate)
        except (OSError, RuntimeError, ValueError):
            if pending is None:
                raise
            pending.append({'app': executable, 'action': 'review',
                            'reason': 'Its opacity settings could not be safely read or updated; they were skipped.'})
    if not targets and not pending:
        if pending is None:
            raise tx.TransactionError('No supported terminal opacity settings could be prepared')
        pending.append({'app': 'Terminals', 'action': 'review',
                        'reason': 'No supported terminal opacity control was detected; no terminal settings were changed.'})
    return targets


def _preflight_terminal(targets):
    # Identify unsafe files before combining terminals. The transaction still
    # repeats its own snapshot and unchanged checks to catch subsequent races.
    for path in tx._target_paths(targets).values():
        _read_terminal(path)


def _read_terminal(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0))
    except FileNotFoundError:
        return b''
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & ~0o777 or info.st_size > tx.MAX_TARGET_BYTES):
            raise tx.TransactionError('Terminal opacity target cannot be safely replaced')
        raw = stream.read(tx.MAX_TARGET_BYTES + 1)
        if len(raw) > tx.MAX_TARGET_BYTES:
            raise tx.TransactionError('Terminal opacity target exceeds the size limit')
        return raw


def _build_terminal(target, amount):
    targets = {}
    if target == 'wezterm-config':
        tx.require_wezterm_location()
    path = tx._ensure_home_path(Path.home() / tx.FILE_TARGETS[target], allow_missing_parents=True)
    raw = _read_terminal(path)
    if target == 'wezterm-config':
        import wezterm_blocks as blocks
        data = blocks.decode(raw.decode())
        data['opacity'] = f'config.window_background_opacity = {amount}\n'
        targets[target] = blocks.encode(data).encode()
        return targets
    data = decode(target, raw)
    if target == 'ghostty-config':
        data['background-opacity'] = f'background-opacity = {amount}\n'
        # Explicit cell backgrounds belong to prompts and other terminal
        # UI. Keep them opaque while changing only the window background.
        data['background-opacity-cells'] = 'background-opacity-cells = false\n'
        css_path = tx._ensure_home_path(Path.home() / tx.FILE_TARGETS['ghostty-opacity-css'], allow_missing_parents=True)
        if css_path.is_dir():
            raise tx.TransactionError('Ghostty opacity stylesheet is not a file')
        data['opacity-css-import'] = 'gtk-custom-css = ' + json.dumps(str(css_path)) + '\n'
        # GTK caches its global user stylesheet in already-running apps.
        # Ghostty reloads this per-app USER-priority provider on SIGUSR2,
        # allowing a repair without closing the user's terminal sessions.
        surfaces = ', '.join('window.window:not(.background)' + suffix for suffix in (
            '', ' treeview', ' textview', ' textview text', ' .view',
            ' list', ' row', ' notebook', ' stack', ' scrolledwindow'))
        targets['ghostty-opacity-css'] = (
            '/* Preserve native terminal transparency beneath GTK user palettes. */\n'
            + surfaces + ' { background-color: transparent; background-image: none; }\n').encode()
    elif target == 'kitty-config':
        data['background_opacity'] = f'background_opacity {amount}\n'
    elif target == 'alacritty-config':
        old = data['window/opacity'] or ''
        key = 'window.opacity' if old.lstrip().startswith('window.opacity') else 'opacity'
        data['window/opacity'] = f'{key} = {amount}\n'
    else:
        # Older Foot uses [colors]; current Foot has separate light/dark.
        fields = ['colors/alpha'] if data['colors/alpha'] is not None else ['colors-dark/alpha', 'colors-light/alpha']
        for field in fields:
            data[field] = f'alpha={amount}\n'
    targets[target] = encode(target, data)
    return targets


def _hash(target):
    path = tx._ensure_home_path(Path.home() / tx.FILE_TARGETS[target], allow_missing_parents=True)
    raw = _read_terminal(path)
    if target == 'wezterm-config':
        import wezterm_blocks
        values = {'opacity': wezterm_blocks.decode(raw.decode())['opacity']}
    else:
        data = decode(target, raw)
        values = {key: data[key] for key in OPACITY_FIELDS[target]}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def _refresh(previous):
    from terminal_reload import reload_terminals
    from application_restarts import processes
    state_path = tx._ensure_home_path(tx.transactions_path().parent / 'opacity-reload.json', allow_missing_parents=True)
    if not previous and not state_path.exists():
        return {'requested': [], 'failed': []}, []
    lost_state = False
    try:
        if state_path.exists() and state_path.stat().st_size > tx.MAX_SETTINGS_BYTES:
            raise ValueError('Opacity reload observations are too large')
        saved = json.loads(state_path.read_bytes()) if state_path.exists() else {}
        if (not isinstance(saved, dict) or set(saved) - {'baselines', 'failedTargets'}
                or not isinstance(saved.get('baselines', {}), dict)
                or not isinstance(saved.get('failedTargets', []), list)
                or set(saved.get('failedTargets', [])) - {'ghostty-config', 'kitty-config'}):
            raise ValueError('Invalid opacity reload observations')
        for target, baselines in saved.get('baselines', {}).items():
            if target not in {'foot-config', 'kitty-config'} or not isinstance(baselines, dict):
                raise ValueError('Invalid opacity restart observations')
            if any(not isinstance(pid, str) or not isinstance(value, str) for pid, value in baselines.items()):
                raise ValueError('Invalid opacity process identity')
    except (ValueError, TypeError):
        # This disposable cache cannot invalidate an already committed Apply.
        # Retry signals and retain conservative notices until old processes exit.
        saved = {'failedTargets': ['ghostty-config', 'kitty-config']}
        lost_state = True
    result = reload_terminals(set(previous) | set(saved.get('failedTargets', [])))
    pending = [{'app': name, 'action': 'reload', 'reason': 'Opacity saved; reopen the terminal to load it.'}
               for name in result['failed']]
    # Foot does not reload its config. Kitty cannot acquire dynamic opacity
    # support by reloading a process that was started without it.
    observations = {}
    for target, name in [('foot-config', 'Foot'), ('kitty-config', 'Kitty')]:
        live = processes(name.lower())
        baselines = saved.get('baselines', {}).get(target, {})
        baselines = {pid: baseline for pid, baseline in baselines.items() if pid in live}
        if target in previous:
            for pid in live:
                baselines.setdefault(pid, previous[target])
        elif lost_state:
            baselines.update(dict.fromkeys(live, 'unknown'))
        if baselines:
            observations[target] = baselines
            if any(value != _hash(target) for value in baselines.values()):
                pending.append({'app': name, 'action': 'reopen', 'reason': 'Fully quit and reopen the terminal to load the saved opacity.'})
    updated = {'baselines': observations,
               'failedTargets': [target for target, executable in TERMINALS.items() if executable in result['failed']]}
    if updated != saved:
        tx._mkdir_private(state_path.parent)
        tx._atomic_write(state_path, (json.dumps(updated, sort_keys=True) + '\n').encode(), 0o600)
    return result, pending


def refresh(previous):
    try:
        return _refresh(previous)
    except (OSError, RuntimeError, ValueError):
        return {'requested': [], 'failed': []}, [
            {'app': 'Terminals', 'action': 'reopen',
             'reason': 'Opacity was saved, but reload status could not be checked. Reopen running terminals.'}]


def apply(percent, *, automatic=False):
    import appearance_policy as policy
    validate_percent(percent)
    skipped = []
    targets = build(percent, skipped)
    changed = policy.changed_targets(targets)
    previous = {target: _hash(target) for target in changed if target in TERMINALS}
    if 'ghostty-opacity-css' in changed:
        previous.setdefault('ghostty-config', _hash('ghostty-config'))
    parent = policy.latest(LABEL) if automatic else None
    if automatic and parent is None:
        raise tx.TransactionError('Saved opacity has no original Apply transaction')
    if automatic:
        targets = policy.changed_targets(targets)
    else:
        targets['appearance-policy'] = policy.update('opacity', percent)
    identity = tx.apply_file_targets(targets, label='Automatic opacity reconciliation' if automatic else LABEL,
                                     parent_transaction=parent[1].name if parent else None,
                                     owned_fields={**OPACITY_FIELDS, 'appearance-policy': {'opacity'}}) if targets else None
    reload_status, pending = refresh(previous)
    pending.extend(skipped)
    return {'kind': 'opacity', 'state': 'committed' if identity else 'already-current',
            'transaction': identity, 'after': f'{percent}%', 'readback': f'{percent}%',
            'opacityPercent': percent, 'terminalReload': reload_status,
            'pendingApplications': pending, 'undoAvailable': True, 'renderedAppearanceVerified': False}


def status():
    import appearance_policy as policy
    return {'undoAvailable': policy.latest(LABEL) is not None, 'savedPercent': policy.read().get('opacity')}


def undo():
    import appearance_policy as policy
    parent = policy.latest(LABEL)
    if parent is None:
        raise tx.TransactionError('There is no saved opacity operation to undo')
    targets = {row['id'] for row in parent[2]['targets']}
    for _, _, child in policy.records():
        if child.get('parentTransaction') == parent[1].name and child['state'] == 'committed':
            targets.update(row['id'] for row in child['targets'])
    previous = {target: _hash(target) for target in targets if target in TERMINALS}
    css_path = (tx._ensure_home_path(Path.home() / tx.FILE_TARGETS['ghostty-opacity-css'], allow_missing_parents=True)
                if 'ghostty-opacity-css' in targets else None)
    css_before = _read_terminal(css_path) if css_path and css_path.exists() else None
    identity = tx.rollback_latest(label=LABEL)
    changed = {target: value for target, value in previous.items() if value != _hash(target)}
    if css_path:
        tx._ensure_home_path(css_path, allow_missing_parents=True)
    css_after = _read_terminal(css_path) if css_path and css_path.exists() else None
    if css_before != css_after:
        changed.setdefault('ghostty-config', previous.get('ghostty-config', _hash('ghostty-config')))
    reload_status, pending = refresh(changed)
    return {'kind': 'opacity', 'rolledBack': identity, 'savedPercent': policy.read().get('opacity'),
            'terminalReload': reload_status, 'pendingApplications': pending, 'renderedAppearanceVerified': False}
