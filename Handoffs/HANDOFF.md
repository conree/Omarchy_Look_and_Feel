# Look & Feel development handoff

Updated: 2026-10-24

Session record: [2026-10-24 handoff](OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-10-24.md).

## Safety and live testing

Do not describe full global Apply as safe or production-validated. Browsing the
panel and changing selections do not apply appearance settings; startup writes
the private inventory record. Theme changes run Omarchy hooks. Boot unlock calls
Omarchy's Plymouth commands, which on this installation invoke `limine-mkinitcpio`;
its integration can update Limine entries as well as boot images. Unlock Undo
reapplies artwork and rebuilds again, not an exact restore of boot files. This
does not meet the owner's requirement to preserve boot settings for live unlock
testing. Full Apply should first be exercised in an isolated environment with
a tested restore path. No irreversible damage was observed; zero risk and
guaranteed recovery have not been established.

A recovery bypass found during this review is fixed: theme/background Apply
and Undo now refuse pending unlock recovery before invoking any setter. Only
an explicitly requested unlock action can enter that recovery. This does not
remove explicit unlock's Limine effects.

## Current state

The panel is intended as one global control surface for system/shell/GTK font
family and size, installed terminal font family and size, theme, boot unlock
design, and desktop background. It contains no application names outside the
missed-app audit input. The panel now has a built-in Help dialog and one bottom
`APPLY` button. The automatic inventory and manual missed-app audit remain in
place. Application names appear only in the audit input; the Help dialog
explains audit use and current support limits.

An optional checkbox labelled `Only show monospaced fonts` now sits below the
terminal family/size controls. It starts unchecked, preserving the full font
list. Checking it filters only terminal menu options to families whose installed
faces Fontconfig classifies as monospace (100) or character-cell (110).
Unchecking it restores all families. The current choice is preserved and its
name stays visible even when absent from the filtered list; toggling does not
write settings or add a restriction to Apply. Office Code Pro remains available
with the checkbox off. Its installed files do not have monospace spacing metadata
and therefore are not included among filtered options. The mandatory exclusion
previously requested and then cancelled has not been reinstated.

Global font Apply and Undo now use a journaled file transaction. The current
adapters write GTK 3/4 settings, Omarchy shell font settings, a saved selection,
and supported terminal configuration files. All 8 detected terminal launchers
map to a reviewed executable and configuration adapter. Foot client/server
launchers share one Foot config target, and Kitty's URL launcher shares one
Kitty config target, for 5 unique terminal config targets overall. Isolated
`/tmp` Apply+Undo checks passed for blank, config-builder, local-config without
a WezTerm binding, and standard WezTerm config fixtures. Missing/blank configs
were made valid and every fixture was restored exactly by Undo; other initially
missing terminal configs returned to absence. An unknown launcher was rejected
before creating a transaction or writing config files.
This does not establish coverage for every installed, sandboxed, or custom
terminal. Global font Apply fails closed when a detected terminal cannot be
matched to a verified adapter.

The single `APPLY` action runs Theme → Fonts → Background. It appends Boot
unlock only after the user changes the unlock selection during the current
panel session; a default selection alone never triggers a boot action. `APPLY`
applies a deliberately changed unlock selection through Omarchy's Plymouth/SDDM
commands and rebuilds initramfs; the installed Limine integration can update
boot entries. Do not test this path during panel
validation. If any step fails, later steps stop and earlier completed steps
remain applied; the Undo control for each section remains available. Icon theme
selection is not applied. Automatic theme mode selects for the current solar
phase when `APPLY` runs; no persistent sunrise/sunset scheduler is wired.

## Remaining work

0. Resolve the unlock action's Limine-entry effects against the owner's boot
   protection requirements before any live unlock Apply/Undo. Validate the full
   Apply failure/recovery flow in an isolated environment first.
1. Add verified per-application theme adapters; the manual audit currently
   registers supported shared font surfaces only.
2. Expand terminal and application discovery/adapter coverage. The current
   terminal adapters cover a limited set and do not establish support for all
   installed, sandboxed, or custom terminals.
3. Add and verify icon-theme Apply/Undo if it remains in scope.
4. Add persistent automatic Light/Dark scheduling after checking coexistence
   with Omarchy's scheduler.
5. Review the current panel live and validate the global flow visually. Do not
   run the unlock step or alter boot configuration during this validation.

## Verification notes

Python syntax checks for the controller, terminal adapter, and inventory
modules passed. The isolated terminal font Apply+Undo check passed as described
above. The removed Betterbird-only CLI Apply/Undo commands
are no longer exposed; no new Betterbird transaction target is allowlisted.
Legacy snapshots remain rollback-eligible. `git diff --check` passed. An
isolated offscreen QuickShell probe confirmed stdout completion can precede
`Process.onExited`; the unlock poll now waits for both events before accepting
readback. The initial Qt 5 lint/format invocations failed. Qt 6 `qmllint`
returned 0 but reported unresolved Omarchy imports/types, so this is not a full
QML validation. The actual font controls were separately rendered offscreen;
mouse-clicking the new checkbox filtered 364 families to 41 and back, keeping
the selected font visible and unchanged. Alias, mixed-spacing, unknown-spacing,
and fixed-cell metadata cases passed. An independent agent reviewed source
and both preview images. Nineteen isolated recovery checks passed with mocked
setters and temporary journals, covering all four pending states, theme/background
Apply/Undo blocking, explicit unlock recovery, and normal background recovery.
No plugin Apply or Undo was run on the live
machine, no machine appearance or boot settings were changed, and the current
full panel has not been visually reviewed live.
