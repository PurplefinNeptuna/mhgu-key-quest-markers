# Native implementation audit — active r2

## Native classification and attachment

The blanket r1 disable gate and unresolved-state placeholders are removed. r2
installs the parent and row hooks after executable/Forge validation and updates
native badge objects synchronously. Ordinary runtime validation rejects actual
mismatched resources or unavailable records. There is no configuration bypass.

Original main NSO SHA-256:
`b3935415499549adaf4c0e89822831daa175cfd456a7990791c79be3997645ef`.
Build ID: `FB08F1D20FD1204FE7070672777F869B`. Offsets below are main-relative.
Saved Ghidra addresses use image base `0x009c9000`; signatures come from the
original NSO because the imported database contains one changed text byte.

| Path | Verified behavior |
| --- | --- |
| Normal row builder `0x616cb0` | Seven integer/pointer args: UI, selection, page, new flags, other flags, cursor, eight quest pointers. Original runs first. |
| Parent controller `0x54d030` | Two pointers: cQuestList and QuestInfoList. UI at controller +0x54. Its nested calls reach the row builder. |
| Offered urgent IDs | QuestInfoList +0x1104 contains sixteen IDs; +0x1144 is their count. The native counter counts this array for its Urgent category. |
| Native menu construction `0x781e60` | Clears IDs/count, filters selector IDs through availability and actual completion, fills at most sixteen IDs, and clears IDs/count together on removal. Its info base is parent state +0x3c; array/count are parent state +0x1140/+0x1180. |
| Availability `0x54af8c` / `0x3b2174` | The offered set already passed the full availability predicate including rotating flags. The adapter rechecks its scene/quest-flag query at 0x3b2174; neither query completes quests. |
| Completion `0x523da4` | Reads the group-index completion bit in sUserInfo +0x42c. Used for every badge and alternative requirement. |
| New/acknowledgement `0x523d00` | Separate bitfield at sUserInfo +0x100; never treated as completion. |
| Progression storage `0x18979f0` | Pointer to a separate record: u16 Village +0x3e0, Hub/G +0x3e2. |
| Script stage evaluator `0x3d17f8` | Opcodes 0x79..0x7c expose Village tiers 1..10; 0x7d..0x80 expose Hub/G tiers 1..13. The adapter reads these fields and never calls progression writers. |
| Village prerequisite counter `0x3b1a18` | Bit zero means required groups satisfied. Alternative byte 1..11 groups quests into interchangeable requirements. |
| Hub/G prerequisite counter `0x3b1d70` | Total/completed category tier +10, tiers 1..13. Empty key-free G-entry tier 8 has total zero. |
| Group records | sQuest +0xb4 resource, count +0x64, records +0x6c, stride12. ID +4, category/alternative bytes +8/+9. |
| Historical urgent identity | cQuestData +0x10c bit zero agrees with group categories 24..46. Loader 0x37539c reads this u16; resource correlation matches 28 historical urgents among 1,302 records. |
| Native GUI identity/visibility/color | 0x546f28 / 0x56e530 / 0x56e6fc. The setters take four integer arguments and change native visibility/all four vertex colors. |

Key relevance compares the actual progression tier with the quest's native group
category: Village 1..10 and Hub/G tier +10. Category18 is a key-free transition;
category23 is final-stage/no-key. An unfinished old key becomes grey; completion
or a satisfied Village alternative group also makes it grey. Only the quest's
own progression domain must be known; an unknown tier hides an unfinished key.

Yellow requires historical urgent identity, membership in the actual counter's
offered set, current availability and the native prerequisite counter. Completed
urgents are grey. Inactive/old urgents are grey even if unfinished. Multiple offered
IDs are evaluated independently. This handles special Village phases involving
601 and 1005 without guessing a category from stage. Incomplete selector pools,
static rank ranges and the separate +0x200 UI bitfield are not used as availability.

The parent copies only UI identity and sixteen IDs into its local stack. Forge's
SDK TLS token connects that frame to nested row calls on the same native thread.
A borrowed guard restores the previous TLS value on return, including nested calls.
No resource pointer or offers frame survives a menu update. The checked raw SDK
allocation reports failure; Forge's higher-level ThreadLocal::new would panic on
that failure and allocate per-thread heap. This is a narrow verified wrapper gap.

## Resource recipe

Selected HD common archive SHA-256:
`fd8cd4521cb5c5d07e0d1e5e7275aaf5ecbcfd34d20aae2b6f880ab65b22f438`.
The staged selected HD set and the inspected Eden common archive have the same
hash. Folder presence is not evidence of activation. No other inspected selected
package replaces this English common archive; any future collision must be merged.

Baseline internal GUI: `eng\GUI\05_meeting_p\count\counter`, hash `0x22948394`,
77,040 bytes, SHA-256
`95730f3adbaf2c017968cb0079a0caa666de541cecd66ff8ad223e1137b30c5a`.
The bounded recipe accepts only this original GUI. It appends relocated tables,
values and a name, leaving original tables/buffers/unknown bytes intact except
required header words. Header changes: file length +8, counts +48/+52/+56,
table pointers +164/+172/+176/+180; animation pointer +164 relocates as well.
Original row animation 20 gains one object/drawable; all 15 existing sequences
and old object bindings remain intact. Later object roots/next/child indices
shift by one as required.

