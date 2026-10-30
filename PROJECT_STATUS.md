# Project status

## Current: v0.3.2 selection fix — October 30

The PCManFM selection-highlight defect is corrected in the GTK palette generator.
Physical-host single, multiple and unfocused selections passed with Dracula Pro
Van Helsing unchanged. Independent source review and the portable-appearance
regression passed; see [release validation](RELEASE_VALIDATION.md).
The owner authorized committing, pushing and publishing v0.3.2. Its Git tag and
GitHub release identify the published revision. The earlier entries below retain
historical scope and are not the current publication status.

## Historical work

October 29 local change: Appearance now has a separate Terminal opacity dropdown
below the theme choices (keep current, or 0–100% in 5% steps). It uses independent
policy ownership, Apply, automatic repair and Undo across the five supported
terminals. Coloured prompt backgrounds remain opaque; blur is preserved.
Reload/reopen notices retain process identity and retry failed signals. Native
parsers, isolated transactions and native panel checks are recorded in
RELEASE_VALIDATION.md. This change follows the October 28 release archive below.
The opacity dropdown is now compact and left-aligned, with a 240 logical-pixel
maximum width. The October 29 changes remain local and await owner review before
any push or submission.

The initial opacity implementation failed its visible acceptance test because
global GTK palette backgrounds covered Ghostty's transparent renderer. The
corrected palette scopes solid surfaces to `window.background`; a reloadable
Ghostty helper stylesheet also repairs existing processes without closing them.
Live production 0/50/100% captures now pass in the original Ghostty process, with
identical Starship prompt background pixels and exact restoration of the owner's
selected 0% setting after the test. Independent review and limits are recorded in
RELEASE_VALIDATION.md.

Updated 2026-10-28. Version 0.2.0 implements the documented Omarchy appearance
interfaces. On October 28, the owner confirmed a successful physical-machine
reboot, the correct unlock screen and correctly themed applications. The supplied
desktop screenshot shows dark-themed Brave, PCManFM and a terminal, with desktop
bars visible on both displays. Further application and scaling coverage is listed
below. Native host diagnostics pass; the pre-restart agent session used `qt6ct`.
The owner initiated the reboot. The current VM
tests verify embedded artwork, graphical Plymouth rendering and encrypted
bootability. Application detection does
not imply control of every custom application's fonts or content.

The owner has returned after the successful restart. Pre-restart context is in
[/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-10-28.md](/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-10-28.md).
Latest saved choices are Dracula Pro Nosferatu, SF Pro 12 pt and Victor Mono 12 pt.
The version 0.2.0 Marketplace candidate includes the Brave explanatory-note fix,
corrected test fixtures, release documentation and a public sample-data preview.
Git identifies the candidate commit. Marketplace listing review is pending.

## Completed

- Physical-host restart and correct unlock screen accepted by the owner on
  October 28. Visual inspection of the supplied post-restart screenshot confirms
  the dark appearance of Brave, PCManFM and a terminal, plus visible desktop bars
  on both displays. The screenshot and the owner's report are retained privately
  under `Testing/Release_2026-10-28/post-restart/`. Exact font faces, point sizes
  and monitor scales are not established by this screenshot.
- The full October 28 sweep passed all 28 test programs, final-build light/dark
  Apply/Undo with 28 native captures, installation/update in a clean VM HOME,
  real PCManFM notice/restart checks, graphical boot authentication and two
  encrypted cold boots. Undo restored the tested settings and boot assets.
  Independent review verifies the recorded artifacts; scope and fixture limits
  are recorded in RELEASE_VALIDATION.md.
- Brave's Custom label was reproduced and traced to a secondary font-family
  name missing from its menu. Native preference-driven rendering confirms that
  Visby CF Medium selects the Medium face. Font results now explain the label
  without changing the selected face or creating a pending action.

- An always-visible reminder asks users to save work in every open application
  before Apply. PCManFM now has a separate live restart notice when GTK appearance
  changes after its process was first observed. Process identity checks clear the
  notice after exit/restart, and unchanged Apply does not create one. Isolated
  lifecycle, controller, UI and native layout checks pass; actual PCManFM rendering
  and changes predating observation are outside this check.

- Public README now leads with installation, first use, section Undo and disabling
  repair, plus native panel captures and a GTK 3 palette comparison. The repair
  notice and panel Help explicitly cover startup/15-second checks in all modes
  and possible replacement of hand edits. Background discovery uses standard
  Omarchy folders and the current wallpaper; the personal Documents scan is
  removed. Office Code Pro metadata uses a checked public archive and license
  evidence. Feature scope is unchanged. Capture methods and limits are recorded
  in RELEASE_VALIDATION.md.

- All drop-downs precede their examples, immediately below the corresponding
  headings. Mode is grouped on the right with Automatic/Light/Dark. The monospaced
  filter sits below the terminal sample, aligning both font sample boxes.

- The final 0.2.0 archive passed real light/dark panel Apply and Undo with 28
  captures, all 27 isolated programs in their required environment, and independent
  source/recovery review. A subsequent checkbox-only layout refinement passed native wide/narrow geometry,
  keyboard and interaction checks; backend files remain identical to the archive.

