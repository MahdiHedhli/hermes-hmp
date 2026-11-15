# Amendment 5 (evidence + approved instrumentation): offline fixture `seed-messages` timeout

Status: **Cause not confirmed. Instrumentation is a candidate pending root acceptance; it is not self-certified.** Scope: the offline fixture build's `fixture_seed.py seed-messages`
call at `build_fixture.py` `build_instance` (the `conv-long` conversation of profile `f1-alpha`,
instance `A`), run under `_fixture_common.run_seed_script` (`timeout=120.0`, unchanged). This file
quotes metadata only: no raw log, environment, home path or transcript text. It does not claim
matrix admission; the full-run terminal result (24 passed, 3 errors) is recorded separately by root.

## E1. Observed in three preserved failed trees (file existence/mtimes/sizes only)

Three trees were inspected from a run while it was still active. The six failure logs seen at
observation time are **not** the final retained set (root's final matrix retains exactly three
errors/logs); the counts here are observation-time and not a full final census. Each is a
`subprocess.TimeoutExpired` (120.0 s) in `run_seed_script`, before any gateway started. The trees
differ in what exists on disk:

| Tree | Root `state.db` | Profile `state.db` | Partial metadata |
| --- | --- | --- | --- |
| 1 | absent (only `state.db.quarantine.lock`) | absent | no main DB file yet |
| 2 | present | absent | no `sessions.json` |
| 3 | present | present; a copy shows 1 `sessions` row, 0 `messages` rows | schema and session row exist |

Quarantine-lock and `fts_rebuild.lock` files also exist in passing builds, so their presence does
not discriminate. This partial-database metadata indicates only that the child had made some
progress. It **cannot prove the exact stack position**, and it does **not rule out** a message
append or commit that was in flight or lost at kill time.

Failure-log mtime minus messages-file mtime was roughly 120 s, 131 s and 194 s. These mtime spans
**do not measure the actual kill-to-exit time** (log and file mtimes bound neither the moment of
the kill nor the child's exit), so nothing is concluded about post-kill behavior.

## E2. Scratch reproduction: three attempts, NOT reproduced

A scratch launcher (not a repo file) wrapped `fixture_seed.main` with a repeating
`faulthandler.dump_traceback_later` into a private file, run through the real `build_fixture.main`
for instance `A` of `approval-dogfood-8afa-git-public` with allowlisted subprocess environments and
disposable `HOME`/`TMPDIR`. Attempts 2 and 3 used a parent calling
`subprocess.run(capture_output=True)` like `build_offline`. All three builds exited 0 in about
16 s; `seed-messages` for `conv-long` took about 2.1 s (600 messages). **No stack was dumped in
any of the three.** A fourth launch failed at the dependency install step because of a shell setup
error before any seed ran; it is excluded. Host load was high (an external matrix was running), so
load alone did not reproduce it. The installed `~/.hermes` was not executed or written.

## E3. What is and is not concluded

- Concluded: three preserved failures hit the 120 s deadline with partial on-disk progress at
  differing points; three instrumented attempts did not reproduce it.
- **Not concluded:** the cause. Lock contention, a native wait, resource exhaustion, a host stall,
  or any whole-process or kernel-level stall are all unexcluded and unestablished. The native code
  has bounded waits near the deadline (`_FTS_REBUILD_LOCK_TIMEOUT_SECONDS = 120.0`,
  `_WRITE_PATIENCE_S = 20.0`, quarantine lock 5 s); they are places to look, not findings.

## E4. Approved instrumentation (nonfatal, explicit opt-in)

Root rejected sending `SIGABRT` to the child: it can write core files containing secrets and
changes the fatal-signal semantics. Instead:

- `fixture_seed.py --diagnostic-stacks` (a global flag; it must precede the subcommand) arms
  `faulthandler.dump_traceback_later(90.0, repeat=False, exit=False)` to stderr immediately before
  the subcommand handler and cancels it in a `finally` on normal return, `SystemExit` and
  exceptions. One all-thread Python stack, no signal handler, no core, no locals, environment or
  argv. Stdout (the JSON contract), `__main__`, `sys.path` and the 120 s deadline are unchanged;
  without the flag (direct, Dart or default invocation) nothing changes.
- `build_fixture.py --private-seed-diagnostics` (default off; rejected with `--serve`) is passed
  by keyword through `build_instance_if_needed`/`build_instance` to the `seed-messages` call only,
  which prepends `--diagnostic-stacks`. Every other seed or CLI call is unchanged.
- `direct_send_fixture.build_offline` adds the flag only after its private 0700 output directory
  descriptor is held, before the child starts; an unsafe destination launches no child. The stack
  stays in the captured stderr, retained only in `BUILD_FAILURE_OUTPUT` (0600, existing size caps)
  on failure; it is never in the closed `FixtureSafetyError` or the pytest report.
- **Sensitive stderr:** a person running `build_fixture.py --private-seed-diagnostics` or
  `fixture_seed.py --diagnostic-stacks` by hand must capture stderr privately (0600, private
  directory). Stack frames carry file paths and function names.

Tests: `tools/fixtures/tests/test_seed_diagnostic_stacks.py` (real child processes with a synthetic
slow handler and a short interval injected only inside that child; the 90 s constant and 120 s
deadline are asserted unchanged).

### Limitations

- A stall before the timer is armed (interpreter start, imports, argument parsing) is not captured.
- Python frames are not kernel proof: a thread blocked in a native call or syscall shows only its
  Python caller, and a stack at 90 s may not be the position at 120 s.
- `capture_output=True` in `build_offline` still buffers child output in memory without a bound;
  only the retained file is capped.
- Other helpers' environment policies (including `run_seed_script`'s `clean_hermes_env`) are
  unchanged.
- A missing stack from a future failure is inconclusive: the child may have stalled before arming,
  the arm or dump may have failed, retention may have failed, or the child may have died first.
  It is neither evidence of a cause nor of its absence.


## Root acceptance checkpoint

Root reviewed the final narrow tool diff and independently verified the final 15 diagnostic
cases with the pinned Python 3.14.6 interpreter and a fresh private pytest root. These include
causal cancellation after caught SystemExit/failure and real stack output retained privately
while absent from an ordinary long pytest report, with an intentionally leaky control. Root
also passed 300 fixture-tool tests before those final test refinements and 23 CI-tool tests;
no final full-suite count is inferred from these separate runs. Configured Ruff 0.16.9,
private-content, plugin-surface and diff checks passed. No native timeout cause, complete matrix
pass, runtime approval admission or device behavior is established by this tooling acceptance.
