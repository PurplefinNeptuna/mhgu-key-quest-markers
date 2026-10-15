# r17 game UI colours and quiet logs — READY_TO_DISTRIBUTE

The reported Eden r16 log contains21 false ERROR diagnostics: successful hook
installation, two hook-entry notices and two nine-line snapshots. Its NRO hash
matches the preserved r16 candidate. `research/log-cleanup.json` records the
log/payload correlation. r17 removes snapshots, hook-entry atomics and diagnostic
ID/flag packets entirely. One INFO startup remains; actual hook/resource failures
are reported once per reason from onUpdate. Creation/validation failures retain
their numeric stage on the same line; historical stage explanations follow below.
No successful rows, pages, saves or frames produce warnings/errors.

## Game UI defaults

Defaults now use the exact game UI colour properties: key green `#006305`
(RGB0,99,5) and urgent red `#A30000` (RGB163,0,0). Completed stays `#808080`.
Saved custom RGB values remain untouched; Reset defaults then Save & apply uses
this palette. Classification, settings, native rendering and geometry are unchanged.

See `research/theme-colours.json` for copied input hashes, object/instance IDs,
file offsets and native category/message bindings. `inspect_theme` verifies the
actual pinned resource and executable at build time; no screenshot is sampled.
The base and HD `counter_down` resource are byte-identical. The main objective's
instance colour overrides its shared Message template; the separate Slaying
category red `#CC0000` is not the colour requested here.

The r16 candidate, receipts and support remain unchanged in its versioned tree.
The user accepted the unchanged r17 on Eden/Linux on 2026-10-15 and requested
distribution readiness. The fresh log contains none of the old plugin diagnostic
dumps. The installed NRO matches the candidate SHA-256
`ebc209c1695a38acb3e3b15d198a89e56dba651484c8b968db152f77570dc9e6`. Individual settings,
persistence, ranks, quest states and transitions were not separately enumerated;
Ryujinx/native Switch gameplay remains unconfirmed. See EVIDENCE.json for the
log fingerprint, scoped acceptance and byte-for-byte candidate preservation.
Promotion changes metadata/support only; it does not rebuild or install.

# r16 configurable colours — DEVELOPMENT

The current candidate targets stock Forge 1.5.1 and preserves r15's original
32×32 native emblem, placement, title fitting and quest classification. The
settings panel uses Forge ImGui only; badges still use the game renderer.

`core/src/colors.rs` owns bounded RGB INI parsing, formatting and the tested
mount/write/readback/commit policy. Key/Urgent/Completed preserve badge ordinals
1/3/2. Configuration keys are exactly `key`, `urgent`, `completed`; all values
are six hexadecimal RGB digits and native alpha remains255.

`src/settings.rs` protects UI drafts and load state with a Forge mutex. Three
independent atomic RGB settings are copied once per native row update, avoiding
settings locks or file I/O in game hooks. Editing/resetting marks loading complete
so delayed storage availability cannot overwrite choices. Save publishes only
after write, flush, readback and checked commit all succeed. Failures preserve
the pending and previously applied palettes; prior disk bytes are not guaranteed.

`src/config.rs` reuses Forge's counted save mount and the checked ARM32 SDK file
ABI established by the maintained preferences implementation. Narrow SDK calls
are necessary because stock forge-rs ScopedMount panics on mount failure,
Reader asserts on short reads, Writer ignores short writes, and checked flush
and commit are absent. Handles and filesystem abort context use scoped guards.
Forge's unmount performs its normal additional commit; the plugin checks an
explicit commit before reporting success. Only the plugin's primary INI is used.

Manual r16 acceptance remains NOT RUN. Check picker/hex edits, pending/reset,
Save & apply without scrolling or counter reopening, restart persistence, all
three badge states, request overlap, selection, confirmation, scrolling and menu
transitions. Record Eden and Ryujinx separately. No installation or launch is
part of candidate preparation.

r15's complete release was preserved byte-for-byte at
`backups/accepted/key-quest-markers/r15-before-colours/`; its hashes are adjacent.
Earlier implementation records follow with their original historical scope.

## Earlier development and research

Current Switch build: r15 with upstream Forge 1.5.1. Earlier version claims below retain their recorded scope.

## Key Quest Markers

**r14 — READY_TO_DISTRIBUTE. Original emblem only.** The user accepted the
unchanged r14 NRO on Eden/Linux on 2026-10-15. Ryujinx and native Switch gameplay
remain unconfirmed; individual cases were not separately enumerated.

