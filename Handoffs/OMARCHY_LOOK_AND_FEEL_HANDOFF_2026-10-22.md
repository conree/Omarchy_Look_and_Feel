# Omarchy Look & Feel handoff — 2026-10-22

## Project and repository

- Project: `/home/si/Projects/Omarchy_Plugins/Look_and_Feel`
- Repository: `https://github.com/conree/Omarchy_Look_and_Feel.git`
- Branch: `main`
- Local commit: `4bfcce8` — `Build live Look and Feel selection panel`
- Push status: **not pushed**. `git push origin main` failed because this environment could not resolve `github.com`.
- Handoff location: `/home/si/Projects/Omarchy_Plugins/Handoffs/`

## Current implementation

- The panel has two-column controls for system and terminal typography, theme mode, Light and Dark themes, boot unlock design, icon theme, and background.
- Icon Theme is now grouped with the theme and unlock dropdowns. The Mode selector spans the theme section width; the Background selector spans the desktop appearance section width.
- Theme and unlock catalogs are discovered from live Omarchy system and user theme directories. Fonts use fontconfig, icon themes use active XDG paths, and wallpapers use live Omarchy and user sources.
- Selecting a boot unlock design opens its preview. Alucard and Van Helsing unlock artwork is included under `assets/unlocks/`.
- Automatic mode has no schedule controls or stored schedule preferences. It uses coordinates from `~/.local/state/omarchy/settings/weather.json` and the system time zone from `/etc/localtime`. Current inventory output resolves Tucson at `32.22174, -110.92648` and `America/Phoenix`.
- The settings contract is version 2. It keeps theme mode and selected themes, typography, unlock, background, and icons; it does not store location, time zone, or sunrise/sunset offsets.
- The controller and solar calculator remain read-only/support code. No persistent scheduler or application Apply adapter is enabled; the panel selections are not saved or applied to desktop settings.
- Font review records are in `font-reviews.json`. The transaction core still has an empty application-target allowlist.

## Verification in this session

- Reviewed the staged panel layout and the version 2 schema/example diff before committing.
- Confirmed the schema and example agree, and that no schedule or offset preference remains in the settings contract.
- Ran the read-only controller inventory and confirmed it reports the system weather coordinates and time zone above.
- `git diff --check` passed for the changed files.
- No tests or live GUI check were run.

## Next work

1. Push commit `4bfcce8` when GitHub DNS/network access is available.
2. Review the panel in the live bar after loading the committed source and confirm the dropdown grouping and widths visually.
3. Design and validate a reversible first application adapter in a disposable home before enabling any Apply path.
4. Connect automatic theme transitions to Omarchy weather settings and the system time zone only after the theme adapter is safe; handle unavailable weather coordinates or timezone as an explicit precondition failure.

The working tree was clean immediately after the local commit. No user system configuration was changed by this commit.
