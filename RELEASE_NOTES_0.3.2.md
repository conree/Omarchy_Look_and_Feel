# Look & Feel 0.3.2

## Fixed: invisible selection highlights in PCManFM

After applying an Appearance theme, PCManFM could select files without showing
which rows were selected. The status bar still reported the selected file, but
its row retained the ordinary background and text colours.

The plugin generated a background rule that was more specific than its selection
rule. That background rule won even when a row was selected. The defect is present
in v0.3.1 and is not specific to Dracula Pro Van Helsing: the theme supplied a
visible purple selection colour, which the plugin's CSS overrode.

The generated selection rule now has sufficient specificity to override the
ordinary view background. The correction preserves the existing scoped surface
rules used to protect Ghostty transparency. No theme palette changes are needed.

## Updating

Update the plugin to v0.3.2, apply your Appearance theme again, then fully quit and
reopen PCManFM. Closing a window may leave its process running with the old GTK
stylesheet. If automatic repair is enabled, it can regenerate the managed
stylesheet; reapplying the theme also works when automatic repair is disabled.

## Verification

Verified on the physical desktop in PCManFM 1.4.0 with Dracula Pro Van Helsing
unchanged: single selection, multiple selection and selection after the window
loses focus all show visible purple highlights with readable text. The existing
portable-appearance regression program and an independent source review passed.

The generator supplies both GTK 3 and GTK 4 stylesheets. Live rendering was tested
in GTK 3 PCManFM; this release does not claim fresh visual testing of every GTK
application or a new Ghostty opacity sweep.
