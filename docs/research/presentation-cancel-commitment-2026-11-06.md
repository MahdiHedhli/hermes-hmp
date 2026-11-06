# After-READY CANCEL commitment — November 6, 2026

The fixed original cleanup signer requires completed original signed READY evidence,
known joined work, frozen cleanup intent and existing write-quiescence/cancel facts.
Its partial owner is retained before native callbacks. `prepare` latches once
before the sole existing `_prepare_cancel` call; no already-consumed preparation
is eligible. It captures the exact native HBR1 frame, seq1 before GO or seq2 after
GO, and actual 16-byte CancellationWindow. Expected context derives from original
READY with fixed gateway/g2b CANCEL and actual native sequence. The signed original
work end remains separate from the earliest frozen cleanup end and body hash.

Current cleanup actor/role/input/transcript checks and remaining time are resealed
around native/crypto boundaries. Primitive row/end types precede comparison or
dictionary reconstruction. Refusal after preparation preserves its consumed
attempt/window/credit; no retry, renewed interval, signed raw publication or
socket-write completion follows. This slice signs data only. It does not authorize
pre-READY cancellation: missing/incomplete READY refuses signing while solely
local cleanup remains independent. Production sender, remote receipt/custody and
full cleanup qualification remain open.

Eight focused original-cleanup cases pass: seq1 and seq2 complete signing,
wrong Task, key retirement during encoding, expiry before and after native
preparation, and foreign expected-row/native-end tripwires with zero callbacks.
Budget work/end values remain unchanged (monotone sample time may advance), and
no cancel write is completed. Independent read-only source review accepted this
bounded signing-only scope. Selected affected regression: **887 passed**,
44.67 seconds; configured lint and whitespace checks passed. No live host,
settings/device, installed build or physical/release qualification changed.
