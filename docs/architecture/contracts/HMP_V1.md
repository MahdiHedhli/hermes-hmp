# Hermes Mobile Protocol (HMP) v1 — Contract


**Current contract review status (2026-10-02):** The clock mechanism, optional pin grammar and N3–N6 were accepted by the prior focused review. The independent D1/D2/D3 sentence review accepted the capacity/retention qualifications, per-`(app, env)` APNs connections and seal-expiry wording. Root resolved its remaining editorial status finding M1 by dating the pre-review statements below. This is contract-text acceptance only. Source, causal tests/vectors, interoperability, provider/device/deployment/release and owner choices O1–O6 remain pending. No task checkbox or security mechanism changed.

| | |
|---|---|
| Status | **APPROVED implementation baseline (OD-F1, 2026-09-25).** The owner ruled on `R0_FREEZE_REVIEW.md` (`R0_OWNER_DECISIONS.md` § "Freeze decisions (2026-09-25)"), subject to the bounded amendments listed there. This does **not** approve a nonconformant implementation, and it does not waive any transport or security requirement. It authorizes implementation work only in the scope OD-L2 ruled on: Feature F1 "Connect and browse", as amended (`FIRST_FEATURE_PLAN.md`). It does not by itself authorize upstream submission or any push (`R0_FREEZE_REVIEW.md` §11). |
| Contract revision | `1.0` (approved 2026-09-25). History: `1.0-rc1` (commit `8657ae5`) was found incomplete by the independent freeze-package review (FZ-R-1..19); `1.0-rc2` (2026-09-24) was the ADVANCED contract-author correction pass that the owner then approved as revision `1.0`. Additive amendments, still served as `/ready` `contract` `"1.0"` (V-3's freeze string; 1.x clients ignore routes they do not call, V-4): **1.1** session browsing (§6a), **1.2** direct send (§7a), **1.3** approvals and Phone chat (§7b, OD-F16); **1.6 (draft, not implemented)** host-local generated images (§7e). |
| Scope | The wire contract between the Hermes Bot Mobile client and the HMP plugin inside one Hermes gateway process. Hermes internals are out of scope, except where a clause states a dependency on a Hermes capability. |
| Implementation and evidence status | **Stated only in [`HMP_V1_CONFORMANCE.md`](HMP_V1_CONFORMANCE.md).** This document defines required behaviour. Approval of this contract text does not state that behaviour is implemented or proven; that is the conformance matrix's sole role. |

**Clause markers.** Every normative clause has an ID (for example `SUB-4`). The conformance matrix has one row per ID.
- **[ahead]**: the R0-E spike has no implementation of this clause. It is an implementation obligation.
- **[diverges]**: the spike does something different. The contract text wins, and the difference is an implementation obligation.
- **[pending: node]**: a named in-flight node is implementing it, or its runtime evidence is still being produced. Its status is settled when that node reports.
- Unmarked clauses have a spike counterpart. The matrix gives its evidence level, which may be as low as "source reviewed".

**Sources.**
- The R0-E spike wire: `E0_PLAN.md` §4 and its controller addenda, at `r0/e-hmp-spike` @ `5fd3d5c`.
- The feasibility findings: `R0_HMP_FEASIBILITY.md`.
- The ADVANCED reviews: `PROTOCOL_REVIEW`, `PROTOCOL_DELTA_REVIEW`, `E0_SECURITY_DESIGN_REVIEW`, `SECURITY_REVIEW_PAIRING_IMPL`, `SECURITY_DELTA_REVIEW`.
- The freeze-package review in `R0_FREEZE_REVIEW.md` §Review.
- The owner rulings in `R0_OWNER_DECISIONS.md`.

Normative keywords follow RFC 2119 and RFC 8174.

---

## 0. Principles (binding)

- **PR-1. Hermes is the authority.**
  - HMP is a transport and device-identity edge.
  - HMP MUST NOT approve, answer, queue, defer, retry or execute anything on Hermes's behalf.
  - HMP MUST NOT hold authoritative conversation, approval or run state.
  - HMP MAY keep **transport observations**: the in-flight `partial`, `turn.observed_state`, the approval-choice cache and the event ring. Each is labelled on the wire as an observation, never as Hermes truth. (Reworded per FZ-R-18.)
  - HMP's durable state is limited to device and identity records, token hashes, idempotency records (no message text), pairing-offer hashes, and the roster baseline.
- **PR-2. Closed plugin surface.**
  - HMP registers exactly two things: its platform adapter and its operator CLI.
  - Every Hermes internal is reached through one bridge module. Each such dependency is listed in §12 as a `HERMES_API_GAP`.
- **PR-3. One active instance.**
  - A client session is bound to exactly one instance (`iid`).
  - There is no cross-instance routing, fallback or retry (ADR-0007).
- **PR-4. Honest guarantees.**
  - The server advertises only guarantees it derives by the rules in §8.
  - Symbol or feature detection alone MUST NOT advertise a guarantee.
  - Clients MUST NOT assume a guarantee that is not advertised. A missing guarantee is `false`.
- **PR-5. No queue anywhere.**
  - The server holds no command queue.
  - The client holds no indefinite queue. Its pending-send state is bounded by `CLIENT_RETRY_WINDOW_S` (§7.4, §13).

## 1. Versioning and compatibility

- **V-1. v1 wire identifiers** [diverges]. The controller-recommended option on FZ-R-16. It is an owner decision at freeze (`R0_FREEZE_REVIEW.md` §5, OD-F6), and this specification assumes it.

  | Identifier | v1 value | Spike (v0) value |
  |---|---|---|
  | HTTP path prefix | `/hmp/v1` | `/hmp/v0` |
  | QR payload prefix | `hmp1:` | `hmp0:` |
  | QR `v`, request `v`, `/ready` `versions` | `1` | `0` |
  | Signature transcript tags | `HMP1-PAIR-REQ`, `HMP1-PAIR-RESP`, `HMP1-PAIR-DONE`, `HMP1-TOKEN`, `HMP1-SELF-REVOKE` | `HMP0-*` |
  | Hash domain tags | `HMP1-OFFER`, `HMP1-HOST` | `HMP0-*` |

  **Why v1 does not keep the v0 identifiers:**
  - v1 changes observable semantics against the spike: reset reasons, the write gate, `guarantees`, the error codes `bad_request`, `retry_state_lost` and `guarantees_unavailable`, the P4 and P5 outcome rules, and integer typing.
  - A spike build and a v1 build must therefore be distinguishable on the wire.
  - The spike's published vectors include fixed test private keys. Bumping the transcript tags domain-separates every v1 signature from every v0 signature, so no spike artefact can ever verify under v1.
  - The cost is one regeneration of the known-answer vectors with the existing independent generator (TR-14).
  - Spike (v0) builds are non-conformant. They MUST NOT be paired with v1 components.
- **V-2. Version selection.**
  - The QR `v` is authoritative. The client never selects a version from the network.
  - `/ready` `versions` is display and diagnostic only.
  - A client MUST NOT fall back to a lower version.
  - If the pinned listener does not serve `/hmp/v1`, that is "host needs an HMP update". It is never a reason to downgrade.
- **V-3. Contract revision.**
  - `/ready` returns `contract`: the contract revision string, `"1.0"` at freeze [ahead].
  - Revisions `1.x` are additive only: new optional response fields, new informational event types, new error codes that fall into an existing client-action class (§4), and new guarantee flags.
  - Anything else is a breaking change. It needs `v2` with every identifier in V-1 bumped together.
  - Constants in §13 change only by contract revision.
- **V-4. Client robustness.** Clients MUST:
  - ignore unknown response fields and unknown SSE event types;
  - treat an unknown `reset.reason` as a reset (refetch the snapshot);
  - treat an unknown submit or lookup `state` as `unknown`, which is non-definitive;
  - treat an unknown error `code` by its HTTP status class. For a submit, an unknown code is always non-definitive;
  - treat an absent guarantee flag as `false`.
- **V-5. Server strictness.** Servers MUST:
  - reject malformed values (§3, §4);
  - ignore unknown request fields. Signed transcripts cover only the named fields, so extra fields carry no authority.

## 2. Identities and types

| Name | JSON type and format | Minted by | Notes |
|---|---|---|---|
| Instance | — | — | One Hermes gateway process (OD-4). |
| `iid` | string: 52 chars, RFC 4648 base32, lowercase, unpadded, of SHA-256 over the SPKI DER of the instance P-256 key (uncompressed point) | HMP | Pinned from the QR code only. |
| Bot (`profile`) | string: a Hermes profile name in the served set | Hermes | Canonical bot id. `display_name` is presentation only, and never `profile` itself: today it is the desktop's own unnamed-profile naming rule (`apps/desktop/src/plugins/hermes-bots/labels.ts:54-63`, `displayName`) -- `default` reads as `Hermes`; any other id has `-`/`_` runs turned into spaces and each word capitalized. Hermes's own stored `profile.yaml` `display_name` is deferred: reading it (`hermes_cli.profiles.read_profile_meta`) would add `hermes_cli/profiles.py` to the read bridge's fingerprinted file set (`bridge_files`) and force every currently qualified build to be requalified (`docs/research/HERMES_PLUGIN_DURABILITY.md` §(c)), which is not worth it for a presentation-only field. |
| `user_id` | string: `hmpu_` + 32 lowercase hex | operator CLI at confirmation | Gateway user. Default is one new user per device (OD-5). |
| `user_ref` | string, opaque | HMP | In v1.0 it equals `user_id`. Clients treat it as opaque. |
| `device_id` | string: `dev_` + b64u of 16 random bytes (22 chars) | HMP at P2 | Opaque to clients. |
| `device_fp` | as `iid`, over the device SPKI | client and HMP | |
| `device_sas` | string: `upper(device_fp[0:20])` grouped `XXXXX-XXXXX-XXXXX-XXXXX` | client and HMP | 100 bits. |
| `oid`, `pairing_id` | string: b64u of exactly 16 bytes | HMP | Raw bytes in transcripts. |
| `conversation_id` | string: `"default"` | fixed | v1 defines one conversation per bot per user. Any other value returns `404 not_found` [diverges: the spike accepts any value and mints a row, E-SI-12(c)]. |
| `client_message_id` (cmid) | string: UUIDv7, canonical lowercase `8-4-4-4-12` hex | client, before first transmission | Server rejects any other form with `400 bad_request` [ahead]. |
| `message_id`, `head_message_id`, `base_message_id` | JSON integer ≥ 1, or `null` | Hermes (row id) | `null` head means an empty conversation. |
| `session_id` | string or `null`, opaque | Hermes | Informational. MUST NOT be used as conversation identity. |
| `live_id` | string, opaque | HMP | Ephemeral id of a streaming bot message. Never durable. |
| `request_id` / `clarify_id` | string, opaque | Hermes | Exec-approval and clarify ids. |
| `epoch` | string, opaque | HMP, per process | Changes on every HMP process start. |
| `seq` | JSON integer ≥ 0 | HMP | Monotonic within `(epoch, conversation)`. |
| Event id | string `<epoch>.<seq>` | HMP | SSE `id:` and `Last-Event-ID`. |
| `chat_id` | server-internal | HMP | `c_` + 128-bit random. Never on the mobile wire. The Hermes-side message id is `hmp:<chat_id>:<cmid>`. |

**Timestamps (ID-1).** Two kinds, never mixed:
- **Protocol-minted:** `ts`, `exp`, `confirm_by`, `access_expires_at`, `served_at`, `turn.since`, `sent_at`.
  - JSON integers, Unix seconds. Booleans and floats are rejected.
  - `served_at` [diverges: the spike emits a float] and `sent_at` [diverges: the spike accepts floats].
- **Hermes-sourced:** `messages[].created_at`.
  - A JSON number (it may be fractional), Unix seconds, informational.
  - Never signed, and never used for a deadline.

**Instance key custody (ID-2).**
- The instance key is anchored in the default profile's plugin data. It is bound to a hashed host id held **outside every Hermes home**, and to a store revocation epoch.
- If the key reaches another host or home by clone, backup or restore, HMP treats that as an identity change and revokes every device (ADR-0003 rule 8).
- The CLI refuses to create a second identity under a named profile [diverges: E-SI-11(d)].

## 3. Transport and encoding

**Transport**
- **TR-1.** HTTPS on the HMP-owned listener only. TLS 1.3 only. The certificate is self-signed over the instance key.
- **TR-2. Client pin** (a mobile-stack gate; see `R0_FREEZE_REVIEW.md` §11.3 G-MOB):
  - The client pins the certificate's SPKI to `iid` taken from the QR code.
  - **Unconditional post-handshake check** [ahead] (DR-15):
    - On **every** connection, after the handshake completes and **before the first application byte is written**, the client extracts the SPKI from the peer certificate and compares it with the pin.
    - This applies whether or not platform verification succeeded.
    - On a mismatch it closes the connection without writing.
    - **Application data MUST flow only on the connection whose peer SPKI was checked** (RV-1). A probe on a separate connection, followed by data on a new connection, does not satisfy TR-2. This applies to every request, the SSE stream and every signed request.
  - A certificate-error callback that fires only when platform verification fails (Dart `badCertificateCallback`, for example) MAY be used in addition. It MUST NOT be the only enforcement point. A CA-valid certificate would pass platform verification and never reach it.
  - **Empty trust store (configuration requirement).**
    - The client's TLS context MUST be configured with no trusted roots (for example `SecurityContext(withTrustedRoots: false)`).
    - This is a configuration requirement. The post-handshake check above, not the trust store, is what makes a CA-valid certificate insufficient.
    - Its effect against a CA-valid certificate must be shown per platform under G-MOB.
- **TR-3. Pin mismatch.** On a paired instance, a pin mismatch is an **identity-changed hard stop**. It is surfaced distinctly from network errors, and there is no silent re-pin (ADR-0003 rule 8).
- **TR-4. Bind and peers.**
  - The server binds only to loopback, `100.64.0.0/10` and `fd7a:115c:a1e0::/48`, and drops other peers with `403 forbidden {why:"peer_not_allowed"}`.
  - TLS-terminating proxies (Tailscale Serve HTTPS, Funnel) are unsupported and fail closed through the pin.
  - Tailscale provides reachability, never authorization (OD-1).
- **TR-5. Headers.**
  - Every authenticated request carries `Authorization: Bearer <access_token>` and `HMP-Instance: <iid>`.
  - An `HMP-Instance` mismatch returns `401 wrong_instance` before any token lookup.
  - No credential may appear in a URL, including the SSE URL.
- **TR-6. Limits** (values in §13):
  - body, JSON depth and header size give `413 too_large`;
  - streams per device give `429 rate_limited {why:"max_streams_per_device"}`;
  - rate limits apply per IP and per offer on P2, per IP and per `pairing_id` on P4, and per IP and per `device_id` on P5, giving `429 rate_limited`;
  - limiter and nonce tables are LRU-bounded.
  - Consequence: message `text` is bounded by `MAX_BODY_BYTES`.
- **TR-7. No exporter channel binding** (E-GAP-28; recommended, and an owner decision at freeze, `R0_FREEZE_REVIEW.md` §9, OD-F6). This is acceptable only while all three hold:
  - (a) the pin is enforced in the handshake against the same key that signs `isig`;
  - (b) `iid` is inside every device-signed transcript;
  - (c) TLS-terminating proxies are unsupported (TR-4).
- **TR-8. Key reuse.** The instance key serves as both TLS key and signing key. This is acceptable only together with TLS 1.3 and the domain-tagged, length-prefixed transcripts of TR-13.

**Encoding** (E-SI-4 and E-SDR-5 controller decisions)
- **TR-9. I-JSON.** Request bodies are I-JSON (RFC 7493): well-formed UTF-8, no lone surrogates, top level an object. A violation returns `400 bad_request`, never `500` [diverges: the spike returns `400 other {why}`, or `400 pair_failed` on pairing routes].
- **TR-10. Integers.** Every protocol-minted integer (ID-1, plus `v`, `seq` and row ids) is a JSON integer. Booleans and floats are rejected.
- **TR-11. base64url** is canonical only: unpadded, RFC 4648 §5 alphabet, and round-trip exact. Decoded lengths are exact:

  | Field | Decoded length |
  |---|---|
  | `oid` | 16 B |
  | `s` | 32 B |
  | `nd` / `ni` | 32 B |
  | `nonce` | 16 B |
  | tokens | 32 B |
  | `pairing_id` | 16 B |
  | `device_pub` | 91 B (P-256 SPKI DER) |

- **TR-12. Keys and digests.**
  - Device keys are P-256 with an uncompressed SEC1 point (65 B, leading `0x04`) inside SPKI. Anything else is rejected.
  - Token and secret digests are SHA-256 over the **raw decoded bytes**, never over the base64url text.
  - `secret_hash(tag, x) = SHA-256(tag ‖ x)`.
- **TR-13. Signatures.**
  - ECDSA P-256 with SHA-256 over the transcript bytes (not prehashed), DER-encoded. Verifiers accept both low-S and high-S.
  - `transcript(tag, f1…fn) = tag ‖ Σ (u32be(len fi) ‖ fi)`, where integers are u64be, strings are UTF-8, and binary values are raw bytes.
  - Field types per transcript:

  | Transcript | Fields, in order (type) |
  |---|---|
  | `HMP1-PAIR-REQ` | `iid` (str), `oid` (raw 16), `SHA-256(S)` (raw 32), `device_pub` (raw SPKI DER), `device_name` (str, exact wire value before sanitization), `nd` (raw 32) |
  | `HMP1-PAIR-RESP` | `iid` (str), `oid` (raw), `device_pub` (raw), `nd` (raw), `ni` (raw), `pairing_id` (raw 16), `device_sas` (str), `confirm_by` (u64) |
  | `HMP1-PAIR-DONE` | `iid` (str), `pairing_id` (raw), `nd` (raw), `ni` (raw), `ts` (u64) |
  | `HMP1-TOKEN` | `iid` (str), `device_id` (str), `SHA-256(refresh raw)` (raw 32), `ts` (u64), `nonce` (raw 16) |
  | `HMP1-SELF-REVOKE` | `iid` (str), `device_id` (str), `ts` (u64) |

- **TR-14. Known-answer vectors** are part of the contract.
  - They are generated by an implementation independent of any HMP implementation (`tools/gen_reference_vectors.py` in the spike, regenerated for the `HMP1-*` tags) [ahead].
  - v1 adds **negative vectors** that a conforming implementation must reject: a compressed-point SPKI, a P-384 SPKI, padded b64u, wrong lengths, a float `ts`, and a boolean `v` [ahead] (E-SDR-6).
  - The first mobile implementation MUST pass the full vector file before the contract is marked interoperable.

## 4. Errors

- **ERR-1. Body.** Every error body is:

  ```
  {"error": {"code": <code>, "message": <fixed text per code>, ...extras}}
  ```

  - `message` never echoes caller input.
  - The only allowed extras inside `error` are `why` (string), `authz` (an `AuthzState`), `head_message_id` (integer or null) and `definitive` (boolean).
  - v1.3 AP-4/AP-5 additionally allow top-level `applied` on prompt results.
  - One top-level sibling is allowed: a `503 guarantees_unavailable` body also carries `"guarantees":{…}` (GU-5).
- **ERR-2. Error table.** "Client action class" is what a client does. For a submit, "definitive" means Hermes will never execute this attempt.

| Code | HTTP | Raised by | Definitive for submit? | Client action class |
|---|---|---|---|---|
| `bad_request` [diverges] | 400 | any route: malformed JSON, wrong type, bad UUIDv7, bad conversation id | yes (nothing handed off) | Client defect. Log it, keep the draft text, no retry. |
| `unauthenticated` | 401 | auth middleware; P5 uniform failure; SSE close | yes | Refresh the access token (P5). If P5 fails, re-pair. |
| `revoked` | 401 | P5 for a **signed** request from a revoked device; refresh reuse; self-revoke of a non-active device | yes | Device credentials are dead. Wipe this instance's credentials and pending state, then show "removed from this Hermes". |
| `wrong_instance` | 401 | `HMP-Instance` ≠ serving `iid` | yes | Client defect or mis-route. Never retry against another instance. |
| `pair_failed` | 401 | P2/P4 uniform failure, including malformed crypto fields | — | Pairing failed. Ask the operator for a new offer. |
| `pair_denied` | 403 | P4 after operator deny, or a device that is not `ACTIVE` [ahead] | — | Pairing refused. Stop polling. |
| `forbidden` | 403 | per-bot gate (`authz` = `pending_operator` or `refused_allow_all`); peer policy | yes | Show the bot's authorization state. |
| `unauthorized` | 403 | submit refused by Hermes's own user-authorization gate | yes | Restore the draft and show the authorization state. |
| `not_found` | 404 | unknown route object: approval/clarify id not pending for this user, or unknown conversation | — | Refetch the snapshot. |
| `offer_used` | 409 | P2 on a non-open offer; P4 re-issue after the window | — | Ask the operator for a new offer. |
| `refused_allow_all` | 409 | P6 only | — | Tell the user the bot is configured for all users; HMP refuses it. |
| `not_routed` | 409 | per-bot gate or P6 (`authz` = `not_routed` or `not_served`) | yes | Bot not on this instance. Re-read the roster. |
| `busy` | 409 | submit: Hermes refused because a turn is running (P2) | yes | Restore the draft ("bot was busy"). |
| `conversation_changed` | 409 | submit: head ≠ `base_message_id`, including an anchor that no longer resolves after in-place compaction (P3/P3b, RO-8); extra `head_message_id`, and optionally `why:"history_rewritten"` | yes | Restore the draft ("conversation changed"), then refetch. |
| `expired` | 409 | submit: admission deadline passed (P3 `not_after`) | yes | Restore the draft. |
| `idempotency_conflict` | 409 | submit: same cmid with a different payload | **no** (an earlier payload under this id may have executed) | Client defect. Mark the local message **unconfirmed** (CL-7). |
| `stale` | 409 | approval or clarify no longer answerable | — | Refetch the snapshot. |
| `invalid_choice` | 409 | approval `choice` not among the offered choices | — | Client defect. |
| `offer_expired` | 410 | P2/P4 on an expired offer or pairing, including a lost P2→P4 state (§5 P4) | — | Ask the operator for a new offer. |
| `too_large` | 413 | limits | yes | Shorten the message (keep the draft). |
| `rate_limited` | 429 | limits | yes (submit is not rate-limited in v1.0) | Back off. Reads, P4 polls and P5 may be retried later; a submit is never retried automatically (CL-4). |
| `unsupported` | 501 | approval answer without the `approval_request_id` guarantee | — | Approvals are read-only on this instance. |
| `draining` | 503 | submit: gateway draining or restarting (P2) | yes | Restore the draft. |
| `lease_timeout` | 503 | submit: durable turn lease not acquired (P3) | yes | Restore the draft. |
| `guarantees_unavailable` | 503 | submit while the write gate is closed (§8, GU-4) | yes (HMP did not hand off) | Keep the draft. Composer is read-only for this instance. Show the reduced-guarantee state. |
| `retry_state_lost` [diverges] | 503 | P5 in-grace retry whose successor cannot be reproduced (E-SI-9) | — | Stop presenting that refresh token. Discard this instance's credentials and re-pair. |
| `other` | 503 / 500 | submit refusal with a definitive exit tag: extras `why` and `definitive:true` [diverges: the spike omits `definitive`]; per-bot gate `unverifiable` (`why:"unverifiable"`, `authz`); internal error (500, `why:"internal_error"`) | **only if `definitive:true`** | If `definitive:true`, restore the draft. Otherwise the send is **unconfirmed**: reconcile (CL-5). |
| `no_bot_chat` (v1.2, DS-4(2)) | 409 | direct send: no canonical Bot Chat exists yet for this bot | yes | Ask the operator to open this bot once on Hermes Desktop first. |
| `session_busy` (v1.2, DS-4(3)) | 409 | direct send: the lease-registry guard found another live writer, or the liveness read itself failed | **no** (Hermes never saw this attempt) | Restore the draft; plain retry once the busy state clears. |
| `stale_head` (v1.2, DS-4(4)) | 409 | direct send: the client's `expected_head` does not match the Bot Chat's current head | yes | Refresh (re-read via SES-2), then retry with the fresh head. Never a silent retry with the old value. |
| `write_gate_closed` (v1.2, DS-2(b)) | 503 | Bot Chat direct send lacks its owner switch, a Hermes API it needs (GU-2d), loopback configuration, or target profile key; on a §7b route also the `approvals` or `phone_chat` member being unavailable | yes (HMP did not hand off) | Keep the draft. Composer is read-only for this bot until its gate reopens. |
| `api_server_unavailable` (v1.2, DS-6) | 503 | direct send: the loopback call to `api_server` failed, timed out, or was refused (`401`) after the gate reported `"open_guarded"`; on a §7b route also a native approval answer that is not a recognised settlement (AP-5), or a Hermes helper that failed at use time (AP-7a) | **no** (ambiguous — reconcile via DS-8) | Treat as UNCONFIRMED (CL-2); reconcile (DS-8), never resend under the same cmid. |
| `cron_unavailable` (v1.4, CR-1) | 503 | mobile cron: flag off, a required Hermes API unavailable (GU-2d), missing scoped loopback endpoint, or uncertain upstream result | — | Refresh jobs before acting again. Never automatically retry a create or edit. |
| `model_unavailable` (v1.5, MD-1) | 503 | mobile default model: flag off, a required Hermes API unavailable (GU-2d), missing scoped picker endpoint, or Hermes read/write failure | — | Reopen the model screen and check the current selection before another write. |
| `media_unavailable` (v1.6 draft, LM-3) | 503 | host-local image fetch: the caller is an owner device but the host flag is off or the feature is unavailable (LM-1). Message: "image delivery is unavailable" | — | Show "Image unavailable". Do not retry automatically. |

- **ERR-2a. Read-compatibility refusal** (GU-2c; additive `other {why}` values, no contract revision; controller clarification, 2026-09-25).
  - `503 other {why:"hermes_build_unsupported"}` on every route except `/ready`, pairing routes included, when the running Hermes declares a version below the minimum supported version for reads (GU-2c), or its install cannot be found. An unknown, unlisted, newer or unreleased version is never refused for that reason.
  - `503 other {why:"hermes_read_dependency_missing"}` when a Hermes internal the read bridge actually needs is missing, mis-shaped or resolves outside the Hermes tree and standard library.
  - HMP makes no bridge call and hands nothing to Hermes. Definitive for submit: yes (nothing handed off).
  - Client action: show "Unsupported Hermes build" for this instance; keep saved content visible and labelled; never retry against another instance.

- **ERR-3. Per-bot gate.** Every `/bots/{p}/…` route except `POST …/authorize` runs Hermes's per-bot authorization query and allow-all canary first, and fails closed. Nothing reaches Hermes on refusal.

  | `authz` | Response |
  |---|---|
  | `pending_operator` / `refused_allow_all` | `403 forbidden {authz}` |
  | `not_routed` / `not_served` | `409 not_routed {authz}` |
  | `unverifiable` | `503 other {authz:"unverifiable", why:"unverifiable"}` |

- **ERR-4. Definitive `other` tags.** A submit `503 other` is definitive only for these exit tags: `bot_loop`, `no_runner`, `estop`, `capacity`, `no_durable_lease`, `no_handler`, `unresolved`, `key_mismatch`, `route_drop`, `pre_dispatch_drop`.
  - `persist_failed`, `unreported_exit`, `unknown`, and any tag not in this list (including `no_start` and `admission_control_unsupported`) are **non-definitive**. The server MUST answer those with `202 {state:"submitted"}`, never with an `other` error (E-PDR-5).
  - A server-side failure while handing the message to Hermes is also non-definitive [diverges: the spike returns `503 other {why:"unknown"}` for an exception in `handle_message`].

- **ERR-2b. Push `why` values** (v1.x draft, §7f; the explicit closed-set addition).
  - The `why` values this contract names form a closed set. The existing values are unchanged:
    `peer_not_allowed` (TR-4, with `403 forbidden`), `max_streams_per_device` (TR-6, with `429
    rate_limited`), `unverifiable` (ERR-3, PR6-1, with `503 other`), `internal_error` (ERR-2, with
    `500 other`), `history_rewritten` (RO-8, optional on `409 conversation_changed`), and
    `hermes_build_unsupported` and `hermes_read_dependency_missing` (ERR-2a, with `503 other`).
  - Four values are added: `push_disabled`, `relay_unconfigured`, `approvals_unavailable` and
    `push_capacity`. Each is allowed **only** on `503 write_gate_closed` from a push route (§7f).
    No other code carries them. `GET /push/registration` also reports the first three in the `why`
    field of its `200` body when `available` is false. `DELETE /push/registration` can carry only
    `push_capacity`; it is never refused with `push_disabled`, `relay_unconfigured` or
    `approvals_unavailable` (§7f PN-REG-3). When more than one availability value applies, the §7f
    PN-AV precedence chooses.
  - This adds **no new error code and no new error extra**: the ERR-1 list of allowed extras is
    unchanged, `409 stale` carries no extra (there is no `generation` extra), and the `write_gate_closed`
    row of ERR-2 is unchanged. Push routes reuse that code and its fixed message text. The app
    ignores message text and acts only on `code` and `why`. A client that does not know a `why`
    value treats it as that code's default (V-4).

## 5. Pairing and device credentials (ADR-0003; OD-1)

### P0 readiness (unauthenticated)

- **PR0-1.** `GET /hmp/v1/ready` returns:

  ```
  200 {"versions":[1], "contract":"1.0", "iid":"<b32>",
       "guarantees":{"no_defer":bool, "atomic_anchor":bool, "approval_request_id":bool, "confirmed_settle":bool},
       "write_gate":{"state":"open"|"open_guarded"|"closed",
                     "reason":null|"guarantees_unavailable"|"write_gate_closed"}}
  ```

  [diverges: the spike returns `{versions, iid, capabilities, guarantees}`. `contract` and `write_gate` are missing. The extra `capabilities` field is diagnostic, and clients ignore it (V-4).]
- It is display and diagnostic only. The client MUST NOT pin from it and MUST NOT act on `versions`.
- It returns no host details and no `install_id`.

### P1 offer (operator, host CLI)

- **PR1-1. Offer creation.**
  - `hermes hmp pair offer [--label TEXT] [--user USER_ID]` creates `oid` (16 random B) and `S` (32 random B).
  - It stores only `secret_hash("HMP1-OFFER", S)` (FZ-R-19), an expiry of now + `OFFER_TTL_S` (server-fixed), and an audit row.
- **PR1-2. Showing the secret.**
  - `S` is rendered once, inside the QR code, only to an interactive TTY. It is never logged or stored.
  - The CLI refuses when any `HERMES_SESSION_*` variable is present. These checks are **mitigations, not a boundary** (SEC-1).
- **PR1-3. QR payload.** `hmp1:` + b64u(JSON):

  ```
  {"v":1, "iid":"<b32>", "ep":["https://<magicdns>:<port>", "https://<tailnet-ip>:<port>"],
   "oid":"<b64u 16B>", "s":"<b64u 32B>", "exp":<int>}
  ```

- **PR1-4. Endpoint derivation.** `ep` values are derived from the listener's actual bind, not typed by the operator [ahead] (E-SI-11(c), FZ-R-19).
- **PR1-5. Client ingestion.**
  - The client ingests `hmp1:` **only from an in-app camera scan**: no deep link and no clipboard.
  - It rejects an unknown `v`, a non-integer or past `exp`, a malformed `iid`, a wrong-length `oid` or `s`, and any `ep` that is not https to `*.ts.net`, `100.64.0.0/10` or `fd7a:115c:a1e0::/48`.
  - Before P2, it shows the instance short fingerprint (`iid[0:20]` grouped) and the expiry.

### P2 request (device)

- **PR2-1. Request.**
  - The device generates a fresh P-256 `DK` **for this instance** and connects with the pinned TLS (TR-2).
  - It sends `POST /hmp/v1/pair/request`:

  ```
  {"v":1, "oid", "s", "device_name":"<≤64 B UTF-8, display only>", "device_pub":"<b64u SPKI>", "nd":"<b64u 32B>",
   "sig":"<b64u sig(DK, HMP1-PAIR-REQ)>"}
  ```

- **PR2-2. Server check order**, cheapest first:
  1. size and shape (`413`);
  2. per-IP rate limit, then per-offer rate limit (`429`);
  3. offer lookup and state: not open gives `409 offer_used` with no SAS; expired gives `410 offer_expired`;
  4. field decoding and lengths;
  5. `device_name` validation;
  6. constant-time secret-hash compare;
  7. possession-proof signature;
  8. atomic claim.

  Every failure not listed returns `401 pair_failed`. The offer burns after `OFFER_MAX_FAILURES` bad attempts. [diverges: the spike verifies the signature before the offer lookup, E-SI-8.]
- **PR2-3. `device_name` sanitization** is for storage and display only.
  - Filter by Unicode category, dropping `Cc`, `Cf`, `Zl`, `Zp`, `Co` and `Cn`. Then apply NFC. Truncate to `DEVICE_NAME_MAX_BYTES`. An empty result becomes `"unnamed device"` [diverges: the spike uses a denylist, E-SI-13].
  - The signature is verified over the exact wire value.
- **PR2-4. Success response:**

  ```
  202 {"pairing_id", "state":"awaiting_operator", "ni":"<b64u 32B>", "device_sas", "confirm_by":<int>,
       "isig":"<b64u sig(IK, HMP1-PAIR-RESP)>"}
  ```

  - The client verifies `isig` under the pinned key.
  - It then displays the SAS **only if** it equals its own locally computed `sas(fingerprint(DK))`. Otherwise it aborts and destroys `DK`.
- **PR2-5. Durable pairing nonces.** `nd` and `ni` are persisted with the pairing record, so a gateway restart between P2 and P4 does not lose them [diverges: the spike keeps them in process memory, and a restart gives `410 offer_expired`, E-SI-9].

### P3 operator confirmation (two-step, host CLI)

- **PR3-1. Listing.** `pair list` shows at most the first SAS group. The device-claimed name is quoted and labelled unverified.
- **PR3-2. Confirmation.** `pair confirm <pairing_id> --sas <full SAS> --label <label> [--new-user | --user <id> --yes-share]`.
  - Requires an interactive TTY and no `HERMES_SESSION_*`.
  - The SAS compare is constant-time. Three mismatches deny the pairing.
  - The operator label becomes the device label and the Hermes `user_name`.
- **PR3-3. `--user`.**
  - `--new-user` is the default.
  - `--user` MUST match the offer's intended user and have the `hmpu_` format. It prints that user's existing devices and grants, including instance-wide env allowlist membership [ahead] (E-SI-7(d)).
- **PR3-4. State rule.** Confirmation activates only a `PENDING` device, re-checked in the same transaction.

### P4 completion

- **PR4-1. Request.** `POST /hmp/v1/pair/complete`:

  ```
  {"pairing_id", "ts":<int>, "sig":"<b64u sig(DK, HMP1-PAIR-DONE)>"}
  ```

  The device polls at intervals of at least 2 s.
- **PR4-2. Outcomes**, in evaluation order after signature verification:

  | Situation | Response |
  |---|---|
  | pairing denied | `403 pair_denied` |
  | expired, or past `confirm_by` | `410 offer_expired` |
  | not yet confirmed | `202 {"state":"awaiting_operator"}` |
  | confirmed, but device not `ACTIVE` (revoked while pending or after confirmation) | `403 pair_denied` [ahead] (E-SI-7(c)) |
  | confirmed and `ACTIVE`, first issue | `200 {"device_id", "user_ref", "refresh_token", "access_token", "access_expires_at":<int>}` |
  | confirmed, tokens already issued, within `PAIRING_CONFIRM_WINDOW_S` of the first issue, `ts` fresh | `200` with a new family; the earlier family is revoked (lost-response re-issue) |
  | tokens already issued, after that window | `409 offer_used` |
  | pairing nonces unavailable | `410 offer_expired` (see PR2-5) |
  | any other failure | `401 pair_failed` |

  `confirm_by` bounds only pairings for which no tokens have been issued yet; after the first issue, the `PAIRING_CONFIRM_WINDOW_S` re-issue window governs (clarification 2026-09-25, F1 security review).

  **Host-side confirmation UI note (OD-F7, 2026-09-27; wire-level PR4-2 is unaffected).** This table describes the wire outcome of P4, which is the same regardless of how the operator decided to confirm. `hermes hmp pair offer`'s interactive one-command flow (server-modules.md "Operator CLI (F1 subset)") shows the operator the code it expects and asks "Does the phone show this code? [y/N]" instead of asking them to type the SAS — the operator's own visual compare against the phone's screen is what drives `pair confirm`'s activation here. `hermes hmp pair confirm --sas <SAS>` (the non-interactive and scripted path) is unchanged: it still requires the caller to supply the full SAS, compared constant-time with the same durable mismatch counter and burn limit as before OD-F7.

- **PR4-3. Fresh `ts`.** Every accepted P4 requires `|ts − now| ≤ CLOCK_SKEW_S` **and** `ts` strictly greater than the last accepted `ts` for that pairing [ahead] (E-SI-7(e), FZ-R-1(b)).
- **PR4-4. Token storage.** Tokens are stored server-side only as SHA-256 of their raw bytes.

### P5 token exchange

- **PR5-1. Request.** `POST /hmp/v1/auth/token`:

  ```
  {"device_id", "refresh_token", "ts":<int>, "nonce":"<b64u 16B>", "sig":"<b64u sig(DK, HMP1-TOKEN)>"}
  ```

- **PR5-2. Success response:**

  ```
  200 {"access_token", "access_expires_at":<int>, "refresh_token"}
  ```

- **PR5-3. Order and disclosure.**
  1. Rate limits.
  2. Shape and length checks.
  3. Device lookup.
  4. **Signature verification.** This happens before any response reveals device state or token state.
  5. Nonce replay check. The nonce is remembered **only after** the signature verifies.
  6. Refresh-owner check.
  7. Rotation.
  - A presented refresh token whose family is revoked (by operator revoke, detected reuse, or a PR4-2 lost-response re-issue) is disclosed as `401 revoked` only after steps 4–6 pass, the same as a revoked device (clarification 2026-09-25, F1 security review).

  Every failure returns a uniform `401 unauthenticated`, except in two cases, which return `401 revoked`: a correctly **signed** request from a revoked device, and detected refresh reuse. [diverges: the spike discloses `revoked` before verification and stores the nonce first, E-SI-8.]
- **PR5-4. Ownership and rotation.**
  - The presented refresh token MUST belong to the signing device. That is checked without mutating state; on a mismatch nothing changes.
  - Refresh tokens are single use and rotate. The rotation is **one transaction** [diverges: the spike uses several transactions, E-SI-9].
- **PR5-5. Retry grace.**
  - Presenting the same refresh token again within `REFRESH_RETRY_GRACE_S`, while its successor is unused, returns the same successor. This MUST survive a gateway restart [diverges: the spike keeps it in process memory].
  - If the successor cannot be reproduced, the server returns `503 retry_state_lost` and the client MUST NOT present that token again (ERR-2).
  - Any other reuse revokes the whole family and returns `401 revoked`.
  - Implementation note (compatible with PR4-4, F1 research R16): the server need not store the successor token itself. It MAY derive the successor deterministically from the presented token under a server-held secret (for example HMAC-SHA-256), storing only hashes. The server secret is protected at the SEC-1 boundary.
- **PR5-6. Access tokens.**
  - They are opaque, last `ACCESS_TTL_S`, and are bound to `(device_id, iid, token family)`.
  - A refresh token is never accepted as an access token, and an access token is never accepted at P5.
  - Access checks fail for any device that is not `ACTIVE`.
- **PR5-7. Expiry.** Refresh tokens expire after `REFRESH_IDLE_TTL_S` idle, and their family after `REFRESH_ABSOLUTE_TTL_S`. Expiry returns `401 unauthenticated`, and the device re-pairs.
- **PR5-8. Device-key rotation is re-pairing.** There is no in-place device-key rotation (FZ-R-19).

### P6 bot authorization

- **PR6-1. Request.** `POST /hmp/v1/bots/{profile}/authorize`, with an empty body. Authorization is decided only by Hermes's own per-profile stores, and fails closed.

  | Situation | Response |
  |---|---|
  | authorized | `200 {"authz":"authorized"}` |
  | allow-all active in either scope, or the never-enrolled canary is authorized | `409 refused_allow_all {authz}` |
  | not routed or not served | `409 not_routed {authz}` |
  | query failed or unscoped | `503 other {authz:"unverifiable", why:"unverifiable"}` |
  | otherwise | `202 {"authz":"pending_operator", "user_id", "instruction":"<fixed operator instruction naming 'hermes -p <p> pairing approve hmp <request_id>'>", "approve_command"? (PR6-4), "note"?}` |

- **PR6-2. No code relay.** Hermes's pairing-code reply is never relayed to the device.
- **PR6-3. Instance-wide note.** `note` is present when a transport-scope env allowlist is active. It states that such a grant is instance-wide (E-GAP-31).
- **PR6-4. `approve_command` (owner requirement, 2026-09-27).** The `pending_operator` response MAY
  carry `approve_command`: one copy-pasteable POSIX shell command, built only from fixed text, the
  served profile name and the caller's own `user_id` (never a Hermes pairing code, PR6-2), that
  finds and approves this user's own pending `hmp` request(s) on this profile via
  `hermes pairing list` / `hermes pairing approve`. This is additive under V-3 ("Revisions `1.x`
  are additive only: new optional response fields..."): a client on an earlier `1.x` build ignores
  it under V-4 ("ignore unknown response fields"), and a server that does not implement it simply
  omits the field. `approve_command` carries the same SR-5 conditional-wording property as
  `instruction`: it is never an assertion that a request exists (a command run when none is
  pending is a no-op).
- **PR6-5. In-terminal grant after pairing (OD-F8, 2026-09-27).** HMP still never approves a P6
  request itself (PR6-3 stands: it only ever *triggers* the request through the inert authorize
  hand-off, and only Hermes decides `authz`). What changed is where the operator's own consent to
  approve is given: right after `hermes hmp pair offer` completes a pairing, the same run may ask
  the operator to allow the phone's served bots and, on a yes, itself run Hermes's public
  `pairing list` / `pairing approve hmp <request_id>` as a subprocess (server-modules.md "Operator
  CLI (F1 subset)") — the same commands `instruction`/`approve_command` already name, just typed
  by the CLI on the operator's already-given consent instead of by the operator's own hands. This
  still only ever approves a *pending request* that already carries this pairing's own `user_id`;
  HMP never writes Hermes's approved-users files directly (PR-2, PR6-3's "HMP only discloses
  existing grants" is unaffected — this is the operator granting a new one through Hermes's own
  approval system, not HMP granting it).

### P7 revocation and liveness

- **PR7-1. Operator actions.**
  - `devices revoke <id>` revokes that device and all its token families atomically.
  - Revoking a user's last device prints the Hermes `pairing revoke` command for each profile where the user is still approved, and flags env allowlist membership. HMP never runs those commands.
- **PR7-2. Rotation.** `instance rotate-key` creates a new key and revokes every device. It **also expires every open offer and pending pairing** [ahead] (E-SI-7(b)).
- **PR7-3. Self-revoke.** `POST /hmp/v1/devices/self/revoke`, with bearer auth plus the body below. It revokes only the calling device.

  ```
  {"ts":<int>, "sig":"<b64u sig(DK, HMP1-SELF-REVOKE)>"}
  ```

  | Situation | Response |
  |---|---|
  | revoked | `200 {}` |
  | stale `ts` or bad signature | `401 unauthenticated` [diverges: the spike returns `401 other {why}`] |
  | device not active | `401 revoked` |
  | malformed | `400 bad_request` |

- **PR7-4. Hermes-side revoke.** `hermes -p <p> pairing revoke hmp <user_id>` removes that bot for all of the user's devices.
- **PR7-5. Stream liveness.** Every open SSE stream is re-checked every `WATCHDOG_INTERVAL_S`. The stream MUST close within `2 × WATCHDOG_INTERVAL_S` after any of these:
  - revocation of the device;
  - revocation of **the token family of the stream's own bearer** (reuse detection, P4 re-issue, self-revoke);
  - expiry of the access token;
  - loss of per-bot authorization.

  The last frame is:
  - `event: revoked {scope:"device"}` for a device or family revocation;
  - `event: revoked {scope:"bot"}` for a per-bot loss;
  - `event: unauthenticated {}` for expiry.
- **PR7-6. Instance-key rotation, as the device sees it** [ahead] (E-SI-14, FZ-R-1(c)). One deterministic sequence:
  1. After `rotate-key`, the running gateway detects the change on its next watchdog tick or next request, whichever comes first. It MUST then stop terminating TLS and signing with the old key.
  2. Open streams are closed. A final `event: revoked {scope:"instance"}` MAY be sent before the close.
  3. The listener then either restarts under the new key or stays closed until the gateway restarts.
  4. A pre-rotation device therefore sees either a connection failure (listener closed) or a **pin mismatch**, which is the identity-changed hard stop of TR-3.
  5. **No HTTP status is promised** to pre-rotation devices. Clients MUST NOT rely on `401 revoked` to detect a rotation.
  - The spike keeps serving the old key until a restart. That is acceptable for the spike only.
- **PR7-7. Admitted turns** keep running after a revocation or de-authorization. HMP delivers nothing further for them (EV-9). Stopping them is Hermes's policy (E-GAP-29; `R0_FREEZE_REVIEW.md` §9).

### Security boundary statement (binding; owner acknowledgement is part of freeze approval)

- **SEC-1. Operator boundary.** "Enrollment only by operator action" holds only up to the **Hermes OS-user boundary**.
  - A prompt-injected Hermes agent with shell access runs as the same OS user.
  - It can read the instance key file, write `ACTIVE` devices or token hashes straight into the HMP store, or run `hermes pairing approve` itself.
  - The TTY check and the `HERMES_SESSION_*` refusal **do not protect keys or stores from code running with the same filesystem authority**. They are mitigations only.
  - For the same reason, a Hermes build modified by same-user code can advertise capabilities it lacks (GU-2b).
  - The real control is upstream gap P11 (E-GAP-23): Hermes-native approval gating for authorization-granting CLIs.
  - HMP MUST NOT substitute its own global per-command approval layer for P11. That would be an authority model outside Hermes (PR-1, ADR-0006).
  - The S15 PTY and background-process sub-cases are `EVIDENCE_GAP`, not passes.
- **SEC-2. Roster metadata.** Every enrolled device sees the names of all served bots, each with its `authz` state, before any grant. This is an accepted OD-5 metadata residual (E-SI-12(d)).
- **SEC-3. Other host surfaces.** Pairing does not protect the host's other listeners: api_server, the dashboard, which runs as its own process and can approve Hermes pairing requests, and Hermes's `/api/status`. Host-hardening guidance ships with HMP (ADR-0003 rule 10; E-SDR-4).
- **SEC-4. Logging.** HMP never logs:
  - `S` or the `hmp1:` payload;
  - `nd` or `ni`;
  - tokens, signatures, private keys or `Authorization` headers;
  - Hermes pairing codes or message text.

  Only 8-character id prefixes and outcome codes are logged.

## 6. Roster, snapshot and history (ADR-0005, ADR-0007)

- **RO-1. Roster.** `GET /hmp/v1/bots` returns:

  ```
  200 {"instance":"<iid>", "served_at":<int>, "guarantees":{…}, "write_gate":{…},
       "bots":[{"profile", "display_name", "authz":"authorized"|"pending_operator"|"refused_allow_all"|"not_routed"|"unverifiable"}]}
  ```

  [diverges: `guarantees`/`write_gate` absent, `served_at` a float]
  - Content of bots the user is not authorized for is never exposed.
  - **Profile send availability (additive, V-3).** Each authorized bot MAY carry
    `"send_gate":{"state":"open"|"open_guarded"|"closed","reason":null|"write_gate_closed"}`.
    It describes the Bot Chat send route for that bot's own profile. A closed value is returned
    when the host switch, a Hermes API send needs (GU-2d), loopback configuration, or that profile's key is
    unavailable; neither the key nor its source is exposed. Bots without authorization omit the
    field and do not trigger a key lookup. The send route rechecks these conditions on every POST.
    A client that understands this field uses it for the selected bot's composer. If absent, it
    falls back to the roster's `write_gate` for older HMP builds, while retaining a rejected
    message as a reviewable draft. For old clients, roster `write_gate` is conservative: it is
    closed if any authorized served bot cannot send. `/ready` remains an instance-level
    diagnostic and does not assert that every named profile has a usable key.
- **RO-2. Roster as state** (E-PDR-6).
  - The client re-reads the roster on every reconnect and on `roster.changed`.
  - `roster.changed` is an optimization, never the source of truth.
  - A bot that leaves the served set is removed. It is never silently re-homed (OD-4).
- **RO-3. Snapshot.** `GET /hmp/v1/bots/{p}/conversations/default?limit=<n>` returns:

  ```
  200 {"conversation_id":"default", "session_id", "head_message_id",
       "messages":[{"id":<int>, "role":<Hermes role string>, "text", "client_message_id":<cmid>|null, "created_at":<number>}],
       "turn":{"observed_state":"idle"|"running"|"stop_requested"|"unknown", "since":<int>|null},
       "partial":{"live_id", "text"}|null, "partial_lost":bool,
       "open_requests":[{"kind":"approval", "request_id", "command", "description", "choices":[…]},
                        {"kind":"clarify", "clarify_id", "question", "choices":[…], "multi_select":bool}],
       "tail":{"epoch", "seq"}}
  ```

  - `client_message_id` is present on rows that HMP originated.
  - `role` is passed through from Hermes. Clients render `user` and `assistant`, and MUST tolerate other roles.
  - **Tool output (additive, V-3).** Optional fields on every `messages[]` item (RO-3, RO-6, and SES-2, which share this shape). Revisions `1.x` are additive only: new optional response fields. A client on an earlier `1.x` build ignores them (V-4, "ignore unknown response fields"). A server that omits them is an older plugin; the client still renders the row from `role` and `text`.
    - Hermes `messages` columns (`~/.hermes/hermes-agent/hermes_state_common.py`, the `messages` table): `tool_calls` TEXT (JSON) on assistant rows, `tool_name` TEXT and `tool_call_id` TEXT on tool rows. `SessionDB.get_messages` (`hermes_state_messages.py`) returns those columns and decodes `tool_calls` from JSON text to a list before HMP sees the row. Only `bridge.py` reads them. HMP never logs the text, the arguments, or the tool name (SEC-4).
    - On an `assistant` row, `tool_calls` is an array of `{"id", "name", "arguments", "arguments_truncated"}`. `arguments` is the call's arguments rendered as compact JSON (no insignificant whitespace), cut to 500 characters. `arguments_truncated` is true when that cut happened. The field is omitted when the row has no tool calls. `id` is the Hermes tool-call id (empty string when the row had none) and matches a tool row's `tool_call_id`.
    - On a `tool` row, `tool_name` and `tool_call_id` are those columns, omitted when null. `text` is the tool output cut to 4000 characters. The full output is never sent above that cap. `truncated` is present and `true` only when that cut happened; absent means the output was not cut. `role` stays `"tool"`.
    - **Optional `media` (v1.6 draft, §7e).** A `tool` row MAY carry `media`: `{"kind":"image","ref":"<43-char base64url>"}`, only when the §7e gate is open. When the gate is closed the field is absent and the response bytes are identical to those of a server without §7e.
  - `turn` and `partial` are HMP **observations** (PR-1).
  - `open_requests` are scoped to this user's session.
  - **v1.3 (§7b).** While the direct-send flag is on, this snapshot's `open_requests` lists the
    caller's **Phone chat** prompts only (Bot Chat prompts are only on `GET …/prompts`). Each
    object keeps the RO-3 fields (`kind`, `request_id` or `clarify_id`, `command`/`description` or
    `question`, `choices`, `multi_select`). `awaiting_text`, `expires_at` and `surface` are extra
    fields a client that does not know them ignores (V-4).
- **RO-4. Tail lower bound.** `tail` is read **before** any other state, so it is a lower bound. A client that resumes from it cannot miss an event (E-PRV-12).
- **RO-5. `partial_lost`** is true only when HMP's in-flight buffer was lost across an HMP epoch change during a running turn. It is never true merely because no chunk has arrived yet (E-PDR-12(a)).
- **RO-6. History.** `GET …/conversations/default/messages?after=<id>&limit=<n>` returns either:
  - `200 {"messages":[…], "head_message_id"}`, or
  - `200 {"reset":{"reason":"cursor_not_resolvable"|"lineage_changed"|"session_replaced"|"history_rewritten", "snapshot_required":true}}`.

  `session_replaced` is returned when the conversation's session was replaced under the client: `/new`, auto-reset, a CLI `--resume` that ends the session (`cli_close`), or a pruned or replaced route (E-PDR-4/7).
  - The server MUST detect a replacement that happened while HMP was not running. That means persisting its per-conversation session baseline, as it already does for the roster baseline (E-PDR-6).
  - [diverges: the spike's baseline is in memory only. After an HMP restart, such a replacement surfaces as `cursor_not_resolvable`. It is still a reset, so nothing is lost silently, but it is not `session_replaced`. Spike `CONTRACT_CONFORMANCE.md` row 4.5.]
- **RO-7. Head semantics.**
  - `head_message_id` is the row id that Hermes's admission precondition compares against.
  - Clients echo it verbatim as `base_message_id`.
  - Until Hermes exposes a conversational head or generation API (P6, E-PRV-11), the head may include non-conversational rows and may move after a turn appears finished. Clients MUST tolerate `conversation_changed` in those cases.
- **RO-8. Row ids are not stable across in-place compaction** [ahead] (DR-19).
  - Hermes's default compaction is in place. It archives the active rows and re-inserts the retained tail with **fresh row ids**. The session id does not change, and Hermes emits no signal.
  - Any anchor, cursor or `message_id` a client holds can therefore stop resolving, including the `message_id` returned in a `200 accepted`.
  - **Detection.** HMP MUST detect that a conversation's history was rewritten. It may use any of these:
    - (a) the head row id or the client's cursor row id is no longer active;
    - (b) the active row count dropped below what the cursor implies;
    - (c) an upstream history or compaction epoch, or a compaction event, when Hermes provides one: `HERMES_API_GAP` P13 (`R0_FREEZE_REVIEW.md` §3).

    Until P13 exists, detection is heuristic.
  - **Signal.** On detection HMP emits a reset with reason `history_rewritten`, both on history (RO-6) and on the SSE tail (EV-2). The client discards its cached rows for that conversation and re-snapshots.
  - **Stale anchors.** A submit whose `base_message_id` no longer resolves is a **definitive** rejection: `409 conversation_changed {head_message_id}`, and HMP MAY add `why:"history_rewritten"`. Hermes never executes it (P3/P3b refuses at admission). The client restores the text as a draft, and the user must act explicitly (CL-3). There is never an automatic resend.
  - **De-duplication.** Clients MUST NOT de-duplicate or merge conversation rows by row id across a reset. HMP-originated rows are identified by `client_message_id`. Everything else is replaced wholesale by the new snapshot.

## 6a. Session browsing (v1.1, amendment A1; OD-F9, OD-F10)

Additive under V-3 ("Revisions `1.x` are additive only: new optional response fields... new error
codes that fall into an existing client action class"): a client on an earlier `1.x` build ignores
these routes entirely (V-4). Design and evidence: `specs/001-connect-and-browse/amendments/
A1-session-browsing.md`. Read-only: no send, no resume, no session mutation, from mobile, ever
(every F1 read-only rule continues to bind). Supersedes OD-F4 ("mobile-originated continuity
only") for reads only; OD-F10 records that a device authorized for a bot may read every session of
that bot from every source, on a single-user host (multi-user hosts are future work); **OD-F11
(2026-09-27, same day) narrows which sessions are actually listed** (below) without touching
OD-F10's bot-level authorization gate.

**OD-F11.** "Bot chats are only done in one channel at a time... our app should not communicate
with terminal and Discord/Telegram channels... just the ones from the bot view." SES-1 lists only
the bot's own canonical "Bot Chat" (Hermes Desktop Bots view's forever-chat, identified by Hermes
itself as the session titled exactly "Bot Chat" and always hidden — cross-checked against
`apps/desktop/src/plugins/hermes-bots/canonical-chat.ts`, `tools/bot_mode_probe.py` and
`hermes_state.py`'s `SessionDB.CANONICAL_BOT_CHAT_TITLE`, all in `~/.hermes/hermes-agent`) plus the
caller's own session (`is_mobile`, SES-1d). No CLI, Telegram, Discord, cron or other channel
session is ever listed, whatever its own title. The authorization gate (bot-level `authz =
authorized`, SES-3) is unchanged.

- **SES-1. `GET /hmp/v1/bots/{p}/sessions?cursor=&limit=`.** Auth: bearer + per-bot gate (ERR-3),
  identical order to every existing `/bots/{p}/…` route.

  ```
  200 {"sessions":[
         {"session_ref":"ses1_<22 chars b64u>", "title":<string|null>,
          "source":"<platform label>", "started_at":<int>, "last_active_at":<int|null>,
          "message_count":<int>, "is_mobile":<bool>}
       ],
       "next_cursor":"<opaque string>|null"}
  ```

  - **SES-1a. `session_ref`, never the raw Hermes `session_id`.** A new, opaque per-`(user_id,
    profile, session_id)` identifier (`ses1_` + b64u of 16 random bytes), minted the first time a
    session is included in a listing and stable thereafter (same session ⇒ same ref on every
    later listing and across restarts). `GET .../sessions/{ref}/messages` (SES-2) resolves
    `ref → session_id` scoped to the caller's own `(user_id, profile)`; a `ref` from another user
    or another profile is `404 not_found`, never disclosed as "exists but not yours".
  - **SES-1b. `title` and `source` are neutralised** the same way `device_name` is (PR2-3): Unicode
    category filtering (`Cc`, `Cf`, `Zl`, `Zp`, `Co`, `Cn` dropped), NFC, byte-length truncation.
    `title` is Hermes/host-controlled text (model-generated or operator-set) and MUST NOT be
    treated as trusted markup.
  - **SES-1c. Never on the wire, by design:** `session_key`, the raw Hermes `session_id`,
    `cwd`/`git_repo_root`/`git_branch`, `billing_*`/`*_cost_usd`, `model`/`model_config`,
    `system_prompt*`, `handoff_*`, `profile_name`/`transport_profile`.
  - **SES-1d. `is_mobile`.** `true` iff `session_ref`'s underlying `session_id` equals the id
    `GET …/conversations/default` resolves today for this `(user_id, profile)`. That route stays
    unchanged; the session list simply also contains this same session, flagged `is_mobile:true`.
  - **SES-1e. Ordering, pagination, cursor.** Rows are most-recently-active first. `next_cursor` is
    an opaque base64 of `{"o": <offset>, "v":1}` (an **offset** cursor, not a keyset one): a
    session created, updated or re-sorted between two page fetches can shift offsets, which may
    show a duplicate row (harmless — rows are keyed by `session_ref`) or transiently omit one
    until the next full refresh. A cursor is never signed: tampering with it can only change which
    offset is read within the caller's own already-authorized, already-profile-scoped query. A
    malformed cursor is `400 bad_request`.
  - **SES-1f. Size and default exclusions.** `limit` default 30, max 100. The route never returns a
    total session count beyond what's paged (no `total`/`count` field) — exposing an exact count
    would let any authorized device cheaply fingerprint host activity across all its users.
    `next_cursor: null` signals "no more pages".
  - **SES-1g. `exclude_sources` default is empty** (owner ruling, 2026-09-27, OD-F10's original
    wording): "all sessions of approved bots". **Superseded in effect by OD-F11** (§6a intro,
    above): the plugin applies a bot-view selector after the Hermes call regardless of
    `exclude_sources`, so a channel session is excluded whatever that setting says.
    `exclude_sources` remains unused plumbing for a possible future host-side narrowing, not how
    OD-F11 is enforced.

- **SES-2. `GET /hmp/v1/bots/{p}/sessions/{ref}/messages?after=&limit=`.** Auth: bearer + per-bot
  gate (ERR-3), identical order to `GET …/conversations/default/messages` (RO-6). A thin
  reparameterization of the existing bridge, never a new read path: `head`/`latest`/`after`/
  `lineage` already take an arbitrary `ConversationRef`, not only the one `conversation_ref()`
  resolves.
  - **Snapshot-equivalent (no `after`, or `after=0`):** `200 {"session_ref", "messages":[…],
    "head_message_id", "truncated":bool}`, via the same `limit` default/max as RO-3
    (`SNAPSHOT_LIMIT_DEFAULT`/`_MAX`). No `turn`, `partial`, `partial_lost`, `open_requests` or
    `tail`: those are HMP's own live-turn observations for the conversation it brokers, and are
    meaningless for a session HMP never runs a live tail for (F1 registers no SSE route, FR-053).
  - **Paged (`after=<id>`):** exactly RO-6's shape and reset algorithm (`HISTORY_RESET_REASONS`,
    `_lineage_reset`), generalized from "the one baseline row keyed `(user_id, profile)`" to "one
    baseline row keyed `(user_id, profile, session_id)`" — reuses `HISTORY_LIMIT_DEFAULT`/`_MAX`
    (RO-6's own `limit`).
  - **Truncation, role pass-through, tool rows.** The `messages` items are the RO-3 shape,
    including the optional tool-output fields (V-3, under RO-3). The client still applies the
    64 KiB display cut and "Message shortened on mobile" note. `role` is passed through
    unfiltered. A `tool` row renders as the collapsible result in S7. Every other role besides
    `user` and `assistant`, including `session_meta` and `system`, stays a neutral note.

- **SES-2a. `GET /hmp/v1/bots/{p}/sessions/{ref}/messages/from-start?limit=`.** This distinct
  read-only route returns the earliest available active rows in the existing RO-6 paged shape:
  `200 {"messages":[…], "head_message_id":<int|null>}` or the same `reset` as SES-2. It calls
  SES-2's `session_history` with cursor zero, then the client continues with SES-2's
  `after=<last-id>` pages. It uses the same bearer, per-bot gate, opaque ref resolution,
  per-device read limiter, history limit default/max, and session-browsing kill switch as SES-2.
  Only `limit` is accepted; unknown or repeated query fields are `400 bad_request`. An older HMP
  release has no route and returns 404, so a client cannot mistake SES-2's `after=0` latest
  snapshot for complete history. No search term is sent to HMP or Hermes. Rows removed by Hermes
  compaction are outside the available active history; clients must not claim to recover them.

- **SES-3. Authz, rate limits, size caps.**
  - **Authz.** Identical per-bot gate to every existing `/bots/{p}/…` route (ERR-3), re-run on
    every call, fail-closed to `UNVERIFIABLE`/`503`. No per-session or per-source authorization
    exists in Hermes, and none is added: OD-F10's whole point is that bot-level authorization is
    sufficient.
  - **Rate limits.** A dedicated per-device limiter on SES-1 (heavier than a single conversation
    read, with no natural "only what changed" bound), alongside SES-1f's hard `limit<=100`. SES-2
    reuses the generic per-device read limit (RO-3/RO-6's own).
  - **Size caps.** SES-1's `limit` (30/100) and SES-2's `limit` (reused RO-6 values) are the only
    new caps.

- **SES-4. Errors.** No new `ErrorCode` values. SES-1/SES-2 reuse ERR-2/ERR-2a wholesale:
  `not_found` for an unknown or foreign `session_ref`; the standard ERR-3 table for authz refusal;
  the ERR-2a compat refusal when the running build lacks the two new `READ_DEPENDENCIES` entries
  (below); `400 bad_request` for a malformed `cursor` or `after`.

- **SES-5. Host-side kill switch.** `gateway.platforms.hmp.extra.session_browsing` (bool, default
  `true`). When `false`, SES-1 and SES-2 are **not registered** at all — the same "not registered,
  `404`" pattern F1 already uses for submit/SSE/approvals/clarify/stop (`server-modules.md` "F1
  route table"). A future higher-sensitivity or multi-user host can turn session browsing off
  entirely without a client update. The app hides its sessions entry whenever these routes answer
  `404` for a bot it can otherwise read.

- **SES-6. New §12 internals.** `hermes_state.SessionDB.list_sessions_rich` and `.get_session`,
  both resolving to `hermes_state_sessions.py` (already in `bridge_files`; no fingerprint change).
  Gap: E-GAP-6/7, the same family as every other `SessionDB` read this contract already lists.

- **SES-7. The OD-F11 bot-view selector adds no new `READ_DEPENDENCIES` entry.** It reads only
  `title` and `hidden`, both plain fields `list_sessions_rich` already returns under SES-6. The
  literal it compares against ("Bot Chat") is not read live from any Hermes symbol —
  `SessionDB.CANONICAL_BOT_CHAT_TITLE` is a string constant, not a class or callable, so it does
  not fit the compat probe's shape check — and is instead asserted by HMP itself, cross-checked
  read-only against three independent, mutually agreeing Hermes-side sources (`apps/desktop/src/
  plugins/hermes-bots/canonical-chat.ts`, `tools/bot_mode_probe.py`, `hermes_state.py`). A future
  rename of that literal fails the selector closed (shows nothing), never open.

## 7. Submit, reconcile and client delivery rules (ADR-0004; CONNECTIVITY.md)

### 7.1 Submit

- **SUB-1. Request.** `POST /hmp/v1/bots/{p}/conversations/default/messages`:

  ```
  {"client_message_id":"<UUIDv7>", "base_message_id":<int>|null, "text":"<string>", "sent_at":<int>?}
  ```

  - `sent_at` is informational. Deadlines use the host clock.
- **SUB-2. Gate order.** The per-bot gate (ERR-3) runs first. Then the write gate (GU-4) runs. Only then is an idempotency record claimed.
- **SUB-3. Idempotency.**
  - The scope is `(iid, user_id, profile, conversation_id)`, keyed by `client_message_id`.
  - `payload_hash = SHA-256` over the canonical `(text, base_message_id, attachments=[])`.
  - The record is claimed atomically before any hand-off. At most one hand-off happens per scope and cmid within retention.
  - The same payload replays the stored outcome and never hands off again. A different payload returns `409 idempotency_conflict`.
  - Records are kept `IDEMPOTENCY_RETENTION_S` after their last change, and never less than `CLIENT_RETRY_WINDOW_S` plus a margin.
  - A purged record reads `unknown`.
  - Hermes receives the message as `hmp:<chat_id>:<cmid>` with `defer_policy="reject"` and an admission precondition of `(base_message_id, not_after = received + ADMISSION_DEADLINE_S)`.
- **SUB-4. Responses.** The body shapes are fixed.

| Outcome | Response | Definitive? |
|---|---|---|
| Accepted: Hermes admitted it and a row exists | `200 {"state":"accepted", "message_id", "head_message_id"}` | yes |
| Idempotent replay | exactly the stored original response | as original |
| Refused (§4): `busy`, `conversation_changed`, `expired`, `draining`, `lease_timeout`, `unauthorized`, `other {definitive:true}` | error body | yes |
| Write gate closed | `503 {"error":{"code":"guarantees_unavailable",…}, "guarantees":{…}}` | yes |
| No outcome within `ADMISSION_WAIT_S`, or a non-definitive Hermes outcome (ERR-4) | `202 {"state":"submitted"}` | **no** |

- **SUB-5. `handed_off` is not emitted in v1.0.** Under the write-safety policy (§8), HMP never hands a write to Hermes without the write guarantees. The spike's baseline response, `202 handed_off`, is withdrawn. If a client ever sees it, the client treats it as `submitted`.
- **SUB-6. Refused submits never start a turn.** A refused submit produces **zero** `turn.started` events.

### 7.2 Lookup (read-only reconciliation)

- **SUB-7. Request.** `GET /hmp/v1/bots/{p}/conversations/default/messages/by-client-id/{cmid}`. It never re-sends.
- **SUB-8. Response:**

  ```
  200 {"state":"accepted"|"rejected"|"not_accepted"|"submitted"|"unknown", "reason":<RejectReason>|null, "message_id":<int>|null}
  ```

  | State | Meaning |
  |---|---|
  | `accepted` | reported **only** from a Hermes row carrying this message id |
  | `rejected` | a definitive refusal was recorded; `reason` is set |
  | `not_accepted` | a record exists, its admission window has closed, and a negative probe of **every** session the message could have entered succeeded: the current lineage, the session resolved at submit, and the session it was admitted into |
  | `submitted` | the outcome is not yet known |
  | `unknown` | no record in the caller's scope (never received, or purged), or the probe could not be trusted |

  - A probe failure answers `unknown`, never `not_accepted`.
  - Another user's cmid answers `unknown`.
- **SUB-9. Bounded `submitted`** [ahead]. The server MUST NOT report `submitted` for a record older than `ADMISSION_DEADLINE_S + LOOKUP_SETTLE_MARGIN_S`. It then reports `not_accepted` (if the negative probe of SUB-8 succeeds) or `unknown`.
  - The spike returns `submitted` until a process restart (`backend.py:689-702`).
- **SUB-10. `not_accepted` depends on the stale-execution invariant.** It relies on "under `defer_policy="reject"` no deferred copy of the message can exist". That is the unclosed R0-BLK-10 invariant (`R0_FREEZE_REVIEW.md` §7).
  - Therefore `not_accepted` is **non-definitive** for clients until a contract revision records R0-BLK-10 closure (CL-4).
  - `rejected` states are definitive now: they come from an explicit refusal outcome at the refusing site.

### 7.3 Client delivery rules — the single retry rule set

These rules replace every earlier retry text in `CONNECTIVITY.md`, ADR-0004 and `R0_FREEZE_REVIEW.md`. Those documents now refer here.

- **CL-1. Pending record.**
  - On Send, the client persists a bounded pending record before first transmission: `client_message_id`, `iid`, profile, conversation, text, `base_message_id` (the current snapshot head), `created_at`, and state.
  - The text is never discarded by the delivery machinery. Only an explicit user action removes it.
- **CL-2. Outcome classes.** Every response or observation falls into exactly one class:
  - **ACCEPTED**: `200 accepted`; lookup `accepted`; or a snapshot or history row carrying this cmid.
  - **REJECTED (definitive)**: every code whose "Definitive for submit?" entry in ERR-2 is "yes", `503 other` with `definitive:true`, and lookup `rejected`. Hermes will never execute this attempt.
  - **UNCONFIRMED (ambiguous)** — everything else:
    - no response: a timeout, or a connection loss after any request byte was written;
    - `202 submitted`, and `202 handed_off` if one is ever seen;
    - `503 other` without `definitive:true`, and `500`;
    - any unknown code;
    - `idempotency_conflict`;
    - lookup `submitted`, `unknown` or `not_accepted` (CL-4).
  - **NOT TRANSMITTED**: the TLS connection never completed, or no request byte was written. This is known locally.
- **CL-3. Actions per class.**
  - **ACCEPTED:** done.
  - **REJECTED and NOT TRANSMITTED:** restore the text as a reviewable draft, with the reason. The actions are **Discard** and **Review & Send**.
    - Review & Send uses a **new** cmid and the **current** head as its anchor.
    - This path is safe from duplication because the earlier attempt definitively never executes.
  - **UNCONFIRMED:**
    - Keep the message visible with its text and the state "not confirmed". Never say it "was not sent" or "was never accepted".
    - Reconcile with read-only lookup and snapshot reads (CL-5) until an ACCEPTED or REJECTED answer arrives, or `CLIENT_RETRY_WINDOW_S` expires.
    - After that the message stays UNCONFIRMED. Offer three actions:
      - **Check again**: read-only.
      - **Send as a new message**: a new cmid and new anchor. The UI MUST warn that if the earlier message was delivered, this will be a duplicate. A new-id resend is never presented as harmless.
      - **Remove from this device**: this is local only and cancels nothing on Hermes.
    - The exact copy is `UX_CONTRACT_GAP` UX-3.
- **CL-4. Automatic retry is disabled in contract revision 1.0**, whatever the advertised flags. A v1.0 client never transmits a message without an explicit user Send action for that transmission. That includes delayed first transmission after a reconnect.
  - This is a **temporary v1 limitation** (`R0_OWNER_DECISIONS.md`, bounded amendment 5), not a reinterpretation of the owner's original conditional-retry requirement. That requirement stays the target once the closure bar (`R0_FREEZE_REVIEW.md` §7) and the future-rule conditions below are both met.
  - A future revision may enable automatic retry only by recording R0-BLK-10 closure (`R0_FREEZE_REVIEW.md` §7). Even then, an automatic retry is permitted **only** when **all** of these hold:
    - (a) it reuses the **same** `client_message_id`, text and `base_message_id`;
    - (b) it follows a read-only reconciliation in which lookup answered `unknown` (no record) **and** a fresh snapshot head equals `base_message_id`;
    - (c) `no_defer` and `atomic_anchor` are both `true`, and `write_gate` is `open`, at retry time;
    - (d) it is within `CLIENT_RETRY_WINDOW_S` of `created_at`, measured on the client's monotonic clock;
    - (e) the attempt count stays within `CLIENT_MAX_AUTO_ATTEMPTS`.
  - A same-id resend of an existing record only replays that record (SUB-3). It can never cause a second execution.
- **CL-5. Reconciliation.** Before **any** resend, the client MUST reconcile read-only (lookup by cmid, then a snapshot read).
  - Lookup polling uses backoff starting at 1 s and capped at 15 s, and runs only within `CLIENT_RETRY_WINDOW_S`.
  - Reconciliation never uses POST.
- **CL-6. Instance binding.** A pending record is bound to its `iid` and conversation forever. It is never sent to another instance (PR-3).
  - Unpair or revoke destroys that instance's pending records. What happens to their text is `UX_CONTRACT_GAP` UX-7 (ADR-0007).
- **CL-7. `idempotency_conflict`** is a client defect: a cmid was reused with a different payload.
  - The client marks the affected local message UNCONFIRMED, because an earlier payload under that id may have executed.
  - It MUST NOT retry under that id.

## 7a. Direct send to Bot Chat (v1.2, amendment F2; OD-F12, OD-F13, OD-F14)

Additive under V-3: an earlier `1.x` client that never sends `expected_head` never reaches this
route's guarded path (DS-2 below) and sees the write gate as closed (V-4), exactly like a client
built before GU-4 existed. Design and evidence: `specs/002-send-messages/DESIGN.md` v5. Owner
rulings: OD-F12 ("for 1.0, let's do the Bot chats... just the ones from the bot view"; other
sessions and Desktop tabs deferred to the upstream gateway rewrite), OD-F13 ("One shared bot
chat"; the phone-only `/conversations/default` conversation is retired for *sends* on a new
client), OD-F14 ("Reduced mode now, upgrade later... Reply directly with a guard... check if it's
the latest message or fail... We only send messages when all messages are in sync between device
and mobile"; approvals mid-turn: "Show it, answer elsewhere") — all in
`docs/architecture/R0_OWNER_DECISIONS.md`.

**DS-0. Target session — exactly the canonical Bot Chat, never `session_ref`-addressed.** Per
OD-F12, a send targets only the bot's own canonical `(profile, "Bot Chat")` session — the same
session SES-1's OD-F11 bot-view selector already resolves for reads (`_is_bot_view_session`: title
exactly `"Bot Chat"`, hidden). There is exactly one target per bot, resolved server-side; the
route never accepts a `session_ref` or `session_id`. **OD-F13 consequence for F1's existing
`/conversations/default`:** that route (and its `POST .../conversations/default/messages` shape,
SUB-1..SUB-10) is kept, unregistered-by-default behaviour unchanged, for backward read/write
compatibility with an older client build — but a client built against this amendment MUST use the
routes below for sending, never `SUB-1`. `SUB-1`'s route never grows `expected_head` and never
opens under the guarded gate; it stays gated by GU-4's original, ungated `"open"` state only,
which no supported build advertises today (§8).

- **DS-1. Request.** `POST /hmp/v1/bots/{p}/chat/messages` (mirrored, like every `/bots/{p}/…`
  route, under `/p/<profile>` on Hermes's own side — that mirroring is internal to the server's
  loopback call, §DS-6, and never visible on this wire):

  ```
  {"client_message_id":"<UUIDv7>", "expected_head":<int>|null, "text":"<string>", "sent_at":<int>?}
  ```

  Auth: bearer + per-bot gate (ERR-3), identical order to every existing `/bots/{p}/…` route.
  `expected_head` is the caller's last-known head for the Bot Chat (the same value SES-2/RO-6
  already expose as `head_message_id`). A request with `expected_head` absent or `null` is
  `400 bad_request`: the guard (DS-4) requires it once this route is registered, so an old client
  that never sends it cannot reach the guarded path at all (V-4's safe default — it simply never
  advertises success here).
- **DS-2. Gate order.** (a) The per-bot gate (ERR-3). (b) The Bot Chat route requires **all** of:
  the host flag `gateway.platforms.hmp.extra.direct_send` is `true` (default `false`, off;
  OD-F14/OD-F15); this Hermes provides the APIs send needs (GU-2d); `api_server` resolves to a
  loopback-only target for the profile (DS-6); and that profile's `API_SERVER_KEY` resolves to a
  usable secret (DS-6). A genuine GU-4 `"open"` state retains its full-guarantee label only
  after these route prerequisites pass. Otherwise the route is `"open_guarded"` and applies
  DS-4's HMP guard. A full Hermes guarantee never bypasses the owner switch or profile key.
  This advertised gate does not probe the port: a later connection failure is
  `api_server_unavailable`, with the message kept unconfirmed. Any missing prerequisite is `"closed"`:
  `POST .../chat/messages` returns `503 {"error":{"code":"write_gate_closed", ...}, "guarantees":
  {…}}` without handing anything to Hermes, mirroring GU-4's existing `guarantees_unavailable`
  shape under a new, route-specific code (added to ERR-2, never replacing it). (c) Only once (a)
  and (b) both pass does the cmid idempotency reservation (DS-3) run, then the guard proper (DS-4).
- **DS-3. Idempotency.** Scope `(iid, user_id, profile)` — OD-F12 means there is exactly one
  target session per bot, so no `conversation_id`/`session_ref` axis is needed (narrower than
  SUB-3's scope). `payload_hash = SHA-256` over the canonical `(text, expected_head)`. The record
  is **reserved atomically before** the loopback call (DS-6), not after: this closes the same
  timing gap SUB-3 already closes for the original submit path, applied to a route with no
  Hermes-side idempotency store of its own. The same payload replays the stored outcome and never
  hands off again; a different payload under the same cmid is `409 idempotency_conflict` (reuses
  `ErrorCode.IDEMPOTENCY_CONFLICT`, no new code). A timeout or ambiguous outcome leaves the record
  `pending`; the client MUST reconcile read-only (DS-8, mirroring CL-5) before any resend, and a
  resend always mints a **new** cmid (mirroring CL-3's "Send as new"), never resubmits the pending
  one. Records are kept `IDEMPOTENCY_RETENTION_S` after their last change, same as SUB-3.
- **DS-4. Guard, in order, each failing closed independently.**
  1. **In-process serialization.** An in-process lock keyed by `(profile, resolved live tip
     session id)` serializes HMP's own concurrent attempts against each other (two devices, a
     double-tap, a retry racing a first attempt). It says nothing about a writer outside HMP's own
     process — (2)-(4) below cover that.
  2. **Bot Chat resolution.** Resolve `(profile, "Bot Chat")` via the same primitive SES-1's OD-F11
     selector and `tools/bot_live_delivery.py`'s `find_canonical_owner` both already use
     (`get_session_by_title`, then the live compression tip). **No Bot Chat exists for this
     profile → `409 {"error":{"code":"no_bot_chat", ...}}`.** HMP never creates one on the send
     path (§DS-9 records the evidence for why: no plugin-reachable supported creation path
     exists). This is definitive: the client's action is to open the bot once on Hermes Desktop
     first (copy is a `UX_CONTRACT_GAP`).
  3. **Liveness (lease-registry) check.** Read-only `active_session_registry_snapshot`, called
     with the **target profile's own** `registry_home` (never the default profile's), checked
     against **every id in the Bot Chat's full compression chain** (not only the live tip — a
     stale-but-still-open CLI session leased on a pre-compression id must still be caught). A
     lease found on any of those ids → `409 {"error":{"code":"session_busy", ...}}`
     (non-definitive: Hermes never saw this attempt; the client may plainly retry once the busy
     state clears). **Any exception from the snapshot call itself also fails closed to
     `session_busy`/`503`** — "ownership uncertainty fails CLOSED", the same discipline
     `try_acquire_active_session` documents for its own callers. **This check does not fire merely
     because Hermes Desktop currently holds the Bot Chat live with its own first prompt already
     sent this run** — that case is handled natively by Hermes's own mailbox hand-off
     (`_admit_to_live_bot_chat`), not by this guard; DS-6 covers what HMP's call sees when that
     mailbox is the one actually running the turn.
  4. **Head precondition.** Resolve the Bot Chat's current head on its live compression tip (the
     same value SES-2 exposes as `head_message_id`) and compare to the request's `expected_head`.
     **Mismatch → `409 {"error":{"code":"stale_head", ...}}`** (definitive for *this* attempt: the
     client MUST refresh — a fresh SES-2 read — before another send is allowed; never a silent
     retry with the old value).
  - **Residual race, named, not hidden.** Between DS-4 completing and DS-6's call actually
    committing, a small set of writers the lease registry cannot see on any build investigated
    (a first-ever Hermes Desktop prompt on this exact Bot Chat, a second concurrent
    `api_server`/`/v1/runs`/`hermes peer dm` caller, an in-process wake turn, or a misconfigured
    cron job targeting this session) can still land unseen. This is bounded, not eliminated;
    DS-7's post-hoc check exists because of it, and closing it fully needs Hermes's own atomic
    admission precondition (§8's `atomic_anchor`), not yet available on any supported build.
- **DS-5. Approvals/clarify raised mid-turn.** OD-F14's "Show it, answer elsewhere" still applies
  when `gateway.platforms.hmp.extra.direct_send` is off, and when §7b's `desktop_held` marker is
  set (Hermes Desktop holds the Bot Chat: the phone shows **Waiting for approval on your Hermes
  Desktop** and renders no Bot Chat card). When the flag is on and this gateway process runs the
  turn, approvals are answerable on the phone (§7b). Clarify on that local Bot Chat turn is not
  answerable: `api_server` sets no clarify callback, so no card is emitted. `execute_code` on that
  same turn does not card either (`api_server` is an unattended platform). OD-F16 (v1.3, §7b)
  narrows this clause; it does not add a new error code.
- **DS-6. The loopback call.** HMP resolves, server-side only, per the target profile: the
  `api_server` bind (`127.0.0.1`/`::1` only — any other resolved value, or a value HMP cannot
  positively determine, fails the gate closed at DS-2(b), never attempted) and the `API_SERVER_KEY`
  (the default profile's key, or a named profile's own independently-scoped key — never the
  default's key reused for a named profile; a `401` from the call below is treated as "this
  profile's write gate is closed", never retried with a different key or logged). The call itself:
  `POST /api/sessions/{live_tip_id}/chat` (default profile) or
  `POST /p/<profile>/api/sessions/{live_tip_id}/chat` (a named profile — the mirrored path, never
  a `/v1/...` path), body `{"message": "<text>"}`, bearer `API_SERVER_KEY`, over
  `aiohttp.ClientSession(trust_env=False)` (no proxy environment ever honoured), pinned to the
  resolved loopback literal, `await`ed directly on HMP's own coroutine (no blocking thread hop —
  this is genuine async socket I/O). `{live_tip_id}` is always the *resolved live compression tip*
  from DS-4(2)/(4), never the canonical registry's root id (routes around a Hermes-side gap where
  the plain session lookup accepts an ended parent without following its tip). **If Hermes Desktop
  currently holds this exact Bot Chat live** (its own mailbox hand-off, `_admit_to_live_bot_chat`),
  the call is durably queued to that mailbox instead of running a competing turn in HMP's own
  process — HMP's own response is `202 {"state":"queued"}`, settling later, never a second agent.
  Otherwise the call runs the turn directly and, if it completes within `ADMISSION_WAIT_S`
  (reused from §13), the reply is returned synchronously.
  **v1.3 (§7b) replaces this URL.** A send that already passes DS-2 and DS-4 calls
  `POST …/chat/stream` (same prefix, same bearer, same loopback rules) and never falls back to
  sync `POST …/chat`. The phone still receives the DS-7 vocabulary at `ADMISSION_WAIT_S`. HMP
  keeps reading the SSE socket until it ends.
- **DS-7. Responses.**

  | Outcome | Response | Definitive? |
  |---|---|---|
  | Accepted, reply available synchronously | `200 {"state":"accepted", "message_id", "head_message_id", "guarantee_level":"guarded", "reply":{"role":"assistant","content":…}}` | yes, for this attempt reaching Hermes |
  | Accepted, mailbox-queued (Desktop holds the Bot Chat live) | `202 {"state":"queued", "guarantee_level":"guarded"}` | no — settle by polling SES-2 |
  | No outcome within `ADMISSION_WAIT_S` | `202 {"state":"submitted", "guarantee_level":"guarded"}` | no |
  | Idempotent replay | exactly the stored original response | as original |
  | DS-4(2) failed: no Bot Chat | `409 {"error":{"code":"no_bot_chat", ...}}` | yes |
  | DS-4(3) failed: busy, or the liveness read itself failed | `409 {"error":{"code":"session_busy", ...}}` | no |
  | DS-4(4) failed: stale client view | `409 {"error":{"code":"stale_head", ...}}` | yes |
  | Idempotency conflict | `409 {"error":{"code":"idempotency_conflict", ...}}` | no (CL-7) |
  | DS-2(b) failed: gate closed | `503 {"error":{"code":"write_gate_closed", ...}, "guarantees":{…}}` | yes |
  | DS-6's loopback call unreachable/refused (`api_server` down, non-loopback bind detected at call time, `401`) | `503 {"error":{"code":"api_server_unavailable", ...}}` | no — HMP did not hand off |
  | Post-hoc verification detects an interleave (DS-7a) | `200`/`202` as above, plus `"interleave_detected":true` | yes for the send itself; informational for ordering |
  | Body too large / malformed | `413 too_large` / `400 bad_request` | yes |
  | Rate limited | `429 rate_limited` | yes |

  `guarantee_level:"guarded"` is present only under the `"open_guarded"` gate, additive, ignored by
  a client that does not recognize it (V-4); it is never present alongside a full, un-gated
  `"open"`-gate accept.
- **DS-7a. Post-hoc verification.** On the post-compression transcript (using the loopback
  response's own `effective_session_id` when a turn-start compaction rotated it during this very
  call — that rotation is the turn's own housekeeping, never a foreign write), the check passes
  only if the only rows committed after `expected_head` are HMP's own user row and its own
  assistant reply, identified by text equality, a bounded timestamp window, and `source=
  "api_server"` (session_chat carries no per-message client id; two identical texts sent close
  together are a stated, residual identification limit, mitigated by DS-3's own duplicate
  prevention, not by this check). Any additional row fails the check: `"interleave_detected":true`
  is added to the otherwise-successful response (never a separate error — Hermes did execute the
  send). For the mailbox `202 queued` outcome, this check is deferred until the delivery settles
  (polled via SES-2), never run immediately after the `202`.
- **DS-8. Status endpoint (reconciliation after a timeout).** `GET /hmp/v1/bots/{p}/chat/messages/
  by-client-id/{cmid}`. Never re-sends. Response: `200 {"state":"accepted"|"rejected"|
  "not_accepted"|"submitted"|"unknown", "message_id":<int>|null}` — the same vocabulary as SUB-8,
  scoped to this route's own idempotency store (DS-3). A probe failure answers `unknown`, never
  `not_accepted`. Reply *content* visibility is not this route's job: once `state` is `"accepted"`,
  the client reads the reply via the existing SES-2 poll (`GET .../sessions/{ref}/messages`) on the
  Bot Chat's own `session_ref` (obtained once via SES-1, which already lists exactly this session
  under OD-F11) — no new read route. This is OD-F13's chosen answer to "how is the Bot Chat read
  exposed": reuse SES-1/SES-2 unmodified, rather than add a parallel `GET /bots/{p}/chat` route,
  because SES-1 already lists nothing but the canonical Bot Chat (and the caller's own
  `is_mobile` session) per OD-F11/OD-F12, so a second, redundant read path would duplicate tested
  plumbing for no new capability.
- **DS-9. Bot Chat creation — evidence, not a decision this amendment makes.** Investigated
  directly and read-only against the owner's own build
  (`~/.hermes/hermes-agent` @ `8afaab3703e336d72a72c812dd2dd249f04f166a`): `api_server`'s
  exact-title lookup (`_handle_list_sessions`'s `title_filter` branch, `api_server.py` ~2900s)
  **only resurrects a Bot Chat that was previously created and then archived** (`db.
  get_session_by_title` finds a row, `unarchive_recoverable_session` brings it back); when no row
  has ever existed for that title, the lookup returns nothing and no session is created.
  `tools/bot_live_delivery.py`'s `find_canonical_owner` (the same primitive DS-4(2) uses) likewise
  returns `None` with no side effect when `get_session_by_title("Bot Chat")` finds no row. The one
  supported creation path is Hermes Desktop's own `session.create` JSON-RPC call
  (`apps/desktop/src/plugins/hermes-bots/canonical-chat.ts`, `title: CANONICAL_CHAT_TITLE,
  hidden: true, follow_profile_config: true`, over `tui_gateway`) — and `tui_gateway` is Desktop's
  own internal RPC surface, never documented or reachable as a platform-plugin dependency
  (confirmed: the platform-adapter guide's plugin-reachable surface list has no `tui_gateway` row).
  **Conclusion: no plugin-reachable supported path creates a Bot Chat that does not already
  exist.** DS-4(2)'s `409 no_bot_chat` is therefore the correct, final behaviour, not a placeholder
  — `HERMES_API_GAP` raised: a platform-plugin-reachable way to create/materialize a bot's
  canonical Bot Chat (today, only Desktop's own UI does this, by design, on first open).
- **DS-10. Host-side owner-dogfood gate flag.** `gateway.platforms.hmp.extra.direct_send` (bool,
  default `false`). Mirrors SES-5's own kill-switch pattern, but this route is always *registered*
  (unlike SES-1/SES-2's "not registered" pattern) — with the flag off, `POST .../chat/messages`
  answers `503 write_gate_closed` rather than `404`, matching how the original SUB-1 route already
  behaves under a closed GU-4 gate. This is the flag OD-F15's second live-config approval turns on,
  for owner dogfood, never a general release default. F3 prompt access and Phone chat additionally
  require the explicit per-device allowlist in §7b; pairing alone is not owner authorization.

## 7b. Approvals and Phone chat (v1.3, amendment F3; OD-F16)

Additive under V-3. An earlier 1.x client never calls these routes and never reads the new fields
(V-4). Design: `specs/003-approvals/DESIGN.md`. No new error code. `applied` is an additive field
on the answer and on the stale/conflict/invalid-choice bodies below. `stale`, `not_found`,
`invalid_choice`, `idempotency_conflict` and `write_gate_closed` are the existing ERR-2 codes.

The owner-only flag `gateway.platforms.hmp.extra.direct_send` (DS-10) gates every route in this
section. Flag off, or the member a route needs being unavailable (see "Availability" below): each
route returns `503 {"error":{"code":"write_gate_closed",…}}` and does not open a loopback stream,
call `handle_message`, or call `resolve_gateway_approval` / `resolve_gateway_clarify` /
`mark_awaiting_text`. Pairing is still required. The flag does not authorize a device by itself.

Auth on every route: bearer, explicit owner-device membership, the F3 rate limit, then the
per-bot gate (`require_bot_authorized`, ERR-3), then the write gate and the availability
gate below. The rate limit is two separate per-device buckets keyed by `device_id`
only: AP-3 reads are limited to 60 per minute per device, and AP-4 answers and AP-6 Phone sends
share one actions bucket of 60 per minute per device. Each bucket aggregates across every profile
and request ID the device uses. Reads do not consume the actions bucket. `{p}` is the served profile, checked against the stored row. An owner device is an active
paired device whose exact ID appears in `gateway.platforms.hmp.extra.owner_device_ids` (list of
strings, default empty; malformed config grants nobody). A non-owner receives `404 not_found`,
even when bot-authorized or sharing the owner's `user_id`. The host loads changes through its
normal config reload/restart; HMP reads the live adapter config each request. The separate
per-device jobs/model controls decision (§7c, §7d) never makes a device an approval owner: an
explicit grant without an `owner_device_ids` entry still receives `404 not_found` on every
AP-3/AP-4/AP-6 route and omits `open_requests`, and an explicit host denial closes an
allowlisted device. An unreadable decision denies. Owner devices of
the same user share the existing per-request serialization and idempotency. Default-conversation
snapshots omit `open_requests` for non-owners and while the direct-send flag is off.
The explicit `direct_send.enabled` flag is mandatory even when the base gate is OPEN.

**Availability (additional gate; owner policy 2026-10-01, spec 034).** Two eligibility members,
computed once when the listener opens beside the others (GU-2d), gate this section.

| Member | Needed by | Requires |
|---|---|---|
| `approvals` | the Bot Chat stream binding, AP-3 and AP-4 for `bot_chat` rows | read and send, and the send floor |
| `phone_chat` | AP-6, AP-4 for `phone_chat` rows, snapshot `open_requests`, the Phone producer hooks | read and send, the send floor, and the in-process helpers below |

Both floors are Hermes `0.21.5` / `2026.9.24`, equal to send. A version that declares itself below
the floor is refused for both without importing a helper; an unknown, placeholder, unlisted, newer
or development version is attempted. `approvals` adds no Hermes dependency of its own: Bot Chat
answers are made only through Hermes's native run-approval route over loopback, so its own key,
room-grant and run-ownership checks apply, and a missing Phone helper never closes it. `phone_chat`
is available only when the helpers HMP calls in process actually exist, with the same containment
and wrapper-chain rules as every other probe (GU-2d): `tools.approval.resolve_gateway_approval`
with named `request_id` and `resolve_all` parameters (a `**kwargs` catch-all never counts) and
`list_gateway_approvals`; `tools.clarify_gateway.resolve_gateway_clarify`, `mark_awaiting_text` and
`get_clarify_timeout`; `tools.approval_context._get_approval_timeout`; the base adapter hooks
`_send_exec_approval_prompt` and `send_clarify`; and the dataclass field
`MessageEvent.allow_gateway_control`. `retire_clarify_card` is an optional hook the gateway finds
on the adapter's own class; it is not on the base class and is not probed. A member is closed only
when its own required API is genuinely missing, or because send or read is. Every member defaults
to closed when no availability information exists.

No exact build, Git SHA, source fingerprint, manifest, process latch or tested-sample receipt admits
or refuses either member, and no runtime path reads one. Tested samples remain evidence only
(GU-2a). The Bot Chat session-stream approval notifier (`APIServerAdapter._register_session_stream_approval`
on the inspected development builds) is reported as a neutral diagnostic fact by
`hermes hmp compat --verbose` and in approval issue drafts. It never gates, never raises a warning
by itself and never establishes a release minimum: where the notifier is absent Hermes emits no
`approval.request`, no card is invented, and Hermes keeps its own fail-closed behavior.

Residual: a later Hermes that stops honoring `allow_gateway_control:false` cannot be detected
statically. The pending preflight and prompt-only answer route (AP-6) remain the protection, and
the dependency check never claims to prove behavior. Ordinary guarded sends (§7a) do not depend on
either member.

- **AP-1. Bot Chat stream (amends DS-6 for approval-owner sends only).** Before it takes the
  profile lock, HMP decides the transport from live state: the stream is used only when the
  sending device is an effective approval owner for this bot (the `owner_device_ids` entry and no
  host denial, AP-7) and `approvals` is available. Every other send, including every non-owner
  send and every send while `approvals` is closed, uses DS-6's synchronous
  `POST …/chat` exactly as in §7a, with unchanged outcomes. The loopback body stays
  `{"message":"<text>"}`. On the stream path the route is
  `{path_prefix}/api/sessions/{live_tip}/chat/stream`. A non-200, or a body that is not that route's
  SSE stream, fails the send as `503 api_server_unavailable`. HMP never opens `POST …/chat`
  instead and never retries after a stream failure. The consumer is a task
  owned by the send, not by the phone HTTP request. At `ADMISSION_WAIT_S` the phone gets the DS-7
  vocabulary: `200 accepted` when `run.completed` already carried an assistant message and DS-7a
  passes; `202 queued` on `run.queued` or a mailbox `done` that never registered a local approval;
  `202 submitted` while the stream is still open. The cmid stays pending until a terminal SSE
  event. The socket dying before that finalizes the row `unknown` (DS-8) and interrupts the Hermes
  turn. DS-3 replay does not open a second stream. `approval.request` is stored as soon as it
  arrives, including before the phone's `202`. The stored command is the redacted SSE value. HMP
  does not un-redact it. A mailbox stream (Desktop holds the Bot Chat: no `approval.request`) sets
  a process-memory marker `{surface:"bot_chat", desktop_held:true}` for the life of that consume
  and clears it when the consume ends. The marker is not proof that Desktop is blocked on a card.
- **AP-2. Prompt rows are process memory.** Key `(iid, user_id, profile, request_id)`. A restart
  drops them immediately (Hermes's own queues are process memory too). After a row settles or
  expires it is kept at most `IDEMPOTENCY_RETENTION_S` (§13) inside one process. The row stores
  the Hermes `run_id` (Bot Chat) or the session key HMP built for this user (Phone chat). The
  client never sends `session_key`, `run_id`, `chat_id` or `profile` in the answer body. Each
  listener open creates a new prompt generation. A stream or hook bound to an older generation can
  never insert rows into, list from or answer in a newer one, and rows of a generation that was
  closed by AP-10 are never listed or answerable. A body
  field `all` or `resolve_all` is `400 bad_request` and is not forwarded. `resolve_all` is never
  passed. An answer is bound to the stored `request_id` and the authorized `user_id`. An id stored
  for a different user is `404 not_found`, the same as an unknown id. No Hermes call is made.
- **AP-3. Read.** `GET /hmp/v1/bots/{p}/prompts` → `200 {"prompts":[Prompt,…], "desktop_held":bool}`.
  `Prompt` fields: `kind` `"approval"`|`"clarify"`; `surface` `"bot_chat"`|`"phone_chat"` (clarify
  is `phone_chat` only); `request_id` (Hermes `request_id`, or `clarify_id` under the same JSON
  name); `choices`; for an approval, `command` and `description`; for a clarify, `question`,
  `multi_select`, `awaiting_text`; `expires_at` (unix seconds, or null when Hermes's clarify
  timeout is unlimited). `desktop_held` true means `prompts` contains no `bot_chat` approval (a
  Phone-chat card may still be listed). `expires_at` is `observed_at` plus the timeout read from
  Hermes (`approvals.timeout`, default 300s; clarify `clarify.timeout`, else `agent.clarify_timeout`,
  else 3600), through `bridge.py` inside that target profile's runtime scope. It is a display hint,
  not Hermes's timer. Approval values <= 0 mean immediate expiry; clarify <= 0 means unlimited.
  Hermes returning nothing pending, clarify retirement, a vanished approval waiter, or the end
  of the bound stream expires the row immediately. A 30-second grace after the display hint
  is the local cleanup backstop: beyond it list omits the row and answer returns `409 stale`,
  `applied:false` without forwarding. Purge removes rows and locks after retention, pinning
  active/queued answerers so a lock cannot be replaced underneath them. Unknown IDs allocate
  neither rows nor locks.
- **AP-4. Answer.** `POST /hmp/v1/bots/{p}/prompts/{request_id}`. The path id is the only id. A
  `kind` field in the body is ignored; the stored row decides. `choice` together with `text`, or
  `other` together with either, is `400 bad_request`.

  | Stored kind | Body | Hermes call |
  |---|---|---|
  | approval | `{"choice":"once"\|"session"\|"always"\|"deny"}` | Bot Chat: `POST {path_prefix}/v1/runs/{stored_run_id}/approval` with `{"choice","request_id"}` only. Phone chat: `resolve_gateway_approval(stored_session_key, choice, request_id=)`. |
  | clarify | `{"choice":"<label>"}` or, when `multi_select`, `{"choices":["<label>",…]}` | `resolve_gateway_clarify`. The label is the offered choice with a trailing `(Recommended)` stripped. Multi-select passes `json.dumps(labels)`. |
  | clarify Other | `{"other":true}` | `mark_awaiting_text`. `200 {"status":"awaiting_text","applied":false}`. |
  | clarify text | `{"text":"<string>"}` | `resolve_gateway_clarify` only when the row is awaiting text or has no choices. Otherwise `409 invalid_choice`, and the Hermes entry stays pending. |

  A `choice` not in the stored `choices` is `409 {"error":{"code":"invalid_choice",…},"applied":false}`
  and makes no Hermes call. Clarify labels are compared after stripping a trailing `(Recommended)`
  and casefolding. A submitted clarify choice (each member of `choices`) that matches more than one
  offered label after that normalization is refused the same way, never resolved by picking the
  first; exact unambiguous replies are unchanged and no automatic retry follows (AP-5). Success is `200 {"status":"resolved","applied":true}`. `applied:true`
  means Hermes accepted the resolution (`resolve_*` returned non-zero, or the runs endpoint
  returned `resolved` > 0). It does not mean the command finished. The UI clears the card only
  after a later poll omits it (INT-2).

- **AP-5. Idempotency and stale answers.** The row stores `answer_hash` once Hermes has accepted
  an answer.

  | Situation | Result |
  |---|---|
  | First answer, Hermes accepts | `200`, `applied:true` |
  | Retry, same body, already accepted | the stored `200`. Hermes is not called again |
  | Retry, different body, already accepted | `409 idempotency_conflict`, `applied:false`. The first choice stands |
  | Phone chat: `resolve_gateway_approval` returns 0, or `resolve_gateway_clarify` returns false | `409 stale`, `applied:false`. The row is marked expired. This call did not apply the choice |
  | Bot Chat native answer: `200` whose bounded JSON body has a non-bool integer `resolved` > 0 | `200`, `applied:true` (the only native result that proves application) |
  | Bot Chat native answer: `409` with parsed JSON error code `approval_not_pending` or `approval_not_active`, or `404` with parsed JSON error code `run_not_found` | `409 stale`, `applied:false`. The row is marked expired |
  | Bot Chat native answer: any other result: an unknown `409` code, a non-JSON, malformed or oversized body on `404`, `401`, `403`, `3xx`, `5xx`, a malformed `200` (missing, non-integer, boolean or non-positive `resolved`), a timeout or a connection failure | `503 api_server_unavailable`, no `applied` field. The row stays open. Not retried. The response text is never echoed or logged |
  | Two in-flight answers for one id | one resolver, in arrival order, under a per-id lock. The second sees the stored outcome |
  | Unknown id, or an id stored for another `user_id` | `404 not_found`. No Hermes call |
  | Flag off, or the row's member unavailable | `503 write_gate_closed` |

  If Hermes accepted a choice and HMP died before recording it, the retry calls Hermes, gets
  nothing pending, and returns `409 stale` / `applied:false`. The client copy is "This prompt
  already ended." It does not offer the other buttons as a fresh decision.
- **AP-6. Phone chat send.** `POST /hmp/v1/bots/{p}/phone/messages` with
  `{"client_message_id":"<UUIDv7>","text":"<string>","sent_at":<int>?}`. No `expected_head`.
  Idempotency key `(iid, user_id, profile, cmid)`, hash of `text`, reserved before
  `handle_message`. The same text replays the stored response and does not hand off again. A
  different text is `409 idempotency_conflict`. `handle_message` is called with
  `allow_gateway_control:false`. On Hermes builds that expose a reject-policy admission ticket,
  HMP returns `202 {"state":"submitted"}` only after Hermes reports `admitted`; an explicit
  known refusal outcome is a refusal. `refused_other` can include persistence failures, and its
  detail is unavailable on the ticket; HMP treats it as unknown. If the ticket is absent, has
  an unclassified outcome, or has no outcome within five seconds, HMP stores and returns
  `200 {"state":"unknown"}`. Replaying that cmid returns
  the stored unknown result without a second delivery. Older stock builds have no admission
  ticket; HMP uses their synchronous acceptance flag. The route does not wait for the model.
  **Definitive refusal.** Only a delivery result that is exactly `False` returns
  `503 {"error":{"code":"api_server_unavailable",…},"applied":false}` with stored status
  `rejected`; `applied:false` means Hermes did not admit the message. The bridge returns `False`
  only when `handle_message` left the event unaccepted or the ticket reports one of the known
  refusals (`refused_busy`, `refused_draining`, `refused_precondition_head`,
  `refused_precondition_expired`, `refused_lease_timeout`, `refused_unauthorized`), none of
  which admit a user turn. Background handling may already have been scheduled. `refused_other` (persist failure, unreported exit) is `None`, not
  `False`. Exact `True` stays `202`. `None`, any non-boolean result, a delivery exception, a
  missing session key or a non-list approval probe are uncertain: no `applied` field (`200
  unknown`, or `503` without `applied` for the pre-delivery and exception cases), never
  `applied:false`. The same cmid replays the stored body without redelivery. This is HMP's own
  wire contract, not a `HERMES_API_GAP`; it adds no error code and does not enable approvals.
  While `list_gateway_approvals` for this
  phone session is non-empty, the route does not call `handle_message` and returns
  `409 {"error":{"code":"stale",…},"applied":false}` — the composer is not a way to say yes.
  While a clarify prompt is pending, composer sends also return `409 stale`, `applied:false`.
  Both kinds of prompt are answered only through AP-4; chat text never resolves a wait. The inert authorize trigger stays `allow_gateway_control:false`, and its
  outbound reply is still dropped. Phone chat does not claim DS-4's single-writer guard.
- **AP-7. Who may answer.** The bearer resolves to `user_id`. The answer route loads the row by
  `request_id` and that `user_id`. Bot Chat answers use the `run_id` Hermes registered for the
  stream HMP opened, sent only to loopback. Phone chat answers use `build_session_key` of the
  source HMP built for this `user_id` and the `default` chat. A client-supplied session key is
  ignored. Logging (SEC-4) is `log_event` only: outcome codes (`stored`, `resolved`,
  `stale`, `invalid_choice`, `conflict`,
  `desktop_held`, `awaiting_text`, `unavailable`, and for phone send `submitted`, `unknown`, `replay`, `conflict`, `refused`;
  and the fixed `approval_binding outcome=changed` and `approval_helper outcome=unavailable`)
  and 8-character prefixes of `user_id`, `request_id`, `run_id`. Never the command, description,
  question, chosen answer, clarify label, message text, SSE body, or `API_SERVER_KEY`.
  All successful answer logs use exactly `outcome=resolved`; no choice suffix is permitted.
  When the adapter cannot uniquely match a command but holds valid pending request IDs for
  this session, it may expose deny-only recovery cards with an empty command and explicit
  unbound-approval copy. They still require an owner action through AP-4, and cannot allow
  execution. No usable ID or queue read failure means fail closed until Hermes times out;
  the fallback never enables slash or plaintext control.

  Transport bounds: approval POST total/read deadlines are 15/10 seconds; SSE total/read
  deadlines are 24 hours/90 seconds. Both disable redirects and environment proxies and use
  only pinned loopback literals. SSE requires `text/event-stream`, validates supplied run IDs
  against `run.started`, accepts LF/CRLF, caps frames at 64 KiB and buffers at 128 KiB. Approval
  responses are capped at 64 KiB. Exceeding a bound closes the transport without retry.
  Phone observations have a global 256-row cap, 60-second TTL and 8 KiB text cap; durable
  role/text matches discard them. They are never merged into cursor-addressed snapshot/history
  message arrays, which contain only durable Hermes rows.

- **AP-8. Discovery.** F3 does not register the EV-1 SSE route. The client polls `GET …/prompts`.
  v1.3 names the live-tail frames so a later revision does not invent a second vocabulary:
  `approval.requested` (includes `surface`), `approval.settled`, `approval.unanswerable` (still the
  GU-6 read-only case when HMP cannot bind a `request_id`), `clarify.requested`, `clarify.retired`,
  and `notice` `{"kind":"desktop_held","text":"Waiting for approval on your Hermes Desktop"}` (an
  empty `text` clears it). Until the tail exists those names are the poll's diff, not bytes on a
  socket. `approval_request_id` in the capability map does not gate these routes. A false flag
  still means the old read-only copy for any approval HMP cannot bind. An unbound prompt is never
  given buttons.
- **AP-9. INT-4 for Phone chat.** Clarify answering on Phone chat ships here. The ownership check
  is HMP's `(user_id, request_id)` row, not `tools.clarify_gateway`'s private index. An id the
  phone did not receive from a prompt HMP stored for that user is `404`, so a guessed `clarify_id`
  never reaches Hermes. Path 1 (Bot Chat stream) still has no clarify. Reads do not import the
  clarify module; the clarify symbols are `phone_chat` probe dependencies only.

- **AP-7a. Use-time capability failure.** A Hermes helper that raises `ImportError`,
  `AttributeError` or `TypeError` when HMP calls it is an actual capability failure for that
  operation, however the install looked at listener open. The route answers `503
  api_server_unavailable` with no `applied` field and logs only the fixed
  `approval_helper outcome=unavailable`. It never fabricates a success and never claims the
  Hermes request expired. Unavailable is not proof a waiter is gone: the row stays open.
- **AP-10. Phone-chat binding fence (object identity).** After the `phone_chat` probe passes,
  HMP keeps strong references to the Hermes callables it actually calls for Phone chat. At each
  use it compares them, by object identity, with the attribute then bound in the Hermes module.
  A difference closes the local Phone-chat generation: HMP expires its own Phone rows, answers
  nothing from them, closes `phone_chat` until the next listener open, and logs only
  `approval_binding outcome=changed`. This is an identity check on the helpers HMP calls. It is
  not authenticity, a fingerprint or loaded-bytecode proof, and it reads no disk or manifest.
  Closing it invalidates HMP's local observations only; it does not establish that Hermes's
  pending request expired, so it reports no native expiry or "not pending". Bot Chat `approvals`
  eligibility is independent of it, and a stream bound to the closed generation cannot reinsert
  rows into a new one.

## 7c. Mobile cron management (v1.4, draft)

This additive route family is disabled unless `gateway.platforms.hmp.extra.cron.enabled`
is explicitly true, at least one `owner_device_ids` entry matches this authenticated device,
and the running Hermes provides the scheduler APIs the route needs (GU-2d). A device also
needs the existing per-bot authorization for `{p}`. A failed gate returns `404 not_found`
for non-owner devices or `503 cron_unavailable` for a disabled or unavailable endpoint, before
any job data or loopback API key is used.

| Method | Path under `/hmp/v1` | Body | Result |
|---|---|---|---|
| GET | `/bots/{p}/jobs` | — | `{"jobs":[job,...]}` |
| POST | `/bots/{p}/jobs` | `{"name":string,"schedule":string,"prompt":string,"deliver"?:"local"\|"bot-chat","continuity"?:boolean,"repeat"?:1..9999}` | `{"job":job}`; created paused |
| PATCH | `/bots/{p}/jobs/{job_id}` | one or more of `name`, `schedule`, `prompt`, `deliver`, `continuity`, `repeat` | `{"job":job}`; `repeat:0` clears a finite run limit |
| DELETE | `/bots/{p}/jobs/{job_id}` | — | `{"deleted":true}` |
| POST | `/bots/{p}/jobs/{job_id}/pause` or `/resume` | — | `{"job":job}` |

`job` contains only `id`, `name`, `prompt`, `schedule`, `enabled`, `state`,
`next_run_at`, `last_run_at`, `last_status`, `deliver`, `continuity`, and `repeat`;
optional status/time fields and `repeat` may be null. Delivery is projected only as
`local`, `bot-chat`, or `other`, never an external channel ID or URL. `continuity`
maps to Hermes's `context_from: ["self"]` reference, preserving any other context
references when edited. `repeat` is the total run limit, not the remaining count.
IDs are twelve lowercase hex characters. At most 100 jobs and one MiB of upstream JSON
are returned. HMP never forwards scripts, workdirs, delivery targets, raw errors, or
other Hermes job internals. Create/edit fields are length bounded; unknown fields are
rejected. Reads, pause/resume, and delete use one profile-scoped, literal-loopback API server
endpoint with the profile's own server key, disabled proxy inheritance, redirects, and
automatic retries. Create and edit use Hermes's profile-scoped cron writer so continuity
is saved atomically with the job; both retain the same owner/device/bot gate and the same required-API availability check.
The phone may select only local run history or its own bot's Bot Chat. It cannot name an
arbitrary delivery destination. HMP still creates jobs paused.
Phone clients must treat a transport failure after a write as an unknown outcome and
refresh before attempting another write. The host flag defaults off; release requires
fixture qualification and independent security review.

## 7d. Bot default model (v1.5, draft)

This additive route family is disabled unless `gateway.platforms.hmp.extra.model_management.enabled`
is explicitly true, this authenticated device is in `owner_device_ids`, the selected bot
passes the existing per-bot access check, and the running Hermes provides the model reader and
writer APIs the route needs (GU-2d). Non-owner devices receive `404 not_found`; a disabled or
unavailable feature receives `503 model_unavailable`. These checks happen before a config read, model
catalog request, or write.

| Method | Path under `/hmp/v1` | Body | Result |
|---|---|---|---|
| GET | `/bots/{p}/model/default` | — | `{"provider":string,"model":string}` |
| GET | `/bots/{p}/model/options` | — | `{"providers":[{"provider":string,"name":string,"models":[string,...]},...]}` |
| PUT | `/bots/{p}/model/default` | `{"provider":string,"model":string}` | Stored provider/model, which Hermes may normalize |

The current model read uses only Hermes's routed profile home and returns no other config.
The options read uses the fixed profile-scoped loopback `/api/model/options` route and the
profile's own API key. HMP never accepts a URL, key, base path, raw config patch, or provider
configuration from the phone. Only authenticated providers with nonempty models are projected;
all other catalog fields are discarded. HMP caps the response at eight MiB, 256 provider rows,
10,000 model IDs, and fixed string lengths. It disables proxy inheritance and redirects.

The PUT calls Hermes's existing validated profile-model writer rather than writing YAML from
HMP. It accepts only provider and model, both bounded. A validation refusal is `400
bad_request`; other write failures are `503 model_unavailable`. A model selection may affect
billing. The phone must confirm the named bot and model before PUT. A lost response is an
unknown result: refresh the current model and never automatically retry. The persisted
default applies to new sessions; this route does not switch a running Desktop-owned turn.
The host flag defaults off. Availability on a given Hermes follows GU-2d, not a build list.

## 7e. Host-local generated images (v1.6, draft; not implemented)

Additive under V-3. **Status: draft serving contract; the feature is not implemented.** Reviewed inert
components are recorded in the task evidence. M2 API eligibility and M3 listener-scoped binding are independently source-reviewed; no serving route, device acceptance or release exists. Descriptor emission on the four read routes (RO-3, RO-6, SES-2, SES-2a) is **independently source-reviewed S4 code** (see ROOT_DECISIONS); fetch and device acceptance remain open. Amended 2026-10-02 for the owner's minimum-version
policy: there is **no build list, manifest, fingerprint or process latch**, and this section never claims
that a build, serving platform or device is qualified. The runtime media binder verifies the listener's in-memory cache chain and closes only that listener on a cache identity change; the S4 candidate's four read routes consume it, the fetch route (S5) does not exist yet. Design record and open gates:
[`specs/011-local-image-serving`](../../../specs/011-local-image-serving/spec.md). A client on an
earlier `1.x` build ignores `media` and the route (V-4). The numeric constants below (20 s, 30 s,
1800 s, 512 per device, 4096 total, 128, 2 per device, 4 per instance, 120 per minute) are **new
choices for this feature**, not existing Hermes or HMP constants.

Scope: an image the host's `image_generate` tool already wrote to that profile's image cache,
shown on the tool row that produced it. Not upload, video, audio, file browsing, arbitrary host
paths, or local `MEDIA:` resolution (assistant `MEDIA:` text stays text).

- **LM-1. Gate.** Default **off**. A device may use this feature only when all hold:
  1. the device passes `is_approval_owner_device` (configured owner allowlist and no explicit
     controls denial; unrelated owner privilege never implies this);
  2. the live host flag `local_media.enabled` is exactly `true`;
  3. the `local_media` eligibility member is available (LM-2, GU-2d): the version floor is met, the
     required Hermes APIs are present, and the in-memory media binding holds. No build list, manifest,
     fingerprint or Git SHA is consulted.

  Otherwise no `media` field is emitted and read response bytes are **identical** to those of a
  server without this section. The gate does not affect compat, roster, send or approvals and
  adds no upper version bound on the install. Approval gates are never waived by it, and no grant
  is made automatically. Each device is checked per request against the owner list and any host denial.
- **LM-2. Availability.** Replaces the retired exact-build qualification (manifest, fingerprints, Git SHA,
  process anchor, preload origin checks, GIL guard). The `local_media` member (GU-2d) is computed **once
  when the listener opens**, beside the other members, and reads no build list, manifest, fingerprint or Git SHA:
  - *Minimum floor (root decision D-M3):* the write floor `0.21.5` / `2026.9.24`, inherited from send, whose
    probe table already contains these rows (EVIDENCE_GAP E-M1: existence at the read floor is unverified). A version that declares itself below the floor is
    unavailable (`hermes_version_below_floor`) and no media module is imported. Unknown, `0.0.0`,
    unlisted, newer and development versions are attempted.
  - *Dependencies:* requires `read` available (otherwise `requires_read`). It does **not** require
    `send` or `session_browsing`; a disabled direct-send switch never closes media. The probe table is
    exactly the native callables the media path reaches beyond the read core:
    `SessionDB.get_session`, `SessionDB.get_session_by_title`, `SessionDB.get_compression_lineage`,
    probed by containment and signature shape (never called), with the GU-2d wrapper and tree rules.
    There is no image-producer probe; a changed producer spelling is refused per candidate by the
    lexical check of LM-5.
  - *Binding:* at listener open, the media-chain cross-references are verified in memory and the
    verified references are bound to that listener. An incoherent chain closes **this listener's**
    media with a fixed outcome and never latches the process; a second coherent listener in the same
    process can open. A cheap use-time identity fence compares the current cache objects with the bound
    ones by identity and, on mismatch, closes only that listener's media (`503 media_unavailable`)
    until the next open. This is not authenticity, a loaded-bytecode proof or attestation. Cache
    publication includes the bridge module and its classes in a single locked tuple assignment, with
    imports outside the publication lock. No component relies on GIL atomicity, and a legacy
    process-anchor value is ignored and never written.
  - The availability result is an in-memory boolean. Authorization, explicit settings, scoped
    credentials, payload bounds, resource bounds and the C6b identity proofs are unchanged.

  Status: the M2 eligibility member, offline issue drafting and M3 listener-scoped binding are independently source-reviewed; **media delivery remains unimplemented** (S4 descriptor emission is independently source-reviewed; the fetch route is not implemented). The fixed binding outcomes are `media_binding_incoherent` and `media_binding_changed`; no path or exception text accompanies them. A compat `available` line is probe eligibility only, not
  serving availability. The retired design is recorded as historical in
  [ROOT_DECISIONS](../../../specs/011-local-image-serving/ROOT_DECISIONS.md#minimum-version-conversion-supersedes-s6-manifestfingerprintanchor-s6a-admission-semantics-s6b-preload-qualification-2026-10-02).
- **LM-3. Closed-gate responses.** A non-owner device gets `404 not_found` before the gate is
  consulted. An owner device with the flag off or the feature unavailable gets `503 media_unavailable`, message "image
  delivery is unavailable" (the only new ERR-2 code). User-visible text elsewhere is unchanged.
- **LM-4. Descriptor.** `media` appears only on `role:"tool"` rows in RO-3, RO-6, SES-2 and SES-2a,
  only when the gate is open:

  ```
  "media": {"kind":"image", "ref":"<43-char base64url of 32 random bytes>"}
  ```

  and nothing else: no MIME, size, dimensions, name, path, digest, expiry or native id. The `ref`
  matches `^[A-Za-z0-9_-]{43}$`. A host never emits extra keys. Client rules: ignore unknown extra
  keys on an otherwise valid descriptor; an unknown `kind` is ignored (row renders, no card); a
  malformed `media` is dropped and the row remains. A descriptor never comes from an assistant row.
- **LM-5. Mint preconditions (candidate only; no image/home file access or stat at mint).** The row is in
  an eligible session of the right kind (LM-6); `tool_name == "image_generate"`; the raw tool-result
  content, before the 4000-character display cut, is a `str` of at most 64 KiB UTF-8 that parses
  to an object with `success` equal to `true`, no `error` key, and `image` a `str` of 1..4096
  characters without NUL; and the lexical name derivation passes. One shared result function serves
  mint and fetch. Name derivation is lexical only: `image` must start with the routed profile home
  string plus `/cache/images/`, and the remainder must be a flat, bounded name. There is no
  `resolve()`, no legacy `image_cache`, no legacy-preferring or mkdir helper. A symlinked or
  differently spelled home refuses at fetch; mint checks spelling lexically and cannot prove
  non-symlink without filesystem access. The existing database-file check remains permitted.
  Descriptor minting also requires one request-scoped active-history linkage batch per
  emitting response under the C6 freeze in `specs/011-local-image-serving/ROOT_DECISIONS.md`: strict
  active-set/declaration/digest checks for each returned candidate, with no cross-request
  authority cache. This performs no image/home file access or stat, and does not replace the
  per-fetch scan. Immediately before mint, owner authorization, the live exact-true flag, availability
  and registry state are checked synchronously, with no await before mint.

- **LM-6. Session kind.** Fixed at mint, rechecked at fetch. `phone` iff the session equals the
  caller's own Phone conversation session. `bot_chat` iff it is in the canonical Bot Chat
  compression chain and its tip is the live tip. Any other session gets no descriptor.
  The C6b freeze in `ROOT_DECISIONS.md` defines the shared mint/fetch proof: exact native
  compression-lineage/parent-chain equality, canonical title holder, hidden lineage root,
  current bound-session resolution and fresh unique-kind classification. The title can move
  to a visible compression child; ordinary visible canonical titles do not qualify. Native
  title writers are trusted metadata and can create indistinguishable retitled hidden lineages;
  per-profile bearer gates and strict tool-result/fetch checks still apply.
- **LM-7. Authority.** Authority comes **only** from a strict same-profile `image_generate` tool
  result row. Assistant `MEDIA:` text and Markdown are never parsed for authority.
- **LM-8. Non-wire sidecar.** The raw candidate is internal. It is carried to the server handler in
  an explicit read-result sidecar (or an equivalent reviewed non-wire carrier). It never enters a
  wire-serialized dataclass and is never promoted blindly into serialized message fields.
- **LM-9. Handle.** The `ref` carries no path. It is process-local state: lock-protected, no
  durable bytes, cleared on restart. Entry binds device, user, instance, profile, session kind,
  bound session, tip, tool row id, raw-content digest, monotonic mint time and the first-served
  sha256. TTL 1800 s, 512 per device, 4096 total, LRU; expired or evicted entries are deleted. Mint
  is idempotent: an unexpired entry with the same binding returns the same ref and never extends
  its TTL. At most 128 descriptors per response, newest first; older rows get none. Possessing a
  ref authorizes nothing: every fetch re-authenticates and rescans. Existing capped tool text can
  already contain the `image` string; that exposure is unchanged and rows are **not** claimed
  pathless.
- **LM-10. Route `GET /hmp/v1/bots/{profile}/media/{ref}`.** Always registered. HEAD and other
  methods get the existing `404 not_found`. Order is normative and no image byte is sent before the
  final synchronous check (LM-12):
  1. bearer, existing `Authenticator`;
  2. non-owner device `404 not_found`, **before** the gate;
  3. any query, body or transfer-encoding: `400 bad_request`;
  4. rate limit 120 per minute per device: `429 rate_limited`;
  5. initial per-bot grant via the existing per-bot gate (ERR-3, unchanged), run off the loop on the
     shared default executor;
  6. flag off or media unavailable (LM-1): `503 media_unavailable`;
  7. ref grammar and binding lookup: one `404 not_found` shape;
  8. nonblocking permits (2 per device, 4 per instance): else `429 rate_limited`, no `why`. The
     instance permit is the buffer permit of LM-13 and the device permit shares its lifetime.

  Existing outer middleware (peer `403`, `413 too_large`, compat `503`) is unchanged and runs first.
- **LM-11. Two off-loop phases.** Both run on one dedicated 4-worker executor, never on the event
  loop, with the caller's profile `ContextVar`s copied into each phase.
  - *Phase one:* fresh same-kind eligibility and tip match; native per-bot authorization; scan of
    the exact tool row in the active set; name derivation; leaf file read; raster structure check
    (fixes the MIME as PNG, JPEG or WebP); sha256; history recheck; returns the buffer. Every
    phase-one refusal is `404 not_found`.
  - *Phase two (post-worker final native check):* a second bounded off-loop call runs fresh native
    per-bot authorization, current same-kind eligibility and tip. It takes a worker permit
    **without queueing**; if none is free the request is `429 rate_limited` (no `why`), zero bytes,
    no retry. A revocation or tip/eligibility change seen by it is `404 not_found`, zero bytes.
  - One 20 s worker-wait deadline is **shared** by both phases, not doubled. A wait beyond it is
    `404 not_found`.
  - **No native check runs on the event loop.**
- **LM-12. Final synchronous section.** After the phase-two future returns, on the loop, with no
  `await` between these steps and response `prepare`: fresh bearer authentication (existing `401`
  codes), approval-owner flag (`404`), live media flag, availability and registry existence/TTL (`404`),
  with no per-request qualification await before this section, and the
  first-served digest compare-and-set under the registry lock (set if absent; if different, delete
  the entry and refuse `404`). A causal change between the phase-one recheck/return and the
  phase-two check refuses. **Residual (unavoidable, stated):** a grant or tip change after the last
  native check and before `prepare` is **not** promised to refuse, because no atomic native API
  exists. This contract makes **no atomic snapshot guarantee**. Bearer, owner, flag, availability, TTL and CAS
  changes on the loop still causally refuse.
- **LM-13. Lifetimes under cancellation.** Each phase's worker permit counts actual concurrent
  future completion, including cancellation, and is released only by that future's done callback.
  The buffer permit survives both futures and is released only when both are done (or phase two
  never started) **and** the handler's `finally` has passed. Cancelling the awaiting coroutine
  releases neither early; a late worker keeps its permits until it really finishes.
- **LM-14. Success response.** `200` with `Content-Type` exactly the structural MIME
  (`image/png`, `image/jpeg` or `image/webp`), `Content-Length`, `Cache-Control: no-store, private`,
  `X-Content-Type-Options: nosniff` and the existing `Server` header. No `Content-Disposition`,
  filename, `ETag`, `Last-Modified` or `Accept-Ranges`; `Range` is ignored. Body at most 8 MiB.
  The body is streamed in 64 KiB slices, each within the remaining **30 s total** write deadline
  including EOF. After `prepare`, timeout, cancellation or error aborts the transport; the handler
  returns only after EOF or abort.
- **LM-15. Error table.** Every body is the ERR-1 shape with the existing messages.

  | Stage | Condition | Status | `code` | Extras |
  |---|---|---|---|---|
  | Initial bearer | wrong or non-ASCII `HMP-Instance` | 401 | `wrong_instance` | none |
  | | missing, bad, unknown or expired token, or device not `ACTIVE` | 401 | `unauthenticated` | none |
  | | device or token family revoked | 401 | `revoked` | none |
  | Non-owner | not an approval-owner device (before the gate) | 404 | `not_found` | none |
  | Shape | query, body or transfer-encoding | 400 | `bad_request` | none |
  | Rate | over 120 per minute per device | 429 | `rate_limited` | none |
  | Initial per-bot grant (ERR-3) | `pending_operator`, `refused_allow_all` | 403 | `forbidden` | `authz` |
  | | `not_routed`, `not_served` | 409 | `not_routed` | `authz` |
  | | `unverifiable`, bridge error, unmapped state | 503 | `other` | `authz:"unverifiable"`, `why:"unverifiable"` |
  | Gate | owner device, flag off or media unavailable | 503 | `media_unavailable` | none |
  | Ref/binding | bad grammar, unknown, expired, evicted, foreign device/user/instance/profile/kind | 404 | `not_found` | none |
  | Permits | device 2 or instance 4 exceeded | 429 | `rate_limited` | none |
  | Phase one | candidate invalid, eligibility or tip changed, file missing or unsafe, raster rejected, digest mismatch, worker error, 20 s shared wait | 404 | `not_found` | none; no oracle between causes |
  | Phase two | grant revoked or changed, eligibility or tip changed, phase-two error, shared 20 s wait | 404 | `not_found` | none; same body as phase one |
  | | no worker permit free (no queue, no retry) | 429 | `rate_limited` | none |
  | Final bearer | token expired, device revoked, wrong instance | 401 | `unauthenticated` / `revoked` / `wrong_instance` | none |
  | Final synchronous | owner flag, media flag, availability, TTL, entry or CAS no longer holds | 404 | `not_found` | none |
  | Unexpected | any other exception | 500 | `other` | `why:"internal_error"` |

  The phase-two per-bot refusal is deliberately `404`, not the ERR-3 mapping; ERR-3 applies only at
  the initial grant stage. After `prepare` there is no status to send, so failure aborts the
  transport.
- **LM-16. Logging.** Logs and access logs carry closed-enum reasons only: never a ref, path, name,
  size, digest, body or exception text (SEC-4).
- **LM-17. Client rules.** The phone parses `media` only on tool rows with the exact ref grammar. It
  fetches through a separate binary load path to the active binding only: raw response, existing
  single `401` refresh, no JSON success parser, no DNS, redirect, public CDN call, disk cache or
  fallback. Success requires `200`, a `Content-Type` of PNG, JPEG or WebP, a byte sniff equal to
  that type, and at most 8 MiB. Decode uses a bounded static-raster decoder. On `404` the client may
  re-read once; if the same row id now carries a ref it may fetch once more, otherwise it shows
  "Image unavailable" with a user retry. `404` is unavailable or expired, `429` busy, `503
  media_unavailable` unavailable. The existing phone transport timeout is 15 s, so a slow fetch may
  show unavailable before the host's 20 s and 30 s deadlines; this contract authorizes no transport
  change.
- **LM-18. Memory ceilings (provisional).** Verification ceilings for four concurrent 8 MiB fetches
  are a traced allocation peak of 96 MiB and an incremental RSS of 128 MiB. They are provisional,
  not a native-allocation bound; a failure changes the implementation, not the ceiling.
- **LM-19. Release-candidate evidence and review (open).** Under the minimum-version policy none of
  the following is a per-build runtime admission gate, and no build list or fingerprint receipt is consulted
  by the runtime. Release evidence still identifies its exact tested candidate and native sample. Sampled evidence describes the builds and platform it ran on and does not prove behavior
  on others. Before any shipping, enablement or platform claim:
  - **E1 (lexical producer string):** the bounded exact-build fixture passes for its stated producer and
    scratch layout, as recorded in [the task evidence](../../../specs/011-local-image-serving/tasks.md#e1-bounded-producer-evidence-2026-10-01).
    It compares the raw producer string lexically with the captured routed home plus
    `/cache/images/`, without path normalization. Other producer spellings are uncharacterized; a
    mismatch refuses that candidate on every build.
  - **Linux file-leaf run (`PLATFORM_GAP` for the rest):** the bounded non-root tmpfs file-leaf run passes,
    as recorded in [the scoped evidence](../../research/local-media-linux-leaf-evidence-2026-10-01.md).
    That covers only the leaf check on its stated platform. Native Linux serving and broader
    platform coverage remain unqualified; no Linux support claim follows.
  - **C6b and T12 (pending sample evidence):** exact-native complete binding cost with concurrent-writer
    evidence, and memory on sampled builds against the provisional ceilings of LM-18, are measured once per
    feature release candidate. A failure changes the implementation, not a ceiling or an allowlist. The
    runtime protections are the in-code bounds that apply on every version (LM-5, LM-9, LM-11, LM-14).
  - Independent security review of the exact candidate, owner-authorized install and flag, and physical-
    device acceptance remain required. `SECURITY_REVIEW_REQUIRED` for the handle, route, availability
    binding and its removal of the retired qualification gate.
- **LM-20. Residuals carried.** No atomic snapshot (including ABA on unrelated rows); change after
  the last native check and before `prepare` (LM-12); a coarse-timestamp torn buffer is left to the
  phone codec; no image provider or producer is qualified or fingerprinted (each candidate is refused
  or accepted by the lexical check and the strict tool-row rules); no loaded-bytecode attestation;
  same-account host code, including plugin-directory writes, is not contained; native session and message
  reads may materialize unbounded content, flush queued token counts and prune (HERMES_API_GAP, every
  build); native title writers are trusted metadata; deadlines and memory ceilings are provisional.
  Assistant `MEDIA:` text stays ordinary unmodified text; producers other than `image_generate` have no
  authority (HERMES_API_GAP: no typed tool-artifact record).


## 7f. Approval push registration, issuance and hint resolution (v1.x, draft; spec 014)

Additive under V-3: a client on an earlier `1.x` build never calls these routes, and an HMP that
lacks them answers `404` (V-4). The minor revision number is assigned when the feature is
implemented; this text does not change the revision in the header. Section 7e is reserved by the
media amendment (spec 011) and is not part of this section. Design and evidence:
`specs/014-approval-push-registration/` (`spec.md`, `plan.md`, `analysis.md`, `ROOT_DECISIONS.md`).
The relay half of the feature is a separate contract:
[`HMP_PUSH_RELAY_V1.md`](HMP_PUSH_RELAY_V1.md) (PN-REL, PN-SEAL).

**Status.** The design was frozen by root on 2026-10-02. This section is contract text only: it is
not implemented and states nothing about runtime or scanner behavior. An independent scoped review of
an earlier candidate of this text accepted it with conditions. This text adds the root review
clarifications of 2026-10-02 (F1 to F7, below). A later independent review of that clarified text accepted its
other clauses and required two source gates, the relay clock source and
the optional pin grammar. This text now writes them (the root clock and pin delta of 2026-10-02: R-F1a, R-PIN and N3
to N6, below). Before its focused review, that delta was new and **unreviewed**; the gates are written, not accepted, and an independent focused
sentence review is pending. The clock-count repair of 2026-10-02 followed a focused review of that delta: the review accepted the mechanism, the pins and N3 to N6, and required text repairs for the 4,800-nonce and 240 s qualification under clock steps (its finding D1) and for one APNs connection granularity per allowed `(app, env)` pair (D2), with editorial wording (D3). At that checkpoint, the repaired capacity and connection sentences awaited a focused check of those sentences only. That check has now accepted D1/D2/D3 as contract text; implementation and verification remain pending. Owner and account choices O1 to O6, provider keys and capabilities, HPKE key
custody, DNS and the global relay budget are **pending**; this section authorizes none of them.

**Root interoperability amendment, 2026-10-02 (authoritative).** Root architecture direction for
contract text only (decisions B1 to B6 and P1 to P3; `specs/014-approval-push-registration/ROOT_DECISIONS.md`
and [`HMP_PUSH_RELAY_V1.md`](HMP_PUSH_RELAY_V1.md) §13.1). By B1 to B6 it addresses the former `GAP-PN-1` item and the six
former relay-contract items whose labels GAP-1 to GAP-6 no longer exist in the relay contract. Those removed
labels are distinct from this contract's own live `GAP-1` and `GAP-2` rules (§12), which the amendment
does not touch and about which it makes no claim. Independent review of the clarified text is still
required, and this text is neither an implementation nor interoperability evidence. In this section it shows up as: `DELETE` does not
depend on push availability (PN-REG-3); the `sealed` value is `b64u(enc ‖ ct)` of 82 to 1,105 decoded
bytes (PN-REG-2); the `kid` and `aud` grammars (PN-AV); raw-byte `R`, `K`, `C` in the relay
signature and the exact `scope` and `C` rules (PN-ISS-1, PN-KEY); and the constants of PN-CONST.
Where this section and the frozen `spec.md` differ, that is a defect to report to root, not a
choice for an implementer. The dispatcher (PN-DSP), revocation cleanup (PN-REV), persistence
(PN-PER), logging (PN-LOG) and operator surface (PN-OPS) bind the implementation but have no wire
shape; they stay in `spec.md` and are not restated here.

**Root review clarifications, 2026-10-02 (authoritative; F1 to F7).** Contract-text clarifications after an
independent scoped review of an earlier candidate. They preserve B1 to B6, P1 to P3 and every authority
and security requirement of this section, and authorize no source, key, relay, deployment, provider
action or owner choice. In this section: F2 sets the `why` precedence, the all-or-nothing kid
configuration (including a nonempty kid list and a well-formed configured `push.relay_spki_pins`), kid liveness only while push is available, and the `PUT` check order (PN-AV, PN-REG-1,
PN-REG-2, PN-BND); F3 qualifies the gap labels above; F7 corrects status wording. The relay-side
items F1 (atomic skew re-check), F4 (strict DER signature), F5 (APNs environment pairs) and F6 (rolling
hourly windows) are in [`HMP_PUSH_RELAY_V1.md`](HMP_PUSH_RELAY_V1.md) §13.4. HMP's own per-device
dispatch rate window (PN-CONST, D6) is unchanged. No vector exists for any of them.

**Root clock and pin delta, 2026-10-02 (authoritative; pre-review status recorded below).** A later independent review
accepted the other clauses above and required two source gates; this delta writes them and none is
accepted until a focused independent sentence review. R-F1a: the relay's acceptance instant is
non-decreasing and its rolling windows use monotonic time (`HMP_PUSH_RELAY_V1.md` CLK-1, §13.5); on
the HMP side it changes no route, code or retry rule, because a relay `401` or `422` is already a
fixed, non-retried delivery outcome (RES-C, RES-E). R-PIN: the one optional host setting
`push.relay_spki_pins` and its grammar, defined in PN-AV below and `HMP_PUSH_RELAY_V1.md` CF-1a. N3
narrows the relay's APNs separation to connections; credential and signing-key provisioning stays
pending owner choice O3. N4 syncs the settings list and the all-off purge reasons (PN-AV, PN-BND). N5
counts an inert active row against D24, not D25 (PN-BND). N6 marks earlier "six gaps resolved"
and skew-replay wording superseded history; the live `GAP-1` and `GAP-2` of §12 stay open. No vector exists.

An approval alert is a **hint, never authority**. The alert carries no command, bot, profile,
session, URL, path, credential or answer. The resolver returns a profile locator only. An answer
still needs the app's fresh read of the approval list and a human choice (INT-1, INT-2).

- **PN-AV. Availability (minimum-version policy).**
  - Push adds no Hermes API dependency, floor, manifest, fingerprint or process latch and no new
    §12 internal. It is available for an approval row's surface exactly when that surface's
    approval member is available (`approvals` for `bot_chat`, `phone_chat` for `phone_chat`; spec
    034 R1), the direct-send flag is effective, the host push flag is on and a relay is configured.
    Later and unknown Hermes versions attempt the actual APIs (GU-2c, GU-2d).
  - Host settings, read live per request and per dispatch, never from the wire: `push.enabled`
    (default `false`), `push.relay_url` (no default), `push.relay_kids` (a closed list of relay key
    IDs the phone may seal to), `push.relay_audience` and the optional `push.relay_spki_pins`. A
    missing, malformed or non-HTTPS required value means push is off. A `kid` is ASCII and fully matches
    `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`; the audience is ASCII and fully matches
    `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. Comparison is case-sensitive and exact, with no URL
    semantics, whitespace, Unicode normalization or trimming. A `relay_kids` entry or audience that
    does not match is malformed, so push is off. The same two grammars apply to `relay_kid` in
    `PUT`, to `relay_kids` in `GET`, and at the relay (`HMP_PUSH_RELAY_V1.md` PR-5). They define no
    real key, audience, endpoint or account.
  - **Optional relay pins (R-PIN).** `push.relay_spki_pins` is read like the other settings, live and
    never from the wire. **Omitted** (key absent) means no optional pin. **Configured** means an exact,
    nonempty list of 1 to 8 distinct entries, each the canonical unpadded base64url of a SHA-256 digest
    of a DER `SubjectPublicKeyInfo`: 43 ASCII characters that decode to 32 bytes and re-encode to the
    identical text. An explicit `None`, an empty list, a non-list, a duplicate or any other entry is
    malformed and means `relay_unconfigured`. Omission is distinct from `None` and from an empty list.
    The setting holds only public digests, has no environment-variable or other fallback, and never
    replaces the standard TLS trust-store chain and host-name validation, which are always required.
    A pin constrains only the relay's **leaf** certificate (`HMP_PUSH_RELAY_V1.md` REQ-2). A mismatch
    occurs before any HTTP request byte is written, is retried only as RES-C allows for a pre-write TLS
    failure and has no trust fallback.
  - **Why precedence (F2).** Availability is evaluated once per call and the first condition that
    holds names the `why`: (1) `push.enabled` is not exactly `true`: `push_disabled`; (2) a missing,
    malformed or non-HTTPS relay configuration (the relay URL, the audience, a nonempty kid list,
    and a configured `push.relay_spki_pins` that is not a well-formed list):
    `relay_unconfigured`; (3) a closed approval prerequisite (both members closed) or the direct-send
    flag off: `approvals_unavailable`. A well-formed relay configuration exists whether or not push is
    currently available.
  - **Kid configuration is all or nothing (F2).** An invalid or missing kid or audience configuration
    is `relay_unconfigured`; it is never read as an empty list of live keys. One malformed
    `push.relay_kids` entry makes the whole push configuration malformed. An explicitly empty kid
    list is `relay_unconfigured`, not an available relay with no live keys. A configured
    `push.relay_spki_pins` that is malformed (explicit `None`, an empty list, a non-list, a duplicate or
    a bad entry) also means `relay_unconfigured`; it is never discarded or replaced by a trust
    fallback. An omitted optional pin setting is allowed. The *live* kids are the
    entries of a well-formed list. `GET` omits `relay_kids` unless `available` is true. **Kid
    liveness is applied only while push is available** (PN-AV for at least one member): `GET` and the
    purge apply removed-kid expiry only then, and dispatch already requires availability. While push
    is off for any reason, an otherwise valid active row is kept inert, never destructively expired
    for kid liveness. Absolute expiry (`expires_at`), revocation, family and hash checks, and the
    retained-row purge operate unchanged.
  - A relay failure is a delivery outcome, not a Hermes compatibility finding. It never closes
    approvals and never produces a `--issue-draft` (GU-2d).
- **PN-GO. Routes and gate order.** All routes are under `/hmp/v1`, use TR-5 bearer auth with
  `HMP-Instance`, I-JSON bodies and the ERR-1 error envelope. They are device-scoped, not per bot,
  and none of them uses `POST /bots/{p}/authorize`, the owner-controls `GRANT` path, any access
  card or any privilege-grant path.

  | Method | Path | Body | Success |
  |---|---|---|---|
  | GET | `/push/registration` | none | `200` (PN-REG-1) |
  | PUT | `/push/registration` | PN-REG-2 | `200 {route, generation, expires_at, state}` |
  | DELETE | `/push/registration` | `{"v":1,"expected_generation":int}` | `200 {"generation":int}` |
  | POST | `/push/hints/resolve` | `{"v":1,"hint":K}` | `200` (PN-RES-2) |

  Order on every route: bearer (TR-5; an `HMP-Instance` mismatch is `401 wrong_instance` before any
  token lookup) → **effective approval owner**, else `404 not_found` (the non-disclosure pattern of
  the approval list; a host jobs/model controls denial also closes it) → per-device bucket (`429
  rate_limited`) → body shape and size (`400 bad_request`, `413 too_large`) → route logic. The
  resolver adds its own order (PN-RES-1), and `DELETE` adds no availability gate to it (PN-REG-3).
  *Effective approval owner* is an exact `owner_device_ids`
  entry and no explicit host controls denial; a jobs/model controls grant alone never qualifies.
- **PN-ST. Status table.** No new error code and no new error extra. `retry_state_lost` and `other`
  are existing codes. The envelope carries only the allowed extras (`why`, `authz`,
  `head_message_id`, `definitive`); `409 stale` carries none, so the app reads the current
  generation with `GET`. Messages are the fixed text of each code and are generic for push.

  | Route | Status and code | When |
  |---|---|---|
  | all | `401` per TR-5, PR5-6 | authentication; `401 revoked` also when a revoke committed after authentication (PN-REG-2) |
  | all | `404 not_found` | not an effective approval owner (before any store read beyond auth) |
  | all | `429 rate_limited` | per-device bucket; nothing changes |
  | all | `400 bad_request`, `413 too_large` | shape, I-JSON, size (the PUT bound is stricter than `MAX_BODY_BYTES`) |
  | `GET` | `200` | PN-REG-1 |
  | `PUT` | `200` | new or identical-replay registration |
  | `PUT` | `400 bad_request` | shape, I-JSON, a `relay_kid` that is not a lexically valid kid (even while push is off), `addr_kind`/`env`/`platform` rules, `seal_expires_at` out of range, or `sealed` not canonical b64u or outside 82 to 1,105 decoded bytes; and, only while push is available, a well-formed `relay_kid` that is not live |
  | `PUT` | `409 stale` | CAS failed, replay with a different bearer family, or a row past `expires_at` |
  | `PUT` | `409 idempotency_conflict` | same `request_id`, different body |
  | `PUT` | `503 write_gate_closed {why}` | `why` is one of the four push values of ERR-2b (the three availability values by the PN-AV precedence), checked after the body checks and before kid membership |
  | `PUT` | `503 retry_state_lost` | replay whose re-derived handle does not match the stored hash, or an unreadable `k_grace` |
  | `PUT` | `503 other` | `route_hash` collision; `G` at the bound; first issue with an unreadable `k_grace` |
  | `DELETE` | `200` | removed; the only confirmation. Independent of push availability (PN-REG-3) |
  | `DELETE` | `401 revoked` | the transactional `ACTIVE` device or live-family re-check failed (PN-REG-3) |
  | `DELETE` | `409 stale` | CAS failed |
  | `DELETE` | `503 write_gate_closed {"why":"push_capacity"}` | the only `why` a `DELETE` can carry: no generation row and the generation-row cap reached; nothing written |
  | `DELETE` | `503 other` | store write failure (not confirmed; the delete fence still closes eligibility) |
  | `POST` | `200 located`, `200 not_pending` | PN-RES-2 |
  | `POST` | `404 not_found` | every other case, including every hidden, unknown, foreign, expired or rotated hint |
  | `POST` | `503 write_gate_closed` | the approval gate for the row's surface (spec 034 `_require_approvals_gate`); the frozen design assigns this route no push `why` |

  **Former `GAP-PN-1` is resolved (decision B5).** `DELETE` is not refused when push is unavailable
  (PN-REG-3). Any `DELETE` answer other than `200` is still "not confirmed" (§11 of the spec;
  PN-APP-3).

- **PN-REG-1. `GET /push/registration`.**

  ```
  200 {"available": bool, "why"?: <code>, "relay_kids"?: [<kid>], "generation": <int>,
       "registration": null | {"state": "active"|"provider_gone"|"expired",
                               "platform": "apns"|"fcm", "expires_at": <int>}}
  ```

  - `GET` writes nothing and creates no row. It reports `generation` 0 for a device with no
    generation row. The route handle is never echoed. It stays readable while push is unavailable
    (`available: false` with its `why`); it is never refused for that reason.
  - `why` is one of `push_disabled`, `relay_unconfigured`, `approvals_unavailable` and appears only
    when `available` is false (a field of this `200` body; the same codes are the `why` values of
    `503 write_gate_closed`, ERR-2b). `approvals_unavailable` covers every closed approval
    prerequisite: both members closed, or the direct-send flag off. When several hold, the `why` is
    chosen by the PN-AV precedence. `relay_kids` is omitted unless `available` is true; it lets the
    phone choose its seal key; the `iid` binding is the pinned `iid` the phone already holds.
  - **Which row.** The device's active row, when one exists and is not in the delete fence
    (PN-BND), is reported `active` if usable and `expired` (re-register needed) if not. Unusable
    means past `expires_at`, its `relay_kid` no longer in the live list (tested only while `available`
    is true; while push is off for any reason a row is not reported `expired` for kid liveness), its
    `family_id` not the bearer's family, or its stored route hash not re-derivable (PN-ISS-4,
    PN-ISS-5, which includes an unreadable `k_grace`). A row in the delete fence is reported as `registration: null`. With
    no active row, the device's latest row is reported (state `provider_gone` or `expired`) only if
    it left `active` by relay feedback or by the purge's expiry (PN-BND) and no write has advanced
    `G` since, that is, the row's `generation + 1` equals the current `G`. Every other case,
    including a `retired` row, is `null`.
  - A `200` is the app's signal that push is present on this host; a `404` on `GET` from an older
    HMP means absent. The app shows the notification-permission opt-in only after some paired
    instance reports `available: true`.
- **PN-REG-2. `PUT /push/registration`.** Body at most 4,096 bytes (`413 too_large` above it):

  ```
  {"v": 1, "request_id": <b64u>, "expected_generation": <int>, "platform": "apns"|"fcm",
   "addr_kind": "apns_token"|"fcm_token"|"fcm_fid", "env"?: "production"|"sandbox",
   "relay_kid": <kid>, "sealed": <b64u>, "seal_expires_at": <int>}
  ```

  - `request_id`: 16 to 32 random bytes, canonical b64u, chosen once per app registration intent and
    reused, with the identical body bytes, on every retry of that intent (PN-APP-2).
  - `sealed`: canonical b64u of `enc ‖ ct` (a 65-byte uncompressed SEC1 P-256 point followed by the
    AES-128-GCM output including its 16-byte tag), with a **decoded length of 82 to 1,105 bytes
    inclusive** (65 + 16 + a 1 to 1,024 byte plaintext, inside the frozen 2,048-byte ceiling);
    anything else is `400 bad_request`. HMP checks only canonical b64u and these bounds. It cannot
    open the value and never tries, so a malformed point, tag or plaintext is found only by the relay
    (`422 sealed_invalid`, feedback `expired`). Its construction is
    [`HMP_PUSH_RELAY_V1.md`](HMP_PUSH_RELAY_V1.md) §6.
  - `relay_kid` must match the `kid` grammar (PN-AV), else `400 bad_request`, whether or not push is
    available. Membership in the live `push.relay_kids` list is checked later, in the order below.
  - `addr_kind` must match `platform` (`apns_token` for `apns`; `fcm_token` or `fcm_fid` for
    `fcm`). `env` is required for `apns` and forbidden for `fcm`. Else `400 bad_request`. These
    declared values are signed into every relay request and the relay rejects any mismatch with the
    sealed plaintext, so the host's checks and the seal agree.
  - `seal_expires_at` must lie in `(now + 3,600 s, now + 1,209,600 s]` (1 hour to 14 days), else
    `400 bad_request`. The row's `expires_at` is defined as exactly `seal_expires_at`.
  - **Check order after the body checks (F2).** The body grammar and size checks above (shape, I-JSON,
    size, the lexical kid grammar, `addr_kind`/`env`/`platform`, `seal_expires_at`, `sealed`) run
    independent of availability. Then, in this order: (1) push available (PN-AV for at least one
    member), else `503 write_gate_closed {why}` with the PN-REG-1 code; (2) `relay_kid` in the live
    `push.relay_kids` list, else `400 bad_request`; (3) transactional liveness, replay and CAS below. So a
    lexically malformed kid is `400` even while push is off, and a well-formed kid that is not live (for
    example removed) is `503` while push is off and `400` while it is available.
  - **Idempotent replay first**, after the checks above. A replay made after push became unavailable
    gets `503 write_gate_closed {why}`, and one whose `relay_kid` was removed since, while push is
    available, gets `400 bad_request`; neither reaches the replay check. The app treats both like `409
    stale`: `GET`, then a new intent. Otherwise, if the device's current active row has the same
    `request_hash`:
    - a different body hash is `409 idempotency_conflict`;
    - a row `family_id` different from the bearer's family, or a row past `expires_at`, is
      `409 stale`;
    - otherwise HMP re-derives `R` from the row's stored inputs (PN-ISS-1). If `SHA-256(R)` equals
      the stored `route_hash`, it returns `200` with that `R` and generation, whatever
      `expected_generation` says. If it differs, or `k_grace` cannot be read (PN-ISS-5), it returns
      `503 retry_state_lost`; the row and `G` stay unchanged. The app treats this like `409 stale`:
      `GET`, then a new intent.
  - **No history is not a replay.** A `request_id` that matches no active row goes to CAS. Every
    successful `PUT` advanced `G` past its own `expected_generation`, and `G` never decreases for a
    non-REVOKED device. So, **absent a consistent restore of the store and the binding**, a replay
    of an already-applied request fails CAS with `409 stale`, even after its retired row was purged
    or evicted, and HMP never answers it with fresh handle bytes. After a consistent restore that
    rolled `G` back, a byte-identical retry of a `PUT` whose acknowledgement was lost can pass CAS
    and returns a fresh `R′`, never the lost `R`. That is harmless: the app never committed the
    lost handle and commits `R′` (RES-20).
  - **Transactional liveness.** Before either replay or CAS, the write transaction re-reads the
    device as `ACTIVE` and its bearer family as live. A revoke committed after authentication
    answers `401 revoked`, with no registration or generation write.
  - **CAS.** Otherwise succeed only if `expected_generation == G` (0 for a device with no
    generation row), else `409 stale` with no extra. Then the capacity checks, with nothing
    changed on refusal: if the device has no active row and the instance already holds 64 active
    rows, or the device has no generation row and 256 non-REVOKED devices already hold one, return
    `503 write_gate_closed {"why": "push_capacity"}`. Replacing the device's own active row never
    counts against capacity. On success, in one store transaction: retire the device's current row
    (if any), advance `G` by exactly one, create the generation row if absent, draw the 32-byte
    row salt from the OS CSPRNG, insert the new active row, enforce the retained-row caps
    (PN-BND), and return `200 {"route": R, "generation": G, "expires_at": int, "state": "active"}`.
    A transaction that changes a device's registration state advances that device's `G` once,
    however many rows it touches. `G` stays below 2^53 (I-JSON): if `G + 1` would reach 2^53 the
    write is refused `503 other` with nothing changed.
  - **Collision.** A UNIQUE violation on `route_hash` (whatever its cause, including an identical
    salt draw) aborts the whole transaction: no row is inserted, the previous row stays active, `G`
    does not advance, and the answer is `503 other`. A retry of the same intent draws a fresh salt.
  - The device's live token family, `iid` and `H` are recorded on the row.
- **PN-REG-3. `DELETE /push/registration`.** CAS as above. It retires the current row (if any),
  advances `G` by one and returns `200 {"generation": G}`. Only a `200` confirms removal; every
  other outcome is "not confirmed". Deleting with no row is still a CAS and still advances `G`, so
  a late older `PUT` cannot land.
  - **Independent of delivery availability (decision B5).** `DELETE` does **not** require
    `push.enabled`, a configured relay, a live `relay_kid`, an available approval member or an
    effective direct-send flag, and none of those closed states changes its answer. A disabled
    delivery lane must not stop the removal of an existing registration. It makes no call to Hermes,
    the relay or a provider.
  - **What it still requires.** Bearer and `HMP-Instance` (TR-5), effective approval owner
    (`404 not_found` otherwise), the per-device bucket, body shape and size, and CAS. In the write
    transaction, before CAS, it re-reads the device as `ACTIVE` and its bearer family as live (`401
    revoked` otherwise, with no write). Terminal revocation and the capacity rules below are
    unchanged. It never resurrects a row, never bypasses authentication, and never claims removal
    before a `200`. It does not read `k_grace`, because it only retires an existing row.
  - **Capacity.** `DELETE` of an existing registration is never refused for capacity and never
    inserts into a capped table: retiring is an in-place update and the device already has its
    generation row. Only a `DELETE` from a device with no generation row would create one, so it is
    subject to the generation-row cap: while 256 non-REVOKED devices already hold one it is refused
    `503 write_gate_closed {"why": "push_capacity"}` with no write. Under the invariant "an active
    registration implies a generation row", nothing is registered for that device. The answer is
    still not a `200`, so it confirms nothing, and the app keeps its pending delete intent.
  - **Documented race (no invariant waiver).** A `PUT` delayed in flight can land after capacity
    frees, after such a no-generation `DELETE` was refused. The app's pending delete intent then
    retries as an ordinary CAS `DELETE` against the now-existing generation row and removes it.
  - **Store write failure.** If the store write itself fails (for example the disk is full),
    eligibility still closes: the listener adds the device's current `route_hash` to an in-memory
    delete fence that dispatch and resolve check, and `GET` stops reporting the row as active. The
    answer is `503 other` (not confirmed) and the app retries `GET`/`DELETE`. The fence entry is
    removed once a store write retires that row. The fence does not survive a restart; between a
    restart and a successful `DELETE`, a revocation or the seal's `not_after`, alerts may resume
    and resolve as unable to check (RES-21).
- **PN-REG-4. Limits.** At most one active registration per device per instance, at most 64 active
  registrations per instance, and at most 256 generation rows of non-REVOKED devices. Per-device
  buckets per minute: 6 registration writes, 30 status reads, 30 resolves. A refused write changes
  nothing.
- **PN-REG-5. No cross-instance effect.** Every row carries the serving `iid`. A route, handle or
  sealed address registered on one instance has no meaning on another. HMP never forwards to,
  falls back to or names another instance (PR-3).
- **PN-ISS-1. Route handle.** `R = b64u(HMAC-SHA256(k_grace, transcript("HMP1-PUSH-ROUTE", iid, H,
  device_id, family_id, G, salt)))`, which is 43 characters. Field types follow TR-13: `iid`,
  `device_id` and `family_id` are UTF-8 strings, `H` and `G` are u64, `salt` is raw 32 bytes. `H` is the store
  revocation epoch (`meta.store_revocation_epoch`). The store keeps `SHA-256(R)` (over the raw
  decoded bytes, TR-12) and the inputs including the salt; it never keeps `R`. `R` can be
  re-derived only with the store **and** the `k_grace` file, the same custody as the refresh retry
  grace (PR5-5). The dispatcher re-derives `R` for the payload and a replay re-derives it for the
  response; both compare the result with the stored hash first. `request_id` is used only for
  idempotency (`request_hash`), not as a handle input.
- **PN-ISS-2. Nonreuse is a computational argument, not a proof.** Under the assumption that
  `k_grace` is secret and uniformly random, HMAC-SHA256 is treated as a PRF. Distinct transcripts
  then give outputs that collide only with negligible probability; distinct inputs alone do not
  make outputs mathematically distinct. The transcripts differ across devices (`device_id` is
  fresh per pairing), credential generations (`family_id`), host generations (`H`), registration
  generations (`G`, persisted and only increasing) and rows (a fresh 32-byte CSPRNG salt). The salt
  keeps handles fresh where the other inputs can repeat:
  - `k_grace` can be re-created without an identity change. A new `k_grace` is a new PRF key; old
    handles then stop validating (PN-ISS-4) rather than becoming reusable.
  - A consistent backup restore of both the store and the binding directory rolls `G` back without
    the identity classification noticing. The salt keeps the next handle fresh. The replay CAS
    guarantees of PN-REG-2 are stated absent such a restore (RES-20).

  A UNIQUE index on `route_hash` over stored rows (active and retained) rejects an actual collision
  deterministically, but only while the row is stored. Beyond retention or cap eviction, nonreuse
  rests on the salts, `G` and the PRF assumption, and is stated that way, not as a test result.
- **PN-ISS-3. Hint ref.** `K` is 32 bytes from the OS CSPRNG, b64u (43 characters), minted per
  (approval row, registration) dispatch. It is held only in process memory with its binding
  `(SHA-256(R), G, prompt generation, row key)`. A collision with a live entry is redrawn. `K`
  lives while its row is open in its prompt generation, then for 60 s after the row settles, and
  never longer than 60 minutes. It dies on listener close or restart, like the rows it names.
- **PN-ISS-4. Validation is exact.** A registration is usable only when every bound field equals
  the current value: row `active`; row `device_id` equals the bearer's device; row `family_id`
  equals the bearer's family (resolver) or is a live family of that device within
  `REFRESH_ABSOLUTE_TTL_S` (dispatch); row `iid` and `H` equal the serving ones; row generation
  equals the device's current `G`; not expired; `relay_kid` still in the live list (dispatch); the
  row's `route_hash` is not in the delete fence; and the re-derived `SHA-256(R)` equals the stored
  `route_hash`. A hint is accepted only when its binding names that exact row hash and generation
  and the current, unclosed prompt generation. Existence alone never suffices.
- **PN-ISS-5. `k_grace` access for push.** Push never calls the existing accessor that re-creates
  and rewrites the file. It uses a new read-only accessor that reads the file, checks its length,
  and never creates, rewrites, deletes or changes the mode of it. Every read runs off the event
  loop, once per request or per batch, never per row and never inside a store transaction. A
  missing, unreadable, wrong-length or transiently failing read means "not re-derivable" for that
  call only: `GET` reports `expired`, dispatch skips the row, a replay answers `503
  retry_state_lost`, a first-issue `PUT` answers `503 other`, and the call writes nothing because
  of the read failure. A transient read error therefore never creates, rewrites or deletes the
  secret, and by itself never changes a row's state. The purge's expiry of a hash mismatch changes
  state only after a successful read whose derived hash differs; independent authoritative expiry
  (past `expires_at`; a removed kid, only while push is available, PN-AV) and revocation still change
  row state with the secret unreadable.
- **PN-KEY. Key separation.** `HMP1-PUSH-ROUTE` and `HMP1-PUSH-COLLAPSE` are HMAC-only tags and
  `HMP1-PUSH-RELAY` is signature-only. None of the three is a row of the V-1 tables and none joins
  the transcript or hash-domain tag lists of V-1 (like `HMP1-GRACE`). None may be a prefix of any
  other tag in use, nor the reverse; a prefix-freeness test runs over the full tag set. The relay
  signature reuses the instance key under decision `⟨D2⟩(a)` and the conditions in
  [`HMP_PUSH_RELAY_V1.md`](HMP_PUSH_RELAY_V1.md) §4. The collapse identifier is
  `C = first 32 characters of b64u(HMAC-SHA256(k_grace, transcript("HMP1-PUSH-COLLAPSE",
  SHA-256(R), scope)))` with `SHA-256(R)` over the raw decoded `R` and `scope` the exact canonical profile locator as
  UTF-8, with no normalization. The first 32 characters of that b64u string decode to exactly 24
  bytes, and `C` is opaque, reveals no profile, and is a stable pseudonym per (registration, bot)
  for the registration's lifetime (RES-23). The relay signature transcript carries `R` and `K` as
  raw 32 bytes and `C` as raw 24 bytes, never as base64url text
  ([`HMP_PUSH_RELAY_V1.md`](HMP_PUSH_RELAY_V1.md) §4).
- **PN-RES-1. `POST /push/hints/resolve`.** Body `{"v": 1, "hint": K}` with `K` a 22 to 64
  character canonical b64u string, else `400 bad_request`. There is no `route` field: this matches
  the accepted app resolver port, which never carries the route handle. Order: bearer → effective
  approval owner (`404`) → bucket (`429`) → body shape (`400`) → push flag on (`404`) → the
  **bearer device's** single current active registration, validated exactly (PN-ISS-4 with the
  bearer's family; `404`) → exact hint whose binding names that registration's route hash and `G`
  (`404`) → bot grant for the hint's profile (`404`, masking ERR-3 detail) → the approval gate for
  the row's surface (`503 write_gate_closed`) → visibility (the approval lane's current-visibility
  seam; a hidden row is `404`, whatever its status) → row state.
- **PN-RES-2. Results.** `200 {"state": "located", "profile": p}` only when the row is open in the
  current prompt generation and visible now. `200 {"state": "not_pending"}` only when the row is
  not hidden now and was settled by an authoritative cause (spec 014 §10, I-2: an applied answer;
  native `409 approval_not_pending`/`approval_not_active` or `404 run_not_found`; Phone listing
  omission). Run completion is excluded (`⟨D4⟩`). Every other case is `404 not_found`: unknown,
  foreign, revoked, rotated, expired, a closed or rebound generation, a hidden row (Desktop held,
  member closed), a locally expired row, a purged or evicted row or hint, and an unknown settle
  cause.
  - **Current visibility (no sticky bit).** Hiddenness is evaluated at resolve time and is not
    remembered. A row that was hidden earlier, was settled authoritatively by Hermes meanwhile and
    is visible now may answer `not_pending`, which is a true statement about Hermes (RES-18).
  - **Local expiry.** A row past `expires_at + EXPIRY_GRACE_S` is locally expired exactly as the
    approval list treats it: no longer open, so `404`.
  - **Phone rows.** The approval list reconciles Phone rows through `list_gateway_approvals`; the
    resolver does not. `located` for a Phone row that Hermes has since withdrawn is the accepted
    residual of RES-18.
- **PN-RES-3.** The response never carries a request ID, command, description, choices, run or
  session identifiers, expiry, instance name or any authority. The located profile is a navigation
  hint for the app's own fresh read.
- **PN-RES-4.** The resolver mutates nothing. A hint can be resolved again while it lives.
- **PN-BND. Resource bounds.** Every table and map has a cardinality and an overflow rule. Active
  registrations are not bounded by the dispatch queue (HMP does not cap paired devices), so push
  sets its own caps.

  | Object | Scope | Cardinality bound | Overflow rule |
  |---|---|---|---|
  | Active registration rows | store, per instance | at most 1 per device and at most 64 | A `PUT` from a device without an active row is refused `503 write_gate_closed {"why":"push_capacity"}`, nothing changed. Replacement, `DELETE` of an existing registration and every retirement are never refused. A row that can never deliver again (past `expires_at`, kid no longer live, hash no longer re-derivable) is expired by the purge and stops counting: capacity frees no later than 14 days plus the next purge interval (up to 1 hour while the listener runs) for expiry, and within one purge interval for kid removal (only while push is available, PN-AV; while it is off for any reason, including an empty kid list or malformed pins, a kid-removed row stays active and inert, and keeps counting against this active cap (D24, not the retained cap D25), until push is available again or `expires_at`) or a hash mismatch after a successful `k_grace` read. A stopped listener purges nothing; the purge runs again at the next listener open. A row of a device that lost owner status stays active and inert until its `expires_at`, because owner status is live and reversible |
  | Retained rows (`retired`, `provider_gone`, `expired`) | store, per instance | at most 8 per device and 1,024 in total, each for at most 30 days from its state change | Enforced only inside a `PUT` transaction and the push purge step, by deleting the oldest retained rows first (per device, then globally). Retirement in `DELETE`, feedback, purge expiry or post-commit cleanup does not enforce caps, so the table may transiently exceed 1,024 by at most 64 rows until the next `PUT` or purge |
  | Device generation rows (`G`) | store | at most 256 rows whose device is not REVOKED | A first `PUT`, or a `DELETE`, from a device without a generation row while 256 such rows exist is refused `503 write_gate_closed {"why":"push_capacity"}`, nothing changed and no write. The purge deletes the generation and registration rows of REVOKED devices, so they do not count. A generation row of a non-REVOKED device is never deleted or decreased. An active registration implies its device's generation row. After 256 distinct non-REVOKED devices have written, a new device remains capacity-blocked until the operator revokes some; registration expiry alone does not release a generation slot (RES-25) |
  | Dispatch queue | memory, per listener | 64 events | Drop the new event, `queue_full` |
  | Recipients per row | memory | 4 | Most recently registered first; the rest skipped, `recipients_capped` |
  | In-flight relay requests | memory, per listener | 2 | The worker waits for a free slot; the dequeue TTL check still applies |
  | Hint map | memory, per listener | 256 entries | Evict, in order: entries whose row settled or whose generation closed; then the oldest by mint time. An evicted hint resolves `404` |
  | Coalescing slots | memory, per listener | 256 | Evict the least recently used idle slot (no pending trailing event). If every slot holds a pending event, drop the new event, `coalesce_full`. Evicting an idle slot forgets its last send time, which loosens the 10 s minimum interval for that slot once; the per-device hourly cap still bounds the rate (RES-22) |
  | Hourly per-device counters | memory, per listener | keyed by `device_id`; at most 256 (only a device with a generation row has one) | A counter survives a re-registration while the device is `ACTIVE` and has an active registration. It is removed when its hour window ends with no active registration, or when the device stops being `ACTIVE`. Never evict a live counter. If the table is full anyway, refuse the send, `rate_table_full` (fail closed, not a reset). A restart discards the table |
  | Delete fence (route hashes whose `DELETE` write failed) | memory, per listener | at most 64 (one per active row; removed when the row leaves `active`) | Cannot exceed the active cap. If it would, every dispatch is refused, `fence_full` (fail closed) |
  | Per-device request buckets | memory, shared `RateLimiter` | `LIMITER_TABLE_MAX` (4,096, LRU) | The existing limiter's behavior: eviction or restart can only loosen a limit briefly. Keys are authenticated device IDs, not attacker-chosen |

  Rows of REVOKED devices wait at most one purge interval before deletion. Their number is bounded
  by the operator-gated pairing and revocation rate over that interval, not by the cap of 256.

  **REVOKED is terminal.** The purge deletes the generation row and every registration row of a
  REVOKED device inside a `BEGIN IMMEDIATE` transaction that re-reads `devices.state` (never a
  cached value). That is safe only while no code path returns a REVOKED device to another state.
  The implementation adds an explicit guard in the store's device-state setter that refuses to
  change a REVOKED device, and a test that fails if it can. The REVOKED purge is not enabled
  without that guard and test. Device IDs are fresh per pairing and never reused.

  **Purge.** A bounded push purge step runs at listener open and then hourly on the listener's
  loop: it reads `k_grace` once, off the loop; deletes retained rows past retention or over the
  caps, oldest first, and wipes the secret columns of any non-active row; deletes the generation
  and registration rows of each REVOKED device; retires active rows whose device is no longer
  `ACTIVE` or whose family is revoked (advancing `G`); and **expires** (`state := expired`,
  advancing that device's `G` once, wiping the secret columns) every active row that is past
  `expires_at`, whose `relay_kid` is no longer live, or whose route hash no longer re-derives after
  a **successful** `k_grace` read. The removed-kid case applies only while push is available
  (PN-AV, F2): while push is off for any reason (`push_disabled`, `relay_unconfigured` including an empty kid list or malformed pins, or `approvals_unavailable`) the purge never expires a row for kid liveness and
  keeps otherwise valid active rows inert, and every other step runs unchanged. Only the
  hash-mismatch case needs a successful read: an
  unreadable `k_grace` never expires a row merely because it is unreadable and never blocks the
  other steps. A purge failure is logged with a fixed code and changes no revoke, token, pairing,
  route or Hermes outcome.

  **Lost idempotency history.** Once a retained row is purged or evicted: a replay of its `PUT`
  gets `409 stale` (CAS); its `R` and any surviving hint resolve `404` (unable to check); late
  relay feedback for it is a no-op. Nonreuse past that point is the computational argument of
  PN-ISS-2. Absent a consistent restore of the store and binding, HMP never answers a replay with
  fresh handle bytes; after such a restore it can, harmlessly (RES-19, RES-20).
- **PN-CONST. Constants of this section.** The frozen values of `ROOT_DECISIONS.md`, collected for
  reference. They are **not rows of the §13 table**: that table is checked mechanically against
  the implementation's constants, and these constants join it, together with that check, only when
  the feature is implemented. Owner deployment budgets stay pending.

  | Name | Value | Decision |
  |---|---|---|
  | Seal lifetime, minimum / maximum | 3,600 s (1 h) / 1,209,600 s (14 d) | D9 |
  | Re-seal refresh threshold | under 345,600 s (4 d) remaining | D9 |
  | Retained-row lifetime | at most 2,592,000 s (30 d) from the state change | D9 |
  | `PUT` body / seal plaintext | 4,096 / 1 to 1,024 bytes | D10 |
  | Sealed value (decoded): accepted range / frozen ceiling | 82 to 1,105 bytes inclusive (`enc` 65 + tag 16 + plaintext) / 2,048 bytes | D10, B3 |
  | `kid` / audience grammar | `[A-Za-z0-9][A-Za-z0-9._-]{0,63}` / `{0,127}`, ASCII, case-sensitive, exact | B4 |
  | FCM `channel_id` and the one global FCM `collapse_key` | the fixed literal `hmp_approval_v1` | B4 |
  | Relay `ts` / `ttl_s` | nonnegative integer below 2^53 / integer 60 to 900 inclusive | B6 |
  | Per-device buckets per minute: writes / status reads / resolves | 6 / 30 / 30 | D11 |
  | Dispatch queue / relay concurrency per listener | 64 / 2 | D12 |
  | Recipients per approval row | 4 | D13 |
  | Hint map entries / hint margin after settle / hint hard maximum | 256 / 60 s / 3,600 s | D14 |
  | Coalescing minimum interval per slot / hourly sends per device | 10 s / 30 | D6 |
  | Provider TTL floor / cap / default | 60 / 900 / 330 s | D7 |
  | Active registrations per instance | 64 | D24 |
  | Retained rows per device / total | 8 / 1,024 | D25 |
  | Coalescing slots per listener | 256 | D26 |
  | Generation rows of non-REVOKED devices | 256 | D28 |
  | Collapse identifier `C` length | 32 characters | D5 |
  | Handles `R`, `K` | 43 characters (32 decoded bytes) | D1/D5 |
  | Collapse identifier `C` decoded | 24 bytes | D5, B1 |

  Relay-side and relay-client constants (retries, timeouts, breaker, limits, replay cache) are in
  [`HMP_PUSH_RELAY_V1.md`](HMP_PUSH_RELAY_V1.md) §12.
- **PN-XREF. Cross-references.** Relay request, signature, verification order, seal, HPKE suite,
  responses and templates: [`HMP_PUSH_RELAY_V1.md`](HMP_PUSH_RELAY_V1.md). Dispatch, revocation
  cleanup, persistence, logging, operator surface, platform truthfulness and app obligations:
  `specs/014-approval-push-registration/spec.md` (PN-DSP, PN-REV, PN-PER, PN-LOG, PN-OPS, PN-PLAT,
  PN-APP) and its §10 and §11. Residuals: §14 RES-13 to RES-27.

## 8. Guarantees, capability contract and write gate (FZ-R-8, FZ-R-9)

- **GU-1. Guarantee flags.**

  | Flag | Meaning when `true` |
  |---|---|
  | `no_defer` | Hermes refuses, rather than defers, a `defer_policy="reject"` message at every deferral site known to the reviewed build (P2) |
  | `atomic_anchor` | the head precondition is checked atomically with the append, including the turn-start compaction commit, and fails closed (P3 + P3b + HP-4/HP-5 amendments) |
  | `approval_request_id` | exec approvals are relayed and resolved by `request_id` (P1) |
  | `confirmed_settle` | Hermes reports turn settlement and the interrupt reason (P4) |

  A `true` flag is a necessary condition, not proof of the R0-BLK-10 invariant (SUB-10, CL-4).
- **GU-2. Runtime derivation**. At runtime, a flag is derived **only** from Hermes's native, versioned capability contract. Hermes exposes `gateway.platforms.base.PLATFORM_ADAPTER_CAPABILITIES`, a mapping whose per-key semantics change only with a version bump. A flag is `true` iff the relevant key is present at or above the floor:

    | Flag | Key | Floor version |
    |---|---|---|
    | `approval_request_id` | `exec_approval_request_id` | ≥ 1 |
    | `no_defer` | `defer_policy_reject` | ≥ 1 |
    | `atomic_anchor` | `admission_precondition` | ≥ 2 |
    | `confirmed_settle` | `turn_settled` | ≥ 1 |

    - The meaning of each version is defined by the comment on that mapping in `gateway/platforms/base.py`, together with its behaviour tests (`tests/gateway/test_platform_adapter_capabilities.py`). Both were added by the reviewed patch series (HP-6).
    - An absent map, an absent key, or a version below the floor gives `false`.
    - Only a genuine integer counts as a version. A boolean, a string or a float is treated as absent (DR-12).
    - `>= floor` relies on the Hermes map's rule that a higher version is a strict superset of every lower version's behaviour (DR-5). HMP SHOULD log any version higher than the ones it knows.
    - HMP does not use a Hermes build identity to derive guarantees. Build identity is used only for GU-2c read compatibility.
- **GU-2a. Tested samples (evidence only; owner policy 2026-10-01).**
  - The HMP release test matrix pins exact reviewed Hermes builds by commit SHA (`R0_FREEZE_REVIEW.md` §6). Those receipts describe the samples that were tested, including the capability-derived flags.
  - A tested-sample match is evidence only. It never admits or refuses a build, and no gate reads it.
  - A build outside the matrix is attempted like any other (GU-2c, GU-2d). Its tested/untested status appears only as evidence in tooling.
- **GU-2b. Residual: false capability claims.**
  - A modified Hermes could advertise capabilities it does not implement.
  - Such code runs as the same OS user as Hermes, so this sits inside the E-SI-15 trust boundary (SEC-1). It is covered by the same owner acknowledgement.
  - HMP does not try to detect it.
- **GU-2c. Minimum supported Hermes version** (owner policy 2026-10-01, replacing the exact-build list of `R0_OWNER_DECISIONS.md` bounded amendment 1).
  - Read compatibility is decided by a minimum version, not a list of builds. The floors are per feature: `read` and session browsing 0.21.4 (2026.9.21); `send`, `jobs` and `model` 0.21.5 (2026.9.24). Each floor is one verified release, expressed in both version schemes.
  - HMP reads the Hermes version with file reads only: a valid `baseVersion` in `install-stamp.json` (read as UTF-8, optional BOM), else a literal `__version__` in `hermes_cli/__init__.py`, else the literal `__release_date__`. The stamp is authoritative, as in Hermes's own version lookup; HMP does not take the larger of the stamp and the literal. The `0.0.0` placeholder and any non-plain version count as absent. HMP never imports, executes or evaluates Hermes code to learn the version, and never converts between the two schemes.
  - Only a version that declares itself below a floor is refused (`hermes_build_unsupported`), and then no Hermes internal is imported. An unknown, unlisted, newer or unreleased version is attempted, subject to GU-2d and every security check. An unidentifiable or unlisted build is not, by that fact alone, unsupported.
  - Exact commit SHAs and source fingerprints are recorded as test evidence only.
- **GU-2d. Required-API availability and failure reporting** (owner policy 2026-10-01).
  - A feature is available when its version floor is met and each Hermes internal it reaches is present, has the required parameter names (a `**kwargs` catch-all never satisfies a name such as `paused`), and resolves, with every wrapper layer, inside the Hermes tree or the standard library (not `site-packages`, `dist-packages` or the Hermes home's `plugins` directory). Probes import and inspect; they never call.
  - A missing core read dependency closes read, and with it every other feature, which uses the same authorization and profile primitives. Otherwise a failure of one feature's own probe table closes that feature; a genuinely absent shared API also closes each other feature whose own table requires it. Session browsing's own absence closes only the session routes (404).
  - Availability is computed once when the listener opens. Permissions, explicit host settings, instance identity, profile routing, scoped credentials, payload bounds and idempotency are unchanged and are checked as before. A genuinely absent implementation is never advertised as usable.
  - A compatibility warning follows a real feature failure only, never a merely unlisted version. A failed probe states the fixed reason and does not claim the version is bad; a "not one of HMP's tested samples" note appears only after a failure and only when no tested sample matches. `hermes hmp compat --issue-draft` prints a user-reviewed GitHub issue draft limited to the Hermes version and its source, the commit SHA when present, the HMP version, the OS family and Python `major.minor`, and the failed feature, reason and HMP's own dependency labels. Nothing is submitted, no network, `gh` or browser is used, and no profile, device, chat, path, host, key, config, content, log or exception text can appear. `--feature` with `--failure-code` records a failure the operator saw (for an upstream failure no static probe can see); it is labelled as operator-reported, grants nothing, and accepts only fixed error codes that match the feature. Permission and routing codes are explained as such and never drafted.
  - **Members (spec 034).** The eligibility set is `read`, `session_browsing`, `send`, `jobs`, `model`, `approvals` and `phone_chat`. `approvals` (Bot Chat approvals) and `phone_chat` (Phone chat sends and approval or clarify answers, §7b) both require read and send and the send floor (0.21.5 / 2026.9.24). `approvals` has no dependency table of its own; `phone_chat` has the table in §7b. A consequence of read or send being unavailable is reported as `requires_read` or `requires_send`, not as a failure of the member, and drafts nothing. `--issue-draft --feature approvals|phone_chat` accepts `write_gate_closed` and `api_server_unavailable` as operator-reported codes; a draft for these members may include the neutral session-stream hook fact (§7b).
  - **Media member (spec 011, M2 source-reviewed; delivery unimplemented).** `local_media` (§7e) is added to the eligibility set, amending spec 013's "no media member" constraint. It requires `read` available but not `send` or `session_browsing`; floor `0.21.5` / `2026.9.24` (inherited from send); probe rows `SessionDB.get_session`, `SessionDB.get_session_by_title` and `SessionDB.get_compression_lineage`, each requiring the existing signature discipline with two positional parameters (self plus the argument HMP passes). Read unavailable reports `requires_read`. A failure of the media table closes only media; a truly absent shared API can independently close siblings that also require it. Compat prints `available` or `unavailable (<fixed reason>)` for probe eligibility only; it does not read the host flag or print a `disabled` state. Listener binding is independently source-reviewed; descriptor emission, fetching and delivery acceptance remain unfinished gates. `--issue-draft --feature local_media` accepts only `media_unavailable` as an operator-declared owner-device, flag-on failure; this offline command cannot attest that declaration. `not_found`, `rate_limited`, `forbidden` and other permission or routing codes get their own reason and no draft. No path, ref, digest, profile or device id can appear.
  - No wire code or field is added.
- **GU-3. Symbol detection never advertises a guarantee.**
  - Detecting `defer_policy`, `AdmissionPrecondition` and similar symbols MAY be used only as a cross-check.
  - If a symbol is absent while the capability map claims the capability, the flag is `false` and HMP logs the inconsistency.
  - [diverges: the spike derives the four guarantee flags from the capability map only (`7033314`). But approval answering is still gated structurally on `detect_p1()`, not on `approval_request_id` (spike `CONTRACT_CONFORMANCE.md` row 6.1d).]
- **GU-4. Write gate**.
  - `write_gate.state` is `open` iff `no_defer` and `atomic_anchor` are both `true`.
  - While it is `closed`, `POST …/messages` returns `503 guarantees_unavailable` **without handing anything to Hermes**. Otherwise a first submission could be deferred and executed later against a changed conversation (FZ-R-9; S4/S16 baseline negative evidence).
  - `reason` is `guarantees_unavailable`: the capability map is absent, or `defer_policy_reject` or `admission_precondition` is below its floor.
  - **Consequence:** until upstream Hermes ships the capability contract, only the reviewed experimental build satisfies GU-2. On **stock Hermes, HMP is read-only.**
  - Reads, the live tail and stop remain available. Approvals follow `approval_request_id`, and clarify follows its own gate (INT-4).
  - **Hand-offs still allowed while the gate is closed** (DR-13). These are **permanent, deliberate exceptions**. Both are non-message control events, never user text:
    - the `/stop` control event (INT-5). Stopping must always be possible.
    - the inert authorization trigger that `POST …/authorize` sends (PR6-1). Pairing authorization must work on any build, including stock Hermes. The trigger hands no user message to Hermes, and Hermes's code reply is never relayed. Gating it would break pairing bootstrap on non-guaranteed builds.
  - No other route may hand anything to Hermes while the gate is closed.
  - **GU-4b. Phone chat (v1.3, §7b, OD-F16).** A named, narrower exception than opening SUB-1:
    `POST /hmp/v1/bots/{p}/phone/messages` may hand **that request's user text** to Hermes while
    GU-4's `"open"` state is false, and only when the same gate as DS-2(b) is open (the
    `direct_send` flag is true, send is available, and `phone_chat` is available, §7b). Flag off,
    or either unavailable: the route returns `503 write_gate_closed` and does not call
    `handle_message`.
    The route does not report `guarantee_level:"guarded"` and does not take `expected_head`. The
    inert authorize trigger remains the only hand-off while the user is not yet authorized.
  - **Accepted residual (RV-7).** The authorize trigger has a narrow race. HMP sends the fixed inert text only after reading `PENDING_OPERATOR`. If the operator's grant lands between that read and the hand-off, Hermes processes the fixed text as an ordinary turn, and on a build without P2 it could be queued. This is accepted: the text is constant, carries no user content and requests no action.
  - **GU-4a. `"open_guarded"` (v1.2, amendment F2; DS-2(b)).** A third `write_gate.state`, scoped
    exclusively to `POST /hmp/v1/bots/{p}/chat/messages` (§7a). It substitutes an HMP-engineered
    guard (DS-4) for the Hermes-side admission guarantees `"open"` requires, and is never returned
    together with `"open"` for the same request (mutually exclusive by construction — a build that
    ever reaches genuine `"open"` uses that path, not this one). A client that does not recognize
    `"open_guarded"` treats it as `"closed"` (V-4's safe default): it never assumes the send
    succeeded merely because the state string is unfamiliar. `"open_guarded"` never applies to the
    original `SUB-1` route (§7) — that route's gate stays exactly GU-4's original two-flag
    derivation, unaffected by this amendment.
    For the Bot Chat route, the host `direct_send` switch and the target profile's keyed
    loopback endpoint remain mandatory even when GU-4's full guarantees are present (DS-2).
- **GU-5. Where guarantees are carried.**
  - `guarantees` and `write_gate` are carried by `/ready` and `GET /bots` [diverges: `/ready` lacks `write_gate`; `GET /bots` carries neither].
  - `guarantees` is also carried at the top level of a `503 guarantees_unavailable` body.
  - Successful submit responses (`200`, `202`) do not carry `guarantees`. A write only succeeds when the write guarantees held, so the field would be redundant there. (This narrows rc2's first draft, following the SPIKE-FIX-5 conformance finding for row 6.1b.)
  - The client uses the latest value it has read.
  - A client with RO-1's optional per-bot `send_gate` uses it for the selected Bot Chat instead
    of the instance-wide fallback. Both are status hints; DS-2 is rechecked on POST.
- **GU-6. Reduced-guarantee UI.**
  - When the selected bot's send gate is `closed`, the UI MUST show that this bot cannot accept
    messages from mobile now, and its composer is read-only. An older client uses the conservative
    instance-wide `write_gate` fallback.
  - When `approval_request_id` is `false`, approvals HMP cannot bind to a stored `request_id` are
    read-only ("answer on another Hermes surface"). v1.3 (§7b) answers a prompt only when HMP
    itself holds that id. The capability flag does not gate the §7b routes.
  - When `confirmed_settle` is `false`, the UI never shows "stopped" (INT-6).
  - The copy is `UX_CONTRACT_GAP` UX-6.

## 9. Live tail and turn lifecycle (ADR-0005)

- **EV-1. Endpoint.** `GET /hmp/v1/bots/{p}/conversations/default/events` is SSE.
  - It is authenticated by header, with an optional `Last-Event-ID: <epoch>.<seq>`.
  - Frames are `id: <epoch>.<seq>`, `event: <type>`, `data: <json>`. `heartbeat` and terminal frames carry no `id`.
- **EV-2. Resume** works only within the same `epoch` and ring. Otherwise the **first** frame is `event: reset {reason}` and the client refetches the snapshot. There is never silent loss.

  | `reason` | Trigger |
  |---|---|
  | `epoch_changed` | HMP process restart |
  | `gap` | `seq` beyond the known range |
  | `ring_overflow` | resume point evicted from the ring |
  | `lineage_changed` | the conversation's session lineage tip changed to a new session id: compaction with session rotation, or continuation |
  | `history_rewritten` | in-place compaction rewrote the conversation's row ids (RO-8) [ahead] |
  | `session_replaced` | as in RO-6 [diverges: see RO-6 on detection across an HMP restart] |

  A `reset` for `lineage_changed` or `session_replaced` MAY also arrive mid-stream. The client then discards its partial state and refetches.
- **EV-3. Fan-out and authorization.**
  - A stream delivers only events of conversations owned by the authenticated user.
  - Every outbound frame carrying bot content (text, notices, approval and clarify events and their settled or retired counterparts) is checked against the owner's **live** per-bot authorization before it is published.
- **EV-4. Turn lifecycle** (E-PDR-1).
  - For an HMP-submitted turn, `turn.started {"cause":"message"}` is published on admission. It precedes every `message.update` of that turn.
  - `turn.started` carries only `cause` in v1.0. rc1's `live_turn_ref` is withdrawn: turns in one session are serialized by Hermes, so no correlation id is needed. A later 1.x revision may add one.
  - A refused submit produces no `turn.started` (SUB-6).
  - Turns with other causes (`auto_resume`, `internal`) get `turn.started {cause}` and settlement on a **best-effort** basis. They are correlated by session key, and clients MUST tolerate their absence.
  - Text produced outside an admitted turn is framed as `notice`, never as turn content.
- **EV-4b. No phantom turns** [ahead] (RV-2). Controller decision: option (b).
  - HMP **always forwards `/stop`** to Hermes, whatever it believes the turn state is (INT-5). A swallowed stop, where the user believes the bot stopped while Hermes keeps running, is never acceptable.
  - Hermes's reply to a command that starts no agent turn (for example `/stop` on an idle session) is framed as `notice`. It never produces a `turn.started`, and it is never turn content.
  - **HMP MUST NOT open a turn it cannot settle.** Every `turn.started` HMP publishes is closed by `turn.settled` (with P4) or `turn.ended` (without P4, or when processing completes without an agent settle).
  - **How HMP tells a command reply from an agent turn:**
    - For HMP's **own** forwarded control events, HMP's own message id (`hmp:stop:*`) is a reliable signal. HMP never announces a turn for them.
    - For command replies HMP did not originate, **no reliable adapter-visible signal exists** at the reviewed build. HMP then announces a non-HMP turn only on a best-effort basis (EV-4), and it MUST still close any turn it announced.
    - The generic fix is upstream gap **P14**: an adapter-visible marker that distinguishes command responses from agent turns (`R0_FREEZE_REVIEW.md` §3).
  - _Rejected alternative (a):_ answering stop-when-idle locally without forwarding. It risks swallowing a real stop whenever HMP's turn-state observation is wrong.
- **EV-5. `message.update`** carries `{"live_id", "text":<cumulative>, "final":bool}`.
  - `final:true` means no further update will be sent for that `live_id`.
  - `final:false` means the text may still be superseded. A `live_id` whose last update was `final:false` is complete once its turn settles or ends.
  - Live ids are not durable. After settlement, the client reads durable rows through history.
- **EV-6. Settlement.**
  - With `confirmed_settle`: `turn.settled {"outcome":"completed"|"stopped"|"interrupted"|"failed", "confirmed":true}`.
    - rc1's `reason` field is withdrawn in v1.0.
    - P4 does supply an interrupt reason (`stop`/`new`/`evict`/`message`), and a 1.x revision may add it as an optional field.
  - Without it: `turn.ended {"outcome", "confirmed":false}`.
  - A client MUST NOT show "stopped" on `turn.ended`.
- **EV-7. Other event types.**

  | Event | Data | Notes |
  |---|---|---|
  | `notice` | `{"kind":"bot_notice", "text"}` | untrusted, live only, never persisted by HMP |
  | `approval.requested` | `{"request_id", "command", "description", "choices":[…]}` | only with `approval_request_id` |
  | `approval.unanswerable` | `{"text"}` | without `approval_request_id`: render read-only |
  | `approval.settled` | `{"request_id", "reason"}` | |
  | `clarify.requested` | `{"clarify_id", "question", "choices":[…], "multi_select":bool}` | |
  | `clarify.retired` | `{"clarify_id"}` | |
  | `tool.activity` | `{"name", "phase"}` | [ahead]: defined but never published by the spike |
  | `stop.requested` | `{"reason":"stop"}` | INT-5 |
  | `roster.changed` | `{"removed":[profile…], "reason"}` | RO-2 |
  | `reset` | `{"reason"}` | EV-2 |
  | `revoked` | `{"scope":"device"|"bot"|"instance"}` | terminal; PR7-5, PR7-6 |
  | `unauthenticated` | `{}` | terminal |
  | `heartbeat` | `{}` | every `HEARTBEAT_S` |

- **EV-8. Lifecycle on the client.** iOS treats backgrounding as connection loss. On every reconnect the client re-reads the roster (RO-2), then the snapshot or resumes with `Last-Event-ID`, then reconciles its pending records (CL-5).
- **EV-9. After de-authorization.** An admitted turn may keep running in Hermes after revocation or de-authorization (PR7-7). Its events are dropped by EV-3 and are never replayed to that user.

## 10. Interventions and stop (ADR-0006)

- **INT-1. Approval answer.** `POST …/approvals/{request_id} {"choice"}`.
  - `choice` MUST be one of the offered choices.
  - The request MUST be pending for this user's session.

  | Result | Response |
  |---|---|
  | resolved | `200 {"status":"resolved"}` |
  | stale | `409 stale` |
  | foreign or unknown id | `404 not_found` |
  | choice not offered | `409 invalid_choice` |
  | no `approval_request_id` | `501 unsupported` |

- **INT-2. Approval rules.** HMP never uses `resolve_all` and never resolves without an id. The UI shows success only after `approval.settled` or subsequent activity.
- **INT-3. Clarify answer.** `POST …/clarify/{clarify_id} {"response"}`.
  - The server verifies that the id is indexed under this user's session.

  | Result | Response |
  |---|---|
  | resolved | `200 {"status":"resolved"}` |
  | stale | `409 stale` |
  | foreign or unknown id | `404 not_found` |

- **INT-4. Clarify is feature-gated, except Phone chat (v1.3, AP-9).** The historical gate stands
  for every surface except the optional Phone chat: the ownership check must not read
  `tools.clarify_gateway`'s private index, and `resolve_gateway_clarify` is not session-scoped
  (E-GAP-20). Phone chat answers only an id HMP stored for that `user_id` (AP-2, AP-9). That is
  the ownership check this clause asked for, done outside the private index. Bot Chat (the session
  stream) still has no clarify card. A clarify HMP cannot bind stays read-only.
- **INT-5. Stop.** `POST …/stop` **always** forwards Hermes's real `/stop`, whatever HMP's observed turn state, and returns `202 {"state":"forwarded"}`. The reply to an idle stop is framed as `notice` (EV-4b).
  - Stop is allowed while the write gate is closed.
  - **`stop.requested` is published only when all three hold:**
    - `confirmed_settle` holds;
    - HMP observes the turn as running when the interrupt lands;
    - Hermes reports the interrupt with reason `stop`.

    (Implemented in the spike at `89833d9` and `f073763`.)
- **INT-6. Stop display.**
  - Without `confirmed_settle`, no `stop.requested` is emitted. The client shows a local "stop sent" state after the `202`, and never shows "stopped".
  - "Stopped" is shown only on `turn.settled {outcome:"stopped"}`.
  - Killing the app never implies that a turn stopped.

## 11. Cross-surface continuity (OD-3) — v1 scope

- **CON-1. HMP sessions are ordinary Hermes sessions.** They are listed by `hermes sessions list` and are resumable from the CLI (S10). Desktop visibility is `EVIDENCE_GAP`.
- **CON-2. CLI resume ends the mobile route.**
  - A CLI `--resume` of an HMP session stamps `cli_close`.
  - The next HMP submit opens a fresh session, and the old route is pruned at the next gateway restart (S10 round 4).
  - The client experiences this as `session_replaced` (RO-6, EV-2). The UX is `UX_CONTRACT_GAP` UX-5.
- **CON-3. No import in v1.**
  - v1 mobile shows **no** Desktop-, CLI- or Bot Chat-originated conversation.
  - Importing or attaching one needs upstream P7 (per-turn resolution by canonical identity without an origin rewrite) plus an ownership model (E-GAP-8).
  - The only rebind available today rewrites a session's origin and owner (S10 `switch_session` experiment). HMP MUST NOT use it.
- **CON-4. This is a gap, not a narrowing of OD-3.** OD-3 still requires continuity wherever Hermes permits it. The effect on delivery scope is recorded in `R0_FREEZE_REVIEW.md` §8 for owner acceptance.

## 12. Hermes internals used (stability gaps; FZ-R-15)

**Optional PN-OPS diagnostics (spec 014 T026).** The read-only `push status` command uses
`gateway.config_loader.merge_platform_sections`, `hermes_cli.config._expand_env_vars`,
`._deep_merge`, `._normalize_root_model_keys`, `hermes_cli.managed_scope.get_managed_dir`, and
`utils.fast_safe_load` through the bridge. These pure primitives resolve host push settings after
native CLI bootstrap; they are not a global read/send dependency or an exact-build admission
list. Missing primitives or malformed input produce only `config_unavailable` for diagnostics.
HMP requests a supported read-only settings projection from Hermes so these optional private
configuration dependencies can be removed. The command never calls config recovery, plugin
discovery/hooks, or loader environment bridging. See [push diagnostics](../../../docs/PUSH_STATUS.md).

The bridge module uses these undocumented Hermes internals. Each is a `HERMES_API_GAP` to be replaced by a supported API. Enumerated from `hermes_bridge.py` @ `5fd3d5c`.

| Internal | Used for | Gap |
|---|---|---|
| `adapter.gateway_runner` (runner handle) | every runner call below | E-GAP-14 |
| `runner.served_profile_names()` | roster, served set | E-GAP-14 |
| `runner._routed_profile_home(profile)` | profile-scoped reads, allow-all canary | E-GAP-14/22/25 |
| `runner._is_user_authorized_for_source(source)` | per-bot authorization query | E-GAP-22/25 |
| `runner._authorization_home_for_source(source)` | evidence only | E-GAP-22 |
| `gateway.run._profile_runtime_scope`, and its async twin | reads in profile scope | E-GAP-14 |
| `hermes_state_registry.acquire(<home>/state.db)` → `SessionDB` reads (`get_compression_chain`, message reads, `platform_message_id` lookup, resume-tip resolution) | head, history, snapshot, lookup | E-GAP-6/7 |
| `SessionDB.list_sessions_rich`, `SessionDB.get_session` (v1.1, amendment A1) | SES-1 session list, SES-2 `session_ref` resolution; `get_session` is also a send dependency (compression-lineage walk when resolving a Bot Chat), so its absence closes both session browsing and send | E-GAP-6/7 |
| `hermes_cli.active_sessions.active_session_registry_snapshot` (v1.2, amendment F2) | DS-4(3) liveness/lease-registry guard | E-GAP-6/7 family; public and exported, used by three independent Hermes surfaces (`cli.py`, `tui_gateway`, `gateway/run_busy.py`) for the same kind of liveness check, but outside the documented plugin contract |
| `tools.bot_live_delivery.find_canonical_owner` (v1.2, amendment F2) | DS-4(2) Bot Chat resolution (same primitive SES-1/OD-F11 already relies on) | E-GAP-6/7 family |
| `adapter._session_store.lookup_by_session_key` | the session resolved at submit | E-GAP-6 |
| `gateway.session.build_session_key` | session correlation | E-GAP-6 |
| `tools.approval.list_gateway_approvals` / `resolve_gateway_approval(request_id=)` | approvals. v1.3 (AP-4, AP-6) calls both with the stored session key and `request_id=`; `resolve_all` is never passed. Probed by the `phone_chat` member only (§7b); not a read or send dependency | E-GAP-9 |
| `tools.approval_context._get_approval_timeout` (v1.3) | approval `expires_at` display hint (AP-3). `tools/approval_context.py`. `phone_chat` probe member | E-GAP-9 |
| `tools.clarify_gateway.resolve_gateway_clarify` / `mark_awaiting_text` / `get_clarify_timeout` (v1.3) | Phone-chat clarify answer, Other, and `expires_at` (AP-4, AP-9). `tools/clarify_gateway.py`. `phone_chat` probe members. HMP does not read `_session_index` or `_entries` | E-GAP-9/20 |
| `tools.clarify_gateway._session_index`, `._entries` | named here as the private index HMP does **not** read (INT-4, AP-9). Not a bridge dependency | E-GAP-9/20 |
| `gateway.platforms._shared.get_scoped_secret`, `platform_gate_env` (private module) | env allowlist detection | E-GAP-31 |
| `gateway.config.load_gateway_config`, `Platform` | platform `extra` settings | E-GAP-14 |
| `gateway.platforms.event.MessageEvent`, `AdmissionPrecondition` | submit event construction | P2/P3 API |
| `hermes_constants.get_default_hermes_root()` | instance-key anchor | documented (PLUGIN) |

**Plugin API used outside the bridge** (controller ruling, 2026-09-25). `adapter.py` imports exactly `gateway.platforms.base.BasePlatformAdapter`, `SendResult` and `gateway.config.Platform`, and `identity.py` imports exactly `hermes_constants.get_default_hermes_root` (the instance-key anchor, needed on every build because `/ready` must serve the `iid`). These are the documented platform-plugin API, not read internals, and they are the only Hermes imports allowed outside the bridge; they (and their transitive imports) load on every build, including unsupported ones. `Platform` is also a bridge dependency (above). `compat.py` locates the Hermes source root without importing it and reads the version from files; only for a build at or above the read floor (or of unknown version) does it run a dependency probe (import and signature inspection, no calls). A build below the minimum version never has a Hermes internal imported by HMP.

**GAP-1.** HMP MUST refuse writes unless the capability contract establishes both write guarantees (GU-2, GU-4). When a bridge dependency HMP needs for **reads** is missing, HMP MUST refuse every route except `/ready` with ERR-2a and make no bridge call (editorial alignment with ERR-2a, 2026-09-25).

**GAP-2 (v1.2, amendment F2, §7a; v1.3 adds the stream and the approval POST; spec 034).**
`api_server`'s `POST /api/sessions/{id}/chat` route and `GET /v1/capabilities`'s `session_chat` flag
are a **product HTTP contract**, not a Python internal HMP imports — HMP never imports
`gateway/platforms/api_server.py`. v1.3 uses the same class of dependency for
`POST /api/sessions/{id}/chat/stream` (approval-owner sends only, AP-1) and
`POST /v1/runs/{run_id}/approval` (`run_approval_response`). There is no fallback from the stream
route to the sync route after a failure (AP-1). This is a structurally different kind of
dependency from every row in the table above: reached over loopback, with a credential
(`API_SERVER_KEY`) HMP does not own the lifecycle of, versioned by `api_server`'s own product
compatibility story rather than by anything `bridge_files` fingerprints. It is not added to
`bridge_files` for that reason (`tools/compat/bridge_files.py`); availability comes from the send
dependency probe (GU-2d) and the `approvals` member (§7b), and a failure of an HTTP route itself,
which no static probe can see, answers `api_server_unavailable` and can be reported with
`hermes hmp compat --issue-draft`. `direct_send_supported_builds.json`
(`server/hmp_plugin/direct_send_supported_builds.json`) records the tested samples as evidence only.
`GET /v1/capabilities` advertises `approval_events` statically on inspected builds, including
releases whose session stream has no approval notifier, so it is not an availability signal
(`HERMES_API_GAP`, not an HMP task).

## 13. Constants (tunable only by contract revision)

| Constant | Value | Notes |
|---|---|---|
| `OFFER_TTL_S` | 300 | server-fixed; ≤ 600 |
| `PAIRING_CONFIRM_WINDOW_S` | 600 | also the P4 re-issue window |
| `ACCESS_TTL_S` | 600 | the bearer exposure window (E-GAP-27) |
| `REFRESH_IDLE_TTL_S` | 2 592 000 (30 d) | |
| `REFRESH_ABSOLUTE_TTL_S` | 7 776 000 (90 d) | |
| `REFRESH_RETRY_GRACE_S` | 30 | |
| `CLOCK_SKEW_S` | 120 | |
| `WATCHDOG_INTERVAL_S` | 2 | streams close within 2× this (PR7-5) |
| `HEARTBEAT_S` | 15 | |
| `TAIL_RING` | 512 | events per conversation |
| `ADMISSION_WAIT_S` | 5 | after this, submit answers `202 submitted` |
| `ADMISSION_DEADLINE_S` | 30 | Hermes precondition `not_after` |
| `LOOKUP_SETTLE_MARGIN_S` | 30 | [ahead]; SUB-9 |
| `IDEMPOTENCY_RETENTION_S` | 86 400 (24 h) | after the last change; purge runs hourly |
| `CLIENT_RETRY_WINDOW_S` | 300 | initial value; validated in dogfood |
| `CLIENT_MAX_AUTO_ATTEMPTS` | 0 in revision 1.0 | CL-4 |
| `MAX_BODY_BYTES` / `MAX_HEADER_BYTES` | 8 192 / 8 192 | |
| `MAX_JSON_DEPTH` | 8 | |
| `MAX_STREAMS_PER_DEVICE` | 4 | |
| `RATE_PAIR_REQUEST_PER_MIN` | 10 per IP, 10 per offer | |
| `RATE_PAIR_COMPLETE_PER_MIN` | 60 per IP, 60 per `pairing_id` | |
| `RATE_TOKEN_PER_MIN` | 20 per IP, 20 per `device_id` | |
| `LIMITER_TABLE_MAX` | 4 096 | LRU bound |
| `OFFER_MAX_FAILURES` | 5 | |
| `SAS_MAX_MISMATCHES` | 3 | |
| `DEVICE_NAME_MAX_BYTES` | 64 | |
| Snapshot `limit` | default 50, max 500 | |
| History `limit` | default 100, max 1 000 | |
| `MEDIA_REF_TTL_S` (v1.6 draft) | 1 800 | §7e LM-9; new feature choice |
| `MEDIA_REFS_PER_DEVICE` / `MEDIA_REFS_TOTAL` (v1.6 draft) | 512 / 4 096 | LRU |
| `MEDIA_DESCRIPTORS_PER_RESPONSE` (v1.6 draft) | 128 | newest first |
| `MEDIA_FETCH_PER_MIN` (v1.6 draft) | 120 per device | |
| `MEDIA_PERMITS_PER_DEVICE` / `_PER_INSTANCE` (v1.6 draft) | 2 / 4 | instance permit is the buffer permit |
| `MEDIA_WORKERS` (v1.6 draft) | 4 | dedicated executor |
| `MEDIA_WORKER_WAIT_S` / `MEDIA_WRITE_DEADLINE_S` (v1.6 draft) | 20 (shared by both phases) / 30 (including EOF) | |
| `MEDIA_MAX_BYTES` (v1.6 draft) | 8 388 608 | |

## 14. Residuals this contract accepts explicitly

- **RES-1.** Bearer access tokens, not sender-constrained (E-GAP-27): an exposure window of `ACCESS_TTL_S`. Decision deferred, with a gate (`R0_FREEZE_REVIEW.md` §9).
- **RES-2.** No TLS exporter binding (E-GAP-28), under TR-7.
- **RES-3.** The operator boundary is the Hermes OS-user boundary (SEC-1).
- **RES-4.** Instance-wide env-allowlist grants under shared-gateway topology (E-GAP-31). They are disclosed through PR6-3 and PR3-3. This is recommended, and an owner decision at freeze (OD-F6).
- **RES-9.** A modified Hermes can advertise false capabilities (GU-2b). This is within the E-SI-15 boundary.
- **RES-10.** Row ids are not stable across in-place compaction. Until P13 exists, rewrite detection is heuristic (RO-8).
- **RES-11.** The authorize-trigger race (GU-4, RV-7).
- **RES-12.** Until P14 exists, HMP cannot reliably tell a Hermes command reply it did not originate from an agent turn (EV-4b).
- **RES-13.** Approval ownership and the legacy controls allowlist share one config list (spec 034, D8). A device in `owner_device_ids` with no recorded host controls decision also receives jobs and model controls (§7c, §7d). An explicit host denial still removes approval ownership. The coupling is recorded, not removed; the runbook asks the operator to record an explicit controls decision before listing a device, and `setup check` prints a read-only notice. No decision or allowlist entry is changed automatically.
- **RES-14.** A later Hermes that stops honoring `allow_gateway_control:false`, or that rebinds an approval helper without HMP noticing the rebinding before use, is not statically detectable (§7b, AP-10). The identity fence is not attestation.
- **RES-5.** Revocation does not stop a running turn (E-GAP-29; PR7-7).
- **RES-6.** Roster names are visible to every enrolled device (SEC-2).
- **RES-7.** `head_message_id` may include non-conversational rows until P6 exists (RO-7).
- **RES-8.** Continuity is limited to HMP-originated sessions until P7 exists (§11).
Residual identifiers below are scoped separately: media v1.6 (§7e) and approval push (§7f).

- **RES-13 (v1.6 draft).** §7e makes no atomic snapshot guarantee; a grant or tip change after the last native check and before response `prepare` is not promised to refuse (LM-12, LM-20).

**Approval push residuals** (v1.x draft, §7f and [`HMP_PUSH_RELAY_V1.md`](HMP_PUSH_RELAY_V1.md); analysis IDs are those of `specs/014-approval-push-registration/analysis.md`). Accepted explicitly; none is closed by design. Public relay enrollment (R1) stays inactive until the owner accepts RES-13 to RES-16 and RES-23.

- **RES-13. Leaked-token spam** (A1). Anyone who obtains a phone's raw provider address can seal it under their own `iid` through an open relay and cause generic "Approval needed" alerts on that phone. The alert carries no authority. The spam is bounded by the per-`(destination, iid)` and per-destination relay caps, and open enrollment is inactive; the owner relay (R2) runs an `iid` allowlist.
- **RES-14. Sybil suppression of real alerts** (A14). The per-`(destination, iid)` cap stops one `iid` from suppressing another host's alerts to the same phone, but under open enrollment `iid`s cost nothing, so at least `⌈destination ceiling / pair cap⌉` sybil `iid`s (2 at the frozen 60 and 30) holding a leaked address still exhaust the destination ceiling and suppress a real host's alerts to that phone. The destination ceiling is kept as the spam bound at the price of this suppression.
- **RES-15. Public global and verify exhaustion** (A17). In public (R1) mode unauthenticated traffic from many source addresses can exhaust the global verify budget, and sybil `iid`s sealing random addresses can exhaust the global hourly budget, because those requests pass the seal checks (the relay checks `app`, `env` and bindings, not whether an address is real). Either exhaustion denies all R1 alerts. Garbage addresses may also affect the relay's standing with a provider (`EVIDENCE_GAP`, not checked). R2 is not immune: the global verify budget is consumed before the signature and allowlist checks.
- **RES-16. Unrevocable seal until `not_after`** (A13). A host that holds a valid seal can use it until its `not_after` (at most 14 days). A phone that unpairs while its host is unreachable cannot withdraw it, and the OS keeps displaying that host's alerts until then. The alert carries no authority; a tap shows "unlinked". Android full alert opt-out can rotate the FCM registration; iOS has no equivalent guarantee.
- **RES-17. Best-effort delivery.** APNs is best effort: it may reorder, stores one notification per bundle ID and may coalesce for an offline device. FCM and the OS may defer or drop. Outcomes after an iOS app-switcher force-quit, an Android recents swipe or force stop, and before first unlock are not established and are measured only. User settings prevail (permission, Time Sensitive, Focus, channel importance, battery). A provider may deliver after the TTL, which is a hint and not Hermes's deadline. Alerts are never a complete inbox; prompts of other bots may have no alert of their own.
- **RES-18. Located but settled elsewhere** (A20; with spec 034's recorded gap that no settlement or expiry event exists). A `located` prompt may already be settled elsewhere and is discovered at answer (`409`). The resolver does not reconcile Phone rows, so `located` can name a Phone row that Hermes has withdrawn, including a withdrawn Phone row; the app's fresh read shows the truth. Visibility is evaluated now, so a row that was hidden earlier, settled authoritatively by Hermes and visible now may answer `not_pending`, which is a true statement.
- **RES-19. Lost idempotency history.** Once a retained row is purged or evicted, a replay of its `PUT` gets `409 stale`, its handle and any surviving hint resolve `404`, and late relay feedback is a no-op. Nonreuse past that point rests on the computational argument of PN-ISS-2.
- **RES-20. Replay after a consistent restore** (A19). After a consistent restore of the store and the binding that rolls `G` back, a byte-identical retry of a `PUT` whose acknowledgement was lost can pass CAS and return a fresh handle `R′`, never the lost `R`. The app never committed the lost handle and commits `R′`. The replay CAS guarantees of PN-REG-2 hold absent such a restore.
- **RES-21. `DELETE` write failure and the delayed `PUT`** (A12, and the race of A21). A `DELETE` whose store write fails answers `503 other` (not confirmed); the in-memory delete fence closes eligibility but does not survive a restart, so alerts may resume until a retry succeeds, a revocation happens or the seal's `not_after` passes. A `PUT` delayed in flight can land after capacity frees, after a no-generation `DELETE` was refused `push_capacity`; the app's pending delete intent then removes it. Background display cannot be suppressed by app code, so removal is never claimed before a `200`.
- **RES-22. Idle-slot eviction** (A22). Evicting an idle coalescing slot forgets its last send time and loosens the 10 s minimum interval once; counters are memory only and a restart resets them. The per-device hourly cap and the relay's per-`(destination, iid)` cap still bound the rate. Self-only effect.
- **RES-23. Relay linkability** (A6). The relay learns which `iid`s a provider address is registered with, and `C` is a stable per-(registration, bot) pseudonym visible to the relay, Apple and Google for the registration's lifetime. Disclosure belongs to the privacy declarations (owner choice O6, pending).
- **RES-24. Coverage** (A5). Push dispatches only for approval rows that the approval lane (spec 034) inserts: Bot Chat streams HMP started and HMP Phone chat. Approvals raised on Desktop, CLI, cron or other platforms are not covered. Cross-channel coverage is an open `EVIDENCE_GAP` (task T005), not an established Hermes API gap.
- **RES-25. Generation-row capacity** (A21). After 256 distinct non-REVOKED devices have written a registration, a new device remains capacity-blocked until the operator revokes some; registration expiry alone does not release a generation slot.
- **RES-26. Relay restart replay window** (P1). The relay's replay cache is memory only on a single replica, and no durable cache is added. After a relay restart, or a restore of the relay's process memory, a captured, signature-valid request that is still inside its skew window can be replayed until `ts + 120 s`, at most 240 s after it was made in relay-clock time. The relay's `last_now` (R-F1a, CLK-1) is memory only and is reset with the cache, so this residual stays. The relay's 240 s retention and at most 4,800 live nonces hold only under normal clock progress; clock stalls or backward steps can prolong retention and reach the 16,384 cap, which refuses `503` with no eviction (relay CLK-1). Within one relay lifetime a backward wall-clock step cannot reopen a purged nonce; a forward step can refuse valid requests until the clock catches up or the operator restarts the relay. The effect is a repeated generic alert, bounded by that window and by the hourly limits, and it carries no authority. Hourly counters also restart.
- **RES-27. Provider refusals do not retire a registration** (B6). After a provider attempt, every result other than acceptance or a definitive gone answer reaches HMP as `502 provider_unavailable`, including APNs `BadDeviceToken` and the topic, payload and permission refusals. HMP never retries it and never retires the registration on it, so a registration whose address the provider permanently refuses keeps costing one failed attempt per alert (bounded by the hourly rate) until the seal expires or the app re-registers. `401` (including an unknown `kid`) and `400` also change nothing. A refusal cannot be told apart from an ambiguous failure, and the response never carries provider text.
