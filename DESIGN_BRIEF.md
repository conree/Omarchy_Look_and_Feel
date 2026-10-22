# Look and Feel: Design Brief

Date: 2026-10-21
Status: approved design; read-only plugin prototype started 2026-10-21
Origin: the closed Meridian project (Decision AH and the Phase 2 theme-engine
goals), carried over to Omarchy Quattro.

## 1. The goal

Set the whole desktop's look and feel in one place, once, and have every
program follow it: the same font at the same visible size, the same colours,
and the same spacing, without editing program config files by hand.

Meridian aimed to do this by owning the whole system. This brief does it as
a layer on Omarchy: one panel and one settings file that drive Omarchy's own
mechanisms and fill the gaps they leave.

## 2. What Omarchy already does well

- **Themes:** `omarchy-theme-set` switches colours across the shell,
  terminals, editors and other apps (22 themes installed).
- **Extension points:** hooks run after a theme or font change
  (`~/.config/omarchy/hooks/theme-set.d/`, `font-set.d/`), and the
  `themed/` folder holds templates for themed app configs.
- **Plugins:** QML panels in the bar, as EE Calc proved.

## 3. The gaps (verified on this machine, 2026-10-01)

1. **Text size has no single meaning.** foot and Alacritty size text against
   the compositor's fractional scale; WezTerm rounds the scale to a whole
   number; Ghostty multiplies by GNOME's `text-scaling-factor`; Kitty uses
   its own metrics. The same "12 pt" shows at four sizes (Meridian Decision
   AH, 2026-09-12).
2. **Omarchy's tools rewrite app configs.** `omarchy-display-text-size` uses
   `sed` on the Alacritty, Kitty, Ghostty and foot configs, which overwrites
   sizes set by hand. `omarchy-font-set` forces foot to `size=9`. Neither
   knows about WezTerm.
3. **Hidden multipliers.** The Display panel's text-size slider can leave
   `text-scaling-factor` at a value other than 1.0, which shrinks GTK apps
   with nothing in any app config to show why.
4. **No single apply step.** foot cannot reload a running window; the other
   terminals each need a different signal or a restart.
5. **No one screen.** Theme, font, text size, gaps and borders are set
   through separate menus, commands and files.

Today's stop-gap is the `fontsize` fish function, which re-pins all five
terminal configs and warns when `text-scaling-factor` is not 1.0.

## 4. Principles (from Meridian Decision AH, adapted)

1. **One source of truth.** A single settings file holds font family, text
   size, and the chosen theme. Nothing else is edited by hand.
2. **One meaning of a point.** The tool decides once how points become
   pixels, and sets each app so its visible size matches, compensating for
   each app's own scaling rule.
3. **Hidden multipliers are pinned.** `text-scaling-factor` and similar
   values are held at 1.0, and the panel shows a warning if anything moves
   them.
4. **Apply means applied.** Changing a setting updates every running program
   that can be updated, and lists any that need reopening.
5. **Work with Omarchy, not against it.** Use Omarchy's hooks and theme
   system. Where an Omarchy tool overwrites our values, re-apply after it
   through a hook, rather than patching Omarchy's own scripts.

## 5. First milestone: one text size everywhere

Scope: font family and text size only, for Alacritty, foot, Ghostty, Kitty
and WezTerm, plus GTK and Qt apps and the Omarchy shell. This preserves
the approved first milestone’s five-terminal scope.

Acceptance test (from Decision AH): with foot, Ghostty and one GTK app open
on both monitors, setting the size to 12 and then 14 changes all of them,
and the measured cell height matches within 1 logical pixel. It must still
pass after running Omarchy's text-size slider and `omarchy-font-set`.

## 6. Later milestones (not started)

- Gaps, borders, rounding and window spacing from the same panel.
- Theme selection and per-theme overrides in the same panel.
- Additional terminals beyond the five named in the first milestone.

## 7. Open questions for the owner

The owner resolved the original questions on 2026-10-21. Current requirements
and priority are recorded in Section 10 below. Remaining implementation
decisions are the location source and sunrise/sunset handling. A versioned
read-only priority-app inventory is recorded in the application support matrix;
LibreOffice Fresh is absent and the Hey CLI version was not queried because its
launcher can invoke mise and alter its managed tool state. The canonical
catalog path and initial Omarchy sources are now selected and copied (Section 12).

## 8. Sources

- Meridian workplan, Decision AH and Phase 2 objectives:
  `/home/si/Projects/Terminated_Projects/Meridian/meridian_monorepo/docs/meridian-workplan.md`
- Meridian constitution ("one place where visual appearance is set"):
  `/home/si/Projects/Terminated_Projects/Meridian/meridian_monorepo/docs/architecture/constitution.md`
- Omarchy scripts read on 2026-10-01: `/usr/bin/omarchy-display-text-size`,
  `/usr/bin/omarchy-font-set` (Omarchy 4.0.0.r1832).

## 9. Review correction — 2026-10-09

