# Release validation — updated 2026-10-29

## Live transparency correction — October 29

The initial checks below missed the essential visible behavior: the plugin's
global GTK palette painted `window`, `stack` and `scrolledwindow` opaque behind
Ghostty. Native A/B desktop captures reproduced the failure at 0%. Restricting
solid palette surfaces to `window.background` fixes newly started Ghostty
processes. Existing GTK processes retain the old user stylesheet, so the opacity
adapter also owns a reloadable Ghostty custom stylesheet that clears those
surfaces while the window lacks its opaque-background class. SIGUSR2 loads this
correction without closing sessions. Explicit prompt/application cell backgrounds
remain opaque (`background-opacity-cells = false`).

Actual production opacity actions were tested at 0%, 50% and 100% in the original
running Ghostty PID 1282224. Desktop captures show visible wallpaper, an intermediate
blend, and an opaque background respectively. More than 5,000 sampled Starship
prompt background pixels retain exactly the same RGB values across all three.
The test actions were undone, restoring the selected 0% policy and all seven
recorded terminal/configuration/CSS hashes; both original sessions remained open.
An independent reviewer checked scripts, source, screenshots, window metadata,
pixel comparisons and exact restored hashes. Fresh-process A/B captures also
include Wayland opaque-region logs. Evidence is private under
`Testing/Opacity_2026-10-29/live-correction/`.

Focused opacity, portable-appearance and 23-case panel regressions pass. An added
regression verifies that Undo refreshes Ghostty even when only the helper CSS
changes. Independent retesting of that edge passes. The earlier 28-program sweep
below predates this correction; it is not claimed as a fresh broad sweep of the
corrected build. Other terminals retain their native background-opacity behavior;
this live capture sequence specifically covers Ghostty on the owner's desktop.

## Initial terminal opacity dropdown checks — October 29

The Appearance tab adds a separate Terminal opacity dropdown below Light/Dark
theme choices. It offers Keep current settings or 0–100% in 5% steps and explains
that 70% opacity means 30% transparency. The default leaves current terminal
settings alone. The shared Apply sequence inserts a selected opacity after
Theme, with separate saved policy, automatic repair and Undo. Native background
settings cover installed Ghostty, Alacritty, Kitty, Foot and WezTerm. Ghostty
keeps explicitly coloured prompt and application cells opaque; blur is preserved.

Twenty-eight isolated test programs passed in the final broad sweep. The
unchanged native Gecko lock test was excluded because host process/lock
interoperability is outside this feature; its earlier coverage remains below.
The new opacity regression covers all five adapters, four Apply/Undo orders,
first-use Fonts/Opacity ownership, unrelated edits, no-op original baselines,
drift repair, terminals added after Apply, 0/100% endpoints, reload retries,
process restart notices and malformed auxiliary-cache recovery. Native Ghostty
and Foot validation, Alacritty's configuration migration parser, and synthetic
WezTerm execution in real Lua passed. The production panel interaction suite
now has 23 cases, including opacity draft preservation, CLI routing, 0%, failure
ordering, independent Undo and truthful pending status.

Independent review reran focused production regressions, probed codec/ownership
edges, inspected actual user-config plans without writing them, and rendered
the production QML controls offscreen at 0% and 70%, with an open dropdown and
zero Qt warnings. Rendering used sample inventory and a substituted shell
wrapper. Live terminal appearance, physical GPU compositing, and every custom
config syntax were not tested. Files with unsupported layouts are refused;
merged Undo may retain harmless empty section headers. Foot/Kitty reopen notices
track process identity rather than proving window appearance.

This local revision follows the October 28 archive below. Private final sweep
logs, source hashes and panel captures are under `Testing/Opacity_2026-10-29/`.

Following owner sizing feedback, the opacity control was narrowed to a left-aligned maximum
of 240 logical pixels. Independent native checks at 840- and 480-pixel panel
widths measured a 240-pixel control and popup, with the full default label visible
and no Qt warnings. The 23-case panel interaction suite still passes. This later
layout-only change leaves backend files unchanged; its QML hash, captures and
geometry are recorded separately in `Testing/Opacity_2026-10-29/compact-layout/`.
The original broad-sweep manifest above identifies the preceding layout.

