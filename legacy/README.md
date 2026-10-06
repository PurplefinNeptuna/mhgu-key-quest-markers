# Key Quest Markers r1

Ready to distribute. Marked 2026-10-06 by the user after the scoped
Eden/Ryujinx acceptance. The package is local and has not been published.

Forge plugin for MHGU Nintendo Switch 1.4.0 on Eden and Ryujinx.
It prefixes progression key quest titles with `[KEY] `, including completed
keys. It uses the native quest-group classification by quest ID. Kiranico was
used to verify the 118-key interpretation; the plugin needs no website access.

The prefix follows the native quest-name getter into quest lists and details.
Its other callers need the manual checks below. Native completion marks,
sorting, unlock conditions, language selection and fallback remain native.
Urgent and training categories receive no prefix. The plugin is always enabled;
its compact Forge Plugin UI row displays status and nested diagnostics.

## Build and package

```bash
python3 scripts/key_quest_markers.py all
```

Requires the preserved executable/quest research inputs, pinned local Forge
headers, existing devkitPro container and host C++ compiler. The recipe validates
input hashes, all seven localized title inventories, the saved Kiranico match,
host tests, native ABI and imports against actual listed Forge binaries.

Output: `build/key-quest-markers/key-quest-markers-r1.zip`.
Its sole entry is `romfs/nativeNX/plugins/key_quest_markers.nro`.
The unpacked package is `build/key-quest-markers/package/`; the manifest,
checksums, validation reports and checklist are beside it.

Preparation does not install, enable or launch anything. The user accepted r1
on 2026-10-06: Eden Village 1★/2★ and Hub 1★; Ryujinx full-rank coverage.
The installed NROs match the staged candidate. See [runtime results](RUNTIME_RESULTS.json),
[completed manual tests](MANUAL_TESTS.md) and
[compatibility and implementation constraints](COMPATIBILITY.md).

Research: [verified data and native callers](../../docs/KEY_QUEST_MARKERS_RESEARCH.md).

## Runtime failures

An unsupported build or a pre-existing patch of the getter leaves the plugin
inactive. Missing quest data, unknown/conflicting IDs, an unreadable or oversized
title, cache contention or full storage returns the original title. There is no
save/config writer. Restart the game after package changes; hot unloading is
unsupported because native UI retains title pointers.
