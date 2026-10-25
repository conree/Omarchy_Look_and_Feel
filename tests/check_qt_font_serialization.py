"""Native Qt 5/6 regression for malformed QFont values, in isolated homes.

Requires PySide6, Qt5 development files/compiler and the installed shared
qt5ct/qt6ct integration. No host settings or running applications are touched.
"""
from pathlib import Path
import configparser
import json
import os
import resource
import subprocess
import sys
import tempfile
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-qt-font-wire-') as directory:
        env = dict(os.environ, HOME=directory, XDG_CONFIG_HOME=directory + '/config',
                   XDG_STATE_HOME=directory + '/state', XDG_DATA_HOME=directory + '/data',
                   XDG_CACHE_HOME=directory + '/cache', XDG_RUNTIME_DIR=directory,
                   QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='generic',
                   QT_STYLE_OVERRIDE='', DBUS_SESSION_BUS_ADDRESS='',
                   PYTHONPATH=str(SOURCE), PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True)
    raise SystemExit()

sys.path.insert(0, str(SOURCE))
from PySide6.QtGui import QFont
from global_font_actions import _qt_font_value, build_global_font_targets
import transaction as tx
from qt_integration import plugins

BAD = 'Avenir Next,11,-1,400,0,0,0,0,0,0,0,0,0,0,1,Regular'
old = QFont()
assert old.fromString(BAD), 'This bug depends on Qt accepting the malformed string'
assert old.stretch() == 1 and old.styleHint().value == 144

# Preserve intentional style/stretch/spacing choices, even extreme but valid
# condensed stretch; this is structural repair, not a typography preference.
custom = QFont('Source', 9)
custom.setWeight(QFont.Bold)
custom.setStyle(QFont.StyleItalic)
custom.setUnderline(True)
custom.setStretch(75)
custom.setStyleHint(QFont.Monospace, QFont.PreferAntialias)
custom.setLetterSpacing(QFont.AbsoluteSpacing, 1.25)
custom.setWordSpacing(1.5)
custom.setStyleName('Bold Italic')
custom.setFeature(QFont.Tag.fromString('liga'), 0)
custom.setVariableAxis(QFont.Tag.fromString('wdth'), 85)
for stretch in (75, 1):
    custom.setStretch(stretch)
    updated = QFont()
    value = _qt_font_value(custom.toString(), 'DejaVu Sans', 12, 6)
    assert updated.fromString(value)
    for getter in ('weight', 'style', 'underline', 'stretch', 'styleHint', 'styleStrategy',
                   'letterSpacingType', 'letterSpacing', 'wordSpacing', 'styleName'):
        assert getattr(updated, getter)() == getattr(custom, getter)(), getter
    assert updated.featureValue(QFont.Tag.fromString('liga')) == 0
    assert updated.variableAxisValue(QFont.Tag.fromString('wdth')) == 85
    assert updated.family() == 'DejaVu Sans' and updated.pointSize() == 12
    assert _qt_font_value(value, 'DejaVu Sans', 12, 6) == value
custom.setPixelSize(24)
pixels = QFont()
assert pixels.fromString(_qt_font_value(custom.toString(), 'DejaVu Sans', 12, 6))
assert pixels.pointSize() == 12 and pixels.pixelSize() == -1

qt5_custom = _qt_font_value('Source,9,-1,7,75,1,1,0,1,0,Bold Italic', 'DejaVu Sans', 12, 5)
assert qt5_custom == 'DejaVu Sans,12,-1,7,75,1,1,0,1,0,Bold Italic'
for version in (5, 6):
    for malformed in (BAD, '', 'bad', 'Font,nan,-1,5,50,0,0,0,0,0',
                      'Font,12,-1,900,50,0,0,0,0,0', 'Font,12,-1,5,50,9,0,0,0,0',
                      'Font,12,-1,5,50,0,1.0,0,0,0'):
        repaired = _qt_font_value(malformed, 'DejaVu Sans', 12, version)
        check = QFont()
        assert check.fromString(repaired)
        assert check.family() == 'DejaVu Sans' and check.pointSize() == 12
        assert check.weight() == QFont.Normal and check.styleHint() == QFont.AnyStyle
        assert check.stretch() == (100 if version == 6 else 0)
with patch.dict(sys.modules, {'PySide6.QtGui': None}):
    try:
        _qt_font_value(BAD, 'DejaVu Sans', 12, 6)
    except tx.TransactionError as exc:
        assert 'pyside6' in str(exc)
    else:
        raise AssertionError('Missing native validator was ignored')

# Exercise the actual builder and journal; both settings retain unrelated keys.
config = Path(os.environ['XDG_CONFIG_HOME'])
before = {}
for version in (5, 6):
    path = config / f'qt{version}ct/qt{version}ct.conf'
    path.parent.mkdir(parents=True)
    raw = ('[Appearance]\nstyle=Fusion\n[Fonts]\ngeneral="' + BAD + '"\nfixed="' + BAD +
           '"\n[Independent]\nmarker=keep this\n').encode()
    path.write_bytes(raw)
    before[version] = raw
