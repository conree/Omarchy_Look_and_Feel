# Look & Feel — handoff immediately before the owner's restart

Captured 2026-10-28 around 09:19 America/Phoenix. The owner is restarting the
physical machine voluntarily, then opening a new session. This handoff records
state and evidence; source authority remains `SOURCE_OF_TRUTH.md`.

## Resume after restart

1. Preserve the working tree in `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`.
   HEAD is `b2d36988b7811210d53ec71da6512778fb5e3679`, branch `main`. Subsequent
   Brave fixes, test-fixture corrections and release documentation are saved
   locally and **not committed/pushed**. Do not reset, restore or pull over them.
2. Confirm the owner's restart booted and unlocked normally; record any bar,
   font or artwork issue. A successful user restart does not establish every
   outstanding physical-host acceptance criterion.
3. Re-read actual saved state. Latest pre-restart choices are **Dracula Pro
   Nosferatu**, **SF Pro 12 pt** system font and **Victor Mono 12 pt** terminal
   font. Do not revert these to the earlier Visby/Office Code Pro choices.
4. Continue physical-host application/monitor/scaling checks, then review the
   local changes for commit/push when requested. Do not repeat the completed
   automated/VM sweep unless changes or failures justify it.

## Repository and publication

- Repository: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`.
- Remote: `https://github.com/conree/Omarchy_Look_and_Feel.git`.
- Installed plugin: `/home/si/.config/omarchy/plugins/si.omarchy-look-and-feel`,
  a symlink to this repository; local runtime changes are used on the host.
- Commit `b2d3698`, containing the save-work reminder and PCManFM restart notices,
  was pushed to `origin/main` and the remote ref was verified.
- Before this handoff, these files were modified locally:

  ```text
  FontActionResult.js
  PROJECT_STATUS.md
  README.md
  RELEASE_VALIDATION.md
  SOURCE_OF_TRUTH.md
  browser_font_actions.py
  controller.py
  tests/check_appearance_result.js
  tests/check_browser_fonts.py
  tests/check_font_pending.js
  tests/check_font_result.js
  tests/check_font_transactions.py
  ```

This handoff and its pointer add documentation changes. No stable release tag or
claim of complete physical-host acceptance was made.

## Completed release tests

Tested runtime/test archive SHA-256:
`a4e1c070ebb2970c12aa54ef5c03cc31bf64902517ade5d17908a810261cb6cd`.
Its 63 file hashes match local runtime/tests; parent commit is `b2d3698`, with
the subsequent local changes included by hash. See `RELEASE_VALIDATION.md`.

- **28/28 test programs passed.** The unchanged native mail-lock test passed
  outside the sandbox, whose ownership mapping otherwise invalidates that test.
- Initial failures were three test-fixture defects: two JS fixtures omitted the
  new restart helper; one transaction fixture inherited the host Qt selector.
  Fixtures were corrected, notice assertions added and the final suite passed.
- Current-build stock VM light/dark four-step Apply, 14 capture phases per mode,
  drafts/scrolling/layout and exact Undo passed. Independent review verified all
  28 image hashes, stable settings digests, restored desktop/background and
  unchanged prior journals.
- Actual plugin-manager installation/enable, inventory, doctor, disable/re-enable
  and fast-forward update passed in a clean HOME with separate XDG directories
  and keyfile GSettings. This shared the existing VM user/packages/compositor;
  it was not a pristine OS. Original VM shell restored; stock/Mesa/polkit warnings
  were retained without claiming a warning-free fresh desktop.
- Real VM PCManFM kept its old **palette** until reopened; its font size updated
  live. The notice appeared, then cleared after exit/reopen and reconciliation.
  Final run checked source hashes, locked snapshots, its own Undo IDs, and exact
  restoration of managed files/desktop settings.
- Graphical pkexec Cancel/Apply/Undo passed through the VM desktop session.
  Cancel preserved boot files. Apply/Undo preserved configuration, EFI and mount
  invariants. SSH lacked a graphical agent, so the final case launched through
  Hyprland, matching the normal desktop path.
- Graphical Plymouth displayed the requested logo, lock and password field;
  encrypted unlock passed. A temporary Limine fixture requested graphics despite
  the lab serial console. It was restored before exact artwork Undo. The restored
  image passed another encrypted cold boot. Only the documented per-boot entropy
  seed differed. The text-based OCR helper could not identify the text-free
  graphical prompt; it was visually confirmed before the lab passphrase was sent.
- Native host doctor passed **13/13** checks outside the sandbox. This proves
  dependency readiness, not rendered correctness of every owner application.
- Independent review verified code, source/evidence hashes and native captures;
  no blocker was found within the tested scope.

The disposable stock VM is **stopped**; managed settings/boot assets were restored.
Its pre-test checkpoint is
`/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Testing/Boot_VM_Lab/guests/stock/checkpoints/release-20261028-before`.
The agent did not change host boot assets or force owner-app closure, logout or
reboot. Disposable native test processes did run on the host.

## Brave finding and local fix

Earlier, Brave's Standard/Serif/Sans-serif selectors displayed **Custom** for
**Visby CF Medium**. Saved preferences were correct. Brave lists primary family
names; Medium is a secondary Fontconfig alias. Replacing it with the listed
parent `Visby CF` would select Regular and lose the requested Medium face.

Disposable native Brave DevTools tests proved inherited/default, serif and
sans-serif rendered `VisbyCF-Medium`; monospace rendered `OfficeCodePro-Regular`.
Explicit parent `Visby CF` rendered `VisbyCF-Regular`.

