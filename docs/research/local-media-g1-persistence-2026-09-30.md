# Local generated media: G1 persistence characterization (2026-09-30)

Research evidence for root review. Not a design, not a wire shape, not a qualification. No media
reference, route, token, mutable manifest, retained custody or product code is introduced, and no
claim is made that local media works. Root decisions M1-M4 are untouched; M4 freezes only the fixture
boundary. The census note (`local-media-delivery-paths-2026-09-30.md`) is not edited here.

## Binding

| Item | Value |
| --- | --- |
| HMP worktree | `docs/local-media-delivery-discovery`, base `9d91ca1` |
| Hermes build | independent git checkout at `8afaab3703e336d72a72c812dd2dd249f04f166a`, tree clean before and after, 16 owning files fingerprinted before/after (unchanged) |
| Runtime | the checkout's own `.venv` (CPython 3.14.7). **Interpreter fact:** that venv's `python` is a symlink into the installed Hermes `tools/python-3.14.7…` directory, so the interpreter binary and stdlib come from under the installed home. Observed in each child: all probed Hermes modules loaded from the independent source, and 0 modules loaded from the installed home outside the interpreter's own base prefix. No installed Hermes code was imported or run |
| Fixture | `tools/research/local_media_persistence_fixture.py` (+ `tools/research/tests/`) |
| Isolation | fresh scratch root per scenario (mode 0700, removed afterward), scratch `HOME`/`HERMES_HOME`/XDG, allow-list environment (no credential-like variables, no inherited `HERMES_*`/`XDG_*`), umask pinned to 022, `TIRITH` off |
| Network | Python-level denial in the child (not an OS sandbox): every IP connect refused except the child's own loopback synthetic model server, and **every AF_UNIX `connect`/`connect_ex`/`sendto` refused** (the synthetic in-memory scenarios need no external Unix IPC; `socketpair`, which asyncio uses, never connects to an address and still works). Refused counts are recorded separately (IP: 0 on the Phone path, 4 on the Desktop path, destinations not captured or investigated; Unix: 0 in every scenario) |
| Subprocess bound | one child per scenario in its own process group, 120 s hard timeout that kills the group, no retry, per-file size limit on what the child may write; every scenario finished well inside the timeout |
| Existing fixture infrastructure | read only; its manifests, dependencies and source/build snapshots were not touched. Its `phone_attachment_primitives.py` (in this worktree) was the pattern for the denial, scratch layout and unstarted `GatewayRunner` |

## Harness safety repair (research tooling only)

A review found three harness gaps; all are repaired without changing any scenario, expectation or
assertion. This is tooling safety, not runtime media authority or qualification.

| Gap | Repair |
| --- | --- |
| Any `--native-src` would be run, including the installed home | Before any evidence write, child launch or native import, the parent refuses (closed reason enum, no path in the message) a source that is relative, missing, a symlink, not a directory, resolves into or contains a live Hermes home (installed home, current `HOME`'s `.hermes`, the account's `.hermes`), has a missing, symlinked or unresolvable `.git`, a `HEAD` other than the pinned commit, or a dirty tracked tree. The git probes use a minimal environment with `core.fsmonitor` off and no optional locks. The direct child CLI runs the same source check plus a scratch-root check (absolute, real directory not a link, owned by the caller, mode 0700, outside live homes, not overlapping the source, prepared layout without links, `HOME`/`HERMES_HOME` equal to the scratch paths) before touching `sys.path` or importing. The `.venv` interpreter may resolve only into the source or the shared interpreter directory of a live home (an interpreter fact); any other target is refused. The guards are small stdlib-only copies of the existing fixture-common ones because that module pulls in the manifest dependencies and the child must stay stdlib-only |
| Unix sockets were allowed | see Network row above |
| `capture_output` held native stdout/stderr in parent memory | child stdout and stderr stream to fresh exclusive 0600 files in a fresh 0700 evidence directory; the parent keeps only byte/line counts, a scratch-path mention flag and a 64 KiB stdout tail (used only when no result file exists). The result file is opened without following links and non-blocking, required to be a regular file, size-checked on the descriptor against a 2 MiB bound before it is read, and refused with a closed enum (`child_result_oversize`, `child_result_unsafe`, `child_result_unparseable`). Scratch is removed on every outcome |
| `write_private` could reuse or follow | files are created `O_EXCL|O_NOFOLLOW` at 0600 and never reused; the evidence path must be new (an existing file, directory or link is refused and never chmodded) |

