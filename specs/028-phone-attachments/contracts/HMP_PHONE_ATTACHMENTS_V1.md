# HMP Phone attachments revision 1

Status: D4 normative/interface and bounded pure-source v4 checkpoints independently accepted
(2026-10-03). Root's exact-v4 Python56, existing contract/module regression115 and Dart71 tests
passed with failures0; four-path Ruff and eight-path Dart analysis clean. This qualifies only
pure DTO/hash/classifier/codec/phase/restore/ports and fake-only causal work. No production route,
upload, readback, media/content decoder, durable storage adapter or attachment Send is implemented
or operationally admitted by this document.

This is the normative D4 successor to the historical Mobile spec 028 D1/D2/D3 candidate. It grants
only the bounded transport-custody category expressly named in HMP PR-1 and the Mobile constitution.
Hermes owns sessions, user rows, admission and execution. There is no authoritative HMP history,
message-text store, command queue, automatic retry, second owner or Bot-to-Phone fallback.

## PA-1 Scope, feature gate and native gap

Only user-explicit Phone Photos/Files composition is covered. Product + is absent while the
complete feature is unavailable; developer local staging is excluded from release artifacts.
Capability defaults closed. The Phone minimum `0.21.5` / `2026.9.24` applies; later, unknown and
development versions attempt the actual required APIs. No SHA/fingerprint/version allowlist,
tested-sample or qualification label determines runtime admission.

Actual native reject-policy settlement is required for the entire dispatch path. Every refusal
must leave zero queue, merge, steer, interrupt, user row or later instruction effect. Terminal
admission preserves the original full CMID, exact target and ordered media. A symbol, callback
boolean or `_gateway_accepted` scheduling flag is insufficient. Unreported, unfamiliar or failed
persistence outcomes remain unknown; no automatic retry. Native admitted is not model completion.

The inspected native `8afaab3703e336d72a72c812dd2dd249f04f166a` lacks `defer_policy` and
`admission_ticket` in MessageEvent. An HMP adapter busy override alone misses startup restore before
hooks, the post-await runner busy path and orphan FIFO. Its present-SID check also lacks atomic
exact-absent-session compare/create settlement. This bounded `PHONE_ATTACHMENT_ATOMIC_ADMISSION_GAP`
does not assert absence on newer builds with real reject-policy/ticket APIs. No private runner
patch, queue snapshot or FIFO alternative is permitted. The missing required settlement keeps this
feature closed on that path without closing ordinary text AP-6.

