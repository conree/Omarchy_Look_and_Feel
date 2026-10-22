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
decisions are sunrise/sunset handling. A versioned
read-only priority-app inventory is recorded in the application support matrix;
LibreOffice Fresh is absent and the Hey CLI version was not queried because its
launcher can invoke mise and alter its managed tool state. The canonical
live Omarchy catalog sources are recorded in Section 12.

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
   Before implementation, inventory every active font family, size, fallback,
   and scaling control that can affect each supported surface. This includes
   GTK 3 and GTK 4 settings plus GNOME/dconf font keys; fontconfig generic
   aliases, fallback chains, and DPI rules; Qt 5/6 settings when their platform
   integration is active; Quickshell's font style and base size; each
   terminal's own config; browser default web fonts; and application-owned UI
   settings such as ONLYOFFICE. Track font-related GTK CSS/theme rules and
   environment overrides, along with monitor/GDK scaling and GTK text scaling
   that change visible size. Record the writers that can reapply competing
   values, including Omarchy font/size/theme commands and enabled plugins.
   Treat document and web-page typography as content preferences, separate
   from application chrome, unless the owner explicitly selects a policy for
   that content. Do not claim a target is covered until its active inputs,
   writers, precedence, and relaunch behavior are represented in the support
   matrix.
4. **Theme and background:** provide independently selected Light and Dark
   themes, plus Light all day, Dark all day, or Automatic mode. Automatic
   switches to Light at apparent sunrise and Dark at apparent sunset, using
   coordinates from Omarchy weather settings and the system IANA time zone.
   Location and time zone come from existing system settings, with no
   user-adjustable solar offsets. The time zone database handles daylight-saving
   changes. At high latitudes, days without sunrise or sunset leave the current
   theme unchanged until the next calculable event. Calculations are offline
   and approximate; they do not request location or network access. The
   background choice is independent of the theme and must persist through
   theme changes.
5. **Icons:** provide an independent global icon-theme choice.
6. **Boot unlock design:** provide a separate dropdown for Omarchy's boot
   decryption screen. Populate it only from themes that include both
   `unlock.png` and `preview-unlock.png`. The selected unlock design is
   independent of the Light/Dark desktop themes. Applying it requires
   a reviewed, reversible adapter for Omarchy's Plymouth integration.
7. **Display setup:** monitor arrangement, resolution, orientation, and
   primary display stay outside Look and Feel. Per-display scale also remains
   in display setup.
8. **Application priority:** first cover email clients (including Hey, the
   email client identified by the owner as native to Omarchy), LibreOffice
   Fresh, OnlyOffice Desktop Editors, the file manager, terminals, and the
   browser. The owner estimates this covers about 80% of everyday use. IDEs
   follow, then content-creation tools.
9. **Font provenance:** offer fonts packaged by the installed Linux
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

## 12. Live appearance catalogs — 2026-10-22

Dropdown inventory reads live sources directly: themes and unlock designs from
`/usr/share/omarchy/themes/` and `~/.config/omarchy/themes/`; theme wallpapers
from each theme's `backgrounds/` folder; additional wallpapers from
`/usr/share/omarchy/backgrounds/`, `~/.config/omarchy/backgrounds/`, and
`~/Documents/Fonts_Icons_Wallpaper/Backgrounds/`; fonts from fontconfig; and
icons from active XDG data directories. The current Omarchy wallpaper is
included. New or updated themes and unlock designs appear without refreshing a
plugin-private snapshot. The old copied catalog remains on disk but is not used
for dropdown discovery.

Inventory records retain deterministic IDs and source/review metadata. Font
provenance metadata applies only to exact family-name matches; discovery does
not imply Apply support or runtime compatibility. `catalog-entry.schema.json`
and `controller.py` define the metadata and selection gate.

Two external discovery sources were supplied by the owner on 2026-10-21:
Omarchy Hub's theme index (`https://omarchy.deepakness.com/themes`) and
`https://github.com/dharmx/walls`. The Hub currently lists official and
community theme projects; each community project needs its own compatibility
and license review before import. The wallpaper repository says its images
were gathered from third-party sources and that its maintainer does not own
them. It is therefore recorded as a discovery reference only; its images are
not copied into the canonical catalog. Any future import needs per-image
rights/provenance review or an explicit user-directed personal import path.

## 13. Priority application support matrix — 2026-10-22

