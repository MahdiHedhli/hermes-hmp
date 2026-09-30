# Approval qualification lane (draft groundwork)

Status: draft. Approvals are not released, not enabled, and not wired to any route.

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
5. `hermes hmp compat` prints an `Approval qualification:` line, `unqualified` for every build while
   the list is empty. It is evaluated only after read compatibility passed.
6. `FEATURES.md` and `ROADMAP.md` describe this as draft groundwork only.

## Out of scope

Approval routes, prompt storage, answer delivery, adapter or gate changes, the send manifest,
qualifying any build, live Hermes configuration, and any release-watch feature. Public privacy rules
apply: no private paths, hosts, IDs or credentials in source or output.
