"""Actual-Qt lifecycle regression for the production shell-font bridge.

Source singleton, qmldir, and widget lifecycle handlers are loaded directly.
Only the underlying Style singleton and widget I/O are test doubles. All runs
use a disposable HOME/offscreen Qt, suppress core dumps, and have a deadline.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]

if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-bridge-independent-') as directory:
        env = dict(os.environ, HOME=directory, XDG_CONFIG_HOME=directory + '/config',
                   XDG_STATE_HOME=directory + '/state', XDG_DATA_HOME=directory + '/data',
                   XDG_CACHE_HOME=directory + '/cache', XDG_RUNTIME_DIR=directory,
                   QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='',
                   QT_QUICK_BACKEND='software', DBUS_SESSION_BUS_ADDRESS='',
                   PYTHONDONTWRITEBYTECODE='1')
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            result = subprocess.run([sys.executable, '-B', __file__, 'run'], env=env,
                                    stdout=stdout, stderr=stderr, timeout=15)
            for label, stream in [('stdout', stdout), ('stderr', stderr)]:
                size = stream.tell()
                stream.seek(0)
                output = stream.read(16000).decode(errors='replace')
                print(label + ':\n' + output)
                if size > 16000:
                    print(f'{label}: {size - 16000} additional bytes omitted')
            raise SystemExit(result.returncode)

import resource
import ctypes
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
assert ctypes.CDLL(None).prctl(4, 0, 0, 0, 0) == 0  # PR_SET_DUMPABLE = 0

from PySide6.QtCore import QCoreApplication, QEvent, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

fixture = Path.home() / 'qml'
fixture.mkdir()
module = fixture / 'qs' / 'Commons'
module.mkdir(parents=True)
(module / 'qmldir').write_text('module qs.Commons\nsingleton Style 1.0 Style.qml\n')
(module / 'Style.qml').write_text('''pragma Singleton
import QtQml
QtObject {
  property string baselineFamily: "Original A"
  property string fontFamily: baselineFamily
  readonly property QtObject font: QtObject {}
}
''')
(fixture / 'ShellFontBridge.qml').write_bytes((SOURCE / 'ShellFontBridge.qml').read_bytes())
(fixture / 'qmldir').write_bytes((SOURCE / 'qmldir').read_bytes())
production = (SOURCE / 'BarWidget.qml').read_text()
start = production.index('  onShellFontOwnedChanged:')
end = production.index('  function readShellFontPolicy()', start)
block = production[start:end]
assert 'Component.onCompleted:' in block and 'Component.onDestruction:' in block
(fixture / 'Client.qml').write_text('''import QtQuick
import qs.Commons
import "." as Local
Item {
  id: root
  property bool shellFontOwned: false
  property string savedShellFont: ""
''' + block + '\n}\n')
(fixture / 'Root.qml').write_text('''import QtQuick
import qs.Commons
Item {
  id: outer
  property string originalFamily: "Original A"
  property bool loaded1: false
  property bool loaded2: false
  property bool loaded3: false
  property bool owned1: false
  property bool owned2: true
  property bool owned3: true
  property string saved1: "Chosen"
  property string saved2: "Chosen"
  property string saved3: "Chosen"
  readonly property string observed: Style.fontFamily
  Binding { target: Style; property: "baselineFamily"; value: outer.originalFamily }
  Loader { active: outer.loaded1; sourceComponent: Client {
    shellFontOwned: outer.owned1; savedShellFont: outer.saved1
  } }
  Loader { active: outer.loaded2; sourceComponent: Client {
    shellFontOwned: outer.owned2; savedShellFont: outer.saved2
  } }
  Loader { active: outer.loaded3; sourceComponent: Client {
    shellFontOwned: outer.owned3; savedShellFont: outer.saved3
  } }
}
''')

app = QGuiApplication([])
engine = QQmlEngine()
engine.addImportPath(str(fixture))
component = QQmlComponent(engine, QUrl.fromLocalFile(str(fixture / 'Root.qml')))
assert not component.isError(), [error.toString() for error in component.errors()]
root = component.create()
assert root is not None, [error.toString() for error in component.errors()]

def check(key, value, expected):
    assert root.setProperty(key, value), key
    app.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()
    actual = root.property('observed')
    print(f'{key}={value!r}: {actual!r}', flush=True)
    assert actual == expected, (key, value, expected, actual)

assert root.property('observed') == 'Original A'
check('loaded1', True, 'Original A')
check('owned1', True, 'Chosen')
check('originalFamily', 'Original B', 'Chosen')
check('loaded2', True, 'Chosen')
check('loaded3', True, 'Chosen')
check('loaded2', False, 'Chosen')
check('loaded1', False, 'Chosen')
check('saved3', 'Updated', 'Updated')
check('owned3', False, 'Original B')
check('originalFamily', 'Original C', 'Original C')
check('owned3', True, 'Updated')
check('loaded3', False, 'Original C')
check('originalFamily', 'Original D', 'Original D')
check('loaded1', True, 'Chosen')
check('loaded2', True, 'Chosen')
check('loaded2', False, 'Chosen')
check('loaded1', False, 'Original D')
check('originalFamily', 'Original E', 'Original E')
check('loaded1', True, 'Chosen')
check('loaded2', True, 'Chosen')
root.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
app.processEvents()
root = component.create()
assert root.property('observed') == 'Original A', root.property('observed')
check('originalFamily', 'Original F', 'Original F')
check('loaded1', True, 'Original F')
check('owned1', True, 'Chosen')
check('loaded1', False, 'Original F')
print('PASS production singleton and lifecycle: middle/creator/final unload, continued updates, ownership release, reacquisition, whole active widget-tree destruction/recreation, original live binding restoration.', flush=True)
root.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
engine.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
