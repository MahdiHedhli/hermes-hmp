# Started-reader terminal proof and publication lifecycle

## End state and non-substitutable ownership planes

Complete the character-image path through authenticated metadata/avatar delivery.
A private result or local drain is not the final feature. Preserve full classic,
blobatar and custom static-image parity; host-local images follow. No live host,
service-manager job, device install or release follows from this source work.

Keep four independent obligations: (1) broker exact-child wait and pipe/control/signal-retirement
closure, (2) original gateway work/transport/clock closure, (3) joined original
parent-policy and native claims/DRAIN, and (4) current native authorization and
candidate integrity at publication. No frame, EOF, task completion, version string,
cleanup boolean or body hash alone closes all four. Never translate remote facts
into fabricated local JobOwner custody events or a fake child. Do not enable
features by trusting a wire-supplied producer/qualification flag.

## Producer provenance and initial source sequencing

A future accepted terminal handoff must join the exact authenticated native
peer/boot, retained channel/clock domain and externally selected installation
generation to an independently qualified producer/runtime. StartupEnrollment's
manifest string, an observed candidate hash, same UID and a decoded claim do not
supply that qualification. This is an executable-origin/native-API gate, not a
Hermes version equality/allowlist gate. Minimum-version policy remains unchanged.
Actual Linux/Darwin runtime/manager/reaper/loader/latency qualification is separate.

Implement producer-side typed local closure and a bounded closed claim codec
first. Decoding yields a *claim*, never an accepted remote completion capability.
Keep wire dispatch/import, COMPLETE, publication, started journal release and
native/credential release closed until the remaining handoff/authority integration
is reviewed. This prerequisite is not a reduced delivery feature.

## Immutable operation-input receipt before effects

After bounded BEGIN decoding and one registry reservation, bind original input3
metadata once before receiver Task initialization or resource start. Seal exact
registry record/binding/profile/kind/deadline, original challenge/epoch, bounded
input SHA-256, worker source-manifest SHA and expected-avatar revision. Preserve
METADATA expected digest None and existing optional avatar behavior; AVATAR needs
its original nonnull digest. The receipt is data/context only, not GO authority.

The broker child shares its service process group and does not prove group
absence. No-spawn/no-FD-transfer and runtime/reaper/containment qualification
remain separate; do not import the old direct-owner group proof.

No raw policy packet, home/root/path, original header, bearer, prompt, model or
provider credential enters the terminal claim. Existing stage_input must match
that same original receipt before its control-write effect. Unbound legacy model
fixtures stay incapable of exporting a started claim; no implicit late bind,
replacement receipt or second reservation. Retain partial bind uncertainty.

## Typed local closure producer and bounded data claim

A retained producer allocation on the original registry record precedes any
local-observation/native validation effect. It captures original resources,
process owner, input receipt, registry map/context and exact observation identity.
Only actual BrokerReaderResources local_observation/validates_local plus original
child wait/control/pipe/signal-retirement facts may supply a typed local closure.
Constructed lookalike dataclasses, booleans, replacement resources/observations,
changed record/input/source/boot/domain and uncertain native outcomes refuse.
Callback-free original-reference checks bracket native boundaries. Partial
construction stays retained; no retry or release authority arises from failure.

The initial codec carries canonical bounded JSON (<=4096 bytes), closed fields:

- schema 1 and kind STARTED_READER_TERMINAL;
- original iid/listener/broker/channel/operation binding;
- canonical profile, METADATA or AVATAR kind and original deadline_ns;
- original challenge, epoch, input_sha256 and worker_source_sha256;
- producer installation_generation and qualified clock-domain SHA-256;
- outcome OK or ABORTED, exact observed signed exit_code;
- result_sha256 for OK, null for ABORTED.

