# Native Rise-style key-quest badge research

Research date: 2026-10-14. Target: MHGU Switch 1.4.0 with Forge on Eden/Ryujinx.
The user selected the native UI approach, then explicitly requested research
only. No plugin code, game resource, release, installed package, save or
emulator setting was changed. No game was launched.

## Requested behavior

Add an emblem on the left of each progression key-quest row. The user later
selected direct reuse of MHGU's HD `HD_lobby00_BM_NOMIP` atlas, with the larger
emblem beside the numbers preferred over the small emblem between the person
and smiley icons. Use red for unfinished keys and grey for completed keys.
Use yellow for active urgents and grey for old/inactive urgents, even if an
inactive urgent is unfinished. Ordinary quests have no badge. Preserve MHGU's quest-type icons,
completion stamps, unlock rules, sorting and progression requirements.
Rise's header counter and its choice-based progression system are outside this
request. Urgents have their own classification and color precedence. Replace
the current `[KEY] ` list prefix when a native implementation
is eventually built; detail-screen behavior remains to be decided.

## Findings

The existing classifier supplies the key/ordinary decision from native quest
groups. Actual completion and the row's "new" indicator are separate data paths.
Adding the badge has a concrete native resource route, but construction and
rendering of an added object have not been validated in-game.

### Completion state and row refresh

Correction to the first research checkpoint: `main + 0x0054d030` builds eight
quest pointers and an eight-byte `local_30` array, but that array controls the
"new" indicators, not actual quest completion. It calls `0x00523d00`, which
reads a separate bitfield at record `+0x100`. A zero return makes the indicator
visible. The badge must not use this flag: acknowledging/viewing a quest and
completing it must remain different events. The special arena/training route
also uses a separate table.

The actual completion reader is `0x00523da4`. Native key-completion counters
at `0x003b1964`/`0x003b1d70` and urgent progression processing at `0x0050cbd0`
use it. It finds the quest's index in `rQuestGroup` and reads:

```text
completed = (record[group_index >> 3] &
             (1 << (group_index & 7))) != 0
```

The fallback index is zero when no match is found. A future implementation must
not independently interpret that fallback as a valid completion result for an
unknown quest. A future adapter should use the checked native completion
reader, or a separately verified row completion field, rather than interpreting
the "new" flags. Its adjacent writers `0x00523f30` and `0x00523e44` target the
completion and `+0x100` bitfields separately; neither should be called by this
mod. This work reads no user's live save.

`main + 0x00616ba0` forwards the page to the eight-row builder at
`main + 0x00616cb0`. That builder receives the quest pointers, the "new" flags,
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

### Direct reuse of the HD emblem

The user-supplied MHGU screenshots show a white emblem on the Quest Counter
header and an existing quest-type icon before each row title. Keep that type
icon and place the new badge farther left; do not recolor the type icon.

The native signboard resource is
`eng\GUI\04_lobby\common\signboard.gui` in the English village common archive.
Its `Board` animation has a `Tex_icon` object. Sequence `0x000f4240` sets that
object to texture ID 2 and rectangle `(136,344,198,406)`. Texture ID 2 resolves
to `eng\GUI\99_texture\HD_lobby00_BM_NOMIP`. This is the larger emblem beside
the numbers. The HD library's signboard GUI is byte-identical to base, and the
decoded HD atlas region matches the requested emblem visually.

The source rectangle is 62x62 in the GUI's logical atlas coordinates. The
referenced atlas metadata is 512x512, with inverse dimensions `1/512`. The HD
texture is 2048x2048, so its corresponding inspection rectangle is
`(544,1376,792,1624)`, 248x248 physical pixels. Preserve the logical rectangle
and native UV normalization; do not put HD pixel coordinates into a GUI that
still declares a 512x512 atlas.

The row's `counter.gui` **already declares this atlas as texture ID 22**.
IDs belong to each resource: the header's ID 2 and row's ID 22 refer to the same
path, but must not be interchanged blindly. A new row texture object can refer
to ID 22 and the existing rectangle. No new icon texture, extracted PNG, copied
sprite sheet or atlas overwrite needs to ship. The inspection copies under
`work/` are research material only. The game will use the atlas supplied by
the selected resource package; the HD appearance requires that HD atlas to
actually win the resource merge.

The larger emblem is a better candidate for a small row badge than the upper
emblem: the larger HD source has more detail and a simpler silhouette. Its
white foreground suits red/grey/yellow vertex tinting, with native shadow/edge
pixels retained. The final color, size, sampling and parent selection tint
still require a native render check. Changing only a new child's tint preserves
the white header emblem and other users of this shared atlas.

### Active and historical urgent quests

