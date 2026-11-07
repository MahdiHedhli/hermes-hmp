# Credential wire v1 and original-owner transitions

Status: independently reviewed companion to [CREDENTIAL_ADMISSION.md](CREDENTIAL_ADMISSION.md).
Bounded source components are accepted as recorded below; complete production
integration remains open. No credential, signer, runtime permission or production
listener is created by this document.

## Canonical authenticated record

An authentication record is `HBA1 || u32be(json_length) || json || signature`.
The signature is exactly 64 raw Ed25519 bytes. JSON is at most 1,976 ASCII bytes;
the complete record is at most 2,048 bytes. Reject lengths before allocation.
No base64 signature, PEM, caller-supplied public key or algorithm negotiation is
accepted on this channel. Configured public keys are exactly 32 raw bytes; their
IDs are lowercase SHA-256 hex of those bytes.

JSON must equal its `sort_keys=True, separators=(",", ":"), ensure_ascii=True,
allow_nan=False` re-encoding byte for byte. Duplicate/unknown/missing keys,
alternate number spellings, escapes outside closed ASCII values, booleans in
integer slots, unsupported versions/types and trailing bytes refuse. The exact
key set depends on the record family/phase below. Every integer is an exact int,
never bool; nanoseconds are in `0..2**63-1`, with positive original work end.
Digests, key IDs, generations, boots, nonces and channel IDs are 64 lowercase hex;
listener is 32 lowercase hex and iid uses the existing canonical instance codec.

Signing bytes are the family domain followed by `u32be(json_length) || json`:

- Handshake: ASCII `HMP-BI1-CREDENTIAL-HANDSHAKE-1` followed by one `0x00` byte.
- Phase: ASCII `HMP-BI1-CREDENTIAL-PHASE-1` followed by one `0x00` byte.

`v=1`, `alg="Ed25519"`, role and direction are signed, not inferred from a
socket. Roles are `gateway|broker`; directions are `g2b|b2g`. A gateway record
must be g2b and a broker record b2g. Each verifies only the pinned opposite-role
public key for the retained installation generation. No fallback algorithm/key,
HMP pairing key, alternate private constructor or generic signer endpoint.

## Bilateral startup transcript

Each original role owner generates a fresh 32-byte boot nonce. Each channel gets
fresh, separate 32-byte gateway and broker nonces. Use the admitted cryptographic
random source, never a clock/PID/counter fallback. One channel serves one original
operation. The operation ID retains the existing serial-plus-entropy BR3 codec;
it is not a new authorization token.

All handshake records have exactly these common keys:
`v,family,alg,phase,role,direction,iid,listener,key_id,peer_key_id,generation,
clock_domain,operation_id,work_end_ns`.
`family="handshake"`. The four closed phases add exactly:

| Order / sender | Phase | Additional keys |
| --- | --- | --- |
| 0 / gateway | HELLO | gateway_boot,gateway_nonce |
| 1 / broker | CHALLENGE | gateway_boot,gateway_nonce,broker_boot,broker_nonce,hello_sha256 |
| 2 / gateway | FINISH | gateway_boot,broker_boot,channel,hello_sha256,challenge_sha256 |
| 3 / broker | ACCEPT | gateway_boot,broker_boot,channel,finish_sha256 |

Each referenced SHA hashes the complete corresponding signed HBA1 record.
`channel=SHA256(ASCII("HMP-BI1-CHANNEL-1") || 0x00 || HELLO_record || CHALLENGE_record)`.
The completed `transcript_sha256` similarly hashes
`ASCII("HMP-BI1-TRANSCRIPT-1") || 0x00 ||` all four complete signed records in order.
ACCEPT does not contain that final hash, avoiding a self-referential signature.
FINISH/ACCEPT echo the exact original selections, boots, operation and deadline.
There are no optional or future extension keys.

`clock_domain` is SHA-256 of canonical ASCII JSON of the **locally qualified**
NativeClockOwner domain: exact `platform,implementation,boot,namespace` fields,
where boot is its lowercase UUID string and namespace is null on Darwin or the
qualified two-integer Linux namespace identity. A peer's signed string is not
clock qualification; require the held local/native domain and peer domain to
match before adopting remote times. This does not attest process origin.

