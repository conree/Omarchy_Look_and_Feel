"""Small allowlisted application adapters; never edit a running mail profile."""
from contextlib import contextmanager
from pathlib import Path
import fcntl
import json
import os
import re
import stat
import socket
import subprocess

BEGIN = '/* BEGIN Look and Feel managed fonts */'
END = '/* END Look and Feel managed fonts */'
MAIL_KEYS = {'msgcompose.font_face', 'font.name.sans-serif.x-western', 'font.size.variable.x-western'}


def typora_css(text, system_family, system_size, terminal_family, terminal_size):
    if BEGIN in text or END in text:
        if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
            raise ValueError('the managed document font block is malformed')
        text = text[:text.index(BEGIN)] + text[text.index(END)+len(END):]
    # Remove only the legacy plugin-owned three-rule profile. Its universal
    # descendant selector incorrectly forced monospace onto prose/math/icons.
    legacy = re.compile(r"/\* Look & Feel font profile: preserve theme styling while sharing font roles\. \*/\s*"
                        r"body\s*\{\s*font-family:[^{}]+;\s*\}\s*"
                        r"#write,\s*#write \*\s*\{\s*font-family:[^{}]+;\s*\}\s*"
                        r"#write code,[^{}]+#write \.CodeMirror \*\s*\{\s*font-family:[^{}]+;\s*\}", re.DOTALL)
    text = legacy.sub('', text, count=1)
    sf = json.dumps(system_family, ensure_ascii=False)
    tf = json.dumps(terminal_family, ensure_ascii=False)
    return text.rstrip() + '\n\n' + '\n'.join([
        BEGIN,
        ':root {', f'  --monospace: {tf}, monospace;', '}',
        'body {', f'  --monospace: {tf}, monospace;', f'  font-family: {sf}, sans-serif !important;', f'  font-size: {system_size}pt !important;', '}',
        '#write {', f'  font-family: {sf}, sans-serif !important;', f'  font-size: {system_size}pt !important;', '}',
        '#write code, #write tt, #write kbd, #write samp, #write pre, #write pre *,',
        '#write .md-fences, #write .CodeMirror, #typora-source, #typora-source .CodeMirror {',
        f'  font-family: {tf}, monospace !important;', f'  font-size: {terminal_size}pt !important;', '}',
        END, '',
    ])


def mail_preferences(text, family, size):
    values = {'msgcompose.font_face': family, 'font.name.sans-serif.x-western': family,
              'font.size.variable.x-western': round(size * 96 / 72)}  # Gecko font sizes are CSS px.
    mail_font_values(text)  # Refuse ambiguous or malformed existing preferences.
    return merge_mail_fonts(text, values)


def mail_profile_busy(path):
    lock = Path(path).parent / 'lock'
    return (lock.exists() or lock.is_symlink()) and stale_local_mail_lock(lock) is None


def stale_local_mail_lock(lock):
    """Recognize only a local numeric-address lock whose PID is absent.

    This is a read-only hint. Removal additionally requires Gecko's native
    .parentlock, an unchanged symlink, and a fresh check of the owner PID.
    A remote, malformed, live, or inaccessible lock is never bypassed.
    """
    try:
        info = lock.lstat()
        if not stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid():
            return None
        target = os.readlink(lock)
        match = re.fullmatch(r'([0-9.]+):\+([1-9][0-9]*)', target)
        if not match:
            return None
        address, pid = match[1], int(match[2])
        socket.inet_pton(socket.AF_INET, address)
        if Path('/proc/sys/net/ipv4/ip_nonlocal_bind').read_text().strip() != '0':
            return None
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.bind((address, 0))  # Local bind only; no network traffic.
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return (info.st_dev, info.st_ino, target)
        return None
    except (OSError, ValueError, OverflowError):
        return None


def _clear_stale_mail_lock(path):
    lock = path.parent / 'lock'
    if not lock.exists() and not lock.is_symlink():
        return
    identity = stale_local_mail_lock(lock)
    if identity is None:
        raise RuntimeError('Close the mail application before changing or undoing its font settings.')
    from transaction import transactions_path, _mkdir_private, _atomic_write
    import time
    directory = transactions_path().parent / 'stale-mail-locks'
    _mkdir_private(directory)
    record_path = directory / (str(time.time_ns()) + '.json')
    record = {'profile': str(path.parent), 'candidateLock': identity[2],
              'nativeParentLockHeld': True, 'state': 'prepared'}
    _atomic_write(record_path, (json.dumps(record) + '\n').encode(), 0o600)
    if stale_local_mail_lock(lock) != identity:
        raise RuntimeError('mail lock changed during stale-lock recovery')
    lock.unlink()
    record['state'] = 'removed'
    _atomic_write(record_path, (json.dumps(record) + '\n').encode(), 0o600)


_held_profile_locks = {}


