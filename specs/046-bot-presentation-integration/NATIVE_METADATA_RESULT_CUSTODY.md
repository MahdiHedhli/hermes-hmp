# Original metadata result custody

Status: contract preparation against `8afe009`; no metadata dispatcher or completed
six-operation qualification. Cache repair qualification remains on frozen source.

## Existing boundaries and preserved behavior

`StartupArtifactOwner._stat` invokes only the captured native operation 3 with
`name`, `dir_fd=parent`, `follow_symlinks=False`. `_fstat` invokes only captured
operation 4 with the held original descriptor. Both currently retain the actual
stat result locally but return it after callback-bearing guards without a typed
pending result/consumer acknowledgment or shared operation debit.

`RuntimeCacheProbeOwner._stat_known` separately accepts only the captured exact
FileNotFoundError class, exact integer ENOENT and exact matching string filename
as missing DATA. The distinct cache-absence diagnostic boundary must retain its
own plan and ordinal; neither path can turn a missing result into fallback,
permission, decoding, read or execution authority. Permission and structural
errors remain failures. Directory enumeration is a separate effect contract.

## Fixed producer and consumer contract

1. Each actual stat/fstat site supplies a held original consumer plan: original
   owner/scope/registration, file or directory walk, fixed site/ordinal, exact
   name/parent or descriptor, and intended policy check. A caller string or copied
   tuple is not a plan. Do not install a generic callable/operation dispatcher.
2. Capture the native callable, stat-result class and exact error classes before
   callbacks. Prepare the original operation/result allocations before admission.
   Use one latched actor sample with pre/post original-cohort closure. Wrong actor
   without drift causes no debit; drift retires the lineage as unknown.
3. Under the original ledger, debit one shared work unit, preserve all existing
   close reservations, publish ACTIVE before the literal C call and retain its
   actual return in the original result slot immediately on return. No callback,
   user equality, imports, metadata reconstruction or plan recapture may precede
   this retention. A diagnostic exception becomes bounded DATA only in its
   explicitly declared missing-result producer, preserving exact type/errno/name.
4. Publish PENDING after original native result, plan, resource, registration,
   authority and lifecycle joins. No new work or descriptor close is admitted
   while a result is pending. A returned stat_result alone does not unblock it.
5. The fixed consumer checks the actual original result against its fixed policy:
   parent directory identity/mode, declared leaf pre-open metadata, held opened
   descriptor identity, post-read identity, link metadata or exact missing probe.
   Its bounded immutable commit contains primitive observed fields and original
   resource/site identities, without cumulative history copies. No caller-built
   success row or reconstruction is acceptable as the actual consumer return.
6. After the last callback, recheck the held actual result and commit, retire the
   raw result/envelope slots, advance the original site cursor, and restore IDLE.
   Caller carries that actual commit through its own closure before later work.
   Failure after admission never refunds allowance, replays work or rewrites a
   completed ACK as an unconsumed operation. Original unknown/debit/ACK history
   survives partial publication; foreign replacement slots are preserved.

## Required implementation and tests

- Inventory every stat/fstat site and each distinct missing-stat diagnostic.
  Declare exact per-site policy and resource proof before adding the call path.
- Wire one literal boundary and its actual fixed consumer end to end first, then
  migrate all sites; incomplete migration cannot claim a six-operation budget.
- Retain symlink/non-following behavior, UID/mode/link-count/size/identity checks,
  original descriptor close reservation and the complete runtime/version gates.
- Causal fixtures must observe actual native calls/returns: wrong actor and
  reentry, pre/post callback owner/activation/root/descriptor/plan replacement,
  wrong result class, copied coherent result/commit, quota exhaustion, no native
  effect before debit, no extra actor sample, metadata mismatch, exact ENOENT vs
  EACCES/ENOTDIR, pending-work/close refusal, partial ACK, lost return and cleanup.
- Current and minimum Python suites, complete startup selection, CPU/RSS/deadline,
  native service/key/runtime and physical character display are separate gates.
  No deadline extension, legacy permission broadening, or host deployment here.

