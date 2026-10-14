# Native Quest Badges (Rust)

**Active DEVELOPMENT r2.** This plugin installs two native Forge hooks and colors
24×24 badges left of the quest rows. Red means a key still needed for current
progression, yellow means a currently offered available urgent, and grey means a
completed or obsolete key or an inactive/old urgent. Ordinary or unresolved quests
have no badge.

The emblem comes directly from the existing English HD lobby atlas. No extracted
image, new atlas, settings, configuration, overlay, counter or progression writes
are added. The original prefix plugin must be disabled during use so `[KEY]`
disappears from titles. Existing C++ and PC releases remain separate.

See [DEVELOPMENT.md](DEVELOPMENT.md) for standalone building,
[docs/NATIVE_AUDIT.md](docs/NATIVE_AUDIT.md) for the verified native paths and
[DISTRIBUTION_README.md](DISTRIBUTION_README.md) for installation and use.
Compiled ARM fixtures exercise the active callbacks through the native setter
boundary. Rendering, clipping and gameplay still need manual Eden/Ryujinx trials.
Build/package commands do not install, launch or change any emulator or save.
