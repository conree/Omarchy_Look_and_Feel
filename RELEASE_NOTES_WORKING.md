# Working release log

This is a local working record for the next release, not a published changelog.
Only describe a fix as released after it has been reviewed and validated. Keep
unfixed findings out of the eventual fixed-issues list until they are addressed.

## 0.3.0 candidate — draft release description

Look & Feel 0.3.0 adds independent terminal opacity and blur controls, improves
application audit messages and pending-action handling, and makes font and
opacity application more resilient when an optional target cannot be updated.
It also improves Alacritty font handling and recovery of managed settings.

Save your work and close open applications before applying changes, then reopen
them. In particular, Brave's webpage font defaults are applied while Brave is
closed; reopening Brave alone does not complete a previously pending Apply.
Application-owned settings, browser policies and installed browser themes can
affect the result. The Brave fixed-width font-size discrepancy remains under
investigation: the current profile reads 16 CSS pixels for both default sizes,
but the earlier observed value of 13 has not been explained. No claim is made
that every application follows these settings.

The user reports the audit lifecycle, failure-isolation and recovery, Brave
workflow, and Ghostty opacity and blur tests passed; the precise setup of the
failure-isolation test was not independently observed. Screenshots show the
audit warning and a clean panel after applying with Brave and PCManFM closed.
The user's live screenshot shows the revised close-applications text and 0.3.0
label. Alacritty was not tested live because the user does not use it.

The 0.3.0 candidate passed all 33 isolated test programs on 29 October 2026.
The stale-mail-lock check passed outside the process sandbox after its liveness
assertion failed inside it. These checks do not establish live appearance.
The suite was rerun after the launcher-search change. A read-only lookup finds
the installed Nextcloud Office — Test launcher with multiple dash and spacing
variants.
The user subsequently verified the live panel finds Nextcloud Office — Test
using `NextCloud Office-Test`; the screenshot shows the unsupported shared
font-control result. The other dash and spacing variants were checked in the
backend, not individually in the live panel.
The detailed entries below retain earlier observations and their historical
verification gaps; the candidate summary above reflects subsequent reports.

## Changes in progress

- **Unresolved app audits blocked all font changes and later Apply steps.**
  An unresolved audit no longer causes the font controller to return early;
  other blockers are recorded below. Independently tested with an unresolved audit in an
  isolated font transaction; the user also applied Herculanum through the live
  panel with the unresolved audit present, and GTK 3 and 4 settings read back
  Herculanum. The user showed the KiCad menu rendering the distinctive font.
- **Clear Audits left the search and result visible.** The panel now clears the
  query on a successful clear and replaces the old result with confirmation.
  It also removes the old audit warning and stale blocked-font status while
  retaining unrelated pending notices. Editing a query clears the previous
  result so it cannot be attributed to the new query. Panel logic checks pass;
  the user subsequently verified the field and result cleared in the live panel;
  the saved audit registry independently read back empty. Unrelated Brave attention
  remained visible in the user's screenshot.
- **Audit results depended on process callback order.** Both audit and clear
  now wait for the process exit and both output streams before reporting a
  result or clearing the field. The six callback orders and a failed exit were
  checked in an inert panel fixture and independently reviewed; live checks remain.
- **Unrecognized terminals and unsafe app font files blocked other font changes.**
  The font controller skips unavailable terminal adapters and separately handles
  malformed terminal, Typora, Betterbird, and Brave font settings, recording
  pending notices. Isolated production transactions tested malformed Alacritty,
  Typora, and Brave files, with a working Foot target and Undo. The Betterbird
  exception case and unknown-terminal discovery were simulated. Live checks remain.
- **Alacritty nested font tables and array tables were mishandled.** The updater
  and managed-field parser have been changed to handle nested font styles and
  keyboard array tables; isolated Apply/Undo tests cover preserving unrelated
  keyboard and opacity changes. Independently reviewed and tested; live checks remain.
- **A missing dependency blocked automatic repair of other sections.** Checks
  now run per section after required transaction recovery. Isolated tests cover
  missing theme, font and opacity dependencies and recovery failure precedence;
  independently reviewed and tested; live checks remain.
- **Foreground actions could immediately collide with automatic repair.**
  Foreground actions now wait up to 10 seconds for the operation lock; automatic
  repair still skips immediately when busy. A cross-process isolated check covers
  acquisition, skipping, and timeout. Independently reviewed; live checks remain.
- **Ambiguous app searches gave misleading font support results.** The panel now
  distinguishes ambiguous matches, package-only matches and unsupported shared
  controls, and notes that detection does not verify rendered fonts. Panel logic
  checks pass. A live SolidCraft audit showed the old wording because the shell
  was still running a panel loaded before the edits; a plugin rescan had not
  replaced that instance. After restarting the shell, the user audited PaliCAD
  and the screenshot showed the revised unsupported-control wording. A separate
  read-only inspection found its launcher but did not identify its toolkit.
- **A bad terminal configuration could block opacity for other terminals.**
  Unsafe, malformed and oversized targets are skipped with a notice while safe
  targets continue. Tests cover later repair, grouped Undo, no terminal found,
  special permissions and unsafe Ghostty stylesheet links. Independent review
  confirmed bounded leaf reads and tested the paths; live checks remain. Parent
  directory validation is not an atomic defense against concurrent replacement.
- **A stale reconciliation could bring back a cleared audit warning.** Results
  from before an audit change now discard stale audit warnings and request a
  fresh check, preserving other notices. An independent reviewer checked the
  generation logic in fixtures; live scheduling remains unverified.
- **A damaged audit registry could block font changes.** A registry read error
  now leaves the registry untouched, reports its status as unknown and allows
  other font changes. A disposable-home test covers an invalid registry, Apply
  and Undo; independently reviewed and tested, with live checks still needed.

