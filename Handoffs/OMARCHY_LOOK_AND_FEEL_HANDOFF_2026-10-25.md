# Look & Feel session handoff — October 24–25, 2026

Updated after midnight October 25, America/Phoenix. This records the long session
begun October 24 and supersedes the operational status in the older handoff.
It records state, not design authority. The root source and status documents
identify the working implementation.

## Owner requirements and safety boundaries

- Do not inspect, enumerate, mount, or change another installed OS. This includes
  `lsblk`; the owner will run such a command personally only after its need is
  explained. No host disk enumeration is needed for this plugin work.
- Do not run host sudo or open password prompts. Preserve boot hardening and
  browser enterprise/security policies.
- Boot unlock is **preview-only**. Its Apply, Undo, and automatic recovery routes
  are blocked in the UI and backend. Do not re-enable them on the host.
- Independent verification is a standing requirement. Distinguish saved settings,
  requested reloads, and actual rendered results. No claim covers every Linux app.
- Commit and push were explicitly requested at the end of this session.

## Installed state

Repository: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`, branch `main`, remote
`https://github.com/conree/Omarchy_Look_and_Feel.git`.
The installed plugin at
`/home/si/.config/omarchy/plugins/si.omarchy-look-and-feel` is a symlink to this
repository. Editing it changes the live installation; stage development elsewhere.

The user's saved selection is Avenir Next 11 pt and Comic Code Ligatures 11 pt,
Dracula Pro Alucard for light, Dracula Pro Van Helsing for dark, mode Dark all day.
The current theme remains Van Helsing. The latest journaled host theme operation
is `20261025T071229Z-37aa9ea92577`; it saved the Qt integration and refreshed the
current theme without switching themes. Hyprland reported no configuration errors.
Its only pending theme action is a fresh login for Qt. The font operation was not
rerun during this final theme-only update.

OnlyOffice's native frame is already configured. The plugin no longer emits an
unconditional reopen notice on every Apply/reconciliation. A changed launcher
still produces a reopen notice if the application is running.

Brave was initially running, so the closed-profile guard correctly left its
11 pt size update pending. During final verification its profile lock cleared;
a native process check confirmed it had exited. Journaled child transaction
`20261025T072059Z-387186e89099` then completed the browser-only font update under
the existing Fonts Apply `20261025T063613Z-044dda9ce1d0`. Saved standard/serif/sans
families remain Avenir Next, fixed-width remains Comic Code Ligatures, and both
saved sizes are now 15 px (11 pt). Settings readback passed. Reopened browser
appearance is still an acceptance check; no browser window was launched.

## What changed across this session

The plugin now stores one desired appearance policy and reconciles supported
settings every 15 seconds while its bar widget is loaded. Automatic light/dark
mode follows the solar phase. Explicit Apply runs Theme → Fonts → Background;
pending applications are reported separately from failed operations.

Shared toolkit settings are the first integration layer: GTK 3/4, desktop
GSettings, Qt, shell, and detected terminals. Application adapters ship in the
plugin for application-owned interfaces: Typora's theme/profile/CSS, Betterbird
font preferences, Brave's default-profile fonts, and OnlyOffice's frame.
Adapters derive settings from the selected palette and font roles; they contain
no dependency on this owner's font or Dracula theme choices. Unreviewed app
schemas, custom launcher/config overrides, and sandboxed package paths remain
coverage limits, not silently claimed successes.

The journal tracks owned fields in shared preferences and groups automatic
repairs with their initiating Apply. Theme and Font Undo preserve one another's
settings and unrelated app preferences. Interrupted operations recover from
journals; conflicting unowned changes cause a refusal. Betterbird uses its
native lock; stale local lock cleanup requires additional checks and a private
audit. Periodic reconciliation never writes the offline browser/editor profiles.

The panel has explicit light/dark control palettes and handles asynchronous
stdout/stderr/exit ordering. ShellFontBridge provides one shared runtime font
binding, including multiple-monitor lifetime and restoration of the original
binding. Font points are converted to shell logical pixels. Terminal reloads
preserve sessions; Ghostty has a contrast floor, Foot color refresh is restricted
to owned PTYs, and WezTerm font/theme blocks preserve original Lua settings.

Theme generation uses the inspected Omarchy headless path. It avoids the normal
post-theme hook chain and privileged browser-policy writer, then explicitly
refreshes desktop/shell/terminal interfaces. Hyprland reload still evaluates its
normal user/theme configuration. Theme Undo restores the previous theme's desktop
defaults, not independently customized pre-Apply theme GSettings. Font GSettings
Undo preserves explicit versus unset values.

The conflicting Brave unpacked theme-only launch flag was removed earlier while
preserving unrelated extensions and policy. The plugin does not rewrite managed
browser custom tint policy. The earlier crash-producing headless Typora CSS
experiment is quarantined under ignored local Testing data and is not a release
test or part of the commit.

## Qt integration correction

Omarchy selects the GTK platform integration. Actual native probes showed Qt 6
using the selected font and dark palette, while Qt 5 inherited the font but kept
a default light palette. Simply saving qtct files did not activate them.

