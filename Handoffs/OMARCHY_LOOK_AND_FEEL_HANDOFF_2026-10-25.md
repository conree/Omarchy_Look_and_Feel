# Look & Feel handoff — October 25, 2026

This supersedes the earlier October 24–25 operational checkpoint. The project
remains a tested development candidate with explicit coverage limits. The bar
incident described below was a release blocker; saved settings alone were not
adequate evidence of successful rendering.

## Source, deployment and publication

Repository and installed source: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`,
branch `main`, remote `https://github.com/conree/Omarchy_Look_and_Feel.git`.
`/home/si/.config/omarchy/plugins/si.omarchy-look-and-feel` points to this repository.
Stage changes away from that live source until they have passed review/tests.
The user explicitly authorized this handoff, commit and push. The commit containing
this document identifies the published source; verify its remote with Git rather
than interpreting an archive hash as a Git commit.

Final runtime/test archive: SHA-256
`d68c7bf132ec47801bbd8924f0cda7b30ef623a3105f32a0f2b7980ce87343ed`, 57 files.
Private manifest: `Testing/Boot_VM_Lab/tools/release-qt-safe-runtime-files.json`.
Documentation and source packaging are also part of the publication commit.
Private VM images, SSH keys, owner profiles, screenshots and backups are ignored.
Four unused owner-theme image copies were removed from the current tree; older
Git history retains them. History was not rewritten.

## Safety boundaries that still apply

- Never inspect, enumerate, mount or access another installed OS. This includes
  `lsblk`; only the owner may run it after its need has been explained.
- No host sudo, password prompts, boot changes or security-policy workarounds.
  Preserve host hardening and browser enterprise policies.
- Boot unlock is preview-only. Apply, Undo and automatic boot recovery are blocked
  in both UI and backend. Appearance tests do not justify re-enabling those paths.
- Independent verification is mandatory. Separate saved configuration, requested
  reloads, native runtime readback and visually accepted application appearance.
- No forced host logout or application termination. Host applications retaining
  an old font cache must be reopened by the owner.

## Restart incident: cause, repair and prevention

After `omarchy-restart-shell`, the saved bar layout and plugin registry were still
intact. The clock and other text-based icons had collapsed to effectively zero
width. The new shell inherited `QT_QPA_PLATFORMTHEME=qt6ct` and read malformed
Qt6 font records. The old family/size replacement code preserved their invalid
trailing fields. Native `QFont.fromString()` returned success while interpreting
an invalid style hint, weight 1 and stretch 1 (one percent character width).
That explains why a settings readback could pass and a fresh shell could fail.

The malformed general record was:
`Avenir Next,11,-1,400,0,0,0,0,0,0,0,0,0,0,1,Regular`.
The matching fixed record used Comic Code Ligatures. The earliest recorded Qt6
font transaction, `20261023T151626Z-9805a62f059b`, already contains the same malformed
suffix in its before snapshot at 12 pt. This proves it preceded that recorded
Apply, not who originally created it. Do not assign unsupported provenance.

Host repair transaction `20261025T164828Z-ec57a58c550d` changed only
`Fonts/general` and `Fonts/fixed` in `~/.config/qt6ct/qt6ct.conf`, preserving
Avenir Next / Comic Code Ligatures at 11 pt and restoring native normal weight
and 100% stretch. A supported `omarchy restart shell` restored the clock and
icons. Independent comparison checked the exact two-field diff, saved layout,
native parsed values, screenshots and bar geometry. Clock width changed from
24 to 61 pixels; the old 24 pixels were padding with collapsed text.
No bar reset, plugin reinstall or boot operation was used.

Portable prevention now ships in the source:

- Validate Qt serialized fields and native semantics before writing them; repair
  malformed records, preserving legitimate custom style, spacing, stretch,
  OpenType features and variable axes. Qt5 keeps its own compatible format.
- Refuse Undo/recovery that would restore malformed saved fonts, including older
  journals, before target or journal mutation. Preserve the repaired state and
  original evidence. Do not delete or silently rewrite historical snapshots.
