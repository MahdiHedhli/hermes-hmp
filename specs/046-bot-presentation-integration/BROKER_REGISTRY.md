# BR3b/BR5b retained broker operation registry — accepted admission contract

## Product requirement and scope

A disconnected or cancelled character request must not orphan a reader, reuse its
slot while cleanup is unknown, replay work, or ACK another operation. The broker
must strongly retain the exact reader owner before launch and keep terminal
observations globally consistent across the original and STATUS connections.
This serves the full desktop name/classic/blobatar/custom-image integration.

This is a separate broker-side registry, not the gateway JobManager. The latter's
GROUP_GONE/SIGNAL_CLOSED and automatic terminal eviction cannot represent shared-
group custody or the broker's explicit global ACK. Do not forge those events or
modify the existing direct manager/supervisor to accept weaker observations.

No service, socket, route, capability or live host/device change is activated.
Authentication, peer/endpoint/runtime qualification and original phone/native
rights remain mandatory outer gates. Binding tokens are correlation only.

## Fixed scope and bounded admission

One registry belongs to one exact qualified iid/listener/broker-boot scope. A
separate source object is not permission to reset replay state or replace a live
scope. Retain immutable scope values and detect drift stickily. Do not accept
callbacks, request-selected parser/executable, arbitrary owner factories, native
services or privilege decisions in registry calls.

One non-reentrant lock serializes admission, queue promotion, resource ownership,
terminalization and ACK. No awaits while holding this lock. Capture the fixed launch recipe once at
registry startup; every constructed child owner must expose only its frozen
configuration for an exact closed-value comparison against that startup recipe,
never accept a request-selected recipe for launch. No foreign equality,
hashing, iterator/property callback or coercion may select an owner, slot or key.
Validate exact closed types before looking up keys. A malformed call refuses;
observed retained-state drift or reentry poisons the registry and retains owners.

Validate exact BrokerBinding, canonical profile and METADATA/AVATAR kind, capture
immutable copies, then consume its serial through the retained ReplayWindow
before capacity decisions. A refused admission burns that issued serial; no
capacity failure or ACK rolls back replay history. Connection channel belongs to
the original operation. STATUS lookup uses the same iid/listener/boot/operation
with a fresh authenticated channel; it never changes the retained original
channel, input, owner, deadline or operation kind. No lookup by profile alone.

Limits from presentation_jobs: active<=6, METADATA<=4, AVATAR<=2, one active per
canonical profile across both kinds, waiting<=16, terminal journal<=64. Queued
operations keep the original absolute input3 monotonic deadline; queueing never
starts a new two-second interval. Capacity/unknown debt is shared across all
listener connections in the registry. A broker boot must also bound the number
of registered listener scopes; multi-listener aggregation is a later service
startup gate, not permission to instantiate unbounded registries.

Reserve terminal-journal capacity for every admitted queued/active operation:
retained terminal + queued + active <=64. Do not evict an unacknowledged terminal
tombstone to admit work. Unknown active ownership continues counting against its
active/type/profile reservation; unknown queued ownership retains its queued
reservation and journal capacity. Refuse admission before any owner creation or
spawn if a bound cannot be met. Stable FIFO promotion may skip a blocked profile
only under the same original deadline; no automatic fairness or expiry claim is
made by this storage layer.

## Exact owner retention before launch

Registry creates an internal operation record and stores it strongly before
constructing its fixed BrokerChildOwner. Bind that owner to the exact record by
identity, store it before any start call, and never expose its Popen or remove it
on exceptions. Constructor failure before a returned owner is retained as unknown
record; no retry or automatic unlaunched classification. A record with a returned
owner is held through every start, signal, wait, pipe and protocol failure.

A source-only admission/retention slice may precede the actual broker resource
binder. It must have NO started-owner terminal/release API until the binder's
owner-minted, exact operation/boot-bound full cleanup observation exists. It may
seal and journal an explicitly never-started queued/reserved owner: call its
one-use seal_unlaunched and validate exact owner/binding/current observation
before moving to the terminal journal. An attempted or ambiguous start is never
sealed, dropped or ACK-released through this path.

The eventual registry start path marks intent and moves the queued reservation
to active atomically before the only owner.start attempt. It captures the same
operation/deadline/authority generation after every later callback/await. No
return from an exception can reset start intent or restore publication. A status
or ACK call cannot call start, signal, rebind, refresh native rights or execute GO.
Actual pipe/control owners must be registered before any input transfer. Owner
retention is necessary but does not establish syscall/hard wall-clock bounds.

## Terminal observations and one global ACK

