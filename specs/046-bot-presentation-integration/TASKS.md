# BI1 integration tasks

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
