"""Real fontconfig matching and production Apply/repair/Undo in a temporary HOME."""
from contextlib import ExitStack
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch
from xml.sax.saxutils import escape

SOURCE = Path(__file__).resolve().parents[1]
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='laf-fontconfig-') as home:
        env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=home + '/config',
                   XDG_STATE_HOME=home + '/state', XDG_DATA_HOME=home + '/data',
                   XDG_CACHE_HOME=home + '/cache', GSETTINGS_BACKEND='keyfile',
                   PYTHONDONTWRITEBYTECODE='1')
        for key in ('FONTCONFIG_FILE', 'FONTCONFIG_PATH', 'FONTCONFIG_SYSROOT'):
            env.pop(key, None)
        subprocess.run([sys.executable, '-B', __file__, 'run'], env=env, check=True)
    raise SystemExit()

sys.path.insert(0, str(SOURCE))
import controller
import fontconfig_policy as adapter
import transaction as tx
import terminal_reload
import appearance_policy as policy
import managed_preferences as preferences
import app_font_actions, browser_font_actions
import manual_app_registry


def match(family, *, config=None):
    env = dict(os.environ)
    if config:
        env['FONTCONFIG_FILE'] = str(config)
    result = subprocess.run(['fc-match', '--format', '%{family[0]}', family],
                            env=env, capture_output=True, text=True, check=True)
    assert not result.stderr.strip(), result.stderr
    return result.stdout


available = set(subprocess.check_output(['fc-list', '--format', '%{family[0]}\n'], text=True).splitlines())
monos = [name for name in ('JetBrainsMono Nerd Font', 'Adwaita Mono', 'DejaVu Sans Mono', 'Liberation Mono')
         if name in available and match(name) == name]
sans = [name for name in ('DejaVu Sans', 'Liberation Sans', 'Adwaita Sans')
        if name in available and match(name) == name]
assert len(monos) >= 2 and sans, 'Native regression needs two installed monospace families and one sans family'
chosen, other, system = monos[0], monos[1], sans[0]
path = Path.home() / tx.FILE_TARGETS['fontconfig-monospace']
path.parent.mkdir(parents=True)


def original_rule(family):
    return ('  <match target="pattern">\r\n'
            '    <test name="family" qual="any"><string>monospace</string></test>\r\n'
            '    <edit name="family" mode="prepend_first" binding="strong">\r\n'
            '      <string>' + escape(family) + '</string>\r\n'
            '    </edit>\r\n  </match>\r\n')


unrelated = ('  <!-- Preserve this unrelated rendering rule and café annotation. -->\r\n'
             '  <match target="font"><edit name="antialias" mode="assign"><bool>true</bool></edit></match>\r\n'
             '  <alias><family>Independent Serif Alias</family><prefer><family>DejaVu Serif</family></prefer></alias>\r\n')
original = ('<?xml version="1.0"?>\r\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\r\n'
            '<fontconfig>\r\n' + unrelated + original_rule(other) + '</fontconfig>\r\n').encode()
path.write_bytes(original)
assert match(chosen) == other, 'The real Omarchy any-family regression was not reproduced'

