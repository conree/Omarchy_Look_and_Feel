# Marketplace security review follow-up — 2026-11-14

## Scope and publication

The owner authorized committing and pushing this focused fix to `origin/main`
and writing this project handoff. The source revision is the commit containing
this document; identify it with:

```sh
git log -1 --format=%H -- Handoffs/OMARCHY_LOOK_AND_FEEL_HANDOFF_2026-11-14_SECURITY_REVIEW.md
```

Repository: <https://github.com/conree/Omarchy_Look_and_Feel>.
Reviewed baseline: `4f0fb67bcac8b5470a9719086a0c595f3dda5235`.
Review: <https://github.com/omacom/omarchy-plugin-marketplace/issues/14718#issuecomment-6858330159>.
This update creates no version tag, GitHub release, Marketplace approval or
issue comment. Existing unrelated working-tree changes are excluded.

## Changes

- `BarWidget.qml` creates the panel only after an explicit open request.
- `Panel.qml` replaces the native editable Applications search with plain
  display text and keyboard handling, avoiding clipboard subscriptions even
  after the panel has been opened. It supports 256 typed characters,
  Backspace/Delete, arrows, Home/End and Control+A. Clipboard paste and
  input-method composition are unavailable; README documents this limitation.
- `BoundedProcess.qml`, registered in `qmldir`, handles all plugin QML command
  collectors, including inventory, reconciliation, Apply, Undo and audits.
  Ordinary commands have a 120-second total deadline and an 8 MiB combined
  stdout/stderr budget. Boot artwork retains its separate 2,430-second outer
  budget around the existing 2,400-second authenticated helper window.
- A two-second startup watchdog completes failed native starts even when
  Quickshell emits no exit/stream completion. Each invocation has a fresh native
  process and identity guards, preventing stale events from completing a retry.
- `process_supervisor.py` uses a relay and guardian with Linux parent-death
  signals. It kills the ordinary controller process group on exit, timeout,
  overflow, cancellation or owner destruction. Partial JSON is discarded on
  resource failure. Cancellation uses a dedicated exception because selectors
  swallows `InterruptedError`; child termination signals are explicitly unmasked.

## Verification

The following checks passed:

```sh
python3 -B tests/check_panel_keyboard.py
python3 -B tests/check_process_limits.py
git diff --check
```

The native Qt checks cover production search editing, the 256-character bound,
focus traversal, no native TextInput/TextEdit in the instantiated styled-control
tree, and no clipboard reads on a clipboard change or Control+V. The process
checks cover total runtime, both output streams, continuing chunks, inherited
pipes/grandchildren, immediate retries, missing interpreter/command, and native
Quickshell Loader destruction. Independent execution also checked abrupt owner
death and successful retry after FailedToStart; source review checked busy-state
completion and stopping a failed Apply sequence.

The full production panel opened and loaded its catalog on Wayland. An isolated
nested Hyprland session then exercised a real hostile clipboard owner under
Qt 6.12. No Paste was issued. Native protocol logs confirmed delivery of non-null
text offers to the shell in every case.

| Actual code and panel state | Clipboard text requests | GUI heartbeats during five-second offer |
| --- | ---: | ---: |
| Reviewed baseline, closed | 1 | 0 — stalled |
| Fixed, never opened | 0 | 50 — responsive |
| Fixed, open | 0 | 50 — responsive |
| Fixed, opened then closed | 0 | 50 — responsive |

The slow owner offered 4 KiB chunks at 50 ms intervals, keeping data arriving
within the native reader's one-second wait throughout the observation window.
The reclosed case offered a faster burst
source; fixed code never requested its payload. The baseline source files were
checked byte-for-byte against the reviewed commit. Independent review checked
the test source, raw Wayland delivery/receive events, actual open-layer lifetime
and heartbeat results. The isolated compositor and test clients were stopped.

Reproduction sources are `tests/check_wayland_clipboard.py` and
`tests/hostile_clipboard_owner.c`. The opt-in test requires a separate compositor
with temporary HOME/config/runtime; it rejects runtime paths outside `/tmp` and
socket symlinks. Invoke it using that compositor's runtime and display:

```sh
python3 -B tests/check_wayland_clipboard.py --runtime-dir /tmp/isolated-runtime --display wayland-1
```

## Limits and next action

This demonstrates removal of the reported clipboard-read exposure; it does not
claim an OOM test. Process cleanup covers ordinary members of the controller's
process group, not arbitrary processes that detach into another session or
cross a privilege boundary. Privileged boot operations were not repeated;
their existing protected staging, verification and recovery protocol remains.

The remaining Marketplace step is maintainer review of the pushed revision.
No approval is implied by passing local checks. Public follow-up should contain
the source commit, changes, software versions and aggregate results only. Raw
logs, screenshots, environment variables, personal paths and unrelated local
documents remain excluded; the hostile payload was generated `x` characters
and the real desktop clipboard was not accessed.