- Boot artwork now has authenticated Apply, exact-file Undo and explicit recovery.
  Each current boot image is staged, checked for the selected artwork and complete
  Plymouth assets, and checked against its bootloader checksum. A shared boot lock
  survives helper death. Failed builds restore the saved state without rebuilding.
  The final helper passed stock one-kernel and hardened two-kernel VM Apply/Undo,
  four encrypted cold boots and injected build failure. Boot colours are preserved;
  signed/Secure Boot and custom boot layouts are outside this implementation.
- Background checks quietly defer when another monitor or Apply owns the lock;
  ordinary contention no longer produces a false action requiring attention.
- Application detection now handles Python Qt launchers and Qt Quick binaries,
  and distinguishes Electron/Flutter content from GTK shell libraries. Manual
  audits can register Qt 5/6 system-font surfaces while excluding editor-specific
  controls. This expands identification and shared controls, not arbitrary app CSS.

- Examples now preload with the plugin and reuse a disposable display cache while
  live inventory refreshes. Cache data cannot enable Apply/Undo or override fresh
  defaults; later refreshes preserve drafts. An isolated native Qt test measured
  44 ms to the first displayed frame after preloading, and 3 ms on reopening.
  Actual host click latency was not measured. See RELEASE_VALIDATION.md.
- Each Light/Dark theme preview now contains separate application and terminal
  examples. Native offscreen Qt rendering covers wide/narrow layouts and missing
  preview data; existing panel interaction and keyboard checks pass. This local
  UI change follows the October 25 VM-tested archive; see RELEASE_VALIDATION.md.
- All examples are displayed inline. Boot artwork is always visible on Appearance,
  with an initial installed example, immediate selection updates and an unavailable
  state when no artwork exists. Its former button, dialog and collapsed section
  are removed; boot Apply and Undo use the verified transaction described above.
- The EE Calc-inspired panel now separates Appearance, Fonts and Applications
  into persistent tabs with a fixed Apply footer. It includes installed-palette,
  wallpaper, icon and font previews, concise results with expandable details,
  per-section Undo, application search and explicit pending actions. Theme accents
  remain readable in light and dark modes. Native keyboard navigation reveals
  offscreen controls. Drafts survive tab changes, reopening and failed refreshes;
  Font Undo preserves unrelated drafts. Boot artwork is always visible.
- The restart-related invisible bar was repaired without changing layout. The
  plugin now validates native Qt font fields, repairs malformed input, refuses
  unsafe historical Undo/recovery, and gates new Qt integration activation until
  its fonts are safe. Native Qt5/Qt6 cold-start metrics pass independent review.

- Installed icon themes have Apply, automatic repair and independent Undo across
  desktop GSettings, GTK and available Qt integrations. Hidden fallback,
  cursor-only, malformed and unavailable selections are handled explicitly.
- Typed GSettings transactions preserve explicit versus unset font, scaling and
  icon values. Font Apply normalizes text scaling to 1.0; Foot uses
  compositor-relative sizing. The plugin does not change monitor scale.
- Font Apply repairs the recognized Omarchy user Fontconfig rule that could
  replace explicitly selected fonts. Owned-rule Undo preserves unrelated XML,
  including after automatic repair and when the original rule was already
  correct. Unknown competing configurations are preserved and refused.
- Read-only `doctor` diagnostics and operation/recovery dependency checks are
  implemented, including grouped Undo parent/child preflight before any writes.
- The earlier Qt-safe candidate passed twenty isolated test programs and the
  guest native mail-lock test. Independent review covered source, recovery, native matching,
  icon discovery/UI routing, metadata ownership and rendered-size evidence.
- The real plugin installer, native GTK/Qt5/Qt6 fonts/palettes/icons, guest
  login activation and exact saved-file Undo were exercised. The desktop HOME
  had an explicitly recorded prior configuration, not a pristine profile.
- The 108-case size matrix and eight additional GTK scaling cases pass the
  comparison with Foot for the tested font, sizes and VM output scales.

Earlier light/dark panel Apply and Undo passed in the stock VM. The Qt-safe
d68c7b… candidate also passed exact malformed-font injection, production repair, a fresh real shell,
native Wayland font metrics and refusal of unsafe Undo with no monitored changes.
Independent review checked screenshots, source and saved evidence.
The redesigned panel has its own final light/dark run with 30 captures, exact
baseline restoration, native keyboard/focus/contrast checks, and 17 production
interaction regressions. See the separate archive scopes in the validation report.
Publication details are recorded in the session handoff. [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md) gives exact
archives, versions, metrics and evidence limits; [README.md](README.md) gives
installation instructions and supported application interfaces.

## Remaining acceptance and coverage limits

The owner accepted the physical-host reboot, unlock screen and visible desktop
application appearance. Detailed host font/size and icon checks, KiCad, Typora,
Betterbird, OnlyOffice, launcher Qt integration and monitor/scaling behavior
remain to be recorded. Brave and PCManFM dark appearance is visible in the
post-restart screenshot. A physical-host boot-artwork Apply/Undo sequence remains
untested; successful unlock records acceptance of the existing screen.
Existing applications may cache fonts; reopen those retaining the old font.

The measured size result covers JetBrainsMono Nerd Font at 12/14 pt and scales
1/1.5 in VMs. It does not cover every font, GPU or custom scaling environment.
Generic Fontconfig aliases already replaced by distribution rules, custom
application schemas/launch overrides, and sandbox-specific profiles remain
outside automatic coverage. Boot changes require explicit authentication; browser security policy is preserved. Four unused owner-theme image copies were removed from the
current tree; older Git history retains them.
