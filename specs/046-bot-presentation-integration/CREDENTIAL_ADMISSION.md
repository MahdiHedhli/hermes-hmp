# Proposed paired startup and phase admission: local role credentials

Status: concrete contract amendment for independent review, not implementation,
credential creation, production authority or deployment permission. The full
desktop display-name, classic/blobatar and custom-static-image feature remains
required. This does not replace delivery with a snapshot or a no-GO fixture.

## Decision and preserved boundaries

Use independently installed, per-instance asymmetric role credentials to
authenticate the existing private UDS data/control path. Do not extend the
unfinished Mach reply-right protocol into production. A valid signature proves
an operator-selected role statement under the trusted-installation premise; it
does **not** attest executable provenance, process ancestry, child exit, timely
release or phone authorization. Do not rename it kernel-origin evidence.

The gateway remains the existing native PM gateway, with its generation lease
and original listener/native authority adapter. The broker remains a separately
supervised, isolated owner and the sole exact-child reaper for the fixed reader.
No gateway-global reaper change, direct gateway subprocess fallback, Kanban
disablement, upstream patch or Hermes build allowlist is introduced.

Keep the reviewed UDS body codecs, reader/sender cursors, retained partial
owners, original two-second operation deadline and first-cause/minimum cleanup
budget, fixed worker recipe, native INITIAL/BEFORE/PRE_GO/DRAIN/PRE_EMIT,
result-integrity transfer, frozen TERMINAL, exact ACK/journal join and sole
authenticated HTTP publisher. Authentication is an additional conjunct, not a
replacement for any of them. Transport delegation may cause refusal or local
revocation; it must not confer permission or signing capability.

## Explicit threat and installation premise

Root, the local administrator, the admitted installed code and its selected
Python/native dependency runtime are trusted. Untrusted capabilities include
HTTP input, presentation data and possession of a delegated UDS endpoint or its
bytes. Such a holder receives no role private key, key descriptor, signer object
or callable signing service. The fixed worker receives none of these either.

This is not an OS sandbox against arbitrary same-UID file/memory access or a
hostile fork snapshot. Mode 0600 and opaque Python/native objects do not provide
that separation. Compromise of trusted runtime code is outside this proof;
do not claim the design contains such compromise. If hostile same-UID execution
or worker RCE is brought into scope, independent key/process isolation is a
prerequisite and this contract must not be represented as sufficient for it.
The existing fixed parser must still treat its data as untrusted, without object
construction, code evaluation, dynamic imports or executable request fields.

An operator-selected installation configuration precedes listener/service
admission. It fixes instance, separate gateway/broker recipes, protocol,
algorithm, key IDs/public pins, credential generation, reachable source/runtime
inventories and admitted library/OS-loader roots. Selection is bounded,
owner-controlled and no-follow, outside served profile inputs. No HTTP value,
tool result, broker response or running verifier selects its own expected bytes.
Candidate inventory generation is not installation approval.

The gateway recipe admits the trusted Hermes PM-managed startup and its actual
API/minimum-version policy, the HMP role-entry origin, fixed credential selection
and retained actual PM generation. A native Hermes commit may be recorded for
diagnostics, but is not compared with a tested-build list to grant admission.
Do not require an operator to qualify each newer Hermes release. The broker's
separately installed isolated runtime has its own expected inventory; this does
not turn that component's installation integrity into a Hermes version gate.

## Keys and private owners

Use distinct Ed25519 key pairs for gateway and broker; each role holds only its
own private key and the pinned peer public key. A verifier cannot sign as its
peer. Do not reuse, derive from, expose or forward phone pairing keys, bearer
tokens, gateway API keys, provider credentials or the HMP instance private key.
No cloud or repository secret is required. Implementation must use a reviewed
standard crypto implementation in the admitted runtime, not home-grown crypto.

Private seed files are exactly 32 bytes in role-specific private installation
storage. Public keys are exactly 32 bytes; key IDs are SHA-256 of public bytes.
The installer, not a request or a verifier, selects their generation and pins.
Require regular single-link owner-controlled files, private modes, no symlink
ancestry and stable bounded reads. Refuse missing, malformed or changed inputs;
never generate a replacement during a request or silently migrate synthetic mode.

Only the paired startup factories load these credentials. Key FDs are closed
before worker creation. No key or signer enters argv, environment, logs, errors,
results, serialized capabilities, worker input or passed/inherited descriptors.
The fixed exec-only worker path must not execute untrusted code before exec or
retain a parent key snapshot after exec. Audit fork and descriptor paths rather
than treating a pathname or `close_fds` comment as proof.

The key stays in the original role owner under the stated runtime premise.
There is no generic `sign`, `approve_digest`, caller-supplied-key or public
GO-capable constructor/endpoint. Private phase transitions derive their own
closed statements only after checking the original local owner and native facts.
A wire claim, echoed nonce, boolean, successful decoder or signature alone never
constructs an operation permission. Existing `synthetic_no_go` objects remain
distinct and cannot be upgraded by toggling a field.

