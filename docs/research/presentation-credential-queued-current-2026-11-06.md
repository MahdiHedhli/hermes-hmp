# Original adopted connection's pre-resource current check

Independent read-only review accepted `CredentialQueuedOwner` and its bounded
source/test integration. The original service retains this owner before its
constructor and before publishing adoption-complete. Failed construction leaves
that same partial owner/ticket/receipt on the failed connection; it does not reset
adoption or start resources. No production factory/dispatcher uses this path yet.

The owner retains the exact original service, connection, registry, ticket,
registry record, immutable input receipt, receiver/result/packet, handshake role
material, clock, task/loop, original cancellation budget and post-BEGIN grammar.
It admits only the original queued phase: no managed resources, start intent,
READY/GO/CANCEL/terminal state or failed connection. A historical ticket or
adoption boolean alone cannot satisfy this check.

`current_queued` checks the original endpoint/channel/registry, current role
material and key/process generation, original input-receipt relationship and
cancellation budget, then the qualified native clock against the exact original
signed WORK end. The shorter original read/admission cap remains historical;
it is neither renewed nor incorrectly reused as the work end. No native/phone
permission or phase signature is created by this current check.

Typed original reference/receipt/budget seals run after callback-bearing checks
before following current fields, including immediately after socket checks and
final clock sampling. An unknown object substituted as a budget, receipt field,
channel or reference container cannot run its getter/comparison/index callback.
Late refusal is sticky on this owner and does not free/relabel a retained ticket.
The output is the original queued record, not a resource/GO permit. Every future
resource and later phase entry must join this exact owner and its own original
phase facts; this queued-only predicate cannot authorize post-start states.

Root's expanded affected regression passed **1,114 tests, one skipped**, in 29.72
seconds; configured repository-wide Ruff passed. The adoption/queued module now
passes 20 cases. Fourteen added cases cover work checks after the earlier local
read end, key/budget/receipt/connection/grammar drift, wrong task, exact work-end
expiry, final-clock key/reference/budget/forged-receipt substitution, earlier
socket-boundary forged receipt, and constructor foreign channel. Tripwires
assert zero foreign getters/comparisons/index calls and no resource/GO effect.
The tests use actual disposable service/socket/registry ownership and synthetic
policy input/keys with modeled peer/clock facts. Review ran no tests/live actions.

Earlier adoption source `778d100` passed CI716 plugin job128025374694: 8,292 tests,
190 subtests, 33 skips, 18 warnings, 310.70 seconds. Plugin steps and all Python
3.12–3.14 Unicode jobs passed. This is not CI qualification of the new queued
owner. Remaining production runtime/source/key startup, signed work/cleanup/direct
IO, resource/GO/result/terminal/native publication, STATUS and physical/release
qualification remain open. No live host/device/permission change or key installation
occurred. The prior destination-custody incident remains unresolved.
