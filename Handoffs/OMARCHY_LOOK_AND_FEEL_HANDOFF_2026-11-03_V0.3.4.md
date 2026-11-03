# Look & Feel handoff: 0.3.4, Brave highlights and Flea integration

Date: 2026-11-03 (America/Phoenix).

## Authority and authorization

Repository: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`, branch `main`.
Installed plugin: `/home/si/.config/omarchy/plugins/si.omarchy-look-and-feel`,
a symlink to that repository. Remote: `https://github.com/conree/Omarchy_Look_and_Feel.git`.

The owner explicitly requested this handoff, a commit and push of the Brave fix
and earlier Flea integration, and release version 0.3.4. This supersedes the
November 2 local-only/no-push instruction. The earlier Flea work is already in
local commit `08c949b02d8c11add301780ab86801f2b8289c54`; fetched `origin/main`
was its parent before this release. The new release commit includes this handoff,
the menu fix, version identifiers and release documentation. `v0.3.4` is the
release tag; verify the remote branch and peeled tag against the release commit
after pushing. Publication completion is established by those refs, not this
pre-commit document.

## Brave diagnosis and correction

Brave's Appearance page initially blocked **Use GTK** because
`/etc/brave/policies/managed/color.json` contained BrowserThemeColor. The owner
was given a sudo command to move it to
`/etc/brave/policies/disabled/color.json.disabled-20261103`, reload policies,
and select GTK. The agent did not execute sudo. That move is separate from this
release; no privileged policy edits are part of the plugin patch. The existing
user policy-helper override is outside the repository. Installers or updates may
recreate the policy; its latest writer was not established.

The active GTK base was Adwaita-dark, with Look and Feel's palette overrides.
The purple selection color was `#9580ff`, but the generated stylesheet covered
button/row hover and omitted menu-item hover. The source change in
`application_themes.py` adds:

```css
menu menuitem:hover {
  background-image: none;
  background-color: <selection color>;
  color: <readable selection foreground>;
}
```

The colors come from the current palette; they are not hardcoded to Van Helsing.
Both active GTK stylesheets received the current purple/black rule through the
existing transaction layer, transaction `20261103T143325Z-703ac34a6be1`.
Future theme applications regenerate it. No window/terminal background rule was
changed. The owner confirmed the pink/purple highlight in the real Brave
bookmark menu. Automated desktop navigation attempts were inconclusive and are
not presented as visual verification.

## Flea work included

Commit `08c949b` adds generic sans-serif/monospace font preferences and a separate
Flea background-opacity control with Apply, Undo and automatic repair. Flea
retains its fixed-width layout and uses the selected terminal family. Native
background alpha preserves opaque text/icons. A fully opaque-started window may
need reopening after lowering opacity; the plugin reports that limitation.

Generic fonts require the one-time loader described in README. It is already
installed on this machine; the release does not run sudo or change it. Shared
shell TOML ownership preserves unrelated fields and independent font/opacity
Undo. No Flea application-source changes are part of this repository release.

Earlier implementation, live checks and limits:
[/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-11-02_FLEA_FONTS_AND_OPACITY.md](/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-11-02_FLEA_FONTS_AND_OPACITY.md).
That document's historical no-push restriction is superseded above; its
observations remain historical, not newly repeated checks.

## Verification and release boundary

Independent review passed for the menu generator and active GTK artifacts.
The owner supplied the live Brave acceptance check. Portable-appearance tests
passed after the menu fix. During 0.3.4 preparation the generic-font, Flea opacity,
terminal opacity, font transaction and Fontconfig policy checks passed.
RELEASE_VALIDATION.md distinguishes those checks from prior live Flea evidence.
No new full-suite, GTK 4 rendering or broad theme sweep is claimed.

Manifest, panel version label and README are bumped to 0.3.4. Release notes,
project status and validation document the combined scope. The source-of-truth
entry identifies the same repository and release notes.

Keep the unrelated existing changes to APPLICATION_SUPPORT_MATRIX.html,
APPLY_TRANSACTION.html and the October 29 14:01 handoff, plus the untracked
October 30 competitive-review documents, out of this commit. Do not discard them.
The prior Flea commit is included by ancestry; do not duplicate or rewrite it.

After updating, restart the Omarchy shell if it retains cached QML/version text.
Reapply the theme to update generated GTK stylesheets. Reopen an application only
when it retains cached styling/fonts or the plugin reports a reopen requirement.
