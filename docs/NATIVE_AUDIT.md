# Native implementation audit — r11 Message binding correction

## Native classification and attachment

The blanket r1 disable gate and unresolved-state placeholders are removed. r11
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
| Object +0x74/+0x78 | Borrowed cGUI owner and rGUI context |
| Object +0x50 | Object ID |
| Root +0x9c/+0xa0 | Original descriptor and live object-index map (first twelve bindings preserved) |
| Root +0xa4/+0x80 | Owned draw-cache allocation and command-list start |
| Root +0x8c bits1/2 | Draw-list/transform dirty flags |

New storage is allocated through the cGUIObjTexture DTI's MT allocator
(`MtDti::getAllocator`, main+0x7aa47c; allocator vft +0x20 alloc/+0x34 free).
The standalone native constructor at main+0xa4f60c runs only after a checked
304-byte aligned allocation. The Texture DTI has three virtual slots; +0x0c is
null, so forge-rs's generic instantiate wrapper does not apply to this game class. Failed unpublished objects are destroyed/freed by
scoped guards. Forge's DTI new wrapper returns a long-lived mutable reference;
the checked raw call keeps native ownership and borrowing local instead.

The native texture gets ID22 from the existing rGUI context through lookup
0xb80fd0 / setter0xa4faf0. Its 512² logical atlas and loaded resource are validated.
The display size is 24×24. r9 used (-28,8) relative to the main row Null;
r10 uses (369,8), or (337,8) when the native request bubble is visible.
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
additional destructor hook, process-lifetime object cache or second renderer is
introduced. The instance-owned index map grows from twelve to thirteen entries. A failed allocation leaves the old
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
All forty supporting windows are checked against original executable bytes.
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
names. The candidate supplies the full 70-byte metadata record (name at offset6) and retains
Forge logging with failures at ERROR. Vendored pins are unchanged.

The installed HD Project and r2 badge package both replace common_eng.arc. The
inspected Eden source selects the alphabetically first file, letting HD Project's
unmodified counter win. Individual live file ownership was not logged. The user
then explicitly chose native runtime insertion with all ARC files untouched.
The candidate implements that choice and contains only the NRO. Remove/disable the old Rust
candidate as a whole so its old ARC cannot remain as a leftover installation file.
Installed packages/settings/saves were read only; no installation or launch occurred.

## Automated evidence and manual acceptance

Policy fixtures cover all states, obsolete unfinished keys, alternative groups,
simultaneous urgents, viewing versus completing, missing/conflicting records and
row transitions. The resource fixture checks the unmodified fifteen-sequence,
twelve-object row and existing HD atlas; the package check rejects any ARC payload.

The compiled fixture uses unmodified twelve-object rows, native-shaped metadata,
query/MT allocation and original-row factory/property doubles and the game's
actual ARM animation and texture constructors, texture style/rectangle/color/
visibility setters, cache allocator/free, child-link helpers, draw walker and
root/container/texture destructors. It verifies object creation, direct-child links, preserved original bindings in expanded index maps,
expanded cache bounds with canaries, actual traversal of visible badges, repeated
updates without additional allocation, native cleanup, failure rollback and every
badge state. Protected quest/completion/progression records remain unchanged.
Pixel rendering and the game's actual query results still require a manual trial.

No emulator was launched, package installed, save modified or loader replaced by
this implementation. The user confirmed r9 works on English HD Eden/Linux;
individual cases and Ryujinx remain unconfirmed: Village/Hub/G progression, alternative groups,
simultaneous urgents, scrolling, selection, confirmation, reopening, quest return
and progression advancement. Check size, four-pixel gap, clipping and colors.
Disable the old prefix plugin during a trial; preserve accepted releases and
installed rollback payloads. See RUNTIME_RESULTS.json for the scoped r9 confirmation.

## r3 runtime failure and r4 correction

The reported Eden r3 trial reached the row callback but returned GUI validation
error64 before creating a badge. The installed NRO matched r3, its folder contained
no ARC, and the installed HD common archive matched the copied input.

The wrong check compared object+0x74 with the animation instance. Native function
0xa38828 instead passes instance+0x6c as the first argument to 0xa38bc0; the latter
writes that cGUI owner to every child+0x74. r4 compares and copies this owner.
The regression fixture executes both original ARM functions with distinct GUI and
animation addresses, using the original counter object records for hierarchy/IDs.
Factories, property initialization and GPU calls remain doubles.

Future row validation failures log their precise guard stage outside the hot hook.
This correction passed the owner regression. The later r4 trial passed these row
checks but failed during object creation, as described below. Neither r3 nor r4
has gameplay acceptance.

## r4 runtime failure and r5 correction

