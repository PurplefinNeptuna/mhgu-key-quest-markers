# Key Quest Markers r27: testing

r27 adds the Grey badges setting: Coloured, Grey or Hidden. It also carries r25 (the game's save
lock held while it saves its settings) and r24 (the quests The Scorching Blade needs are green at
Village 5★). Purple-lib r17 or later is optional and only needed for step 5.

## Steps

1. Open the quest counter. Badges show as in r23, plus more blue and orange ones: r24 reads the
   game's talk conditions in full, so more quests count as unlocking or leading to a reward.
2. Open **Plugin UI > Key Quest Markers** in Forge's overlay, choose **Hidden** under Grey
   badges and press **Save & apply**. At the quest counter, the grey badges are gone and the
   other colours stay. Note whether rows already on screen change at once, or only after you
   scroll or turn the page.
3. Restart the game. Grey badges stay hidden, and `key_quest_markers.ini` ends with `[Badges]`
   and `grey_badges = hidden`.
4. Choose **Coloured** and press Save & apply. Cleared quests show their own colour again: red
   for urgent quests, green for key quests, orange or blue for the rest. Key and urgent quests
   that are no longer current but were never cleared stay grey. Choose **Grey** to go back.
5. With Purple-lib, open **Options > Mod Options** and choose "Key Quest Markers". Its one row,
   "Grey badges", steps through Coloured, Grey and Hidden, and the help bar says what Coloured
   and Hidden do. A change applies at once; close the window, restart, and the choice is kept.
6. With a save at Village 5★ that has not been offered The Scorching Blade yet: The Thunderclaw
   Wyvern, The Unwavering Colossus and The Entrancing Water Dancer are green until cleared, and
   so are the earlier chief requests that lead to them, on their own star pages. At other Village
   ranks these quests are blue, or grey once cleared.

## Log lines

Forge shows INFO and WARN lines only when its log level allows them. With an ERROR-only filter,
only the `can't find` and `hidden` lines and a failed start appear.

| Line | Meaning |
| --- | --- |
| `Key Quest Markers r26 loaded` | Started |
| `Key Quest Markers: setting added to Purple-lib Mod Options` | Purple-lib called the mod and took its page |
| `Key Quest Markers: Purple-lib API version N is older than 3; Mod Options not added` | An older Purple-lib called the mod: install r17 or later |
| `Key Quest Markers: Purple-lib refused the Mod Options page` | Send the log |
| `Key Quest Markers waited for the game to finish saving before saving its settings` | A save met a game save and waited, then went ahead |
| `Key Quest Markers can't find the game's save lock, so it won't save its settings yet` | Nothing is saved: send the log |
| `Key Quest Markers: ` followed by a message | A failed start (ERROR) or a failed save or load (WARN); the message says why |
| `Key Quest Markers hidden: …` | Badges are off for a reason the line names: send the log |

Without Purple-lib, no Purple-lib line appears; that is expected.
