# Declared-cache shared read custody

Implementation in progress from2312e0b. The existing cache read method remains
unchanged and the new input join helper is unused DATA validation, not authority.

The fixed cache producer will retain actual per-call heads (prior attempts,
prior results, new attempts) locally before admission/actor callbacks. The owner
holds the same transient roots while the original owner snapshot is sampled.
Admission joins original module/owner/activation aliases, claim/effect/count and
actual heads; a global-only swap differs from these roots, and a coherent owner
swap differs from the snapshot. Use one latched actor path and one shared debit.

After native return, retain raw bytes first, then actual new count/resultslot and
result tuple. The original pending envelope must carry the actual attempt/result
and actual head allocations; never recapture owner heads after callbacks. Clear
only original owned transient heads after sealed pending publication. An owning
failure preserves actual known progress and uncertainty, retires raw and retains
original descriptor cleanup; a foreign replacement is not erased or adopted.

Fixed cache consumption feeds original buffer/SHA and captures first16 header
bytes before ACK. Actual empty EOF with zero count delta is ACKed before later
metadata/final hash. Preserve the existing4096-call cap, claim lifecycle and full
read-chain checks. ACK commits keep bounded per-call attempt/result/index/header
facts; no prefix tuple heads may remain through retained operation/consumer/step
backreferences (avoids quadratic retention). The caller holds the original
envelope through final closure, then releases ephemeral prefix references.

Required next: native producer, actual pending return, fixed consumer/header/EOF
ACK, exact failure cleanup and wiring. Causal tests must cover namespace-only
and coherent head swaps, stale/foreign claim/result/slot, wrong actor, copied
count, lost native/consumer/ACK return, reentry and complete buffer/prefix release.
Runtime read-regression2312e0b remains frozen and running separately. Remaining
metadata/link/diagnostic outcomes and enumeration are still required; neither
this helper nor the existing runtime read pass certifies the six-site boundary.

Bounded review found no type-order/foreign-hook defect in this unused helper.
The helper also checks the effect's original before-count and unreturned/known
state. It does not establish the complete attempts prefix solely from lengths
and the new slot; the fixed producer must construct that exact prefix from its
held prior tuple, and admission must join it across the actor snapshot. Neither
these DATA checks nor source review are a successful cache-read test.
