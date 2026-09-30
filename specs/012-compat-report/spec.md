# Operator-consented compatibility report

Status: Draft implementation candidate for issue #24. It never qualifies a build. The
receipt writer it consumes is in draft PR #46; nothing here has shipped.

## Operator outcome

`hermes hmp compat report --matrix <receipt>` lets an operator whose Hermes build
passed the ad-hoc candidate compatibility matrix tell HMP maintainers, after
seeing exactly what would be sent, where, and under which GitHub login. The
report is advisory, unverified data for a reviewed listing; it does not admit
the build, edit a compatibility list, or import the read bridge.

## Interface consumed: the format-1 candidate receipt

The receipt is written by the ad-hoc matrix on the tooling branch
(`infra/ad-hoc-compat-matrix`). This feature accepts only this shape and refuses
any other, including unknown or missing keys at every level and the listing-mode
`run_matrix` receipt:

- `format` = 1 (an integer), `mode` = `"candidate"`, `generated_at` = UTC
  `YYYY-MM-DDTHH:MM:SS[.ffffff]Z`.
- `hmp_source` = `{commit, version, worktree_dirty}`: 40-hex commit, a version
  string, and `worktree_dirty` exactly `false`.
- `matrix_runtime` = `{os, python}`: the OS and Python the *matrix* ran on. `os` is
  `platform.system()` or null (undetermined); `python` is `major.minor`.
- `candidate` = `{label = "candidate", commit, python_requested, fingerprint}`.
- `checks` = exactly the writer's ten keys, in its order: `clone_commit_matches`,
  `extraction_metadata_valid`, `extraction_metadata_commit_matches`,
  `interpreter_matches`, `source_fingerprint_matches`, `selfcheck_passed`,
  `read_suite_passed`, `sc007_passed`, `sc007_bound_to_candidate`,
  `source_unchanged_after_run`, each exactly `true`. Missing, extra or renamed
  keys refuse. The payload's `stages` reports these same ten names as `pass`.
- `runtime_dependencies` (a bounded object of package name to version or null)
  and `assurance` (a bounded string) are the writer's commentary. They must be
  present and well-formed; they are never copied into the report.
- `read_suite_tests_run` an integer greater than 0.
- `sc007` = `{label = "candidate", ran = true, ok = true, status = "unsupported",
  why = "hermes_build_unsupported", bridge_imported = false}`.
- `failed_stage` = `null`, `candidate_passed` = `true`.

## Requirements

- Require stdin and stdout TTYs and no `HERMES_SESSION_*` variable, before
  reading anything.
- Receipt file: regular, non-symlink, at most 512,000 bytes, owned by the current
  user, not writable by group or others; strict JSON (no duplicate keys or
  non-finite numbers).
- Fresh: `generated_at` at most seven days old and not in the future (five
  minutes of clock skew allowed).
- Bound to this host: `candidate.commit` equals this host's Hermes git SHA and
  `candidate.fingerprint` equals its read-bridge fingerprint (file reads only).
  No git SHA, or an unidentifiable host, refuses. The host identity is the `.git`
  HEAD commit plus a hash of the read-bridge files as they are on disk: a local
  edit to a bridge file changes the fingerprint and refuses, but a local or
  untracked edit anywhere else in the Hermes tree, or an uncommitted change that
  leaves HEAD in place, is covered by neither. The match means "this commit's
  bridge files", not "this tree is exactly that commit".
- Not already listed: a build that `compat.match_build` finds in the committed
  read-compat list refuses. An unreadable list refuses.
- HMP source: `worktree_dirty` must be exactly `false`, and `hmp_source.version`
  must equal the installed HMP version. This is a version-only comparison: an
  installed copy carries no source SHA, so `hmp_source.commit` is reported as the
  matrix claimed it and is not checked against what is installed. Two different
  HMP sources with one version string are indistinguishable here.
- The receipt is unsigned, so the payload carries a fixed `advisory` field saying
  it is unverified and not an attestation, plus the matrix's HMP source SHA.
- The payload is a fixed allowlist: advisory, Hermes SHA, read fingerprint, HMP
  version, matrix HMP source SHA, receipt timestamp, read-suite test count, named
  stage results, and the *matrix* OS family (macOS, Linux, Windows, other) and
  Python `major.minor`. The CLI host's OS and Python are not reported. Nothing
  else is copied from the receipt or host. A null or uncommon matrix OS (for
  example FreeBSD) is reported as the fixed word `other`, never copied; an OS
  value that is not a known `platform.system()` name, such as a hostname, refuses.
- Before the prompt, print the fixed destination (`MahdiHedhli/hermes-hmp`,
  fixed title), the effective GitHub login, and the exact issue body including
  its code fences. The login comes from one read-only `gh api user` in the same
  environment as the send; if it cannot be determined nothing is offered. That
  is the only request made before consent. There is no duplicate search, because
  it would tell GitHub the Hermes SHA before the operator agreed; the operator
  is told to check the issues manually.
