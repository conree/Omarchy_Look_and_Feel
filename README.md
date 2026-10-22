# Omarchy Look & Feel

Omarchy bar plugin for the one-source-of-truth appearance project.

## Current stage

The `0.1.0` source is a read-only prototype for appearance settings. Its bar
entry opens an inventory and transaction panel. `controller.py inventory` discovers installed priority applications,
the copied canonical Omarchy theme/background catalogs, fontconfig families,
and installed icon themes.
It does not write appearance settings, start a service, or change the active
desktop. The panel exposes transaction status, recovery, and rollback; Apply
is visibly unavailable while the target allowlist has no reviewed adapters.
The inventory command never runs transaction actions.

The source of authority for the owner requirements is
[`DESIGN_BRIEF.md`](DESIGN_BRIEF.md). The expanded, printable plan is
`/home/si/Projects/Omarchy_Look_and_Feel.html`. Parent project entry points
are in `/home/si/Projects/Omarchy_Plugins/`.

## Source files

- `manifest.json`: Omarchy plugin declaration.
- `BarWidget.qml`: bar entry and popup lifecycle.
- `Panel.qml`: current read-only inventory panel.
- `controller.py`: read-only app and catalog discovery.
- `solar_schedule.py`: offline approximate local sunrise/sunset calculations
  and next Light/Dark transition selection. No scheduler or apply adapter is
  enabled yet.
- `catalog-entry.schema.json`: metadata contract for stable, read-only
  catalog entries. Discovery entries stay unselectable until provenance,
  license, and compatibility checks are complete.
- `transaction.py`: reversible file transaction core. Its explicit application
  target allowlist is empty until an adapter has a reviewed restore path.
- `settings.schema.json` and `settings.example.json`: version 1 of the
  plugin-owned preference contract and an intentionally unselected example.
- `APPLY_TRANSACTION.html`: printable contract for safe apply, journaling,
  backups, verification, rollback, and interruption recovery.
- `APPLICATION_SUPPORT_MATRIX.html`: printable read-only audit of app control points, local versions, conflicts, and unverified support claims.

## Persistent theme and background catalogs

The canonical catalog root is
`~/.local/share/omarchy-look-and-feel/catalogs/`. It contains copies of the
current packaged Omarchy theme trees, the user's custom Omarchy theme trees,
and a separate background image library. Theme source directories are copied
under `themes/omarchy-packaged/` and `themes/omarchy-user/`. Background images
are collected separately under `backgrounds/omarchy-packaged/`,
`backgrounds/omarchy-user/`, and `backgrounds/user-library/`, preserving
source/theme names. Original Omarchy directories were not changed.

This is a local snapshot, not a live mirror. An Omarchy update will not silently
overwrite the plugin's catalog; a deliberate refresh operation should be
designed before automatic synchronization is introduced. `catalog-manifest.json`
records the copied files, sizes, and SHA-256 hashes.

External discovery references are recorded in `DESIGN_BRIEF.md`. Community
themes need per-project compatibility and license review before import. The
third-party wallpaper collection is not bulk-imported because its README says
the maintainer does not own the images.

Font choices follow the provenance rule in `DESIGN_BRIEF.md`: distribution-
packaged fonts and individually verified open-source fonts may be catalogued.
Record the exact source and license before a font appears in the chooser;
fontconfig visibility alone is not sufficient. OpenFont, Fontsource, and Font
Library are discovery sources, with per-family license checks required. This
catalog policy does not change fonts already installed or selected on desktop.

## Next implementation work

1. Establish verified provenance, licensing, and compatibility for chosen
   catalog items; the current 616 discovered records all remain unselectable.
2. Implement and validate the first reviewed appearance adapter in a
   disposable home before adding its target to the transaction allowlist.
3. Connect a persistent scheduler to the Apply transaction after a theme
   adapter and selectable Light/Dark themes exist. It cannot safely apply a
   transition before those prerequisites are met.

The prototype has not been copied to `~/.config/omarchy/plugins/`, enabled in
the active bar, or runtime-validated. No tests have been added or run.
