# Look & Feel 0.3.4 — GTK menu highlights and Flea integration

GTK menu-item hover now uses the selected palette's selection color and a
readable foreground. This fixes Brave bookmark menus retaining a blue base-theme
highlight while the rest of the interface follows Dracula Pro Van Helsing.
Brave must use **Use GTK** for this integration. The plugin generates the rule
for both managed GTK stylesheets, so later theme applications retain the fix.

This release also includes the previously local generic-font and Flea opacity
work. Generic sans-serif and monospace preferences follow the selected system
and terminal fonts. Flea keeps its fixed-width layout and uses the selected
terminal font; it does not receive a proportional-font override. Appearance now
has a separate **Flea opacity** picker, its own Undo, and automatic repair.
Opacity changes affect the background while text and icons remain opaque.

## Setup and updating

Generic font preferences require the one-time Fontconfig loader installation
shown in the README's **Generic font preferences** section. Later font changes
need no administrator access. Reopen Flea to load cached font changes. A Flea
window started at 100% opacity may also need reopening after lowering opacity;
the plugin reports that condition.

Update the plugin and restart the Omarchy shell if its panel remains cached at
an older version. Reapply the desired theme to regenerate GTK rules. If Brave
still shows the previous highlight, reopen it. A managed BrowserThemeColor
policy can prevent selecting GTK; this release does not remove system policies.

## Verification and limits

The owner confirmed the pink/purple bookmark highlight in running Brave on
November 3. Independent review checked the generator and matching active GTK
stylesheets. The portable-appearance regression passed after the rule change.

The November 2 Flea work was previously checked in the live panel and real Flea
windows at 0%, 75% and 100%, including opaque-start reopening behavior. Native
Fontconfig resolution and a reopened Flea confirmed the selected monospace font.
Those observations are retained as earlier evidence, not a new live sweep.
Focused regression checks and exact limits are recorded in RELEASE_VALIDATION.md.
No universal browser, GTK 4, Flea-version or desktop-environment claim is made.
