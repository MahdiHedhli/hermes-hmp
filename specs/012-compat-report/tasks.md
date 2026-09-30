# Tasks

- [x] Accept only the format-1 candidate receipt: exact keys, exact-true checks, tests run > 0, SC007 block, no failed stage.
- [x] Bind it to this host (Hermes SHA and read fingerprint), reject already-listed builds, dirty or missing HMP source, and a mismatched installed HMP version.
- [x] Reject stale (over 7 days) and future receipts, and receipts not owned by the current user or writable by group/others.
- [x] Build the fixed-allowlist payload with an explicit unverified/advisory marker, the matrix HMP source SHA, and the matrix (not CLI host) OS and Python.
- [x] Print the fixed destination, effective GitHub login and the exact issue body (with fences) before the prompt; consent is `REPORT` plus newline only.
- [x] Send through authenticated `gh` with a 0600 body file, argument list, no shell, cleanup; the printed body is the sent body.
- [x] Report preflight failures as "not sent" and any started-create failure as "delivery unconfirmed" with a check-before-retry instruction.
- [x] Add focused offline tests for each boundary and update docs.
- [x] Run the stacked tests and Ruff locally: 1,357 HMP unit tests passed (11 fixture skips), including nine in-tree writer contract tests; Ruff passed. CI remains pending.
- [x] Reconcile `checks` key names and `matrix_runtime` spellings with the candidate-receipt writer's `_run_candidate_stages`; add an `ast`-based contract test (`HMP_MATRIX_WRITER`).
- [x] Independent-review remediation: discard pending TTY input after the disclosure and before the prompt; re-read the login after consent; Ctrl-C before create is "not sent" (130); `gh` discovery accepts an absolute `~/.local/bin`, `~/bin` or snap/Homebrew symlink and refuses relative/cwd `PATH` entries, reporting "missing" and "unsafe" separately; `gh` environment gains keyring, proxy and certificate variables only; uncommon or null matrix OS reports as `other`.
- [x] No pre-consent duplicate search (it would reveal the Hermes SHA); manual duplicate check documented.
- [x] Status is Draft; docs scope the host match (HEAD commit plus bridge-file hash, not local edits elsewhere) and state the version-only HMP source comparison.
- [x] Extend the `ast` contract test to `hmp_source` keys, literal `format`/`mode`, candidate/SC-007 values, the timestamp format and the runtime expressions; default to the in-tree writer, `HMP_MATRIX_WRITER` overrides.
- [x] Stack this branch with the writer branch and confirm the in-tree writer contract test runs (9 passed locally; CI pending).
- [ ] Ship the ad-hoc matrix branch so real receipts exist (remaining dependency).
- [ ] Review PR; exercise once against a real candidate receipt and a scratch GitHub account.
