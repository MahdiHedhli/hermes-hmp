# Local generated media: bounded active-set scan, link and recheck (2026-10-01)

Research evidence for root and Opus review. Not a design, wire shape, qualification or product change.
It prototypes the root-decided scan for G4 outside `server/hmp_plugin` and checks it against the real
native `SessionDB`. There is no route, registry, transport, authorization claim, producer hook, media
reference, retained copy or copied SQL. G1/G2 and the broader matrix were not rerun. Shared wire is not
frozen.

## What exists

| File | Role |
| --- | --- |
| `tools/research/local_media_active_scan.py` | Stdlib-only scanner (`scan_active_set`, `recheck`). Reads only native `get_active_message_ids` and `get_messages(after_id, limit)` |
| `tools/research/local_media_active_scan_fixture.py` | Parent/child fixture: exact independent `8afaab37…` build, own `.venv` interpreter, disposable home, real native writes at the scan seams |
| `tools/research/tests/` | 28 scanner unit tests on a fake store (parsing, bounds, bracket logic only) and one test that runs the native fixture |

The scanner takes a caller-provided tip, the selected tool row ID and a `current_tip` callable. It does
**not** authorize eligibility, device or profile: HMP must do that freshly before and after, and
`current_tip` must report what that check resolves to now. The package module may operate on caller data;
its `repr` and `report()` carry closed reasons, counts and 12-hex digest prefixes, never IDs, content or
paths (asserted by a unit test and a native case).

## Rules implemented (root decisions)

- **Bracket:** tip callback, `ids0`, keyset pages of 128, `ids1`, tip callback. Accept only if `ids0 == scanned
  IDs == ids1` and the tip is unchanged. IDs must be a strictly increasing list of exact `int` (not `bool`).
  More than 4096 active IDs refuses before any page is read. No internal retry.
- **Uniqueness over the entire active set**, not a 256 window: exactly one tool row with the call ID
  whatever its tool name; exactly one declaration across active assistants (outer IDs and any inner `id`
  or `call_id` an entry actually declares; none is required); the declaring row is outer and has a lower
  ID than the selected tool row.
- **Positive shapes:** direct `image_generate`, modern `tool_call {calls: [one image_generate entry]}`, and the
  observed legacy `tool_call {name: "image_generate", arguments}`. A
  multi-entry bridge refuses as ambiguous. The tool row must be named `image_generate`.
- **Uncertain means refuse globally** (any active assistant row): `tool_calls` that is not a non-empty
  list (so a stored or decoded `[]`, or a malformed blob, which native decodes to `[]`), a non-mapping
  call, a missing/empty/over-256/NUL/surrogate ID, a bad `function`, bridge arguments that are not a
  string within 64 KiB UTF-8, not JSON, or not an object with `calls` or `name`, an invalid inner ID, more
  than 64 declared IDs in a row or 4096 total. `NULL` means no calls (native writes `NULL` for an empty list;
  checked on the real writer).
- **Budget:** 4 MiB, UTF-8 weighted. Each inspected value costs 8 plus, for a string, its UTF-8 length,
  counted by a chunked walker without a full encoded copy; lone surrogates refuse; containers are
  walked iteratively to depth 32 and visits are capped by the budget. Charged: row ID and role, tool-row
  call ID and name, the full `tool_calls` of every assistant row, and the selected tool row's content.
  Other content is not inspected and not charged. Exactly 4 MiB is accepted and 4 MiB + 1 refuses.
- **Selected result:** at most 64 KiB UTF-8 before `json.loads`; an object with `success is True`, no
  `error` key and a string `image` of 1 to 4096 characters without NUL. Only that candidate fact is kept;
  assistant `MEDIA:` text is never authority. Confinement to the selected profile cache is G3's.
- **Digests:** tool row over ID, name, call ID and full raw content; assistant row over ID, role and
  canonical `tool_calls` (content excluded, because native repair fills blank assistant content in
  place). Canonical serialization runs only after the bounded walk.
