#!/usr/bin/env python3
"""Check the build-time unlock and reward lists against hand-traced game cases and a synthetic script."""
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from paths import input_path
import quest_unlocks as qu


def script(*records):
    body = b''.join(struct.pack('<IB', i, c) + a.encode() + b'\0' + b.encode() + b'\0'
                    for i, (c, a, b) in enumerate(records))
    return struct.pack('<fI', 1.0, len(records)) + body


# A case body ends at 0x23 or at a 0x24 switch boundary; later labels start a new case.
records = qu.script_records(script(
    (0x0e, '[WORK0]', '5'), (0x27, '', ''), (0x26, '', ''), (0x76, '1', ''), (0xa1, '[WORK1]', '1'),
    (0x03, '', ''), (0x24, '', ''), (0x20, '[WORK0]', '20000'), (0x0e, '[WORK0]', '6'),
    (0x27, '', ''), (0x26, '', ''), (0x41, '9', ''), (0xa1, '[WORK1]', '1'), (0x03, '', ''), (0x23, '', '')))
quests, flags = qu.script_requirements(records)
assert dict(quests) == {5: {1}} and dict(flags) == {6: {9}}, (quests, flags)
for bad in [b'', struct.pack('<fI', 2.0, 1), script((0x0e, 'x', 'y')) + b'!']:
    try:
        qu.script_records(bad)
    except ValueError:
        continue
    raise AssertionError('malformed unlock script accepted')

ids, rewards = qu.from_inputs(input_path)
assert ids == sorted(set(ids)) and 0 not in ids and rewards == sorted(set(rewards)) and 0 not in rewards
# Traced in the pinned base 1.4.0 data:
#   220: npc_*_td sets the flag that unlocks 219 once 220 is cleared.
#   703: with 705, NPC 701 sets flag 1010, which leads to key quest 717.
#   10750: one of the clears 10772's script case counts.
#   111304 / 41811: talk quests given as table base (10003 -> 100000, 10004 -> 40000) plus param.
for quest in (220, 703, 705, 10750, 111304, 41811):
    assert quest in ids, quest
# 102 is only a case label; 202 is required by nothing.
for quest in (102, 202):
    assert quest not in ids, quest
# Rewards: 11207 grants Hunter Arts and 233 ingredients after their NPC talk; 10529 is required
# on the way to Hunter Arts quest 11211, and 10124 on the way to ingredient quest 11113.
for quest in (11207, 233, 10529, 10124):
    assert quest in rewards, quest
for quest in (202, 220):
    assert quest not in rewards, quest
assert qu.rust_lists([1, 2], [3]) == 'pub static UNLOCKS: &[u32] = &[1, 2];\npub static REWARDS: &[u32] = &[3];\n'
print('PASS: unlock list', len(ids), 'quests; reward list', len(rewards), 'quests')
