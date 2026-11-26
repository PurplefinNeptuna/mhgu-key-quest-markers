"""Quests whose clear makes the game grant a Hunter Art, decoded from main.

Two loops grant arts. Grant 0x3f0c3c takes a table of u32 art IDs (pointer in r1, count in
r2); its ten callers (0x3f1020..0x3f12b4) are the base set and the nine set functions that talk
tag kinds 46..53 and mAction2 9..16, 24, 25 reach. Loop 0x3ea6e8 walks a fixed 44-art table with
no talk row; its caller 0x38669c is reached from 0x384968, in the quest result code (inference
from the address range). Both set the owned bit (+0xd24) of an art the player lacks only when
check 0x3efb30 returns 1. The check switches on art - 2 (189 cases, jump table at 0x3efb84).
A case that reaches 0x523da4 (quest cleared) with the quest in r1 needs that clear; r1 enters
the switch as 0x18899 (100505). Cases that read only story flags route through urgent quests
402, 713 and 10768 (flags 24, 1007, 1400), which the talk reward list already holds.
"""
import struct

GRANT = 0x3f0c3c
GRANT_SITES = (0x3f1020, 0x3f1134, 0x3f1164, 0x3f1194, 0x3f11c4,
               0x3f11f4, 0x3f1224, 0x3f1254, 0x3f1284, 0x3f12b4)
# Result loop 0x3ea6e8: its check call, table address (add rX, pc, rY) and loop count (cmp).
RESULT_CHECK_CALL = 0x3ea738
RESULT_TABLE = 0x3ea6fc
RESULT_COUNT = 0x3ea77c
CHECK = 0x3efb30
CHECK_END = 0x3f0a74
CASES = 0x3efb84
CASE_COUNT = 189
FIRST_ART = 2
ENTRY_R1 = (0x3efb74, 0x3efb7c)
QUEST_CLEARED = 0x523da4
# Other checks the cases call or tail-call; none loads a quest clear (callees unread).
OTHER_CALLS = {0x524040, 0x262f68, 0x523b0c, 0x526dd4}
AL = 0xe


def require(condition, message):
    if not condition:
        raise ValueError(message)


def word(image, at):
    return struct.unpack_from('<I', image, at)[0]


def branch(w, at):
    """(target, link) for b/bl, else None."""
    if (w >> 25) & 7 != 5 or w >> 28 == 0xf:
        return None
    offset = (w & 0xffffff) - ((w & 0x800000) << 1)
    return (at + 8 + (offset << 2)) & 0xffffffff, bool(w & (1 << 24))


def mov_imm(w):
    """(rd, value, kind) for movw, movt and mov with a rotated immediate."""
    rd = (w >> 12) & 15
    if w & 0x0ff00000 in (0x03000000, 0x03400000):
        kind = 'movt' if w & 0x00400000 else 'movw'
        return rd, ((w >> 4) & 0xf000) | (w & 0xfff), kind
    if w & 0x0fef0000 == 0x03a00000:
        rot, imm = ((w >> 8) & 15) * 2, w & 0xff
        return rd, ((imm >> rot) | (imm << (32 - rot))) & 0xffffffff, 'mov'
    return None


def writes_r1(w):
    """True when an instruction outside the decoded forms may change r1."""
    if (w >> 26) & 3 == 0:
        test = (w >> 21) & 15 in range(8, 12) and w & (1 << 20)
        return not test and (w >> 12) & 15 == 1
    if (w >> 26) & 3 == 1:
        return bool(w & (1 << 20)) and (w >> 12) & 15 == 1
    if (w >> 25) & 7 == 4:
        return bool(w & (1 << 20)) and bool(w & 2)
    return False


def entry_r1(image):
    low, high = (mov_imm(word(image, at)) for at in ENTRY_R1)
    require(low and low[:1] == (1,) and low[2] == 'movw', 'Art check entry differs')
    require(high and high[:1] == (1,) and high[2] == 'movt', 'Art check entry differs')
    return low[1] | (high[1] << 16)


