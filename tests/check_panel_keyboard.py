"""Native Qt keyboard regression for the production panel's key wrapper.

Loads the installed PanelKeyCatcher unchanged and extracts the production
Panel's wrapper bindings, focus helper, and styled control definitions.
Uses a disposable HOME and offscreen window; no controller or host GUI runs.
"""
from pathlib import Path
import os
import resource
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-panel-keyboard-') as directory:
        env = dict(os.environ, HOME=directory, XDG_CONFIG_HOME=directory+'/.config',
                   XDG_DATA_HOME=directory+'/.local/share', XDG_STATE_HOME=directory+'/.local/state',
                   XDG_CACHE_HOME=directory+'/.cache', XDG_RUNTIME_DIR=directory,
                   QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='generic',
                   QT_STYLE_OVERRIDE='', QT_QUICK_BACKEND='software', QML_DISABLE_DISK_CACHE='1',
                   DBUS_SESSION_BUS_ADDRESS='', PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True, timeout=20)
    raise SystemExit()

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

omarchy = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy'))
catcher = omarchy / 'shell/Ui/PanelKeyCatcher.qml'
assert catcher.is_file(), 'Installed Omarchy PanelKeyCatcher is required'
fixture = Path.home()
(fixture/'PanelKeyCatcher.qml').write_bytes(catcher.read_bytes())
production = (SOURCE/'Panel.qml').read_text()
start = production.index('    PanelKeyCatcher {')
end = production.index('      Controls.Pane {', start)
wrapper = production[start:end]
assert 'id: keyCatcher' in wrapper

qml = '''import QtQuick
import QtQuick.Controls as Controls
Window {
  id: window
  width: 420; height: 240; visible: true
  Item {
    id: root; objectName: "root"; anchors.fill: parent
    property int closedCount: 0
    property int activations: 0
    property bool popupOpen: selector.popup.visible
    function close() { closedCount += 1 }
''' + wrapper + '''
      Controls.Button {
        objectName: "first"; x: 10; y: 10; text: "Action"; focusPolicy: Qt.StrongFocus
        onClicked: root.activations += 1
      }
      Controls.TextField { objectName: "editor"; x: 10; y: 60; width: 260; focusPolicy: Qt.StrongFocus }
      Controls.ComboBox { id: selector; objectName: "picker"; x: 10; y: 110; width: 260; model: ["One", "Two", "Three"]; focusPolicy: Qt.StrongFocus }
    }
    Component.onCompleted: keyCatcher.forceActiveFocus()
  }
}
'''
(fixture/'main.qml').write_text(qml)
app = QGuiApplication([])
engine = QQmlApplicationEngine()
engine.load(QUrl.fromLocalFile(str(fixture/'main.qml')))
assert engine.rootObjects(), 'Production key wrapper did not load'
window = engine.rootObjects()[0]
root = window.findChild(QQuickItem, 'root')
editor = window.findChild(QQuickItem, 'editor')
picker = window.findChild(QQuickItem, 'picker')
app.processEvents()


def key(value, modifiers=Qt.NoModifier):
    QTest.keyClick(window, value, modifiers)
    app.processEvents()


key(Qt.Key_Tab)
assert window.activeFocusItem().objectName() == 'first', 'Initial Tab was trapped by the key catcher'
key(Qt.Key_Space)
assert root.property('activations') == 1, 'Native button activation was swallowed'
key(Qt.Key_Tab)
assert window.activeFocusItem().objectName() == 'editor'
for value in (Qt.Key_H, Qt.Key_J, Qt.Key_K, Qt.Key_L, Qt.Key_Space, Qt.Key_X):
    key(value)
assert editor.property('text') == 'hjkl x', 'Editor text was mistaken for shell navigation'
key(Qt.Key_Backtab, Qt.ShiftModifier)
assert window.activeFocusItem().objectName() == 'first', 'Reverse focus traversal failed'
key(Qt.Key_Tab)
key(Qt.Key_Tab)
assert window.activeFocusItem().objectName() == 'picker'
key(Qt.Key_Down)
assert picker.property('currentIndex') == 1, 'Native selector navigation was swallowed'
key(Qt.Key_Space)
assert root.property('popupOpen'), 'Keyboard could not open the selector popup'
key(Qt.Key_Escape)
assert not root.property('popupOpen'), 'Escape did not dismiss the selector popup'
assert root.property('closedCount') == 0, 'Dismissing a popup also closed its panel'
key(Qt.Key_Escape)
assert root.property('closedCount') == 1, 'Escape no longer closes the panel'
print('Native panel keyboard passed: initial/reverse Tab, button activation, normal typing, selector arrows and popup/panel Escape.')

