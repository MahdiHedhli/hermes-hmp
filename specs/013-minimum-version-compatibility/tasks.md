# Tasks

- [x] Add `hermes_version.py` (file-only parser, floors, `KNOWN_RELEASES`) and its tests.
- [x] Add `evaluate_eligibility`, the `Feature`/`Unavailable` enums and the thin `CompatGate` wrapper.
- [x] Replace the file-list containment with Hermes-tree plus stdlib containment; add `paused` and
      positional-count checks; split the read table; add jobs and model tables.
- [x] Remove every exact-build admission gate (read, send, jobs, model); keep `match_build`,
      `GitFingerprintReader` and the `qualified_build` matchers as evidence tools.
- [x] Compute eligibility once in `open_components`; rename the context fields to `*_available`;
      separate the owner send flag from send availability; fix the health snapshot label.
- [x] Register the SES routes only when session browsing is available.
- [x] Rewrite `hermes hmp compat` and the `setup check` hint; add `--issue-draft`, `--feature` and
      `--failure-code` in the offline `issue_draft.py`.
- [x] Tests: parser, eligibility, probe containment and signatures, route behaviour, CLI wording,
      draft golden body, allowed and refused pairs, privacy canary, no-network/subprocess/browser.
- [x] Adapt the obsolete exact-gate tests to evidence or availability tests without removing any
      security negative test.
- [x] Amend the constitution, CONTRIBUTING, HMP_V1, conformance summary and the user docs.
- [x] Run the CONTRIBUTING suite, Ruff, the plugin-surface check and the privacy scans.
- [x] Review repair (B1, B2, N1, N3, N6): issue-draft helpers revalidate every value themselves;
      `SessionDB.get_session` is a send dependency; the install stamp is read as UTF-8 with an
      optional BOM and wins over the literal; the inert `deps.qualified()` hook is removed.
- [ ] Follow-on, not in this slice (no live claim): N2 `ServerContext.send_available` and
      `session_browsing_available` default to True while the cron/model ones default to False. The
      only constructor (`adapter`) sets all four, so today nothing is exposed, but a future
      constructor that forgets them would fail open. N4 jobs do not verify after creation that the
      returned job is paused; a future Hermes writer that accepts `paused` and ignores it would
      create an active job. A wrapper with explicit parameters and no `paused` raises before
      anything is created.
- [ ] Independent security review of the diff before any deploy (SECURITY_REVIEW_REQUIRED).
- [ ] Deploy to the owner's host and exercise the features there (separate authorization step).
- [ ] F1 runtime failure ledger and phone-version reporting; F2 phone copy; F3 approvals conversion;
      F4 report-only release watch; F5 finer read splits; F6 retire the `gh` submission path.

- [ ] N7: harden report helpers against intentionally hostile in-process string/tuple subclasses. Current production callers use parser-produced ordinary values; no CLI exposure was found.
