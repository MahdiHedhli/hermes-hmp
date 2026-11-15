# BI1 native presentation service — architecture amendment for review

Status: independently accepted NS1 implementation contract, November11,2026.
Root owns implementation. No route/capability,
installed software, permission or live file read is enabled by this proposal.
The original broker/credential/RGA branch remains preserved and unqualified.
This is a replacement implementation for the SAME complete BI1 feature, not a
metadata-only fallback or a waiver inside the old broker's security boundary.

## Evidence and decision

The current046 contract selects a delegated reader/broker, credentials, original
GO/result transport and exclusive child/reaper custody. Its startup/source/link
attestation and RGA gates are necessary for THAT architecture. They are not an
intrinsic dependency of drawing a character or existing HMP authentication.
The independently qualified029 native GatewayRunner/adapter/Store/TLS/Dart/Flutter
media route does not import hmp_startup or rely on those gates.

Inspected nativeed1/e0f078 profile APIs do not supply a suitable replacement:
profiles.list traverses broad configuration/model/provider metadata before
projection; get_asset accepts a general asset selector and uses unbounded,
link-following reads; read_profile_meta supplies name/title only. Do not wire or
post-filter these APIs. No ready full-parity native getter is asserted.

Implement a NEW HMP-internal native presentation/asset reader under the same
trusted installed native runtime premise as029. It is bound to the actual native
adapter/listener, original bridge/Store/identity and selected dependency runtime.
No upstream core edit, new provider, credential, signing key or permission grant
is required. The delegated-broker boundary is absent; its GO/key/process/reaper
proofs are inapplicable here, rather than silently marked passed. Never treat a
new native result as an old OwnedWorkerRead, broker receipt or signed GO result.
The old architecture is not an automatic runtime fallback.

## Full output contract retained

Retain the existing authenticated capability/version and presentation/avatar URL
contracts and closed DTO: version/iid/profile/display_name/name_source/character/
metadata_revision/avatar/observed_at, at most4096 decoded bytes. Preserve complete
name, all seven classic shapes, color, blobatar-v2 and custom static PNG/JPEG/WebP
parity, canonical revision rules and clear/rename behavior. Reuse the existing pure
projection/Unicode policy, bounded event reduction and raster structure checks
where their contracts fit. Do not truncate the feature to avatars:null.

Keep fixed profile.yaml presentation projection and fixed assets/avatar.png,
avatar.jpg,avatar.webp selection only. Refuse multiple ambiguous fixed images.
Metadata input <=65,536 bytes; avatar <=2,000,000 bytes, edge<=1024 and declared
pixels<=1,048,576. Never read config.yaml, SOUL, prompts, conversations, provider
secrets, credentials or an arbitrary caller-selected file/URL. No profiles.list,
general asset RPC, directory export, redirect, SVG or animated fallback.
Raw paths, YAML, exceptions and object graphs never cross the response boundary.
The client still performs its bounded decode; structure admission is not decoding.

## Authority and listener lifecycle

Bind the private native interface through actual normal adapter startup, following
open_components/async listener lifecycle ownership. Retain original bridge,
Store/identity/IID and listener generation; create no profile worker before request
authorization. Capability1 advertises only while the bound service is healthy.
Unknown Hermes version metadata alone does not disable it: attempt the supported
minimum contract and concrete required APIs/primitives. Genuine missing safe APIs/
OS/dependencies give precise optional-feature diagnostics, without gating chat.

Use original bearer/HMP-Instance authentication, device/user/token-family and
current authorized canonical profile/bot policy before resolving the native home.
Use the existing narrow routing-home interface, not a broad profile/config API.
Recheck native authorization/home/current listener and original headers before
emission; observed revoke/switch/retirement and stale await generations cannot
publish a result. Native external edits after the last observation are not claimed
atomic with socket delivery; preserve the explicit observation scope below.
Jobs/default-model Controls, approval ownership and mode-admin are unrelated.
The request supplies profile and optionally a hex revision, never a home/path,
callable/backend/dependency/module name or authority boolean.