Tests added (all synthetic; no installed code imported): per-reason refusals asserting the child launch
function was never called, a canary module in the fake source was never imported and `sys.path` was
unchanged; a fresh-interpreter direct child refusal; interpreter-root cases; evidence/`write_private`
reuse and link refusals; a fresh-process Unix contact refusal (no listener exists, so the fixture's own
error, not the OS's, proves the wrapper refused); an 8 MB-per-stream fake child proving streaming (parent
peak allocation under 3 MB), oversize-result refusal and scratch removal; a hard-timeout test proving the
process group is killed; a result-symlink refusal; a writer-less result FIFO refused quickly (the result is opened non-blocking, then required to be a regular file). Disabling the source validation makes the refusal tests
fail. Limits that remain: the denial is Python-level instrumentation (native code using raw `_socket` or
a subprocess is not covered), the parent trusts the pinned checkout's own git metadata, and the
fixture-common helpers were not reused directly.

## What is real and what is replaced

| Component | Status |
| --- | --- |
| Model | **Replaced**: loopback OpenAI-compatible synthetic server, scripted (call `image_generate` once with a 6000-character prompt, then answer). Real client, real `run_conversation` loop |
| Image provider | **Replaced**: synthetic `ImageGenProvider` registered in-process through the native registry; it returns the native `success_response` with a path from the real `agent.image_gen_provider.save_b64_image` (valid 1x1 PNG) |
| Tool dispatch, executor, row construction, flush, `SessionDB` | **Real**, unmodified, except the observer below |
| Desktop surface | **Real** `tui_gateway.server.dispatch`: `session.create` (profile `alpha`, hidden, title "Bot Chat") then `prompt.submit` over a collecting transport; native agent build, `run_conversation`, event projection |
| Phone surface | **Real** `GatewayRunner._handle_message` and `BasePlatformAdapter.handle_message` with a source from the real `build_source` (`scope_id`/`guild_id` = profile, `gateway.profile_routes` + `multiplex_profiles` on) and an event built as `Bridge._phone_event` does (`allow_gateway_control` false, `defer_policy` reject). **Substituted:** the adapter is an inert stand-in, **not `HmpAdapter`**; it records sends and delegates the native media senders to the real base methods. Authorization is a stand-in (synthetic allowlist in the profile `.env`); HMP's own authorization, store and wire layer are not exercised. So this is a real gateway turn on a Phone-shaped source, not an HMP end-to-end turn |
| Observer | `SessionDB.append_messages_batch` is wrapped to record order/roles. In the two `flushfail` scenarios the wrapper raises for any batch containing a tool row **before** the native method runs. This is fault injection at the native public-method boundary, not a SQLite reimplementation; no HMP code reads or writes any database |
| HMP caps | `TOOL_OUTPUT_CAP` (4000) and `TOOL_ARGUMENTS_CAP` (500) are read as text from `contract.py` and compared arithmetically. `hmp_plugin` is never imported and the bridge cap was not executed |

Scenarios: `desktop`, `desktop_flushfail`, `desktop_deferred` (default tool search, so the model calls
the native `tool_call` bridge), `phone`, `phone_flushfail`.

## Observed behavior (closed metadata, every scenario COMPLETED, isolation checks all true)

Normal turns (`desktop`, `phone`, `desktop_deferred`):

