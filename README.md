# Native Quest Badges (Rust)

**DEVELOPMENT r11. Fixes r10's title-class rejection; request-slot layout and native title fitting remain. r11 manual acceptance is pending.** Implements native 24×24 quest badges by creating GUI children
at runtime. Red means a key still needed for current progression, yellow means a
currently offered available urgent, and grey means a completed/obsolete key or an
inactive/old urgent. Ordinary and unresolved quests have no badge.

Badges share an empty request slot and sit four pixels left of a visible request
bubble. Native AutoScale fits long titles and resets on row reuse.

The badges reuse the already-loaded English HD lobby emblem. The package contains
one NRO; no ARC, atlas or other game asset is replaced. The game owns rendering and
object cleanup. There is no overlay, settings panel, configuration or progression
write. Forge lists the plugin as **Native Quest Badges r11** and logs failures at
ERROR level even with the default loader filter. r11 also records installation, first hook entry and two bounded classification snapshots, without changing loader settings.

See [DISTRIBUTION_README.md](DISTRIBUTION_README.md) for installing a clean package,
[DEVELOPMENT.md](DEVELOPMENT.md) for independent builds, and
[docs/NATIVE_AUDIT.md](docs/NATIVE_AUDIT.md) for the native ownership and ABI audit.
Old C++/PC releases and earlier development candidates remain preserved.
Compiled fixtures execute native draw-list traversal and destructor cleanup;
the user confirmed the preceding r9 works on Eden/Linux. Individual states/transitions and
Ryujinx gameplay remain unconfirmed. See [runtime evidence](docs/RUNTIME_RESULTS.json).
