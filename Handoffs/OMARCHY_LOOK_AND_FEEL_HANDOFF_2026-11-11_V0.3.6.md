# Look & Feel handoff: 0.3.6, font sizing and application ownership

Date: 2026-11-11 (America/Phoenix).

## Authority and publication

Repository: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`, branch `main`.
Installed plugin: `/home/si/.config/omarchy/plugins/si.omarchy-look-and-feel`,
a symlink to this repository. Remote: `https://github.com/conree/Omarchy_Look_and_Feel.git`.

The owner requested this handoff, commit, push, and a 0.3.6 Marketplace
revision after confirming the live font result. The parent release is `v0.3.5`
(`8190205`); commit `d7e6d39` (newer Omarchy theme-script compatibility) was
already on main after that tag. Manifest, panel label, README, source-of-truth
entry, project status and release notes identify 0.3.6. The release commit,
annotated `v0.3.6` tag and GitHub release identify the publication revision once
pushed. Verify remote `main`, the peeled tag and the GitHub release body after
publishing.

## Session problem

The owner switched to Sakura Mochi. Colours applied, but fonts remained visibly
different across the shell, GTK/Qt apps, terminals, Flea and Betterbird; the
boot unlock screen still showed Dracula Pro Van Helsing.

Two independent causes were found:

1. Sakura Mochi pins every `[font]` token in its theme `shell.toml` (`body = 12`,
   `heading = 18`, etc.). Omarchy merges theme and user `shell.toml` per key, so
   pinned theme values won over `base-size`. The plugin wrote only
   `base-size = 16`; the bar, panels and lock screen stayed at the theme's 12 px
   default while GTK/Qt/terminals used 12 pt. Dracula themes do not pin those
   tokens, which is why this appeared only after the theme switch.
2. The Betterbird adapter managed composition/content preferences but not
   `mail.uifontsize`, the interface size. The file-manager Flea had its own
   pinned `display.textSize` override and was not following the shell at all.

The boot unlock was operational rather than plugin-code: the installed Plymouth
logo was Sakura after the interrupted Apply, but both UKIs still embedded
Dracula. The owner ran `omarchy plymouth set by theme sakura-mochi`; both UKIs
were verified to embed the Sakura logo, and the stale root journal/status were
removed. Later, for font comparison, the owner intentionally switched the
desktop and boot artwork to Dracula; the current boot state is Dracula,
committed. No boot helper code changed in 0.3.6.

## Changes included

- `global_font_actions._shell_font_plan` reads the active theme's pinned tokens,
  scales them from its base to the selected point size, fills standard
  multipliers for unpinned tokens, and follows Omarchy's derived icon tokens.
  `shell_preferences` owns all shell font fields for exact Undo;
  `managed_preferences` and `controller` declare the same ownership.
- Betterbird: `mail.uifontsize` is managed alongside
  `msgcompose.font_face`, `font.name.sans-serif.x-western` and
  `font.size.variable.x-western`. The UI target is derived from the focused
  monitor scale (`5/3 → 17 px` at 12 pt; `1.5 → 15`; `2.5 → 26`) with a 5/3
  fallback. Gecko's default 16 px content size is represented as absent so it
  is not dropped on the next save and does not cause a permanent
  close-and-apply notice.
- Betterbird profile resolution now uses each profile's
  `compatibility.ini` `LastAppDir` against the installed executable instead of
  a hardcoded profile name. Inventory and writable resolution use the same
  rule; ambiguous matches are refused. The active profile on this machine is
  `.thunderbird/mpsjivab.default-default`; the older
  `u1f22xee.default-beta` profile belongs to the Thunderbird-beta install and is
  not selected.
- New `flea_preferences.py` and the `flea-ui-state` transaction target set
  Flea's `display.textSize` to `{"mode":"system"}`. The JSON codec preserves
  unrelated keys, refuses malformed state, and restores the exact previous
  value or absence on Undo. If Flea is running, Apply now skips the write and
  reports close-and-apply rather than letting Flea overwrite the change on
  exit.