| Observation | Result |
| --- | --- |
| Rows | `user, assistant(call), tool, assistant(final)`; Phone also holds one `session_meta` row |
| Order of effects | assistant call row batch → provider writes file → tool-row batch → (Desktop) `tool.complete` frame / (Phone) final text send, then media sends. Provider write precedes the tool-row flush in every run; the tool-row flush precedes the Desktop `tool.complete` frame and the Phone reply and media sends |
| Call/row linkage | tool row `tool_call_id` equals the assistant call `id`; row `tool_name` is `image_generate`; the call row precedes the tool row |
| **Bridge case** | with Hermes default tool search the stored **assistant call name is `tool_call`** (the underlying name is inside its arguments) while the stored tool row `tool_name` is `image_generate`. Linkage by "assistant call name == image_generate" fails in the default configuration; the id match plus the tool row's `tool_name` still holds |
| Raw tool JSON before any cap | 6283 characters, parses as one JSON object; key order `success, image, model, prompt, aspect_ratio, modality, provider`; `image` key at offset 18, `prompt` at 198; **the first 4000 characters do not parse as JSON** while the full text does. `image` and its value end are inside the first 4000 characters (the long prompt came after them) |
| Assistant call arguments | 6014 characters, above the 500-character HMP compaction; call `id`/name are present in the row |
| `host_image` / `agent_visible_image` | absent (local terminal backend); not exercised for a non-local backend |
| Provider path and profile ownership | the path equals the provider's own saved path; parent is the selected profile's `cache/images`; the provider ran on a non-main tool thread whose `get_hermes_home()` was the **profile** home; the profile cache holds 1 file, the root and other-profile caches hold 0; the session lives in the profile's `state.db` only (root and other-profile databases have 0 sessions) |
| File | valid PNG magic, bytes equal the synthetic PNG, regular file, `nlink` 1, mode 0644 under the pinned umask 022 |
| `MEDIA:` text | the tag appears in no stored row and in no text the adapter was asked to send; yet native media sending ran on the Phone path (`send_multiple_images`, then `send_image_file`, then the base failure notice because the stand-in does not override the media senders, as with `HmpAdapter` per census O14). The mechanism that produced the media call is a **source inference** (census O6-O8), not observed |
| Phone notices | a native "home channel" notice was sent before any database write (first send of the turn) |
| Hidden Bot Chat (Desktop) | session `hidden` true, `source` `tui`, title `Bot Chat` retained after a normal turn, row in the profile database. See the title observation under failures |

Forced flush failure (`desktop_flushfail`, `phone_flushfail`; both tool-row batch writes refused, 2 attempts each):

| Observation | Result |
| --- | --- |
| Durable state | cache file present and valid (1 file); assistant call row present with the expected call id; **0 tool rows**; `cache_file_without_authoritative_row` true in both |
| Desktop | `tool.complete` never projected; agent flagged `_incremental_persistence_failed`; the follow-up model request did not carry a tool row; no final assistant row stored |
| Phone | the user received the native "turn stopped while a tool result was still pending" notice instead of the model text; **native media sends still ran after the failed flush** (2 calls, then the base failure notice); no tool row and no final assistant row were stored |
| Desktop title | the hidden session's title was **replaced by an auto-generated title** (the Bot Chat title was not retained) while `hidden` stayed true. Cause not isolated (an artifact of the injected failure is possible) |

These show a file in the cache is not evidence of an authoritative row, and that native delivery is not
evidence of a durable row. They give **no** candidate-artifact claim for the failure cases.

## Source inference vs observed

Observed in this fixture: everything in the tables above for build `8afaab37`, one synthetic turn per
scenario, one provider shape, one profile. Still source inference (not run): that the appended `MEDIA:`
tag is added to the delivered text and not to stored rows (only the outcome was observed); that the
auto-append reads in-memory messages (consistent with the delivery after a failed flush, not isolated);
spill/untrusted-wrapper behavior for large results; behavior for any other provider, tool name,
backend or build.

