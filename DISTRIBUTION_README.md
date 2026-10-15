# Native Quest Badges — Rust r12-small candidate

**DEVELOPMENT build; in-game acceptance pending.** Rise-style quest badges for
English HD MHGU 1.4.0 on Eden/Ryujinx. Requires Forge 1.5.0 with the matching
24-byte Hook ABI and the English HD Project.

## Badges

| Quest state | Badge |
| --- | --- |
| Key still needed for current progression | Red |
| Completed or obsolete key | Grey |
| Currently needed, offered and available urgent | Yellow |
| Completed, old or inactive urgent | Grey |
| Ordinary or unresolved quest | Hidden |

The 32×32 badge appears inside the quest row, in the request-mark slot. When a
quest also has a yellow request bubble, both marks appear, with the badge four
pixels left of the bubble. Long quest names automatically shrink to fit before
the badge; their full text is preserved.

This alternate uses the smaller top-of-atlas emblem with a black outline.
Its 32×32 size, position and state colours match the original r12.

## Installation

1. Close the game and extract the ZIP.
2. Put its `key-quest-markers-rs` folder in the emulator's MHGU mod location beside
   Forge and the English HD Project, then enable it. When updating, keep the old
   package outside the enabled mod directory and replace its folder as a whole.
3. Keep the HD Project enabled. Disable the original Key Quest Markers prefix
   plugin so `[KEY]` disappears from list/detail titles.

The runtime folder contains:

```text
romfs/nativeNX/plugins/key_quest_markers_rs.nro
```

Forge's Loaded Plugins list shows **Native Quest Badges r12-small**. This plugin has no
settings panel. Initialization and GUI failures are logged once at ERROR level.

To remove it, close the game and disable/remove its folder.

## Known limits

This development candidate needs an in-game trial on Eden and Ryujinx. Check long
names, both marks together, completion ribbons, selection, scrolling, confirmation
and reopening the menu. Only the English HD layout is supported.