This is a tested development candidate for the documented Omarchy baseline,
not a claim that every Linux application or hardware configuration is supported.
Version 0.2.0 adds verified boot-artwork Apply/Undo for the supported layout.
The owner accepted the physical-host reboot, unlock screen and visible application
appearance on October 28. Detailed application and scaling coverage remains below.

## Marketplace preparation — October 28

The submission candidate remains version 0.2.0. Its 63 runtime/test file hashes
match the October 28 archive below, and all 28 recorded test results identify
the current test files. The post-restart acceptance update changes documentation
and private evidence. Root `preview.png` is an exact copy of the public
`docs/screenshots/appearance.png` sample-data capture; its provenance and capture
limits are described under Public documentation and portability revision.
Private `Testing/` evidence and licensed local theme/font assets are excluded
from publication. Marketplace review and approval are separate from these checks.

## Physical-host restart acceptance — October 28

After voluntarily restarting the physical machine, the owner reported: “The
computer reboot worked perfectly, showing the correct unlock screen and showing
the correctly themed applications.” The attached desktop screenshot shows Brave,
PCManFM and a terminal using a dark appearance, with desktop bars visible on both
displays. Separate visual inspection of that image corroborates the displayed
application appearance. Host uptime also corroborates a recent boot.

The screenshot, its SHA-256 and the owner's report are retained privately under
`Testing/Release_2026-10-28/post-restart/`. Unlock-screen correctness is owner
acceptance; the supplied image shows the unlocked desktop. Exact font faces and
sizes, monitor scales, launcher Qt integration, KiCad, Typora, Betterbird and
OnlyOffice still need detailed host checks. This reboot did not exercise a host
boot-artwork Apply/Undo sequence. No further restart or configuration change was
performed to record this acceptance.

## Current-build release sweep — October 28

The current runtime/test archive has SHA-256
`a4e1c070ebb2970c12aa54ef5c03cc31bf64902517ade5d17908a810261cb6cd`.
Its manifest is `Testing/Release_2026-10-28/runtime-files.json`; the parent Git
commit is `b2d3698`. The archive includes the Brave explanatory-note change and
the test-fixture corrections described below. Private raw results are under
`Testing/Release_2026-10-28/` and `Testing/Boot_VM_Lab/results/`.

All 28 test programs pass. Three failures in the first complete run were fixture
problems: two JavaScript fixtures omitted the newly called restart helper, and
the transaction fixture inherited the operator's active Qt selector. Those
fixtures were corrected, with added notice-delivery assertions. The final full
run passes all 27 sandbox-compatible programs; the unchanged native mail-lock
test passed outside the sandbox. `checks-final.json` records current file hashes.

The current build passed the real four-step desktop Apply in light and dark
modes, 14 capture phases each, and exact Undo. Managed files, desktop settings,
background content and prior journal hashes were restored. A single settings
digest remains unchanged through tab/draft/preview interactions. Independent
review checked all 28 screenshot hashes and representative wide/narrow layouts.

The real plugin manager installed and enabled the build from a local Git mirror
in a clean HOME with separate XDG directories and keyfile GSettings. Inventory,
doctor, disable/re-enable and a fast-forward update to identical runtime bytes
passed. This used the existing VM user, packages and compositor, rather than a
new OS installation. Its original shell was restored afterward.

Real VM PCManFM retained its old palette while running, produced the restart
notice, adopted the changed palette after reopening, and cleared the panel
count after reconciliation. The test restored managed files and desktop settings.

Native Brave with disposable profiles reproduced Custom for Visby CF Medium.
Its menu enumerates primary families and omits that secondary family name.
DevTools platform-font measurements verify that inherited/default, serif and
sans-serif samples use `VisbyCF-Medium`, while monospace uses
`OfficeCodePro-Regular`. Explicitly selecting the parent Visby CF instead uses
`VisbyCF-Regular`. The plugin preserves the variant and reports an informational
note; it does not create an outstanding action. Mathematical fonts are outside
the managed browser font fields. No owner browser profile was changed.

