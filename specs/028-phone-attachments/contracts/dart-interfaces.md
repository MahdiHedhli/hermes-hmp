# Exact Dart attachment declarations — interface review candidate

No Dart implementation is included. These are declaration contracts for the next independently
accepted pure slice, not permission for native/storage/network/UI adapters. Existing `PhoneSend`
and its AP-6 classifier/constructor remain unchanged. All constructors validate the normative
schema with fixed content-free errors; lists are defensively copied and unmodifiable. All values'
`toString` is type/enum only, including records/stamps/capabilities/proofs; no generated record
printer exposing fields. Types live in `hmp_client`, without Flutter/native imports.
Invalid new DTO values/phase/reference transitions throw `ArgumentError('invalid phone attachment')`
without a value/name payload; no `ArgumentError.value`, input interpolation or retained raw cause.
The slot codec uses only its fixed `FormatException('malformed stored record')` instead. This does
not change legacy PhoneSend validation/error behavior.

## Value declarations

```dart
enum PhoneAttachmentMime { jpeg, png, pdf, plainText, markdown, csv }
enum PhoneAttachmentTargetState { present, absent }
enum PhoneAttachmentUnavailableReason {
  admissionUnavailable, targetUnavailable, validatorUnavailable, featureUnavailable,
}
enum PhoneAttachmentSendPhase { preMessage, messageMayTransmit, submitted, unknown, notSent }

final class PhoneAttachmentStamp {
  PhoneAttachmentStamp({required InstanceId iid, required int epoch,
    required String profile, required int phoneSlotGeneration,
    required int attachmentGeneration});
  InstanceId get iid;
  int get epoch;
  String get profile;
  int get phoneSlotGeneration;
  int get attachmentGeneration;
}
final class PhoneAttachmentLimits {
  PhoneAttachmentLimits({required int itemCount, required int itemBytes,
    required int messageBytes, required int outputEdge, required int sourcePixels,
    required int sourceEdge, required int sourceImageBytes,
    required int selectionSourceBytes, required List<PhoneAttachmentMime> normalizedMimes});
  int get itemCount; int get itemBytes; int get messageBytes; int get outputEdge;
  int get sourcePixels; int get sourceEdge; int get sourceImageBytes;
  int get selectionSourceBytes;
  List<PhoneAttachmentMime> get normalizedMimes;
}
final class PhoneAttachmentTarget {
  PhoneAttachmentTarget({required String binding,
    required PhoneAttachmentTargetState state, required DateTime expiresAt});
  String get binding;
  PhoneAttachmentTargetState get state;
  DateTime get expiresAt;
}
sealed class PhoneAttachmentCapability {}
final class PhoneAttachmentsUnavailable extends PhoneAttachmentCapability {
  PhoneAttachmentsUnavailable(PhoneAttachmentUnavailableReason reason);
  PhoneAttachmentUnavailableReason get reason;
}
final class PhoneAttachmentsAvailable extends PhoneAttachmentCapability {
  PhoneAttachmentsAvailable({required PhoneAttachmentTarget target,
    required PhoneAttachmentLimits limits});
  PhoneAttachmentTarget get target;
  PhoneAttachmentLimits get limits;
}
final class PhoneAttachmentLogicalItem {
  PhoneAttachmentLogicalItem({required String clientAttachmentId,
    required String sha256, required PhoneAttachmentMime mime,
    required int length, required String label});
  String get clientAttachmentId; String get sha256;
  PhoneAttachmentMime get mime; int get length; String get label;
}
final class PhoneAttachmentPayload {
  PhoneAttachmentPayload({required String targetBinding, required String text,
    required List<PhoneAttachmentLogicalItem> items});
  String get targetBinding; String get text;
  List<PhoneAttachmentLogicalItem> get items;
}
final class PhoneAttachmentUploadReference {
  PhoneAttachmentUploadReference({required PhoneAttachmentLogicalItem item,
    required String targetBinding, required String custodyReference,
    required DateTime expiresAt});
  PhoneAttachmentLogicalItem get item; String get targetBinding;
  String get custodyReference; DateTime get expiresAt;
}
final class PhoneAttachmentMessageRequest {
  PhoneAttachmentMessageRequest({required String clientMessageId,
    required PhoneAttachmentPayload payload,
    required List<PhoneAttachmentUploadReference> references});
  String get clientMessageId; PhoneAttachmentPayload get payload;
  List<PhoneAttachmentUploadReference> get references;
}
final class PhoneAttachmentSend {
  PhoneAttachmentSend({required String clientMessageId, required String profile,
    required PhoneAttachmentPayload payload, required DateTime createdAt,
    required PhoneAttachmentSendPhase phase,
    required List<PhoneAttachmentUploadReference?> references});
  String get clientMessageId; String get profile;
  PhoneAttachmentPayload get payload; DateTime get createdAt;
  PhoneAttachmentSendPhase get phase;
  List<PhoneAttachmentUploadReference?> get references;
  PhoneAttachmentSend withPhase(PhoneAttachmentSendPhase next);
  PhoneAttachmentSend withReference(int index, PhoneAttachmentUploadReference reference);
  PhoneAttachmentSend restoredAtOpen();
}

Uint8List canonicalPhoneAttachmentPayloadBytes(PhoneAttachmentPayload payload);
String phoneAttachmentPayloadHash(PhoneAttachmentPayload payload);
String phoneAttachmentMimeWireValue(PhoneAttachmentMime mime);
```

