# Key Quest Markers: development and research

**Current state.** r20 DEVELOPMENT candidate, gameplay NOT RUN, at `build/key-quest-markers/candidates/r20/`. It sizes the row's object map and draw cache from the live tree, so another mod can add children to the same quest rows; badges and settings are unchanged. r19 is the gameplay-accepted build for quest badges on Eden, on the user's report (see `EVIDENCE.json`), kept at `build/key-quest-markers/candidates/r19/`, with its release preserved in `backups/accepted/key-quest-markers/r19-before-tree-sizing/`. Ryujinx and native Switch gameplay remain unconfirmed. DISTRIBUTION.json is authoritative; EVIDENCE.json holds exact results, with the pre-compaction `docs/*.json` records under `historical`.

The mod draws badges with the game's own GUI objects: native cGUIObjTexture
children on each quest row, the already-loaded lobby emblem and the native
renderer. Forge supplies lifecycle, hooks, logging, singleton/DTI lookup and
supporting APIs. There is no ImGui badge drawing, ARC replacement or shipped
artwork; the package is one NRO. The HD Project is optional (user-confirmed on
2026-10-15); the copied English HD archive is only a build-time layout fixture.

## Build and validate

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

`prepare` verifies inputs and the read-only native GUI layout fixture. All
commands are offline; there is no download, install, game launch or settings
command. Outputs use the workspace's `build/key-quest-markers/candidates/r18/`
and matching `work/` folder, or the independent checkout's own `build/` and
`work/` folders after export. The target keeps PIC and adds `-nostartfiles` and
`-Wl,-z,text`; the final NRO verifier rejects DT_TEXTREL/DF_TEXTREL.

The workspace coordinator packages the registered record with
`python3 scripts/mod_distribution.py package key-quest-markers`. It delegates to
the owned builder, verifies ZIP/runtime/support/checksums, and does not grant
release approval. Run the full coordinator `check` before committing
distribution work. A different runtime needs a new version and separate
validation and acceptance.

`KQM_SMALL_MARK=1` builds the archived small-emblem comparison variant
(`-small` version suffix, separate build/work paths). It exists only to reproduce
historical comparisons; ready-release packaging rejects it. The pinned converter
does not accept Cargo feature arguments, so build.rs emits a checked cfg from
this one environment flag.

## Badge policy and colours

| Badge | Ordinal | Default | Meaning |
| --- | --- | --- | --- |
| Key | 1 | `#006305` (RGB 0,99,5) | Needed key quest for the current progression tier |
| Completed | 2 | `#808080` | Completed, satisfied or no-longer-relevant quests |
| Urgent | 3 | `#A30000` (RGB 163,0,0) | Offered, available, unfinished urgent |

The defaults are the exact game UI colour properties. See
`research/theme-colours.json` for copied input hashes, object/instance IDs, file
offsets and native category/message bindings; `inspect_theme` verifies the
pinned resource and executable at build time. The base and HD `counter_down`
resource are byte-identical. The main objective's instance colour overrides its
shared Message template; the separate Slaying category red `#CC0000` is not the
requested colour. Native alpha stays 255.

Groups 47..54 are four special Village encounter pairs that Kiranico lists as
Urgent. They lack the rank-up urgency bit and use the full native counter
availability predicate instead of the rank-up offered set. Completion of either
record in a family makes both grey. Native details are under "Native reference".

## Settings

Configuration keys are exactly `key`, `urgent`, `completed`; values are six
hexadecimal RGB digits. Saved custom values are never rewritten; Reset defaults
then Save & apply uses the game palette. The settings panel uses Forge ImGui only.

`core/src/colors.rs` owns bounded RGB INI parsing, formatting and the tested
mount/write/readback/commit policy. `src/settings.rs` protects UI drafts and load
state with a Forge mutex. Three independent atomic RGB settings are copied once
per native row update, avoiding settings locks or file I/O in game hooks.
Editing/resetting marks loading complete so delayed storage availability cannot
overwrite choices. Save publishes only after write, flush, readback and checked
commit all succeed. Failures preserve the pending and previously applied
palettes; prior disk bytes are not guaranteed.

`src/config.rs` reuses Forge's counted save mount and the checked ARM32 SDK file
ABI established by the maintained preferences implementation. Narrow SDK calls
are necessary because stock forge-rs ScopedMount panics on mount failure,
Reader asserts on short reads, Writer ignores short writes, and checked flush
and commit are absent. Handles and filesystem abort context use scoped guards.
Forge's unmount performs its normal additional commit; the plugin checks an
explicit commit before reporting success. Only the plugin's primary INI is used.

## Logging

Startup is one INFO line. Actual hook/resource failures are reported once per
reason from onUpdate; creation/validation failures carry their numeric stage on
the same line (stage meanings are in `src/gui.rs`). Successful rows,
pages, saves and frames produce no warnings or errors. `research/log-cleanup.json`
records why the older diagnostic lines were removed.