## Startup transcript and bounded commitments

Freeze the concrete canonical envelope and framing before implementing them.
Use an explicit new authentication version, with no downgrade or fallback to
unauthenticated HBR1. Reuse the existing bounded body frames; do not create a
second untracked reader or parallel cursor. Unknown algorithms, keys, fields,
duplicates, noncanonical encodings, wrong sizes and trailing bytes refuse.

Before any profile/input body, mutually authenticate fresh unpredictable boot
and channel nonces, both roles, instance, selected protocol/algorithm/key IDs,
installation generation and the qualified common clock-domain identity. Each
proof covers the whole transcript and its direction to prevent reflection.
One role's proof is not a proof by the other role. Reconnect/restart establishes
a new channel and cannot resume old work or reuse operation authority.

Every effect-bearing frame needs a phase-specific signed commitment to its exact
canonical header/body digest and length, both boots, channel, original operation,
direction, sequence and protected input/context binding. The input binding
includes canonical profile, proof kind, input3 SHA, challenge, epoch and original
deadline. Length/type/phase bounds are checked before allocation; authenticated
commitments do not authorize an unbounded body or change the aggregate budget.
An incoming body is not admitted until its exact committed digest is checked.

Required phase transitions:

- INITIAL/BEGIN: the original gateway owner captures actual native INITIAL and
  original input3; only then may its BEGIN commitment authorize broker admission.
- READY/GO: the original broker owner retains its actual child/input/READY facts;
  gateway GO requires its fresh original PRE_GO and exact original context.
- RESULT: the broker owner first commits its held immutable candidate/header
  and intended exact length/SHA before streaming. The actual completed-transfer
  fact exists only after the full original write succeeds and is separately
  required for normal OK TERMINAL. A presend commitment is not transfer or child closure;
  a torn transfer permits no append, retry or completed-transfer claim.
- CANCEL: the original owner first freezes its actual first cause and current
  `CancellationWindow`, then commits the exact window, operation/channel,
  direction/sequence and original deadline. Only full authenticated validation
  permits adopting a remote window or remote-inherited resource effects. Local
  EOF/error/revocation may independently freeze a local cause and clean up that
  owner's already-held resources under its original local authority/budget;
  this does not trust any remote window or settle another owner's debt. No
  re-signing with a renewed cause, window or deadline.
- TERMINAL: sign only the existing frozen envelope after actual custody facts
  and current first-cause/minimum-budget checks. Normal OK additionally needs
  actual completed RESULT transfer. Pre-result ABORTED instead needs its actual
  invalidated-output/retired-budget and resource-closure facts, not a nonexistent
  RESULT. A shorter end or later cause invalidates an old envelope; do not
  re-sign/retry a torn or stale handoff.
- ACK: the original gateway receiver signs only its exact consumed envelope and
  sequence. Keep broker ACK/tombstone and native DRAIN/PRE_EMIT joins independent.
- STATUS: dispatch remains closed until a separate bounded existing-state
  lookup/journal/boot/key-rotation and lookup-budget contract is reviewed and
  implemented. It remains part of the full feature. It can never start, resume,
  repeat BEGIN/GO or return a fresh result body.

CANCEL, EOF, timeout and credential retirement revoke local publication
immediately. Inherited budgets/resource effects still require validated original
scope. No unauthenticated record can renew a timer, shorten another operation's
budget, release a journal entry or establish clean closure. Unknown/lost ACK or
write outcome retains the original debt; no automatic reconnect or resend.

METADATA/AVATAR and `expected_avatar_sha` bind through the original validated
input3/job and context digest, never a new signed boolean or nonexistent result
field. The concrete wire/retirement decisions are in
[CREDENTIAL_WIRE.md](CREDENTIAL_WIRE.md); neither document is authority by itself.

## Lifecycle, rotation and actual closure

Native peer/endpoint ownership and process-lifetime observations remain useful
independent checks. They are not converted into executable attestation. Retain
original endpoint, role owner, boot, clock, task/cursor and operation references.
Observed drift, key/config rotation, source/runtime change or retirement closes
publication before notifying affected operations. No new current owner, key or
generation repairs a failed original operation. Verification must remain bounded
and occur before issuing operation deadlines; no unbounded hash walk inside a
cleanup interval or claim against unseen trusted-account ABA replacement.

Credential retirement conservatively refuses every later remote effect or new
signature, including cleanup CANCEL/TERMINAL/ACK. Retained old keys do not regain
authority. Original local cleanup may continue with its already-held resources
and earliest budget; remote/journal uncertainty remains UNKNOWN. Facts fully
accepted before retirement remain historical observations, not permission for
new publication, work or a fresh ACK. No automatic key replacement or replay.

