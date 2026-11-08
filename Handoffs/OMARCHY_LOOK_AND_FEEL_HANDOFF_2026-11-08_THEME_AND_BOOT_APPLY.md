# Look & Feel — Theme and boot artwork Apply failures

Date: 2026-11-08 (America/Phoenix)

## Scope and source

Repository: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`, branch `main`.
Remote: `https://github.com/conree/Omarchy_Look_and_Feel.git`.
The installed plugin at
`/home/si/.config/omarchy/plugins/si.omarchy-look-and-feel` links to this repository.
This handoff records the repair; repository source remains authoritative.

## First failure: Apply stopped at Theme

Look & Feel 0.3.5 displayed:

> Use an Omarchy build with the supported OMARCHY_THEME_HEADLESS branch; this build cannot safely apply themes.

The installed `/usr/share/omarchy/bin/omarchy-theme-set` already supported
headless generation. `theme_runtime.require_offline_support()` incorrectly
rejected it because the check required `run_parallel` immediately after the
non-headless guard. Newer Omarchy inserts a nested check of
`THEME_INTRO_TOKEN` that adds `omarchy-restart-hyprctl` to the visible command
list before `run_parallel`.

`theme_runtime.py` now accepts that specific optional prefix as well as the
original layout. It does not use an unrestricted search across arbitrary shell
blocks. The existing checks for headless activation remain intact.

`tests/check_theme_runtime.py` exercises both accepted layouts, commands moved
outside their guard, an unguarded command, comment-only activation and a missing
script. No packaged Omarchy files were edited.

## Second failure: Apply stopped at Boot unlock

After the compatibility fix, Apply advanced to Boot unlock. Read-only extraction
of both installed UKIs found that their embedded `omarchy.script` and `logo.png`
differed from the installed files in `/usr/share/plymouth/themes/omarchy`.
The other eight checked Plymouth assets matched. Kernel versions matched their
installed module directories and both Limine BLAKE2 checksum references were valid.

The boot helper verifies embedded assets against installed assets before changing
artwork. The mismatch blocks that preflight. The exact expanded UI error was not
captured; the asset mismatch was independently reproduced from both images.

The user ran the installed standard rebuild command in their own terminal:

```bash
sudo limine-mkinitcpio
```

It rebuilt and published:

- `/boot/EFI/Linux/omarchy_linux.efi` — `7.2.11-arch1-1`
- `/boot/EFI/Linux/omarchy_linux-omarchy.efi` — `7.2.15-1-omarchy`

The command also updated `/boot/limine.conf`. This command invokes configured
boot hooks; it is a targeted repair, not an instruction to rebuild every user's
boot images. The agent did not run sudo. No boot-helper safety checks were removed
or weakened, and no boot-helper code changed.

## Verification and acceptance

- `python -B tests/check_theme_runtime.py` passed.
- `python -B tests/check_requirements.py` passed, including expected failure cases.
- The installed theme capability preflight passed after the compatibility edit.
- The real installed theme script generated a Catppuccin theme in a temporary
  home with headless and skip-background enabled. Generated theme files existed,
  the background link was preserved, and execution tracing showed no runtime
  retint hooks, app restarts, browser-policy command or privileged command.
- Independent review checked the actual shell script and compatibility diff,
  including rejection of unsupported guard layouts.
- After the user's rebuild, fresh extraction verified all 10 expected Plymouth
  assets in each UKI and both Limine checksums. A separate reviewer independently
  repeated those checks.
- The user retried Apply and confirmed: "It worked."

Full desktop Apply is therefore user-confirmed. Reboot appearance was not tested.
No broad application appearance regression sweep is claimed.

## Publication scope

The user authorized writing this handoff, committing and pushing the fix.
The intended commit contains only this handoff, `theme_runtime.py`, and
`tests/check_theme_runtime.py`. Pre-existing unrelated documentation and handoff
changes stay outside this commit.

The compatibility fix is appropriate for users of the newer Omarchy script.
A 0.3.6 patch release was recommended, but this task does not create a release,
tag, or version bump; the manifest remains at 0.3.5. The boot rebuild was a local
repair and is not distributed as automatic behavior.
