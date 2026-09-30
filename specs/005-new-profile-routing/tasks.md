# Tasks: routing for a bot created after installation

Status: the bounded correction is root-reviewed; disposable-host qualification is open. The earlier two-file implementation and its
review (below, historical) are superseded by the root-only candidate; nothing here is certified.

Root-only correction (current, reviewed):

- [x] C1 Product bug: the earlier helper also set `gateway.multiplex_profiles: true` in the named
      profile. On `ca705dbf7ef86425b381b542712aff310f1ee52c` a multiplexing root serves profiles
      without that flag, and the flag changes the profile's history namespace. Route helper is now
      root route only; the profile config is inspected (path, owner, mode, size, strict YAML) and
      drift-checked, never written, backed up, interpreted or refused for its flag or history.
- [x] C2 Removed the profile write, the two-file ordering, the conditional profile restore, the
      profile backup, `profile_multiplex_added`, and every CLI/doc claim about it. One root atomic
      write keeps the original mode, one private rolling backup, both files rechecked before the
      rename. Failure or interrupt from the write onward reports the root's state from its bytes
      (on disk / not changed by this command / unconfirmed); nothing is restored.
- [x] C3 Output and docs: the route is on disk only, not activated by this command; reload
      needs a restart on the inspected build; sending has separate prerequisites; approval stays manual. Version boundary stated: `ca705` is the
      authority; older fixtures' namespaces are not a universal claim.
- [x] C4 Tests: profile bytes/mtime/inode untouched for absent/false/true/string/top-level/empty
      flags; existing sessions allowed and untouched; no profile backup; only the root (and its
      backup) is ever written; the root conflict, refusal, no-op, symlink, mode, YAML, oversize,
      drift, interrupt and privacy cases are retained; write failure before and after the rename
      and an external edit are covered. Regression check: the new tests fail against the prior
      code (29 failures) and pass with the fix.
- [ ] C6 Remaining disposable-host gateway-loop and authorization qualification on `ca705`.
      Root independently reproduced the real-store fixture: 7 passed, zero skips; history the
      root creates for an exact routed source reads with the profile's own flag absent or false.
      Earlier standalone-profile history stays intact and resolves by session id, but is absent
      from the canonical read and Phone list. Route-only preparation is not a legacy-history
      migration or a live sending guarantee. Root-reviewed evidence: `C6-EVIDENCE.md`.
- [x] C5 Root code and documentation review of this candidate. Root CI: 1322 passed, 10 existing
      skips, one existing warning; final route tests: 138 passed; pinned Ruff, plugin surface,
      privacy and diff checks clean. Opus cleared the bounded code review and the documentation
      findings were repaired and root-reviewed. Remaining host steps: PyYAML acceptance by the Hermes
      plugin manager; gateway restart and new-profile access check on a disposable host.

Earlier history (superseded, kept for the record). The implementation steps T1-T7 were built for the
two-file design; T2, T3, T6 and T7 are replaced by C1-C4, and the review findings below were
against that design.

- [x] T1 Write spec, plan, tasks.
- [x] T2 (superseded by C2) `routes.py`: safe reads, strict YAML, planner, backups, ordered atomic
      writes, rollback report.
- [x] T3 (superseded by C2, C3) CLI: parser, mutating guard, dispatch, custody, output text.
- [x] T4 Surface check: `yaml` restricted to `routes.py`, lazy; test.
- [x] T5 PyYAML runtime dependency in `pyproject.toml`, both `plugin.yaml`, `uv.lock`.
- [x] T6 (superseded by C4) Tests in isolated tmp homes.
- [x] T7 (superseded by C3) Docs: `docs/INSTALL.md`, `server/DEPLOYMENT.md`, README section.

Findings from the earlier independent review (historical). Those that concern profile writes,
rollback of a profile, or per-profile flag/namespace handling (S1, S2, S4, F1, L2 in part) applied to
a design that no longer exists; the root-related ones still hold in the current code:

- B1 Root `gateway.multiplex_profiles` is never turned on; the command refuses unless it is `true`.
- B2 `enabled: null` and null-valued extra keys are conflicts, not the exact route.
- S3 Serving is never promised; an eligible profile is served only after the root gateway detects it.
- L1 Pre-write failures are clean, status-only refusals.
- F2 Emission sits inside the pre-write catch.
- S1/F1/S2/S4/L2 were written for two files and a profile restore; superseded by C2.