The normal graphical pkexec path was exercised from the VM's desktop session:
Cancel left all boot files unchanged, and Apply/Undo passed image verification
and configuration/EFI/mount invariants. The initial SSH-launched attempt lacked
a graphical session agent, so the final case launched through Hyprland.
Two encrypted cold boots also passed. To exercise graphical Plymouth despite
the lab's serial console, temporary Limine options requested graphics. The
requested logo and graphical password field were captured and visually checked;
unlock succeeded. The options were restored before exact artwork Undo. Boot
assets were restored, excluding only the documented per-boot entropy seed, and
the restored image passed another encrypted cold boot. The text-only OCR helper
could not identify the graphical prompt, so its field was visually confirmed
before the disposable VM passphrase was entered.

Native host doctor checks pass outside the sandbox. The later owner-initiated
physical reboot and visible application acceptance are recorded above; detailed
host application/scaling checks and host boot-artwork Apply/Undo remain open.
The full earlier two-VM failure/recovery matrix remains applicable to the
unchanged boot helper; this sweep adds the graphical path rather than repeating
every earlier injected-failure case. No owner appearance settings, boot files,
login or existing owner application processes were changed by these release
tests. Disposable native test processes did run on the host.

## Initial PCManFM and save-work checks — October 28

`application_restarts.py` observes exact same-user PCManFM process identities
(boot ID, PID and start time), relevant GTK 3 settings/CSS and desktop font,
scaling and icon settings. Before/after controller observations and periodic
reconciliation maintain a separate current restart list; old section results
cannot retain a resolved notice. Failed observations preserve existing notices
without changing Apply success. The tracker never signals or restarts an app.

The isolated restart suite covers real keyfile GSettings, theme/font/icon changes,
unchanged and unrelated writes, repeated checks, multiple processes, PID reuse,
exit/reboot, restoration to the baseline, read failures, unsafe configuration
paths, controller delivery and reconciliation clearing. The 21 panel interaction
cases, font pending, icon panel, application font, portable appearance and native
keyboard/focus checks pass. Production panel captures with sample data in an
offscreen Qt window show the reminder above Apply on every tab without QML
warnings. Captures for this revision are temporary review artifacts; the checked-in
README screenshots and their provenance still describe the October 26 source.

These initial checks covered settings/process lifetime, not rendered PCManFM. They cannot
infer changes made before the process's first observation. No live host Apply,
forced application restart or repeat of the VM/boot matrix was performed.

## Public documentation and portability revision

The later October 26 revision reorganizes the README around installation, Apply,
Undo and disabling repair. The README and panel Help state that saved themes,
fonts and icons are checked on load and every 15 seconds in every mode, including
with the panel closed, and that hand edits to managed values can be replaced.
`controller.py` no longer scans the owner's Documents wallpaper library. Standard
Omarchy background folders, theme backgrounds and the current wallpaper remain
discovery sources. Runtime feature scope and transaction writers are unchanged.

`docs/screenshots/` contains three native renders of current production panel
controls/layout with sample data in an isolated Qt window, and a native GTK 3
example before/after loading the production Catppuccin stylesheet. The capture
helpers are `docs/capture_screenshots.py` and `docs/capture_gtk.py`. The former
replaces the shell window/IPC wrapper and does not run controller commands;
the latter uses an offscreen widget on a private temporary Broadway display.
They do not demonstrate end-to-end desktop Apply or arbitrary app compatibility.
No personal wallpaper, profile, paid theme or real application inventory is used.

Office Code Pro's public Font Library archive was downloaded and inspected:
SHA-256 `cc6f46af8de42d43b633f0c21200ca247d53e6bfd407445b9a6fcf44f1ca6c6e`.
Its `Office-Code-Pro-master/LICENSE.txt` contains SIL OFL 1.1 and has SHA-256
`78ce650b35110da0870b8665f006f5ec28db05028b84bb8e0c675305f4137d54`.
The regular OTF's native family name is Office Code Pro. The metadata describes
this public archive, not arbitrary installed files or the earlier local ZIP.

