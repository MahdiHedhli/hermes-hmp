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
