"""Derive the quests whose clear unlocks another quest, and the reward quests with
their chains, from copied game resources.

Two native sources decide when a quest appears on the counter:

- `script\\check_quest_unlocked` (rCommonScript 0x5f6a387f, `loc/arc/village/common.arc`).
  sCommonScript query 0x3d7e90 runs it with the quest ID in [WORK0] through VM
  0x3d17f8 (opcode - 1 indexes the jump table at main+0x3d5874). 0x0e labels a case;
  a body is an AND of checks (0xa1 A == B, 0xa7 A >= B, a failure returns 0) ended by
  0x03 (return 1). Opcodes 0x75..0x78 load "quest P cleared" (0x523da4) and 0x40..0x43
  load bit P of the story flags at [GOT 0x18390e0] + 0x500. Every loaded value is
  only compared == 1 or summed into a count >= N, so a clear never locks a quest.
- NPC talk tables (rNpcTalkData 0x1a3e9cba, `loc/arc/npc/talk.arc`), 37-byte packed
  records. Tag evaluator 0x2451c8: kind 1 flag set, kind 11 quest cleared (quest =
  param, plus table[fixed - 10002] when fixed is 10002..10004). Action switch at
  main+0x2479d8: mAction1 kinds 1 and 4 set flag mAction1Param in the same array.

A quest unlocks another when its clear is loaded by a case body, or is a talk
condition of a row that sets a flag such a body loads, directly or through further
talk rows. A reward quest is the cleared-quest condition of a talk row that grants
Hunter Arts or Felyne ingredients; its chain is every quest its unlock requires.
"""
import struct
from collections import defaultdict

SCRIPT = ('script\\check_quest_unlocked', 0x5f6a387f)
TALK_KIND = 0x1a3e9cba
TALK_RECORD = '<IBBBBBHHhHHhHHhHHHHH'
QUEST_CLEARED = range(0x75, 0x79)
GRANTS = {*range(9, 17), 24, 25, *range(17, 22)}
FLAG_SET = range(0x40, 0x44)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def script_records(data):
    """u32 index, u8 command, two NUL-terminated strings; the header is f32 1.0, u32 count."""
    require(len(data) >= 8, 'Unlock script truncated')
    version, count = struct.unpack_from('<fI', data)
    require(version == 1.0 and 0 < count <= 65536, 'Unlock script header differs')
    records, at = [], 8
    for _ in range(count):
        require(at + 5 <= len(data), 'Unlock script record truncated')
        index, command = struct.unpack_from('<IB', data, at)
        at += 5
        params = []
        for _ in range(2):
            end = data.find(b'\0', at)
            require(end >= 0, 'Unlock script string unterminated')
            params.append(data[at:end].decode('ascii'))
            at = end + 1
        records.append((index, command, *params))
    require(at == len(data), 'Unlock script has trailing bytes')
    return records


def number(text, what):
    require(text.isdigit(), what + ' is not a number: ' + repr(text))
    return int(text)


def script_requirements(records):
    """Map each case's quest IDs to the quests and flags its body loads."""
    quests, flags = defaultdict(set), defaultdict(set)
    i = 0
    while i < len(records):
        if records[i][1] != 0x0e:
            i += 1
            continue
        targets = set()
        while i < len(records) and records[i][1] == 0x0e:
            # One base-game label has an empty ID; it can match no quest.
            if records[i][2] == '[WORK0]' and records[i][3].isdigit():
                targets.add(int(records[i][3]))
            i += 1
        while i < len(records) and records[i][1] not in (0x23, 0x24):
            _, command, first, _ = records[i]
            if command in QUEST_CLEARED:
                for t in targets:
                    quests[t].add(number(first, 'Cleared-quest operand'))
            elif command in FLAG_SET:
                for t in targets:
                    flags[t].add(number(first, 'Flag operand'))
            i += 1
    return quests, flags


def talk_rows(tables):
    rows = []
    size = struct.calcsize(TALK_RECORD)
    for name, data in sorted(tables.items()):
        require(len(data) >= 8, 'Talk table truncated: ' + name)
        version, count = struct.unpack_from('<fI', data)
        require(version == 1.0 and len(data) == 8 + size * count, 'Talk table layout differs: ' + name)
        rows += [struct.unpack_from(TALK_RECORD, data, 8 + size * i) for i in range(count)]
    return rows


