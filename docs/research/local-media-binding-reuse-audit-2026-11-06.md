# Complete-binding evidence reuse audit — 2026-11-06

This is a source comparison, not another native execution or performance pass.
It scopes the remaining C6b refresh without rewriting accepted HMP binding code.

## Existing evidence retained

The [October 2 complete-binding study](local-media-complete-binding-sample-2026-10-02.md)
measured HMP `b07890ec7af4e773f575e13b3db801aa1d3e5fd3` against native
`8afaab3703e336d72a72c812dd2dd249f04f166a`. Its 72 timing cells, 44 Python
allocation cells, 20 fresh-process RSS rows and 500 writer phases remain
historical evidence for that exact sample. Their controls, refusal assertions
and explicitly accepted residual/ABA outcomes must be reused, not relabeled as
new execution or replaced by an atomic-snapshot claim.

## Current source comparison

Root compared immutable Git blobs with HMP
`8d096b5857a514a0c6b61fdf8cc19a4e2f416dde`. Independent read-only review
confirmed the source hashes and these eight byte-identical bridge methods:

| Method | Reusable implementation evidence |
|---|---|
| `_db_home` | Same home/database capture |
| `_phone_proof` | Same own-conversation classification |
| `_bot_chat_proof` | Same canonical title/lineage classification |
| `media_eligibility` | Same two-proof composition |
| `bind_media_batch` | Same complete binding and rechecks |
| `_media_rows` | Same native-to-sidecar capture |
| `latest_with_media` | Same latest read twin |
| `after_with_media` | Same incremental read twin |

The complete `local_media_batch_binding.py`, `local_media_registry.py` and
`reads.py` files are also byte-identical. The scanner, sidecar and candidate
files differ, including reviewed R1/C1a changes. Their old performance results
are not silently transferred to the amended path.

On native `ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df`, actual owning
`SessionSessionsMixin.get_session` and `SessionMessagesMixin.get_messages` /
`get_active_message_ids` implementations differ from the old sample. The
facade imports these owners; comparing a nonexistent facade method would not
establish identity. Native helper closure and database lifecycle must therefore
be included in the current execution, not inferred from public signatures.

## Remaining current-candidate work

Refresh the established complete-binding measurement using the real current
native APIs, unchanged HMP capture/classification/binding/registry, and current
scanner/sidecar/candidate code. Retain the declared Bot Chat/Phone, candidate-
count, short/near-limit lineage and synthetic large-prompt shapes, with public
native reads verifying that the intended fixture was actually materialized.
Retain writer controls, refusal cases and observed residual/ABA assertions;
reported timing/allocation outcomes must belong to the current execution.

Use disposable source-bound homes and owned workers/processes. No live prompt,
conversation, credential, gateway, profile setting or provider is an input.
No old temporary script is executed merely because a historical receipt exists.
Any recovered harness must be read/reviewed and bound to the current source and
runtime before execution; otherwise implement the documented method as a
versioned fixture, reusing its established assertions.

No new HTTP, provider, Linux or physical-device prerequisite is added to C6b.
Those remain separate feature/release requirements. Existing native serving and
T12 evidence do not substitute for C6b timing/allocation/writer outcomes. This
audit does not close C6b, impose per-version allowlists, or resolve G-M1/G-M2.
The reviewer ran no tests, native operation or measurement.
