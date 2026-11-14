# Media readiness protocol 1 — source candidate, not released

This additive protocol does not change AR1's jobs/model response. It is implemented
on `feat/media-read-entitlement-20261108`; runtime and mobile qualification remain
open. It does not provide remote grants or automatically enable host features.

## Discovery

Authenticated `GET /media-readiness/capabilities` has no query or body:

```json
{"protocol":1,"media_readiness":true,"remote_permission_write":false}
```

This advertises the diagnostic protocol only, not permission, operational readiness,
image availability, or native-version qualification. An older host's 404 means this
extension is unavailable; retain existing image behavior and explain the diagnostic
gap. Do not infer denied rights, enable settings, or retry against another instance.
The normal host compatibility gate still applies. There is no new unauthenticated
or compatibility-exempt diagnostic surface.

## Scoped snapshot

Authenticated `GET /bots/{canonical_profile}/media-readiness`, without query/body,
requires current bot authorization before any diagnostic disclosure. Success is
`Cache-Control: no-store` and JSON:

```json
{"protocol":1,"checked_at":0,"generation":"00000000000000000000000000000000","media":{"entitlement":"missing","host_setting":"disabled","runtime_api":"unavailable","operational":false,"reasons":["host_flag_disabled","media_api_unavailable","media_read_missing"],"action":"contact_host_operator","image_availability":"not_probed"}}
```

`checked_at` uses the existing AR1 clock and safe-integer constraints; `generation`
is the current listener generation. The closed axes are:

- entitlement: `granted`, `missing`, `unknown`;
- host_setting: `enabled`, `disabled`, `unknown`;
- runtime_api: `available`, `unavailable`, `unknown`.

`operational` is true only for granted/enabled/available. Reasons are sorted and
restricted to `media_read_missing`, `media_read_unknown`, `host_flag_disabled`,
`host_flag_unknown`, `media_api_unavailable`, `media_api_unknown`. Action is `none`
when operational, otherwise `contact_host_operator`. No Request access/Fix mutation
is advertised. Image availability is always `not_probed`. No path, filename, media
reference, model/provider value, job content, or another device's rights is returned.

Missing opt-in is disabled; malformed host flags stay unknown. Authority failures
refuse the response rather than masquerading as missing rights. Absent/unauthorized
bots remain masked with 404; uncertain readiness returns the existing fixed 503
`readiness_unavailable`. Authentication, instance mismatch, rate limit, empty-GET,
size and deadline checks retain their existing errors and bounds.

## Client lifecycle

Bind requests and state to the selected instance, device/session, canonical profile
and request generation. Discard late results after selection changes, unpair,
revocation, logout or newer refresh. Display axes independently; an API problem is
not a missing-rights diagnosis. A snapshot never authorizes an operation. Operators
must inspect current authority before changing rights or host-wide settings.

## Remaining qualification

Final delivery uses synchronous authority/config checks after the worker await;
latency under contention needs qualification. Callback and post-worker revocation
checks are covered by focused tests, not a complete concurrency proof. Independent
review, broader route/contract tests, mobile decoder/UI, packaging and physical
Android/iOS acceptance remain required before deployment. Legacy owner fallback
has no persistent policy revision; its previously documented restore/revival limit
is not solved by this diagnostic protocol.
