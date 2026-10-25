"""Optional actual qt6ct/QWidget readback in an isolated offscreen process."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

if len(sys.argv) == 1:
    source = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='laf-native-qt-') as directory:
        env = dict(os.environ, HOME=directory, XDG_CONFIG_HOME=directory + '/config',
                   XDG_STATE_HOME=directory + '/state', XDG_RUNTIME_DIR=directory,
                   QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='qt6ct',
                   QT_STYLE_OVERRIDE='', DBUS_SESSION_BUS_ADDRESS='', GSETTINGS_BACKEND='keyfile',
                   PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True)
    raise SystemExit()

from PySide6.QtGui import QFont, QPalette
from PySide6.QtWidgets import QApplication, QLineEdit
from application_themes import qt_palette
from global_font_actions import build_global_font_targets
from transaction import FILE_TARGETS

config = Path(os.environ['XDG_CONFIG_HOME'])
qt = config / 'qt6ct/qt6ct.conf'
qt.parent.mkdir(parents=True)
colors_path = config / 'qt6ct/colors/look-and-feel.conf'
colors_path.parent.mkdir()
colors = {'foreground': '#101020', 'background': '#fafafa', 'accent': '#305090',
          'selection': '#305090', 'lighter_background': '#eeeeee', 'muted': '#555555'}
colors_path.write_bytes(qt_palette(colors))
qt.write_text('[Appearance]\nstyle=Fusion\ncustom_palette=true\ncolor_scheme_path=' + str(colors_path) + '\n[Fonts]\ngeneral="Sans Serif,9,-1,5,50,0,0,0,0,0"\nfixed="Monospace,9,-1,5,50,0,0,0,0,0"\n')
targets, _ = build_global_font_targets('DejaVu Sans', 12, 'DejaVu Sans Mono', 13, set())
qt.write_bytes(targets['qt6ct-settings'])
app = QApplication([])
entry = QLineEdit()
entry.setPlaceholderText('Visible placeholder')
entry.show()
app.processEvents()
palette = entry.palette()
font = app.font()
assert font.family() == 'DejaVu Sans' and font.pointSize() == 12, font.toString()
assert palette.color(QPalette.Base).name() == colors['background'], palette.color(QPalette.Base).name()
assert palette.color(QPalette.Text).name() == colors['foreground']
assert palette.color(QPalette.PlaceholderText) != palette.color(QPalette.Base)
serialized = QFont()
assert serialized.fromString('DejaVu Sans Mono,13,-1,5,50,0,0,0,0,0')
assert serialized.family() == 'DejaVu Sans Mono' and serialized.pointSize() == 13
print(json.dumps({'actualQWidgetFont': font.toString(), 'base': palette.color(QPalette.Base).name(),
                  'text': palette.color(QPalette.Text).name(),
                  'placeholder': palette.color(QPalette.PlaceholderText).name(), 'platform': app.platformName()}))
