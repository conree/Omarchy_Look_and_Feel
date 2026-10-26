# Omarchy Look & Feel

Version **0.2.0**. One Omarchy panel for desktop and terminal fonts, themes, backgrounds, icons and boot artwork.

## Install

The tested baseline is Omarchy **4.0.6**, Hyprland **0.56.2** with its standard
Lua configuration, and Python **3.11 or later**. Theme Apply also checks for
Omarchy's supported headless theme-generation branch. Older or custom builds
are not assumed compatible merely because the plugin can be loaded.

Install prerequisites using your normal package workflow. On that baseline:

```sh
sudo pacman -S --needed python python-gobject gsettings-desktop-schemas fontconfig procps-ng pyside6 qt5ct qt6ct
omarchy plugin add https://github.com/conree/Omarchy_Look_and_Feel.git --enable --yes
python3 -B ~/.config/omarchy/plugins/si.omarchy-look-and-feel/controller.py doctor
```

Run these from your active Omarchy session. The plugin manager clones, validates
and enables the plugin; it does not install dependencies. `doctor` is read-only
and reports missing packages or unsupported capabilities (exit 2 when incomplete).
It checks available APIs and schemas, not application rendering or live IPC
health. Optional `binutils` improves toolkit discovery through `readelf`.
Application-specific packages are needed only for applications you actually use.

Choose your fonts, themes and optional icons, then press **Apply changes**. If Qt integration
needs activation, save your work, sign out and back in once, then reopen your
applications. The plugin reports this requirement; it never restarts the desktop.
Brave and other offline profiles must remain closed while their settings are
being applied. The current source tree bundles no paid fonts, commercial themes or owner
profiles. Earlier commits contain four unused owner-theme unlock image copies;
they have been removed from the current tree, not from Git history. Runtime
previews discover assets already installed by the user.

Update with `omarchy plugin update si.omarchy-look-and-feel`. Undo each owned
appearance choice **before** disabling/removing the plugin if you want its prior
settings restored. Disabling alone stops reconciliation and releases its shell
font binding; it intentionally does not discard saved application preferences.

## Using the panel

The panel has three tabs, with one **Apply changes** button always available
below the scrolling content. Each drop-down sits directly below its heading,
with its example underneath. The Mode label sits beside the three mode buttons:

- **Appearance:** choose Automatic, Light or Dark mode, compare previews of the
  installed light/dark palettes with separate application and terminal examples,
  and select a background and optional icon theme. Application examples show menus,
  tabs and a file list; terminal examples use the selected terminal font and palette.
  Background thumbnails and icon samples use your installed files. Boot artwork
  is shown inline by default; choosing a logo updates the image immediately.
  A changed selection is applied last and requests administrator authentication.
- **Fonts:** compare samples of the selected system and terminal fonts at their
  chosen sizes. The monospace filter belongs to the terminal selector. Samples
  demonstrate the font in this panel; they do not verify another application.
- **Applications:** review outstanding actions, search detected applications,
  and audit a missing application. A detected application is not automatically
  a supported or visually verified application.

Switching tabs, reopening the panel and refreshing the catalog preserve drafts
while the plugin instance remains loaded. Drafts are not saved across a shell
restart. **Apply changes** uses selections from all three tabs. Section results
describe the last action; expand **Details** for the full result. Undo remains
separate for themes, fonts, backgrounds, icons and boot artwork. Interrupted
boot operations expose an explicit **Recover boot artwork** action. Font Undo refreshes the font
choices without discarding unrelated drafts.

The panel derives accents from the active palette, checks text contrast, and
uses the desktop system font for its controls. Light and dark themes share the
same layout; smaller panels stack the previews into a single column.

Examples are prepared when the plugin loads and reused when the panel opens.
A disposable preview catalog under `~/.cache/omarchy-look-and-feel/` (or
`XDG_CACHE_HOME`) provides examples while live settings refresh in the background.
Apply and appearance selectors wait for that first live refresh; cached data
never enables Apply or Undo. The first run without a cache still needs discovery.

## Apply and automatic reconciliation

The plugin saves the chosen fonts and light/dark themes in one desired-state
file: `~/.config/omarchy-look-and-feel/policy.json` (or its XDG equivalent).
Apply generates configuration from the selected palette and detected application
interfaces. No Alucard, Van Helsing, user name, or particular font is required.
The bar checks saved choices every 15 seconds while loaded, repairs supported
configuration drift, and follows the solar phase in Automatic mode. It does
nothing to appearance until a choice has been applied. Background is applied
separately. An installed icon theme can be applied independently across desktop,
GTK and available Qt integrations, with its own Undo.

The panel runs Theme, Fonts, Background, optional Icons, then explicitly changed
boot artwork with administrator authentication. A failed step stops later steps;
completed steps remain available to Undo. Pending application work is named.
Saved configuration, requested reloads, and rendered appearance are separate
results: a successful file write is never proof of what an application displays.

