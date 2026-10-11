# Feature: Permission readiness and explicit remediation

Status: contract v3 independently accepted on 2026-10-04; bounded HMP/Mobile
source implementation remains under independent review. It is not an
administrator grant or evidence that an installed phone or host currently works.

Source basis: HMP `b65f6aa00193d6d6e37ca3c7bcdc886e2bdcc55c`; compatibility reference
`4d6863ef8a311462adb68fc82dd3835657739f81`. The two revisions are separate Git
blob sources in the private input manifest; neither is a runtime allowlist.
This spec follows the owner-authorized AR1 task in the mobile roadmap.

## Summary

After pairing, an authenticated device can check its own readiness for scheduled
jobs and bot default-model management on one bot it is already authorized to
access. The result separates HMP/Hermes API capability, the device's effective
jobs-and-models control permission, live host feature settings, and whether the
profile-scoped API endpoint is configured. It never reads jobs, the current
model, a model list, provider data, or job contents to produce the check.

The diagnostic does not probe whether Hermes's loopback API is answering. It
must say that reachability was not tested; it must not display “ready” solely
because the static API probe, host flag, permission, and endpoint configuration
pass. An actual feature operation can still fail. This first slice gives a
fixed **Request access** guidance action or a fixed **Plan remediation** action;
it sends no access request and changes no grant, flag, configuration, job, or
model.

## User stories and acceptance scenarios

1. As a paired device with bot access but without jobs/model controls, I can
   see that my own controls permission is missing for that authorized bot, and
   open local Request access guidance. No request is transmitted or recorded.
2. As a device with controls, I can distinguish an unavailable feature API, a
   disabled host flag, missing profile API configuration, and an untested API
   connection. The phone never treats an untested connection as working.
3. As an operator, I receive a fixed, single-setting remediation plan. HMP
   neither applies the plan nor changes a global flag or restarts Hermes.
4. Given an unsupported, unknown, or newer Hermes version, HMP preserves the
   minimum-version policy: it refuses only declared below-floor or missing
   feature dependencies; unknown and newer versions attempt their feature APIs.
5. Given a wrong instance, revoked/expired device, unauthorized bot, stale
   device family, replaced listener generation, or changed bot authorization,
   the response contains no readiness details for that request.
6. Given an older HMP that lacks capability negotiation, the phone presents a
   conservative “readiness unavailable on this host” message. It does not
   infer missing permission or make another-version request.

## Requirements

### Negotiation and compatibility

- **AR1-R1.** Add authenticated `GET /hmp/v1/readiness/capabilities` and
  `GET /hmp/v1/bots/{p}/readiness`. The existing unauthenticated `/ready`
  response is unchanged and MUST NOT gain per-device or permission data.
- **AR1-R2.** The capabilities path is the sole additional compatibility-gate
  exemption. It still passes current-key, peer, request-size, instance, and
  bearer checks. The handler authenticates before returning even the fixed
  protocol version. The per-bot route stays behind the normal feature
  compatibility gate and repeats authentication in its handler.
- **AR1-R3.** Capability negotiation is bound to the active bearer and current
  HMP instance header. It returns `protocol: 1` and fixed per-feature
  compatibility states for only `jobs` and `model`; it includes no device,
  user, profile, instance, build fingerprint, dependency name, version, or
  setting value. The endpoint is safe on below-floor/core-incomplete builds
  because it authenticates against HMP's own store and reads only the
  already-computed eligibility result. No durable capability cache is kept.
  The current Mobile TokenManager has no public event for successful P5 token
  rotation, so this slice does not claim immediate UI invalidation on that
  unobserved event; readiness remains informational and is freshly negotiated
  before any local guidance action or jobs/model operation.
- **AR1-R4.** Unknown/newer Hermes versions are attempted. A declared
  below-floor version, missing dependency, failed API probe, missing Hermes
  root, and prerequisite read/send failure remain distinct fixed reasons from
  spec 013/034. Tested-build labels and source fingerprints never gate or
  appear in the response. HMP maps its existing `FeatureStatus` to the closed
  response enum; it never probes Hermes by importing extra helpers on request.
- **AR1-R5.** An old HMP's absent capability route means `legacy_unknown` only.
  The phone retains safe existing flows and tells the user to check host
  compatibility. It MUST NOT interpret absence, a generic 404, or a network
  failure as missing controls.

### Per-bot authorization, entitlement, and disclosure