## Unsupported or open (not claimed)

- HMP's own adapter, authorization, store, wire projection and `Bridge` cap were not exercised; the
  Phone result is a real gateway turn through a stand-in adapter.
- Deferred-tool linkage was observed only through the `tool_call` single-entry bridge and only on Desktop.
- Not run: in-place/child compaction, rewind, import/branch rows, database replacement/restore, cache
  sweep, symlink/hardlink/FIFO/oversize/non-raster/animation refusal, multiplexed cache scope with two
  concurrent profiles, grant revocation, mid-request tip change (G2-G4). No raster, file-open or serving
  policy is characterized here, and no HMP read path was written.
- The two failure scenarios use injected failure; a natural database failure may differ.
- Network denial is Python-level; the 4 refused Desktop attempts were not attributed.

## Acceptance status (root accepted research, 2026-09-30)

- Root ran the full fixture suite on the pre-format sources: **28 passed**, including the build-bound
  test that runs all five native scenarios. Its 81 warnings were old pytest temp-directory garbage
  cleanup (`rm_rf` "Directory not empty") outside these fixtures.
- Those sources were tool `7fb563a62ec5ffdb033424efc00ce200475279cfa576554774d91ad79d7dc271` and
  test `eaeb2d12d3f4981fdbe8ee971c23eed4326a1965ee04ca11cd0a693480bf9eb0`.
- A publication cleanup then applied the pinned Ruff 0.16.9 formatter, its safe fixes and line wrapping
  only. The executable AST differs from the root-run sources in exactly four places: three `UP037`
  quote removals on type annotations and one import reorder in the test file. Comments, including
  narrow rule-coded `noqa` notes, are not in the AST. The five native scenarios were **not** re-run on
  this candidate. Root independently inspected the AST diff: the three annotations remain postponed
  under `from __future__ import annotations`, and the test-only `struct` import reorder changes no
  executable statement. Root accepts the final candidate as research tooling on that basis, with the
  native behavior result bound to the pre-format hashes above and the semantic comparison recorded
  separately. This is not HMP media admission, delivery qualification or a live-device result.
- Candidate hashes (SHA-256):
  - tool `0e87ef4b380f30456d3b67910ff77a2bc2b44126fcd0ddd0f5ed4fdd13fcb72a`
  - test `c1638b27364c7c02aae3377fc635f581d0c75a48beac1859bf634355128f87b6`
  - conftest `e1912852e937671f985e6e066a948bb8c7e181614912e630fd5b295130fac242` (unchanged)
- The census note is unchanged (SHA-256 `c275be2780ac50b48f94713cd04c0fb0826b5b929a2150ec7e376e32ae0fe3e7`).
- Publication checks: pinned Ruff 0.16.9, closed plugin surface, privacy and diff checks passed. The
  repository log scanner had no captured acceptance logs in its configured directory to inspect;
  that result does not characterize native child logs. The final non-native safety suite passed
  **27 tests**; one native aggregate test was
  deselected because the executable logic was unchanged. Narrow per-line lint suppressions retain
  the reviewed fixed-argument subprocess calls and best-effort cleanup behavior.

## Run

```
python3 tools/research/local_media_persistence_fixture.py run --evidence <fresh private dir>
cd tools/research && PYTHONDONTWRITEBYTECODE=1 <venv>/bin/pytest -p no:cacheprovider --rootdir=. -q tests
```

The default build path is the independent checkout above; pass `--native-src` to override and
`--scenario NAME` (repeatable) to run a subset. Unit tests need no build; the build-bound test skips if
the build is absent and otherwise runs all five scenarios (about 30 s). The `--evidence` path must not
exist; the evidence directory is created fresh at 0700 and holds `report.json` (closed metadata plus the
ordered event list), per-scenario child stdout and stderr files and `*.private.json` (synthetic row text
for diagnosis); all are mode 0600 and are not committed. Scratch roots are removed by the parent.
