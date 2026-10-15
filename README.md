# Key Quest Markers

Rise-style quest badges for Monster Hunter Generations Ultimate 1.4.0 on Switch
emulators. Requires [Fexty's Forge 1.5.1](https://github.com/Fexty12573/forge/releases/tag/v1.5.1).

## Badges

| Quest state | Badge |
| --- | --- |
| Key still needed for current progression | Green |
| Completed or obsolete key | Grey |
| Currently needed and available urgent | Red |
| Completed, old or inactive urgent | Grey |
| Ordinary quest | No badge |

The badge appears in the quest row's request bubble slot. When a quest also
has a yellow request bubble, the badge appears beside it. Long quest names
automatically shrink to fit before the badge.

## Installation

1. Close the game and extract the ZIP.
2. Copy the `key-quest-markers` folder into your emulator's MHGU mod directory,
   beside Forge, then enable it. Replace the whole
   folder when updating.

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

Press **Save & apply** to use and save your chosen colours. They take effect
without restarting or reopening the quest counter. **Reset defaults** fills in
the default colours, which match the game's UI. Press Save & apply afterward
to apply them. Updating the mod keeps your saved colours, so use these two
buttons if you want to switch to the current defaults.

Colours are saved in `key_quest_markers.ini` in MHGU's save folder:

```ini
[Colors]
key = 006305
urgent = A30000
completed = 808080
```

All colours stay opaque. If saving fails, the previous colours stay in use and
your pending choices remain in the panel. Load a player save and try saving
again. Missing or invalid configuration uses defaults.

## Compatibility

Works with the base game and the MHGU HD Project. HD is optional.

If the plugin reports an incompatible loader or resource, check that MHGU is
version 1.4.0 and that you are using Forge 1.5.1.