targets, _ = build_global_font_targets('DejaVu Sans', 12, 'DejaVu Sans Mono', 13, set())
selected = {key: targets[key] for key in ('qt5ct-settings', 'qt6ct-settings')}
repair_id = tx.apply_file_targets(selected, label='Native Qt font repair')
for version in (5, 6):
    assert b'marker=keep this' in (config / f'qt{version}ct/qt{version}ct.conf').read_bytes()

found = plugins()
common = found.get(5, set()) & found.get(6, set())
assert common, 'Native regression needs a shared qt5ct/qt6ct integration'
selector = 'qt6ct' if 'qt6ct' in common else 'qt5ct'
env = dict(os.environ, QT_QPA_PLATFORMTHEME=selector)
qt6_probe = '''from PySide6.QtGui import QFont,QFontMetricsF
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication,QLineEdit
import os
app=QApplication([]);w=QLineEdit();f=w.font()
assert f.family()=='DejaVu Sans' and f.pointSize()==12, f.toString()
assert f.weight()==QFont.Normal and f.stretch()==100 and f.styleHint()==QFont.AnyStyle, f.toString()
expected=QFont('DejaVu Sans',12);expected.setStretch(100)
width=QFontMetricsF(f).horizontalAdvance('08:42 Aa')
assert abs(width-QFontMetricsF(expected).horizontalAdvance('08:42 Aa'))<0.1, width
bad=QFont();assert bad.fromString(%r);bad.setFamily('DejaVu Sans');bad.setPointSize(12)
assert QFontMetricsF(bad).horizontalAdvance('08:42 Aa') < width/2
s=QSettings(os.environ['XDG_CONFIG_HOME']+'/qt6ct/qt6ct.conf',QSettings.IniFormat)
fixed=QFont();assert fixed.fromString(s.value('Fonts/fixed'))
assert fixed.family()=='DejaVu Sans Mono' and fixed.pointSize()==13 and fixed.stretch()==100
print('Qt6 fresh native widget font:',f.toString(),'sample width:',width)
''' % BAD
subprocess.run([sys.executable, '-B', '-c', qt6_probe], env=env, check=True)

# Qt5 must parse the production legacy-format output with its own library,
# not merely Qt6's compatibility decoder.
cpp = r'''#include <QApplication>
#include <QLineEdit>
#include <QFontMetricsF>
#include <QSettings>
#include <cstdio>
int main(int argc,char **argv) {
 QApplication app(argc,argv); QLineEdit widget; QFont f=widget.font();
 if(f.family()!="DejaVu Sans" || f.pointSize()!=12 || f.weight()!=QFont::Normal || f.styleHint()!=QFont::AnyStyle || f.stretch()!=0) return 2;
 QFont expected("DejaVu Sans",12);
 if(qAbs(QFontMetricsF(f).horizontalAdvance("08:42 Aa")-QFontMetricsF(expected).horizontalAdvance("08:42 Aa"))>0.1) return 3;
 QFont custom; if(!custom.fromString(QString::fromUtf8(argv[1])) || custom.weight()!=QFont::Bold || !custom.italic() || !custom.underline() || custom.styleHint()!=QFont::Monospace || custom.styleName()!="Bold Italic") return 4;
 QSettings s(qEnvironmentVariable("XDG_CONFIG_HOME")+"/qt5ct/qt5ct.conf",QSettings::IniFormat);
 QFont fixed; if(!fixed.fromString(s.value("Fonts/fixed").toString()) || fixed.family()!="DejaVu Sans Mono" || fixed.pointSize()!=13 || fixed.weight()!=QFont::Normal) return 5;
 printf("Qt5 fresh native widget font: %s sample width: %.3f\n",f.toString().toUtf8().constData(),QFontMetricsF(f).horizontalAdvance("08:42 Aa"));
}'''
source = Path.home() / 'qt5-font-probe.cpp'
source.write_text(cpp)
binary = Path.home() / 'qt5-font-probe'
flags = subprocess.check_output(['pkg-config', '--cflags', '--libs', 'Qt5Widgets'], text=True).split()
subprocess.run(['c++', '-fPIC', str(source), '-o', str(binary), *flags], check=True)
subprocess.run([str(binary), qt5_custom], env=env, check=True)
def tree_state():
    return {str(path.relative_to(Path.home())): path.read_bytes()
            for folder in (config, tx.transactions_path()) for path in folder.rglob('*') if path.is_file()}


# Undo and recovery must not put a known-broken font back. Verify both modern
# field metadata and a historical whole-file journal, before any writes.
journal_path = tx.transactions_path() / repair_id / 'transaction.json'
saved_journal = journal_path.read_bytes()
unchanged = tree_state()
with patch.dict(sys.modules, {'PySide6.QtGui': None}):
    try:
        tx.rollback_latest(label='Native Qt font repair')
    except tx.TransactionError as exc:
        assert 'pyside6' in str(exc)
    else:
        raise AssertionError('Undo ignored its native font validator dependency')
