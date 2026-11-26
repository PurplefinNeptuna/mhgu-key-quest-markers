# Key Quest Markers r32: testing

r32 shows more quests orange. Many Hunter Arts unlock when you clear one particular quest, and r31
only knew the few that a talk row names. r32 reads the quest each Hunter Art checks for in the game
itself, so quests such as Hub 3★ Wyvern Sand Runners now count. The rest is as in r31: the Finished
quests setting (Colored, Gray or Hidden), the game's save lock while it saves its settings, and
green for the quests The Scorching Blade needs at Village 5★. Purple-lib r17 or later is optional
and only needed for step 5.

## Steps

1. Open the Hub quest counter on the 3★ page. Wyvern Sand Runners is orange, or gray if you have
   cleared it. Expect more orange and fewer blue badges than in r31, because quests
   that lead to one of these Hunter Arts quests are orange too.
2. Open **Plugin UI > Key Quest Markers** in Forge's overlay, choose **Hidden** under Finished
   quests and press **Save & apply**. At the quest counter, finished quests have no badge and the
   other colors stay. Note whether rows already on screen change at once, or only after you
   scroll or turn the page.
3. Restart the game. Finished quests stay without a badge, and `key_quest_markers.ini` ends with `[Badges]`
   and `finished_quests = hidden`.
4. Choose **Colored** and press Save & apply. Cleared quests show their own color again: red
   for urgent quests, green for key quests, orange or blue for the rest. No gray badge should be
   left, and a special encounter shows red once either of its versions is cleared. Choose
   **Gray** to go back.
5. With Purple-lib, open **Options > Mod Options** and choose "Key Quest Markers". Its one row,
   "Finished quests", steps through Colored, Gray and Hidden, and the help bar says what each
   does. A change applies at once; close the window, restart, and the choice is kept.
6. With a save at Village 5★ that has not been offered The Scorching Blade yet: The Thunderclaw
   Wyvern, The Unwavering Colossus and The Entrancing Water Dancer are green until cleared, and
   so are the earlier chief requests that lead to them, on their own star pages. At other Village
   ranks these quests are orange, or gray once cleared: they lead to The Scorching Blade, which
   unlocks a Hunter Art.

## Log lines

Forge shows INFO and WARN lines only when its log level allows them. With an ERROR-only filter,
only the `can't find` and `hidden` lines and a failed start appear.

| Line | Meaning |
| --- | --- |
| `Key Quest Markers r32 loaded` | Started |
| `Key Quest Markers: setting added to Purple-lib Mod Options` | Purple-lib called the mod and took its page |
| `Key Quest Markers: Purple-lib API version N is older than 3; Mod Options not added` | An older Purple-lib called the mod: install r17 or later |
| `Key Quest Markers: Purple-lib refused the Mod Options page` | Send the log |
| `Key Quest Markers waited for the game to finish saving before saving its settings` | A save met a game save and waited, then went ahead |
| `Key Quest Markers can't find the game's save lock, so it won't save its settings yet` | Nothing is saved: send the log |
| `Key Quest Markers: ` followed by a message | A failed start (ERROR) or a failed save or load (WARN); the message says why |
| `Key Quest Markers hidden: …` | Badges are off for a reason the line names: send the log |

Without Purple-lib, no Purple-lib line appears; that is expected.
