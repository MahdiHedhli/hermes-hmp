# Permission-readiness wire contract v1

Accepted contract v3 (2026-10-04), recorded in the private source manifest and
independent review receipt. The endpoint family is additive under HMP v1 and
uses no client-selected fallback. HMP and Mobile source acceptance and runtime
qualification remain separate.

## Negotiation

`GET /hmp/v1/readiness/capabilities`

The request has no body and requires exactly the normal `HMP-Instance` and
Bearer authentication. It is the only additional exemption from HMP's
compatibility middleware so an authenticated client can learn that diagnostics
are unavailable on a below-floor or incomplete Hermes build. Current-key,
peer, header-size, and authentication checks still run first. The handler must
authenticate before returning protocol support or compatibility state.

Successful response, exact fields:

```json
{"protocol":1,"features":{"jobs":{"capability":"available"},"model":{"capability":"below_floor"}}}
```

The fixed feature keys mean only that this HMP build implements the response
shape. `capability` uses the closed values below and reports only the existing
feature compatibility result. It does not mean that a device is granted,
enabled, configured, or reachable. This endpoint exposes no resource, profile,
build identity, version, dependency name, or user/device/instance identifier.
For this exact negotiation path, HTTP 404 or 405 is the conservative
`legacy_unknown` result: the client does not call the bot route and does not
infer controls. The status/body of a 404 from the per-bot route is never
interpreted as legacy negotiation or missing controls. Authentication errors,
network/timeout/pin/clock failures, and other refusal statuses remain distinct
failures; malformed success is `protocol_unknown`, not legacy fallback.

## Per-bot diagnostic

`GET /hmp/v1/bots/{p}/readiness`

No body or query parameters are accepted. `{p}` is the existing bounded bot
profile identifier grammar. The path is not echoed. It requires capability
revision 1 and ordinary instance-bound bearer authentication. For an
unsupported Hermes read build the existing compatibility refusal applies.

Success schema (field order is non-normative; field set and types are exact):

```json
{
  "protocol": 1,
  "checked_at": 1791052800,
  "generation": "0123456789abcdef0123456789abcdef",
  "features": {
    "jobs": {
      "capability": "available",
      "entitlement": "missing",
      "host_setting": "enabled",
      "profile_api": "configured",
      "api_reachability": "not_probed",
      "reasons": ["api_not_probed", "controls_missing"],
      "action": "request_access"
    },
    "model": {
      "capability": "available",
      "entitlement": "missing",
      "host_setting": "enabled",
      "profile_api": "configured",
      "api_reachability": "not_probed",
      "reasons": ["api_not_probed", "controls_missing"],
      "action": "request_access"
    }
  }
}
```

`generation` is 32 lowercase hexadecimal characters from 16 random bytes,
created once per listener lifetime. It is not an authorization token and does
not replace bearer, instance, bot, or current-authority checks. `checked_at` is
a JSON safe integer timestamp in seconds from the HMP clock, in the inclusive
range `0..9007199254740991`; booleans and floating-point values are invalid.
It records observation time only, not freshness proof, grant, or authorization.
Each response is freshly
computed; clients do not persist it as a grant or authorization cache. The
current Mobile TokenManager exposes no successful P5 rotation event, so this
slice does not claim UI invalidation at that instant. Any displayed result is
informational only and must be refreshed with capabilities negotiation plus
the per-bot GET using the same captured foreground API, `iid`, epoch, and
selected profile before local guidance or a jobs/model action. If any of those
change, discard the result and any local dialog based on it. A legacy-unknown,
not-probed, malformed, network, or readiness-unavailable result does not
independently authorize or deny the normal feature operation. A failed
refresh is not a grant decision and does not suppress that operation; its
existing route/lifecycle checks remain authoritative.

### Closed values

