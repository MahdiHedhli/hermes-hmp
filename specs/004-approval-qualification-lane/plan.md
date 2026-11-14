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
3. In `cli.py`, `_cmd_compat` prints `Approval qualification (on-disk source):`. It calls the gate only when read
   compatibility passed; otherwise it prints `unqualified` without any call.
4. Ship the new JSON in the wheel (`pyproject.toml`, wheel content test).
5. Unit tests in `test_compat.py` and `test_cli.py`; update `FEATURES.md` and `ROADMAP.md`.

6. Wiring (same draft branch): `ServerContext.approval_qualified` (default closed) and
   `approval_qualification_open()`; `adapter.open_components` binds
   `supported AND approval_build_qualified(identity)`; `server.py` gates AP-3/4/6 and the
   snapshot; `DirectSendDeps` and `AdapterHooks` take the callback. The send decision is made
   before the profile lock; `consume_sse` phase transitions do not depend on `bind`.

7. L2/L5 repair (supersedes the wiring in 6 and "no cache"; pending controller/review
   verification): `compat.approval_listener_qualifier(read_identity)` returns the callback.
   `open_components` calls it once, blocking, only for a supported build, so the startup baseline
   (root, ordered files, fingerprint, SHA) is independent of any request. The callback re-reads
   the manifest and the source every call and opens only while all equal the baseline and an
   exact entry matches. A bounded (<= 8), lock-guarded, success-only probe cache keyed by
   (root, files, fingerprint, SHA) avoids re-running the import probe; failures retry and there is
   no TTL. `approval_build_qualified` stays as the informational CLI check.

8. Process latch (supersedes the per-call baseline in 7): the baseline is one per-process latch
   fixed by the first supported factory call; listener reconnect never rebinds it and a first
   bad manifest closes the process until a full gateway process restart. Startup cross-checks the
   read fingerprint and SHA and requires an exact manifest match. Source on disk is not memory
   attestation; unload/reimport is not defended; the restart qualification gate stays open. The
   1339 result is historical; the latest independent run is 1348 passed, 12 skipped, 1 existing
   warning, with pinned Ruff passing first. No behavior qualification or release is claimed.

Not touched: `gate.py`, route registration, the send manifest, app code, live Hermes home,
GitHub. The only cache is the successful-probe cache in item 7.

## Risks

- The list ships empty, so a later change that adds a build is the only thing that can qualify one.
  It needs behavioral evidence, not only a fingerprint and import probe.
- The candidate's approval behavior is unreviewed. This lane only gates; it implements none of it.