## Native implementation

### Native classification and attachment

The plugin installs the parent and row hooks after executable/Forge validation
and updates native badge objects synchronously. Ordinary runtime validation rejects actual
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

An active urgent badge (ordinal 3) requires historical urgent identity, membership in the actual counter's
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
The display size is 32×32 at row-local Y=3, X=365 in a free request slot or
X=329 before a visible request bubble.
The source rectangle is `(136,344,198,406)` in HD_lobby00_BM_NOMIP, the white lobby
emblem already loaded by English HD. The size/position fields (+0xb4/+0xb8 and
+0x80/+0x84) are verified by native getters/setters. Position setters use VFP scalar
arguments; checked scalar writes plus native dirty flags avoid a float ABI shim.
All other style, texture, rectangle, visibility and color methods use integer or
pointer arguments. No texture pixels or new atlas are embedded in the NRO.

A new drawable must also fit the root's cached command list. Native root setup
0xa49b28 allocates `(drawableCount * 16 + 8)` bytes when its secondary prefix count
is zero. The unmodified row has nine drawables (152 bytes), and this mod's child alone
needs 168. The size comes from the live tree: twelve resource nodes and nine drawables,
plus one node and one drawable per child already added by any plugin. The descriptor/counts stay unchanged because native draw walker
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
introduced. The instance-owned index map grows by one entry from the live count `0xa38ffc`, and the badge can sit at any index past the resource's twelve. A failed allocation leaves the old
root/cache/index arrays valid and destroys unpublished storage.

### ARM and Forge boundaries

forge-rs 1.5.0 is pinned at `d1865b68e9b194eb3eacc8bd71bbf601a5fac63e`.
The loader handshake requests 1.5.1. Native and Rust checks agree on Hook size24,
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

Both detours call the original once with their arguments and return, so every window
accepts another plugin's Forge hook over its first eight bytes (see "Chaining" in the forge-modding hooks reference).
`window_matches` in core is the check, and the trampoline is compared against the
pre-hook snapshot.

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

## Fixtures and validation

Core policy fixtures cover all badge states, alternatives, obsolete unfinished
keys, simultaneous urgents, viewing versus completing and conflicting records.
The hook harness executes production ownership-aware rollback with Forge doubles.

`resource.py` only reads the copied native GUI/atlas layout and rejects corrupt
bounds. It checks that no ARC is staged. The fifteen original row sequences and
twelve-object index layout are inputs, and remain unchanged at runtime.

`arm.py` runs the compiled seven-argument pass-through callback in all sixteen GE
patterns, checks callee-saved state, named 70-byte metadata with canaries, the
1.5.1 request and native Hook declarations, and retains caller continuation code.

`native_adapter.py` runs the compiled parent/row/GUI adapter with native-shaped
memory, MT constructor/query doubles and real game ARM draw-list/destructor code.
Its twenty-one cases cover states, progression evidence, both holder tables, missing
context, bad objects, object/cache allocation failure and repeated insertion.
It checks colors, pose/size, unchanged index arrays and saved records, actual native
draw traversal, cache canaries, root/child cleanup and balanced stack/TLS.

The GPU commands are doubles. No fixture launches Forge or establishes actual
in-game pixels, clipping or gameplay acceptance.

The package check rejects any ARC payload. Protected quest, completion and progression records stay unchanged in every fixture. Pixel rendering and the game's actual query results still need a manual trial.

Runtime evidence: r17 was accepted by the user on Eden/Linux, with and without HD, and its build is at `build/key-quest-markers/candidates/r17/`. See `EVIDENCE.json`.

## Native reference

Native `Tex_icon` settings and the setters that apply them (main-relative):

| Setting | Actual value | Setter |
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

The native loader at main+0xb7f988 leaves INIT_PARAM types 17 and 18 unrelocated. Dispatcher 0xb344f4 reads kind 17 as the low byte of the value (bool) and kind 18 as the value word. Only kind 3 references kv8; kinds 1, 2 and 7 and others use kv32; kind 4 uses kv128.

Title `cGUIObjMessage`, CRC `0x2fb82eae`, size 352, at row binding 4, ID 6. Native operations:

| Operation | Address / contract |
| --- | --- |
| AutoScale setter | 0xa53348, two integers, preserves all but +0xf0 bit 0 |
| AutoWrap setter | 0xa53324, two integers, +0xf8 bits 18..19; enum 0 disables wrapping |
| Size setter | 0xa53528, object and float2 pointer, writes +0xc8/+0xcc |
| FontSize invalidation tail | 0xa5350c, ORs +0xf0 bit 16 |
| Cached-layout refresh | 0xa53aa8 checks bit 16, calls virtual +0x70, then clears it |
| Message type getter | 0xa56ab8, GOT input main+0x183f0b0 |

