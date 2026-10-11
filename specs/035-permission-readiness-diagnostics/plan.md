# Implementation plan: permission readiness diagnostics

Status: contract v3 accepted 2026-10-04; bounded HMP source is being authored
for independent review and Mobile source is under separate review. This plan
does not claim source acceptance, phone UI acceptance, host activation, or
runtime qualification.

## Context and decisions

The feature follows [spec.md](spec.md), accepted wire
[contract](contracts/readiness-v1.md), and
[clarifications](clarifications.md). It is scoped to the currently paired
device and one bot for which that device has current bot authorization. It
reports the current effective shared jobs/model controls privilege without
changing it.

Source facts used for this proposal:

- `server.py` has an unauthenticated `/ready`; its compatibility middleware
  blocks other paths on unsupported builds before route handlers. Therefore
  the small capability endpoint must be exempted from that one middleware and
  authenticate inside the handler before returning data. It must not add
  permission detail to `/ready`.
- `auth.py` authenticates an unexpired bearer bound to the current `iid`,
  family, and ACTIVE device. `request_ctx.ServerContext.is_owner_device`
  resolves explicit controls and its current legacy owner-list fallback, but
  collapses some read failures to `False`/`None`. The readiness slice needs a
  separate exception-preserving projection and strict `allowed` 0/1 validation;
  ordinary operation gates remain unchanged.
- `reads.require_bot_authorized` checks current per-bot authorization. The
  existing jobs/model handlers check device controls before awaiting this
  authorization read. The proposed diagnostic uses a separate order so an
  authenticated device missing controls can learn its own status only after
  bot authorization succeeds.
- `compat.Eligibility.features` separately records jobs and model floors and
  dependency/API probe results. The tested label and build identity are
  evidence only. `adapter.py` reads `cron.enabled` and
  `model_management.enabled` live with exact-true semantics.
- `bridge.direct_send_endpoint` resolves only the fixed loopback bind and the
  selected profile's usable API key. It does not open a probe socket. The
  proposed response discards these values and reports only configured/missing/
  unknown.
- The normal jobs/model loopback methods can read job or model data and return
  generic unavailable errors. Diagnostics do neither. No reviewed
  profile-scoped, content-free health probe is established by this source
  pass, so runtime API reachability remains unknown.

The v1.6 feature route is additive and no existing error meaning is changed in
this slice. Do not edit HMP v1 or mobile source until independent review accepts
the proposed route and the open reachability limitation.

## Affected modules and contracts

| Area | Planned change | Verification |
|---|---|---|
| `server.py`, `contract.py` | authenticated capability path; compatibility exception for that path only; bot-scoped read-only readiness route and fixed `readiness_unavailable` | route-order tests, below-floor auth-before-response tests, closed response schema |
| `request_ctx.py`, `store.py`, `adapter.py` | separate strict readiness-only projections for feature status, exact-true flags, effective controls, and listener generation; preserve source errors without changing ordinary gates | absent/default, malformed, indeterminate, exception, timeout, stale generation and per-feature independence tests |
| `bridge.py`, `reads.py` | preserve current per-bot authorization and add a strict readiness-only profile configuration projection; collapsed resolver `None` is `unknown`, not proof of missing; no new Hermes imports or catalog/job readers | call-order and no-content-read mocks; named-profile scoping and unknown/error distinction tests |
| `mobile_model.py`, `mobile_cron.py` | no diagnostic calls to these data readers; preserve current operation routes | assert zero calls from readiness route |
| Mobile readiness screens | negotiate on each authenticated instance; display fixed Request access guidance or remediation plan; show “not tested” when API reachability is unknown | legacy fallback, forced fresh read before local/feature actions, app resume, revocation, and reason-to-action UI tests |
| `HMP_V1.md` | after contract review, add additive v1.6 routes, limits, enums, refusal behavior, and scope | contract/schema conformance fixtures |
| Host remediation/admin flow | no change in this slice | future separately reviewed contract and source task |

## Request and worker flow

