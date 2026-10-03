# D4 interface review bundle

The authoritative wire contract is `docs/architecture/contracts/HMP_PHONE_ATTACHMENTS_V1.md` in
the HMP repository. Its mirror here and the Mobile spec 028 contract copy are byte-identical at
this freeze. `dart-interfaces.md`, `python-interfaces.md`, `pending-slot-codec.md`,
`canonical-hash.md` and `canonical-hash-vectors.json` are also exact mirrors between repositories.
Declaration snippets are documentation, not compilable implementations or runtime imports.

Normative/interface and bounded pure-source v4 checkpoints are independently accepted. Root's
exact-v4 Python56, existing contract/module regression115 and Dart71 tests passed with failures0;
four-path Ruff and eight-path Dart analysis clean. This qualifies only pure DTO/hash/classifier/
strict-codec/phase/restore/ports and fake-only causal work. No database migration,
encrypted owned-file format, real validator, native adapter, network transport, picker or route
implementation is admitted by this bundle. Full upload/Send/readback remains closed.
