"""Request supported terminal reloads without terminating sessions."""
import os
import subprocess
import re
import stat
from pathlib import Path
import json

SIGNALS = {'ghostty-config': ('ghostty', 'USR2'), 'kitty-config': ('kitty', 'USR1')}


def reload_fonts(target_ids, *, retry=False):
    """Retain failed font reload requests across otherwise unchanged ticks."""
    from transaction import transactions_path, _atomic_write, _ensure_home_path
    status = _ensure_home_path(transactions_path().parent / 'font-reload.json', allow_missing_parents=True)
    targets = set(target_ids)
    if retry and status.exists():
        saved = json.loads(status.read_bytes())
        targets.update(key for key, (name, _) in SIGNALS.items() if name in saved.get('failed', []))
    result = reload_terminals(targets)
    payload = (json.dumps(result, sort_keys=True) + '\n').encode()
    if not status.exists() or status.read_bytes() != payload:
        _atomic_write(status, payload, 0o600)
    return result


def reload_terminals(target_ids):
    requested, failed = [], []
    for target, (name, sig) in SIGNALS.items():
        if target not in target_ids:
            continue
        try:
            result = subprocess.run(['/usr/bin/pkill', '--require-handler', '--signal', sig, '--euid', str(os.geteuid()), '--exact', name],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=5)
            if result.returncode == 0:
                requested.append(name)
            elif result.returncode == 1:
                # A live process with no registered signal handler must not be
                # mistaken for a process that is absent (or signaled anyway).
                running = subprocess.run(['/usr/bin/pgrep', '--euid', str(os.geteuid()), '--exact', name],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                if running.returncode != 1:
                    failed.append(name)
            else:
                failed.append(name)
        except (OSError, subprocess.SubprocessError):
            failed.append(name)
    return {'requested': requested, 'failed': failed, 'renderedAppearanceVerified': False}


def recolor_foot(colors):
    """Use Foot's OSC support on only this user's Foot child PTYs.

    No shell, command text, signal, process restart, or arbitrary device path.
    Open descriptors are checked again before writing the bounded color data.
    """
    from wezterm_blocks import ansi
    values = [(10, colors['foreground']), (11, colors['background']),
              (12, colors['foreground']), (17, colors['selection']),
              (19, colors['selection_foreground'])]
    sequence = ''.join(f'\033]{code};{color}\007' for code, color in values)
    sequence += ''.join(f'\033]4;{i};{color}\007' for i, color in enumerate(ansi(colors)))
    if any(not re.fullmatch(r'#[0-9a-fA-F]{6}', value) for _, value in values):
        raise ValueError('Invalid terminal color')
    requested, failed = [], []
    uid = str(os.geteuid())
    try:
        parents = subprocess.run(['pgrep', '--euid', uid, '--exact', 'foot'], capture_output=True, text=True, timeout=5)
        if parents.returncode not in (0, 1):
            raise RuntimeError('Foot process discovery failed')
        for pid in parents.stdout.split():
            if not pid.isdecimal():
                continue
            children = subprocess.run(['pgrep', '--euid', uid, '--parent', pid], capture_output=True, text=True, timeout=5)
            if children.returncode not in (0, 1):
                failed.append('foot:' + pid)
                continue
            for child in children.stdout.split():
                if not child.isdecimal():
                    continue
                fd = None
                try:
                    process = Path('/proc') / child
                    if process.stat().st_uid != os.geteuid():
                        continue
                    tty = os.readlink(process / 'fd/1')
                    if not re.fullmatch(r'/dev/pts/[0-9]+', tty):
                        continue
                    fd = os.open(tty, os.O_WRONLY | os.O_NOFOLLOW | os.O_NOCTTY | os.O_NONBLOCK)
                    info = os.fstat(fd)
                    if info.st_uid != os.geteuid() or not stat.S_ISCHR(info.st_mode):
                        raise RuntimeError('Foot PTY ownership changed')
                    payload = sequence.encode('ascii')
                    if os.write(fd, payload) != len(payload):
                        raise RuntimeError('Incomplete Foot color refresh')
                    requested.append('foot:' + pid)
                except (OSError, RuntimeError):
                    failed.append('foot:' + pid)
                finally:
                    if fd is not None:
                        os.close(fd)
    except (OSError, RuntimeError, subprocess.SubprocessError):
        failed.append('foot')
    return {'requested': sorted(set(requested)), 'failed': sorted(set(failed)), 'renderedAppearanceVerified': False}