1. Client performs capability negotiation for the currently pinned HMP
   instance using its current bearer. Unknown/old HMP takes the conservative
   fallback. Keep no durable authorization cache; clear known stale display
   state on sign-out, instance switch, capability/listener change, and app
   resume. The current Mobile TokenManager has no success event for P5 token
   rotation, so no immediate invalidation on that unobserved event is claimed.
2. A valid `protocol: 1` response permits the client to request
   `/bots/{p}/readiness` for its selected bot even when one feature's
   capability state is unavailable. The two feature states are independent;
   they describe status rather than gate this diagnostic route. The route's
   ordinary global compatibility refusal remains authoritative. There are no
   parameters or body. HMP authenticates, applies a per-device bucket, and
   authorizes the bot before examining the caller's controls.
3. A bounded, non-queueing readiness worker has a 2,000 ms response deadline
   and captures a complete point-in-time
   snapshot: same bearer/device/family/instance revalidation, bot authorization,
   exception-preserving effective shared controls, per-feature compatibility
   state, live settings,
   profile endpoint configuration, and listener generation. No partial
   snapshot is serialized. Do not hold a worker slot after its underlying
   blocking function ends; on caller timeout, the slot stays occupied until
   that function actually returns. At most four readiness workers are active;
   there is no unbounded queue. If all slots are occupied or the fixed request
   response deadline expires, return `503 readiness_unavailable` and no
   partial body. A timeout does not cancel the worker or free its slot; the
   slot remains charged until the underlying function actually returns.
4. Encode only the fixed DTO from the wire contract, cap the response at 2 KiB,
   and return no raw values. The diagnostic never calls the jobs route, the
   model current/options route, or any feature writer.
5. The phone computes the fixed action independently for each selected feature;
   another feature's capability or flag cannot change that action. “Request
   access” opens local guidance and says nothing was sent; “Plan remediation”
   is a non-applied host plan; “Check host”
   does not claim readiness. Before feature use, refresh diagnostics after app
   resume. A later refusal remains authoritative and cannot be masked by the
   prior snapshot.

## Security and compatibility review

The identity chain is bearer → active device/family → current bot authorization
→ current device-controls decision. Bot authorization is deliberately checked
before exposing the caller's own controls status. Any other bot refusal is
generic not-found. Reads after an await must be bounded and the complete scope
must be rechecked before disclosure. The handler takes a point-in-time snapshot;
it cannot make the subsequent job/model operation atomic with that snapshot.

Only current HMP's minimum-version and per-feature dependency/API compatibility
states are used. Do not use operational helpers that collapse exception or
ambiguity into `False`/`None` as diagnostic facts. Readiness-only projections
preserve observable errors; completed indeterminate values map to `unknown`.
Unknown/newer versions continue to be attempted. No exact SHA
or tested label can enter a runtime decision. A completed source read may map
an indeterminate value to the corresponding `unknown` enum; read exceptions,
timeouts, malformed internal values, and failed revalidation return fixed
`503 readiness_unavailable`. No raw exception or dependency name is returned.

Resource boundaries: no request body; existing bounded profile grammar; 30
diagnostics per device per minute; four concurrent work slots with no queue;
two-second response deadline; at most one scoped endpoint resolution per
profile request; 2 KiB response; no loopback network or provider call. The
diagnostic never retries; Mobile retains only its existing single P5 bearer
refresh for a genuine unauthenticated GET on the same captured lifecycle. It
does not retry generic not-found, network, unavailable, stale, or malformed
responses, and no write/request is retried. The design does not claim to bound latency of an underlying filesystem
or same-process Hermes call beyond worker concurrency/deadline, and timed-out
workers remain charged until actually finished.

Boundary fixed by this contract: the current pinned HMP source does not
establish a content-free, profile-scoped endpoint whose response safely proves
the jobs/model API server is reachable. This slice returns
`api_reachability: not_probed`; no jobs/model content route may be repurposed
as a health probe. Existing job/model handlers also have an
asynchronous authorization recheck gap. That is a separate security finding
and blocks claims about those operations, but this read-only diagnostics slice
does not silently widen into their writer/auth changes.
