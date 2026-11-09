## November 8 — reviewed host updates deployed; character integration remains open

Paired media source qualification: backend `f7f5084` passes both 1,063-case
combined suites (Python 3.14.9 and 3.11.15), zero failures/errors/skips and unchanged
source. Mobile `5ca14a9` pinned to that backend passes 66 client and 73 app/chat/
accessibility tests; whole client/app analysis is clean. Private scan has no new
findings, retaining its existing 170 baseline exclusions. These are scoped source
checks, not full release review, rendered/device acceptance or live serving.
Performance/contention, legacy fallback and safe migration remain open. No install.

The repaired media backend `f7f5084` now passes its combined 1,063-case current
Python suite with zero failures/errors/skips and unchanged source. The matching
floor run is active. Focused backend branch `feat/media-read-entitlement-20261108`
and mobile branch `feat/media-readiness-mobile-20261108` are published. Mobile
integration commit `5ca14a9` pins that exact HMP commit for reproducible source
review; mobile tests against this new submodule pin remain to be rerun. No live
migration, grant, opt-in, build installation or release occurred. Performance,
legacy fallback, migration quiescence and runtime/device gates remain open.

Media freshness regressions now have isolated negative controls: restoring the
matching prior server implementations reproduces stale HTTP 200 responses where
503 is required. One initial mismatched callback-count case was excluded and rerun
against the correct intermediate source; its mutation then reached stale delivery.
Candidate `f7f5084` remains unchanged and its combined 1,063-case current-interpreter
run is active; no result or floor run is claimed yet. These controls establish
regression sensitivity, not atomic revocation, performance or release acceptance.

Independent review found final-callback and request-context freshness gaps in
undeployed media backend `fb82aef`, despite its passing 1,059-case integration run.
Source `f7f5084` repairs post-callback media checks, original request/dependency
cohort binding, clock ordering and final IID/listener-generation seals. Both
89-case readiness suites pass, including causal callback/context regressions;
independent re-review verified the identified defects resolved on exact f7f5084.
This is delta review only. Performance/contention, non-atomic source reads,
legacy fallback revocation, migration and runtime/device gates remain open.
No source-review or release clearance, grant, opt-in or deployment is claimed.

Mobile media independence repair `463c6bf` keeps image inspection available when
the separate jobs/model diagnostic fails, preserving scope/generation checks.
All 67 combined UI/chat tests and six large-text accessibility regressions pass;
focused analysis is clean. Independent review, backend final-check latency,
rendered/device acceptance and schema/deployment gates remain open. No new install.

Mobile media UI source `6485c25` adds independent image-access guidance to the
chat overview readiness panel, with no grant/Fix action. It distinguishes missing
image rights, disabled host opt-in and unavailable API; existing scope/refresh
fences discard late results after bot changes. Ten focused panel tests and 56
selected-bot/Bot Chat regressions pass; focused Flutter analysis is clean.
This completes the first source UI path, not review/runtime/physical qualification.
Independent review, backend final-check latency and schema/deployment gates remain;
no new build was installed and no live rights/settings changed.

Mobile media lifecycle source `0dcbbb4` binds discovery and bot diagnostics to
the captured foreground API and original pairing lifecycle scope. Switching during
either await cancels the result; late revocation affects only its original host.
All 52 focused media domain/API/context and existing AR1 context tests pass;
focused analysis has no issues. UI profile/request-generation binding, visible
image guidance, independent review and device qualification remain open.
No live host request, permission change, build installation or deployment occurred.

Mobile media API source `467e576` now reads discovery and per-bot diagnostics
through the existing pinned authenticated transport. Discovery-only 404/405 is
legacy unknown; malformed success is protocol unknown; bot 404 remains a refusal.
No alternate route, remote grant, or feature mutation is attempted. All 53 focused
Dart domain/media-wire/existing-AR1 tests pass and focused analysis has no issues.
Context lifecycle integration, UI, independent review and device qualification
remain open. This source is not built/installed/deployed.

Both 256-case media-readiness/contract/plugin-surface suites at `fb82aef` have
now passed, zero failures/errors/skips and unchanged source. Mobile branch
`feat/media-readiness-mobile-20261108` source `46bee41` adds strict content-free
discovery/readiness DTOs: 34 Dart tests pass and focused analysis reports no issues.
This is decoder-only progress; authenticated API transport, context lifecycle and
phone UI are not implemented yet. No device/build/deployment qualification claimed.

Media-readiness discovery is implemented at source `e1edd5f` through authenticated
`GET /media-readiness/capabilities`: protocol support only, explicitly no remote
permission writes. Its 85-case current-interpreter readiness suite passes.
Contract documentation at `fb82aef` defines closed DTO axes, older-host 404 fallback,
per-instance/device/profile lifecycle and remaining review/qualification gates.
The broader 256-case readiness/contract/plugin-surface run is in progress; no pass
is claimed for it yet. Mobile decoder/display remains unfinished, and no new
backend source or permission/schema change is deployed.

Media-readiness final-delivery source `bbd75f3` rechecks authenticated bot/session
scope after the worker await and compares the private permission revision before
removing that internal snapshot from the wire DTO. Post-worker deny/regrant,
listener-generation drift and bot revocation tests reject stale responses.
Both 84-case readiness suites pass on Python 3.14.9 and 3.11.15 with zero
failures/errors/skips and unchanged source. This final synchronous recheck can
perform SQLite/native configuration I/O; event-loop latency has not been qualified.
Independent security/performance review, capability negotiation, mobile wiring,
broader contract tests and physical acceptance remain open. No live deployment.

Media-readiness causal tests at `d41750f` now revoke media rights or bot access,
change listener generation, or change host opt-in inside a sampled callback.
All discard the snapshot without a media DTO or unrelated controls changes.
Both expanded 81-case suites pass with zero failures/errors/skips on Python
3.14.9 and 3.11.15, unchanged source. These are callback-drift proofs, not final
post-worker delivery/revocation qualification. Final delivery-fence review,
mobile wiring, route contract/capability negotiation and physical testing remain.

Media readiness source `701783e` now adds an authenticated, per-bot read-only
`GET /bots/{p}/media-readiness` route with separate rights/host/API axes and
no image-existence probe. Both 77-case readiness suites pass (Python 3.14.9
and 3.11.15; zero failures/errors/skips, unchanged source). Mobile wiring,
capability negotiation, independent review, broader route-contract coverage
and physical acceptance remain pending. No remote self-grant or live deployment.

Independent media-read entitlement backend is implemented on focused source
`1f39122` (not deployed). Store schema 4 adds explicit per-device allow/deny
with revision-fenced issuance/fetch and operator-only typed confirmation;
it does not grant approval-answer, jobs, models or bot membership. The integrated
797-case suite at `8c88920` passed on Python 3.14.9 and 3.11.15 with no failures,
errors or skips and unchanged source. Six additional operator interruption cases
cover cancel, listener nonce/generation drift, expiry, a concurrent decision and
lost acknowledgement; the resulting 15-case runtime suite passes on both versions.
Readiness/capability negotiation and mobile diagnostics remain unfinished.
No schema migration, media grant, host opt-in or device acceptance is claimed.
Deployment must drain the old process before schema migration; cold old-version
startup rejects schema 4, but an already-running old process is not stopped by
that check. Legacy approval-owner fallback remains unversioned: removal denies
fetch, but restoration can revive an old reference. Explicit media deny/regrant
is revision-fenced and does not revive old references. This legacy limitation
remains open; no universal revocation qualification is claimed.

Declared bytecode-cache reader work has advanced separately: frozen producer
`9d5e549` adds exact-type preflight and original-cohort cleanup, with three
malformed-field cases passing on both interpreters (3 each, no skips, unchanged
source and verified log/XML bindings). Descendant `6f84dee` integrates
a fixed buffer/hash/header and actual-EOF consumer plus caller ACK closure;
The 18-case cache-reader run on `6f84dee` finished 17 passing and one failing:
activation-owner drift was refused but its read claim had already been cleared.
The failed source/log/XML evidence is retained. Repair `8afe009` adds activation
owner/cell joins before publication; independent finite review found no new
blocker. Normal plus owner-drift cases passed on each Python version (2 each,
unchanged source, verified log/XML). Its 34-case suite, including partial-ACK
interruptions and prefix-wrapper retirement checks, passed on Python 3.14.9:
zero failures/errors/skips, unchanged source, source/receipt/log/XML rehashed.
The same 34-case suite also passed on Python 3.11.15, with zero failures/errors/
skips and unchanged source; source/receipt/log/XML bindings were independently
rehashed. Both runs qualify this cache-reader slice only. The separate floor
linear-read timeout remains open; no complete startup, six-operation, runtime/
service or physical qualification is claimed.

Separate unqualified metadata preparation `b63aed9` inventories all39 stat/fstat
sites and both missing-stat diagnostics, captures primitive stat DATA, allocates
lazy original declared-file site plans and retains the actual plan in its walk
handoff. Review corrected the plan to match final ancestor checks. Eleven focused
plan/caller cases passed on each supported Python version (11 each). Resource
`e593cde` passed five composed cases on each version, and operation preparation
`0884893` passed eight on each; all sources/receipt/log/XML bindings were rehashed.
These qualify preparation slices only. Directory-consumer preparation `bbf877d`
retains original scope/material/lifetime bindings and one-use result ownership;
nine focused cases passed on each interpreter. Subsequent causal constructor
mutation tests reproduced a missing final material-closure check on the control;
repair `cefd515` passed all12 cases on each interpreter. Each injected mutation
was refused before publication. Fixed directory-policy DATA source `d537500`
passed20 cases on each interpreter. Exact source/log/XML hashes were rechecked.
Latched-cohort preparation `a19560a` separates structural joins from unclaimed
admission; all14 dedicated cases passed on Python3.14.9 with unchanged source
and rehashed source/log/XML evidence. All14 also passed on Python3.11.15,
with source/log/XML hashes rechecked. Fixed ACTIVE-state guard `a131932` passed
all20 cases on Python3.14.9 with unchanged source and rehashed evidence; its
same20 cases also passed on Python3.11.15 with unchanged source and rehashed
source/log/XML evidence. Finite review found no new concrete defect after the
explicit phase/failure-slot checks. These remain guard-only passes.

Separate uninstalled directory producer `f47a1be` passed29 original intent/
admission/pending-return cases on each supported interpreter. Candidate
`8f12da7`, with production bytes unchanged from ACK source `520b08d`, then passed
all45 selected synthetic native/policy/ACK cases on each interpreter, including
10 source-store interruptions. Source/receipt/log/XML hashes were rechecked.
These component passes are not complete caller, runtime or device acceptance.

A new negative control on unchanged production `4072412` reproduced lost producer
return on both interpreters: the actual return-event fault fired, the caller
received no value, raw/envelope remained pending and the ledger was still healthy;
the one-unit charge remained. Each original test failed once as expected, with
exact private stage evidence rehashed. Those failures remain failures. Producer
finally alone does not establish caller receipt; current stored rows cannot be
adopted as returned receipts. The uninstalled candidate remains unqualified.

Directory custody migration `b6b8322` moved retained result/consumer raw-bearing
cells behind one detachable payload link. Its 58-case current-version regression
finished55 passing/3 failing, with no errors/skips and unchanged source. All
three failures reached the original60-second child deadline; no cause is yet
established. The failed source/receipt/log/XML evidence was rehashed and retained;
that candidate is not qualified and its floor lane did not start.

Successor `963b0a6` fixes reviewed state/equality and captured-cell ordering gaps,
captures actual cells before C, stores the raw return immediately, and rejoins
original lifecycle/material/native/budget state after custody callbacks. Its11
memory checks passed on each supported interpreter, including actual marker-
return cell replacement and GC-disabled synthetic reclamation. Its four fixed
producer cases also passed on each version, including revocation after custody
capture with zero observed callee c_call events and normal-case calibration.
These events are not kernel-entry receipts. Source/receipt/log/XML bindings were
rehashed. The full62-case selection then passed on Python3.14.9 with zero
failures/errors/skips, unchanged source and rehashed source/receipt/log/XML.
The same62 cases passed on Python3.11.15 too, with zero failures/errors/skips,
unchanged source and rehashed bindings. These qualify that selected source,
not the later caller or a complete runtime/feature.