The printable [application support matrix](APPLICATION_SUPPORT_MATRIX.html)
records package versions, observed configuration files, current font/theme
values, Omarchy side effects, and runtime proof still required for PCManFM,
five terminals, Brave, Hey, and ONLYOFFICE. LibreOffice Fresh is not installed.
Font controls now recorded include separate GTK 3/GTK 4 base fonts, separate
GNOME interface/document/monospace font keys, fontconfig generic-family aliases
and fallback chains, Qt 5/6 preferences, five terminal configs, Quickshell's
base size and Shell Font plugin, Brave's default web-content fonts, GTK theme
CSS, and monitor/GDK/fontconfig scaling. Known competing writers include
Omarchy font/size/theme commands, the user's `fontsize` fish function, and the
Shell Font plugin. The dconf probe could not access its runtime path from this
inspection environment; verify those reported values in the live session.
OnlyOffice's UI font authority and live Qt platform-theme integration remain
unconfirmed. The support matrix records these sources and the remaining
per-application verification work. Omarchy theme changes normally replace the
background unless told to skip that step.

This was a read-only audit. No settings were modified and no target is yet
classified as supported. Application chrome must be distinguished from website
and document content, which may carry their own typography and colors. The
chosen enforcement boundary must be proven before claiming no-exceptions
support.

## 14. Settings contract — 2026-10-21

Version 2 of the canonical settings contract is in
`settings.schema.json`; `settings.example.json` shows its unselected initial
state. It keeps system and terminal font IDs/sizes separate; Light and Dark
theme IDs separate from the active mode; the background and icon theme
independent; and automatic scheduling derives location and time zone from
system settings. Font sizes are stored in
points as the requested logical size; each application adapter is responsible
for translating that value to the application's own units and measuring its
rendered result. Monitor arrangement and scale are intentionally absent.

The example is not installed as live user settings. Before implementing any
writer, specify atomic save behavior, per-target backups, rollback on partial
failure, and recovery after interruption. Automatic mode must not apply until
both themes are selected and Omarchy weather coordinates plus the system time
zone can be resolved. No geolocation lookup or network dependency is assumed.

The apply/rollback contract is now specified in the printable
`APPLY_TRANSACTION.html`. It requires a durable journal and private exact-target
snapshots before writes, readback before commit, reverse-order restoration on
failure, startup recovery after interruption, and a user-visible recovery
state if restoration cannot complete. It is a design gate; no configuration-
writing adapter is enabled yet.

## 15. Transaction core — 2026-10-21

`transaction.py` now implements the file-target transaction lifecycle,
stdlib validation for settings version 2, atomic replacement, private
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

## 16. Owner's initial appearance preferences — 2026-10-22

The owner supplied these requested starting values:

- System font: Aileron, 12 pt. (The owner replaced Avenir Next with Aileron on
  2026-10-22.)
- Terminal font: Office Code Pro, 12 pt.
- Theme mode: Automatic; Light theme Alucard; Dark theme Dracula Pro Van
  Helsing.
- Current catalog IDs: `theme:dracula-pro-alucard-3bbe21886bb2` and
  `theme:dracula-pro-van-helsing-b06cbc9d080a`.
- Boot unlock design: Dracula Pro Van Helsing. This is one independent boot
  choice and does not switch with the desktop's Light/Dark schedule.
- Background: `/home/si/Documents/Fonts_Icons_Wallpaper/Backgrounds/1333929.jpeg`.
- Icon theme: `Tela-circle-dracula-dark-van-helsing` (the active installed
  icon-theme ID), catalog ID `icon:tela-circle-dracula-dark-van-helsing-8087a116ad09`.
- Schedule: Automatic mode uses system location and time zone. Location comes
  from `/home/si/.local/state/omarchy/settings/weather.json`; the
  inspected system file names Tucson at latitude `32.22174`, longitude
  `-110.92648`. Time zone comes from `/etc/localtime`, which currently
  resolves to `America/Phoenix`. These values are system context, not
  separately editable Look & Feel preferences. No sunrise/sunset offsets are
  configured.

These are requested preferences, not a claim that catalog entries are
selectable or have been applied. Fontconfig resolves both requested font
families. Their provenance review and the remaining catalog-selection gate
are recorded in Section 17. The background file was present when checked.
The current prototype remains read-only.

## 17. Initial selection inventory check — 2026-10-22

The installed icon setting resolves to
`Tela-circle-dracula-dark-van-helsing`; its installed directory is
`/usr/share/icons/Tela-circle-dracula-dark-van-helsing/`. Schedule coordinates
are read from the machine's Omarchy weather settings rather than the Census
city-center point previously recorded in version 1 of this brief.