Bind the actual selected parser/native operations at listener startup; no request
activation of .pth/sitecustomize or arbitrary imports. Preserve trusted package/
native runtime ownership and detect retired listener/binding changes, without
reimplementing whole-process executable attestation on each metadata request.
No legacy broad API or broker is substituted after a failure.

### Health and HTTP outcomes

Transient queue/backpressure/deadline outcomes do not withdraw capability. Only
retirement, missing required safe primitives/dependency or a broken native binding
makes the service unavailable; an unrelated chat/jobs capability stays unchanged.
Use standard ERR-1/ERR-2 shapes: malformed profile/revision400 bad_request;
original credential/IID failures retain401 lifecycle semantics; native bot denials
retain existing403/404 masking before any file lookup. Busy operation/profile/
queue is409 busy (retryable only by a new explicit request); rate enforcement is
429 rate_limited. Expired work or unavailable/unreadable/refused/mutated source
is503 presentation_unavailable, an optional forward-compatible error code; no
credential retirement or implicit retry. Unsupported/absent optional route keeps
404/405 fallback for older clients. A stale avatar revision is404 not_found,
never a new image under the old revision URL. Add matching contract/client tests.

A positively observed missing fixed avatar is legitimate avatar:null metadata
(or404 for its fixed avatar URL). Ambiguous multiple images, unreadable files,
unknown ownership/close, structural refusal or observed mutation is unavailable,
not silently converted to absence. Apply the same absence/error distinction to
optional presentation fields/profile metadata with the native default rules.
Revision binds actual returned bytes; source recheck/clear/rename semantics remain.

## Bounded native work and file custody

Use explicit owned native worker records, not an anonymous fire-and-forget
asyncio.to_thread result. Retain actual Thread/start/join state and read handles
before callbacks or awaits can lose them. At most16 queued operations, six actual
workers (four metadata/two avatar), one active request per canonical profile;
retain claims through unknown start/close/join. No new worker replaces unsettled
work after a timeout. Limits are per listener across profiles, with explicit raw/
parser/raster/result memory budgets and the029 aggregate contribution documented.

One original nonrenewing two-second operation budget covers queue, native policy,
file and parse work and pre-emission checks. Timeout retires output immediately;
it does not prove a blocking native syscall or thread stopped. Event-loop waiting
is bounded while actual resources remain owned until known termination/closure.
Do not claim a hard native-operation lifetime bound. No new OS process, broker
signing, process-group probing/kill or reaper is used by this route.

The following accounting table is frozen for application-owned representations;
all amounts count live logical data lengths, including simultaneous conversion
copies, rather than allocator capacity/interpreter object overhead or OS/TLS/kernel
buffers. It is not a process RSS guarantee. Charge before allocating/retaining
and release only after actual ownership moves or the object is dropped.

| Retained state | Limit and ownership |
| --- | --- |
| Waiting descriptors |16 x4096 maximum copied header/profile/revision/lease/control bytes; zero raw YAML/image/parser/result buffers |
| Active operation logical payload envelope |16MiB/64 live buffer reservations each, six slots retained across running/result/emission/unknown states; no unleased completed-result queue |
| Read representations |Total read credit4,131,076; separately include original chunks/bytearray and simultaneous immutable conversion copies in16MiB envelope |
| Parser state |One SafeLoader pass live at a time, raw input65,536, decoded text at most4x input scalar count; token2048/event1024/node256/depth8/scalarUTF81024 consumption caps; close/dispose both sequential scan/event passes before result publication |
| Parser internal objects |Bounded input plus trusted parser implementation/work limits; no claimed exact Python heap cap. Qualify peak native memory under worst-case bounded inputs; no parser/traceback/future retains a completed request's raw data |
| Result mailbox |One closed result per slot: metadata4096 or avatar2,000,000 plus bounded descriptor; future returns status only, not payload; late/finished handler drops payload |
| Streaming scratch |64KiB application slice plus64KiB high-water allowance per emitting slot, counted inside16MiB; no second full image copy for streaming |
| Presentation aggregate |6 x16MiB +16x4096 logical presentation payload envelope (100,728,832); unknown native/result/emission debt keeps its slot, so it cannot multiply capacity |
| Existing029 coexistence |Source caps4 leases/4 workers,8MiB payload each. At simultaneous read-conversion allow2x8MiB+2x64KiB per lease:67,633,152 logical bytes. Keep its existing admission accounting unchanged; verify this bound against actual bridge/file/sink code before enabling combined service |
| Planned combined payload envelope |168,361,984 logical image/presentation payload bytes for the two services under the above source assumptions; not hard RSS. If native tests reveal another retained copy or unbounded channel, fix the implementation/table before advertising |

