"""Per-terminal Hyprland blur, independent of opacity and global blur strength."""
from pathlib import Path
import subprocess
import transaction as tx

LABEL = 'Terminal blur settings'
BEGIN = '-- BEGIN Look and Feel terminal blur\n'
END = '-- END Look and Feel terminal blur\n'


def block(enabled):
    if type(enabled) is not bool:
        raise ValueError('Terminal blur must be On or Off')
    return BEGIN + 'o.window({ tag = "terminal" }, { no_blur = ' + ('false' if enabled else 'true') + ' })\n' + END


def decode(raw):
    text = raw.decode()
    value = None
    if BEGIN in text or END in text:
        if text.count(BEGIN) != 1 or text.count(END) != 1:
            raise ValueError('Malformed terminal blur block')
        a, b = text.index(BEGIN), text.index(END) + len(END)
        if b <= a:
            raise ValueError('Malformed terminal blur block')
        value = text[a:b]
        if value not in (block(True), block(False)):
            raise ValueError('Terminal blur block changed independently')
    return {'_text': text, 'blur': value}


def encode(data):
    text, wanted = data.get('_text', ''), data.get('blur')
    old = decode(text.encode())['blur']
    if wanted is not None and wanted not in (block(True), block(False)):
        raise ValueError('Invalid terminal blur block')
    if old == wanted:
        return text.encode()
    if old is not None:
        return text.replace(old, wanted or '', 1).encode()
    return (text + ('\n' if text and not text.endswith('\n') else '') + (wanted or '')).encode()


def _command(*args):
    result = subprocess.run(['hyprctl', *args], capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Hyprland control failed')
    return result.stdout.strip()


def reload():
    _command('reload')
    errors = _command('configerrors')
    if errors:
        raise RuntimeError('Hyprland configuration error: ' + errors)


def refresh(*, changed=False):
    pending = tx._ensure_home_path(tx.transactions_path().parent / 'blur-reload-pending')
    if changed:
        tx._atomic_write(pending, b'pending\n', 0o600)
    if pending.exists():
        reload()
        pending.unlink()


def apply(enabled, *, automatic=False):
    import appearance_policy as policy
    wanted = block(enabled)
    if enabled and 'bool: true' not in _command('getoption', 'decoration:blur:enabled'):
        raise RuntimeError('Enable compositor blur before choosing terminal Blur On')
    path = tx._ensure_home_path(Path.home() / tx.FILE_TARGETS['terminal-blur-config'], allow_missing_parents=True)
    data = decode(path.read_bytes() if path.exists() else b'')
    data['blur'] = wanted
    targets = {'terminal-blur-config': encode(data)}
    parent = policy.latest(LABEL) if automatic else None
    if automatic and parent is None:
        raise tx.TransactionError('Saved blur has no original Apply transaction')
    if automatic:
        targets = policy.changed_targets(targets)
    else:
        targets['appearance-policy'] = policy.update('blur', enabled)
    identity = tx.apply_file_targets(targets, label='Automatic blur reconciliation' if automatic else LABEL,
                                     parent_transaction=parent[1].name if parent else None,
                                     owned_fields={'terminal-blur-config': {'blur'}, 'appearance-policy': {'blur'}}) if targets else None
    refresh(changed=bool(identity))
    name = 'On' if enabled else 'Off'
    return {'kind': 'blur', 'state': 'committed' if identity else 'already-current',
            'transaction': identity, 'after': name, 'readback': name,
            'blurEnabled': enabled, 'pendingApplications': [], 'undoAvailable': True}


def status():
    import appearance_policy as policy
    return {'undoAvailable': policy.latest(LABEL) is not None, 'savedBlur': policy.read().get('blur')}


def undo():
    import appearance_policy as policy
    identity = tx.rollback_latest(label=LABEL)
    refresh(changed=True)
    return {'kind': 'blur', 'rolledBack': identity, 'savedBlur': policy.read().get('blur'), 'pendingApplications': []}
