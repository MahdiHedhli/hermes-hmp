# Phone attachment native primitives: runtime evidence (2026-09-30)

Discovery evidence for root review. This is not a qualification, not a wire freeze and not a
feature-ready claim. Root independently reviewed the fixture and bounded repairs and reproduced the native results; discovery evidence is accepted with the gaps below. It observes one archive
copy of a Hermes source tree; nothing here generalizes to a released build.

## Binding

| Item | Value |
| --- | --- |
| Native source | archive copy, provenance `ca705dbf` (**not a Git SHA attestation**; not a git repository) |
| Native interpreter | the source tree's `.venv` CPython 3.14.6, editable `hermes-agent` 0.0.0 install |
| Tool | `tools/fixtures/phone_attachment_primitives.py` (`run`), tests in `tools/fixtures/tests/test_phone_attachment_primitives.py` |
| HMP base | `847696d`; no HMP runtime, wire, API, auth, manifest or dependency file changed |

SHA-256 of each exercised native file, computed by the tool before and after the run; every pair
was identical (`source_unchanged: true`). Files also in the census table match its hashes.

| File | SHA-256 |
| --- | --- |
| `gateway/platforms/base.py` | `48425a540a7b07bae75fdae2c27051f0485a2154b33efc4d492f2660a0344929` |
| `gateway/platforms/event.py` | `b3d43c556bcbf6919d6b3e351ab9e4f8c83a86af73962a844f7f215d93af9110` |
| `gateway/platforms/media_cache.py` | `5a81fdbcd872eafcfe94bee6bf1ab0670a3b120e1d9a6fa283a4f490dc356370` |
| `gateway/run.py` | `c1184c3dd38d42a08cfec0a29538382ab33fe03d948faa02d607d17148aa601a` |
| `gateway/run_inbound.py` | `791849d5e2fe828fb1d1a7769efcb712b171bd632ebcfd553f6f412465345288` |
| `gateway/run_busy.py` | `e4baf0d89c3d035660be743543fc0504348619d17d7df2ddb28dfe066b666ddb` |
| `gateway/run_turn.py` | `2455db4176cbcd610174ab5ec8e741ed6de6d88a931a3b9491761901ddb2c61c` |
| `gateway/session.py` | `d274960c58869d456d0063358a8143562ccdbe9471d996e99841275789c4e998` |
| `agent/session_persistence.py` | `9c6f6bb2e0e785ee53499cbb0997a0e628f91991abd4c2cfb0d51a3afe5d2f4e` |
| `hermes_state.py` | `3480963f6b6a6ca0c4b70b1c901a6dc808cdf919577191c555ddcdd51acc03ce` |
| `hermes_state_messages.py` | `7a3c00cea0810d25aab8c900f1ef72e122262a6d90403a47bca409fda05e4637` |
| `hermes_state_sessions.py` | `9a3592eba3e8f7ccd9141f28304458b478b4c5e6e6de0655649d22d0a6620232` |

## Boundaries

- One child process under the native interpreter; private temporary HOME, HERMES_HOME (a profile
  home), XDG and runtime roots set before any native import, in an allow-list environment with no
  credentials, proxies or inherited `HERMES_*`/`XDG_*`. The scratch tree is removed afterwards
  (`scratch_removed: true`) and never exported.
- IP `connect`, `connect_ex`, `sendto` and `create_connection` are denied and counted; AF_UNIX
  works. The denial self-tested (all four denial methods plus AF_UNIX, each with its own key, four
  counted self-test attempts excluded from the native count), and native code caused 0 blocked
  attempts.
  **Limit:** this is Python-level patching, not an OS sandbox. It does not cover C-extension
  sockets, subprocesses or DNS resolution, so "no network" here means "no Python-level IP
  connect observed", not "network impossible".
- No full gateway start (a real `GatewayRunner` was constructed, not started), no model call, no
  pairing, server, port or TLS. The installed CLI, any live Hermes home and the running approval
  matrix were neither run nor read.
