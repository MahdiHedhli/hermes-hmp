# BI1 external reader custodian — proposed no-core-change path

Status: architecture review requested; no live service, capability or route.
The direct gateway reader cannot assume exclusive wait ownership when the native
Kanban thread may call waitpid(-1). An HMP-only lock, forkserver started by the
gateway, detached child or altered SIGCHLD handler does not repair that premise.
The external custodian below is separately started/supervised by the operator's
OS service manager. The gateway never starts, kills or reaps the custodian. No
native global reaper/configuration is changed. This retains full desktop name,
classic/blobatar and custom static image parity; it is not a manual snapshot
substitute for that scope.

## Authority and trust split

Gateway retains original phone authentication, canonical bot authorization,
listener/store/device/profile generation, directory policy, original two-second
monotonic deadline, native pre-GO/pre-emit checks and the sole HTTP emission.
Original bearer/headers/keys never leave it. The broker has no gateway, Hermes,
provider, identity or credential initialization and does not assert phone rights.
Its sole privileged task is the existing fixed isolated reader and exact child,
pipe, wait, termination and cleanup custody under the separately reviewed topology.
The shared-group child contract supersedes any exclusive-reader-group assumption:
no per-reader group signal or group_absent proof is permitted. It consumes bounded input3
and GO only after the gateway authorizes that exact operation.

An explicit separate broker-operation owner/closure receipt is required at the
gateway boundary. Never forge a Popen, local waitpid observation or existing
PresentationProcessOwner to represent an authenticated remote completion. The
current direct ReaderSupervisor/ParentAuthorityAdapter stay closed until a new
backend's authority integration is reviewed and tested.

Use only a private local Unix socket. Kernel peer identity, fixed instance,
private non-symlink socket directory, held/current endpoint identity and installed
code/runtime provenance must be bound on supported Linux/macOS before activation.
No TCP, public URL, redirects, bearer forwarding, unverified peer or self-reported
hash as attestation. Exact platform peer-credential mechanics remain to qualify;
a missing supported credential/endpoint mechanism is unavailable, never fallback.
Same-UID local host administrator and root remain trusted; remote paired phones
never receive this IPC endpoint or a broker operation capability.

The broker fixes its own instance and fresh boot nonce at startup, and freezes
its selected interpreter/stdlib/own code/parser/bytecode configuration. A listener
captures the independently qualified broker boot identity before jobs. Broker
restart/source change invalidates old operations and does not refresh/retry them.
Code integrity is distinct from Hermes minimum-version compatibility; do not add
a runtime allowlist of tested Hermes revisions.

## Single-operation connection and framing

One connection carries one operation. No request-controlled executable, module,
filename, PID, signal, timeout extension or capacity is accepted. A closed binary
frame has magic HBR1, four-byte big-endian header length, canonical UTF-8 JSON
header <=1024 bytes and bounded raw body. Canonical encoding is json.dumps with
sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False, then
ASCII bytes. This schema permits only fixed ASCII names/values; no escape
sequences, alternate key order, whitespace, duplicate keys or numeric spellings
survive byte equality against that re-encoding. Total frame maximum is exactly
8+1024+OUTPUT_LIMIT bytes. Header exact keys:
`v/kind/iid/listener/broker/channel/operation/sequence/body_length`.
Version exactly integer1; iid52 canonical lowercase base32 of32 bytes; listener32 hex; broker/channel/
operation64 hex. Sequence exact nonnegative integer0..3, never bool. This is a syntactic bounded
placeholder only: BR3 must freeze per-direction/race/ACK/STATUS sequencing before
any service uses it; it does not define a global lifecycle counter. Tokens bind
operation correlation only and confer no authorization.

Frame kinds and body limits:
- BEGIN: existing input3 frame, 4..8196 bytes (8192-byte JSON plus its four-byte prefix); input's identity/challenge/original
  deadline must be joined to the retained operation by the eventual broker owner.
- READY/GO/CANCEL/CLOSED/ACK/STATUS/PENDING/UNKNOWN: no body.
- RESULT: existing output2 bytes, 4..OUTPUT_LIMIT; separately validate its content,
  work/source proof and terminal ownership before any gateway native pre-emit.

The [BR3 lifecycle amendment](BROKER_LIFECYCLE.md) structures the operation field
as monotonic serial plus192-bit entropy and defines per-direction sequences,
status-only PENDING/UNKNOWN and terminal/CANCEL races. The old random-only/sequence
placeholder is superseded for future service integration; no live protocol exists.

No generic error text, paths, headers, prompts or arbitrary metadata in transport
headers. Duplicate/unknown keys, invalid constants/UTF8/magic/types, overlong or
partial/mismatched body and trailing bytes refuse. Decoder checks kind-specific
body bounds before accepting/allocating that body. A buffer codec does not itself
prove network receive limits; actual readexactly/flow-control/deadline and aggregate
memory accounting remain transport tasks.

