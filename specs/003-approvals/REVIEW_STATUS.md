# Approvals review status

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
export HMP_HERMES_BUILDS_DIR=/private/tmp/claude-501/-Users-mhedhli-Documents-Coding-Hermes-Bot-Mobile/b92f30dd-0a00-4c39-90d2-4fc012477eae/scratchpad/hermes_builds
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
