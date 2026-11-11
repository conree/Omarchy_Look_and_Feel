# Look & Feel 0.3.6 — Font sizes that follow the selected point size

This release fixes two independent reasons the desktop could show several
different text sizes after choosing a single point size.

## What's changed

- **Shell text scales again when a theme pins its type tokens.** Sakura Mochi
  and similar themes set their own `[font]` sizes in `shell.toml`; Omarchy lets
  those pinned values win over `base-size`. The plugin now reads the active
  theme, scales every pinned shell token to the requested point size, and owns
  those fields for exact Undo. The bar, panels and lock screen follow the
  selected size instead of staying at the theme's 12 px default.
- **Betterbird's interface size is managed.** The plugin now writes
  `mail.uifontsize` alongside the composition fonts, derived from the focused
  monitor's compositor scale. At the reference 5/3 scale, 12 pt maps to 17 px
  for the UI and 16 px for message content. Gecko's default 16 px content size
  is represented as absent, so it is not dropped on the next save and does not
  leave a permanent close-and-apply notice.
- **Betterbird's active profile is resolved from the executable.** The adapter
  now matches each profile's `compatibility.ini` `LastAppDir` against the
  installed Betterbird executable instead of relying on a profile name. An
  ambiguous match is refused rather than writing the wrong profile.
- **Flea follows Omarchy by default.** Font Apply sets Flea's
  `display.textSize` to `{"mode":"system"}` through a journaled target. If Flea
  is running, the plugin asks you to close it first so the state is not
  overwritten on exit.
- **Newer Omarchy theme scripts are supported.** The 0.3.5-era capability
  check that rejected newer `omarchy-theme-set` layouts is fixed, so Apply can
  generate the theme when the script contains the optional empty-token guard.

## Updating

Update the plugin and restart the Omarchy shell. If Betterbird is open, close
it and keep it closed while pressing APPLY CHANGES, then reopen it. Reopen Flea
after a text-size change. If you switch Betterbird profiles, restart the shell
so the plugin resolves the new profile.

Browser and web-app content remains controlled by the browser and the page.
The plugin does not claim a single font setting can override site CSS or every
application's own editor fonts.

## Verification

Focused regressions cover pinned and derived shell themes, partial pinning,
Betterbird UI and composition sizes, malformed `hyprctl` fallback, active
profile selection and ambiguity, Flea state preservation and Undo, and the
existing font/Flea/portable-appearance suites. Independent reviewers inspected
the changes and live state; their found edge cases (malformed scale output,
out-of-home state paths, running Flea, and profile-discovery consistency) were
fixed and retested. See [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md) for exact
scope and limits.
