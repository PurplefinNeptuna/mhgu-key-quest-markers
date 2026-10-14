# Native Quest Badges — Rust r2 candidate

**Active DEVELOPMENT build.** Adds Rise-style quest badges to English HD MHGU
1.4.0 on Nintendo Switch emulators Eden/Ryujinx. Requires a compatible Forge
1.5.0 loader with its 24-byte Hook ABI; older loaders are rejected.

## Badges

| Quest state | Badge |
| --- | --- |
| Key still needed for current progression | Red |
| Completed or obsolete key | Grey |
| Currently needed, offered and available urgent | Yellow |
| Completed, old or inactive urgent | Grey |
| Ordinary or unresolved quest | Hidden |

Badges are 24×24, left of the existing quest row with a four-pixel gap. They reuse
the HD lobby emblem directly. No separate emblem file, replacement atlas,
settings, config, overlay, header counter or progression changes are included.

## Installation

The ZIP contains this guide and the `key-quest-markers-rs` runtime folder:

- `romfs/nativeNX/plugins/key_quest_markers_rs.nro`
- `romfs/nativeNX/eng/arc/village/common_eng.arc`

Close the game before changing packages. Back up an existing candidate and place
the named folder in the emulator's MHGU mod directory beside the compatible
Forge and English HD packages, then enable it in the emulator's mod controls.
Replace the old r1 candidate if present; it intentionally did not display badges.
This ZIP does not include or upgrade Forge. On Ryujinx, confirm the loader version
rather than assuming a compatible loader is installed.

Disable the original Key Quest Markers prefix plugin during use. `[KEY]` should
disappear from list and detail titles; this plugin does not rewrite quest names.
Keep the original package so it can be restored.

The replacement English common archive retains its selected HD resources and
adds the badge object to the native row animation. Other languages are untouched.
Another mod replacing this same archive needs a deliberate resource merge; file
ordering alone cannot combine changes. To remove this candidate, close the game,
disable/remove its folder and restore your previous packages as desired.

## Validation limits

Host fixtures, compiled ARM callbacks, seven-argument forwarding, native imports,
archive readback and all 15 row bindings pass automated checks. The active callback
fixtures reach the native visibility/color setters for red, grey and yellow states.
These checks do not render the game UI or establish gameplay compatibility.

English HD trials on Eden and Ryujinx remain pending: Village/Hub/G-rank,
scrolling, selection, confirmation, reopening, quest return and progression
advancement. Check badge size, clipping and colors. If badges are hidden by a
runtime validation failure, Forge logs a deduplicated reason. This is a development
candidate; keep rollback packages available during testing.