Source acquisition/projection/final authorization has its one nonrenewing two-second
deadline. Once a complete closed result is authorized for output before that
deadline, HTTP writes use one separate nonrenewing30-second prepare/write/EOF
budget like029. It cannot renew acquisition or authorize another read; current
listener/device-family/authority fences still govern output, and a failed/late
write aborts transport without a second body or retry. Keep the operation slot and
result ownership through actual writer settlement. Test this distinction explicitly;
neither budget proves an OS thread or already buffered network bytes ceased.

A native-read-specific capability, issued only by the actual authorized service,
binds canonical native home/profile/listener/operation/deadline and work ledger.
Its object identity must be registered in the actual service live-operation registry
and joined to the held native authority/listener snapshot; copied well-shaped caps
or current-home strings alone cannot authorize I/O.
Do not fake the old worker GO challenge to reuse its high-level reader. Reuse
lower-level proven file-custody logic only with an explicit native-read contract.
Open fixed names relative to held native directory FDs with no-follow/nonblocking/
close-on-exec where supported; enforce canonical home/component, owner/mode,
regular-file, inode/device/link and pre/post-read/path identity rules. Charge
before every operation and chunk; bound retries and refuse unknown closure.
No raw FD or mutable file object is returned to the HTTP layer.

Retain the existing nonresetting PresentationWorkLedger limits: read_bytes
4,131,076; hash_bytes2,000,000; opens80; metadata1024; path_bytes32,768; yaml_nodes
256; yaml_tokens2048; raster_units10,000; at most34 held FDs. The closed reducer's
event1024/depth8/scalarUTF8-1024 limits remain. Bound live retained byte buffers and
queued results in addition to total work credit; stream token/event consumption
and dispose parser state. Account aggregate presentation payloads across all six
workers and the actual029 bound separately. These are logical input/work/payload
bounds, not a claimed process-RSS hard limit. The accounting table below fixes logical channel limits; native source/fault tests
must verify actual buffer ownership and disposal before activation. No unlimited
raw diagnostic/body queue is permitted.

Run parser/scanner work off the event loop under byte/token/event/depth/work caps;
no YAML graph construction, aliases/tags or execution. Preserve exact static image
revision/content joins. Close every original FD through actual observed close;
ambiguous close retains debt and is never retried using a possibly reused number.
Cancellation/handler completion cannot release active or ambiguous worker claims.
Listener shutdown withdraws capability/output, drains actual workers/FDs/writers
first, then retires Store/identity/native authority. Cover disconnect, failed or
cancelled connect, partial service construction, bind/listen failure and server
error cleanup; adopt each partial owner before the next acquisition. A cancelled
future is not drain and no exception path may jump directly to Store.close. Stalled/unknown debt is visible and bounded.
Retained capacity/debt survives listener replacement and reconnect. A failed or
retired generation with unsettled worker/FD/writer ownership cannot be replaced
by a fresh six-slot pool that resets accounting. Block replacement of this service
until actual drain, or charge old and new generations to the same retained native
owner budget. Other ready HMP feature families need not be disabled.

File/auth observations do not lock external edits atomically. State the actual
observation scope, refresh on explicit request, and never claim instantaneous
cross-process edit/clear semantics without a native primitive.

## Client and compatibility behavior retained

