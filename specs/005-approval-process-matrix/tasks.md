# Tasks: approval process qualification matrix

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

## Current status (single block; supersedes every earlier status note)

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
- [ ] Root: a fresh matrix run (matrix 8, after the CMID repair, with `--upstream-source`) for any
      final receipt.
- [x] Targeted Opus re-review of the six amendment-1 findings cleared (before the CMID repair).
- [ ] Git-install lifecycle: not covered; the fixture is an extracted archive without `.git`.
- [ ] Git branch behavior beyond existing unit tests: not covered.
- [ ] Physical device gate: not done.
- [ ] Loaded-memory attestation: not provided.
- [ ] Release gate and security review: not done. No manifest entry is added.
