"""Isolated boot transactions and process supervision; no host boot writes."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import base64
import hashlib
import json
import os
import struct
import subprocess
import sys
import time
import zlib
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import boot_unlock_helper as boot


def png(value):
    def chunk(name, data):
        return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0'+bytes([value,2,3,255])))+chunk(b'IEND',b'')


boot.validate_png(png(1))
for bad in (png(1)[:24], png(1)[:-1], png(1)+b'x', png(1).replace(b'IDAT',b'XXXX')):
    try: boot.validate_png(bad)
    except (RuntimeError, zlib.error): pass
    else: raise AssertionError('Invalid artwork accepted')

with TemporaryDirectory(prefix='laf-child-test-') as tmp:
    marker = Path(tmp)/'child'
    child = f'import time; from pathlib import Path; time.sleep(.3); Path({str(marker)!r}).write_text("late")'
    parent = f'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",{child!r}]); time.sleep(5)'
    try: boot.run([sys.executable,'-c',parent],timeout=.05)
    except subprocess.TimeoutExpired: pass
    else: raise AssertionError('Missing timeout')
    time.sleep(.4)
    assert not marker.exists(), 'A child survived timeout and could race restoration'


# SIGKILL bypasses Python cleanup. The supervisor must keep the boot lock until
# all publication descendants finish, so a second recovery cannot overlap them.
with TemporaryDirectory(prefix='laf-helper-death-') as tmp:
    import fcntl, signal
    root=Path(tmp); lock=root/'lock'; marker=root/'published'; ready=root/'ready'
    publisher=f"import time; from pathlib import Path; Path({str(ready)!r}).touch(); time.sleep(.35); Path({str(marker)!r}).touch()"
    program=f"""import sys,os,fcntl
sys.path.insert(0,{str(Path(boot.__file__).parent)!r})
import boot_unlock_helper as boot
fd=os.open({str(lock)!r},os.O_CREAT|os.O_RDWR,0o600)
fcntl.flock(fd,fcntl.LOCK_EX)
boot.ACTIVE_LOCK_FD=fd
boot.run([sys.executable,'-c',{publisher!r}])
"""
    process=subprocess.Popen([sys.executable,'-B','-c',program])
    deadline=time.monotonic()+5
    while not ready.exists():
        assert time.monotonic()<deadline
        time.sleep(.01)
    process.kill();process.wait()
    with lock.open('r+') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:pass
        else:raise AssertionError('Recovery lock released while publisher survived helper death')
        fcntl.flock(stream,fcntl.LOCK_EX)
        assert marker.exists(), 'Lock released before publication finished'


with TemporaryDirectory(prefix='laf-helper-term-') as tmp:
    root=Path(tmp); marker=root/'published';ready=root/'ready'
    publisher=f"import time; from pathlib import Path; Path({str(ready)!r}).touch(); time.sleep(1); Path({str(marker)!r}).touch()"
    program=f"""import sys,os,io