- `capability`: `available | hermes_not_found | below_floor | dependency_missing | probe_failed | requires_read | requires_send | unknown`
- `entitlement`: `granted | missing | unknown`
- `host_setting`: `enabled | disabled | unknown`
- `profile_api`: `configured | missing | unknown`
- `api_reachability`: exactly `not_probed`
- `reasons`: unique, lexicographically sorted exact set composed from
  `hermes_not_found | version_below_floor | dependency_missing | probe_failed |
  requires_read | requires_send | compatibility_unknown | controls_missing |
  controls_unknown | host_flag_disabled | profile_api_missing |
  profile_api_unknown | api_not_probed`
- `action`: `request_access | plan_host_remediation | check_host`

No open string, native error, version, dependency label, profile label, key,
URL, port, job, model, provider, or arbitrary config field is permitted.

### Mobile decoding and legacy behavior

The capabilities DTO has exactly `protocol` and `features`, with strict
integer `protocol: 1`, exactly `jobs` and `model` beneath `features`, and only
the closed `capability` field within each feature. Its body is also capped at
2 KiB. A well-formed response with one or both feature values unavailable
still negotiates protocol 1.

The Mobile DTO decoder accepts only the exact field sets above, strict integer
`protocol == 1`, strict safe-integer `checked_at` in `0..9007199254740991`, a
lowercase 32-character hexadecimal generation, the exact `jobs` and `model`
keys, closed enum values, and exact reason/action cross-field rules. It rejects
booleans where integers are required, duplicate JSON keys, non-finite numbers,
nested structure deeper than 4, excess bytes, unknown fields, unsorted/duplicate
reasons, and contradictory feature equality/action combinations as
`protocol_unknown`; it never coerces types or unknown enum strings. The client
uses the existing strict I-JSON decoder and a 2 KiB maximum response body.

Only a 404/405 from the fixed capabilities path maps to `legacy_unknown` and
fixed “readiness unavailable on this host” guidance. That outcome causes no
controls claim and no alternate-version/path request. A network, timeout,
clock, TLS pin, 401/403, 429, or 5xx result remains a transport/auth/refusal
state and is never translated into `legacy_unknown` or `controls_missing`.
For the per-bot path, a generic not-found remains generic and never proves
absence of the feature or a grant. A valid `protocol: 1` capability response
must precede the per-bot request on the same captured authenticated instance;
it is not necessary for both feature capability values to be `available`.
The per-bot route's normal global compatibility gate remains authoritative.

The client presents `request_access` as local guidance with a visible
“Nothing was sent” note; `plan_host_remediation` is display-only; and
`check_host` is not success. If `api_reachability` is `not_probed`, the UI
shows “not tested” and no green-ready state. A normal user-invoked jobs/model
operation remains available and follows its existing route; this diagnostic
state does not suppress that operation. Refresh capabilities and readiness on
the same captured foreground API, `iid`, epoch, and selected profile before
opening any local action or issuing the normal feature action. This does not
use a hidden P6 flow or send a controls request. If refresh fails, retain a
non-authoritative warning and still let the user invoke the ordinary feature
route. Preserve the existing single P5
bearer refresh only for a genuine unauthenticated GET on the same captured
lifecycle. It is not a readiness retry: do not refresh on 404, network,
timeout, malformed, stale, unavailable, or any write, and never replay a
write.

### HMP exception-preserving diagnostic projection

The readiness handler MUST NOT call an operation-gate convenience method and
reinterpret its fail-closed `False`/`None` as a diagnostic cause. In the pinned
source, controls, feature flags and endpoint helpers intentionally collapse
some exceptions/ambiguity for operational gating. Implement separate
readiness-only projections that preserve the source outcome while leaving
every ordinary gate unchanged:

- **Controls:** read the existing explicit `device_owner_controls.allowed`
  decision first and accept only SQLite integer `0` or `1`. A row is the
  exact decision; no row means use the existing legacy `owner_device_ids`
  fallback. An absent allowlist follows its existing empty-list default; a
  valid string list resolves membership. A malformed row/list is unavailable,
  not “missing”; a failed read is unavailable. Use `unknown` only when a
  completed authoritative source read is itself indeterminate.
