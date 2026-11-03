# Look & Feel 0.3.5 — Recover Apply after a missing wallpaper

APPLY CHANGES no longer gets stuck at Theme when the current wallpaper link
points to a deleted image. Select an available background and Apply; the plugin
now installs that replacement before applying the theme and remaining settings.

The repair records the original link for recovery if the operation fails or is
interrupted. It reports success only when the replacement image is readable,
preserves intervening external changes, and rejects stale missing selections.
Undo is unavailable for this repair because the previous image no longer exists.
Normal background changes retain their existing Undo behavior.

## Updating

Update the plugin. Restart the Omarchy shell if it retains the older panel or
Apply order. Choose an existing background and click APPLY CHANGES. Wallpaper
files are not moved or recreated by this release.

## Verification

The owner confirmed that the repaired background appeared and that full Apply
worked. Independent review checked the implementation, live wallpaper link,
repair journal and reconciliation state. Focused regressions cover repair,
failure and interrupted recovery, drift protection, ordinary Undo, and panel
Apply sequencing. See [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md) for exact
scope and limits. No new broad application or opacity sweep is claimed.
