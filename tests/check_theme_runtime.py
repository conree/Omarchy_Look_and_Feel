"""Recognize supported headless layouts without accepting an unguarded refresh."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme_runtime import require_offline_support

setup = '''if [[ ${OMARCHY_THEME_HEADLESS:-} == "1" ]]; then
  THEME_HEADLESS=1
fi
'''
guard = 'if [[ $THEME_HEADLESS != "1" ]]; then\n'
intro = '''  # Reload Hyprland only when no intro handles it.
  if [[ -z $THEME_INTRO_TOKEN ]]; then
    visible_theme_commands+=(omarchy-restart-hyprctl)
  fi
'''
refresh = '  run_parallel "${visible_theme_commands[@]}"\n'
cases = [
    (setup + guard + refresh + 'fi\n', True),
    (setup + guard + intro + refresh + 'fi\n', True),
    (setup + guard + 'fi\n' + refresh, False),
    (setup + guard + intro + 'fi\n' + refresh, False),
    (setup + refresh, False),
    ('# ' + setup.replace('\n', '\n# ') + guard + refresh + 'fi\n', False),
]
with tempfile.TemporaryDirectory(prefix='laf-headless-') as tmp:
    root = Path(tmp)
    script = root / 'bin/omarchy-theme-set'
    script.parent.mkdir()
    for source, expected in cases:
        script.write_text(source)
        try:
            require_offline_support(root)
        except RuntimeError:
            assert not expected, source
        else:
            assert expected, source
    with patch.object(Path, 'is_file', return_value=False):
        try:
            require_offline_support(root)
        except RuntimeError:
            pass
        else:
            raise AssertionError('missing script accepted')
print('Original and intro-aware headless guards accepted; unguarded refresh rejected.')
