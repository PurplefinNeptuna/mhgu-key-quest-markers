# Native Quest Badges — Rust r6 candidate

**DEVELOPMENT build; in-game acceptance pending.** Adds Rise-style native badges to English HD MHGU
1.4.0 on Eden/Ryujinx. Requires Forge 1.5.0 with the matching 24-byte Hook ABI.

## Badges

| Quest state | Badge |
| --- | --- |
| Key still needed for current progression | Red |
| Completed or obsolete key | Grey |
| Currently needed, offered and available urgent | Yellow |
| Completed, old or inactive urgent | Grey |
| Ordinary or unresolved quest | Hidden |

The 24×24 badges sit left of the existing rows with a four-pixel gap. New native
GUI children reuse the already-loaded HD lobby emblem. The package replaces no
ARC or atlas and contains no separate image, overlay, settings, counter or
progression changes. The game draws the badges and releases them with the menu.

## Installation

Close the game first. Back up and disable/remove the old Rust badge candidate
folder as a whole; do not copy r6 over it and leave its old `common_eng.arc` behind.
Keep that backup outside the emulator's enabled mod directory.

Extract the ZIP and put its `key-quest-markers-rs` folder in the emulator's MHGU mod
location beside Forge and the English HD Project, then enable it. The runtime
folder contains only:

```text
romfs/nativeNX/plugins/key_quest_markers_rs.nro
```

Keep the HD Project enabled. Disable the original Key Quest Markers prefix plugin
so `[KEY]` disappears from list/detail titles. Only one Rust badge candidate should
be enabled. The ZIP does not include or replace Forge; confirm Ryujinx's loader is
also 1.5.0 before testing.

Forge's Loaded Plugins list should show **Native Quest Badges r6**. There is no
Plugin UI settings panel. Earlier forge-rs entries omitted the name, so a loaded
plugin could be missing from that list. This candidate reports actual initialization
or GUI failures once at ERROR level, without requiring a loader config change.

To remove it, close the game and disable/remove its folder. Restore previous
packages from your backups if desired. No saves or game archives need changing.

r6 corrects r5’s startup hook check, which restored valid hooks before the menu
could run. It retains the native constructor and GUI owner corrections.

## Validation limits

Host policy/rollback checks, ARM argument forwarding and named registration,
native imports, runtime GUI insertion, allocation failure cleanup, unchanged
lookup arrays, and native draw-list/destructor execution pass automated fixtures.
These checks do not establish actual in-game pixels or gameplay acceptance.

Manual English HD acceptance remains pending on Eden and Ryujinx: Village/Hub/G,
scrolling, selection, confirmation, reopening, quest return and progression
advancement. Check badge placement, clipping, size and colors. Keep rollback
packages available while testing this development build.
