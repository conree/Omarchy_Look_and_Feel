# Look & Feel session handoff — 2026-10-24

## Repository and checkpoint

- Repository: `https://github.com/conree/Omarchy_Look_and_Feel.git`, branch `main`.
- Source: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`.
- Previous commit: `a4a58ea`. This handoff accompanies the next source checkpoint.
- User requested a handoff, commit, and push. This includes the accumulated
  reviewed panel/font/audit work and the optional terminal-font filter. It is
  not a production-readiness declaration.
- Handoffs are stored in this project's `Handoffs/`. Earlier handoffs are
  preserved here; their historical paths and statuses are not current.

## Owner decisions and implemented changes

- Treat all applications equally. The panel contains no named-app controls or
  application names outside the manual audit input. Retain the installed-app
  census and missed-app audit mechanism.
- Retain global fonts/sizes, theme, unlock, and background controls, with
  consistent typography and dropdown dimensions. Light/Dark themes are stacked
  on the left; Mode/Boot unlock are on the right. Background is one column wide.
- One bottom `APPLY` button, with section Undo controls. Preserve the requested
  Linux coverage disclaimer verbatim. Help explains behavior and limitations.
- The mandatory monospace restriction was cancelled and reverted. Its replacement
  is the exact-label checkbox `Only show monospaced fonts`, unchecked by default.
  It filters menu options by Fontconfig spacing (100/110); the current choice
  stays visible and selected even if absent from the filtered list. It does not
  write settings or restrict Apply. Office Code Pro remains available with the
  checkbox off; its installed files lack qualifying spacing metadata.
- Global font transactions cover GTK 3/4, shell fonts, and detected terminals
  with verified adapters. Eight launcher records share five terminal config
  targets. WezTerm handles initially absent configs and missing module bindings.
- Manual audit persists supported shared font surfaces and revalidates them on
  Apply; unsupported/unresolved registrations block font Apply. Per-application
  theme registration remains incomplete.
- Show panel changes for review. This session showed an isolated rendering of
  the actual font controls, not a live screenshot of the complete panel.
- Preserve boot protections. The required reference read during this review is
  `/home/si/Documents/OMARCHY_SYSTEM_BIBLE_RESTORE_2026-09-19/current/OMARCHY-BOOT-PROTECTION.md`.
  Consult its boot-route section directly; do not duplicate or infer its conclusions.

## Safety assessment

**Do not recommend full Apply/Undo on the owner's primary installation yet.**
Zero risk cannot be guaranteed. No irreversible damage was observed, and these
findings do not establish that it is likely; they also do not establish that
every failure is recoverable.

Opening the panel, selecting values, and toggling the checkbox do not apply
appearance settings. Startup saves the private census and may create plugin
state directories. Manual audit also persists registrations.

Global Apply runs Theme → Fonts → Background, adding unlock only after the user
deliberately changes its selector. A failure stops later steps while earlier
successful steps remain applied. Theme Apply executes Omarchy commands and
hooks; Undo reapplies the previous theme and cannot reverse arbitrary hook
effects. Font snapshots restore the managed files, not all possible effects of
application restarts or configuration interpretation.

Unlock Apply/Undo is more invasive. Read-only inspection found that installed
`/usr/share/omarchy/bin/omarchy-plymouth-set` calls `sudo limine-mkinitcpio` when
available. `/usr/share/libalpm/scripts/limine-mkinitcpio-install` calls
`limine-entry-tool` to add/update/remove entries. This can change Limine entries
as well as boot images and does not meet a guarantee of preserved boot settings.
Undo rebuilds using the prior design; it does not restore exact boot files.
Artwork readback does not prove the next boot image is valid. No live Apply,
Undo, sudo, boot rebuild, or boot-protection modification was run this session.

The safety review found and fixed an unintended recovery path: a pending unlock
journal could be replayed during theme/background Apply or Undo. Those actions
now refuse pending unlock recovery before invoking any setter. Only an explicit
unlock action can perform that recovery. The fix does not remove explicit
unlock's Limine effects or establish whole-system safety.

## Checks and independent reviews

- Earlier isolated temporary-home font Apply/Undo checks passed for terminal
  aliases and four WezTerm config shapes, including missing files/imports.
  Unknown launchers stopped before writes. These fixtures do not cover every
  installed, sandboxed, or custom application.
- Actual font-control QML was extracted into an offscreen harness. Qt mouse
  clicks exercised unchecked → checked → unchecked: 364 → 41 → 364 families,
  preserving the current visible selection. Metadata fixtures covered aliases,
  mixed faces, unknown spacing, proportional/dual width, and fixed cell.
- Preview files: `/tmp/look_and_feel_checkbox_off.png` and
  `/tmp/look_and_feel_checkbox_on.png`; harness:
  `/tmp/look_and_feel_checkbox_preview.py`. These are temporary development
  artifacts. An independent agent reviewed both screenshots and source.
- `tests/check_unlock_recovery.py` contains 19 isolated checks: four pending
  states × theme/background × Apply/Undo, explicit unlock Apply and Undo
  recovery, and normal background recovery. Setters are mocked, `_omarchy` is
  forbidden, and journals are confined to temporary directories. A separate
  reviewer independently reran the original harness and approved the guard.
- Python syntax and whitespace checks passed. Qt 6 lint previously returned
  zero with unresolved Omarchy imports/types; that is not full QML validation.
  The complete panel/global flow has not been visually reviewed or exercised
  live against the owner's settings.
- Python caches are ignored; generated previews and temporary homes are not
  release/deployment files.

## Next steps

1. Resolve explicit unlock's boot-entry effects against the owner's preservation
   requirement. Do not test it on the primary installation as currently wired.
2. Validate the full global sequence, partial failures, and recovery in an
   isolated environment with a tested restore path, then obtain live UI acceptance.
3. Add verified application font/theme control surfaces beyond shared font
   adapters while preserving equal treatment and the manual audit workflow.
4. Complete icon-theme Apply/Undo and persistent Automatic theme scheduling.
5. Verify the active plugin deployment and reload behavior. The earlier scan of
   the standard plugin directory did not identify the active Look & Feel copy;
   do not assert an existing screenshot reflects this source checkpoint.