Fresh original-byte-checked exports identify a useful native route:

- `cQuestData::load`, `0x0037539c`, reads the final `u16` into `mFlag`.
  The ARM32 field is at object `+0x10c`.
- `0x003bc5f0` checks `mFlag & 1` before classifying the quest into five
  special selector categories (`0..4`); its default is `5`. Classification
  additionally checks native progression ranges and quest IDs. Do not use
  `mQuestType` or a quest-title string as the urgency decision.
- `0x003bb318` calls that classifier and the actual completion reader. For
  category `0..4` with completion false, its special-list branch retains up
  to 16 quest IDs per category. Those arrays begin at selector `+0x68`, with
  a `0x40`-byte stride, and their `u16` counts begin at `+0x1a8`.

The copied `vq/gq/gq2` resources supplied 1,302 compact quest records. Their
final `u16` candidate at file offset 367 has bit zero set for 28 records, all
in urgent progression groups `24..46`; every other inspected record clears it.
This matches the native loader's final-field read and selector gate. Reading
the live object field is preferable to introducing a file decoder into the
plugin. The parsed file-tail correlation alone is not a gameplay test or an
exhaustive check of DLC/runtime variants.

The strongest proposed yellow decision is membership of the current native
special lists, after confirming their menu/category meaning and freshness.
That distinguishes currently routed, unfinished urgents from historical ones.
Urgent identity must still be retained when the classifier returns `5`, because
an old urgent should display grey rather than disappear. Confirm the normal
Village, Hub and G-rank paths, multiple simultaneous urgents and exceptional
progression variants before treating these arrays as a final plugin contract.

An earlier candidate at `0x003b187c` is rejected for urgency: its neighboring
call paths inspect delivery items and quantities in the `+0xec/+0xf8` records.
Those item/request fields are not an established active-urgent identifier.

Proposed badge precedence:

| Native classification/state | Badge |
| --- | --- |
| Urgent, currently active | Yellow |
| Urgent, old/inactive or completed | Grey |
| Progression key, unfinished | Red |
| Progression key, completed | Grey |
| Ordinary, unknown or unused row | Hidden |

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

1. Add a row child object referring directly to existing texture ID 22 and
   the larger emblem rectangle, default hidden. Add no separate icon asset.
   Preserve all existing object bindings and all 15 row sequences.
2. After the ordinary row update, classify the exact quest ID. Hide the badge
   for unknown, ordinary or unused rows. Show red for unfinished progression
   keys and grey for completed ones using actual completion. Active urgents
   take yellow precedence; historical/inactive urgents use grey.
3. Tint the new child red/grey/yellow. Audit
   parent selection colors so highlighting does not recolor the badge.
4. Keep the existing accepted release immutable and stage a separate candidate.
   Verify archive readback, unrelated resource preservation, hook ABI/state,
   packaging and selected-mod collisions before requesting a manual test.

The key/completion decision and existing atlas reuse have concrete paths.
Active urgent menu routing needs more validation. The added drawable object,
resource layout, selection inheritance and clipping are the substantial work.
No safe spare badge slot has been established. This is feasible in principle,
with moderate-to-difficult native UI work; it is not a verified drop-in change.

Manual acceptance would need unfinished/completed/ordinary rows, selection,
both pages and scrolling, list closure/reopening, viewing versus completing
a quest, completion after returning from a quest, active versus old urgents,
multiple urgents, Village/Hub/G-rank coverage and the selected HD/mod set on each
target emulator. The emblem source rectangle is identified; final badge
coordinates and native added-object rendering are not validated.

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

HD `HD_lobby00_BM_NOMIP` texture payload SHA-256:
`5365fe565554b4d339e7ef0d095a19a217515be82a092b88add9453bc647368c`.
The existing Revil `mtf_tex_to_dds` v2.10.9 with `--platform NSW` decoded
copied atlas inputs for inspection; no import, repacking or installed write
was performed.

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
- `work/key-quest-markers/research/rise-native/signboard-icon.json`: native
  sequence properties identifying the emblem rectangle and texture ID.
- `work/key-quest-markers/research/rise-native/quest-counter-emblem-hd-inspection.png`:
  unmodified atlas-region inspection, not a distributable replacement asset.
- `work/key-quest-markers/research/rise-native/urgent-flag-candidate.json`:
  copied resource flag/group correlation with explicit scope limits.
- Fresh exports under `work/damage-numbers/research/1b80ce1a2377/`,
  `e10a22364731/` and `f7b474e483ba/` retain the loader, selector, signboard
  update and separate completion/acknowledgement functions. Original instruction
  comparisons passed with zero mismatches for the defined functions.

No runtime, packaging, save write, installation or activation was tested.
