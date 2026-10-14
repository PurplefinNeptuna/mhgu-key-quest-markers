# Native Quest Badges — Rust r1 candidate

**DEVELOPMENT; inactive.** This candidate builds, but it does not activate its
native hook or show quest badges. Progression availability and the new GUI object
attachment still need verification. It is not ready for regular play or distribution.

## Intended behavior

English HD, MHGU 1.4.0, Nintendo Switch on Eden/Ryujinx, with a compatible
Forge 1.5.0 loader using its 24-byte Hook ABI.

| Quest state | Intended badge |
| --- | --- |
| Key still needed for current progression | Red |
| Completed or obsolete key | Grey |
| Currently needed, available urgent | Yellow |
| Completed, old or inactive urgent | Grey |
| Ordinary or unresolved quest | Hidden |

Badges are 24×24, left of the existing quest row with a four-pixel gap. They use
the existing HD lobby emblem. No separate emblem file, new texture atlas,
settings, config, overlay, counter or progression modification is included.

## Contents and future installation

The ZIP contains this guide and the `key-quest-markers-rs` runtime folder:

- `romfs/nativeNX/plugins/key_quest_markers_rs.nro`
- `romfs/nativeNX/eng/arc/village/common_eng.arc`

Do not install this inactive research candidate for regular play. After the
verification gates are resolved, a separately authorized trial can place the
named folder inside the emulator's MHGU mod directory, beside the compatible
Forge and English HD packages. Loader replacement is a separate operation.
The replacement common archive retains its selected English HD resources and
adds one hidden badge object. Other languages remain untouched.

Disable the original Key Quest Markers prefix plugin during that future trial.
`[KEY]` must disappear from list and detail titles; this plugin does not rewrite
quest names. Preserve the old package so it can be restored. Other mods changing
this same English common archive require a deliberate resource merge.

## Validation limits

Host fixtures, ARM argument forwarding, native import checks, archive readback and
all 15 row bindings are checked. They do not establish gameplay compatibility.
English HD acceptance on Eden and Ryujinx, Village/Hub/G-rank progression,
scrolling, selection, confirmation, reopening, quest return, clipping and colors
remain untested. The candidate stays inactive until the missing native semantics
and attachment contract are established.
