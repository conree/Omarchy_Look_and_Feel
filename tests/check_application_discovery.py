"""Toolkit discovery must not confuse shell libraries with app UI controls."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from types import SimpleNamespace
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import font_application_inventory as inventory
with TemporaryDirectory() as directory:
 script=Path(directory)/'app';script.write_text('from PySide6.QtWidgets import QApplication\n')
 with patch.object(inventory.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='')):
  assert inventory._binary_toolkit(str(script))=='Qt 6'
 for libraries,expected in [('libQt6Gui.so.6','Qt 6'),('libQt5Gui.so.5','Qt 5'),('libflutter_linux_gtk.so libgtk-3.so','Flutter')]:
  inventory._binary_toolkit.cache_clear()
  with patch.object(inventory.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=libraries)):
   assert inventory._binary_toolkit(str(script))==expected
 with patch.object(inventory,'_binary_toolkit',return_value='GTK 3'):
  assert inventory._framework('teams-for-linux.desktop','Teams','teams-for-linux',set())=='Electron/Chromium'
  assert inventory._framework('signal.desktop','Signal','signal-desktop',set())=='Electron/Chromium'
 with patch.object(inventory,'_binary_toolkit',return_value='GTK 3'), patch.object(inventory,'_resolved_exec',return_value=script):
  assert inventory._framework('cursor-theme-editor.desktop','Cursor Theme Editor','cursor-editor',set())=='GTK 3 application'
 resource=Path(directory)/'real/resources';resource.mkdir(parents=True)
 (resource/'app.asar').touch();binary=resource.parent/'app';binary.touch()
 link=Path(directory)/'launcher';link.symlink_to(binary)
 with patch.object(inventory,'_resolved_exec',return_value=link):
  assert inventory._framework('wrapped.desktop','Wrapped','wrapped',set())=='Electron/Chromium'
 assert 'application-specific' in inventory._generic_surface('Flutter application')[1][0]
print('Python Qt launchers, Qt Quick libraries and Electron/Flutter UI distinctions passed.')

import manual_app_registry as registry
for version in (5,6):
 record={'framework':f'Qt {version} application','fontRoles':['system-ui'],
         'controlPoints':[f'~/.config/qt{version}ct/qt{version}ct.conf [Fonts]: general/fixed'],
         'launchable':True}
 assert registry._classify(record)==f'qt{version}'
 record['fontRoles'].append('editor-monospace')
 assert registry._classify(record)=='unsupported', 'Editor-specific control cannot be inferred from Qt chrome'
print('Manual audits register identified Qt system-font surfaces; app-specific editor controls remain explicit.')