WezTerm belongs in terminal coverage; the duplicate future-milestone entry
has been removed. A read-only bar-plugin prototype now inventories sources
and applications. It does not yet apply settings, and no desktop acceptance
has been completed.

For the one-logical-pixel criterion, define text height as the baseline
pitch of a fixed 20-line, unwrapped sample rendered in the chosen font
with default line spacing. Measure from the first to last baseline, divide
by 19, and convert captured physical pixels using that monitor’s actual
scale. Compare each app’s mean baseline pitch with foot on the same
monitor at both requested sizes. For GTK, Qt and shell surfaces use a
controlled multiline text sample; do not compare widget padding with a
terminal cell. Record font/version, app/version, display scale and
measurement uncertainty. A spread above one logical pixel fails; uncertainty
that prevents that distinction is inconclusive. Repeat after each named
Omarchy override action. This is the proposed measurement protocol for
implementation, not a claim that current application metrics match.

## 10. Owner decisions — 2026-10-21

These decisions update and supersede earlier scope or milestone statements in
this brief wherever they conflict.

1. **Delivery:** an Omarchy bar plugin, following the EE Calc interaction
   model.
2. **Authority and enforcement:** the plugin's saved Look and Feel choices
   are authoritative and must override every competing setting every time,
   with no application exceptions. Reassert the selected values after
   relevant setting drift, theme changes, application starts, and system or
   application updates. An app that cannot be controlled this way is an
   implementation blocker before it can be called supported.
3. **Independent fonts:** provide separate family and size choices for
   non-terminal system applications and for terminals. The terminal face may
   be monospace; it must not force a monospace face on the rest of the system.
4. **Theme and background:** provide independently selected Light and Dark
   themes, plus Light all day, Dark all day, or Automatic mode. Automatic
   switches to Light at apparent sunrise and Dark at apparent sunset, using
   manually entered coordinates and an IANA time zone. Sunrise and sunset
   offsets are applied in local wall-clock minutes and may be adjusted by up
   to three hours either way. The time zone database handles daylight-saving
   changes. At high latitudes, days without sunrise or sunset leave the current
   theme unchanged until the next calculable event. Calculations are offline
   and approximate; they do not request location or network access. The
   background choice is independent of the theme and must persist through
   theme changes.
5. **Icons:** provide an independent global icon-theme choice.
6. **Display setup:** monitor arrangement, resolution, orientation, and
   primary display stay outside Look and Feel. Per-display scale also remains
   in display setup.
7. **Application priority:** first cover email clients (including Hey, the
   email client identified by the owner as native to Omarchy), LibreOffice
   Fresh, OnlyOffice Desktop Editors, the file manager, terminals, and the
   browser. The owner estimates this covers about 80% of everyday use. IDEs
   follow, then content-creation tools.
8. **Font provenance:** offer fonts packaged by the installed Linux
   distribution and explicitly verified open-source alternatives. A font
   discovered in a local directory or online catalog is not automatically
   eligible. Record each family's styles, exact source/package, license, and
   license reference before adding it to the selectable catalog. OpenFont,
   Fontsource, and Font Library are discovery sources; verify individual
   licenses, since Font Library includes multiple license types. This project
   rule does not remove or replace fonts already installed on the desktop.

The canonical preference file and adapters must make these controls survive
Omarchy actions and app/system updates. The implementation must not silently
accept app-specific overrides for supported applications. Local solar-event
calculation is implemented in `solar_schedule.py`; a persistent scheduler and
Apply adapter remain future work.
Installed app versions and control points are recorded in the application
support matrix (Section 13); LibreOffice Fresh is absent locally.

## 11. Initial implementation stage — 2026-10-21

The plugin source is under `Look_and_Feel/` beside this brief. Its current
bar widget opens an inventory panel, and `controller.py inventory` is
read-only. It discovers Omarchy themes, fontconfig families, icon themes,
background candidates, and the requested applications. No appearance
settings are written by this prototype.

Initial machine inventory:

- Present: Hey launcher, OnlyOffice Desktop Editors, PCManFM, Brave, and
  Alacritty, Foot, Ghostty, Kitty, and WezTerm.
- Not present: LibreOffice Fresh. Its adapter can be designed, but cannot be
  confirmed against an installed application on this machine yet.
- Existing settings conflict: GTK and Qt use different general font
  families; terminal families agree but configured sizes do not. Omarchy's
  theme setter also selects a theme-associated background, and its font/size
  commands edit terminal configuration files.
- An independent Shell Font plugin applies its own shell font at startup;
  central enforcement must coordinate with or supersede that behavior.
- Hey launches the Hey web application through Omarchy's web-app handler,
  which means its appearance also depends on the browser and the site's own
  styles.
- Brave has a managed `BrowserColorScheme=device` policy; browser appearance
  control must account for the policy's precedence while following the
  central Light/Dark mode.

These findings are from local configuration and executable/package
inspection on 2026-10-21; they are not claims that the prototype can already
enforce the selected appearance.

## 12. Initial catalog snapshot — 2026-10-21

