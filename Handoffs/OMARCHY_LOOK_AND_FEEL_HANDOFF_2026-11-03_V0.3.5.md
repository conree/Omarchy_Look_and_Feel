# Look & Feel handoff: 0.3.5, missing wallpaper recovery

Date: 2026-11-03 (America/Phoenix).

## Authority and publication

Repository: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`, branch `main`.
Installed plugin: `/home/si/.config/omarchy/plugins/si.omarchy-look-and-feel`,
a symlink to the repository. Remote: `https://github.com/conree/Omarchy_Look_and_Feel.git`.

After confirming full Apply worked, the owner requested: “Write a handoff, commit
changes, push and publish 0.3.5.” This authorizes publication of this focused fix.
The parent release is `3003bcc6c151027cbc3687935b5cbea963cf9f7f` (v0.3.4).
Manifest, panel label and README identify 0.3.5. The release commit, annotated
`v0.3.5` tag and GitHub release identify the publication revision. This document
is prepared before committing; verify remote main and the peeled tag match the
release commit, and verify the GitHub release is published rather than draft.

## Failure and correction

The current wallpaper symlink at
`/home/si/.local/state/omarchy/current/background` pointed to missing file
`/home/si/.config/omarchy/backgrounds/dracula-pro-van-helsing/1334003.jpeg`.
Reconciliation reported that the current background could not be read. Theme
refused to proceed because it could not preserve that image. Full Apply queued
Background later, so the selected replacement could never repair the failure.

`Panel.qml` now runs Background before Theme when current wallpaper readback is
absent. `appearance_actions.py` permits explicit repair of a dangling link,
journals its prior identity and restores that identity after failed/interrupted
repair. Successful Apply still requires a readable image. External drift is
preserved. Undo is unavailable for a repair whose previous image was missing;
ordinary background Apply and Undo remain supported. Missing-link, non-symlink
and other unreadable-state recovery beyond this dangling-link case is not added.

The live repair used the screenshot's selected
`/home/si/.config/omarchy/backgrounds/dracula-pro-van-helsing/Fractal_Blue.jpeg`.
Transaction: `20261103T194836Z-ccfac2e9a700`, journal:
`/home/si/.local/state/omarchy-look-and-feel/transactions/appearance-actions/background/20261103T194836Z-ccfac2e9a700/action.json`.
No wallpaper files were relocated. Their source folder remains
`/home/si/.config/omarchy/backgrounds/`.

## Acceptance and limits

The owner first confirmed “Background just showed up” and then “The Full Apply
worked.” The live controller committed the readable replacement, and subsequent
reconciliation had no pending errors across theme, fonts, icons, blur, terminal
opacity and Flea opacity. Flea was still saved at 60% immediately after wallpaper
repair; the screenshot's 50% draft had been blocked by Theme. The final full
Apply confirmation establishes success, not a separately measured final Flea
opacity value or a fresh opacity-extremes sweep.

`tests/check_background_repair.py`, `tests/check_unlock_recovery.py` (28 checks)
and `tests/check_panel_design.js` (31 cases) passed. Independent review inspected
the actual broken/repaired links, journal, reconciliation state and changed
source, then independently reran the background regression. Two false-success
edges found during review were fixed and tested: disappearance of a replacement
during Apply and a stale selection matching the missing original file. Panel
tests use inert I/O; direct owner confirmation supplies live full Apply evidence.
Release preparation reuses these passing checks for unchanged runtime behavior.

## Release boundaries and updating

The release includes the focused source/tests, version identifiers, README,
release notes, validation, project status, source-of-truth entry and this handoff.
Keep pre-existing edits to `APPLICATION_SUPPORT_MATRIX.html`,
`APPLY_TRANSACTION.html`, and the October 29 14:01 handoff, plus untracked October
30 competitive-review documents, outside this commit. Preserve them locally.

Restart the Omarchy shell if it retains an older version label or cached Apply
order. No sudo, browser-policy changes, boot rebuild or wider application changes
are required for this fix. Previous release context:
[/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-11-03_V0.3.4.md](/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-11-03_V0.3.4.md).
