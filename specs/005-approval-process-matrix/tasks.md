# Tasks: approval process qualification matrix

## Current status at the exact tested revision (supersedes every status block below)

Everything in this section applies only to HMP revision `f4730ebb901933f34c69c609e718f3984c6e62d9`
(the 005 approval process qualification matrix tooling, branch `test/seed-timeout-diagnosis`) run
against an independent clean Git clone of Hermes `8afaab3703e336d72a72c812dd2dd249f04f166a`. It is
fixture evidence, not a statement about any later revision.

- **Fresh full matrix passed.** Exit 0; all seven stages (identity, boundary, behavior, integration,
  reconnect, timing, stability) true; the integration stage selected exactly the 27 required cases:
  27 passed, 0 skipped, 0 errors, 0 failures. A final fixture receipt was written. Runtime plugin
  digest `f2ee1c97ec3ebc010f38954c1a80bca507466f082d7febf76464a871d401174b`; shipped
  `approval_supported_builds.json` still `"builds": []`.
- **Independent root validation.** Root validated the final receipt against the current fingerprints,
  JUnit digest and exact case identities, and against the independent clean Git source at the same
  revision. The receipt is an unsigned, disposable local fixture file: it is not signed,
  authenticated or promoted, and it does not authorize a manifest entry.
- **Git-install fixture lifecycle: passed in that run** (fixture clone; `.git` identity unchanged
  before and after the in-place swap). This is the fixture mode of amendment 2 only.
- **Seed-timeout diagnostics did not trigger.** The nonfatal diagnostics of amendment 5 did not fire,
  so the earlier `seed-messages` stalls (three 120-second setup timeouts in the `d8b8b08` attempt)
  were not reproduced. **Their cause remains unknown.** The earlier failures are not explained or
  erased by this pass.
- **Not claimed:** loaded-memory attestation, physical-device, live-host, release or security-review
  gates, and anything about the Phone-chat composer runtime. No manifest entry is added.
- **Integration needs a new matrix.** Integrating this revision with the app's pinned HMP revision
  (the other feature set) changes security wiring and therefore the runtime plugin digest. This
  receipt cannot qualify the integrated runtime. After root reviews the integrated revision, run a
  new full matrix on it; do not rerun the unchanged `f4730eb` revision as a substitute.

Everything below is dated history for its exact diff or run and is kept unchanged except for
labels and the two gate lines marked in "Still open".

## Implemented (written, not all verified; see the status block)

- [x] Spec, plan, tasks, checklist (this directory); `amendment-1-safety-review.md` (review rulings).
- [x] `bridge_files.py` approval dependency target.
- [x] `approval_probes.py` interrupt and timeout wait probes.
- [x] `approval_fixture.py` receipt validation, fixture-copy install/remove/rebind, mutation copy.
- [x] `direct_send_fixture.build_offline` approval receipt hook; `approval_timeout` config.
- [x] Extend `test_approvals_fixture.py`; add `test_approval_process_lifecycle.py`.
- [x] Reconnect and timing harnesses.
- [x] `approval_matrix.py` runner with explicit required IDs and final receipt.
- [x] Unit/tool tests written, including the amendment-1 regressions
      (`tools/fixtures/tests/test_approval_copy_safety.py`, additions to
      `test_approval_qualification.py`).

## Historical status (before the passing matrix; superseded by the section above)

The unit counts below apply only to their exact historical diffs. Failures and the pending-rerun
wording are preserved as written at the time.

- **Pre-safety diff only:** the locked Python 3.14 local unit/tool suites passed 1399 tests with
  12 skips (one existing aiohttp deprecation warning) and pinned Ruff was clean. Both results apply
  ONLY to the diff before amendment 1. Neither covers the real gateway.
- **Current tooling:** root ran the locked Python 3.14 full local suite: 1,443 passed, 12 skipped,
  one existing aiohttp warning; pinned Ruff passed. Focused safety tests also passed (75).
  Independent Opus review cleared the six assigned findings, including the collector repair.
  Matrix 6 stopped before execution because invocation paths differed from server-root collected
  IDs. The repaired collector confirmed exactly 27 actual IDs and matrix 7 ran.
- **Matrix 7 failure (no receipt):** terminal failure at the Phone-chat wire assertion. Diagnosis,
  independently confirmed by root: `bridge._cmid` recovers only canonical lowercase UUIDv7 ids under
  the exact `hmp:<chat>:` prefix, but T8 sent UUIDv4 ids, so the positive wire evidence could never
  pass and a refused-ID negative would have been vacuous. No integration process is running.