- Controlled doubles: the image-routing decision (`_decide_image_input_mode`, forced to native)
  and an inert adapter subclass. Everything else ran native code.
- Output is booleans, counts and status codes. A test asserts the summary contains no sentinel
  content, ids, scratch or profile paths. Child stderr was empty; native logs captured in-process
  held 386 records (357 DEBUG, 29 INFO), none naming a cache path. One DEBUG record from the
  plugin loader named the scratch home (not an attachment path).

## Results

Overall status `PASS_WITH_EVIDENCE_GAP`: 73 checks across five subcases, all held; three
subcases carry named gaps. "Check" = asserted and must hold; "observation" = recorded fact about
this build that is not judged.

### 1. Cache helpers (24 checks)

- `cache_document_from_bytes` wrote hostile names (`../../x`, absolute, nested, `..`, `.`, empty,
  NUL) only inside the active profile's `cache/documents`; `..`, `.` and empty become a generic
  name and a NUL byte is removed.
- `cache_image_from_bytes` honored the configured cap from `config.yaml`: a valid 1x1 PNG padded
  to exactly the cap was cached, cap+1 was rejected and wrote nothing. Invalid magic was rejected
  and wrote nothing.
- Observations: the rejection message echoes the rejected bytes; magic-prefix-only bytes are
  accepted (no decode); cap `0` reads as unlimited, a negative cap rejects every positive size
  (the helper docstring says otherwise), an unparseable cap falls back to the default; a
  document above the image cap is cached (no document bound); POSIX backslash is not a separator
  and a newline survives into the cache filename; an over-255-byte name fails with a raw
  `OSError`; files are `0644` and the directory `0755` under umask 022 (native applies no
  private mode).

### 2. `MessageEvent` (10 checks)

Path, MIME and caption sit in `media_urls`, `media_types`, `text`. Across all dataclass fields
only `media_urls` holds the path; the source and the session key are unchanged by attaching
media and do not contain the path; neither a caption nor a path used as message text is a
command.

### 3. Inbound preparation (11 checks, real `GatewayRunner` methods)

- For `text/plain`, an absent `media_text_inlined` and `[None]` produce the same note as `[True]`;
  `[False]` produces a different note. In no case is the file content present in the prepared text:
  native never inlines, so the flag only changes what the agent is told.
- A binary (`application/pdf`) note is identical for absent, False and True.
- The note points at the host cache path and the caption stays last.
- Native-vision mode (routing double): the prepared text is the caption only, and the path is
  held in the per-session native image buffer.
- Observations: a `media_urls` entry outside the cache is accepted and named in the note (no
  containment check); a newline in the cached filename reaches the note text through the path;
  `application/octet-stream` with a `.txt` name is treated as text.

### 4. Busy handling (17 checks)

- Base adapter fallback (no runner handler): PHOTO+PHOTO, PHOTO+DOCUMENT and DOCUMENT+DOCUMENT
  each merge into one pending event; the first client id is kept, captions are joined, the second
  event is marked accepted, and a merge with a photo retypes it PHOTO.
- Runner `_queue_or_replace_pending_event`: PHOTO/TEXT in either order merge (TEXT then PHOTO
  retypes to PHOTO); DOCUMENT+DOCUMENT, PHOTO+DOCUMENT and DOCUMENT+PHOTO take FIFO slots.
  Negative controls: differing `gateway_session_key` metadata, and differing
  `allow_gateway_control`, prevent a PHOTO merge; matching non-empty scope merges.
- A merged event carries one client id; the second message's id is not on it, so two client
  messages become one turn. HMP would have to track that itself.

### 5. Durable rows (11 checks)

Real `_db_flush_collect` / `_db_flush_write` wrote into a real `SessionDB` (default path under the
scratch profile home), and `get_messages` read it back.

