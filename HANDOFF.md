# Look & Feel development handoff

Updated: 2026-10-23

## Current state

The `main` branch contains the Look & Feel panel prototype and the current worktree extends it with installed-app/font discovery, reversible font actions, app-specific review, readback auditing, and Omarchy theme/background/unlock actions. The active bar widget and panel are in `BarWidget.qml` and `Panel.qml`; catalog and action routing are in `controller.py`.

The latest feature adds journaled Apply, Undo, recovery, and readback for Omarchy themes, desktop backgrounds, and boot unlock designs. `appearance_actions.py` records the detected prior value and verifies the result. Theme Apply preserves a wallpaper that lives under Omarchy's generated current-theme directory by keeping a private image copy and restoring its link after the theme swap. The audit compares wallpaper content hashes, so that preserved copy still matches the selected image. Recovery and history pruning protect current and referenced wallpaper backups.

Unlock Apply and Undo open Omarchy's floating terminal so sudo authorization can use a real terminal. The panel polls for a matching installed Plymouth readback before reporting success. The inventory currently exposes 31/31 themes and 24/26 unlock designs as selectable. Vantablack and White are excluded because they share the same logo image; Omarchy's `plymouth current` cannot distinguish them. Symlinked unlock assets and assets matching Omarchy's default logo are also excluded from automatic application.

The automatic theme choice applies the current solar phase once. No future sunrise/sunset scheduler is wired. Icon-theme selection remains draft-only. System-wide font Apply remains unavailable; current font actions cover Ghostty and Betterbird, while shared GTK settings are audited as a common surface.

## Rollback and audit limits

- Theme Undo re-runs Omarchy's setter for the previous detected theme. It re-runs normal theme hooks, but cannot reverse arbitrary side effects from custom hooks or restore every generated application setting byte-for-byte.
- Unlock Undo re-applies the previous detected design through Omarchy's Plymouth/SDDM commands. Those commands rebuild initramfs. Readback verifies installed Plymouth artwork but does not inspect the image in the next-boot initramfs.
- Background Undo restores the previously resolved wallpaper path. Theme-owned wallpapers receive a private backup when the generated theme directory is replaced.
- The read-only audit checks selected font settings, theme name/palette, wallpaper image content, and installed Plymouth artwork. It cannot prove rendered pixels or that a boot image contains the installed artwork.
- The application census is best effort. It does not promise to find or configure every installed Linux application; manual app lookup remains separate from startup inventory.

Omarchy paths follow its documentation: stock themes are under `$OMARCHY_PATH/themes`, user themes under `~/.config/omarchy/themes`, extra per-theme backgrounds under `~/.config/omarchy/backgrounds/<theme>`, and the active background link under `~/.local/state/omarchy/current/background`. Root resolution is environment, `/etc/omarchy.conf`, then `/usr/share/omarchy`; resolved `OMARCHY_PATH` is passed to noninteractive Omarchy commands.

## Verification completed

- Python source syntax compiled successfully with Python's `compile()`.
- `git diff --check` completed without whitespace errors.
- Read-only catalog check reported 31 selectable themes and 24 selectable unlock designs; Vantablack and White were the ambiguous pair.
- Three parallel reviewers inspected action safety, catalog/audit linkage, and panel behavior. Their findings about wallpaper loss on theme switches, logo ambiguity, history pruning, sudo interaction, automatic-mode auditing, and undo feedback were incorporated.
- No Apply action was run against the live desktop during this implementation work.

## Next work

1. Validate the panel visually and exercise one Apply/Undo cycle per action on the owner's system, starting with a wallpaper whose source is inside `~/.local/state/omarchy/current/theme`.
2. Check the unlock terminal's authorization and initramfs rebuild path on the target Omarchy installation; compare the installed artwork and next-boot behavior separately.
3. Decide whether to add persistent automatic theme scheduling and an icon-theme Apply adapter.
4. Continue app-specific font adapter coverage and update the support matrix only when each control point has verified readback and rollback behavior.

The apply/rollback behavior and its limitations are also documented in `APPLY_TRANSACTION.html`, `README.md`, and Section 21 of `DESIGN_BRIEF.md`.
