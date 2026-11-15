# Clarifications: permission readiness

This records the bounded first-slice decisions accepted in contract v3. It is
not a source/runtime acceptance or an administrator grant.

| Question | Draft resolution |
|---|---|
| Does the public `/ready` route gain permissions or feature detail? | No. It remains unchanged. A new bearer-authenticated negotiation route is the only compatibility exemption and returns only fixed global jobs/model compatibility states. |
| Can an authenticated device without jobs/model controls learn its own missing permission? | Yes, but only for a bot it is currently authorized to access. Authenticate the bearer, authorize the requested bot, then read the caller's own effective controls decision. All other bot failures stay generic not-found. |
| Do jobs and model use separate device grants? | No. The current host decision covers both. Each feature reports capability and live host setting separately while both report the same effective shared entitlement. |
| Does capability mean feature ready? | No. It means only that the version/API checks represented by the existing HMP feature status passed. It says nothing about this device, host flag, profile endpoint, API server uptime, or future route success. |
| What does the Mobile client do with an absent route? | Only HTTP 404/405 from the exact capabilities path becomes `legacy_unknown` and fixed conservative guidance. A 404 from the per-bot path stays a generic refusal; malformed advertised responses, authentication errors, network/timeout/pin/clock failures, and server errors are not legacy fallback or evidence of missing controls. |
| Does diagnostics test loopback API reachability? | No. HMP's existing read operations do not provide an established content-free, profile-scoped health probe. Jobs/model listing/current/options are expressly excluded. `api_reachability=not_probed` is mandatory; the per-feature action is still determined by that feature's known capability/flag, the shared profile configuration, and shared entitlement. Do not infer API success. |
| What happens when a normal jobs/model call fails? | The normal screen shows a fixed host/API failure and offers refresh/manual host check. The existing `cron_unavailable` and `model_unavailable` errors do not identify the exact origin; AR1 does not claim to distinguish a network outage from a native route failure. That gap remains outside this source slice. |
| What does “Request access” do? | It opens local text explaining that one host control covers jobs and models and how to ask the administrator. It submits and records nothing. A real request/notification path awaits its own reviewed contract. |
| Does “Plan remediation” change host state? | No. It displays one fixed host instruction for a disabled flag, absent endpoint configuration, below-floor Hermes, or missing feature API. It never applies settings, restarts the gateway, or changes a permission. |
| What does an unknown/newer version mean? | The existing minimum-version policy allows ordinary feature operations to attempt unknown/newer versions. This readiness response does not probe Hermes; it reports only the already-computed compatibility state, then always reports `api_reachability=not_probed`. Exact tested-build labels are not consulted. |
| Is readiness a promise that the action will work? | No. It is a point-in-time informational result, never an authorization cache. It is refreshed on app resume and before local guidance or a feature action. The current TokenManager has no event for successful P5 token rotation, so immediate UI invalidation on that event is not claimed. It cannot make asynchronous authorization atomic with later operations. |

The existing single P5 bearer refresh remains limited to a genuine
unauthenticated GET on the same captured lifecycle. It is transport
authentication recovery, not a readiness or feature-operation retry. No other
read is retried, and no write is replayed.

## Contract decisions recorded for independent review

1. The capability endpoint is limited to fixed feature compatibility states
   and authenticates before disclosure.
2. `api_reachability=not_probed` is accepted for this slice; do not substitute
   jobs/model content reads or infer API success.
3. The controls/bot authorization disclosure fence is point-in-time and has an
   irreducible check/use race. It does not repair existing operations'
   asynchronous authorization checks.
