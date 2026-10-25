"""Optional native Qt5/Qt6 common-selector check in an isolated HOME.

Requires the Qt5 development package, a C++ compiler, PySide6 and both qtct
plugins. It never connects to the user's display or reads their preferences.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import json
SOURCE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SOURCE))
from qt_integration import plugins
common=plugins().get(5,set()) & plugins().get(6,set())
assert common, 'Qt5 and Qt6 need a shared native integration for this test'
selector='qt6ct' if 'qt6ct' in common else 'qt5ct'
CPP='''#include <QApplication>
#include <QLineEdit>
#include <QPalette>
#include <cstdio>
int main(int argc, char **argv) { QApplication app(argc,argv); QLineEdit w;
if(w.palette().color(QPalette::Base).name() != "#112233" || w.palette().color(QPalette::Text).name() != "#eeeeff" || w.font().pointSize()!=13) return 3;
printf("Qt5 actual widget: %s %s %s\\n",w.font().toString().toUtf8().constData(),w.palette().color(QPalette::Base).name().toUtf8().constData(),w.palette().color(QPalette::Text).name().toUtf8().constData()); }
'''
with tempfile.TemporaryDirectory(prefix='laf-native-qt5-') as root:
    home=Path(root)
    env=dict(os.environ,HOME=root,XDG_CONFIG_HOME=root+'/config',XDG_RUNTIME_DIR=root,QT_QPA_PLATFORM='offscreen',QT_QPA_PLATFORMTHEME=selector,QT_STYLE_OVERRIDE='',DBUS_SESSION_BUS_ADDRESS='',PYTHONPATH=str(SOURCE))
    source=home/'probe.cpp';source.write_text(CPP)
    flags=subprocess.check_output(['pkg-config','--cflags','--libs','Qt5Widgets'],text=True).split()
    subprocess.run(['c++','-fPIC',str(source),'-o',str(home/'probe'),*flags],check=True)
    from application_themes import qt_palette
    colors={'foreground':'#eeeeff','background':'#112233','accent':'#9977ee','selection':'#9977ee','lighter_background':'#223344','muted':'#aaaacc'}
    for major in (5,6):
        folder=home/f'config/qt{major}ct';folder.mkdir(parents=True)
        palette=folder/'colors.conf';palette.write_bytes(qt_palette(colors))
        (folder/f'qt{major}ct.conf').write_text('[Appearance]\ncustom_palette=true\nstyle=Fusion\ncolor_scheme_path='+str(palette)+'\n[Fonts]\ngeneral="DejaVu Sans,13,-1,5,50,0,0,0,0,0"\n')
    subprocess.run([str(home/'probe')],env=env,check=True)
    subprocess.run([sys.executable,'-B','-c', '''from PySide6.QtWidgets import QApplication,QLineEdit
from PySide6.QtGui import QPalette
app=QApplication([]);w=QLineEdit()
assert w.palette().color(QPalette.Base).name()=='#112233'
assert w.palette().color(QPalette.Text).name()=='#eeeeff'
assert w.font().pointSize()==13
print('Qt6 actual widget:',w.font().toString(),w.palette().color(QPalette.Base).name(),w.palette().color(QPalette.Text).name())'''],env=env,check=True)
print('Both native Qt majors used the detected shared selector:',selector)
