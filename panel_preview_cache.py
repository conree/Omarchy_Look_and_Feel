"""Disposable display data for opening the panel without waiting for discovery.

This cache never authorizes Apply/Undo and contains no application audit or
transaction state. The panel refreshes live inventory before enabling actions.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

SCHEMA_VERSION = 1
MAX_BYTES = 8 * 1024 * 1024


def cache_path() -> Path:
    configured = Path(os.environ.get('XDG_CACHE_HOME', ''))
    base = configured if configured.is_absolute() else Path.home() / '.cache'
    return base / 'omarchy-look-and-feel' / 'panel-previews.json'


def save(inventory: dict) -> None:
    """Atomically replace optional presentation data; callers tolerate I/O failure."""
    display = {key: inventory[key] for key in
               ('catalog_entries', 'preferences', 'desiredAppearance')}
    display['appearance_action_status'] = {
        kind: {'observedValue': status.get('observedValue')}
        for kind, status in inventory.get('appearance_action_status', {}).items()
    }
    raw = json.dumps({'schemaVersion': SCHEMA_VERSION, 'inventory': display},
                     ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(raw) > MAX_BYTES:
        return
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.panel-previews-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
