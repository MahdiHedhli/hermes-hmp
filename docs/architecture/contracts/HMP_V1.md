# Hermes Mobile Protocol (HMP) v1 — Contract

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
| `write_gate_closed` (v1.2, DS-2(b)) | 503 | Bot Chat direct send lacks its owner switch, qualification, loopback configuration, or target profile key | yes (HMP did not hand off) | Keep the draft. Composer is read-only for this bot until its gate reopens. |
| `api_server_unavailable` (v1.2, DS-6) | 503 | direct send: the loopback call to `api_server` failed, timed out, or was refused (`401`) after the gate reported `"open_guarded"` | **no** (ambiguous — reconcile via DS-8) | Treat as UNCONFIRMED (CL-2); reconcile (DS-8), never resend under the same cmid. |
| `cron_unavailable` (v1.4, CR-1) | 503 | mobile cron: flag off, unqualified build, missing scoped loopback endpoint, or uncertain upstream result | — | Refresh jobs before acting again. Never automatically retry a create or edit. |
| `model_unavailable` (v1.5, MD-1) | 503 | mobile default model: flag off, unqualified build, missing scoped picker endpoint, or Hermes read/write failure | — | Reopen the model screen and check the current selection before another write. |
| `media_unavailable` (v1.6 draft, LM-3) | 503 | host-local image fetch: the caller is an owner device but the media gate is closed. Message: "image delivery is unavailable" | — | Show "Image unavailable". Do not retry automatically. |

- **ERR-2a. Read-compatibility refusal** (GU-2c; additive `other {why}` values, no contract revision; controller clarification, 2026-09-25).
  - `503 other {why:"hermes_build_unsupported"}` on every route except `/ready`, pairing routes included, when the running Hermes build's identity is not on the read-compatible builds list or cannot be determined.
  - `503 other {why:"hermes_read_dependency_missing"}` when a listed build lacks a Hermes internal the read bridge needs.
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
    when the host switch, configured qualification check, loopback configuration, or that profile's key is
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
  OD-F14/OD-F15); any configured qualification check passes; `api_server` resolves to a
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
section. Flag off, a failed direct-send dependency probe, or a `direct_send_supported_builds.json`
fingerprint that no longer matches the running Hermes tree: each route returns
`503 {"error":{"code":"write_gate_closed",…}}` and does not open a loopback stream, call
`handle_message`, or call `resolve_gateway_approval` / `resolve_gateway_clarify` /
`mark_awaiting_text`. Pairing is still required. The flag does not authorize a device by itself.

Auth on every route: bearer, explicit owner-device membership, the F3 rate limit, then the
per-bot gate (`require_bot_authorized`, ERR-3), then the write gate and the approval
qualification gate below. The rate limit is two separate per-device buckets keyed by `device_id`
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

**Independent approval qualification (additional gate).** AP-3, AP-4 and AP-6, the snapshot
`open_requests` field, the send-stream prompt binding and the producer hooks also require
the listener-bound qualifier `compat.approval_listener_qualifier` (its callback) to return exactly
`True`. The qualifier is bound to a process-level baseline (resolved root, ordered read and
approval file lists, read and approval fingerprints, git SHA) fixed by the first SUPPORTED
factory call in the gateway process (which may follow unsupported listener opens in the same
process; it cannot attest already-loaded Hermes module bytes, so a full gateway process restart
remains mandatory after any source or plugin change, and this is not process-start attestation), cross-checked against the read gate's identity and requiring
a matching startup entry. A reconnecting listener may open only on that same baseline; a first
call with an empty, malformed, missing or unlisted manifest closes the process until a **full
gateway process restart**, not merely a listener restart. `approval_build_qualified` and the
`hermes hmp compat` line are an informational check of the on-disk source, not admission. This
does not protect against in-process unload or reimport of the plugin, which resets the baseline;
after any Hermes, source or plugin change the gateway process must be restarted. This is required
IN ADDITION TO, never instead of, the supported/send-qualified build, the owner device, the
per-bot authorization and the `direct_send` flag. It reads a separate allowlist,
`approval_supported_builds.json`, independent of `direct_send_supported_builds.json`. The shipped
list is **empty**, so approvals are closed on every build, including a send-qualified one: AP-3,
AP-4 and AP-6 return `503 write_gate_closed` without an endpoint, resolver, listing or delivery
call; snapshot `open_requests` is omitted; closed producer hooks call no approval helper and
store no row. A false, raising or non-boolean result closes the gate. Passing a fixture matrix
does not add a build to the list. Ordinary guarded sends (§7a) do not depend on this gate and are
unaffected by it. `hermes hmp compat` reports the approval qualification on its own line.