- **Repair (pending rerun):** all AP6/direct-send client_message_ids in `test_approvals_fixture.py`
  and `test_approval_process_lifecycle.py` now use native `uuid.uuid7()` (Python 3.14, the build's
  locked interpreter; no custom generator). Request IDs, session IDs, the exact
  `client_message_id`, `role=user`, profile-scoped and exactly-one assertions are unchanged; the
  bridge regex and server parser are not weakened. New unit regression
  `server/tests/unit/test_fixture_cmid_contract.py` (2 passed on 3.14): a fixture UUIDv7
  round-trips through `bridge._cmid` only under its own chat prefix, and UUIDv4 is rejected. It is
  skipped where `uuid.uuid7` is absent (Python < 3.14). The repaired integration tests have NOT
  been rerun.
- **Worker gates after repair:** focused 3.14 run (new regression, `test_bridge.py`, tools
  fixture tests) 216 passed, 3 skipped; pinned `ruff==0.16.9` clean. Not the full suite.
- **Follow-up (separate):** the AP6 server parser accepts bounded non-v7 strings
  (`_CMID_MAX_BYTES`) despite the contract; the app always sends v7. Tighten separately.
- **Real matrix:** the ORIGINAL run 5 baseline completed: 27/27 real gateway tests and all seven
  stages passed, on the pre-safety tooling. Its fixture-only receipt does not exercise amendment 1
  and does not qualify the current tooling. No shipped qualification, live enablement, memory,
  git, device or release claim.
- **No runtime file, shipped manifest, live home, original Hermes source or venv changed.**

## Still open (actual gate; nothing here is released or cleared)

- [x] Root: amendment-1 tests and Ruff ran (1,443 passed, 12 skipped; Ruff clean); root reran after
      the CMID repair: 1,445 passed, 12 skipped, one existing warning; pinned Ruff clean.
- [x] Root: a fresh matrix run with `--upstream-source` for a final receipt: done at `f4730eb`
      (see the current status; supersedes the matrix 8 plan).
- [x] Targeted Opus re-review of the six amendment-1 findings cleared (before the CMID repair).
- [x] Git-install lifecycle: covered by the fixture-clone mode in the `f4730eb` run (the original
      "not covered" note described the archive-only fixture and is historical).
- [ ] Git branch behavior beyond existing unit tests: not covered.
- [ ] Physical device gate: not done.
- [ ] Loaded-memory attestation: not provided.
- [ ] Release gate and security review: not done. No manifest entry is added.

## Addendum: native start readiness (amendment 3, scoped; does not close or reopen any gate above)

- [x] `direct_send_fixture.wait_for_native_listener` / `require_native_listener` /
      `start_native_gateway`: same loopback connect and 45 s hard deadline, exact-process check
      before and after connect, deadline re-checked after a successful connect (at or after it is
      `deadline`, never `ready`), connect/sleep bounded by the remaining deadline, classified
      errors (new metadata content-free; existing private log tail preserved, unredacted),
      cleanup on failure. Both native starts (first start, restart) use it.
- [x] Minimal per-start record `native_start_readiness.jsonl` (phase, outcome, elapsed, attempts,
      exit code).
- [x] Causal unit tests and real synthetic loopback smoke:
      `tools/fixtures/tests/test_native_start_readiness.py`.
- [x] Opus recommendations addressed (amendment 3 R6): process_exit precedence after a failed
      connect, cleanup tests, doc accuracy. Focused readiness 55 passed; fixture suite 262 passed;
      ruff and privacy scan clean. Worker evidence only.
- [ ] **Unresolved (still open after the passing run):** why the native listener did not start within 45 s in two setups of one
      combined-tree run while an isolated probe started in about 23.7 s. Slow import or plugin
      load is an unconfirmed hypothesis. Not diagnosed, not fixed, deadline not changed.
- [x] Root reviewed the final tooling plus focused Opus report and ran the locked local suite:
      1,613 passed, 13 existing skips, one existing aiohttp warning; pinned Ruff, plugin-surface,
      changed-file privacy and diff checks passed. No production plugin diff.
- [x] Root: a fresh 27-test real-gateway matrix run: passed at the exact `f4730eb` revision only. It
      is not the integrated runtime; integration changes the digest and needs its own new matrix.
