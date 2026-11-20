# Look & Feel handoff: 0.3.7, themed screensaver diagnosis and release

Date: 2026-11-20 (America/Phoenix).

## Authority and publication

Repository: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`, branch `main`.
Installed plugin: `/home/si/.config/omarchy/plugins/si.omarchy-look-and-feel`,
a symlink to this repository. Remote: `https://github.com/conree/Omarchy_Look_and_Feel.git`.

After confirming the screensaver worked live, the owner asked for this handoff,
a commit, a push, and a Marketplace revision. Both the GitHub release and the
Marketplace request must have a "New in this Release" section. The parent
release is `v0.3.6`. Six commits were already on main after that tag: the
November 14 security fix (`c951632`) and the MailCraft adapter series
(`3f6f618`..`72196ee`). This release adds the themed screensaver, which was
still uncommitted, and the 0.3.7 version bump. Identify the release revision
with the annotated `v0.3.7` tag or:

```sh
git log -1 --format=%H -- Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-11-20_V0.3.7.md
```

## Session problem and diagnosis

The owner left the machine idle for 15 minutes and the plugin's screensaver
(On, Matrix, 10 minutes) did not start.

- **Cause:** Omarchy's Stay Awake indicator was on. The file
  `~/.local/state/omarchy/indicators/stay-awake` had existed since 05:33:17.
  Omarchy's idle service logged `stay-awake: enabled state-file` and
  `idle-cycle-cancel: stay-awake`. `screensaver/launch idle` exits before
  opening any window when that file exists. This is intended and documented
  ("Stay Awake pauses it").
- **Evidence:** A `bash -x` trace of the real launcher in idle mode exited at
  the `[[ -f …/indicators/stay-awake ]]` check. The trace has to run from a
  script file. When the command line itself contains `org.omarchy.screensaver`,
  the launcher's `pgrep -f '[o]rg.omarchy.screensaver'` matches the calling
  shell and exits early, which gives a false "already running" result.
- **Unknown:** what turned Stay Awake on. It came on while the screen was
  locked, and nothing in the logs or key bindings identifies the source.
- **Settings were correct:** `~/.config/omarchy-look-and-feel/screensaver.json`
  = `{"effect":"matrix","enabled":true,"holdsOmarchyToggle":true,"idleSeconds":600}`,
  and Omarchy's `toggles/screensaver-off` was held by the plugin.
  `hypridle.conf`'s old Matrix listener was retired at 04:40 (backup:
  `~/.config/hypr/hypridle.conf.before-look-and-feel-screensaver`).
- **Resolution:** the owner turned Stay Awake off and confirmed the screensaver
  started after the idle time. No code change was needed for the miss.
- **Gap:** the launcher doesn't log anything, so there is no record of the
  plugin's IdleMonitor firing during the failed 15 minutes. A launch log line
  would make the next diagnosis faster. Not done; not requested.

## Release contents (0.3.7)

- Themed screensaver: `screensaver.py`, `screensaver/launch`,
  `screensaver/render`, `tests/check_screensaver.py`, plus wiring in
  `BarWidget.qml` (settings FileView, IdleMonitor via Variants, Preview) and
  `Panel.qml` (Appearance > Screensaver), and `controller.py` subcommands
  `set-screensaver on|off <seconds> <effect>` and `screensaver-status`. README
  section "Screensaver".
- MailCraft appearance-file adapter (already committed).
- Marketplace security-review fixes from 14 November (already committed; see
  [/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-11-14_SECURITY_REVIEW.md](/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-11-14_SECURITY_REVIEW.md)).
- Version 0.3.7 in `manifest.json`, the panel label, README ("New in this
  Release (0.3.7)"), `SOURCE_OF_TRUTH.md`, `PROJECT_STATUS.md`,
  `RELEASE_VALIDATION.md` and `RELEASE_NOTES_0.3.7.md`.

Excluded unrelated working-tree files, as in earlier releases:
`APPLICATION_SUPPORT_MATRIX.html`, `APPLY_TRANSACTION.html`,
`Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-10-29_1401.md`, the October 30
competitive-review handoff, the November 4 Flea-system-font handoff, and the
`docs/*.eml` Marketplace email.

## Marketplace update

Listing: `https://plugins.omarchy.org/plugin.html?id=si.omarchy-look-and-feel`.
Procedure, the same as 0.3.6: open the Plugin verification issue form in
`omacom/omarchy-plugin-marketplace`, choose **Verify and publish a newer
upstream commit**, and give the plugin ID `si.omarchy-look-and-feel`, the
repository `https://github.com/conree/Omarchy_Look_and_Feel`, and the full
40-character release commit. Then post the release body ("New in this
Release") as a context comment. The v0.3.7 GitHub release body is
`RELEASE_NOTES_0.3.7.md`.

The 0.3.6 request, issue #14718, is still open. It was blocked by maintainer
HANCORE-linux on 13 November (clipboard denial of service, unbounded process
collectors). The 14 November fixes address that review and ship in 0.3.7, so
the new request should point the maintainer to #14718 and say which findings
were fixed.

Don't claim publication until the bot reports `Updated and verified` and the
listing shows v0.3.7. A write-authorized maintainer must apply
`approved-and-verified`. Expect `security-review-required` again for the same
documented `sudo`/`pkexec`/pacman capabilities. The screensaver adds no
privileged operation.

The new issue's number is recorded in `PROJECT_STATUS.md` after creation.

## Independent review findings not acted on

- The default **Start after** (600 s) is longer than Omarchy's default idle
  lock (300 s), so on a default system the screensaver never starts until one
  of them is changed. This is documented in the README and release notes. The
  default was not changed, pending the owner's decision.
- Cosmetic caption size and width changes in `Panel.qml` ship with the
  screensaver work and are not listed in the release notes.
- Changing a screensaver setting while it is On re-creates Omarchy's
  `screensaver-off` flag if the user removed it.

## Next steps

1. Watch the new Marketplace issue for the bot's validation and the maintainer's
   review. Answer findings there.
2. Close #14718 as superseded once the maintainer agrees, or when the owner
   decides. It was not closed in this session.
3. Repair the `check_appearance_result.js` and `check_icon_panel.js`
   fixtures (see `RELEASE_VALIDATION.md`).
4. Optional: add a single log line to `screensaver/launch` for each early exit
   (Stay Awake, locked, already running).

Previous release context:
[/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-11-11_V0.3.6.md](/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-11-11_V0.3.6.md).
