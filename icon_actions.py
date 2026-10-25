"""One installed icon-theme selection shared by GTK, Qt and desktop settings."""
from pathlib import Path
import configparser
import re

LABEL = 'Icon settings'


def resolve(identity):
    from controller import icon_entries
    entry = next((row for row in icon_entries() if row['id'] == identity), None)
    if entry is None or not selectable(entry['name'], entry['source']):
        raise ValueError('The selected installed icon theme is unavailable.')
    return entry['name']


def supported_name(name):
    # INI whitespace, interpolation, lists and quoted values are ambiguous
    # across GTK and Qt; accept the portable installed-theme identifier subset.
    return isinstance(name, str) and bool(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.+-]{0,199}', name))


def metadata(name, sources):
    """Validate the first index.theme, without loading or rendering icon files.

    Cursor themes also use index.theme but lack icon directory declarations.
    Hidden fallback themes remain valid metadata, but are not selector choices.
    Later search roots cannot repair an invalid index that shadows them.
    """
    if not supported_name(name) or not sources:
        return None
    path = Path(sources[0]) / 'index.theme'
    try:
        if path.stat().st_size > 1024 * 1024:
            return None
        parser = configparser.RawConfigParser(strict=True)
        parser.read_string(path.read_text(encoding='utf-8'))
        if not parser.get('Icon Theme', 'Name', fallback='').strip():
            return None
        directories = [value.strip() for value in parser.get('Icon Theme', 'Directories', fallback='').split(',') if value.strip()]
        if not directories:
            return None
        directories += [value.strip() for value in parser.get('Icon Theme', 'ScaledDirectories', fallback='').split(',') if value.strip()]
        for directory in directories:
            parts = directory.split('/')
            if any(part in ('', '.', '..') for part in parts):
                return None
            if not parser.has_section(directory) or parser.getint(directory, 'Size', fallback=0) <= 0:
                return None
        return {'name': parser.get('Icon Theme', 'Name'),
                'hidden': parser.getboolean('Icon Theme', 'Hidden', fallback=False)}
    except (OSError, configparser.Error, UnicodeError, ValueError):
        return None


def selectable(name, sources):
    info = metadata(name, sources)
    return info is not None and not info['hidden']


def build(name):
    from application_themes import read, ini
    from qt_integration import plugins
    targets = {}
    for version in (3, 4):
        key = f'gtk{version}-settings'
        targets[key] = ini(read(key).decode(), 'Settings', 'gtk-icon-theme-name', name).encode()
    for version in (5, 6):
        key = f'qt{version}ct-settings'
        raw = read(key)
        if raw or version in plugins():
            targets[key] = ini(raw.decode(), 'Appearance', 'icon_theme', name).encode()
    return targets


def apply(identity, *, automatic=False):
    import appearance_policy as policy
    import transaction as tx
    import desktop_fonts as desktop
    name = resolve(identity)
    targets = build(name)
    values = {'icon-theme': name}
    parent = policy.latest(LABEL) if automatic else None
    if automatic and parent is None:
        raise tx.TransactionError('Saved icons have no original Apply transaction.')
    desktop_changed = True
    if automatic:
        targets = policy.changed_targets(targets)
        desktop_changed = any(row['effectiveBefore'] != row['after'] for row in desktop.capture(values))
        if desktop_changed and not targets:
            targets['gtk3-settings'] = build(name)['gtk3-settings']
    else:
        targets['appearance-policy'] = policy.update('icons', identity)
    owned = {'appearance-policy': {'icons'},
             'gtk3-settings': {'Settings/gtk-icon-theme-name'},
             'gtk4-settings': {'Settings/gtk-icon-theme-name'},
             'qt5ct-settings': {'Appearance/icon_theme'},
             'qt6ct-settings': {'Appearance/icon_theme'}}
    identity = tx.apply_file_targets(targets, label='Automatic icon reconciliation' if automatic else LABEL,
                                     parent_transaction=parent[1].name if parent else None,
                                     desktop_font_values=values if desktop_changed else None,
                                     owned_fields=owned) if targets else None
    return {'kind': 'icons', 'state': 'committed' if identity else 'already-current',
            'transaction': identity, 'after': name, 'readback': name, 'desktopIconsVerified': True,
            'renderedAppearanceVerified': False, 'pendingApplications': [], 'undoAvailable': True}


def undo():
    import transaction as tx
    import desktop_fonts as desktop
    identity = tx.rollback_latest(label=LABEL)
    actual = desktop.effective(desktop._settings()[1], 'icon-theme')
    return {'kind': 'icons', 'rolledBack': identity, 'restored': actual, 'readback': actual}


def status():
    import appearance_policy as policy
    import desktop_fonts as desktop
    row = policy.latest(LABEL)
    try:
        value = desktop.effective(desktop._settings()[1], 'icon-theme')
    except (ImportError, OSError, RuntimeError):
        value = ''
    return {'undoAvailable': row is not None, 'observedValue': value}
