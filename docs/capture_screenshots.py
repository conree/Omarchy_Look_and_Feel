#!/usr/bin/env python3
"""Capture README panel images from production QML using an isolated Qt window.

Run: python3 -B docs/capture_screenshots.py
Requires PySide6 and the stock Catppuccin/Latte palettes in OMARCHY_PATH.
Only the shell window/IPC wrapper is replaced; controls/layout come from Panel.qml.
Catalog and application records are sample data. No controller commands run.
The wallpaper is an original geometric SVG fixture; no personal assets are read.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
OUTPUT = SOURCE / 'docs/screenshots'
sys.path.insert(0, str(SOURCE))
os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='generic',
                  QT_QUICK_BACKEND='software', QML_DISABLE_DISK_CACHE='1',
                  QT_STYLE_OVERRIDE='')

from PySide6.QtCore import QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlEngine, QQmlExpression
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from appearance_previews import theme_preview, IconPreviews


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    production = (SOURCE / 'Panel.qml').read_text()
    # Keep all production properties, functions, components and tab content.
    body = production[production.index('  readonly property color popupForeground:'):
                      production.index('  Component.onCompleted: root.refreshInventory()')]
    body = re.sub(r'  readonly property string previewCachePath: \{.*?\n  \}',
                  '  readonly property string previewCachePath: ""', body, flags=re.S)
    body = body.replace('Color.popups.text', '"#cdd6f4"').replace('Color.popups.background', '"#1e1e2e"')
    body = body.replace('Color.accent', '"#89b4fa"').replace('Style.font.family', '"DejaVu Sans"').replace('Style.font.body', '16')
    a, b = body.index('  KeyboardPanel {'), body.index('    PanelKeyCatcher {')
    body = body[:a] + '''  Item {
    id: panel; anchors.fill: parent
    readonly property real availableCardWidth: width
    readonly property real availableCardHeight: height
''' + body[b:]
    body = body.replace('    PanelKeyCatcher {', '    Item {').replace('      blocked: true\n', '')
    qml = '''pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
Window {
  id: window; width: 840; height: 1040; visible: true; color: "#1e1e2e"
  Item {
    id: root; objectName: "root"; anchors.fill: parent
    property var bar: null
    property bool opened: true
    QtObject { id: sampleHost; property bool repairEnabled: true; property bool repairSettingLoaded: true; property string repairSettingError: "" }
''' + body + '\n  }\n}\n'
    qml = qml.replace('property var hostWidget: null', 'property var hostWidget: sampleHost')
    omarchy = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy'))
    themes = []
    for name, label in [('catppuccin-latte', 'Catppuccin Latte'), ('catppuccin', 'Catppuccin')]:
        preview = theme_preview([str(omarchy / 'themes' / name)])
        assert preview, f'Missing stock palette: {name}'
        themes.append(dict(id=name, name=name, displayName=label, preview=preview, selectable=True))
    warnings = []
    qInstallMessageHandler(lambda kind, context, message: warnings.append(message))
    app = QGuiApplication([])
    with tempfile.TemporaryDirectory(prefix='laf-readme-panel-') as directory:
        fixture = Path(directory)
        wallpaper = fixture / 'geometric.svg'
        wallpaper.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="300">'
                             '<rect width="800" height="300" fill="#1e1e2e"/>'
                             '<circle cx="650" cy="65" r="90" fill="#f5c2e7"/>'
                             '<path d="M0 300V250L260 60L500 300Z" fill="#45475a"/>'
                             '<path d="M240 300L510 100L800 300Z" fill="#89b4fa"/></svg>')
        path = fixture / 'main.qml'
        path.write_text(qml)
        engine = QQmlApplicationEngine()
        engine.load(QUrl.fromLocalFile(str(path)))
        assert engine.rootObjects(), warnings
        window = engine.rootObjects()[0]
        root = window.findChild(QQuickItem, 'root')
        inventory = {
            'catalog_entries': {
                'fonts': [{'id': 'sans', 'name': 'DejaVu Sans', 'monospace': False},
                          {'id': 'mono', 'name': 'DejaVu Sans Mono', 'monospace': True}],
                'themes': themes,
                'backgrounds': [{'id': 'geometric', 'name': 'Geometric', 'source': str(wallpaper), 'selectable': True}],
                'icons': [{'id': 'adwaita', 'name': 'Adwaita', 'displayName': 'Adwaita',
                           'selectable': True, 'previewIcons': IconPreviews((Path('/usr/share/icons'),)).samples('Adwaita')}],
                'unlocks': [],
            },
            'appearance_action_status': {'theme': {'observedValue': 'catppuccin', 'undoAvailable': True}},
            'global_font_undo_available': True,
            'preferences': {'systemFontId': 'sans', 'terminalFontId': 'mono'},
            'desiredAppearance': {'theme': {'mode': 'dark', 'light': 'catppuccin-latte', 'dark': 'catppuccin'}, 'icons': 'adwaita'},
            'font_application_inventory': {'desktopApplications': [
                {'name': 'Alacritty', 'framework': 'Terminal'},
                {'name': 'Files', 'framework': 'GTK 4'},
                {'name': 'KiCad', 'framework': 'GTK 3'},
                {'name': 'Qt Assistant', 'framework': 'Qt 6'},
            ]},
        }
        expression = QQmlExpression(QQmlEngine.contextForObject(root), root,
                                   'root.adoptInventory(' + json.dumps(json.dumps(inventory)) + ', false)')
        expression.evaluate()
        assert not expression.hasError(), expression.error().toString()
        assert root.property('inventoryLoaded')
        root.setProperty('onlyMonospacedTerminalFonts', True)
        for tab, name, height in [(0, 'appearance', 950), (1, 'fonts', 730), (2, 'applications', 850)]:
            root.setProperty('activeTab', tab)
            window.setHeight(height)
            QTest.qWait(350)
            assert window.grabWindow().save(str(OUTPUT / (name + '.png')))
        assert not warnings, warnings
    print('Captured production panel controls: Appearance, Fonts, Applications (sample data).')
    print('Panel.qml SHA-256:', hashlib.sha256(production.encode()).hexdigest())


if __name__ == '__main__':
    main()