- A document turn's row holds the prepared note, including the host cache path.
- A part-list content with image part and a string override stayed a list; the row is the caption
  plus `[screenshot]`, with no path. The string override did not replace the list.
- The row schema has no media/attachment/path/url column; ids are increasing integers;
  `after_id` returned only later rows; the client message id round-trips as `platform_message_id`.

## Evidence gaps (not proven, no shadow implementation written)

| Gap | Reason |
| --- | --- |
| Text-mode image enrichment | needs the vision tool and a model/provider call |
| Runner busy handler entry (`_handle_active_session_busy_message`) | needs authorization, busy-ack send and steer/interrupt machinery; only the queue-policy method ran |
| `defer_policy` reject | absent from this native build |
| Real agent-turn flush | the flush helpers ran on a duck-typed agent; the list-content plus string-override shapes are assumed from the census, not produced by an agent turn |
| HMP read bridge | HMP runtime is out of scope; read-back was the native row |
| Full busy-handler/auth admission | see busy handler entry above; admission and authorization were not exercised |
| Multiplexed-profile re-homing, 24-hour sweep, audio/video | not exercised |
| Release attribution | the archive provenance is not a Git SHA attestation; no authoritatively supported release is established |
| OS-level network denial | Python-level patch only; DNS, C-extension and subprocess sockets remain uncovered |

## Review status

- Worker fixed an earlier evidence error: the self-test claimed four denial methods but ran three;
  `connect_ex` now has its own probe, `denies_connect_ex` key, and the expected count is four.
- Root independently reproduced the prior run (73 checks, source unchanged, scratch removed,
  0 blocked attempts) before this repair.
- Current repair (connect_ex probe; parent exit now requires every run boundary, fail closed with
  `run_boundary_not_held` and only the boundary name) was independently reviewed and reproduced by root. Status stays
  `PASS_WITH_EVIDENCE_GAP`; it is not a full qualification.

## What this does and does not show for design

These are observations about this build. They do not choose a wire shape or limit.

- Native bounds for documents do not exist and image bounds can be configured away, so any
  product limits (bytes, count, type, filename) belong to HMP before `cache_*_from_bytes`.
- A generated cache filename would avoid the newline and backslash carry-through.
- `media_urls` is trusted as given; only paths HMP itself created should ever reach it.
- For text documents HMP would need `media_text_inlined=[False]`; the default makes a false claim.
- Merging, FIFO and the lost merged client id (a design risk) affect "one send = one turn" and
  idempotency.
- Requirements for HMP, not native behavior: generated cache paths only, private file mode, and
  an input bound before any `cache_*_from_bytes`.
- Phone read-back of a document turn would show host paths; a native-vision image turn leaves a
  `[screenshot]` placeholder with no attachment identity.

## Verification

Focused tests: 14 passed (7 unit, 7 native). They ran alongside the existing manifest tests in
one invocation (63 passed); the existing tests were not changed. The full CI-equivalent suite was
not run for this work. Pinned Ruff 0.16.9 (`server tools`), plugin surface, the private scan over
the new files, log scan (nothing captured to scan) and `git diff --check` passed. Tests do not
mutate native behavior, so they show the fixture records what this build does, not that the
checks would catch every regression.

### Final root verification

Root read the exact fixture and causal assertions, reproduced the repaired native CLI run
(73 checks held, all four denial probes true, native IP attempts zero, source unchanged, scratch
removed, no stderr or cache-path log messages), and passed all **30 focused tests** with no skips.
Root also passed **315 fixture and CI-tool tests together** with a fresh private pytest base
directory. A wider worker invocation had earlier reported four failures; they did not reproduce
in this run. Their cause is not established, and no broader CI-equivalent result is claimed.
The isolated existing Git-fixture file separately passed 65 tests. Root Ruff on both new files,
plugin surface, explicit new-file privacy and diff checks passed. Discovery is accepted; the
product wire, release/build qualification and upload feature remain open.