## Finite contract review additions

Each site plan needs an independently anchored original allocation plus a one-use
consumption latch captured before the first admitted callback. Stat binds the
actual nofollow parent allocation and original lexical component; fstat binds the
actual held open result and its FD, never numeric-FD membership alone. Review
inventory `NATIVE_METADATA_SITES.json` records source hashes and syntax sites;
it is not the independent runtime plan or admission authority.

Pending metadata must not invoke IDLE-only work guards. The fixed material policy
closure is surrounded by import-free original plan/result tails. Snapshot fields
are exactly dev/ino/mode/uid/gid for directory identity, adding nlink/size/mtime_ns/
ctime_ns for file identity. Preserve exact integer primitives. Where source
bytecode timestamp policy needs seconds, retain actual st_mtime and perform the
existing bounded `int(actual st_mtime)` conversion, not nanosecond flooring. Keep
the actual stat_result held until the primitive snapshot and consumer commit are
closed after callbacks.

The diagnostic producer classifies an actual native exception only inside the
native-call handler, through captured exact error classes/member descriptors.
Keep bounded diagnostic category DATA, never the exception/traceback/errno/name
object. Bind each diagnostic to its original pass/path/component/ordinal; the next
distinct confirmation needs its own plan and follows the previous typed ACK.
Both share the same original global quota. Do not broaden generic stat to treat
any exception as missing.

Known raised native work, mismatched result, interrupted publication and partial
ACK all need an explicit ended/abandon transition. Reserved descriptor cleanup
can proceed only after that original work has ended; unknown/ACK/debit history
remains sticky. No retry or restoration of IDLE can erase ambiguous work.

## First source preparation

An unwired `_NativeMetadataSnapshot` and `_native_metadata_snapshot` now capture exact identity integers plus the actual st_mtime under original native machinery joins. They perform no native call, debit, phase change, site advance or ACK. The producer must first retain its actual C return, and a fixed consumer must later bind this DATA to the original pending result. Merely constructing or copying a snapshot grants nothing. No timestamp conversion or policy is silently applied at snapshot capture. Runtime tests and boundary wiring remain required.

## Original declared-file site allocation prototype

Each registered file walk now has an original metadata slot. Beginning that walk allocates its fixed metadata order once, before descriptor acquisition: directory fstats, leaf pre-stat/opened-fstat, after-read fstat/stat, and after-hash fstat/stat pairs for every ancestor, whether or not source hashing is active. Allocation is lazy per file, avoiding a full path-product allocation across the package. The original walk pins the actual plan and its progress cells. These definitions do not bind an opened parent or leaf yet, admit native work, debit budget, consume results or advance an ACK. Tree/link/cache-absence site plans and operation/consumer wiring remain required. This source is isolated from the running8afe qualification and has not run tests.

Finite source review caught and corrected an initial definition mismatch: the actual walker performs final ancestor checks, not an extra leaf pair. No native calls or checks were added/removed to fit the plan. This correction is unexecuted source and does not qualify metadata consumers.

The experimental walk handoff now carries its actual locally allocated metadata plan as a sixth held item. The file caller retains that handoff through finish, which compares the original plan identity against its original walk slot; it does not recapture an allegedly current plan after callbacks. Until metadata consumers are wired, the final check requires the metadata cursor to remain zero with no pending result. This six-item handoff change exists only on this unqualified preparation branch; the separately running8afe cache lane retains its five-item handoff.

## Original resource preparation prototype

A separate descendant now checks the actual six-item held walk/metadata plan and prepares the next resource DATA. Fstat binds the original opened component; stat binds its actual original nofollow parent chain (or the explicit root None parent) and exact lexical component. Each chain joins original open allocation/result, ledger membership, registration, flags and unattempted reserved close. Numeric FD membership alone is insufficient. The resource captures original arguments before any future admission callback. These helpers perform no syscall, debit, plan advance, result consumption or ACK and are not yet wired. The prior11-case candidate stays frozen; these new helpers require causal resource tests and review.

