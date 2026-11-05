## Character broker private endpoint — November 4, 2026

The reviewed source can now retain a private socket directory through an
FD-relative no-symlink ancestry walk and observe the fixed endpoint entry.
It enforces expected ownership and exact private permissions, detects held/current
path or socket replacement, and keeps refusal sticky after observed drift.
Partial acquisition retains its owner; exact owned descriptors close at most once,
with no-op, reuse and ambiguous closure unable to produce a success fact.

Root and independent suites each pass 56 endpoint cases. Complete serial Python
3.11 and 3.14.9 regression runs each pass 803 tests plus 66 subtests; lint and
closed-import scanning pass. The previous resource source `f04b3b5` also passed
hosted CI41963160105. These are source and isolated kernel-fixture observations.
The endpoint helper never creates, connects, repairs or deletes a socket, and
cannot attest a future connection, service code/boot or child custody. Runtime
qualification, service/transport/native integration, started terminal release,
authenticated routes and physical character delivery remain open. No live host
or app installation changed. See [endpoint contract](specs/046-bot-presentation-integration/BROKER_ENDPOINT.md).

## Character reader resource binding — November 4, 2026

The reviewed source now binds each metadata/custom-image reader to its original
request, child, control pipe, output buffer and deadline before launch. It checks
input scope before transfer, moves a complete bounded result only once, and
invalidates output immediately on cancellation. Cleanup retains uncertain owners
and never touches another operation's buffers or child.

The new resource suite passes 38 cases; independent review passed its earlier
37-case version, followed by one additional valid wrong-profile input test.
Complete serial Python 3.11 and 3.14.9 runs each pass 746 tests plus 66 subtests;
lint and the plugin import scanner pass. These are source/fixture results.
Local completion still leaves started registry reservations PENDING. Production
service/runtime qualification, authenticated transport, gateway integration,
terminal release and physical character delivery remain open. No host or phone
capability was activated. See [resource API](specs/046-bot-presentation-integration/BROKER_RESOURCE_API.md).

## Character reader local cleanup — November 4, 2026

The reviewed cleanup layer now retains partial control acquisition and separates
work refusal from unknown resource closure without clearing legacy uncertainty.
A local close observation requires the native owning file operation; wrapper
flags, no-op overrides and closefd=False cannot supply it. The separate bounded
local discard entry verifies exact child wait/control close and native read-end/
selector closure, including independently checking any adopted legacy state.
It cannot renew cleanup, restore output, claim descendants gone or free a started
registry/native reservation. The direct process-group cleanup contract is preserved.

Independent56 focused cases pass. Complete serial Python3.11/3.14.9 runs each pass
707 tests plus66 subtests, with lint/import scanner. Hosted CI41958240003 also
passes the Ubuntu plugin and Python3.12–3.14 Unicode jobs on exact sourceb000ca9.
Later documentation does not change that executable. Actual fixed-reader EOF stays
registry PENDING. Full resource binding, service/runtime provenance, transport/
routes and physical character delivery remain open; no phone feature is activated.
See [resource-drain contract](specs/046-bot-presentation-integration/BROKER_RESOURCE_DRAIN.md).

## Character request retention — November 4, 2026

A separately reviewed broker registry now retains reader owners before launch,
enforces total/type/profile/queue/journal limits across connections, and preserves
replay history after refusal or acknowledgement. Original-deadline checks prevent
late normal starts; ambiguous/late starts keep their exact owner and reservation.
Only an explicitly sealed never-started owner can take the current global ACK
path. Started reap and pipe EOF alone remain PENDING and cannot release a slot.

Independent87 registry/child cases and root composed548 on Python3.11/3.14.9 pass,
plus lint/import scanner. Hosted CI41954648933 also passes all jobs on exact
sourcecf33ec9. The next local-FD resource-drain contract is independently frozen;
its partial-control retention and monotonic uncertainty prerequisites are next.
No runtime imports this registry. Started-resource
closure binding, service/runtime qualification, authenticated routes and physical
character delivery remain open; no phone capability is activated. See [registry](specs/046-bot-presentation-integration/BROKER_REGISTRY.md).

## Character broker child ownership — November 4, 2026

The separate shared-group reader owner is now implemented and independently
reviewed. It launches only the fixed isolated reader, exposes owned pipes, waits
only for its exact retained child, and permits one child-only cleanup signal.
It never signals the shared group or treats reap as full resource closure.
Malformed/coercible PID, recipe/stream drift, stolen wait, reentry and uncertain
launch/signal outcomes refuse; uncertain handles remain retained.

