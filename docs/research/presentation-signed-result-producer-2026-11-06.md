# Signed RESULT producer — November 6, 2026

## Implemented boundary

`presentation_credential_result.py` retains a distinct original-service signing
owner after the original native worker has drained normally and the fixed signed
GO relay has an actual full 65-byte local control-write/known-close fact. That
historical fact does not certify execution, transfer or terminal settlement.

The owner checks original reciprocal control, signed GO, adoption, binding,
cursor, registry record and resource references. Current role keys, original
service Task, native clock, cause-free frozen budget and drained resource state
remain conjuncts. It takes the immutable native candidate once, hashes canonical
RESULT header plus bounded payload views, and signs broker-to-gateway RESULT seq1.
It does not allocate a complete concatenated frame or write to a socket.

Failed preparation is sticky. After a native take, failure discards the owned
payload and signed-data references; pre-take refusal does not claim disposal of
the resource-owned candidate. Original cancellation withdraws the producer's
payload/frozen aliases before native cleanup clock sampling. No retry, replacement
actor, unsigned fallback, transfer fact, terminal fact or publication is enabled.
Immutable bytes are released by reference withdrawal, not claimed securely erased.

## Verification and limits

Seven private-peer stages cover successful signing, wrong actor without poisoning,
key retirement, deadline expiry without revival, post-take retirement, post-crypto
key retirement, and post-take GO alias substitution without foreign getter calls.
They use disposable synthetic workers and private sockets, no provider/user data.
The cancellation probe checks withdrawal before native cleanup sampling; wrong
control cannot retire this owner. Error traceback locals and cause context are
checked for retained candidate/signed-data aliases.

Focused final run: seven passed, 22 deselected in 4.13 seconds; lint passed.
Independent read-only review accepted the final reciprocal alias checks and
signing-only scope. Full exact-source regression: 1,584 passed, one skipped in 97.96 seconds;
whitespace checks passed. Historical intermittent broker controller/wrong-spine failures remain
unresolved; a later passing run does not establish their cause or resolution.

## Remaining integration

Implement original-service counted signed RESULT streaming, original-controller
first-cause withdrawal and active-write retirement, gateway original-cursor signed
RESULT reading, terminal/ACK continuation, installed-runtime startup and native
publication gates. Full wire delivery must precede any transfer fact; signature or
local worker completion cannot substitute. Physical and release qualification
remain separate. No host, device, build, keys, grants or settings changed here.
