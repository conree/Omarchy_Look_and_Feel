# Project status

Updated 2026-10-25. The plugin is a tested development candidate for Omarchy
4.0.6 / Hyprland 0.56.2. This is not an unrestricted release-readiness claim.
The owner's reopened application appearance after a fresh login remains an
acceptance check. Boot unlock is preview-only and cannot be applied or undone.

## Completed

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
- Twenty final-runtime isolated test programs and the guest native mail-lock
  test pass. Independent review covered source, recovery, native matching,
  icon discovery/UI routing, metadata ownership and rendered-size evidence.
- The real plugin installer, native GTK/Qt5/Qt6 fonts/palettes/icons, guest
  login activation and exact saved-file Undo were exercised. The desktop HOME
  had an explicitly recorded prior configuration, not a pristine profile.
- The 108-case size matrix and eight additional GTK scaling cases pass the
  comparison with Foot for the tested font, sizes and VM output scales.

Light/dark panel Apply and Undo passed in the stock VM. The final candidate also
passed exact malformed-font injection, production repair, a fresh real shell,
native Wayland font metrics and refusal of unsafe Undo with no monitored changes.
Independent review checked screenshots, source and saved evidence.
Publication details are recorded in the session handoff. [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md) gives exact
archives, versions, metrics and evidence limits; [README.md](README.md) gives
installation instructions and supported application interfaces.

## Remaining acceptance and coverage limits

The owner must sign out/back in to activate any previously saved Qt integration,
then check reopened PCManFM, KiCad, Typora, Betterbird, Brave and OnlyOffice.
This work does not claim their rendered host appearance has been verified.
Existing applications may cache fonts; reopen those retaining the old font.

The measured size result covers JetBrainsMono Nerd Font at 12/14 pt and scales
1/1.5 in VMs. It does not cover every font, GPU or custom scaling environment.
Generic Fontconfig aliases already replaced by distribution rules, custom
application schemas/launch overrides, and sandbox-specific profiles remain
outside automatic coverage. No privileged boot action or browser-policy rewrite
is introduced. Four unused owner-theme image copies were removed from the
current tree; older Git history retains them.