Local accept/connect uses a fixed maximum two-second handshake end. Gateway also
uses its original request work end. After authenticated HELLO and common-clock
qualification, broker uses the earlier of its original accept end and that same
signed work end, rejecting expired or more-than-two-seconds-future ends. Nothing
renews a deadline. Startup inventory/key verification occurs outside operation
admission; per-channel work is charged to the original work budget. No profile
body or worker admission precedes mutual authentication and known complete
local handshake writes and exact received peer records. This means each owner's
own completed-write/postcheck facts, not proof that its peer observed a final
post-write check. Broker refuses BEGIN if its own ACCEPT write/postcheck is
unknown. An uncertain ACCEPT write is UNKNOWN, not authenticated work.

At most four authenticating channels are retained, charged within the existing
MAX_WAITING capacity rather than added to it. Reserve ownership before accept.
Unknown close retains its slot; a new connection cannot repair an old owner.
No more than four handshake records or 8,192 handshake wire bytes per channel.

## Phase commitment and existing body frame

After handshake, exactly one HBA1 phase record precedes each existing HBR1 body
frame. Body frames use the existing v2 grammar; no unauthenticated/v1 fallback.
Use the original single sender/reader/cursor; do not add a second parser task.
The exact phase key set is:
`v,family,alg,phase,role,direction,iid,listener,key_id,peer_key_id,generation,
gateway_boot,broker_boot,channel,transcript_sha256,operation_id,sequence,
input_sha256,scope_sha256,work_end_ns,frame_sha256,frame_length`.
`family="phase"`; phase is exactly one of BEGIN,READY,GO,RESULT,CANCEL,TERMINAL,ACK
and must equal the following HBR1 kind. Sequence equals that frame's original
per-direction BR3 sequence, in `0..3`. No independent renewable auth counter.
Frame SHA and length cover the **entire** exact encoded HBR1 header/body frame.

Gateway retains `input_sha256` of the original exact input3 bytes. Broker stages
authenticated BEGIN's intended hashes/length as **unadopted metadata** on the
original bounded cursor, not an original local input or authorization fact. It
then receives/hashes the exact frame, decodes and validates input3, independently
derives its scope hash and compares every binding before registry/resource or
worker effects. No signed, self-selected hash becomes native authority. The scope
hash covers canonical JSON with exactly:
`v=1,iid,listener,operation_id,profile,kind,expected_avatar_sha,challenge,epoch,
deadline_ns,input_sha256`. Profile/kind/expected-avatar/challenge/epoch/deadline
are taken from the same validated original input3 and native job; kind is its
METADATA/AVATAR operation. These are not new result fields or caller booleans.
Full input validation and original native scope checks remain mandatory.

Check signed phase/sequence and all held context before allocating/reading its
bounded body. Read the bounded HBR1 prefix/header once, compare decoded version,
kind, sequence, outer binding and length with the retained commitment before body
allocation, and hash prefix + raw header + body on that same cursor. Compare the
entire exact encoded frame SHA/length before adopting it or causing phase effects.
BEGIN uses the two-stage unadopted handling above. Existing first-cause,
native scope, registry and actual-resource checks follow; cryptographic success
alone returns no permission. Malformed/authentication failure latches refusal.

BEGIN needs actual original INITIAL/input scope; READY needs actual retained
child/input/READY. GO needs the original fresh PRE_GO. RESULT's presend commitment
binds held immutable candidate/header and intended length/SHA; it is **not** a
completed-write fact. Only a complete successful original write mints the separate
transfer fact required by normal OK TERMINAL. A torn/unknown write is not appended to,
refrozen, replayed or represented as completed.

CANCEL commits the exact 16-byte existing CancellationWindow body after the
original owner freezes its first cause. It binds all original context and the
current sequence. Receiver may adopt a remote window only after complete
authenticated validation and qualified-clock/budget checks; it takes the earliest
existing end, never a new duration. Local EOF/error may independently revoke and
clean up already-owned resources using an actual local cause and original local
authority/budget. That does not trust a remote window or settle another owner.

TERMINAL commits only its existing current frozen envelope and outcome-specific
facts. OK requires actual completed RESULT transfer plus actual custody closure.
Pre-READY/pre-RESULT ABORTED requires its actual invalidated-output/retired-budget
and resource-closure facts, never a nonexistent completed RESULT. Keep the existing
claim/grammar distinctions. A new cause or smaller end invalidates an old envelope,
not permission to re-sign/retry. ACK binds the exact original terminal digest
and sequence after the receiver's full validation; it remains separate from
broker journal release, actual native DRAIN and fresh PRE_EMIT/publication.