- On POSIX hosts, after the whole body is printed and before the prompt, discard any pending
  terminal input (`tcdrain` then `tcflush`), so
  text typed or pasted ahead can never be consent. If input cannot be discarded
  the command sends nothing.
- This version refuses cleanly on Windows because receipt ownership relies on POSIX user IDs.
- Consent is `REPORT` followed by a newline, exactly. Padding, other case, a
  missing newline, EOF, or an interrupt sends nothing.
- After consent and before create, read the login again; if it differs or cannot
  be read, send nothing. Ctrl-C during preflight, or before `gh issue create`
  starts, is "not sent" and exits 130.
- Find `gh` by walking `PATH` like a shell and judging the first executable `gh`:
  a relative or empty entry is refused; an absolute one is accepted anywhere
  (`~/.local/bin`, `~/bin`, a snap or Homebrew symlink, run by its unresolved
  path) if what it resolves to is a regular file owned by the user or root and not
  group/world-writable, in a directory owned by the user or root that is not
  world-writable. "Not found" and "found but unsafe" are reported differently.
  A group-writable directory (a Homebrew `admin` group) is tolerated.
- Send only with the operator's own `gh issue create`: fixed repo and title, a
  0600 temporary body file holding the printed body, an argument list, no shell,
  no stdin, and an allowlisted environment pinned to github.com. The allowlist is
  `PATH`, `HOME`, `TMPDIR`, `LANG`/`LC_*`, `GH_TOKEN`, `GITHUB_TOKEN`,
  `GH_CONFIG_DIR`, `XDG_CONFIG_HOME`, `XDG_RUNTIME_DIR`, `DBUS_SESSION_BUS_ADDRESS`
  (Linux keyring), the `HTTPS_PROXY`/`HTTP_PROXY`/`ALL_PROXY`/`NO_PROXY` family in
  both cases, and `SSL_CERT_FILE`/`SSL_CERT_DIR`. `gh` debug, pager, repository and
  host controls are never forwarded. Remove the file on every path.
- Outcomes are reported truthfully:
  - A failure before `gh issue create` starts (no or unsafe `gh`, no login, a
    changed login, an interrupt, temporary file error) prints "Report was not sent".
  - Once create has started, a nonzero exit, timeout, launch failure or
    interrupt prints "Delivery unconfirmed" and tells the operator to check the
    repository's issues before retrying. It never says the report was not sent.
  - No error path prints `gh` output or the body. No path changes a
    compatibility gate or list.
- Inputs, `gh`, the clock, the committed list and the temporary directory are
  injectable for tests.

## Acceptance

Offline tests cover: a consented send (argv, same environment for login lookup
and create, body-file mode and cleanup, printed body equals sent body); refusal
of every non-exact receipt field, stale, future and wrongly-shaped receipts,
dirty or mismatched HMP source, another user's or group/world-writable receipts,
already-listed and mismatched hosts; matrix (not CLI host) OS and Python;
non-interactive refusal; every non-`REPORT\n` answer; consent typed before the
body was shown (discarded), and a terminal that cannot discard; a login that
changed or cannot be re-read after consent; Ctrl-C before create; `gh` discovery
(`~/.local/bin`, `~/bin`, snap/Homebrew symlinks accepted, relative and cwd
entries and unsafe files refused, missing versus unsafe); the `gh` environment
allowlist; the OS mapping; preflight failures as "not sent"; and create failures
as "delivery unconfirmed". The `ast` contract test checks the writer's keys at
every level, its literal `format`/`mode`, its candidate and SC-007 values, its
timestamp format and its runtime expressions. No real `gh`, network, Hermes
install, or Hermes home is touched.

## Known limits and open dependency

- **Remaining dependency.** The schema is reconciled with the writer's
  `run_matrix.py::_run_candidate_stages` in draft PR #46
  (`infra/ad-hoc-compat-matrix`). An `ast`-based contract
  test reads it as text and never imports or runs it. It checks the receipt keys
  at every level, the literal `format`/`mode`, the `candidate`/SC-007 values, the
  timestamp format and the runtime expressions. It looks for the writer at the
  in-tree `tools/compat/run_matrix.py` and is skipped only when that file has no
  candidate writer at all; `HMP_MATRIX_WRITER` points it at another copy and, when
  set, a missing file is a failure. Once the writer and this report share a tree
  the test runs in CI. The writer is not shipped, so real receipts exist only
  once it is; a later writer change must be re-reconciled.
- **Not exercised for real.** No real receipt, `gh` or GitHub account has been
  used with this command; every test is offline.
- **Duplicate reports.** Nothing checks for an existing report; see above. Two
  reports for one build are possible.
- Receipts are unsigned and self-reported. Matching this host is a sanity gate,
  not an attestation, and maintainers must rerun the matrix before listing.
- A public issue cannot be reliably retracted.
