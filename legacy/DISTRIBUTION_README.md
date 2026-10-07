# Key Quest Markers r2

Adds `[KEY] ` before progression key quest titles in Monster Hunter Generations
Ultimate 1.4.0 for Nintendo Switch, including completed keys. The prefix appears
in native quest lists and details. Urgent and training quests receive no prefix.
Completion marks, sorting, unlock conditions and language selection keep their
normal behavior.

## Requirements

Forge is required and supplied separately. Use MHGU 1.4.0 on Eden or Ryujinx.
Earlier gameplay confirmation covered Eden Village 1/2 star and Hub 1 star,
and all ranks on the tested Ryujinx installation. r2 has not had a separate
gameplay test. Higher ranks on Eden, every language/screen combination and
native Switch hardware remain unverified.

## Install or update

1. Close the emulator.
2. Extract `key-quest-markers-r2.zip` and copy its `key-quest-markers` folder
   into the emulator's MHGU mod directory, alongside Forge. For Eden, use
   `~/.local/share/eden/load/0100770008DD8000/`; for Ryujinx-based emulators,
   use `mods/contents/0100770008dd8000/` inside your emulator's data directory.
3. When updating, back up the old package outside that directory and replace it.
   Keep only one copy of the plugin installed.
4. Enable the package and restart the game.

The plugin works automatically and has no settings panel. It does not change
quest or save data and needs no internet connection.

To remove it, close the emulator, disable or remove `key-quest-markers`,
then restart the game.

## Troubleshooting

If markers do not appear, check that MHGU is version 1.4.0, Forge and the package
are enabled, and no other mod patches the same quest-name function. Unsupported
game builds or conflicting patches leave the plugin inactive. Unrecognized
quests or titles it cannot safely mark keep their original names.

Always restart after changing this package. Include your emulator/game version,
affected quest title, other enabled mods and a fresh emulator log when reporting
a problem.

## Sharing

Keep `NOTICES.txt` with the ZIP when sharing it.