The fresh Eden trial used the exact r4 NRO and reached error16 (object/cache
creation), with no row validation error. The cGUIObjTexture DTI vtable at
main+0x178ff90 contains destructor0x32c, destructor0xa568a8 and factory0xa4f550;
the following word at +0x0c is zero. r4 required that nonexistent placement slot
before allocating anything, so it could not create a badge.

r5 retains checked MT allocation and calls the actual placement constructor
0xa4f60c with storage in r0. Both that function and its Polygon base constructor
0xa4d0d8 have checked instruction windows. Native texture constructors, setters,
cache allocation/free and texture destructors now execute in the compiled fixture.
DTI +0x0c stays null, reproducing r4's failure and allowing r5 to proceed.
Creation errors report a bounded stage number outside the hot hook. No archive,
installed payload, emulator setting or save is changed by preparation.

The real GPU renderer and live current-progression queries remain manual gates.
The Eden report also contains a later unmapped-memory message during shutdown;
no evidence here attributes that separate message to this failed creation path.

## r5 startup failure and r6 correction

The latest Eden log used the exact r5 NRO and reported “Forge hook failed;
restored originals” during initialization. No row or creation callback ran.
Adding constructor signature windows at the beginning of SIGNATURES shifted the
table, but the installer still compared the first hook trampoline with
SIGNATURES[0] and the second with SIGNATURES[1]. Those were constructor bytes,
so the installer rejected valid hooks and rolled them back.

r6 compares each trampoline with its own Patch original-byte snapshot. The full
signature table is still validated before any write; adding/reordering supporting
windows cannot change which original bytes a hook must preserve.

The compiled fixture now starts at forge_onInit, supplies the native 20-byte Patch
and 24-byte Hook return ABIs, runs the real installer, enters both patched game
addresses, and then performs native texture creation, setters, drawing traversal
and cleanup. It never forces ACTIVE. Additional cases corrupt the first/second
trampoline independently and verify both target bytes are restored. The unchanged
r5 NRO fails this startup regression with the same error as the user’s log; r6
passes. Forge/kernel allocation/query operations, original menu builders, native
quest query results and GPU commands remain doubles. Live pixels/gameplay remain
manual acceptance gates. No installed mod or emulator configuration was changed.

## r6 freeze and r7 object-map lifetime correction

The preserved Eden r6 log reports an unmapped Read32 and null instruction fetch.
The return address maps to main+0x5457c8 in native GUI resource cleanup0x5456e4;
r7 (the register) is 12, identifying the first slot beyond the original map.
Native count getter0xa38ffc calls tree traversal0xa47d2c and adds the root. It
therefore returns 13 after child insertion, while r6 kept only twelve pointers.
The cleanup loop then dereferences map[12] as an object. The unchanged r6 NRO
reproduces this fault at index12 in the compiled fixture.

r7 allocates a thirteen-pointer map with cGUIInstance's MT allocator (alloc1 at
vft+0x1c). The allocator class is verified from the shared GOT slot0x18422b4,
used by original map construction0xa38bc0 and destruction0xa38b58/0xa38828.
The first twelve pointers are copied without reordering; slot12 holds the new
texture. Both instance+0xd8 and root+0xa0 are published before linking the child,
then the old map is freed with the same allocator class. Native instance cleanup
frees the replacement after destroying the root and its children. Unpublished
map allocations use scoped rollback alongside the badge and cache allocations.
The resource descriptor still names twelve original sequence-bound objects; no
shared descriptor, ARC, sequence or original object binding is changed.

The fixture executes the actual crashing cleanup function and the actual
animation clear function, with distinct map and texture allocator doubles. It
checks map allocation failure, preserved original bindings, repeated updates,
both aliases, and destruction of all new allocations. The other three callers of
the native tree count (0x546360,0x547a14,0x548438) likewise iterate the live map;
none needs a new object's resource property descriptor. Live GPU pixels and
progression queries still require manual acceptance.


## r7 invisible report and r8 diagnostic build

The fresh Eden log ending 2026-10-15 06:56:17 +0700 has no native badge
rejection or guest exception. The installed NRO matches r7:
`0bc68c1053cfee62a442645d5144e87f6c15e455f218cd495168e19c63f68d36`.
The user reported no icons. This does not establish successful hook execution,
classification, geometry emission or visible pixels. The shutdown unmap is not
attributed to the badges.

r8 retains r7's functional insertion/classification and adds bounded diagnostics;
it is not a confirmed visibility repair. Initialization records successful hook
installation. Parent/row entry bits and two immutable scalar snapshots are
published in callbacks and logged outside them in forge_onUpdate. A snapshot
records eight quest IDs, group categories, urgency flags, badge decisions, native
visibility flags and both progression tiers. It retains no pointers. Release/acquire
publication prevents partial records; each snapshot is claimed once for logging.
The first classified page and first page with a visible decision are independent,
so an ordinary first page cannot suppress the useful key-page record.

