# Key Quest Markers: development and research

**Current state.** r23 is READY_TO_DISTRIBUTE (2026-11-23), unpublished, release at `build/key-quest-markers/releases/r23/`. It marks quests that grant Hunter Arts or Felyne ingredients, and the quests their unlock chains require, in orange (`#FF7F00`), and quests that unlock others in blue, from build-time lists. r23 loaded on Eden and MHGURecomp beside WishFinder r143, and the user reports it working after many runs, unitemized. r20 at `build/key-quest-markers/candidates/r20/` is the previous accepted build. Ryujinx and native Switch gameplay remain unconfirmed. DISTRIBUTION.json is authoritative; EVIDENCE.json holds exact results.

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
folder. Inputs are copied `main`, `sdk`, a matching Forge NSO named `forge`,
the selected HD English `common_eng.arc`, and the 1.4.0 RomFS
`loc/arc/village/common.arc` and `loc/arc/npc/talk.arc` named
`village_common.arc` and `talk.arc` (HD Project's copies of the entries read
are byte-identical). Never edit originals.

Run from any directory:

```sh
./build.sh fetch     # once: downloads forge-rs and crates into vendor/
./build.sh doctor
./build.sh build
./build.sh test
./build.sh verify
./build.sh package
./build.sh export --output /path/to/new/source-folder
```

`prepare` verifies inputs and the read-only native GUI layout fixture. All
commands are offline; there is no download, install, game launch or settings
command. Outputs use the workspace's `build/key-quest-markers/candidates/VERSION/`
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
| Unlocks | 4 | `#0032C2` (RGB 0,50,194) | Other quest whose clear unlocks a different quest; grey once cleared |
| Reward | 5 | `#FF7F00` (RGB 255,127,0) | Other quest that grants Hunter Arts or ingredients, or one its unlock chain requires; outranks Unlocks; grey once cleared |