- **Host flags:** read the currently loaded flag source used by the existing
  closures. An absent `cron`/`model_management` block or absent `enabled` key
  follows the exact existing closed default (`disabled`); exact `true` is
  enabled and exact `false` is disabled. A non-mapping source/block,
  non-boolean present value, malformed object, or read exception is
  unavailable, never `disabled`. Do not change normal route gates.
- **Profile API:** use the same selected-profile runtime scope, precedence,
  loopback policy, and key-usability floor as the existing resolver. Return
  `configured` only for a fully usable fixed-loopback endpoint. Return
  `missing` only when a completed, well-formed strict source read proves that
  endpoint/key is not usable under the existing policy. A `None` from the
  existing error-collapsing helper, an indeterminate result, or any ambiguity
  is `unknown`; an exception, timeout, or malformed internal value is
  unavailable. Never export or log credential/config values.
- **Compatibility:** a correctly typed `FeatureStatus` with
  `available=True` and no reason maps to `available`; `available=False` with a
  recognized closed `Unavailable` reason maps to that reason; a correctly
  typed unavailable status with no reason, or a well-formed absent status
  entry, maps to `unknown`. A wrong object/type, non-boolean `available`,
  unrecognized reason, or contradictory `available=True` plus a reason is
  unavailable. Never project tested labels or missing dependency names.

An observable read exception/timeout or malformed result at a required
projection boundary produces fixed `503 readiness_unavailable` and no partial
success. A completed indeterminate source value is returned as its `unknown`
axis. A definitive current-authority failure discards all fields and returns
the ordinary generic not-found/auth refusal; uncertainty while rechecking
authority is unavailable. No catch-and-default wrapper may change one class
into another.

### Deterministic mapping

1. Map existing `FeatureStatus` for `jobs` and `model` independently. The
   capability endpoint returns this same mapping without profile or
   entitlement data, including when the overall Hermes read gate is closed.
   A client must not call the per-bot route without a valid capability
   response and current instance session. Individual feature capability
   values do not gate the read-only diagnostic. A declared below-floor reason
   becomes `below_floor` plus `version_below_floor`; each other recognized
   `Unavailable` value maps to its matching closed capability/reason. A
   well-formed status with no determinate reason maps to `unknown` plus
   `compatibility_unknown`; malformed status returns unavailable.
   Unknown/newer versions with a well-formed successful status map to
   `available`; they are not rejected for lacking a tested label.
2. Evaluate effective controls for the authenticated device with the
   exception-preserving projection below. Exact effective allow is `granted`;
   exact effective denial after the legacy fallback is `missing`; a completed
   but indeterminate decision is `unknown`. Malformed or failed reads return
   unavailable. Add the corresponding controls reason. Never reveal whether
   the explicit row or legacy fallback supplied the decision.
3. Read live `cron.enabled` or `model_management.enabled` with the strict
   projection below. Exact true is `enabled`; exact false or an absent key
   under the existing closed default is `disabled`; completed indeterminate
   input is `unknown`. Malformed or failed reads return unavailable. Add
   `host_flag_disabled` only for `disabled`.
4. Resolve the profile's fixed-loopback endpoint/key only after current
   device and bot authorization. Return only `configured`, `missing`, or
   `unknown`; discard endpoint/key fields. A strict completed source result
   may prove `missing`; a `None` from the existing error-collapsing resolver
   is `unknown`. Malformed or failed reads return unavailable. Do not make a
   network call.
5. Always set reachability to `not_probed` and add `api_not_probed`.
6. Choose each feature's `action` independently using this precedence for that
   feature: if its capability is `hermes_not_found`, `below_floor`, or
   `dependency_missing`, or its `host_setting=disabled` or shared
   `profile_api=missing`, use `plan_host_remediation`; else if shared
   entitlement is `missing`, use `request_access`; else use `check_host`.
   A different feature's capability or flag never changes this feature's
   action. Unknown axes, `probe_failed`, `requires_read`, `requires_send`, and
   mandatory `not_probed` never become a positive action. No successful
   “ready” action exists.

### Normative response validity

For a successful per-bot response:

- Top-level keys are exactly `protocol`, `checked_at`, `generation`,
  `features`. The feature keys are exactly `jobs`, `model`; each feature has
  exactly the seven fields and types in the example.
