"""Native Quickshell lifecycle and real command resource regressions."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import time

SOURCE = Path(__file__).resolve().parents[1]
SUPERVISOR = SOURCE / "process_supervisor.py"


def supervised(code, seconds=.4, budget=1024):
    return subprocess.run([sys.executable, "-B", str(SUPERVISOR), str(seconds), str(budget),
                           sys.executable, "-c", code], capture_output=True, timeout=4)


result = supervised("import sys; print('out'); print('err', file=sys.stderr)")
assert (result.returncode, result.stdout, result.stderr) == (0, b"out\n", b"err\n"), result
for code, message in [
    ("import time; time.sleep(10)", b"time limit"),
    ("print('x'*2000)", b"output limit"),
    ("import sys; sys.stderr.write('x'*2000)", b"output limit"),
    ("import os,time\nwhile True: os.write(1,b'x'); time.sleep(.01)", b"time limit"),
]:
    result = supervised(code)
    assert result.returncode == 125 and not result.stdout and message in result.stderr, result
with tempfile.TemporaryDirectory(prefix="laf-process-regression-") as temporary:
    fixture = Path(temporary)
    marker = fixture / "escaped"
    code = ("import os,time; from pathlib import Path; child=os.fork(); "
            "time.sleep(.6) if child == 0 else None; "
            f"Path({str(marker)!r}).write_text('escaped') if child == 0 else None")
    result = supervised(code, seconds=2)
    assert result.returncode == 0, result
    time.sleep(.8)
    assert not marker.exists(), "Grandchild survived direct parent exit"
    for name in ("BoundedProcess.qml", "process_supervisor.py"):
        shutil.copyfile(SOURCE/name, fixture/name)
    runtime = fixture / "runtime"
    runtime.mkdir(mode=0o700)
    (fixture / "shell.qml").write_text('''import QtQuick
import Quickshell
ShellRoot {
  property int step: 0
  BoundedProcess {
    id: job
    onCompleted: {
      console.log("RESULT", step, resultExitCode, JSON.stringify(outputText), JSON.stringify(errorText))
      if (step === 0 && (resultExitCode !== 0 || outputText.trim() !== "hello")) Qt.exit(10)
      if (step > 0 && resultExitCode !== 125) Qt.exit(11)
      step++
      if (step === 5) { console.log("ALL_PROCESS_CASES_PASSED"); Qt.quit(); return }
      if (step === 1) { timeoutMs = 100; command = ["/usr/bin/python3", "-c", "import time; time.sleep(10)"] }
      if (step === 2) { timeoutMs = 2000; outputLimit = 1024; command = ["/usr/bin/python3", "-c", "print('x'*2000)"] }
      if (step === 3) interpreter = "/does-not-exist/laf-python"
      if (step === 4) { interpreter = "/usr/bin/python3"; command = ["/does-not-exist/laf-command"] }
      running = true
    }
  }
  Component.onCompleted: { job.command = ["/usr/bin/python3", "-c", "print('hello')"]; job.running = true }
  Timer { interval: 12000; running: true; onTriggered: Qt.exit(12) }
}
''')
    result = subprocess.run(["quickshell", "--path", str(fixture / "shell.qml"), "--no-color"],
                            env=dict(os.environ, QT_QPA_PLATFORM="offscreen", XDG_RUNTIME_DIR=str(runtime)),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15)
    assert result.returncode == 0 and "ALL_PROCESS_CASES_PASSED" in result.stdout, result.stdout
    # Destroy the QML loader while its controller is alive. The native Process
    # may kill the relay, so this specifically exercises guardian cancellation.
    started = fixture / "started"
    escaped = fixture / "escaped-after-unload"
    child_code = (f"from pathlib import Path; import time; Path({str(started)!r}).touch(); "
                  f"time.sleep(1); Path({str(escaped)!r}).touch()")
    import json
    (fixture / "unload.qml").write_text('''import QtQuick
import Quickshell
ShellRoot {
  Loader {
    id: loader
    sourceComponent: BoundedProcess {
      command: ["/usr/bin/python3", "-c", CHILD_CODE]
      Component.onCompleted: running = true
    }
  }
  Timer { interval: 400; running: true; onTriggered: loader.active = false }
  Timer { interval: 1800; running: true; onTriggered: Qt.quit() }
}
'''.replace('CHILD_CODE', json.dumps(child_code)))
    result = subprocess.run(["quickshell", "--path", str(fixture / "unload.qml"), "--no-color"],
                            env=dict(os.environ, QT_QPA_PLATFORM="offscreen", XDG_RUNTIME_DIR=str(runtime)),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=5)
    assert result.returncode == 0 and started.exists(), result.stdout
    assert not escaped.exists(), "Controller survived production component destruction"
print("Process limits passed: total deadline, both output streams, continuing chunks, grandchild cleanup; native Quickshell success, immediate retries, FailedToStart watchdog, missing command and component destruction.")
