"""Capability failures must precede recovery and all Apply writes."""
from pathlib import Path
from contextlib import redirect_stdout
import io, json, os, sys, tempfile, subprocess
from unittest.mock import patch
SOURCE=Path(__file__).resolve().parents[1]
if len(sys.argv)==1:
    with tempfile.TemporaryDirectory(prefix='laf-requirements-') as home:
        subprocess.run([sys.executable,'-B',__file__,'run'],check=True,env=dict(os.environ,HOME=home,XDG_CONFIG_HOME=home+'/.config',XDG_STATE_HOME=home+'/.local/state',GSETTINGS_BACKEND='keyfile'))
    raise SystemExit()
sys.path.insert(0,str(SOURCE))
import controller, requirements, appearance_policy
saved={'theme':{'mode':'dark','light':'one','dark':'two'},'fonts':{},'icons':None}
for argv,area in ((['apply-global-fonts','a','12','b','12'],'fonts'),(['apply-theme','dark','one','two'],'theme'),(['apply-catalog-action','icons','x'],'icons'),(['apply-catalog-action','background','x'],'background')):
    with patch.object(requirements,'require',side_effect=RuntimeError('Missing dependency: '+area)) as require, patch.object(controller,'recover_pending') as recover, patch.object(controller,'_main') as main, patch.object(appearance_policy,'read',return_value=saved):
        assert controller.main(argv)==1
        require.assert_called_once_with(area)
        recover.assert_not_called();main.assert_not_called()

# Reconciliation must isolate capability failures after safe recovery. A missing
# theme dependency cannot suppress a healthy font repair (and vice versa).
saved = {'theme': {'mode': 'dark', 'light': 'one', 'dark': 'two'},
         'fonts': {'systemId': 'a', 'systemSize': 12, 'terminalId': 'b', 'terminalSize': 12},
         'icons': None, 'opacity': None, 'blur': None}
import application_restarts, opacity_actions, blur_actions
for missing in ('theme', 'fonts'):
    def require(area):
        if area == missing: raise RuntimeError('Missing ' + area)
    out = io.StringIO()
    with patch.object(appearance_policy, 'read', return_value=saved), \
         patch.object(requirements, 'require', side_effect=require), \
         patch.object(controller, 'recover_pending', return_value=[]), \
         patch.object(appearance_policy, 'recover_theme_undos'), \
         patch.object(application_restarts, 'observe'), \
         patch.object(application_restarts, 'add_to_result', side_effect=lambda result: result), \
         patch.object(appearance_policy, 'apply_theme', return_value={'pendingApplications': []}) as theme, \
         patch.object(controller, 'apply_global_fonts', return_value={'pendingApplications': []}) as fonts, \
         patch.object(opacity_actions, '_refresh', return_value=({}, [])), \
         patch.object(blur_actions, 'refresh'), redirect_stdout(out):
        assert controller.main(['reconcile']) == 0
        result = json.loads(out.getvalue())
        assert any(row['app'] == missing and row['reason'] == 'Missing ' + missing for row in result['pendingApplications'])
        assert result['pendingBySection'][missing] == [row for row in result['pendingApplications'] if row['app'] == missing]
        assert theme.called == (missing != 'theme')
        assert fonts.called == (missing != 'fonts')
        assert ('theme' in result['results']) == (missing != 'theme')
        assert ('fonts' in result['results']) == (missing != 'fonts')

opacity_saved = dict(saved, theme=None, fonts=None, opacity=50)
with patch.object(appearance_policy, 'read', return_value=opacity_saved), \
     patch.object(requirements, 'require', side_effect=RuntimeError('Missing opacity')), \
     patch.object(opacity_actions, '_refresh') as refresh, \
     patch.object(blur_actions, 'refresh'), \
     patch.object(application_restarts, 'add_to_result', side_effect=lambda result: result):
    result = appearance_policy.reconcile()
    assert any(row['app'] == 'opacity' and row['reason'] == 'Missing opacity' for row in result['pendingApplications'])
    assert 'opacity' not in result['results']
    refresh.assert_not_called()

with patch.object(appearance_policy, 'read', return_value=dict(saved, theme=None)), \
     patch.object(requirements, 'require'), \
     patch.object(controller, 'apply_global_fonts', return_value={'pendingApplications': [], 'terminalReload': {'failed': ['kitty']}}), \
     patch.object(opacity_actions, '_refresh', return_value=({}, [])), \
     patch.object(blur_actions, 'refresh'), \
     patch.object(application_restarts, 'add_to_result', side_effect=lambda result: result):
    result = appearance_policy.reconcile()
    assert any(row['app'] == 'kitty' and row['action'] == 'reload' for row in result['pendingBySection']['fonts'])
    assert result['pendingBySection']['fonts'][0] in result['pendingApplications']

# When no font policy exists, successful registry validation can still resolve
# a legacy audit blocker; read errors are explicitly unknown, never zero.
for audit_result in ({'registeredCount': 0, 'unsupportedCount': 0}, RuntimeError('damaged registry')):
    with patch.object(appearance_policy, 'read', return_value=dict(saved, theme=None, fonts=None)), \
         patch.object(controller, 'validated_apply_status', side_effect=audit_result if isinstance(audit_result, Exception) else None,
                      return_value=None if isinstance(audit_result, Exception) else audit_result), \
         patch.object(opacity_actions, '_refresh', return_value=({}, [])), \
         patch.object(blur_actions, 'refresh'), \
         patch.object(application_restarts, 'add_to_result', side_effect=lambda result: result):
        result = appearance_policy.reconcile()
        assert result['auditRegistryStatus'] == (None if isinstance(audit_result, Exception) else audit_result)

# An incomplete transaction still takes precedence: if recovery cannot safely
# finish, no section is reconciled even if other capabilities are available.
with patch.object(appearance_policy, 'read', return_value=saved), \
     patch.object(controller, 'recover_pending', side_effect=RuntimeError('recovery required')), \
     patch.object(application_restarts, 'observe'), \
     patch.object(appearance_policy, 'reconcile') as reconcile:
    assert controller.main(['reconcile']) == 1
    reconcile.assert_not_called()
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
print('Manual prerequisite gates, isolated automatic repair, and recovery precedence passed.')