## Confirmed findings not yet fixed

- With Brave open, changing the system font to Visby CF Medium left Brave's
  webpage defaults at SF Pro and Comic Code Ligatures (fixed width), while the
  user observed Visby in the toolbar. The profile and selected-font files were
  independently read; the plugin reported a close-and-apply notice. Automatic
  reconciliation deliberately does not write Brave's profile, even when it
  closes. Review whether a safer, less manual way to apply the defaults is
  possible; toolbar rendering and webpage defaults are separate surfaces.
  After the user closed Brave, applied again and reopened it, the screenshot
  showed “Custom” for standard/serif/sans-serif. The saved Brave profile now
  says `Visby CF Medium` for those three roles, matching the plugin. Fontconfig
  identifies this as an alias of `Visby CF`; the Custom label is consistent with
  that alias but does not by itself prove what Brave renders. Brave's fixed-width
  size read back as 13 while the plugin's 12 pt target converts to 16 CSS pixels;
  the reason for this difference needs investigation.
- The user reports that the 100% terminal background appeared opaque, with no
  wallpaper visible; at 0%, the supplied image shows a transparent background
  and a visually solid coloured prompt. The transaction log confirms a
  50%-to-100% Ghostty setting followed by 0%. Hyprland's configured
  `default-opacity` rule specifies 0.985 active / 0.96 inactive, but its exact
  effective alpha for this window has not been measured. An earlier claim that
  the wallpaper was visible at 100% was incorrect and has been withdrawn.
- The user reports that terminal blur On and Off work. The latest screenshot
  shows a clear background behind the transparent terminal; the saved policy
  and Hyprland rule independently read back blur Off. This does not independently
  verify the On state or blur Undo.
- The user reports the requested opacity, blur and audit-lifecycle checks passed.
  A later screenshot shows the new panel guidance and version label live.
- A Brave pending card remained after a successful Apply even though Brave was
  closed, its font preferences matched the selection, and the latest automatic
  reconciliation reported no pending actions. Section-attributed pending results
  and generation checks were added; isolated tests and independent review pass.
  After a shell restart, the live panel showed no pending action, but that does
  not verify immediate notice clearing in the original Apply interaction.
- Brave font Apply could report the browser was open after termination because
  a stale `SingletonLock` symlink remained. A reporting-only fix identifies a
  probable stale local lock and explains how to recover; the lock still blocks
  writes. Isolated tests and independent review passed; live recovery and Apply
  remain in progress.
- Brave remained dark after the user reopened it under the Dracula Pro Alucard
  light theme. Its profile selects a Dracula Van Helsing theme and a managed
  system browser-colour policy specifies a dark colour. The plugin does not
  update that privileged policy or remove an installed profile theme, and its
  current Brave pending notice concerns fonts rather than toolbar appearance.
  The selected theme's manifest sets a dark toolbar, matching the user's
  screenshot. The additional effect of the managed policy has not been isolated
  in a live test. Do not overwrite managed policies or profile settings without
  a reviewed reversible approach.
- Brave's appearance settings reported that its theme was managed and could not be
  changed. The local root-owned `/etc/brave/policies/managed/color.json`
  contained a dark `BrowserThemeColor`; Omarchy ships a browser-theme policy
  writer which produces that policy format, but the actual writer of this file
  has not been established. A separate test profile also opened with a dark
  toolbar under the same policy. On the user's instruction the file was backed
  up at `/home/si/.local/state/omarchy-look-and-feel/backups/brave-color-policy-2026-10-29.json`
  and the user removed the original; its absence and the backup hash were
  checked. The user selected GTK in Brave, and its live toolbar was observed
  light under Dracula Pro Alucard and dark after the user switched to Ethereal;
  the profile independently read back GTK mode and no extension theme ID.
  This verifies the observed light-to-dark switch, not every theme or transition.
  Normal Omarchy browser-theme policy writes can recreate the removed policy.

## Further investigation

- The user installed Firefox to test a non-Chromium browser. Under Dracula Pro
  Alucard, its live toolbar and new-tab page appeared light and visibly used
  Papyrus, matching the independently checked GTK and plugin selections. The
  plugin has no Firefox-specific webpage-font adapter; arbitrary websites and
  Firefox dark-mode behavior remain unverified.
- PCManFM visibly adopted the light appearance and distinctive selected font
  after the user reopened it, as requested by its pending notice.
- The user reports Brave passed the live checks. The user also observed that
  PCManFM adopts a font change while running but needs reopening for a theme
  change. Its current restart notice monitors font and other appearance
  settings as well as theme-related changes; it does not verify rendering, so a
  font-only change may produce an unnecessary restart notice.
- Alacritty bold-italic font overrides were missed by Apply; inline and nested
  cases now have isolated Apply/Undo coverage and independent review.
- Automatic reconciliation could read through a swapped parent symlink and
  incorrectly skip an update. A descriptor-based comparison read now fails
  closed in an isolated reproduction; independent review passed.
- Re-auditing could leave an old audit warning visible or briefly hide a still
  unresolved one. The revised logic waits for current validated reconciliation,
  including when no font policy exists. Focused fixtures and independent review
  pass; live verification remains.
- Live verification remains necessary for the newer re-audit and notice lifecycle,
  individual failure isolation, and automatic-repair and Undo behavior. The
  Clear Audits field-clearing behavior and revised PaliCAD message were checked
  live as recorded above.
- Unsafe font target metadata is now checked before each optional group joins
  the transaction; isolated tests and independent review cover special mode,
  oversized Alacritty and a Ghostty overlay symlink. The identified font reads
  now use bounded descriptor-based reads and have been independently reviewed.
  Live behavior remains unverified.
