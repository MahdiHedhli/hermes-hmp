# HMP v1 conformance

This public checklist accompanies the [HMP v1 contract](HMP_V1.md). It describes the required gates for an HMP release; detailed physical-device evidence stays outside this repository.

| Area | Required verification |
| --- | --- |
| Pairing | Expired, replayed, mismatched, and malformed offers fail closed. Both screens confirm the same short authentication string. |
| Instance identity | TLS is pinned to the paired instance key; a changed key requires a new pairing decision. |
| Authorization | Device and profile access are checked on every route; denial and revocation take effect without cached privilege. |
| Tokens | Refresh rotation is atomic, retry grace is bounded, and replay cannot create a second successor. |
| Reads | Roster, snapshot, and history stay within the authorized profile and current instance. |
| Sends | Only qualified Hermes builds pass the guarded send gate. Stale anchors, duplicate client message IDs, and unknown outcomes fail closed or reconcile safely. |
| Logs | No offer secret, token, signature, message text, device label, or private network endpoint appears in logs. |
| Compatibility | The `bridge_files` fingerprint and behavioral fixture suite qualify each supported Hermes build. |

Run the unit suite, plugin surface check, vector regeneration check, privacy scan, log scan, and fixture compatibility matrix before release. The root [README](../../../README.md) and [CONTRIBUTING](../../../CONTRIBUTING.md) list the commands.

The initial public migration changes packaging only. It does not certify a new Hermes build or the proposed approvals feature.