The canonical persistent catalog root is
`~/.local/share/omarchy-look-and-feel/catalogs/`. The plugin inventory reads
themes and backgrounds from this root. It is seeded from `/usr/share/omarchy/
themes`, `~/.config/omarchy/themes`, and `~/.config/omarchy/backgrounds`.
Theme directory trees are retained under `themes/omarchy-packaged/` and
`themes/omarchy-user/`. Background images are separately gathered under
`backgrounds/omarchy-packaged/`, `backgrounds/omarchy-user/`, and
`backgrounds/user-library/`; image paths preserve their theme or source
subdirectory. Theme videos and other non-image media are not included in the
background library.

This is a copied local snapshot, not a live mirror. The original Omarchy
directories were not changed. A future catalog refresh must be explicit and
must not replace user-added catalog items without review. `catalog-manifest.json`
records file paths, sizes, and SHA-256 hashes. Initial source sizes were about
211 MiB for packaged themes, 1.1 GiB for custom themes, and 29 MiB for the
standalone background library. The resulting catalog occupies about 1.6 GiB,
including the separate theme-wallpaper copies. The read-only prototype
inventories these canonical copies; it does not yet apply themes or
backgrounds. Inventory records now include deterministic IDs and source/review
metadata. The selection gate requires verified provenance, an explicit
license and evidence reference, and (for themes) a compatibility review. An
audit of the current inventory found 616 entries and no entries with complete
evidence; all remain unselectable. This is intentional because fontconfig
presence and a copied image/theme do not establish a usable license. Audit
counts are available in `controller.py inventory`; the metadata shape and
selection gate are defined in `catalog-entry.schema.json` and `controller.py`.

Two external discovery sources were supplied by the owner on 2026-10-21:
Omarchy Hub's theme index (`https://omarchy.deepakness.com/themes`) and
`https://github.com/dharmx/walls`. The Hub currently lists official and
community theme projects; each community project needs its own compatibility
and license review before import. The wallpaper repository says its images
were gathered from third-party sources and that its maintainer does not own
them. It is therefore recorded as a discovery reference only; its images are
not copied into the canonical catalog. Any future import needs per-image
rights/provenance review or an explicit user-directed personal import path.

## 13. Priority application support matrix — 2026-10-21

The printable [application support matrix](APPLICATION_SUPPORT_MATRIX.html)
records package versions, observed configuration files, current font/theme
values, Omarchy side effects, and runtime proof still required for PCManFM,
five terminals, Brave, Hey, and ONLYOFFICE. LibreOffice Fresh is not installed.
Key conflicts found include distinct GTK 3/GTK 4 fonts and dark-mode settings,
separate Qt font/palette files whose active session integration is not proven,
WezTerm's independent palette, the managed Brave color-scheme policy, the
enabled Shell Font plugin, and a Fish GTK theme environment override. Omarchy
theme changes normally replace the background unless told to skip that step.

This was a read-only audit. No settings were modified and no target is yet
classified as supported. Application chrome must be distinguished from website
and document content, which may carry their own typography and colors. The
chosen enforcement boundary must be proven before claiming no-exceptions
support.

## 14. Settings contract — 2026-10-21

The first version of the canonical settings contract is in
`settings.schema.json`; `settings.example.json` shows its unselected initial
state. It keeps system and terminal font IDs/sizes separate; Light and Dark
theme IDs separate from the active mode; the background and icon theme
independent; and schedule location/offsets explicit. Font sizes are stored in
points as the requested logical size; each application adapter is responsible
for translating that value to the application's own units and measuring its
rendered result. Monitor arrangement and scale are intentionally absent.

The example is not installed as live user settings. Before implementing any
writer, specify atomic save behavior, per-target backups, rollback on partial
failure, and recovery after interruption. Automatic mode must not apply until
both themes and a manually configured location/time zone are valid. No
geolocation lookup or network dependency is assumed.

The apply/rollback contract is now specified in the printable
`APPLY_TRANSACTION.html`. It requires a durable journal and private exact-target
snapshots before writes, readback before commit, reverse-order restoration on
failure, startup recovery after interruption, and a user-visible recovery
state if restoration cannot complete. It is a design gate; no configuration-
writing adapter is enabled yet.

## 15. Transaction core — 2026-10-21

`transaction.py` now implements the file-target transaction lifecycle,
stdlib validation for settings version 1, atomic replacement, private
snapshots and journal, target readback, reverse-order restoration, interrupted
transaction recovery, last-commit rollback, and bounded snapshot retention.
The reviewed file target allowlist is intentionally empty. Calls to Apply are
rejected before creating settings or application files until at least one
adapter is explicitly registered. The core does not run shell commands or
write outside the user's home. Application adapters and live desktop behavior
remain unimplemented and unverified. The transaction core now recovers pending
transactions under its lock before beginning a new Apply. The user-facing
rollback control still needs integration before the Apply UI is exposed.
Explicit CLI commands provide transaction status, recovery, and rollback;
inventory discovery remains read-only and invokes none of them.
