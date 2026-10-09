# Key Quest Markers

Prefixes progression key quest titles with `[KEY] ` using the native quest-group
classification. Completed keys remain marked; urgent and training categories
retain their native titles. The plugin has no settings panel.

Current local release: **r2**, READY_TO_DISTRIBUTE and unpublished.
[Installation and settings](DISTRIBUTION_README.md); [status and payload hashes](DISTRIBUTION.json).

## Development and evidence

Use [DEVELOPMENT.md](DEVELOPMENT.md) for pinned inputs, build/test/package/export
commands. [Runtime evidence](RUNTIME_RESULTS.json) retains the version and limits of user
reports. [THIRD_PARTY.md](THIRD_PARTY.md) records development provenance;
[DISTRIBUTION_NOTICES.md](DISTRIBUTION_NOTICES.md) supplies release credits.


R2 has host/ARM/static cleanup evidence and no new gameplay run.
[CLEANUP_VALIDATION.json](CLEANUP_VALIDATION.json) records the checks.
Prior r1 acceptance covers Eden Village 1/2-star and Hub 1-star on the
progression save, and Ryujinx full-rank coverage. Higher ranks on Eden and
individual language/screen combinations were not all enumerated.

Technical references: [native research](RESEARCH.md),
[compatibility and storage constraints](COMPATIBILITY.md),
[runtime results](RUNTIME_RESULTS.json) and [manual tests](MANUAL_TESTS.md).
Missing/unsupported data returns the original title. Native UI retains title
pointers, so hot unloading is unsupported.
