# Approval qualification lane (draft groundwork)

Status: draft. Approvals are not released and not enabled. The gate is wired to the prompt routes
and producers but closed for every build, because the shipped list is empty.

## User story

As an HMP maintainer, I want a separate, fail-closed qualification gate for a future approvals
feature, so that approvals can only ever be admitted on an exactly qualified Hermes build and can
never widen the read or guarded-send gates.

## Acceptance scenarios

1. `approval_supported_builds.json` ships with an empty `builds` list and a bounded `bridge_files`
   list: the current guarded-send list plus the approval-relevant Hermes source files.
2. `approval_build_qualified(read_identity, hermes_root, compat_path)` returns `False` for an empty,
   malformed or missing list, a missing listed source file, a changed fingerprint or Git SHA, no exact
   list match, or any dependency-probe failure or error.
3. With an empty list it returns before reading any Hermes file or importing any Hermes module.
4. `APPROVAL_DEPENDENCIES` is its own table. `DIRECT_SEND_DEPENDENCIES` and
   `direct_send_build_qualified` are unchanged, and each lane's result is independent of the other's.
5. `hermes hmp compat` prints an `Approval qualification (on-disk source):` line, `unqualified` for
   every build while the list is empty. It is evaluated only after read compatibility passed. It is
   informational: it checks the source currently on disk, not the running gateway.
6. `FEATURES.md` and `ROADMAP.md` describe this as draft groundwork only.
7. Route/producer wiring: AP-3, AP-4 and AP-6 and snapshot `open_requests` require the gate
   (exact `True`, off-loop, exceptions closed) after owner, rate-limit and bot authorization.
   The adapter binds a callback built ONCE at listener start (see 8) and passes it to the send
   deps and prompt hooks. While closed, ordinary DS-4 sends bind no stream, call no approval
   helper and keep identical result classification.
8. Listener-start identity (L2/L5 repair, pending controller/review verification).
   `compat.approval_listener_qualifier(read_identity)` is called once, synchronously, inside
   `open_components`, only when `result.supported` is true. It captures a startup baseline (exact
   resolved source root, ordered approval file list, approval fingerprint, git SHA), independent
   of any later request. An empty, malformed or missing list, an unidentifiable source, or a
   startup SHA that differs from the read identity yields a callback that stays closed until
   restart; with an empty list no approval file is inspected or imported (adding the first entry
   needs a restart). Each callback reloads the manifest, recomputes fingerprint and SHA, requires
   root, ordered list, fingerprint and SHA to equal the baseline and an exact current list entry,
   then probes. So an in-place swap to another also-qualified build, with or without git, closes
   until restart; manifest removal closes at once; restoring the same startup entry may reopen.
9. Probe cache. Only a SUCCESSFUL probe is cached, keyed by (root, ordered files, fingerprint, git
   SHA), at most 8 entries (oldest evicted), under a lock so simultaneous `to_thread` callers
   probe once. It is separate from the guarded-send cache. Failures are never cached, and there is
   no TTL: manifest, fingerprint and SHA are re-read on every callback, so revocation is visible
   on the next call.
10. `approval_build_qualified` and the `hermes hmp compat` line remain a one-shot,
    informational exact check of the source currently on disk. They have no startup baseline and
    are not production admission.
11. Process-level baseline (supersedes the per-call wording in 8). The startup baseline is one
    per-process latch fixed by the first supported factory call. A listener reconnect never
    rebinds or redefines it; a first empty, malformed, missing or unlisted manifest closes the
    process until a full gateway process restart (not a listener restart). At startup the read
    fingerprint and git SHA are cross-checked against the read gate's fresh identity, and the
    startup manifest must contain an exact matching entry.
12. Limits. Source on disk is not memory attestation: modules already imported are not re-verified.
    Unload/reimport of the plugin is not defended against. Runbook: restart the whole gateway
    process after any Hermes, source or plugin change. The restart qualification gate remains open,
    and approvals behavior qualification and release stay no-go. Earlier full-suite counts (1339)
    are historical; the latest independent run was 1348 passed, 12 skipped, 1 existing warning.
    Nothing here claims behavior qualification or release.

## Out of scope

Changing approval behavior itself, caching anything but a successful probe, the send manifest, qualifying any build, live Hermes configuration, and any
release-watch feature. Public privacy rules
apply: no private paths, hosts, IDs or credentials in source or output.
