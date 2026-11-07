# Presentation credential handshake source checkpoint

The retained credential handshake actor and channel exclusion were independently
accepted in source review on November 6, 2026. Root's final focused regression
run passed **452 tests, one skipped**, in the isolated PM-built Python 3.14
requirements environment. Review inspected source and tests without executing
those tests. The earlier environment lacked the declared PyYAML dependency and
stopped during collection; it supplied no regression pass. The replacement test
environment uses the native lock's PyYAML 6.0.3 and the prior direct test/runtime
versions; no installed host environment was changed.

The actor is retained by its original SocketChannel before initialization. Its
single original task/loop/socket/cursor owns a fixed four-record exchange. Private
writes derive only HELLO, CHALLENGE, FINISH and ACCEPT from retained state, with
no caller-selected statement or generic signing endpoint. Fixed per-startup boot
and per-channel nonces come from the standard cryptographic random source.

Original role key, selection, clock and channel references remain independent
from mutable current references. Native clock boundaries receive typed local
reseals before equality, arithmetic, signing, IO or completion. The broker's
verified HELLO operation/deadline are staged metadata: its original accept end
can only become earlier, and neither value becomes native input or registry
admission. Actual input3 scope comparison remains mandatory before effects.

Each write retains intent before a potentially partial send and records local
completion only after a complete write and postcheck. Existing channel IO and
socket/clock-close entry points reject an outstanding handshake claim. Only the
original known-complete local IO fact permits external quiescence; this releases
no operation/native/custody permission. Torn writes, partial reads, cancellation,
key retirement or lost task/context retain refusal and original debt, without
resend, reauthentication or cursor replacement. Failure poisons only the
independently retained original reciprocal channel.

Tests use synthetic keys and disposable sockets. The bilateral actor models mock
native peer/channel/clock qualification. A separate boundary case uses real
SocketChannel construction, endpoint/descriptor checks and IO/close entry guards,
while mocking peer and native-clock qualification. These are not native
qualification of the credential actor, a production startup factory, executable
attestation, or a claim against hostile same-UID runtime code.

The source causals include final-sample retirement/foreign cursor preventing
sign preparation and sends, typed foreign constructor metadata without callbacks,
authenticated HELLO deadline mutation without adoption, original-channel custody
under paired current-reference substitution, actual partial-prefix cancellation,
and failed-send/reinitialization debt preservation.

Still open: paired admitted runtime/source/credential factory and rotation
fences, shared authentication capacity reservation, exact binding handoff to the
original native operation, signed phase streaming on original cursors, actual
GO and all character variants, RESULT/TERMINAL/ACK/journal/native joins, STATUS,
authenticated HTTP publication, installation and physical/release qualification.
The historical Mach incident remains unresolved. No installed credential,
permission, provider, model, job or live service was changed by this work.
