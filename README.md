# Native Quest Badges (Rust)

**Active DEVELOPMENT r3.** Adds native 24×24 quest badges by creating GUI children
at runtime. Red means a key still needed for current progression, yellow means a
currently offered available urgent, and grey means a completed/obsolete key or an
inactive/old urgent. Ordinary and unresolved quests have no badge.

The badges reuse the already-loaded English HD lobby emblem. The package contains
one NRO; no ARC, atlas or other game asset is replaced. The game owns rendering and
object cleanup. There is no overlay, settings panel, configuration or progression
write. Forge lists the plugin as **Native Quest Badges r3** and logs failures at
ERROR level even with the default loader filter.

See [DISTRIBUTION_README.md](DISTRIBUTION_README.md) for installing a clean package,
[DEVELOPMENT.md](DEVELOPMENT.md) for independent builds, and
[docs/NATIVE_AUDIT.md](docs/NATIVE_AUDIT.md) for the native ownership and ABI audit.
Old C++/PC releases and earlier development candidates remain preserved.
Compiled fixtures execute native draw-list traversal and destructor cleanup;
actual pixels and gameplay still require a manual Eden/Ryujinx trial.