Stamp is immutable synchronous comparison data only, never read/send authority. Private controller
captures exact instance API/page/Phone-window/session/absence identity before await. Epoch/slot/
attachment generation monotonically invalidate on slot/session/target/grant/revoke/context loss,
including A→B→A. No send-readiness promotion, deferred-record application, automatic refresh/retry
or Bot scope. A new current stamp does not rehabilitate an old capture. Owned picker completion
requires current exact owned-picker ticket and fresh same target; stamp alone is insufficient.

All integer limits are positive within PA-7 lowering-only ceilings; stamp counters are nonnegative
monotonic values, never wrapped/reused. Target state exposes no native SID/key. Bindings/references
are canonical 43-character base64url of 32 bytes; dates are UTC and integer-millisecond representable.
Items are distinct canonical UUIDv7s; types/bytes/labels/text use PA-3. References must match their
payload's exact item order/value/target. Nullable reservation references align one-for-one with
items; every phase other than preMessage, including notSent, requires a complete matching list. withReference is
legal only in preMessage and cannot alter logical identity. restoredAtOpen maps only
messageMayTransmit to unknown; preMessage never implies an instruction was sent. Constructors do
not read clocks/files or establish current authorization; a target DTO is not a capability grant.

## Same pending slot and strict migration

Wrapper union preserves existing final `PhoneSend`; it does not subclass/change its library.

```dart
sealed class PhonePendingRecord {
  String get clientMessageId; String get profile;
}
final class PhoneTextPendingRecord extends PhonePendingRecord {
  PhoneTextPendingRecord(PhoneSend send);
  PhoneSend get send;
}
final class PhoneAttachmentPendingRecord extends PhonePendingRecord {
  PhoneAttachmentPendingRecord(PhoneAttachmentSend send);
  PhoneAttachmentSend get send;
}
final class PhoneSlotRevision { PhoneSlotRevision(); }
final class PhoneSlotSnapshot {
  PhoneSlotSnapshot({required PhoneSlotRevision revision, required PhonePendingRecord? record});
  PhoneSlotRevision get revision; PhonePendingRecord? get record;
}
enum PhoneSlotWriteResult { written, conflict, unavailable }
abstract interface class PhonePendingSlotStore {
  Future<PhoneSlotSnapshot> readPhonePendingSlot(InstanceId iid, String profile);
  Future<PhoneSlotWriteResult> compareAndWritePhonePendingSlot(
    InstanceId iid, String profile,
    {required PhoneSlotRevision expected, required PhonePendingRecord? next});
}
Map<String, Object?> encodePhonePendingRecord(PhonePendingRecord record);
PhonePendingRecord decodePhonePendingRecord(Object? json);
PhonePendingRecord decodePhonePendingRecordBytes(Uint8List utf8Json);
```