Size and AutoScale do not invalidate cached glyphs, so the adapter sets bit 16 after an actual layout change. Restore uses width 355, height 38, AutoScale 0 and AutoWrap 0. AutoScale dispatch is at 0xa42374..0xa423cc and clamp function 0xa449c0.

Row layout on the unchanged English HD resource: request Texture ID 20 at lookup index 3, (365,2), 32x32; title Message ID 6 at index 4, X 62, 355x38, both children of the same row Null. The builder calls 0x56e530/0x545630 to set the request's visibility immediately through 0xa47950, so `+0x54` bit 0 is the displayed request state after the original returns. Badge 32x32 at Y 3, X 365 free or X 329 before a bubble, title widths 299 and 263. The bubble case keeps a four-pixel gap. A quest can be both: quest 107, Another Pack Attack, is native key category 1 with mRequestVillage 8, which the builder's 0x11e0 mask shows as a request bubble.

Object map: count getter 0xa38ffc calls tree traversal 0xa47d2c and adds the root, so each added child needs one more entry, read by cleanup 0x5456e4 and by 0x546360, 0x547a14 and 0x548438. The allocator is `cGUIInstance`'s MT allocator (alloc1 at vft+0x1c), confirmed by GOT slot 0x18422b4, used by map construction 0xa38bc0 and destruction 0xa38b58/0xa38828. Native 0xa38828 passes instance+0x6c to 0xa38bc0, which writes that cGUI owner to every child +0x74. The cGUIObjTexture DTI vtable at main+0x178ff90 has destructors 0x32c and 0xa568a8, factory 0xa4f550, and a null +0x0c; placement constructor 0xa4f60c, Polygon base 0xa4d0d8.

Special encounter urgents (groups 47..54) are urgent by Kiranico's label although cQuestData +0x10c bit 0 is clear (flags 0x300/0x308). Family getter 0x3b21f0 reads main+0x162a8a0 (first eight words 1,1,2,2,3,3,4,4); 0x3b85d8 uses it with repeat-category predicate 0x3b2214. Availability predicate 0x54af8c, called with category 0xff and null menu context, checks scene query 0x3b2174 and a 51-entry enabled-bit table; all eight IDs are entries 0..7 at 0x162cde4, stride 8, bits at owner +0x35d4. The mod uses that predicate, completion 0x523da4, and completion of either record in the same family. Available unfinished unsatisfied pairs show the urgent colour; completed or satisfied pairs and unavailable records are grey. No rank is inferred from the viewed star page. `EVIDENCE.json` `historical` holds hashes, URLs and limits.

## Checks still open

Individual settings, persistence, ranks, quest states and transitions were never separately enumerated in any acceptance. Worth a dedicated run on Eden and Ryujinx separately: picker and hex edits, pending and reset, Save & apply without scrolling or reopening the counter, restart persistence, all three badge states, request overlap, selection, confirmation, scrolling and menu transitions. r18 itself has no runtime test; it differs from accepted r17 only in link flags and build identification.

## Do not

- **Replace `common_eng.arc`.** HD Project also replaces it, and Eden takes the alphabetically first file. The user chose native runtime insertion with all ARC files untouched. Remove an old ARC-based install as a whole.
- **Compare a child's `+0x74` with the animation instance.** It holds the cGUI owner from instance+0x6c.
- **Require the DTI's placement slot at +0x0c.** It is null. Call constructor 0xa4f60c with storage in r0.
- **Compare trampolines by index into the signature table.** Adding a window shifts the table and rolls back valid hooks. Compare each with its own Patch snapshot.
- **Grow the tree without growing the map.** Cleanup dereferenced map[12], an unmapped Read32 and a null fetch. Publish instance +0xd8 and root +0xa0 before linking the child.
- **Trust the row's visible bit as success.** Callback, classification and the Visible bit do not prove pixels.
- **Decode INIT_PARAM kinds 17 and 18 as kv8 offsets.** The first kv8 bytes happen to be 1, which hid this and produced Mask 1 and an invisible badge. Mask 0 is normal colour drawing.
- **Require `cGUIObjText` size 384 for the title, or force a type onto a fixture.** Derive fixture classes from the real resource's CRC. The Text subclass, CRC `0x313f6cc4`, must be rejected.
- **Skip restoring titles before classification can fail.** Restore valid titles first, and let a bad request or title binding skip only its own decoration.
- **Call a screenshot's pixels native units.** The 32 px mark and 39x37 bubble were screen measurements.
- **Use Size or AutoScale's title contract on Texture objects.** Saved Texture DTI's Size has a getter and no setter.
- **Infer the current rank from the viewed star page, or count rank-up prerequisites as a special encounter's activation.** The two pools are separate.
- **Log below ERROR and expect to see it.** The user's Forge filter is ERROR only. Keep diagnostics process-capped and outside hot hooks.

Older colours and sizes (orange-red keys, purple or yellow urgents, 24x24 badges, the small emblem) are retired. Use the current policy above.
