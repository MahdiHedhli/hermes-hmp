# GR1-AUTH02: canonical group transport and phone authority

Status: proposed for independent contract review. No runtime caller, native ticket,
route, capability or phone permission is enabled by this contract.

This advances the complete GR1 group feature, not a read-only substitute. The
selected native source is4162ecf11f611400fa6e5c42d2f360188ce50b39. The existing
047 input parser remains observation-only. Native APIs are present; HMP integration
and phone authorization remain unimplemented. Installeded1 is not this source.

## Exact source findings

The six-file source-pins.json binds the inspected files. The canonical client
accepts an explicit discovered endpoint without starting a gateway; its default
path can start one. Its explicit branch does not forward restart-wait refusal.
Its ticket query runs in asyncio.to_thread; cancelling that await does not prove
socket/thread settlement. GatewayClient.rpc sends before starting its answer wait
and has no explicit pending-request count limit. These are wrapper requirements,
not an assertion of a deployed vulnerability.

A profile-scoped interactive ticket grants create/read/submit/control/approve/
respond session capabilities together. The SSH tickets command instead requests
host scope for interactive and refuses a profile selector. Neither is an HMP phone
grant. No ticket, subject or native connection is returned to a phone. Do not use
the host-scoped SSH command or forward a dashboard identity as an integration
shortcut. Successful redemption consumes a grant; its30-second TTL is an admission
limit, not proof an admitted connection expires after30seconds.

## Complete implementation target

Use the native canonical room service and its durable room/event/member semantics
for discovery/history, creation/membership, send, Stop/Continue/Retry/Discard,
approval and reconnect. Do not fan a group message into Bot Chat requests or build
a shadow room runtime. Peer invitation/revocation remains a separate explicit
operator contract; existing Jobs/Models Controls and approval ownership grant no
peer or group permission automatically.

## First transport slice

Implement an internal endpoint-only owned transport, initially with no production
caller. Freeze and test its lifecycle against synthetic transports before native
integration. It must not accept caller-provided URLs/homes/subjects/callables from
HTTP parameters. Only the original adapter-bound native authority supplies the
endpoint and immutable instance/profile/listener generation. Explicit endpoint
absence or unsupported admission policy is unavailable, never auto-start or remote
fallback. Concrete API/dependency refusal is separate from version metadata.

Every native operation requires an internal operation record registered with the
actual HMP authority owner, bound to original instance/device/token family,
canonical profile, room identity where applicable, operation and authority
snapshot. Constructing a well-shaped record is not authority. There is no new
public grant flag in this slice. A full phone group entitlement contract, including
admin grant/revoke semantics, must converge before routes can be activated.

Native owner room checks do not replace phone bot membership. Detached native
room-table fallback is prohibited. A room containing a hidden/unauthorized member
must not expose existence, members, counts, logs or attachments to that phone.
Authorization must remain valid through native acquisition and output, not merely
a separate state-then-log precheck. If current APIs cannot supply a reviewed
native-owned membership/snapshot fence, withhold that operation and record the
precise primitive gap; do not infer an upstream gap from an untraced path.

## Ownership and finite bounds

One original nonrenewing operation deadline starts before any queue/admission
waiting and covers ticket acquisition,
WebSocket dial, request send and response. Internal phase timeouts may only reduce
remaining time; dequeue never renews the original deadline. Timeout retires output,
never proves a thread/socket/write stopped.
No automatic retry of acquisition with uncertain credential or mutation outcomes.
An old-owner restart-policy compatibility retry is not an allowed implicit bypass.

The following numeric limits are provisional design ceilings, not an accepted
compatibility result: validate them against complete canonical method, paginated
log and attachment shapes before freezing production transport. If any full
feature shape needs a different bound, review that change; do not truncate or
reduce functionality merely to satisfy this initial budget.

At most one active connection attempt per exact authority binding, one reader per
connection,16 pending requests and64 waiting operation descriptors per owner.
Descriptors carry no credentials or raw result. Bound encoded request/frame to
1MiB, decoded event/result aggregate to8MiB and queued events to256; charge before
retention/conversion and include simultaneous copies. These are application-owned
logical-byte limits, not RSS claims. Full group logs/attachments require bounded
pagination or their separate media transport; never silently truncate results.
This transport must not inherit the generic client's16,384-event overflow queue.

The8MiB aggregate is shared across pending responses, queued events and every
simultaneous application-owned encoded/decoded/conversion copy, including
completed results waiting for publication and retired-generation debt. Neither
per-queue limits nor reconnect create another aggregate. Descriptors have a
separate total64KiB bound across all64 descriptors; charge immutable scope and
request metadata before enqueue. Library WebSocket receive/decompression/JSON
working buffers need an explicit independent bound/configuration and measured
qualification; the application retention budget does not claim to cover them or
arbitrary parser heap. Reject before allocation where the format permits it;
otherwise qualify the decoder's bounded input/structure separately.

Revocation, retirement, close and cancellation use an out-of-band control lane
that cannot wait behind a full application queue. Withdraw publication promptly,
then retain/drain the actual producer and payload debt. A full queue must not
starve these controls, discard terminal outcome evidence or be solved by an
unbounded overflow/priority queue. Test queue saturation concurrently with each
control and a stalled consumer.

Preown ticket-worker record before starting it and retain actual worker, socket,
read/write handles and known close/join state. Use supported explicit endpoint and
same-user control policy, with restart admission refusal actually carried and
identity/protocol readback checked. A canceled future is not drain. A lost start,
close or join retains bounded debt and blocks replacement rather than opening a
new budget. No private thread termination, kill or arbitrary native monkeypatch.
If the supported client cannot expose necessary custody, implement a reviewed
HMP-owned protocol adapter using the documented local socket/ticket/WebSocket
contract, not an in-process forged AuthorityConnection.

Connection retirement fences output immediately, then joins reader/writers and
ticket worker before releasing authority/resources. Reconnect requires actual
settlement or shared retained debt; no fresh pool hiding old unknown work. Store/
identity shutdown follows those owners. Retain original outcome/operation ID for
ambiguous writes; disconnection after possible send is not definite failure and
never causes automatic replay. Native admission acknowledgement is not every
member's completed turn. A later result cannot overwrite a newer generation.

## Error/privacy and acceptance

Use fixed bounded internal reason enums and standard HMP lifecycle semantics.
Before authorization, deny without resource-existence details. After exact scope
is authorized, distinguish missing native service, unavailable API/dependency,
restart/drain, busy, timeout and revoked rights. Never publish ticket, local path,
subject, raw native error/traceback or foreign room information.

Acceptance must cover wrong instance/profile/device/family/room; partial and
revoked bot grants; membership changes before/during/after read; detached driver;
stale discovery/restart admission; failed/unknown worker start/close/join; full
queues; blocked send; lost acknowledgement; cancellation during each phase;
reconnect/Store shutdown; unchanged caller data; no implicit retry or unrelated
writes. Run native TLS/current/minimum-platform integration only after synthetic
causal tests and independent security review. Signed Android/iOS physical,
accessibility/storage/provider/security-release qualification stays separate.
