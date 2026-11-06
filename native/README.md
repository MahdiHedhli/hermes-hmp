# Typed dead-reply retirement — source/model candidate

The current extension adds one cleanup-only attempt for the sole copied reply
in a closed simple received header. It observes the held name's exact DEAD_NAME
type and one reference, then calls `mach_port_mod_refs(DEAD_NAME, -1)`. The typed
primitive refuses a live right rather than dispatching to send-once notification.
There is no polymorphic reply deallocation, destructor or fallback. Exclusive
ownership of the original held name is a runtime premise, not protection against
arbitrary in-process corruption.

The actual release is recorded before post-call clock/reentry checks. Only a
timely retirement fact permits subsequent endpoint close. Native errors, live or
wrong types, other refcounts, invalid ownership shape, unknown copyout, expiry and
reentry retain debt with no retry. A simple rejected body can still have its sole
dead reply safely retired; that cleanup fact never admits the rejected request.
General live-right/message disposal and startup/right provenance remain open.

Independent source/model review accepted this slice, without reviewer execution.
The direct C model covers 70 scenarios; root's portable selections pass 17 pytest
checks on Python 3.11.15 and 3.14.4 (one model test plus schema/driver checks).
Actual native cases were deselected. Whole configured lint, C syntax and
plugin/privacy gates pass. No native request or retirement execution qualifies
this candidate. Earlier native lifecycle evidence below binds older source only.
HMP does not load the owner; there is no exposed endpoint, reply sending,
production admission or operation/terminal authority.

## Earlier retained request observation — source-only extension

Source `48a3764` adds one fixed request receive to the original owner. It
retains the complete kernel buffer and returned reply name before clock/reentry
checks. It validates exact received dispositions, endpoint, frame and bounded
audit trailer. Observation grants no startup or operation authority. Any received
message or uncertain copyout prevents close/disposal: retained message debt is
not explicit cleanup. No reply, destructor or generic notification is emitted by
these paths. The endpoint remains unexported and no production receiver is admitted.
Future actual input must use explicitly owned fixture reply destinations; even
send-once disposal can notify its destination.

The direct C model now covers 47 scenarios, including 24 request outcomes and
all three request clock boundaries, with exact next-effect and one-cursor checks.
Root's portable selection passes 17 pytest checks on Python 3.11.15 and 3.14.4;
the real native case was deselected. These use a fake Mach/trailer ABI, not kernel
flags or identity evidence. Independent source review accepted the retained-debt
slice and requested these additional causal cases; no reviewer execution.
The revised native driver pins/links libbsm. Neither a real request receive nor
the revised own-right native harness has run for this candidate. Earlier native
evidence below binds its original source, not this extension.

## Earlier retained native endpoint foundation

`hmp_admission_owner.c` implements private Darwin endpoint ownership only. HMP does
not load or package it, and it has no public route, port export, message exchange,
startup selection or operation authority. The caller must retain the empty
allocation before initialization, use it serially on its original process/thread,
and retain every refused/uncertain owner. An expired or poisoned close is debt,
not proof of resource release. This is not a bounded leak-free production service.

The original work and cleanup deadlines cannot be replaced. Reentry permanently
refuses the owner; actual returned resource effects are recorded before the next
boundary check. Each native release is attempted at most once. Only known timely
closure permits disposal. Receive-right release and the remaining own send/dead
name reference are separate effects. No arbitrary supplied right is accepted.

Root's deterministic C model executes the implementation against a fake Mach ABI:
20 causal scenarios cover all four native-boundary reentries, all six clock
samples, native failures, ordinary closure, expired retained rights, wrong process
and invalid original deadlines. The pytest driver passed on Python 3.11.15 and 3.14.4.
Initial configured lint found an import-order issue; it was corrected. Compiler
syntax checks and configured Ruff pass. Independent repaired-source/model review
accepted the repaired lifecycle, with explicit native-call totals added to each
clock-boundary case so the prevented next effect is checked. No reviewer execution
is claimed. These model results are not kernel, message or runtime qualification;
after independent harness source review, root completed one actual Darwin
lifecycle run: 17 passing checks in 0.84 seconds (one actual native case plus
16 portable/driver checks). It observed own receive/send references, wrong-thread
refusal followed by known join, the receive-to-one-dead-name transition, timely
close, idempotent close, final name absence and disposal. The fixed harness sends
no messages and uses no global names or services. The separate fake-driver receipt
is not native evidence. Independent artifact review accepted all six source hashes, 19 artifacts,
compiler/SDK/binary bindings and five terminal commands; no reviewer execution.

Exact source, compiler, SDK, binary and private artifacts are recorded in
`/private/tmp/hermes-admission-native-311-20261106.json`. This is lifecycle
observation only; no message exchange or production startup is qualified.

Remaining implementation: retained reply-right and receive-cursor ownership,
closed header/disposition/error contracts, original audit incarnation and lifetime
observer, independently selected startup/runtime provenance, and native
phase/digest or kernel-origin control binding. A reply right does not prove that
its receiver is the sender; do not challenge an unqualified request. A boot
handshake does not authenticate later UDS frames. Preserve the distinct native
PRE_EMIT/DRAIN, terminal/ACK and per-device/profile authorization requirements.

See `specs/046-bot-presentation-integration/RUNTIME_ISSUER.md` and its task list.
Full desktop characters and host-local images remain unfinished. No live gateway,
device, permission, provider, model or job is changed by this source.
