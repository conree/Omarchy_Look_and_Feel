"""Flea's own UI text-size override in its JSON state file.

Flea can follow the Omarchy shell base or pin one of its 9–20 px stops. The
plugin owns the "follow" state so a font Apply does not leave Flea on an old
pinned size; its shell type tokens then provide the actual sizes.
"""
from __future__ import annotations

import json
from pathlib import Path

TARGET = 'flea-ui-state'
FIELD = 'display/textSize'
SYSTEM = {'mode': 'system'}


def _text_size(value):
    if not isinstance(value, dict) or set(value) != {'mode'}:
        raise ValueError('Flea text size needs its mode')
    mode = value['mode']
    if mode != 'system' and (type(mode) is not int or not 9 <= mode <= 20):
        raise ValueError('Flea text size mode is invalid')
    return value


def decode(raw: bytes):
    text = raw.decode('utf-8')
    if not text.strip():
        return {'_text': ''}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError('Flea UI state is not valid JSON') from exc
    if not isinstance(data, dict):
        raise ValueError('Flea UI state must be an object')
    display = data.get('display', {})
    if not isinstance(display, dict):
        raise ValueError('Flea display state must be an object')
    result = {'_text': text}
    if 'textSize' in display:
        result[FIELD] = _text_size(display['textSize'])
    return result


def encode(data):
    text = data.get('_text', '')
    current = decode(text.encode()) if text.strip() else {'_text': ''}
    wanted = data.get(FIELD)
    if wanted == current.get(FIELD):
        return text.encode()
    obj = json.loads(text) if text.strip() else {}
    if 'display' in obj:
        display = obj['display']
        if not isinstance(display, dict):
            raise ValueError('Flea display state must be an object')
    elif wanted is None:
        return text.encode()
    else:
        display = {}
        obj['display'] = display
    if wanted is None:
        display.pop('textSize', None)
    else:
        display['textSize'] = _text_size(wanted)
    return (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode()


def build():
    from global_font_actions import HOME, _read
    from transaction import FILE_TARGETS
    text = _read(HOME / FILE_TARGETS[TARGET], allow_missing=True)
    data = decode(text.encode()) if text.strip() else {'_text': ''}
    data[FIELD] = dict(SYSTEM)
    return encode(data)