DEVELOPMENT diagnostic lines intentionally use ERROR severity to pass the user's
existing error-only Forge filter, with an explicit diagnostic label. No loader
configuration is changed. ARM fixtures now run with that same ERROR threshold and
verify hook entries, exact scalar records and absence of per-frame repeated logs.
They still do not execute the actual GPU geometry/draw path or establish pixels.
The next manual trial must open a page containing a key and retain its Eden log;
these records will separate absent hooks, all-hidden decisions and a rendering
failure before another functional change is proposed.

## r8 runtime trace and r9 material correction

The user's completed r8 Eden run (log mtime 2026-10-15 07:15:34 +0700)
confirmed installation, both hook entries, Village stage4 and Hub/G stage2.
Quest402 received grey (badge2); quest409 received red (badge1), both with the
native Visible bit set. No guest exception or badge rejection was logged.
Installed r8 SHA: `d06c32389f39f2e227d9e7fad4dc926c5d07b26ac525f6d721a152d8e8aa4d4d`.
This establishes callback/classification execution, not visible pixels.

The source of the incorrect material was the read-only GUI decoder. It treated
INIT_PARAM types17/18 as offsets into kv8. The native loader at main+0xb7f988
leaves these two immediate types unrelocated. The dispatcher at 0xb344f4 reads
kind17 as the low byte of value (bool), and kind18 as the value word itself.
Only kind3 references kv8; kinds1/2/7 and others use kv32, while kind4 uses kv128.
The first kv8 bytes happen to be 1, masking the parsing error.

The original Tex_icon's actual settings and r9's native setters are:

| Setting | Actual value | Setter (main-relative) |
| --- | --- | --- |
| BlendState | 1 | 0xa4dc24 |
| ControlPoint | 0 (top-left) | 0xa4a9f4 |
| FixFrame | 0 | 0xa47a94 |
| Mask | 0 (ordinary colour drawing) | 0xa4dca0 |
| Priority | 2 | 0xa47a04 |
| ReferencePosition / Rotation | 1 / 1 | 0xa4aa24 / 0xa4aa5c |
| ReferenceScale X/Y/Z | 3 / 3 / 3 | 0xa4aa94 / 0xa4aac8 / 0xa4aafc |
| Reverse | 0 | 0xa4dc54 |
| SamplerState | 0 | 0xa4fa5c |

r8 incorrectly used Mask1, a centre anchor, fixed-frame mode, scale mode1 and
horizontal reversal. Its unchanged NRO reproduces entry from the real native
prepaint function 0xa4e628 into mask setup 0xb375c4. This reproduction bypasses
the style-table assertion, so it checks the native dispatch rather than merely
comparing constants. No r8 package/receipt is overwritten.

r9 corrects the decoder and setter values. Resource checks assert the actual
immediates; the compiled adapter's setter arguments must agree with those decoded
source properties. The fixture now executes native prepaint dispatch, Texture
Draw0xa4fc9c, quad generation0xa4feb4 and postpaint through the real draw walker.
GPU allocation/binding/submission are doubles; bounding-box calculation is marked
already complete to isolate material dispatch. The fixture rejects every native
mask-pass entry and checks emitted 24x24 colour vertices, all four opaque state
colours and logical atlas UVs. With top-left anchoring, row-local X=-28 plus
quad X=0..24 leaves the requested four-pixel gap.

The host fixture does not establish actual clipping, world transforms or visible
GPU pixels. The later user-confirmed r9 Eden success is recorded below;
no emulator launch, install, archive replacement, settings or save change by the agent is part
of this repair.


## Confirmed working baseline — r9, 2026-10-15

The user confirmed: “ok then save this knowledge somewhere in this project
because this is working, nice job”. The installed NRO matches the r9 candidate
SHA `331adf1f4ec406c5da9d1b661ebf85f881a67852d6dacde1d0943486ab80e576`.
The fresh Eden log identifies MHGU 1.4.0, Forge1.5.0, r9 initialization and both
hook entries. Visible success is established by the user report. The snapshot
ends partway through a diagnostic line, so it proves no clean-shutdown result.
Full hashes, snapshot identity and coverage limits are in [RUNTIME_RESULTS.json](RUNTIME_RESULTS.json).

Preserve this native GUI implementation: the game's own cGUIObjTexture objects,
row hierarchy, loaded HD atlas and native renderer provide the badges. Forge
supplies lifecycle, hooks, logging, singleton/DTI lookup and supporting APIs.
There is no ImGui or forge_onImGuiFreeRender drawing, ARC replacement or shipped
extracted emblem. For this row, Mask0 is the normal colour path; the immediate
INIT_PARAM kinds17/18 must not be decoded as kv8 offsets. Preserve the expanded
13-entry object map and 168-byte draw cache with native allocation/cleanup.

