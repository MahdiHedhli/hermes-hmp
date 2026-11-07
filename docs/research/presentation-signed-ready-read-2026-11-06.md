# Original-work signed READY read — November 6, 2026

`NativeReadyReceiver` derives one original-work receive admission from the completed
`NativeBeginWriter`, its full signed-wire/private completion and SAME native
BEGIN intent/fact. It has no production caller and grants no native READY phase,
resource admission, worker GO, execution acknowledgement or publication. Tests
use the original native policy/shared-slot/work allocation with actual private
socket IO; peer READY signatures are synthetic fixtures, not a broker-resource
qualification. Existing production-path signing tests remain unchanged.

## Linear native admission

Callback-free original actor/complete-writer checks precede retaining a partial
receiver in both writer and channel. The admission attempt is consumed before
crypto/native boundaries. Original transcript/input scope derives fixed broker /
b2g / READY / sequence-zero expectations and key pins. Current original native
work authority, packet/binding/clock/key/descriptor/task facts are checked before
joining actual BEGIN completion into the native send-completed state. The existing
native `_authorize_channel` receives the fixed receive claim once. Late refusal
leaves its original linear state consumed; restoration cannot acquire another
receiver or native claim. A mutable send-completed flag without completed signed
BEGIN evidence cannot pass. Wrong actors cannot consume original admission/run.

The presend BEGIN guard and caller-owned handshake guard are not relaxed. A fixed
read-stage guard composes original-work local checks, current BEGIN_INTENT native
checks, original qualified clock/deadline and concrete peer/socket checks. It
requires the same original completed writer/native fact throughout. No generic
credential channel refusal is removed or replaced by a permission flag.

## Original bounded cursor

The reader retains its original scope/buffer identity, target, actual consumed
count, pending return and owned readiness registration. It reads directly through
captured native nonblocking recv, rechecks concrete descriptor/mode after native
callbacks, and permits an owned read wait only after exact EAGAIN/EWOULDBLOCK.
The original deadline is not renewed. Actual syscall count is recorded before
callback revalidation; held target and committed-count identities are resealed
before byte commit. Drift, pending/uncertain native outcomes and unknown
registration retain debt. Original buffer alone is wiped on failure; a substituted
foreign buffer remains untouched. Retry refuses before modifying prior evidence.

HBA record prefix/length, broker signature, exact original context, input/scope
hashes, original key roles/generation and the committed empty READY HBR1 frame
are checked. READY must be broker/b2g sequence0, version2 and bodyless. Bound is
RECORD_LIMIT+8+HEADER_LIMIT = 3,080. A private completion retains original
buffer/count/target and exact raw/frame bytes. `current_ready()` revalidates
signature/frame/current context on the original work task; late key retirement
withholds current read evidence while preserving known local IO history.

Transient part/value/frame aliases are cleared. Failures/cancellation propagate
outside their catch with no internal exception context or immutable partial
aliases in retained read tracebacks. Exact role-selection/public-key byte types
are checked before pin comparison, preventing foreign comparison/getter dispatch.
Malformed, EOF, partial and cancelled reads conservatively retain UNKNOWN debt in
this slice; no general cancellation/unknown-error settlement is inferred from
control-reader proofs. Historical local read release requires original work task
joined and known IO. It grants no native write-quiescence, remote/resource/native
release or authentication success to failed reads.

## Review and tests

Independent read-only source/test review accepted the repaired receiver. It found
and required clearing failure aliases/context, postcallback target/count joins,
and role-key primitive fences; those are covered by causals. The reviewer ran no
tests/native actions. Root targeted run: **20 passed**, 2.75 seconds. Cases cover
valid/fragmented READY; invalid signature, scope, sequence, hash and phase;
oversized authentication; EOF/unknown native recv; postguard count/target/buffer
drift; late key retirement; late native receive-claim refusal/restoration; wrong
factory/run actor; forged mutable BEGIN-completion flag; exact deadline refusal;
cancelled wait; and foreign key-pin fields with zero comparison callbacks. Partial
failure tracebacks are inspected for absent internal context and cleared aliases.

The first seven new tests lacked an imported dependent fixture and errored before
setup; explicit fixture import repaired that test issue. No protocol budget or
native/context guard changed to make tests pass. Final affected regression: **1,429 passed, one skipped**, 64.17 seconds; configured
repository-wide Ruff passed. Exact new-source CI remains pending. Source/CI binding
is recorded in the current checkpoint/private receipt.

No live host/device/settings, role-key installation, permission/provider change
or mobile build. Native policy/peer/clock qualification remains synthetic. Signed
READY read success remains separate from a fresh PRE_GO observation and native
RemotePhase.READY transition; signed later phase IO, production resource admission,
worker GO relay, runtime/startup, native publication, STATUS and physical/release
qualification remain open. Full character delivery is unavailable. The earlier
native-destination incident remains separate and unresolved.