Checks for this revision passed: appearance previews, preview cache, native panel
keyboard/focus, 20 panel interaction cases, appearance result ordering and icon
panel routing. An isolated background-discovery check covers standard libraries,
stock/user theme folders and an active image stored outside those libraries,
including one in the former personal library. README relative links and anchors
resolve; JSON and Python sources parse; `git diff --check` is clean.
An initial disposable discovery probe inherited the host XDG config path and was
correctly refused by the home-boundary guard; rerunning with isolated XDG paths
passed. This was a test-fixture setup error, not a runtime change.

Independent review inspected the source/docs and all five images, reproduced
the panel captures without QML warnings, checked background discovery and font
archive evidence, and found no blocking issue. Portable appearance and icon
transaction suites also passed independently. Source/image hashes are recorded
in `docs/screenshots/provenance.json`. This revision has not repeated the full VM
Apply/Undo or boot matrix; its runtime changes are limited to discovery and Help.

## Version 0.2.0 completion checks

Full-panel VM-tested runtime/test archive: SHA-256
`c01b9ad40e7493a7990c3bb749c75e5de20d26e86b00cdcd6b8bb522459d1c43`,
61 files. Manifest: `Testing/Boot_VM_Lab/tools/finish-runtime-files.json`.

The final archive ran the real panel's four desktop Apply steps in light and dark
modes, with 14 captures per mode (28 total). Tests cover all tabs, constrained
window sizes, footer placement, scrolling, drafts, refresh, reopening and inline
boot artwork. The final layout places all drop-downs above their examples and
groups Mode with the three buttons on the right. Both modes restored all saved application files, desktop settings
and prior journals exactly through Undo. Shell logs contain image-picker module, Bluetooth and Qt.atob deprecation
warnings; no Look & Feel load/type errors were reported.
This UI test did not select a boot change; privileged boot behavior was tested
separately below. Evidence: `design-ui-c01b9ad40e74-{read,logs,undo}-{light,dark}.json`
in `Testing/Boot_VM_Lab/results/`.

All 27 isolated programs pass in their required environment: 26 in the sandbox,
and the native mail-lock ownership test outside it with a temporary HOME.
The final 20-case production panel interaction check passes after the last status
wording change. All backend files match the VM archive. A later checkbox-position refinement
is covered by the native checks below.

The exact final boot helper passed two disposable guests: stock with one current
UKI, and the owner's hardening fixture with two current UKIs. Each passed Apply,
independent embedded-artwork extraction, encrypted cold boot, exact boot-file
Undo, and another encrypted cold boot. An injected mkinitcpio exit 42 was reported
as failure and restored the original boot bytes without requiring a working builder.
Evidence: `Testing/Boot_VM_Lab/results/finish-boot-acceptance.json`, including the
helper source hash, per-phase probes and cold-boot captures. The boot-generated
random seed is intentionally excluded from cross-boot byte comparisons; EFI
variables and mount protections are compared immediately around each operation,
since firmware timing variables legitimately change at boot. System configuration
remained unchanged. The host boot files were never modified.
The VM cold-boot captures show text encrypted-root password prompts, not a
graphical Plymouth logo. They prove bootability and unlock plus independently
verified embedded artwork bytes; they do not prove the artwork's graphical
rendering during boot. That remains a host/graphical-boot acceptance limit.

Isolated regressions also cover malformed/truncated PNGs, a stale second UKI,
partial publication, stale bootloader checksums, intervening kernel changes,
interrupted transaction recovery, and subprocess timeout, SIGTERM and SIGKILL.
Independent real-process checks confirmed that no surviving publisher races
recovery and that SIGTERM stops publication. The GUI uses the ordinary checked
controller process; no terminal launcher or slug-only success polling remains.
Old unverified journals remain blocked. The graphical administrator prompt itself
was not used on the host; guest boot tests ran the exact helper with an explicitly
identified test-user UID via the lab's authenticated root connection.

Boot artwork changes only the logo, preserving existing Plymouth colours and
SDDM. Supported preflight is limited to standard unsigned Omarchy UKIs; signed or
Secure Boot images, enrolled configurations, fallback/custom build options and
unhandled sections are refused. No claim is made for those untested layouts.

Application discovery regressions cover Python Qt launchers, Qt Gui/Quick-only
binaries, misleading application names, symlinked Electron launchers and Flutter.
Manual audits include matching Qt system-font controls and exclude editor-specific
roles. Native GTK/Qt and application-profile coverage from earlier checks remains
bounded as described below; identifying an application is not proof its content
follows desktop settings. Transient operation-lock contention now skips only the
background check, retaining previous pending actions.

