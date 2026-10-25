# Current project handoff

Read the complete current handoff:
[/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-10-25.md](/home/si/Projects/Omarchy_Plugins/Look_and_Feel/Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-10-25.md).

Current status: tested development candidate. Icons now apply and undo;
Fontconfig override repair, typed scaling and dependency/recovery safeguards
are implemented. Malformed Qt font validation prevents the restart-related
invisible-bar failure; unsafe font Undo/recovery is refused. The final malformed-
font VM cold-start test and independent review passed. The VM size matrix
passes within its recorded scope.
The EE Calc-inspired redesign is implemented: Appearance/Fonts/Applications tabs,
installed-asset previews, fixed Apply footer, concise results, keyboard scrolling
and preserved drafts. Its final light/dark VM run has 30 captures and exact Undo;
the detailed handoff separates that archive from earlier backend/size evidence.
Boot unlock remains blocked and preview-only. Host visual acceptance after
fresh login is outstanding; no universal app or hardware claim is made.

Source: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`.
Publication: `https://github.com/conree/Omarchy_Look_and_Feel`, branch `main`.
Use `PROJECT_STATUS.md`, `RELEASE_VALIDATION.md` and `SOURCE_OF_TRUTH.md` for
current behavior and evidence, rather than older handoff claims.

Never enumerate or access another installed OS, including with `lsblk`.
Never run host sudo. Preserve boot hardening and browser security policies.
