# Amendment 4: offline fixture-build setup diagnostics (fixture tooling only)

Status: independently reviewed and accepted for fixture tooling; branch publication pending. Scope is `tools/fixtures/direct_send_fixture.py`
(`build_offline`) and its tests. No runtime plugin, approval manifest, wire, gate, native-source,
receipt, live-home, installed-CLI, device or store change. No fixture manifest is promoted and no
gate is opened or closed. Matrix run 75975 is terminal and its outputs are untouched.

## R1. Observation (metadata only)

Run 4 (`/private/tmp/hmp-ap4`) selected the exact 27 required cases: 24 passed and 3 ended in a
**setup ERROR** (T7 local-run, T7 Desktop-held, T7 replay). The identity, boundary and behavior
stages passed; no final receipt was written. The error frames run
`gateway` fixture -> `build_offline` -> `subprocess.run(..., check=True)` and end in
`CalledProcessError` exit 1 from `build_fixture.py` (offline). These are **not** the readiness
45 s timeouts of amendment 3: every failure here happened before any native gateway was started.

## R2. Where the three partial fixture trees stopped (file existence/counts/mtimes only)

All three lack `fixture_meta.json`, `approval-probe/`, every `gateway*.log` and
`native_start_readiness.jsonl`, and their `xdg_state/A` is empty. The plugin copy exists with both
supported-builds files at their copy-time mtime (no receipt installed). All four named profiles
exist. They stopped in `build_instance` step 3 (per-profile seeding) for profile `f1-alpha`, at
**different** points:

| Case | Reached | Evidence |
| --- | --- | --- |
| T7 local-run | conversation messages file written; no `state.db` | 1 file in `tmp/A`, no `state.db` |
| T7 Desktop-held | other-session seeding under way | 3 message files in `tmp/A`, `state.db` present |
| T7 replay | seeding started; `state.db` present | 1 message file in `tmp/A` |

For comparison a passing T7 fixture holds 11 message files, `fixture_meta.json` and a full home.
Span between first and last write in each failed home: about 10 s, 17 s and 128 s. The build
stopped within seeding, never in plugin copy, profile creation or native start.

## R3. Cause: UNCONFIRMED (evidence gap)

The build child's stdout/stderr were captured in memory (`capture_output=True`) and dropped when
`CalledProcessError` was raised; nothing is retained in any of the three trees or in the run's
logs. The exact failing child (`hermes` CLI or a seed script), its exit code and its message are
therefore **not known**, and this amendment does not guess. Independent offline builds in scratch
with a minimal environment succeeded twice (root) and once more here (R6), which shows the
build can pass but does not prove the cause is fixed or that an ambient variable was involved.
The different stop points are consistent with a transient or environmental failure in a child
command, and with nothing else that is established. Root approved rerunning only the three failing cases in fresh disposable roots with the new
diagnostics, before deciding whether to run the complete unchanged matrix. Their earlier cause
remains unconfirmed; a successful rerun would not retrospectively identify it.

## R4. Future capture (implemented)

`build_offline` runs `build_fixture.py` with `check=False`. Before launching it, it arranges the
private output directory; on a failure it retains the output into that same directory.

Destination contract (`_open_private_output_dir`):

- the absolute `out` path is walked from `/` one component at a time with
  `openat(O_RDONLY|O_DIRECTORY|O_NOFOLLOW)`: a symlink in **any** component (not only the last) is
  refused, nothing is resolved, and a `..` component is refused. The only normalization is the known
  platform alias table `/tmp -> private/tmp` and `/var -> private/var`, applied only while that alias
  is a root-owned symlink with exactly that target; it is not a general resolver;
- **ancestor policy**: every directory above the final one (including `/`) must be a directory owned
  by root or the effective uid and not group/other-writable, so nobody else can rename the final 0700
  directory while a pathname is in use and the fixture and the retained fd cannot diverge. The sole
  exception is the known shared temp base, canonical `/private/tmp` (or `/tmp` where that is the real
  directory), accepted only when its actual metadata is a root-owned directory with the sticky bit.
  No other sticky or foreign-owned directory is trusted (`/private/var/tmp` is deliberately not
  listed: no caller needs it). Nothing is chmod-ed and no intermediate directory is created;
- only the **final** component may be created (`mkdir` mode 0700 relative to the already-opened
  parent fd). Missing intermediate parents are never created and nothing is written through them;
  a missing parent means no retention. Nothing is ever chmod-ed: a pre-existing `out` is used only if
  it is already owned by this user and its mode is exactly 0700. Any other `out` (symlinked ancestor,
  missing parent, `..`, foreign owner, 0755) is **refused by `build_offline` before any child is
  started**: `FixtureSafetyError` `phase=build_offline_destination
  private_output=not_retained_unsafe_destination`, no path, `from None`. It is left as it was (never
  chmod-ed, nothing created or written). `_retain_build_failure_output` still returns
  `not_retained_unsafe_destination` when handed a directory that fails its own re-check or whose file
  name is already taken (a defence in depth case, not reachable for a refused destination);
