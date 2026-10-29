# Look & Feel handoff — 29 October 2026

Project: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`. The installed plugin links to this source. This handoff describes the local work as of this commit; consult Git for the exact commit and working-tree state. Do not push or publish without the user's authorization. See the previous handoff for earlier release and reboot history.

## Current work

- Added separate terminal opacity and blur controls, with independent undo. Ghostty's terminal background and the opaque coloured prompt were exercised live during the earlier work. Other terminals and all possible combinations should not be assumed live-verified from that result.
- Reworked the panel layout and undo placement, including fonts and boot artwork, and simplified the Applications tab. The manual audit now reports “Font support detected” or “Font support not detected”; the panel help and README explain its limitations and saved records. Clear Audits removes manual audit records, not applications or automatic support.
- The user expects real application and environment checks for interactive and visual changes, independent verification of results, focused scope, and prompt progress. Do not claim fixture or configuration checks demonstrate live behaviour. See `/home/si/AGENTS.md`.

## Outstanding: verify KiCad's actual menu font

The user explicitly asked to verify which font the running KiCad project manager's menus actually render. This remains **unverified**. GTK 3 and GTK 4 settings specify `SF Pro 12`, and the running KiCad executable uses wxWidgets/GTK 3, but those facts do not prove the widget's rendered font. The user's screenshot looks like SF Pro, which is also not proof.

A GTK Inspector shortcut attempt was sent to the Codex terminal instead of KiCad and disconnected the session; the user was informed. Do not repeat this: verify the active keyboard focus is KiCad immediately before sending any shortcut, and avoid disturbing the open project. AT-SPI exposed the KiCad menu tree, but the inspected menu nodes did not expose font attributes. The machine's ptrace policy prevents an ordinary debugger attach to the existing process; do not use sudo. Temporary investigation files under `/tmp` are ephemeral, not project evidence. If direct inspection cannot be performed, say so instead of inferring the rendered font.

## Audit caveat

The query `KiCAD` matched six installed launchers and was recorded as ambiguous/unsupported. The message “Font support not detected” can therefore be misleading: ambiguity is not proof that KiCad lacks support. A more specific launcher query matched the main application as GTK, but does not verify the rendered font. Ambiguous or unsupported saved audits can block font apply and automatic font repair; a more specific query does not remove an earlier record. Do not clear the user's audits without authorization. The user has not yet requested a change to distinguish ambiguity in the message.

## Verification and next steps

Previous live checks covered Ghostty opacity and prompt rendering and a supported Font Manager audit; a live unsupported-result check was not completed. Some UI states were checked in native QML fixtures, which are not a substitute for the live panel. Refer to project status and validation documents for their specific scope, and do not treat older release checks as validation of all subsequent changes. Resume with the KiCad font investigation if the user asks to continue, using a safe, targeted check and independent verification. Keep any further work local for review.