- `protocol` is strict integer `1`, not boolean. `checked_at` is strict JSON
  integer `0..9007199254740991`, not boolean or floating point. `generation`
  is exactly 32 lowercase ASCII hex characters.
- `reasons` is exactly the lexicographically sorted set implied by the axes;
  there are no extras. Per feature, `capability=available` adds no capability
  reason; `hermes_not_found` adds `hermes_not_found`; `below_floor` adds
  `version_below_floor`; `dependency_missing`, `probe_failed`, `requires_read`,
  and `requires_send` add the identically named reason; `unknown` adds
  `compatibility_unknown`. `entitlement=granted` adds no controls reason;
  `missing` adds `controls_missing`; `unknown` adds `controls_unknown`.
  `host_setting=disabled` adds `host_flag_disabled`; enabled/unknown add none.
  `profile_api=missing` adds `profile_api_missing`; `unknown` adds
  `profile_api_unknown`; configured adds none. Every feature adds
  `api_not_probed`. The array is duplicate-free and uses exactly this union.
- Both feature objects have the same `entitlement` and `profile_api` because
  there is one effective device decision and one profile observation in the
  snapshot. Capability and host-setting axes can differ. Reachability is
  `not_probed` in both. Each action must exactly follow the precedence above.
  Reject contradictions; Mobile must not repair them.
- Sample reasons therefore serialize as `["api_not_probed", "controls_missing"]` in this order.

The bounded response is at most 2 KiB. Request bodies are empty; query
parameters are forbidden. For JSON parsing, root object depth is 1, the
`features` object depth is 2, a feature object depth is 3, and a `reasons`
array depth is 4; maximum accepted nesting is exactly 4. Use the existing
strict I-JSON duplicate/depth behavior. HMP emits no partial response after a
failed authority or data read.

## Authorization and errors

The per-bot route order is: normal current TLS key and peer checks; parser
limits; compatibility middleware; bearer/instance authentication; per-device
rate limit; current per-bot authorization; then readiness-only reads. This
first per-bot auth is what permits reporting the caller's own missing
device-controls grant. It prevents using readiness to enumerate unauthorized
bots. HMP then re-auths the same bearer and rechecks ACTIVE device/family, bot
authorization, effective controls, feature flags, and listener generation
after every blocking lookup and immediately before constructing the response.
A definitive authority loss uses the ordinary generic not-found/auth refusal
identical to the nonexistent-profile refusal; an authority recheck that cannot
establish the current scope or a generation replacement returns
`503 readiness_unavailable`. Either discards every readiness field. A completed
indeterminate data projection is an axis value `unknown`; it is distinct from
uncertain authority and does not become a 503 by itself.

Fixed errors: ordinary authentication errors; generic `404 not_found` for a
definitively unauthorized/nonexistent bot; `429 rate_limited`; `400
bad_request` for a body/query or malformed target; and `503
readiness_unavailable` when a required read throws, times out, or yields a
malformed internal projection, when an authority recheck cannot establish the
current scope, or when listener generation changes during the snapshot. A
completed but indeterminate data value is represented as `unknown`, not 503.
The new unavailable envelope is
exactly `{"error":{"code":"readiness_unavailable","message":"readiness unavailable"}}`;
no `why`, `authz`, or top-level extra is allowed. Generic not-found is exactly
`{"error":{"code":"not_found","message":"not found"}}` with no extras.
No error body distinguishes an unauthorized profile from a nonexistent one.
The capability endpoint returns ordinary bearer errors and never grants
access.

Both endpoints are read-only. They do not write the store or listener record,
call the cron/model loopback API, probe a port, read job/model data, perform a
grant, or send a request to an administrator. They do not retry a failed
readiness response or API/content request. Preserve the Mobile client's
existing single P5 bearer refresh for an actual unauthenticated GET only, on
the same captured foreground instance and within that existing lifecycle; it
is authentication recovery, not a readiness retry policy. Generic not-found,
network, unavailable, stale, or malformed responses never trigger that
refresh. No write or request is retried.