- **AR1-R6.** The per-bot route uses this order: current TLS identity check;
  bounded parser/peer policy; bearer plus instance authentication; per-device
  rate limit; current `require_bot_authorized(user, p)`; current authorization
  and ACTIVE device/family revalidation; then readiness reads. Authentication
  is repeated after every blocking/async lookup and immediately before response
  construction. Definitive authority loss uses the ordinary generic
  authentication/not-found refusal; an uncertain authority read or listener
  generation replacement returns fixed `503 readiness_unavailable`. Every
  refusal discards all partial readiness results.
- **AR1-R7.** A paired active device without jobs/model controls may query only
  a bot it is currently authorized to access. This deliberate ordering lets
  that same caller learn its own missing control permission; a different or
  unauthorized bot, user, instance, or device gets the same generic not-found
  response. No roster, device list, grant row, job, or model existence is
  enumerated.
- **AR1-R8.** The entitlement is the existing effective `is_owner_device`
  decision, including its current legacy allowlist fallback when no explicit
  controls decision exists. The wire reports only `granted`, `missing`, or
  `unknown`; it does not reveal whether a legacy list or explicit row supplied
  that result. The readiness-only projection validates an explicit stored
  `allowed` value as SQLite integer `0` or `1`; malformed values or failed
  reads are unavailable, not a denial. Jobs and model management share one controls grant. The UI
  explains that it covers both features and is separate from bot membership,
  pairing, approval ownership, approval mode, and gateway administration.
- **AR1-R9.** A missing entitlement has the local **Request access** action. It
  opens a fixed explanation of the exact shared jobs/model control scope and
  tells the user how to ask the host administrator, with an explicit “Nothing
  was sent” note. The local UI action is labelled Request access; it performs
  no request, notification, network send, or store write. The host grants through the
  existing host-side control flow only; this feature adds no phone grant path.

- **AR1-R9a.** This diagnostic does not repair or qualify the existing jobs or
  model operation routes. In the pinned source, those routes check controls
  before an awaited bot-authorization read and do not reauthenticate after
  that await. The new diagnostics path must recheck its own disclosure scope;
  revocation/write-boundary correctness of existing operations remains a
  separate source-review and causal-test prerequisite.

### Status semantics and bounded wire contract

- **AR1-R10.** Each feature object has exactly these fields: `capability`,
  `entitlement`, `host_setting`, `profile_api`, `api_reachability`, `reasons`,
  and `action`. Enumerations and cross-field rules are in
  [`contracts/readiness-v1.md`](contracts/readiness-v1.md). Unknown, malformed,
  stale, contradictory, or unsupported internal state fails closed; arbitrary
  Hermes exception text and dependency names never cross the boundary.
- **AR1-R11.** `capability` is `available`, `hermes_not_found`, `below_floor`,
  `dependency_missing`, `probe_failed`, `requires_read`, `requires_send`, or
  `unknown`, mapped from the existing per-feature compatibility result.
  `entitlement` is the effective device
  controls result. `host_setting` reads the current exact-true feature flag
  (`cron.enabled` or `model_management.enabled`) for each request. These axes
  are never collapsed into one boolean.
- **AR1-R12.** `profile_api` is `configured`, `missing`, or `unknown`, based
  only on the existing fixed-loopback profile endpoint/key resolver for the
  already-authorized profile. The resolver may internally consult the
  profile's existing endpoint/key metadata; the diagnostic exports no
  credential bytes, endpoint, key, port, path, exception, or arbitrary config
  value. A blocking resolution runs outside the event loop. A normal no-usable
  result is `missing`; an indeterminate result is `unknown`; an exception,
  timeout, malformed internal value, or uncertain revalidation returns fixed
  `503 readiness_unavailable`. A `None` from the existing error-collapsing
  resolver is indeterminate, not proof of missing configuration.
- **AR1-R13.** `api_reachability` is always `not_probed` in this slice. The
  diagnostic makes no loopback request and reads no model or job resource.
  The API's availability at a future operation remains unknown. This is an
  explicit limit, not a success state. If a future safe probe is proposed, it
  needs a separate reviewed contract establishing a content-free endpoint,
  request/response bounds, authentication, timeout, and no side effects.
- **AR1-R14.** Reasons are exactly the lexicographically sorted union implied
  by the axes in `contracts/readiness-v1.md`: `version_below_floor`,
  `hermes_not_found`, `dependency_missing`, `probe_failed`, `requires_read`,
  `requires_send`, `compatibility_unknown`, `controls_missing`,
  `controls_unknown`, `host_flag_disabled`,
  `profile_api_missing`, `profile_api_unknown`, and `api_not_probed`. Cross-
  field iff rules and reason ordering are normative; duplicate, extra, missing,
  or unsorted reasons are invalid. A successful source read that returns an
  explicitly unknown status is represented by that axis's `unknown` enum and
  corresponding reason. A read exception, timeout, malformed internal object,
  uncertain scope revalidation, or listener-generation replacement returns
  fixed `503 readiness_unavailable`, never a partial response. Definitive
  authorization loss uses the ordinary generic refusal. `api_not_probed` is
  present on every feature.