Native 32×32 badges share an empty request slot and sit four pixels left of a
visible request bubble. Needed keys are orange-red #E74725, active urgents purple
#9B4DCA, and completed/inactive badges grey #808080. Native AutoScale fits long
titles and resets on row reuse. Special Village urgent pairs are included.

The game owns texture children, drawing and cleanup. The plugin references the
already-loaded English HD lobby emblem; it ships one NRO and no game assets or
ARC replacements. Runtime source and the tested NRO were not changed during
promotion. The accepted binary retains its bounded startup/first-page diagnostic
logs; there is no per-frame logging.

- [Installation guide](README.md)
- [Independent builds and packaging](DEVELOPMENT.md)
- [Native ownership, resource and ABI audit](DEVELOPMENT.md)
- [r14 runtime acceptance](EVIDENCE.json)
- [Promotion and archived comparison receipts](EVIDENCE.json)
- [Special-urgent native/Kiranico cross-check](EVIDENCE.json)

The original r14 release is under `build/key-quest-markers/releases/r15/` in
the workspace. Small-emblem comparisons are archived and are not release options.
Historical r9/r11 evidence and original C++/PC releases remain preserved.


## Current release workflow

r14 with the original emblem is READY_TO_DISTRIBUTE, approved on 2026-10-15.
Its NRO is pinned to SHA-256
`79783ac8c236af966160a962218b9d5d36e2088da477cd0f1dc1de88bc09ca65`.
Use `./build.sh package` or the workspace distribution coordinator to package
those approved bytes. Packaging verifies the existing build and test receipts;
it does not rebuild, install or launch. Rebuilding a different runtime requires
a new version and separate validation/acceptance.

Only the original emblem is a supported release. `KQM_SMALL_MARK=1` remains solely
for reproducing historical comparisons; ready-release packaging rejects it.
All small-emblem candidate deliveries are archived with verified hashes recorded
in docs/PROMOTION_R14.json. Preserve original candidate/rollback bytes.

The following sections retain the build procedure and implementation history.

## Development

The independent source folder owns its recipes, Rust sources, vendored sources,
locks, tests and licenses. Supply your own game/resource inputs and tool binaries
through ignored `build.local.json`; supported hashes are in `dependencies.lock.json`.
No build reads installed emulator packages or imports another mod's source.

Use nightly-2026-10-02 with rust-src (the prepared compiler identifies itself as
`rustc 1.101.0-nightly (c36f14571 2026-10-01)`), the pinned cargo-forge converter,
and devkitARM. Python resource/import checks use the standard library and liblz4;
ARM execution fixtures use Unicorn 2.1.4. Tool binary hashes are also pinned.
Registry sources, including build-std resolver inputs, are vendored for offline builds.

Copy `build.local.example.json` to `build.local.json` and set the tools and input
folder. Inputs are copied `main`, `sdk`, a matching Forge NSO named `forge`, and
the selected HD English `common_eng.arc`. Never edit originals.

Run from any directory:

```sh
./build.sh doctor
./build.sh build
./build.sh test
./build.sh verify
./build.sh package
./build.sh export --output /path/to/new/source-folder
```

`prepare` verifies inputs and the read-only native GUI layout fixture. All commands are offline;
there is no download, install, game launch or settings command. Outputs use the
workspace's `build/key-quest-markers/candidates/r15/` and matching `work/` folder,
or the independent checkout's own `build/` and `work/` folders after export.

The workspace coordinator also supports
`python3 scripts/mod_distribution.py package key-quest-markers` for this
explicitly registered DEVELOPMENT candidate. It delegates to the owned builder,
verifies ZIP/runtime/support/checksums, and does not grant release approval.
Run the full coordinator `check` before committing distribution work.

r12 activates the parent and row hooks after executable/Forge validation. The
parent copies offered urgent IDs into scoped Forge SDK TLS; the row callback reads
native progression/completion and creates missing cGUIObjTexture children. They
are attached to each row's main Null, using the game's MT allocation/constructor
and sibling-link functions. The native draw cache grows from 152 to 168 bytes.
The runtime index map grows to thirteen entries with the original twelve
bindings preserved; resource descriptors remain untouched. See the
native audit for exact ownership and the source of these sizes.

