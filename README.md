# Native Quest Badges (Rust)

**DEVELOPMENT r1; inactive.** The plugin and English HD GUI candidate build and
package, but native progression availability and GUI attachment remain unverified.
This candidate does not install its row hook or display badges. It is not a working
replacement for the accepted Key Quest Markers plugin yet.

The intended behavior is a native 24×24 badge left of each quest row: red for a
currently needed key, yellow for an available current urgent, grey for completed
or obsolete keys and inactive/old urgents, and hidden for ordinary or unresolved
quests. The existing HD lobby atlas supplies the emblem; no extracted image,
new atlas, settings panel, configuration, overlay or progression changes are added.

See [DEVELOPMENT.md](DEVELOPMENT.md) for building and verification,
[docs/NATIVE_AUDIT.md](docs/NATIVE_AUDIT.md) for the unresolved gates, and
[DISTRIBUTION_README.md](DISTRIBUTION_README.md) for the candidate guide.

The existing C++ and PC releases remain separate. An eventual runtime trial must
disable the original prefix plugin so `[KEY]` is absent from list and detail
names. Preparation does not install, launch or change any emulator or save.
