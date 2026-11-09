## November 9 — shared cache-probe lifecycle implemented; image delivery not yet complete

The experimental HMP cache-probe engine now shares the existing admission, native stat/fstat producer, consumption, acknowledgement, caller-held custody and producer-unwound retirement machinery. Directory-consumer ownership stays closed; the probe uses a distinct fixed typed policy. Known missing-file reports contain no exception, errno or filename and are classified only around the literal native stat call. Current lifecycle checks run immediately before each native branch. These are local HMP implementation changes, not a demonstrated upstream Hermes blocker.

At source `d117656`, all 12 selected producer/lifetime/diagnostic checks pass on Python 3.14.9 with unchanged source. At `6755ffe`, all 15 selected shared-ACK interruption, origin-refusal and real missing/directory/declared traversal checks pass with zero failures/errors/skips and unchanged source. The ten interruption cases exercise actual shared ACK stores, preserve the acknowledged original and partial history/cursor without rollback or metered replay, retire raw payloads and close known reserved descriptors. The case formerly called lost-return interrupted immediately before return; it is not evidence of a return-event fault. Test-only successor `eb16eef` adds that separate return-event case. All 16 cases pass on Python 3.14.9 with unchanged source and zero failures/errors/skips. The return-event case does not claim native-call observation from the profiler disabled by its injected exception; independent original ledger/history/count assertions establish no metered replay.

The earlier 22-case directory/resource/cache suite passed on both Python 3.14.9 and 3.11.15 at parent `c981bc2`. Those results do not qualify the later shared producer/consume/ACK changes; the same compatibility selection still needs execution on the latest source. Source successor `9a247bb` adds an exact operation-type fence before resource inspection and a causal foreign-property regression case. Its 23-case existing directory/resource/cache plus shape-check selection is running; no result is claimed yet. Complete diagnostic/type/descriptor/final-seal qualification and actual observe-caller adoption remain open. The prototype is unwired and uninstalled. Full bot-character and host-local image delivery, service/resource bounds and physical/release qualification are not complete. Earlier initial green observer runs that swallowed assertions remain withdrawn; their corrected evidence is described in the historical checkpoints.

Deployment is separate: the recorded LLY520 update runs Hermes 0.23.0 (`0f0e96f`) and HMP `5ecd2ba`, with a graceful restart, verified installed files/listener/TLS, preserved configuration and device controls, and Hermes/Belac/School Bot ready. Lucas/Serenity retain their prior unavailable baseline. ColPanicM2 also has the separately verified HMP safety backport. These host receipts do not prove phone UI or this experimental image candidate. R3 local-media code was installed separately; that does not enable media access or qualify the unfinished character pipeline. No new host/device/grant/provider/model/job/release action occurred during this source/test work. The full roadmap goal remains active.

### Historical review checkpoints

# Fresh-probe complete engine prototype — not for installation

November 9, 2026. Source `f840da6`, direct-admission causal successor `eda8143`.
This branch is uninstalled and the legacy `observe` traversal is not switched.
The full feature and PS1-FP-NATIVE remain incomplete. This is local HMP work,
not an upstream Hermes capability blocker or a release candidate.

The prototype executes the complete original missing/directory/declared-regular
traversal with real native stat/fstat, ordered opened ancestors, final checks,
reserved closes and zero reads. Three positive GC-disabled fixtures pass on
Python 3.14.9. They do not qualify failure, lifetime, interruption or cleanup.
The initial known-raised representation must also be replaced: a diagnostic is
a distinct stable typed outcome, not returned-success or the common unknown bit.

Independent read-only review found blocking contracts. Direct causal tests use
the same normal `_start` admission now used by `observe`, then call the candidate
from an ordinary Python frame so nested fault tracing really executes. They do
not spoof owner flags, grant rights or bypass admission. At `eda8143`, the three
new controls fail as intended and two existing legacy missing/declared probes
pass. All runs bind unchanged source. Failed synthetic stages are retained
privately; no paths, exceptions, credentials or user content are published here.

| Contract | Observed or reviewed limitation |
| --- | --- |
| Current lifetime after actor sampling | Retiring continuation before the call still permits one stat; causal failure. |
| Producer-unwound memory retirement | Lost actual return retains one raw capsule; causal failure with GC disabled. |
| Known reserved cleanup | The same loss leaves one known ancestor unclosed because ended routing stays occupied; causal failure. |
| Wrong actor before publication | Refusal still publishes execution and poisons the ledger despite no debit; causal failure. |
| Partial ACK/late-finalizer seal | Source review found missing original ACK attempt and full final pure rejoin. |
| Exact type and descriptor proofs | Source review found nested reads/comparisons before closed shapes and incomplete original live parent/component/flag checks. |
| Foreign state and accounting | Failure must preserve foreign slots, own-ended routing must be retired conditionally, and final exact debit/reserve/byte/close accounting must be authoritative. |

## Required coherent correction

Factor one common lifecycle in `presentation_native_metadata` with closed typed
directory/probe projections, retaining DirectoryConsumer's existing owner scope.
Reuse the original factory/capsule, actor primitives, stat snapshot and reserved
open/close mechanisms. Extract the hardened admission, outcome, consumption,
partial ACK, caller-held producer-unwound retirement and late-callback seals;
do not copy another independent per-site dispatcher or accept caller callbacks.
The probe keeps its own branch policy, literal previous actual return and finish.
Site index is not execution-history length; missing confirmation is distinct.

Qualify retirement at the final actor boundary, wrong actor with zero publication,
producer/ACK return loss, interrupted ACK stores, foreign slot preservation,
late weak-reference mutation, wrong types with zero hooks, exact diagnostic
class/errno/name/subclass behavior, first/confirmation drift and close reserves.
Run actual missing/directory/declared and all existing probe regressions on both
supported interpreters. Only then switch the complete actual caller. Startup
before/after source effects, other policies/operations, service/resource bounds,
authenticated image transport, physical devices and release remain separate.

## Shared admission/retirement correction

`c981bc2` reuses the actual shared admission and caller-held original custody
retirement. Closed probe stages are rejoined to registered original function,
code, module and export identities before every invocation. Existing directory
owner/file/EOF policy remains separate. Actor preflight, pure current lifetime,
independently held opened descriptors and history/accounting checks were added.

The repaired selection has8 current passes at ee3edf0 and4 descendant guard
passes at c981bc2, independently audited; failing stage-code and scope-field
controls are preserved. The intermediary4case failure was a directory-only
postACK tail accidentally retained in the probe path; its fixed attached stage
now passes positive paths as well as refusal controls. Existing directory
compatibility22 passes on current and minimum Python, unchanged source; this
does not qualify later producer changes. No minimum/runtime/device qualification
or fullengine approval follows from these selected checks.

Shared native outcome, consumption and partial ACK handling remain incomplete.
Do not wire or install the probe while those and the full failure/finish/type/
descriptor causals remain unqualified. PS1-FP-NATIVE stays open.

The separate common-producer worktree has a canonical known-raised outcome and
one stat/fstat producer. Its initial broad classification handler failed two
causal controls; `c4b7930` isolates the literal native stat call and preserves
actual returned history on bookkeeping loss. Initial runtime12:11PASS/1retirementFAIL; d117656 restores final branch
lifetime closure outside classification. Corrected12 is running, unqualified.
Do not infer this source's qualification from the c981 parent compatibility.
