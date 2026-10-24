# Omarchy Look & Feel

Omarchy bar plugin for the one-source-of-truth appearance project.

## Current stage

The `0.1.0` source provides global appearance controls for system and terminal
fonts and sizes, theme mode and Light/Dark themes, boot unlock design,
background, and icon theme. Automatic mode calculates the current solar phase
from Omarchy weather settings and the system time zone; future transitions are
not scheduled yet. The panel shows no application names outside the missed-app
audit input and includes a Help dialog.

This is a development checkpoint, not a validated release for live global
Apply. Opening the panel and changing selections does not apply appearance
settings, although startup saves an inventory record. Full Apply can run theme
hooks, and boot unlock can rebuild boot images and update Limine entries on
systems using `limine-mkinitcpio`. Undo does not guarantee restoration of all
hook or boot-system side effects. See the
[current handoff](Handoffs/HANDOFF.md) and
[2026-10-24 session handoff](Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-10-24.md)
for the checks performed and remaining safety work.

An optional **Only show monospaced fonts** checkbox below the terminal font
controls starts unchecked. Checking it filters the terminal menu by Fontconfig
spacing metadata; unchecking it restores all families. The chosen font remains
visible and selected until another is chosen, even if absent from the filtered
menu. This display filter does not change saved preferences or restrict Apply.

One bottom `APPLY` button runs theme, fonts, and background in that order.
Boot unlock is appended only after the user changes the unlock selection during
the current panel session; the loaded default alone never triggers a boot
change. If `APPLY` follows a deliberate unlock selection, its final step runs
Omarchy's Plymouth/SDDM update and rebuilds the initramfs; its installed Limine
integration can also update boot entries. If a step fails,
later steps stop and previously completed steps remain applied. The
per-section Undo controls remain available. Icon theme is selection-only and
is not included in `APPLY`.

Global font Apply/Undo uses a journaled transaction for GTK 3/4 settings,
Omarchy shell font settings, and detected terminal configurations with reviewed
adapters. Foot client/server launchers share the Foot configuration, and Kitty's
URL launcher shares the Kitty configuration; each detected launcher is checked
against its executable and verified configuration adapter, while shared
configurations are changed once. Terminal discovery is based on the audited
launcher census. This is not yet universal application font coverage: manual
audit persists verified shared GTK 3/4 and supported terminal font surfaces in
a private registry.
Global font Apply revalidates those registrations and blocks if any audited
result is unsupported or unresolved. Unmodeled surfaces such as Qt or
application-owned settings still need verified adapters. Manual audit does not
register app-specific theme controls; global theme selection does not provide
per-application theme adapters.
`controller.py inventory` discovers theme/background catalogs, fontconfig
families, and installed icon themes. Its best-effort census combines effective
desktop launchers, pacman package records (including foreign packages),
Flatpak/Snap applications, common AppImage locations, web-app launchers, and a
curated set of CLI/TUI programs. Package provenance is not always recoverable:
pacman records a local install but does not retain whether a foreign package
came from yay, `pacman -U`, or another build/install path. The census is saved
privately under XDG state and leaves unknown or unverified font controls marked
for review. The inventory includes framework-classification coverage for
discovered app candidates (visible launchers, curated CLI/TUI tools,
Flatpak/Snap records, and discovered AppImages). It explicitly excludes package-only executables,
services, hidden helpers, and apps absent from those sources, so it is not a
claim of exhaustive installed-app discovery or successful font application.
The read-only appearance audit compares selected values with saved font
settings, active Omarchy theme files, wallpaper image content, and installed
Plymouth artwork after appearance actions. It does not inspect rendered pixels,
prove the plugin caused a value, or verify the next-boot initramfs. A separate
manual audit searches the entered app name, launcher, executable, or package
without adding that request to the automatic census. It reports generic
framework and font-role findings; application names and record paths are not
echoed in panel output.

The theme, background, and unlock actions keep a durable journal and verify
their resulting selected state. Theme Undo re-applies the previous Omarchy
theme, which may rerun theme hooks; it cannot reverse arbitrary side effects
from those hooks. Unlock Undo re-applies the previous detected design through
Omarchy's Plymouth/SDDM commands and rebuilds the initramfs; readback verifies
installed Plymouth artwork, not the image that will load at next boot. Unlock
Undo is semantic and does not restore exact system files or guarantee
preservation of Limine entries. Background Undo
restores the prior resolved path. Automatic theme selection chooses for the
current solar phase when `APPLY` runs; persistent transitions are not
implemented.

The source of authority for the owner requirements is
[`DESIGN_BRIEF.md`](DESIGN_BRIEF.md). The expanded, printable plan is
`/home/si/Projects/Omarchy_Look_and_Feel.html`. Parent project entry points
are in `/home/si/Projects/Omarchy_Plugins/`.

## Source files

- `manifest.json`: Omarchy plugin declaration.
- `BarWidget.qml`: bar entry and popup lifecycle.
- `Panel.qml`: global appearance controls, built-in Help, the single `APPLY`
  action, Undo controls, and the missed-app audit workflow.
