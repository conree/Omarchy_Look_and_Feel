"""Preview-cache persistence must be optional, private and presentation-only."""
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import panel_preview_cache as cache

record = {'catalog_entries': {'themes': [], 'fonts': []}, 'preferences': {},
          'desiredAppearance': {}, 'appearance_action_status': {
              'theme': {'observedValue': 'test', 'undoAvailable': True, 'transaction': 'private-id'}},
          'global_font_undo_available': True, 'font_application_inventory': {'private': 'audit'}}
with tempfile.TemporaryDirectory(prefix='laf-display-cache-') as directory:
    with patch.dict(os.environ, {'XDG_CACHE_HOME': directory}):
        cache.save(record)
        path = cache.cache_path()
        before = path.read_bytes()
        result = json.loads(before)
        assert result['schemaVersion'] == 1
        assert set(result['inventory']) == {'catalog_entries', 'preferences', 'desiredAppearance', 'appearance_action_status'}
        assert result['inventory']['appearance_action_status'] == {'theme': {'observedValue': 'test'}}
        assert path.stat().st_mode & 0o777 == 0o600
        with patch.object(cache.os, 'replace', side_effect=OSError('disk full')):
            try:
                cache.save({**record, 'preferences': {'changed': True}})
            except OSError:
                pass
            else:
                raise AssertionError('Simulated replacement failure was not raised')
        assert path.read_bytes() == before
        assert list(path.parent.iterdir()) == [path]
        with patch.object(cache, 'MAX_BYTES', 10):
            cache.save(record)
        assert path.read_bytes() == before
    with patch.dict(os.environ, {'XDG_CACHE_HOME': 'relative'}):
        assert cache.cache_path() == Path.home() / '.cache/omarchy-look-and-feel/panel-previews.json'
print('Preview cache passed: display-only fields, private atomic replacement, failure preservation, size bound and XDG fallback.')
