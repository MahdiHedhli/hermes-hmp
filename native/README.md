# Retained native admission owner — incomplete source foundation

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
no actual native lifecycle harness has run for this source. Wrong-thread refusal
and the kernel receive-to-dead-name transition remain unobserved.

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
