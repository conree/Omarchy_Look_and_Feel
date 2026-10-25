from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import ExitStack
from unittest.mock import patch
import json,os,sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import transaction as tx
import browser_font_actions as app
old={'webkit':{'webprefs':{'fonts':{'standard':{'Zyyy':'Old','Jpan':'Keep Japanese'},'fixed':{'Zyyy':'Old Mono'}},'default_font_size':18}},'unrelated':{'value':1}}
wanted={'standard':'Avenir Next','sansserif':'Avenir Next','serif':'Avenir Next','fixed':'Comic Code Ligatures','size':16,'fixed_size':16}
for bad in ({'webkit':None},{'webkit':{'webprefs':None}},{'webkit':{'webprefs':{'fonts':7}}}):
    try:app.values(bad)
    except ValueError:pass
    else:raise AssertionError('invalid structure accepted')
with TemporaryDirectory(prefix='laf-browser-fonts-') as tmp,ExitStack() as stack:
    home=Path(tmp);path=home/tx.FILE_TARGETS['brave-default-preferences'];path.parent.mkdir(parents=True)
    stack.enter_context(patch.object(tx,'_home',return_value=home))
    stack.enter_context(patch.dict(os.environ,{'XDG_CONFIG_HOME':str(home/'.config'),'XDG_STATE_HOME':str(home/'.local/state')}))
    path.write_text(json.dumps(old))
    payload=json.dumps(app.merge(old,wanted)).encode()
    newest=json.loads(path.read_text());newest['saved.before.lock']='keep';path.write_text(json.dumps(newest))
    tid=tx.apply_file_targets({'brave-default-preferences':payload},label='browser')
    current=json.loads(path.read_text());assert app.values(current)==wanted
    assert current['saved.before.lock']=='keep'
    assert current['webkit']['webprefs']['fonts']['standard']['Jpan']=='Keep Japanese'
    current['unrelated']['value']=2;current['after.startup']=True;path.write_text(json.dumps(current))
    assert tx.rollback_latest(label='browser')==tid
    restored=json.loads(path.read_text());assert app.values(restored)==app.values(old)
    assert restored['after.startup'] and restored['unrelated']['value']==2
    # Exact-snapshot Undo also refuses before any write when browser is running.
    tid=tx.apply_file_targets({'brave-default-preferences':payload},label='browser')
    lock=path.parent.parent/'SingletonLock';lock.symlink_to('running-browser')
    before=path.read_bytes()
    try:tx.rollback_latest(label='browser')
    except RuntimeError:pass
    else:raise AssertionError('running browser Undo allowed')
    assert path.read_bytes()==before
    lock.unlink();assert tx.rollback_latest(label='browser')==tid
    # Revalidate profile selection even for stale prepared payloads.
    state=path.parent.parent/'Local State';state.write_text('{"profile":{"last_used":"Profile 1"}}')
    before=path.read_bytes()
    try:tx.apply_file_targets({'brave-default-preferences':payload},label='browser')
    except RuntimeError:pass
    else:raise AssertionError('non-selected profile written')
    assert path.read_bytes()==before
    state.unlink()
    # A browser startup detected after writing leaves recoverable state, never
    # overwrites the now-live profile during rollback, and recovers after close.
    real_write=tx._atomic_write
    def start_browser(target,payload,mode):
        real_write(target,payload,mode)
        if target==path:lock.symlink_to('running-browser')
    with patch.object(tx,'_atomic_write',side_effect=start_browser):
        try:tx.apply_file_targets({'brave-default-preferences':payload},label='startup')
        except tx.TransactionError:pass
        else:raise AssertionError('concurrent startup ignored')
    journals=[json.loads(p.read_text()) for p in tx.transactions_path().glob('*/transaction.json')]
    assert any(j.get('label')=='startup' and j['state']=='recovery_required' for j in journals)
    lock.unlink();assert tx.recover_pending()
print('Browser tests passed: merge/Undo preservation, malformed data, closed-profile guards, selected-profile recheck, startup interruption and recovery.')
