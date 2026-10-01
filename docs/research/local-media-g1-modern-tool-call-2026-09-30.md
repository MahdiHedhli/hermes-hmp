# Local generated media: modern `tool_call {calls: [...]}` linkage (2026-09-30)

Research evidence for root review. Not a design, wire shape, qualification or product change. It
extends the accepted G1 fixture (`local-media-g1-persistence-2026-09-30.md`, not edited) by four native
scenarios. No media reference, route, token, candidate extractor or wire shape is introduced. The G1
isolation, parent, path, socket, resource, timeout, scratch and provenance guards are unchanged, and the
native executor is not monkeypatched. No G2, provenance hook or product interface work was done.

**Not repeated:** the five accepted scenarios (`desktop`, `phone`, `desktop_flushfail`,
`phone_flushfail`, `desktop_deferred`) were not run again. They stay the default of `run`; only the four
new names are run here.

## Why

The owner's screenshot shows the modern bridge shape `tool_call {calls: [{name: "image_generate",
arguments}]}`. G1 exercised only the legacy single-entry `tool_call {name, arguments}` and only on
Desktop. Both surfaces, with one entry and with two, are now observed.

## Binding

| Item | Value |
| --- | --- |
| Worktree | `test/local-media-modern-tool-linkage`, base `5a688c7` |
| Hermes build | independent checkout `8afaab37…`, HEAD matches, tree clean before and after, 16 owning files unchanged (fingerprinted before/after) |
| Runtime | the checkout's own `.venv`; modules loaded from that source; 0 from the installed home outside the interpreter base; Unix contacts blocked 0 in all four cases |
| Surfaces | real `tui_gateway.server.dispatch` (Desktop) and real `GatewayRunner._handle_message` with a Phone-shaped source (Phone); adapter is the inert stand-in, **not `HmpAdapter`**; no HMP authorization, store, wire or cap proof |
| Tool search | Hermes default (on): `image_generate` is deferred, so the model must use the bridge |
| Model/provider | synthetic loopback model (scripted: one bridge call, then a final answer; no retry after a rejection) and the synthetic provider, as in G1 |

## Native source traced before the fixture (source reading, then confirmed by running)

| File (SHA-256 prefix) | Relevant behavior |
| --- | --- |
| `tools/tool_search_validation.py` (`495d75b44fca`) | `normalize_tool_call_entries` accepts `{calls: [...]}` and tolerantly the legacy `{name, arguments}`; a single call is a batch of one. `local_batch_error`: a multi-entry batch naming a local tool is rejected ("takes exactly one entry for local tools … Only connectors__ names may be batched together") |
| `tools/tool_search.py` (`1f3598a0cd22`) | `resolve_underlying_call`: more than one entry with any non-connector name returns an error; one local entry resolves to that tool and its arguments; a connector-only batch resolves to a batch sentinel (not exercised here) |
| `agent/tool_executor.py` (`38585996a589`) | `_unwrap_tool_search_call` peels a one-entry bridge so hooks see the underlying name; on an error it returns the wrapper unchanged; `tool_call.function` stays untouched "for the transcript and tool_call_id pairing" |
| `agent/tool_dispatch_helpers.py` (`c4595cf173ed`) | `_peel_bridge_call`/`_batch_admission` decide parallel admission on the underlying tool; a resolve error keeps the call a sequential barrier |
| `model_tools.py` (`5d5a947d84f3`) | `handle_function_call` → `_dispatch_bridge_tool`: a resolve error becomes `tool_error(...)`; a one-entry call re-enters `handle_function_call` with the underlying name and the **same outer call id** |
| `gateway/media_repair.py` (`536b75b269b8`), `gateway/run.py` (`8ee0a9f498bc`) | the Phone auto-append of generated media maps call ids to the assistant call's **outer function name** and only accepts `image_generate` (and TTS) |

Predicted from source before running, then observed: one entry executes; two entries are rejected
before any provider call; Phone media auto-append would not recognize the bridge name.

## Fixture changes (research tooling only)

- Scenarios `desktop_deferred_calls`, `phone_deferred_calls` (one entry; keeps the 6000-character
  prompt) and `desktop_deferred_batch`, `phone_deferred_batch` (two entries in one parent `tool_call`,
  distinct short synthetic prompts, which the synthetic provider turns into distinct filename prefixes).
  Listed in `MODERN_SCENARIOS`/`BRIDGE_SHAPES`; `SCENARIOS` is still the accepted five.
- `inspect_rows` keeps every existing single-entry key and adds `bridge_shape` (`describe_bridge_shape`):
  per outer call: id, closed name class, shape (`direct`/`legacy_single`/`calls_array`), entry count,
  closed entry names, count of distinct entry prompts; per tool row: closed name class, whether the id
  is an outer id, JSON type, top-level key names, a closed error class, image-field key paths (bounded
  walk, depth 4, 200 nodes), type, absolute flag and provider-saved flag; tool-row count per outer id,
  one-wrapper-versus-multiple flags, `shared_id_ambiguous`, cache counts and membership. It never
  emits prompts, paths, file names or error text; a unit test asserts that.
- Desktop `tool.complete` frames record a closed name class and whether `tool_id` is the outer id;
  Phone media senders record call counts (and image count for `send_multiple_images`).
- Raw rows and the per-scenario private diagnostics stay in the fresh 0700 evidence directory at 0600
  and are not committed; child stdout/stderr stream to 0600 files (stdout 0 bytes, stderr 1 to 2 lines,
  none mentioning scratch).

## Observed (build `8afaab37`, one synthetic turn per case, all COMPLETED, isolation checks all true)

| Observation | `*_deferred_calls` (1 entry) | `*_deferred_batch` (2 entries) |
| --- | --- | --- |
| Persisted assistant call | one outer call, function name `tool_call`, arguments shape `calls` array, 1 entry named `image_generate` | one outer call, `tool_call`, `calls` array, **2** entries both `image_generate`, 2 distinct prompts |
| Outer call id | the model's id (no per-entry ids exist in the entries) | same single outer id |
| Executing tool rows | **1** row, `tool_name` `image_generate`, `tool_call_id` = outer id | **1** row, `tool_name` **`tool_call`**, `tool_call_id` = outer id |
| Wrapper vs multiple rows | one wrapper result, no multiple rows | one wrapper result, no multiple rows |
| Result JSON | one object, keys `success, image, model, prompt, aspect_ratio, modality, provider` (same single-object shape as legacy); `image` at top level, 1 string, absolute, equals the provider path | one object, only key `error` (class `local_batch_rejected`); 0 image fields |
| Image fields (total / unique) | 1 / 1 | 0 / 0 |
| Provider saves, profile cache files | 1, 1 (profile `alpha` cache; root and `beta` 0; tool thread's `get_hermes_home()` is the profile, not main thread) | **0, 0** (no provider call) |
| Cache membership | the 1 file is referenced by the row; 0 unreferenced | no files |
| Shared-id ambiguity | no (1 entry, 1 row) | yes: 2 entries, 1 row, 1 id; see below |
| Durable order | provider write precedes the tool-row batch | no provider write; the (error) tool-row batch is still written |
| Desktop | tool-row batch precedes the single `tool.complete` frame; frame name class `image_generate`, id = outer id | tool-row batch precedes the single `tool.complete` frame; frame name class `tool_call`, id = outer id |
| Phone | tool-row batch precedes the first reply send; **0 native media sender calls**, no `MEDIA:` tag in any sent text | tool-row batch precedes the first reply send; 0 media sender calls |
| Scope | profile `alpha` only; root and `beta` databases hold 0 sessions; Phone has the same `session_meta` row as in G1 | same |
| Synthetic model | 6 requests, 1 tool-call response (the rest are final answers, including requests unrelated to the turn), follow-up carried the tool row | same |

Desktop refused IP connects were 4 (not investigated, as in G1); Phone 0; loopback synthetic connects
18 in each case.

## Findings and limits

1. **A one-entry `calls` array behaves like the legacy single entry.** Same executing tool row
   (`image_generate`, outer id), same result object and the same provider/cache/order facts, on both
   surfaces. The stored assistant call name is still `tool_call`, so linkage by the assistant name still
   fails; linkage by outer id plus the tool row's name still holds.
2. **A two-entry batch of local `image_generate` calls is not accepted by this build.** It produces a
   single error row named `tool_call` with no image field and no provider call. The fixture and native
   path were not changed to make it succeed. This is the observed unsupported case: native batch
   generation of several images in one parent call does not occur in `8afaab37`, and the row for a
   rejected batch carries the wrapper name, not `image_generate`. Only a one-entry array has been seen to
   generate. A connector-only batch is a different native path and was not exercised.
3. **Shared ids are not execution proof.** In the batch case the single outer id appears on the assistant
   call and on the one tool row, with two underlying entries. The id cannot attribute a result to an
   entry (entries carry no ids of their own), and here it does not even imply any execution. A matching
   id alone must not be treated as evidence that an underlying call ran.
4. **Difference from the G1 direct Phone path:** G1 recorded
   native media senders running on the direct Phone path; here a successfully generated bridged image
   (Phone, one entry) produced **0** media sender calls. Source reading explains it (the auto-append keys on
   the assistant's outer function name, which is `tool_call`), but that is source inference. These
   are different call shapes, not conflicting measurements of the same scenario. HMP must not assume
   the native auto-append delivers a bridged image. A future HMP history-based path can instead use
   the persisted successful tool result, after its own active-history, authorization and file checks;
   that path has not been implemented or qualified here.
5. Desktop shows the underlying tool name on `tool.complete` for a one-entry call and the wrapper name
   for a rejected batch; the persisted assistant row is the same in both surfaces.
6. Limits: one provider, one turn per case, no flush failure for these shapes, no connector batch, no
   non-local backend, Python-level network denial only, HMP code not exercised.

## Hashes (SHA-256)

| File | SHA-256 |
| --- | --- |
| `tools/research/local_media_persistence_fixture.py` | `85c9f01671c26546173f4382bc47699f3232ecf4f603b2b99d2534476c95cd68` |
| `tools/research/tests/test_local_media_persistence_fixture.py` | `b36f3836142d46424abf71615620851f68241cfe9fc6c4b7fdf22db3cfc94c5f` |
| `tools/research/tests/conftest.py` (unchanged) | `e1912852e937671f985e6e066a948bb8c7e181614912e630fd5b295130fac242` |
| `local-media-delivery-paths-2026-09-30.md` (unchanged) | `c275be2780ac50b48f94713cd04c0fb0826b5b929a2150ec7e376e32ae0fe3e7` |
| `local-media-g1-persistence-2026-09-30.md` (unchanged) | `2a55eb5d561b239eb0e41bb95fa79aebf300518663b788b12027ad6496452b9b` |

Native files fingerprinted by the fixture before and after (unchanged; first 12 hex characters):
`agent/image_gen_provider.py` `ab9eead2a808`, `agent/provider_media.py` `86407bed43c2`,
`agent/session_persistence.py` `412c04eb2e74`, `agent/tool_dispatch_helpers.py` `c4595cf173ed`,
`agent/tool_executor.py` `38585996a589`, `tools/image_generation_tool.py` `8db2a3b73984`,
`gateway/run.py` `8ee0a9f498bc`, `gateway/run_turn.py` `ba8b1ce7d2f8`,
`gateway/run_turn_runner.py` `7c33056b0e97`, `gateway/platforms/base.py` `d4fcf44878f2`,
`hermes_state.py` `e66115733214`, `hermes_state_messages.py` `c9be693fe268`,
`tui_gateway/server.py` `f98ac3b54d5b`, `tui_gateway/methods_session.py` `eaeeaf9d7ea7`,
`tui_gateway/methods_prompt.py` `1aabddbac695`, `tui_gateway/prompt_turn.py` `62673e7c8581`.
Additionally read (tracked, tree clean, not part of the fixture fingerprint): the four files with
prefixes in the trace table above that are not in this list.

## Checks run

- Root's final run: **38 passed**, including the new native test (exactly the four new cases),
  **1 deselected** (the accepted five-scenario test). Final collection confirms 39 total tests;
  the worker's earlier 39 non-native count was incorrect. The old five cases were not repeated.
- Pinned Ruff 0.16.9: check on `server` and `tools` clean; format check clean for `tools/research`. No
  new `noqa`; the 14 existing ones are unchanged and carry their reasons.
- `check_plugin_surface` OK; `scan_private` clean; `scan_logs` had no captured logs to scan; `git diff
  --check` clean. Test warnings are the old pytest temp-directory cleanup noise seen before.

## Run

```
python3 tools/research/local_media_persistence_fixture.py run --evidence <fresh private dir> \
  --scenario desktop_deferred_calls --scenario phone_deferred_calls \
  --scenario desktop_deferred_batch --scenario phone_deferred_batch
```

## Next bounded design implication

For a Hermes-recorded generation result in this build, a candidate must be recognized from the tool row
(`tool_name` `image_generate`, result `success` plus top-level `image`), not from the assistant call name
(`tool_call`). The tested one-entry bridge records a successful result; this build rejects a batch of
two local entries, whose error row must not become a candidate. Native Phone auto-append did not run
for the tested bridged result. This does not block an HMP-owned, history-based media path: its own
active-record, profile confinement, authorization and byte-serving qualification remain necessary.

Root accepted this as research after inspecting the final source and independently running the 38
tests above. No product interface is frozen. The source guards are unchanged, and the same 81 older
pytest garbage-cleanup warnings remain; they are not failures of the four native scenarios.
