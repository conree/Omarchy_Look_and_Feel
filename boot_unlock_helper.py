#!/usr/bin/env python3
"""Privileged, explicit Plymouth-artwork transactions for Omarchy UKI systems.

Invoked with Python -I through pkexec. No user modules or input paths are loaded.
Boot images are built and inspected before publication; Undo restores saved bytes.
"""
from contextlib import contextmanager
from pathlib import Path
import base64
import configparser
import ctypes
import fcntl
import hashlib
import json
import os
import re
import shutil
import shlex
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import uuid
import zlib

ROOT = Path('/var/lib/omarchy-look-and-feel')
THEME = Path('/usr/share/plymouth/themes/omarchy')
LOGO = THEME / 'logo.png'
BOOT = Path('/boot/EFI/Linux')
CONF = Path('/boot/limine.conf')
CONF_BACKUP = Path('/boot/limine.conf.old')
PLYMOUTH_CONF = Path('/etc/plymouth/plymouthd.conf')
MAX_LOGO = 16 * 1024 * 1024
ACTIVE_LOCK_FD = None
# This supervisor retains the shared lock even if the authenticated helper is
# SIGKILLed. It also adopts and waits for descendants of shell launchers.
SUPERVISOR = """
import ctypes, json, os, subprocess, sys
if ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) != 0: sys.exit(125)
fd = int(sys.argv[1])
child = subprocess.Popen(json.loads(sys.argv[2]), pass_fds=(fd,))
code = child.wait()
while True:
    try: os.waitpid(-1, 0)
    except ChildProcessError: break
sys.exit(code)
"""


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def trusted(path, directory=False):
    path = Path(path)
    if path.resolve(strict=True) != path or path.is_symlink():
        raise RuntimeError(f'Unsupported linked path: {path}')
    for item in (path, *path.parents):
        info = item.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise RuntimeError(f'Expected a root-owned, protected path: {item}')
    if not (path.is_dir() if directory else path.is_file()):
        raise RuntimeError(f'Unexpected file type: {path}')
    return path


