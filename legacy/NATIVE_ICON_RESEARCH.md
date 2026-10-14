# Native Rise-style key-quest badge research

Research date: 2026-10-14. Target: MHGU Switch 1.4.0 with Forge on Eden/Ryujinx.
The user selected the native UI approach, then explicitly requested research
only. No plugin code, game resource, release, installed package, save or
emulator setting was changed. No game was launched.

## Requested behavior

Add the emblem shown in the supplied Rise screenshots on the left of each
progression key-quest row. Use red when that quest is unfinished and grey when
completed. Ordinary quests have no badge. Preserve MHGU's quest-type icons,
completion stamps, unlock rules, sorting and progression requirements.
Rise's header counter and its choice-based progression system are outside this
request. An urgent quest does not become a progression key merely because it
is urgent. Replace the current `[KEY] ` list prefix when a native implementation
is eventually built; detail-screen behavior remains to be decided.

## Findings

The existing classifier supplies the key/ordinary decision from native quest
groups. The ordinary quest-list caller supplies the completion decision too.
Adding the badge has a concrete native resource route, but construction and
rendering of an added object have not been validated in-game.

### Completion state and row refresh

The saved decompilation of `main + 0x0054d030` builds eight quest pointers and
an eight-byte `local_30` array. For each normal quest it calls
`main + 0x00523d00` with the current completion record and quest number. A zero
return sets that row's flag to true; the normal UI then uses those flags for
its "new" indicators. The special arena/training route uses a different table;
it must not be treated as the normal rank-progression path.

The completion lookup at `0x00523d00` finds the quest's index in `rQuestGroup`
and reads a packed bit:

```text
completed = (record[0x100 + (group_index >> 3)] &
             (1 << (group_index & 7))) != 0
```

The fallback index is zero when no match is found. A future implementation must
not independently interpret that fallback as a valid completion result for an
unknown quest. Reusing the already built normal-row state avoids introducing
a second save-bit decoder. This work reads no user's live save.

`main + 0x00616ba0` forwards the page to the eight-row builder at
`main + 0x00616cb0`. That builder receives the quest pointers, the above flags,
the selected row and other native row flags. It updates visibility, title,
selection appearance and existing icons, and hides unused rows. Its post-call
boundary is a candidate for applying badge visibility and red/grey appearance
after native updates. The entry signature, original-call ABI, GE/flags liveness,
callers and conflict handling still require a plugin audit before any detour.

The second builder at `0x00618324` is reached through a special list path;
matching native layout is not proof that every category should receive badges.

### Native resource and left-side space

The inspected English quest-list resource is:

```text
nativeNX/eng/arc/village/common_eng.arc
  eng\GUI\05_meeting_p\count\counter.gui
```

It is GUI version 141077, 77,040 bytes, with a 1280x720 virtual screen,
63 instances, 56 animation objects and nine animations. Native instance indices
16 through 23 are `Anm_list_S00` through `Anm_list_S07`; all use animation ID
20, `list_S`. Their initial Y offsets are 0, 42, ... 294. The row animation has
12 objects and 15 sequences.

The original executable's row table at `main + 0x01635158` contains
`16,17,18,19,20,21,22,23`, matching the extracted instance indices. Other
native arrays select indices 45-52 for "new" indicators and 53-60 for stamps.
These existing elements must not be reused as the key badge.

Inside `list_S`, relative object slot 2 (`Tex_icon`) starts at X=28, Y=6 and
is 28x28. Slot 4 (`Message`) starts at X=62, Y=9 with a 355x38 text area.
The background starts at X=0 and has a 40-pixel row height. These are initial
resource values, not a verified final on-screen placement: row sequences,
parent transforms and clipping still affect them.

A separate texture object attached to the row animation would give each row
its own badge while sharing the authored layout. A candidate position is
immediately left of the row's existing icon/background, subject to checking
the parent bounds and animation states. Do not replace `Tex_icon` or globally
replace a shared atlas region: those paths already carry other information.