A fresh production-component render measured cache adoption 18 ms, all five images
ready while hidden at 277 ms, first displayed/captured frame 44 ms, and reopen 3 ms.
This is an offscreen Qt measurement, excluding compositor/animation timing. The
final panel retains inline examples and no Preview buttons. Logs and isolated
check results are in `Testing/Release_2026-10-26/`. The mail-lock native test passes
outside the sandbox using a temporary HOME; sandbox UID mapping invalidates that
ownership test, so its sandbox failure is not recorded as a product regression.

Host readback confirms the saved selector is `qt6ct` but the current session still
uses `gtk3`. The owner must save work and sign out/back in, then check reopened
applications. This remaining session activation is not automated.
The tested plugin was activated with a host shell restart. The installed symlink
resolves to the release source, its manifest is 0.2.0, and the regenerated cache
contains the new default-logo entry. The fresh shell log has no Look & Feel,
ReferenceError, TypeError or SyntaxError matches. Unrelated shell warnings remain.
Reconciliation reports exactly one pending action: the Qt fresh login.

## Final checkbox alignment refinement

After the full-panel VM run, the existing monospace filter was moved below the
terminal font example. Only Panel.qml differs from the archived runtime. Native
production-component rendering at 820 px measured both sample boxes at y=146,
height=158, with the checkbox below at y=316. At 450 px the stacked terminal
sample ends at y=606 and its checkbox starts at y=618. The system-side filter
remains hidden. Existing native keyboard/focus and 20 interaction checks pass.
Evidence: `Testing/Release_2026-10-26/font-alignment.log`,
`font-alignment-source.json` and `fonts-checkbox-{wide,narrow}.png`.

## October 26 inline examples

`Panel.qml` now shows separate application and terminal examples for each theme.
Native offscreen Qt loaded the production preview components without warnings
at 820 px and 450 px fixture widths, including missing-palette fallback. The
17-case panel interaction regression and native keyboard/focus/theme-file tests
pass, as do the icon, appearance-result and font-result checks. Independent review
checked the source and rendered samples. These checks cover representative palette
and font fixtures, not actual application rendering or a new full-panel VM run.
The October 25 archives below predate this UI-only change.

Boot artwork also appears inline by default; its Preview button, modal and
collapse toggle are removed. Native offscreen Qt rendered the production section
with installed Catppuccin/Latte artwork at 820 px and 450 px fixture widths.
Keyboard selection immediately changed the image; missing-image and empty-catalog
states rendered correctly. Independent source checks covered current-design
selection, first-installed fallback, no initial pending change and draft preservation.
The existing 17 interaction cases and native keyboard checks pass after this change.

## October 26 example-loading performance

The initial instrumented inventory took 4,875 ms, including icon samples
2,625 ms and application discovery 1,172 ms. These are profiler timings on the
host files, with inventory-record persistence suppressed and sandbox-limited
desktop readback; they are not end-to-end desktop latency measurements.

The panel now preloads while closed, reads a bounded disposable display cache,
and keeps decoded static images. Fresh inventory replaces cached defaults before
enabling appearance controls or Apply; cache data contains no Undo authority or
application audits. Duplicate scans on opening are suppressed. Icon lookup
rejects nonexistent files before resolving paths but still validates containment;
legacy font/background lists reuse the already-built catalog.

A native offscreen Quickshell fixture loaded the production FileView, adoption
functions, styled components and Appearance page against the host catalog and
five installed images. Cache adoption took 17 ms; images were ready while hidden
at 288 ms. Showing the previously hidden window and capturing its first frame
took 43 ms; reopening took 4 ms. These exclude shell animation/compositor timing.
Evidence: `Testing/Panel_Performance/2026-10-26/`. A first run with no cache still
needs discovery. No measured host click-to-visible guarantee is made.