`PhoneSlotRevision` is a fresh process-local identity token minted/registered by the store on a
successful readable capture; user-constructed/unregistered tokens have no authority. It contains
no serialization/ID/path and cannot be persisted. The store compares the captured exact slot,
generation and record under its own atomic write/lifecycle fence, not token string equality. Each
new read/write invalidates prior slot tokens. Missing valid partition yields unavailable; corrupt/
unknown-kind/unsupported-version data throws fixed `FormatException('malformed stored record')`
and yields no empty snapshot/token. No old token can clear/overwrite another profile/kind/CMID.

Future `SavedContentStore` implements this additional port over the **same** phone-send filename
and partition/AAD. Existing writePhoneSend/readPhoneSend stay as legacy text facades: read throws
for combined/unknown kind; write, including null clear, refuses to replace/clear a combined or
unreadable slot. Existing text-kind behavior is preserved. `InstanceWriteScope` gains the exact
compareAndWritePhonePendingSlot signature with iid omitted and keeps its currency check and
instance lifecycle lock across the actual write. Byte upload/normalization never runs under it.
No second slot/file and no unconditional combined clear. The encrypted-file adapter's actual
revision/write format remains a separate reviewed gate; this port does not settle that format.

The map decoder validates shape/values only; duplicate JSON keys have already been lost by an
ordinary jsonDecode and cannot be detected there. The bounded raw byte decoder must reject
duplicate keys, invalid UTF-8/scalar Unicode, excess depth/member/count/length and invalid JSON
before producing the map. Stores use that strict raw decoder, not jsonDecode plus the map helper.
Exact byte responsibilities and legal phase/reopen graph are in pending-slot-codec.md.

## Combined classifier and transport declarations

```dart
enum PhoneAttachmentNotSentReason {
  badRequest, unauthenticated, forbidden, notFound, stale, expired,
  tooLarge, rateLimited, writeGateClosed, apiServerRefused,
  connectionRejected, tokenUnavailable,
}
enum PhoneAttachmentUnknownReason {
  admissionUnknown, malformedSuccess, idempotencyConflict, refusalUnproven,
  transportAfterHandoff, unrecognizedError, serverError, unexpectedFailure,
}
sealed class PhoneAttachmentSendResult {}
final class PhoneAttachmentSubmitted extends PhoneAttachmentSendResult {
  const PhoneAttachmentSubmitted();
}
final class PhoneAttachmentNotSent extends PhoneAttachmentSendResult {
  const PhoneAttachmentNotSent(PhoneAttachmentNotSentReason reason);
  PhoneAttachmentNotSentReason get reason;
}
final class PhoneAttachmentUnknown extends PhoneAttachmentSendResult {
  const PhoneAttachmentUnknown(PhoneAttachmentUnknownReason reason);
  PhoneAttachmentUnknownReason get reason;
}
PhoneAttachmentSendResult classifyPhoneAttachmentSend(PhoneSendObservation observation);

abstract interface class PhoneAttachmentByteSink {
  Future<void> write(Uint8List chunk);
}
abstract interface class PhoneAttachmentByteSource {
  int get length;
  Future<void> copyTo(PhoneAttachmentByteSink sink);
  Future<void> close();
}
abstract interface class PhoneAttachmentsApi {
  Future<PhoneAttachmentCapability> readPhoneAttachmentCapability(String profile);
  Future<PhoneAttachmentUploadReference> uploadPhoneAttachment(String profile,
    {required PhoneAttachmentTarget target, required PhoneAttachmentLogicalItem item,
    required PhoneAttachmentByteSource source, required bool Function() mayTransmit});
  Future<PhoneAttachmentSendResult> sendPhoneAttachmentMessage(String profile,
    {required PhoneAttachmentMessageRequest request, required bool Function() mayTransmit});
  Future<PhoneAttachmentReconciliation> reconcilePhoneAttachmentMessage(String profile,
    {required String clientMessageId});
  Future<PhoneAttachmentFetchedBytes> fetchOwnPhoneAttachment(String profile,
    {required PhoneAttachmentReadRequest request, required bool Function() mayRead});
}
```