- `controller.py`: application/catalog discovery, global font routes, and
  appearance Apply/Undo routes.
- `global_font_actions.py`: reversible GTK, Omarchy shell, and detected
  supported-terminal font target generation.
- `appearance_audit.py`: read-only configuration and active-theme/Plymouth
  readback used by `controller.py audit-appearance JSON`.
- `font_application_inventory.py`: desktop-app, package-source, AppImage,
  curated CLI/TUI, and Quickshell widget font-surface scan; writes the current
  record atomically to `~/.local/state/omarchy-look-and-feel/font-application-inventory.json`.
- `manual_app_inspector.py`: targeted user-requested app lookup, kept separate
  from the startup census.
- `manual_app_registry.py`: private registration and Apply-time validation for
  supported shared font surfaces discovered by manual audit.
- `font-application-inventory.schema.json`: record contract for the installed
  application and shell-font census.
- Theme and unlock choices are discovered directly from the active Omarchy
  theme roots. Apply uses Omarchy's supported commands. Backgrounds come from
  live Omarchy paths, the current wallpaper, and the selected personal
  wallpaper library. Icons remain selection-only.
- `appearance_actions.py`: journaled apply/readback/undo for Omarchy theme,
  background, and unlock selections. Theme and unlock undo are semantic
  compensations because Omarchy commands update generated/runtime and system
  assets beyond a user-owned file snapshot.
- `solar_schedule.py`: offline approximate local sunrise/sunset calculations
  and next Light/Dark transition selection. No scheduler or apply adapter is
  enabled yet.
- `catalog-entry.schema.json`: metadata contract for stable, read-only
  catalog entries. Discovery entries stay unselectable until provenance,
  license, and compatibility checks are complete.
- `transaction.py`: reversible file transaction core and target allowlist.
- `terminal-font.schema.json`: contract for the saved Terminal dropdown value.
- `settings.schema.json` and `settings.example.json`: version 2 of the
  plugin-owned preference contract and an intentionally unselected example.
- `APPLY_TRANSACTION.html`: printable contract for safe apply, journaling,
  backups, verification, rollback, and interruption recovery.
- `APPLICATION_SUPPORT_MATRIX.html`: printable read-only audit of app control points, local versions, conflicts, and unverified support claims.

## Live appearance catalogs

Themes and unlock designs come directly from the configured Omarchy root
(`$OMARCHY_PATH`, `/etc/omarchy.conf`, or `/usr/share/omarchy`) and
`~/.config/omarchy/themes/`. Unlock designs need both `unlock.png` and
`preview-unlock.png`; designs whose logos cannot be uniquely verified are
excluded from the independent boot-unlock selector.
This follows the [Omarchy theme manual](https://omarchy.org/manual/themes/) and
[Omarchy's theming guide](https://github.com/omacom/omarchy/blob/quattro/docs/theming.md):
stock themes live in the Omarchy tree, user themes live in
`~/.config/omarchy/themes/`, and each theme may include `backgrounds/` and
unlock assets. Extra per-theme wallpapers come from
`~/.config/omarchy/backgrounds/<theme>/`; the active wallpaper is
`~/.local/state/omarchy/current/background`. The catalog also scans theme
`backgrounds/` folders,
`/usr/share/omarchy/backgrounds/`, `~/.config/omarchy/backgrounds/`, the active wallpaper, and
`~/Documents/Fonts_Icons_Wallpaper/Backgrounds/`. Fonts are discovered through
fontconfig; icons through active XDG data directories. The old copied catalog
under `~/.local/share/omarchy-look-and-feel/catalogs/` is not read for dropdown
discovery, so newly installed and updated Omarchy themes appear without a
separate snapshot refresh.

External discovery references are recorded in `DESIGN_BRIEF.md`. Community
themes need per-project compatibility and license review before import. The
third-party wallpaper collection is not bulk-imported because its README says
the maintainer does not own the images.

Font choices follow the provenance rule in `DESIGN_BRIEF.md`: distribution-
packaged fonts and individually verified open-source fonts may be catalogued.
Record the exact source and license before a font appears in the chooser;
fontconfig visibility alone is not sufficient. `font-reviews.json` currently
contains reviewed records for Aileron and Office Code Pro. The latter's source
and license evidence points to the verified local archive in `/home/si/Downloads`,
so that record is specific to this machine until portable upstream evidence is
established. OpenFont, Fontsource, and Font Library are discovery sources,
with per-family license checks required. This catalog policy does not change
fonts already installed or selected on desktop.

## Next implementation work

1. Resolve the inventory entries marked for toolkit or app-specific review,
   starting with source editors, Markdown apps, custom Qt/GTK apps, and active
   Quickshell widgets. Then add reversible adapters by shared control surface.
   Ghostty selection and Undo already pass the disposable-home check.
2. Add persistent automatic Light/Dark scheduling after validating how it
   coexists with Omarchy's own scheduler. Add global icon-theme Apply with
   explicit readback and rollback semantics.

Earlier development verified a Ghostty font transaction. The current single-
`APPLY` panel flow has not been reviewed live or exercised against the owner's
settings. Terminal and application coverage remain incomplete.