- `theme_runtime.require_offline_support` accepts the newer `omarchy-theme-set`
  layout with the optional empty-token/`omarchy-restart-hyprctl` guard (commit
  `d7e6d39`).
- README, panel help/version, release notes, validation, source-of-truth and
  project-status text updated. New regressions:
  `check_shell_font_scaling.py`, `check_flea_ui_state.py`,
  `check_mail_profile_resolution.py`; extended `check_application_fonts.py`.

## Live acceptance

After the final close-apps/Apply:

- both monitors at `1.6666666` scale, positions `0` and `2304`;
- `omarchy display text size` reports `16 px`; shell `base-size`/`body` 16,
  `heading` 21 for Dracula, caption 13;
- GTK/Qt Montserrat 12, terminals Comic Code 12;
- active Betterbird profile `mpsjivab.default-default`: `mail.uifontsize` 17,
  `font.name.sans-serif.x-western` Montserrat, `msgcompose.font_face`
  Montserrat, `font.size.variable.x-western` absent (Gecko default);
- Flea `display.textSize` is `{"mode":"system"}`;
- reconciliation font pending list is empty; only the unrelated Flea opacity
  check remains until Flea is reopened;
- the plugin is enabled and in the bar. All bar widgets report `active: false`
  while their panels are closed, which is normal.

The owner confirmed the resulting font sizes. The remaining visual difference
between Betterbird and Flea at the same nominal size is the UI font face and
x-height, not a missing point-size target; browser/web-app content remains
browser-controlled.

## Verification and limits

Passing focused checks: `check_shell_font_scaling.py` (4 scenarios),
`check_application_fonts.py`, `check_mail_profile_resolution.py` (including no
`[Install]` and ambiguous cases), `check_flea_ui_state.py` (including
out-of-home `XDG_STATE_HOME`), `check_font_transactions.py`,
`check_flea_opacity.py`, `check_portable_appearance.py` and
`check_fontconfig_policy.py`. `omarchy plugin validate` is run during release
preparation.

Three independent reviewers inspected the code and live state. All returned
PASS. They found and we fixed: malformed `hyprctl` entries aborting Apply,
out-of-home `XDG_STATE_HOME` being redirected, a running Flea overwriting its
state, and inventory/writable profile rules disagreeing. Tests cover the first
three and the no-`[Install]`/ambiguous profile cases.

Limits: no broad live sweep of every application is claimed. The Betterbird
profile target is resolved when the plugin loads, so switching profiles requires
a shell restart. A running Flea must be closed before Apply can adopt the system
size. The boot and monitor-scale changes were operational and are not part of
this plugin revision.

## Release boundaries and exclusions

Include the source, tests, version identifiers, README, release notes,
validation, project status, source-of-truth entry and this handoff. Keep the
pre-existing edits to `APPLICATION_SUPPORT_MATRIX.html`,
`APPLY_TRANSACTION.html` and
`Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-10-29_1401.md`, plus the untracked
October 30 competitive-review and November 4 Flea-system-font documents, outside
the release commit. The matrix already had unrelated style/font edits; its
single Betterbird line is omitted to avoid mixing them.

## Marketplace update

The listing is
`https://plugins.omarchy.org/plugin.html?id=si.omarchy-look-and-feel` (canonical;
`omarchyplugins.com` redirects there). Use the Plugin verification issue form,
select **Verify and publish a newer upstream commit**, and provide:

- Plugin ID: `si.omarchy-look-and-feel`
- Repository: `https://github.com/conree/Omarchy_Look_and_Feel`
- Target commit: the full 40-character release HEAD SHA

The Marketplace's automated validation and security baseline run against that
exact commit; a write-authorized maintainer must apply `approved-and-verified`
before publication. The "What's new" content is the v0.3.6 GitHub release body
(`RELEASE_NOTES_0.3.6.md`) and is also posted as a context comment on the
verification issue after creation. Do not claim publication until the bot
reports `Updated and verified` and the listing shows v0.3.6.

Previous release context:
[/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-11-03_V0.3.5.md](/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-11-03_V0.3.5.md).
