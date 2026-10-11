# Host decision for device controls

Status: draft implementation. This changes a privilege boundary and requires independent security review before release.

## Operator outcome

After pairing a phone, the host decides separately whether that device may manage scheduled jobs and bot default models. Bot Chat access does not imply this privilege. An unambiguous `GRANT` answer enables it for that device; every other answer leaves it off. The host can change the decision later for an active device.

## Acceptance scenarios

1. Two phones share one HMP user. Granting one does not grant the other.
2. The host pairs a phone and gives an old `y` answer intended for Bot Chat access. Jobs and model controls stay off; only the literal `GRANT` turns them on.
3. A host denial overrides a legacy `extra.owner_device_ids` entry. A later explicit grant works without that entry.
4. A revoked or unknown device cannot receive a control grant. Its bearer cannot use a privileged route.
5. After a `GRANT` at pairing or `devices grant-controls`, the host output says only that the permission is saved for this phone. It states that the permission does not activate the previews and that jobs and models each need the host feature flag, a supported build, the profile API and key, and bot authorization. It points to `hermes hmp health check` and `docs/INSTALL.md`. A denial, or a revoked or unknown device, never prints the saved-permission message.
6. A gateway restart preserves the decision. An existing device with no decision retains the legacy config behavior until the host records one.

## Security constraints

- Require an active device bearer and the existing per-bot authorization on every route request.
- Store only the device ID, boolean decision, and decision time. No credential or message content enters the decision table or logs.
- The host commands use the existing interactive-terminal and Hermes-session refusal guards. They do not claim to stop arbitrary code running as the same OS user.
- The grant output is informational. It never claims a preview is ready, and the commands do not read credentials, probe endpoints, or change host configuration.
- A failed decision read denies access. A newly paired device has no implicit owner role.
