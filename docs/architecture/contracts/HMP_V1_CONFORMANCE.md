# HMP v1 conformance

This public checklist accompanies the [HMP v1 contract](HMP_V1.md). It describes the required gates for an HMP release; detailed physical-device evidence stays outside this repository.

| Area | Required verification |
| --- | --- |
| Pairing | Expired, replayed, mismatched, and malformed offers fail closed. Both screens confirm the same short authentication string. |
| Instance identity | TLS is pinned to the paired instance key; a changed key requires a new pairing decision. |
| Authorization | Device and profile access are checked on every route; denial and revocation take effect without cached privilege. |
| Tokens | Refresh rotation is atomic, retry grace is bounded, and replay cannot create a second successor. |
| Reads | Roster, snapshot, and history stay within the authorized profile and current instance. |
| Sends | Only a Hermes that provides the send dependencies (GU-2d) passes the guarded send gate. Stale anchors, duplicate client message IDs, and unknown outcomes fail closed or reconcile safely. |
| Logs | No offer secret, token, signature, message text, device label, or private network endpoint appears in logs. |
| Compatibility | A minimum supported Hermes version and per-feature dependency probes decide availability (GU-2c, GU-2d). The `bridge_files` fingerprint and fixture suite record tested samples as evidence only. |

Run the unit suite, plugin surface check, vector regeneration check, privacy scan, log scan, and fixture compatibility matrix before release. The root [README](../../../README.md) and [CONTRIBUTING](../../../CONTRIBUTING.md) list the commands.

The initial public migration changes packaging only. It does not certify a new Hermes build or the proposed approvals feature.

## Host-local generated images (draft §7e, v1.6): not implemented

[§7e](HMP_V1.md) is a draft contract. **No row below is implemented, qualified or passing.** The product manifest of supported builds is empty. Each future test must fail when its named guard is removed. Test IDs refer to [`specs/011-local-image-serving/plan.md`](../../../specs/011-local-image-serving/plan.md).

| Clause | Future verification | Status |
| --- | --- | --- |
| LM-1, LM-3, LM-8 | T1: gate closed (flag, build, non-owner) reproduces the golden RO-3, RO-6, SES-2 and SES-2a bytes; the candidate never reaches wire serialization | Unimplemented |
| LM-9, LM-10 | T2: a ref used by another device, user, profile, or after expiry or eviction gives one 404 shape | Unimplemented |
| LM-12 | T3: revoke between worker return and the loop check gives the existing 401, no bytes | Unimplemented |
| LM-6, LM-9 | T4, T5: compression, rewind, retire, replaced Phone conversation and non-canonical Bot Chat session refuse | Unimplemented |
| LM-7 | T6: assistant `MEDIA:` or Markdown never mints or reads | Unimplemented |
| LM-5 | T7: `image` outside the lexical `<home>/cache/images/` rule gives no descriptor and 404 if forced | Unimplemented |
| LM-9, LM-12 | T8: a file replaced after first 200 gives 404; concurrent first fetches serve at most one digest | Unimplemented |
| LM-11, LM-12 | T9: causal changes before the phase-two check give 404; initial grant refusals keep ERR-3; no native call on the loop; phase-two busy gives 429; one shared 20 s deadline; the post-last-check residual is documented and not tested as refused | Unimplemented |
| LM-10, LM-13 | T10: permit limits and permits held through cancellation | Unimplemented |
| LM-14 | T11, T13: slow reader, EOF stall, abort at 30 s, exact headers, query, body, HEAD and `Range` | Unimplemented |
| LM-18 | T12: four-fetch measurement against the provisional ceilings | Unimplemented |
| LM-17 | T14: phone parse, binary path, no disk cache, no public fallback, one refresh and one refetch | Unimplemented |
| LM-16 | T15: logs carry closed enums only | Unimplemented |
| LM-15 | T16: one test per error-table row | Unimplemented |
| LM-11, LM-13 | T17: copied `ContextVar` profile scope in both phases | Unimplemented |
| LM-1, LM-2 | T18: startup baseline mismatch, later disk mismatch, restoration, empty manifest | Unimplemented |
| LM-19 | E1 lexical-producer-string fixture and Linux errno qualification | Not run |
