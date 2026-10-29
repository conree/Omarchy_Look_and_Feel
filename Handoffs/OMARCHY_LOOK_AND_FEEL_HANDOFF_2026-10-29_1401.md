# Look & Feel handoff — 29 October 2026, 14:01 MST

Project: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`. The installed
plugin is linked to this source. This handoff supersedes the earlier handoff
of the same date. Consult Git for the exact commit and current working tree.
The user requested a local commit; do not push, publish or make a release
without further authorization.

## User priorities and current state

The user has repeatedly caught incorrect claims and live defects. They require
independent verification of all deliverables, accurate reports of what was
actually observed, focused work, and real application tests for visual or
interactive behavior. Do not ask them to repeat checks already established;
keep them informed and do not present configuration or fixtures as live proof.
Read `/home/si/AGENTS.md` for the standing instructions.

The current request is a handoff and commit, not a release. The working release
log is `RELEASE_NOTES_WORKING.md`; keep it current and use it to prepare the
eventual “About this release”. Some entries preserve the history of resolved
states; this handoff records the latest observations.

## Changes in the local commit

- Audit result wording distinguishes supported shared control, unsupported,
  ambiguous and no-match cases; it does not assert the rendered font. Clear
  Audits clears the query and result after success. Independent panel fixtures
  and the user's live PaliCAD/Clear Audits screenshots support those checks.
- Unresolved or unreadable manual audits no longer abort font Apply. Optional
  terminal and app font targets and terminal opacity targets are isolated;
  unsafe inputs are skipped and reported while other supported targets proceed.
- Added conservative Brave stale-lock reporting; locks remain write barriers.
  Added section-attributed reconciliation notices and generation checks to
  avoid stale warnings, and bounded foreground lock waits. Automatic repair
  checks requirements by section after transaction recovery.
- Fixed Alacritty nested font tables, bold-italic selection and array-table
  boundaries for managed Undo; hardened reads used during font building and
  automatic-repair comparisons. See the release log for scope and limitations.

The latest broad run passed 33 isolated checks; the stale-mail-lock check was
rerun successfully outside the process sandbox. Independent reviewers checked
the affected transaction, UI and backend paths. Fixture and isolated tests do
not prove live appearance, scheduling, or every app/terminal combination.
Some later UI changes require a shell reload before live testing; a previous
plugin rescan left an old panel loaded, while `omarchy restart shell` loaded
the revised wording. Do not restart without considering unsaved panel drafts.

## Latest live observations and outstanding issue

- The user tested Ghostty at 100% and explicitly reported the dark background
  looked opaque with no wallpaper visible. At 0%, the screenshot shows the
  wallpaper and a visibly solid coloured prompt. The user reports blur On and
  Off work. The exact compositor alpha was not measured: the default Hyprland
  window rule specifies 0.985/0.96 for windows tagged `default-opacity`. Do not
  repeat the withdrawn claim that the user's 100% test showed visible wallpaper.
  Blur/opacity Undo and all extremes under active/inactive states remain to be
  tested live as needed.
- The user verified KiCad's menu follows a highly distinctive Herculanum font;
  that does not prove which font was rendered before the change.
- The user observed Firefox's interface and new-tab page in the light theme and
  Papyrus; PCManFM adopted font changes live but required reopening for a theme
  change. A PCManFM restart notice can be conservative for a font-only change.
- Brave toolbar followed a light-to-dark switch after the user selected GTK.
  The root-owned `/etc/brave/policies/managed/color.json` was backed up to
  `/home/si/.local/state/omarchy-look-and-feel/backups/brave-color-policy-2026-10-29.json`
  and the user removed the original. Omarchy's regular browser-theme policy
  writer can recreate it. Do not alter managed policy without a safe, reviewed
  approach; Codex cannot run sudo in this environment.
- **Outstanding Brave issue:** with Brave open, Look & Feel selected
  `Visby CF Medium` while Brave's webpage defaults still showed and saved
  `SF Pro`; the user observed Visby in the toolbar. Those are separate font
  surfaces. The current plugin reports close-and-apply, writes the profile only
  during explicit Apply while Brave is closed, and intentionally does not
  automatically write it during reconciliation. Investigate a safe, usable
  solution without changing a live profile blindly or closing the user's
  browser. The user expects Look & Feel to work without manually changing
  Brave's theme or font menus. A prior `pkill brave` left a stale singleton
  lock; normal reopening and closing cleared it. Do not delete or bypass an
  unverified browser lock.
- A stale Brave notice survived a successful Apply in the live panel even
  though Brave's profile matched and the latest reconciliation was empty.
  New section-aware fixes passed independent fixtures, but a shell restart
  merely showed a clean panel and did not prove immediate live notice clearing.
  Later re-audit warning fixes likewise need a live check.

## Resume safely

Start with the outstanding Brave default-font behavior and the live checks in
the release log. Preserve the user's current desktop, open applications, audit
records and chosen fonts. Use an independent reviewer or genuinely independent
method on the actual artifact and disclose any live-test gap. The user's last
request mentions an overfull cache; no cache deletion was requested or performed
as part of this handoff.
