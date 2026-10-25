# Release validation — 2026-10-25

This is a tested development candidate for the documented Omarchy baseline,
not a claim that every Linux application or hardware configuration is supported.
Boot unlock remains preview-only. Host application appearance after a fresh login
still needs owner acceptance; no host logout or application restart was forced.

## Candidate and environment

Final runtime/test archive: SHA-256
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

## Checks completed

- Twenty isolated Python/JavaScript test programs passed on the final runtime.
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

During this continuation no other installed OS was enumerated, mounted or accessed. No host sudo, boot
rebuild, browser-policy write, compositor-scale change or forced logout was used.
Boot unlock Apply/Undo/recovery remains disabled. VM success does not establish
all Omarchy versions, hardware, app-specific rendering or custom profile paths.
Older Git commits still contain the four removed, unused owner-theme images;
repository history was not rewritten.
