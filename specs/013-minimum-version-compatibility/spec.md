# Minimum Hermes version compatibility

Status: implementation draft, awaiting independent security review. The owner's policy in
[`OWNER_POLICY.md`](OWNER_POLICY.md) takes precedence over the earlier exact-build wording in the
constitution, the HMP v1 contract, the tests and the Hermes developer skill.

## User outcome

An operator on a later Hermes release or a development build gets every implemented HMP feature the
host actually supports, without waiting for HMP to list that exact build. A build below HMP's minimum
version is refused with a clear statement. A feature that really fails is reported with a warning and
a user-reviewed GitHub issue draft that carries only bounded version and fixed-code metadata.

## Policy

1. HMP declares a minimum supported Hermes version per feature (read and session browsing 0.21.4 /
   2026.9.21; send, jobs and model 0.21.5 / 2026.9.24). A version that declares itself below a floor
   is refused for that feature, and read below its floor imports no Hermes module.
2. An unknown, placeholder (`0.0.0`), unlisted, newer or unreleased version is attempted. Only a real
   missing API, or a security check, closes a feature.
3. Exact commit SHAs, source fingerprints, file lists and the `*_supported_builds.json` manifests are
   test evidence. They label a build "tested" for display and tooling and never admit or refuse a
   build. No gate reads them.
4. These stay enforced exactly as before: bearer and owner-device checks, per-bot authorization,
   explicit host feature flags, instance identity and custody, profile routing, the profile's own
   scoped loopback key, payload bounds and DS-3 idempotency, create-paused for jobs, the model
   projection allowlist, and the inert trigger guard. No grant, job execution or host topology change
   is introduced.

## Acceptance scenarios

1. A Hermes at or above a feature's floor with that feature's APIs present serves it, whether or not
   its commit or fingerprint appears in any manifest.
2. A Hermes whose version cannot be read (including the `0.0.0` placeholder) is attempted.
3. A Hermes declaring a version below the read floor gets `503 other {why:"hermes_build_unsupported"}`
   on every route except `/ready`, and HMP imports no Hermes internal.
4. A missing core read dependency gives `503 other {why:"hermes_read_dependency_missing"}`, refuses
   `pair offer`, and marks every other feature `requires_read`. A missing dependency of send, jobs,
   model or session browsing closes only that feature (`write_gate_closed`, `cron_unavailable`,
   `model_unavailable`, or a 404 on the session routes).
5. A cron writer that has `**kwargs` but no named `paused` parameter makes jobs unavailable.
6. A Hermes symbol resolving, with any wrapper layer, outside the Hermes tree and standard library
   (`site-packages`, `dist-packages`, the Hermes home's `plugins` directory) is treated as missing.
   A symbol that moved to another file inside the tree still counts.
7. `hermes hmp compat` prints the version, its source, the minimum versions and each feature's
   availability. On success it contains none of "unvalidated", "unsupported", "qualified" or "tested".
   After a real failure at or above the floor it prints "The <feature> compatibility check failed on
   Hermes <version> (<fixed reason>: <HMP dependency labels>)", adds "This Hermes is not one of HMP's
   tested samples." only when no tested sample matches, and prints the hint
   `hermes hmp compat --issue-draft`. It never claims the version is bad, because a failed probe is a
   fact about the install's APIs. Below the floor it says to update Hermes and offers no draft.
8. `hermes hmp compat --issue-draft` is pure and offline. With no failure and no operator context it
   prints `No HMP feature failure detected; nothing to report.` Otherwise it prints a title, a
   Markdown body and the fixed `issues/new` URL with paste instructions. No data goes into the URL.
9. `--issue-draft --feature <read|session_browsing|send|jobs|model> --failure-code <code>` records a
   failure the operator saw, for an upstream failure the static probe cannot see. The pair must be
   given together, only fixed `ErrorCode` values that match the feature are accepted, wrong pairs and
   free text are refused without being echoed, and the draft is available even when every probe
   passes. The draft labels the failure "Reported by the operator, not automatically observed", and a
   probe failure "Observed by HMP's static dependency check"; neither establishes a cause. Permission and routing codes (for example `forbidden`, `unauthorized`,
   `not_found` for jobs/model/send) are explained as their own reason and never drafted.
10. The draft contains only: Hermes version and its source, commit SHA or `none`, HMP version, OS
    family and Python `major.minor`, and for each failed feature the feature, reason and HMP's own
    dependency labels, plus the operator-reported feature and code when given. Profiles, device,
    user and chat IDs, paths, hostnames, addresses, keys, config, content, prompts, logs, exception
    text, fingerprints and manifest labels never appear.

## Constraints

- No new wire code, field or route, no contract revision bump, no new plugin registration surface.
  The old phone app keeps working unchanged.
- Availability is computed once when the listener opens. No per-request fingerprint hashing remains.
- The eligibility feature set is closed: no media and no approvals member. Reaching a floor never
  implies either.
- The issue draft never contacts the network, `gh`, a browser or a subprocess.
- The tested-sample manifests and the tool-native fixtures are unchanged byte for byte.

## Not in this change (tracked, not done)

- **F1** Runtime failure ledger: record the last upstream failure per feature and surface it in
  `health check` and `--issue-draft` automatically.
- **F2** Phone-version reporting and phone copy updates (text only).
- **F3** Convert the approvals branch to a probe, a floor and evidence only before it merges.
- **F4** Make the CI release watch report-only.
- **F5** Finer read splits. **F6** Retire the `feat/compat-report` `gh` submission path.
