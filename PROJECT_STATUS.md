# Project status

Updated 2026-10-26. Version 0.2.0 implements the documented Omarchy appearance
interfaces. Host acceptance after a fresh login remains the owner's final step:
the current session still uses `gtk3`, while the saved Qt selector is `qt6ct`.
No logout or application restart has been forced. VM boot checks verify embedded
artwork and encrypted bootability; graphical Plymouth rendering remains unverified. Application detection does
not imply control of every custom application's fonts or content.

## Completed

- The final 0.2.0 archive passed real light/dark panel Apply and Undo with 28
  captures, all 27 isolated programs in their required environment, and independent
  source/recovery review. All 61 runtime/test files match that archive.

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
  43 ms to the first displayed frame after preloading, and 4 ms on reopening.
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

The owner must sign out/back in to activate any previously saved Qt integration,
then check reopened PCManFM, KiCad, Typora, Betterbird, Brave and OnlyOffice.
This work does not claim their rendered host appearance has been verified.
Existing applications may cache fonts; reopen those retaining the old font.

The measured size result covers JetBrainsMono Nerd Font at 12/14 pt and scales
1/1.5 in VMs. It does not cover every font, GPU or custom scaling environment.
Generic Fontconfig aliases already replaced by distribution rules, custom
application schemas/launch overrides, and sandbox-specific profiles remain
outside automatic coverage. Boot changes require explicit authentication; browser security policy is preserved. Four unused owner-theme image copies were removed from the
current tree; older Git history retains them.
