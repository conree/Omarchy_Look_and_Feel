# Look & Feel 0.2.0 handoff — 2026-10-26

Source: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`.
Publication: `https://github.com/conree/Omarchy_Look_and_Feel`, branch `main`.
The installed plugin is a symlink to this repository. The host shell was reloaded
and the 0.2.0 manifest/new catalog cache were verified; the fresh log has no
Look & Feel load/type errors. Git identifies publication;
`README.md`, `PROJECT_STATUS.md` and `RELEASE_VALIDATION.md` define supported
behavior and evidence. This handoff supersedes the October 25 operational status.

## Completed implementation

- Inline examples throughout Appearance, with separate application/terminal
  examples per theme. Preview buttons and decorative palette bars are removed.
  All drop-downs now sit below their headings with examples underneath; Mode
  sits next to the three mode buttons on the right. The monospace filter is below
  the terminal sample so the two font sample boxes align.
- Hidden preload, disposable private cache, static image reuse and bounded icon
  lookups. Cached metadata cannot authorize writes. Live inventory supplies all
  Apply/Undo authority. The latest offscreen test measured 44 ms for first
  displayed/captured frame and 3 ms for reopening after preload.
- Explicit authenticated boot-artwork Apply, exact Undo and interrupted recovery.
  Logo changes preserve Plymouth colours and SDDM. The helper uses staged UKI
  builds, complete embedded-asset checks, actual bootloader checksum checks,
  durable private backups and the shared boot lock. Process supervision retains
  exclusion after helper death. Background reconciliation cannot perform boot work.
- Transient lock contention is skipped by background checks and no longer shown
  as a problem requiring user action.
- Qt script/Quick detection, accurate Electron/Flutter distinctions and Qt 5/6
  manual audit registration for documented system-font controls.

## Validation

Full-panel VM-tested runtime/test archive:
`c01b9ad40e7493a7990c3bb749c75e5de20d26e86b00cdcd6b8bb522459d1c43`
(61 files), manifest `Testing/Boot_VM_Lab/tools/finish-runtime-files.json`.
The final archive also passed real panel Apply/Undo in light and dark modes,
with 28 captures, preserved drafts and exact application-file restoration.
A later checkbox-only Panel.qml refinement passed native 820/450 px alignment,
keyboard and interaction checks; its source hash is recorded in
`Testing/Release_2026-10-26/font-alignment-source.json`.
There are 27 isolated test programs. The native mail-lock ownership test must
run outside the sandbox with its own temporary HOME because UID mapping prevents
its stale-owner check inside the sandbox. The other 26 pass inside it.

The exact boot helper passed Apply, independent embedded-artwork extraction,
encrypted cold boot, exact boot-file Undo and a second cold boot in both stock
one-kernel and hardened two-kernel VMs. Injected build failure restores original
boot bytes without requiring another builder run. Evidence is in
`Testing/Boot_VM_Lab/results/finish-boot-acceptance.json`. The normal boot random
seed is excluded from cross-boot comparisons; it is never restored by the plugin.
Root system config and immediate operation EFI/mount invariants were preserved.
VM cold-boot captures show text password prompts. Embedded artwork and bootability
are verified; graphical Plymouth artwork rendering remains unverified.

Independent review checked source, recovery and security boundaries and reproduced
signal/descendant failure cases using real processes. Private VM artifacts,
licensed installed assets and screenshots are not publication payloads.

## Owner action and support limits

The host still runs `QT_QPA_PLATFORMTHEME=gtk3`; `qt6ct` is saved in the same login
session. Save work, sign out and back in once, then reopen applications. Do not
force logout or kill applications with unsaved work. Host visual acceptance after
that login remains unverified, and the recorded preview timings exclude the host
compositor and animations.

Supported boot changes require the standard unsigned Omarchy UKI layout on
`/boot`. Secure Boot/signed images, enrolled Limine configurations, fallback/custom
build options and unhandled sections are refused. Backups and authoritative
receipts live under `/var/lib/omarchy-look-and-feel`; old slug-only user journals
are preserved, never promoted into verified Undo authority.

Shared GTK/Qt defaults and documented native application adapters do not control
arbitrary application CSS, custom editors, unsupported schemas or sandboxed
profiles. No universal application-appearance claim is made.

Never run host sudo or enumerate/access another installed OS. Keep boot hardening
and browser security policies. All boot-write tests belong in the guarded,
file-backed VMs under `Testing/Boot_VM_Lab`.
