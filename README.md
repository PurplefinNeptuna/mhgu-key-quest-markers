# Key Quest Markers

Rise-style quest badges for Monster Hunter Generations Ultimate 1.4.0 on Switch
emulators. Requires a compatible Forge 1.5.1 loader and the English MHGU HD Project.

## Badges

| Quest state | Badge |
| --- | --- |
| Key still needed for current progression | Gathering green |
| Completed or obsolete key | Grey |
| Currently needed and available urgent | Objective red |
| Completed, old or inactive urgent | Grey |
| Ordinary quest | No badge |

The 32×32 badge appears in the quest row's request-mark slot. When a quest also
has a yellow request bubble, the badge appears four pixels to its left. Long
quest names automatically shrink to fit before the badge.

## Installation

1. Close the game and extract the ZIP.
2. Copy the `key-quest-markers` folder into your emulator's MHGU mod directory,
   beside Forge and the English HD Project, then enable it. Replace the whole
   folder when updating.
3. Keep the English HD Project enabled. Disable the original Key Quest Markers
   prefix plugin to remove `[KEY]` from quest titles.

Forge's Loaded Plugins list shows **Key Quest Markers r17**. The badges work
automatically when you open the quest counter.

To remove the mod, close the game and disable or remove its folder.

## Colour settings

Open Forge's **Plugin UI → Key Quest Markers**. Click a colour swatch to open
its picker, or enter a hexadecimal RGB value.

| Setting | Default | Meaning |
| --- | --- | --- |
| Key | `006305` | Currently needed key quests |
| Urgent | `A30000` | Currently needed and available urgent quests |
| Completed | `808080` | Completed, obsolete or inactive key/urgent quests |

Edits stay pending until you press **Save & apply**. Saved colours take effect
without restarting or reopening the quest counter. **Reset defaults** fills in
the default colours; press Save & apply to use and retain them. Updates preserve
existing saved choices; use Reset defaults and Save & apply to adopt the new
game-matched defaults.

Colours are saved in `key_quest_markers.ini` in MHGU's save folder:

```ini
[Colors]
key = 006305
urgent = A30000
completed = 808080
```

All colours stay opaque. If saving fails, load a player save and retry; the
previously applied colours remain in use and your pending choices remain in the
panel. Missing or invalid configuration uses defaults.

## Compatibility

Use the English HD counter layout. Other languages and replacement counter
layouts are unsupported. If the plugin reports an incompatible loader or resource,
check that MHGU is version 1.4.0 and that Forge and the English HD Project match
these requirements.
