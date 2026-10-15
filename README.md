# Native Quest Badges (Rust)

**r14 — READY_TO_DISTRIBUTE. Original emblem only.** The user accepted the
unchanged r14 NRO on Eden/Linux on 2026-10-15. Ryujinx and native Switch gameplay
remain unconfirmed; individual cases were not separately enumerated.

Native 32×32 badges share an empty request slot and sit four pixels left of a
visible request bubble. Needed keys are orange-red #E74725, active urgents purple
#9B4DCA, and completed/inactive badges grey #808080. Native AutoScale fits long
titles and resets on row reuse. Special Village urgent pairs are included.

The game owns texture children, drawing and cleanup. The plugin references the
already-loaded English HD lobby emblem; it ships one NRO and no game assets or
ARC replacements. Runtime source and the tested NRO were not changed during
promotion. The accepted binary retains its bounded startup/first-page diagnostic
logs; there is no per-frame logging.

- [Installation guide](DISTRIBUTION_README.md)
- [Independent builds and packaging](DEVELOPMENT.md)
- [Native ownership, resource and ABI audit](docs/NATIVE_AUDIT.md)
- [r14 runtime acceptance](docs/RUNTIME_R14.json)
- [Promotion and archived comparison receipts](docs/PROMOTION_R14.json)
- [Special-urgent native/Kiranico cross-check](docs/SPECIAL_URGENTS.json)

The original r14 release is under `build/key-quest-markers-rs/releases/r14/` in
the workspace. Small-emblem comparisons are archived and are not release options.
Historical r9/r11 evidence and original C++/PC releases remain preserved.
