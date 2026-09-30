# Tasks: approval qualification lane

- [x] Write spec, plan and tasks.
- [x] Add empty `approval_supported_builds.json` with the bounded `bridge_files` list.
- [x] Add `APPROVAL_DEPENDENCIES`, `probe_approval_dependencies` and `approval_build_qualified`.
- [x] Leave `DIRECT_SEND_DEPENDENCIES` and `direct_send_build_qualified` unchanged.
- [x] Add the read-only `Approval qualification (on-disk source):` line to `hermes hmp compat`.
- [x] Package the new list in the wheel.
- [x] Unit tests: empty list, malformed list, missing list, missing source file, SHA mismatch, probe
      failure, independence from guarded-send qualification, CLI output.
- [x] Update `FEATURES.md` and `ROADMAP.md` as draft groundwork.
- [x] Wire the gate to AP-3/4/6, snapshot, send-stream binding and producer hooks (closed).
- [x] Review fixes: bind-independent SSE classification (M1), qualification before the lock (L1),
      supported-and-qualified adapter callback (L4), wiring and ordering tests.
- [x] Controller: full suite 1320 passed, 12 skipped, one existing warning, 25.07s
      (`/private/tmp/hmp-approval-route-qualification-pytest-3.log`); pinned Ruff 0.16.9 server
      tools PASS after only `noqa` comments were corrected; surface/private checks PASS as
      previously recorded. Earlier counts (e.g. 1197) were from the original lane.
- [x] L5/L2 repair implemented: `approval_listener_qualifier` startup baseline bound in
      `open_components`, bounded success-only probe cache, tests in `test_compat.py` and
      `test_approval_route_qualification.py`. PENDING controller full-suite, pinned lint,
      privacy/surface runs and independent review; no counts are claimed here.
- [x] Pre-fix root evidence (historical, before the F1-F4 changes below): 1339 passed, 12
      skipped, one warning (`/private/tmp/hmp-approval-route-qualification-pytest-4.log`); pinned
      Ruff, surface and private checks PASS. Preserved; it does not describe the current code.
- [x] F1-F4 gate-binding review fixes implemented (PENDING verification, no counts claimed):
      process-level admission latch in `compat.py` (first supported factory call fixes it;
      reconnect must equal it; empty/malformed/missing/unlisted first manifest latches closed until
      a FULL gateway process restart), read-identity cross-check via `read_compat_path`, approval
      list must cover the read files, startup entry must match (F2), CLI label "Approval
      qualification (on-disk source):", HMP_V1 §7b/request_ctx/DESIGN/REVIEW_STATUS corrected,
      F4 tests added in `test_compat.py`, `test_cli.py` updated. Focused tests, pinned Ruff and
      the full suite were NOT run by the implementer; controller must run them.
- [x] Root verification of F1-F4 (before the M1 choice change): pytest-5 1348 passed, 12 skipped,
      1 warning. Historical counts above (1320, 1339) stay scoped to the code they ran on.
- [x] Focused Opus review (`/private/tmp/hmp-approval-process-final-review-opus.out`) cleared
      F1/F2/F4 code as CLOSED groundwork with no material code residual; it ran no tests. Docs
      precision (baseline = first SUPPORTED factory use, no module-byte attestation) applied.
- [x] Root verified current pytest-6 after the process binding and ambiguous-label fixes:
      1364 passed, 12 skipped, one existing warning, 24.40s. The narrow deliberate Unicode-test
      lint comment added afterwards changes no behavior. Release/behavior admission is not claimed.
- [ ] Still open: full behavioral qualification, restart lifecycle, device and release gates.
      Qualification and the goal are NOT closed. Earlier scratch paths/counts are evidence only.
- [ ] Runbook: full gateway process restart after any Hermes/source/plugin change; approvals
      qualification and release stay no-go until that lifecycle is verified. The empty manifest
      is not a completed feature and no build entry has been added.
- [ ] Release gate, full matrix and physical-device gate: not satisfied.
- [ ] Remaining draft risk, unresolved: L3 in-flight rows/TOCTOU (documented limit; the
      fingerprint/HEAD reads are still not atomic and a bound stream can outlive the gate).
- [x] L2/L5 code repairs verified by root tests and focused Opus review. Actual gateway restart
      lifecycle and probe latency under load remain before admission.
- [ ] Later, separate slices: behavioral approval qualification evidence, then any build entry.
