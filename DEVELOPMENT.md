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

`prepare` verifies inputs and builds the resource only. All commands are offline;
there is no download, install, game launch or settings command. Outputs use the
workspace's `build/key-quest-markers-rs/candidates/r1/` and matching `work/` folder,
or the independent checkout's own `build/` and `work/` folders after export.

The workspace coordinator also supports
`python3 scripts/mod_distribution.py package key-quest-markers-rs` for this
explicitly registered DEVELOPMENT candidate. It delegates to the owned builder,
verifies ZIP/runtime/support/checksums, and does not grant release approval.
Run the full coordinator `check` before committing distribution work.

The immutable `kqm_verified_contract` is zero. Do not patch it to enable the mod.
Resolve the progression and GUI gates in `docs/NATIVE_AUDIT.md`, update the native
adapter's unresolved evidence, then rebuild and repeat validation. Initialization
currently returns before singleton access, resource access or hook installation.
Manual acceptance needs separate authorization; no automated game suite exists.

Owned code explains native offsets and resource/table ownership beside its use.
Forge owns allocation, hooks, patches, logging and callbacks. Narrow SVC bindings
cover only memory queries, title identity and cache flushes unavailable as exports.
Native UI setters cover the game GUI operations not wrapped by forge-rs.
