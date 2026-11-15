# Signed RESULT discard data continuation — November 6, 2026

`SignedResultDiscard` extends the existing framing/digest data component. It
accepts only bounded already-consumed HBA1 and RESULT outer-header bytes, fixed
broker/b2g/sequence1 expectations and pinned signature keys/context. It derives
the exact next byte count itself. Header replay stops before any image body.
Subsequent body bytes feed only the bounded original-frame digest; they are not
retained in a new image accumulator. Authentication, header/frame size and final
full-frame digest checks remain independent. A terminal-looking body chunk is
still RESULT body data; no delimiter scan, overread, restart or terminal escape.

When given an existing partial-body `CommittedFrameDigest`, the parser checks
its exact header/commitment/binding and continues that SAME supplied object/hash
at its actual received count. It does not copy or restart the hash, or replay
already-consumed body bytes. Supplying a digest is not proof of original runtime
ownership: the upcoming typed runtime bridge must bind it independently to the
actual signed capture/body allocation. This helper performs NO socket IO, clock
sampling, role admission, read transfer, cancellation, terminal acceptance, ACK,
native release or publication. It cannot certify the caller's read authority.

Needed reads are bounded by exact framing and 65,536-byte body chunks. Sticky
refusal wipes the original bounded framing buffer. Supplied chunk/prefix aliases
are cleared and fresh stable errors raised outside native exception handlers;
synthetic marker tests inspect component traceback locals and context. It retains
existing framing/commitment metadata and hash state, not image bytes.

Independent review found two concrete pre-check issues: foreign expected keys
could be compared before exact typing, and paired foreign auth offsets could
reach index/arithmetic. Both are fixed with type-first key/schema checks and
per-stage exact integer/bounds/target/buffer predicates; zero-callback tests cover
the dictionary key and every post-prefix auth-offset stage. Review accepted the
repaired source/tests as DATA ONLY, with no reviewer execution or native actions.

The first fixture used independently generated alternate keys with the original
verification pins and failed before the intended parser call: one failed, 42
passed. Corrected valid alternate fixture then passed43; traceback cases passed44;
final key/offset causal matrix passed49 in0.25s. These runs overlap and are not
summed. Full regression is recorded after actual terminal completion.

The signed request reservation/read-ready bridge remains next. Reservation must
precede cause completion and suppress cancellation only for exact live original
registered wait/capture, known write quiescence, no in-flight I/O and frozen
remaining budget. Actual correlated wake on the original work actor then supplies
a DISTINCT one-shot read-ready notice. Neither is legacy gate._fact_origin or
work-joined. Cleanup remains sole CANCEL/ACK writer; the same original task/cursor
must drain and authenticate signed TERMINAL. Current whole-work-join signing
contracts cannot simply be weakened or bypassed. No live enablement occurred.

Historical broker failures, native sender-destination incident, full runtime
composition and physical/release character-image qualification remain open.
No host/device/build/config/grant/provider/deployment changed.

Contract review corrected an important grammar limit: this fixed RESULT data
helper is only one branch. Cleanup can receive a directly signed ABORTED TERMINAL
before RESULT at a legitimate record boundary; a partial authentication prefix
must remain on its original record until phase is authenticated. No speculative
RESULT parse followed by fallback is allowed. Runtime boundary dispatch remains
required; once RESULT is established its exact remainder cannot be skipped.
Normal OK still requires actual completed RESULT. No runtime gate was enabled.

Final expanded affected regression completed: **1,810 passed, one skipped in
152.20s**. Lint/whitespace pass. Focused49 overlap; no combined-total or device/CI
claim. The independently reviewed next handoff contract remains unimplemented.
