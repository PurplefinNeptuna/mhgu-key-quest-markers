# Native Quest Badges (Rust)

**DEVELOPMENT r13 / r13-small. Fixes the special Village urgent pairs; manual acceptance is pending.** Implements native 32×32 quest badges by creating GUI children
at runtime. Red means a key still needed for current progression, yellow means a
currently offered available urgent, and grey means a completed/obsolete key or an
inactive/old urgent. Ordinary and unresolved quests have no badge.

Badges share an empty request slot and sit four pixels left of a visible request
bubble. Native AutoScale fits long titles and resets on row reuse.

The badges reuse the already-loaded English HD lobby emblem. The package contains
one NRO; no ARC, atlas or other game asset is replaced. The game owns rendering and
object cleanup. There is no overlay, settings panel, configuration or progression
write. Forge lists the plugin as **Native Quest Badges r13 / r13-small** and logs failures at
ERROR level even with the default loader filter. The development build also records installation, first hook entry and two bounded classification snapshots, without changing loader settings.

See [DISTRIBUTION_README.md](DISTRIBUTION_README.md) for installing a clean package,
[DEVELOPMENT.md](DEVELOPMENT.md) for independent builds, and
[docs/NATIVE_AUDIT.md](docs/NATIVE_AUDIT.md) for the native ownership and ABI audit.
Old C++/PC releases and earlier development candidates remain preserved.
Compiled fixtures execute native draw-list traversal and destructor cleanup.
The user confirmed r9 and r11 working on Eden/Linux; see [r9 evidence](docs/RUNTIME_RESULTS.json)
and [r11 evidence](docs/RUNTIME_R11.json). The new r12 size and alignment require
separate manual acceptance. Individual state/transition coverage and Ryujinx
play remain unconfirmed.

The original r12 and r12-small deliveries are preserved unchanged. r12-small
selected logical UV `(342,0,372,30)` on the same loaded atlas while keeping
r12 geometry and behaviour. See [comparison record](docs/R12_COMPARISON.json).

Both emblem variants share the special-urgent correction documented in
[the Kiranico and native cross-check](docs/SPECIAL_URGENTS.json). Original r12
and r12-small delivery bytes remain preserved.