with ExitStack() as stack:
    # Keep catalog discovery and app/terminal processes outside this native
    # fontconfig test; production builders, Gio, policy and transactions run.
    stack.enter_context(patch.object(controller, 'font_entries', return_value=[
        {'id': 'font:test-system', 'name': system}, {'id': 'font:test-terminal', 'name': chosen}]))
    stack.enter_context(patch.object(controller, 'installed_font_applications', return_value={'desktopApplications': []}))
    stack.enter_context(patch.object(controller, 'validated_apply_status', return_value={'unsupportedCount': 1, 'registeredCount': 0}))
    stack.enter_context(patch.object(controller, 'build_app_targets', return_value=({}, [])))
    stack.enter_context(patch.object(controller, 'build_browser_targets', return_value=({}, [])))
    stack.enter_context(patch.object(terminal_reload, 'reload_fonts', return_value={'requested': [], 'failed': []}))

    def apply(automatic=False):
        return controller.apply_global_fonts('font:test-system', 12, 'font:test-terminal', 12, automatic=automatic)

    result = apply()
    first = result['transaction']
    assert first and result['unsupportedManualCount'] == 1
    assert any(row['app'] == 'Audited applications' for row in result['pendingApplications'])
    repaired = path.read_bytes()
    assert unrelated.encode() in repaired
    assert match(chosen) == chosen and match(other) == other and match(system) == system
    assert match(other + ',monospace') == other
    assert adapter.build(repaired.decode(), chosen).encode() == repaired
    automatic = apply(automatic=True)
    assert automatic['transaction'] is None and automatic['unsupportedManualCount'] == 1
    tx.rollback_latest(label=policy.LABEL_FONTS)
    assert path.read_bytes() == original and match(chosen) == other

    # A bad app or unsupported terminal must not block shared settings or
    # other apps. Actual font transaction and Undo still run in this HOME.
    apps = [{'id': 'mystery.desktop', 'name': 'Mystery terminal', 'framework': 'terminal-emulator'},
            {'id': 'typora.desktop'}, {'id': 'eu.betterbird.Betterbird.desktop'}, {'id': 'brave-browser.desktop'}]
    def app_build(*args):
        if 'typora.desktop' in args[-1]:
            raise ValueError('unsafe Typora settings')
        assert 'eu.betterbird.Betterbird.desktop' in args[-1]
        return {}, [{'app': 'Betterbird', 'action': 'reopen', 'reason': 'test'}]
    with patch.object(controller, 'installed_font_applications', return_value={'desktopApplications': apps}), \
         patch.object(controller, 'build_app_targets', side_effect=app_build), \
         patch.object(controller, 'build_browser_targets', side_effect=ValueError('bad browser preferences')):
        isolated = apply()
        assert isolated['transaction']
        assert {item['app'] for item in isolated['pendingApplications']} >= {'Mystery terminal', 'Typora', 'Betterbird', 'Brave'}
        assert match(chosen) == chosen
        tx.rollback_latest(label=policy.LABEL_FONTS)
        assert path.read_bytes() == original

    css = Path.home() / tx.FILE_TARGETS['typora-base-user-css']
    css.parent.mkdir(parents=True, exist_ok=True)
    css.write_bytes(b'\xffbad css')
    brave = Path.home() / tx.FILE_TARGETS['brave-default-preferences']
    brave.parent.mkdir(parents=True, exist_ok=True)
    brave.write_text('{}')
    state = brave.parent.parent / 'Local State'
    alacritty = Path.home() / tx.FILE_TARGETS['alacritty-config']
    alacritty.parent.mkdir(parents=True, exist_ok=True)
    alacritty.write_text('[font\n')
    for malformed_state in ('[]', '{"profile":[]}'):
        state.write_text(malformed_state)
        actual_apps = [{'id': 'typora.desktop'}, {'id': 'brave-browser.desktop'},
                       {'id': 'Alacritty.desktop', 'framework': 'terminal-emulator'},
                       {'id': 'foot.desktop', 'framework': 'terminal-emulator'}]
        with patch.object(controller, 'installed_font_applications', return_value={'desktopApplications': actual_apps}), \
             patch.object(controller, 'build_app_targets', app_font_actions.build_app_targets), \
             patch.object(controller, 'build_browser_targets', browser_font_actions.build):
            isolated = apply()
            assert isolated['transaction']
            assert {item['app'] for item in isolated['pendingApplications']} >= {'Typora', 'Brave', 'Alacritty.desktop'}
            assert css.read_bytes() == b'\xffbad css' and state.read_text() == malformed_state and alacritty.read_text() == '[font\n'
            foot = Path.home() / tx.FILE_TARGETS['foot-config']
            assert chosen in foot.read_text()
            tx.rollback_latest(label=policy.LABEL_FONTS)
            assert not foot.exists()

    # Unsafe files are isolated before a batch is composed. A Ghostty overlay
    # is inseparable from its config, and no skipped target may be touched.
    ghostty = Path.home() / tx.FILE_TARGETS['ghostty-config']
    overlay = Path.home() / tx.FILE_TARGETS['ghostty-font-overlay']
    ghostty.parent.mkdir(parents=True, exist_ok=True)
    ghostty.write_text('font-size = 11\n')
    sentinel = Path.home() / 'overlay-sentinel'
    sentinel.write_text('untouched')
    overlay.symlink_to(sentinel)
    css.write_text('body { color: red; }\n')
    css.chmod(0o4600)
    alacritty.write_bytes(b'#' + b'x' * tx.MAX_TARGET_BYTES)
    unsafe_apps = [{'id': 'typora.desktop'},
                   {'id': 'com.mitchellh.ghostty.desktop', 'framework': 'terminal-emulator'},
                   {'id': 'Alacritty.desktop', 'framework': 'terminal-emulator'},
                   {'id': 'foot.desktop', 'framework': 'terminal-emulator'}]
    with patch.object(controller, 'installed_font_applications', return_value={'desktopApplications': unsafe_apps}), \
         patch.object(controller, 'build_app_targets', app_font_actions.build_app_targets):
        isolated = apply()
        assert isolated['transaction']
        assert {row['app'] for row in isolated['pendingApplications']} >= {'Typora', 'Alacritty.desktop', 'com.mitchellh.ghostty.desktop'}
        assert ghostty.read_text() == 'font-size = 11\n' and overlay.is_symlink() and sentinel.read_text() == 'untouched'
        assert css.stat().st_mode & 0o4000 and alacritty.stat().st_size == tx.MAX_TARGET_BYTES + 1
        foot = Path.home() / tx.FILE_TARGETS['foot-config']
        assert chosen in foot.read_text() and match(chosen) == chosen
        tx.rollback_latest(label=policy.LABEL_FONTS)
        assert not foot.exists() and overlay.is_symlink()
    css.chmod(0o600)

    # A malformed registry is retained for diagnosis and cannot block the
    # real shared-font transaction or cause its counts to be reported as zero.
    registry = Path(os.environ['XDG_STATE_HOME']) / 'omarchy-look-and-feel/manual-app-controls.json'
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_bytes(b'{invalid audit registry')
    registry.chmod(0o600)
    with patch.object(controller, 'validated_apply_status', manual_app_registry.validated_apply_status):
        isolated = apply()
        assert isolated['transaction']
        assert isolated['registeredManualCount'] is None and isolated['unsupportedManualCount'] is None
        assert any('could not be read safely' in row['reason'] for row in isolated['pendingApplications'])
        assert registry.read_bytes() == b'{invalid audit registry' and match(chosen) == chosen
        tx.rollback_latest(label=policy.LABEL_FONTS)
        assert registry.read_bytes() == b'{invalid audit registry'

    # First use creates a removable target; unrelated existing XML is retained.
    path.unlink()
    apply()
    assert match(chosen) == chosen and match(other) == other
    tx.rollback_latest(label=policy.LABEL_FONTS)
    assert not path.exists()

    # A repair belongs to the original Apply. Undo restores its original rule,
    # while preserving independent additions to the surrounding XML verbatim.
    path.write_bytes(original)
    parent = apply()['transaction']
    drift = ('<?xml version="1.0"?>\n<fontconfig>\n' + unrelated +
             '<!-- Independent edit retained by repair. -->\n' + original_rule(other) + '</fontconfig>\n').encode()
    path.write_bytes(drift)
    child = apply(automatic=True)['transaction']
    assert child and match(chosen) == chosen and match(other) == other
    assert b'Independent edit retained by repair.' in path.read_bytes()
    assert json.loads((tx.transactions_path() / child / 'transaction.json').read_bytes())['parentTransaction'] == parent
    tx.rollback_latest(label=policy.LABEL_FONTS)
    assert path.read_bytes() == drift and match(chosen) == other
    assert json.loads((tx.transactions_path() / child / 'transaction.json').read_bytes())['state'] == 'rolled_back'

    # Exact file shape emitted by the installed omarchy-font-set. Its command
    # also signals/restarts desktop processes, so only its XML output is used
    # here; the real command is exercised separately inside disposable VMs.
    path.write_bytes(original)
    parent = apply()['transaction']
    omarchy_output = ('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
                      '<fontconfig>\n  <match target="pattern">\n'
                      '    <test name="family" qual="any">\n'
                      '      <string>monospace</string>\n    </test>\n'
                      '    <edit name="family" mode="prepend_first" binding="strong">\n'
                      '      <string>' + escape(other) + '</string>\n'
                      '    </edit>\n  </match>\n</fontconfig>\n')
    path.write_text(omarchy_output)
    assert match(chosen) == other
    child = apply(automatic=True)['transaction']
    assert child and match(chosen) == chosen and match(other) == other
    tx.rollback_latest(label=policy.LABEL_FONTS)
    restored = path.read_bytes()
    assert adapter.decode(restored.decode())['monospace-rule'] == adapter.decode(original.decode())['monospace-rule']
    assert unrelated.encode() not in restored, 'Undo resurrected unrelated XML removed outside the plugin'
    assert match(chosen) == other

    # An already-correct original rule still anchors Undo. Its initial Apply
    # must not let a later child's external drift become the before-value.
    correct = adapter.build(original.decode(), chosen).encode()
    path.write_bytes(correct)
    apply()
    path.write_text(omarchy_output)
    assert apply(automatic=True)['transaction']
    tx.rollback_latest(label=policy.LABEL_FONTS)
    assert adapter.decode(path.read_bytes().decode())['monospace-rule'] == adapter.decode(correct.decode())['monospace-rule']
    assert match(chosen) == chosen and match(other) == other

    # Initially absent target: an independent rendering rule survives Undo,
    # while the plugin's inserted monospace rule is removed completely.
    path.unlink()
    apply()
    added = '<!-- Added independently -->\n<match target="font"><edit name="hinting" mode="assign"><bool>false</bool></edit></match>\n'
    path.write_bytes(omarchy_output.replace('</fontconfig>', added + '</fontconfig>').encode())
    assert apply(automatic=True)['transaction']
    tx.rollback_latest(label=policy.LABEL_FONTS)
    assert added.encode() in path.read_bytes()
    assert adapter.decode(path.read_text())['monospace-rule'] == []

    # Unknown conflicting constructs fail during planning, before any journal
    # or target mutation, including automatic repair.
    path.write_bytes(original)
    apply()
    unsupported = path.read_bytes().replace(b'</fontconfig>', b'<include>other.conf</include></fontconfig>')
    path.write_bytes(unsupported)
    journals_before = {p: p.read_bytes() for p in tx.transactions_path().glob('*/transaction.json')}
    for automatic in (False, True):
        try:
            apply(automatic=automatic)
        except tx.TransactionError as exc:
            assert 'includes need a reviewed adapter' in str(exc)
        else:
            raise AssertionError('Unknown XML was silently overwritten')
    assert path.read_bytes() == unsupported
    assert journals_before == {p: p.read_bytes() for p in tx.transactions_path().glob('*/transaction.json')}

    # The same uncertain external changes are refused by field-aware Undo.
    changes = preferences.edits('fontconfig-monospace', original, adapter.build(original.decode(), chosen).encode())
    try:
        preferences.restore('fontconfig-monospace', unsupported, changes)
    except ValueError as exc:
        assert 'includes need a reviewed adapter' in str(exc)
    else:
        raise AssertionError('Undo accepted unknown competing XML')
    independent_rule = adapter.build(original.decode(), system).encode()
    try:
        preferences.restore('fontconfig-monospace', independent_rule, changes)
    except ValueError as exc:
        assert 'changed independently' in str(exc)
    else:
        raise AssertionError('Undo discarded an independently selected font')

