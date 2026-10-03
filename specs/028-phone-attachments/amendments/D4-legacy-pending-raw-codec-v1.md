# D4 precision amendment: bounded legacy pending raw fidelity

Status: PROPOSED_INTERFACE_PRECISION_ONLY; independent root acceptance pending. Earlier D4
interface receipts remain immutable. No raw parser/codec execution or disk adapter change.

## Concrete source boundary and normative repair

Existing `PhoneSend` allows 7680 UTF-8 text bytes, a nonempty <=256 UTF-16-unit profile without
C0/DEL, canonical UUIDv7, UTC DateTime and four exact states. It does not reject lone UTF-16 units:
the old UTF-8 size check counts replacement encoding while the JSON writer escapes the original
unit. Existing `phone_send_codec` has seven exact keys and canonical DateTime rendering. The new
32768 raw ceiling/scalar-only rule cannot be applied to every historical text record without loss.

Keep the public declaration `decodePhonePendingRecordBytes(Uint8List)` unchanged. Its raw envelope
is now **65536 bytes maximum**, rejecting invalid UTF-8 bytes, duplicate keys, trailing nonspace
data and JSON grammar/depth/member/array violations before any public DTO. After strict bounded
parsing, distinguish exact kind and enforce its own raw bound before return:

- `phone_attachment_send`: <=32768 raw bytes, unchanged 8192 combined wire ceiling, scalar Unicode
  in every parsed string including keys/unknown members, depth<=8, total members<=39,
  members/object<=8, elements/array<=4. No relaxation to unknown-kind or nested generic acceptance.
- `phone_send`: <=65536 raw bytes, exact original seven-key Map/PhoneSend value validation and
  UTF-16 codeunit fidelity, including legacy-accepted escaped lone surrogates. No normalization,
  trimming, text shortening, replacement-codeunit rewrite, phase inference or auto-send. Old
  nonblank text/7680 UTF-8 limit, profile validation and UTC DateTime/state rules remain exact.
- Missing/unknown kind or invalid schema: fixed `FormatException('malformed stored record')`, no
  empty snapshot/token and no overwrite or retry. The shape Map decoder still cannot certify raw
  duplicate keys, byte size, requested partition or sealed AAD.

Use the same finite structural ceiling39/depth8/8members/array4 while parsing both kinds; the
legacy exact schema contains only one seven-member object and no arrays. Raw strings retain their
decoded UTF-16 units until kind is known. Reject every unpaired surrogate for combined kind;
preserve old constructor semantics for legacy kind. Strict UTF-8 bytes never gain recovery decoding.

## DATA-only bound and definitions

Text worst-case escaping is <=6*7680=46080 ASCII bytes; profile <=6*256=1536. Canonical DateTime
fits32 characters, fixed UUID is36 ASCII and the longest state is submitted(9). Compact legacy
writer conservative total is **47798 bytes**, below65536. This is a safe envelope, not an attained
maximum claim; nonblank text and field rules can lower it. Synthetic C0-text/escaped-profile sample
is47783 bytes. The DATA companion records exact derivation and5 positive/7 negative definitions:
over32768 valid legacy text, lone text/profile units, pair+lone, exact text bound, blank/overflow,
duplicate kind, cap+1, invalid UTF-8, combined32768+1 and combined lone surrogate.

These are manual stdlib DATA definitions, not Dart codec executions or test passes. The future
tests must compare original UTF-16 codeunits and fixed-error/locked behavior, not re-encode lossy
UTF-8 and call it fidelity. No source/disk/schema/crypto/native/network/API/body limit, authority,
overwrite/CAS capability or operational attachment gate changes. The earlier private WIP parser
has not run or been accepted; it must be repaired only after this amendment is accepted.