The build only reads the copied HD common archive as a layout fixture; it does
not stage any ARC. r1/r2/r3/r4/r5/r6/r7/r8/r9/r10/r11 and the original C++/PC releases remain preserved. r12
retains the 70-byte named plugin metadata and reports failures at ERROR.
No command installs, launches, edits saves or changes emulator settings.

Forge owns lifecycle/logging, allocation for plugin data, hooks, patches, singleton
lookup, main addresses and SDK TLS. DTI lookup uses its high-level wrapper. The
bindings do not expose the native GUI hierarchy or MT allocator/constructor
operations needed for game-owned children; checked raw native calls fill that gap.
Using Forge malloc for these objects would mismatch their native destructors.

Texture construction uses the checked native function at main+0xa4f60c after MT
allocation. MHGU’s Texture DTI has no placement virtual; the generic forge-rs
instantiate wrapper cannot be used for this class.

The compiled adapter fixture calls forge_onInit, installs both hooks and enters
their patched game addresses before creating badges. Supporting signature order
is independent of each trampoline’s target snapshot.

The r8 runtime log confirmed both hooks and visible red/grey decisions. Its
incorrect native mask mode came from reading immediate INIT_PARAM kinds 17/18
as byte-section offsets. r9 decodes those fields directly and copies the actual
Tex_icon style, including Mask=0. The unchanged r8 NRO reproduces a mask-pass
entry in the regression; the r9 fixture executes native colour draw and quad
generation with GPU commands doubled. The user confirmed r9 works on Eden/Linux; r10 was rejected before drawing and r11 was subsequently user-confirmed working (docs/RUNTIME_R11.json).


r11 reads native request visibility after the original builder and positions the
same 24×24 child at X=369, or X=337 when the bubble is visible at X=365. The title
gets native AutoScale and width303/271 (X=62 plus a four-pixel gap); ordinary or
unresolved rows restore width355, height38 and AutoScale=false. The request mark
is read-only. Title Size/AutoScale/AutoWrap calls use their audited integer/pointer
ABIs; setting text dirty bit16 invalidates cached glyph layout. Invalid request
bindings hide only the affected badge and restore its valid title before returning.

The compiled fixture also executes native AutoScale dispatch and clamp arithmetic
with supplied glyph bounds; glyph scaling and GPU submission remain doubles.
It checks short/long titles, both slots, per-row binding failures and early-return
restoration. Preserve the accepted r9 runtime evidence in docs/RUNTIME_RESULTS.json.


r10 failed its new title binding: source object ID6 declares cGUIObjMessage, CRC
0x2fb82eae, size352. r10 incorrectly required the cGUIObjText subclass, size384.
Fresh Eden logs show classification with zero GUI flags and error128. The unchanged
r10 binary reproduces rejection against the corrected fixture. r11 uses Message
DTI and its native getDTI at0xa56ab8; inherited Size/AutoScale APIs remain unchanged.
Fixtures derive title CRC from the original GUI record, use the real Message
getDTI instructions and reject a substituted Text subclass with otherwise valid
ID and ownership. No rendering priority changes are part of this correction.


r12 keeps the accepted r11 binding/renderer and enlarges only the badge quad to
32×32. Its free-slot X=365 preserves the slot centre; X=329 leaves four pixels
before a bubble at365. Y=3 lifts the emblem within the white band, versus r11's
24px/Y=8. The full quad ends at35 within the native 40px row envelope. Title
widths become299/263 with the same four-pixel gap and restoration rules. The
screenshot shows r11's visible emblem lower and smaller than the bubble; r12's
appearance still requires a new in-game check. No extra hooks, objects, resources,
map/cache capacity or renderer changes are needed for this size adjustment.


### r12-small comparison variant

Only the source UV and build identity differ from r12. The smaller outlined top
emblem occupies logical `(342,0,372,30)` in texture22, equivalent to physical
`(1368,0,1488,120)` in the 2048² HD atlas. It is drawn at the same 32×32 size.
Native compiled fixtures check the rectangle setter, stored UV and all four
half-texel-inset UV corners, along with the unchanged layout and cleanup cases.
The original r12 delivery remains untouched; its complete file hashes are in
`docs/R12_COMPARISON.json`. Independent source exports and output paths use
`r12-small`, so neither build nor package commands overwrite original r12.


### r13: special Village urgents, both emblem builds

