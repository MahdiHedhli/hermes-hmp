# Runtime qualification issuer — proposed Darwin implementation contract

This is the next implementation contract for full desktop character delivery,
not qualification evidence. No issuer is implemented or admitted by this file.
Keep TERMINAL dispatch/acceptance, ACK, started journal release, native completion
and HTTP image publication closed until the composed implementation is reviewed
and its exact runtime is observed. Preserve classic, blobatar and custom static
images; host-local chat media retains its separate authenticated authority path.

## Why the existing verifier cannot issue authority

`presentation_broker_bootstrap.VerifiedInstall` explicitly verifies only
`synthetic_no_go`. Its inventory and full recheck are useful mechanisms, but
neither their output nor a `StartupEnrollment` is a GO-capable qualification.
Kernel peer observation identifies a connected process; it does not establish
that process's executable origin, exclusive reaper, endpoint or manager policy.
No decoder, expected digest supplied by an operation, same UID, mutable Python
field, Hermes version or fixture PASS may convert those objects into authority.

This is a broker installation/runtime requirement, not a Hermes equality or
allowlist restriction. Hermes retains minimum-version/best-effort behavior with
actual native API and authorization checks. No native reaper replacement,
Kanban disablement, permission change or upstream patch is planned here.

## Trusted inputs and two local issuers

Use fixed startup code on each side of the private connection. The service and
gateway independently qualify their own role and the same externally selected
installation and boot. Broker/worker isolation applies to the separate broker
installation, not the existing PM-bootstrapped Hermes gateway: the gateway issuer
binds its actual native instance/listener, current HMP code origin and native
authority adapter. It does not require the gateway to share broker import roots,
use -S, or match an exact Hermes release. Never serialize a Python permit or accept
one in a frame.
The only permitted external selection comes from the operator's fixed reviewed
installation configuration, captured before listener admission. HTTP parameters,
bot configuration, native tool output and broker responses cannot select it.

The installation configuration must pin the verifier/entry origin, interpreter,
source/dependency/runtime inventory digest and manager launch recipe. It must
have bounded canonical representation and private owner-controlled ancestry,
no-follow reads and exact owner/mode/type checks. An inventory tool may generate
a candidate; an independently reviewed install decision selects the expected
bytes. Candidate self-hashing or copying observed bytes into expected fields in
the running issuer is forbidden. No new signing service or secret is required.
An administrator replacing both the trusted configuration and executable remains
inside the stated trusted-installation boundary; hashes are not an OS sandbox.

Each issuer retains all partial owners before effects. The service issuer runs
from the fixed manager entry before resource admission. The manager launch recipe
binds the broker process; it does not assert ownership of the existing gateway.
The gateway issuer runs
before adopting a presentation channel. They issue only after all checks below
succeed, and retain a single boot-bound qualification in the original service or
listener owner. Constructor failure, reentry, observed drift or uncertain native
results permanently refuse that owner. There is no reset, late enrollment,
automatic restart or fallback to the synthetic verifier.

## Required evidence joined before issuance

1. **Executable and imports.** Reuse reviewed bounded inventory mechanisms but
   introduce a separately reviewed GO-capable mode. Verify the running fixed
   `-I -B -S` interpreter and namespace-only broker/worker/parser entry, actual
   import roots, admitted source/cache/archive/native extension bytes and absent
   import candidates. Audit the complete reachable worker path, not just the
   entry file, for extra processes, regrouping and descriptor transfer. Do not
   inherit gateway `sys.path`, environment, providers or credentials. Bind the
   chosen dependency generation; PM parent activation alone supplies none.
2. **Loader premise.** Account explicitly for admitted installed libraries and
   the platform's fixed OS-managed loader roots. Record what is measured versus
   trusted; do not claim all loaded native images are measured from Python file
   hashes. An unexplained extension/library/import origin refuses issuance.
   Installation immutability during an admitted boot is an explicit prerequisite,
   with observed metadata/generation drift causing revocation. Metadata checks
   do not prove the absence of an unobserved same-account ABA replacement.
3. **Manager and lifetime.** For the first Darwin implementation, use one exact
   independently supervised launchd job, its fixed ProgramArguments and original
   boot/process identity. Join manager observations with the exact native kernel
   peer, retained endpoint identity and process lifetime observer acquired while
   that identity is live. Register before relying on later exit observations;
   an already exited, reused, unobservable or ambiguous process cannot issue.
   A label, PID or peer-supplied nonce alone is insufficient. Never look up or
   signal arbitrary processes, enumerate jobs or repair an existing service.
4. **Reaper and containment.** The broker is outside the gateway process and is
   sole exact-child reaper for its fixed reader. Preserve shared-group manager
   policy, no auto-reaper, no spawn/no-FD-transfer worker premise and retained
   control/read/selector/signal owners. Existing crash and group contrast fixtures
   establish their stated observations only, not arbitrary-descendant absence or
   a production hard latency bound. Native operations that could block need the
   separately reviewed watchdog/latency premise before claiming a hard bound.
5. **Channel and clock.** Bind exact instance/listener/broker boot, initial kernel
   peer observation, endpoint/native socket/FD, role, installation generation,
   selected protocol and qualified common monotonic clock domain. Keep original
   enrollment immutable and authenticate before any input body. Reconnect is a
   new independently qualified connection; it cannot resume an old operation.

## Darwin lifetime acquisition decision and unresolved production anchor