def case_quests(image, start, r1):
    """Quests one art case loads as cleared, over every path of the case."""
    found, seen, pending = set(), set(), [(start, r1)]
    while pending:
        at, r1 = pending.pop()
        while (at, r1) not in seen:
            seen.add((at, r1))
            require(CHECK <= at < CHECK_END, 'Art check leaves its function at %#x' % at)
            w = word(image, at)
            jump, moved = branch(w, at), mov_imm(w)
            if jump and jump[0] == QUEST_CLEARED:
                require(r1 is not None, 'Art check quest unknown at %#x' % at)
                found.add(r1)
            outside = jump and not CHECK <= jump[0] < CHECK_END
            require(not outside or jump[0] in OTHER_CALLS | {QUEST_CLEARED},
                    'Art check calls unread code at %#x' % at)
            if jump and not jump[1] and not outside:
                pending.append((jump[0], r1))
            if jump and jump[1]:
                r1 = None
            if jump and not jump[1] and w >> 28 == AL:
                break
            if w & 0x0fff8000 == 0x08bd8000 and w >> 28 == AL:
                break
            if moved and moved[0] == 1 and w >> 28 == AL and moved[2] != 'movt':
                r1 = moved[1]
            elif moved and moved[0] == 1 and w >> 28 == AL and r1 is not None:
                r1 = (r1 & 0xffff) | (moved[1] << 16)
            elif w & 0x0ffff000 == 0x02811000 and w >> 28 == AL and r1 is not None:
                r1 = r1 + mov_imm(0x03a01000 | (w & 0xfff))[1]
            elif moved and moved[0] == 1 or not moved and writes_r1(w):
                r1 = None
            at += 4
    return found


def pc_table(image, at):
    """Address that `add rX, pc, rY` at `at` forms from the literal an earlier `ldr rY, [pc, #imm]` loads."""
    w = word(image, at)
    require(w & 0x0fff0ff0 == 0x008f0000, 'Art table address differs at %#x' % at)
    loads = [a for a in range(at - 4, at - 24, -4)
             if word(image, a) & 0x0fff0000 == 0x059f0000 and (word(image, a) >> 12) & 15 == w & 15]
    require(loads, 'Art table literal missing at %#x' % at)
    return (word(image, loads[0] + 8 + (word(image, loads[0]) & 0xfff)) + at + 8) & 0xffffffff


def grant_tables(image):
    """Art IDs of every table either grant loop checks."""
    tables = []
    for site in GRANT_SITES:
        require(branch(word(image, site), site) == (GRANT, True), 'Art grant call differs at %#x' % site)
        near = range(site - 4, site - 40, -4)
        adds = [at for at in near if word(image, at) & 0x0ffffff0 == 0x008f1000]
        counts = [mov_imm(word(image, at)) for at in near]
        counts = [m[1] for m in counts if m and m[0] == 2]
        require(adds and counts, 'Art table differs at %#x' % site)
        tables.append((pc_table(image, adds[0]), counts[0]))
    require(branch(word(image, RESULT_CHECK_CALL), RESULT_CHECK_CALL) == (CHECK, True),
            'Result art check call differs')
    cmp = word(image, RESULT_COUNT)
    require(cmp & 0x0ff0f000 == 0x03500000, 'Result art count differs')
    tables.append((pc_table(image, RESULT_TABLE), mov_imm(0x03a00000 | (cmp & 0xfff))[1]))
    arts = set()
    for table, count in tables:
        require(0 < count <= CASE_COUNT, 'Art table count %d is implausible' % count)
        arts.update(struct.unpack_from('<%dI' % count, image, table))
    return arts


def art_quests(image):
    """Quests whose clear the check of some granted Hunter Art needs."""
    r1 = entry_r1(image)
    quests = set()
    for art in grant_tables(image):
        require(FIRST_ART <= art < FIRST_ART + CASE_COUNT, 'Art %d outside the check switch' % art)
        start = (CASES + struct.unpack_from('<i', image, CASES + 4 * (art - FIRST_ART))[0]) & 0xffffffff
        quests |= case_quests(image, start, r1)
    return quests
