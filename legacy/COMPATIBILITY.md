# Compatibility and implementation

Target: title `0100770008DD8000`, MHGU Switch 1.4.0, main build
`FB08F1D20FD1204FE7070672777F869B` (zero-padded NSO ID). Source executable
SHA-256: `b3935415499549adaf4c0e89822831daa175cfd456a7990791c79be3997645ef`.
The runtime checks the GNU note header/name/full 16-byte descriptor and exact
32-byte getter/accessor signatures. Unsupported targets remain inactive.

## Native data and storage

`cQuestData::getName` at main `+0x003b57d0` returns the original localized title
first. The ID comes from object `+8`. Forge resolves `sQuest`; its group resource
is at `+0xb4`, with count `+0x64` and records `+0x6c`. Native
`rQuestGroup::getEntry` at `+0x0039bd1c` returns a 12-byte record. The adapter
validates the array and returned addresses, checks duplicate fields and rechecks
resource identity. Attributes `1..17` and `19..22` receive the prefix.

The live group is scanned on each intercepted lookup; IDs are not embedded.
This preserves the distinction between missing/unavailable data and non-key
data, and avoids reusing a previous session's resource pointer. Mapped-memory
checks cannot prevent a resource from being freed concurrently; the native
quest UI's synchronous resource ownership remains a runtime assumption.

The details screen retains the returned pointer. A 1,024-slot cache stores
immutable strings by ID and source title bytes, covering 826 variants for 118
keys in seven languages with spare capacity. Slots are sized from all copied
localized titles, with a 256-byte minimum. A lock-free 32-bit atomic provides a
non-blocking cache lock. Every failure returns the original pointer; storage is
never evicted or freed during the process. UTF-8 bytes are preserved without
truncation. The fixed ASCII prefix also applies in non-English languages.

## Forge facilities and verified gaps

Use the maintained `codex/forge-legacyctx14` headers at
`b8921fa3bbe35bbbafb11ccc489d5f1c6aa24a2d`; metadata requires Forge 1.4.1.
Native compile assertions pin Hook/Jit/initialization ABI at 76/28/70 bytes.
Forge supplies lifecycle, logging, main address, singleton lookup and ImGui.
No preferences, input callbacks, independent renderer or filesystem wrapper is
needed. Forge and other plugins remain unchanged.

Two inspected limitations justify narrow private operations:

- `forge_mem_queryMemory` is declared/implemented but absent from the inspected
  dynamic export sets. The plugin uses the existing pinned ARM32 QueryMemory
  SVC wrapper for readability checks.
- `forge_hook_create` publishes the entry patch before its executable transition
  succeeds. Its failure path can leave a detour with no original. This plugin
  adapts the owned transactional CodeMemory backend for one exact hook: prepare
  the 16-byte original trampoline in a dedicated 4 KiB arena, make it executable,
  recheck the target, then publish. Only the verified `push {r4,lr}; mov r4,r0`
  pair is accepted. Rollback checks ownership; failure retains executable storage
  and reports an error. No live retries or removal occur.

The freestanding compiler emits zero-fill calls for stack aggregates. Target
Forge exports no `memset`; a private byte-loop supplies that language runtime
operation. `forge/mem.h` needs an explicit C linkage wrapper for its C exports.

Forge dispatches initialization before original `sApp::run`, before the quest
menu/detail consumers begin. This installation boundary and emulator cache
behavior need runtime acceptance. The private backend retains the existing
direct guest code-write behavior and kernel cache flush; it does not establish
native Switch portability. Ryujinx's separate APSR issue is outside this plugin;
the getter uses a standard function-entry hook with no displaced GE operation.

## Actual package evidence

The recipe hashes listed packages and resolves imports against each actual
Forge NSO dynamic table. `binary-validation.json` records those identities.
The current Eden Forge differs from the historical baseline record; a folder
or configured package does not prove activation. No emulator configuration or
installed payload is changed by this recipe.

Demand is one additional CodeMemory object and 4 KiB, plus the reported NRO
BSS. Runtime headroom is not reserved or proven by a static inventory; allocation
failure leaves the getter unchanged. The sole replacement path is the new
plugin NRO. Other title-getter hooks conflict and cause initial rejection.

Status: static checks are required before packaging. Eden and Ryujinx gameplay
acceptance is **NOT RUN**. Do not label r1 compatible or release-ready until both
[manual checklists](MANUAL_TESTS.md) pass against the exact artifact.
