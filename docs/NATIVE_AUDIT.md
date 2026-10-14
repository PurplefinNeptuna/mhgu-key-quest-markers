# Native implementation audit — r1

## Candidate gate

**Inactive.** `kqm_verified_contract == 0` makes initialization stop before native
lookups or hook creation. No config or UI setting bypasses this gate. Two missing
contracts prevent activation: complete native progression/urgent availability
semantics, and the new object's attachment/identity in the live GUI holder.
The delivered GUI object is hidden by default. Loading the extended GUI itself
still needs a separately authorized runtime trial; inactivity of the plugin is
not evidence of resource-load safety.

The portable policy is implemented and fixture-tested. The native adapter reads
completion, groups, urgency flags, stages, prerequisites and incomplete-urgent
pools, but supplies `None` for current-key relevance and active-urgent availability.
It must not be activated merely by changing the gate. Resolve those facts first.
Host fixtures use explicit verified facts; they do not prove native availability.

## Verified code/data paths

Original main NSO SHA-256:
`b3935415499549adaf4c0e89822831daa175cfd456a7990791c79be3997645ef`.
Build ID: `FB08F1D20FD1204FE7070672777F869B`. Offsets below are main-relative.
Saved Ghidra addresses use image base `0x009c9000`; original NSO bytes supply
signatures because the imported database contains one changed text byte.

| Path | Evidence |
| --- | --- |
| Normal row builder `0x616cb0` | Seven integer/pointer args: UI, selection, page, new flags, other flags, cursor, eight quest pointers. Calls original before updates. |
| Completion reader `0x523da4` | Reads the quest group index bit in the completion record at `sUserInfo + 0x42c`. |
| New/acknowledgement reader `0x523d00` | Separate bitfield at `sUserInfo + 0x100`; never used as completion. |
| Native Village prerequisite reader `0x3b1a18` | Bit zero indicates required groups satisfied; category 1..10 and alternative group byte 1..11. |
| Native Hub/G prerequisite counter `0x3b1d70` | Counts total/completed category `tier + 10`; accepts tiers 1..13. |
| Native progression processor `0x50cbd0` | Reads completions, then writes separate Village/Hub stage fields. Validation only; the plugin never calls this writer. |
| Progression storage `0x18979f0` | Its loaded record supplies u16 fields at `+0x3e0`, `+0x3e2`; this is separate from sUserInfo's completion bits. |
| Group resource | `sQuest + 0xb4`, count `+0x64`, records `+0x6c`, 12-byte records. ID at +4, category/alternative bytes +8/+9. |
| Urgent identity | `cQuestData + 0x10c`, bit zero. The loader `0x37539c` reads the compact resource's final u16. Resource correlation matches all 28 historical urgents among 1,302 records. |
| Incomplete urgent pools | `sQuestSelector + 0x68`, five pools with 16 IDs each, u16 counts at `+0x1a8`. Membership does not prove current availability. |
| Native visibility/color | UI wrappers `0x56e530`, `0x56e6fc`; four integer args. No scalar float ABI crossing. |

The progression processor counts Village categories 24..33 and Hub categories
34..46. It has special handling for Village quest IDs 601 and 1005 when stages
are 5 and 9. A simple `urgentCategory = base + stage` assumption would mislabel
other urgents in those groups. The first stage can be zero; zero is not blanket
proof of corrupt state. The static range classifier `0x3bc5f0` and incomplete
urgent pools alone also fail to establish an urgent's availability.

Required follow-up: trace the quest counter's actual urgent offer/unlock checks,
including NPC/prerequisite routing, special Village branches, alternatives and
simultaneous urgents. Establish exact current-key relevance for Village, Hub and
G-rank separately. Do not use the viewed rank, new flags, or static rank ranges.

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

Candidate object access expects holder UI+0x24, instance count +0x298,
instance-pointer table +0xf8, row instances 16..23, object array +0xd8 and slot12.
It validates object ID21 and cGUIObjTexture DTI before writes. Establish the live
resource identity/array ordering and sequence initialization behavior before
activation. Kernel readability checks cannot establish object ownership/lifetime.

## ARM and Forge boundaries

forge-rs 1.5.0 is pinned at `d1865b68e9b194eb3eacc8bd71bbf601a5fac63e`.
The loader handshake requests 1.5.0. Native and Rust compile-time checks agree on
Hook size24, alignment4, context offset12, ctx_cell offset16 and has_ctx offset20
(native). Older incompatible loaders are rejected; no loader is bundled/replaced.

The two displaced ARM words are `e92d4ff0` (PUSH r4-r11,lr) and `e24dd004`
(SUB sp,sp,#4). They have no PC-relative operands or GE/NZCVQ operations.
Forge's 16-byte trampoline must contain those words, `e51ff004` (literal LDR pc),
and target+8. Installation compares exact support windows first, verifies the
trampoline and published branch, and flushes code caches. One ordinary hook uses
one pooled 16-byte slot; Forge owns the pool's 16 KiB CodeMemory chunk. This is a
capacity description, not proof of runtime headroom with a particular mod set.

The typed function-entry detour preserves AAPCS callee-saved integer/VFP state
and forwards r0..r3 plus three stack arguments. Unicorn executes the compiled
NRO with a deliberately clobbering original double in all 16 GE patterns.
Incoming GE reaches the original unchanged. Direct caller sites 0x616bfc,
0x618bbc and 0x618cb8 use no GE-dependent SEL before their next call. The first
two set their own condition flags before conditional use; the third makes an
unconditional next call. Flags are not an additional return value here. No MSR
status writes occur in the compiled plugin. These checks do not validate a live
Forge installation or the new native GUI writes.

Rollback accepts only original/owned branch words, including partial publication.
Foreign words are not overwritten. Disabled Patch snapshots cannot restore on
Drop; verified original continuations remain process-owned/reachable on failure.
The fixture exercises the production rollback against whole/partial owned writes
and foreign modification. A failure retaining a redirect requires a restart;
there is no unloading or hot-reload path.

Forge owns lifecycle, logging, allocation, singleton lookup, main text address,
ordinary hooks and patches. Immutable DTI lookup fits its high-level wrapper.
Game-owned mutable objects use scoped raw access; no resource pointer is retained
across menu transitions. Pinned Forge exports lack memory-query/program-ID/cache
flush helpers and native GUI-holder operations, so narrow SVC/native calls cover
those gaps. There is no duplicate allocator, hook engine or renderer.

## Remaining acceptance

No game was launched and no package was installed. Resolve the two native gates
first, then rebuild and repeat static validation before a separately authorized
English HD trial on Eden and Ryujinx: Village/Hub/G progression, obsolete keys,
alternative groups, simultaneous urgents, viewing without completing, scrolling,
selection, confirmation, reopening, quest return and progression advancement.
Check badge size, four-pixel gap, clipping, colors and resource transitions.
Disable the old prefix plugin during that future trial; preserve its accepted
payloads/releases. GUI load safety, attachment and gameplay remain untested.
