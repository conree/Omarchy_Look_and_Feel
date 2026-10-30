# Look & Feel handoff: PCManFM selection fix, v0.3.2

Date: 2026-10-30 (America/Phoenix).

## Scope and authority

Authoritative repository: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`.
Installed plugin: `/home/si/.config/omarchy/plugins/si.omarchy-look-and-feel`, a
symlink to that repository. Branch: `main`. Remote:
`https://github.com/conree/Omarchy_Look_and_Feel.git`.

The owner requested a handoff, commit, push and v0.3.2 release explaining this fix.
The v0.3.2 Git tag identifies the exact release commit; do not use a handoff as an
alternate source of code authority. Publication target:
https://github.com/conree/Omarchy_Look_and_Feel/releases/tag/v0.3.2

## Reported problem and confirmed cause

After Look & Feel applied a theme, PCManFM's status bar identified `version.json`
as selected while its row had no visible highlight. The active palette specified
background `#0b0d0f`, foreground `#f8f8f2`, selection `#9580ff` and selected text
`#000000`. Dracula Pro Van Helsing supplied a distinct selection colour.

The plugin's generated `window.background .view` rule has specificity (0,2,1),
and `window.background treeview` has (0,1,2). Both outranked the (0,1,0)
`*:selected` rule, forcing ordinary background/text colours onto selected rows.
A GTK 3 computed-style probe confirmed identical normal and selected colours.
This is a plugin CSS precedence defect, not a defect in the Dracula palette.

Public main and v0.3.1 were checked remotely and both resolved to
`eba0133618fc401a1e6c265dfcbcc7454e856623`, which contains the faulty generator.
Other users of that code can encounter the same issue; no claim is made that
every GTK app or earlier release was tested.

## Correction

In `application_themes.py`, the selection rule now includes
`window.background *:selected`. Its specificity (0,2,1) ties the `.view` rule and
wins because it appears later, while also outranking the treeview rule.

The existing solid-surface selectors remain scoped to `window.background` to
preserve the Ghostty transparency protection. No palette, opacity or prompt-cell
settings were changed. The active GTK 3 and GTK 4 user stylesheets were corrected
locally as well as the generator, so future application retains the fix.

The release updates the manifest and visible panel label to 0.3.2, the README,
project status, validation report and `RELEASE_NOTES_0.3.2.md`.

## Verification and limits

- Actual PCManFM 1.4.0 was restarted on the physical Wayland desktop with Dracula
  Pro Van Helsing unchanged. Final desktop captures show a purple selected file
  with readable text, two selected rows, and a visible selection without focus.
- Accessibility selection identified the exact file; scrolling brought it into
  view. Earlier sidebar-focus/offscreen captures were not counted as passes.
- `python -B tests/check_portable_appearance.py` passed with the source fix.
- Independent review checked the source patch, both active stylesheets, CSS
  specificity, unchanged transparency scoping and the v0.3.1 source defect.
- No fresh live GTK 4, other-theme, other-app or Ghostty opacity sweep is claimed.

Final screenshot evidence is temporary under `/tmp/pcmanfm-selection-focused.png`,
`/tmp/pcmanfm-selection-multiple.png`, and `/tmp/pcmanfm-selection-inactive.png`.
These files can disappear after cleanup/reboot and are not public release assets.
Pre-edit user CSS backups are `/tmp/pcmanfm-selection-before-gtk3.css` and
`/tmp/pcmanfm-selection-before-gtk4.css`, also temporary.

## Upgrade behaviour

Other users must update the plugin, apply the Appearance theme again, then fully
quit and reopen PCManFM. Closing a window alone can leave the old process and
stylesheet loaded. Automatic repair can regenerate managed CSS when enabled;
manual reapplication also works when repair is disabled.

## Release boundary

Commit only this fix, version updates, release documentation and this handoff.
Pre-existing changes in `APPLICATION_SUPPORT_MATRIX.html`, `APPLY_TRANSACTION.html`,
the older October 29 handoff, and the competitive-review handoff files are
unrelated and must remain outside the v0.3.2 commit. The current handoff pointer
is updated to this document, retaining the prior release context as history.
The owner authorized this release; no Marketplace submission was requested.