OK requires exit0, normal complete result and a minted metadata-only digest/length
fact from the exact writer after concrete transfer completion; never a caller
digest or result cleanup claim; ABORTED requires irrevocably revoked output and actual known local resource
closure. Neither is a native permission, whole-operation closure or execution
acknowledgement. Do not export OK from a result's self-reported cleanup field.
The claim omits reusable authority tokens and private filesystem/OS identifiers.
A body cannot select a new boot, domain, runtime generation, deadline or peer.
Canonical decode rejects unknown keys, duplicate keys, noncanonical encoding,
bool-as-int, overflow, malformed digests/bindings/profile/outcome combinations and
oversize before allocation. Cancellation observed before the one outcome mint requires ABORTED; an ambiguous
race may retain unknown debt rather than remint. Later revocation cannot turn a
frozen historical OK into publication authority or mint a second outcome.
Repeated local observation does not mint another
started journal entry or admission credit. Encoded data and decoded claims never
become the opaque local observation/custody capability.

## Required joined wire/ACK/STATUS lifecycle (not yet enabled)

The selected-v2 codec/grammar now represent a dedicated typed terminal frame
after RESULT, or an aborted terminal outcome after cancellation, with separate
sequence and bounded body rules. This is transcript syntax/data correlation
only, not an enabled transport, accepted producer capability or completion path.
Legacy v1 retains its one terminal RESULT/bodyless CLOSED behavior. Preserve one continuous broker control cursor/task; no competing ACK reader.
The gateway's original work task validates exact original binding, challenge,
input/source/domain/generation and required producer qualification before accepting
any remote closure capability. No reconnect BEGIN/GO/result replay or fresh budget.

Normal proof uses remaining original work time. Cleanup proof/ACK uses only the
earliest frozen original cleanup interval; delayed/expired claims get no allowance.
Partial send, lost proof/ACK, timeout, unknown producer, stale generation or
revocation retain journal/native debt. ACK retires only the broker journal after
its typed local closure; it does not drop native headers, policy or job credits.
STATUS needs a reviewed boot-bound lookup/ACK contract; UNKNOWN/PENDING cannot
resume work or certify closure, and old-boot responses cannot cross generations.
Do not enable only the exporter, decoder or grammar as completion authority.

## Reviewed selected-v2 transcript syntax

TERMINAL is v2-only with 1..4096 bytes of canonical closed handoff data; the
framing, inner claim and outer envelope share one limit. The inner historical
STARTED_READER_TERMINAL claim remains separate from the outer schema1
STARTED_READER_HANDOFF envelope. Its exact keys are schema/kind/claim/cleanup;
cleanup is null or start_ns/end_ns. ACK v2 carries exactly 32 raw bytes,
SHA-256 of the exact entire envelope, not merely its inner claim. V1 framing and bodyless ACK are unchanged;
no version fallback or v2 STATUS construction is added.

| Path | Broker sequence | Client ACK sequence |
| --- | --- | --- |
| Normal | READY0, RESULT1, TERMINAL2 | 2 after GO1 |
| Abort before READY | TERMINAL0 | 1 after BEGIN0 |
| Abort after READY, before RESULT | READY0, TERMINAL1 | next client sequence |
| Abort after RESULT | READY0, RESULT1, TERMINAL2 | 2 after GO1 |
| One CANCEL races frozen TERMINAL | terminal sequence/outcome/digest unchanged | advances by one |

BEGIN/READY/GO keep existing role and ordering rules. Selected-v2 RESULT is one
private candidate message, not the terminal transcript event and never enough
for ACK. OK terminal syntax requires GO and RESULT. Broker ABORTED syntax needs
sticky local invalidation; this is not real cancellation-budget/resource proof.
A gateway may learn ABORTED from terminal data, which permanently invalidates its
candidate. Header and claim must name the exact same original operation binding.
ABORTED requires a sender cleanup stamp. A broker whose grammar is already
invalidated must include a stamp even for historical OK; sticky invalidation is
only a syntax check, not proof that it used the actual original budget. Stamps
are immutable exact integers, end=start+250ms, within signed63 bounds and with
start no later than the original deadline. The codec does not sample a clock,
adopt a budget or prove the stamp is not future-dated at the receiving endpoint.
An expired stamp remains the same expired data, never a renewed interval. Null
means no sender cause at envelope capture, not permission for a fresh interval
or proof that no later cause occurred. Raw-claim fallback is refused.
The grammar does not validate challenge/input/source/domain/producer authority;
the joined receiver must still bind all of them before accepting closure.