The broker still proves its actual child/pipe/wait/termination/drain custody
under the independently supervised topology. Signatures do not make ECHILD,
EOF, supervisor exit or a timer clean closure. The gateway separately proves
original credentials, current native grants/kind/tip, candidate integrity,
native DRAIN and fresh PRE_EMIT before any HTTP metadata/image publication.

## Implementation and acceptance sequence

1. Independently accept this explicit trust/control amendment and freeze the
   concrete credential/envelope/phase API contract. Production stays closed.
2. Implement paired startup factories, typed nondelegated role owners and
   bounded bilateral transcript/phase verification using the admitted crypto
   runtime. Preserve original native and UDS owners; no signer service.
3. Compose real GO through the actual fixed worker and native authority, then
   RESULT/TERMINAL/CANCEL/ACK/journal/DRAIN/PRE_EMIT and authenticated publication.
   All classic/name/blobatar/custom-static variants use this same full path.
4. Exercise wrong role/key/config, reflection/downgrade, cross-instance/profile/
   operation borrowing, delegated-holder forged commitments, replay/reordering/
   torn frames, old boots, drift/rotation at final boundaries and two-operation
   isolation. Audit no key/signing-capability inheritance or worker export.
5. Exercise partial initialization/write ownership, original task/cursor loss,
   CANCEL under backpressure, earliest cleanup end/expiry, lost ACK and real
   normal/abort custody. Unknown retains debt and never grants publication.
6. Independently review source and actual synthetic native artifacts, then seek
   separately authorized installation/credential/service and physical/release
   qualification. No real host credentials/profile/message/provider are needed
   for source or disposable synthetic acceptance.

## Historical Mach work and current deployment separation

The unexported Mach observation/dead-reply prototype and its limitations remain
historical evidence, not a hidden alternative admission path. Do not send a new
challenge or dispose unknown live rights. The original unknown-destination
incident remains unresolved; retiring a proposed transport does not resolve it.

This amendment does not change the independently reviewed image-delivery
candidate `5e247a6`, its pending ColPanicM2 owner decision, current device grants,
live host configuration or any runtime. Existing per-feature minimum-version/
API/security gates and older-host fallback remain unchanged.

## Startup key-file source checkpoint — November 6, 2026

`presentation_credential_files.py` implements bounded startup-only acquisition of
fixed `own.seed`, `own.pub` and `peer.pub` in an operator-selected role directory.
The directory is private 0700; leaves are regular owner-controlled 0600,
single-link, exactly 32 bytes. An original no-follow ancestor walk and final
path/descriptor joins accompany own-key derivation and both configured public
pin checks. Shared ancestors use stable inode/type/owner/mode identity; unrelated
directory entries do not select a key. Root-owned sticky ancestors are allowed
under the same trusted-administrator premise as the endpoint owner.

All original descriptors are retained before allocation and closed before the
owner becomes ready. Unknown close stays retained and is never retried.
Reinitialization cannot reset state or revive retirement; retirement before final
publication prevents ready/key publication. Failure drops reachable seed/key
aliases before the outward context-free exception. This is not zeroization or
same-UID/fork isolation. Cleanup refuses foreign PID/UID before descriptor effects.

Independent source/test review accepted this component under serialized trusted
startup. Root's expanded focused suite passed 213 tests without warnings in a
fresh owned test root; the strengthened actual-descriptor process-context case
then passed the targeted 30-test loader suite. Review did not execute tests.
An earlier default pytest run produced stale temporary-directory cleanup warnings;
subsequent tests used an explicit fresh root. Two fresh-root failures exposed an
exact-bool sticky-directory policy defect, now corrected and retained as failure
history rather than called successful runs.

The component generates no key, exposes no signing method and is not connected
to a request, listener or installer. Actual operator-selected runtime inventory,
credential retirement/drift detection, typed paired role factory, handshake,
original native phase/cursor ownership and no-key-inheritance audit remain open.
No installed credentials or live host settings were read or changed in these
synthetic tests.

## Retained handshake source checkpoint

The original-task credential handshake actor and channel IO/close exclusion
passed independent source review and a root regression run of 452 tests, one
skipped. See [the evidence and limits](../../docs/research/presentation-credential-handshake-2026-11-06.md).
Only a historical known-complete local IO fact releases the socket claim;
unknown retains original debt. No runtime factory, phase/native authority or
production feature is enabled by this source component.

## Original native input correlation checkpoint

The one-attempt handshake/native-input handoff is independently source-reviewed;
the final affected regression passed 640 tests, one skipped. It joins the exact
original policy packet and native job slot with typed post-callback fences.
See [evidence and limits](../../docs/research/presentation-credential-native-input-2026-11-06.md).
Unsigned phases remain refused until original streaming and direct broker IO
paths receive the typed signed transport; this is not native authorization or
production runtime admission.
