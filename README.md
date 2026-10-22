# Omarchy Look & Feel

Omarchy bar plugin for the one-source-of-truth appearance project.

## Current stage

The `0.1.0` source is a read-only appearance-choice prototype. The bar panel
presents controls for system and terminal fonts and sizes, theme mode and
Light/Dark themes, boot unlock design, background, and icon theme. Automatic
scheduling uses coordinates from Omarchy weather settings and the system time
zone; it has no extra user controls.
It opens with the owner's
initial choices selected. Choices are currently transient UI state: they are
not saved or applied to the desktop. `controller.py inventory` discovers
theme/background catalogs, fontconfig families, and installed icon themes to
populate the controls. Application adapters and settings persistence remain
future work.

The source of authority for the owner requirements is
[`DESIGN_BRIEF.md`](DESIGN_BRIEF.md). The expanded, printable plan is
`/home/si/Projects/Omarchy_Look_and_Feel.html`. Parent project entry points
are in `/home/si/Projects/Omarchy_Plugins/`.

## Source files

- `manifest.json`: Omarchy plugin declaration.
- `BarWidget.qml`: bar entry and popup lifecycle.
- `Panel.qml`: appearance-choice panel; selections are currently transient.
- `controller.py`: read-only app and catalog discovery.
- Theme and unlock choices are discovered directly from live Omarchy theme
  directories. Fonts come from fontconfig and icon themes from XDG icon paths.
  Backgrounds come from live Omarchy paths, the current wallpaper, and the
  selected personal wallpaper library. Choices are not yet saved or applied.
- `solar_schedule.py`: offline approximate local sunrise/sunset calculations
  and next Light/Dark transition selection. No scheduler or apply adapter is
  enabled yet.
- `catalog-entry.schema.json`: metadata contract for stable, read-only
  catalog entries. Discovery entries stay unselectable until provenance,
  license, and compatibility checks are complete.
- `transaction.py`: reversible file transaction core. Its explicit application
  target allowlist is empty until an adapter has a reviewed restore path.
- `settings.schema.json` and `settings.example.json`: version 2 of the
  plugin-owned preference contract and an intentionally unselected example.
- `APPLY_TRANSACTION.html`: printable contract for safe apply, journaling,
  backups, verification, rollback, and interruption recovery.
- `APPLICATION_SUPPORT_MATRIX.html`: printable read-only audit of app control points, local versions, conflicts, and unverified support claims.

## Live appearance catalogs

Themes and unlock designs come directly from `/usr/share/omarchy/themes/` and
`~/.config/omarchy/themes/`. Themes with both `unlock.png` and
`preview-unlock.png` appear in the independent boot-unlock selector.
Backgrounds come from theme `backgrounds/` folders,
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

1. Continue implementing the selected appearance choices. The two reviewed
   font records are eligible when their exact family names are installed;
   Alucard/Van Helsing unlocks are read from live Omarchy theme directories;
   and selected Dracula Pro themes still need compatibility review and an
   adapter. The unlock choice is not saved or applied yet.
2. Implement and validate the first reviewed appearance adapter in a
   disposable home before adding its target to the transaction allowlist.
3. Connect a persistent scheduler to the Apply transaction after a theme
   adapter and selectable Light/Dark themes exist. It cannot safely apply a
   transition before those prerequisites are met.

The plugin has been enabled in the active bar and its panel appearance has
been reviewed on the owner's system. Dropdown discovery now reads live
canonical sources; application changes are still not applied. No tests have
been added or run.