Independent review covered cache/live ordering, missing live font preferences,
preserved drafts, action gates, atomic private persistence, icon containment and
the rendered examples. Nineteen interaction cases, cache-persistence checks,
native keyboard/focus/file-watcher checks, icon previews and result handling pass.
Host activation required a shell restart after plugin rescan did not start the
new preload path. After restart, the schema-1 cache was created (250,757 bytes;
31 themes, 26 unlock designs, 364 fonts, 74 icon themes, 145 backgrounds), with
no matching plugin/QML errors in the fresh shell log. This confirms activation,
not a host click-latency measurement.

## Candidate and environment

October 25 panel redesign runtime/test archive: SHA-256
`ea7774d1c2d4e853b90545b6a8cc9b17dd767d3d9207c9ba3763ef0fa9006ec3`,
61 files. Manifest: `Testing/Boot_VM_Lab/tools/design-release-runtime-files.json`.
Backend appearance writers are unchanged from the earlier Qt-safe candidate.
The controller adds read-only palette/icon preview metadata; panel state and
presentation changes are covered separately below.

Earlier Qt-safe runtime/test archive: SHA-256
`d68c7bf132ec47801bbd8924f0cda7b30ef623a3105f32a0f2b7980ce87343ed`,
57 files. The private manifest is
`Testing/Boot_VM_Lab/tools/release-qt-safe-runtime-files.json`.
Git identifies the published source including documentation; private VM files
and licensed owner assets are excluded from the current source tree.

The rendered-size archive is
`6458b71d8f28e50fb2ba070c070a4bbd0d01dcf4595088149631278068bbf18b`.
Independent comparison separates the subsequent changes: reopening guidance,
Fontconfig Undo ownership, and Qt font validation/serialization, restore preflight,
ownership anchors and activation gating. The new serializer changes Qt6 wire
format, so identical font-generation bytes are not claimed. Non-Qt font rendering
paths are unchanged. Independent review recovered the actual matrix Qt values from journals and
verified snapshot hashes. All eight general/fixed values at 12/14 pt retain equal
decoded attributes and native metrics; Qt5 bytes remain identical and Qt6 uses
canonical serialization. This supports reusing the bounded matrix; it was not
rerun. Final guest fault-injection results are recorded below.

Guests use Omarchy 4.0.6, Hyprland 0.56.2, GTK 3.24.52, Qt 5.15.19 and Qt 6.12.0.
Real qt5ct/qt6ct packages were installed. Guest application probes ran on Wayland through the
actual user-manager environment; isolated host Qt tests used offscreen widgets. These are disposable QEMU guests with file-backed
disks, not host disk passthrough or a test of the owner's physical GPU/monitors.

## Panel redesign acceptance

The final design archive ran the real four-step Apply sequence in the stock VM
in light and dark modes. Each mode produced 15 captures covering all three tabs,
normal and constrained 640×560 panel sizes, scrolling to the actual bottom,
unsaved font edits, tab changes, catalog refresh, reopening and unlock artwork
preview. The fixed footer and enabled Apply button stayed within the panel.
Installed wallpaper/icon samples loaded, font samples reported the requested
families/sizes, the active-theme badge matched the observed theme file, and the
18×18 checkbox had a visible outline with measured contrast above 3:1.

All post-Apply navigation/preview captures retained an identical monitored
appearance-settings and journal snapshot. Draft choices survived refresh and
reopening. Undo restored compared file contents, modes and existence, desktop
settings and background content, with zero differences. Policy JSON was compared
semantically; older journal hashes were unchanged. The intentionally unsafe
older font journal was not undone. Temporary QML instrumentation was removed
and all 61 installed source/test files again matched the archive.

Five JavaScript regression programs pass, including 17 production panel cases,
all stdout/stderr/exit arrival orders, failures that stop later steps, pending
application work, invalid refreshes, unrelated-draft preservation on Font Undo,
and observed-theme changes without draft changes. The native Qt regression loads
the actual controls, keyboard wrapper and focus helper: Tab/Shift-Tab, automatic
scrolling, typing, selector navigation and popup-before-panel Escape all pass.
Twelve actual Qt color cases meet 4.8:1 against their panel backgrounds. The real
Quickshell FileView passes initial read, atomic replacement, invalid data,
deletion and recreation in an isolated temporary home. Read-only palette/icon
preview tests and the existing icon catalog tests pass. Qt 6 parses the panel.

