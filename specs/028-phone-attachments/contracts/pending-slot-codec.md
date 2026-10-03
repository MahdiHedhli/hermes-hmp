# Strict combined Phone pending-slot codec — exact review candidate

Pure syntactic raw/map codec and phase/restore source is independently reviewed and tested in
D4-P v4. No durable storage/CAS/filename migration or adapter implementation is qualified. The
accepted [legacy raw precision amendment](../amendments/D4-legacy-pending-raw-codec-v1.md) governs
the additive legacy envelope/fidelity path. Existing text kind `phone_send` and its exact seven-key
schema are preserved. Combined kind uses the **same** existing per-instance/profile Phone slot/filename
and sealing namespace; no attachment reservation sidecar or second send slot.

Combined top-level keys are exactly:
`format`, `kind`, `client_message_id`, `profile`, `payload`, `created_at`, `phase`, `references`.
`format` is integer 1; `kind` exactly `phone_attachment_send`; `created_at` the exact canonical
UTC ISO string already used by the text codec. Phase strings are exactly `pre_message`,
`message_may_transmit`, `submitted`, `unknown`, `not_sent`, corresponding to the Dart enum.

`payload` has exactly `target_binding`, `text`, `items`; each logical item exactly
`client_attachment_id`, `sha256`, `mime`, `length`, `label`. Values/order/bounds are PA-3/PA-4.
`references` is an array of exactly the same length/order. An unresolved entry is JSON null;
a resolved entry has exactly `custody_reference`, `expires_at` (UTC integer milliseconds).
Its item/target are inherited from the same positional payload item, not duplicated or mutable.
Only pre_message allows null. A complete reference list in pre_message still does not imply POST.
message_may_transmit is durably written before pool handoff and restores as unknown. Other phases
retain exactly the stored state; expiry does not erase text, IDs, reference or ambiguity.

The strict `decodePhonePendingRecordBytes(Uint8List)` parser first enforces <=32768 UTF-8 bytes,
maximum nesting depth 8, at most 39 object members in total, at most 8 members in any object,
at most 4 elements in any array, valid scalar Unicode and no
duplicate keys; rejects invalid JSON/trailing bytes without values in errors. The shape-only
`decodePhonePendingRecord(Object?)` cannot detect keys lost by a previous jsonDecode. It rejects
unknown kind/format/key/phase, missing/extra fields, malformed Unicode,
float/bool integers, invalid date/noncanonical timezone, null/mismatched list and invalid profile
with fixed `FormatException('malformed stored record')`. The store separately checks the requested
profile and sealed partition/AAD before returning a record; the decoder has no partition authority
argument and cannot itself establish that binding. Unknown schema is never null.
Text codec on a combined/unknown record throws; legacy writes including null clear cannot replace
combined or unreadable data. Compare-and-write requires the exact captured current slot revision
under the lifecycle fence, including clear. No code can clear based solely on a copied CMID string.

Legal `withPhase` graph (same phase is idempotent): preMessage→messageMayTransmit only with a full
reference list; messageMayTransmit→submitted/unknown/notSent; unknown→unknown; submitted→submitted;
notSent→notSent. All other transitions throw a fixed error. withReference is preMessage-only.
In particular, no unknown/submitted/notSent→preMessage. A proven first message refusal always
occurs after full references were collected; pre-message upload failures retain preMessage rather
than manufacturing a notSent instruction outcome with missing refs. restoredAtOpen only maps
messageMayTransmit→unknown.

Explicit review/slot clearing is separate from phase mutation: preMessage can clear only after all
owned upload/read futures settle and proof that no instruction POST was handed off; notSent can
clear after the exact definitive first-attempt result and real terminal cleanup; unknown/submitted
can reconcile/clear only against a current actual own native user CMID row and matching transport
payload metadata under the private foreground/lifecycle fence. No matching row leaves unknown
locked. A return to review creates a new reservation/CMID/logical asset IDs under fresh authority;
it never edits the old combined identity or causes a background retry. Byte expiry/revocation/
carried reads and an API row DTO alone do not clear a maybe-sent slot.

Plaintext combined stored record is bounded to 32768 encoded UTF-8 JSON bytes before sealing.
This is a local codec ceiling, not the separately unfrozen encrypted-chunk envelope. User text
<=4096 UTF-8 bytes can expand through JSON escaping, so the single **wire** combined request must
independently fit the unchanged 8192-byte route bound. Validate its exact eventual schema/encoded
length (using fixed-width placeholder references before upload) before reservation/upload. A wire
too-large refusal preserves the tray/text and emits zero upload/instruction bytes. Do not raise
JSON/network limits to fit a valid local record. A restored over-wire-bound record still blocks
the slot and is never silently shortened or changed to text-only.

Partial cipher/metadata/unknown-envelope/crash states expose no readable slot and cannot authorize
replacement. Exact atomic ciphertext/nonce/key/AAD/chunk adapter format remains a separate root
review prerequisite; these declarations do not certify the current sealed-file adapter for assets.
