# Signed GO to fixed worker relay

Status: original-service current GO read and fixed native relay component are
implemented/reviewed. Production service dispatch, RESULT/TERMINAL and startup
qualification remain open. See
[component evidence](../../docs/research/presentation-signed-go-relay-2026-11-06.md).
Inspected base: bbcd2876cc0354ba3eba0e2f0499e1d2a7fc96e0.

## Actual dependency before RESULT and TERMINAL

`CredentialGoPhase.run` records the authenticated original GO, publishes its
original Future and keeps the same controller reading CANCEL. It intentionally
grants no worker relay. The generic `BrokerCancellationOwner.go_receipt` and
service ordinary-work gates stay closed for credential channels. Calling the
registry's legacy relay after a matching signature would bypass that separation.
No RESULT transfer or normal OK terminal may be inferred before actual relay and
held immutable result/native closure observations. ABORTED has separate actual
resource closure and earliest-budget requirements.

`CredentialGoPhase.creator_current` now revalidates the exact native GO receipt
on the original service actor, not the controller Task or an arbitrary caller.
It independently verifies the original signed GO/frame/context, current role,
clock, uncased original work budget, native control not retired/failed/unknown
and original actor after boundaries. Wrong actor/not-yet-notified queries cannot
poison the owner; admitted currentness failure is sticky for this consumer.
It returns only the original current read receipt. It starts no resource, sets
no relay completion and enables no generic work permission.

## Required relay implementation

1. Retain a distinct one-shot original-service relay owner on the original
   control before native effects, linked to the original current GO receipt,
   completed original READY writer, exact resources/input/control pipe/process,
   registry ticket, binding/generation/clock/budget and original service Task.
   Missing, failed or uncertain owners cannot be replaced or retried.
2. Require actual native/grammar GO and original current role at relay admission,
   with no local cause, remote CANCEL/header retirement or expired budget. Recheck
   exact READY/input native write observations; a receipt/boolean alone is not a
   child-control write. Do not revive the pre-resource queued phase.
3. Preserve `BrokerReaderResources.relay_go` and `OwnedControlPipe.send_go` native
   one-use ownership and control-close checks. Add only a fixed typed credential
   relay fence at the final `OwnedControlPipe._write_go` boundary, AFTER existing
   `_current`, exact FD and time callbacks and BEFORE the actual `os.write`.
   Its reciprocal original owner/role/cause/budget/actor seal must be callback-free
   after the last native callback. Do not install a caller-selected callback,
   replace `_current`, use a generic allow boolean or weaken native GO.
4. A complete actual native control write and known native pipe retirement under
   post-current original scope may mint a private local relay fact. It proves
   control delivery only, never child execution acknowledgement, result transfer,
   resource/terminal closure, native DRAIN/PRE_EMIT or publication. Partial send,
   close uncertainty, drift/cancellation or failed postcheck remains consumed
   with debt, not a retry, re-pair or renewed timer.
5. Compose the fixed credential service path only after component review; generic
   unsigned and public admission remain unchanged. Then implement actual signed
   RESULT transport and frozen TERMINAL/ACK on the original cursor, with startup
   qualification still independent. Do not replace the requested full feature
   with a snapshot or a no-GO fixture.

## Qualification

Use disposable fixed worker/source/input only; no real user profile/message,
provider, live host, credential installation or production deployment. Test actual
original native control bytes and child/result observations independently. Cover
wrong actor/scope/receipt/task/future, before GO, duplicate relay, key retirement,
CANCEL and deadline at each final boundary, native short/unknown write and close,
partial initialization and lost acknowledgement. No other operation's budget,
resource or native credit may change. Qualify no key/signing-capability inheritance
through the fixed exec/descriptor topology separately. Full character delivery,
startup, terminal/ACK/STATUS and physical/release qualification remain required.
