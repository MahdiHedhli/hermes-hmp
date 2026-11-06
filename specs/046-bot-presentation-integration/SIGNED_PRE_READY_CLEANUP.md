# Signed pre-READY cleanup integration

Status: first local READY-wait retirement prerequisite implemented and reviewed;
the distinct BEGIN-derived signing-only owner is also implemented/reviewed.
Pre-READY transport remains unimplemented, not an enabled route.
See [source evidence](../../docs/research/presentation-ready-cancel-retirement-2026-11-06.md).
Pinned inspected source: bdb3adff9fcfee52fa384f59ac1b438d5b754eb4.
Preserve complete desktop character delivery; this prerequisite is not a substitute.

## Exact current gap

The existing post-READY `NativeCancelCommitment.retain` requires a completed
`NativeReadyTransition`; the separate `NativePreReadyCancelCommitment` now derives
signed data from completed BEGIN plus exact cancelled-reader retirement.
`NativeCancelWriter` derives its original BEGIN scope through that transition.
Neither can safely be called with a fabricated READY object before READY arrives.
`NativePhaseWorkOwner._cleanup_material` also requires the original work Task
joined. `NativeReadyReceiver.run` now distinguishes an exact retained cancelled-wait
retirement from failures with unknown IO. The broader signed CANCEL path still
requires the remaining separate integration below.
Its `_released` requires known inactive/no-IO state. Merely joining the Task or
seeing a cancellation exception cannot prove that state.

The prior noncredential pre-READY cursor integration remains separate. Do not
route signed bytes through its unsigned reader, add a competing reader, reset a
partial cursor or infer signed native permission from those earlier tests.

## Implementation sequence

1. Retain an exact cancellation-only retirement on `NativeReadyReceiver`, following
   the existing `CredentialControlCursor` owned-wait pattern. Capture original
   scope, Task, socket, loop, readiness owner/Future/handle/binding, unchanged
   target/consumed/buffer bytes and cutoff **before** awaiting. Accept only the
   internal minted `_ReadinessCancelledError` whose exact owned wait retired
   under actual cancellation of the original Task. Recheck callback-free local
   custody after any native retirement checks. Never require live work/role
   authority to dispose proven local interest; never grant fresh read permission.
2. Preserve the original cancellation and permanent operation failure. Only an
   exact retained retirement may clear active local read ownership. Unknown
   registration, pending recv intent, substituted receipt/owner/Future, fake
   cancellation, stale cursor or torn read retain unknown debt. Buffer disposal
   is not an IO receipt; keep exact pre-disposal progress in the retirement fact.
   `_released` must prove the original Task actually done **and cancelled**,
   plus the retained fact;
   no boolean-only release. This yields local closure only, not CANCEL authority.
3. Introduce a distinct fixed pre-READY cancellation scope derived from the
   original completed signed BEGIN writer and checked transcript. Do not broaden
   the existing post-READY signer via nullable/fake transition fields. Require
   exact native BEGIN write fact, original cleanup actor, known write quiescence,
   known retired READY read and no GO attempt. Derive seq1/context from retained
   BEGIN data. Independently join the original cause/budget/qualified clock and
   existing `_can_cancel`/write-quiescence proof; read retirement replaces none
   of them. Native `_prepare_cancel` encodes/consumes the already-frozen earliest
   native cleanup window, never starts or renews it.
   Retain partial signer before native effects, consume once, reseal role/material
   and actor after crypto/native boundaries. No unsigned fallback or renewed time.
4. Compose the bounded signed writer through an explicitly typed scope join.
   Keep existing post-READY seq1/seq2 behavior and reciprocal BEGIN/GO writer
   proofs. Full native send counts are local transmission only. Uncertain write
   remains non-retryable UNKNOWN; local signing refusal cleanup may operate only
   with the same independently proven no-IO and original-budget constraints.
5. Correlate the actual original broker cursor's seq1 adoption with the exact
   frame/window. Broker resources/PENDING/terminal/native custody remain distinct.
   ACK, original-cursor continuation, result transport and publication require
   their own remaining implementation; no CLOSED or full character success claim.

## Required causal qualification

Exercise before any READY bytes, partial signed-record prefix/body, complete
signed record with partial native header, and complete READY before native
transition. Observe actual owned read-interest cancellation and original Task
join. Negative cases: generic/fake cancellation, wrong Task/instance/channel,
substituted readiness owner/Future/handle/end, stale cursor/byte count, pending
recv, uncertain registration, revoked role during signing, expired cleanup end,
torn BEGIN/GO and cancellation during final send. Each must prove no appended
CANCEL or closure credit where prerequisites are missing. Cross-operation facts
must never transfer. Do not restore failed production flags to make a test pass.

Run existing post-READY signer/writer/local-refusal and original broker adoption
regressions. Retain failure diagnostics and exact source/test binding. Independent
contract/security review precedes source qualification. Production startup,
physical devices and release qualification remain separate tasks.
