# Key Quest Markers

Adds Rise-style badges to key and urgent quests, with colours that show
whether you still need them for progression. Quests that give Hunter Arts or
Felyne ingredients, and quests that unlock other quests, get a badge too.

## Requirements

- MHGU 1.4.0 for Nintendo Switch.
- [Fexty's Forge 1.5.1](https://github.com/Fexty12573/forge/releases/tag/v1.5.1).

## Installation

1. Close the emulator.
2. Extract `key-quest-markers-r22.zip`.
3. Copy the whole `key-quest-markers` folder into your emulator's MHGU mod directory:
   - Eden: `~/.local/share/eden/load/0100770008DD8000/`
   - Ryujinx: `mods/contents/0100770008dd8000/` inside its data directory.
4. Enable `key-quest-markers` and launch MHGU.

## Usage

Badges appear automatically when you open the quest counter.

| Quest state | Badge |
| --- | --- |
| Key quest you still need to clear | Green |
| Current urgent quest | Red |
| Other quest that gives Hunter Arts or ingredients, or leads to one that does | Gold |
| Other quest that unlocks another quest when you clear it | Blue |
| Completed or inactive key or urgent quest, or a cleared gold or blue quest | Grey |
| Other quest | No badge |

The badge appears in the quest row's request bubble slot. When a quest also
has a yellow request bubble, the badge appears beside it. Long quest names
shrink to fit before the badge.

A quest is blue when clearing it unlocks a different quest, either straight
away or after you talk to someone. Some unlocks need several
quests cleared, so a blue quest may be one of a few. Key and urgent quests keep
their green or red badge even when they also unlock something.

A quest is gold when clearing it gets you new Hunter Arts or Felyne kitchen
ingredients. You get the reward from someone you talk to after clearing the
quest. Quests you have to clear before a reward quest appears are gold too, so
you can follow the chain. Gold replaces blue on the same quest.

### Settings

Open **Plugin UI > Key Quest Markers** in Forge's overlay. Click a colour
swatch to open its picker, or enter a hexadecimal RGB value.

Forge opens its overlay with the Insert key on a keyboard; `[menu] key` in Forge's
`config.ini` changes the key. On Ryujinx, turn on Direct Keyboard Access in the input
settings first. On MHGU Recomp, press Insert or choose **Open the Forge menu** on the
Mods tab of its settings menu (F1, or Plus and Minus on a controller).

| Setting | Default | Effect |
| --- | --- | --- |
| Key | `006305` | Key quest badge colour. |
| Urgent | `A30000` | Urgent quest badge colour. |
| Completed | `808080` | Badge colour for completed or inactive quests. |
| Unlocks a quest | `0032C2` | Badge colour for quests that unlock another quest. |
| Gives a reward | `9B6500` | Badge colour for quests that give Hunter Arts or ingredients, and the quests that lead to them. |

Edits stay pending until you press **Save & apply**. The colours then take
effect without restarting or reopening the quest counter. **Reset defaults**
fills in the default colours. Press Save & apply afterward to use and save them.

Updates keep your saved colours. To use the current defaults, press Reset
defaults followed by Save & apply. All colours stay opaque.

### INI settings

Colours are saved in `key_quest_markers.ini` in MHGU's save folder:

```ini
[Colors]
key = 006305
urgent = A30000
completed = 808080
unlocks = 0032C2
reward = 9B6500
```

A file saved by an older version may lack the `unlocks` or `reward` line; it
keeps its colours and uses the default blue or gold. Missing or invalid configuration uses defaults. If saving fails, the previous
colours stay in use and your pending choices remain in the panel. Load a player
save and try saving again.

## Update and removal

Close the emulator before updating or removing the mod. To update, replace
its `key-quest-markers` folder with the one from the new ZIP. To remove it,
disable the package or delete its folder from the emulator's mod directory.

## Compatibility and known issues

Works with the base game and the MHGU HD Project. HD is optional.

Native Switch compatibility is unconfirmed.

If the plugin reports an incompatible loader or resource, check that MHGU is
version 1.4.0 and that you are using Forge 1.5.1.

It can load alongside plugins that hook the same game functions.

The gold and blue badges know the unlock rules and rewards of the base game, its
updates and DLC. Quests that another mod adds, such as MHGU Definitive Edition,
get no gold or blue badge, and changes
a mod makes to unlock rules are not followed.