- **AR1-R15.** `action` is exactly one of `request_access`,
  `plan_host_remediation`, or `check_host`, chosen independently per feature.
  For that feature, known missing Hermes root/dependency, below-floor,
  disabled flag, or missing profile API maps to a fixed local remediation
  plan; otherwise a missing shared entitlement maps to local Request access;
  all other states map to check-host guidance. Another feature's state never
  changes this feature's action. The plan is informational, names only the
  relevant public HMP setting or standard host check, does not read or rewrite
  host configuration beyond existing flag/endpoint reads, and never offers an
  automatic “Fix” action.
- **AR1-R16.** The response includes strict integer protocol revision `1`,
  strict JSON safe-integer `checked_at` in the inclusive range
  `0..9007199254740991`, and an opaque random 128-bit `generation` created for the
  listener lifetime. It contains exactly `jobs` and `model` entries and is at
  most 2 KiB. No names, identifiers, settings values, keys, endpoint data,
  job/model data, raw errors, or logs are returned.
- **AR1-R17.** The route is read-only, has no body or query, has a separate fixed
  per-device read bucket no greater than 30 requests/minute, four non-queued
  worker slots, a 2,000 ms response deadline, and returns fixed `401`, generic
  `404`, `429`, or fixed `503 readiness_unavailable` failures. Unavailable
  and generic not-found error bodies are exact and have no extra fields per
  the wire contract. A
  changed device family, device state, control decision, bot authorization,
  or listener generation during a lookup discards the response. There is no
  retry, write, persistent snapshot, or “green” cache.

### Client behavior and future mutation boundary

- **AR1-R18.** The client negotiates on each authenticated instance session.
  It fetches diagnostics only for the selected bot, at pairing completion,
  explicit refresh, and screen entry/resume; no background polling. It clears
  state on sign-out, reported revocation, instance switch, capability change,
  or listener-generation change. The current Mobile TokenManager exposes no
  event for successful P5 rotation; no immediate clear on that event is
  claimed. Displayed readiness is informational, is not an authorization
  cache, and MUST be freshly negotiated and fetched on the same captured
  foreground API, `iid`, epoch, and selected profile before opening local
  Request access/remediation guidance or before a jobs/model action. Any
  lifecycle change discards the readiness result and a local dialog tied to
  it. The fetch is observability only: legacy-unknown, not-probed, malformed,
  network, and readiness-unavailable outcomes do not independently authorize
  or deny the normal jobs/model operation. Failure to refresh cannot be shown
  as current permission status and cannot suppress the ordinary feature
  operation, whose existing route/lifecycle checks remain authoritative.
- **AR1-R19.** Readiness is a point-in-time preflight, not an execution
  guarantee. The jobs/model screens still handle their normal route refusal.
  The current route's masked `404` is not decoded as missing controls. If the
  normal operation fails, the UI shows a safe generic host/API failure and
  offers refresh/manual host check; it never retries a write automatically.
  `not_probed` does not disable or suppress normal user-invoked jobs/model
  reads, and it is never presented as ready.
- **AR1-R20.** A real access request, administrator notification, grant/deny,
  or Fix operation is out of this slice. A later separately reviewed contract
  must bind request and decision to exact device, user, instance, generation,
  bot, and feature scope; require current administrator authority and explicit
  confirmation; handle cancel/deny/expiry/revocation and concurrency; and
  provide authoritative readback. It must leave lost acknowledgement
  unresolved until readback and never replay a grant automatically.
- **AR1-R21.** Global host flags affect every paired device. Any future
  mutating workflow must show affected devices/bots, require explicit
  administrator confirmation, modify one allowlisted leaf only, recheck
  authority and concurrent changes at the write boundary, read back the
  effective value, and define rollback. No such global flag or restart action
  is part of this slice.

## Out of scope

Actual access-request transport, admin notification/decision API, grant or
revoke changes, automatic configuration repair, job creation/listing/content,
model selection/current-model/catalog/provider reads, API availability probes,
native Hermes changes, approval/push/phone-attachment behavior, host restart,
and physical-device/release qualification.