Known terminal state means either explicit never-launched sealing as above, or
one future topology-specific resource binder observation joining exact child
wait, owned result/diagnostic EOF+close, input/control close, qualified fixed
no-spawn/no-FD-transfer runtime premise and exact operation identity. Reap, socket
EOF, peer PID, timeout, output JSON cleanup flags or arbitrary boolean is not such
an observation. Native/work resources remain separately held in the gateway;
broker terminal state alone never releases the gateway's native reservation or
authorizes HTTP output. Original native pre-emit and work/source validation stay.

The first valid terminal transition stores only a bounded closed summary, wipes
result/input payload references, and retires the active/type/profile reservation
once while retaining its terminal-journal slot and exact safe owner/fact until
ACK. No RESULT body is retained/replayed for STATUS. If wiping/closure validation
is uncertain, keep debt and do not issue CLOSED or release capacity.

Original and STATUS ACKs converge on one atomic registry acknowledgement for the
same exact terminal operation and boot. The first valid ACK removes that journal
entry only after its retained fact is revalidated. Duplicate ACK is idempotent
and cannot release or affect anything else. To avoid an unbounded ACK-history
set, distinguish 'no matching terminal entry' from fresh work; it may return a
bounded already-absent/no-op outcome, never assert past closure or permit replay.
The retained ReplayWindow still refuses any old BEGIN. Delayed ACK for an aged-
out/unknown operation, changed boot/instance/listener or guessed identity cannot
retire a current operation. Wrong channel on STATUS is not a lookup shortcut;
outer exact authenticated scope and fresh status grammar are still required.

STATUS returns only PENDING for retained active/queued/unknown debt, CLOSED for a
revalidated known terminal fact, and UNKNOWN when no verifiable record remains.
After ACK, UNKNOWN is truthful: this layer need not prove historical closure.
No input/result bytes, paths, model/provider data or native credentials appear
in summaries/status/errors. Broker crash/restart/EOF remains gateway UNKNOWN;
new registry state never certifies old process/resource closure.

## Implementation sequence and acceptance

- [x] Independent contract review, especially journal reservation, type/profile
  aggregation, channel-independent global ACK, and never-launched exception path.
- [x] BR3b source admission/retention and explicit unlaunched sealing/ACK, no started
  release. All records/owners retained before start; no service runtime imported.
- [ ] BR5b separately reviewed actual resource binder: child wait+owned pipes+
  control+qualified runtime premises, original deadline and frozen cleanup budget.
- [ ] Integrate binder-only terminal transition and global idempotent ACK with
  no-result STATUS, no auto expiry/eviction or restart-based release.
- [ ] Causal tests: capacities/type/profile/queue/journal bounds, independent
  connections racing ACK, duplicate/cross-scope/rebound/coercible keys, serial
  replay after ACK/eviction/refusal, start/constructor/close uncertainty retention,
  exact owner retained before observable launch, cancellation/deadline/revocation
  races, wrong operation/boot/fact, no result replay or unrelated release.
- [ ] Exact actual child/process pipe tests plus source tests and independent
  security convergence. Physical/service/release qualification remains distinct.

## Reviewed admission slice and remaining resource binder

Independent87 registry/child cases pass. Root registry/child/direct-process/probe/
codec/peer/lifecycle/inventory union548 cases pass on Python3.11 and3.14.9 on this
Mac, plus lint and closed-import scanner. The actual fixed reader received empty
input only; real result/diagnostic EOF and exact child reap left its reservation
ACTIVE/PENDING and unacknowledgeable. No profile input, GO, service or native
permission was used. No owner is dropped on uncertain constructor/start outcomes.

The source registry captures a fixed startup recipe and checks every constructed
owner against it. Before any start, it validates exact type/profile/aggregate
capacity, original deadline and retained ownership. A review-found delay race is
closed with state/deadline checks after ownership validation, inside the owner
immediately before Popen, and after spawn returns. A late observed launch retains
the exact returned handle and ACTIVE unknown reservation without normal return.
These are freshness checks, not a syscall wall-clock containment guarantee.

Never-launched sealing is independently revalidated under the registry lock
before CLOSED or global ACK removal. Lookup excludes channel only because the
outer authenticated original/STATUS grammar remains mandatory. Unknown/started
records cannot take this path; there is no started-owner terminal API. Replay
history survives ACK and capacity/deadline refusal. All key types are validated
before map lookup, and poisoned or rebound retained state cannot emit CLOSED.

Actual started-resource binder, result/input wiping, terminal custody handoff,
wire transport, global multi-listener capacity, native gateway backend, runtime/
service qualification and physical character delivery remain open. This source
slice does not advertise a capability or make the feature available on devices.
