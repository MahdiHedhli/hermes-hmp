# Cooperative post-GO cleanup reader

Status: bounded post-GO source coupling independently accepted after 467 checks
on Python 3.13. The 56-file Python 3.11.15 and 3.14.4 matrices each pass 1,959
tests and 190 subtests with one Linux-native skip. Final cleanup causals rerun
after the test-only deterministic peer-EOF correction. This is not an image-serving route or runtime admission.

## Ownership and transition

Only the original RESULT reader task may switch to discard. The original cause,
write-quiescence fact, settled receive/commit intents and known selector ownership
must be retained before the request selects this lane. Otherwise cancellation uses
the existing cancel/join path. The original work task mints a read-scope fact; it
is neither a join nor socket closure. Only the existing cleanup task may write its
one CANCEL against that fact. Normal work and candidate publication stay revoked.

The original reader finishes exactly the remaining RESULT framing/body, then at
most the bounded TERMINAL envelope. It never scans after a torn frame, creates a
replacement reader, acknowledges terminal data or releases native credit. EOF is
local receive evidence only. Decoded terminal fields remain unaccepted data and
cannot authorize subsequent I/O. Socket/clock closure still requires joining the
original reader and observing no unresolved receive/write debt.

## Deadline shortening

Cleanup uses the original qualified cleanup clock and nonrenewing minimum budget.
`CleanupReadGate.inherit(window)` is the only supported adoption API for this
reader: it checks the original caller/work/cleanup actor, revokes I/O during
publication, samples the existing clock, signals the original owned change Future
and publishes the smaller end synchronously. It never extends the allowance.
Each wait binds the notice generation/end before registration, preventing a missed
earlier deadline. The readiness helper retires its original timer and selector
subscription before the reader rechecks the minimum and rebinds. A simultaneous
readiness hint grants no receive ahead of the change check.

Partial allocation, initialization, signal or budget publication poisons the
operation; no retry or use of the former end is permitted. Direct budget mutation
outside this adoption API is unsupported trusted-memory corruption, not qualified
timely cancellation. Syscall/scheduler latency and deployed runtime admission are
not certified by these tests.

## Receive and commit boundaries

Immediately before concrete receive, qualify original descriptor identity, kernel
nonblocking mode and exact Python timeout 0.0 without reviving work/peer authority.
Capture original outer buffer, header and primitive counters across receive. Retain
consumed bytes as pending before post-native validation. Commit only to held
original storage and integers. Drift leaves unknown receive debt; never touch a
foreign buffer or invoke foreign arithmetic. Wipe only the fact's original outer
buffer and bounded local terminal bytes. Unknown selector retirement must latch
read debt before any later cleanup sampling, even when that later sampling fails.

## Current verification and remaining gates

Synthetic enrolled Unix-socket tests exercise interrupted prefix/header/body,
foreign outer/counter replacement, kernel blocking and positive Python timeout,
blocked/pre-registration shortening, simultaneous readiness hint, change-Future
initialization and signal before/after failure, paired notice allocation drift,
expired-deadline reentry after native descriptor checks, torn CANCEL without retry,
external work/cleanup cancellation, lost registration proof and a complete
RESULT-to-TERMINAL decode that cannot adopt an unaccepted sender stamp. They use mocked
peer/clock premises and do not qualify production peers, managers or devices.

Independent final regression accepts the bounded post-GO coupling. Its 23
cleanup cases distinguish pre-intent zero-write from post-intent one-write
external cancellation; the earlier scheduling-only assertion failure was repaired
with explicit writer-entry synchronization, preserving all safety assertions.
The min-wake test now supplies controlled peer stream EOF after rebind instead of
assuming variable service/native retirement completes before the smaller end.
That test-only correction neither extends time nor proves native custody closure. Pre-READY cleanup, terminal acceptance/ACK,
PRE_EMIT/DRAIN and credential retirement remain separate unfinished work. Existing
Kanban waitpid(-1) interference and actual producer/receiver runtime qualification
remain release gates. No capability, host image route or deployment is enabled.

## Separate unresolved supervisor observation

One full Python 3.11 repeat failed the unchanged lost-sink-acknowledgement test
before it reached the sink. The isolated test and all 17 supervisor cases then
passed. This does not prove a timing cause or resolve the intermittent symptom.
Status-only diagnostics now preserve original task exception class, native stage
counts, remaining original budget and custody flags on recurrence; no messages,
headers or payloads are printed. Assertions and the two-second allowance stay
unchanged. Keep this qualification limit visible separately from accepted
post-GO coupling; do not turn a later green run into a claimed causal fix.
