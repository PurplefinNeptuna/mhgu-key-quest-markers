# Key Quest Markers

Adds Rise-style badges to key and urgent quests, with colors that show
whether you still need them for progression. Quests that give Hunter Arts or
Felyne ingredients, and quests that unlock other quests, get a badge too.

## Requirements

- MHGU 1.4.0 for Nintendo Switch.
- [Fexty's Forge 1.5.1](https://github.com/Fexty12573/forge/releases/tag/v1.5.1).
- Optional: Purple-lib r17 or later, to change the badge settings from the game's own Options menu.

## Installation

1. Close the emulator.
2. Extract `key-quest-markers-r32.zip`.
3. Copy the whole `key-quest-markers` folder into your emulator's MHGU mod directory:
   - Eden: `~/.local/share/eden/load/0100770008DD8000/`
   - Ryujinx: `mods/contents/0100770008dd8000/` inside its data directory.
4. Enable `key-quest-markers` and launch MHGU.

## Usage

Badges appear automatically when you open the quest counter.

| Quest | Badge |
| --- | --- |
| Current urgent quest | Red |
| Key quest you still need to clear | Green |
| Quest that gives Hunter Arts or ingredients, or leads to one that does | Orange |
| Quest that unlocks another quest when you clear it | Blue |
| A cleared quest from the rows above, or an urgent or key quest that is no longer current | Gray |
| Any other quest | No badge |

Each quest shows one badge. When a quest fits more than one row, the higher
row wins. An urgent or key quest stays red or green even if it also gives a
reward or unlocks a quest, and orange wins over blue.

The **Finished quests** setting decides how finished quests show. **Gray**, the
default, shows them gray. **Colored** leaves their color unchanged. **Hidden**
removes their badge.

Some quests aren't key quests in the game's own list, but the game still needs
them before it offers the next urgent quest. These show green too. In the
Village, that's the 5★ Astalos, Gammoth and Mizutsune hunts for the Kokoto,
Pokke and Yukumo chiefs, plus the earlier requests in each village that lead to
them. They turn green once 5★ is your highest Village rank, and stay green until
you clear them.

A quest is orange when clearing it gets you new Hunter Arts or Felyne kitchen
ingredients. For some of these rewards you also have to talk to someone after
the quest. The quests you need to clear before a reward quest shows up are
orange too.

A quest is blue when clearing it unlocks a different quest, straight away or
after you talk to someone. Some quests unlock only after several others are
cleared, so a blue quest may be one of a few you need.

The badge appears in the quest row's request bubble slot. When a quest also
has a yellow request bubble, the badge appears beside it. Long quest names
shrink to fit before the badge.

### Settings

Open **Plugin UI > Key Quest Markers** in Forge's overlay. Click a color
swatch to open its picker, or enter a hexadecimal RGB value.

Forge opens its overlay with the Insert key on a keyboard; `[menu] key` in Forge's
`config.ini` changes the key. On Ryujinx, turn on Direct Keyboard Access in the input
settings first. On MHGU Recomp, press Insert or choose **Open the Forge menu** on the
Mods tab of its settings menu (F1, or Plus and Minus on a controller).

| Setting | Default | Effect |
| --- | --- | --- |
| Key | `006305` | Key quest badge color. |
| Urgent | `A30000` | Urgent quest badge color. |
| Completed | `808080` | Badge color for completed or inactive quests. |
| Unlocks a quest | `0032C2` | Badge color for quests that unlock another quest. |
| Gives a reward | `FF7F00` | Badge color for quests that give Hunter Arts or ingredients, and the quests that lead to them. |
| Finished quests | Gray | Colored, Gray or Hidden: how finished quests show. |

Changes in the panel, including Finished quests, stay pending until
you press **Save & apply**. They then take effect without restarting or
reopening the quest counter. **Reset defaults** fills in the default colors and
sets Finished quests back to Gray. Press Save & apply afterward to use and save them.

Updates keep your saved colors. To use the current defaults, press Reset
defaults followed by Save & apply. All colors stay opaque.

### In the game's Options menu

With Purple-lib installed, **Finished quests** is also
under **Options > Mod Options** in the start menu: choose "Key Quest Markers" from the
list of mods (with Purple-lib r19 or older, press L or R until its page shows). A change
takes effect as soon as you make it, and closing the window saves it to the same INI.
The page is in English in every language.

### INI settings

Settings are saved in `key_quest_markers.ini` in MHGU's save folder:

```ini
[Colors]
key = 006305
urgent = A30000
completed = 808080
unlocks = 0032C2
reward = FF7F00

[Badges]
finished_quests = gray
```

`finished_quests` is `colored`, `gray` or `hidden`.

A file saved by an older version may lack the `unlocks` or `reward` line, or the
`[Badges]` section. It keeps its colors, uses the default blue or orange, and
shows gray badges. Missing or invalid configuration uses defaults. While the game is saving, or
before a player save is loaded, the mod waits and saves by itself as soon as it
can. If saving fails, the previous colors stay in use and your pending choices
remain in the panel.

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

The orange and blue badges use the unlock rules and rewards of the base game, its
updates and DLC. Quests that another mod adds, such as MHGU Definitive Edition,
get no orange or blue badge, and the badges don't follow another mod's changes to
unlock rules.

## License

Copyright (c) 2026 PurplefinNeptuna. Key Quest Markers is licensed under the GNU GPL, version 3 or
later. The source code and the license text are at
https://github.com/PurplefinNeptuna/mhgu-key-quest-markers.
