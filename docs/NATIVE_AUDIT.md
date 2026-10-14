# Native implementation audit — active r3

## Native classification and attachment

The blanket r1 disable gate and unresolved-state placeholders are removed. r3
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

## Runtime GUI insertion and ownership

No game resource or archive is replaced. The copied HD English common archive
(SHA `fd8cd4521cb5c5d07e0d1e5e7275aaf5ecbcfd34d20aae2b6f880ab65b22f438`)
is only a read-only layout fixture. Its counter GUI has animation20, twelve lookup
objects, fifteen sequences, nine drawables and sixty-three instances.

The normal row builder selects native GUI identity5. The holder uses +0xf8 for
its primary table/count +0x298 and +0x294 for indices beyond that count. Instances
16..23 have a twelve-object index array at +0xd8 and owned root at +0xdc. The root
is cGUIObjRoot (176 bytes), ID1; index1 is its main Null (ID14), and index2 is
cGUIObjTexture (304 bytes), ID12. Their identities, owner links and mappings are
checked before writes. The callback searches a bounded direct-child chain with
cycle/ID-collision checks. Marker ID `0x4b514d33` identifies only our new children.
No game pointer is retained after the callback.

Native root/array/descriptor fields are:

| Field | Role |
| --- | --- |
| Object +0x68/+0x6c/+0x70 | First child, next sibling, parent |
| Object +0x74/+0x78 | Borrowed instance and rGUI context |
| Object +0x50 | Object ID |
| Root +0x9c/+0xa0 | Original animation descriptor and object-index array; unchanged |
| Root +0xa4/+0x80 | Owned draw-cache allocation and command-list start |
| Root +0x8c bits1/2 | Draw-list/transform dirty flags |

New storage is allocated through the cGUIObjTexture DTI's MT allocator
(`MtDti::getAllocator`, main+0x7aa47c; allocator vft +0x20 alloc/+0x34 free).
The DTI's native in-place constructor at vft +0x0c runs only after a checked
304-byte aligned allocation. Failed unpublished objects are destroyed/freed by
scoped guards. Forge's DTI new wrapper returns a long-lived mutable reference;
the checked raw call keeps native ownership and borrowing local instead.

The native texture gets ID22 from the existing rGUI context through lookup
0xb80fd0 / setter0xa4faf0. Its 512² logical atlas and loaded resource are validated.
The display size is 24×24; position is (-28,8) relative to the main row Null.
The source rectangle is `(136,344,198,406)` in HD_lobby00_BM_NOMIP, the white lobby
emblem already loaded by English HD. The size/position fields (+0xb4/+0xb8 and
+0x80/+0x84) are verified by native getters/setters. Position setters use VFP scalar
arguments; checked scalar writes plus native dirty flags avoid a float ABI shim.
All other style, texture, rectangle, visibility and color methods use integer or
pointer arguments. No texture pixels or new atlas are embedded in the NRO.

A new drawable must also fit the root's cached command list. Native root setup
0xa49b28 allocates `(drawableCount * 16 + 8)` bytes when its secondary prefix count
is zero. The unmodified row has nine drawables (152 bytes); the new child needs
168 bytes. The descriptor/counts stay unchanged because native draw walker
0xa494a0 traverses the linked tree, while animation/property updates retain their
original twelve lookup entries. The new child is static and excluded from those
sequence updates, preserving its state color.

The row's virtual cache allocator/free (+0x58/+0x5c, functions 0x540c08/0x540c38)
and root destructor0xa48668 read the same allocator DTI GOT slot0x183ef98.
This proves the replacement cache uses the allocator that will free it. Both
object and cache are fully prepared before publication. Native sibling helper
0xa4844c links the child and supplies its parent; the old cache is released only
after the new one is published. Root/parent dirty flags rebuild sorting, transforms
and commands. Ordinary row/menu visibility is inherited through the native tree.

Root destruction frees its new cache, then recursively destroys children. Texture
child destruction releases native graphics buffers and its MT allocation. No
additional destructor hook, process-lifetime object cache, second renderer or
object-index-array replacement is introduced. A failed allocation leaves the old
root/cache/index arrays valid and destroys unpublished storage.

## ARM and Forge boundaries

forge-rs 1.5.0 is pinned at `d1865b68e9b194eb3eacc8bd71bbf601a5fac63e`.
The loader handshake requests 1.5.0. Native and Rust checks agree on Hook size24,
alignment4, context offset12, ctx_cell offset16 and has_ctx offset20 (native).
Older incompatible loaders are rejected; no loader is bundled or replaced.

The row prologue displaces `e92d4ff0` (PUSH r4-r11,lr), `e24dd004` (SUB sp,sp,#4).
The parent uses the same PUSH followed by `e24dd06c` (SUB sp,sp,#108). Both are
position independent and contain no GE/NZCVQ operations. Each Forge trampoline
must contain its original eight bytes, `e51ff004` literal LDR pc, and target+8.
All thirty-six support windows are checked against original executable bytes.
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

## Runtime report and revised delivery

The user reported Rust Damage Numbers in Plugin UI but absent from Loaded Plugins,
and no quest badges. The installed badge NRO/archive matched r2. The checked Eden
logs show Forge1.5.0; its config filters at ERROR, hiding r2's INFO/WARN messages.
forge-rs's entry macro writes only the version prefix; Forge's list skips empty
names. r3 supplies the full 70-byte metadata record (name at offset6) and retains
Forge logging with failures at ERROR. Vendored pins are unchanged.

The installed HD Project and r2 badge package both replace common_eng.arc. The
inspected Eden source selects the alphabetically first file, letting HD Project's
unmodified counter win. Individual live file ownership was not logged. The user
then explicitly chose native runtime insertion with all ARC files untouched.
r3 implements that choice and contains only the NRO. Remove/disable the old Rust
candidate as a whole so its old ARC cannot remain as a leftover installation file.
Installed packages/settings/saves were read only; no installation or launch occurred.

## Automated evidence and manual acceptance

Policy fixtures cover all states, obsolete unfinished keys, alternative groups,
simultaneous urgents, viewing versus completing, missing/conflicting records and
row transitions. The resource fixture checks the unmodified fifteen-sequence,
twelve-object row and existing HD atlas; the package check rejects any ARC payload.

The compiled fixture uses unmodified twelve-object rows, native-shaped metadata,
query/MT constructor doubles and the game's actual ARM draw walker/root/container
destructors. It verifies object creation, direct-child links, unchanged index arrays,
expanded cache bounds with canaries, actual traversal of visible badges, repeated
updates without additional allocation, native cleanup, failure rollback and every
badge state. Protected quest/completion/progression records remain unchanged.
Pixel rendering and the game's actual query results still require a manual trial.

No emulator was launched, package installed, save modified or loader replaced by
this implementation. r3 is active DEVELOPMENT, with manual acceptance pending on
English HD Eden and Ryujinx: Village/Hub/G progression, alternative groups,
simultaneous urgents, scrolling, selection, confirmation, reopening, quest return
and progression advancement. Check size, four-pixel gap, clipping and colors.
Disable the old prefix plugin during a trial; preserve accepted releases and
installed rollback payloads. Live resource load and gameplay remain untested.
