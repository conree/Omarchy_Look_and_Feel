"""Journaled GNOME desktop font settings, including their unset/default state."""
from __future__ import annotations

SCHEMA = 'org.gnome.desktop.interface'
KEYS = {'font-name', 'document-font-name', 'monospace-font-name'}


def _settings():
    import gi
    gi.require_version('Gio', '2.0')
    from gi.repository import Gio
    source = Gio.SettingsSchemaSource.get_default()
    schema = source.lookup(SCHEMA, True) if source else None
    if schema is None:
        raise RuntimeError('the desktop font settings schema is unavailable')
    return Gio, Gio.Settings.new_full(schema, None, None)


def _user_value(settings, key):
    value = settings.get_user_value(key)
    return value.get_string() if value is not None else None


def validate(records):
    if not isinstance(records, list) or len(records) != len(KEYS):
        raise RuntimeError('invalid desktop font snapshot')
    seen = set()
    for row in records:
        if not isinstance(row, dict) or set(row) != {'key', 'before', 'effectiveBefore', 'after'}:
            raise RuntimeError('invalid desktop font record')
        if row['key'] not in KEYS or row['key'] in seen:
            raise RuntimeError('invalid desktop font key')
        seen.add(row['key'])
        for key in ('before', 'effectiveBefore', 'after'):
            value = row[key]
            if key == 'before' and value is None:
                continue
            if not isinstance(value, str) or not value or len(value) > 300 or any(ord(c) < 32 for c in value):
                raise RuntimeError('invalid desktop font value')


def capture(values):
    if set(values) != KEYS:
        raise RuntimeError('unsupported desktop font settings')
    _, settings = _settings()
    records = []
    for key in sorted(KEYS):
        if not settings.is_writable(key):
            raise RuntimeError('a desktop font setting is locked')
        records.append({'key': key, 'before': _user_value(settings, key),
                        'effectiveBefore': settings.get_string(key), 'after': values[key]})
    validate(records)
    return records


def apply(records):
    validate(records)
    Gio, settings = _settings()
    for row in records:
        if (_user_value(settings, row['key']) != row['before']
                or settings.get_string(row['key']) != row['effectiveBefore']):
            raise RuntimeError('desktop fonts changed independently before Apply')
    settings.delay()
    for row in records:
        if not settings.set_string(row['key'], row['after']):
            settings.revert()
            raise RuntimeError('a desktop font setting could not be written')
    settings.apply()
    Gio.Settings.sync()
    _, readback = _settings()
    if any(readback.get_string(row['key']) != row['after'] or _user_value(readback, row['key']) != row['after'] for row in records):
        raise RuntimeError('desktop font readback did not match the requested values')


def restore(records):
    validate(records)
    Gio, settings = _settings()
    errors = []
    restore_rows = []
    for row in records:
        current = _user_value(settings, row['key'])
        if current == row['before']:
            continue
        if current != row['after']:
            errors.append(row['key'])
            continue
        if not settings.is_writable(row['key']):
            errors.append(row['key'])
            continue
        restore_rows.append(row)
    settings.delay()
    for row in restore_rows:
        if row['before'] is None:
            settings.reset(row['key'])
        elif not settings.set_string(row['key'], row['before']):
            settings.revert()
            raise RuntimeError('desktop font restoration was refused')
    settings.apply()
    Gio.Settings.sync()
    _, readback = _settings()
    for row in restore_rows:
        if _user_value(readback, row['key']) != row['before']:
            errors.append(row['key'])
    if errors:
        raise RuntimeError('desktop font recovery incomplete; preserving independent or locked settings: ' + ', '.join(errors))