This is confirmation of working r9 badges on Eden/Linux, with individual rank,
colour and transition checks unenumerated. It grants no Ryujinx/native Switch
acceptance or distribution promotion. Keep r9 runtime/ZIP bytes unchanged; future
runtime changes need a new candidate version. Its packaged pretrial validation
is a historical snapshot; this record is the later manual evidence.


## r10 request-slot placement and title fitting

The unchanged English HD resource has request Texture ID20 at lookup index3,
position (365,2), size32×32; title Message ID6 at index4, X=62, size355×38. Both are
children of the same row Null. The native builder calls 0x56e530/0x545630 to set
the request object's visibility immediately through 0xa47950; +0x54 bit0 is
therefore the current displayed request state after the original returns.

The child stays 24×24 at Y=8. X=369 centres it in the free 32px request slot;
X=337 ends at361, leaving four pixels before the request bubble. Title widths
303/271 leave four pixels before these respective positions. No request object,
resource animation, original map binding, colour classifier or progression record
is modified. Shared identity is possible: copied quest107, Another Pack Attack,
is native key category1 with mRequestVillage=8, which the builder's 0x11e0 mask
shows as a request bubble.

r10 incorrectly required Text size384. r11 validates the resource's Message
size352, Texture size304, IDs, native types, owning cGUI,
resource and common parent. Handles remain synchronous callback locals. Existing
badges are hidden and valid titles restored before classification can fail.
A bad request/title binding skips only its decoration and reports error128 once;
a valid title is restored even when its request binding is invalid.

Verified native title operations (main-relative):

| Operation | Address / contract |
| --- | --- |
| AutoScale setter | 0xa53348, two integers, preserves all but +0xf0 bit0 |
| AutoWrap setter | 0xa53324, two integers, +0xf8 bits18..19; enum0 disables wrapping |
| Size setter | 0xa53528, object and float2 pointer, writes +0xc8/+0xcc |
| Native FontSize invalidation tail | 0xa5350c, ORs +0xf0 bit16 |
| Cached-layout refresh | 0xa53aa8 checks bit16, calls virtual+0x70, then clears it |
| Message type getter (r11) | 0xa56ab8; replaces the inappropriate Text getter0xa56b4c |

Size and AutoScale setters do not invalidate cached glyphs. The adapter sets the
same bit16 as FontSize after an actual layout change. It changes neither font,
font size, colours nor title strings. Restore uses width355, height38, AutoScale=0
and AutoWrap=0, matching the hashed source. Badge movement marks native transform
state dirty. These six added supporting windows are checked before hook installation.

ARM fixtures run the native AutoScale flag dispatch at 0xa42374..0xa423cc and
complete clamp function0xa449c0, using supplied glyph bounds. An 80px title stays
at scale1; a 500px title fits width303/271, without enlargement. The final glyph
scaler and GPU submission are doubles. Fixture results establish dispatch,
geometry and restoration, not font measurement, visible clipping or GPU pixels.
The r9 acceptance record remains historical; r10 needs its own manual trial.


## r10 Eden failure and r11 correction — 2026-10-15

The tested installed NRO matched r10 SHA
`df8099a24b8c4f33e033b8eb99d59972cee1899569ce724ea3b587e8baeba1a9`.
Fresh Eden logs at59.07s show both hooks, correct key/urgent decisions, every
GUI flags snapshot zero, and error128 (request/title binding invalid). No badge
objects reached rendering. The copied source GUI's object34/row binding4/ID6
has type CRC800599726 (`0x2fb82eae`), cGUIObjMessage, size352. Its derived
cGUIObjText class has a different CRC826240196 (`0x313f6cc4`) and size384.
Exact-type validation in r10 therefore rejected the genuine title.

The old fixture forced a Text type onto that resource and missed the rejection.
r11 reads the source class CRC and resolves its own factory DTI accordingly.
Message's actual getDTI instructions at0xa56ab8 run against their GOT input
main+0x183f0b0. The saved Message DTI and original vtable confirm shared Size,
AutoScale, AutoWrap, font invalidation and cached-layout refresh operations.
Those property fields and setters did not need changing. Only the required
class/size and its supporting type-getter signature change in the native adapter.

The unchanged r10 NRO reproduces all-eight-row rejection and creates no badges
against the corrected fixture. A new negative fixture gives ID6 valid ownership
but substitutes the Text subclass; r11 must reject that one row while other badges
continue working. Original r9 and r10 payloads are preserved; r11 is a new
DEVELOPMENT candidate, requiring separate manual acceptance. This evidence
establishes the pre-render rejection, not the absence of every possible later
clipping or layering problem.
