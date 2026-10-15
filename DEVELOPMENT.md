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
workspace's `build/key-quest-markers-rs/candidates/r10/` and matching `work/` folder,
or the independent checkout's own `build/` and `work/` folders after export.

The workspace coordinator also supports
`python3 scripts/mod_distribution.py package key-quest-markers-rs` for this
explicitly registered DEVELOPMENT candidate. It delegates to the owned builder,
verifies ZIP/runtime/support/checksums, and does not grant release approval.
Run the full coordinator `check` before committing distribution work.

r10 activates the parent and row hooks after executable/Forge validation. The
parent copies offered urgent IDs into scoped Forge SDK TLS; the row callback reads
native progression/completion and creates missing cGUIObjTexture children. They
are attached to each row's main Null, using the game's MT allocation/constructor
and sibling-link functions. The native draw cache grows from 152 to 168 bytes.
The runtime index map grows to thirteen entries with the original twelve
bindings preserved; resource descriptors remain untouched. See the
native audit for exact ownership and the source of these sizes.

The build only reads the copied HD common archive as a layout fixture; it does
not stage any ARC. r1/r2/r3/r4/r5/r6/r7/r8/r9 and the original C++/PC releases remain preserved. r10
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
generation with GPU commands doubled. The user confirmed r9 works on Eden/Linux; r10 placement remains untested in-game.


r10 reads native request visibility after the original builder and positions the
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
