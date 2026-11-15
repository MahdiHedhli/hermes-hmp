# Internal signed READY dispatch — November 6, 2026

The existing `RemoteOperationOwner._begin_ready_exchange` credential branch now
uses `NativePhaseWorkOwner.exchange_ready` after its existing PRE_GO, native
BEGIN_INTENT, reserved send intent and signed preparation. Before returning True
it rechecks the exact retained transition/current receipt and native READY state.
The existing `_retained_local` fences preserve credential/channel/native-input
identity. The unsigned send/receive branch remains noncredential-only; generic
credential GO/CANCEL/result gates remain closed. No startup/key selection factory,
resource admission, deployment or worker GO permission is added.

Component tests now intercept the signed exchange seam instead of unsigned
`SocketChannel.send`. The signing-only test explicitly refuses at that seam and
retains its zero-IO scope. Three direct tests exercise actual `remote.begin_ready`
and original cleanup allocations: valid signed READY publishes the existing
barrier while original work remains parked; a bad signature publishes no READY;
an existing cleanup request during fresh PRE_GO wins before READY publication.
All three pass. Actual owned cleanup joins original work, with UNKNOWN retained
where signed cleanup relay is still unimplemented; no manufactured native release
or unsigned cleanup fallback is credited.

Independent read-only implementation review accepted this bounded dispatch slice.
Configured lint and diff whitespace checks pass. Full affected regression before
the final explicit producer/remote identity join: **1,444 passed, one skipped**,
65.99 seconds. After that join: **172 focused tests passed**, 13.57 seconds.
Independent final identity-check readback review accepted the explicit joins.
Prior unexplained cancellation observation remains recorded separately; later
passes do not establish its cause. Character delivery and physical/release
qualification remain incomplete. No live host, settings or mobile build changed.