assert tree_state() == unchanged
for legacy, pending in ((False, False), (True, False), (True, True), (False, True)):
    journal = json.loads(saved_journal)
    if legacy:
        for row in journal['targets']:
            row.pop('managedEdits', None)
    if pending:
        journal['state'] = 'applying'
    journal_path.write_text(json.dumps(journal))
    unchanged = tree_state()
    try:
        tx.recover_pending() if pending else tx.rollback_latest(label='Native Qt font repair')
    except tx.TransactionError as exc:
        assert 'malformed saved font' in str(exc), str(exc)
    else:
        raise AssertionError('Undo/recovery restored a known malformed font')
    assert tree_state() == unchanged, 'Refused restoration mutated files or journals'
journal_path.write_bytes(saved_journal)

# A safe original parent remains Undo-able after a child repairs bad drift.
# Child before-values are not the final grouped restoration plan.
safe_original = {}
for version in (5, 6):
    path = config / f'qt{version}ct/qt{version}ct.conf'
    old_font = _qt_font_value('', 'DejaVu Sans', 10, version)
    raw = ('[Appearance]\nstyle=Fusion\n[Fonts]\ngeneral="' + old_font + '"\n').encode()
    path.write_bytes(raw)
    safe_original[version] = raw
targets, _ = build_global_font_targets('DejaVu Sans', 12, 'DejaVu Sans Mono', 13, set())
parent = tx.apply_file_targets({key: targets[key] for key in selected}, label='Native safe original')
qt6_path = config / 'qt6ct/qt6ct.conf'
qt6_path.write_text('[Fonts]\ngeneral="' + BAD + '"\n')
targets, _ = build_global_font_targets('DejaVu Sans', 12, 'DejaVu Sans Mono', 13, set())
tx.apply_file_targets({'qt6ct-settings': targets['qt6ct-settings']}, label='Native repair child', parent_transaction=parent)
tx.rollback_latest(label='Native safe original')
assert _qt_font_value('', 'DejaVu Sans', 10, 6).encode() in qt6_path.read_bytes()
assert (config / 'qt5ct/qt5ct.conf').read_bytes() == safe_original[5]

# Equality anchors retain a valid original when the initial Fonts Apply was
# already correct, and later repair must preserve independent shared data.
ready = ('[Fonts]\ngeneral="' + _qt_font_value('', 'DejaVu Sans', 12, 6) + '"\n').encode()
qt6_path.write_bytes(ready)
parent = tx.apply_file_targets({'qt6ct-settings': ready}, label='Native equal original',
                              owned_fields={'qt6ct-settings': {'Fonts/general', 'Fonts/fixed'}})
qt6_path.write_text('[Fonts]\ngeneral="' + BAD + '"\n')
tx.apply_file_targets({'qt6ct-settings': ready}, label='Native equal repair child', parent_transaction=parent,
                      owned_fields={'qt6ct-settings': {'Fonts/general', 'Fonts/fixed'}})
addition = b'[Independent]\nmarker=keep this addition\n'
qt6_path.write_bytes(qt6_path.read_bytes() + addition)
tx.rollback_latest(label='Native equal original')
assert qt6_path.read_bytes() == ready + addition

# A child-only Qt target requires snapshot consolidation. A bad saved font
# must stop before those snapshot copies or any parent target restoration.
qt6_path.write_text('[Fonts]\ngeneral="' + BAD + '"\n')
parent = tx.apply_file_targets({'global-font-selection': b'{}\n'}, label='Native child-only unsafe')
tx.apply_file_targets({'qt6ct-settings': ready}, label='Native child-only repair', parent_transaction=parent)
unchanged = tree_state()
try:
    tx.rollback_latest(label='Native child-only unsafe')
except tx.TransactionError as exc:
    assert 'malformed saved font' in str(exc)
else:
    raise AssertionError('Grouped Undo accepted the malformed child-only snapshot')
assert tree_state() == unchanged

# Palette/icon-only Undo leaves unrelated invalid font fields alone.
raw = ('[Fonts]\ngeneral="' + BAD + '"\n[Appearance]\nicon_theme=old\n').encode()
qt6_path.write_bytes(raw)
tx.apply_file_targets({'qt6ct-settings': raw.replace(b'icon_theme=old', b'icon_theme=new')},
                      label='Native icon only', owned_fields={'qt6ct-settings': {'Appearance/icon_theme'}})
tx.rollback_latest(label='Native icon only')
assert qt6_path.read_bytes() == raw
print('Native Qt serialization passed: fresh Qt5/Qt6 metrics, valid custom attributes, blocked malformed legacy/modern Undo and recovery, safe grouped Undo, unaffected icon-only Undo.')
