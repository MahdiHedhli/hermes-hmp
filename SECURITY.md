# Security policy

Please report a vulnerability privately through [GitHub private vulnerability reporting](https://github.com/MahdiHedhli/hermes-hmp/security/advisories/new). Do not include credentials, pairing payloads, device identifiers, or private network addresses in a public issue.

HMP treats the phone as a separately authorized device, not as a trusted extension of the host. It uses an instance-pinned TLS connection, per-device keys, explicit pairing confirmation, scoped profile access, and fail-closed compatibility checks. The [HMP v1 contract](docs/architecture/contracts/HMP_V1.md) defines the wire protocol and trust boundaries. The [host hardening guide](server/HOST_HARDENING.md) covers adjacent Hermes services.

Security-sensitive changes require tests for authorization, replay handling, expiry, logs, and resource bounds. The proposed mobile approvals work is under review and is not part of this initial migration.
