# Tasks: routing for a bot created after installation

Initial implementation (before independent review):

- [x] T1 Write spec, plan, tasks.
- [x] T2 `routes.py`: safe reads, strict YAML, planner, backups, ordered atomic writes, rollback report.
- [x] T3 CLI: parser, mutating guard, dispatch, custody, output text.
- [x] T4 Surface check: `yaml` restricted to `routes.py`, lazy; test.
- [x] T5 PyYAML runtime dependency in `pyproject.toml`, both `plugin.yaml`, `uv.lock`.
- [x] T6 Tests in isolated tmp homes: new bot after initial routing; idempotence; existing
      profiles, routes and config untouched; bad profile, symlink, mode, size, YAML; route and
      multiplex conflicts; changed under us; write failure and rollback report; TTY, session and
      named-profile refusal; no subprocess, store, or approval side effect.
- [x] T7 Docs: `docs/INSTALL.md`, `server/DEPLOYMENT.md` (new profile lifecycle: routing vs
      serving vs authorization), README section.

Independent review findings (a separate Opus review, adopted by root) and their repair. These
were found by the reviewer, not by the initial implementation or its tests:

- [x] B1 Command could turn on root `gateway.multiplex_profiles`, widening the whole gateway.
      Fixed: it now requires the root value to be boolean `true` and otherwise refuses with a
      pointer to the initial setup; `root_multiplex_added` and its output/claims are removed. The
      supported per-profile flag is unchanged. No flag was added to widen serving.
- [x] B2 `enabled: null` and null-valued extra keys were treated as the exact route. Fixed:
      exact means no extra key at all and `enabled` absent or `true`. Negative tests added
      (`enabled-null`, `user-id-null`, `chat-id-null`, `extra-key-null`).
- [x] S1 Only changing files were rechecked. Fixed: both snapshots are compared before backups and
      again before the first config write. The small final check/rename same-user race is kept
      and documented, not claimed eliminated.
- [x] S2 Interrupts after the profile write were unreported. Fixed: any exception, `KeyboardInterrupt`
      or `SystemExit` after that write triggers a conditional restore and a final-state report
      (exit 130 for interrupts). "Root unchanged" now reads "not changed by this command".
      Tests: interrupt before root replace, after profile replace, after root replace, and during
      rollback.
- [x] S3 "Served as soon as it exists" corrected everywhere (module, DEPLOYMENT, spec): eligible
      profiles are served only after the root multiplex gateway detects them; the command serves
      and reloads nothing.
- [x] S4 Docs warn that a per-profile flag can change a used profile's session namespace; review
      sessions and back up first; no transcript migration. Also in CLI output.
- [x] L1 Pre-write OSError/RecursionError/ImportError (read, stat, deepcopy, missing PyYAML,
      backup-target stat) are clean, status-only refusals. Post-write paths never claim "no
      changes". Tests use a secret marker to prove no detail leaks.
- [x] L2 Accepted limitation: one rolling private backup; docs say a second run replaces it and
      the first run's comments survive only in an operator copy.

Final review findings (Opus, no security blockers) and repair:

- [x] F1 Root-only interrupt (profile already multiplexed) after the root replace came out raw
      with no final-state report. Now any interrupt once the root write has started enters
      final-state reporting; `_failure` takes `profile_changed` and says the profile "was not
      changed by this command" (no "Both files carry the change") when only the root changed.
      Tests: interrupt after root replace (keyed on file content, not the backup phase) and
      before root replace; both through the CLI, exit 130, truthful partial flags, no restart or
      approval.
- [x] F2 Emission (`_verified_emit`) moved inside the pre-write catch, so OSError/RecursionError/
      ImportError there is a status-only refusal. Test injects RecursionError into `_emit`.
      Nothing after the first write is caught this way.
- [x] S3 follow-up: README, INSTALL and DEPLOYMENT new-bot sections all say a multiplexing gateway
      picks up an eligible profile on its own detection; no unconditional serving promise
      (INSTALL still opened with "Creating a Hermes profile serves it"; corrected).
- [ ] Owner steps, still open: full suite and scanner on the final diff, PyYAML acceptance by the
      Hermes plugin manager, and gateway-restart routing check on a disposable host.

Checks:

- [x] T9 Focused tests, ruff on changed files, plugin-surface check re-run after the repair (see
      the final report; the initial evidence of 1298 passed / 10 skipped predates the repair and
      does not qualify the revised diff).
- [ ] T8 Root review of the revised diff. Live verification on a real host is the owner's step,
      not part of this change.
