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
  The first case whose label matches decides: its body always ends in a return
  (0x03 at 0x3d5cdc, a failed check at 0x3d5cac), so a later label never runs.
- NPC talk tables (rNpcTalkData 0x1a3e9cba, `loc/arc/npc/talk.arc`), 37-byte packed
  records. Tag evaluator 0x2451c8: kind 1 flag set, kind 11 quest cleared (quest =
  param, plus table[fixed - 10002] when fixed is 10002..10004); kinds 16 and 18 are
  the OR forms of 1 and 11. Action switch at main+0x2479d8: mAction1 kinds 1 and 4
  set flag mAction1Param in the same array.
- Conversations: selector 0x243d00 splits a table into consecutive blocks, each ending
  at a row whose page attribute is 2, 7, 8, 10, 14 or 15 (mask 0x3161 at 0x243e48).
  A block plays when the tags of its first row and of every following row, up to a
  row whose first tag is 0, all hold (0x2443ec); an OR-kind tag joins the tag before
  it and kind 15 only continues. Runner 0x246b1c then applies every row's actions.

A quest unlocks another when its clear is loaded by a case body, or is a condition
of a conversation that sets a flag such a body loads, directly or through further
conversations. A reward quest is a cleared-quest condition of a conversation that
grants Hunter Arts or Felyne ingredients; its chain is every quest its unlock requires.
"""
import struct
from collections import defaultdict

SCRIPT = ('script\\check_quest_unlocked', 0x5f6a387f)
TALK_KIND = 0x1a3e9cba
TALK_RECORD = '<IBBBBBHHhHHhHHhHHHHH'
QUEST_CLEARED = range(0x75, 0x79)
GRANTS = {*range(9, 17), 24, 25, *range(17, 22)}
FLAG_SET = range(0x40, 0x44)
# Talk tag kinds (evaluator 0x2451c8 jump table at 0x2451fc): 16..18 share the
# handlers of 1, 2 and 11; the selector ORs 16..21, 119 and 147 with the tag before.
TALK_FLAG = (1, 16)
TALK_QUEST = (11, 18)
TALK_OR = {*range(16, 22), 119, 147}
TALK_CONTINUE = 15
TALK_STOP = {2, 7, 8, 10, 14, 15}


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


def script_cases(records):
    """quest -> body records of the first case labelled with it."""
    cases = {}
    i = 0
    while i < len(records):
        if records[i][1] != 0x0e:
            i += 1
            continue
        targets = []
        while i < len(records) and records[i][1] == 0x0e:
            # One base-game label has an empty ID; it can match no quest.
            if records[i][2] == '[WORK0]' and records[i][3].isdigit():
                targets.append(int(records[i][3]))
            i += 1
        body = []
        while i < len(records) and records[i][1] not in (0x23, 0x24):
            body.append(records[i])
            i += 1
        for t in targets:
            cases.setdefault(t, body)
    return cases


def script_requirements(records):
    """Map each quest to the quests and flags its first case body loads."""
    quests, flags = defaultdict(set), defaultdict(set)
    for target, body in script_cases(records).items():
        for _, command, first, _ in body:
            if command in QUEST_CLEARED:
                quests[target].add(number(first, 'Cleared-quest operand'))
            elif command in FLAG_SET:
                flags[target].add(number(first, 'Flag operand'))
    return quests, flags


def talk_tables(tables):
    """Rows of each talk table, in archive name order."""
    size = struct.calcsize(TALK_RECORD)
    out = []
    for name, data in sorted(tables.items()):
        require(len(data) >= 8, 'Talk table truncated: ' + name)
        version, count = struct.unpack_from('<fI', data)
        require(version == 1.0 and len(data) == 8 + size * count, 'Talk table layout differs: ' + name)
        out.append([struct.unpack_from(TALK_RECORD, data, 8 + size * i) for i in range(count)])
    return out


def condition_groups(block):
    """AND list of OR groups of (kind, fixed, param) tags that decide whether a block plays."""
    groups = []
    for n, row in enumerate(block):
        if n and row[6] == 0:
            break
        for tag in (row[6:9], row[9:12], row[12:15]):
            if tag[0] in (0, TALK_CONTINUE):
                continue
            if tag[0] in TALK_OR and groups:
                groups[-1].append(tag)
            else:
                groups.append([tag])
    return groups


def conversations(tables):
    """(rows, condition groups) for every conversation block of every talk table."""
    out = []
    for rows in talk_tables(tables):
        start = 0
        for i, row in enumerate(rows):
            if row[1] in TALK_STOP or i == len(rows) - 1:
                block = rows[start:i + 1]
                out.append((block, condition_groups(block)))
                start = i + 1
    return out


def quest_table(image):
    """The tag-11 base table, through the literal the evaluator loads at main+0x2454f8."""
    literal = struct.unpack_from('<I', image, 0x2464f0)[0]
    table = (literal + 0x2454fc + 8) & 0xffffffff
    values = struct.unpack_from('<3I', image, table)
    require(all(v % 10000 == 0 for v in values), 'Talk quest table differs')
    return values


def flags_set(block):
    """Flags any row of a conversation sets when it plays."""
    return {r[16] for r in block if r[15] in (1, 4) and r[16]}


def talk_requirements(talks, bases):
    """flag -> (quests cleared, flags set) any conversation setting the flag checks."""
    setters = defaultdict(lambda: (set(), set()))
    for block, groups in talks:
        for flag in flags_set(block):
            quests, flags = setters[flag]
            for kind, fixed, param in (tag for group in groups for tag in group):
                if kind in TALK_FLAG:
                    flags.add(fixed)
                elif kind in TALK_QUEST:
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
    talks = conversations(tables)
    setters = talk_requirements(talks, bases)
    needs = {t: (set(quests[t]) | flag_quests(flags[t], setters)) - {t} for t in set(quests) | set(flags)}
    return needs, talks


def reward_quests(talks, bases):
    """Quests a conversation checks as cleared when one of its rows' mAction2 grants Hunter Arts
    or ingredients.

    Action2 switch at main+0x247c58: kinds 9..16, 24, 25 call the Hunter Arts grant
    0x3f0c3c in mode 0 (DialogMsg 100 "You learned new Hunter Arts!"); kinds 17..21
    call 0x3f1380 (DialogMsg 73 "New Ingredients were added!"). No other code grants them.
    """
    found = set()
    for block, groups in talks:
        if any(r[17] in GRANTS for r in block):
            for kind, fixed, param in (tag for group in groups for tag in group):
                if kind in TALK_QUEST:
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
    needs, talks = requirements(script, tables, bases)
    unlocks = set().union(*needs.values())
    rewards, pending = set(), list(reward_quests(talks, bases))
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
    from urgent_chain import GROUPS, quest_groups, urgent_keys
    require(GROUPS in common, 'Quest groups missing from village common archive')
    unlocks, rewards = quest_lists(common[SCRIPT]['data'], tables, image)
    groups = quest_groups(common[GROUPS]['data'])
    chained = urgent_keys(common[SCRIPT]['data'], tables, quest_table(image), groups)
    return unlocks, rewards, chained


def rust_lists(unlocks, rewards, chained):
    lists = ''.join(f'pub static {name}: &[u32] = &[{", ".join(map(str, ids))}];\n'
                    for name, ids in (('UNLOCKS', unlocks), ('REWARDS', rewards)))
    pairs = ', '.join(f'({quest}, {tier})' for quest, tier in chained)
    return lists + f'pub static URGENT_KEYS: &[(u32, u8)] = &[{pairs}];\n'