sys.path.insert(0,{str(Path(boot.__file__).parent)!r})
import boot_unlock_helper as boot
boot.os.geteuid=lambda:0
os.environ['PKEXEC_UID']='1000'
sys.argv=['helper','apply']
sys.stdin=io.TextIOWrapper(io.BytesIO(b'{{}}'))
boot.execute=lambda *args:boot.run([sys.executable,'-c',{publisher!r}])
try:boot.main()
except boot.BootInterrupted:sys.exit(42)
"""
    process=subprocess.Popen([sys.executable,'-B','-c',program])
    deadline=time.monotonic()+5
    while not ready.exists():
        assert time.monotonic()<deadline
        time.sleep(.01)
    process.terminate()
    assert process.wait(timeout=.8)==42, 'SIGTERM must interrupt subprocess waiting'
    assert not marker.exists()


for failure in ('none','build','publish-second','stale-second','stale-checksum','drift-undo','recover'):
    with TemporaryDirectory(prefix='laf-boot-fixture-') as tmp, ExitStack() as stack:
        root=Path(tmp); state=root/'state'; state.mkdir()
        images=root/'EFI/Linux'; images.mkdir(parents=True)
        logo=root/'logo.png'; logo.write_bytes(png(1))
        conf=root/'limine.conf'; conf.write_text('path: boot():/EFI/Linux/omarchy_linux.efi#111\npath: boot():/EFI/Linux/omarchy_linux-lts.efi#222\ncmdline: unchanged\n')
        oldconf=root/'limine.conf.old' # absent baseline must remain absent after Undo
        targets=[]
        for name in ('linux','linux-lts'):
            path=images/f'omarchy_{name}.efi'; path.write_bytes(b'UKI'+png(1))
            targets.append((name,'1.0',path,{'.linux':b'kernel','.uname':b'1.0'}))
        def configure():
            conf.write_text(''.join('path: boot():/EFI/Linux/'+row[2].name+'#'+hashlib.blake2b(row[2].read_bytes()).hexdigest()+'\n' for row in targets)+'cmdline: unchanged\n')
        configure()
        paths=[logo,conf,oldconf,*(row[2] for row in targets)]
        baseline={str(p):p.read_bytes() if p.exists() else None for p in paths}
        for key,value in [('ROOT',state),('LOGO',logo),('CONF',conf),('CONF_BACKUP',oldconf),('BOOT',images)]:
            stack.enter_context(patch.object(boot,key,value))
        stack.enter_context(patch.object(boot,'trusted',side_effect=lambda p,directory=False:Path(p)))
        from contextlib import nullcontext
        stack.enter_context(patch.object(boot,'boot_lock',nullcontext))
        stack.enter_context(patch.object(boot,'targets',return_value=targets))
        stack.enter_context(patch.object(boot,'assets',side_effect=lambda:{str(logo):boot.digest(logo)}))
        stack.enter_context(patch.object(boot,'pe_sections',return_value={'.linux':b'kernel','.uname':b'1.0'}))
        def verify(files,expected):
            for path in files:
                if hashlib.sha256(path.read_bytes()[3:]).hexdigest()!=expected[str(logo)]:
                    raise RuntimeError('Stale embedded artwork')
        stack.enter_context(patch.object(boot,'verify_images',side_effect=verify))
        publishes=[]
        def run(args,**kwargs):
            if args[0].endswith('mkinitcpio'):
                assert '--nopost' in args and '--no-cmdline' in args
                if failure=='build': raise RuntimeError('Injected build failure')
                Path(args[-1]).write_bytes(b'UKI'+logo.read_bytes())
            else:
                name=args[2]; staged=Path(args[3]); publishes.append(name)
                if failure=='publish-second' and len(publishes)==2: raise RuntimeError('Injected partial publication')
                (images/f'omarchy_{name}.efi').write_bytes(staged.read_bytes())
                oldconf.write_bytes(baseline[str(conf)])
                if failure != 'stale-checksum': configure()
            return b''
        stack.enter_context(patch.object(boot,'run',side_effect=run))
        request=dict(design='new',beforeDesign='old',logo=base64.b64encode(png(2)).decode(),expectedLogo=boot.digest(logo))
        if failure=='stale-second': targets[1][2].write_bytes(b'UKI'+png(9))
        try: result=boot.execute('apply',request,1000)
        except RuntimeError:
            assert failure in ('build','publish-second','stale-second','stale-checksum')
            if failure!='stale-second': assert {str(p):p.read_bytes() if p.exists() else None for p in paths}==baseline
            else: assert not publishes and logo.read_bytes()==png(1)
            continue
        assert result['state']=='committed' and len(publishes)==2
        if failure=='drift-undo':
            targets[0][2].write_bytes(b'new system kernel')
            after={str(p):p.read_bytes() if p.exists() else None for p in paths}
            try:boot.execute('undo',{},1000)
            except RuntimeError as e:assert 'changed since Apply' in str(e)
            else:raise AssertionError('Undo overwrote a newer kernel')
            assert {str(p):p.read_bytes() if p.exists() else None for p in paths}==after
        else:
            operation='undo'
            if failure=='recover':
                journal=next((state/'unlock-transactions').glob('*/journal.json'))
                data=json.loads(journal.read_text());data['state']='applying';journal.write_text(json.dumps(data));operation='recover'
            restored=boot.execute(operation,{},1000)
            assert restored['restored']=='old'
            assert {str(p):p.read_bytes() if p.exists() else None for p in paths}==baseline
print('Boot transactions: valid/malformed PNG, descendant timeout cleanup, staged builds, partial publication rollback, stale second image, exact Undo, intervening kernel protection and interrupted recovery passed.')