STATUS/PENDING/UNKNOWN/CLOSED phase dispatch is not admitted by this version.
Production never-started/abort uses the reviewed v2 ABORTED TERMINAL path, not a
v1 CLOSED shortcut. STATUS remains a required later contract for bounded existing
state only; its unfinished lookup/rotation/journal rules grant no dispatch now.

## Lifetime byte caps and retirement

Maximums per original channel, including both directions and without resets:

- Four handshake records: 8,192 bytes.
- At most seven phase commitments: 14,336 bytes.
- At most seven HBR1 frames: each header overhead at most 1,032 bytes; combined
  body limits are input3 8,196 + RESULT 2,008,196 + TERMINAL 4,096 + CANCEL 16 + ACK 32.
- Total: **2,050,288 wire bytes**. The cleanup subset CANCEL/TERMINAL/ACK is at
  most **13,384 bytes**, within the same total and original cleanup end.

These are wire limits, not measured resident/native-memory bounds. Existing
aggregate quotas and actual lifetime accounting remain. No extra records on
replay, error, cancellation, backpressure or reconnect. A duplicate record is a
refusal, not an idempotent second effect or a new connection allowance.

Retirement is conservative: no new signing or remote-effect acceptance after
observed key/config/generation/source retirement, including CANCEL/TERMINAL/ACK.
Do not reauthenticate to finish an old operation. Original local cleanup may
continue under already-held authority and earliest budget; uncertain remote
closure/journal settlement stays UNKNOWN. Already accepted historical facts do
not authorize fresh work, publication or a delayed newly signed ACK.

The installer/loader/key-custody and actual native owner transitions must still
be implemented and reviewed. This finite format does not silently activate the
old synthetic service or claim full delivery without real GO, all output variants,
actual custody/terminal/ACK/native joins and authenticated HTTP publication.

## Source checkpoint — November 6, 2026

The new `presentation_credential_codec.py` implements bounded canonical HBA1
record data parsing; `presentation_credential_transcript.py` checks the four
signed handshake records against supplied role pins and original context.
Neither component enrolls a runtime, creates a signer, admits GO or proves local
write completion/native custody. Phase-to-role/sequence lifecycle admission is
reserved for the retained operation owners; phase syntax alone grants nothing.

`presentation_credential_scope.py` independently derives the protected scope
from the exact bounded validated input3 packet and operation binding, without
reading a filesystem or accepting result-supplied fields.

Focused synthetic tests cover canonical/type/length rejection, all handshake
phases and all seven phase-record families, signature tampering, domain binding,
transcript splicing, correctly signed broken links, wrong pins, order, original
input changes and operation-context mismatch. The focused
suite including the existing HBR1 and input3 codecs passed 167 tests. Typed startup/key
custody, original cursor integration, actual GO/output/TERMINAL/ACK/native joins,
STATUS and authenticated HTTP publication remain incomplete. No live change or
physical-device qualification follows from this checkpoint.

### Phase commitment source checkpoint

`presentation_credential_phase.py` adds independently reviewed data-only signed
phase/context checks, bounded exact HBR1 v2 header matching before body
allocation, and a whole-frame fixture digest check. The focused suite including
input3 and HBR1 passed 183 tests (root execution; independent review read-only).
The original receiver must retain its exact checked commitment, supply locally
held pins/context and stream/hash its own cursor. Reconstructing a data object
is not signature proof. BEGIN scope must be independently derived before any
registry/resource effect. Actual native and lifecycle authority remain separate;
no signer, GO admission, completed transfer or runtime capability is added.

### Streaming digest source checkpoint

The independently reviewed data-only `CommittedFrameDigest` checks exact original
prefix/header and bounded chunks without retaining another full body buffer.
Root's expanded affected regression passed 658 tests, one skipped; configured
lint passed. See [evidence and limits](../../docs/research/presentation-credential-stream-2026-11-06.md).
The receiver still must supply actual signature-checked retained context and its
original cursor; no digest data is a phase/native/transfer or publication permit.

## BEGIN data prerequisite checkpoint

The two-stage data-only BEGIN/input checks are implemented and independently
reviewed; affected regression passed 956 tests, one skipped. Signed hash claims
remain unadopted until whole-frame/input3/scope/deadline consistency succeeds.
Actual original broker cursor/native admission and complete transport remain
unfinished. See [evidence and limits](../../docs/research/presentation-credential-begin-input-2026-11-06.md).