Independent reviewers checked production source, tests, screenshot hashes and
rendered layout. The guest shell logs contained no detected plugin QML errors
or binding warnings; unrelated stock warnings are retained in the evidence.
VM GUI handlers were exercised programmatically. Native QTest delivered keyboard
events in isolated fixtures; a physical mouse/keyboard session across every
control and every owner's theme/font combination was not tested. These UI checks
do not extend application support or prove all applications render the saved
settings. New runtime assets come from installed themes; none are redistributed.

Private evidence: `design-ui-ea7774d1c2d4-{read,logs,undo}-{light,dark}.json`
and the corresponding 30 PNG captures in `Testing/Boot_VM_Lab/results`.
The earlier backend and sizing evidence below retains its original archive scope.

## Checks completed

- Twenty isolated Python/JavaScript test programs passed on the earlier Qt-safe
  d68c7b… candidate.
  The native Gecko lock test also passed inside the guest. These cover file and
  typed GSettings transactions, grouped repair/Undo, dependency refusals,
  native Qt widget readback, app-profile ownership, UI completion ordering,
  icons, Fontconfig matching, and blocked boot-unlock recovery.
- The real Omarchy plugin installer completed a clean plugin installation in
  the stock VM. This was an existing desktop HOME with a recorded baseline,
  not a pristine user profile. Installed file bytes matched the tested archive.
- Actual GTK/Qt5/Qt6 probes verified selected fonts, palettes and icons. After
  a guest login, Qt5/Qt6 both rendered the fixture icon with center pixel
  `#22cc88` and used the intended dark palette. Undo restored baseline file
  contents, modes and existence. A second login verified restored native state.
  The baseline already contained a saved Qt integration override; the earlier
  running environment had not activated it. Undo restored that configured state,
  not the stale pre-login process environment.
- The sizing matrix contains 108 captures: nine applications, two sizes,
  two output scales, and Apply / actual Omarchy text-size change / actual
  Omarchy font change, followed by plugin reconciliation. Independent image
  measurement and native metrics/protocol checks passed the design brief's
  comparison with Foot. Eight additional GTK/Ghostty captures with `GDK_SCALE=2`
  also passed. No arbitrary font spacing correction was introduced.

The earlier Qt-safe d68c7b… archive passed fault injection of the exact malformed host Qt6 general
and fixed records. Fixture insertion and the real production font Apply body ran
under the production operation lock with normal dependency/recovery preflight,
preventing the background timer from repairing the fixture first. A fresh shell
process loaded Adwaita Sans 13 pt with 361.39 px sample width and 21 px text height;
clock, workspaces and icons remained visible. A fresh Wayland widget launched
through the real user manager confirmed weight 400 and stretch 100. Unsafe Undo
refused before mutation: 32 file targets, 18 journal hashes and four typed desktop
settings remained identical. Test instrumentation was removed and all 57 installed
files again matched the final archive. That candidate’s guest native mail-lock check
also passed. Independent review inspected source, nested snapshots and screenshot
hashes. Evidence: `release-qt-cold-stock-*.json`, its restart screenshot and
`release-qt-safe-mail-lock.json`. This is a real shell cold start, not a new full
logout/login cycle on the final archive; the earlier candidate supplied that
separate login-activation evidence.

The actual panel light/dark flows on archive `3cd67d…` completed all four steps
without pending attention. Fresh guest GTK/Qt5/Qt6 probes read back selected fonts,
light/dark palettes and the fixture icon. Both Undo checks restored compared application file
contents, existence and modes with zero differences; the desired-state policy
file was excluded from that byte comparison. The temporary QML
instrumentation was removed and all 56 installed runtime files matched the archive.

## Rendered spacing

Font: JetBrainsMono Nerd Font, Regular, package
`ttf-jetbrains-mono-nerd-basic 3.5.1-2`, Fontconfig version value 150994. Font file
SHA-256 `1c680e8cde9fcf8b88a5605ce8d1fb94dd3fb15841f7ca7bf4c55664855e5611`.
Terminals: Foot 1.28.0, Alacritty 0.17.0, Kitty 0.49.2, Ghostty 1.3.1,
WezTerm git build `20240203.110809.r898.gfe3006a-1`.
Twenty identical, unwrapped lines with
default spacing. Values below are logical pixel baseline pitches. All three
phases agreed. Each application's pitch is within one logical pixel of Foot
on the same output. This is not a guarantee for every selectable font or scale.