The defaults are the exact game UI colour properties (blue is the Capture category's), except Reward's orange, which the user chose. See
`research/theme-colours.json` for copied input hashes, object/instance IDs, file
offsets and native category/message bindings; `inspect_theme` verifies the
pinned resource and executable at build time. The base and HD `counter_down`
resource are byte-identical. The main objective's instance colour overrides its
shared Message template; the separate Slaying category red `#CC0000` is not the
requested colour. Native alpha stays 255.

Groups 47..54 are four special Village encounter pairs that Kiranico lists as
Urgent. They lack the rank-up urgency bit and use the full native counter
availability predicate instead of the rank-up offered set. Completion of either
record in a family makes both grey. Native details are under [Native reference](../../.agents/skills/mhgu-forge-modding/references/worked/quest-badges.md#native-reference).

## Settings

Configuration keys are exactly `key`, `urgent`, `completed` and optional
`unlocks` and `reward`; values are six hexadecimal RGB digits. An INI without
one of them keeps its colours and uses that colour's default. Saved custom values are never rewritten; Reset defaults
then Save & apply uses the game palette. The settings panel uses Forge ImGui only.

`core/src/colors.rs` owns bounded RGB INI parsing, formatting and the tested
mount/write/readback/commit policy. `src/settings.rs` protects UI drafts and load
state with a Forge mutex. Five independent atomic RGB settings are copied once
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

## Quest lists

`scripts/quest_unlocks.py` runs in `prepare` and writes the two sorted ID lists
that `build.rs` embeds (`src/quest_lists.rs`, binary search). Game-derived IDs stay
out of Git; `quest-lists.json` in the candidate records counts, hash and input
hashes. `tests/unlocks.py` checks hand-traced cases. A quest is listed when its clear is
loaded by a case of the unlock script, or is a talk condition of a row that sets a
flag such a case loads, directly or through further talk rows. The 1.4.0 inputs
give 557 IDs; 468 are neither key nor urgent, and the 429 of those outside the reward list show blue. Event/DLC IDs
(1,000,000 and up) appear in no unlock rule. An ID another mod adds is absent,
so it gets no badge; MHGU Definitive Edition adds 48 such IDs and patches no
checked window.

The reward list holds the cleared-quest conditions of talk rows whose mAction2
grants Hunter Arts or ingredients, plus every quest their unlock requires,
recursively: 33 reward quests (7 Hunter Arts, 26 ingredients) and 47 chain
quests, 80 IDs; 49 are neither key nor urgent. Talk rows that grant without a
quest condition (the 92-art base set on flag 847, level-gated ingredients) add
nothing.

| Source | Verified behaviour |
| --- | --- |
| `script\check_quest_unlocked` (rCommonScript, `village/common.arc`) | sCommonScript (0x8e8 bytes) query 0x3d7e90 runs it with the quest in `[WORK0]`, cached per quest at +0x8e0. Records: u32 index, u8 command, two strings; header f32 1.0, count. |
| VM 0x3d17f8 | Command - 1 indexes the jump table at 0x3d5874. 0x0e labels a case; a body ends at 0x23 (or 0x24 at a switch boundary). 0xa1 requires A == B, 0xa7 A >= B (failure returns 0); 0x03 returns 1. 0x75..0x78 load quest cleared (0x523da4); 0x40..0x43 load story flag bit P of `[0x18390e0]+0x500`; 0x50 adds, 0x52 sets. Loaded values are only compared == 1 or counted >= N, so a clear never locks a quest. |
| rNpcTalkData (`npc/talk.arc`, 171 tables) | 37-byte packed records (cNpcTalkData fields). Evaluator 0x2451c8 returns 1 when a tag holds: 1 flag set, 2 not set, 11 quest cleared, 12 not cleared; quest = param plus `[10000,100000,40000][fixed-10002]` for fixed 10002..10004 (table via literal at 0x2464f0). Tags combine with AND except kinds 16..21, 119, 147. Action switch at 0x2479d8 on mAction1: 1 and 4 set flag mAction1Param in the same array (0x247a14), 2 clears; mAction2 writes no flag. |
| mAction2 grants (switch 0x247c58, kinds 1..26) | 4 Wycademy points (DialogMsg 92); 5..8 `0x523a80` point counters; 9..16, 24, 25 Hunter Arts sets through `0x3f0c3c` mode 0 (DialogMsg 100/101; mode 1 from the tag evaluator only checks them); 17..21 ingredient groups through `0x3f1380` (DialogMsg 73); 22 Poogie/Moofy costumes (25/26); 23 shop music (112). The grant functions have no other direct or table callers. |
| Other flag writers | Helper 0x244f14 (43 callers), the script VM (clear only, 0x3d2e1c) and the progress table 0x3f1778 (flags 233..239) write no unlock-chain flag except 1503, set in-quest at 0x3aee44. |

## Logging

Startup is one INFO line. Actual hook/resource failures are reported once per
reason from onUpdate; creation/validation failures carry their numeric stage on
the same line (stage meanings are in `src/gui.rs`). Successful rows,
pages, saves and frames produce no warnings or errors. `research/log-cleanup.json`
records why the older diagnostic lines were removed.

## How it works

Design, hooks and native detail live in the skills: [Key Quest Markers: classification and badges](../../.agents/skills/mhgu-forge-modding/references/worked/quest-badges.md).

## Fixtures and validation

Core policy fixtures cover all badge states, alternatives, obsolete unfinished
keys, simultaneous urgents, unlocking quests, viewing versus completing,
conflicting records and INIs without `unlocks`.
The hook harness executes production ownership-aware rollback with Forge doubles.

`resource.py` only reads the copied native GUI/atlas layout and rejects corrupt
bounds. It checks that no ARC is staged. The fifteen original row sequences and
twelve-object index layout are inputs, and remain unchanged at runtime.

`arm.py` runs the compiled seven-argument pass-through callback in all sixteen GE
patterns, checks callee-saved state, named 70-byte metadata with canaries, the
1.5.1 request and native Hook declarations, and retains caller continuation code.

`native_adapter.py` runs the compiled parent/row/GUI adapter with native-shaped
memory, MT constructor/query doubles and real game ARM draw-list/destructor code.
Its cases cover states, the blue badge on real quest 220 and orange on 233 from the generated lists, progression evidence, both holder tables, missing
context, bad objects, object/cache allocation failure and repeated insertion.
It checks colors, pose/size, unchanged index arrays and saved records, actual native
draw traversal, cache canaries, root/child cleanup and balanced stack/TLS.

The GPU commands are doubles. No fixture launches Forge or establishes actual
in-game pixels, clipping or gameplay acceptance.

The package check rejects any ARC payload. Protected quest, completion and progression records stay unchanged in every fixture. Pixel rendering and the game's actual query results still need a manual trial.

Gameplay with and without HD was accepted on r17 (`build/key-quest-markers/candidates/r17/`); see `EVIDENCE.json`.

## Checks still open

Individual settings, persistence, ranks, quest states and transitions were never separately enumerated in any acceptance. Worth a dedicated run on Eden and Ryujinx separately: picker and hex edits, pending and reset, Save & apply without scrolling or reopening the counter, restart persistence, all three badge states, request overlap, selection, confirmation, scrolling and menu transitions.

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
- **Read the unlock script or talk tables at the counter.** The script module loads only in some scenes and talk tables per NPC; the list is built from the pinned RomFS.
- **Treat mAction2 kind 1 as a flag set.** Only mAction1 writes flags; mAction2 rows look like item and count (`1, 1875, 3`).
- **Log below ERROR and expect to see it.** The user's Forge filter is ERROR only. Keep diagnostics process-capped and outside hot hooks.
