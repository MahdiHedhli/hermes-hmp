# HMP constitution

## I. Hermes owns agent behavior

HMP is a gateway platform adapter. It may not bypass Hermes authorization, session ownership, or approval decisions. Builds below HMP's minimum supported Hermes version are refused. Newer or unknown versions are attempted, and a feature closes only when its own required Hermes API or a security check fails.

Spec 028 D4 permits one additional bounded transport-custody category, governed by
`docs/architecture/contracts/HMP_PHONE_ATTACHMENTS_V1.md`: issuing-device/exact-Phone-target upload
blobs; finite target/reference metadata; combined idempotency hashes/claims without message text;
and finite non-evicting generated-export/CMID redaction metadata joined to fresh canonical Hermes
rows. This is not history, approval, run, queue, retry or execution authority. Custody bytes expire;
revocation ends reads but cannot retract delivered native data. No caller path or identifier grants
access. Exact interface/source review and separate storage/validator/native/release gates precede
implementation or operational exposure. This normative exception grants no new hook/tool/network
destination, native patch, scanner waiver or second owner.

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

## VII. Closed outbound surface

HMP registers one platform adapter and one operator CLI, and adds no hook, tool, prompt section or dependency beyond those its contract names. Its calls into Hermes's own services stay on loopback literals, as HMP v1 §7a, §7c and §7d specify. One further exception is **proposed** by spec 014 and takes effect only after it is implemented, independently reviewed and accepted: a single outbound HTTPS client module, `push_relay.py`, whose destination comes only from explicit host configuration. A destination never comes from the wire, a phone, a sealed value, a redirect or a built-in default. The client is bound by the frozen relay policies in [`HMP_PUSH_RELAY_V1.md`](../../docs/architecture/contracts/HMP_PUSH_RELAY_V1.md) and HMP v1 §7f.

This is a narrow, source-only exception. It grants no authority to any other socket, client, destination, dependency, hook, tool or registration. It makes no statement about current runtime behavior or scanner coverage, and no scanner rule changes with this text.
