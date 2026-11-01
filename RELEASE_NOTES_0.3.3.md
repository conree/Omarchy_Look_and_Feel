# Look & Feel 0.3.3 — bug fixes

The Fonts tab could grow wider than its viewport because the terminal font
checkbox and Undo button shared one row. **Undo fonts** now sits below the
checkbox, with a wrapping checkbox label, keeping the controls inside the panel.

A successful background font check now replaces the panel's old pending-font
snapshot. Resolved Betterbird warnings clear; current pending work remains.
Failed, blocked, missing or outdated results do not clear old warnings.

The main button is **APPLY CHANGES**. Footer guidance is one paragraph beside it,
without the idle status line. Help and the user guide distinguish closing an app
before saving profile changes from reopening an app to load already-saved settings.

For Betterbird composition-font updates, fully close Betterbird, click
**APPLY CHANGES**, wait for settings to finish saving, then reopen Betterbird.
A quick restart alone is not a reliable substitute. Automatic repair can also
complete the update if Betterbird stays closed across a background check.

## Updating

Update the plugin and restart the Omarchy shell if it still displays the old
panel. On the tested desktop, rescanning plugins retained cached QML; restarting
the shell loaded the changes. Open applications do not need to be terminated
for that shell restart.

## Verification and limits

Live desktop captures and independent review confirmed the visible Undo button,
terminal column bounds, final footer alignment and Applications with no pending
actions after Betterbird's saved font settings matched. The owner confirmed the
close-before-APPLY CHANGES workflow and accepted the final footer layout.

Regression checks cover current no-op success, remaining pending work, stale
section/audit generations, failed/blocked/missing results, and existing panel
interaction/result handling. Betterbird's managed preferences were independently
read back against the saved font selection. Its rendered message fonts were not
verified. No new broad application, theme, display-size or opacity sweep is claimed.