@contextmanager
def lock_mail_paths(paths):
    acquired = []
    try:
        for path in paths:
            path = Path(path)
            if path.name != 'prefs.js':
                continue
            # Validate every parent before even creating an advisory lock.
            from transaction import _ensure_home_path
            _ensure_home_path(path, allow_missing_leaf=False)
            lock = path.parent / '.parentlock'
            key = str(lock)
            if key in _held_profile_locks:
                _held_profile_locks[key][1] += 1
                acquired.append(key)
                continue
            if mail_profile_busy(path):
                raise RuntimeError('Close the mail application before changing or undoing its font settings.')
            fd = os.open(lock, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                    raise RuntimeError('unsafe mail profile lock')
                fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                _clear_stale_mail_lock(path)
            except BaseException:
                os.close(fd)
                raise
            _held_profile_locks[key] = [fd, 1]
            acquired.append(key)
        yield
    finally:
        for key in reversed(acquired):
            held = _held_profile_locks[key]
            held[1] -= 1
            if held[1] == 0:
                os.close(held[0])
                del _held_profile_locks[key]


def build_app_targets(system_family, system_size, terminal_family, terminal_size, desktop_ids):
    from global_font_actions import _read, HOME, CONFIG
    from transaction import FILE_TARGETS
    targets, pending = {}, []
    if any('typora' in item.casefold() for item in desktop_ids):
        path = HOME / FILE_TARGETS['typora-base-user-css']
        before = _read(path, allow_missing=True)
        updated = typora_css(before, system_family, system_size, terminal_family, terminal_size)
        targets['typora-base-user-css'] = updated.encode()
        if updated != before:
            running = subprocess.run(['pgrep', '--euid', str(os.getuid()), '--exact', '[Tt]ypora'], capture_output=True, timeout=5)
            if running.returncode != 1:
                pending.append({'app': 'Typora', 'action': 'reopen', 'reason': 'Reload or reopen the document to load its updated font stylesheet.'})
    if 'eu.betterbird.Betterbird.desktop' in desktop_ids:
        relative = FILE_TARGETS.get('betterbird-prefs')
        if not relative:
            pending.append({'app': 'Betterbird', 'action': 'profile-unresolved', 'reason': 'A unique supported mail profile could not be resolved.'})
        else:
            path = HOME / relative
            if (path.parent / 'user.js').exists():
                pending.append({'app': 'Betterbird', 'action': 'profile-override', 'reason': 'A user preference override needs review before changing composition fonts.'})
            else:
                before = _read(path)
                updated = mail_preferences(before, system_family, system_size)
                if mail_font_values(before) != mail_font_values(updated):
                    if mail_profile_busy(path):
                        pending.append({'app': 'Betterbird', 'action': 'close-and-apply', 'reason': 'Save work and close the mail application to update composition fonts.'})
                    else:
                        targets['betterbird-prefs'] = updated.encode()
    return targets, pending


def _mail_records(text):
    # Gecko writes one canonical statement per line. Refuse other syntax, and
    # never interpret statements inside comments as active preferences.
    canonical = re.compile(r'user_pref\(("(?:\\.|[^"\\])*"), ("(?:\\.|[^"\\])*"|-?[0-9]+|true|false)\);')
    records = []
    managed_keys = set()
    in_comment = False
    for index, raw in enumerate(text.splitlines()):
        line = raw.strip()
        if in_comment:
            if '*/' in line:
                in_comment = False
                if line.split('*/', 1)[1].strip():
                    raise ValueError('unsupported mail preference syntax')
            continue
        if not line or line.startswith('//'):
            continue
        if line.startswith('/*'):
            if '*/' not in line:
                in_comment = True
            elif line.split('*/', 1)[1].strip():
                raise ValueError('unsupported mail preference syntax')
            continue
        match = canonical.fullmatch(line)
        if not match:
            raise ValueError('unsupported mail preference syntax; refusing to alter this profile')
        key, value = json.loads(match[1]), json.loads(match[2])
        if key in MAIL_KEYS:
            if key in managed_keys:
                raise ValueError('duplicate mail font preferences need review')
            managed_keys.add(key)
            records.append((index, key, value))
    if in_comment:
        raise ValueError('unterminated mail preference comment')
    return records


def mail_font_values(text):
    result = {key: None for key in MAIL_KEYS}
    for _, key, value in _mail_records(text):
        result[key] = value
    validate_mail_font_values(result)
    return result


def validate_mail_font_values(values):
    if not isinstance(values, dict) or set(values) != MAIL_KEYS:
        raise ValueError('invalid mail font snapshot')
    for key, value in values.items():
        if value is None:
            continue
        if key == 'font.size.variable.x-western':
            if type(value) is not int or not 1 <= value <= 200:
                raise ValueError('invalid mail font size')
        elif not isinstance(value, str) or len(value) > 300 or any(ord(c) < 32 for c in value):
            raise ValueError('invalid mail font family')


def merge_mail_fonts(text, values):
    validate_mail_font_values(values)
    mail_font_values(text)
    remove = {index for index, _, _ in _mail_records(text)}
    lines = [line for index, line in enumerate(text.splitlines()) if index not in remove]
    for key, value in sorted(values.items()):
        if value is not None:
            lines.append('user_pref(' + json.dumps(key) + ', ' + json.dumps(value, ensure_ascii=False) + ');')
    return '\n'.join(lines) + '\n'
