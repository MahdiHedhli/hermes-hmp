# Canonical Phone attachment payload bytes — exact DATA contract

Revision 1; interface review candidate. No candidate Dart/Python code, codec test, decoder, crypto
package or native operation was executed to define these fixtures. The companion JSON is synthetic
metadata DATA, not valid image/document content or an operational attachment receipt.

## Logical identity

After closed PA-3 value validation, encode this array with exactly this order:

```text
["HMP1-PHONE-ATTACHMENT-SEND",1,target_binding,text,[[id,sha256,mime,length,label],...]]
```

`id` is the canonical lowercase UUIDv7 client attachment ID. SHA-256 is lowercase hex. MIME is the
exact closed wire string; length is a positive integer, never bool/float. Items retain their order
and have distinct IDs. The original write target binding is included, not a subsequently renewed
read target. No sorting, trimming, Unicode normalization, line-ending conversion or label rewrite.
Empty text with one item is valid. Hash is lowercase SHA-256 of the resulting UTF-8 bytes.

Custody references, expiry/creation/read clocks, CMID and a fresh read binding are outside this
logical array. CMID is separately part of the shared reservation identity key, so omitting it from
the payload hash does not permit a second instruction. Renewing a read binding or transport
reference cannot change the original Send hash, authorize a new claim or make unknown safe to retry.

## Exact JSON/UTF-8 algorithm

- Arrays use `[`/`]` and `,` with no whitespace. Version/length use unsigned base-10 ASCII digits
  without sign, fraction, exponent or leading zero. There are no object-key ordering decisions in
  the canonical logical array.
- Strings use ASCII double quotes. Escape double quote as `\"` and backslash as `\\`. Slash is
  literal `/`.
- Escape U+0008, U+0009, U+000A, U+000C and U+000D as `\b`, `\t`, `\n`, `\f`, `\r`. Other U+0000
  through U+001F use lowercase `\u00xx`, including leading zeros. Never escape those as alternative
  long/uppercase forms in canonical output.
- Every other valid Unicode scalar is literal UTF-8, including emoji, decomposed combining marks,
  U+2028 and U+2029. Do not ASCII-escape them, normalize them or escape HTML-sensitive characters.
  A valid UTF-16 surrogate pair represents its one scalar; lone high/low surrogates are rejected
  before encoding. UTF-8 is strict, without BOM or replacement characters introduced by recovery.
- Text has a 4096 **UTF-8-byte** bound, not a UTF-16/Python-character bound. Label has a 128 UTF-8-byte
  bound and PA-3 controls/path/dot-only rejection. Encoders do not override schema validation.

For validated builtin values, Python compact `json.dumps(..., ensure_ascii=False,
separators=(',', ':'))` then strict UTF-8 has this output. The inspected Dart 3.12.2 SDK JSON
stringifier statically has the same lower-hex C0/quote/backslash rules, preserves other scalars and
combines valid surrogate pairs. Its handling of lone surrogates is **not** schema rejection; the
future Dart validator must reject them first. This source comparison is not an executed
cross-language equivalence claim. Future implementations must independently verify the exact
UTF-8 hex and hash definitions, rather than treating encoder defaults as authority.

## Wire-size preflight

The wire object is separate from the logical array. For deterministic preflight/vectors, construct
compact JSON in this insertion order: `revision`, `client_message_id`, `text`, `target_binding`,
`attachments`; each item is `client_attachment_id`, `sha256`, `mime`, `length`, `label`,
`custody_reference`. Use the same escaping/UTF-8 rules. Each actual canonical CMID is 36 ASCII
characters; each canonical reference is 43 ASCII characters. Fixed-width placeholders therefore
give the exact eventual encoded length, independent of their random values. A serializer using a
different valid object-key order has the same byte length; it must use the frozen escaping rules.

Before reserving/uploading, require actual eventual wire length <=8192. A logical payload that
passes the 4096-byte text bound can fail that wire bound: 4096 NUL scalars expand to 24576 escaped
text bytes. Refuse without text truncation, upload, slot mutation or instruction bytes. That case
still has a well-defined logical hash for restoring/classifying a locked local record; a hash does
not prove the request admissible. The local pending-codec 32768-byte ceiling does not enlarge wire.

## Finite definitions and independent verification gate

`canonical-hash-vectors.json` contains **23 positive logical definitions, 16 negative logical
definitions and 2 negative raw-JSON definitions** (41 total). Every positive includes expected
canonical UTF-8 hex, SHA-256 and placeholder wire byte count/validation. Negative definitions have
no canonical/hash output. Raw invalid JSON is represented as hex so the fixture itself contains
only valid scalar JSON.

Cases cover empty-caption attachment-first, four mixed/order changes, text/label/original-binding
changes, excluded reference/clock/CMID/read-binding changes, emoji, composed/decomposed forms,
U+2028/U+2029, C0 controls, quotes/backslashes, exact4096-byte ASCII/emoji text, exact item bound,
overflow, bool/float lengths, UUID/SHA/MIME/label/count/total restrictions, duplicate raw keys and
lone surrogate rejection. These are finite interface definitions, not exhaustive parser coverage,
executed passes, byte validation, model compatibility or actual custody proof. All decoder/codec,
constructor/classifier, strict raw parser, lifecycle, storage, native and device tasks remain pending.

After independent interface acceptance, the pure slice must check these same frozen DATA bytes in
both languages and add causal type/unknown-schema/phase/classifier/fixed-error tests. Production
adapter, database migration, encrypted envelope, native send/readback and feature exposure are
separate gates.
