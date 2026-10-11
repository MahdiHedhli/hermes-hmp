# Amendment 3: process-aware native start readiness (fixture tooling only)

Status: independently reviewed fixture tooling; the fresh real-gateway matrix is pending.
Scope is fixture tooling and its tests.
No runtime plugin file, receipt, manifest, isolated source or build, or live host/home/store/device
changes. Nothing here qualifies, re-qualifies or closes any approval or release gate, and no past
qualified run is restated as current evidence.

## R1. Why

A combined-tree matrix run selected 27 required tests and 25 passed; two (the T7 timeout
case and the T8 unknown-clarification case) ended in setup errors because the native HMP
listener was not reachable within the fixture's 45 s wait. A separate isolated single probe on a
short path reached the listener in about 23.7 s with closed manifests. That probe does not
reproduce or qualify the receipt-installed and restart path.

**The cause of the slow or missing listener is UNRESOLVED.** A slow-import or plugin-load delay is
a hypothesis, not a finding. This amendment does not claim it, and it does not change the wait. It
only makes the existing wait (a) stop at once when the process it is waiting for has died, and
(b) record how each native start ended so the next run has evidence instead of a bare timeout.

## R2. Revised readiness semantics (exact)

Both native starts in `server/tests/integration/test_direct_send_fixture.py` (the first start in
the `gateway` fixture and `DirectSendFixture.restart_gateway`, which the approval lifecycle tests
reuse) now call `direct_send_fixture.start_native_gateway(..., phase="first_start"|"restart")`.
It spawns the gateway exactly as before, then `wait_for_native_listener` applies:

1. **Same condition.** A loopback TCP connect to `127.0.0.1:<hmp_port>` succeeding. Nothing new is
   required of the listener.
2. **Same hard deadline, no extension.** 45 s (`NATIVE_LISTENER_DEADLINE_SECONDS`) on the monotonic
   clock, measured from the call right after spawn. It never slides. A caller may shorten it; a
   value above 45, negative or non-finite raises `ValueError` instead of widening it.
3. **Exact-process check.** The spawned `Popen` is polled before every connect attempt and once
   more after a connect succeeds. An exited process is `process_exit` immediately (with its exit
   code), even if a connect just succeeded and even if the deadline has also passed. A dead
   process therefore cannot be qualified by an unrelated listener on the port.
4. **The ceiling binds a successful connect too.** After that post-connect poll the monotonic
   clock is read once more: at or after the deadline the outcome is `deadline`, never `ready`
   (the reported elapsed is the honest value, which may exceed the ceiling). This covers a
   last-moment connect and an OS scheduling delay in the connect or in the poll. Strictly before
   the deadline it is `ready`. There is no new ceiling and no sliding extension; the order of
   precedence is `process_exit`, then `deadline`, then `ready`. That precedence also holds after a
   *failed* connect: if the failing connect uses up the remaining time and the process exits
   meanwhile, the loop polls the process again before the deadline check and reports
   `process_exit` with its exit code, not `deadline`.
5. **Bounded requested waits.** Each connect timeout is `min(1.0 s, time left)` and each retry
   sleep is `min(0.5 s, time left)`, so the helper never asks to wait past the deadline (the old
   loop could, by up to a connect timeout or sleep). This does not promise exact wall-clock
   behaviour: the OS may return from a connect, sleep or poll later than requested, so `elapsed`
   can exceed the ceiling. What is guaranteed is that no success observed at or after the ceiling
   qualifies.
6. **Uniform failed connects.** Any `OSError` from a connect (refused, timed out, interrupted,
   other) means "not ready, try again". Other exceptions, including `KeyboardInterrupt`, propagate.
7. **Outcomes.** `ReadinessResult(outcome, elapsed, attempts, exit_code)` with outcome `ready`,
   `process_exit` or `deadline`. `require_native_listener` raises `NativeProcessExitError` or
   `NativeListenerDeadlineError` (both `NativeStartError`, a `RuntimeError`, with a
   `classification` and the result). The new structured metadata (result, record line, and the
   phase, exit code and deadline in the message) is content-free. The message also carries the
   existing local gateway log tail, bounded to the same final 4000 characters as before. That
   tail is unfiltered fixture-private material, preserved as it was: it is not redacted by this
   change, it is not a public artifact, and nothing here promises it is free of prompts, keys,
   identifiers or transcript text.
8. **Cleanup.** On any failure (including an interrupt) `start_native_gateway` stops the process it
   spawned before re-raising, so a failed restart leaves `gateway_proc` on the old, stopped
   process and teardown stays idempotent.

Unchanged on purpose: the roster wait (30 s) and the startup-marker wait (30 s) in
`restart_gateway`; body timeouts; security, config, environment and cold-cache isolation; case
selection; receipts and admission. The legacy generic `direct_send_fixture.wait_for_port` is kept but
currently unused (only a regression test calls it); `build_fixture.py --serve` keeps its own
separate wait.

## R3. Artifact record

Each native start appends one line to `<fixture>/native_start_readiness.jsonl`:
`{"phase", "outcome", "elapsed_seconds", "attempts", "exit_code"}`. The key set is closed, and
`phase` is validated to be `first_start` or `restart` (anything else raises `ValueError` before
a spawn or a write). That vocabulary is a fixed, caller-internal one: there is presently no
external authority behind it. A run
that restarts the gateway has one line for the first start and one per restart. This is local
timing evidence for diagnosis, not a qualification receipt, and it is not read by any gate.