- **Recheck** (after the caller's file read): same tip, identical active ID list, and exactly the two
  selected rows re-read; only their digests must match. No second full scan.

## Native fixture results (build `8afaab37`, tree clean before and after)

71 cases (the legacy case flipped from `shape_unsupported` to `ok`; one fixture run after the repair), 71 matched their expected closed reason, 0 mismatches (run directly and inside the test).

| Group | Cases | Observed |
| --- | --- | --- |
| Positive | 13 `ok` | direct; one-entry bridge; legacy single `{name, arguments}` bridge (`bridge_legacy_one`, the G1-observed equivalent; was refused before the repair); unique inner ID; `tool_calls=[]` written as `NULL`; 4096 rows; declared-ID total exactly 4096; byte budget exactly 4 MiB; 4 recheck passes; the redaction check |
| Rows and limits | 4097 rows → `too_many_rows` (0 pages read); 4096 rows → 33 reads; 4097 declared → `declaration_limit`; 65 calls in a row → `declaration_limit`; 4 MiB + 1 → `budget_exceeded` | as listed |
| Uniqueness | duplicate tool row before (outside any 256 window) or after the selected row, duplicate outer declaration, duplicate declared inner ID, missing declaration, assistant not before the tool row | each refused with its own reason |
| Malformed / uncertain | 17 `tool_calls_uncertain`, 1 `malformed` (lone-surrogate ID, written natively and read back) | includes stored `[]` and a garbage blob (SQL, test only), non-list value, non-mapping, missing/empty/257-char/NUL IDs, bad function, bad bridge arguments, oversized bridge arguments |
| Shape | multi-entry bridge `bridge_ambiguous`; other entry name, other outer function → `shape_unsupported` | |
| Result | 8 `result_not_candidate`, 1 `result_too_large`, 1 `tool_name_mismatch`, `MEDIA:` text only → `declaration_missing` | |
| Selection | not a tool row, deactivated, in a retired parent's rows (not in the tip's active set), boolean row ID | closed refusals |
| Change between reads | append, deactivate and rewind between pages; deactivate before the final ID list → `rows_changed`; tip change mid-page and before the first read → `tip_changed` | native writes at the seam |
| Recheck | unchanged `ok`; **native assistant content repair accepted**; tool content or assistant `tool_calls` edited → `selected_changed`; append, deactivate unrelated or selected → `rows_changed`; tip change → `tip_changed` | |
| Characterized escapes | an unrelated row deactivated then reactivated, and an unrelated row's content swapped, between scan and recheck → **both `ok`** | see limits |

Isolation (all true): `hermes_state` loaded from the checkout, no module from the real Hermes home, owning
files (`hermes_state.py` `e66115733214`, `hermes_state_messages.py` `c9be693fe268`, `hermes_state_sessions.py`
`17082eace7e2`, `agent/transcript_repair.py` `2f66bd8b605b`) unchanged, 0 network connects attempted, child
stdout 0 bytes, child stderr 2 lines (native "falling back to []" warnings from the deliberate malformed
blobs; no scratch path), scratch removed.

Direct SQL (through the native writer) is used only in fixtures, labelled `test_only_sql`, for: storing a
`[]` or garbage `tool_calls` blob and a non-list value (native normalizes these away on write), editing a
tool row or assistant `tool_calls` in place, editing an unrelated row, and reactivating a row. Everything
else is a native method.

## Open limits

1. **Native allocation is not bounded.** `SELECT *` materializes and decodes the whole page, including
   unrelated columns, and the ID list is uncapped, before this module counts anything. The budget bounds
   HMP-side work only. Inside the trusted-database boundary, as for today's text reads.
2. **Availability is all-or-nothing per chat.** One malformed assistant `tool_calls`, one bridge call with
   arguments over 64 KiB, more than 4096 active rows, more than 4 MiB of inspected values, or any write
   during the scan refuses every image in that chat until compaction or a retry.
3. **No atomicity or epoch.** Two cases above show an unrelated row undone or content-swapped between the
   reads escapes detection. This is the documented trusted-operator boundary, not a fix.