- Validate the final merged grouped-Undo plan. Keep baseline ownership even when
  the original font already matched, so later repairs cannot become the baseline.
- Keep icon/palette-only Undo independent of untouched font fields.
- Defer newly enabling Qt integration if its existing fonts are malformed. Apply
  fonts, then explicitly Apply again; automatic reconciliation cannot introduce
  the integration. A fresh login remains necessary for all launchers to inherit it.
- Check the PySide6 validator prerequisite before Fonts Apply/Undo/recovery.

Host repair evidence is private under `Testing/Boot_VM_Lab/results/`:
`host-qt-font-repair.json` and `laf-host-bar-{before,rescan,repaired}.png`.
The general host application appearance has not thereby been accepted.

## Other completed release work

Installed icon themes now Apply, reconcile and independently Undo across GTK,
Qt and typed desktop settings. Validation excludes hidden fallback, cursor-only,
malformed and unavailable chooser entries, and respects first-path precedence.
No icon artwork or redistribution license is inferred from installation.

Font transactions own the desktop text-scaling double and set it to 1.0; Foot
uses compositor-relative sizing. Monitor scale remains untouched. Typed desktop
Undo retains the difference between an explicit value and an unset value.
Missing prerequisites are reported before recovery or Apply can partially write.
The read-only `controller.py doctor` checks capabilities, not rendering or IPC.

Actual Omarchy font changes exposed a second defect: its recognized user
Fontconfig monospace rule could replace explicitly requested fonts with the old
family. The new adapter restricts that rule to the first requested family,
retains unrelated XML and journals owned rules for grouped Undo. Unknown
competing constructs are refused. Distribution rules may have already resolved
a bare generic `monospace`; applications receive explicit selected families.

The panel runs Theme → Fonts → Background → Icons when an icon is selected.
It reports saved/pending/failure results separately and stops later steps after
a failure. Earlier completed changes remain independently undoable. Light and
dark control colors are explicit. Fonts/theme use portable shared toolkit
settings and shipped adapters for Typora, Betterbird, Brave and OnlyOffice;
there are no per-owner font/theme scripts in those adapters. Unknown controls,
custom launch arguments and unsupported/sandboxed profiles remain coverage limits.

Automatic reconciliation runs every 15 seconds only while the plugin is loaded.
Theme generation uses the inspected headless Omarchy route, skips privileged
browser-policy writers and arbitrary post-theme hooks, and refreshes explicit
session interfaces. Normal Hyprland reload still evaluates usual user settings.
Brave/Typora/OnlyOffice profile edits require closed applications. Betterbird
uses its native lock. Periodic reconciliation does not write offline profiles.
OnlyOffice native frame and the earlier Brave theme-launch conflict repair remain
in place; enterprise policy is not overwritten.

## Validation and provenance

See `RELEASE_VALIDATION.md` for versions, metrics and precise coverage. The final
runtime has 21 test programs: 20 isolated host runs and the guest native mail-lock
check. Qt tests use actual Qt5/Qt6 widgets and text widths, not just string equality.
Independent source review reran the affected native, transaction and integration
suites and checked host repair evidence.

The stock VM exercised the real plugin installer, actual GTK/Qt5/Qt6 palette,
font and icon readback, a fresh guest login and exact saved-file Undo. This was
a clean plugin installation in an existing desktop HOME with a recorded baseline,
not a pristine user profile. Both qtct packages and PySide6 are now installed in
the guests; earlier claims based on missing dependencies are superseded.

The 108-case rendered-size matrix covers Foot, Alacritty, Kitty, Ghostty, WezTerm,
GTK3, Qt5, Qt6 and the real shell at 12/14 pt and output scales 1/1.5, across Apply
and actual Omarchy text-size/font changes followed by reconciliation. All measured
baseline pitches were within one logical pixel of Foot on the same output.
Eight GTK/Ghostty cases with explicit GDK_SCALE=2 also passed. Independent image,
native cell metrics and Wayland mapping review supports that bounded result.
The selected font is JetBrainsMono Nerd Font; physical GPU/monitor behavior and
every font/scale combination were not tested. These were fresh app windows;
existing processes may retain cached fonts.

