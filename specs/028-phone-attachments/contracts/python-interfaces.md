# Exact Python DTO/closed-validator declarations — review candidate

Documentation only: no Python module or executable fixture. Types below are planned in
`hmp_plugin.contract`; parser/hash functions in the planned pure portion of `phone_attachments`.
Native imports remain bridge-only. Frozen slotted DTO constructors must validate exact builtin
scalar/container types before inspecting values; no subclass hooks, arbitrary Mapping/Sequence,
generator traversal or truthy booleans as integers. Enum fields require the exact declared enum
type, not an arbitrary string/subclass. All collections below are exact tuples;
validated JSON input is an exact dict/list with bounded counts. No constructor creates authority.
Every DTO supplies content-free `__repr__` and `__str__`; dataclass repr does not expose fields.
Invalid DTO values raise `ValueError("invalid phone attachment")` without a field value/cause.
Pure wire parsers raise `ValueError("malformed phone attachment request")`; adapters later map
that to the fixed PA-3 bad_request envelope. No exception embeds input or a native error.

```python
class PhoneAttachmentMime(StrEnum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    PDF = "application/pdf"
    PLAIN_TEXT = "text/plain"
    MARKDOWN = "text/markdown"
    CSV = "text/csv"

class PhoneAttachmentTargetState(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"

class PhoneAttachmentUnavailableReason(StrEnum):
    ADMISSION_UNAVAILABLE = "admission_unavailable"
    TARGET_UNAVAILABLE = "target_unavailable"
    VALIDATOR_UNAVAILABLE = "validator_unavailable"
    FEATURE_UNAVAILABLE = "feature_unavailable"

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentLogicalItem:
    client_attachment_id: str
    sha256: str
    mime: PhoneAttachmentMime
    length: int
    label: str

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentPayload:
    target_binding: str
    text: str
    items: tuple[PhoneAttachmentLogicalItem, ...]

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentUploadReference:
    item: PhoneAttachmentLogicalItem
    target_binding: str
    custody_reference: str
    expires_at_ms: int

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentWireReference:
    item: PhoneAttachmentLogicalItem
    custody_reference: str

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentMessageRequest:
    client_message_id: str
    payload: PhoneAttachmentPayload
    references: tuple[PhoneAttachmentWireReference, ...]

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentTargetBinding:
    binding: str
    state: PhoneAttachmentTargetState
    expires_at_ms: int

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentLimits:
    item_count: int
    item_bytes: int
    message_bytes: int
    output_edge: int
    source_pixels: int
    source_edge: int
    source_image_bytes: int
    selection_source_bytes: int
    normalized_mimes: tuple[PhoneAttachmentMime, ...]

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentsUnavailable:
    reason: PhoneAttachmentUnavailableReason

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentsAvailable:
    target: PhoneAttachmentTargetBinding
    limits: PhoneAttachmentLimits

PhoneAttachmentCapability = PhoneAttachmentsUnavailable | PhoneAttachmentsAvailable

class PhoneAttachmentSendState(StrEnum):
    RESERVED = "reserved"
    SUBMITTED = "submitted"
    UNKNOWN = "unknown"
    REJECTED = "rejected"

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentReservation:
    iid: str
    user_id: str
    issuing_device_id: str
    profile: str
    client_message_id: str
    target_binding: str
    payload_sha256: str
    ordered_asset_ids: tuple[str, ...]
    caption_sha256: str
    caption_utf8_length: int
    state: PhoneAttachmentSendState
    created_at_ms: int

class PhoneAttachmentBytesState(StrEnum):
    AVAILABLE = "available"
    EXPIRED = "expired"

class PhoneAttachmentCaptionState(StrEnum):
    VERIFIED = "verified"
    UNAVAILABLE = "unavailable"

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentProjectedItem:
    item: PhoneAttachmentLogicalItem
    bytes_state: PhoneAttachmentBytesState
    custody_reference: str | None

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentReceipt:
    transport_payload_sha256: str
    caption_state: PhoneAttachmentCaptionState
    items: tuple[PhoneAttachmentProjectedItem, ...]

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentRowPresent:
    row_id: int
    client_message_id: str
    receipt: PhoneAttachmentReceipt

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentReconciliationUnknown:
    pass

PhoneAttachmentReconciliation = PhoneAttachmentRowPresent | PhoneAttachmentReconciliationUnknown

def canonical_phone_attachment_payload(payload: PhoneAttachmentPayload, /) -> bytes: ...
def phone_attachment_payload_hash(payload: PhoneAttachmentPayload, /) -> str: ...
def parse_phone_attachment_message(body: dict[str, object], /) -> PhoneAttachmentMessageRequest: ...
def parse_phone_attachment_message_json(raw: bytes, /) -> PhoneAttachmentMessageRequest: ...
def phone_attachment_message_wire(request: PhoneAttachmentMessageRequest, /) -> dict[str, object]: ...
```