Actual fixed-child checks verify empty-input EOF/exact reap and termination that
leaves another owned reader and the controller unaffected. Independent53 cases
pass; root composed513 pass on Python3.11/3.14.9, plus lint/import scanner.
Hosted CI41952456322 also passes the full Ubuntu plugin job and Python3.12–3.14
Unicode jobs on exact executable sourcec715030. Later documentation commits do not
change that executable. This is source-only: retained registry, topology-specific closure binder,
service/runtime qualification, authenticated routes and signed-device parity
remain open. No bot character capability is activated. See [contract and limits](specs/046-bot-presentation-integration/BROKER_CHILD_CUSTODY.md).

## Character reader crash experiment — November 4, 2026

A reviewed temporary launchd fixture now demonstrates why the current new-session
reader cannot rely on its broker's process-group cleanup: its connection stayed
open for the two-second observation window after broker death. The shared-group
fixture reached EOF within0.644ms. Both temporary jobs were removed and separate
reader connection cleanup was verified.19 focused safety tests and190 composed
broker cases pass. This is communication evidence, not production process/group
closure. A reviewed shared-group custody contract and runtime/service qualification
remain prerequisites; no bot character route or capability has been activated.
See [experiment and limits](specs/046-bot-presentation-integration/BROKER_CONTAINMENT_PROBE.md).

## Broker lifecycle and replay controls — November 4, 2026

The reviewed source model now enforces per-direction one-use BEGIN/GO/CANCEL/ACK,
terminal/cancellation races and status-only reconnect responses. Local invalidation
and observed binding/role/mode drift cannot revive old work. A gateway discards a
result racing with cancellation; the broker accepts in-flight late cancellation
for cleanup without sending another terminal frame.

Operation IDs carry a monotonic serial and192-bit random suffix. A retained64-bit
window per exact instance/listener/broker boot refuses replay even after terminal
ACK, random-suffix/channel changes, out-of-order arrivals or history age-out.
This is bounded grammar/admission state, not a grant or execution/custody receipt.
ACK_REQUEST still requires one atomic global tombstone acknowledgement; no counter
or resource is released by this model.

Root lifecycle/codec/peer/source-inventory419 cases pass on Python3.11/3.14.9 on
this Mac; independent lifecycle/codec132 pass, plus lint and the closed-import
scanner. Hosted HMP CI41947357398 also passes the Ubuntu plugin suite and
Python3.12–3.14 Unicode jobs on exact source b4a97e5; this is source CI, not
service/endpoint or signed-device qualification. No service is active and no character availability is advertised.
Actual registry, native/transport integration, runtime/endpoint provenance and
service-manager orphan containment remain open. In particular, existing readers
start new sessions: broker exit/group termination is not assumed to close them.
See [lifecycle contract](specs/046-bot-presentation-integration/BROKER_LIFECYCLE.md).

## Local broker peer observation — November 4, 2026

The next reviewed broker prerequisite can now match a connected local stream's
kernel UID/PID to trusted startup expectations. Actual temporary Darwin endpoint
and separate synthetic-process checks verify the retained child's PID, reject
wrong UID/PID and preserve fixed refusals on missing/unsupported APIs. The helper
checks connected AF_UNIX stream and observed descriptor consistency. It never
signals/waits for peer IDs or treats them as phone rights, code identity, liveness
or child custody. No broker service/route is activated.

Independent39-case peer review passes; root peer/codec/skeleton368 cases pass on
Python3.11 and3.14.9 on this Mac, plus lint and closed-import scanner. Linux
credential layouts have decoder tests, not a fresh Linux kernel qualification.
Darwin's inspected xucred ABI is explicitly versioned/unstable; unknown APIs or
shapes refuse without fallback. Endpoint acquisition, service/code identity,
lifecycle/remote closure and orphan/shutdown qualification remain open. See the
[peer decision](specs/046-bot-presentation-integration/BROKER_PEER_DECISION.md).

## External character custodian path — November 4, 2026

A separately OS-supervised reader broker is the selected development path around
the conditional native waitpid(-1) conflict. The gateway will retain original phone
and bot authorization plus final response approval; it will not start/reap/kill
that service or treat remote completion as a forged local Popen/wait receipt.
No service is implemented or activated yet.

