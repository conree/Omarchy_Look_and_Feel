# Look & Feel handoff: bug fixes, v0.3.3

Date: 2026-11-01 (America/Phoenix).

## Repository and authorization

Authoritative repository: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`.
Installed plugin: `/home/si/.config/omarchy/plugins/si.omarchy-look-and-feel`
(symlink to the repository). Branch: `main`. Remote:
`https://github.com/conree/Omarchy_Look_and_Feel.git`.

The owner requested this handoff, a commit and push as "bug fixes", v0.3.3.
The commit message is `bug fixes`; the intended version tag is `v0.3.3`.
Check remote main and the tag for publication state. A GitHub release page is
not part of this request.

## Changes and accepted behavior

- Panel.qml: put Undo fonts below the terminal monospace checkbox, allow the
  checkbox label to wrap, and keep terminal controls within the viewport.
- BarWidget.qml: replace the old Apply-time font pending snapshot with a current
  successful reconciliation result. Preserve warnings for failed, blocked,
  absent or stale evidence; preserve unrelated pending work.
- Button label: APPLY CHANGES. Idle status removed. Final owner-approved footer
  is one paragraph at the button's vertical level:
  "Save your work and close all open applications before APPLYING CHANGES.
  APPLY CHANGES saves your selections from all three tabs."
- Help, action labels and README distinguish closing before applying a profile
  update from reopening to load settings already saved.

## Betterbird lesson

A restart alone is not a reliable way to resolve close-and-apply work. Fully
close Betterbird, click APPLY CHANGES while it remains closed, wait for saving
to finish, then reopen it. Automatic repair checks every 15 seconds and may
also complete the update during a closed interval. Do not suppress a valid
pending warning merely because a process restarted. The user's screenshots
confirmed the manual close-then-apply sequence.

## Evidence and limits

Independent review covered the patch, production-function regression tests,
actual managed Betterbird preference readback and live panel screenshots.
The managed composition/sans-serif family matched Montserrat; 16 CSS px matched
12 pt. The live Applications tab showed no pending actions after resolution.
The final Fonts layout and combined footer were visibly unclipped, and the
owner explicitly accepted the footer layout.

See RELEASE_VALIDATION.md and RELEASE_NOTES_0.3.3.md for the validation scope.
Temporary screenshots are /tmp/look-feel-fonts-restarted.png,
/tmp/look-feel-apps-verified.png and /tmp/look-feel-combined-footer.png.
They are local, ephemeral evidence, not public release assets. Betterbird's
rendered message fonts and broader app/theme/display-size coverage were not
newly verified. Saved settings alone do not prove application rendering.

## Loading changes

On this desktop, plugin rescanning retained old QML. `omarchy restart shell`
loaded the new code. Open applications remained open. Restarting the shell
clears unsaved plugin drafts. Do not confuse a cached panel with the edited source.

## Release boundary

Commit the current runtime fixes, their two modified JS tests, manifest/version,
README, release notes, project status, validation and this handoff/pointer only.
Pre-existing modifications to APPLICATION_SUPPORT_MATRIX.html and
APPLY_TRANSACTION.html, the older October 29 handoff, and untracked competitive
review documents are unrelated; preserve them outside this commit.

No extra cleanup, upstream issue, broad refactor or release-page publication is
requested. Future work should use the final owner-approved wording and layout.
