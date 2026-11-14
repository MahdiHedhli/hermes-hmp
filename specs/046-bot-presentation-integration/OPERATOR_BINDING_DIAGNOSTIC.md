# Read-only presentation binding diagnostic

Status: source candidate, not deployed; issue [148](https://github.com/MahdiHedhli/hermes-hmp/issues/148).
Base HMP9ab269583e4b99e9950e4354349a30d93c1b7814. This supports BI1/AR1
qualification; it is not an avatar fetch, access grant or rendering verdict.

## Specify / clarify

Add `hermes hmp health presentation`. Existing health check output/exit semantics,
listener record format and Controls/media operator operations stay unchanged.
Use the existing0700/same-UID/inode-checked operator socket, nonce and fresh TLS-
verified listener identity. New closed operation `host_presentation_binding_context`
has exactly protocol(1 integer),operation,iid,nonce,challenge; no profile/device/
path/URL/credentials/command. Its reply has exactly those five fields plus
 generation,state,sample_ms,expires_ms. State is `bound_not_probed` or `unavailable`.
The latter is not proof of a version, permission or host-setting cause.

Binding is sampled on the owning loop, never by calling the service's loop-affine
available property in a worker. Inspect the exact NativePresentationService type,
original ctx/loop/bridge/store/identity/iid links, retired=false and the listener's
existing presentation-current callback. Do not read metadata/images, call submit,
start a provider or construct an owner. This is binding metadata, not native
receipt/authority proof. Snapshot exact service identity and the binding boolean
before the existing bounded identity worker wait and recheck both afterward.
Replacement, generation change, closure or uncertainty refuses the observation.
An absent service can produce the unavailable enum only under an otherwise
current listener/source observation; arbitrary callback/read failures refuse.

Use existing nonqueueing shared read-worker capacity/retirement; acquire no new
slot, executor or detached task. The worker verifies current instance identity,
generation and the one2second deadline, but receives no NEW service capture or
argument and must not read loop-affine service state. The existing context graph
may already reference the service; transitive graph absence is not claimed. Only the loop adds the final state after
rejoin. Keep existing connection/request/response caps and peer/source checks.

The client validates all closed fields, challenge/iid/nonce/generation, strict
booleans/integers/enums and monotonic sample lifetime<=2000ms. For this new read,
pass one absolute2second transport deadline through connect/send/receive; do not
renew it per recv. Existing Controls/media transport behavior is not tightened
by this feature. Kernel/filesystem stalls and total CLI/setup time are not
claimed bounded by socket timeouts. Re-read the listener record and verify its
same pid/nonce/iid and TLS readiness after the exchange, then check the original
sample/expiry again before reporting status; do not renew or cache a result.
Older listeners' empty refusal becomes a fixed unavailable diagnostic, never an
instruction to disable ordinary features or broaden permissions.

CLI output contains only fixed status/guidance and existing setup-check output.
Bound text explicitly says images and phone access were not tested. Unavailable
or stale/legacy context returns EXIT_REFUSED; a valid bound-only observation
returns EXIT_OK for this diagnostic, not a feature or release acceptance.

## Plan / tasks

- [x] PB1 Independently review this contract, source call path and threat checklist.
- [x] PB2 Add closed request/reply client+server handling and owning-loop snapshot/
  identity-worker/rejoin within the original operator budgets and shutdown rules.
- [x] PB3 Register the readonly CLI subcommand outside writable Store dispatch;
  preserve existing health/setup/Controls/media and mutation command sets.
- [x] PB4 Causal source tests for loop-only sampling, bound/unbound, foreign source,
  replaced service during wait, stale generation/nonce/iid/challenge, wrong peer/
  unsafe parent, shutdown/cancellation/unknown submit and absolute transport budget.
- [x] PB5 Independent implementation review, related regressions, lint/surface/
  privacy/log checks and clear source-versus-host/device/release evidence.
- [ ] PB6 Separately qualify exact installed host behavior; no source result
  marks this or actual phone images/access tested.

## Security / analysis checklist

No new HTTP route, config/flags, persistent schema, grants/approval ownership or
mode change, model/provider/job/message operation, image/metadata read, private
profile content, background polling or new dependency. Same-UID admin observation
is not phone authorization. Preserve original worker completion-based retirement
and unknown-submit debt; a timed-out/cancelled observer cannot refund a live
worker. New parsing remains bounded/closed and existing request schemas unchanged.
No record or snapshot authorizes a native operation; rendering/worker/provider
readiness, per-bot data and physical delivery remain explicitly unprobed.

## Source verification (November 14, 2026)

Independent implementation/security review found and resolved one stale-observation
case: final TLS verification could outlast the reply TTL. A causal clock-advance
test now requires refusal after that check, without renewing the observation.
The final related run passed 252 cases: the 31 new diagnostic cases plus existing
operator-read, operator-fd, CLI, native presentation service and logging-policy
tests. Ruff, plugin surface, whitespace and staged privacy checks passed.

The positive service fixture is synthetic structural data, not an original
native service/provider receipt; the Unix exchange uses an actual same-user
private test socket. Successful shutdown assertions cover operator-work debt,
not executor-thread termination or all SDK lifetimes. Existing operator tests
cover unsafe parents, peer/source refusals and unknown-submit accounting; the
new tests cover this operation's rejoin, cancellation and shared capacity.
No gateway/core compatibility, installed host, physical device, image rendering
or release qualification follows from this source run. PB6 remains open.
