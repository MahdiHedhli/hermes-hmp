# Plan

1. **Version evidence.** New pure module `hermes_version.py`: reads `install-stamp.json` `baseVersion`
   (UTF-8, optional BOM, bounded), then `__version__` or `__release_date__` literals with `ast.parse`,
   from files only, in that fixed precedence (a valid stamp is authoritative, as in Hermes itself). The `0.0.0` placeholder and non-plain versions are absent, giving `UNKNOWN`. Per-feature
   floors are rows of a verified release table (`KNOWN_RELEASES`).
2. **Eligibility.** `compat.evaluate_eligibility` locates the root without importing, reads the
   version, refuses features below their floor (no import when read is below), probes the core read
   dependencies, then probes session browsing, send, jobs and model independently. Evidence labels are
   filled in last and never read by a gate. `CompatGate` becomes a thin wrapper returning the existing
   `CompatResult`, now with an `eligibility` field.
3. **Probe.** Replace the file allowlist with Hermes-tree plus standard-library containment (no
   `site-packages`, `dist-packages` or Hermes-home `plugins`), still walking every wrapper layer. Add
   named-parameter (`paused`) and minimum-positional checks. Split the read table so session browsing
   has its own rows; add jobs and model tables.
4. **Call sites.** `adapter.open_components` computes eligibility once. `ServerContext` fields become
   `cron_available`, `model_available`, `send_available` and `session_browsing_available`; the owner's
   send flag stays separate from send availability. `server.py` keys the SES routes off browsing
   availability. The health snapshot reports `unsupported` when a flag is on but the feature is
   unavailable.
5. **CLI.** Rewrite the `compat` wording, add the offline `--issue-draft` (new module
   `issue_draft.py`) with `--feature`/`--failure-code`, and rewrite the `setup check` hint.
6. **Policy text.** Amend constitution I and V, CONTRIBUTING, HMP_V1 (GU-2a, GU-2c, new GU-2d, ERR-2a,
   error table, §12, cron, model), the conformance summary, INSTALL, FEATURES, README, ROADMAP, the
   release watch doc and DEPLOYMENT. The out-of-tree Hermes developer skill is amended by the owner.
7. **Verify.** New parser, eligibility, probe, CLI and privacy tests; adapt the exact-gate tests to
   evidence or availability tests; keep every security regression unchanged; run the CONTRIBUTING
   suite, Ruff, the plugin-surface check and the privacy and log scans.

## Deviation from the architecture report

`cron.scheduler.create_job_with_scheduler_registration` takes `**kwargs` on current Hermes and
forwards them to `cron.jobs.create_job`. The named-parameter check for `paused` (and `name`,
`schedule`, `prompt`, `deliver`, `repeat`, `context_from`) is therefore made on `cron.jobs.create_job`,
the writer that defines them, while the wrapper is only required to exist and be callable. A writer
that has `**kwargs` but not a named `paused` still fails the probe.