## R4. Limits (not claimed)

- Readiness only, not ownership or authority. No listener-PID lookup is done (no `lsof`, no new
  dependency). A live spawned process plus a successful connect still reads `ready`, including if
  the port were held by something else; ports come from `find_free_port`. Readiness alone is not
  TLS or PID ownership: the fixture `Client` uses `ssl.CERT_NONE` with hostname checks off, so TLS
  establishes no identity here. The later gates that exist in the fixture are: the bearer token
  on the roster request, the roster wait (30 s, default profile present in `/hmp/v1/bots`) and,
  on restart, the startup-marker wait (30 s, the `Press Ctrl+C to stop` count in
  `home/logs/gateway.log` exceeding its pre-restart count). These are fixture-level checks; they
  are not claimed to prove which process holds the port.
- This does not shorten, explain or fix a slow start. If the next run times out, the record shows
  whether the process died or the deadline elapsed; the cause stays open until diagnosed.
- Timing is one host's local measurement, not a guarantee; see semantics 5 on the OS returning
  later than requested.
- No redaction. The new record and result are content-free by construction. The unit test that
  the process object's argv and environment never reach the error or the record proves only
  that, not that the log tail is redacted. There is no global redactor or cache policy here.

## R5. Verification

`tools/fixtures/tests/test_native_start_readiness.py` (injected clock, sleep, connect and process;
the real integration-module `restart_gateway` and `gateway` fixture with only spawn/stop stubbed;
real spawned synthetic loopback processes). The full 27-test real-gateway matrix is not run by
this amendment; root runs it after review.

Unit commands (from the repo root, pinned Python 3.14 environment, the repo's explicit pytest
configuration, no warning-suppression flags):

    server/.venv/bin/python -m pytest -c server/pyproject.toml --rootdir server \
      tools/fixtures/tests/test_native_start_readiness.py -q --basetemp=<fresh-dir>/run
    uvx ruff==0.16.9 check --config server/pyproject.toml server tools

Use a fresh dedicated `--basetemp` for each run. Earlier worker runs of this module that used a
warning-ignore flag could mask existing temp-cleanup warnings; they are not evidence about those
warnings. Root re-runs independently without suppression. The causal deadline tests cover success
before, exactly at and after the ceiling, a delayed post-connect `poll`, and dead-process
precedence, including after a failed connect that uses up the remaining time.
Cleanup tests (real `start_native_gateway`, spawn/stop stubbed) cover a record-write `OSError` on a
`ready` outcome and a missing log file on `process_exit` and `deadline`: the record is written
first, the spawned process is stopped, the error propagates and no process is returned. The real
synthetic timing test leaves scheduler slack and asserts only that no extra connect or sleep is
requested; the injected-clock tests are the hard-deadline proof.

## R6. Follow-up result (Opus review recommendations addressed; worker evidence, not certification)

Changes: a failed connect at the deadline now yields to the top-of-loop poll so an exited process
is `process_exit`; cleanup tests for record-write error and missing log; doc corrections (R2.4,
R4 TLS/ownership and gates); the integration-module import is scoped with
`monkeypatch.setitem`; the real synthetic timing bound is scheduler-tolerant (`< 2.0 s` for a
1.0 s deadline). No deadline, runtime, security or cold-cache change.

Fresh-`--basetemp`, no warning suppression, pinned `server/.venv` Python, `-c server/pyproject.toml`:
- `tools/fixtures/tests/test_native_start_readiness.py`: 55 passed.
- `tools/fixtures/tests` (whole fixture suite): 262 passed.
- `ruff==0.16.9 check --config server/pyproject.toml server tools`: all checks passed.
- `tools/ci/scan_private.py` on the six files: clean; `git diff --check`: clean.

Not run: the 27-test real-gateway matrix and the full server suite for this candidate. The root's
earlier full run (1608 passed, 13 skipped, 1 existing deprecation warning) predates this follow-up
and is prior evidence only.

## R7. Root review and final local verification

Root reviewed the final six-file candidate and the focused independent Opus report. Opus found
no code blocker; its diagnostic, cleanup-test and documentation recommendations were addressed.
Root checked the failed-connect exit precedence, successful-connect deadline, cleanup ordering,
scoped module import and unchanged production plugin diff. The fixture's TLS client does not
authenticate listener ownership; R4 preserves that limit.

Root ran the final locked local suite with a new dedicated basetemp and no warning suppression:
**1,613 passed, 13 existing skips, one existing aiohttp inheritance deprecation warning**, exit zero.
The command covered `server/tests/unit`, `tools/ci/tests`, `tools/fixtures/tests`,
`tools/hermes_builds/tests`, `tools/vectors/tests`, `tools/acceptance/tests` and `tools/compat` using
the explicit server pytest configuration. Pinned Ruff, plugin-surface check, privacy scan of the
six changed files and `git diff --check` passed. No runtime plugin file or manifest changed.

This admits the tooling for the next isolated matrix run only. All seven native stages and the
exact 27 required real-gateway cases still need a fresh pass against the final combined runtime;
no receipt, live admission, device or release gate is closed here. The startup-delay cause remains
unresolved.