```dart
enum PhoneAttachmentBytesState { available, expired }
enum PhoneAttachmentCaptionState { verified, unavailable }
final class PhoneAttachmentProjectedItem {
  PhoneAttachmentProjectedItem({required PhoneAttachmentLogicalItem item,
    required PhoneAttachmentBytesState bytesState, required String? custodyReference});
  PhoneAttachmentLogicalItem get item; PhoneAttachmentBytesState get bytesState;
  String? get custodyReference;
}
final class PhoneAttachmentReceipt {
  PhoneAttachmentReceipt({required String transportPayloadSha256,
    required PhoneAttachmentCaptionState captionState,
    required List<PhoneAttachmentProjectedItem> items});
  String get transportPayloadSha256; PhoneAttachmentCaptionState get captionState;
  List<PhoneAttachmentProjectedItem> get items;
}
sealed class PhoneAttachmentReconciliation {}
final class PhoneAttachmentReconciliationUnknown extends PhoneAttachmentReconciliation {
  const PhoneAttachmentReconciliationUnknown();
}
final class PhoneAttachmentRowPresent extends PhoneAttachmentReconciliation {
  PhoneAttachmentRowPresent({required int rowId, required String clientMessageId,
    required PhoneAttachmentReceipt receipt});
  int get rowId; String get clientMessageId; PhoneAttachmentReceipt get receipt;
}
final class PhoneAttachmentReadRequest {
  PhoneAttachmentReadRequest({required PhoneAttachmentTarget currentReadTarget,
    required int rowId, required String clientMessageId,
    required PhoneAttachmentProjectedItem item});
  PhoneAttachmentTarget get currentReadTarget; int get rowId;
  String get clientMessageId; PhoneAttachmentProjectedItem get item;
}
final class PhoneAttachmentFetchedBytes {
  PhoneAttachmentFetchedBytes({required PhoneAttachmentLogicalItem item,
    required Uint8List bytes});
  PhoneAttachmentLogicalItem get item; Uint8List get bytes;
}
```

Projected items are immutable defensive copies; available requires a canonical reference, expired
requires null. Receipt is transport metadata, never a native body/hash. RowPresent is a parsed API
observation, not client-created read authority: private controller reloads exact fresh own row and
same logical target before/after fetch, and the host independently repeats authorization/native
proof. New row IDs are positive <=2^53−1. Read target is fresh **present**, not the immutable original
Send binding; actual matching canonical session/lineage is proved privately. A renewed read binding
cannot change Send identity or revive an upload. Fetched bytes are defensively copied into an
unmodifiable view, <=item length/item cap, actual length/digest/MIME validated; its Future settles
only after the actual bounded network reader terminates, not when a lazy stream is handed out.
Read capability/receipt/ref constructors do not themselves authorize a read.

API belongs to one captured existing pinned instance API. No clock/credentials/path/backend in DTOs.
The admission classifier is total and distinct: first and only instruction attempt; contradictions,
unknown responses and after-handoff failures stay unknown. 202 requires exact submitted and no
error/applied contradiction; 200 unknown stays unknown. stale/expired/apiServerUnavailable require
strict applied:false. The pre-reserve PA-3 table is only for the first attempt and contradictory
applied:true/nonboolean stays unknown. Conflict never becomes notSent. Same rule as existing
beforeAnyByte/tokenUnavailable observation, without changing AP-6. The attachment API must strictly
validate its response envelope before building this existing observation vocabulary. It must not
use the legacy lossy fromWire factory as proof that unknown/missing/duplicate response fields were
valid. A malformed success maps to successState.other; an unrecognized/contradictory error maps to
unknown. The pure classifier does not inspect raw JSON or independently certify that parse.