Row objects originally occupy indices 30..41. The new object is inserted at 42,
local slot 12, ID 21, name `QuestBadge`. Object 39's next sibling points to 42;
the badge is under the main row Null rather than the offset ticket subtree.
Initializers specify X=-28, Y=8, size 24×24, hidden, opaque grey. All 15 badge
sequence records have no animated parameters. Runtime color setters apply state
colors after the ordinary row update; selection/clipping remain acceptance gates.

The existing texture ID 22 references `eng\GUI\99_texture\HD_lobby00_BM_NOMIP`.
Logical source rectangle `(136,344,198,406)` matches the native signboard icon.
The HD 2048² texture corresponds to logical 512² coordinates; the badge's display
size stays 24×24. It does not require scaling/extracting the source texture.
The atlas is external to this common archive and is neither shipped nor replaced.
Its existing HD SHA-256 is
`5365fe565554b4d339e7ef0d095a19a217515be82a092b88add9453bc647368c`.

`rGUI::setData` at `0xb7f988` copies a prepacked geometry byte span from header
vertexOffset/vertexBufferSize. Both remain unchanged. The added standard texture
object has no cached TextureSet extension; arbitrary buffer enlargement would
copy out of bounds. All 114 unrelated resources retain decompressed bytes and
compressed blocks after ARC readback.

Native object access validates holder UI+0x24, instance count +0x298,
instance-pointer table +0xf8, row instances 16..23, object array +0xd8 and slot12.
It checks the native GUI identity query `0x546f28` returns set 5 (selected by the
normal row builder), then validates all eight object IDs and cGUIObjTexture DTI
before any setter. Compiled fixtures exercise this access path. Live sequence
initialization and clipping remain manual acceptance checks; memory readability
alone does not establish ownership.

## ARM and Forge boundaries

forge-rs 1.5.0 is pinned at `d1865b68e9b194eb3eacc8bd71bbf601a5fac63e`.
The loader handshake requests 1.5.0. Native and Rust checks agree on Hook size24,
alignment4, context offset12, ctx_cell offset16 and has_ctx offset20 (native).
Older incompatible loaders are rejected; no loader is bundled or replaced.

The row prologue displaces `e92d4ff0` (PUSH r4-r11,lr), `e24dd004` (SUB sp,sp,#4).
The parent uses the same PUSH followed by `e24dd06c` (SUB sp,sp,#108). Both are
position independent and contain no GE/NZCVQ operations. Each Forge trampoline
must contain its original eight bytes, `e51ff004` literal LDR pc, and target+8.
All seventeen support windows are checked against original executable bytes.
Installation validates both trampolines and redirects, flushes code caches and
publishes active state only after both hooks succeed. The hooks use two 16-byte
slots in Forge's shared 16 KiB CodeMemory pool. No additional hook engine exists.

The row typed callback forwards r0..r3 and three stack arguments. Unicorn runs
the compiled NRO with clobbering original doubles for all sixteen incoming GE
patterns, checks original forwarding and AAPCS callee-saved integer/VFP state.
Direct row callers 0x616bfc/0x618bbc set their own condition flags before use;
0x618cb8 proceeds to an unconditional call. Parent callers 0x782bb0/0x6e3f64
likewise branch/call unconditionally or replace flags with CMP before conditional
use. Their continuations contain no GE-dependent SEL before the next call. No
MSR status writes occur in the compiled plugin; APSR_g is not a prerequisite.

Rollback checks original/owned branch words, including partial publication, and
restores patches in reverse order. Foreign modifications retain ownership.
Disabled Patch snapshots do not write on Drop. Valid original continuations are
published before later checks and remain Forge-owned for process lifetime even
on failure. A failed rollback reports that restart is required. There is no
unloading or hot reload path.

Forge owns lifecycle, logging, allocation, singleton lookup, main-address helpers,
ordinary hooks, patch snapshots and SDK TLS. Immutable DTI lookup fits its wrapper.
Game objects use checked scoped raw reads to avoid long-lived mutable aliases.
The pinned exports lack memory-query/program-ID/cache-flush helpers and native
GUI-holder operations; narrow SVC/native calls fill those gaps. No second renderer
or allocator is introduced. Diagnostics are deduplicated outside hot hooks.

## Automated evidence and manual acceptance

Policy fixtures cover all states, obsolete unfinished keys, alternative groups,
simultaneous urgents, viewing versus completing, missing/conflicting records and
row transitions. Resource checks retain all fifteen original sequences/bindings,
all unrelated resource bytes, atlas references and original cached geometry.

The compiled active parent/row fixture uses native-shaped memory and query/setter
doubles. It verifies actual visibility and packed state colors, original-call
ordering, urgent offer/flag/prerequisite failures, actual completion versus new
indicators, bad GUI identity, invalid context, row reuse, balanced stack/TLS and
unchanged game input records. These checks validate the adapter's execution, not
live rendering or the native game's query results.

No emulator was launched, package installed, save modified or loader replaced by
this implementation. r2 is active DEVELOPMENT, with manual acceptance pending on
English HD Eden and Ryujinx: Village/Hub/G progression, alternative groups,
simultaneous urgents, scrolling, selection, confirmation, reopening, quest return
and progression advancement. Check size, four-pixel gap, clipping and colors.
Disable the old prefix plugin during a trial; preserve accepted releases and
installed rollback payloads. Live resource load and gameplay remain untested.