# Native matching also proves the first-family condition itself. A minimal
# config intentionally loads the user rule before any package substitutions.
# The normal Omarchy configuration above may already have replaced generic
# monospace before reaching this user file; no contrary guarantee is made.
minimal = Path.home() / 'native-fontconfig.conf'
path.write_text(adapter.build('', other))
minimal.write_text('<?xml version="1.0"?><fontconfig><dir>/usr/share/fonts</dir>'
                   '<cachedir>' + str(Path.home() / 'cache/fontconfig') + '</cachedir>'
                   '<include>' + str(path) + '</include></fontconfig>')
assert match('monospace', config=minimal) == other
assert match(chosen + ',monospace', config=minimal) == chosen

# Refuse unknown competing semantics, external input, and malformed XML.
bad = [
    '<fontconfig><include>other.conf</include></fontconfig>',
    '<fontconfig><alias><family>monospace</family><prefer><family>Other</family></prefer></alias></fontconfig>',
    '<fontconfig><match><edit name="family" mode="assign"><string>Other</string></edit></match></fontconfig>',
    '<fontconfig><match><test name="family"><string>monospace</string></test><edit name="family" mode="assign"><string>Other</string></edit></match></fontconfig>',
    '<!DOCTYPE fontconfig [<!ENTITY custom "monospace">]><fontconfig/>',
    '<!DOCTYPE fontconfig SYSTEM "file:///not-read"><fontconfig/>',
    '<fontconfig><match></fontconfig>',
]
for value in bad:
    try:
        adapter.build(value, chosen)
    except ValueError:
        pass
    else:
        raise AssertionError('Unsupported fontconfig input was accepted')
    try:
        preferences.validate_edits('fontconfig-monospace', {'monospace-rule': {'before': [], 'after': [[value]]}})
    except ValueError:
        pass
    else:
        raise AssertionError('Unreviewed journal rule was accepted')