The combined first-attempt classifier table is frozen as follows; an ERR-2 code must match its
existing allowed HTTP status before any row applies:

| Observation | Result |
|---|---|
| 202, submitted, no error, applied absent or strict true | submitted |
| 200, unknown | unknown/admissionUnknown |
| Other/contradictory 2xx | unknown/malformedSuccess |
| idempotency_conflict | unknown/idempotencyConflict, regardless of applied |
| stale, expired, api_server_unavailable with strict applied:false | notSent/stale, expired, apiServerRefused |
| Those three without strict applied:false | unknown/refusalUnproven |
| First-attempt pre-reserve bad_request; unauthenticated/revoked/wrong_instance; forbidden/unauthorized; not_found; too_large; rate_limited; write_gate_closed, applied absent/false | corresponding notSent reason (authentication aliases use unauthenticated; grant aliases use forbidden) |
| Same pre-reserve code with applied:true/nonboolean | unknown/refusalUnproven |
| Unrecognized or status-mismatched non-2xx | unknown/serverError for 5xx, otherwise unknown/unrecognizedError |
| beforeAnyByte connectionRejected/tokenUnavailable | corresponding notSent reason |
| Any other transport failure | unknown/unexpectedFailure for unexpected, otherwise unknown/transportAfterHandoff |

This table cannot classify a replay as a new first attempt. 200 unknown is never a notSent proof,
including contradictory input; malformed/unknown envelope parsing never emits a submitted
observation. No old AP-6 classifier changes or shared automatic retry behavior are authorized.

Byte source comes only from an owned validated staging handle, no filename/URI selector. Sink
chunks <=64 KiB; copyTo enforces declared total and settles only after actual reader termination.
close requests closure and awaits actual release; cancellation is not terminal proof. A held source/
reader future retains the operation budget until terminal, even if mayTransmit becomes false.
Pool handoff ambiguity is conservative; callback false prevents future bytes but proves no prior
bytes only if transport establishes beforeAnyByte. No automatic token-refresh POST replay.
This port is documentation, not raw streaming/storage/transport implementation permission.

## Closed validator interface (pure fake implementation only after review)

```dart
enum PhoneAttachmentValidationFailure {
  malformed, tooLarge, unsupportedType, metadataPresent, multipleFrames,
  cancelled, unavailable,
}
sealed class PhoneAttachmentValidationResult {}
final class PhoneAttachmentValidated extends PhoneAttachmentValidationResult {
  PhoneAttachmentValidated(PhoneAttachmentLogicalItem item);
  PhoneAttachmentLogicalItem get item;
}
final class PhoneAttachmentValidationRejected extends PhoneAttachmentValidationResult {
  const PhoneAttachmentValidationRejected(PhoneAttachmentValidationFailure reason);
  PhoneAttachmentValidationFailure get reason;
}
abstract interface class PhoneAttachmentValidator {
  Future<PhoneAttachmentValidationResult> validate(
    {required PhoneAttachmentLogicalItem expected, required PhoneAttachmentByteSource source});
}
```

Success means actual bytes/type/length/hash and closed normalized content policy validated, not
sniff-only or a claimed MIME. One-use owned source, no arbitrary file/network input; descriptor/
operation owner remains held until validation and worker/source close actually settle. Fake ports
are explicit test-only controls and never advertise availability. OS picker/normalizer DTOs and
owned encrypted-file adapters are deferred to their separately frozen exact platform/envelope seam.
Canonical own-row proof/readback controller/route wiring is separately gated; no client-produced
row proof class grants host byte authority.