## Lifecycle to implement and independently review

BEGIN is admitted only for a new exact operation/current boot and fixed capacity;
never implicitly retry on reconnect. Broker reserves before spawn, retains partial
owners, writes input but no GO, then READY. Gateway freshly authorizes current GO
and sends it once. Broker relays only the captured input challenge to its owned
reader. Duplicate GO never rereads or respawns. EOF is cancellation, not GO.
CANCEL/timeout/disconnect invalidates output before bounded cleanup; no further
normal actions. Both sides honor the same original monotonic deadline, not a
new per-hop duration. Cleanup uses the frozen total250ms phase across planes.

RESULT or CLOSED requires the broker's actual terminal custody observations;
JSON booleans supplied by a client or a closed socket cannot stand in for them.
Gateway still revalidates current native authority and output before rendering.
A cancellation/result race can retire verified remote closure while discarding
output, never restore cancelled publication. Unknown/partial startup or cleanup
stays retained debt and disables/reduces available capacity; no invented closure.

Keep bounded terminal tombstones and explicit ACK after the gateway consumes a
known terminal observation. Reconnect STATUS with the original bound operation
may observe existing state only; it never starts/resumes work or returns a new
result body. Lost delivery/ACK never triggers BEGIN replay. Unknown operation,
broker crash/restart or unqualified service-manager/descendant closure remains
unknown debt, not proof of child exit. Socket EOF, peer exit and timer expiry do
not independently prove child/group/pipe cleanup. No automatic PID scanning/kill
or listener/host restart is introduced. Service containment, shutdown and orphan
handling must be qualified before runtime activation.

## Sequenced tasks / checklist

- [x] BR1: independently review architecture and freeze bounded frame codec. Codec may
  land source-only first; all service/authority/activation gates stay explicit.
- [x] BR2: implement closed pure codec + causal malformed/boundary/isolation tests.
- [x] BR3a: freeze and implement source-only per-direction grammar and bounded serial replay window; see BROKER_LIFECYCLE.md.
- [x] BR3b: retained source admission, original deadline and sealed-never-launched global ACK; see [registry contract](BROKER_REGISTRY.md). No started-owner release.
- [ ] BR3: complete exact global atomic ACK/tombstone integration and typed remote custody authority, plus client/server lifecycle, sequencing/cancellation race,
  capacity/tombstone/ACK/status and typed remote closure authority contract.
- [x] BR4a: implement/review kernel UID/PID snapshot helper and actual Darwin cross-process fixture; endpoint/code/liveness/custody remain separate.
- [ ] BR4: qualify platform UID/endpoint identity and private socket acquisition,
  race-safe startup and nonblocking bounded transport with original deadlines.
- [x] BR5a: implement/review separate shared-group exact-child custody; no group/remote closure. See [child contract](BROKER_CHILD_CUSTODY.md).
- [ ] BR5: implement standalone namespace-only broker using explicit parser recipe,
  fixed reader, exclusive child custody, retained partial owners and real drains.
- [ ] BR6: new gateway backend with native original-credential pre-GO/pre-emit;
  keep typed remote observations distinct from local process proof.
- [ ] BR7: actual kernel fixture tests with broker not parented by the gateway,
  competing exact-own-child reaps only, disconnection/late GO/duplicate/rebind/
  restart/unknown debt; no real host content or profile execution.
- [ ] BR8: supported service-manager/code-generation/stdlib/parser/bytecode and
  crash/descendant/watchdog qualification; no self-attestation or hard-bound claim.
- [ ] BR9: authenticated metadata/avatar routes, revision/cache/clear semantics,
  safe listener startup/shutdown, mobile composition and physical parity.
- [ ] BR10: independent security convergence, source/artifact docs, authorized
  dogfood deployment and signed Android/iOS qualification; no release implication.

Until BR3+ are reviewed/implemented, the codec is not a service protocol promise,
remote closure authority or a reason to advertise character availability.

## BR2 source convergence

Independent review accepted the codec and explicitly excluded runtime/lifecycle
claims. Root and independent codec/skeleton suites each pass328 tests on Python
3.14.9; root Python3.11 also passes328. Ruff and mandatory closed-import scanner
pass without scanner exceptions. Only the exact new module enters the source
inventory. The codec validates body bounds before a future transport receives it,
but its whole-buffer decoder is not itself a receive/allocation bound. BEGIN and
RESULT bodies are not typed work/custody proof until the future backend validates
them. BR3+ remain open and no service imports this codec.

A fresh source check of native ed1afb also confirms profiles.list is not a scoped
presentation replacement: its own row invokes _profile_info (model/provider etc),
reads full YAML ui_meta and discovers sibling metadata; its Desktop actor contract
is not HMP phone authorization. No such RPC or private profile read was invoked.
The external custodian path preserves the existing closed presentation reader.