Five composed synthetic resource cases are authored at the actual first opened directory in a runtime-source file walk: normal, copied descriptor, copied registration, foreign descriptor and unexpected lexical name. They require unchanged budget/attempt count/plan cursor/phase and successful original file completion after a refused preparation. Syntax/static checks pass; execution and broader resource/debit/consumer qualification remain pending.

## Metadata intent/result preallocation prototype

The separate `presentation_native_metadata` module now prepares original metadata intent/result cells from the actual held resource. Only captured stat/fstat operation3/4 bindings and original arguments are recorded. Preparation requires IDLE, no inflight/pending result, a nonfailed original ledger and capacity for one work unit while preserving existing close reservations. It captures actual attempts/count allocations and preallocates raw/category/snapshot/consumer/ACK/envelope cells, then repeats original resource and budget joins. It does not debit, publish to ledger, change phase, invoke a native callable or bind a policy consumer. No admission helper or syscall dispatcher is provided until original fixed consumer/lifecycle closure is implemented and tested.

The composed synthetic package now copies and imports `presentation_native_metadata` before its package namespace closes. Eight operation-preparation cases are authored: five actual resource paths (normal verifies captured fixed C callable, original arguments/budget/result cells and no ledger/phase/cursor changes), plus three malformed-field zero-hook cases. This repairs the fixture package rather than stubbing the new module. They remain unrun; no operation admission or result-consumer pass is claimed.

## Fixed directory consumer preparation prototype

A separate descendant now binds the unused original operation to a fixed initial-directory consumer for retained runtime-source or declared-cache owners. It captures the original scope owner type/material namespace/code and file-function/code plus the existing parent lifetime cohort. Registry lookups only rejoin the retained namespace; they do not nominate a replacement class. Original result/budget/phase cells are checked before and after preparation and the actual consumer is bound once into the original result. No actor sample, work debit, native call, result policy evaluation or ACK exists yet. The scanner rejected direct new startup imports; those imports were removed in favor of retained scope bindings without changing scanner policy. Configuration/tree/other-owner policies remain distinct unfinished consumers.

## Constructor-return material closure repair

Finite review found the initial consumer factory rechecked resource/lifetime but omitted a final code/module/class closure after consumer allocation. This isolated successor captures class/module names and the actual file-owner type and applies an import-free material tail immediately before and after consumer publication. It rejoins original function code/globals, scope origin, class exports, fixed file function/class and original registry module identities. This is preparation-only source, not a syscall bypass or a qualified native consumer; causal constructor-return drift tests and replacement execution are required. The earlier9-case candidate remains frozen and separate.

## Fixed directory policy DATA

An isolated descendant now implements the existing POSIX directory checks over an exact primitive stat snapshot: directory type, root/current UID, no setuid/setgid, and no group/world write except root-owned sticky directories. It uses literal POSIX bit operations to avoid a new mutable stat-helper callback during future pending consumption. Twenty authored scalar/foreign-hook cases cover allowed roots/owner directories and unsafe modes/types/owners. It returns five-field identity DATA only; actual native-return provenance, one-use consumption, work debit and ACK remain separate unimplemented requirements. No mode/provider/grant/job or host setting changes occur.

## Latched cohort preparation checkpoint — November 8

The unclaimed metadata-plan validator now delegates structural joins to a
separate helper and still requires an empty pending-consumer slot before its
original work-registration check. The new latched directory-resource helper
requires the original consumer in that slot, original operation/result links,
resource/site/ordinal, held descriptor chain and retained material closures.
It performs no phase transition, debit, actor sampling, native call or ACK.
Type checks precede primitive equality at the operation/site boundary.

This helper is preparation only: static checks passed; dedicated causal
latched-consumer tests and independent review remain required before wiring it.
Separately, frozen constructor repair source `cefd515` passed 12 cases on both
Python 3.14.9 and 3.11.15; policy source `d537500` passed 20 on each. These
results do not qualify this changed helper, an integrated dispatcher or devices.