- **AP-1. Bot Chat stream (amends DS-6).** The loopback body stays `{"message":"<text>"}`. The
  path is `{path_prefix}/api/sessions/{live_tip}/chat/stream`. A missing `session_chat_streaming`
  capability, a non-200, or a body that is not that route's SSE stream fails the send as
  `503 api_server_unavailable`. HMP does not open `POST …/chat` instead. The consumer is a task
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
  client never sends `session_key`, `run_id`, `chat_id` or `profile` in the answer body. A body
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
  | Hermes returns 0, `approval_not_pending`, `approval_not_active`, or `resolve_gateway_clarify` returns false | `409 stale`, `applied:false`. The row is marked expired. This call did not apply the choice |
  | Two in-flight answers for one id | one resolver, in arrival order, under a per-id lock. The second sees the stored outcome |
  | Unknown id, or an id stored for another `user_id` | `404 not_found`. No Hermes call |
  | Flag off | `503 write_gate_closed` |

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
  `desktop_held`, `awaiting_text`, and for phone send `submitted`, `unknown`, `replay`, `conflict`, `refused`)
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
  clarify module; the symbols below are direct-send bridge dependencies only.

## 7c. Mobile cron management (v1.4, draft)

This additive route family is disabled unless `gateway.platforms.hmp.extra.cron.enabled`
is explicitly true, this authenticated device holds the host's controls decision (an explicit
grant, or a legacy `owner_device_ids` entry when no decision exists; an explicit denial wins),
and the running Hermes build has an independently qualified cron fingerprint. A device also
needs the existing per-bot authorization for `{p}`. A failed gate returns `404 not_found`
for non-owner devices or `503 cron_unavailable` for a disabled/unqualified endpoint, before
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
is saved atomically with the job; both retain the same owner/device/bot/qualified-build gate.
The phone may select only local run history or its own bot's Bot Chat. It cannot name an
arbitrary delivery destination. HMP still creates jobs paused.
Phone clients must treat a transport failure after a write as an unknown outcome and
refresh before attempting another write. The host flag defaults off; release requires
fixture qualification and independent security review.

## 7d. Bot default model (v1.5, draft)

This additive route family is disabled unless `gateway.platforms.hmp.extra.model_management.enabled`
is explicitly true, this authenticated device holds the host's controls decision (as in §7c), the selected bot
passes the existing per-bot access check, and the running Hermes model writer is an exact
qualified build. Non-owner devices receive `404 not_found`; a disabled or unqualified
feature receives `503 model_unavailable`. These checks happen before a config read, model
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
The host flag defaults off, and the owner's live Hermes is not qualified by this draft.

## 7e. Host-local generated images (v1.6, draft; not implemented)

Additive under V-3. **Status: draft serving contract.** Reviewed inert components are recorded in
the task evidence below; no serving route, admitted manifest entry, process/device qualification
or release exists. The product manifest of supported builds is **empty**; this section never
claims that a complete build, serving platform or device is qualified. Design record and open gates:
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
  3. the process-qualified manifest has an entry for this exact build. The shipped manifest has
     `builds: []`; no entry exists until an actual qualification.

  Otherwise no `media` field is emitted and read response bytes are **identical** to those of a
  server without this section. The gate does not affect compat, roster, send or approvals and
  adds no upper version bound on the install. Approval gates are never waived by it.