| Interface | What the plugin applies |
| --- | --- |
| GTK 3/4 and desktop settings | Font, normalized text-scaling factor, icons, light/dark preference, generated palette; competing appearance declarations in user GTK CSS are removed while layout is retained. |
| Qt through qt5ct/qt6ct | System/fixed fonts, installed icon theme and generated palette. Apply detects a selector shared by both installed integrations and saves one owned override in the standard Omarchy Hyprland Lua config. A fresh login activates it for all launchers. Qt 6 can inherit GTK colors; Qt 5 GTK integration alone does not supply the palette. |
| Ghostty, Alacritty, Kitty, Foot, WezTerm | Detected terminal fonts; Omarchy terminal palettes plus a generated WezTerm override. Supported reloads preserve sessions. Foot color refresh uses only owned PTYs; font changes need new Foot windows. |
| Omarchy shell | A shared runtime system-font binding, with point-to-pixel size conversion and restoration when font ownership ends. No separate shell-font plugin is required. |
| Typora | System font for prose, terminal font for code, generated theme and user CSS conflict repair. Its native profile is activated once while closed; subsequent theme changes update the managed stylesheet. |
| Betterbird | Selected profile's font preferences, with its native profile lock held. Ambiguous profiles remain pending. |
| Brave | Default profile's standard/serif/sans/fixed font preferences while closed; conflicting unpacked theme-only launch flags can be removed. Enterprise policy is never rewritten. |
| OnlyOffice | Reversible native-frame setting and launcher flag, avoiding its custom transparent frame. Apply requires closure when changing its native setting. |

Application adapters ship with the plugin and derive values from the same saved
choices. They are not host-specific scripts. Unknown application-owned controls,
custom command-line configuration overrides, Flatpak/Snap-specific config paths,
and unsupported schemas still need adapters; generic toolkit inheritance cannot
force every application to comply. The inventory does not claim exhaustive app
discovery. Manual audit registers identified GTK, Qt 5/6 and supported terminal font surfaces. App-owned editor controls remain separate. Runtime detection distinguishes Electron/Flutter content from their GTK window shell and recognizes Python Qt launchers and Qt Quick binaries.

PySide6 validates Qt font serialization and reads integration metadata without loading the integration libraries. Both qt5ct and qt6ct must offer a common selector before the plugin changes the desktop integration. Unsupported/custom Lua configurations remain pending. The background timer cannot introduce this override: it needs an explicit Apply. Apply and Undo require a fresh login when the selector changes; existing processes keep their old environment. The plugin does not restart the session or change activation variables live.

The transaction journal snapshots original data, records ownership of individual
fields in shared GTK/Qt, policy, Typora and WezTerm files, and groups automatic
repairs under the initiating Apply. Theme Undo preserves a later font choice;
font Undo preserves a later theme choice. Unrelated application preferences and
WezTerm Lua settings are retained. Unknown conflicting edits cause a refusal,
not silent replacement. Interrupted operations recover from durable journals.
Qt font records are checked for valid native fields before use. Font Apply repairs
malformed records while preserving valid custom font attributes. Undo and recovery
refuse to restore a malformed saved font, including in older journals; the repaired
settings and original journal remain available for review. Palette/icon-only Undo
does not replace unrelated font fields. Newly enabling Qt integration is deferred
if its existing font records are malformed: apply fonts, then Apply again.
New files may leave empty directories after Undo.

Keep Brave, Typora and OnlyOffice closed until an explicit profile Apply or Undo finishes.
Their closed-state checks do not provide application-respected exclusion against
concurrent starts; periodic reconciliation never writes those offline profiles.
Betterbird uses its native fcntl lock. A stale owned local PID lock is removed
only after acquiring that lock, checking the dead local owner, and recording a
private audit. Unknown or live locks are preserved.

Theme generation requires an Omarchy version with the inspected headless branch.
The plugin skips the normal post-theme hook chain and privileged browser-policy
writer, then refreshes explicit desktop/session interfaces. Normal Hyprland
reload still evaluates its usual configuration. Some Omarchy application retints
outside these adapters are not invoked, including managed browser custom tint.
Theme Undo re-applies the previous theme's desktop defaults; it does not restore
independently customized pre-Apply theme GSettings. Font and icon GSettings Undo restore explicit versus unset values. Font Apply
owns GNOME text-scaling-factor as a double and sets it to 1.0. Foot uses
compositor-relative sizing (`dpi-aware=no`); compositor scale itself is retained.

Font Apply also repairs the recognized Omarchy user Fontconfig rule that can
replace explicitly requested fonts after `omarchy font set`. It limits that
rule to the first requested family and journals the rule separately from
unrelated XML. Unknown competing rules or includes require review and are
preserved. This does not promise that a bare `monospace` request follows the
terminal choice: earlier distribution rules can already have resolved that
generic family. Supported applications receive explicit selected families.

