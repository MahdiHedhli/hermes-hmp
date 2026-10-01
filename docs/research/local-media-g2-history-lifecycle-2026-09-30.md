# Local generated media: G2 native history lifecycle (2026-09-30)

Research evidence for root review. Not a design, wire shape, qualification, eligibility policy or product
change. It adds one scenario, `history_lifecycle`, to the accepted G1 fixture. No media reference, route,
grant, token, candidate extractor, reference interface or wire shape is introduced, and `pair_observation`
in the fixture is a counting helper, not that interface. The five accepted and four modern scenarios were
**not** run again.

## What this is and is not

Storage-API characterization: what build `8afa` SessionDB's own methods do to one synthetic image
tool-call/result pair. The rows are written through the real `SessionDB.append_messages_batch`; every later
change is a native method. The fixture contains no SQL write and no copied SQLite implementation (a test
parses the history functions and refuses `execute`, `sqlite3` and write-statement text). Results say nothing
about HMP authorization, per-bot grants, an HMP adapter, a device, or the whole HMP chain.

## Binding

| Item | Value |
| --- | --- |
| Worktree | `test/local-media-active-history`, base `97316ad` |
| Hermes build | independent checkout `8afaab37…`, HEAD matches, tree clean before and after (parent check) |
| Runtime | the checkout's own `.venv`; `hermes_state` and the other imported modules come from that source; 0 modules from the installed home outside the interpreter base |
| Guards (unchanged, reused) | `validate_native_src`, `validate_scratch_root`, `prepare_evidence_dir` (fresh 0700), child allow-list environment, Python-level IP and Unix denial (no loopback port is allowed here: no model server), `RLIMIT_FSIZE`, 120 s child deadline with process-group kill, bounded 0600 result file, streamed 0600 stdout/stderr, scratch removal |
| Observed | stdout 0 bytes, stderr 0 bytes, IP and Unix contacts blocked 0, scratch removed, `source_unchanged` true over **25** native files |
| Seed | one valid 1x1 PNG from `synthetic_png()` placed in the profile cache by the fixture (never an untrusted path); a synthetic session of user, one-entry `tool_call {calls:[image_generate]}` assistant row, successful `image_generate` result linked by the outer id, final answer |
| Restore target | only `<scratch>/hermes/profiles/alpha/restore_probe/state.db`, checked by `validate_restore_target` (shape, symlink, inside scratch, not the primary database, not inside or holding a live Hermes home) earlier, before the snapshot and later history, and again immediately before `_safe_restore_db` (`guarded_restore`) |

## Observed (build `8afa`, one run, all steps returned; "pair" = active assistant call row plus active result row)

