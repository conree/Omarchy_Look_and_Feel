"""Native Gecko lock interoperability, confined to an isolated HOME."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-stale-mail-') as directory:
        env = dict(os.environ, HOME=directory, XDG_CONFIG_HOME=directory + '/config',
                   XDG_STATE_HOME=directory + '/state', PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True)
    raise SystemExit()

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app_font_actions as app

profile = Path.home() / 'mail-profile'
profile.mkdir()
prefs = profile / 'prefs.js'
prefs.write_text('user_pref("msgcompose.font_face", "Original");\n')
lock = profile / 'lock'
child = subprocess.Popen(['true'])
pid = child.pid
child.wait()
lock.symlink_to(f'127.0.0.1:+{pid}')
assert app.stale_local_mail_lock(lock) is not None
with app.lock_mail_paths([prefs]):
    assert not lock.is_symlink()
    probe = subprocess.run([sys.executable, '-c', '''import fcntl,sys
f=open(sys.argv[1],'r+')
try: fcntl.lockf(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError: sys.exit(7)
''', str(profile / '.parentlock')])
    assert probe.returncode == 7
assert prefs.read_text() == 'user_pref("msgcompose.font_face", "Original");\n'

for target in (f'127.0.0.1:+{os.getpid()}', f'203.0.113.99:+{pid}', 'unknown-owner'):
    lock.symlink_to(target)
    assert app.stale_local_mail_lock(lock) is None
    try:
        with app.lock_mail_paths([prefs]):
            raise AssertionError('unsafe lock was acquired')
    except RuntimeError:
        pass
    assert lock.is_symlink()
    lock.unlink()
print('Native stale mail lock cleanup passed; live, nonlocal and unknown locks preserved; native lock excludes another process.')
