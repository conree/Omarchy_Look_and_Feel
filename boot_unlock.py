"""Unprivileged boot-artwork requests and root-issued status receipts."""
from pathlib import Path
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess

from transaction import TransactionError

LOGO = Path('/usr/share/plymouth/themes/omarchy/logo.png')
ROOT = Path('/var/lib/omarchy-look-and-feel')


def capability():
    missing = [name for name in ('pkexec', 'mkinitcpio', 'lsinitcpio', 'limine-entry-tool') if not shutil.which(name)]
    return {'available': not missing and LOGO.is_file(),
            'detail': 'Missing: '+', '.join(missing) if missing else
                      'Administrator authentication is required. The boot layout is checked before any change.'}


def preview_background():
    try:
        script = LOGO.with_name('omarchy.script').read_text()
        match = re.search(r'Window.SetBackgroundTopColor\(([0-9.]+),\s*([0-9.]+),\s*([0-9.]+)\)', script)
        if match:
            channels = [float(value) for value in match.groups()]
            if all(0 <= value <= 1 for value in channels):
                return '#' + ''.join(f'{round(value*255):02x}' for value in channels)
    except OSError:
        pass
    return '#1a1b26'


def status():
    result = {'undoAvailable': False, 'recoveryAvailable': False, 'state': 'none',
              'applyAvailable': capability()['available']}
    path = ROOT / f'unlock-status-{os.getuid()}.json'
    try:
        info = path.stat()
        if path.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022 or info.st_size > 65536:
            return result
        saved = json.loads(path.read_text())
        if saved.get('schemaVersion') != 2:
            return result
        result.update(saved)
        if saved.get('state') == 'committed':
            matches = hashlib.sha256(LOGO.read_bytes()).hexdigest() == saved.get('logoSha256')
            result['undoAvailable'] = matches
            result['state'] = 'applied' if matches else 'drifted'
            if not matches:
                result.pop('observedValue', None)
            # The privileged Undo rechecks all boot-file hashes after authentication.
        elif saved.get('state') == 'rolled_back':
            result.pop('observedValue', None)
    except (OSError, ValueError, TypeError):
        pass
    return result


def invoke(operation, request):
    if not capability()['available']:
        raise TransactionError('Boot artwork changes require Plymouth, pkexec, mkinitcpio and Limine')
    # Capture the complete program before authentication. A changed user-writable
    # pathname must not substitute privileged code after the user approves it.
    program = Path(__file__).with_name('boot_unlock_helper.py').read_text()
    proc = subprocess.run(['/usr/bin/pkexec', '/usr/bin/python3', '-I', '-c', program, operation],
                          input=json.dumps(request), capture_output=True, text=True, timeout=2400)
    if proc.returncode:
        detail = proc.stderr.strip() or 'Administrator authentication was cancelled.'
        raise TransactionError(detail[-4500:])
    try:
        result = json.loads(proc.stdout)
    except ValueError as exc:
        raise TransactionError('The boot operation returned an unreadable result; refresh its status') from exc
    if result.get('kind') != 'unlock':
        raise TransactionError('Unexpected boot operation result')
    return result


def apply(design, logo_path, before_design):
    path = Path(logo_path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16*1024*1024:
        raise TransactionError('The selected artwork is unavailable')
    return invoke('apply', {'design': design, 'logo': base64.b64encode(path.read_bytes()).decode(),
                            'expectedLogo': hashlib.sha256(LOGO.read_bytes()).hexdigest(),
                            'beforeDesign': before_design or 'previous artwork'})


def undo():
    return invoke('undo', {})


def recover():
    return invoke('recover', {})
