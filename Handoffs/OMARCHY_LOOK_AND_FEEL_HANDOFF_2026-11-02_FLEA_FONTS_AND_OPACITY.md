# Look & Feel handoff: generic fonts and Flea opacity

Date: 2026-11-02 (America/Phoenix).

## Repository and authorization

Authoritative repository: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`.
Installed plugin: `/home/si/.config/omarchy/plugins/si.omarchy-look-and-feel`
(symlink to this repository). Branch: `main`.

The owner authorized local generic-font integration and Flea opacity controls,
then requested this handoff and a local commit. **Do not push.** The commit
containing this document records the session changes. No version bump, tag,
release or publication is part of this work; the manifest remains at 0.3.3.

## Font investigation and implemented fix

Installed Flea 0.3.12-1 already inherited the selected Dracula Pro Van Helsing
palette and 16 px base size. Its separate QML process used a generic monospace
family, whereas the plugin's shell font bridge applied Montserrat within the
shell process. The selected terminal family was Comic Code Ligatures, 12 pt.

`/etc/fonts/conf.d/50-omarchy.conf` assigned JetBrainsMono Nerd Font before the
normal user configuration was loaded. An isolated copy of the installed
Fontconfig rules, removing only that system monospace rule, resolved the generic
family to Comic Code Ligatures. This confirmed precedence as the obstacle.

The plugin now generates early, first-family Fontconfig preferences for
`sans-serif` and `monospace`, using its selected system and terminal families.
`generic_fonts.py` generates the rules and checks effective resolution;
`global_font_actions.py`, `transaction.py` and `controller.py` integrate Apply,
Undo and pending status. The generated user file is
`~/.config/omarchy-look-and-feel/fontconfig-generics.conf`.

The owner installed the static loader with:

```sh
sudo install -m 0644 /home/si/Projects/Omarchy_Plugins/Look_and_Feel/assets/00-look-and-feel.conf /etc/fonts/conf.d/00-look-and-feel.conf
```

That loader is installed and matches the repository asset. Subsequent font
choices update the user file without sudo. Fresh native Fontconfig queries
resolved sans-serif to Montserrat and monospace to Comic Code Ligatures;
serif remained Liberation Serif. Explicit JetBrainsMono and Liberation Sans
requests retained those families. A newly opened Flea reported Comic Code
Ligatures through live IPC and displayed it, with the palette unchanged.

A Flea-specific proportional Montserrat adapter was discussed but not built.
Generic monospace selection preserves Flea's fixed-width layout expectations.

## Flea opacity control

Appearance now contains an independent **Flea opacity** picker: Keep current
settings, or 0–100% in 5% steps. APPLY CHANGES saves it; its own Undo restores
the previous setting. Automatic repair reconciles the saved choice.

`flea_opacity.py` manages Flea's native `[flea] background-alpha` in
`~/.config/omarchy/shell.toml`. It uses background alpha, preserving opaque
foreground text and icons. Windows started fully opaque may need reopening
before transparency can work; the plugin reports that condition without closing
windows or interrupting file operations.

`shell_preferences.py` owns only `font/base-size` and `flea/background-alpha`.
The shared transaction integration preserves unrelated shell settings and keeps
font and opacity Undo independent. It rejects ambiguous managed TOML fields.
No-op first applies retain a baseline so later repair and Undo restore the
original value rather than intervening drift. Section headers at EOF are handled.
Historical whole-file transactions were not migrated.

`Panel.qml`, `BarWidget.qml`, `controller.py`, `appearance_policy.py` and
`managed_preferences.py` integrate selection, status, Apply, Undo and repair.
README documents setup and the reopening limitation.

## Verification and limits

The following focused checks passed during this session:

```sh
python3 -B tests/check_generic_fonts.py
python3 -B tests/check_flea_opacity.py
python3 -B tests/check_terminal_opacity.py
python3 -B tests/check_font_transactions.py
python3 -B tests/check_fontconfig_policy.py
git diff --check
```

Changed Python modules also passed AST parsing. No full-suite result is claimed.
Tests cover native Fontconfig ordering, generated-file transactions, interleaved
font/opacity Undo, baseline preservation across drift and repair, missing-file
restoration, and managed TOML validation.

The installed panel and real Flea windows were exercised at 0%, 75% and 100%.
Live IPC reported alpha 0, approximately 0.749 (8-bit quantization) and 1.
Screenshots confirmed transparent versus opaque backgrounds with visible opaque
text/icons. A second window started at 100% remained opaque when lowered;
the actual plugin displayed its reopen notice. Test changes were undone through
the real handler. Keyboard navigation reached the production picker.

An independent reviewer checked source, regression evidence, live screenshots,
restored configuration and final production panel. Two review findings—no-op
baseline anchoring and a section header without a trailing newline—were fixed
and rechecked. No findings remained. Wider Flea versions and desktop environments
were not tested.

Local screenshots include `/tmp/flea-comic-code-after.png`,
`/tmp/flea-opacity-zero.png`, `/tmp/flea-opacity-full.png` and
`/tmp/laf-flea-final-control.png`. These are ephemeral evidence, not committed
assets. A temporary test IPC hook was removed before the final shell restart;
test Flea windows were closed.

## Local state and loading changes

At the end of live testing, the installed panel showed **Keep current settings**,
with no saved `fleaOpacity` override; the shell TOML contained only the font
section. Terminal opacity was then 50%, and blur was On.

A fresh read during handoff preparation at 14:48 MST showed subsequent saved
choices of **60% Flea opacity and 60% terminal opacity**, with blur still On.
These newer choices were preserved. Current shell TOML:

```toml
[font]
base-size = 16
[flea]
background-alpha = 0.6
```

Montserrat and Comic Code Ligatures remain selected, with the early loader
active. The 60% settings were read from the actual configuration and policy;
their live appearance was not separately re-tested during handoff preparation.

Plugin rescanning retained cached QML on this desktop. `omarchy restart shell`
loaded the edited production UI; that restart has already been completed.
It clears unsaved panel drafts. No additional setup is needed on this machine
to select Flea opacity; an opaque-started Flea window may need reopening.

## Commit boundary

Commit only the session's runtime changes, focused tests, README, loader asset
and this handoff. Preserve unrelated pre-existing edits to
`APPLICATION_SUPPORT_MATRIX.html`, `APPLY_TRANSACTION.html`, the October 29
14:01 handoff, and the untracked October 30 competitive-review documents outside
the commit. Do not push or publish without new authorization.