`qt_integration.py` reads installed Qt plugin metadata without loading those
libraries. A shared selector is chosen only when both Qt5 and Qt6 qtct plugins
advertise it. On this host it is `qt6ct`; both majors advertise that alias.
PySide6 is required for this metadata inspection. Missing or incompatible
integration support remains an actionable pending result.

An explicit Apply adds one owned block at the end of the standard user
`hyprland.lua`, setting `QT_QPA_PLATFORMTHEME` through `hl.env`. No activation
variables are changed directly. The block records the originating compositor
session. Pending status stays until a different session has the compatible
selector; restarting only the shell in the same session does not clear it.
Omarchy/Hyprland import the compositor environment at startup. Existing launchers
retain their inherited environment, so a fresh login is required.

Undo removes/restores the owned field while retaining unrelated edits before the
block. Edited markers, appended content after the block, unsupported control
flow, and shadowed Lua API names cause safe refusal. Undo of a changed integration
also reports a fresh-login boundary. This is intentionally limited to the
reviewed Omarchy Lua layout; it does not rewrite arbitrary compositor configs.

## Verification and material limits

The owner visually confirmed all five terminal types earlier: Alacritty,
Ghostty, Kitty, Foot and WezTerm. That does not prove the remaining application
interfaces or the new 11 pt selection render correctly after reopening.

Earlier real QML tests in both lab VMs exercised the complete panel Apply in
light/dark modes, including native shell font readback and readable controls.
The final Python changes did not change that QML. Independent review checked
the recorded screenshots/results. Native GTK readback and grouped Undo were
also exercised in both VMs.

The final check run contains 17 successful commands: transaction/file safety,
app/mail/browser fonts, real isolated Gio restoration and failure recovery,
28 mocked boot-recovery/gate checks, portable ownership/CSS/drift, native Lua/PTY
terminal behavior, actual Qt widgets, actual shell binding lifecycle, JS process
completion handling, Qt6 QML parsing, and new Qt session integration regressions.
A separate reviewer independently reran session tests and actual Qt5/Qt6 widget
probes, and checked the underlying code and evidence.

Final tests in both VMs passed Theme/Fonts Apply/Undo, drift repair/idempotence,
real GTK readback, boot-unlock refusal, actual Hyprland parsing after adding the
Qt block, and exact Hyprland-file restoration after Undo. The minimal lab guests do not
contain qt5ct, qt6ct or PySide6: their Qt metadata was a fixture for the Hyprland
configuration test. Actual Qt5/Qt6 native widget font/palette readback was verified separately in
offscreen temporary homes on the host. **A complete logout/login activation cycle
has not been exercised.** Neither these tests nor the two VMs establish universal
application or boot safety.

Local evidence, deliberately excluded from Git:

- `Testing/Boot_VM_Lab/results/attention-unit.json`
- `Testing/Boot_VM_Lab/results/attention-owner.log` and `attention-stock.log`
- `Testing/Boot_VM_Lab/tools/attention_guest.py`
- `Testing/Boot_VM_Lab/tools/attention-candidate-files.json`
- `Testing/Portable_Appearance/attention-deployment.json`
- `Testing/Portable_Appearance/attention-host-apply.json`
- `Testing/Portable_Appearance/attention-browser-completed.json`
- Earlier panel evidence: `Testing/Boot_VM_Lab/results/portable-ui-*-light.json`
  and `portable-ui-*-dark.json`, plus the corresponding screenshots.

Final tested archive SHA-256:
`b9a35c8de98c2f7cac0fd53c1e2685f4c032ac2cfa562241ce506b02f27b0041`.
It includes the subsequently quarantined headless-browser Typora CSS fixture,
which was excluded from the final validation run; the
committed source excludes that experiment. Functional source matches the tested
manifest. Deployment backup is in
`Testing/Portable_Appearance/backups/20261025T071152Z`.

Both VM plugin copies were updated to the 50 reviewed source/test files; their
installed-file checks passed and the quarantined experiment was removed.

The existing lab is under `Testing/Boot_VM_Lab`, with stock/owner guests and
localhost SSH ports 22440/22441. Use its guarded scripts; do not recreate a host
hardware survey. Guest images, keys, owner-state archives, licensed assets,
screenshots and backups must remain private and ignored. Root `.gitignore`
excludes the entire Testing tree. Reusable tests live in `tests/`.

## Next actions

1. Save work, sign out and back in, then reopen the panel and Qt applications.
   Confirm the Qt login notice clears and Qt application menus use the chosen
   font and palette. Check the GTK3 PCManFM interface separately. This is the outstanding real-session acceptance check.
2. Reopen Brave and verify its standard, serif and sans fonts are Avenir Next;
   fixed-width is Comic Code Ligatures; both saved defaults are 15 px for the
   selected 11 pt size. The closed-profile update is now complete.
3. Verify Typora prose/code, Betterbird composition fonts, KiCad interface fonts,
   and OnlyOffice's border after reopening. Do not equate generated settings with
   visual acceptance. Record any remaining specific mismatch.
4. Keep boot unlock preview-only. Icon selection is also not implemented as
   Apply/Undo. Broader application discovery/adapters and packaged environments
   need their own evidence before expanding support claims.
5. For future regression runs, add the optional Qt packages to dedicated VM
   fixtures and test a complete fresh-login/Undo cycle. Do not turn the existing
   metadata-fixture test into a claim of native VM Qt coverage.
