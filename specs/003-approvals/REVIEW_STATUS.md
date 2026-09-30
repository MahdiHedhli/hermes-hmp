# Approvals review status

## Independent approval route qualification (draft wiring)

Prompt listing, exact-ID answers and Phone sends are now gated by an approval qualification
that is separate from guarded-send qualification and closed by default. The shipped approval
build list is empty, so approvals are not live, enabled or released on any build. The ac0
matrix below remains fixture evidence only.

Test intent (`server/tests/unit/test_approval_route_qualification.py`): a false, raising or
non-boolean approval result closes AP-3/AP-4/AP-6 even with a valid owner device, a
send-qualified build and an open write gate, with no endpoint, resolver, listing or delivery
call; an explicit `True` keeps the F3 behavior; snapshot `open_requests` is stripped while
closed; non-owners and unauthorized bots never reach the qualifier; ordinary guarded sends are
unaffected; closed producer hooks call no approval helper and store no row; the production
adapter binds `supported AND approval_listener_qualifier(identity)` (process-level baseline; the
older `approval_build_qualified` binding is superseded) and passes the same callback to the send
deps and the hooks. Older pass counts (for example 1197) belong to the original lane and are
not current.

**Controller evidence (current slice, September 30):**

- Full suite after the process-binding and ambiguous-label fixes
  (`/private/tmp/hmp-approval-route-qualification-pytest-6.log`): **1364 passed,
  12 skipped, one existing warning, 24.40s**.
- Focused independent Opus review cleared F1/F2/F4 as closed groundwork with no material
  code residual. It ran no tests. L2/L5 code repairs are verified; latency under load remains
  unmeasured and the operator restart runbook still needs real gateway evidence.
- Ambiguous-label tests cover single/multi answers, mixed selections, case, whitespace,
  recommendation suffixes, sharp S and sigma collisions, with no resolver call on refusal.

**Earlier evidence (superseded by the current run):**

- Full suite (`/private/tmp/hmp-approval-route-qualification-pytest-3.log`): 1320 passed,
  12 skipped, one existing warning, 25.07s.
- Pinned Ruff 0.16.9 server tools: PASS, after only `noqa` comments were corrected.
- Surface and private checks: PASS, as previously recorded.

This is draft evidence only. The release gate, current full real gateway matrix and physical-device
gate are not satisfied. L3 remains a documented trusted-operator/in-flight limit. The historical
L2/L5 findings and their verified repairs are recorded below.

### Independent Opus review (static, no tests run) and follow-up fixes

An independent read-only review of `a643341` found no security blocker (the shipped approval
list is empty and every traced path stays closed). Fixed in this slice:

- **M1:** unbinding the stream while closed changed DS-4 result classification (a
  `run.started` → keepalive → `done` stream became unknown instead of queued). Mailbox phase
  transitions in `consume_sse` no longer depend on `bind`; `bind` only drives prompt-store side
  effects. Tests feed the same frame sequences bound and unbound and require identical results.
- **L1:** the approval check now runs before the profile lock and the fresh head/lease checks
  (only when a prompt store exists, off-loop, exact `True`, exceptions closed).
- **L4:** the adapter callback requires a supported build as well.

**Historical review findings (superseded for L2/L5 by the repairs below):**

- **L2:** the qualification probe is uncached and re-runs per request, snapshot, send and
  `reconcile_chat`. Harmless while the list is empty; a cache needs its own fingerprint and
  revocation design and is deliberately not in this slice.
- **L3:** the gate is checked once per AP-4/AP-6 request; a bound DS-4 stream (up to 24h) can keep
  storing rows after qualification closes, and rows may reappear if it reopens. Rows stay
  unactionable because AP-3 and the snapshot re-check the gate. The fingerprint and HEAD reads
  are not atomic.
- **L5:** on installs without git both SHAs are `None`, so the SHA comparison passes trivially and
  only the approval fingerprint binds the read identity.