- **LM-2. Qualification.** Requires the loaded/start baseline **and** fresh on-disk equality over a
  dedicated media file list and the exact native/HMP dependencies. The startup baseline is
  immutable across in-process reloads and Hermes homes: the first supported factory fixes it
  process-wide, and a different native root or plugin directory closes later listeners. Only a
  full OS process restart clears it. A startup closed state never reopens; a listener captured
  with a mismatch stays closed for its lifetime. A matching listener can close on later disk
  mismatch and reopen after a fresh restoration check. Disk and dependency
  work runs off the event loop on the shared default executor. A full approval run is not required
  for media reads. The S6 design details and retained loaded-code/source limitations are in
  [ROOT_DECISIONS](../../../specs/011-local-image-serving/ROOT_DECISIONS.md#s6-media-qualification-design-freeze-2026-10-01).
- **LM-3. Closed-gate responses.** A non-owner device gets `404 not_found` before the gate is
  consulted. An owner device with a closed gate gets `503 media_unavailable`, message "image
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
  per-fetch scan.

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
  6. gate closed: `503 media_unavailable`;
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
  codes), approval-owner flag (`404`), gate flag and registry existence/TTL (`404`), and the
  first-served digest compare-and-set under the registry lock (set if absent; if different, delete
  the entry and refuse `404`). A causal change between the phase-one recheck/return and the
  phase-two check refuses. **Residual (unavoidable, stated):** a grant or tip change after the last
  native check and before `prepare` is **not** promised to refuse, because no atomic native API
  exists. This contract makes **no atomic snapshot guarantee**. Bearer, owner, gate, TTL and CAS
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
  | Gate | owner device, gate closed | 503 | `media_unavailable` | none |
  | Ref/binding | bad grammar, unknown, expired, evicted, foreign device/user/instance/profile/kind | 404 | `not_found` | none |
  | Permits | device 2 or instance 4 exceeded | 429 | `rate_limited` | none |
  | Phase one | candidate invalid, eligibility or tip changed, file missing or unsafe, raster rejected, digest mismatch, worker error, 20 s shared wait | 404 | `not_found` | none; no oracle between causes |
  | Phase two | grant revoked or changed, eligibility or tip changed, phase-two error, shared 20 s wait | 404 | `not_found` | none; same body as phase one |
  | | no worker permit free (no queue, no retry) | 429 | `rate_limited` | none |
  | Final bearer | token expired, device revoked, wrong instance | 401 | `unauthenticated` / `revoked` / `wrong_instance` | none |
  | Final synchronous | owner flag, gate, TTL, entry or CAS no longer holds | 404 | `not_found` | none |
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
- **LM-19. Admission gates (open).** Before any manifest entry exists, and before any shipping or
  platform claim:
  - **E1 (lexical producer string):** the bounded exact-build fixture now passes for its stated
    producer and scratch layout, as recorded in [the task evidence](../../../specs/011-local-image-serving/tasks.md#e1-bounded-producer-evidence-2026-10-01).
    It compares the raw producer string lexically with the captured routed home plus
    `/cache/images/`, without path normalization. Other producer spellings remain uncharacterized;
    a mismatch refuses.
  - **Linux errno qualification (`PLATFORM_GAP`):** the bounded non-root tmpfs file-leaf run now
    passes, as recorded in [the scoped evidence](../../research/local-media-linux-leaf-evidence-2026-10-01.md).
    That closes only the leaf check on its stated platform. Native Linux serving and broader
    platform coverage remain unqualified; no full Linux support claim follows from it.
  - Independent security review of the exact candidate, owner-authorized qualification and device
    acceptance. `SECURITY_REVIEW_REQUIRED` for the handle, route, gate and process qualification.
- **LM-20. Residuals carried.** No atomic snapshot (including ABA on unrelated rows); change after
  the last native check and before `prepare` (LM-12); a coarse-timestamp torn buffer is left to the
  phone codec; out-of-tree image providers are not fingerprinted; same-account host code is not
  contained; deadlines and memory ceilings are provisional.

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
- **GU-2a. Supported builds (release gating).**
  - A Hermes build is **supported** only if it is listed in the HMP release test matrix. That matrix pins exact reviewed Hermes builds by commit SHA (`R0_FREEZE_REVIEW.md` §6).
  - The HMP release is tested against every listed build, and those tests include the capability-derived flags.
  - A build outside the matrix whose capability map meets the floors will still open the write gate at runtime. It is nevertheless **unsupported**, and the documentation says so.
- **GU-2b. Residual: false capability claims.**
  - A modified Hermes could advertise capabilities it does not implement.
  - Such code runs as the same OS user as Hermes, so this sits inside the E-SI-15 trust boundary (SEC-1). It is covered by the same owner acknowledgement.
  - HMP does not try to detect it.
- **GU-2c. Read-compatible builds** (`R0_OWNER_DECISIONS.md`, bounded amendment 1).
  - Read compatibility is a separate question from write qualification (GU-2a). "Works on any Hermes build" is replaced by an exact list of tested **read-compatible** Hermes builds, pinned by commit SHA, maintained separately from the write-supported release matrix.
  - HMP's read routes (roster, snapshot, history, and the live tail and stop where reachable) are exercised against each build on that list before the build is added.
  - A Hermes build outside the read-compatible list is not silently assumed to work. It yields an understandable compatibility state to the client — never a guessed call into an unlisted build's private API surface.
  - The list starts empty. F1 (`FIRST_FEATURE_PLAN.md`) populates its first entries.
  - Build identity is the exact Hermes git commit SHA when the install has git metadata; otherwise a deterministic SHA-256 fingerprint over the exact source files the read bridge depends on. The list records both identity kinds. An unidentifiable build is unsupported (controller clarification, 2026-09-25).
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
    `direct_send` flag is true, the direct-send dependency probe passes, and the build's
    `direct_send_supported_builds.json` fingerprint still matches). Flag off, a failed probe, or a
    stale fingerprint: the route returns `503 write_gate_closed` and does not call `handle_message`.
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
| `SessionDB.list_sessions_rich`, `SessionDB.get_session` (v1.1, amendment A1) | SES-1 session list, SES-2 `session_ref` resolution | E-GAP-6/7 |
| `hermes_cli.active_sessions.active_session_registry_snapshot` (v1.2, amendment F2) | DS-4(3) liveness/lease-registry guard | E-GAP-6/7 family; public and exported, used by three independent Hermes surfaces (`cli.py`, `tui_gateway`, `gateway/run_busy.py`) for the same kind of liveness check, but outside the documented plugin contract |
| `tools.bot_live_delivery.find_canonical_owner` (v1.2, amendment F2) | DS-4(2) Bot Chat resolution (same primitive SES-1/OD-F11 already relies on) | E-GAP-6/7 family |
| `adapter._session_store.lookup_by_session_key` | the session resolved at submit | E-GAP-6 |
| `gateway.session.build_session_key` | session correlation | E-GAP-6 |
| `tools.approval.list_gateway_approvals` / `resolve_gateway_approval(request_id=)` | approvals. v1.3 (AP-4, AP-6) calls both with the stored session key and `request_id=`; `resolve_all` is never passed. `tools/approval.py` is a direct-send `bridge_files` entry, not a read one | E-GAP-9 |
| `tools.approval_context._get_approval_timeout` (v1.3) | approval `expires_at` display hint (AP-3). `tools/approval_context.py` | E-GAP-9 |
| `tools.clarify_gateway.resolve_gateway_clarify` / `mark_awaiting_text` / `get_clarify_timeout` (v1.3) | Phone-chat clarify answer, Other, and `expires_at` (AP-4, AP-9). `tools/clarify_gateway.py`. HMP does not read `_session_index` or `_entries` | E-GAP-9/20 |
| `tools.clarify_gateway._session_index`, `._entries` | named here as the private index HMP does **not** read (INT-4, AP-9). Not a bridge dependency | E-GAP-9/20 |
| `gateway.platforms._shared.get_scoped_secret`, `platform_gate_env` (private module) | env allowlist detection | E-GAP-31 |
| `gateway.config.load_gateway_config`, `Platform` | platform `extra` settings | E-GAP-14 |
| `gateway.platforms.event.MessageEvent`, `AdmissionPrecondition` | submit event construction | P2/P3 API |
| `hermes_constants.get_default_hermes_root()` | instance-key anchor | documented (PLUGIN) |

