# Omarchy Look & Feel

Omarchy bar plugin for the one-source-of-truth appearance project.

## Apply and automatic reconciliation

The plugin saves the chosen fonts and light/dark themes in one desired-state
file: `~/.config/omarchy-look-and-feel/policy.json` (or its XDG equivalent).
Apply generates configuration from the selected palette and detected application
interfaces. No Alucard, Van Helsing, user name, or particular font is required.
The bar checks saved choices every 15 seconds while loaded, repairs supported
configuration drift, and follows the solar phase in Automatic mode. It does
nothing to appearance until a choice has been applied. Background is applied
separately; icon selection remains preview-only.

The panel runs Theme, Fonts, then Background. A failed step stops later steps;
completed steps remain available to Undo. Pending application work is named.
Saved configuration, requested reloads, and rendered appearance are separate
results: a successful file write is never proof of what an application displays.

| Interface | What the plugin applies |
| --- | --- |
| GTK 3/4 and desktop settings | Font, light/dark preference, generated palette; competing appearance declarations in user GTK CSS are removed while layout is retained. |
| Qt through qt5ct/qt6ct | System/fixed fonts and generated palette. Apply detects a selector shared by both installed integrations and saves one owned override in the standard Omarchy Hyprland Lua config. A fresh login activates it for all launchers. Qt 6 can inherit GTK colors; Qt 5 GTK integration alone does not supply the palette. |
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
discovery. Manual audit registers only control surfaces it can verify.

Qt integration detection uses PySide6 to read plugin metadata without loading the libraries. Both qt5ct and qt6ct must offer a common selector before the plugin changes the desktop integration. Unsupported/custom Lua configurations remain pending. The background timer cannot introduce this override: it needs an explicit Apply. Apply and Undo require a fresh login when the selector changes; existing processes keep their old environment. The plugin does not restart the session or change activation variables live.

The transaction journal snapshots original data, records ownership of individual
fields in shared GTK/Qt, policy, Typora and WezTerm files, and groups automatic
repairs under the initiating Apply. Theme Undo preserves a later font choice;
font Undo preserves a later theme choice. Unrelated application preferences and
WezTerm Lua settings are retained. Unknown conflicting edits cause a refusal,
not silent replacement. Interrupted operations recover from durable journals.
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
independently customized pre-Apply theme GSettings. Font GSettings Undo does
restore explicit versus unset values.

Boot unlock remains preview-only. Apply, Undo, and automatic boot recovery are
blocked in both UI and backend. Appearance reconciliation does not enable them.

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
- `Panel.qml`: global appearance controls, built-in Help, the single `APPLY`
  action, Undo controls, and the missed-app audit workflow.
- `controller.py`: application/catalog discovery, global font routes, and
  appearance Apply/Undo routes.
- `FontActionResult.js`: combined command output/exit evaluation for font Apply and Undo.
- `desktop_fonts.py`: journaled GSettings font values and exact unset-state restoration.
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
  wallpaper library. Icons remain selection-only.
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
an offscreen native Qt widget; `check_stale_mail_lock.py` needs local socket-bind
capability and is also run in the VMs. VM tooling and results belong under
`Testing/Boot_VM_Lab/`; guest guards must remain enabled.

Remaining coverage includes unsupported application-owned controls and profiles,
full live visual testing across apps, global icon Apply, and repairing the gated
boot-unlock implementation. Do not infer boot safety from appearance tests or
claim every application's rendering has been verified.
