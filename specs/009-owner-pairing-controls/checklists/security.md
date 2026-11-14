# Security checklist

- [x] Pairing alone leaves privileged controls denied for a new device.
- [x] A stale yes/no answer cannot grant privilege.
- [x] An explicit host denial overrides the old config allowlist.
- [x] A grant applies to one active device, not a shared user or every bot's devices.
- [x] The jobs and model routes still require bearer authentication and per-bot authorization.
- [x] Revoked or unknown devices cannot gain controls through the CLI.
- [x] No device ID, secret, or host configuration is added to the public repository.
- [ ] Independent security review passes on the exact release candidate.
