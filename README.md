# Omarchy Look & Feel

Omarchy bar plugin for the one-source-of-truth appearance project.

## Current stage

The `0.1.0` source is an appearance-choice prototype. The bar panel
presents controls for system and terminal fonts and sizes, theme mode and
Light/Dark themes, boot unlock design, background, and icon theme. Automatic
mode calculates the current solar phase from Omarchy weather settings and the
system time zone; future transitions are not scheduled yet.
It opens with the owner's initial choices selected. Other choices remain
transient. Choosing a Terminal font or size applies both to Ghostty and saves
that selection; the Ghostty-only undo action restores the prior config and
saved choice.
The system-font section also catalogs Betterbird, Thunderbird, Evolution, and
Geary by font-control type. Its mail-app action applies the selected system
family to Betterbird's resolved profile through the reversible transaction
journal, including the selected point size; GTK mail clients inherit the
shared system-font surface.
`controller.py inventory` discovers theme/background catalogs, fontconfig
families, and installed icon themes. Its best-effort census combines effective
desktop launchers, pacman package records (including foreign packages),
Flatpak/Snap applications, common AppImage locations, web-app launchers, and a
curated set of CLI/TUI programs. Package provenance is not always recoverable:
pacman records a local install but does not retain whether a foreign package
came from yay, `pacman -U`, or another build/install path. The census is saved
privately under XDG state and leaves unknown or unverified font controls marked
for review. The panel reports framework-classification coverage for discovered
app candidates (visible launchers, curated CLI/TUI tools, Flatpak/Snap records,
and discovered AppImages). It explicitly excludes package-only executables,
services, hidden helpers, and apps absent from those sources, so it is not a
claim of exhaustive installed-app discovery or successful font application.
A read-only **Audit current state** compares current selections with saved
GTK/GSettings, active Qt platform-theme configs, terminal configs, Betterbird
profile prefs, active Omarchy theme files, wallpaper image content, and
installed Plymouth artwork. It
reports mismatches and unobservable surfaces; it does not inspect rendered
pixels, prove the plugin caused a value, or verify the next-boot initramfs.
A separate manual lookup searches an app name, launcher,
executable, or package without adding that request to the automatic census.
Ghostty, Betterbird, Omarchy desktop themes, backgrounds, and boot unlock
designs have Apply and Undo actions. The appearance actions keep a durable
journal and verify their resulting selected state. Theme Undo re-applies the
previous Omarchy theme, which may rerun theme hooks; it cannot reverse arbitrary
side effects from those hooks. Unlock Apply/Undo uses Omarchy's Plymouth and
SDDM commands, which rebuild initramfs; the readback verifies the installed
Plymouth artwork but not the image that will be loaded at next boot. Undo
restores the previous detected design semantically, not by restoring exact
system files. Background Undo restores the prior resolved path. Automatic theme
selection applies only the current solar phase; future transitions are not
scheduled. System-wide font Apply remains unavailable.

The source of authority for the owner requirements is
[`DESIGN_BRIEF.md`](DESIGN_BRIEF.md). The expanded, printable plan is
`/home/si/Projects/Omarchy_Look_and_Feel.html`. Parent project entry points
are in `/home/si/Projects/Omarchy_Plugins/`.

## Source files

- `manifest.json`: Omarchy plugin declaration.
- `BarWidget.qml`: bar entry and popup lifecycle.
- `Panel.qml`: appearance-choice panel with Ghostty and Betterbird font actions,
  best-effort coverage disclaimer, and a separate manual application lookup.
- `controller.py`: app/catalog discovery plus the Ghostty font adapter and
  saved terminal-font selection.
- `appearance_audit.py`: read-only configuration and active-theme/Plymouth
  readback used by `controller.py audit-appearance JSON`.
- `font_application_inventory.py`: desktop-app, package-source, AppImage,
  curated CLI/TUI, and Quickshell widget font-surface scan; writes the current
  record atomically to `~/.local/state/omarchy-look-and-feel/font-application-inventory.json`.
- `manual_app_inspector.py`: targeted user-requested app lookup, kept separate
  from the startup census.
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
- `mail_font_adapters.py`: mail-client type catalog, Gecko profile resolution,
  and Betterbird preference adapter.
- `transaction.py`: reversible file transaction core with Ghostty font targets
  and the discovered Betterbird profile prefs.
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

The plugin has been enabled in the active bar and its panel appearance has
been reviewed on the owner's system. Dropdown discovery now reads live
canonical sources; changing the Terminal font applies it to Ghostty and saves
the selection transactionally. The resolved Ghostty config and reversible
Apply/Undo behavior were verified; cross-terminal enforcement remains future
work.