# Use the real styled controls and focus helper in a deliberately short viewport.
# This tests native focus delivery and coordinates without invoking the controller
# or loading the shell. Its outer geometry is a fixture, not a full-panel test.
def function(name):
    start = production.index('  function '+name+'(')
    end = production.index('\n  function ', start + 1)
    return production[start:end]


start = production.index('  component ActionButton:')
end = production.index('  component ResultNotice:', start)
components = production[start:end]
start = production.index('    Controls.CheckBox {', production.index('  component FontChoice:'))
end = production.index('\n    }\n', start) + len('\n    }')
checkbox = production[start:end].replace('Controls.CheckBox {', 'Controls.CheckBox {\n      x: 12; y: 800', 1)
focus_qml = '''pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
Window {
  id: window; width: 480; height: 340; visible: true
  Item {
    id: root; objectName: "root"; anchors.fill: parent
    property string fontFamily: "Sans"
    property int controlFontPixelSize: 16
    property int selectorHeight: 30
    property color popupBackground: "#eff1f5"
    property color popupForeground: "#4c4f69"
    property color surfaceColor: "#e9ebf0"
    property color accentColor: "#0066aa"
    property color lineColor: "#aabbcc"
    property color mutedColor: "#4c4f69"
    property bool onlyMonospacedTerminalFonts: true
    property int closedCount: 0
    function close() { closedCount += 1 }
    QtObject { id: panel; property int availableCardHeight: 340 }
    QtObject { id: choice; property bool terminal: true }
''' + function('revealControl') + '\n' + function('readable') + '\n' + components + wrapper + '''
      ActionButton { objectName: "header"; x: 10; y: 5; text: "Header" }
      Flickable {
        id: contentViewport; objectName: "viewport"
        x: 10; y: 55; width: 450; height: 200; clip: true
        contentWidth: width; contentHeight: content.height
        Item {
          id: content; width: contentViewport.width; height: 900
          ActionButton { objectName: "top"; x: 12; y: 10; text: "Top" }
          Picker { objectName: "bottomPicker"; x: 12; y: 400; width: 300; model: [{id: "a", name: "First"}, {id: "b", name: "Second"}] }
          SearchField { objectName: "bottomEditor"; x: 12; y: 620; width: 300 }
''' + checkbox + '''
        }
      }
      ActionButton { objectName: "footer"; x: 10; y: 280; text: "Footer" }
    }
    Component.onCompleted: keyCatcher.forceActiveFocus()
  }
}
'''
(fixture/'focus.qml').write_text(focus_qml)
window.setVisible(False)
focus_engine = QQmlApplicationEngine()
focus_engine.load(QUrl.fromLocalFile(str(fixture/'focus.qml')))
assert focus_engine.rootObjects(), 'Production styled controls/focus helper did not load'
window = focus_engine.rootObjects()[0]
root = window.findChild(QQuickItem, 'root')
viewport = window.findChild(QQuickItem, 'viewport')
app.processEvents()


def focused(name):
    assert window.activeFocusItem().objectName() == name, (name, window.activeFocusItem().objectName())


def inside(name):
    item = window.findChild(QQuickItem, name)
    point = item.mapToItem(viewport, 0, 0)
    assert point.y() >= 0 and point.y() + item.height() <= viewport.height(), (name, point.y(), item.height(), viewport.height())


key(Qt.Key_Tab)
focused('header')
assert viewport.property('contentY') == 0
key(Qt.Key_Tab)
focused('top'); inside('top')
key(Qt.Key_Tab)
focused('bottomPicker'); inside('bottomPicker')
assert viewport.property('contentY') > 200, 'Offscreen selector was not revealed'
key(Qt.Key_Tab)
focused('bottomEditor'); inside('bottomEditor')
key(Qt.Key_Tab)
focused('monospaceFilter'); inside('monospaceFilter')
scrolled = viewport.property('contentY')
key(Qt.Key_Tab)
focused('footer')
assert viewport.property('contentY') == scrolled, 'Footer focus unexpectedly scrolled the page'
for name in ('monospaceFilter', 'bottomEditor', 'bottomPicker', 'top'):
    key(Qt.Key_Backtab, Qt.ShiftModifier)
    focused(name); inside(name)