Default commands build/test/package r13 with the original emblem. Prefix the same
commands with `KQM_SMALL_MARK=1` for r13-small. This is a build-time selection;
there is no runtime option or config. Separate work/build paths, metadata names
and version receipts prevent either comparison candidate overwriting the other.
The pinned converter does not accept Cargo feature arguments, so build.rs emits
a checked cfg from this one environment flag. Both binaries share all classifier
and native adapter source; only UVs, plugin name and diagnostic version differ.

Run both `./build.sh build` and `./build.sh test` before packaging each variant.
Use `./build.sh package` for the small variant; it invokes the same complete
candidate validator. The workspace coordinator packages/checks the default r13
record. Independent exports support both commands with the same flag.

Groups47..54 are the four special encounter pairs listed Urgent on Kiranico.
They lack the rank-up urgency bit. They use the full native counter availability
predicate (scene flag plus per-record enabled bit), rather than the rank-up
offered set or rank-key prerequisites. Completion
of either record in a native family makes both grey. Detailed resources, native
functions, live URLs and limits are in docs/SPECIAL_URGENTS.json. No new hooks,
resources, pointers, native signatures or save writes are introduced.


### r14: purple active urgents

The default and `KQM_SMALL_MARK=1` commands now build r14 and r14-small.
Active urgent badges change from yellow #FFD239 to purple #9B4DCA, packed as
0xffca4d9b so little-endian bytes are155,77,202,255. The internal state remains
ordinal3 and is named Purple in core and diagnostics. Native request objects,
key/grey colours, classification and layout are unchanged. Existing exact-RGBA
and compiled native quad checks validate the new colour in both builds.
Original r13/r13-small packages remain byte-for-byte preserved.


## Native implementation audit — r12 badge size and alignment

### Native classification and attachment

The blanket r1 disable gate and unresolved-state placeholders are removed. r12
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

### Runtime GUI insertion and ownership

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

### ARM and Forge boundaries

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

### Runtime report and revised delivery

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

### Automated evidence and manual acceptance

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

### r3 runtime failure and r4 correction

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

### r4 runtime failure and r5 correction

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

### r5 startup failure and r6 correction

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

### r6 freeze and r7 object-map lifetime correction

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


### r7 invisible report and r8 diagnostic build

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

### r8 runtime trace and r9 material correction

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


### Confirmed working baseline — r9, 2026-10-15

The user confirmed: “ok then save this knowledge somewhere in this project
because this is working, nice job”. The installed NRO matches the r9 candidate
SHA `331adf1f4ec406c5da9d1b661ebf85f881a67852d6dacde1d0943486ab80e576`.
The fresh Eden log identifies MHGU 1.4.0, Forge1.5.0, r9 initialization and both
hook entries. Visible success is established by the user report. The snapshot
ends partway through a diagnostic line, so it proves no clean-shutdown result.
Full hashes, snapshot identity and coverage limits are in [RUNTIME_RESULTS.json](EVIDENCE.json).

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


### r10 request-slot placement and title fitting

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


### r10 Eden failure and r11 correction — 2026-10-15

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


### r11 acceptance and r12 badge geometry — 2026-10-15

The user confirmed r11 works and supplied a screenshot showing red/grey badges,
request bubbles and a completion ribbon. The installed NRO matches r11 SHA
`12b56381c6b1aee0934bd1c5a3b0128942a9e088d57cacf651a3291d4adb7e48`;
the fresh Eden log identifies r11, both hooks and visible native GUI flags.
Details and preserved screenshot/log hashes are in [RUNTIME_R11.json](EVIDENCE.json).
This accepts the binding correction on Eden/Linux without exhaustive coverage.

The screenshot's visible red mark is about32px square, versus a request bubble
about39×37px. Its white row spans Y222..270 while the red pixels span231..263,
putting the visible centre slightly low. These are screenshot pixel measurements,
not native GUI units. r12 uses the native request slot's 32×32 quad size, raised
to row-local Y=3. The full quad fits Y3..35 within the native 40px row envelope;
its visible emblem content remains inset by the atlas shape. Exact pixels and
clipping still require a manual r12 trial.

Free-slot X365..397 matches the request slot width. With a bubble, X329..361
preserves four pixels before X365. The title widths become299/263 rather than
303/271. Existing geometry fixtures verify all four native quad vertices, both
positions, source UVs, colours, title sizing/restoration and row-height bounds.
The accepted r11 payload is unchanged; no new objects, cache/map capacity or
hooks are introduced. Layer priority and native Message bindings stay intact.