The live inventory reports 31 themes, 26 unlock designs, 364 font families,
74 icon themes, and 145 deduplicated backgrounds. It includes Alucard and Van
Helsing from the Omarchy user theme directory; both contain `unlock.png` and
`preview-unlock.png` and appear in the unlock selector. The two reviewed font
families are selectable in the development catalog; theme compatibility
review and Apply adapters remain separate gates.
The local Dracula Pro source bundle also contains its EULA; review its
personal-use and modification terms against the derived theme files before
marking those theme records selectable.

The local `/home/si/Downloads/office-code-pro.zip` has SHA-256
`0976a8dfb646770166011c5b2c47de659e124b679ef725704d850e7d1905bbd8`. It
contains an OFL 1.1 license; the installed font metadata also names the SIL
Open Font License, and all eight installed Office Code Pro OTF files match
the corresponding archive members. This verifies the local source archive
and its license, though its original download URL is not recorded.

The owner selected Aileron as the system font. The designer's official
[Aileron page](https://dotcolon.net/fonts/aileron/) identifies version 0.102
as “No Rights Reserved” and permits use, modification, and redistribution.
The local `/home/si/Downloads/aileron_0102.zip` archive contains all 16
installed OTF files byte-for-byte; its SHA-256 is
`a93a1327f44912a7b1410ad0056fec3e904074413b0bd9da550f6175587cf958`. Font
metadata also says “No Rights Reserved.” This satisfies the source and
license review for Aileron. `font-reviews.json` now records this review and
Office Code Pro's local archive/OFL review. The inventory applies reviewed
metadata only to exact family-name matches reported by fontconfig. Office Code
Pro's evidence currently references `/home/si/Downloads/office-code-pro.zip`,
so that record is machine-specific; its original download URL is unknown.
These records make the two font catalog entries eligible, but no appearance
settings have been applied.

Avenir Next is no longer selected. The installed TTC identifies Linotype GmbH
and says all rights reserved; it contains no open-source license record. The
downloaded Avenir Next LT Pro archives also have no included license file.
Monotype offers Avenir Next with commercial licensing choices
([Monotype product page](https://www.monotype.com/fonts/avenir-next-world)).

## 18. Dracula Pro license and snapshot audit — 2026-10-22

The local source bundle's `/home/si/Documents/Dracula_Pro_Theme_Pack/license.md`
identifies itself as the Dracula PRO EULA. It grants personal, non-transferable
use on up to three computers, prohibits editing or adapting any part of the
Software, and prohibits copying or distributing it for commercial purposes.
It also says components designated open source follow their own licenses. The
official [Dracula Pro page](https://draculatheme.com/pro) describes a license
for three computers and up to three active devices. These sources establish
the published use limits, but do not specifically resolve whether derived
unlock artwork, inclusion in a personal plugin, or onward distribution is
permitted. This is a project eligibility review, not a legal interpretation.

The previous plugin snapshot's Alucard and Van Helsing directories were
compared with their live Omarchy theme directories (six and twenty-five common
files respectively); that snapshot omitted the unlock images. Current dropdown
discovery reads the live theme roots directly. The SHA-256 values are Alucard `unlock.png`
`45677c44d64240ea2df4c8f3be8868470aaa9db75e232b7d8c307179f9f8f279`,
`preview-unlock.png`
`214ec322d3363dfa9ef1c47d4b2ba156505c195cb943f17adf20279f325faa28`; Van
Helsing `unlock.png`
`6d837610f23006abf8dbd7d78641159df1ce93f7bb5393de235e1827e4f31399`,
`preview-unlock.png`
`d1cb15239095be0c8511c7b71dbc413040e257aa56225f27169425ca74da63e1`.

The owner has directed that licensing not block this development work. Treat
the local EULA review above as context only; do not infer permission for
redistribution. The selected Alucard and Van Helsing theme entries are marked
development-only and bypass license gating, but still need plugin
compatibility review and an Apply adapter before they can be applied.

## 19. Live Omarchy unlock entries — 2026-10-22

The controller discovers unlock designs directly from the live Omarchy theme
directories and requires both `unlock.png` and `preview-unlock.png`. The panel
shows a dropdown and preview, preselecting Van Helsing from the owner's initial
preferences. The selected value is transient UI state and is not saved or
applied. Theme application remains pending an adapter.
