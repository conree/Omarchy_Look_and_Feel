# Look & Feel 0.3.7 — Themed screensaver, MailCraft support, security fixes

## New in this Release

- **Themed screensaver.** Appearance now has **Screensaver** controls: On/Off,
  a start time from 1 minute to 1 hour of idle, and an effect (Matrix, a random
  effect each cycle, or any single ttfx effect). Colours come from the active
  Omarchy theme every time an effect starts, so theme changes are followed
  without an Apply. Waking it locks the screen; **Preview** shows it without
  locking. Turning it On also turns Omarchy's own screensaver off so the two
  never both start; turning it Off restores Omarchy's only if the plugin was the
  one that turned it off. It is always opaque, even with translucent terminals.
- **MailCraft follows the desktop.** When MailCraft is installed, theme, font
  and App opacity Applies write `~/.config/mailcraft/appearance.json`: colours
  from the active Omarchy palette, the system font for the interface, and the
  App opacity setting. MailCraft uses the file while its interface theme is set
  to *Follow appearance file*.
  Theme, font and opacity each own their own fields, so undoing one never
  blocks another, and an unreadable file never blocks another app's Apply or
  Undo. The font outgoing mail is written in stays MailCraft's own setting.
- **Marketplace security review fixes.** The panel is created only when you
  open it, and the Applications search no longer uses a native editable text
  field, so the plugin no longer makes the shell subscribe to clipboard changes.
  Every panel and reconciliation command whose output the plugin collects is
  now bounded by total time and combined output, a command that fails to start
  still completes, and helper process groups are cleaned up on cancel. (The
  screensaver launcher is started detached and its output is not collected.)

## Updating

Update the plugin and restart the Omarchy shell. The screensaver's idle timer
runs in the bar widget, so the widget must be on the bar. The screensaver does
not start while Omarchy's **Stay Awake** indicator is on, while an idle
inhibitor (for example, a playing video) is active, or on an already locked
screen. Omarchy's own idle lock (`idle.lock` in `~/.config/omarchy/shell.json`,
5 minutes by default) is separate: choose a shorter **Start after** time or set
`idle.lock` to `0`.

Paste and input-method composition are not available in the Applications
search field; type the name instead (up to 256 characters).

## Verification

The owner confirmed the screensaver starting live on the desktop after the idle
time, with the plugin's own timer and launcher. An earlier miss was traced to
Omarchy's Stay Awake indicator being on, which pauses the screensaver as
documented; the launcher's idle path was traced live to that check. The
security fixes are covered by the clipboard, process-limit and panel-keyboard
regressions recorded in the 14 November security follow-up; the MailCraft
adapter is covered by its focused regressions. 41 of 44 isolated test programs
pass. One is a live-session harness that was not rerun. Two JavaScript panel
fixtures fail because they cut functions out of the panel source and no longer
match it: `check_icon_panel.js` already failed in v0.3.6, and
`check_appearance_result.js` has failed since the security fix included here, so
its appearance-action completion-order coverage is currently not exercised. See [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md)
for exact scope and limits.
