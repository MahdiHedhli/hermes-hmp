# Plan: approval qualification lane

1. Add `server/hmp_plugin/approval_supported_builds.json`: `format` 1, empty `builds`, and
   `bridge_files` equal to the current `direct_send_supported_builds.json` list plus the approval
   source files (approval, wait, clarify and interrupt tools; busy, inbound and turn-runner gateway
   modules; API-server run modules; profile and auth helpers; `agent/secret_scope.py`) taken from the
   `origin/test/approvals-main-candidate` direct-send list. It is sorted, relative-path only, and a
   strict superset of the guarded-send list.
2. In `compat.py` add `APPROVAL_COMPAT_FILE`, `APPROVAL_DEPENDENCIES`,
   `probe_approval_dependencies` and `approval_build_qualified`. Reuse the existing loader,
   fingerprint reader, `match_build` and `probe_read_dependencies`; add no new import path. Check
   order: identity type, list load, non-empty builds, Hermes root, recomputed fingerprint and SHA,
   exact match, then the probe. Every failure, including any exception, returns `False`.
3. In `cli.py`, `_cmd_compat` prints `Approval qualification:`. It calls the gate only when read
   compatibility passed; otherwise it prints `unqualified` without any call.
4. Ship the new JSON in the wheel (`pyproject.toml`, wheel content test).
5. Unit tests in `test_compat.py` and `test_cli.py`; update `FEATURES.md` and `ROADMAP.md`.

Not touched: `adapter.py`, `gate.py`, route registration, the send manifest, app code, live Hermes
home, GitHub.

## Risks

- The list ships empty, so a later change that adds a build is the only thing that can qualify one.
  It needs behavioral evidence, not only a fingerprint and import probe.
- The candidate's approval behavior is unreviewed. This lane only gates; it implements none of it.