The first reviewed source piece is bounded private framing: canonical closed
headers, kind-specific input3/output2 size limits and exact instance/listener/
broker/channel/operation correlation. Codec/skeleton328 cases pass on Python3.11
and3.14.9, independently repeated; lint and the closed-import scanner pass.
This is framing only, not peer authentication, lifecycle sequencing, body content
validation, child closure or transport memory-bound certification. Service peer/
endpoint identity, restart/orphan custody, native backend integration and physical
character parity remain open. See [broker decision](specs/046-bot-presentation-integration/BROKER_DECISION.md).

## Explicit character-parser runtime — November 4, 2026

The development reader now accepts a validated, frozen startup parser package
under -I -B -S. It exposes only the selected package namespace, never executes its
initializer or site hooks, and uses fixed pure-Python SafeLoader token/event
imports. Graph retrieval/construction methods are not called; SafeLoader's
transitive constructor/composer/resolver code and initialization remain part of
the trusted dependency closure. Both iterators dispose on refusal or closure.
The original general importlib mechanism failed the closed-import scanner and was
replaced; S2 was not relaxed. Exact lazy adapter-only S1 rules retain negative
checks for every other module and unsafe loader/import variant.

Independent review accepted the source repair, including a pending-native-await
startup-binding mutation finding and its no-launch/no-emission regression.
Python3.14.9 presentation/skeleton/surface run passes790 tests+190 subtests, with
20 parser-launch cases separately passing after three extra missing-flag cases;
Python3.11 final run passes793 tests+190 subtests. Counts overlap. Ruff and the
mandatory closed-surface scanner pass. No installed runtime or physical character
parity is claimed.

Actual listener PM-generation/interpreter/stdlib/source/parser/bytecode attestation
and the conditional Kanban reaper conflict remain activation gates. The default
unbound worker refuses; no path is derived from phone input or a fresh mutable PM
selection per job. No route, capability, dependency, host grant or provider setting
was activated. See [runtime decision](specs/046-bot-presentation-integration/DEPENDENCY_LAUNCH_DECISION.md).

The app separately has selected-chat readiness source and scanned unsigned iOS
2026110403. This HMP branch is not silently substituted into that app artifact or
its pinned submodule, and neither is claimed installed/device-qualified.

## Harmless approval-test compatibility — November 4, 2026

Reviewed repair 4ad1344 fixes a real current-native mismatch: native notifications
add `timeout_s`, which the old strict callback decoder rejected. Only that bounded
integer metadata is optional; original identity/pattern checks, unknown-field
refusal and the operator's original deadline remain enforced. The AT1 union
passes 470 tests on Python 3.14.9; two further probe-admission tests pass. Actual
exported ed1afb helpers and an independent rerun complete once/deny/cancel/expiry
with joined cleanup, empty queues and released slots. This is not paired-phone,
operator-IPC or deployed-runtime qualification. The source registers the scoped
`hermes hmp approval-test` interface; see the precise
[native compatibility scope](specs/039-hmp-operator-approval-test/NATIVE_COMPATIBILITY.md).

iPad signing attempt 2026110402 is blocked by Apple's updated Program License
Agreement and missing device coverage in the existing profile. No agreement was
accepted and no signed artifact/app installation resulted. The scanned unsigned
2026110401 candidate remains available. The broader feature work remains active.

## Runtime integration findings and host-local images — November 4, 2026

Current native source exposes two concrete character-reader integration gaps:
PM activates dependencies only in the parent's import path, and the embedded
Kanban reaper can consume another direct child's exit status. See the pinned
[runtime findings](specs/046-bot-presentation-integration/RUNTIME_FINDINGS.md).
This is not an exact-version or Linux rejection. Bare Python 3.14.9 lacking yaml
does not prove the selected PM environment lacks it, and launcher metadata does
not prove the running gateway's interpreter. The reaper conflict applies when
that native path runs; active configuration was not inspected or changed.
Dependency-aware launch and native child ownership or a separately reviewed
external broker remain implementation work. No missing wait is treated as exit.

Host-local image delivery is independent of that reader. Fresh source checks
passed 1,359 server media assertions on isolated Python 3.14.9 and 62 Flutter
loader/card/transcript/Bot Chat tests. The broad server run reported old pytest
temporary-directory cleanup warnings and one unobserved synthetic client-task
error; the test-only request-observation repair passed independent review and
its targeted rerun without that orphan warning. These are not physical image
display evidence. The iPad Pro is connected with Developer Mode; iPhone 15 Pro
Max is disconnected. Unsigned iOS build 2026110401 compiled and passed the release
artifact scan. The generated native-plugin lock/framework reconciliation passed
independent review; signing, installation and physical image display remain open.

