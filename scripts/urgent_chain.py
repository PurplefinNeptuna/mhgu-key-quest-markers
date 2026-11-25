"""Quests outside the game's key categories that a rank-up urgent quest still needs.

An urgent quest opens only through its unlock-script case and the conversations
that set the flags that case loads (rules in quest_unlocks). A quest is needed when
every way to open the urgent clears it:

- a script load compared == 1 on its own (0xa1), or a count check (0x50 adds,
  0xa7 [WORK2] >= N) whose threshold covers every load it adds;
- a conversation tag outside an OR group; an OR group needs only what all its
  alternatives need, and a flag set by several conversations only what all of them need.

Bodies with other commands (branches, other loads) add nothing, so a list never
names a quest the game does not need. Key and urgent categories are left out: the
game's own key check covers them.

Village urgent category 24 + T is offered at Village tier T, the tier whose key
check (tag kind 13, counter 0x3b1a18 through 0x526d28) its chain makes. The build
checks that pairing for every urgent that yields a quest, and refuses a Hub/G urgent
that yields one, whose tier pairing is unverified.
"""
import struct
import quest_unlocks as qu

GROUPS = ('quest\\quest_group', 0x61cf79af)
GROUP_RECORD = '<IBBB'
TALK_KEY_CHECK = 13
SCRIPT_STEPS = {0x27, 0x26, 0xa1, 0x50, 0x52, 0xa7, 0x03, *qu.QUEST_CLEARED, *qu.FLAG_SET}


def quest_groups(data):
    """quest -> group category from the packed quest_group resource (f32 4.0, count, 7-byte records)."""
    qu.require(len(data) >= 8, 'Quest groups truncated')
    version, count = struct.unpack_from('<fI', data)
    size = struct.calcsize(GROUP_RECORD)
    qu.require(version == 4.0 and len(data) == 8 + size * count, 'Quest group layout differs')
    groups = {}
    for i in range(count):
        quest, category, _, _ = struct.unpack_from(GROUP_RECORD, data, 8 + size * i)
        qu.require(groups.get(quest, category) == category, f'Quest {quest} has conflicting groups')
        groups[quest] = category
    return groups


def key(category):
    return 1 <= category <= 17 or 19 <= category <= 22


def urgent(category):
    return 24 <= category <= 54


def body_needs(body):
    """(quests, flags) a case body requires one by one; nothing for a body it cannot model."""
    if any(command not in SCRIPT_STEPS for _, command, _, _ in body):
        return set(), set()
    needed, pending, counted = set(), None, []
    for _, command, first, second in body:
        if command in qu.QUEST_CLEARED:
            pending = ('quest', qu.number(first, 'Cleared-quest operand'))
        elif command in qu.FLAG_SET:
            pending = ('flag', qu.number(first, 'Flag operand'))
        elif command == 0xa1 and (first, second) == ('[WORK1]', '1') and pending:
            needed.add(pending)
            pending = None
        elif command == 0x50 and (first, second) == ('[WORK2]', '[WORK1]') and pending:
            counted.append(pending)
            pending = None
        elif command == 0xa7 and first == '[WORK2]' and second.isdigit():
            if int(second) >= len(counted):
                needed.update(counted)
            counted = []
        elif command == 0x52:
            counted = []
    return {v for k, v in needed if k == 'quest'}, {v for k, v in needed if k == 'flag'}


class Chains:
    """Memoised needs of quests and flags; an entry still being computed counts as needing nothing."""

    def __init__(self, script, tables, bases):
        self.cases = qu.script_cases(qu.script_records(script))
        self.bases = bases
        self.setters = {}
        for block, groups in qu.conversations(tables):
            for flag in qu.flags_set(block):
                self.setters.setdefault(flag, []).append(groups)
        self.quests = {}
        self.flags = {}

    def quest(self, quest):
        """(quests, key-check tiers) needed before quest is listed."""
        if quest not in self.quests:
            self.quests[quest] = (set(), set())
            quests, flags = body_needs(self.cases.get(quest, []))
            found, tiers = set(quests), set()
            for q in quests:
                more, more_tiers = self.quest(q)
                found |= more
                tiers |= more_tiers
            for f in flags:
                more, more_tiers = self.flag(f)
                found |= more
                tiers |= more_tiers
            self.quests[quest] = (found, tiers)
        return self.quests[quest]

    def flag(self, flag):
        if flag not in self.flags:
            self.flags[flag] = (set(), set())
            ways = [self.conversation(groups) for groups in self.setters.get(flag, [])]
            if ways:
                found = set.intersection(*(q for q, _ in ways))
                tiers = set.intersection(*(t for _, t in ways))
            else:
                found, tiers = set(), set()
            self.flags[flag] = (found, tiers)
        return self.flags[flag]

    def conversation(self, groups):
        found, tiers = set(), set()
        for group in groups:
            ways = [self.tag(tag) for tag in group]
            found |= set.intersection(*(q for q, _ in ways))
            tiers |= set.intersection(*(t for _, t in ways))
        return found, tiers

    def tag(self, tag):
        kind, fixed, param = tag
        if kind in qu.TALK_QUEST:
            quest = qu.talk_quest(fixed, param, self.bases)
            more, tiers = self.quest(quest)
            return {quest} | more, set(tiers)
        if kind in qu.TALK_FLAG:
            more, tiers = self.flag(fixed)
            return set(more), set(tiers)
        if kind == TALK_KEY_CHECK:
            return set(), {param}
        return set(), set()


def urgent_keys(script, tables, bases, groups):
    """Sorted (quest, Village tier) pairs: non-key quests a Village urgent needs at that tier."""
    chains = Chains(script, tables, bases)
    found = {}
    for quest, category in sorted(groups.items()):
        if not 24 <= category <= 46:
            continue
        needed, tiers = chains.quest(quest)
        extra = {q for q in needed if q != quest and not key(groups.get(q, 0)) and not urgent(groups.get(q, 0))}
        if not extra:
            continue
        qu.require(category <= 33, f'Hub/G urgent {quest} needs non-key quests {sorted(extra)}')
        tier = category - 24
        qu.require(tier in tiers, f'Urgent {quest} chain checks tiers {sorted(tiers)}, not {tier}')
        for q in extra:
            qu.require(found.get(q, tier) == tier, f'Quest {q} is needed at two Village tiers')
            found[q] = tier
    return sorted(found.items())