Local `browser_font_actions.family_notes()` detects such aliases; the controller
returns `fontNotes` and `FontActionResult.js` explains the label. It is an
informational note, creates no pending action and preserves the exact font.
It is returned even when preferences already match. Math fonts remain outside
the managed fields. The owner subsequently chose **SF Pro / Victor Mono**; latest
Brave standard/serif/sans-serif are SF Pro, fixed is Victor Mono, sizes 16/16 px.

## Nosferatu installation and the flat background

Installed and independently verified:
`/home/si/.config/omarchy/themes/dracula-pro-nosferatu`.
Source bundle: `/home/si/Documents/dracula-pro-v2.2.4`.

- **73 installed files**, matching provenance; 58 original source checksums
  verified. Paid assets remain local, outside the public repository.
- All 16 ANSI values match `design/palette.md`'s Nosferatu terminal table and
  the Ghostty exporter. Design Purple supplies accent `#B3A6BC`; background
  `#17191B`, foreground `#D2D0CB`, selection `#2E3236`, muted/cursor `#9EA4AC`.
- Modern/legacy colors, four color-only terminal configurations, the installed
  Dracula icon family, local preview and plain background are supplied. Live
  terminal refresh can normalize cursor/ANSI black; exact supplied values are
  preserved in configuration files.
- `vscode-theme.json` exactly matches the Nosferatu JSON in the bundled VSIX.
  Omarchy's normal local-theme hook can use it in Code-family editors, including
  installed Cursor, when this variant is selected.
- Dedicated app resources/instructions are under `applications/`; inspect
  `applications/inventory.json` for the supplied formats.
- Original Vim engine unchanged; a local Nosferatu palette driver was added.
  `neovim.lua` points to Omarchy's fixed
  `~/.local/state/omarchy/current/theme/applications/vim` path. Isolated native
  Neovim checks passed Normal foreground/background and all 16 terminal colors,
  including a nondefault XDG_STATE_HOME compatibility check.
- Original Vim/Zed packs did not have Nosferatu. Vim has the documented adapter;
  the retained original Zed pack is not represented as a supplied Nosferatu theme.
- Collecting the assets did not separately install/activate other app extensions.
  Installation did not activate the desktop variant; the owner selected it later.

**The flat wallpaper is intentional.** The bundle has no Nosferatu wallpaper.
The installed 3840×2160 background is solid `#17191B` at
`/home/si/.config/omarchy/themes/dracula-pro-nosferatu/backgrounds/nosferatu.png`.
The owner asked whether the blank desktop was correct, and this was confirmed:
the screenshot center and installed image both equal RGB `(23,25,27)`.
Another wallpaper can be chosen from Appearance later.

No Nosferatu boot artwork was created. Pre-restart host boot-artwork status was
`state: none`, Undo/recovery unavailable, Apply available. Selecting the desktop
variant is not proof of a boot-logo change.

## Durable evidence for the new session

Private evidence base:
`/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Testing/Release_2026-10-28/`.
It is ignored by Git. Relevant files/directories:

```text
acceptance-summary.json
checks-final.json
runtime-files.json
vm-ui-complete.json
vm-live/pcmanfm.json and screenshots
vm-fresh/fresh-profile.json, fresh-shell.log and screenshot
brave-Visby_CF_Medium.json and native screenshots
boot-gui.json and authentication screenshots
graphical-boot.json and graphical-applied-unlock.png
host-doctor-native.json
pre-restart/state.json
pre-restart/working-tree.patch
pre-restart/nosferatu-provenance.json
pre-restart/build_install_nosferatu.py
pre-restart/augment_nosferatu_apps.py
```

The helper scripts/provenance originally under `/tmp` were copied to this durable
directory. The theme is already installed; do not blindly rerun builders/installers.
The pending patch snapshot predates this handoff's own documentation edits.
`/tmp` staging may disappear at reboot and is not needed for resuming.

Additional raw VM evidence is under
`/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Testing/Boot_VM_Lab/results/`.
Final UI prefix: `design-ui-a4e1c070ebb2-`. New boot prefixes:
`stock-release20261028-graphical-` and `stock-release20261028-boot-gui-`.

## Remaining acceptance and working constraints

- Record actual PCManFM, KiCad, Typora, Betterbird, Brave and OnlyOffice behavior
  on the owner's monitors, plus supported terminal font/size behavior.
- Check real theme/fonts/icons, monitor scaling and restart notices. Follow
  actual Applications messages, including Brave's close-then-Apply requirement.
- Verify launcher Qt integration after restart. The prior agent already used
  `qt6ct`; do not demand another logout based on older dated inactive-selector
  notes alone.
- Physical hardware boot-artwork acceptance remains distinct from successful
  VM boot checks. No host artwork Apply/Undo sequence has been performed here.
- Before any later disruptive app closures/logouts/reboots, establish that newly
  opened work is saved. This owner-initiated restart is not blanket permission
  for later session termination.
- Follow the Omarchy skill for user configuration. Never edit packaged
  `/usr/share/omarchy` files; preserve boot hardening and browser security policy.
- Follow `/home/si/AGENTS.md`: independently verify outcomes; do not launch host
  sudo or leave sudo password prompts waiting. Use the normal explicit
  authenticated boot workflow only when authorized.
- Keep licensed Dracula Pro assets and all private `Testing/` evidence outside
  public Git commits. Preserve the uncommitted fixes and release documentation.
