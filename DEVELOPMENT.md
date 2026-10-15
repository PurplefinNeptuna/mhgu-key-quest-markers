# Current release workflow

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

# Development

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
workspace's `build/key-quest-markers-rs/candidates/r14/` and matching `work/` folder,
or the independent checkout's own `build/` and `work/` folders after export.

The workspace coordinator also supports
`python3 scripts/mod_distribution.py package key-quest-markers-rs` for this
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


## r12-small comparison variant

Only the source UV and build identity differ from r12. The smaller outlined top
emblem occupies logical `(342,0,372,30)` in texture22, equivalent to physical
`(1368,0,1488,120)` in the 2048² HD atlas. It is drawn at the same 32×32 size.
Native compiled fixtures check the rectangle setter, stored UV and all four
half-texel-inset UV corners, along with the unchanged layout and cleanup cases.
The original r12 delivery remains untouched; its complete file hashes are in
`docs/R12_COMPARISON.json`. Independent source exports and output paths use
`r12-small`, so neither build nor package commands overwrite original r12.


## r13: special Village urgents, both emblem builds

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


## r14: purple active urgents

The default and `KQM_SMALL_MARK=1` commands now build r14 and r14-small.
Active urgent badges change from yellow #FFD239 to purple #9B4DCA, packed as
0xffca4d9b so little-endian bytes are155,77,202,255. The internal state remains
ordinal3 and is named Purple in core and diagnostics. Native request objects,
key/grey colours, classification and layout are unchanged. Existing exact-RGBA
and compiled native quad checks validate the new colour in both builds.
Original r13/r13-small packages remain byte-for-byte preserved.