def atomic(path, data, mode=0o600):
    trusted(path.parent, True)
    if path.exists() or path.is_symlink():
        trusted(path)
    fd, temporary = tempfile.mkstemp(prefix='.laf-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_json(path, data, mode=0o600):
    atomic(path, (json.dumps(data, sort_keys=True, indent=2) + '\n').encode(), mode)


def sync_directory(path):
    fd = os.open(path, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def run(args, **kwargs):
    # Adopt orphaned descendants so timeout cannot race a still-running publisher.
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError('Cannot establish safe child-process supervision')
    timeout = kwargs.pop('timeout', 900)
    inherited = () if ACTIVE_LOCK_FD is None else (ACTIVE_LOCK_FD,)
    command = args if ACTIVE_LOCK_FD is None else [sys.executable, '-I', '-c', SUPERVISOR, str(ACTIVE_LOCK_FD), json.dumps(args)]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True, pass_fds=inherited, **kwargs)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        while True:
            try:
                os.waitpid(-process.pid, 0)
            except ChildProcessError:
                break
        raise
    if process.returncode:
        detail = (stderr + stdout)[-4000:].decode(errors='replace')
        raise RuntimeError(f'{Path(args[0]).name} failed ({process.returncode}): {detail}')
    return stdout


def validate_png(data):
    if not 33 <= len(data) <= MAX_LOGO or data[:8] != b'\x89PNG\r\n\x1a\n':
        raise RuntimeError('Expected bounded PNG artwork')
    offset, chunks, compressed, palette = 8, [], bytearray(), False
    width = height = stride = 0
    while offset < len(data):
        if offset + 12 > len(data):
            raise RuntimeError('Truncated PNG chunk')
        size = struct.unpack_from('>I', data, offset)[0]
        kind = data[offset+4:offset+8]
        end = offset+8+size
        if end+4 > len(data) or zlib.crc32(data[offset+4:end]) != struct.unpack_from('>I', data, end)[0]:
            raise RuntimeError('Invalid PNG chunk or checksum')
        payload = data[offset+8:end]
        if not chunks and kind != b'IHDR':
            raise RuntimeError('PNG header is missing')
        if kind == b'IHDR':
            if chunks or size != 13:
                raise RuntimeError('Invalid PNG header')
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            depths = {0: (1,2,4,8,16), 2: (8,16), 3: (1,2,4,8), 4: (8,16), 6: (8,16)}
            if not (1 <= width <= 8192 and 1 <= height <= 8192 and depth in depths.get(color, ())
                    and compression == filtering == interlace == 0):
                raise RuntimeError('Unsupported PNG format or dimensions')
            stride = (width * {0:1, 2:3, 3:1, 4:2, 6:4}[color] * depth + 7)//8 + 1
            if stride*height > 64*1024*1024:
                raise RuntimeError('Decoded artwork is too large')
        elif kind == b'PLTE':
            if palette or not size or size % 3 or size > 768 or b'IDAT' in chunks:
                raise RuntimeError('Invalid PNG palette')
            palette = True
        elif kind == b'IDAT':
            if b'IDAT' in chunks and chunks[-1] != b'IDAT':
                raise RuntimeError('Non-contiguous PNG image data')
            compressed.extend(payload)
        elif kind == b'IEND':
            if size or end+4 != len(data) or not compressed:
                raise RuntimeError('Invalid PNG ending')
        elif not kind[0] & 32:
            raise RuntimeError('Unsupported critical PNG chunk')
        chunks.append(kind)
        offset = end+4
    if not chunks or chunks[-1] != b'IEND' or (color == 3 and not palette):
        raise RuntimeError('Incomplete PNG')
    decoder = zlib.decompressobj()
    pixels = decoder.decompress(compressed, stride*height+1)
    if not decoder.eof or decoder.unused_data or len(pixels) != stride*height or any(pixels[i] > 4 for i in range(0,len(pixels),stride)):
        raise RuntimeError('Invalid PNG image data')


def pe_sections(path):
    """Read PE section data and signing metadata without executing the image."""
    data = path.read_bytes()
    if data[:2] != b'MZ' or len(data) < 64:
        raise RuntimeError('Expected a PE unified kernel image')
    start = struct.unpack_from('<I', data, 60)[0]
    if data[start:start+4] != b'PE\0\0':
        raise RuntimeError('Invalid PE header')
    count = struct.unpack_from('<H', data, start+6)[0]
    optional_size = struct.unpack_from('<H', data, start+20)[0]
    optional = start+24
    if struct.unpack_from('<H', data, optional)[0] != 0x20b:
        raise RuntimeError('Only PE32+ UKIs are supported')
    # The certificate table is data directory 4. Signed builds need a separate
    # signing-preservation workflow, so refuse them before any write.
    cert = struct.unpack_from('<II', data, optional+112+4*8)
    if cert != (0, 0):
        raise RuntimeError('Signed boot images are not supported by artwork Apply')
    sections = {}
    table = optional + optional_size
    for i in range(count):
        offset = table+i*40
        name = data[offset:offset+8].rstrip(b'\0').decode('ascii')
        virtual, _, size, pointer = struct.unpack_from('<IIII', data, offset+8)
        if pointer+size > len(data):
            raise RuntimeError('Truncated PE section')
        sections[name] = data[pointer:pointer+min(size, virtual)]
    if not {'.linux', '.initrd', '.osrel', '.uname'} <= sections.keys():
        raise RuntimeError('Required UKI sections are missing')
    return sections


def targets():
    trusted(CONF)
    config = {}
    paths = [*sorted(Path('/usr/share/limine-entry-tool.d').glob('*.conf')),
             Path('/etc/limine-entry-tool.conf'),
             *sorted(Path('/etc/limine-entry-tool.d').glob('*.conf')),
             Path('/etc/default/limine')]
    relevant = {'ESP_PATH', 'CUSTOM_UKI_NAME', 'ENABLE_UKI', 'ENABLE_ENROLL_LIMINE_CONFIG',
                'MKINITCPIO_UKI_OPTIONS', 'MKINITCPIO_FALLBACK'}
    for path in paths:
        if not path.exists():
            continue
        for line in trusted(path).read_text().splitlines():
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            key, sep, raw = line.partition('=')
            if sep and key.strip() in relevant:
                values = shlex.split(raw, comments=True)
                if len(values) != 1 or any(c in values[0] for c in '$`\\'):
                    raise RuntimeError('Unsupported dynamic Limine option')
                config[key.strip()] = values[0]
    for key, value in (('ESP_PATH', '/boot'), ('CUSTOM_UKI_NAME', 'omarchy'), ('ENABLE_UKI', 'yes')):
        if config.get(key) != value:
            raise RuntimeError('Artwork Apply requires the standard Omarchy UKI layout')
    if config.get('ENABLE_ENROLL_LIMINE_CONFIG', 'no') not in ('no', ''):
        raise RuntimeError('Enrolled boot configuration is not supported by artwork Apply')
    if config.get('MKINITCPIO_UKI_OPTIONS') or config.get('MKINITCPIO_FALLBACK', 'no') not in ('no', ''):
        raise RuntimeError('Custom UKI build options require a dedicated adapter')
    # Read only the current OS SecureBoot variable, never other OS disks/entries.
    secure = Path('/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c')
    if secure.exists() and secure.read_bytes()[4:5] != b'\0':
        raise RuntimeError('Secure Boot artwork changes require signing support')
    found = []
    for module in sorted(Path('/usr/lib/modules').iterdir()):
        pkgbase = module / 'pkgbase'
        if not pkgbase.is_file():
            continue
        name = trusted(pkgbase).read_text().strip()
        if not re.fullmatch(r'linux(?:-[a-z0-9-]+)?', name):
            raise RuntimeError('Unsupported kernel package')
        image = trusted(BOOT / f'omarchy_{name}.efi')
        sections = pe_sections(image)
        if sections.keys() - {'.text', '.rodata', '.data', '.reloc', '.sbat', '.sdmagic', '.osrel', '.cmdline', '.uname', '.linux', '.initrd'}:
            raise RuntimeError('Custom UKI sections require a dedicated adapter')
        if sections['.uname'].rstrip(b'\0\n').decode() != module.name:
            raise RuntimeError('Installed kernel and boot image versions differ; finish the system update first')
        found.append((name, module.name, image, sections))
    if not found or len({row[0] for row in found}) != len(found):
        raise RuntimeError('Current Omarchy boot images could not be identified uniquely')
    return found


def verify_boot_config(images):
    text = trusted(CONF).read_text()
    for image in images:
        relative = str(image.relative_to(CONF.parent))
        references = [line.strip() for line in text.splitlines() if 'path:' in line and '/'+relative in line]
        with image.open('rb') as stream:
            checksum = hashlib.file_digest(stream, 'blake2b').hexdigest()
        expected = 'path: boot():/' + relative + '#' + checksum
        if not references or any(line != expected for line in references):
            raise RuntimeError(f'Bootloader checksum verification failed: {image.name}')


def assets():
    config = configparser.ConfigParser()
    config.read(trusted(PLYMOUTH_CONF))
    if config.get('Daemon', 'Theme', fallback='') != 'omarchy':
        raise RuntimeError('The active Plymouth theme must already be Omarchy')
    definition = configparser.ConfigParser()
    definition.read(trusted(THEME/'omarchy.plymouth'))
    if (definition.get('Plymouth Theme', 'ModuleName', fallback='') != 'script'
        or definition.get('script', 'ImageDir', fallback='') != str(THEME)
        or definition.get('script', 'ScriptFile', fallback='') != str(THEME/'omarchy.script')):
        raise RuntimeError('Unsupported Plymouth theme definition')
    files = [PLYMOUTH_CONF, THEME/'omarchy.plymouth', THEME/'omarchy.script']
    for image in sorted(THEME.rglob('*.png')):
        if image.name != 'preview-unlock.png':
            files.append(trusted(image))
    return {str(path): digest(trusted(path)) for path in files}


def verify_images(images, expected):
    for image in images:
        with tempfile.TemporaryDirectory(prefix='verify-', dir=ROOT) as temporary:
            run(['/usr/bin/lsinitcpio', '-x', str(image)], cwd=temporary)
            for name, value in expected.items():
                extracted = Path(temporary) / name.lstrip('/')
                if not extracted.is_file() or extracted.is_symlink() or digest(extracted) != value:
                    raise RuntimeError(f'Boot image verification failed: {image.name}: {name}')


def hashes(paths):
    return {str(path): digest(trusted(path)) if path.exists() else None for path in paths}


def receipt(uid, record, **extra):
    value = {key: record[key] for key in ('id', 'state', 'beforeDesign', 'afterDesign')}
    value.update(kind='unlock', schemaVersion=2, **extra)
    write_json(ROOT / f'unlock-status-{uid}.json', value, 0o644)
    return value


def restore(directory, record):
    # All restore destinations are derived from a root-owned journal, with the
    # same fixed allowlist used on creation. No caller-supplied paths are accepted.
    for name, info in record['files'].items():
        path = Path(name)
        if path not in (LOGO, CONF, CONF_BACKUP) and not (path.parent == BOOT and re.fullmatch(r'omarchy_linux(?:-[a-z0-9-]+)?\.efi', path.name)):
            raise RuntimeError('Invalid saved restore destination')
        if info['backup'] is None:
            continue
        saved = trusted(directory / info['backup'])
        if digest(saved) != info['sha256']:
            raise RuntimeError('Saved boot backup failed its integrity check')
    for name, info in record['files'].items():
        if info['backup'] is None:
            if Path(name).exists():
                trusted(Path(name)).unlink()
                sync_directory(Path(name).parent)
        else:
            atomic(Path(name), (directory / info['backup']).read_bytes(), info['mode'])
    if hashes(map(Path, record['beforeHashes'])) != record['beforeHashes']:
        raise RuntimeError('Exact boot restoration failed')
    verify_images([Path(name) for name in record['beforeHashes'] if name.endswith('.efi')], record['beforeAssets'])
    verify_boot_config([Path(name) for name in record['beforeHashes'] if name.endswith('.efi')])
    record['state'] = 'rolled_back'
    write_json(directory/'journal.json', record)


@contextmanager
def boot_lock():
    global ACTIVE_LOCK_FD
    path = Path('/run/lock/boot-partition.lock')
    trusted(path.parent, True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        trusted(path)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ACTIVE_LOCK_FD = fd
        yield
    finally:
        ACTIVE_LOCK_FD = None
        os.close(fd)


def execute(operation, request, uid):
    ROOT.mkdir(mode=0o755, exist_ok=True)
    trusted(ROOT, True)
    ROOT.chmod(0o755)
    sync_directory(ROOT.parent)
    journal_root = ROOT / 'unlock-transactions'
    journal_root.mkdir(mode=0o700, exist_ok=True)
    trusted(journal_root, True)
    sync_directory(ROOT)
    with boot_lock():
        records = []
        for path in journal_root.glob('*/journal.json'):
            data = json.loads(trusted(path).read_text())
            records.append((path.parent, data))
        records.sort(key=lambda row: row[1]['createdNs'])
        pending = [row for row in records if row[1]['state'] in ('applying', 'restoring', 'recovery_required')]
        if pending:
            if operation != 'recover':
                raise RuntimeError('An interrupted boot change needs Recover boot unlock first')
            directory, record = pending[-1]
            if record['uid'] != uid:
                raise RuntimeError('Only the user who started this boot change may recover it')
            # Preserve any intervening change after interruption. We know each
            # published destination hash before writing it, including each UKI.
            for name, before in record['beforeHashes'].items():
                allowed = {before}
                for field in ('afterHashes', 'plannedHashes'):
                    if name in record.get(field, {}):
                        allowed.add(record[field][name])
                if hashes([Path(name)])[name] not in allowed:
                    raise RuntimeError('Boot files changed independently; preserving them for manual recovery')
            try:
                restore(directory, record)
            except BaseException:
                record['state'] = 'recovery_required'
                write_json(directory/'journal.json', record)
                receipt(uid, record, undoAvailable=False, recoveryAvailable=True)
                raise
            return receipt(uid, record, rolledBack=record['id'], restored=record['beforeDesign'], readback=record['beforeDesign'], undoAvailable=False)
        if operation == 'recover':
            raise RuntimeError('No interrupted boot change needs recovery')
        if operation == 'undo':
            previous = [row for row in records if row[1]['uid'] == uid and row[1]['state'] == 'committed']
            if not previous:
                raise RuntimeError('No verified boot unlock change is available to undo')
            directory, record = previous[-1]
            if hashes(map(Path, record['afterHashes'])) != record['afterHashes'] or assets() != record['afterAssets']:
                raise RuntimeError('Boot files changed since Apply; preserving the intervening changes')
            record['state'] = 'restoring'
            write_json(directory/'journal.json', record)
            receipt(uid, record, undoAvailable=False, recoveryAvailable=True)
            try:
                restore(directory, record)
            except BaseException:
                record['state'] = 'recovery_required'
                write_json(directory/'journal.json', record)
                receipt(uid, record, undoAvailable=False, recoveryAvailable=True)
                raise
            return receipt(uid, record, rolledBack=record['id'], restored=record['beforeDesign'], readback=record['beforeDesign'], undoAvailable=False)
        if operation != 'apply':
            raise RuntimeError('Unknown boot operation')
        design = request.get('design', '')
        if not isinstance(design, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,100}', design):
            raise RuntimeError('Invalid design name')
        logo = base64.b64decode(request.get('logo', ''), validate=True)
        validate_png(logo)
        boot = targets()
        before_assets = assets()
        verify_boot_config([row[2] for row in boot])
        verify_images([row[2] for row in boot], before_assets)
        paths = [LOGO, CONF, CONF_BACKUP, *(row[2] for row in boot)]
        before = hashes(paths)
        if request.get('expectedLogo') != before[str(LOGO)]:
            raise RuntimeError('The boot artwork changed while authentication was pending; refresh and retry')
        before_design = request.get('beforeDesign', 'previous artwork')
        if not isinstance(before_design, str) or len(before_design) > 120:
            raise RuntimeError('Invalid previous design label')
        if hashlib.sha256(logo).hexdigest() == before[str(LOGO)]:
            return dict(state='already-current', kind='unlock', after=design, readback=design, verifiedImages=len(boot))
        directory = journal_root / uuid.uuid4().hex
        directory.mkdir(mode=0o700)
        sync_directory(journal_root)
        record = dict(id=directory.name, uid=uid, createdNs=__import__('time').time_ns(), state='prepared',
                      beforeDesign=before_design, afterDesign=design, beforeHashes=before,
                      beforeAssets=before_assets, files={}, plannedHashes={str(LOGO): hashlib.sha256(logo).hexdigest()})
        for i, path in enumerate(paths):
            if not path.exists():
                record['files'][str(path)] = dict(backup=None, sha256=None, mode=None)
                continue
            data = path.read_bytes()
            atomic(directory / str(i), data)
            record['files'][str(path)] = dict(backup=str(i), sha256=before[str(path)], mode=stat.S_IMODE(path.stat().st_mode))
        write_json(directory/'journal.json', record)
        try:
            record['state'] = 'applying'
            write_json(directory/'journal.json', record)
            receipt(uid, record, recoveryAvailable=True, undoAvailable=False)
            atomic(LOGO, logo, record['files'][str(LOGO)]['mode'])
            intended = assets()
            staged = []
            for name, version, image, sections in boot:
                output = directory / (name + '.efi')
                cmdline = sections.get('.cmdline', b'').rstrip(b'\0')
                args = ['/usr/bin/mkinitcpio', '--nopost', '--kernel', version]
                if cmdline:
                    command_file = directory / (name+'.cmdline')
                    atomic(command_file, cmdline)
                    args += ['--cmdline', str(command_file)]
                else:
                    args += ['--no-cmdline']
                run(args + ['--uki', str(output)])
                built = pe_sections(output)
                for key in ('.linux', '.cmdline', '.osrel', '.uname', '.sbat'):
                    if built.get(key, b'').rstrip(b'\0') != sections.get(key, b'').rstrip(b'\0'):
                        raise RuntimeError(f'The rebuild changed {key}; refusing to publish')
                verify_images([output], intended)
                record['plannedHashes'][str(image)] = digest(output)
                staged.append((name, version, output))
            record['plannedHashes'][str(CONF_BACKUP)] = record['beforeHashes'][str(CONF)]
            write_json(directory/'journal.json', record)
            # The upstream tool updates only these current OS entries. Hooks are
            # deliberately omitted, including other-bootloader discovery.
            for name, version, output in staged:
                run(['/usr/bin/limine-entry-tool', '--add-uki', name, str(output), '--comment',
                     'Kernel version: '+version, '--no-mutex', '--no-hooks'])
                record['plannedHashes'][str(CONF)] = digest(CONF)
                write_json(directory/'journal.json', record)
            verify_images([row[2] for row in boot], intended)
            verify_boot_config([row[2] for row in boot])
            original_conf = (directory / record['files'][str(CONF)]['backup']).read_text()
            def stable_config(text):
                for _, _, image, _ in boot:
                    text = re.sub(re.escape(str(image.relative_to(CONF.parent))) + r'#[a-fA-F0-9]+', str(image.relative_to(CONF.parent)), text)
                return text
            if stable_config(CONF.read_text()) != stable_config(original_conf):
                raise RuntimeError('The boot update changed settings beyond the image checksums')
            for path in paths:
                if not path.exists():
                    continue
                with path.open('rb') as stream:
                    os.fsync(stream.fileno())
                sync_directory(path.parent)
            record.update(state='committed', afterHashes=hashes(paths), afterAssets=intended)
            write_json(directory/'journal.json', record)
            return receipt(uid, record, transaction=record['id'], before=before_design, after=design,
                           readback=design, observedValue=design, previousValue=before_design,
                           logoSha256=intended[str(LOGO)], verifiedImages=len(boot), undoAvailable=True)
        except BaseException as exc:
            try:
                restore(directory, record)
                receipt(uid, record, undoAvailable=False, recoveryAvailable=False, detail=str(exc)[-1500:])
            except BaseException as recovery:
                record['state'] = 'recovery_required'
                write_json(directory/'journal.json', record)
                receipt(uid, record, undoAvailable=False, recoveryAvailable=True, detail=str(recovery)[-1500:])
                raise RuntimeError(f'Apply failed ({exc}); saved boot files need recovery: {recovery}') from exc
            raise RuntimeError(f'Apply failed; previous boot files were restored exactly: {exc}') from exc


class BootInterrupted(RuntimeError):
    pass


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Administrator authentication is required')
    uid = int(os.environ.get('PKEXEC_UID', '-1'))
    if uid <= 0:
        raise RuntimeError('Run this helper through pkexec as a desktop user')
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', LANG='C.UTF-8', HOME='/root')
    os.umask(0o077)
    def interrupted(signum, frame):
        raise BootInterrupted('Boot operation interrupted')
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, interrupted)
    raw = sys.stdin.buffer.read(MAX_LOGO*2+1)
    if len(raw) > MAX_LOGO*2:
        raise RuntimeError('Oversized artwork request')
    request = json.loads(raw)
    if not isinstance(request, dict) or len(sys.argv) != 2:
        raise RuntimeError('Invalid boot operation')
    result = execute(sys.argv[1], request, uid)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