**L2/L5 repair (verified by the current controller suite and focused independent review).**
The two bullets above are the historical findings and stay as
written. The production callback is now `compat.approval_listener_qualifier`, built once in
`open_components` for a supported build, with a startup baseline of root, ordered approval file
list, fingerprint and git SHA. Each callback re-reads the manifest and source and requires all to
equal the baseline plus an exact current entry, so a disk swap to another also-listed build after
the baseline closes, manifest removal closes at once, and an empty or malformed startup list stays
closed without reading or importing approval files. This covers swaps after the baseline only:
memory is not attested, and "restart" means a full gateway process restart, not a listener restart.
**Follow-up (F1-F4 of the gate-binding review, verified in the current suite and focused review):** the
baseline is now one process-level latch fixed by the first supported factory call (listener
reconnect cannot redefine it; a first empty, malformed, missing or unlisted manifest closes the
process until a full process restart), cross-checked against the read gate's fresh identity, and
requires a matching startup entry. The CLI line is labelled "Approval qualification (on-disk
source)" and is informational, not the running gateway. Unload/reimport of the plugin is not
defended against; runbook: restart the whole gateway process after any Hermes, source or plugin
change, and approvals qualification and release stay no-go until that lifecycle is verified. Only a successful probe is cached (<= 8, keyed by
root, ordered files, fingerprint, SHA, lock-guarded, separate from the guarded-send cache); failures
retry and there is no TTL. `approval_build_qualified` and the CLI line remain an informational
one-shot exact-source check, not production admission. L3 is unchanged and still documented as a
limit: a bound stream can outlive the gate and the fingerprint/HEAD reads are not atomic.