## Original BEGIN cursor source checkpoint

The standalone original broker-task receive cursor is independently reviewed,
with 967 affected tests passed and one skipped. It retains its own exact reads,
signed-record/header/input checks, original deadline and unknown-read debt. It
returns checked data/local IO closure only; production service/native adoption
and full signed transport remain open. See [evidence and limits](../../docs/research/presentation-credential-begin-receiver-2026-11-06.md).

## Distinct conserved admission and work ends

The broker's original local accept/handshake/BEGIN-read end is an admission cap:
use the earlier of that cap and the original signed work end for the handshake,
all BEGIN reads and registry/input adoption. Adoption must FINISH while that
original earlier cap is still current. A successful read alone is not adoption.

The operation's work end remains the exact input3/signed `work_end_ns` established
before the handshake. Subsequent native/registry work may use only that pre-existing
end, independently checked by its native authority; never derive it from `now`,
renew it at adoption, or rewrite the input to match a shorter local read cap.
Thus a valid input can have a later original work end than the shorter local
admission cap, provided admission completes under both and all native gates hold.
This distinction is specific to the new role-credential path; legacy dispatch's
existing stricter `input deadline <= admission_end` predicate remains unchanged.
Neither end grants permission, cleanup-budget renewal or unqualified GO.

## Sticky connection adoption is mandatory for future phase integration

The new service adoption seam consumes exactly one connection attempt. If a
registry reservation or input bind succeeds and a later current-authority check
fails, the original ticket/receipt is retained; the original connection's
`credential_adoption_failed` remains true and `credential_adoption_complete`
remains false. A queued ticket may still be known by the registry. Its existence
or capacity-only `resources_startable` result is NOT credential authority.

Every future credential resource/GO path MUST retain that same original
connection/registry/ticket/receiver join, require complete=true and failed=false,
and independently check its current native phase/key/generation/work deadline.
Neither a caller boolean nor a new/copy connection may satisfy this gate. No
credential resource/GO path is opened by the source-only adoption seam; existing
unsigned phase IO remains refused. Do not generically poison/retry/free a ticket
merely to make its status match the separate failed connection attempt.

## Queued pre-resource owner checkpoint

The original adopted connection now retains a reviewed queued-current owner
before adoption-complete. Its current checks bind original receipt/budget/grammar
identity, role material, native clock and exact signed work end. It is QUEUED-only
and cannot authorize later resource/GO phases; future entries must retain it and
their own phase facts. Root affected regression: 1,114 passed, one skipped.
See [evidence and limits](../../docs/research/presentation-credential-queued-current-2026-11-06.md).

## Direct IO fallback boundary

Legacy raw GO/CANCEL and result IO explicitly refuse credential-attached channels
before claims or bytes; normal legacy channels remain unchanged. Signed control
is not implemented. Resource startup must wait for the actual original signed
control context/cursor, not merely an existing legacy controller object. The
reviewed [control contract](SIGNED_CONTROL_OWNER.md) fixes its task, phase and
earliest-budget requirements; no dispatcher/generic work gate is opened here.

## Signed RESULT preparation checkpoint — November 6, 2026

The original-service `CredentialResultProducer` now prepares the closed broker
RESULT seq1 commitment from one native immutable candidate after normal resource
drain and actual fixed local GO relay. Current original actor/key/clock/budget and
reciprocal control/GO/adoption/cursor/resource checks remain required. Cancellation
withdraws producer-owned payload references before native cleanup sampling.
This component signs data only: no socket writer, full-transfer mint, gateway
RESULT read, terminal/ACK or publication follows. See the
[reviewed producer evidence](../../docs/research/presentation-signed-result-producer-2026-11-06.md).

The next writer must retain one exact writer before write intent, stream the
signed record then canonical header and payload slices on the original service
Task, and credit each actual native count before checking mutable aliases. It
must seal current authority immediately before each socket syscall and after
completion, preserve short/unknown delivery without retry, and release owned
payload on original-controller first cause. Active-write cancellation may target
only that exact original Task under the existing frozen cleanup budget. A full
transfer fact requires all actual signed-record/header/payload bytes and final
currentness checks; it grants neither terminal settlement nor HTTP publication.
The gateway must keep its sole original work cursor and independently validate
the commitment and result2. Generic channel RESULT paths remain closed.