Test-only `6d3a8cd`, with production identical to `b6b8322`, ran one original
timeout case with a private45-second stack sampler and unchanged60-second
deadline. It passed at26.093 seconds before sampling, leaving an empty stack
file. This supplies no timeout cause and does not erase the original failures.
A fresh static recheck of installed native source `ed1afb0` finds the public
`hermes-gateway-v1` session-authority contract (typed submissions/request IDs,
receipts, snapshots and mutation). This is a potential integration route, not
qualified HMP phone access: native transport ticket/actor authorization must be
mapped explicitly, and session attachment changes subscription/lifecycle state
rather than acting as a passive health read. Legacy peer sends generate a fresh
delivery key; contract presence alone does not resolve external message identity
or the duplicate-history bug. No live requests, grants or session operations
were performed. Independent read-only review confirms that the public runner
reference is not itself a device-authority issuer. No qualified per-device native
read/submit delegation route was identified in the inspected paths; this is not
proof the entire SDK lacks one or that upstream code changes are required.
Native authorize can also restore/mount cold sessions, so passive readiness must
not invoke it. See the current native session-authority source note.

Fixed-site DATA preparation `e285873` adds original row variants allocated with
the plan before descriptor acquisition. Structural role/op/component checks,
current resource and latched-consumer variant joins are source-reviewed, with
no new concrete DATA preparation blocker;19 plan tests now pass on each
supported interpreter, with unchanged source and source/log/XML hashes rechecked.
The tail is not full canonical-order or original-plan proof. Future fixed
callers must carry actual plan/variant returns across callbacks and bind all
predecessors/resources/actor/budget phases. No dispatcher, effect site or walker
finish-guard change is introduced; this code remains separate and uninstalled.

The next source draft `872e0fb` adds original-actor eligibility before caller
custody allocation/latching while retaining the later ACTIVE sample. Independent
source review found no new blocker. An unchanged-production cross-thread control
then failed on each interpreter: actual rejection and zero native calls still
changed preparation and metadata-progress state. Those failures remain failures.
The early-actor repair passed the same case on each interpreter with all nine
observed shared-state fields unchanged; it did not add effect authority. Uninstalled leaf-policy
preparation `d85d5d2` preserves declared regular-file type/owner/link/size/mode
checks in primitive DATA;23 tests pass on each supported interpreter, with
unchanged source and rehashed evidence. This proves selected policy checks,
not native-result/declaration provenance or admission. It
excludes anchor/configuration policies; actual leaf/ancestor consumers, original
mtime/hash/EOF checks, complete plan ACK progress and device/runtime integration
remain required. The refreshed39-site inventory matches all prior semantic
entries with current five-file hashes and diagnostic function locations checked.

The same source `e597dfe` subsequently passed the full71-case selected metadata,
memory and caller regression on each interpreter (71 each, no failures/errors/
skips, unchanged source and rehashed evidence). A separate test-only single-
interruption control `9808a93` then found pre-detach payload retention on both
interpreters; post-detach controls reclaimed it. Each control suite remains one
failure and one pass, not qualification. Corrected diagnostics reached actual
producer/native/arm/injection checkpoints exactly once, with GC disabled and
original debit/failed phase preserved; earlier missing-diagnostic refusals remain
inconclusive. Isolated repair `779312e` rechecks original actor and pre-effect
custody before a final conditional memory-only detach. Both before/after cases
now pass on each interpreter (2 each), with payload reclaimed and no invented
retirement/ACK marker. Lint and plugin-surface checks pass. The broader73-case
repair regression now passes on Python3.14.9 (zero failures/errors/skips,
unchanged source and every source/log/XML hash rechecked). The same73 cases
also passed on Python3.11.15 with zero failures/errors/skips, unchanged source
and all source/log/XML hashes rechecked. Independent repair review found no new blocker for the
single interruption. Four selected combined actual-caller cases on `cc9603e`
now pass on each interpreter: normal, wrong actor and before/after-detach
interruption, with unchanged source and rehashed evidence. The broader121-case
selected regression of that exact source now passes on Python3.14.9, with zero
failures/errors/skips, unchanged source and every source/log/XML hash rechecked.
The same121 cases also passed on Python3.11.15, with unchanged source and
source/log/XML bindings rehashed. Separate constructor controls on both versions
then reproduced accepted snapshot identity/mtime drift after an actual native
return. Those negative controls are retained as failures, not qualification.
Isolated repair `b2deb97` rejoins primitive returned fields to held native-derived
inputs before publication; independent finite review found no new blocker.
Separate identity-only and timestamp-only regressions plus normal/interrupted
caller cases now pass on both Python3.14.9 and3.11.15 (5 each, zero failures,
errors or skips, unchanged source and rehashed receipt/log/XML). All four causal
constructor checkpoints prove post-native refusal, no producer publication/ACK,
reclaimed payload with GC disabled and preserved original debit/failed state.
The121-case baseline did not cover this later constructor defect; its negative
controls remain retained and the repair has only the stated focused scope. Other isolation/
repeated-interruption cases, actual-site integration and physical/runtime
qualification remain open. The older73-case baseline does not cover the later
cross-thread preparation defect; the separate repair/control evidence above
must not be replaced by that passing baseline. This is not a completed image-delivery feature.

Separate caller source `e597dfe` has now passed13 memory cases and seven actual
synthetic native caller cases on each supported interpreter (20 each), with
zero failures/errors/skips, unchanged source and rehashed source/receipt/log/XML.
The caller holds actual factory custody before effects and actual producer/
policy/ACK returns. With cyclic GC disabled, tests verify owned capsule
reclamation for normal operation, actual lost producer return, revocation,
foreign public slot and copied inner marker. Late marker drift and a finalizer
revoking activation during disposal preserve the real ACK/cursor/debit while
failing the original operation; no native replay, refund or FD close is used.
The call counter observes callee c_call events, not kernel-entry receipts.