Archive separation matters:

- `6e814d374623cd79b30542ced02da4e20bab6d068397aec58b891248856ccdbe`:
  earlier real installer/login/Undo checks.
- `6458b71d8f28e50fb2ba070c070a4bbd0d01dcf4595088149631278068bbf18b`:
  complete size matrix, including the Fontconfig repair.
- `3cd67d0404fe267d66dabad01837179a9105342357a439791cdd89d2bd5b08a3`:
  real panel light/dark Apply, native toolkit probes and exact Undo, before
  the malformed-Qt fix.
- `d68c7bf132ec47801bbd8924f0cda7b30ef623a3105f32a0f2b7980ce87343ed`:
  final Qt-safe runtime and native regression; guest fault-injection results below.

The panel light/dark flows on archive `3cd67d…` completed Theme/Fonts/Background/Icons with no
pending attention. Fresh GTK/Qt5/Qt6 probes verified the selected font, palette and
fixture icon. Undo returned zero compared application-file differences in both modes; the
desired-state policy was excluded from that byte comparison. Records are
`release-final-stock-{read,probe,undo}-{light,dark}.json`; screenshots accompany
`read` records. Independent source-delta/native-metric comparison of the actual
matrix journal values supports reusing that earlier 108-case evidence for the
final Qt-safe source, rather than claiming an identical serializer or a full rerun.

The final archive passed fault injection of the exact malformed host Qt6 general
and fixed records. Fixture insertion and the real production font Apply body ran
under the production operation lock with normal dependency/recovery preflight,
preventing the background timer from repairing the fixture first. A fresh shell
process loaded Adwaita Sans 13 pt with 361.39 px sample width and 21 px text height;
clock, workspaces and icons remained visible. A fresh Wayland widget launched
through the real user manager confirmed weight 400 and stretch 100. Unsafe Undo
refused before mutation: 32 file targets, 18 journal hashes and four typed desktop
settings remained identical. Test instrumentation was removed and all 57 installed
files again matched the final archive. The final guest native mail-lock check
also passed. Independent review inspected source, nested snapshots and screenshot
hashes. Evidence: `release-qt-cold-stock-*.json`, its restart screenshot and
`release-qt-safe-mail-lock.json`. This is a real shell cold start, not a new full
logout/login cycle on the final archive; the earlier candidate supplied that
separate login-activation evidence.

## Host state and remaining acceptance

Saved choices remain Avenir Next 11 pt, Comic Code Ligatures 11 pt, Alucard for
light and Van Helsing for dark, mode Dark all day. The bar is restored and its
layout is preserved. A new shell has inherited qt6ct; other existing launchers
may still carry the older environment until a fresh login. No host logout was
forced. Reopen and inspect PCManFM, KiCad, Typora, Betterbird, Brave and OnlyOffice
after a fresh login before claiming their rendered host appearance is correct.

The earlier browser-only update completed while Brave was closed; no application
window was launched to claim visual verification. The owner previously confirmed
all five terminals visually, but that does not prove every later size/theme in
all running applications. Do not mark the whole plugin universally release-ready.
Boot unlock remains an intentionally disabled feature.

The lab lives under `Testing/Boot_VM_Lab`, stock/owner SSH ports 22440/22441.
Use its existing guarded tooling; disks are VM files, never host disk passthrough.
The owner VM's temporary monitor/probe setup has been restored. The stock VM's
light/dark and cold-start instrumentation was removed and all 57 final archive
files matched. Its saved fonts remain the repaired 13/12 pt test selection; the
latest font journal deliberately contains the malformed fixture as its before
state, so its Undo safely refuses. Preserve that evidence rather than treating
the refusal as a new regression. Both guests now contain all 57 final runtime files; the owner update preserved a
private source backup and did not explicitly change its appearance configuration.
Raw results, private baselines and recovery backups stay ignored. The reproducible regression tests are in `tests/`.
