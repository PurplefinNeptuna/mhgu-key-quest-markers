# Development provenance

- forge-rs 1.5.0, revision `d1865b68e9b194eb3eacc8bd71bbf601a5fac63e`,
  https://github.com/Fexty12573/forge-rs. Vendored source and MIT license are unchanged.
- Forge native Hook declaration matches the maintained 1.5.0 ordinary-hook API;
  https://github.com/jeffi6375/forge. Its copied header supplies the independent
  compiler layout fixture, not a second hook implementation.
- `src/svc.S` derives from libnx ARM32 syscall wrappers, licensed MIT by the
  Hydrosphere Developers; https://github.com/switchbrew/libnx. Three private
  entry names avoid conflicting loader exports. Applicable MIT text is included.
- Vendored registry packages retain their own license files and Cargo checksums.
  `research/sysroot-Cargo.lock` records the prepared nightly's build-std resolver.
  The Rust toolchain itself is an externally supplied build tool.
- Original game assets are by Capcom. Copied English HD common archive input:
  `fd8cd4521cb5c5d07e0d1e5e7275aaf5ecbcfd34d20aae2b6f880ab65b22f438`.
  Retained HD assets are from MHGU HD Project by Monkbreh / Monke,
  https://github.com/Monkbreh/MHGU-HD-Project. Its public README describes ESRGAN
  upscaling; specific models and training datasets are not disclosed. This recipe
  generates no artwork and ships no replacement emblem atlas.
- GUI format reference: https://github.com/RTHKKona/MHGU-Modding,
  `templates/gui_mhgu.bt`; saved Ghidra/DTI research is summarized in the audit.
- Owned resource/import/export helpers are bounded project snapshots. There are
  no sibling-mod dependencies in a standalone export.

Game archives and native binaries are external, copied inputs and excluded from
source exports. Release notices separately cover the current runtime contents.