Use a retained original process lifetime anchored **before** connection, not a
numeric PID lookup after peer authentication. First establish the trusted
startup origin of that exact process; register its retained NOTE_EXIT observer
while it is still known live, verify no already-pending event, then connect.
Join the expected peer and recheck the same lifetime after authentication and
before any body. Exit, ambiguous registration, replacement or lost observation
refuses; never register a replacement PID and call it the original lifetime.
The observer is not an owned reap or authority to signal that PID.

For the first disposable transcript, the external supervisor must own both
synthetic process objects from creation, retain their unreaped lifetimes through
registration/peer join, and be their only reaper. That gives the fixture an
actual preconnection anchor; its data cannot qualify a production listener.
Production must separately join the broker's exact manager-owned launch with a
trusted original gateway native instance/listener lifetime **before** connection.
**EVIDENCE_GAP:** the precise gateway-to-service startup anchor transfer remains
an open design item; an expected PID/version copied into startup JSON is not its implementation.
Do not implement a production issuer by assuming this missing transfer.

The installed Darwin SDK exposes LOCAL_PEERTOKEN, but it is not selected here as
a standalone original-peer-incarnation proof. Inspected Apple kernel code looks
up a current process from the peer socket's last PID when answering that option;
a returned pidversion alone does not prove retention of the original process.
See [Apple's implementation](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/bsd/kern/uipc_usrreq.c).
This is a source-level reason to retain the lifetime gate, not evidence of a
live attack or an assertion about every OS kernel version.

## Scope, freshness and revocation

Issuance has three joined levels: shared trusted-install/boot admission, then
exact authenticated-channel qualification before any input body, then an
original-operation terminal permission derived only after input and native scope
binding. Boot evidence may be shared by its own service/listener operations; it
is not itself a profile/device grant or an operation permission. These are stages
of one owned issuer workflow, not freely constructible or swappable tokens.

The resulting operation fact is nonserializable and redacted. It binds its exact
issuer, original service/listener owner, role, installation/boot, manager/lifetime
observations, endpoint/channel and clock-domain references. It is not created by
a public constructor accepting an `authorized=True` value, caller callback or
wire generation. Separate service and gateway facts cannot be exchanged or
borrowed across operations, profiles, devices, instances or later boots.

Before an operation adopts the fact and around every terminal IO boundary, check
its original ownership and current generation/lifetime/channel/clock fences.
Do full bounded installation verification before issuing work deadlines; do not
charge an unbounded hash walk to a cleanup interval or renew a deadline after it.
After an await or native boundary, recheck the held references before publishing
another permission. A new current fact cannot repair a failed original one.

Retirement or observed drift revokes publication before notifying retained
operations. Each affected operation freezes or shortens only its own original
cancellation budget and keeps uncertain debt. No cleanup renewal, fresh reader,
automatic retry, reauthentication revival or cross-operation resource traversal.
Lost acknowledgement of revocation remains unknown, not successful cleanup.
Known transport close, process exit, journal ACK and native DRAIN remain separate
observations; none may stand in for the others.

## Exact integration after actual issuance

The broker may use its original `LocalStartedProducer` and frozen envelope only
under this original qualification, original service Task and known non-torn
write history. Recheck `_handoff_failed`, actual current minimum cause/end and
original custody immediately before IO. Any later cause or shorter end refuses
the old envelope rather than refreezing, retransmitting or appending after a
torn write. Bound header/body and preserve the sole controller's ACK cursor.

The gateway retains a single receiver before IO on the original work Task and
cursor. Canonical handoff data must join the outer binding and original input
SHA/profile/kind/deadline/challenge/epoch/worker-source, qualified installation
and clock domain. OK additionally joins the retained result transfer's actual
streaming digest, token and current candidate integrity. ABORTED never publishes.
An accepted caused stamp may only shorten the same `CleanupReadGate` budget via
its owned inheritance path, before subsequent IO; unqualified data never does.

Only reviewed joined TERMINAL/ACK completion may settle its exact journal debt.
Gateway native INITIAL/BEFORE/PRE_GO/PRE_EMIT, original headers and bot/device
authorization, parent policy work/join, native DRAIN, final candidate integrity
and credential retirement remain independently required. Runtime qualification
does not grant filesystem reads, phone access or emission. Full image routes and
physical parity follow only after these planes compose.

## Implementation and acceptance sequence

- [ ] Independently review this issuer contract and resolve the concrete manager,
      installation immutability, loader and native-latency premises.
- [ ] Implement the two fixed startup issuers and retained partial state together
      with GO-capable exact-runtime verification. Keep synthetic mode distinct.
- [ ] Compose one actual Darwin original-task service/gateway transcript using
      only new disposable synthetic profile files and reviewed temporary own-job
      ownership. Bind its expected installation independently before execution.
      No live Hermes profile, message, device, provider or permission change.
- [ ] Cover issuer substitution/self-selected expected hash, wrong role/source/
      dependency/cache/library, manager/peer/endpoint mismatch, stale or reused
      process, boot/reconnect/generation drift, revocation during IO and lost
      acknowledgement. Prove another admitted operation remains unaffected.
- [ ] Exercise normal and abort pre-READY/post-READY/partial-result/post-result,
      frozen-envelope cause/min shortening, torn/lost TERMINAL/ACK, expired/future
      stamps and original Task/cursor ownership. Unknown retains debt; no resend.
- [ ] Independently review source and actual artifacts, then integrate native
      authority/retirement and authenticated routes. Separately qualify the exact
      installed runtime and signed devices. A source fixture is not deployment.

Linux needs a separate systemd/pidfd/loader qualification under the same contract;
Darwin results cannot admit Linux or turn a missing OS API into an allowlist.
The full cross-platform feature remains required and the broader goal stays open.