| Native API | Observation |
| --- | --- |
| baseline `append_messages_batch` | 4 rows, ids consecutive, pair complete; default read equals the active rows of the audit read |
| `archive_and_compact`, watermark below the call row (full tail clone) | old pair rows `active=0, compacted=0`; 4 new active rows with new, higher ids, 2 of them the pair clone; clone payload identity equals the old; the same call id now sits on 2 assistant and 2 result rows across the retired and active sets; active pair complete; the session id (the tip) did not change while the active ids did; no inactive row was reactivated |
| `archive_and_compact`, watermark between call and result (one-half tail clone) | old call row `active=0, compacted=1`; old result row `active=0, compacted=0`; only the result is cloned; **active pair incomplete** (0 call rows, 1 result row, result still parses as success); `tool_call_count` 0. The deduped display read (`include_compacted`) still shows 1 call row and 1 result row |
| `replace_messages(archive_dropped=True)`, diverging suffix | pair rows `active=0, compacted=0`; the kept prefix row keeps its id; pair incomplete |
| same, identical prefix plus one new row | the 4 original rows keep their ids and stay active; 1 new row; pair complete (a replace can leave the pair untouched) |
| `replace_messages` default | pair rows are deleted (absent from the audit read); re-appending the identical payload gives **new** ids (no reuse), equal payload identity, pair complete again |
| `rewind_to_message` to the first user row | 6 rows rewound, `rewind_count` 1, pair rows `active=0, compacted=0` but retained; to the second user row: 2 rewound, pair and its ids unchanged |
| `deactivate_message` on the result or on the call | returns 1, and 1 again on a second call (matched-row count, not a change count); the half pair that remains is incomplete |
| `clear_messages` | 0 rows in the audit read; re-seeded rows take new ids (no reuse); identical payload |
| `publish_compression_child` (pair as the parent's tail; called with `require_compression_lease=False`, bypassing the lease the real compression path holds) | child holds summary plus a pair clone (active, complete); the parent gets `end_reason='compression'` and **its rows stay `active=1` and unchanged**; `resolve_resume_session_id` and `get_compression_tip` return the child; a tip chosen before publication, then read, still returns a complete active pair from the closed parent with ids disjoint from the child's |
| Desktop branch via native `_persist_branch` (with its own `_BRANCH_COPY_FIELDS`) | tool row copied as 1 row, but **0** `tool_call_id` columns and **0** assistant `tool_calls` columns: pair incomplete in the child; `_branched_from` set; the parent still resolves to itself |
| gateway-shaped copy: native `_branch_row` applied through public `create_session` and `append_messages_batch`, input from `get_messages_as_conversation` (the async handler was **not** run) | pair complete in the child |
| `export_session` then `import_sessions` (payload `id` and `parent_session_id` edited) | each of 4 payloads imported (0 errors); new row ids; `source` kept; `origin_json` empty. A result row whose `image` names a path outside the profile cache, and one whose `image` is a non-string, were both **stored verbatim** (import validates nothing of the kind) |
| imported child with `parent_session_id` = a live, un-ended parent | `resolve_resume_session_id(parent)` **returns the imported child**; `get_compression_tip(parent)` does not. HMP `bridge.py:799-800` `_tip` calls the former |
| `get_resume_conversations(old parent id)` after a compression child | its model history is the closed parent's still-active pair (4 rows, pair present) |
| same-inode restore (`_safe_copy_db` snapshot, later history, `_safe_restore_db`) | inode and device unchanged (raw numbers are kept only in the private evidence file; the public report holds booleans); the original ids 1..4 are active again and the post-snapshot clones are gone; `conversation_generations` read via `latest_conversation_boundary` went `None` to 1 to **`None`**; `rewind_count` went 0 to 1 to **0**; the state_meta file stamp and stored `application_id` handle field (compared per handle, not a fresh `PRAGMA` query) are **unchanged**; a pre-restore open handle converges with a fresh handle, reports `_db_file_was_replaced()` false and accepted a write; that write took an id already used in the discarded later timeline |

## Findings and limits

1. **Native active history is not monotonic.** In-place compaction, replacement, rewind, deactivate and clear
   all retire or remove the pair; a re-append, an import and a restore can put an identical pair back (with
   the same ids only after a restore; a replace with an identical prefix never retires it). Re-check the
   active rows at request time; a mint-time check does not hold.
2. **Same-inode restore rolls history back and nothing observed detects it.** The inode, the file stamp and
   `application_id` did not change; the conversation generation and `rewind_count` went down; ids were
   reused. No restore-safe epoch was observed among the examined native fields (conversation generation, `rewind_count`, file stamp, `application_id`, inode); none was invented, and this is not a proof of absence elsewhere in the codebase. A
   different-file or swapped-inode restore was not run, so "database identity" has only been observed not to
   change under this restore.
3. **Row id plus call id is not a durable name for a pair.** The half tail clone leaves a result with no
   active call row. A closed parent keeps `active=1` rows after a compression child; "active" is only
   meaningful at the tip.
4. **Branch, import and tip selection.** The Desktop branch copy helper drops the call linkage (a Desktop
   branch child serves no pair); the gateway row helper keeps it. A session imported with a parent edge to a
   live parent became the resume tip. Import stored foreign and non-string image values verbatim; nothing was opened or served. None of this is
   described as newly generated media, and an eligible clone is a Hermes history copy, not a new generation.
5. **No consistent public snapshot was observed** in the sampled interleavings (stale closed parent, and separate public reads). This is not a proof that no API provides one. Tip selection and `get_messages` are separate reads
   (shown by the tip-then-read cases); `get_resume_conversations` is one row `SELECT` but its lineage walk is
   an earlier read (source: `hermes_state_messages.py:1376-1392`, `:1398`). No race was driven; the
   interleaves were sequential native calls between the two reads.
6. A cache file's persistence is not row authority: the PNG was unchanged across every step, including those
   after which no active pair existed.

Root minimum gaps: no examined native API gave a restore-safe database epoch or an atomic "tip plus rows" read.
Whether any of this needs product-side design is left to root.

## Not run

Gateway `/branch` handler, CLI `_handle_branch_command` (`hermes_cli/cli_commands_mixin.py:1383`) and the API
server branch (`gateway/platforms/api_server.py:3264-3270`) need a live runner or CLI object; follow-up with
source evidence only. Also not run: `rewind_user_turn`, `archive_and_compact` with `covered_ids`, restore of a
snapshot from a different database file, a swapped inode, a concurrent second process, and real concurrency
(no threads were raced). One provider shape, one synthetic call id, no HMP code.

## Hashes (SHA-256)

| File | SHA-256 |
| --- | --- |
| `tools/research/local_media_persistence_fixture.py` | `a6b9f5b9fe171136a566cdc02b98115104a67fe547867d1c2ed57e59f813907c` |
| `tools/research/tests/test_local_media_persistence_fixture.py` | `dcc80e098c540952a6628ac2ca616cc29202d1da563c9725a7bcefa598b6f516` |
| `tools/research/tests/conftest.py` (unchanged) | `e1912852e937671f985e6e066a948bb8c7e181614912e630fd5b295130fac242` |
| `local-media-delivery-paths-2026-09-30.md` (unchanged) | `c275be2780ac50b48f94713cd04c0fb0826b5b929a2150ec7e376e32ae0fe3e7` |
| `local-media-g1-persistence-2026-09-30.md` (unchanged) | `2a55eb5d561b239eb0e41bb95fa79aebf300518663b788b12027ad6496452b9b` |
| `local-media-g1-modern-tool-call-2026-09-30.md` (unchanged) | `541161b454c0e26543b9a25e2a09eafb8fba4da408b874db6f047f6288a2465b` |

Native files added to the pre/post fingerprint when a history scenario runs (first 12 hex characters), in
addition to the 16 listed in the modern note: `hermes_state_common.py` `54ad9c5d683a`,
`hermes_state_errors.py` `340226604dbf`, `hermes_state_sessions.py` `17082eace7e2`,
`hermes_state_compression.py` `c920bb587aa3`, `hermes_state_portability.py` `40f4e911bde9`,
`hermes_state_rewind.py` `c147473e80de`, `hermes_cli/backup_restore.py` `1b1bc5c87362`,
`hermes_cli/backup_sqlite.py` `ca8f443b8026`, `gateway/slash_commands_session.py` `b7cdb1be5aa1`.

## Checks run

- Own Python 3.14 virtual environment with pytest 9.1.1: the file collects 60 tests (57 non-native plus 3
  native aggregates). Focused run of the new tests only (2 new non-native tests and the new native
  test `test_history_lifecycle_native_observations`, selected by exact node id): 3 passed. The 3 old native
  aggregates (including the five- and four-case ones) were not run by the worker; the root ran them in a broad
  selection before this repair (58 passing at an earlier source hash, not this one) and then ran 56 passing
  (55 non-native plus the new native test, 2 old aggregates deselected) in 9.55s, also before this repair. Those
  root counts are historical, not for the current hashes.
- The native test now also checks that no `dev_ino` key reaches the public report (recursively) and that the
  private file keeps the raw numbers; with the sanitization removed it fails.
- Ruff 0.15.10 (the pinned 0.16.9 was not available locally; `--config server/pyproject.toml`): check on
  `server` and `tools` clean; format check clean for `tools/research`. No new `noqa`.
- `git diff --check` clean after the repair. `check_plugin_surface`, `scan_private` and `scan_logs` were not rerun
  after this repair. The old pytest temp-directory cleanup warnings remain.

## Run

```
python3 tools/research/local_media_persistence_fixture.py run --evidence <fresh private dir> \
  --scenario history_lifecycle
```

Raw synthetic rows are written only to `history_lifecycle.private.json` (0600) in the evidence directory;
the report holds ids, flags, counts, short payload hashes and closed enums.

## Root acceptance of the final research delta

Root reproduced the final three exact repair tests, including the one G2 native aggregate:
**3 passed**, with 81 existing pytest temporary-directory cleanup warnings. The earlier five- and
four-case aggregates were not selected in this final run. Fixture and test hashes above are unchanged.
Root also ran pinned Ruff 0.16.9 check and format, `check_plugin_surface`, `scan_private` and
`git diff --check`: all passed. No captured native logs were published or treated as log-scan clearance.

Independent Opus review accepted the repaired safety and privacy delta at these code hashes. Root
corrected its remaining note-only old-aggregate count from 3 to 2. This is accepted storage research;
G3 filesystem/raster and G4 scope/grant/race qualification remain open. No local media feature,
reference, authorization grant, device or release is admitted by this evidence.
