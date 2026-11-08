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

## Ephemeral actual-return prototype

A new immutable cache return holds actual attempt/result allocations and their
original tuple heads only while the fixed caller holds it. Its pure return tail
joins the exact result slot, effect/count bridge, module/owner/activation aliases
and original registration/lifetime. Neither holder nor helper is wired yet.
The future producer must pass its actual locally retained return; constructing
an equal holder or copying a namespace is not independent IO proof. Retained
ACK facts must exclude this return's prefix heads, with explicit graph checks.

## Optional cache producer prototype (no caller)

DeclaredCacheReadOwner._read now delegates only when given a typed consumer.
The default legacy route remains unchanged. The experimental producer publishes
the same cache journal attempt/effect, holds transient original heads before the
single latched actor/admission path, retains actual raw bytes immediately, then
publishes actual count/result/resultslot and a pending envelope containing the
locally held cache return. It retires only its original transient owner heads
after pending publication and checks the actual return again across callbacks.

Failure retains actual progress, abandons owned raw results, preserves a foreign
head replacement and raises fresh without raw-bearing exception context. Exact
clean unadmitted actor refusal retires this cache reader without inventing an
unknown native read or poisoning the unchanged shared ledger. No reader reuse is
promised. The old finally path is not used for typed reads.

This producer is not called by the file loop. Cache buffer/header consumption,
actual EOF ACK, bounded retained commit, caller closure and causal tests remain
unimplemented. Static checks are not operational qualification.

### Reviewed producer safeguards, November 8

The optional producer now fences the descriptor, effect cell and read list before nested access. Cleanup requires the held original owner/root/scope and journal cohort; routing drift preserves uncertain claims rather than clearing them. Three focused malformed-field regression cases have been added (descriptor, effect and reads), asserting zero foreign hooks and zero reader mutation. These cases are not yet executed: the existing minimum-version regression process remains live, and native suites are serialized. The cache consumer, header/EOF acknowledgment and file-loop integration remain unfinished.

### Cache consumer prototype, November 8

A separate descendant branch now contains an unwired fixed cache consumer. It holds the original pending envelope across actor/material checks, claims a one-use consumption cell, appends actual bytes to the original buffer/hash, and captures a bounded first-16-byte header. Actual empty EOF is checked before acknowledging its zero-delta return. The commit excludes cumulative journal prefixes; the pending envelope is retired at ACK. Owning failures abandon the original result and wipe the captured buffer; wrong-actor/duplicate attempts do not acquire cleanup ownership. This is static-checked prototype source, not tested integration. Caller closure, causal failure tests, reference-retention audit, independent review and file-loop wiring remain required. The producer checkpoint 9d5e549 stays clean and frozen for queued tests.

### Experimental caller integration, November 8

The descendant source now routes registered declared-cache reads through the typed producer and fixed consumer, including a real empty EOF acknowledgment before final metadata/hash checks. The caller carries the actual commit into an import-free closure checking the original ledger, retired raw/envelope cells, cursor, journal attempt/result/index and bounded header. Legacy unregistered reads retain their existing route. This integration has only static checks; no runtime pass or deployment is claimed. Required next gates are causal cache tests, partial-ACK cleanup and retention review, current/minimum-version suites and independent review.

### Partial acknowledgment test matrix, November 8

A test-only descendant adds sixteen interruptions: eight exact consumer boundaries for a nonempty chunk and the same eight for actual EOF (ACK publication, raw retirement, envelope retirement, cursor, progress, EOF state, phase and return). Assertions require preserved actual ACK history, raw/envelope retirement, failed lineage, cleared original buffer and no replay. These are authored synthetic cases, not executed passes and not claims about every bytecode interruption. The original 18-case integration remains frozen for its already queued current/floor lane.

Successful synthetic reads additionally assert that every retained commit has retired raw/envelope slots and that no exact cache-return envelope for this owner remains in the GC object inventory after collection. This is a focused regression for the prefix-bearing return wrapper, not a complete heap-size, deadline or native runtime qualification.

### Actual late-owner regression and repair, November 8

The 18-case current-version integration run on frozen `6f84dee` completed 17 passes and one failure (`late_owner`), unchanged source. The mutation was refused but the claim had already been cleared: the post-native `same` predicate lacked the activation owner/cell joins before publishing results and retiring the claim. This successor adds those original joins before publication. Foreign activation routing now prevents that publication and the existing finally cohort preserves the uncertain claim. The original failed receipt is retained; no repaired runtime pass is claimed until executed. This defect is confined to uninstalled prototype source.
