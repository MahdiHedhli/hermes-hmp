# Owned-peer lifetime/possession probe — bounded experiment accepted

This implements the reviewed conditional proof below as a disposable Darwin
experiment. It is not a production issuer, code-origin attestation, native
authority or started-reader release. No real Hermes home, service-manager label,
phone, provider, message, permissions or application protocol is involved.
The broader desktop-character and host-local-image goal remains unchanged.

## Conditional proof and limits

Under original exclusive connection custody, register a retained exact process
exit observer before generating a new unpredictable challenge. Require no pending
exit and no queued bytes/EOF. Send one role/scope-bound challenge on that same
socket under the unchanged admission deadline, require the exact response, then
recheck peer and the same observer. No second attempt, reconnect, reset or fresh
deadline follows any refusal or partial IO.

If no other process can retain or receive the peer FD, a fresh correct response
after registration proves that the original peer was alive during the proof.
An unrelated reused PID cannot answer on that connection. This conditional proof
can avoid an unconditional register-before-connect requirement; it cannot avoid
the custody premise. CLOEXEC alone does not prevent fork inheritance or explicit
descriptor passing. HMP-only source review does not prove the ambient gateway's
fork/dup/SCM_RIGHTS/delegation behavior. Do not disable tools/providers to satisfy
this premise, and do not turn this experiment into production permission.

## Actual source experiment

`tools/compat/presentation_peer_lifetime_probe.py` creates one private endpoint
and one fixed isolated no-content child. The external fixture controller alone
owns/reaps that child and keeps it unreaped through registration and proof. Its
descriptor ownership is a fixture premise, not a property inferred for Hermes.
Observer and child allocations remain retained before constructor effects.
Unknown cleanup retains actual owners; no automatic retry clears debt.

The challenge has a fixed version and role, 32 original scope bytes and a new
32-byte OS-random nonce generated only after registration/predrain. Response
framing is exact, bounded and distinct by role. Raw nonce/response/exception text
does not enter returned metadata. Native exit is distinct from owned child wait,
socket close, observer close and path cleanup. The controller never signals a PID
learned from a socket: emergency cleanup uses only its original owned Popen.

Candidate cases: normal echo; prequeued response before challenge; wrong role;
wrong scope; old nonce; partial response; unchanged-deadline silence; original
exit before proof; and an explicit delegated-socket counterexample. In that last
case only, the fixed child passes its own FD to the controller over a separate
owned fixture-control socket. After kernel-observed original exit, the other
holder can still return the correct fresh response. The original lifetime fence
must refuse despite the matching bytes. This demonstrates why possession alone
does not prove the original process, without PID scans/reuse forcing or orphaning
an unowned descendant. All processes are the controller's exact retained child.

Independent source review accepted one bounded nine-mode Darwin run. Root's
exact-source CPython 3.11.15 execution passed 20 checks in 0.45s: nine native cases
and eleven portable mode/path/admission guards. The reviewer independently read
all four source hashes, log hash and nine private mode-0600 observation files;
reviewer execution is not claimed. Every native case records known cleanup and
temporary-directory removal. Only normal echo succeeds. The delegated case
records matching fresh bytes after original-peer exit and a refused exchange.
Prequeued data refuses before nonce generation; early exit in this run refuses
at initial peer observation, not at a later timing boundary.

The private source-bound receipt is
`/private/tmp/hermes-lifetime-probe-311-20261106.json`. This one-way owned-child
experiment is not a bidirectional service/gateway terminal transcript, forced
PID-reuse test, exit-timing matrix or partial-constructor fault qualification.
Those remain separate work. Linux skips for the Darwin-specific primitive are
not Linux qualification; its separate runtime contract remains.

## Remaining production work

The [runtime issuer plan](RUNTIME_ISSUER.md) remains proposed with production
startup-origin/ambient FD custody unresolved. A source-level conditional proof,
fixture child ownership and typed local observation cannot mint production
qualification. A reviewed mechanism or complete applicable custody proof is
needed before deploying the handshake, then qualified terminal/ACK transport,
native PRE_EMIT/DRAIN/credential retirement, authenticated routes and signed
physical-device parity still have to compose. All remain required.
