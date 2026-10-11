# HMP constitution

## I. Hermes owns agent behavior

HMP is a gateway platform adapter. It may not bypass Hermes authorization, session ownership, or approval decisions. Builds below HMP's minimum supported Hermes version are refused. Newer or unknown versions are attempted, and a feature closes only when its own required Hermes API or a security check fails.

## II. Device trust is explicit

Each device is paired to one instance, uses its own key, and receives only explicitly approved profile access. Pairing and authorization require host-side confirmation. Replay, expiry, and revocation are contract requirements.

## III. Public by default

All files and Git history here are public. No real names beyond public project attribution, private addresses, live IDs, secrets, screenshots, or owner session evidence belong in this repository. CI scans every tracked file without a suppression baseline.

## IV. Contract before code

For each behavior change, write or update a Spec Kit feature specification, design plan, and testable tasks in `specs/<number>-<feature>/`. Update the HMP wire contract when observable protocol behavior changes. Keep migration-only packaging changes separate from behavior changes.

## V. Verify on Hermes

Unit tests, lint, the closed plugin surface check, log and privacy scans, and fixture compatibility checks gate release. Record exact Hermes build fingerprints as test evidence; they never admit or refuse a build. Test installs use an isolated Hermes home.

## VI. Review security findings

Unresolved authorization, expiry, resource bound, or log-leak findings block a release. Document open findings in the relevant PR and request review before calling a feature ready.