A historical OK frozen before cancellation may arrive after cancellation, but is
classified as discarded data and cannot revive work. A gateway can parse one
late RESULT as discarded while continuing its original cursor to TERMINAL. A
broker cannot start RESULT after its local invalidation. One CANCEL after RESULT
or TERMINAL advances the next client sequence without changing the frozen terminal
outcome/digest. Duplicate RESULT/TERMINAL/ACK, wrong roles/sequences/scope/digests,
malformed or oversized claims and ACK before TERMINAL fail permanently. ABORTED
never becomes an image candidate. The terminal digest/outcome are captured once in an immutable metadata-only
NamedTuple with an independent original reference; scalar/reference drift is
sticky refusal. It retains no claim-body or candidate aliases. This guards
ordinary ownership drift under trusted installed-memory premises, not arbitrary
Python-memory tampering. Digest equality and ACK_REQUEST are syntactic
correlation only, not permission to send ACK or retire any journal/native credit.

See [joined transport prerequisites](TERMINAL_TRANSPORT.md) for the retained-work
cleanup-reader and original-controller continuation contract.

Actual send/receive dispatch remains closed: the continuous original controller,
known non-torn write facts, qualified producer/receiver custody, original work or
earliest cleanup budget and no-replay failure semantics must be integrated and
reviewed together. A torn RESULT/TERMINAL cannot get an appended frame or retry;
uncertain/truncated parsing retains debt. V2 STATUS needs its own reviewed,
authenticated boot-bound lookup and journal-only ACK contract. A new lookup may
never renew expired operation work/cleanup or resume a candidate.

## Candidate integrity, fresh native emission and retirement

The existing private candidate/token is not enough to publish. Bind a stable
candidate representation/digest to the original validated result and terminal
handoff; detect container/body/token substitution and concurrent revocation around
all later awaits. Bound any hashing/canonical re-encoding and transient copies by
existing admission/body limits; do not create another unbounded result ledger.
Public projection exposes only whitelisted presentation fields and bounded avatar
bytes, never raw result2 chain/inode/work ledger/private context.

Only after required original resource/ownership observations and the native
completion contract may the original job enter a distinct remote completion path.
Fresh PRE_EMIT must use original headers/native lease and original process/store/
listener/device/profile generations. Consume one exact synchronous emission intent
immediately before the authorized sink, with no await/replay and no legacy local
custody shortcut. Retire/drop original credentials from both record and sealed
remote references only after all required native/policy/work/transport ownership
planes close; preserve unknown debt and original scope on ambiguous DRAIN.
Native authorization, drain, credential drop and broker ACK are not interchangeable.

## Causal acceptance

Use real owned synthetic readers and strict local-observation identity: normal
result versus cancellation/abort, partial start/input, actual wait/control/pipe/
signal retirement, copied observation refusal, input/source/domain/boot drift,
metadata callbacks, duplicate/late bind, malformed/oversize/mixed claims. Prove
no existing CLOSED/ACK/status, local no-child, boolean or decoder path can release
started registry/native credits. Preserve raw headers and candidate revocation.

Before full activation, add joined wire/proof/ACK loss races, native permission
revocation, candidate/token mutation at PRE_EMIT, policy/native DRAIN failure,
credential retention/drop, cross-instance/profile/device/generation isolation,
actual runtime/reaper/manager/latency and signed physical qualification. Source
model passes and fixture-generated expected manifests are not production trust.