**Plugin API used outside the bridge** (controller ruling, 2026-09-25). `adapter.py` imports exactly `gateway.platforms.base.BasePlatformAdapter`, `SendResult` and `gateway.config.Platform`, and `identity.py` imports exactly `hermes_constants.get_default_hermes_root` (the instance-key anchor, needed on every build because `/ready` must serve the `iid`). These are the documented platform-plugin API, not read internals, and they are the only Hermes imports allowed outside the bridge; they (and their transitive imports) load on every build, including unsupported ones. `Platform` is also a bridge dependency (above). `compat.py` locates the Hermes source root without importing it; only for a build already on the GU-2c list does it run a dependency probe (import and signature inspection, no calls). An unlisted build never has a Hermes internal imported by HMP.

**GAP-1.** HMP MUST refuse writes unless the capability contract establishes both write guarantees (GU-2, GU-4). When a bridge dependency HMP needs for **reads** is missing, HMP MUST refuse every route except `/ready` with ERR-2a and make no bridge call (editorial alignment with ERR-2a, 2026-09-25).

**GAP-2 (v1.2, amendment F2, §7a; v1.3 adds the stream and the approval POST).** `api_server`'s
`POST /api/sessions/{id}/chat` route and `GET /v1/capabilities`'s `session_chat` flag are a
**product HTTP contract**, not a Python internal HMP imports — HMP never imports
`gateway/platforms/api_server.py`. v1.3 uses the same class of dependency for
`POST /api/sessions/{id}/chat/stream` (`session_chat_streaming`) and
`POST /v1/runs/{run_id}/approval` (`run_approval_response`). There is no fallback from the stream
route to the sync route (AP-1). This is a structurally different kind of dependency from every row
in the table above: reached over loopback, with a credential (`API_SERVER_KEY`) HMP does not own
the lifecycle of, versioned by `api_server`'s own product compatibility story rather than by
anything `bridge_files` fingerprints. It is not added to `bridge_files` for that reason
(`tools/compat/bridge_files.py`); it is qualified instead by the route probe and behavioral
confirmation in `direct_send_supported_builds.json`
(`server/hmp_plugin/direct_send_supported_builds.json`, starts empty, same discipline as
`write_supported_builds.json` under OD-F3). v1.3 adds `tools/approval.py`,
`tools/approval_context.py` and `tools/clarify_gateway.py` to that file's `bridge_files` only.
The previously qualified fingerprint no longer matches, so the direct-send gate stays closed
until a human requalifies the build. Reads do not import those three files, and
`read_compat_builds.json` does not list them.

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
- **RES-5.** Revocation does not stop a running turn (E-GAP-29; PR7-7).
- **RES-6.** Roster names are visible to every enrolled device (SEC-2).
- **RES-7.** `head_message_id` may include non-conversational rows until P6 exists (RO-7).
- **RES-8.** Continuity is limited to HMP-originated sessions until P7 exists (§11).
- **RES-13 (v1.6 draft).** §7e makes no atomic snapshot guarantee; a grant or tip change after the last native check and before response `prepare` is not promised to refuse (LM-12, LM-20).
