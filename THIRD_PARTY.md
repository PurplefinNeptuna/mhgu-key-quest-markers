# Development provenance

- forge-rs 1.5.0, revision `d1865b68e9b194eb3eacc8bd71bbf601a5fac63e`,
  https://github.com/Fexty12573/forge-rs. Vendored source and MIT license are unchanged.
- Forge native Hook declaration matches the maintained 1.5.0 ordinary-hook API;
  https://github.com/Fexty12573/forge, Fexty's fork of Jeffi's original Forge.
  Its copied header supplies the independent
  compiler layout fixture, not a second hook implementation.
- `src/svc.S` derives from libnx ARM32 syscall wrappers, licensed MIT by the
  Hydrosphere Developers; https://github.com/switchbrew/libnx. Three private
  entry names avoid conflicting loader exports. Applicable MIT text is included.
- Vendored registry packages retain their own license files and Cargo checksums.
  `research/sysroot-Cargo.lock` records the prepared nightly's build-std resolver.
  The Rust toolchain itself is an externally supplied build tool.
- Original game assets are by Capcom. Copied English HD common archive input:
  `fd8cd4521cb5c5d07e0d1e5e7275aaf5ecbcfd34d20aae2b6f880ab65b22f438`.
  The external HD assets are from MHGU HD Project by Monkbreh / Monke,
  https://github.com/Monkbreh/MHGU-HD-Project. Its public README describes ESRGAN
  upscaling; specific models and training datasets are not disclosed. The read-only
  fixture ships none of these assets; native children reference the already-loaded
  emblem. No artwork is generated.
- GUI format reference: https://github.com/RTHKKona/MHGU-Modding,
  `templates/gui_mhgu.bt`; saved Ghidra/DTI research is summarized in the audit.
- Owned resource/import/export helpers are bounded project snapshots. There are
  no sibling-mod dependencies in a standalone export.

Game archives and native binaries are external, copied inputs and excluded from
source exports. Release notices separately cover the current runtime contents.

Rust `core` and `alloc` are compiled into the ARM plugin by `.cargo/config.toml`
with `compiler_builtins` memory support. The pinned toolchain is
`c36f1457196e315bc204b9564a6a5a7fe7f5a51f`. `licenses/RUST-MIT.txt` is copied
unchanged from
https://github.com/rust-lang/rust/blob/c36f1457196e315bc204b9564a6a5a7fe7f5a51f/LICENSE-MIT
(SHA-256 `b71bd43a069ca0641a9ecfe585ca7b3c53b5cc1608f8b68321168698e28b5ea1`).
These notices cover the linked libraries. The compiler and host-only dependencies
are build tools and are excluded from release notices.

The linked ARM ELF contains
`core::unicode::unicode_data::white_space::WHITESPACE_MAP` as well as
`core`, `alloc` and `compiler_builtins` symbols (`nm -C --defined-only`).
The pinned toolchain's `COPYRIGHT-library.html` identifies
`library/core/src/unicode` as Unicode-3.0, copyright 1991-2024 Unicode, Inc.
`licenses/UNICODE-3.0.txt` is copied unchanged from that toolchain's
`share/doc/rust/licenses/Unicode-3.0.txt`
(SHA-256 `f5062c9a188d81dfe66b56db4182dcf9e4b17c0d9b0d311a8e20b3a1b075c443`).
