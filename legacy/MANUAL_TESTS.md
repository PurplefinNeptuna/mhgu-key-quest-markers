# Key Quest Markers r1: manual acceptance

Run this checklist independently on **Eden** and **Ryujinx**. Record emulator
version, main build, enabled package set and exact NRO SHA-256. Installation and
activation require their own authorization. Fully restart after package changes.
Retain the fresh emulator log before another run. Existing saves are used as-is.

## Save coverage

- **Ryujinx: full save.** Cover Village low/high, Hub low/high and G rank,
  including completed keys across the available tiers.
- **Eden: personal progression save.** Cover currently unlocked quests and
  menus, including incomplete keys and any completed keys already available.

Keep each emulator's existing save. No transfer, replacement or save editing is
needed. Higher ranks locked on Eden are an availability limit, not a failed
marker test; record that coverage as untested on Eden.

## Required on each emulator

- [ ] Game boots and an existing save loads; Forge lists Key Quest Markers as active.
- [ ] The plugin row is small, unframed and initially closed; nested diagnostics open normally.
- [ ] Keys in the ranks unlocked on this save show one `[KEY] ` prefix.
- [ ] Verify representative keys: Find the Ferns / Wipe Out! (Village 1★), and Pecking Order (G1), where unlocked.
- [ ] Ordinary, urgent and training quests have no added prefix.
- [ ] Completed keys remain marked, and native completion/urgent icons remain correct.
- [ ] First/last rows, scrolling and page changes preserve selection and title presentation.
- [ ] Quest details retain the correct title after selecting several different quests and reopening the list.
- [ ] Longest available titles fit or use the game's normal scrolling/clipping without corrupting adjacent rows.
- [ ] Check each available game language; fallback titles remain correct and Unicode text is intact.
- [ ] Inspect other quest-name screens, including accepted quest information, multiplayer listings where available and result/history screens. Record prefix coverage and any layout issue.
- [ ] Markers continue with the Forge row/menu closed; village transitions and a quest departure/return work.
- [ ] Fully restart and repeat a list/detail transition; no save/config write was introduced.
- [ ] Latest emulator log shows the expected initialization status and no new plugin fault; retain exact log and hashes with the gameplay report.

## Full-rank coverage on Ryujinx

- [ ] Village low/high, Hub low/high and G-rank keys show one `[KEY] ` prefix.
- [ ] Completed keys remain marked across those categories, with native completion marks intact.

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