assert 'A &amp; B &lt;C&gt;' in adapter.build('<fontconfig/>', 'A & B <C>')
# Duplicate reviewed rules retain their independent locations and all bytes
# outside the owned match spans during a field merge.
twice = '<fontconfig>\n' + original_rule(other) + '<!-- middle -->\n' + original_rule(chosen) + '</fontconfig>'
patched = adapter.build(twice, system)
assert adapter.encode(adapter.decode(twice)) == twice
changes = preferences.edits('fontconfig-monospace', twice.encode(), patched.encode())
fresh = patched.replace('<!-- middle -->', '<!-- independently updated middle -->')
restored = preferences.restore('fontconfig-monospace', fresh.encode(), changes).decode()
assert restored == twice.replace('<!-- middle -->', '<!-- independently updated middle -->')
for invalid in (None, 'not-a-list', [None], [original_rule(other)], [original_rule(other).strip() + '<include>other.conf</include>']):
    try:
        preferences.validate_edits('fontconfig-monospace', {'monospace-rule': {'before': [], 'after': [invalid]}})
    except ValueError:
        pass
    else:
        raise AssertionError('Malformed managed fontconfig metadata was accepted')
print('Native fontconfig passed: reproduced explicit-family hijack, preserved explicit fonts, first-only generic rule, exact Apply/Undo, no-op reconciliation, grouped drift repair/Undo, unrelated XML preservation, and unsafe configuration/metadata refusal.')
print('Installed package rules may resolve generic monospace before the user rule; generic default replacement is not claimed.')
