# Key Quest Markers r1: manual acceptance

Run this checklist independently on **Eden** and **Ryujinx**. Record emulator
version, main build, enabled package set and exact NRO SHA-256. Installation and
activation require their own authorization. Fully restart after package changes.
Retain the fresh emulator log before another run. Existing saves are used as-is.

**Accepted 2026-10-06.** The user checked every applicable item below and reported
"all checklist passed". Logs and installed-file hashes were reviewed; detailed
evidence and emulator messages are recorded in [RUNTIME_RESULTS.json](RUNTIME_RESULTS.json).
The checkmarks record manual results, not an automated gameplay test.

## Save coverage

- **Ryujinx: full save.** Cover Village low/high, Hub low/high and G rank,
  including completed keys across the available tiers.
- **Eden: personal progression save, Village 2★ / Hub 1★.** Cover Village 1★
  and 2★ plus Hub 1★, including incomplete keys and completed keys already
  available. Higher Village/Hub tiers and G rank are outside this save's coverage.

Keep each emulator's existing save. No transfer, replacement or save editing is
needed. Higher ranks locked on Eden are an availability limit, not a failed
marker test; record that coverage as untested on Eden.

## Required on each emulator

- [x] Game boots and an existing save loads; Forge lists Key Quest Markers as active.
- [x] The plugin row is small, unframed and initially closed; nested diagnostics open normally.
- [x] Keys in the ranks unlocked on this save show one `[KEY] ` prefix.
- [x] Verify representative Village 1★ keys: Find the Ferns / Wipe Out!, where available.
- [x] Ordinary, urgent and training quests have no added prefix.
- [x] Completed keys remain marked, and native completion/urgent icons remain correct.
- [x] First/last rows, scrolling and page changes preserve selection and title presentation.
- [x] Quest details retain the correct title after selecting several different quests and reopening the list.
- [x] Longest available titles fit or use the game's normal scrolling/clipping without corrupting adjacent rows.
- [x] Check each available game language; fallback titles remain correct and Unicode text is intact.
- [x] Inspect other quest-name screens, including accepted quest information, multiplayer listings where available and result/history screens. Record prefix coverage and any layout issue.
- [x] Markers continue with the Forge row/menu closed; village transitions and a quest departure/return work.
- [x] Fully restart and repeat a list/detail transition; no save/config write was introduced.
- [x] Latest emulator log shows the expected initialization status and no new plugin fault; retain exact log and hashes with the gameplay report.

## Full-rank coverage on Ryujinx

- [x] Verify Pecking Order (G1) as a representative G-rank key.
- [x] Village low/high, Hub low/high and G-rank keys show one `[KEY] ` prefix.
- [x] Completed keys remain marked across those categories, with native completion marks intact.

Acceptance requires the shared checks on both emulators and the full-rank
checks on Ryujinx. Report Eden's locked-rank coverage separately; a Ryujinx
result does not establish those screens' behavior on Eden.

## Availability and limits

Record inaccessible ranks, languages or online screens as **not tested**, with a
reason. The automatic resource comparison proves the 118-ID classification;
spot checks do not prove every UI consumer. A static build, resolved imports,
or successful boot alone does not complete this checklist.

Do not deliberately load an unsupported executable or inject a conflicting
hook during normal play. Those rejection paths are covered by host/byte checks.
Any runtime fault needs fresh logs and the actual active package set before
attributing it to this plugin or the emulator.