| Surface | 12 pt, scale 1 | 12 pt, scale 1.5 | 14 pt, scale 1 | 14 pt, scale 1.5 |
| --- | ---: | ---: | ---: | ---: |
| Foot | 22 | 22 | 26 | 25.333 |
| Alacritty | 22 | 22 | 26 | 25.333 |
| Kitty | 22 | 21.333 | 25 | 24.667 |
| Ghostty | 21 | 21 | 25 | 24.5 |
| WezTerm | 22 | 21.5 | 25 | 25 |
| GTK 3 | 22 | 22 | 26 | 26 |
| Qt 5 | 21 | 21 | 25 | 25 |
| Qt 6 | 22 | 22 | 26 | 26 |
| Omarchy shell | 22 | 22 | 26 | 26 |

Screenshots use the actual output scale and 1000×640 logical-pixel windows.
Raster endpoint uncertainty is up to two physical pixels over 19 intervals;
independent band-center fits and native cell/layout metrics resolve boundary
cases. Foot/Ghostty final viewport mappings and WezTerm buffer scale were checked
rather than treating a buffer pixel as a logical pixel. WezTerm's CSI grid size
was captured before resize; its cell pitch is corroborated by final screenshot
and surface mapping. Shell samples read the real Style/FontInfo in the live shell.
Application probes are fresh windows, not proof that every existing process
refreshes its font cache. The main matrix had no GDK_SCALE override; the separate
eight-case supplement explicitly used Omarchy's default value of 2.

## Defects found by these checks

A host shell restart exposed a malformed Qt6 font record whose native decoder
reported success while producing 1% character width. Saved layout/plugins were
intact; text and icons became invisible. Independent review confirmed the repaired
two font entries and the restored bar. The original invalid record predates the
first recorded Qt6 font Apply; its creator is not established.

The final source validates native font semantics, repairs malformed inputs, and
preserves valid custom attributes. New tests cold-start actual Qt5/Qt6 widgets and
measure text width. Undo/recovery refuses malformed saved fonts before any writes,
including legacy journals, and validates final grouped restoration plans. Initial
ownership anchors retain valid original fields through later repair. Theme-only
activation cannot newly enable qtct over malformed fonts: repair fonts first,
then explicitly Apply again. The independent reviewer reran these tests.


The actual `omarchy font set` test exposed a Fontconfig rule that overrode
explicit font requests even after application settings were repaired. The new
adapter narrows only that recognized rule, preserves unrelated XML, rejects
unknown competing constructs, and journals the rule for grouped Undo. Native
`fc-match` tests reproduce the failure and verify both selected and other explicit
families after repair. Generic aliases already resolved by earlier distribution
rules remain a documented limitation.

Review also found an unavailable icon selection retained behind an empty chooser,
cursor-only/hidden metadata offered as icon themes, missing dependency checks
before grouped Undo preparation, and the initially-correct Fontconfig Undo edge.
Regression tests cover those cases.

## Evidence and limits

Raw guest screenshots, protocol logs, file baselines and independent reviews are
private under `Testing/Boot_VM_Lab/results/`. Main records include
`release-qt-safe-unit.json`, `release-stock-*.json`, `release-final-stock-*.json`,
`size-verified/`, `size-gdk2/`, `laf_size_*_independent_review.json`, and
`qt-matrix-font-{provenance,equivalence-independent}.json`.
They are ignored by Git; this document summarizes reproducible scope without
publishing private guest data.

During this continuation no other installed OS was enumerated, mounted or accessed. No host boot
rebuild, browser-policy write, compositor-scale change or forced logout was used.
Only explicit authenticated boot-artwork actions can change boot files; automatic reconciliation cannot. VM success does not establish
all Omarchy versions, hardware, app-specific rendering or custom profile paths.
Older Git commits still contain the four removed, unused owner-theme images;
repository history was not rewritten.