This handles the original lost-return counterexample in the isolated new caller;
the original failing control remains preserved. It does not prove interruption
at every store, wrong-actor cleanup, arbitrary foreign alias erasure, complete
retained-root graphs or real directory/site integration. The original timeout
cause remains unknown; no deadline was raised. These local implementation and
runtime/device gates stay open; no prototype is installed. An ordinary ledger-
field replacement finding was withdrawn after source verification showed the
fields are immutable named tuples; unneeded defensive code was reverted. No
runtime vulnerability or incident was established for that invalid example.
The [caller and repair contract](https://github.com/MahdiHedhli/hermes-hmp/blob/feat/startup-bytecode-headers-20261107/specs/046-bot-presentation-integration/NATIVE_METADATA_RESULT_CUSTODY.md)
and dated39-site inventory document the local work. Caller integration, all
metadata/tree/link/missing-stat sites, six operations plus enumeration, original
aggregate budgets/reserved cleanup, complete factory/service/key/runtime, the
open minimum-version timeout and physical character delivery remain unfinished.
No character-prototype activation, device/feature/release pass or observed
user-data exposure is claimed. This startup bytecode/character custody work is separate from the
reviewed host-local chat-image deployment, which the owner has now authorized
and which is installed separately as recorded below. Physical acceptance remains
open. No character prototype is represented as installed.

Source-specific leaf-before policy `4c6f33c` now preserves the actual snapshot's
`st_mtime` conversion: exact numeric types, strict64-bit bounds and integer
truncation toward zero, including pre-epoch fractions; nanoseconds are not used
as a replacement. Forty focused leaf/timestamp DATA cases pass on each supported
interpreter, unchanged source and receipt/log/XML rehashed. Independent policy
review found no new blocker; its source-only scope is explicit, so cache or
non-source reads do not gain a new timestamp requirement. This remains a
prerequisite for the shared fixed-site consumer, not native admission or a
completed walker. Fresh static inspection of installed Hermes0.23.0/0f0e96fc
still finds the unbounded native avatar getter; no qualified safe shortcut was
established, no getter was called and no upstream change was made.

The shared metadata engine now retains original raw-free ACK history in
`c82a97a`: one predecessor link per consumer, original attempt/result/consumer
joins, exact ordinal fences before indexing, and another join after material/
native closure. Its33 selected cases pass on each supported interpreter with
unchanged source, receipt/log/XML and six actual-result checkpoints rehashed.
The after-append/before-cursor interruption keeps partial history, the old
cursor, sticky failure and original debit; payload is reclaimed with GC disabled.
The initial `b7df9ef` run remains30 cases with27 passes/3 fixture failures (an
attached-payload assertion after retirement), not relabeled passing. Its source
review also found type-order and copied-prefix storage problems corrected by
`c82a97a`. Retained predecessor references are linear; full-chain audit CPU and
the separate minimum-version timeout are not qualified by this statement.
Three additional two-directory causal cases on test-only `9a96111` (production
unchanged from `c82a97a`) pass on both Python3.14.9 and3.11.15 (3 each). Sources
were unchanged; receipt/log/XML and all six causal checkpoints were rehashed.
They retain real first/second ACKs without test refunds or history rearming, and
copied or missing history blocks the second metadata C call/debit. The old walker
stays refused intentionally. This is not a complete leaf/ancestor or runtime pass.
See the [ACK history contract](https://github.com/MahdiHedhli/hermes-hmp/blob/feat/startup-bytecode-headers-20261107/specs/046-bot-presentation-integration/NATIVE_METADATA_ACK_HISTORY.md).

LLY520's R3 installation does not opt into image access: a fresh read-only
single-leaf check found its local-media flag absent/off and no configured
approval-owner list. Jobs/model controls do not grant that role. No flag, owner
role or device grant was changed. [LM-ENT1](https://github.com/MahdiHedhli/hermes-hmp/blob/feat/startup-bytecode-headers-20261107/specs/011-local-image-serving/MEDIA_READ_ENTITLEMENT_PLAN.md)
records a reviewed HMP-owned proposal for a separate default-deny media-read
permission, preserving existing owner-only fallback and all bot/image bounds.
Its proposed operator commands are not implemented; no live opt-in is implied.
Approval authority must not be granted merely as an image-access shortcut.

Open-registration source `1aa605d` passed all 1,434 configured startup cases on
Python 3.14.9 with zero failures, errors or skips; its eight focused cases passed
on both Python 3.14.9 and 3.11.15. Exact source/receipt/log/XML bindings were
verified. Earlier `77ae4dc` retains its separate 1,426-case pass and 183 focused
passes on each interpreter. The original `9e6f02a` failed run remains preserved.

Later coupled open/close source `5439fee` finished its 412-case focused run:
400 passed and 12 failed, with no errors/skips and unchanged source. Source,
receipt, log and XML bindings were rechecked. Eleven positive cases hit the
existing 60-second child deadline; one failed a close-ACK assertion. Diagnosis
continues without extending the deadline or relabeling failures as passing.
Unrun intermediate queues were consolidated into this descendant only after
ancestry and selected-case coverage checks; no active test was interrupted and
no unrun candidate is claimed passing. Its floor and full regression runs depend
on resolving the focused failures. No complete native IO/cleanup/quota/runtime
or device qualification is claimed.

Separate uninstalled source `9dc2875` finished its 68-case reader selection:
38 passed and 30 failed. Its first normal-case refusal was traced using only
synthetic guard function/line metadata: the caller passed an entire five-part
walk receipt instead of its original plan. Successor `2312e0b` corrects that join
and the optimistic close-status mirror without weakening the original-ledger
validator. The first 14 focused cases passed on Python 3.14.9. The repaired source then
passed all 130 selected read/close cases on that interpreter with zero failures,
errors or skips and unchanged source. Actual source, receipt, log and XML hashes
were rechecked. Python 3.11.15 then finished 129 passing and one failure: the
synthetic source-digest `linear_reads` child exceeded its existing 60-second
deadline. Source was unchanged; receipt/log/XML bindings were verified. This
floor suite is not qualified. Test-only `daf6350` prepares a 45-second bounded
stack diagnostic without changing the deadline. It reproduced the timeout,
but the parent did not persist child output. Test-only `ca2ea03` repairs private
raw-output persistence and adds two failure-preservation checks; all three
isolated cases passed, with the linear case at58.038 seconds. A further test-only
`01b586c` saved a private45-second stack even on success and passed at59.128s.
The sample shows repeated parent-package descriptor-history validation during
entry-file completion, not proof of an exclusive cause. Review found no safe
direct audit deletion across callback/import boundaries. The original timeouts
remain preserved; no deadline extension, weakened test or full floor pass is
claimed.
The original failures remain preserved, not relabeled passing; no complete
startup, six-operation, runtime/service or device/image qualification is claimed.

Corrected isolated EOF source `708beff` passed29 cases on each Python3.14.9 and
3.11.15 with zero failures/errors/skips and unchanged source; all bindings were
rechecked. Its original `7a4d42f`26-pass/3-failure fixture run remains preserved.
Cleanup diagnostic `b3115ee` passed its two mock evidence tests but still failed
the normal60-second timeout and close-status check. The latter now passes on
2312e0b; the profiling timeout cause is still unresolved. No deadline was raised.
The unstarted repeat on test-only3102341 was deferred before any child ran,
allowing source diagnosis first; no active test was interrupted.

Host-local media and desktop characters have separate source paths. Reviewed
local-media package `5e247a6` plus client source `56d517c` do not depend on the
unfinished character-source admission stack. After explicit owner approval,
ColPanicM2 received the exact reviewed109-file HMP package and a single native
graceful restart. Its new gateway retains native0.22.7/ed1afb0 and three profiles;
TLS identity and send/jobs/model readiness checks pass. LLY520 completed its
native0.23.0/0f0e96fc update, then received the same reviewed HMP package and a
supported graceful restart. Five profiles remain served; Belac/default/School Bot
channels are ready, while Lucas/Serenity retain their prior unavailable status.
LLY520 configuration and paired-device/control fingerprints are unchanged across
the HMP install/restart. Compatibility checks report local-media availability;
no actual phone image-display pass or per-device/API execution is claimed.
Existing paired-device legacy controls-decision warnings are retained for a
separate access review; no grants were changed. Character factory/runtime admission, remaining cache/metadata/link/
diagnostic integration and enumeration are still unfinished. Separate source
486bf04 prepares original cache journal joins and transient head handling; its
new helper is unused DATA validation. The actual cache producer, fixed consumer,
header/EOF acknowledgment and causal tests remain to implement.

Device-local sections/static icons and selected-bot readiness are implemented in
app source, with physical qualification pending. Desktop character parity and
host-local image delivery remain unfinished. No upstream prerequisite has been
established for the remaining HMP integration. Public integrated code remains
`34b862e` for the unfinished character work; the separate R3 image package
deployment above does not qualify that stack. The connected iPad
still refused automated launch as locked; no launch/crash acceptance is claimed.
# BI1 integration tasks

## Native interface reuse audit

- [x] Inspect exact Desktop asset reader and canonical roster; record why neither
      establishes HMP-safe asset delivery. See [audit](NATIVE_AVATAR_INTERFACE_AUDIT.md).
- [ ] Finish actual runtime/native acceptance and physical avatar delivery; no
      legacy Desktop RPC bypass or source-helper completion claim.

## Executable leaf-link integration

- [x] **GR2-LINKS-L1** Explicit recipe2/interpreter2 document loader under original immutable version/root/IO/counter ownership, no detection/fallback/retry; D1 rejects recipe2 before artifact acquisition. Bounded independent source review accepted. This loads pinned DATA only.
- [x] **GR2-LINKS-L2** Decode/retain the closed selected interpreter link plan against original entry/runtime bindings, canonical target/UID/executable-mode constraints and raw/normalized path policy. Preserve stricter pins during deduplication and reserve both text observations in the original limits. Independent source review accepted the plan boundary; actual completion is tracked separately in L3.
- [x] **GR2-LINKS-L3** Retain descriptor-relative leaf-link observations before/after target hashing through the SAME original aggregate IO owner, charge both actual readlink observations, and verify the complete real-link/target refusal matrix. Hardlinks/ancestor links remain refused.
- [ ] **GR2-LINKS-L4** Actual installed runtime/loader and native/key/broker/physical character delivery; no source snapshot substitutes for acceptance.

See [selected executable link contract](EXECUTABLE_LINK_SNAPSHOT.md). All four belong to the existing character-delivery goal; L1 does not close GR2 or qualify a symlink.

## Fixed startup factory implementation order

See [fixed startup factory contract](GATEWAY_STARTUP_FACTORY.md).

- [x] **PS1-ANCHOR** Freeze trusted installer/entry root selection and implement
      independent private approval-anchor loader, avoiding circular hash approval.
      Source/review and original-prefix composed tests complete; see OPERATOR_APPROVAL.md.
- [x] **PS1-CONTINUATION-DATA** Retain original completed startup lineage before
      native imports, with sticky refusal and callback identity fences. See
      [contract](STARTUP_CONTINUATION.md). This does not complete PS1-LOADER.
- [x] **PS1-BYTECODE-HEADER-DATA** Observe selected headers during original hashing
      and classify against original interpreter magic without execution or extra IO.
      See [scope and remaining gates](BYTECODE_HEADERS.md); not runtime admission.
- [x] **PS1-CACHE-PATH-DATA** Implement/review complete supported POSIX source-cache
      location mapping, including CPython root/CWD edge. See [scope](CACHE_CANDIDATES.md).
      Actual original pre-IO context and cache/absence observations remain open.
- [x] **PS1-CACHE-CONTEXT** Retain original entry/recipe/plugin/interpreter and required
      CWD on the fixed snapshot inputs before artifact IO allocation; preserve the
      actual fact through continuation. [Context DATA only](CACHE_CONTEXT.md).
- [x] **PS1-CACHE-OBSERVE** Reserve and observe declared caches plus unresolved
      no-follow absence probes in the same original aggregate owner before completion.
      Never infer loose-cache absence or extend a completed owner.
      Original-owner loose absence source and sidecar are implemented;
      [verification scope](CACHE_OBSERVATIONS.md) remains separately tracked.
- [x] **PS1-SOURCE-DIGEST** Compute original source digests in the existing prefix/
      pending file reads and consume exact immutable facts through continuation.
      [Implementation and remaining qualification](SOURCE_DIGESTS.md); not cache
      equivalence or runtime admission.
- [x] **PS1-CACHE-INPUT-RULES** Capture original source timestamp and implement/review
      supported source-loader input-attempt rules.60 current and52 actual floor
      child cases pass; [scope](SOURCE_CACHE_INPUTS.md), not runtime admission.
- [x] **PS1-CACHE-INPUT-BIND** Bind actual original source/cache receipts and
      absence/nonfile observations under original mode/magic/location before
      any runtime use; reseal held allocations after callbacks. See
      [implementation and runtime limits](SOURCE_CACHE_INPUTS.md).
- [x] **PS1-RUNTIME-SOURCE-READ** Fresh original-continuation source phase with
      independent IO/read-effect budget, final content seal and original-buffer
      cleanup. Implementation and bounded source review accepted;130 focused
      reader/scanner checks and15 actual floor child cases passed;1162 unchanged
      startup checks passed. Fixture-only line wrap preserves script AST and
      passes one current/two floor rechecks plus full lint. Linux CI pending.
      [Contract and runtime limits](RUNTIME_SOURCE_READ.md).
- [x] **PS1-SOURCE-COMPILATION** Capture original actual compiler resolution and
      own one native source compilation without execution. Isolated implementation
      and bounded source review accepted;37 current matrix cases plus stronger
      parity/syntax checks pass.38 actual floor children and1185 unchanged-source
      startup regressions pass; Linux/operational qualification remains separate. [Contract and limits](SOURCE_COMPILATION_CONTRACT.md).
- [x] **PS1-CACHE-DECODE-ORIGIN** Hold original native marshal/fixer and frozen
      helper origins; refuse substitutions before dispatch.17 current and17
      actual floor cases and1202 unchanged-source shared-startup cases pass;
      bounded review accepted; this is not owned decoding or execution.
      [Contract and limits](RUNTIME_CACHE_INPUT_CONTRACT.md).
- [x] **PS1-CACHE-METADATA-PROBE** Fresh no-follow original-row diagnostic probe,
      with bounded review;11 current/11 actual floor cases,122 scanner checks,
      and1,220 unchanged-source startup cases passed. Five later cleanup fault
      cases passed on both actual interpreters. No payload/fallback authority.
- [ ] **PS1-RUNTIME-CACHE-IO** Fresh original-row diagnostic metadata probe is
      implemented with bounded independent source acceptance;11 current and11
      actual floor child cases pass.1220 unchanged-source startup checks passed. Cache
      payload IO, typed failure/effect provenance and fallback authority remain
      incomplete. See [probe scope](RUNTIME_CACHE_PROBE.md).
- [x] **PS1-DECLARED-CACHE-READ** Original declared-row byte reader implemented
      in an isolated branch, with independent bounded source acceptance after
      effect/claim custody repairs.141 current checks (14 reader,127 scanner) and14
      actual floor child cases and1,244 unchanged-source startup checks passed.
      Source-only phase complete; operational resource qualification remains open. This does
      not cover known native unavailability, source fallback or code decoding.
      [Contract and review limits](DECLARED_CACHE_READ.md).
- [ ] **PS1-SELECTED-CACHE-DECODE** Implement fixed actual-successful-reader-only
      native decode/fixer custody with recomputed original selection evidence,
      ephemeral payload handling and historical effect facts. Independent bounded
      contract and source review accepted this separate increment; 19 current and 19
      actual floor causal cases passed. Combined broader tests remain pending.
      Known-unavailability/fallback and operational resource gates stay open. [Contract and exact limits](OWNED_CACHE_DECODE.md).
- [ ] **PS1-NATIVE-FILE-MACHINERY** Retain original observed POSIX C bindings,
      aliases, flags and result/error classes at interpreter entry. Metadata-only
      implementation has bounded source acceptance; 17 current and 17 actual floor
      cases passed with verified receipt/source binding. Combined startup pending.
      Actual typed outcomes, audit/ABI/resource policy and fallback stay open.
      [Exact scope](NATIVE_FILE_IO_ORIGIN.md).
- [ ] **PS1-LOADER** Enforce actual platform runtime/current and future import policy;
      snapshot DATA cannot mint startup admission.
      Next reviewed executable slice: original source-hash builtin/key/machinery,
      same-read temporary buffer/counter ownership, timestamp/hash cache selection
      and fallback enforcement consumed at fixed runtime boundaries. See
      [exact implementation requirements](LOADER_POLICY_IMPLEMENTATION.md).
      Archive members, ABI/library closure and full runtime admission stay open.
- [ ] **PS1-LISTENER** Bind original admitted startup to actual listener/native owner,
      with fixed currentness methods and explicit PresentationNativeService wiring.
- [ ] **PS1-KEYS** Acquire only the gateway role key after those joins; broker and
      terminal/ACK/PRE_EMIT remain separate acceptance tasks.

## Installed-startup and native acceptance critical path

See [paired startup composition](PAIRED_STARTUP_COMPOSITION.md). These are HMP
implementation tasks, not an established upstream Hermes blocker.

- [x] PS1 observation prerequisite: retain original early bootstrap/PM/import-origin
      DATA with no selection query, sticky partial ownership and callback/late-import
      fences;25 isolated synthetic cases plus308 layout/import checks pass.
      This does not complete PS1 admission/native composition.
- [x] PS1 selected-file observation prerequisite: bounded original-context descriptor
      ownership, no-follow traversal, actual bytes/hash/metadata and one-close cleanup;
     18 file cases +25 activation +309 layout/import checks pass (352 total).
      Expected-file tuples are not approved configuration or complete inventory.
- [x] PS1 private-file loader prerequisite: fixed filename/modes/canonical schema,
      independently expected bytes, original buffer/root fact ownership and late-load
      refusal;30 config cases plus shared artifact/activation/import checks pass (383).
      Loaded configuration is DATA, not trusted-entry/operator approval.
- [x] PS1 HMP-package snapshot prerequisite: pinned full table, unexpected-entry
      refusal, all-file hashes, original file/directory/ancestor metadata and loaded
      HMP-origin consistency;19 cases plus startup/import coverage pass (403 total).
      This is not the complete gateway runtime/dependency/loader admission recipe.
- [ ] GR1–GR3: implement the [complete versioned gateway recipe](GATEWAY_RECIPE.md),
      original child pins/entry/runtime coverage and actual native/key composition.
      Existing schema1 package snapshots cannot satisfy this gate.
- [ ] PS1 configuration/inventory join: fixed trusted entry/operator approval of loader inputs,
      independent expected roots/bytes, complete reachable tree and unexpected-file,
      future-import/extension/OS-loader validation before native/key composition.
- [ ] PS1: original gateway startup owner, actual activated PM generation/HMP
      entry binding, native observation/drain composition and gateway-only key custody.
- [ ] PS2: independently selected isolated broker runtime/parser/worker and
      manager/reaper ownership, broker-only keys closed before worker creation.
- [ ] PS3: exact original role/channel/handshake binding and revocation preserving
      local cleanup debt; no caller-provided qualification flag.
- [ ] PS4: original normal native terminal acceptance, DRAIN, signed counted ACK,
      original controller acceptance, distinct journal/native credit release and
      fresh PRE_EMIT before authenticated candidate publication.
- [ ] PS5: cleanup/ABORTED/earlier terminal variants and actual Linux/Darwin runtime,
      installation, physical and release qualification, each with its own evidence.

## Current envelope stop preparation

- [x] Reseal completed normal correlation DATA through original fact/allocation,
      canonical original terminal bytes and current actor/key/custody before consumer use.

- [x] Add pre-adoption original-task normal terminal DATA reception, owned readiness,
      original parser/credit provenance, candidate withdrawal and I/O-debt preservation.
- [ ] Complete native terminal acceptance, signed ACK and native resource release;
      qualify trusted runtime and physical character display separately.

- [x] Add separate bounded RESULT/result2-body digest DATA from the actual fresh
      frame or captured original native hash copy, preserving frozen native and
      original full-frame digests; sanitized feed refusals and source-drift checks.
- [x] Correlate completed-RESULT TERMINAL/2 DATA against actual original input,
      profile/operation, generation/domain and retained RESULT-body digest;
      original-actor admission and final held-cell refusal causals are covered.
- [x] Publish signed sender cleanup stamp only as a minimum on the original
      native budget after current correlation; reject future/expired continuation,
      wrong actor and lost/drifted publication without renewal, restore or replay.
- [x] Join normal signed RESULT counted transfer after payload withdrawal with
      the actual original native local closure observation/input in LocalStartedProducer;
      independent payload-hash/scope/count refusal and withdrawal causals are covered.
- [x] Freeze original normal signed producer handoff and prepare a one-shot
      signed TERMINAL/2 envelope from current original broker role/context; enforce
      exact handoff body, wrong-actor/no-retry and late cause/key/scope refusal.
- [x] Qualify normal AVATAR and METADATA export/counting in the native synthetic
      fixture, retaining same socket/task/budget and fixed signed-result write-slot
      ownership; cover short/zero/EAGAIN/lost-ack/cause/current-owner drift refusals.
- [ ] Explain expanded-run stopped-reader nextfeedrows first-frame refusal;
      isolated/related green runs do not prove its cause or remove that gate.
- [ ] Qualify trusted runtime/startup, cleanup-time/aborted exporters, remote
      acceptance, earlier/direct terminal positions, EAGAIN waiting, lifecycle,
      original control-reader ACK and native release before production routing.

- [x] Separate historical native wake/custody binding from the existing strict
      frozen digest wrappers; actual3-byte original-digest advancement preserves
      binding but refuses old currentness/release and retains UNKNOWN/counts.
      No authority path switches to weaker binding-only helpers.

- [x] Qualify one bounded original-task/socket native receive with post-clock fixed
      FD/mode probes, final metadata/I/O claim fences, independent native-count and
      pending-byte ownership, fixed cleanup observer and work-exit pending retirement.
      No parser/feed/hash/frame credit, readiness continuation or cooperative route.
- [x] Causally verify raw same-parser feed cannot reuse frozen stopped-reader
      proof: actual received8-byte prefix, unknown refusal, retained native count
      and dropped pending aliases. Independent read-only review accepted; no handoff.
- [x] Consume one actual native pending allocation on its original work actor into
      the SAME bound authentication parser or original body digest. Independent
      pre-boundary attempt/progress cells, irreversible consumption, fixed cleanup
      observer, postcallback currentness and no replay; reviewed one-shot slice.
- [x] Continue immediate nonblocking exact-needed reads on the original reader;
      original flags unchanged, one current step/ledger, actual syscall-attempt /
      received / parsed accounting, no linked history, record-boundary refusal.
- [ ] Qualify waiting after EAGAIN with fresh owned registration/retirement under
      the original actor/deadline; never reuse the retired selector registration.
- [x] Verify the completed original auth record once, with independently retained
      attempt/result, finished-parser continuity, held pre-crypto counts and post-
      callback native/role/alias seals. Positive RESULT and nine refusal causals.
- [x] Parse bounded committed RESULT/TERMINAL frame DATA from header prefix through
      exact full digest; no auth replay, RESULT buffer or terminal claim authority.
      Independently anchored header/digest/hash, bounded metadata transfer and25
      positive/refusal cases; native binding below remains required.
- [x] Bind newly completed authentication to one original-reader RESULT/1 or
      TERMINAL/1 frame stage; fixed parser dispatch, actual allocation continuity,
      cumulative counts and eight synthetic positive/refusal causals. DATA only.
- [x] Admit captured-complete authentication plus retained outer header without
      new auth-byte receive/consume credit, parser reset or fabricated progress;
      exact original allocations, zero seed, cleanup observer/work-exit binding,
      actual four-byte retained header RESULT path and five refusal causals.
- [x] Complete an originally partial body using its SAME original digest; exact
      original progress/stream/hash joins, retained finish/result and frozen counts,
      finished-state observer and ten synthetic positive/refusal cases. Consistency
      only; the new-frame parser is not substituted for this original digest.
- [x] Advance actual completed RESULT/1 into a distinct TERMINAL/2 authentication
      record on the same task/socket, with cumulative counts, current predecessor
      seals and bounded step retirement; both full-frame/partial-body predecessors.
      Thirteen new private-socket cases; authentication DATA only.
- [x] Read the next authenticated TERMINAL/2 frame/body and verify its full hash
      on the same native reader, separately retained parser/counters and bounded
      metadata, including both original RESULT completion paths. Consistency only.
- [ ] Qualify terminal domain claim and inherited cleanup end, keeping direct/
      earlier terminal lifecycle positions separate. No auth restart/fallback or
      captured-prefix byte credit.
- [ ] Explain the pre-terminal-frame auth acquisition refusal observed in the
      constructor causal's first grouped run; retain original250ms budget/guards
      and distinguish the later isolated pass from root-cause evidence.

- [x] Retain one-shot original-reader IDLE admission before native currentness;
      independently anchor owner/scope/fact, exact bounded count/original minimum
      end, malformed metadata refusal, partial attribution and held-original failure.
- [ ] Qualify active digest/framing handoff and native receive progress separately
      from IDLE admission; keep original stopped-validator and signing gates intact.

- [x] Retain original stopped authentication parser/outer-header framing or SAME
      partial-body digest, with independent parser/state allocations before effects
      and postcallback currentness. Exact-type replacement and partial-init refusal.
- [x] Authenticate early TERMINAL sequence data against retained expected sequence;
      RESULT only1, TERMINAL exact0..2. Lifecycle/ABORTED claim admission remains open.
- [ ] Qualify native receive/registration and exact next-byte accounting on this
      original bound reader, without enabling concurrent signing or publication.

- [x] Add fixed original-reader post-notification stop-currentness validation,
      repeating actual Future/fact/cursor/role/actor seals after native callbacks.
      Data only; exact parser/digest admission and receive ownership remain open.

- [x] Retain one bounded partial cleanup authentication record through exact-needed
      reads; fixed signed phase consistency, no overread/restart, permanent refusal.
      Component data only, with independent read-only review and focused causals.

- [x] Authenticate broker RESULT/1 or TERMINAL/0..2 at the retained expected sequence;
      closed context and signature, no fallback. Independent read-only review passed.
- [ ] Bind boundary dispatch to original native cursor/transition and validate direct
      ABORTED terminal body; this helper alone grants no lifecycle or read permission.

- [x] Retain payload-free original pre-await envelope waiter/Future/scope/deadline
      and byte counters through actual Task-cancellation validation and historical
      release; reject paired Future substitution after immediate wait checks.
- [x] Wire the actual native cleanup-cause wake into envelope waits with distinct
      typed current/historical stop receipts and frozen signed capture correlation.
      Independent read-only review accepted the bounded local-stop implementation.
- [x] Implement/review bounded signed RESULT discard DATA continuation from partial
      authentication/header or SAME supplied partial-body digest; no body retention,
      scanning or runtime read authority. Parser/digest allocation binding is retained;
      native receive ownership remains open.
- [x] Implement/review disabled signed reservation preflight from actual registered
      envelope/partial-body wait, original write-quiescence/current role/frozen
      budget and post-cause custody. Request still False; no suppression/read grant.
- [x] Implement/review original-work one-shot signed stop notice, with actual Future
      and fact allocation cells, native partial initialization/dispatch uncertainty,
      correlated stop/current role/earliest-budget seals and no publication retry.
      Stop-data consumers exist; no receive/signing authority or cooperative route is enabled.
- [x] Verify actual broker parked-CANCEL expiry under the original250ms timeout:
      receipt retained, late consumption refused, frozen end unchanged, no credit/
      closure. Controlled causal does not resolve earlier broad broker failures.
- [ ] Diagnose original broad-suite broker cancellation failures from actual
      bounded state/underlying-task evidence; passing reruns are not resolution.
      November7 broad failures include go_relay control-read refusal/closeFalse
      and body_adopt_capture_phase cancellation-adoption refusal. Both remain
      unqualified despite passing isolated reruns; primitive diagnostics retained.
- [x] Add/review fixed original-cleanup current stop-DATA validation and bounded
      original notice/work wait with actual Future/task dispatch fences. Separate
      sender/receiver actors; actual live/completed-work and partial-body causals.
      No read-admission, concurrent CANCEL, legacy fact or work-join relaxation.
- [ ] Qualify distinct signed request reservation and original-work read-ready
      notice, with current frozen budget/quiescence/role checks; no legacy fact or
      fabricated work-join substitution. See [integration contract](SIGNED_CLEANUP_HANDOFF.md).
- [ ] Qualify signed cooperative cursor transfer/drain and terminal/ACK against
      the same original capture/budget; no whole-work-join relaxation is enabled.

See [bounded source checkpoint](../../docs/research/presentation-envelope-wait-hold-2026-11-06.md).

## Current credential direction

The independently reviewed local role-credential contract supersedes the
unfinished Mach production-admission tasks below. Those dated tasks remain
historical, not an alternative live authorization path or resolved incident.

- [x] Implement and independently review data-only HBA1 codec, four-record signed
      transcript consistency and original input3 scope binding (`7c37b4f`).
      Root ran 167 focused tests; independent review was source/test read-only.
- [x] Implement/review data-only signed phase/body checks (`46c697c`) and
      startup-only role key-file acquisition/retirement (`33beebe`), with no
      signer or runtime permission. Root's expanded focused suite passed 213.
- [x] Implement/review the retained original-task handshake and external channel
      IO/close claim, with synthetic socket tests and 452-pass/one-skip focused
      regression. Native qualification is mocked in the actor tests; no production
      factory or phase/native permission follows.
- [x] Implement/review the one-attempt original native-input correlation join,
      with actual policy-thread/shared-slot model, final-current refusal causals
      and 640-pass/one-skip affected regression. This grants no phase authority.
- [x] Implement/review bounded data-only full-frame streaming digest, all seven
      phase bodies/max result and one-shot/drift/thread refusal cases; expanded
      affected regression 658 passed, one skipped. This is not cursor/native authority.
- [x] Implement/review original work-task no-IO BEGIN intent reservation after
      actual PRE_GO; caller/duplicate/intent/no-write assertions retained and
      affected regression 928 passed, one skipped.
- [x] Implement/review the fixed BEGIN work-role signing producer in the caller/start-barrier
      gap, preserving original work allocation and the SAME reserved intent.
      Final affected regression: 940 passed, one skipped; no transport/GO activation.
      See [actual task/producer contract](PHASE_WORK_OWNER.md).
- [x] Implement/review fixed BEGIN unadopted signed-claim staging and complete
      input3/frame/hash/scope/deadline data checks. Affected regression: 956 passed,
      one skipped. No broker cursor/native-adoption authority follows.
- [x] Implement/review the standalone original broker signed-record/read cursor
      and current role context, actual bounded socket reads and safe failure cleanup.
      Affected regression: 967 passed, one skipped. No native input adoption.
- [x] Implement/review original service connection/registry one-attempt queue and
      input-receipt adoption, current receiver revalidation and sticky late failure.
      Expanded affected regression: 1,099 passed, one skipped; no resources/GO.
- [x] Implement/review the original adopted connection's queued-current owner,
      original input/budget/grammar references, key/task/socket/work-end checks
      and callback-boundary refusal tests; 1,114 affected passed, one skipped.
      No resource or GO permission is minted; partial owner is retained on failure.
- [x] Refuse legacy direct GO/CANCEL/result IO on credential channels before native
      claims; preserve known-refusal grammar/budget and original controller task.
      Affected regression: 1,116 passed, one skipped. No signed control activation.
- [x] Review the fixed original [signed control handoff contract](SIGNED_CONTROL_OWNER.md).
- [x] Implement/review the no-IO original controller allocation/key-context
      preparation handoff, with work guards hard-closed and partial objects retained.
      Affected regression: 1,120 passed, one skipped. This is NOT a signed reader.
- [x] Implement/review role-material checks on the actual controller reader Task,
      original control scope and callback-safe reference seals, without borrowing
      creator authority. 1,123 affected passed, one skipped; no phase/IO permission.
- [x] Implement/review the original-task first signed control frame cursor, with
      signature/header/body/scope validation, callback-safe byte custody and no
      native receipt/grammar/window/resource effects. Full lifecycle remains below.
- [x] Implement/review original signed pre-GO CANCEL-to-native grammar/budget/receipt
      and owned local controller park/stop; 1,151 affected passed, one skipped;
      final focused55 includes unusable post-notification failure. This does not
      integrate ordinary service receipt consumers or release native debt.
- [x] Implement/review the dedicated original-service receipt validator/consumer without
      relaxing generic credential work guards; reject stale/revoked/late failures.
- [x] Implement/review authenticated GO read/native receipt followed by one signed
      CANCELseq2 on the SAME original controller cursor under original work time;
      pre-GO CANCELseq1 remains supported. Modeled READY is not resource qualification.
- [x] Implement/review authenticated cleanup-time control under the original earliest
      budget, including partial auth/header/body expiry and original cause retention.
- [x] Implement/review fixed signing-only READY producer from actual independently
      started/staged fixture resources and native completed-input write observation.
      1,262 affected passed, one skipped; no socket/grammar/resource admission grant.
- [x] Repair CI736 fixture cause/GO ordering without changing protocol deadlines;
      prior exact-source failures remain recorded; exact replacement `22bc509`
      passed CI738 plugin and Python 3.12/3.13/3.14 Unicode jobs.
- [x] Implement/review original-task write-slot readiness with immutable direction,
      opposite-reader preservation and one-shot initialization/debt retention.
      This notification primitive sends no READY bytes and grants no protocol phase.
- [x] Implement/review actual fixed signed READY write from retained original resource/
      input facts, one write/grammar intent and original completion-Future allocation.
      Same-reader GO joins that exact completion; production startup and worker relay
      remain closed. See [write evidence and limits](../../docs/research/presentation-signed-ready-write-2026-11-06.md).
- [x] Implement/review source signed GO/CANCEL receiver/context on the existing original
      controller task/cursor and frozen budget before any credential resource/READY
      startup. No legacy fallback, new parser task or boolean gate opening.
      Source fixture acceptance does not qualify signed READY/resources or production startup.
- [x] Implement/review cancellation-only local retirement for the original signed
      control read's exact positively retired readiness wait, with original held
      task/cursor/count/buffer/wake/Future/handle binding and no authenticated completion.
      Historical closure requires actual original Task.done+cancelled. Unknown native/
      readiness/pending/drift/fake/stale state remains debt, without retry or resource credit.
- [x] Implement/review the fixed original-work signed BEGIN socket writer on the SAME
      reserved native intent; concrete full-wire progress and one completion check
      precede native write fact. Partial/unknown no retry, original maximum input3
      envelope and native actor scope retained. No production caller/READY read.
- [x] Implement/review original-work signed READY read from completed signed BEGIN
      evidence, one existing native receive claim, original deadline/cursor and
      broker signature/context/hash. Read success is separate from fresh native
      PRE_GO/READY transition, resources and GO; production caller remains closed.
- [ ] Wire only through qualified production startup/service dispatch; preserve
      the exact original adopted connection plus current native phase authority
      before any credential resource/GO path. Ticket/capacity alone is insufficient.
- [ ] Integrate operator-selected paired runtime/source/credential startup,
      capacity and rotation with the retained handshake on its original channel,
      task/cursor and known local write completion facts.
- [ ] Integrate signed phase commitments with original native phase owners;
      complete actual GO, all character output variants, transfer/custody,
      TERMINAL/ACK/journal/DRAIN/PRE_EMIT and authenticated HTTP publication.
- [ ] Implement the separately bounded existing-state STATUS contract.
- [ ] Complete independent runtime/security acceptance and separately authorized
      installation, physical-device and release qualification.

## Historical endpoint and Mach research

- [x] Review and execute one owned-child native request/typed-retirement path:
      root20 checks, independent source/toolchain/25-artifact readback accepted.
      Child cleanup is reported; parent wait/retirement/endpoint release observed.
      No production authority or native failure-path qualification follows.

- [x] Implement/review typed-dead-only reply retirement with held-name queries,
      one typed decrement, actual-effect capture and timely-close fact. Cover
      live/uncertain refusal, errors, reentry and expiry in the 70-scenario model.
      This does not qualify native requests or general live-right disposal.

- [x] Implement observation-only retained request receipt and closed header/trailer
      validation, with source review and 47 causal model scenarios. Received or
      uncertain copied rights block close/disposal; no message authority follows.
- [ ] Review and implement original message/reply disposal ownership and qualify
      actual owned-destination request/error/reentry behavior before a live
      receiver. Account for kernel send-once notifications and process teardown.

- [x] Implement and independently review the retained native endpoint foundation
      and causal boundary model (PR118), then observe one own-right native
      lifecycle run (PR119: 17 checks, independent artifact readback). This
      completes only endpoint lifecycle, not admission/message authority;
      exact-source CI and production composition remain separate.

- [ ] Implement the reviewed retained Mach boot/channel admission owner with
      endpoint, reply-right, audit incarnation, original lifetime and deadline
      ownership. Keep it observation-only until independently selected startup
      owners/runtime recipes and native phase/digest or kernel-origin control
      binding are joined. Reject delegated UDS holders across the actual binding;
      no BEGIN/GO/control/terminal permission from a boot handshake. Integrate at
      StartupEnrollment/SocketChannel, ParentAuthorityAdapter.bind_remote and
      RemoteOperationOwner without admitting synthetic_no_go or decoded data.
      See [selected issuer direction](RUNTIME_ISSUER.md).

- [x] Complete independent artifact review and CI for the fresh-child native
      sender experiment. Root's single actual Darwin run plus portable checks
      passes 57 cases; PR117 is integrated with all four CI jobs green (7,286 tests).
      Production authority remains unqualified. Historical
      first-route recipient uncertainty remains open. See
      [native sender evidence](NATIVE_SENDER_AUDIT.md).

- [x] Implement/review the owned-child lifetime/possession experiment and perform
      one bounded actual Darwin run. Root passes 20 checks (nine native modes,
      eleven guards); reviewer independently matches source/log/artifact hashes,
      no reviewer execution. All nine cleanups known; delegated fresh echo after
      original exit refuses. This does not qualify ambient gateway FD custody,
      production issuer, bidirectional terminal transcript or native release.
      See [exact experiment scope](PEER_LIFETIME_PROBE.md).

- [ ] Review and implement the actual trusted startup/runtime issuer, separate
      from synthetic_no_go inventories and enrollment DATA, together with one
      actual original-task terminal transcript. See [issuer contract](RUNTIME_ISSUER.md).
      No new permit or dispatch is admitted by this planning item.

- [x] Independently accept bounded cooperative post-GO cleanup reader, owned minimum-deadline wake and adversarial coupling matrix (467 focused cases on Python 3.13); exact source/test scope is in [CLEANUP_READER.md](CLEANUP_READER.md). No image route or terminal authority is enabled.

- [x] Compose existing HMP/mobile presentation foundations with current candidate.
- [x] Implement explicit POSIX backend and actual synthetic kernel transaction tests.
- [x] Implement native authority observer; independent review accepted0eef repair.
- [x] Implement actual YAML token/event adapter; independent review accepted51fc fix.
- [x] Connect file/parser/raster/closed DTO pipeline.
- [x] Add bounded pinned client read, roster capability and foreground fencing.
- [x] Connect classic renderer to live roster rows (not deployed capability).
- [ ] Review complete proposed transport/custody contract and mobile integration.
- [x] Implement one nonresetting fixed-file/YAML/raster work ledger; bounded source review accepted d1521fd.
- [x] Implement bounded child control/GO and result processing primitives; source review accepted recorded repairs.
- [x] Implement actual fixed processing-only child bootstrap and schema2 processing; independent bounded source reviews accepted.
- [ ] Qualify installed interpreter/dependency/code and bytecode-cache provenance before launching from a live listener.
- [x] Implement reviewed fixed process launch/exact wait, owned result pipes and one-use input/GO/control-close primitives.
- [ ] Qualify runtime reaper/source premises and implement hard termination/full JobOwner drain binder.
- [x] Add retained-owner cancellation/termination and exact stream/control closure projection; bounded review accepted the large-result repair in 017abd6. Synthetic codec composition is separate from live custody qualification.
- [x] Compose policy/launch/input/GO/read/wait/group/control/final-native-emission phases into a retained supervisor; independently reviewed actual-process and adversarial tests. No live activation certification.
- [ ] Qualify runtime/code/dependency/exclusive-reaper premises and synchronous syscall latency or external watchdog before claiming a hard wall-clock bound in a live listener.
- [x] Implement explicit frozen startup parser-package launch under -I -B -S, with namespace-only parser binding, no site activation and reviewed static imports.
- [ ] Bind and attest the actual listener PM generation, interpreter/stdlib/parser/bytecode closure; parent sys.path activation is not inherited by the current -I child. See RUNTIME_FINDINGS.md.
- [x] Review external OS-supervised custodian architecture and implement bounded source-only frame codec (BR1/BR2); no service or remote closure authority.
- [x] Implement/review read-only broker kernel peer observation with actual Darwin separate-process identity checks (BR4a); no service or endpoint attestation.
- [x] Implement/review BR3a message grammar and retained64-serial replay window, including sticky scope/role/mode guards; not native/remote custody authority.
- [x] Implement/review and run bounded BR8a temporary launchd crash fixture; new-session reader socket remains open, shared-group socket EOF observed, own-job/communication cleanup verified. This is not production process closure.
- [x] Implement and independently review fixture-only retained Darwin exit observer (`1996c03`); 41 focused cases and serial floor/current combined suites pass. Registration/exit/local close facts remain distinct from service containment.
- [x] Compose and independently review actual verified bootstrap/registry/fixed-reader crash fixture (`d86d9d4`); one owned-label run observes broker/reader kernel exit and exact job/monitor cleanup. No input/GO/host activation, manager causality remains unproven.
- [x] Implement/review and run one instrumented Darwin new/shared-group control (`dfa2858`) with retained kernel observers, independent reader lifetime and cleanup after outcome freeze; bounded contrast passes with no leftover fixture debt.
- [ ] Qualify production service-manager crash/orphan policy before broker activation. Broker readers share its group; the older direct reader creates a new session and must not inherit the broker containment claim. Arbitrary descendants, Linux, restart/multi-operation service policy and runtime admission remain unqualified.
- [x] Implement/review source-only shared-group broker child owner, exact wait and one-use child-only termination; real two-child isolation, no group closure API.
- [x] Implement/review bounded broker registry retention, replay-burning capacity admission, original-deadline launch guards and never-launched global ACK; started-owner terminal release remains unavailable until actual resource binder.
- [x] Implement/review retained partial control acquisition, native close observations and bounded local-FD-only discard; no descendant/native/registry closure inferred. Resource binding is tracked separately below.
- [x] Bind retained metadata/avatar resources before launch; enforce original scope/deadline, one-use candidate transfer, cancellation, exact local drain and cross-operation isolation. Source-only; 38 resource cases and 746 plus 66 subtests on each Python 3.11/3.14.9.
- [x] Implement/review held private endpoint snapshots with FD-relative ancestry, exact private owner/modes, replacement refusal and one-use local close; 56 focused cases independently pass. No connection/service authority.
- [x] Implement/review the [fixed-install verifier plus namespace-only synthetic bootstrap](BROKER_BOOTSTRAP.md); external expected manifest trust and explicit runtime/bytecode/OS-loader premises; actual retained no-GO child and generation/deadline refusal tested. Production audit/service/crash gates remain separate.
- [x] Independently audit the fixed own-code worker and PyYAML 6.0.3 token/event path for process/group/FD-transfer calls; source-path evidence only, not OS confinement. See [audit](BROKER_WORKER_SOURCE_AUDIT.md).
- [x] Implement/review native Popen retention before initialization, opaque partial state, fresh-process empty-active guards and original-deadline checks; 120 focused cases independently pass. Constructor-internal cleanup remains UNKNOWN; no reaper patch or ECHILD-to-success conversion.
- [ ] Qualify multi-operation service lifecycle under the fresh-runtime/exclusive-reaper premises, including crash/orphan containment and retained unknown debt; see [reviewed bounded fixture sequence](BROKER_SERVICE_CONTAINMENT_FIXTURE.md).
- [x] Compose enrolled no-GO private service spine (`e0fe0e7`): actual socket framing/registry/resources, READY/cancel/STATUS, before-effect accept retention, sticky cancellation and local close proof; 29 local cases independently pass with peer identity explicitly mocked.
- [x] Implement/review the separate-process no-GO fixture and outbound scope guard (`8a77d13`);54 focused cases pass on3.11/3.14.9. Actual run supplies peer/boot rejection, READY/cancel/local drain/reader exit, then refuses before STATUS/shutdown; cleanup known, lock retained. This is partial evidence only.
- [x] Independently review bounded fixture polling/control count and private phase diagnostics (`e0eafcf`),26 component cases; original actual FrameError attribution remains unproven, no repeat run or service-acceptance claim.
- [x] Observe one reviewed externally supervised no-GO service fixture (`0bea1c8`/product`89734eb`) with real mutual kernel identities/enrollment, peer/boot refusal, READY/cancel/local drain/PENDING, terminal STATUS and shutdown/known cleanup. Independent artifact review accepted118 private files; no GO/native/started-release/production qualification. See [actual fixture](SERVICE_PROCESS_FIXTURE.md).
- [x] Implement/review the dedicated bodyless terminal STATUS owner: actual initial PeerObservation seal, unchanged deadline, current local/generation guards, queuedEOF vs singleSHUT_WR+EOF, strict CLOSED/ACK, sticky refusal and both native nonblocking/timeout guards.83 focused cases independently pass. See [terminal repair](TERMINAL_STATUS.md); original actual failure attribution/new runtime qualification remain open.
- [x] Implement/review the [native-owned remote BEGIN/READY prerequisite](REMOTE_OPERATION.md): existing admission credits, exact joined policy packet, shared retained remote slot, exclusive channel, fresh original native checks and post-peer deadline/cancellation guards. Local custody/release shortcuts are refused; source `0a4fbeb` passes independent 100+2 focused checks and root 1,379+190 subtests on each 3.11/3.14.9. GO/result/terminal release remain closed.
- [x] Implement/review nonrenewing original cancellation arithmetic and explicitly selected v2 framing (`1a02abe`); 384 independent focused cases and 1,422+190 subtests on each root runtime pass. Existing service remains v1; no clock/transport/release qualification.
- [x] Implement/review retained native clock observer (`37fd2da`), real Darwin private-peer observation, Linux peer-pidfd/procfs/nsfs source path and refusal/close causals. Independent 46PASS/1skip; root serial 1,469PASS/1skip+190 subtests on each runtime. This is not native Linux or production startup qualification. See [native clock](NATIVE_CLOCK.md).
- [x] Implement/review irreversible cleanup-only original native clock (`9f975f7`), prospective local-vs-peer failure planes, exact domain seals and real private-helper first-budget preservation; 62 independent focused cases / 1 Linux-native skip and serial 1,485+190 root subtests. No transport activation or terminal proof.
- [x] Implement/review selected-v2 enrollment/native clock lifecycle (`2e2f4f8`) and Linux self-pidfd/proc PID-realm repair (`6aa829f`). Nine-field guards, retained partial initialization, no fallback, concrete boundaries and distinct close facts; v2 dispatch/cancellation remain refused. Root final serial 1,529+190 subtests / 1 Linux-native skip on each runtime. See [selected protocol](SELECTED_PROTOCOL.md) and [realm repair](PROC_PID_REALM.md).
- [x] Bind one original budget before native observation and broker resource effects, seal remote/resource references, freeze explicit parent cancellation immediately and reject caused-budget launches. Independent current focused review: 195 cases plus 23 subtests. This is local custody plumbing, not joined transport.
- [x] Join native remote BEGIN/READY to its exact selected protocol, qualified clock/domain/value/qualification seals and original budget; callback-free ownership fencing protects both sides of native sampling. Independent 170 cases / 1 Linux-native skip. No CANCEL/task/dispatch/GO/result/release activation.
- [x] Implement/review selected grammar and exclusive broker CANCEL1 receiver/adoption: original domain/budget, partial bytes across work expiry, exact task allocation/init proof, fail-closed construction, metadata callback guards and native nonblocking checks. Independent 94 cases pass; no service v2 dispatch or gateway send activation. See [inherited cancellation](INHERITED_CANCEL.md).
- [ ] Adopt the inherited minimum at both transport ends under the original qualified clock/domain and exact operation before cleanup effects. Source framing/clock/local-owner facts alone cannot authorize this.
- [x] Retain selected-v2 work/cleanup tasks and partial native Future/Task allocations before effects; immutable allocation seals, caller cancellation shielding, same-budget first-cause retirement, actual work join and distinct local socket/clock facts. Independent85 cases pass; source only, no CANCEL frame or release. See [retained cleanup](REMOTE_CLEANUP.md).
- [x] Independently review coupled one-use CANCEL sender, immutable BEGIN-write fact and private v2 BEGIN/READY/CANCEL service retirement. Independent 243 cases pass on Python3.13; preserve original cutoff, retained partial tasks and no release. See [transport](INHERITED_CANCEL.md).
- [x] Review [retained async GO contract](ASYNC_GO.md) and implement READY notification with the original work task parked through READY; immutable Future/fact ownership, partial initialization and final native-reference fences independently accepted. That prerequisite alone did not open GO; the following coupled task adds it.
- [x] Implement and independently review retained GO-request/shared intent states, fresh native GO admission, continuous broker control cursor, concrete GO-write facts/CANCEL1-or2 and one-use service relay together. Partial GO never gets an appended frame; scope/allocation drift refuses before callbacks. Synthetic source evidence only, no result/release or runtime shortcuts.
- [x] Implement/review [private result2 transport](RESULT_TRANSPORT.md): same original work/service tasks, original credited accumulator and transferred payload ownership, independently validated challenge/epoch/parent chain/totals/hash/revision, metadata-only notification/token and cancellation wipe. No publication/COMPLETE or release.
- [x] Implement/review typed local started-reader producer, immutable input receipt and bounded data-only claim codec; exact child-wait/control/pipe/signal facts and completed-transfer digest. Independent 82 focused cases pass on Python3.13. No remote proof or release. See [terminal contract](STARTED_TERMINAL.md).
- [x] Bind/review original candidate identity, bounded canonical header integrity and streaming wire digest; discard all owned payload aliases on central revocation without following foreign slots. Independent103 focused cases pass on Python3.13, including cross-operation custody/scope/failure/finally drift. Private data only, no completion/publication/release.
- [x] Implement/review selected-v2 TERMINAL/digest ACK codec and transcript grammar, immutable metadata seal and shared body ceiling; preserve legacy v1, late-cancellation invalidation and no producer/release authority. Independent290 integration cases before seal addendum plus final192 codec/lifecycle cases pass on Python3.13. Actual dispatch and STATUS remain closed pending joined custody integration.
- [x] Implement/review bounded terminal handoff envelope with sender minimum cleanup stamp; immutable deep values, whole-envelope ACK correlation, no raw-claim fallback. Independent319 focused cases pass on Python3.13. No budget adoption, qualification, transport activation or release from decoded data.
- [x] Implement/review original-work write-quiescence fact/Future, irreversible ordinary-write retirement and one-use CANCEL consumption while retaining whole-task-join/readFalse gates. Independent332 focused cases pass on Python3.13, including partial initialization, scope/actor substitution and failed-mint no-retry. No cleanup-reader/terminal transport activation. See [write quiescence](WRITE_QUIESCENCE.md).
- [x] Implement/review owned readiness-only notification primitive after confirming sock_recv cancellation can lose consumed bytes; independent46 cases pass on Python3.13, including scheduler and original-Future refusal fences. No receive-path activation. See [readiness/cursor boundary](READINESS_CURSOR.md).
- [x] Independently review normal RESULT readiness/cursor integration with retained outer/body offsets, original digest and sticky ambiguous IO. Independent178 focused cases plus final EAGAIN/cancellation causal pass on Python3.13; no cleanup-reader activation.
- [x] Independently review broker control readiness/cumulative-cursor integration, immediate queued-control draining and original work-to-cleanup timeout transition. Independent153 focused cases plus the final cross-channel isolation causal pass on Python3.13; no ACK continuation or release. See [broker control cursor](BROKER_CONTROL_CURSOR.md).
- [x] Independently review selected-v2 retained pre-result BEGIN/READY cursor, callback-free final remote custody fence and readiness-proof-before-current ordering. Independent231-case regression and final9-case owner-binding causals pass on Python3.13; preserve v1 and no cleanup activation. See [pre-result cursor](PRE_RESULT_CURSOR.md).
- [ ] Extend the reviewed post-GO write-quiescence/cleanup-reader coupling to pre-READY and continue the original broker controller after CANCEL toward qualified ACK; retain legacy join gates outside the reviewed scope. See [joined transport prerequisites](TERMINAL_TRANSPORT.md).
- [x] Integrate the bounded DATA-only local-producer handoff freeze. The
      [reviewed source](LOCAL_HANDOFF_FREEZE.md) binds immutable envelope bytes
      to original custody and the actual minimum budget; it supplies DATA only.
      Root's local 418 coupled plus 230 budget/grammar cases pass on each of
      Python 3.11.15 and 3.14.4. Integrated source797dbbc passes exact
      CI42129488493: 7,219 passed, 21 skipped, 190 subtests and Unicode jobs.
      Qualified factories and any sender/receiver/ACK permission remain open.
- [x] Implement and independently source-review original pre-READY/READY-wait
      cleanup-reader coupling, preserving the original Task/cursor/buffer and
      earliest shared budget. Root's exact-source serial nine-module regression
      passes 334 cases on each of Python 3.11.15 and 3.14.4, with 74 dedicated
      causals and no unobserved-task warnings. Reviewer execution is not claimed.
      Integrated source2c2a14e passes exact CI42124526459 (7,192 passed,
      21 skipped, 190 subtests plus Unicode jobs); no ACK/native release,
      route activation or runtime/device qualification follows from this check.
      See [bounded prerequisite](PRE_READY_CLEANUP.md); the combined task above
      and complete character/host-local image delivery remain open.
- [x] Implement and independently source-review the original broker cancellation
      adoption notice and bounded controller park, separate from Task/FD closure.
      Exact native Future/Task descriptors reject shadowed methods on supported
      runtimes; original cursor bytes/cumulative offsets, same cleanup end and
      one-use stop/join remain retained. No ACK/terminal permission is enabled.
      See [controller prerequisite](BROKER_CONTINUATION.md); the full combined
      pre-READY/qualified-ACK task above remains open.
- [ ] Complete selected-v2 STATUS lifecycle, fresh PRE_EMIT, typed started-terminal proof and native/credential retirement before publication; no replay or release shortcuts. See [cancellation contract](CANCELLATION_CLOCK.md).
- [ ] Qualify broker service/runtime and authenticated transport, integrate native gateway routes and bind started terminal release; local observations alone retain PENDING.
- [ ] Resolve direct-child native Kanban waitpid(-1) interference through an ownership-aware native contract or a separately reviewed external broker; do not disable Kanban or reinterpret ECHILD as closure.
- [x] Add reviewed cleanup-only discard after exact child/group/control closure (bf24a54); frozen cleanup budget, actual EOF, buffered wipe and unknown-debt causals.
- [x] Review and implement refusal-only post-GO cancellation closure without treating discarded/missing worker output as successful work; keep ambiguous native/policy resources retained. Actual parent GO-write/termination test uses synthetic native authority; runtime containment premise remains unqualified.
- [x] Review schema3 parent policy/work accounting and implement directory-only policy acquisition.
- [x] Bind actual policy thread/join to native-authorized reserved job; callback closure reviewed a2746c8.
- [x] Bind result2 job receiver to retained parent identity/work; reviewed7955c06.
- [x] Transfer private input3 once after native postcheck; reviewed1784355.
- [x] Close independent review of pre-transfer abort/credential retirement (4ea76f2, twelve cases).
- [ ] Implement reviewed listener startup/shutdown and authenticated metadata route.
- [x] Implement source-only revision-bound client avatar transport, bounded codec and per-widget image owner; independently reviewed.
- [x] Review stable app-level aggregate avatar budget binding (3881fa2); screen regression122cases pass.
- [ ] Sample aggregate avatar resources on exact signed physical devices.
- [ ] Implement authenticated host avatar route and qualify revision/cache behavior physically.
- [ ] Complete header/details, blobatar v2 and custom static image parity.
- [ ] Run exact native/transport/UI causal checks and independent security review.
- [ ] Update host/app candidate, deploy authorized dogfood and qualify physical phones.
- [ ] Reconcile app/plugin feature inventories and upstream Gist with verified scope.

- [x] Complete bounded independent source review and affected regression of
      original-task native READY transition after signed READY plus fresh PRE_GO:
      1,438 passed/one skipped; phase identity tripwire included. Production
      wiring/GO remain closed; earlier cancellation failure cause remains unproven.

- [x] Qualify bounded original-task signed exchange composition (BEGIN writer, READY
      reader, fresh PRE_GO/native READY): three focused cases, 841 selected
      affected tests and lint pass; independent read-only review accepted.
      Production selection/startup and GO stay closed.

- [x] Finalize bounded internal credential READY dispatch through the existing original
      work/caller barrier; three direct cases and independent source review pass.
      Full regression 1,444 passed/one skipped; final explicit-join focused172
      passed/lint passed. Final readback review accepted; startup/GO/release remain open.

- [x] Qualify bounded fixed GO signing-only producer from actual native GO_INTENT and
      original BEGIN/READY/transition/admission; eight focused cases and bounded
      source review pass. Selected853 passed before final value join; focused8
      and lint pass afterward. Final review accepted; transport remains closed.

- [x] Finalize bounded signed GO transport on original native intent/work Task:
      twelve causal cases, lint and independent repair review pass; final affected
      regression 1,466 passed/one skipped. Production sender/GO_SENT/relay remain open.

- [x] Integrate bounded internal signed GO dispatch through original native
      admission/single GO_SENT and full-write proof. Six direct cases, selected872
      and lint pass; independent boundary repair review accepted. Shared cause
      wait is fenced; no unsigned RESULT fallback/result token or execution credit.
- [ ] Integrate authenticated cleanup/result/terminal custody and actual broker
      worker relay before qualifying complete character delivery/startup/release.

- [x] Qualify bounded fixed original-cleanup current role material separately from work
      authority: six direct actor/tail cases and independent read-only review pass;
      selected878 and lint pass. CANCEL signer/writer remains open.

- [x] Qualify bounded after-READY fixed CANCEL signing on original cleanup Task:
      one native preparation/window, seq1/seq2, no interval renewal. Eight focused
      cases, selected887 and lint pass; independent read-only review accepted.
      Socket transport, pre-READY cancellation and remote custody remain open.

- [x] Qualify bounded after-READY signed CANCEL socket writer on the same native
      preparation/window: twelve causal cases, 1,500 affected/one skipped, lint
      and independent final repair review pass. Routing/pre-READY/custody remain open.

- [x] Qualify bounded BEGIN/GO final descriptor-tail audit repairs: reproduced unsafe
      synthetic writes retained (BEGIN2586/GO1617); fixed pure custody + role/actor
      seals and nine new zero-send causals pass independent source review.
      Selected909 and lint pass; no live deployment qualification follows.

- [x] Finalize bounded internal signed CANCEL routing: original cleanup actor,
      partial-owner retention before native effects, no retries/unsigned fallback.
      Five direct route + two actual peer-correlation cases/source review pass;
      full1,516/one skipped and lint pass. The subsequent known no-IO local-close
      follow-up is recorded separately below; remote settlement remains unproven.
- [x] Complete/review automatic solely-local cleanup after known no-IO post-READY
      signing refusal, with exact original actor/frozen budget and repeated no-IO seals.
      Expiry/cancellation/unknown-read causals retain debt; remote UNKNOWN and
      original refusal survive actual local close. 100 focused tests passed.

- [ ] Implement signed pre-READY cleanup under the explicit original READY-wait
      retirement and distinct BEGIN-derived signer contract in
      [SIGNED_PRE_READY_CLEANUP.md](SIGNED_PRE_READY_CLEANUP.md). No fabricated
      READY transition, replacement reader, unsigned fallback or ACK inference.

- [x] Implement/review cancellation-only local retirement of the original signed
      READY wait: exact minted selector proof, original Task done+cancelled for
      historical release, payload-free count fact and wiped bytes. Seven causals
      and 104 READY-reader module tests pass; no pre-READY CANCEL/ACK enabled.

- [x] Implement/review distinct BEGIN-derived pre-READY CANCEL signing-only owner:
      original cleanup Task, completed BEGIN/cancelled read, earliest native seq1
      preparation and reciprocal signer exclusion. Final reader-release custody
      seals reject key/unknown/intent drift. Transport/ACK/publication stay open.

- [x] Implement/review fixed pre-READY signed CANCEL writer on the original cleanup
      Task/end, with native count/fact reciprocity, typed BEGIN slot handoff and
      thirteen known/unknown/current-custody causals. Automatic route/correlation
      and remote ACK/resource/native publication remain open.

- [x] Compose/review original pre-READY signed CANCEL route and actual broker
      seq1/window/end correlation before READY, preserving existing READY/GO
      paths. Three peer and 31 component cancellation cases pass. No ACK,
      worker GO or remote/native settlement is inferred.
- [x] Implement/review automatic solely-local cleanup after known no-IO pre-READY
      signing refusal; fixed reciprocal owner/no-output/no-writer proofs repeat
      after native budget boundaries. Expiry/cancelled actor/unknown read deny
      new credit; post-socket expiry retains only actual socket close. Remote
      UNKNOWN/original refusal remain; 13 focused route/refusal cases pass.

- [x] Implement/review original-service current signed GO receipt validator:
      exact signature/frame/current role/clock/uncased budget and original actor;
      wrong actor/early query does not poison, currentness refusal stays sticky.
      Returns a read fact only; worker GO and generic work gates stay closed.
- [x] Implement/review fixed original-service signed worker-GO relay component,
      with reciprocal final native pipe-write credential fence and local fact,
      native count/unknown-debt preservation, original completed READY/input and
      original actor/budget. 17 peer stages plus five field-shape tests pass;
      actual native OK result observed independently. Production dispatch and
      signed RESULT/TERMINAL integration remain open. See
      [SIGNED_GO_RELAY.md](SIGNED_GO_RELAY.md).
- [ ] Integrate the qualified fixed credential service worker-relay route with
      signed RESULT transport and original retained TERMINAL/ACK lifecycle. No
      unsigned fallback, decoded-claim permission or publication shortcut.

- [x] Implement/review original-service immutable native RESULT signing-only owner:
      actual historical GO relay, drained resources, reciprocal GO/adoption/cursor
      custody and current role/actor/frozen budget; one native take, sticky refusal
      and pure cancellation payload withdrawal before cleanup sampling. Seven
      focused peer stages pass. No wire transfer/terminal/publication credit.
- [ ] Integrate counted signed RESULT streaming and original-controller write
      retirement, then original gateway cursor and retained terminal/ACK lifecycle.
      Preserve actual byte counts, unknown delivery debt and no unsigned fallback.

- [x] Qualify original-service signed RESULT writer and fixed READY slot handoff:
      actual bounded socket sends/counts, original-controller cancellation and
      payload withdrawal; thirteen focused peer cases plus channel tripwire.
      Final1,599 passed/one skipped101.50s; lint/whitespace and independent review
      pass. No production dispatch or terminal/publication credit.
- [ ] Compose signed RESULT with original gateway work cursor under
      [SIGNED_RESULT_READ.md](SIGNED_RESULT_READ.md), then retained
      terminal/ACK/startup/native publication. Local full-count fact is not receipt.

- [x] Qualify fixed gateway GO_SENT result-custody tail with original credential
      work actor/material, native policy/admission/listener/context and uncaused
      frozen budget. Seven causals include actual earlier-phase refusal. Final
      confirmation1,606 passed/one skipped102.87s; lint/whitespace/source review pass.
      Earlier existing signed-cancellation failure is unresolved and preserved.
      This is not a result reader, I/O grant or publication transition.

- [x] Qualify original gateway signed RESULT envelope cursor with fixed native
      GO_SENT admission, bounded HBA1/header reads, reciprocal historical READY
      read claim and exact local cancellation retirement. Twenty-one cases in
      final1,628 passed/one skipped108.30s; lint/whitespace/source review pass.
      Envelope only; no image body, native candidate or publication credit.
- [ ] Continue that same signed cursor through committed image body/result2 and
      original native parent/revision validation, then typed candidate withdrawal,
      cleanup discard/terminal continuation and production dispatch. No second
      reader or envelope-to-image/terminal/publication shortcut.

- [x] Qualify same-original-task signed body streaming and private candidate:
      independent original native buffer/custody, actual signed frame/body hash,
      native result2/parent/revision checks, independent stream/hash allocation,
      typed first-cause discard and exact local wait retirement. Nineteen actual
      private-peer cases; final1,648 passed/one skipped123.36s, lint/whitespace and
      independent source review pass. No native adoption or public delivery.
- [ ] Add reviewed typed native candidate adoption/result notification and same
      cooperative signed cleanup cursor/terminal continuation. Preserve private
      ownership, earliest cause and no competing reader or cancelled-task revival.

- [x] Qualify private candidate-use refusal boundaries: exact original actor scopes,
      primitive signed-stream/fact fields, canonical header identity, sticky admitted
      withdrawal and payload-free exception context. Five additional foreign nested
      metadata cases prove no getter execution and no actor poisoning (5 passed,
      0.38s); independent read-only review accepts the bounded tests. This is not
      native candidate adoption or phone display.
- [x] Implement a distinct fixed post-adoption authority tail for the exact signed
      body owner, preserving original native job/token/candidate joins, current
      keys/policy/clock/budget and first-cause withdrawal. The original envelope
      and result-intent tails remain GO_SENT-only; the new tail is fixed to actual
      RESULT_VALIDATED, without phase reset/selector or legacy owner substitution.
      Cooperative cleanup/terminal and publication remain open below.

- [x] Implement and independently review private signed native candidate adoption:
      dedicated original owner slot, independent adoption/token allocation, original
      actor one-shot native RESULT_VALIDATED transition, fixed post-adoption tail,
      first-cause native/private withdrawal and payload-free refusal. Twenty-eight
      body cases passed in 18.81s, nine exercising adoption/currentness. Final
      affected regression: 1,662 passed/one skipped in 126.11s; lint/whitespace and
      independent read-only review pass. Earlier cleanup refusal remains unresolved;
      no production publication credit.
- [x] Qualify original-caller signed result notification without reusing the
      original-work actor gate. No generic caller-selected actor/phase bypass,
      fake legacy owner, phase reset or competing receiver. Production/cleanup
      integration remains separate below.

- [x] Implement and independently review original-work signed result notification
      and fixed original-caller readiness, retaining actual native Future/barrier/
      allocation and role/policy/socket/budget. Nine actual private-peer causals
      passed in 7.84s, including final dispatch substitution and native ambiguous
      scheduling failure. Final expanded affected regression: 1,738 passed, one
      skipped in 142.79s, including legacy result-ready consumers; lint/whitespace
      and independent read-only review pass. No image/terminal/release returned.
- [ ] Compose original signed receiver/body/adoption/notification into production
      only with the reviewed same cooperative cleanup cursor and signed terminal/ACK;
      retain original actor, budget and native cancellation/unknown debt. Then
      qualify startup/publication and physical/release delivery without shortcuts.

- [x] Capture original signed cleanup progress before first-cause poisoning as
      frozen DATA: actual envelope/body/hash allocation and native wait scope,
      Future, registration/flags. Preserve zero image-body copy, no new read/clock/
      deadline, enum-identity checks and no signed-to-legacy fallback. Independent
      read-only review and targeted actual envelope/body/adoption/notice cases pass.
      Final expanded affected regression: 1,742 passed/one skipped in 146.11s;
      lint/whitespace pass. The inspector grants no IO, quiescence, retirement,
      transfer or release; historical broker failures remain unresolved.
- [ ] Qualify a distinct typed same-original-Task signed cleanup transition from
      held progress, with actual native cause wake/known wait retirement, current
      original custody/role, original write quiescence and minimum budget. Keep
      signed request disabled until those checks and causal isolation tests pass;
      then continue signed body discard/terminal authentication without a new reader.

- [x] Retain actual original registered-wake retirement after native owned-interest
      removal/opposite-direction preservation. Seal original pre-await identities,
      exact retained receipt and original uncancelled actor after final guards;
      generic early wakes and genuine Task cancellation stay distinct. Ninety-one
      readiness cases pass in 0.41s; independent read-only review accepts the
      prerequisite. Final expanded regression: 1,757 passed/one skipped in 150.03s;
      lint/whitespace pass. No current kernel/role/budget/IO/transfer permission.
- [ ] Wire the same signed envelope/body wait to its actual native cause and
      correlate this actual retirement receipt with frozen original progress,
      current registration/custody, write quiescence and original minimum budget.
      Keep signed request disabled until full typed cooperative transition and
      isolation/expiry/stale-ack/unknown-retirement cases pass.

- [x] Bind signed BODY waits to the held actual native cleanup cause and correlate
      actual registered-wake retirement to original signed capture/wait/hash/counts/
      custody and original uncancelled actor. Separate historical completion checks
      preserve local stop only; exact error type and both waiter aliases are sealed
      after final guards. Eleven cause cases pass in 7.36s; nine genuine external
      cancellation cases pass in 6.03s; independent read-only review accepts scope.
      Final expanded regression: 1,768 passed/one skipped in 149.49s; lint/whitespace
      pass. Historical broker failures remain unresolved; no transfer/IO grant.
- [ ] Wire signed envelope cause and qualify actual same-cursor cooperative
      continuation/current registration/role/write-quiescence/minimum budget.
      Signed request remains disabled; no concurrent read, terminal, release or
      publication follows from local stop. Retain existing whole-work-join CANCEL.

### PS1 historical handoff checkpoint — November 7, 2026

- [x] Retain original immutable configuration/package DATA across native startup and namespace eviction, with original context/fact/custody checks; focused416 checks pass.
- [ ] Compose fixed trusted entry, full runtime/dependency/loader recipe and actual native/key factory; historical data alone cannot satisfy admission.

### PS1 entry/bootstrap checkpoint — November 7, 2026

- [x] Separate source entry retains original invocation before fixed bootstrap import, rejoins original scope/cell and aliases, captures activation;18 synthetic bootstrap cases/434 combined checks pass.
- [ ] Independently admit/install exact entry and qualify native PM re-exec; compose remaining runtime/operator/native/key joins. No launch entrypoint is installed by this component.

### PS1 native command-builder fixture checkpoint — November 7, 2026

- [x] Observe actual disposable exec and wrapper re-entry for script/module launch using pinned native relaunch_command source; provenance reviewed;436 combined checks pass.
- [ ] Qualify actual installed entry and native bootstrap/PM activation/lease continuity; this fixture does not satisfy those gates or complete PS1.

### GR1 explicit version-selection slice — November 7, 2026

- [x] Freeze complete recipe pin/child/native-boundary contract; independently reviewed.
- [x] Preserve fixed schema1 loading and add explicit schema2 selection DATA, with no fallback/alternate recapture; package-only verifier refuses schema2 before IO;477 combined checks pass.
- [x] GR1 source document IO: actual complete-recipe/four fixed child reads, canonical common envelopes and shared aggregate budget;39 cases/517 combined checks pass. Fixed entry/operator wiring remains open.
- [ ] Finish GR2 entry/dependency/runtime/link/loader and GR3 actual native/key joins; no authority or deployment is enabled by this checkpoint.

### GR1 original document publication checkpoint — November 7, 2026

- [x] Bind published recipe/child DATA to independently held actual returned byte objects; later-child/final-callback row substitution refuses.
- [x] Retain partial initialization and unknown read/close debt; foreign plan/fact state is preserved; busy owners refuse before fresh capture.
- [ ] GR2 validate complete child tables, entry/dependency/runtime/link/loader closure and original artifact-count handoff.
- [ ] GR3 bind actual native listener/store/bridge/identity service and role keys; broker startup and terminal acceptance/ACK/release remain required.

### GR2 recipe-to-plugin child checkpoint — November 7, 2026

- [x] Consume actual retained schema2 recipe plugin bytes/expectations through verify_recipe; no caller replacement payload/digest or schema1 downgrade.
- [x] Carry actual document count allocation into package IO; seal post-read/document-hash/final-package count identity and retain final actual cell;14 composed cases/534 combined checks pass.
- [x] Preserve historical recipe/configuration/data custody after namespace/path drift; occupied package refuses before fresh capture.
- [x] Carry actual original selection count into recipe/plugin/entry accounting;576 startup checks pass.
- [ ] Complete later dependency/interpreter accounting in one combined original-owner plan; see [composition](DEPENDENCY_FILE_COMPOSITION.md).
- [ ] Complete GR2 entry/dependency/interpreter/link/loader closure, then GR3 native listener/store/bridge/identity/key factory. Full character-image runtime remains unfinished.

### GR2 original entry observation checkpoint — November 7, 2026

- [x] Retain independent started publication joining original invocation/activation/bootstrap and actual import-time module/function/code observations; final callback fences, historical data and fresh queries;32 entry cases/548 combined checks pass.
- [x] Cover foreign publication/aliases, namespace/argv/source changes and wrong-thread/actual-fork refusal without poisoning historical records.
- [ ] Qualify actual selected entry package/wrapper files and execution/control flow, with a reviewed typed original-owner/recipe binding. These observations are not artifact admission.
- [ ] Complete remaining GR2 dependencies/interpreter/link/loader/budget and GR3 actual native/key factory; physical character display remains unfinished.

### GR2 entry/wrapper filesystem checkpoint — November 7, 2026

- [x] Consume original entry child with original entry/recipe/plugin owner joins; closed complete entry table and actual wrapper path, exact internal dedup, no replacement digest/root.
- [x] Own metadata trees before/after actual file hashes and wrapper ancestry/identity joins; preserve unknown scan/close debt and no replay.
- [x] Retain/complete file lifecycle with one-shot-before-native-effects, actual metadata/count publication, compatible legacy facts and typed prior package budget;18 entry/21 artifact cases,569 combined checks pass.
- [ ] Complete actual installed wrapper execution/control-flow and independent operator qualification; snapshots alone do not attest executed bytes.
- [ ] Complete remaining dependency/interpreter/link/loader accounting and native/key factory, broker/ACK/release and physical image qualification.

### Combined entry preparation checkpoint — November 7, 2026

- [x] Separate original entry retention from one-shot file completion, with no
      artifact IO allocated during preparation; exact inactive attempt anchor,
      zero-IO copied-attempt refusal and failed/successful no-replay causals.
      Independent source review accepted;580 affected startup checks passed.
- [ ] Freeze/integrate the complete combined dependency/interpreter plan before
      completion; entry preparation alone neither implements this plan nor grants
      runtime/native/key authority or physical image qualification.

### Original interpreter continuity checkpoint — November 7, 2026

- [x] Capture original interpreter observations before bootstrap and rejoin them
      after callbacks; historical DATA is distinct from current runtime admission.
- [x] Preserve exact original opaque stdlib typing aliases without weakening other
      nonmodule refusals;595 startup checks and49 actual3.11 child cases passed.
- [ ] Integrate original interpreter inputs with the complete combined file plan,
      measured HMP dependency closure and explicit link/loader/operator/native/key
      requirements. No physical avatar or production image route is qualified.

### D1 combined runtime-file checkpoint — November 7, 2026

- [x] Freeze and implement closed dependency/interpreter schemas through one
      original entry/recipe/plugin preparation and file IO owner, no fallback.
- [x] Join all declared package/loose file metadata and original prior receipts,
      exact shared-row deduplication, inherited counts and current module origins.
      Independent source review accepted;632 startup checks and59 actual3.11 child
      cases passed with unchanged source. Namespace/non-file origins refuse.
- [ ] Qualify actual installation closure, required links, future imports and
      OS-loaded libraries plus executed entry/operator/native/key factory. D1 is
      file DATA only; broker acceptance/ACK/release and physical images remain open.

### Original native file effects — pending source branches November 8

- [x] Original-entry lineage5883690:1,290 configured startup cases passed on actual3.14.9, unchanged source, zero failures/errors/skips.
- [x] Exact18 current and18 actual3.11.15 sanitizer cases passed on66f7897; preserve diagnostic DATA
      versus actual operation/kernel/authority distinctions.
- [ ] Execute exact16 current/floor ledger cases; shape checks do not enforce
      transitions or qualify resource recovery.
- [ ] Bind actual scope and predeclared step/consumer claims to the original
      ledger; replace inactive-only shape with a closed claim lifecycle.
- [ ] Implement all six fixed boundaries plus direct cache read/stat migration,
      shared attempt accounting and preallocated reserved cleanup custody.
- [ ] Qualify actual temporary native returns, original result ACK, refusal and
      cleanup semantics before production presentation/runtime and device tests.

See [native file effects contract](NATIVE_FILE_EFFECTS.md). The integrated original
lineage and unwired diagnostic classifier do not implement the remaining full
operation/consumer/cleanup/runtime/device requirements. Unpublished ledger and
repaired scope registry remain separate pending source qualification.

### Unpublished registration source qualification — November 8

- [x] Ledger1b47c95:16 current/16 actual3.11.15 selected cases passed.
- [x] Scope registry731e7ac:14 current/14 actual3.11.15 cases passed.
- [x] Original scope slot874d6bf:20 current/20 actual3.11.15 cases passed.
- [x] Repaired partial file walkersfffa1b3:22 current/22 actual3.11.15 cases passed.
- [ ] Finish cache/link11ff67b55-case actual3.11.15 run; current55 passed.
- [ ] Execute fresh-probe0d74d6525 current/floor cases sequentially.
- [ ] Complete entry metadata/tree registration, original step/consumer plans and
      native-operation/enumeration/cleanup/runtime/device requirements.

All completed boxes here describe exact selected source tests, not delivered
character or host-local-image features. These candidate sources are not included
in this branch's34b862e server/scanner bytes and are not deployed.

### Fixed metadata result path — November 8 current checkpoint

- [x] **PS1-META-COHORT** Exact `a19560a` structural original-consumer/refusal
      selection:14 cases pass on each supported interpreter; source/log/XML
      hashes rechecked. Preparation only.
- [x] **PS1-META-ACTIVE** Exact `a131932` state/debit/failure guard selection:
      20 cases pass on each interpreter with rehashed source/evidence. These
      fixtures construct ACTIVE state; they do not prove native admission.
- [ ] **PS1-META-PRODUCER** Qualify `f47a1be` original consumer latch, actual actor
      admission, literal captured fstat and actual pending return. The29-case
      descendant preserves all prior unrun26 cases; current execution is active
      and the floor is dependent. Review corrections precede these tests.
- [ ] **PS1-META-ACK** Implement fixed directory policy consumption of the actual
      pending producer return: original UID/mode/identity policy, one-use latch,
      raw-free original commit, post-callback closure, raw/envelope retirement,
      exact cursor advance and IDLE. Preserve partial ACK/debit/failure history,
      foreign slots and wrong-actor/revoked-lifetime refusal; no replay/refund.
- [ ] **PS1-META-MIGRATE** Complete all39 stat/fstat sites, both distinct missing
      diagnostics, tree/link plans, six fixed operations and separate directory
      enumeration under original aggregate budgets and reserved cleanup.
- [ ] **PS1-META-ACCEPT** Complete integrated startup/factory/service/key/runtime,
      CPU/RSS/deadline and physical character delivery qualification. The prior
      60-second floor timeout remains unresolved; do not extend its deadline.

All rows retain the full character-delivery scope. They do not activate hosts,
change grants, deliver host-local chat media or certify release readiness.

### Caller integration prerequisite from exact source review

- [ ] **PS1-META-CALLER** Implement the fixed directory caller, original
      unadmitted-preparation release and abort/lost-return cleanup; carry actual
      producer/commit through complete ACK and discard caller envelope aliases.
      Preserve configuration/tree/link-specific policy and finish only after all
      declared metadata sites completed. Do not relax the current unwired cursor0
      assertion to make partial migration pass. These are local implementation
      gaps, not upstream blockers. See [contract](NATIVE_METADATA_RESULT_CUSTODY.md).

### Lost producer-return evidence and repair gate

- [x] **PS1-META-ACK-MATRIX** Exact8f12da7 selected45 cases pass on current and
      actual minimum Python, unchanged source and rehashed source/log/XML. This
      does not cover lost return or qualify a complete caller/runtime/device.
- [x] **PS1-META-RETURN-CONTROL** Exact4072412 counterexample reproduced on each
      interpreter with one intentional failure and exact private stage evidence.
      Original failing receipts remain failed; no component pass is implied.
- [ ] **PS1-META-RETURN-REPAIR** Implement independent pre-C-held retirement
      ownership without adopting current slots as returned receipts; prove all
      raw-bearing backlinks, copy/foreign/context/revocation/interruption/loss
      and GC-disabled cleanup before closing the caller gate. The capsule/weak
      identity proposal is conditional design, not an implemented fix.