Parsing checks PA-3 revision/closed vocabulary/shape, then exact items, distinct IDs, total length
and matched ordered refs. No target/reference lookup, auth, expiration clock, store or native call
in pure parsing. Thus idempotency lookup after auth precedes new expiry/claim checks. Timestamp
integers are nonnegative <=2^53−1; row IDs positive <=2^53−1 on the new routes. Existing identity/
profile validation is reused, never invented by strings in these DTOs. Target DTO exposes no native
SID/key; the server-private target record additionally captures the actual native present/absence
state and generations through existing authorized bridge lookup, never a wire parser.

Wire references match payload item/order and have no expiry or target-authority field. Upload
receipt references separately include the captured target and positive actual expiry. The parser
does not manufacture an upload receipt or an expiry sentinel. Before a new claim, custody lookup
proves every wire reference's real issuer/target/item/expiry; same-CMID replay needs no new lookup.
No syntactic DTO is advertised as validated custody.

Reservation is the durable host metadata without message text. The transient request's payload
has text; the reservation stores only its combined/caption hashes and length. No body/path/native
SID is mirrored into it. RESERVED restored after a possibly handed-off task becomes UNKNOWN, not
a safe resend. Stored response is the existing bounded redacted result, no body/prompt copy.
These declarations do not implement database schema, migrations, quota/custody or native dispatch.
The reservation uses the existing shared text/attachment Phone CMID namespace, with a payload-kind
discriminator, not a second table allowing the same native CMID. Its issuing_device_id must equal
the current authenticated device before replay/reconciliation/projection/bytes; same-user foreign
device gets fixed 404 without metadata. Raw JSON parser enforces 8192 bytes/depth 8, at most 29
object members in total, at most 6 members per object and at most 4 elements per array,
duplicate-key/UTF-8/scalar-Unicode rejection before map decoding; the map helper cannot detect
duplicates already removed. No arbitrary nested generic objects or native exceptions escape.

## Closed validator port

```python
class PhoneAttachmentValidationFailure(StrEnum):
    MALFORMED = "malformed"
    TOO_LARGE = "too_large"
    UNSUPPORTED_TYPE = "unsupported_type"
    METADATA_PRESENT = "metadata_present"
    MULTIPLE_FRAMES = "multiple_frames"
    CANCELLED = "cancelled"
    UNAVAILABLE = "unavailable"

@dataclass(frozen=True, slots=True, repr=False)
class OwnedPhoneAttachmentInput:
    fd: int
    expected: PhoneAttachmentLogicalItem

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentValidated:
    item: PhoneAttachmentLogicalItem

@dataclass(frozen=True, slots=True, repr=False)
class PhoneAttachmentValidationRejected:
    reason: PhoneAttachmentValidationFailure

PhoneAttachmentValidationResult = PhoneAttachmentValidated | PhoneAttachmentValidationRejected

class PhoneAttachmentValidator(Protocol):
    async def validate(
        self, source: OwnedPhoneAttachmentInput, /
    ) -> PhoneAttachmentValidationResult: ...
```

Owned input is internal custody-manager data, never a parser/wire constructor. The manager supplies
an already-authorized regular single-link owned read-only FD with verified identity/mode/length,
bounded offset/read count and exclusive operation ownership. The integer is not a file-read grant
to any client. No filename/path/URL or arbitrary bytes iterator enters this port. Validator reads
only this descriptor within declared/item limits; source metadata/type/hash are expectations, not
validation. Its success proves actual content, hash/length, dimensions/frame/metadata or original
PDF/UTF-8 policy. Native magic-only helpers do not satisfy it.

Custody owns descriptor lifetime; validator may neither publish/mint/copy into native cache nor
change permissions/write input/delete assets/run network. Cancellation/deadline requests stopping;
the actual validate future must remain pending until every worker/read terminates and is reaped.
Parent closes FD and releases budget only after that terminal future. A wedged backend retains
capacity and closes availability. Exceptions map to fixed unavailable without raw error logging.
One descriptor/input use, no implicit queue/retry or decoder-selected arbitrary plugin. Fake-only
ports are explicitly injected deterministic controls and cannot advertise production availability.
Package/ABI/worker containment and actual lifetime proof remain separately unselected/unadmitted.

## Native row/readback boundary

No public DTO is an authority-bearing native-row proof. Planned custody lookup may match its own
reservation/export metadata only after the bridge independently re-reads a canonical authorized
native user row/own-chat CMID/current session/lineage. Constructor strings, terminal submitted or
an upload reference cannot synthesize such proof. Before and after byte copying, the host repeats
current auth/generation and native row membership; failure emits no byte grant. Current fresh
present-target read binding may renew after 10 minutes while matching the original canonical
receipt's native target. That does not change the original Send hash/claim or revive unclaimed
uploads. No arbitrary private queue/session/path adapter or alternate readback authority is added.