Exact source evidence:
[adapter guard/fallback](https://github.com/NousResearch/hermes-agent/blob/8afaab3703e336d72a72c812dd2dd249f04f166a/gateway/platforms/base.py#L3954-L4072),
[startup/busy/orphan entry](https://github.com/NousResearch/hermes-agent/blob/8afaab3703e336d72a72c812dd2dd249f04f166a/gateway/run_inbound.py#L1243-L1344),
[startup before hooks](https://github.com/NousResearch/hermes-agent/blob/8afaab3703e336d72a72c812dd2dd249f04f166a/gateway/run_inbound.py#L162-L255),
[runner handler ownership](https://github.com/NousResearch/hermes-agent/blob/8afaab3703e336d72a72c812dd2dd249f04f166a/gateway/run_adapters.py#L1594-L1667).

## PA-2 Authorization and exact target

Each operation checks pinned iid, bearer/device proof, active issuing device, approval-owner Phone
permission without host denial, served profile, current per-bot grant, direct-send flag and current
Phone/attachment API binding generation. Controls grant alone never grants Phone attachment access.
No supplied SID, native path, URL, label, row ID, filename or custody ID is authority.

The server derives the Phone chat/source/session key through the existing routed bridge. Target
binding is 32 random bytes encoded as canonical unpadded base64url (43 characters), non-bearer,
bound durably to issuer/device/profile and instance/device/grant/listener/API generations. Native
target state is either present with exact nonempty SID, or exact absent for that native session key.
The wire carries target state and opaque binding, never a caller-selected native SID/key.

Binding expires at most 10 minutes after mint. Renewal creates a different binding; it never
rewrites existing upload/reservation identity. Unclaimed bindings invalidate on revoke, grant loss,
listener generation change or session rotation. Reads never create a native session.
Attachment-first Send MUST be supported: native admission atomically compares absence and creates
the canonical session as this one original instruction, or refuses stale absence. A prior text
message, fabricated authorize/user turn or HMP-created native session is not a prerequisite.
Until this native API is present, absent-target Send is unavailable, not redirected or synthesized.

Check authorization before body, in final mint/claim transactions, at native strict target
admission and before/after readback copying. Recheck durable generations even if a CLI revoke runs
in another process. No token/network/decoder work under the store lock. Revoke prevents future HMP
reads immediately; bytes already handed to Hermes are delivered data and cannot be retracted.

## PA-3 Routes, schemas and fixed errors

All new routes are proposed, unimplemented, capability-closed. They use existing pinned transport,
device authentication and no redirects. Other body/header limits and legacy AP-6 are unchanged.

| Operation | Exact path under `/hmp/v1/bots/{p}/phone` |
|---|---|
| Capability | `GET /attachments/capability` |
| Raw upload | `POST /attachments/{client_attachment_id}` |
| Combined Send | `POST /attachment-messages` |
| Reconcile | `GET /attachment-messages/by-client-id/{cmid}` |
| Own-upload bytes | `GET /attachments/{custody_reference}/bytes` |

Capability success has exactly `revision:1`, `available:true`, `target_state:"present"|"absent"`,
`target_binding`, `target_expires_at` (UTC integer milliseconds), and `limits`. Limits has exactly
`item_count`, `item_bytes`, `message_bytes`, `output_edge`, `source_pixels`, `source_edge`,
`source_image_bytes`, `selection_source_bytes`, `normalized_mimes` (closed distinct ordered subset
of JPEG, PNG, PDF, UTF-8 plain/markdown/CSV). Each number is a positive non-bool integer and can
only lower PA-7 ceilings. Unavailability has exactly `revision:1`, `available:false`,
`reason:"admission_unavailable"|"target_unavailable"|"validator_unavailable"|"feature_unavailable"`;
no target binding. This field is diagnostic, never a version or fixture allowlist.

Raw upload uses required canonical `HMP-Attachment-Target`, `HMP-Attachment-SHA256`,
`HMP-Attachment-Label` (unpadded base64url of the validated UTF-8 label) and `Content-Type` headers.
Require one exact Content-Length, 1..8 MiB declared and actual bytes. Header aggregate stays 8 KiB.
Reject duplicate authority headers, chunked/Transfer-Encoding, Content-Encoding, multipart and
missing/conflicting length. No filename/path/URL input. Reader chunks are at most 64 KiB and no
byte beyond the declared/absolute bound is read. All other JSON routes retain 8 KiB; no global
`aiohttp` body-limit increase. Hash the actual bytes and independently validate actual content.

Successful raw upload has exactly `revision:1`, `client_attachment_id`, `custody_reference`,
`sha256`, `mime`, `length`, `label`, `expires_at` (UTC integer milliseconds). IDs are canonical
lowercase UUIDv7; SHA-256 is 64 lowercase hex; reference is canonical base64url of 32 random bytes.
Reference knowledge alone grants nothing; byte access requires its issuer and canonical own row.

Combined small JSON has exactly `revision:1`, `client_message_id`, `text`, `target_binding`,
`attachments`. Text is scalar Unicode, at most 4096 UTF-8 bytes; empty is legal for attachment-only
Send. Attachments is an ordered list of 1..4 distinct logical IDs totaling at most 16 MiB. Each has
exactly `client_attachment_id`, `custody_reference`, `sha256`, `mime`, `length`, `label`, all equal
to its validated custody record. Label is display-only, 1..128 UTF-8 bytes; reject controls,
slash/backslash and dot-only labels rather than truncate. Controls here mean U+0000..U+001F and
U+007F..U+009F; dot-only means one or more ASCII periods, not Unicode normalization. MIME is exactly `image/jpeg`,
`image/png`, `application/pdf`, `text/plain`, `text/markdown` or `text/csv`. Unknown/missing/duplicate
members, floats/bools as integers, invalid Unicode or noncanonical encodings are malformed.
Raw combined JSON parsing is bounded before generic decoding: depth <=8, <=29 total object
members, <=6 members/object and <=4 elements/array. Duplicate keys are rejected before maps lose
them. Limits do not excuse accepting an unknown member or nested generic value.
The actual serialized combined request must also be <=8192 UTF-8 bytes. Text's 4096-byte limit is
not a promise that escaped JSON fits; check eventual serialized size before reservation/upload
using fixed-width reference placeholders. Refuse without altering text or uploading, never raise
the JSON bound or truncate.

Readback requires `HMP-Attachment-Target` and `HMP-Attachment-Row` (canonical positive decimal native
row ID). Fresh native proof is reloaded; neither header grants access. Success is a bounded raw
body with exact validated Content-Type, Content-Length and HMP-Attachment-SHA256, never a path.
No generic artifacts/generated-output download authority is added.

Reconcile success is exactly either `{"revision":1,"state":"unknown"}` (no row proof) or an
object with `revision:1`, `state:"present"`, `row_id`, `client_message_id`, `receipt`. The latter
requires an actual fresh canonical authorized own user row and exact reservation/CMID/lineage
join. Receipt has exactly `transport_payload_sha256`, `caption_state:"verified"|"unavailable"`,
`items`; each projected item has exactly `client_attachment_id`, `sha256`, `mime`, `length`,
`label`, `bytes_state:"available"|"expired"`, `custody_reference` (43-character reference when
available, null when expired). Metadata hash is the original transport payload hash, not a hash of
native row content or model processing. Additive own-upload Phone snapshot/history row member
`phone_attachment_receipt` uses the same receipt; omit it for every other row. Do not invent a row
from a receipt. New row IDs are positive non-bool integers <=2^53−1.

Current byte reads use a fresh present-target binding with actual canonical row/session/lineage
matching the original receipt's native target. This permits same-device retained-blob readback
after the 10-minute write-binding TTL or listener restart; it never changes the original Send hash,
revives an unclaimed upload or authorizes a different session. Reconciliation requires current
auth and actual row evidence even if a stored outcome is submitted/unknown.

Fixed existing ERR-2 vocabulary: malformed/unsupported-type `400 bad_request`; authentication/
revoke/wrong-instance existing 401 codes; denied issuer/grant `403 forbidden`; unknown/foreign
asset/row `404 not_found`; new-CMID stale target `409 stale, applied:false`; new-CMID expiry
`409 expired, applied:false`; payload mismatch `409 idempotency_conflict` without definitive flag;
bound `413 too_large`; allocation/concurrency quota `429 rate_limited`; missing required API/
validator `503 write_gate_closed`; exact native nonadmission `503 api_server_unavailable,
applied:false`. Unknown is never rewritten into quota/expiry/refusal. No new free-form why/native
body/message/exception. Read/upload errors say nothing about an instruction. Classifier is distinct
from legacy AP-6; unrecognized/malformed combined outcomes fail to unknown.

## PA-4 Canonical identity, claims, outcomes and same pending slot

Logical payload bytes are UTF-8 compact JSON of
`["HMP1-PHONE-ATTACHMENT-SEND",1,target_binding,text,[[id,sha256,mime,length,label],...]]`.
Array order is preserved; no whitespace or normalization, literal scalar Unicode, standard JSON
escaping, integers only for version/length. Custody references and clocks are excluded. The hash is
SHA-256 of these bytes. Identity key is `(iid,user_id,profile,cmid)` with issuing device in its
record. Hash vectors and exact declarations live under spec 028/contracts.

After authentication/current issuer/profile authorization and bounded structural parsing, look up
existing full CMID before current target/reference expiry or claims. Matching hash returns stored
outcome without another handoff; changed text/target/order/ID/hash/type/length/label conflicts.
Revoked/stale devices cannot look up a CMID solely by knowledge. Expiry/target rotation cannot make
an existing unknown not-sent. Renewed transport references do not change logical identity.
Before returning any existing attachment-CMID outcome or receipt, stored `issuing_device_id` MUST equal the
current authenticated issuing device. A different same-user paired device gets fixed 404 not_found
without outcome/hash/metadata; knowledge/hash equality is not own-upload authority. Repeat this
issuer join for reconciliation, projection and byte reads. Phone text/attachments share the one
existing `(iid,user_id,profile,cmid)` reservation namespace; record payload kind separates hash
semantics. Cross-kind CMID reuse refuses without native handoff, never creates parallel rows in a
second idempotency table. Existing valid text-only AP-6 hash/outcomes are preserved.

For a new CMID, atomically reserve the CMID and claim the complete ordered list before native
copy/handoff. No partial claims; no second CMID can obtain claimed assets after handoff is possible.
Same-ID upload replay returns its original unexpired reference only for identical issuer/target/
actual bytes/type/label, never extends 10-minute TTL and never executes. Expired uploads cannot be
revived. Known pre-handoff refusal permits explicit review/new logical IDs after reservation
resolution. Ambiguity retains the old CMID and claim; no automatic message/upload retry or POST
401 replay, background resume, text-only substitution or alternate instance/target.

Only native terminal admitted produces 202 `{"state":"submitted"}`. Exact known native refusal
uses the fixed applied:false table. Missing/unknown/unreported/persistence-failed/timeout outcome
stores 200 `{"state":"unknown"}` or an uncertain fixed error without applied:false. A five-second
HTTP reporting wait does not release native/reader/decoder resource ownership prematurely.

Explicit Send writes a sealed combined reservation in the existing `(iid,profile)` Phone slot
before the first upload. New kind `phone_attachment_send`, format 1, is strict; legacy text kind
`phone_send` remains exact. A legacy/unreadable/unknown kind blocks sending and cannot be treated
as empty or overwritten/cleared by legacy writes. Combined phases: pre_message (no instruction
POST handoff possible), message_may_transmit (durably written before pool handoff), submitted,
unknown, not_sent. Restore message_may_transmit as unknown. Byte expiry preserves pending text/
asset identity/ambiguity. A comparison token and lifecycle lock protect the same slot; no second
attachment reservation file bypasses it. Generation loss drops UI proof while real futures remain
pending through terminal write/read/validation/native settlement and cleanup.

## PA-5 File custody, native transfer and retained redaction index

HMP staging is private, separate and non-swept. Generated internal names only, descriptor-relative
exclusive/no-follow creation, owned regular single-link 0600 files in owned 0700 directories,
identity checks through completion/cleanup. Temp → actual hash/type/length verification → fsync →
atomic final publication/mint with final authorization. Partial/failed readers mint nothing. Cleanup
deletes only proven own files and preserves descriptor replacement fences. No generic cache scan.

After auth/claim, create a bounded own copy in the actual target profile's native media cache via
the single bridge, not a caller path/native helper's unsafe defaults. Native event is DOCUMENT with
ordered actual MIME, `media_text_inlined=[False,...]`, exact `hmp:<own-chat-id>:<cmid>`, internal
false, gateway control false, native strict present/absent target precondition and no-defer policy.
DOCUMENT is correct classification, not FIFO permission. Native profile/backend translation,
sweep and admission remain fixture gates. Exports handed off or unknown are native-delivered data;
revoke does not unlink them or claim retraction. HMP source blobs expire after 24 hours; a claimed
10-minute reference never deletes a file the native turn may still need.

Proposed accepted finite bounds: 256 MiB custody plus outstanding native-export allocation,
256 MiB free reserve before allocation, 64 live assets/device, 256/instance; one raw upload/device,
two/listener, no waiting queue. Reserve all temp/copy maximums before bytes. Reader total 120 s,
inactivity 10 s, including terminal validation/cleanup; hung work retains capacity and closes the
feature rather than freeing a still-running operation. No lifetime/resource qualification claimed.

Redaction metadata is bounded/non-evicting: 1024 lifetime export entries/device, 4096/instance,
reserved atomically at claim. Capacity exhaustion refuses new attachments; no pruning command.
TTL/revoke/unpair removes blobs/read authority but retains generated own-export/target/CMID
redaction association, no caption/body/history copy. Never evict while native path-bearing history
may remain readable. Future pruning requires proof of native history removal and another contract.

## PA-6 Canonical own-row readback and privacy

Cards/bytes require fresh authorized native user row, exact own-chat CMID, matching session/lineage
and retained trusted HMP-created asset metadata. Duplicate/missing/wrong-session rows yield no
proof; flags, text echoes, assistant/tool rows and pending thumbnails never substitute. Recheck
before/after byte copying and after restart/paging. A carried/error/stale window cannot authorize
loading. Distinct Phone stamp/scope/controller proof; no Bot media binding substitution.

Label these as this device's uploaded attachments, not universal Hermes media inventory or model
processing receipts. Other devices get no byte grant through the identifiers. Expired bytes may
show an expired card only with actual canonical row and metadata; never read a MEDIA/path string.

Suppress native generated note text only on proved own-upload user rows. Recover a bounded caption
suffix only when its exact UTF-8 length/hash equals retained caption metadata; store no caption
text. Empty caption has an empty hash. Native transformation gives fixed caption-unavailable, not
reconstructed text. Redact only exact own-export paths using trusted retained metadata across this
authorized Phone conversation; no global host-path/MEDIA regex or new file authority. Return no raw
injected cache path. Values/errors/toString are content-free; no IDs, profile, session, filenames,
references, hashes, paths, thumbnails, bodies, credentials or native exceptions in logs/navigation.

## PA-7 Client normalization/staging and separate adapter gates

4 items, 8 MiB normalized/item, 16 MiB/message; output edge <=2048. Source image <=16 MiB,
selection originals <=32 MiB, source header <=120 MP and edge <=32768. OS subsampled decode admits
ordinary 24/48 MP Photos; do not restore the rejected 20 MP rule. One normalizer/platform instance,
two global, proposed 64 MiB working allowance/operation. JPEG quality 0.85, orientation in pixels,
no copied EXIF/location/ICC/text metadata; alpha uses stripped PNG, animation/multiframe rejected.
OS HEIC/HEIF → normalized JPEG/PNG or that platform Photos path remains unqualified. Documents
are original bytes: PDF (untrusted; prefix is no sanitation/render safety claim) or fully valid
UTF-8 plain/markdown/CSV without NUL. No archives/executables/SVG/HTML/inline PDF/automatic execution.

Encrypted drafts: 24 h or removal/unpair/revoke first; 16 MiB/message, 32 MiB/instance, 64 MiB global.
Nothing leaves the phone before explicit Send. Picker-scoped grants release on all terminal paths;
no source URI/path persists, no broad library/all-files permission. Review tray is explicit Phone,
cancel unchanged, per-item/remove-all, explicit text-only confirmation with staged items.

Before owned-file adapter code, independently freeze exact algorithm/key-purpose separation,
nonce uniqueness across rewrite/crash, AAD/context/ordinal/count/total length/digest/finality,
authenticated completion manifest, atomic/fsynced metadata/ciphertext publication and finite
temporary/cleanup lifetime. Chunk plaintext <=64 KiB, <=128 chunks/asset, sealed metadata <=8 KiB.
Corrupt/truncated/reordered/duplicate/extra/cross-context chunks expose no byte source. Existing
sealing keys/nonces are not reused by implication. This remains a separate gate.

Host JPEG/PNG validator independently verifies actual decode/dimensions/frame/metadata, not label
or native magic. Closed fake validator port can precede actual decoder/dependency/ABI/worker
memory/CPU/output/deadline/reap/read-only-input admission. No selected portable production decoder
is implied here. No production feature routes enable until admission, validator/privacy/storage
and complete native/physical-device/release gates clear; no simulator/source-only proof substitutes.