The supplied HD Project archive contains a byte-identical `counter.gui`.
Its outer archive differs from base and contains other HD resources, so any
future RomFS replacement must deliberately preserve/merge them. This checks
the library input, not installed packages or activation.

### Native controls available

The saved DTI includes `cGUIObjTexture` properties for texture, rectangle,
vertex color, size and visibility. The native UI wrappers forward through the
holder at `cUIObject + 0x24`:

- `0x0056e528`: instance visibility.
- `0x0056e530`: object-property visibility through holder `0x00545630`.
- `0x0056e6fc`: object color through holder `0x0054700c`; the latter updates
  four vertices for the recognized texture/polygon classes.
- `0x0056eec8`: texture rectangle through holder `0x00546f84`.

Fresh read-only exports compared these functions with the original executable
instructions and found zero byte differences. Some decompiler signatures omit
forwarded arguments or floating-point arguments; those signatures must not be
copied into a plugin without checking ARM instructions and actual calling ABI.

Forge supplies hooking, memory and resource access, but the inspected public
headers expose no general native GUI-object creation/editor API. A resource
extension plus Forge row-state updates is the strongest current approach.
Runtime-only object construction remains an unverified alternative.

## Proposed implementation boundary, not an implementation

1. Add a dedicated emblem texture and a row child object, default hidden.
   Preserve all existing object bindings and all 15 row sequences.
2. After the ordinary row update, classify the exact quest ID. Hide the badge
   for unknown, ordinary or unused rows. Show red for unfinished progression
   keys and grey for completed ones using that page's native completion state.
3. Use a neutral emblem with tint or separate red/grey texture regions. Audit
   parent selection colors so highlighting does not recolor the badge.
4. Keep the existing accepted release immutable and stage a separate candidate.
   Verify archive readback, unrelated resource preservation, hook ABI/state,
   packaging and selected-mod collisions before requesting a manual test.

The state decision is comparatively small. The added drawable object,
resource layout, selection inheritance and clipping are the substantial work.
No safe spare badge slot has been established. This is feasible in principle,
with moderate-to-difficult native UI work; it is not a verified drop-in change.

Manual acceptance would need unfinished/completed/ordinary rows, selection,
both pages and scrolling, list closure/reopening, completion after returning
from a quest, Village/Hub/G-rank coverage and the selected HD/mod set on each
target emulator. The exact emblem asset and final coordinates are not produced
by this research.

## Evidence and input identity

Original main SHA-256:
`b3935415499549adaf4c0e89822831daa175cfd456a7990791c79be3997645ef`.
The saved database uses image base `0x009c9000`; all offsets above are relative
to main. The original executable stores the resolved row-table pointer as a
main-relative value; do not subtract the Ghidra base from that pointer again.

Base English common archive SHA-256:
`c4a614f61a629e5d9591dd8772b335fc24615001c8d5ed52e964f91ea1cfea44`.
HD library English common archive SHA-256:
`fd8cd4521cb5c5d07e0d1e5e7275aaf5ecbcfd34d20aae2b6f880ab65b22f438`.
Both inspected `counter.gui` payloads SHA-256:
`95730f3adbaf2c017968cb0079a0caa666de541cecd66ff8ad223e1137b30c5a`.

Evidence stays outside distributions:

- `work/key-quest-markers/research/rise-native/inputs.json`: copied dump input
  hashes and extracted GUI paths/hashes.
- `work/key-quest-markers/research/rise-native/row-layout.json`: parsed native
  row instances and object properties; assertions check animation ID and
  initial boolean visibility.
- `work/key-quest-markers/research/pass1/function_0054d030.c` and
  `function_00616cb0.c`, plus pass2/pass3: previously saved callers and lookup.
- `work/damage-numbers/research/1ed6a076a012/` and `92dce073e93a/`: fresh
  read-only exports made with the existing generic research helper.
- `references/MHGU-Modding/templates/gui_mhgu.bt`: structural reference,
  checked against extracted counts, bounds, names and native row-table values.

No runtime, packaging, save write, installation or activation was tested.
