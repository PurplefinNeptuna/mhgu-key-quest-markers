# Key quest markers: investigation

Investigated 2026-10-06 for MHGU Nintendo Switch 1.4.0. This is static research;
no plugin was built, installed or enabled, and no emulator, save or game resource
was changed.

## Finding and proposed first prototype

The game's `quest\quest_group` resource classifies all **118 progression key
quests** found in the current [Kiranico quest list](https://mhgu.kiranico.com/quest):
58 Village, 37 Hub low/high rank, and 23 G rank. A Forge plugin can use this
native classification by quest ID. A manually maintained quest-name list is
unnecessary for the inspected inputs.

The most concrete first prototype is a `[KEY] ` prefix supplied at runtime by
the native quest-name getter. It would use the game's font, selection styling
and title layout. A separate icon beside the quest row remains a later UI
research task: the page builders are located, but a suitable spare native UI
element and icon layout have not been verified.

Keep the native completion marks, urgency, unlock conditions and sorting.
Display the marker on completed key quests too. Urgent quests remain separate.
Kiranico also applies its Key badge to 113 training rows (7 basic, 98 weapon,
8 Prowler); the 118 count and proposed initial feature cover rank progression.
Training badges are not evidence that those quests advance Village/Hub rank.

## Input identity

The original executable authority is the preserved update NSO at
`work/shared/game-exefs/main`:

- SHA-256: `b3935415499549adaf4c0e89822831daa175cfd456a7990791c79be3997645ef`.
- Build ID: `fb08f1d20fd1204fe7070672777f869b00000000000000000000000000000000`.
- Verified reconstructed image SHA-256:
  `24c208c395c65727b21b5fa91af8381396e70cf421b0fcfee0345d8743298110`.
- Imported Ghidra image base: `0x009c9000`. All offsets below are relative
  to the original main image, after subtracting this base.

The RomFS inputs were copied from
`~/.local/share/eden/dump/0100770008DD8000/romfs/nativeNX/`
to `work/key-quest-markers/inputs/`, retaining the relative paths:

| Relative archive | SHA-256 | Resources |
| --- | --- | ---: |
| `loc/arc/village/common.arc` | `8b5e466ad141fcaafd187cafcf0adcf7648bca327536a722f9faa69778e27231` | 723 |
| `loc/arc/quest/vq.arc` | `4126956feec6ca93f3866ce6c31181f0c16c82d137ab8c9904a9e46571d45e76` | 3904 |
| `loc/arc/quest/gq.arc` | `5d28425a975459e62630d32685d5e5bc84d4798180e282d3a5110d1a5bafe95a` | 4672 |
| `loc/arc/quest/gq2.arc` | `03eba4ff182966f784ae11f429859109d5a3ed5134e33f735a0d77c57b28e724` | 1840 |

The ARC reader validates tables, block bounds, decompressed lengths and
non-overlapping blocks. Copied and original archive hashes were rechecked after
the investigation. These identities establish research inputs, not the running
game's version or the active mod set.

## Native classification

In `common.arc`, internal resource `quest\quest_group`, type `0x61cf79af`
(`rQuestGroup` / `.qsg`), has SHA-256
`d7145de5cd1e20ab6f7021cf70bcb77c2f8f193ba321040fb4c72396709b7fbd`.

Its 10,571 bytes contain a little-endian float version `4.0`, a 32-bit record
count `1509`, then 1509 packed seven-byte records:

| Record offset | Type | Meaning from DTI and code |
| --- | --- | --- |
| `+0` | `u32` | `mQuestNo` |
| `+4` | `u8` | `mAttribute1` |
| `+5` | `u8` | `mAttribute2` |
| `+6` | `u8` | `mTitleVer` |

The runtime `cQuestGroup` is **12 bytes**, with its vtable at `+0`, ID at `+4`,
attributes at `+8/+9`, and title version at `+10`. Do not cast packed resource
bytes to that runtime structure. `rQuestGroup::getEntry`, main `+0x0039bd1c`,
checks the count at `rQuestGroup +0x64` and indexes runtime records from the
pointer at `+0x6c`. The DTI dump agrees with the field offsets and sizes.

Classification verified against Kiranico:

| `mAttribute1` | Progression category | Keys |
| --- | --- | ---: |
| `1..10` | Village 1★ through 10★ | 58 |
| `11..17` | Hub 1★ through 7★ | 37 |
| `19..22` | G1 through G4 | 23 |

Attribute 18 has no records in this input. Use the explicit verified ranges,
and keep other categories separate. Ordinary, urgent and training entries also
exist in the same table. Membership in the table alone does not mean Key.

There are 1507 unique IDs. IDs `1049` and `1050` each occur twice with identical
attributes. A marker lookup can consolidate those equal classifications, but
the original table order must remain intact: completion state indexes this
table by record position.

Native code corroborates that this is live quest/progression data:

- `sQuestSelector::loadQuests`, `+0x003b7de8`, obtains the group resource from
  the quest system at `+0xb4`, iterates it and loads quest IDs for the current area.
- `+0x003b1964` counts Village records with `mAttribute1 == requested tier`
  and calls the completion reader. `+0x003b1d70` does the same with tier `+10`
  for the Hub tier categories.
- `+0x00523da4` maps a quest ID to the resource's record index and reads its
  completion bit. Its neighboring routines write completion/other bitfields;
  they are research evidence and must not be called to implement a marker.
- `+0x0050cbd0` processes other attribute ranges (`24..33` and `34..46`) when
  updating progression after urgent completion. This supports keeping urgent
  categories separate from the key ranges.

No verified, standalone native `isKeyQuest(id)` helper was found. Reading the
small runtime record through the existing native accessor is the proposed gap
to fill; it requires no progression or save mutation.

## Kiranico cross-check

Fetched `https://mhgu.kiranico.com/quest` on 2026-10-06 and preserved the HTML at
`work/key-quest-markers/research/kiranico-quest.html`, SHA-256
`167a87e5697f5f2b001a20acf3f56de84f1bece9632730751c398ac0ceacab9c`.
The comparison uses the site's Village/Hub tier panes `s0-*` and `s1-*`, taking
each row once from its nearest pane. It does not count the outer panes again.

Kiranico URLs contain site-specific IDs; they are not the game's numeric quest
IDs. The comparison joins area, tier and exact English title to the copied
quest resources, then obtains each game's ID from its binary quest-data record.

- 1302 local quest/text resources were inspected across the three quest archives.
- Restricting to regular Village/Hub IDs gives exactly 944 rows, matching the
  website's area/tier/title inventory, including duplicate-title multiplicities.
- 934 rows have a unique local identity. Ten website rows correspond to five
  duplicate-title pairs; their exact site-to-game variant identity is unresolved.
- All 118 Key rows map uniquely to game IDs and native key categories. The
  native candidate ID set equals the website's matched Key ID set.
- All 934 unique matches agree on Key versus non-Key. The ten ambiguous rows
  and every candidate variant in those pairs are also non-Key.

The duplicate-title pairs are `Tumultuous Sprouts`, `Into the Wyvern's Den`,
`No Go on the Popo`, `A Forest Fracas`, and `Beware the Comet of Disaster`.
The last pair has different urgency badges. No urgent classification claim is
made from the unresolved variant mapping.

Examples independently opened in the website tool include
[Find the Ferns](https://mhgu.kiranico.com/quest/46384) (game ID 101) and
[Wipe Out!](https://mhgu.kiranico.com/quest/48834) (game ID 106), both Village 1★
keys with native group 1. G1 has five keys in native group 19, including
[Pecking Order](https://mhgu.kiranico.com/quest/8bdb3) (game ID 11106).

## Display route and constraints

`cQuestData::getName`, main `+0x003b57d0`, takes one ARM32 object pointer and
returns a title pointer. It obtains the selected-language `rGUIMessage`, with
the existing fallback path, then reads string `mIndex * 7`. Keep that native
behavior when adding a prefix.

Concrete callers:

| Main offset | Observed behavior |
| --- | --- |
| `0x00616cb0` | Fills a page of up to eight quest rows from `cQuestData**`; calls the getter and sends the name to native text property 4 |
| `0x00618324` | Another eight-row builder with the same title path; exact menu/category coverage remains untested |
| `0x00614778` | Stores the returned name pointer at detail-state `+0x58` |
| `0x0056ea08` | Native text setter wrapper; forwards to GUI resource holder and enables the property |

A single function-entry detour on the getter is a candidate for consistent
markers in the list and details. It has eleven direct callers in the saved
analysis, so its effects on other quest-title displays must also be checked.
The first eight original bytes are `10402de90040a0e1` (push `r4/lr`, move
`r0` to `r4`), with no PC-relative instruction in the overwritten span.
This makes it a plausible ordinary Forge trampoline target, not a validated hook.

The detail caller **retains the pointer**. Do not return one reusable scratch
buffer or a pointer into temporary memory. Keep separate stable storage for
each marked quest/language/source title; retain it while native UI can reference
it. Preserve the original title on null, unknown classification, unsupported
build, allocation failure or an oversized title. Verify thread ownership and
reentrancy before implementing a cache.

Use Forge's singleton lookup for the quest system, native group accessor for
its records, logging and main-address helpers, and `forge_hook_create` with
the native ARM32 Hook layout. The maintained fork is still
`codex/forge-legacyctx14` at `b8921fa3bbe35bbbafb11ccc489d5f1c6aa24a2d`.
One ordinary hook with an original trampoline requests one 4 KiB JIT arena;
the installed hooks' remaining CodeMemory capacity needs checking during build
preparation. It does not use the binary-specific legacy Better Input shim.

Any settings row follows [FORGE_PLUGIN_GUIDELINES.md](docs/FORGE_PLUGIN_GUIDELINES.md).
The marker runs independently of that row's open state. If preferences are
added, use Forge's counted save-data mount and a plugin-specific config.

## Evidence and next validation

Research exports live under `work/key-quest-markers/research/pass1/` through
`pass6/`. The existing `ExportModernControlsAudit.java` was reused with
`-readOnly -noanalysis`; no annotations were changed. It exported 57 functions
at verified original instruction bytes, plus five exploratory addresses without
functions. All inspected instruction bytes match the reconstructed original NSO.
The database's known changed byte lies outside the inspected functions.

`scripts/key_quest_research.py` reproduces the inventory and Kiranico comparison
using the copied inputs and saved HTML. It requires Python and the currently
available `beautifulsoup4` for HTML parsing:

```bash
python3 scripts/key_quest_research.py
python3 -m py_compile scripts/key_quest_research.py
git diff --check
```

Outputs: `work/key-quest-markers/research/verified-crosscheck.json` and the
separately recorded `validation.json`. Full comparison, syntax, four malformed
resource/header rejection checks and original/copy hash readback passed.
Generated HTML, archives, quest text and decompilation stay outside Git.

Before a runtime candidate: confirm actual executable/package identities and
activation, fingerprint the hook span, audit title storage lifetime, and verify
imports, ARM32 ABI and CodeMemory demand. Native group availability while browsing
quests, final title fit, font glyphs, scrolling, detail transitions, completed
keys, urgent differentiation, multiple languages and other getter callers still
need user-run emulator validation. No gameplay or performance success is claimed.

## Implementation checkpoint: 2026-10-06

[Key Quest Markers r1](README.md) implements the accepted
always-enabled prefix using native classification. Host checks cover all 118
keys, conflicting records, retained title storage, concurrency and transactional
hook failures. The ARM32 build and imports against current listed Eden/Ryujinx
Forge binaries passed. All 9,114 copied localized titles fit 256-byte slots.

The implementation documents two verified Forge API gaps: memory-query export
availability and non-transactional hook publication. It uses narrow private
operations for those gaps without changing the maintained Forge fork. The staged
package has one NRO, 276 KiB BSS and one requested 4 KiB CodeMemory arena.
Actual package hashes are recorded in the build report; activation, live main
identity, runtime allocation headroom and gameplay acceptance remain unverified.
No installation, activation or emulator launch was performed. Both emulator
checklists remain pending.

## User acceptance: 2026-10-06

The user subsequently installed/tested r1 and reported all applicable checklist
items passed. Eden coverage is Village 1★/2★ and Hub 1★; Ryujinx uses a full save
for the remaining Village/Hub tiers and G rank. Both installed NRO hashes match
the candidate. Latest logs corroborate the MHGU 1.4.0 launches and enabled
marker package; Eden also records successful marker activation. Ryujinx filters
Forge info messages, so its active UI/marker result remains user-confirmed.

[Runtime evidence](RUNTIME_RESULTS.json) retains log
hashes, actual Forge identities, scoped coverage and unattributed
emulator messages. The candidate bytes are unchanged. Higher-rank Eden gameplay
remains untested; no general native Switch or emulator-build portability claim
is made.
