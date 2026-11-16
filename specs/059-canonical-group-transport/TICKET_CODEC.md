# GT3-CODEC — native control-ticket DATA boundary

Status: unactivated source component; no runtime caller, native import, socket,
real ticket mint, device permission or WebSocket exists in this component. This
does not complete GT1 or GT3. The native source sample remains4162ecf1.

## Fixed request and reply

build_group_ticket_request accepts exact built-in nonempty UTF-8 strings for
profile_id (up to4096 bytes) and instance_id (up to256 bytes), rejecting NUL,
surrogates and oversize character counts before encoding. The actual future owner
must supply the already verified adapter-owned native binding, never HTTP-selected
identity/home/path/backend. The codec is not that binding or authentication.

The returned immutable bytes contain exactly protocol1/id1/session-ticket,
purpose interactive, scope profile and restart_wait refuse. There is no subject,
host scope, gateway start or policy-dropping retry. This carries the native restart
admission policy; it does not prove that a future socket redeemed it or was admitted.
The broad native interactive capabilities are never HMP phone rights. This codec's
profile scope is not proof every served sibling is seatable; full multi-profile
room routing and grants remain GT1 decisions, without implicit scope broadening.

parse_group_ticket_reply requires exclusively owned exact immutable bytes with
one terminal LF, at most65,536 body bytes. The actual reader must enforce this
BEFORE acquiring/retaining bytes. UTF-8/JSON recursion, malformed numbers,
duplicate keys, extra framing and raw error replies produce one fixed refusal.
The error does not chain the JSON decoder's diagnostic. This is not a guarantee
that ordinary Python caller stacks/strings are securely erased.

The bounded projection accepts at most8 keys per object, each at most64 UTF-8
bytes. Extra fields must be bounded scalars: None/bool, signed64-bit int, finite
float or at most256 UTF-8 bytes of text. Empty optional text is harmless and
ignored; nested objects/lists or oversize ignored metadata are not retained.
Required protocol and request ID are exact integers, not bool. The result must
match the original profile/IID/runtime protocol, contain a positive signed32-bit
expiry observation and a1..256-character WebSocket subprotocol-compatible token.
The exact expiry observation is DATA, not connected-socket lifetime or HMP rights.

The frozen result contains only ticket and expires_in_seconds. repr=False is
logging hygiene, not secrecy or authority: Python code can read its fields, and
it must never be forwarded to a phone, logs, public diagnostics or an issue body.
Actual same-user peer credentials, listener generation, native admission and all
HMP device/profile/room/bot authority remain mandatory in the actual transport.

## Successful-envelope size proof

The native control server has a512KiB generic response ceiling, while the generic
client uses64KiB. This codec intentionally supports only the closed successful
ticket shape, not arbitrary control responses or group RPC/media frames.

UTF-8-byte-bounded profile and IID use at most6 ASCII-escape characters per input
byte under the native default json.dumps escaping:24,576 and1536 respectively.
The token is at most256 unescaped ASCII bytes. At most7 optional scalar values
across the two8-field objects contribute no more than7*1536 bytes; bounded keys,
fixed required keys, numbers, punctuation and native whitespace fit the remaining
margin. The explicit worst-shape test (maximum legal non-NUL control characters,
keys/scalars, token and expiry) is below44,800 bytes, comfortably within65,536.
This proves this successful shape's encoded bound, not JSON heap/RSS or an
arbitrary future metadata object. The separate20,000,000-character attachment
surface must not be squeezed through this control-ticket limit.

## Verification and remaining work

85 focused cases pass against fresh isolated home/runtime and synthetic bytes.
Disposable-copy guard omissions cause the intended failures: ID type1, profile
binding1, duplicates2, frame limit1, restart policy1. Production source stays
unchanged throughout. Focused Ruff passes. No native core function is executed.

Next integrate a concrete owned local socket exchange against synthetic private
Unix peers: original absolute deadline before queueing, retained actual socket
before connect/send, kernel peer UID, original request/binding readback and actual
close/worker settlement. Unknown start/close must retain debt and prevent automatic
retry/replacement. Then separately qualify native/WebSocket and full HMP authority
before any route/capability activation. Signed physical and release checks remain.
