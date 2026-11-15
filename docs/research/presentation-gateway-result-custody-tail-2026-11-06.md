# Fixed gateway result custody tail — November 6, 2026

## Receiver prerequisite

The existing `RemoteOperationOwner._go_intent_local` is fixed to native GO_INTENT.
It cannot safely be reused after actual native GO_SENT by a result receiver or
made caller-selectable. The new distinct `_result_intent_local` is fixed to
GO_SENT and retains the same original native policy/lease/listener/admission/
operation/context/clock-budget custody checks, with explicit uncaused original
budget and current original credential work material and actor.

The method is a callback-free local conjunction after separate native current
checks, not a current-time sample, socket-read permission, received-result fact,
phase transition, publication gate or terminal settlement. It admits no generic
credential work and has no phase argument. Wrong-task refusal does not poison the
original work owner. A signature or matching phase enum cannot replace original
Task, native admission, role keys, policy closure or earliest frozen-budget seals.

## Causal verification

Seven cases use the actual retained original work Task and actual JobOwner
GO_SENT transition in the synthetic private peer fixture: current success, wrong
caller without poisoning, retired gateway role key, invalid native policy work,
retired listener, replaced admission alias and refused budget. Each negative first
proves the valid original conjunction, then changes only its named gate and checks
refusal. No result reader, native result, provider, real profile or production
startup is introduced. Independent read-only review accepted the fixed prerequisite and strengthened
before-GO_SENT tests. Focused run seven passed/132 deselected in 2.56s; the later
exact failed-node plus seven strengthened cases passed eight/132 deselected in
2.98s. Final affected confirmation: 1,606 passed, one skipped in 102.87s;
lint/whitespace passed. The earlier broader failure below remains unresolved.

Preserved intermediate fixture failures: first new cases referenced a conditionally
imported class and raised NameError; the five expected-negative test bodies then
passed for the wrong reason and are not coverage evidence. The explicit import
and bounded exception function/line diagnostic corrected that defect. A later run
had six passing test bodies plus one teardown error after actual admission alias
drift; the fixture now recognizes that exact immutable-admission mismatch as a
reason to perform fixture-owned raw socket disposal, without restoring admission,
protocol flags or native release facts. The subsequent seven-case run above is the
qualification evidence. Historical broker intermittency remains unresolved.

## Complete delivery remains open

Use this fixed tail only together with a retained original gateway signed RESULT
cursor, current native checks, original descriptor and bounded native result2
buffer/context. That receiver and its cancellation/discard/terminal continuation
are still required; see `SIGNED_RESULT_READ.md`. The broker counted signed writer
is a separate source component. No production dispatcher, host/device/build,
permissions, keys or settings changed here. Physical/release qualification and
native terminal/ACK/startup/publication remain incomplete.

A broader run reported 1 failed, 1,605 passed and one skipped in 105.14 seconds:
existing `test_signed_cancel_native_receipt_and_owned_local_stop` case
`signed_control_native_cancel-2` raised `BI1_CREDENTIAL_CANCEL_ADOPTION_REFUSED`
from the original control Task before notice consumption. No causal link to the
new tail has been demonstrated; its cause remains unresolved. The exact failed
node plus all seven strengthened result-tail cases then passed (eight passed,
132 deselected in 2.98 seconds). A later confirmation is recorded separately;
neither targeted nor broader success establishes a root cause or resolution.
