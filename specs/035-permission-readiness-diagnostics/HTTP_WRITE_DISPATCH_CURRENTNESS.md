# AR1-035-T014c: loopback jobs mutation dispatch

Scope: DELETE job and POST pause/resume. Preserve the existing fixed numeric
loopback endpoint, profile prefix, native API credential, bounds, timeout,
no redirects and fixed response projection. No operator/live-host action follows.

The server captures original authenticated phone/profile/listener dependencies,
request task and job target before initial awaits. Authorization and endpoint
resolution use the held scope, with currentness checks after each await. Before
transport entry it rechecks that same scope. The fixed per-request preflight
checks the original task/cancellation and current authority without retaining or
logging URL/header callback parameters. It grants no rights and refreshes no token.

A fresh private ClientSession owns only HMP's fixed request class and middleware.
Mutation middleware retains one irreversible first-attempt latch before connect;
a second attempt refuses fixed CRON_UNAVAILABLE before another connection/send.
This also blocks aiohttp's transparent retry of idempotent DELETE after a lost
acknowledgement. GET behavior is unchanged. Never replay or reauthenticate to make
an already-attempted mutation proceed.

A local ClientRequest subclass checks a separate one-send latch and preflight at
send entry, after acquiring the connection, then immediately delegates to the
base send method. The connection belongs to ClientSession at that boundary;
its send-exception handler closes it. Do not move a refusing guard to connection
creation traces: inspected aiohttp3.14.5 connector exception cleanup does not
register/close its newly created protocol at that trace boundary. A trace named
headers_sent is not a documented pre-buffer authorization contract either.

No private retry flag, connector patch or dependency version allowlist is used.
The existing dependency floor is aiohttp>=3.14.5,<4. The supported ClientSession
request_class/middlewares extension points and ClientRequest.send are used. A
missing extension/unsupported constructor must refuse feature-unavailable before
connecting, with no alternate transport fallback. Exact dependency builds need
actual refusal/closure and one-attempt tests; version metadata alone is not proof.

The final pre-send sample is point-in-time, not atomic native revocation or a
write lease. Once native dispatch may have begun, retain ordinary completion or
uncertainty. Do not turn a completed mutation into a fresh auth refusal, claim it
was undone, or retry after lost acknowledgement/cancellation. Post-dispatch
response revocation, cross-system native atomicity and physical qualification
remain separate open requirements underT014.

## Acceptance

Use only disposable synthetic loopback peers. Require: successful each action
exactly once and unchanged projection; a lost acknowledgement produces exactly
one DELETE/POST with no replay; refusing pre-send after acquired connection gives
zero HTTP bytes AND peer EOF; real HMP routes losing controls at connection
acquisition never dispatch HTTP; unsupported middleware API has no fallback.
Preserve all existing read/native-write currentness, validation and readiness tests.

Primary API references:
- https://docs.aiohttp.org/en/stable/client_reference.html
- https://docs.aiohttp.org/en/stable/client_middleware_cookbook.html
- https://docs.aiohttp.org/en/stable/tracing_reference.html

The callback cleanup/order assessment also inspects exact installed aiohttp3.14.5
client.py, client_reqrep.py, connector.py and http_writer.py; it is source evidence,
not a new upstream guarantee or a claim about arbitrary future dependency builds.

## Source acceptance checkpoint

Independent focused contract and implementation review accepted the acquired-
connection request-class boundary and one-attempt middleware.163 focused HTTP,
native-write, read-currentness, cron/model and readiness checks pass with source
hashes unchanged. The three real HMP route fixtures revoke controls after the
connection is acquired and observe404 with zero HTTP bytes and actual peer EOF.
Lost-ack peers see exactly one DELETE/POST; positive routes return the original
projection exactly once. Ruff, plugin-surface, privacy and log scans pass.
This is not an installed host/device or release qualification.