Boot unlock artwork has explicit Apply, Undo and interrupted-operation recovery.
Selecting a different logo includes it as the last Apply step and opens the normal
administrator authentication prompt. The preview shows that logo against the
existing boot background; Plymouth colours and the login-screen theme are preserved.
The backend builds each current UKI in a private staging directory, verifies its
embedded Plymouth assets and bootloader checksum, then publishes it under the
standard boot-partition lock. Undo restores saved bytes and refuses intervening
kernel or configuration changes. Background reconciliation never performs boot work.

This feature supports the standard unsigned Omarchy UKI layout on `/boot`, with
one or multiple installed kernels. Secure Boot/signed images, enrolled Limine
configurations, fallback/custom UKI options and unhandled image sections are
refused before changes. It requires `pkexec`, `mkinitcpio`, `lsinitcpio` and
`limine-entry-tool`; detailed privileged preflight runs after authentication.
Recovery backups remain root-private under `/var/lib/omarchy-look-and-feel`.
Older unverified unlock journals are preserved and cannot authorize Undo.

An optional **Only show monospaced fonts** filter uses Fontconfig metadata and
retains the current selection. Inventory and preferences are stored under XDG
user directories. No separate service or timer is installed: automatic repair
and transitions run only while the plugin is loaded in the shell.

This is still development software. Isolated fixtures and the stock/owner VM
checks verify ownership, recovery, generated configuration and selected native
GTK/Qt behavior; they do not establish visual correctness in every application.
The source of owner requirements is [`DESIGN_BRIEF.md`](DESIGN_BRIEF.md).

## Source files

- `manifest.json`: Omarchy plugin declaration.
- `BarWidget.qml`: bar entry, popup lifecycle and guarded reconciliation timer.
- `ShellFontBridge.qml`: one runtime font binding shared across monitors, released when the final widget leaves.
- `appearance_policy.py`: desired state, serialized operations and grouped theme Undo.
- `application_themes.py`: palette-driven toolkit and application adapters.
- `managed_preferences.py`: per-field codecs and ownership-aware restoration.
- `css_takeover.py`: syntax-aware CSS conflict repair preserving layout.
- `wezterm_blocks.py`: separately owned Lua font/theme overrides; source is never executed by the adapter.
- `theme_runtime.py`: capability-checked headless generation refresh.
- `Panel.qml`: tabbed appearance controls, previews, built-in Help, the single
  **Apply changes** action, Undo controls, and the missed-app audit workflow.
- `boot_unlock.py` / `boot_unlock_helper.py`: explicit authenticated, staged and verified boot-artwork transactions.
- `panel_preview_cache.py`: disposable private display cache; it never authorizes writes.
- `appearance_previews.py`: read-only palette previews and bounded installed-icon
  sample resolution, including icon-theme inheritance.
- `controller.py`: application/catalog discovery, global font routes, and
  appearance Apply/Undo routes.
- `FontActionResult.js`: combined command output/exit evaluation for font Apply and Undo.
- `desktop_fonts.py`: typed, journaled GSettings font/scaling/icon values and exact unset-state restoration.
- `fontconfig_policy.py`: narrow XML rule repair, native font-resolution protection and owned-rule Undo.
- `icon_actions.py`: installed icon-theme Apply, drift repair and independent Undo.
- `requirements.py`: read-only dependency diagnostics and operation/recovery preflight.
- `terminal_reload.py`: supported reload requests that preserve terminal sessions.
- `app_font_actions.py`: Typora CSS and closed-profile mail font edits.
- `browser_font_actions.py`: closed default-profile browser font edits and per-key Undo.
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
  wallpaper library. Icons use installed themes with portable identifiers; selection does
  not import or redistribute icon artwork or assert its redistribution license.
- `appearance_actions.py`: journaled apply/readback/undo for Omarchy theme,
  background selections. Theme undo is a semantic
  compensation because Omarchy commands update generated/runtime and system
  assets beyond a user-owned file snapshot.
- `solar_schedule.py`: offline approximate local sunrise/sunset calculations
  and next Light/Dark transition selection, evaluated by reconciliation.
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

## Validation and remaining coverage

Run the scripts in `tests/` from this source directory. The portable, terminal,
application and browser suites create isolated homes. `check_native_qt.py` uses
an offscreen native Qt widget. The native Qt5/serialization tests also require
Qt5 development headers, `pkg-config`, and a C++ compiler.
`check_stale_mail_lock.py` needs local socket-bind
capability and is also run in the VMs. VM tooling and results belong under
`Testing/Boot_VM_Lab/`; guest guards must remain enabled.

Remaining coverage includes unsupported application-owned controls and profiles,
full live visual testing across apps and physical hardware, fonts/scales beyond
the measured VM matrix, and repairing the gated boot-unlock implementation. Do not infer boot safety from appearance tests or
claim every application's rendering has been verified.