### r12-small atlas comparison — 2026-10-15

This variant preserves r12 geometry and native calls, changing the source UV
from `(136,344,198,406)` to `(342,0,372,30)` on existing texture22. The new region
is the smaller outlined top emblem, matching the 32px orange preview. In the
2048² HD atlas the crop is `(1368,0,1488,120)`; coordinates divide by four for
the native 512² logical atlas. Its black outline remains in the source pixels.
The compiled native fixture checks the UV setter and stored rectangle, then
quad UV corners at X342.5/371.5 and Y0.5/29.5. The quad remains 32×32 at Y3
and X365/329. No resources, ownership, hooks, title fitting or classification
change. Original r12 delivery hashes are retained in `R12_COMPARISON.json`.
Actual sampling and visual preference require the user's in-game comparison.


### r13: special encounter urgent pairs — 2026-10-15

The earlier historical-urgent correlation covered only rank-up groups24..46.
It omitted groups47..54, whose eight records Kiranico labels Urgent even though
cQuestData +0x10c bit0 is clear (flags0x300/0x308). The actual category-to-family
getter0x3b21f0 reads main+0x162a8a0; first eight words are1,1,2,2,3,3,4,4.
Native selector counter0x3b85d8 uses that getter and the repeat-category predicate
0x3b2214 when distinguishing first-run/repeat versions. The patch limits this
pair policy to47..54, leaving other family-like categories outside the feature.

The native counter availability predicate0x54af8c, called with category0xff and
null menu context, checks the scene query0x3b2174 and a 51-entry quest enabled-bit
table. All eight
special IDs occupy entries0..7 of the original table at0x162cde4, with stride8.
The enabled bits are read at native flag owner+0x35d4; scene availability alone
is insufficient to distinguish first-run/repeat offers. The separate rank-up
pool and rank-key prerequisite count are not the special encounters' activation
requirements. r13 calls that full three-argument availability predicate and uses
actual completion0x523da4 plus
completion of either record in the same family. Available unfinished unsatisfied
pairs are yellow; completed/satisfied pairs and unavailable records are grey.
No current rank is inferred from the viewed star page.

The adapter still requires valid UI, metadata, progress and parent offer context.
Rank-up quests keep both their urgent flag and offered/prerequisite checks.
The full availability predicate already has a checked signature; its new call
uses the audited three-integer ABI. No hook sites, allocation or renderer change.
Static ARM cases
exercise all eight real ID/category/flag records, missing offer context, availability,
independent pair completion and native drawing/cleanup in both emblem builds.
See SPECIAL_URGENTS.json for hashes, URLs, user-report evidence and runtime limits.


### r14: urgent colour — 2026-10-15

Only the active urgent colour changes: native packed RGBA0xffca4d9b gives
bytes155,77,202,255 (#9B4DCA). The badge state remains ordinal3, now named Purple
in source and startup diagnostics. Both original/small emblem builds use the
same mapping. Needed keys remain #E74725 and completed/inactive badges #808080.
The game's yellow request objects are untouched. r13 special-urgent semantics,
all native calls, hooks, row geometry and ownership remain unchanged. Existing
exact-byte host assertions and every coloured native quad check cover this change.


## Fixtures

Core policy fixtures cover all badge states, alternatives, obsolete unfinished
keys, simultaneous urgents, viewing versus completing and conflicting records.
The hook harness executes production ownership-aware rollback with Forge doubles.

`resource.py` only reads the copied native GUI/atlas layout and rejects corrupt
bounds. It checks that no ARC is staged. The fifteen original row sequences and
twelve-object index layout are inputs, and remain unchanged at runtime.

`arm.py` runs the compiled seven-argument pass-through callback in all sixteen GE
patterns, checks callee-saved state, named 70-byte metadata with canaries, the
1.5.0 request and native Hook declarations, and retains caller continuation code.

`native_adapter.py` runs the compiled parent/row/GUI adapter with native-shaped
memory, MT constructor/query doubles and real game ARM draw-list/destructor code.
Its twenty-one cases cover states, progression evidence, both holder tables, missing
context, bad objects, object/cache allocation failure and repeated insertion.
It checks colors, pose/size, unchanged index arrays and saved records, actual native
draw traversal, cache canaries, root/child cleanup and balanced stack/TLS.

The GPU commands are doubles. No fixture launches Forge or establishes actual
in-game pixels, clipping or gameplay acceptance.
