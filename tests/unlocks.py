#!/usr/bin/env python3
"""Check the build-time unlock and reward lists against hand-traced game cases and a synthetic script."""
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from paths import input_path
import quest_unlocks as qu
import urgent_chain as uc


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

# The first case labelled with a quest decides; a later label for it never runs.
cases = qu.script_cases(qu.script_records(script(
    (0x0e, '[WORK0]', '7'), (0x27, '', ''), (0x41, '1', ''), (0x23, '', ''),
    (0x0e, '[WORK0]', '7'), (0x27, '', ''), (0x41, '2', ''), (0x23, '', ''))))
assert [r[2] for r in cases[7]] == ['', '1'], cases

# Talk rows: (index, page, talk, label, village, online, tag1 x3, tag2 x3, tag3 x3, action1 x2, action2 x3).
def row(page, talk, tags=(), action=(0, 0)):
    flat = [v for tag in tags for v in tag] + [0] * (9 - 3 * len(tags))
    return (0, page, talk, 0, 0, 0, *flat, *action, 0, 0, 0)

# A block plays only when its first row and every following row up to one whose first tag
# is 0 hold; an OR tag joins the tag before it, and kind 15 only continues.
block = [row(1, 3, [(2, 31, 0), (13, 0, 5)], (1, 31)), row(1, 0, [(1, 209, 0), (1, 259, 0)], (1, 745)),
         row(1, 0), row(2, 0, [(1, 999, 0)])]
assert qu.condition_groups(block) == [[(2, 31, 0)], [(13, 0, 5)], [(1, 209, 0)], [(1, 259, 0)]]
assert qu.flags_set(block) == {31, 745}
either = [row(1, 6, [(2, 157, 0), (15, 0, 0), (11, 0, 319)], (1, 157)), row(1, 0, [(18, 0, 320)]), row(2, 0)]
assert qu.condition_groups(either) == [[(2, 157, 0)], [(11, 0, 319), (18, 0, 320)]]

# Counted clears are needed only when the threshold covers every one of them.
both = [(0, 0x76, '1', ''), (0, 0x50, '[WORK2]', '[WORK1]'), (0, 0x76, '2', ''),
        (0, 0x50, '[WORK2]', '[WORK1]'), (0, 0xa7, '[WORK2]', '2'), (0, 0x03, '', '')]
assert uc.body_needs(both) == ({1, 2}, set())
assert uc.body_needs(both[:4] + [(0, 0xa7, '[WORK2]', '1')]) == (set(), set())
assert uc.body_needs([(0, 0x16, '[HR]', '9'), (0, 0x76, '1', ''), (0, 0xa1, '[WORK1]', '1')]) == (set(), set())

ids, rewards, chained = qu.from_inputs(input_path)
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
# The Scorching Blade (601), Village tier 5: the Bherna Chief's Glavenus talk (npc_001 rows 116-117)
# needs flags 159, 209 and 259, set after 504, 508 and 510 are reported to the Kokoto, Pokke and
# Yukumo chiefs; each of those opens through its chief's request line (219/220/318, 224/225/323,
# 229/230/328) and either quest of a special encounter pair.
assert chained == [(q, 5) for q in (219, 220, 224, 225, 229, 230, 318, 323, 328, 504, 508, 510)], chained
for quest in (508, 510):
    assert quest in ids, quest
expected = ('pub static UNLOCKS: &[u32] = &[1, 2];\npub static REWARDS: &[u32] = &[3];\n'
            'pub static URGENT_KEYS: &[(u32, u8)] = &[(4, 5)];\n')
assert qu.rust_lists([1, 2], [3], [(4, 5)]) == expected
print('PASS: unlock list', len(ids), 'quests; reward list', len(rewards), 'quests;',
      'urgent quest chain', len(chained), 'quests')
