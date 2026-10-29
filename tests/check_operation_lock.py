"""Exercise lock contention with another process and an isolated state directory."""
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import io
import os
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))

if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-lock-') as home:
        env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=home + '/config',
                   XDG_STATE_HOME=home + '/state', PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', __file__, 'test'], env=env, check=True)
    raise SystemExit()

import appearance_policy as policy
import controller

if sys.argv[1] == 'holder':
    with policy.operation_lock():
        print('locked', flush=True)
        sys.stdin.readline()
    raise SystemExit()

def holder():
    child = subprocess.Popen([sys.executable, '-B', __file__, 'holder'],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    assert child.stdout.readline().strip() == 'locked'
    return child

child = holder()
try:
    start = time.monotonic()
    try:
        with policy.operation_lock():
            raise AssertionError('automatic operation acquired a held lock')
    except policy.OperationBusy:
        assert time.monotonic() - start < 0.5
    timer = threading.Timer(0.2, lambda: (child.stdin.write('\n'), child.stdin.flush()))
    timer.start()
    start = time.monotonic()
    with policy.operation_lock(timeout=2):
        assert time.monotonic() - start >= 0.1
    timer.join()
    assert child.wait(timeout=2) == 0
finally:
    if child.poll() is None:
        child.stdin.write('\n'); child.stdin.flush(); child.wait(timeout=2)

child = holder()
try:
    start = time.monotonic()
    try:
        with policy.operation_lock(timeout=0.25):
            raise AssertionError('foreground operation acquired a held lock')
    except policy.OperationBusy as exc:
        elapsed = time.monotonic() - start
        assert 0.2 <= elapsed < 1.5 and 'retry' in str(exc)
finally:
    child.stdin.write('\n'); child.stdin.flush(); child.wait(timeout=2)

# The actual controller requests a bounded wait only for foreground operations.
seen = []
def unavailable(*, timeout):
    seen.append(timeout)
    raise policy.OperationBusy('busy')
with patch.object(policy, 'operation_lock', side_effect=unavailable), \
     redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
    assert controller.main(['reconcile']) == 0
    assert controller.main(['apply-opacity', '50']) == 1
    assert controller.main(['rollback-appearance', 'theme']) == 1
assert seen == [0, 10, 10]
print('Cross-process lock: immediate background skip, foreground wait and bounded timeout passed.')