Preserve original instance/profile/foreground epoch/connection generation;
clear/dispose metadata and decoded images on scope/roster/revoke/unpair/background
changes. Saved rows do not fetch; local explicit icon priority and accessibility/
reduced-motion behavior remain. Existing mobile DTO/transport/renderer work is
reused, not weakened. Android/iOS signed physical qualification stays separate.
Supported Linux/macOS safe primitives and missing Windows equivalents are tested/
documented explicitly; no unsafe follow-link fallback or version allowlist.

## Build and acceptance tasks

- [x] NS1: independent contract/security review; freeze exact dependency/authority/
  filesystem/worker lifecycle and amend canonical046 contract explicitly.
- [ ] NS2: implement a real narrow native read capability/backend and full pure
  projection/YAML/raster composition; prove no broad/private API or file access.
- [ ] NS3: implement owned bounded scheduling, current auth/home/source/revision,
  cancellation/timeout/late result/unknown close/start/join and listener drain.
- [ ] NS4: bind actual native adapter/ServerContext and authenticated endpoints;
  advertise only this service's capability, preserve old broker closure.
- [ ] NS5: causal unit/fault/isolation/concurrency/privacy tests, exact minimum and
  current runtime checks, mandatory scanners and independent source review.
- [ ] NS6: actual original native GatewayRunner/adapter/profile authorization and
  production TLS/Dart/Flutter full name/classic/blobatar/static-image journeys;
  mutations/revoke/clear/rename/background/cleanup without fake full access.
- [ ] NS7: Linux/macOS and signed Android/iOS physical/decode/storage/accessibility
  qualification, artifact/release security and truthful documentation/Gist.

These tasks preserve the original full roadmap objective. A failed gate does not
become a pass because the architecture changed; obsolete broker-only requirements
must be marked inapplicable to this separate route, with their evidence preserved.

## Implementation sequence and analysis checklist

1. Portable native operation/capability/registry and length-based memory/work
   accounting; no filesystem access or feature activation at import/construction.
2. Native authorized routing-home binding and fixed no-follow file transaction;
   new native-read capability semantics, pure projection/YAML/raster reuse only.
3. Actual owned worker/mailbox/scheduler/drain; failed/late acquisition and every
   disconnect/error/partial-bind/reconnect transition preserve capacity and owners.
4. Private factory and existing authenticated URL/capability wiring; one service
   only, no broker fallback or inherited worker GO semantics.
5. Exact-source causal/privacy/authority/resource/compatibility review, normal
   native factory plus real production TLS/client/UI journey, then authorized
   device artifacts/physical and release qualification.

- [ ] Complete name/classic/blobatar/static-avatar output, revision and clear/rename
  parity; no metadata-only substitute, no client scope/lifecycle regression.
- [ ] Whitelist source acquisitions and prove no broad config/profile/asset API,
  private file, credentials or user-supplied backend/path/callable reaches reader.
- [ ] NativeReadCap identity/current-generation/actual native authorization and
  original token-family checks survive every asynchronous phase and stale result.
- [ ] Shared operation work/memory and retained-generation debt remain bounded;
  known close/join/writer settlement is necessary to reclaim a slot.
- [ ] Busy/absent/unavailable outcomes and2s acquisition/30s emission clocks follow
  the exact contract; no false native lifetime/RSS/atomic external-edit claim.
- [ ] Native normal/fault source tests plus Android/iOS physical/platform/security
  gates prove only their actual scope. Unsupported safe OS primitives remain an
  explicit platform gap with fallback; no unsafe replacement.

Independent character_custody_review accepts NS1 direction and fixed outcomes,
identity-bound capability, deadlines and logical envelope. Its final lifecycle
correction (retained debt across reconnect/replacement) is incorporated above.
No NS2–NS7 result follows from this contract acceptance.

### NS2 bookkeeping convergence

presentation_memory is the first portable native-service source component. It
performs no file read and grants no authority. Both current/minimum runtime17-case
suites independently pass with identical cases, matching log/XML hashes and559
source maps; identity-bound stored-size leases reject forged/changed/duplicate
release and concurrent overbooking. Its explicit memory tickets do not prove an
actual producer charged every buffer, nor settle worker/FD/writer debt. Those
integration and native evidence requirements remain unchecked above.
