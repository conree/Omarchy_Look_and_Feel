"""Saved intent, bounded reconciliation, and operation-level Undo.

The bar invokes one short-lived reconciliation process periodically. There is
no AI, shell evaluation, privileged helper, or boot integration in this layer.
Busy application profiles remain pending until a subsequent closed interval.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import copy
import fcntl
import json
import os
import re

import transaction as tx

LABEL_THEME = 'Theme settings'
LABEL_FONTS = 'Global font settings'


def validate(data):
    if (not isinstance(data, dict) or data.get('schemaVersion') != 1
            or set(data) != {'schemaVersion', 'fonts', 'theme', 'background'}):
        raise ValueError('unsupported Look and Feel policy schema')
    fonts = data['fonts']
    if fonts is not None:
        if not isinstance(fonts, dict) or set(fonts) != {'systemId', 'systemSize', 'terminalId', 'terminalSize'}:
            raise ValueError('invalid saved font selection')
        for key in ('systemId', 'terminalId'):
            if not isinstance(fonts[key], str) or not fonts[key] or len(fonts[key]) > 300:
                raise ValueError('invalid saved font identity')
        for key in ('systemSize', 'terminalSize'):
            if type(fonts[key]) is not int or not 6 <= fonts[key] <= 48:
                raise ValueError('invalid saved font size')
    theme = data['theme']
    if theme is not None:
        if not isinstance(theme, dict) or set(theme) != {'mode', 'light', 'dark'}:
            raise ValueError('invalid saved theme selection')
        if theme['mode'] not in {'light', 'dark', 'automatic'}:
            raise ValueError('invalid saved theme mode')
        for key in ('light', 'dark'):
            if not isinstance(theme[key], str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', theme[key]):
                raise ValueError('invalid saved theme identity')
    if data['background'] is not None and (not isinstance(data['background'], str) or not data['background']):
        raise ValueError('invalid saved background identity')
    return data


def read():
    path = tx._ensure_home_path(Path.home() / tx.FILE_TARGETS['appearance-policy'], allow_missing_parents=True)
    if not path.exists():
        return {'schemaVersion': 1, 'fonts': None, 'theme': None, 'background': None}
    if path.stat().st_size > tx.MAX_SETTINGS_BYTES:
        raise ValueError('saved appearance policy is too large')
    from managed_preferences import decode
    return decode('appearance-policy', path.read_bytes())


def update(section, value):
    data = copy.deepcopy(read())
    data[section] = value
    validate(data)
    from managed_preferences import encode
    return encode('appearance-policy', data)


@contextmanager
def operation_lock():
    directory = tx.transactions_path().parent
    tx._mkdir_private(directory)
    path = tx._ensure_home_path(directory / 'reconcile.lock')
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise tx.TransactionError('another appearance operation is in progress; retry shortly') from exc
        yield
    finally:
        os.close(fd)


def records():
    directory = tx.transactions_path()
    if not directory.exists():
        return []
    result = []
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_dir() or not tx.TRANSACTION_ID_RE.fullmatch(path.name):
            continue
        if not (path / 'transaction.json').exists():
            continue
        journal = tx._load_journal(path)
        result.append((journal.get('createdAt', ''), path, journal))
    return sorted(result, key=lambda row: (row[0], row[1].name))


def latest(label):
    matches = [row for row in records() if row[2]['state'] == 'committed'
               and row[2].get('label') == label and not row[2].get('parentTransaction')]
    return matches[-1] if matches else None


def changed_targets(targets):
    result = {}
    for name, payload in targets.items():
        path = tx._ensure_home_path(Path.home() / tx.FILE_TARGETS[name], allow_missing_parents=True)
        if not path.exists() or path.read_bytes() != payload:
            result[name] = payload
    return result


def apply_theme(mode, light, dark, *, automatic=False):
    import controller
    import appearance_actions as actions
    from appearance_audit import _theme_mode_expected
    from application_themes import palette, build
    entries = {str(row['name']): row for row in controller.theme_entries() if controller.catalog_entry_eligible(row)}
    if light not in entries or dark not in entries or mode not in {'light', 'dark', 'automatic'}:
        raise tx.TransactionError('one of the saved themes or the mode is unavailable')
    chosen, reason = _theme_mode_expected(mode, controller.display_words(light), controller.display_words(dark))
    if not chosen:
        raise tx.TransactionError(reason)
    target = chosen.casefold().replace(' ', '-')
    # User overlays are last in source order, matching Omarchy's precedence.
    palettes = {}
    for name in {light, dark}:
        source = next((p for p in reversed(entries[name]['source'])
                       if (Path(p) / 'colors.toml').is_file() or (Path(p) / 'alacritty.toml').is_file()), None)
        if source is None:
            raise tx.TransactionError('selected theme has no readable palette')
        palettes[name] = palette(source)
    desktop_ids = {str(app.get('id', '')) for app in controller.installed_font_applications().get('desktopApplications', [])}
    plan = build(palettes[light], palettes[dark], 'light' if target == light else 'dark', mode, desktop_ids, automatic=automatic)
    before = actions._theme_state()
    if before is None:
        raise tx.TransactionError('current theme cannot be read for Undo')
    if actions._background_state() is None:
        raise tx.TransactionError('current background cannot be read; choose an available background before Theme Apply')
    parent = latest(LABEL_THEME) if automatic else None
    if automatic and parent is None:
        raise tx.TransactionError('saved theme has no original Apply transaction')
    if not automatic:
        plan.targets['appearance-policy'] = update('theme', {'mode': mode, 'light': light, 'dark': dark})
    targets = changed_targets(plan.targets) if automatic else plan.targets
    transaction_id = None
    if targets:
        transaction_id = tx.apply_file_targets(targets, label='Automatic theme reconciliation' if automatic else LABEL_THEME,
                                               parent_transaction=parent[1].name if parent else None,
                                               appearance_context={'themeBefore': before, 'themeAfter': target},
                                               owned_fields={
                                                   'wezterm-config': {'theme'},
                                                   'appearance-policy': {'theme'},
                                                   'gtk3-settings': {'Settings/gtk-theme-name', 'Settings/gtk-application-prefer-dark-theme'},
                                                   'gtk4-settings': {'Settings/gtk-theme-name', 'Settings/gtk-application-prefer-dark-theme'},
                                                   'qt5ct-settings': {'Appearance/custom_palette', 'Appearance/color_scheme_path'},
                                                   'qt6ct-settings': {'Appearance/custom_palette', 'Appearance/color_scheme_path'},
                                                   'typora-base-user-css': {'body'},
                                               })
    # Saving desired state is durable before this separately journaled command.
    # A crash or failed command is retried on the next tick; no success is
    # reported for the command until its own readback succeeds.
    outcome = actions.apply_action('theme', target, set(entries))
    import theme_runtime
    if outcome['state'] == 'already-current' and (not automatic or theme_runtime.needs_refresh()):
        theme_runtime.refresh()
    outcome["runtimeRefresh"] = theme_runtime.LAST_REFRESH
    for name in theme_runtime.LAST_REFRESH.get('terminalReload', {}).get('failed', []):
        plan.wait(name, 'reload', 'Settings saved, but the running terminal could not be refreshed; reopen it or retry Apply.')
    outcome.update(applicationTransaction=transaction_id, pendingApplications=plan.pending,
                   configuredSurfaces=plan.surfaces, selectionReason=reason,
                   automaticFutureSwitching='while-plugin-loaded', renderedAppearanceVerified=False,
                   undoAvailable=True)
    return outcome


def recover_theme_undos():
    import appearance_actions as actions
    for _, path, journal in records():
        if not journal.get('themeUndoPending'):
            continue
        context = journal.get('appearanceContext', {})
        before = context.get('themeBefore')
        if not isinstance(before, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', before):
            raise tx.TransactionError('invalid saved theme Undo target')
        if journal['state'] != 'rolled_back':
            # File group recovery must finish before applying the old theme.
            raise tx.TransactionError('theme file Undo needs recovery before the theme can be restored')
        current = actions._theme_state()
        if current not in {before, journal.get('themeUndoExpected')}:
            raise tx.TransactionError('theme changed independently while Undo was pending; preserving it')
        outcome = actions.apply_action('theme', before, {before})
        if outcome['state'] == 'already-current':
            import theme_runtime
            theme_runtime.refresh()
        journal['themeUndoPending'] = False
        tx._write_journal(path / 'transaction.json', journal)


def undo_theme():
    row = latest(LABEL_THEME)
    if row is None:
        if any(item[2].get('label') == LABEL_THEME for item in records()):
            raise tx.TransactionError('there is no saved theme operation to undo')
        from appearance_actions import rollback_action
        return rollback_action('theme')  # Pre-policy transaction migration.
    _, path, journal = row
    import appearance_actions as actions
    owned = {journal['appearanceContext']['themeAfter'], journal['appearanceContext']['themeBefore']}
    for _, child_path, child in records():
        if child.get('parentTransaction') == path.name and child['state'] == 'committed':
            owned.add(child.get('appearanceContext', {}).get('themeAfter'))
    current = actions._theme_state()
    if current not in owned:
        raise tx.TransactionError('theme changed independently; preserving it instead of undoing an unrelated selection')
    # Immutable historical drift must refuse before durable Undo intent, so
    # unrelated future operations remain usable.
    with tx._locked(tx.transactions_path()):
        tx._prepare_group_undo(tx.transactions_path(), path, journal)
    journal['themeUndoExpected'] = current
    journal['themeUndoPending'] = True
    journal['groupUndoPending'] = True
    tx._write_journal(path / 'transaction.json', journal)
    restored = journal['appearanceContext']['themeBefore']
    tx.rollback_latest(label=LABEL_THEME)
    recover_theme_undos()
    import theme_runtime
    pending = [{'app': name, 'action': 'reload', 'reason': 'Settings restored, but the running terminal could not be refreshed; reopen it.'}
               for name in theme_runtime.LAST_REFRESH.get('terminalReload', {}).get('failed', [])]
    if any(item['id'] == 'hypr-qt-integration' and item.get('managedEdits') for item in journal['targets']):
        pending.append({'app': 'Qt', 'action': 'login', 'reason': 'Qt integration was restored. Sign out and back in to refresh all application launchers.'})
    return {'rolledBack': path.name, 'kind': 'theme', 'restored': restored, 'readback': restored,
            'runtimeRefresh': theme_runtime.LAST_REFRESH, 'pendingApplications': pending}


def reconcile():
    import controller
    policy = read()
    pending, results = [], {}
    for section in ('theme', 'fonts'):
        value = policy[section]
        if value is None:
            continue
        try:
            if section == 'theme':
                result = apply_theme(value['mode'], value['light'], value['dark'], automatic=True)
            else:
                result = controller.apply_global_fonts(value['systemId'], value['systemSize'],
                                                       value['terminalId'], value['terminalSize'], automatic=True)
            pending.extend(result.get('pendingApplications', []))
            if result.get('blocked'):
                pending.append({'app': 'Fonts', 'action': 'manual-audit',
                                'reason': 'A registered application no longer has a verified font adapter; review its application audit before applying fonts.'})
            for name in result.get('terminalReload', {}).get('failed', []):
                pending.append({'app': name, 'action': 'reload', 'reason': 'Saved fonts could not be loaded into its running window; reopen it or retry Apply.'})
            results[section] = result
        except (OSError, RuntimeError, ValueError) as exc:
            pending.append({'app': section, 'action': 'retry', 'reason': str(exc)})
    status = {'schemaVersion': 1, 'pendingApplications': pending, 'results': results,
              'renderedAppearanceVerified': False}
    path = tx.transactions_path().parent / 'reconcile-status.json'
    payload = (json.dumps(status, ensure_ascii=False, sort_keys=True) + '\n').encode()
    if not path.exists() or path.read_bytes() != payload:
        tx._atomic_write(path, payload, 0o600)
    return status
