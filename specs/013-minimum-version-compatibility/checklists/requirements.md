# Requirements checklist

## Policy
- [x] No gate reads a commit SHA, fingerprint, file list, source hash or process identity.
- [x] An unknown, placeholder, unlisted, newer or unreleased version is attempted.
- [x] A version below its floor is refused, and read below its floor imports no Hermes module.
- [x] Tested-sample manifests and tool-native fixtures are unchanged; they are evidence only.
- [x] No `requires_hermes` in `plugin.yaml`.
- [x] No media and no approvals member in the eligibility feature set.

## Security (unchanged checks)
- [x] Owner-device check and limiter order, per-bot authorization, host flags: untouched.
- [x] Loopback-only endpoint, profile's own scoped key, no cross-profile fallback: untouched.
- [x] DS-3 idempotency, lease, lineage and payload hash: untouched.
- [x] Jobs create paused, prompt scan, edit refusals and bounds: untouched.
- [x] Model projection allowlist and `authenticated` filter: untouched.
- [x] A `**kwargs` catch-all never satisfies a required parameter name.
- [x] A symbol or wrapper layer outside the Hermes tree and stdlib counts as missing.
- [x] Independent Opus review and bounded repair review accepted the finished source; installation evidence is separate.

## Reporting and privacy
- [x] `--issue-draft` is pure and offline; no network, `gh`, browser or subprocess.
- [x] Only allowlisted fields appear, each re-validated; no data in the URL.
- [x] `--feature` and `--failure-code` are required together, fixed-enum, feature-matched, never echoed.
- [x] The operator report is labelled reported, not observed, with no causal claim.
- [x] Permission, routing and authorization codes are explained, never drafted.
- [x] Warning text follows a real failure only; none on success or an unlisted version.
- [ ] F1 automatic runtime ledger and phone-version reporting: tracked, not implemented.

## Wire
- [x] No new code, field or route; `/ready` body unchanged; no contract revision bump.