## Composed character reader — November 4, 2026

The source-only supervisor now connects native authorization, actual directory
policy work/join, fixed child input/GO, result2 validation, process/group/pipe
closure, final native authorization, single emission and credential retirement.
Independent review accepted 15 composed/adversarial cases: late native responses,
original timeout, partial acquisition, cancellation, cleanup-budget exhaustion,
duplicate run, native DRAIN and blocked policy-thread debt. The full presentation
suite passes 437 tests and 190 subtests on the host Python 3.14 executable via
isolated dependencies; two subsequent independently reviewed test-only additions
cover lost sink acknowledgement and cleanup-budget nonextension. Prior pushed
checkpoint 8f5bef1 also passed GitHub CI.

This is not installed-phone support. Live runtime/code/dependency and exclusive
reaper qualification, synchronous syscall latency/watchdog behavior, listener
lifecycle and authenticated routes remain open. The asynchronous timeout cannot
bound a synchronous syscall that blocks the event loop. Uncertain partial setup
or late native/thread work retains debt and credentials rather than claiming
cleanup. Fixed worker no-spawn/no-FD-transfer remains a required premise.

## Character reader abort lifecycle — November 4, 2026

Reviewed source 71b592c adds a dedicated refusal-only aborted-result marker after
exact retained process/group/pipe/control closure and irreversible output discard.
It cannot recover prior UNKNOWN, skip ordinary result validation, reauthorize or
emit. Native/policy resources must still close independently before credential
retirement. An actual fixed-child test covers input/GO write, termination request,
wait/group/pipe closure and no display; authority is synthetic and there is no
child acknowledgement or completed-read claim. Failed native DRAIN retains
credentials/claim and disables the scope. All 422 presentation tests and 190
subtests pass on the host Python 3.14 executable in an isolated environment;
independent bounded review accepted the change. Live activation still requires
the fixed worker's no-spawn/no-FD-transfer runtime/code premise, full supervisor,
authenticated routes and physical app verification.

## Character reader cleanup — November 4, 2026

Reviewed source bf24a54 adds cleanup-only pipe draining after exact retained
child exit, process-group absence and control closure. It irreversibly cancels
output, wipes buffered results (including already-drained readers), and uses one
nonrenewable 250 ms cleanup allowance. Actual pipe/empty-child checks cover
timeout, wrong control identity, overflow and uncertain descriptors. The full
presentation suite passes 416 tests and 190 subtests on the host's Python 3.14
executable in an isolated environment. Independent bounded review accepted this
slice. Its initial post-GO UNKNOWN limitation is superseded by the reviewed
refusal-only marker above; the full supervisor remains unfinished. Nothing is
activated on phones by this source checkpoint.

## Character delivery recovery — November 4, 2026

The recovered character integration branch now retains a presentation process under
one operation identity and requires explicit never-launched closure or terminal
process/group closure before credential retirement. Focused Python 3.13 synthetic
checks now pass 409 tests and 190 subtests on Python 3.11, 3.13 and the updated
host's Python 3.14 interpreter in isolated dependency environments; changed
modules pass Ruff 0.16.9. Independent bounded review accepted the callback/custody
repair and ordered result chunking (017abd6). A valid 140 KB synthetic V2 avatar
now survives collector-to-codec transfer rather than exceeding the 64 KB feed
limit. This does not qualify live process custody or installed dependencies.
Full supervisor, live authenticated metadata/avatar routes,
exact runtime qualification and signed phone checks are still incomplete. This
is not a deployed bot-character feature. Host-local images retain their separate
implementation and physical-verification requirements.

## Character reader integration — October 12, 2026

Native policy callback findings are closed by independent review. The job receiver
now compares result2 against retained parent work and directory identity (reviewed).
One-use native-policy input transfer and known pre-transfer cleanup are implemented
and independently reviewed. Full composed regressions are running. Authenticated route activation, process supervision/runtime
attestation and physical character display remain incomplete. Installed app/host
versions have not changed; host-local image phone display remains unverified.

# HMP features

## Bot character integration checkpoint — October 12, 2026