- `out` must be outside the real home (`assert_outside_real_home`, as before);
- the fd is held across the build, so the file is created in the inode that was validated, never in
  whatever the path names afterwards. The directory is re-checked (owner, 0700) when written.

Retention (`_retain_build_failure_output`, never raises):

- raw stdout/stderr go to `<out>/build_offline_failure.log`, mode 0600, created
  `O_CREAT|O_EXCL|O_NOFOLLOW` relative to that fd; a pre-existing or symlinked target is never
  followed or changed;
- each stream keeps its final 64 KiB with its full byte count in a header line. This is a
  **file-retention** cap only: `capture_output=True` still holds each stream whole in the parent's
  memory until the child exits, so it is not a limit on that memory and not a redesign of it;
- a write/close failure, or a zero/negative/non-integer/oversized write return (no progress), returns
  the closed status `not_retained_write_failed` with no retry and no spin;
- the caller's own close of the held directory fd suppresses `OSError` only, so it can never replace
  the native failure (or a success); the retention status is unchanged by it;
- a write/close failure returns the closed status `not_retained_write_failed`. The native phase and
  exit code are preserved in the raised error; no retry; no exception text or path from the I/O
  failure is kept. An incomplete file is removed only through the original dir fd and only if the
  name still refers to the inode this call created (otherwise it is left alone, and a failed cleanup
  is not retried). A cleanup failure can therefore leave a partial 0600 file in the private directory;
- the raise is a closed `FixtureSafetyError`: `phase=build_offline exit_code=<n>
  private_output=retained|not_retained_unsafe_destination|not_retained_write_failed`. No argv,
  environment, output or path, and `from None` so no `CalledProcessError` rides along. The exit is
  never turned into a pass and is never retried. A `FileNotFoundError` for the interpreter propagates
  unchanged.
- a **zero exit whose stdout is not one UTF-8 JSON object** raises the same closed error with
  `phase=build_offline_output exit_code=0 stdout_bytes=<n>`; the body is retained privately the same
  way. Reason (verified, see R7): pytest's long traceback prints each frame's arguments, so an
  uncaught `json.JSONDecodeError` from `json.loads(s=<child stdout>)` put the whole body in a real
  failure report. `--showlocals`/`-l` would show a frame local too; that remains opt-in by the caller.

The raw file is unfiltered fixture-private diagnostic material for the root reviewer only. A native
failure's output can include the inner build/seed trace text. It stays in the private file, is not
redacted (a scrubber could mask an auth bug), is not a public artifact and is never quoted in an
exception or a report. This is path/permission hygiene for one file, **not an OS sandbox** and not
complete containment of the child's ambient environment (see R5, R6).

## R5. Privacy risk (recorded, not confirmed leaked)

Before this change `build_offline` passed `dict(os.environ)` to the child and used
`check=True`. The resulting `CalledProcessError`/frame kwargs serialize the caller's environment,
and the root error trace was seen to include ambient variables (a browser public verification key
and Codex variables). This is a **diagnostic privacy risk**, not a confirmed credential leak; it
stays recorded until root verifies it fixed in a real run. The same ambient environment still
reaches children of other fixture helpers (`run_hermes_cli`, `run_seed_script`, native gateway
start) through `clean_hermes_env`, which strips only `HERMES_*`/`XDG_*`. Those are out of scope for
this amendment and are listed as a follow-up for root to decide.

## R6. Child environment allowlist (proposed from the owning code)

The code under the build (`build_fixture.py`, `_fixture_common`, `fixture_seed.py`,
`fixture_pairing_cli.py`, `approval_fixture.py`, `server/hmp_plugin`) reads no environment variable
except `HMP_HERMES_BUILDS_DIR` (by `build_fixture.py`, also passed as `--builds-dir` by some
callers), `HERMES_*`/`XDG_*` (which it sets itself), and `PATH`/`HOME` (by `clean_hermes_env`).
`HMP_DIRECT_SEND_QUALIFICATION` and `HMP_APPROVAL_QUALIFICATION` are read by the **parent** after
the build. So the child gets exactly:

`PATH, HOME, TMPDIR, LANG, LC_ALL, LC_CTYPE, PYTHONDONTWRITEBYTECODE` (when set in the caller) plus
`HMP_HERMES_BUILDS_DIR` (the explicit `builds_dir`, else the caller's). `TMPDIR`/`LANG`/`LC_*` are
toolchain basics for `git`/Python; `PYTHONDONTWRITEBYTECODE` is the matrix's own control. Nothing
else, in particular no credential, `HERMES_*`, `XDG_*`, proxy, `PYTHONPATH`, `VIRTUAL_ENV`,
`SSL_*` or `UV_*` variable. Root accepted this allowlist **provisionally** on the strength of one real offline build passing;
that is not proof of the cause. Root may still veto a name if the matrix host needs it.

Validation: one offline build of instance `A` of `approval-dogfood-8afa-git-public` (independent
clone `8afaab37...`, offline, no gateway/model/API) through this `build_offline` exited 0 in
about 18 s with all four profiles. Across that run the pinned build's `git rev-parse HEAD` (`8afaab3703e336d72a72c812dd2dd249f04f166a`),
its `git status --porcelain` line count (0) and a combined SHA-256 of `tools/fixtures/*.py` +
`server/hmp_plugin/*.py` were identical before and after (the tooling hash was taken with the edit
already in place, so it shows the run changed nothing, not that the edit is absent); the run wrote
only to a scratch directory. This shows the allowlisted build can pass; it does not show the
failing-run cause. The installed Mac Hermes is not the fixture.

## R7. Tests

`tools/fixtures/tests/test_offline_build_diagnostics.py` (27 tests): positive offline JSON parse;
allowlist exact, explicit controls kept; a real child never sees ambient secrets (including receipt
variables); closed message with phase/exit code only and no marker, secret, path, argv or cause;
0600 file and 0700 created directory; single call with `check=False`; 64 KiB tail cap. Destination:
symlinked `out`; **symlinked ancestor** (existing leaf: destination unchanged; absent leaf: nothing
created through the link); missing parent not created; `..` refused; existing 0755 `out` unchanged
and unused; existing target file unchanged and symlinked target not followed; group/other-writable
`out` refused; a 0777 non-sticky ancestor and a (mocked) foreign-owned ancestor refused with zero child calls and bytes/mode unchanged; the trust rule table (root sticky `/tmp` valid, arbitrary sticky or `/private/var/tmp` hostile paths refused); a real root-sticky `/tmp` ancestor valid; the real `/tmp` alias normalized while a symlink beneath it is still refused. Every refused
destination is asserted to make zero child calls, to leave ancestor/target bytes and the 0755/0777
mode unchanged, and to carry `phase=build_offline_destination` with no path; a fresh valid 0700 path
is still created and retained. A zero-progress `os.write` finishes bounded with the native exit kept;
a failing close of the owned directory fd keeps `exit_code` and `private_output=retained` with no raw
marker or path.
Failure handling: a monkeypatched `os.write` error and a close error each give
`not_retained_write_failed`, keep `exit_code`, leak no path/error text, make one subprocess call and
leave no file; cleanup never unlinks a different file that replaced the name. Malformed success:
closed error without the body, body only in the private file, and a real nested pytest run with
`--tb=long` whose report does not contain the body (with a control showing the same harness does see
a plain `json.loads` body). A mutation check (final-component-only open, and no-fd walk) fails the
ancestor, write-failure and alias tests, so they are causal.

## R8. Independent root review and next action

Root accepted the bounded offline-builder allowlist and diagnostic destination/retention changes.
On the final candidate root independently ran the pinned Python 3.14 fixtures and CI tooling tests:
**312 passed**. Pinned Ruff 0.16.9 with `server/pyproject.toml`, the public private-content scanner,
plugin-surface scanner and diff whitespace check passed. Root inspected the descriptor walk,
ancestor policy, closed errors, zero-progress writes, close failures and malformed-output tests.
The source and test SHA-256 values are respectively
`4be6b00a359f7176a5977a27f320df8dc755ddf1325af17e379139ac9a00151f` and
`a2e8399f7b3fe1fd6b333f8698fa0a60755a8547f517a7af23109e7f50e66a61`.

Root's prior real offline build succeeded with one instance, an unchanged independent Git source
and a private 0700 output directory. That build predates the final ancestor-policy addition;
it does not qualify a gateway or diagnose the original three failures.

The next authorized step is the three formerly setup-failing cases, using fresh scratch, exact
source identity and fixture-only receipts, with a minimal environment for the parent test process
and a disposable caller home. Remaining helpers still inherit that parent; their general ambient-
environment risk is open outside this contained invocation. If those cases pass, run all unchanged
27 required cases and the seven matrix stages on the actual new tooling candidate. A partial rerun
cannot produce a qualification receipt or open a live gate. Unbounded in-memory stream capture,
`--showlocals` exposure, and unavailable Run 4 stderr remain explicit limitations.