4. **Legacy single-entry bridge accepted only exactly as `image_generate`.** `{name: "image_generate",
   arguments}` at the top level (native normalizer: `calls` absent) links like the one-entry list. Still
   refused: `calls: null` with `name`, `calls` as a string or dict, other or whitespace names, a wrapper-named
   tool row, multi-entry. No broader parser or bridge acceptance.
5. **Inner ID key names** (`id`, `call_id`) are an assumption: G1 modern entries carry none.
6. **Unbounded string scan.** `str.isascii()` in the UTF-8 weight measure scans a whole string before any
   early stop, so one very large native or trusted string is scanned once, unbounded; same constant-factor
   class as limit 1. The ID-list length cap is checked before any element is iterated (`too_many_rows` at the
   first read, `rows_changed` at the second read and in recheck).
7. **Arguments deliberately uninspected.** Direct `function.arguments` and each bridge entry's `arguments`
   are not validated (bridge wrapper arguments only get the 64 KiB cap and structure parse). Linkage rests on
   the outer call ID plus a strictly successful result.
8. **Provider call-ID reuse** across turns makes every image in that chat refuse (duplicate tool row or
   ambiguous declaration): an availability limit.
9. **Test seam.** The `seam` argument is test-only (production passes `None`); its exceptions are not
   wrapped. The tip callback is production-facing: an exception, a non-`str` result or a hostile
   comparison closes as `tip_changed` with no exception text.
10. One native build, one interpreter (Python 3.14 child; post-repair unit tests under 3.14), Python-level network
   denial, synthetic rows only, no real generation or file.
11. **Test invocation:** from the repo root pytest 9.1.1 tries to import the root `__init__.py` and errors,
   for existing suites too (`tools/fixtures/tests` fails the same way). The run below used
   `cd tools/research/tests && python (3.14 venv) -m pytest -c /dev/null --rootdir=. --confcutdir=. .`.

## Checks run

- After the repair: 28 unit tests passed (all, small), and the native fixture test once: 1 passed, 71 cases, 0 mismatches. No new native source, matrix, G1 or G2 run. Ruff is not available in the repair environment and was **not rerun**; the pre-repair Ruff result does not cover the edits. Three `noqa` from before: one internal control-flow exception name in the scanner, two fixed-argv subprocess calls in the fixture.
- Native checkout: HEAD matches, tree clean before and after, owning files unchanged.
- `check_plugin_surface`, `scan_private` and server/tools Ruff: pre-repair results only, not rerun.
- Not run: G1/G2, the full matrix, build, install, live host.
  Nothing staged, committed or pushed.

## Hashes (SHA-256)

| File | SHA-256 |
| --- | --- |
| `tools/research/local_media_active_scan.py` | `81eb6880f396ad3c2a244c875753887332336da4c4a2a68569f3e7c455b8b4c2` |
| `tools/research/local_media_active_scan_fixture.py` | `a2ca094769b92b640e0b51dfffd6a7a8327aea3244fc605818ee84031c1fe19e` |
| `tools/research/tests/test_local_media_active_scan.py` | `aae2acb6247105417b4c3d997e7ccef172f5d54cb61fac3e006e4851832ca7ed` |
| `tools/research/tests/conftest.py` | `0e6688238cfacece68e270603e677879676cc91f5708b05eb5fbd6a80ff19fe7` |

## Root acceptance checkpoint

Opus independently accepted the repaired bounded research module: 28 unit cases passed and
causal mutations caught the callback, early row cap, phase reason, legacy linkage and digest
exception repairs. The worker's one native rerun observed 71 expected outcomes with no
mismatches; Opus did not duplicate it. Root separately passed six callback/cap/legacy cases.
Root strengthened the optional recheck regression with a digest-call spy so oversized values
must be refused before serialization; that focused case passed. The test lambda binds its
iteration variable to satisfy configured lint; module and fixture bytes remain exactly those
reviewed by Opus. Configured pinned Ruff, plugin-surface and private-data scans passed after
the repair, with no new suppressions. This supersedes the pre-repair scanner status above.

Accepted as research only: no authenticated serving route, device grant qualification,
transport, reference registry, wire contract, build or installed local-media feature follows
from this checkpoint.
