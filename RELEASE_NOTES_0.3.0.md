# Look & Feel 0.3.0 — draft release notes

## What's new

- Control terminal background opacity and blur independently of theme and
  font choices. Opacity has its own Apply and Undo; Ghostty keeps explicitly
  coloured prompt and application cells opaque.
- Find application launchers using ordinary hyphens or other dash characters,
  with flexible spacing. Audit results distinguish missing applications,
  ambiguous matches and unsupported shared font controls.
- See clearer application attention messages, including when a browser needs
  to be closed before its font defaults can be applied.

## Improvements and fixes

- Clear Audits clears the search field, result and associated audit warning while
  preserving unrelated notices. Editing a search clears its previous result.
- Audit and clear results wait for the operation and its output to finish before
  reporting success. Re-auditing and reconciliation avoid restoring stale audit
  warnings or briefly hiding warnings that still apply.
- Unresolved audits or an unreadable audit registry no longer prevent font
  changes to supported targets; an unreadable registry is left untouched.
- Skip unavailable, unsafe or malformed optional font and opacity targets, report
  the affected targets, and continue applying changes to supported targets.
- Correct Alacritty font-style handling, including bold italic, nested font tables
  and keyboard array tables, while preserving unrelated settings during Undo.
- Check dependencies by section during automatic repair, so a missing dependency
  does not unnecessarily prevent repair of other sections.
- Reduce collisions between Apply and automatic repair by allowing foreground
  actions to wait briefly for the operation lock.
- Keep pending notices associated with their sections and guard against stale
  reconciliation results. Brave also reports a probable stale local lock while
  continuing to protect its profile from writes.
- Harden reads and managed-setting comparisons used by font application and
  automatic repair.

## Before applying

Save your work and close all open applications before applying changes through
Look & Feel. Reopen them afterward. Brave must be closed during Apply for its
webpage font defaults to be updated; reopening it alone does not complete an
earlier pending Apply.

Fonts are discovered through Fontconfig. Themes and backgrounds are discovered
from Omarchy's installed and user directories, and icon themes from the active
XDG data directories. See the [user guide](README.md#first-use) for details.

## Known limitations

- Applications can use their own theme and font settings; a successful Apply
  does not verify their rendered appearance. Browser policies and installed
  browser themes may also affect Brave's appearance.
- An earlier Brave fixed-width font-size reading differed from the expected
  value. The current profile reads 16 CSS pixels for both default font sizes;
  the earlier discrepancy remains unexplained.