**Mobile review M1 (ambiguous clarify labels; verified by the controller's current suite).** A clarify
choice whose normalized form (`strip_recommended(...).casefold()`) matches more than one offered
label, e.g. `Apple`/`apple` or `Straße`/`STRASSE`, is refused with `409 invalid_choice`,
`applied:false` and no resolver or delivery call, on both the single and multi-select paths. It is
not guessed. Unambiguous replies and the Other transition are unchanged, and nothing about the
choice is logged.

Review limits: static review only; it ran no tests, used no live Hermes home, did not verify
real Hermes keepalive-only mailbox streams, and did not re-review F3 code outside the diff.
Independent review is not release approval.

## Exact untagged Hermes `main` fixture matrix

The isolated archive of Hermes
`ac0cfa7db94cefa90cf3e35191f38b53888b9e17` passed HMP's boundary and
behavior probes and the F2/F3 real gateway/PTY fixture matrix. Its JUnit report
has **17 selected cases, 17 passed, 0 failures, 0 errors, 0 skips**: T7 Bot Chat
approval **3/3**, T8 Phone chat approval **3/3**, and approval fail-closed
owner/flag/qualification cases **3/3**. The fixture used loopback listeners,
Hermes's real gateway and pairing paths, a fake model, synthetic credentials,
and scratch homes. The source archive's approval stream and busy resolver files
matched that exact upstream commit. The matrix produced a fixture-only receipt
under `/private/tmp/hmp-approval-matrix-results-4`; it was not copied to a
runtime allowlist or the owner's live Hermes.

The added T8 case pairs one device with two authorized fixture profiles. An
approval request raised in the first profile stays pending when the device
submits its exact ID and an allow choice through the second profile; only a
deny through the issuing profile settles it, and the fixture command never
runs. This proves the profile binding on this isolated candidate, not live
multi-profile configuration. The fixture requires the exact scratch
qualification receipt; running it without that receipt intentionally closes
all guarded routes before any profile-specific check.

This result covers the **exact untagged archive only**. It does not qualify a
published Hermes release, a git install, real model/tool latency, a physical
phone, or a live multi-profile deployment. The source's lockfile required
Python 3.14, so extraction used a scratch per-build interpreter override that
is not part of this PR. A released build needs its own locked, reproducible
extraction and full matrix, followed by independent release security review.
F3 stays disabled. The test-only resolver update in this PR preserves the
old-build path and exercises the active language's approval words plus
slash-confirm words under `allow_gateway_control=False`.

## Untagged Hermes `main` candidate: source and handler probe only

Hermes `main` at `ac0cfa7db94cefa90cf3e35191f38b53888b9e17` registers an
approval notifier on the Bot Chat session stream. This is newer than the
published `v2026.9.24` tag and supersedes the missing-notifier finding below
**for this exact untagged source only**. It does not qualify a released build.

The evidence-only `tools/compat/session_chat_approval_probe.py` ran against
that pinned source with a disposable `HERMES_HOME`, fake model and SSE response,
and no socket or command execution. Its 32 named checks passed: a nonempty
request ID and offered choices were emitted; wrong request/run IDs, key, and
profile were rejected; exact-ID denial kept the fake executor idle; replay
failed; exact-ID `once` released only the fake executor; and a simulated stream
drop interrupted the fake agent and rejected the late answer with the **real**
request ID. The wrapper and focused lint passed. Independent security review
found and prompted the late-answer assertion fix before this recorded rerun.

On its own, this handler probe is not the full T7/T8 real-route matrix above.
Its fake agent sets the interrupt flag in its own worker thread. The matrix
separately covers the loopback gateway, pairing, and HMP relay, but a physical
device, real model/tool latency, live multiplex profile secrets, smart mode,
timeout, and concurrent prompts remain untested. Upstream's API-key
answer route also accepts an omitted request ID or bulk selection; **HMP must
require and forward one exact ID and refuse bulk choices**. No runtime
fingerprint, allowlist entry, or live plugin change was made. F3 remains off.

**Historical round 5:** HMP rate limiting and fixture defects were fixed on
`feat/approvals`, base `e1ddb28`. The two builds tested then lacked the Bot Chat
session-stream approval lifecycle. Neither build qualified F3. The newer,
untagged source finding above does not change those results.

## Controller fixture run after round 5

The round-5 changes are committed at `ac469d3`. The controller ran the real gateway/PTY
matrix against both isolated extracted builds outside the coding sandbox. Boundary and
behavior probes passed on each build, but **neither build qualified** and no final runtime
qualification receipt was produced.

| Build | Integration result | Release implication |
| --- | --- | --- |
| Stock base | 15 passed, 1 failed; 32 deselected | T7 Bot Chat approval finished without a pending prompt, confirming the upstream session-chat gap. |
| Experimental | 13 passed, 3 failed; 32 deselected | T7 has the same gap. Both T8 Phone chat tests timed out waiting for an approval card; the cause is still under investigation. |

In that round, the experimental Phone chat failure prevented qualification independently of
T7. No fixture fingerprint was added to a runtime allowlist. The owner's live Hermes and plugin
were not changed.

## Focused T8 rerun after admission and fixture-readiness fixes

At HMP commit `4ce9aad` plus the test-harness readiness change on this branch, both isolated
T8 cases pass against each exact extracted build: **stock-base 2/2**, **experimental 2/2**.
The fixture uses a provisional qualification receipt bound to each build's source fingerprint;
it is never installed into the runtime allowlist. The first experimental rerun exposed
`refused_draining`: HMP's listener and bot roster were live while Hermes's startup-restore
gate was still closed. The harness now waits for the post-restore `Press Ctrl+C to stop` marker
from the gateway log before sending. This makes the real admission result visible and removes
the startup race from T8. These focused passes do not clear the mandatory T7 failure or
constitute a full qualification receipt.

**Experimental admission risk addressed in the draft (source-path finding, not established as
the T8 cause):** `BasePlatformAdapter.handle_message` sets `_gateway_accepted` when it starts a
background task; `defer_policy="reject"` reports the later durable admission or refusal through
`MessageEvent.admission_ticket`. HMP now waits for that outcome. A refused or unconfirmed event
is never reported as `202 submitted`; an unconfirmed event is stored as `200 unknown` and cannot
be delivered twice by replaying its cmid. Regression tests failed before this change and pass
after it. The stock build does not expose this admission API and retains its previous behavior.
Catch-all `refused_other` is now treated as unknown because the ticket omits the reason and
`persist_failed` cannot be ruled out. HMP adds a Phone chat observation only after confirmed
admission, so a refused or unknown send cannot appear as a delivered user turn.
The focused real-gateway T8 rerun now passes on the exact experimental build; full-matrix
qualification and the T7 upstream gap remain open.

## Round-5 findings and changes

1. **Polling concealed failures and starved answers.** F3 reused the direct-send test helper's
   250 ms polling (up to 240/minute) against one 60/minute/device bucket shared by reads,
   answers and Phone sends. Predicates swallowed 429 as “not ready”; the settlement predicate
   even treated an HTTP error as no remaining approval. F3 waits now poll every **3 seconds**,
   matching the fastest phone cadence, and assert HTTP 200 immediately.
   Production now has **60 reads/minute/device** and a separate **60 actions/minute/device**
   shared by answers and Phone sends. Both aggregate across profiles/IDs, retain owner checks,
   and reject before downstream work. At 3 seconds, 20 periodic reads plus 20 answer refreshes
   fit with 20 reads of headroom; 20 answers plus 20 sends fit the independent action budget.
   The 15-second cadence is less demanding. No unlimited route or fail-open fallback was added.

2. **Phone fixture turns had no tools.** The fixture omitted `platform_toolsets.hmp`.
   Hermes selects the nonexistent default `hermes-hmp`, which expands to no tools. The fake
   provider classifies requests without tools as auxiliary and returns its default summary,
   never consuming the queued terminal call. Controller logs confirm one text-only model call
   and zero tool turns. The fixture now explicitly selects `[terminal, clarify]` in the root
   and every named profile. It sets `approvals.mode: manual`, a 120-second timeout, and
   `unattended_mode: deny`; the default smart guardian's fake auxiliary response is no longer
   part of this human-approval test. Real Hermes config/toolset resolution verified root→A→B→A
   on both extracted builds. These settings apply only to scratch fixtures.

3. **Bot Chat's missing prompt is a real upstream capability gap.** On stock-base
   `04fa849e70165336ba73e6750257a1ebd7ff998d` and experimental
   `7e8c8f07a11a781b82ff2ad249196e2dc3f4bbb3`,
   `gateway/platforms/api_server.py::_handle_session_chat_stream` calls `_run_agent`, which
   registers no approval notifier and never populates `_run_approval_sessions`.
   `tools/approval.py::_human_decision` therefore returns nonblocking `pending_approval`;
   the agent ends its turn without an `approval.request` event. The required notifier/context
   registration exists in `gateway/platforms/api_server_runs.py::_run_agent_sync`, used by
   `/v1/runs`, **not the session-chat route HMP uses**. Manual fixture config cannot repair this.
   A socket-free diagnostic executed the actual session-stream handler, executor and approval
   guard (mocking model/transport/storage boundaries, never executing a command). Both builds
   emitted `run.started`, `message.started`, `assistant.completed`, `run.completed`, `done`;
   approval was false, guard status was `pending_approval`, and the run approval map was empty.
   This rules out an HMP stream-consumer race. T7 still requires a real prompt and a human answer;
   it now fails early with this explanation if the turn finishes before an answer.

4. **Later fixture assumptions were stale.** The Phone test now scripts approval→clarify in
   one turn, avoiding a second-send race while the previous agent is finishing. After “Other”,
   composer text must return `409 stale`; only the request-ID answer route applies the text.
   The unknown-ID test is named honestly (it did not pair a foreign bearer). Existing device/user
   isolation regressions remain. Approval commands target only a per-test sentinel under the
   fixture directory; assertions prove it survives before consent/after deny and disappears only
   after an explicit Bot Chat approval. Terminal cwd is also confined to that fixture directory.

## Round-5 validation

- Socket-free CI set: **1097 passed, 2 skipped, 148 deselected**, one warning.
  The existing runner excludes socket/gateway test functions because this sandbox denies binds;
  these deselections are not integration evidence. Log: `/private/tmp/hmp-f3-r4/r5-unit.log`.
- Focused cadence/isolation/config regressions: **4 passed**. Re-executing the round-4 handler
  and config-writer function bodies against these regressions gives **3 failed, 1 passed**;
  only the slow 15-second cadence already passed. Logs: `r5-red.log` under the same directory.
- Real-Hermes diagnostic scripts and logs: `r5-route-probe.py`,
  `r5-route-probe-{stock,experimental}.log`, `r5-config-probe.py`,
  `r5-config-{stock,experimental}.log`, all under `/private/tmp/hmp-f3-r4/`.
- Standalone stock-base F3 integration attempted: **8 setup errors, 16 deselected**, all
  `PermissionError` at loopback bind. Log: `r5-integration.log`.
- Matrix rerun: boundary and existing control/exact-ID behavioral probes pass for both builds;
  integration cannot bind sockets. **Neither qualified; no candidates or final receipt.**
  Output: `/private/tmp/hmp-f3-r4/r5-sandbox-matrix/`. The existing behavioral probes do not
  prove session-stream approval support; T7 remains mandatory and exposes that gap.
- Ruff (`server tools`), plugin-surface check, private-data scan and diff whitespace check pass.
  `scan_logs` rejects the diagnostic/pytest failure logs on `TOKEN_B64U` matches for long test
  identifiers, scratch paths and diagnostic field names (for example `run_approval_sessions`).
  It is not reported as passing; the original logs and scanner remain unchanged. No bearer
  was created by the denied integration setups, and no prompt/answer logging was added.
- Diagnostic runtime warning: these extracted interpreters report SQLite 3.50.4's WAL-reset
  issue. Hermes explicitly falls back to DELETE journaling for the diagnostic run stores,
  mitigating that path. Runtime upgrade remains outside this HMP change; no installed runtime
  or live Hermes home was touched.

## Round-5 remaining work and handoff

The proper Bot Chat fix belongs in Hermes's actual session-stream path: a per-run approval
context/notifier, an owned run→approval-session mapping, `approval.request` events with exact
request IDs and offered choices, and cleanup/wakeup on termination, disconnect and failure.
It needs approval/deny, exact-ID, cross-profile, timeout and disconnect regressions on that route.
HMP must not manufacture cards from tool text, switch to an unqualified alternate route, patch
Hermes at plugin runtime, or mark empty prompts as success. No Hermes source or qualification
allowlist was modified this round. The optional upstream-patch scope question is still open.

`/private/tmp/hmp-f3-r4/run.sh` now writes to `controller-r5/`, preserving the controller's
original evidence in `controller/`. It still requires a successful matrix before standalone
integration or receipt use. Run it outside this sandbox; T8 changes require that live rerun,
and unpatched T7 is expected to prevent qualification. Once Hermes is repaired, requalify the
new source bytes rather than copying the old fingerprints into the runtime list.

The coding sandbox could not create `.git/index.lock`; the controller later committed the
round-5 changes at `ac469d3`. The fixture run above was performed after that commit. No push
or attribution trailer was used for the round-5 commit.

---

**Round 4 remediation implemented on `feat/approvals`, base `e5a9fd6`; controller integration
qualification remains pending.** This section supersedes the round-3 status and handoff below.

## Round-4 root cause and fix

The controller's round-3 matrix passed boundary and behavior probes for stock-base and
experimental, but both integration suites failed before endpoint resolution. Provisional
receipts (and the final receipt producer) emitted only `label`, `fingerprint`, `git_sha` and
`source_sha`. The fixture copied these identity-only entries into its runtime compatibility
list. `compat._parse_build_entry` also requires `qualified_by` and `qualified_at`, so loading
that list raised `ValueError`, and `_direct_send_build_qualified` returned false.

This explains the whole early-refusal pattern: stock-base returned `write_gate_closed`;
experimental's OPEN base gate returned `api_server_unavailable` with no endpoint; Phone chat
and approvals returned `write_gate_closed`. Even stale-head/missing-chat requests failed before
their guards. No SSE response or pinned connection was reached by these failures.

- Both receipt producers now emit complete runtime entries. Provisional provenance explicitly
  says integration is pending; final provenance is emitted only after qualification succeeds.
- The installer validates receipts through the actual runtime parser before changing the scratch
  plugin copy. Missing metadata is a fixture setup error rather than a hidden runtime 503.
- The owner-removal integration case now restarts the gateway after rewriting the owner list,
  matching Hermes's adapter-config loading behavior and the existing flag test.
- Matrix pytest temporary directories now stay under its output directory for retained diagnostics.

Runtime plugin code and committed build lists are unchanged. Fail-closed behavior, exact source
fingerprints, owner/device authorization, flags, loopback literals, redirect policy, SSE content
type and run-ID binding all retain their existing checks.

## Round-4 validation

The new socket-free regression failed before the fix with the actual missing `qualified_by`
parser error. It now exercises the real matrix orchestration with subprocess execution replaced
by controlled results, installs provisional and final receipts, and checks the runtime gate.
Changed source bytes still close the gate. Failed, skipped and empty integration reports never
produce a final receipt. Installer tests reject either missing provenance field without changing
the installed file. These tests do not claim real integration qualification.

- Requested unit/tools CI set, excluding socket/gateway cases: **1095 passed, 2 skipped,
  148 deselected**, one existing aiohttp subclass deprecation warning. Logs and exact local
  runner: `/private/tmp/hmp-f3-r4/unit-final.log` and `local_checks.py`; the exclusion list is
  `deselected.txt` in the same directory. No test assertions or skip markers were weakened.
- The first exclusion command used incorrect node IDs and attempted socket tests; it was
  interrupted and replaced with a name-based exclusion filter. Its incomplete run is not
  validation evidence. Matrix and standalone integration were left for the controller.
- The offline wheel test initially failed because the isolated uv cache lacked setuptools.
  It passed using the supplied interpreter's installed setuptools with
  `UV_NO_BUILD_ISOLATION=1` and `UV_PYTHON`; the final offline suite used those settings too.
- Ruff **0.16.9**, `server tools`: PASS. `check_plugin_surface`: PASS. `git diff --check`: PASS.
- `scan_private`: PASS with zero baseline. `scan_logs`: PASS on the final offline log and wheel
  recheck log; default captured-log scan also passes. Scanning the older failed pytest tracebacks
  additionally produced 205 heuristic matches (203 token-shaped identifiers/paths, two literal
  `bearer is` prose matches), all reviewed as non-secrets. No suppression was added.

Controller handoff: run `/private/tmp/hmp-f3-r4/run.sh` from this checkout. It uses the supplied
interpreter/builds, runs `run_matrix.py --target direct-send --builds stock-base,experimental`,
then runs both integration suites with `HMP_DIRECT_SEND_QUALIFICATION` pointing at the final
receipt. It stops on matrix failure and keeps scratch writes under `/private/tmp/hmp-f3-r4/`.
No runtime qualification entries are committed. Release remains blocked until the controller
reports passing matrix/integration results and review is complete.

Local commit attempt: blocked by `Operation not permitted` creating `.git/index.lock`.
All five changed files remain in the working tree; HEAD is still
`e5a9fd611c515ab6f9eadf179c617e0fbc44e504`. No push or attribution trailer was added.

## Historical round-3 record

**Round 3 remediation implemented; release remains blocked on external integration and review.**
Base: `7173cff`. The round-2 verdict was REJECT. The installed Hermes checkout remained read-only
at `8afaab3703e336d72a72c812dd2dd249f04f166a`; checks used a temporary `git archive` export and the
existing extracted builds. No live owner configuration was changed. No push was made.

## Round-2 findings

| Finding | Status and evidence |
|---|---|
| Fingerprint BLOCKER | FIXED in code: the mechanically derived 34-file boundary covers input controls, prompt delivery, resolution, timeout, API routes/auth and profile scoping. Old entries move to `requalification_required` with their original fingerprints preserved; `builds` is empty. External integration qualification is still pending. |
| B3 PARTIAL | FIXED: `tools/compat/approval_probes.py` executes real Hermes methods with pending approvals and both choice/free-text clarifications. All slash inputs, every bare approval word from Hermes's routing table, numeric/label/Other replies and free text leave the waiters unresolved with `allow_gateway_control=False`. The same harness with control enabled resolves the waiters. |
| Integration fixture | FIXED in code: the shared fixture writes the exact paired device into `owner_device_ids` and retains it through flag/config rewrites; `direct_send.enabled` defaults true only in this fixture. Qualification receipts are checked against current bytes and installed only in the scratch plugin copy. Actual integration remains BLOCKED by sandbox sockets. |

B3 source citations at the pinned Hermes commit: `gateway/platforms/event.py:104-111` gates slash
parsing; `gateway/platforms/base.py:3971` gates plaintext command coercion and `4028-4041` gates
clarify bypass; `gateway/run_busy.py:507-551` gates bare approval words at line 529;
`gateway/run_inbound.py:1209-1222` gates pending-reply interception before clarify resolution.
`gateway/run_turn_runner.py:1457-1550` independently delivers outbound approval prompts.
`tools/approval.py:138-172` selects the exact request ID under the queue lock;
`tools/approval_gateway_wait.py:47-72` enforces the finite approval deadline.

The probes also put two approvals in one session: an unknown ID or foreign session resolves zero,
answering the second ID leaves the first pending, and replay resolves zero. Removing each of the
four control guards (`event`, `base`, `run_busy`, `run_inbound`) or request-ID selection from the
**temporary export** makes qualification fail. All five mutants were rejected; the unchanged
pinned export and both extracted builds pass. The live Hermes source was never mutated.

## Mechanical fingerprint derivation

`tools/compat/bridge_files.py --dependencies-attr DIRECT_SEND_DEPENDENCIES` now derives the union
of read dependencies, direct-send dependencies and their AST imports. For each declared symbol it
includes the defining module and every non-stdlib wrapper source. The command was run with
`--write --check` against stock-base and experimental and with the pinned export; no fingerprint
was substituted for a qualification result. Each file's purpose follows (paths relative to Hermes):

| File | Security property / dependency |
|---|---|
| `agent/secret_scope.py` | API key resolution in the selected profile |
| `gateway/authz_mixin.py` | Bot authorization before reads and delivery |
| `gateway/config.py` | Platform configuration, routing and endpoint settings |
| `gateway/pairing.py` | Exact approved Hermes user lookup |
| `gateway/platforms/_shared.py` | Scoped secrets and platform authorization environment |
| `gateway/platforms/api_server.py` | Profile-scoped bearer authentication, session stream, run-ID-stamped approval delivery |
| `gateway/platforms/api_server_room_grants.py` | Run-route authorization helpers and grant validation |
| `gateway/platforms/api_server_run_idempotency.py` | Durable run ownership/scope used by approval routes |
| `gateway/platforms/api_server_runs.py` | Owned-run lookup and exact-ID approval POST delegate |
| `gateway/platforms/base.py` | Active-session dispatch, plaintext coercion and clarify bypass control checks |
| `gateway/platforms/event.py` | Control-disabled slash parsing |
| `gateway/run.py` | Gateway facade resolving the read/auth/profile dependencies |
| `gateway/run_adapters.py` | Served profiles and gateway routing scope wrappers |
| `gateway/run_busy.py` | Control-disabled bare yes/no/approve routing and busy dispatch |
| `gateway/run_inbound.py` | Control-disabled pending clarify/control interception |
| `gateway/run_profile_reconcile.py` | Profile home resolution and runtime scope |
| `gateway/run_turn_runner.py` | Outbound approval/clarify delivery independent of inbound control |
| `gateway/session.py` | Session keys, sources and lookup isolation |
| `hermes_cli/active_sessions.py` | Bot Chat lease and Desktop-held classification |
| `hermes_cli/auth.py` | Usable scoped API-key validation |
| `hermes_cli/profiles.py` | Profile/home matching for the API prefix |
| `hermes_constants.py` | Profile-scoped home and instance-root identity |
| `hermes_state.py` | Session DB facade |
| `hermes_state_compression.py` | Compression lineage and effective target/head resolution |
| `hermes_state_messages.py` | Durable messages and active message IDs |
| `hermes_state_registry.py` | Profile DB acquisition and release |
| `hermes_state_sessions.py` | Session lookup and authorization context |
| `hermes_state_titles.py` | Canonical Bot Chat target lookup |
| `tools/approval.py` | Exact-ID queue resolution, blocking state and retirement |
| `tools/approval_context.py` | Profile approval timeout |
| `tools/approval_gateway_wait.py` | Approval wait deadline, settlement and fail-closed timeout |
| `tools/approval_human_wait.py` | Wait lifecycle/heartbeat context used by deadline polling |
| `tools/clarify_gateway.py` | Clarify queue, exact-ID resolver and timeout/removal |
| `tools/interrupt.py` | Interrupt termination of the blocked approval wait |

## Validation

- Ruff 0.16.9, `server tools`: PASS.
- `check_plugin_surface`: PASS. Runtime Hermes import boundaries remain unchanged; no new
  request-time relative imports. Qualification tooling is outside the runtime plugin.
- `scan_private`: PASS, zero baseline. `scan_logs`: PASS on the behavioral-probe logs; the default
  captured-log directory is empty. No prompt/answer logging was added (SEC-4).
- Full requested unit/tool command with extracted-build discovery enabled: **1092 passed,
  147 failed, 2 skipped**. Of the failures, 142 are direct socket permission failures, three are
  dependent listener timeouts, one is the read-matrix reproduction's denied socket, and one is
  the offline wheel build lacking cached `setuptools`. No tests were weakened or sandbox skips added.
- Socket-free security/bridge/qualification subset: **128 passed, 5 deselected**. The five
  socket-dependent tests were also attempted in the full run above.
- T7/T8 integration explicitly selected for stock-base and experimental: **16 setup errors,
  8 deselected**, all denied loopback binds. The extra six cases assert fail-closed ACL/flag/build
  behavior. Deselected cases are owner-local, which is not one of these extracted builds.
- Direct-send matrix: boundary and behavioral probes PASS for both builds; F2/F3 integration has
  **16 socket setup errors per build**, so `qualified=false`, `candidate_entries=[]`, and no final
  qualification receipt is emitted. A provisional file is fixture bootstrap material, not evidence
  of qualification.

Existing regressions for B1/B2/B4/B5/B6 and A1–A5 remain, including unlisted devices and an
unqualified build making no loopback call. New fixture tests additionally remove the owner,
flag and qualified entry on a running gateway. The original remediation was independently
red-tested against `0c17860` (35 failures); this round adds real-Hermes and qualification coverage.

## Controller commands outside the sandbox

Run from the repository root, using the server development environment. These commands qualify
only the extracted fixtures; they never add an owner-local entry to the committed runtime list.
The first command reruns all requested CI tests, including the previously blocked socket tests.

```bash
export HMP_HERMES_BUILDS_DIR=/path/to/isolated/hermes_builds
server/.venv/bin/python -m pytest server/tests/unit tools/ci/tests tools/fixtures/tests tools/hermes_builds/tests tools/vectors/tests tools/acceptance/tests -q
server/.venv/bin/python tools/compat/run_matrix.py --target direct-send --builds stock-base,experimental --out /private/tmp/hmp-f3-round3-controller --json-out /private/tmp/hmp-f3-round3-controller/matrix.json --fixture-qualification-out /private/tmp/hmp-f3-round3-controller/qualified.json
export HMP_DIRECT_SEND_QUALIFICATION=/private/tmp/hmp-f3-round3-controller/qualified.json
server/.venv/bin/python -m pytest server/tests/integration/test_direct_send_fixture.py server/tests/integration/test_approvals_fixture.py -k 'stock-base or experimental' -q
```

Proceed to the standalone integration command only after matrix exit 0 and a final receipt exists.
The matrix itself runs both integration suites per build, rejects any skips/empty selection, and
checks that the source fingerprint did not change during qualification. It emits candidates only
after boundary, behavior and integration pass. Its final fixture receipt requires **all** selected
builds to pass; stale receipts are removed before the run.

For the currently observed extracted bytes, successful `matrix.json.candidate_entries` and
`qualified.json.builds` must contain exactly these entries:

```json
[
  {
    "label": "stock-base",
    "fingerprint": "5da717e56ca820cb2bea65ed793287e69c46e61095b6f5adc8e32b5b514dbd42",
    "git_sha": null,
    "source_sha": "04fa849e70165336ba73e6750257a1ebd7ff998d"
  },
  {
    "label": "experimental",
    "fingerprint": "81404cdbc7d4aef0165fa405170a89aeca8332bea42f0aff8f7c9544f36d5a31",
    "git_sha": null,
    "source_sha": "7e8c8f07a11a781b82ff2ad249196e2dc3f4bbb3"
  }
]
```

These hashes are observed identities, **not** a claim that integration passed. If the extracted
source changed, inspect the difference and rerun qualification; never paste these hashes into the
committed list to open the live gate. The owner-local pre-F3 hash remains preserved under
`requalification_required`. Owner-local qualification and release review remain outstanding.

## Local commit handoff

The sandbox denies writes to this workspace's `.git/index.lock`. The complete revision is
committed on `feat/approvals` in `/private/tmp/hmp-f3-round3-local-commit`; its mail patch is
`/private/tmp/hmp-f3-round3.patch`. The original workspace already contains the same file edits,
but its branch cannot be advanced inside this sandbox. No push was attempted.

On the controller, either apply that patch with `git am` to a **clean** checkout at `7173cff`,
or commit the existing edits in this workspace after running the external checks:

```bash
git add server/hmp_plugin/compat.py server/hmp_plugin/direct_send_supported_builds.json server/tests/integration/test_approvals_fixture.py server/tests/integration/test_direct_send_fixture.py server/tests/unit/test_bridge.py specs/003-approvals/REVIEW_STATUS.md tools/compat/bridge_files.py tools/compat/run_matrix.py tools/compat/approval_probes.py tools/fixtures/direct_send_fixture.py tools/fixtures/tests/test_direct_send_qualification.py
git commit -m "Bind approval qualification to Hermes security behavior"
```