def quest_table(image):
    """The tag-11 base table, through the literal the evaluator loads at main+0x2454f8."""
    literal = struct.unpack_from('<I', image, 0x2464f0)[0]
    table = (literal + 0x2454fc + 8) & 0xffffffff
    values = struct.unpack_from('<3I', image, table)
    require(all(v % 10000 == 0 for v in values), 'Talk quest table differs')
    return values


def talk_requirements(rows, bases):
    """flag -> (quests cleared, flags set) required by any talk row that sets the flag."""
    setters = defaultdict(lambda: (set(), set()))
    for r in rows:
        action, flag = r[15], r[16]
        if action not in (1, 4) or flag == 0:
            continue
        quests, flags = setters[flag]
        for kind, fixed, param in (r[6:9], r[9:12], r[12:15]):
            if kind == 1:
                flags.add(fixed)
            elif kind == 11:
                quests.add(talk_quest(fixed, param, bases))
    return setters


def talk_quest(fixed, param, bases):
    """Tag 11's quest: param, plus the table base when fixed is 10002..10004."""
    return param + (bases[fixed - 10002] if 10002 <= fixed <= 10004 else 0)


def flag_quests(flags, setters):
    """Quests cleared by any talk row that sets one of these flags, through further flag rows."""
    found, pending, seen = set(), list(flags), set()
    while pending:
        flag = pending.pop()
        if flag in seen:
            continue
        seen.add(flag)
        more_quests, more_flags = setters.get(flag, ((), ()))
        found |= set(more_quests)
        pending += more_flags
    return found


def requirements(script, tables, bases):
    """quest -> other quests whose clear its unlock loads, through script cases and talk flags."""
    quests, flags = script_requirements(script_records(script))
    rows = talk_rows(tables)
    setters = talk_requirements(rows, bases)
    needs = {t: (set(quests[t]) | flag_quests(flags[t], setters)) - {t} for t in set(quests) | set(flags)}
    return needs, rows


def reward_quests(rows, bases):
    """Quests named as cleared on a talk row whose mAction2 grants Hunter Arts or ingredients.

    Action2 switch at main+0x247c58: kinds 9..16, 24, 25 call the Hunter Arts grant
    0x3f0c3c in mode 0 (DialogMsg 100 "You learned new Hunter Arts!"); kinds 17..21
    call 0x3f1380 (DialogMsg 73 "New Ingredients were added!"). No other code grants them.
    """
    found = set()
    for r in rows:
        if r[17] in GRANTS:
            for kind, fixed, param in (r[6:9], r[9:12], r[12:15]):
                if kind == 11:
                    found.add(talk_quest(fixed, param, bases))
    return found


def checked(ids, what):
    ids = sorted(q for q in ids if 0 < q <= 0xffffffff)
    require(len(ids) <= 4096, what + ' list is implausibly long')
    return ids


def quest_lists(script, tables, image):
    """(unlocks, rewards): quests whose clear unlocks a different quest, and reward
    quests together with every quest their unlock chains require."""
    bases = quest_table(image)
    needs, rows = requirements(script, tables, bases)
    unlocks = set().union(*needs.values())
    rewards, pending = set(), list(reward_quests(rows, bases))
    while pending:
        q = pending.pop()
        if q not in rewards:
            rewards.add(q)
            pending += needs.get(q, ())
    return checked(unlocks, 'Unlock'), checked(rewards, 'Reward')


def from_inputs(input_path):
    """Read the pinned copies of loc/arc/village/common.arc, loc/arc/npc/talk.arc and main."""
    from mhgu_assets import read_arc
    from mhgu_binary import main_image
    _, common = read_arc(input_path('village_common.arc'))
    _, talk = read_arc(input_path('talk.arc'))
    require(SCRIPT in common, 'Unlock script missing from village common archive')
    tables = {name: e['data'] for (name, kind), e in talk.items() if kind == TALK_KIND}
    require(tables, 'No talk tables in talk archive')
    image, _ = main_image(input_path('main').read_bytes())
    return quest_lists(common[SCRIPT]['data'], tables, image)


def rust_lists(unlocks, rewards):
    return ''.join(f'pub static {name}: &[u32] = &[{", ".join(map(str, ids))}];\n'
                   for name, ids in (('UNLOCKS', unlocks), ('REWARDS', rewards)))