Bot presentation now has a real isolated schema2 reader verified on synthetic
profile files. Bounded input, exact identity/policy reconstruction and the fixed
processing-only entry passed independent source review. This is **not available
on installed phones**: live source/runtime provenance, supervisor custody,
authenticated routes, image transport and physical qualification remain open.
The current local-media candidate is implemented and enabled on the dogfood
host, but fresh end-to-end physical rendering remains unverified; the older
MEDIA path shown by the user no longer exists. No arbitrary-path serving is
introduced to compensate.


HMP is the Hermes gateway plugin used by the [HermesBot Mobile](https://hermes-bot.app) apps. This page describes the plugin; the mobile UI is tracked in the private app repository.

| Status | Capability | Notes |
| --- | --- | --- |
| Available | Device pairing | Local QR offer, operator code comparison, one key per device, and a separate host decision for jobs and model controls. |
| Available | Private transport | TLS instance-key pinning over a private network such as Tailscale. |
| Available | Bot roster and Bot Chat reads | Profile list, snapshots, history, and access state through the Hermes gateway. |
| Draft | Host setup check | Read-only build, identity, and pinned-listener diagnostic; profile routing remains an operator check. See [install](docs/INSTALL.md). |
| Draft | Bot channel health check | Read-only per-bot send, jobs, and model prerequisites from the running gateway; enabled failures exit nonzero. See [install](docs/INSTALL.md). |
| Preview | Bot Chat sends | Explicit owner gate on every build, profile-specific send status, freshness check, and retry-safe handling. A bot without a usable profile key reports read-only. A Hermes below the minimum version, or one missing an API send needs, reports send as unavailable. |
| Preview, off by default | Scheduled jobs | Owner-gated list, create-paused, edit, pause, resume, and delete on Hermes 0.21.5 or later that provides the scheduler APIs. New mobile jobs can send results to Bot Chat or keep them in run history, use a finite run count, and carry Hermes's previous-run continuity. |
| Preview, off by default | Bot default model | Owner-gated catalog and validated change within the selected bot's profile. New sessions use the choice. |
| Draft, under security review | Phone chat approvals and choices | Implemented under the minimum-version policy and not yet independently reviewed or released. Available on Hermes 0.21.5 or later when the Phone helpers HMP calls actually exist (`hermes hmp compat` shows `phone_chat`), for a device the host listed in `owner_device_ids` with the direct-send switch on. No exact build, receipt or restart latch admits it. The mobile integration is draft app PR #48; physical-device behavior is unverified. |
| Draft, under security review | Bot Chat approvals | Implemented under the minimum-version policy and not yet independently reviewed or released (`approvals` in `hermes hmp compat`). An approval-owner device's guarded send opens the session stream and may answer Hermes's own card through its native route; every other device keeps the synchronous send. Cards exist only where Hermes's session stream emits approval events: inspected on untagged development builds, absent on release `v2026.9.24`, where the send still works and Hermes keeps its own fail-closed behavior. No release is claimed for cards. Earlier exact-build fixture passes are sampled evidence only. |
| Delivery candidate; physical verification pending | Host-local generated images | Authenticated `/bots/{p}/media/{ref}` delivery and the mobile loader/card/transcript path exist in source. Fresh checks pass 1,359 server assertions and 62 Flutter cases. The host switch, device approval-owner right, per-bot authorization and required native APIs remain enforced. Only validated typed `image_generate` tool results mint references; assistant `MEDIA:` text is not file authority. Actual image display on a signed physical candidate remains unverified. Other producers still require an authenticated typed-artifact contract. |
| Draft read support | Phone Bot Chat search | A distinct start-of-history page for authorized sessions lets the phone match locally without passing query text to Hermes. The companion app draft handles compaction, incomplete scans, and bounded paging; this is not Hermes-wide search. |
| Upstream gap | Hermes-wide search | Hermes logs raw query text on a slow search path; HMP cannot safely expose that full-corpus search yet. |
| Upstream gap | Create and delete bots | The profile-scoped API server lacks a complete profile lifecycle and canonical Bot Chat create-or-get contract. |
| Partly available | Session management | Read-only browsing exists. Metadata writes and non-destructive branching need a stable canonical remote contract. |

See the [roadmap](ROADMAP.md), [unified gateway research](HermesUnifiedGatewayResearch.md), [wire contract](docs/architecture/contracts/HMP_V1.md), and [upstream requests for Nous Research](NOUS_GATEWAY_OBSERVATIONS.md).
