# Plan: approval process qualification matrix

1. `tools/compat/bridge_files.py`: `--dependencies-attr APPROVAL_DEPENDENCIES` probes read + guarded
   send + approval dependencies (the same union rule as direct send) so the committed approval list
   can be checked against the real build. `_ALL_DEPENDENCY_ATTRS` is unchanged, so read and
   direct-send AST exclusions do not weaken.
2. `tools/compat/approval_probes.py`: add in-process interrupt and timeout wait probes that call
   Hermes' real `_await_gateway_decision` on a thread (fail-closed deny; no execution path).
3. `tools/fixtures/approval_fixture.py`: receipt validation, manifest install/remove/rebind for the
   fixture plugin copy only, plugin-source digest, and the mutation-copy helper (venv finder and
   shebang rewrite, self-import check).
4. `tools/fixtures/direct_send_fixture.py`: `build_offline` installs an approval receipt only when
   `HMP_APPROVAL_QUALIFICATION` is set; `write_direct_send_config` gains `approval_timeout`.
5. Integration tests: extend `test_approvals_fixture.py` (Bot Chat deny, phone text/slash refusal,
   real expiry, extra fail-closed cases, extra build labels via `HMP_FIXTURE_EXTRA_BUILDS`); add
   `test_approval_process_lifecycle.py` (empty-start, admitted-start, in-place swap on a copy).
6. `tools/compat/approval_reconnect_harness.py` and `approval_timing.py`: build-interpreter
   subprocess helpers, each a fresh process so the module-level latch is fresh.
7. `tools/compat/approval_matrix.py`: stages identity -> boundary -> behavior -> integration ->
   reconnect -> timing -> stability, explicit required IDs, final receipt.
8. Unit/tool tests in `tools/fixtures/tests/test_approval_qualification.py`.
9. Draft-status docs only (`FEATURES.md`, `ROADMAP.md`, spec 004 tasks).

## Risks

- The approval boundary check may find the committed approval list incomplete for the pinned
  build. That would be a contract finding to report, not something to paper over in the tool.
- Integration tests were authored without executing them in the authoring session; the first root
  run may expose fixture timing or status-code mismatches that are test bugs, not gate bugs.
- Mutation copy is ~400 MB; it is made once, only for the swap test.
