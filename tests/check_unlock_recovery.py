"""Isolated regression checks: never execute live Omarchy commands."""

from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import json
import sys
import uuid

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import appearance_actions as actions
import transaction


def fixture(stack, temporary):
    root = Path(temporary)
    observed = {kind: 'after' for kind in actions.ACTION_KINDS}
    setters = {}
    handlers = {}
    for kind in actions.ACTION_KINDS:
        setter = Mock(side_effect=lambda value, kind=kind: observed.__setitem__(kind, value))
        setters[kind] = setter
        handlers[kind] = (lambda kind=kind: observed[kind], setter)
    stack.enter_context(patch.object(transaction, '_home', return_value=root))
    stack.enter_context(patch.object(actions, 'transactions_path', return_value=root / 'transactions'))
    stack.enter_context(patch.object(actions, 'HANDLERS', handlers))
    stack.enter_context(patch.object(actions, '_omarchy', side_effect=AssertionError('LIVE COMMAND FORBIDDEN')))
    return observed, setters


def seed(kind, state, before='before', after='after'):
    action_id = '20261024T000000Z-' + uuid.uuid4().hex[:12]
    directory = actions._kind_root(kind) / action_id
    directory.mkdir()
    journal = {'schemaVersion': 1, 'id': action_id, 'kind': kind,
               'state': state, 'before': before, 'after': after}
    actions._write_journal(directory / 'action.json', journal)
    return directory / 'action.json'


count = 0
for pending_state in ('prepared', 'applying', 'rolling_back', 'recovery_required'):
    for requested_kind in ('theme', 'background'):
        for operation in ('apply', 'undo'):
            with TemporaryDirectory(prefix='laf-recovery-guard-') as tmp, ExitStack() as stack:
                observed, setters = fixture(stack, tmp)
                unlock = seed('unlock', pending_state)
                background = seed('background', 'applying')
                originals = {path: path.read_bytes() for path in (unlock, background)}
                try:
                    if operation == 'apply':
                        actions.apply_action(requested_kind, 'fresh', {'fresh'})
                    else:
                        actions.rollback_action(requested_kind)
                except transaction.TransactionError as exc:
                    assert 'explicit unlock recovery' in str(exc), str(exc)
                else:
                    raise AssertionError('non-unlock action accepted pending unlock recovery')
                assert all(setter.call_count == 0 for setter in setters.values())
                assert all(path.read_bytes() == data for path, data in originals.items())
                count += 1

# The temporary unlock gate must preserve journals without invoking any setter.
for operation in ('apply', 'undo'):
    for pending_state in ('prepared', 'applying', 'rolling_back', 'recovery_required', 'committed'):
        with TemporaryDirectory(prefix='laf-unlock-gate-') as tmp, ExitStack() as stack:
            observed, setters = fixture(stack, tmp)
            journal = seed('unlock', pending_state)
            original = journal.read_bytes()
            try:
                if operation == 'apply':
                    actions.apply_action('unlock', 'fresh', {'fresh'})
                else:
                    actions.rollback_action('unlock')
            except transaction.TransactionError as exc:
                assert 'preview-only' in str(exc), str(exc)
            else:
                raise AssertionError('unlock write gate was bypassed')
            assert all(not setter.called for setter in setters.values())
            assert journal.read_bytes() == original
            count += 1

# Direct setter calls are blocked too, before invoking any Omarchy command.
with patch.object(actions, '_omarchy', side_effect=AssertionError('LIVE COMMAND FORBIDDEN')) as command:
    try:
        actions._set_unlock('default')
    except transaction.TransactionError as exc:
        assert 'preview-only' in str(exc)
    else:
        raise AssertionError('unlock setter gate was bypassed')
    assert not command.called
    count += 1

# Ordinary background recovery remains available when there is no pending unlock.
with TemporaryDirectory(prefix='laf-background-recovery-') as tmp, ExitStack() as stack:
    observed, setters = fixture(stack, tmp)
    pending = seed('background', 'applying')
    result = actions.apply_action('background', 'fresh', {'fresh'})
    assert result['state'] == 'committed'
    assert [call.args for call in setters['background'].call_args_list] == [('before',), ('fresh',)]
    assert not setters['unlock'].called
    assert json.loads(pending.read_text())['state'] == 'rolled_back'
    count += 1

print(f'{count} isolated recovery checks passed; all setters were mocks; no live commands or configuration writes.')
