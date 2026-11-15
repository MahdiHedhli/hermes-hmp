# Bot channel health check

Status: draft implementation.

## Operator outcome

`hermes hmp health check` reports whether each currently served bot has the
runtime prerequisites for the HMP channels the owner enabled: Bot Chat send,
scheduled jobs, and default-model management. It identifies a blocked bot
before the phone tries a write. It changes no Hermes configuration or secret.

## Acceptance scenarios

1. A named bot lacks a usable profile-scoped API server key while the owner has
   enabled sending. The check marks that bot's send channel unavailable, exits
   nonzero, and does not reveal a key or endpoint. A healthy bot stays ready.
2. A channel intentionally disabled by the owner is shown as disabled and does
   not make the host unhealthy. An enabled channel with an unqualified build or
   missing loopback route/key is unhealthy.
3. After the operator repairs a profile and restarts the gateway, a fresh
   runtime snapshot reports readiness. A stale or malformed snapshot cannot
   produce a passing check.
4. A gateway with no current TLS-pinned listener, an unsupported Hermes build,
   or an unserved bot returns a nonzero result without creating host state.

## Constraints

- The gateway derives status from the same live flags, exact-build checks, and
  profile-scoped endpoint lookup as the actual routes. No key or endpoint is
  serialized; the private listener record carries only bounded status codes.
- Status is a prerequisite check, not a send guarantee. It cannot prove that a
  device is authorized or that a later loopback call will succeed.
- No unauthenticated network route is added. The CLI reads the checked local
  listener record and verifies the listener's pinned TLS identity.
- The check is safe to run repeatedly and does not invoke a child Hermes CLI.
- A record from an older HMP build reports health unavailable and fails closed.
