"""Capability failures must precede recovery and all Apply writes."""
from pathlib import Path
import os, sys, tempfile, subprocess
from unittest.mock import patch
SOURCE=Path(__file__).resolve().parents[1]
if len(sys.argv)==1:
    with tempfile.TemporaryDirectory(prefix='laf-requirements-') as home:
        subprocess.run([sys.executable,'-B',__file__,'run'],check=True,env=dict(os.environ,HOME=home,XDG_CONFIG_HOME=home+'/.config',XDG_STATE_HOME=home+'/.local/state',GSETTINGS_BACKEND='keyfile'))
    raise SystemExit()
sys.path.insert(0,str(SOURCE))
import controller, requirements, appearance_policy
saved={'theme':{'mode':'dark','light':'one','dark':'two'},'fonts':{},'icons':None}
for argv,area in ((['apply-global-fonts','a','12','b','12'],'fonts'),(['apply-theme','dark','one','two'],'theme'),(['apply-catalog-action','icons','x'],'icons'),(['apply-catalog-action','background','x'],'background'),(['reconcile'],'theme')):
    with patch.object(requirements,'require',side_effect=RuntimeError('Missing dependency: '+area)) as require, patch.object(controller,'recover_pending') as recover, patch.object(controller,'_main') as main, patch.object(appearance_policy,'read',return_value=saved):
        assert controller.main(argv)==1
        require.assert_called_once_with(area)
        recover.assert_not_called();main.assert_not_called()
with patch.object(requirements.shutil,'which',return_value=None):
    result=requirements.inspect()
    for area in ('fonts','theme','background'):
        try: requirements.require(area)
        except RuntimeError as exc: assert 'Install' in str(exc)
        else: raise AssertionError('missing executable ignored')
    assert not result['ready']
with patch.dict(sys.modules, {'PySide6.QtGui': None}), patch('qt_integration.plugins',return_value={}):
    for area in ('fonts','font-restore'):
        try: requirements.require(area)
        except RuntimeError as exc: assert 'pyside6' in str(exc)
        else: raise AssertionError('native Qt font validation prerequisite ignored')
    for argv in (['apply-global-fonts','a','12','b','12'], ['rollback-global-fonts']):
        with patch.object(controller,'recover_pending') as recover, patch.object(controller,'_main') as main:
            assert controller.main(argv)==1
            recover.assert_not_called();main.assert_not_called()
print('Missing dependency gates precede recovery/Apply, including background and automatic theme repair.')