assert viewport.property('contentY') <= 10, 'Reverse traversal did not restore the top controls'
key(Qt.Key_Backtab, Qt.ShiftModifier)
focused('header')
assert viewport.property('contentY') <= 10

# Probe the actual Qt color implementation, including Qt.rgba conversion.
import json
from PySide6.QtQml import QQmlExpression, QQmlEngine
expression = QQmlExpression(QQmlEngine.contextForObject(root), root, '''(function() {
  var samples = ["#eeeeee", "#111111", "#8899aa", "#ee8833", "#0066cc", "#dd55cc"];
  var results = [];
  function lum(c) { function ch(v) { return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4) }; return ch(c.r)*.2126+ch(c.g)*.7152+ch(c.b)*.0722 }
  var backgrounds = [["#eff1f5", "#4c4f69"], ["#1e1e2e", "#cdd6f4"]];
  backgrounds.forEach(function(pair) {
    root.popupBackground = pair[0]; root.popupForeground = pair[1];
    samples.forEach(function(candidate) {
      var actual = root.readable(candidate), a = lum(actual), b = lum(root.popupBackground);
      results.push({candidate: candidate, background: pair[0], actual: actual.toString(), ratio: (Math.max(a,b)+.05)/(Math.min(a,b)+.05)});
    });
  });
  return JSON.stringify(results);
})()''')
report, undefined = expression.evaluate()
assert not expression.hasError(), expression.error().toString()
assert not undefined
colors = json.loads(report)
assert len(colors) == 12
assert all(item['ratio'] >= 4.8 for item in colors), colors
assert any(item['actual'] != '#4c4f69' for item in colors if item['background'] == '#eff1f5'), 'All light-theme accents lost their color'
print('Native production focus passed: forward/reverse Tab reveals buttons, selectors, editors, checkbox; header/footer do not scroll. Actual Qt contrast passed 12 light/dark cases at >=4.8:1.')

# Exercise the production FileView with only its HOME-relative theme.name fixture.
# Quickshell has a disposable runtime directory/config path and no host bus.
import shutil
import time
assert shutil.which('quickshell'), 'Installed Quickshell is required for native FileView coverage'
start = production.index('  FileView {\n    id: observedThemeName')
end = production.index('\n  Process {', start)
watcher = production[start:end]
theme_name = fixture/'.local/state/omarchy/current/theme.name'
theme_name.parent.mkdir(parents=True, exist_ok=True)
theme_name.write_text('catppuccin-latte\n')
watch_qml = '''import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
  id: root
  property string observedTheme: ""
  property string selectedLightThemeId: "unchanged-draft"
  onObservedThemeChanged: console.log("LAF_THEME_WATCH:" + JSON.stringify([observedTheme, selectedLightThemeId]))
''' + function('adoptObservedThemeName') + '\n' + watcher + '\n}\n'
(fixture/'watch.qml').write_text(watch_qml)
log = fixture/'watch.log'
with log.open('w') as output:
    process = subprocess.Popen(['quickshell', '--path', str(fixture/'watch.qml'), '--no-color'],
                               stdout=output, stderr=subprocess.STDOUT)
    try:
        offset = 0

        def observed(expected):
            global offset
            marker = 'LAF_THEME_WATCH:'+json.dumps([expected, 'unchanged-draft'], separators=(',', ':'))
            deadline = time.monotonic() + 2.5
            while time.monotonic() < deadline:
                value = log.read_text()
                at = value.find(marker, offset)
                if at >= 0:
                    offset = at + len(marker)
                    return
                assert process.poll() is None, value
                time.sleep(.02)
            raise AssertionError('Native file observer did not report '+repr(expected)+'; '+log.read_text())

        observed('catppuccin-latte')
        for text, expected in [('catppuccin\n', 'catppuccin'), ('../invalid\n', ''), ('nord\n', 'nord')]:
            temporary = theme_name.with_suffix('.tmp')
            temporary.write_text(text)
            temporary.replace(theme_name)
            observed(expected)
        theme_name.unlink()
        observed('')
        theme_name.write_text('tokyo-night\n')
        observed('tokyo-night')
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
print('Native production FileView passed: initial read, repeated atomic replacement, invalid-name clearing, deletion and recreation; draft unchanged.')
