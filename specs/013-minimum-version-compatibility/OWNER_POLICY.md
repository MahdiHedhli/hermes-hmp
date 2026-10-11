# Owner compatibility policy — 2026-10-01

The owner explicitly replaces runtime availability decisions based on exact Hermes
commit/file-fingerprint qualification with a minimum supported version policy.

Implemented features must be attempted on later releases and development builds.
An unknown or unlisted version is not evidence of incompatibility. Historical
qualification receipts remain evidence for the tested samples; they do not gate
other versions. Do not require an exact-build test pass before permitting a feature.

Warnings about unvalidated/unsupported versions follow a real feature failure.
Offer a user-reviewed GitHub issue draft with bounded version and fixed error
metadata. Never submit automatically or include credentials, chat content, device
identifiers, host addresses, profile names or raw logs.

Permissions, explicit host feature settings, instance identity, profile routing,
scoped credentials, required runtime primitives, payload bounds and idempotency
remain enforced. A genuinely absent implementation cannot be advertised as usable.
No automatic grants, job execution or host topology changes are authorized by this
policy. Feature-specific API failures should not disable unrelated features.

Deployment uses the existing plugin scan and build checks with an idle gateway
restart. Preserve saved grants and report actual installed versions separately.

This instruction takes precedence over earlier exact-build gate wording in the
constitution, contracts, tests and skill. The implementation must amend those
requirements explicitly instead of preserving the old gate under another name.
