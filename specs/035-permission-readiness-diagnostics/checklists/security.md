# AR1 security checklist: permission readiness diagnostics

This checklist is a review plan. No item is marked complete by drafting this
specification.

## Authority and disclosure

- [ ] Capability negotiation requires current `HMP-Instance` and a valid
  unexpired bearer, even when the Hermes compatibility gate is closed.
- [ ] `/ready` remains unchanged and has no controls, profile, or per-device
  status.
- [ ] Per-bot readiness authenticates before rate-limit subject or profile
  lookups, then current bot authorization precedes controls disclosure.
- [ ] Unauthorized and nonexistent profiles have indistinguishable response
  status/body/headers; no profile name or grant existence is reflected.
- [ ] Device must remain ACTIVE, token family unrevoked/unexpired, same user,
  device, family, and `iid` throughout the point-in-time snapshot.
- [ ] Bot authorization and effective controls are checked after blocking
  awaits; any change or uncertainty discards the full snapshot.
- [ ] Current listener generation is compared before output; an older
  generation cannot produce a passing response.
- [ ] Existing `/bots/{p}/jobs` and `/model/*` authorization race is called
  out separately; the new route does not claim to fix or qualify it.

## Data minimization and semantics

- [ ] No jobs, prompts, job metadata, run state, current model, model catalog,
  or provider data is read by diagnostics. The existing scoped resolver may
  consult endpoint/key metadata to return only configured/missing/unknown;
  credential contents, endpoint, port, profile-home path, arbitrary config,
  and raw errors are never exported or logged.
- [ ] Feature API status, shared jobs/model entitlement, live per-feature
  setting, and profile endpoint configuration remain separate fields.
- [ ] Readiness never infers a denial from an operation helper's collapsed
  `False`/`None`; explicit controls accept only integer 0/1, absent data follows
  only the specified legacy/default behavior, and malformed reads are fixed
  unavailable. Completed indeterminate data alone maps to `unknown`.
- [ ] Observable projection exceptions/timeouts/malformed internal objects and
  uncertain authority rechecks produce the exact fixed 503 envelope; definitive
  authorization loss uses the generic not-found/auth refusal with no partial
  fields or `authz`/`why` detail.
- [ ] `unknown` is never converted to `missing`, `disabled`, or `ready`.
- [ ] Tested build labels, fingerprints, Git SHAs, raw missing-dependency
  names, and Hermes exception text are absent from wire and logs.
- [ ] `api_reachability=not_probed` cannot be interpreted as success. The UI
  has no green-ready state for this response.
- [ ] Request access is local fixed guidance only; no route, notification,
  database row, or implicit host grant is created.
- [ ] Remediation plans are fixed, host-only instructions; no settings,
  restart, rollback, or permission mutation exists in this slice.

## Bounds, cancellation, and failures

- [ ] Capability and readiness bodies are rejected; request and response size
  limits are explicit.
- [ ] Per-device reads are rate-limited; concurrent diagnostics use a fixed
  four-slot non-queueing bound.
- [ ] Deadline expiry returns a fixed refusal with no partial data; a
  cancellation does not release capacity before underlying blocking work has
  returned.
- [ ] Malformed profile, invalid enum, missing store/bridge, failed endpoint
  resolution, error while reading settings, clock failure, worker exhaustion,
  and stale identity all fail closed with fixed codes.
- [ ] No readiness/API retry, API probe, endpoint redirect, environment proxy,
  or external network call is introduced. The only permitted auth recovery is
  Mobile's pre-existing single P5 bearer refresh for a genuine unauthenticated
  GET within the same captured lifecycle; no generic 404/network/unavailable
  response triggers it and no write is retried.

## Required causal tests before source acceptance

- [ ] Capability route returns fixed global compatibility states after auth on
  below-floor, dependency-missing, unknown/newer, and normal builds; an
  unauthenticated request reveals none of them.
- [ ] A device missing controls can see `missing` only for a bot it is
  authorized to access; unauthorized, absent, cross-user, cross-instance, and
  cross-profile targets are identical not-found responses.
- [ ] Explicit controls grant/revoke, legacy fallback, store uncertainty,
  device revoke, family revoke/rotation, and expiry change during a blocked
  bot-auth read; stale results are discarded.
- [ ] Bot access revocation during the endpoint-resolution await prevents
  profile status from being returned.
- [ ] Listener-generation replacement during the worker await prevents output;
  app resume/instance switch clears visible state and causes a fresh negotiated
  read; no durable or authorization cache exists.
- [ ] Each flag and feature capability changes only its own axis; shared
  controls report consistently for jobs and model.
- [ ] Jobs and model actions are evaluated independently. A model capability
  or flag issue cannot change the Jobs action, and vice versa. Sorted reason
  arrays are exact unions; timestamps are strict integers in `0..9007199254740991`.
- [ ] Named-profile endpoint/key configuration is resolved in the correct
  profile scope and never appears in result/logs. No credential enters the
  diagnostic network because there is no diagnostic network request.
- [ ] Spies prove zero job listing, model current/options/catalog, job write,
  grant, config write, restart, provider call, or push side effect.
- [ ] Invalid/oversized response construction, unexpected source values,
  malformed profile, blocking worker saturation, timeout, caller cancellation,
  and late worker completion are bounded, private, and do not free worker slots
  early.
- [ ] UI tests show Request access guidance without sending; host remediation
  is a plan only; legacy hosts do not show “permission missing”; API status
  never shows “ready” while reachability is untested. Fresh negotiation/read
  before local or feature actions uses the same captured API, IID, epoch, and
  profile, but never gates the ordinary feature operation.
- [ ] No test or UI claim assumes an event for successful P5 token rotation:
  the current TokenManager exposes none. Readiness remains informational and
  no durable authorization cache exists.
- [ ] Existing jobs/model operation authorization and response behavior are
  independently tested/reviewed before any claim about their security. This
  task does not cover that gate.
