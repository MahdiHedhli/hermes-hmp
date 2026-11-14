# HMP Push Relay Contract v1 (draft)


**Current contract review status (2026-10-02):** The clock mechanism, optional pin grammar and N3–N6 were accepted by the prior focused review. The independent D1/D2/D3 sentence review accepted the capacity/retention qualifications, per-`(app, env)` APNs connections and seal-expiry wording. Root resolved its remaining editorial status finding M1 by dating the pre-review statements below. This is contract-text acceptance only. Source, causal tests/vectors, interoperability, provider/device/deployment/release and owner choices O1–O6 remain pending. No task checkbox or security mechanism changed.

| | |
|---|---|
| Status | **Draft contract text. Not implemented and not deployed. An independent scoped review of an earlier candidate of this text accepted it with conditions; this text adds the root review clarifications of 2026-10-02 (F1 to F7, §13.4). A later independent review of that clarified text accepted its other clauses and required two source gates, the relay clock source and the optional pin grammar. Those gates are now written as the root clock and pin delta of 2026-10-02 (R-F1a, R-PIN, N3 to N6, §13.5). Before its focused review, that delta was new, unreviewed text; the gates are written, not accepted. The independent focused sentence review of the delta is pending. The clock-count repair of 2026-10-02 followed a focused review of that delta: the review accepted the mechanism, the pins and N3 to N6, and required text repairs for the 4,800-nonce and 240 s qualification under clock steps (its finding D1) and for one APNs connection granularity per allowed `(app, env)` pair (D2), with editorial wording (D3). At that checkpoint, the repaired capacity and connection sentences awaited a focused check of those sentences only. That check has now accepted D1/D2/D3 as contract text; implementation and verification remain pending.** It transcribes the design frozen by root on 2026-10-02 (`specs/014-approval-push-registration/`: `spec.md` PN-REL, PN-SEAL; `plan.md` §6.5; `ROOT_DECISIONS.md` D1, D7–D10, D15–D18, D23, D27), **as amended by the root interoperability amendment of 2026-10-02 (B1–B6, P1–P3; §13.1, authoritative) and by the root review clarifications of 2026-10-02 (F1–F7; §13.4, authoritative)**. It states nothing about current runtime, scanner or provider behavior. |
| Scope | The wire contract between an HMP host (the client of the relay) and a push relay, and between a phone and the relay by way of the sealed provider address that the host carries but cannot open. The host-to-phone routes (`/push/registration`, `/push/hints/resolve`) are in [`HMP_V1.md`](HMP_V1.md) §7f. |
| Audience | The relay repository (a separate service, visibility an owner choice, O5) and the HMP and app implementers. |
| Owner choices | O1 to O6, provider keys and capabilities, HPKE key custody, DNS and the global relay budget are **pending**. This document names no real relay host, key, key ID, account, bundle ID, package, project or device. Every identifier in it is a placeholder. |
| Open items | The six former relay-contract `HMP_CONTRACT_GAP` items (labels GAP-1 to GAP-6, no longer present in this document and unrelated to the live `GAP-1` and `GAP-2` rules of `HMP_V1.md` §12) are addressed in contract text by decisions B1 to B6 (§13.1) and no longer block interoperability. What stays open is §13.2 (owner choices), §13.3 (not claimed) and the residuals of `HMP_V1.md` §14. HMP-specific known-answer vectors are implementation follow-up (§6.3 KAT-3). The amendment is root architecture direction for contract text only; independent review of the clarified text is still required. |

Normative keywords follow RFC 2119 and RFC 8174. `⟨Dn⟩` is the frozen decision of that number in `ROOT_DECISIONS.md`. The values are written out in §12.

**What the relay is.** A small service that accepts one signed HTTPS request per alert from an HMP host, opens a **sealed provider address** that only the relay can decrypt, checks that the seal is bound to that host, and sends a fixed, generic "Approval needed" alert through APNs (iOS) or FCM (Android). It keeps no database of provider addresses, users or instances. The host never sees a raw provider address.

**What an alert is.** A hint. It carries no command, bot, profile, session, URL, credential or answer, and it never authorizes anything (SECURITY.md "Notifications"; `HMP_V1.md` §7f).

---

## 1. Conventions and the TR primitive

- **PR-1.** Bodies are I-JSON (`HMP_V1.md` TR-9): well-formed UTF-8, no lone surrogates, top level an object. Protocol integers are JSON integers (TR-10); booleans and floats are rejected. Binary values are canonical base64url (TR-11): unpadded, RFC 4648 §5 alphabet, round-trip exact, decoded length exact where stated.
- **PR-2. Signature primitive (the generic TR primitive).** `HMP_V1.md` TR-13 applies unchanged: ECDSA P-256 with SHA-256 over the transcript bytes (not prehashed), DER-encoded, verifiers accept low-S and high-S, and

  `transcript(tag, f1…fn) = tag ‖ Σ (u32be(len fi) ‖ fi)`

  where integers are u64be, strings are UTF-8 and binary values are raw bytes. Digests follow TR-12: SHA-256 over the **raw decoded bytes**, never over the base64url text. Keys are P-256 with an uncompressed SEC1 point inside SPKI (TR-12); anything else is rejected.
- **PR-3.** Unknown request fields are ignored by the relay and carry no authority, because the signed transcript covers only the named fields (`HMP_V1.md` V-5). A required field that is absent, of the wrong type or outside its bound is `400 bad_request`.
- **PR-4. Identifiers.** `iid` is the 52-character, lowercase, unpadded RFC 4648 base32 of SHA-256 over the instance key's SPKI DER (`HMP_V1.md` §2). The relay computes it from the supplied `iid_spki` **before** it builds the signature transcript (§4 SIG-1); it never trusts a claimed value, and the wire carries no `iid` field.
- **PR-5. Identifier grammar (B4).** `kid`: ASCII, full match of `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`. `aud`: ASCII, full match of `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. Comparison is case-sensitive and exact. There are no URL semantics, no whitespace, no Unicode normalization and no trimming. Host configuration (`push.relay_kids`, `push.relay_audience`), HMP registration and status (`relay_kid`, `relay_kids`) and relay wire parsing all use these two grammars. The grammars define no real key, audience, endpoint or account.

## 2. Roles, configuration and trust

| Party | Holds | Never holds |
|---|---|---|
| Phone (app) | its provider address (raw, only inside a seal when it leaves the device); the closed `kid → relay public key` list shipped in the build | provider credentials |
| HMP host | the sealed blob `S` (opaque), the route handle `R`, instance key; host configuration below | the raw provider address, any provider credential, any relay private key |
| Relay | per-`kid` HPKE private keys, the APNs token-signing key, FCM credentials, its audience, app allowlist, optional `iid` allowlist, bounded in-memory rate and replay state | a database of tokens, users or instances |

- **CF-1. Host configuration (the only source of the relay destination).** `push.enabled` (default `false`), `push.relay_url` (no default, `⟨D3⟩`), `push.relay_kids` (a closed list of relay key IDs the phone may seal to), `push.relay_audience` (the relay identifier bound into every signature), and the optional setting `push.relay_spki_pins` (R-PIN, CF-1a). A missing, malformed or non-HTTPS required value means push is off; an explicitly empty `relay_kids` list, an entry or audience that does not match PR-5, or a configured `push.relay_spki_pins` that does not match CF-1a is `relay_unconfigured`. An omitted `push.relay_spki_pins` setting is allowed and means no optional pin; a configured malformed value is never discarded or replaced by a trust fallback.
- **CF-1a. Optional relay pins (R-PIN).** The one host setting is `push.relay_spki_pins`. **Omitted** (the key is absent from the host configuration) means no optional pin. A **configured** value must be an exact, nonempty list of 1 to 8 distinct entries. Each entry is the canonical unpadded base64url (RFC 4648 §5, no padding) of a SHA-256 digest over a DER `SubjectPublicKeyInfo`: exactly 43 ASCII characters that decode to 32 bytes and re-encode to the identical text. An explicit `None`, an empty list, a value that is not a list, a duplicate entry, or an entry that is not such a digest is malformed, and malformed means `relay_unconfigured` (HMP_V1.md §7f PN-AV). Omission and an explicit `None` or empty list are **distinct** states: the first is no pin, the others are malformed. The setting holds only public digests and no secret. There is no environment-variable or other fallback source for it, and none may be invented. **No host setting, URL, host name, kid or audience comes from the wire**, from a phone, from a sealed value or from a redirect.
- **CF-2. Relay configuration.** Its own audience; the app allowlist, whose entries are `(app, env)` pairs for APNs (a bundle ID together with `production` or `sandbox`) and packages for FCM (F5, §5 ENV-1; there is no global APNs mode); the `kid → HPKE private key` map; APNs team and key IDs; the FCM project; the optional `iid` allowlist; the limits of §9.
- **CF-3. Single replica (`⟨D27⟩`).** The relay runs as exactly one replica with in-memory replay and rate state. Several replicas would need shared replay and rate state, a new design and a new review. Hosting consequences are owner choice O2 (pending).
- **CF-4. Stages (owner choice O1, pending).** R2: an owner-operated relay with an `iid` allowlist (at most 8 entries, `⟨D23⟩`). R1: a project-operated public relay. **Open enrollment (R1) is not activated** until the owner explicitly accepts the recorded residuals (`HMP_V1.md` §14 RES-13 to RES-16 and RES-23). Staging uses one codebase and one contract; only the URL, audience, pins, kids and allowlist mode differ.

## 3. Endpoint and request (PN-REL-1, PN-REL-2)

- **REQ-1. Endpoint.** `POST {push.relay_url}/v1/push`, HTTPS only. The request body is at most 4 KiB.
- **REQ-2. Client transport rules (HMP).** `aiohttp.ClientSession(trust_env=False)` (no proxy environment), redirects refused, response read bounded to 1 KiB, and the platform trust store. Standard TLS certificate-chain validation against that trust store **and** host-name validation are always required, whether or not pins are configured. When `push.relay_spki_pins` is configured (CF-1a), the relay's **leaf certificate only** must also match one configured digest, computed over that certificate's DER `SubjectPublicKeyInfo`. A pin is an additional constraint and never a replacement trust anchor: it admits no self-signed certificate, no chain-certificate match and no bypass of chain or host-name validation. A pin mismatch is detected after the TLS handshake and before any HTTP request line, header or body byte is written. It is a pre-write TLS failure: it follows the same bounded RES-C retry rule as any other pre-write TLS failure, and no trust fallback exists. A kid that is not in the host list is refused at registration and skipped at dispatch. This is the one sanctioned outbound non-loopback client of HMP, a single module `push_relay.py`; see the constitution (VII) and `specs/001-connect-and-browse/contracts/server-modules.md`. It is a source-only proposal until implemented and reviewed.
- **REQ-3. Request body.**

  ```
  {"v": 1, "kind": "approval", "aud": <string>, "iid_spki": <b64u>, "ts": <int>,
   "nonce": <b64u>, "kid": <string>, "platform": "apns"|"fcm",
   "addr_kind": "apns_token"|"fcm_token"|"fcm_fid", "env"?: "production"|"sandbox",
   "sealed": <b64u>, "route": <b64u>, "hint": <b64u>, "collapse": <b64u>, "ttl_s": <int>}
  ```

  and the header `HMP-Relay-Signature: <b64u DER ECDSA signature>` (§4).

  | Field | Meaning and bound |
  |---|---|
  | `v` | JSON integer `1` |
  | `kind` | the string `"approval"`; no other kind exists |
  | `aud` | **Audience.** Exactly the relay's own configured audience, copied by the host from `push.relay_audience`. Signed (§4). It stops a request signed for one relay (for example the owner relay) from being replayed to another relay that shares kids. Grammar: PR-5. A well-formed but different value is `401 unauthorized` |
  | `iid_spki` | canonical b64u of the instance key's SPKI DER (91 bytes, P-256, uncompressed point, TR-11/12). The relay derives `iid` from it, then verifies the signature under it |
  | `ts` | nonnegative JSON integer below 2^53, Unix seconds. Out of the skew window is `401 unauthorized` (§5 step 6) |
  | `nonce` | canonical b64u, exactly 16 bytes (TR-11) |
  | `kid` | the relay key ID the seal was made to. Grammar: PR-5. An unknown `kid` is `401 unauthorized` |
  | `platform` | `apns` or `fcm` |
  | `addr_kind` | **Address kind.** `apns_token` for `apns`; `fcm_token` or `fcm_fid` for `fcm`. It is the declared kind of the sealed provider address, and it selects the FCM target field (§8). HMP enforces the pairing rule at registration. At the relay, a signed value that disagrees with the sealed value fails the binding check (§5 step 13) |
  | `env` | the APNs environment. **Required for `apns`, forbidden for `fcm`** (HMP enforces this at registration). The relay's checks and results are those of §5 steps 1 and 15, including that a signed `env` on an `fcm` request is `400 bad_request` |
  | `sealed` | the sealed address `S` (§6): canonical b64u of `enc ‖ ct`, **decoded length 82 to 1,105 bytes inclusive** (`⟨D10⟩`; the frozen 2,048-byte ceiling is not the check). Any other decoded length is `400 bad_request` |
  | `route` | the route handle `R`: canonical b64u, 43 characters (32 decoded bytes) |
  | `hint` | the hint ref `K`: canonical b64u, 43 characters (32 decoded bytes) |
  | `collapse` | the collapse identifier `C`: canonical b64u, 32 characters (24 decoded bytes) |
  | `ttl_s` | JSON integer in **60 to 900 inclusive**, seconds; the relay checks it independently, and any other value (or a non-integer) is `400 bad_request`. HMP computes it as `clamp(expiry_estimate − now + EXPIRY_GRACE_S, 60, 900)` or 330 when no estimate exists (`⟨D7⟩`) |

- **REQ-4. No host text.** The host contributes no visible text and no payload field other than those above. The relay's templates are fixed (§8).

## 4. Request signature (PN-REL-2)

- **SIG-1. Transcript.** `HMP1-PUSH-RELAY` is a **signature-only** tag. The signature is ECDSA P-256 under the **instance key** (decision `⟨D2⟩(a)`: reuse of the instance key with a distinct tag), carried in the header as the canonical b64u of a DER ECDSA signature (strict encoding, F4: the header is the canonical b64u of a minimal ASN.1 DER `SEQUENCE` of exactly two positive `INTEGER`s `r` and `s`, each in `1` to `n − 1` where `n` is the P-256 group order, with no trailing bytes. A non-minimal encoding, a zero, negative or out-of-range value, a wrong structure or trailing bytes is `400 bad_request`; a syntactically valid, in-range pair that does not verify is `401 unauthorized`. Both low-S and high-S verify, TR-13. The ECDSA verification itself uses a vetted implementation; there is no homemade verifier), over

  `transcript("HMP1-PUSH-RELAY", aud, iid, ts, nonce, kid, platform, addr_kind, env, SHA-256(S), R, K, C, ttl_s, kind)`

  in this field order:

  | # | Field | Type in the transcript |
  |---|---|---|
  | 1 | `aud` | string (UTF-8) |
  | 2 | `iid` | string (the computed 52-character base32, not `iid_spki`) |
  | 3 | `ts` | u64 |
  | 4 | `nonce` | raw 16 bytes |
  | 5 | `kid` | string |
  | 6 | `platform` | string |
  | 7 | `addr_kind` | string |
  | 8 | `env` | string; **an absent `env` is encoded as the empty string** (a zero-length field, still length-prefixed) |
  | 9 | `SHA-256(S)` | raw 32 bytes, over the **raw decoded** `sealed` bytes (TR-12) |
  | 10 | `R` (`route`) | raw 32 bytes (the decoded value of the 43-character wire string) |
  | 11 | `K` (`hint`) | raw 32 bytes (the decoded value of the 43-character wire string) |
  | 12 | `C` (`collapse`) | raw 24 bytes (the decoded value of the 32-character wire string) |
  | 13 | `ttl_s` | u64 |
  | 14 | `kind` | string |

  **Decision B1 (root, 2026-10-02).** Rows 10 to 12 enter the transcript as raw decoded bytes (32, 32 and 24), never as their base64url text. Their wire forms stay canonical b64u strings of 43, 43 and 32 characters. `SHA-256(S)` and `SHA-256(R)` are over raw decoded bytes (TR-12). The base TR framing `tag ‖ Σ (u32be(len fi) ‖ fi)` is unchanged, and rows 1 to 9, 13 and 14 keep the TR-13 and TR-11 defaults (integer → u64, string → UTF-8, `nonce` → raw 16, digest → raw SHA-256). The `ROUTE` and `COLLAPSE` HMAC transcripts follow the same rule: `iid`, `device_id` and `family_id` are UTF-8, `H` and `G` are u64, `salt` is raw 32; the `COLLAPSE` `scope` is the exact canonical profile locator as UTF-8 with no normalization, and `C` is the first 32 characters of `b64u(HMAC-SHA256(…))`, which decode to 24 bytes.
  - **Derive `iid` first.** The relay parses the supplied SPKI, derives `iid` from it (PR-4) and uses that derived value as row 2 when it builds the transcript. It never uses a wire `iid`, and it cannot defer this derivation until after verification: the transcript needs it. A key that fails parsing or curve validation is `400 bad_request` (§5 step 3).
  - **Vectors.** No HMP known-answer signature vector is included here. It must come from an independent generator and be reviewed (TR-14 practice) as implementation follow-up (§6.3 KAT-3). That includes vectors for the strict DER and range cases above (non-minimal, zero, negative, `n` and above, trailing bytes, both low-S and high-S valid); none is included here. Nothing in this section blocks that work.
- **SIG-2. Key separation (conditions for `⟨D2⟩(a)`).**
  - `HMP1-PUSH-RELAY` must not be a prefix of any existing transcript or hash-domain tag, nor the reverse; a prefix-freeness test runs over the full tag set (`HMP_V1.md` §7f PN-KEY).
  - It is signature-only. No phone verifier accepts it. The tags `HMP1-PUSH-ROUTE` and `HMP1-PUSH-COLLAPSE` are HMAC-only tags that never produce a signature.
  - HMP serves TLS 1.3 only (TR-1), so there is no TLS 1.2 signing oracle. TLS 1.3 CertificateVerify content starts with 64 bytes of 0x20 and cannot equal `HMP1-`. If TLS 1.2 is ever enabled, `⟨D2⟩` is revisited. `⟨D2⟩(b)` (a dedicated relay key) remains a valid alternative if root wants relay unlinkability from the TLS identity.
- **SIG-3. Effect of identity change.** Reusing the instance key means an identity rotation (`rotate-key`, clone or restore) changes `iid`, so every sealed address bound to the old `iid` fails the binding check (§5 step 12) rather than becoming usable by another host.

## 5. Relay verification order (PN-REL-3)

The relay performs these steps in order and stops at the first failure. **No provider is contacted before step 17.** Step 16 only checks and charges the hourly limits; it contacts no provider. Result codes are those of §7 and follow decision B6 (§13.1): malformed request, shape, SPKI, signature encoding, identifier or `ttl_s` is `400` before any provider work; a well-formed but invalid signature, a different audience, an out-of-window `ts`, an unknown `kid` or an allowlist miss is `401`; a seal that does not open or does not bind is `422`.

| Step | Check | Result on failure |
|---|---|---|
| 1 | Body size at most 4 KiB; I-JSON; required fields, types, shapes, identifier grammars (PR-5), canonical b64u and decoded lengths of §3 (`nonce` 16, `route` 32, `hint` 32, `collapse` 24, `sealed` 82 to 1,105, `iid_spki` a 91-byte P-256 SPKI structure); `ts` a nonnegative integer below 2^53; `ttl_s` an integer 60 to 900; the signature header canonical b64u of a strict minimal DER ECDSA structure (SIG-1: exactly two positive `INTEGER`s, each in `1` to `n − 1`, no trailing bytes); the `platform`, `addr_kind` and `env` combination (`env` required for `apns`, forbidden for `fcm`; `addr_kind` consistent with `platform`) | `400 bad_request` |
| 2 | **Pre-verification admission (§9 LIM-1).** The per-source limit and the global verify budget `⟨D17 verify⟩` (at most 20 signature checks in any rolling 1-second interval, no extra burst; rolling windows are measured on monotonic elapsed time, CLK-1) are checked together, atomically. Both are charged immediately, and only if both admit, **even if a later signature or seal check fails**. CPU is never charged later | `429 rate_limited` (provider not attempted; nothing charged) |
| 3 | Load the supplied `iid_spki` (91-byte P-256 uncompressed point, TR-12; a key that fails parsing or curve validation is `400`). Compute `iid := base32(SHA-256(SPKI DER))` from it. Build the §4 transcript with that derived `iid` and verify the signature under the supplied key | `400 bad_request` for a malformed key; `401 unauthorized` for a syntactically valid, in-range signature that does not verify |
| 4 | `aud` equals the relay's own audience (exact, PR-5) | `401 unauthorized` |
| 5 | No check. The `iid` derived at step 3 is the only identity later steps use | n/a |
| 6 | **Early skew screen.** `ts` within the window: `ts ≤ now + CLOCK_SKEW_S` and `now < ts + CLOCK_SKEW_S`, against a raw wall-clock `now` read for this screen, which is allowed because the screen only rejects. It rejects early; step 7 repeats both inequalities at the effective acceptance instant of CLK-1, and nothing relies on this raw `now` afterwards (F1, R-F1a, §5 VER-1) | `401 unauthorized` |
| 7 | **Atomic nonce check-and-reserve (F1).** Inside one atomic section the relay obtains one **effective acceptance instant** `now := max(raw_wall_now, last_now)` and sets `last_now := now` (R-F1a, CLK-1). It re-checks both inequalities of step 6 against `now` (`ts ≤ now + CLOCK_SKEW_S` and `now < ts + CLOCK_SKEW_S`), and then purges (`expiry ≤ now`), checks for a seen nonce, checks room and reserves, all with that same instant. A failed re-check refuses the request with no new nonce and no provider work. A seen nonce is refused. Otherwise, if the cache has room, the nonce is reserved in the same atomic step, until `ts + CLOCK_SKEW_S`, before any decrypt or provider work. Two concurrent identical requests cannot both pass. A reservation is **not** released early when a later check refuses the request | `401 unauthorized` (failed re-check); `409 replayed` (seen nonce) |
| 8 | If the replay cache is full (checked in the same atomic step as 7) | `503 unavailable` (provider not attempted; **no unexpired nonce is evicted**) |
| 9 | `kid` is known to the relay | `401 unauthorized` |
| 10 | The derived `iid` is allowed, when the relay runs an allowlist (`⟨D23⟩`) | `401 unauthorized` |
| 11 | HPKE: RFC 9180 §7.1.4 input and output validation of the key exchange (public-key deserialization and the DH output check), authenticate and open `S` with the relay private key for `kid` (§6), then validate the plaintext (exact member set, restricted JCS, §6.1) | `422 sealed_invalid` |
| 12 | Sealed `iid` equals the `iid` derived at step 3; sealed `app` is in the relay's app allowlist | `422 sealed_invalid` |
| 13 | Sealed `platform` and `addr_kind` equal the signed values and match each other | `422 sealed_invalid` |
| 14 | `not_after > now` and `not_after ≤ now + ⟨D9 max⟩` (14 days), where `now` is the **same effective acceptance instant** the request obtained at step 7 (CLK-1), never a later raw wall-clock reading | `422 sealed_invalid` |
| 15 | `env` and the allowlist pair (F5, ENV-1): for `apns`, the sealed `env` equals the signed `env` **and** the pair (sealed `app`, that `env`) is an allowed pair of the relay's allowlist; that pair's own provider connection is the one used. There is no global APNs mode and no environment fallback. For `fcm`, `env` is absent from the seal and only the package allowlist applies. (A signed `env` on an `fcm` request was already refused at step 1 as `400 bad_request`) | `422 sealed_invalid` |
| 16 | The four counters (per `iid`, per destination, per `(destination, iid)`, global `B`), each over a rolling 3,600-second window measured on monotonic elapsed time (§9 LIM-3, F6, CLK-1), are checked together, atomically, and charged only if **every** one admits (§9 LIM-1). No provider is contacted | `429 rate_limited` |
| 17 | One provider attempt (§8, §10). This is the first step at which a provider is contacted | per §7 |

- **VER-1. Replay window and nonce retention (P1, P2).** The window equals HMP `CLOCK_SKEW_S` (120 s, `⟨D18⟩`). A nonce is retained over the interval **`[receipt, ts + CLOCK_SKEW_S)`**, so under normal clock progress it lives at most 240 s (CLK-1, capacity bullet), and it is purged when its expiry is at or before `now` (`expiry ≤ now`). The boundary is enforced where the nonce is held (F1): step 7 obtains one effective acceptance instant `now` inside its atomic section (CLK-1), re-checks both skew inequalities and then purges, checks and reserves with that same instant, so a request that reaches a reservation was inside the window at that instant and its nonce is not purged at it. Because that instant never decreases within a replica lifetime (CLK-1), a backward step of the wall clock cannot reopen a nonce that was already purged. A request that passed the step 6 early screen before `ts + CLOCK_SKEW_S` but reaches step 7 after it is refused `401 unauthorized`, creates no new nonce and reaches no provider. Neither step relies on an instant captured earlier, in particular not one read before another worker purged the nonce. The global verify budget allows at most 20 checks in any rolling 1-second interval with no additional burst, so, under normal clock progress, at most 4,800 nonces are live. That is below the cache size of 16,384, so a full cache is a defensive path and not an expected one under normal clock progress. Clock stalls and backward steps can prolong retention and exceed 4,800 (CLK-1, capacity bullet). The nonce step follows signature, audience and the early skew screen in the §5 order, so only signature-verified requests reach it. A nonce reserved by a request that a later check refuses (unknown `kid`, allowlist miss, seal failure, hourly limit) stays reserved until its expiry.
- **VER-1a. Restart replay residual (recorded, not closed).** The replay cache and `last_now` are memory only on a single replica and no durable cache or durable clock is added. After a relay restart, or a restore of process memory to an earlier state, a captured, still-skew-valid, signature-valid request can be replayed until `ts + CLOCK_SKEW_S`, at most 240 s after it was made, in relay-clock time (a relay clock that runs behind real time lengthens that interval in real time). Nothing here claims that nonces persist or that a restart is immune. The hourly counters also restart. The effect is a repeated generic alert to the destination, bounded by the window, and it carries no authority (`HMP_V1.md` §14 RES-26).
- **CLK-1. Relay clock source and effective acceptance instant (R-F1a, root 2026-10-02; contract text accepted, source pending).** The relay keeps one in-memory value `last_now`, initialized at process start to the wall clock. Inside the single atomic nonce admission section of step 7, the relay computes `now := max(raw_wall_now, last_now)` and sets `last_now := now`. That `now` is the request's **effective acceptance instant**. The step 7 re-check of both skew bounds, the purge, the seen check, the capacity check and the reservation all use it, and step 14's seal-expiry checks reuse it unchanged. The early screen of step 6 may use the raw wall clock because it only rejects. The rolling windows of step 2 (the global verify budget of at most 20 checks in any rolling 1-second interval, and the per-source limit of 600 per rolling 3,600 seconds) and of step 16 (the four counters, 3,600 seconds) are measured on a monotonic clock as elapsed time, never on raw wall-clock readings that can step backwards. The per-source limit is a rolling 3,600-second window like the others and is not a fixed clock hour.
  - *Backward wall-clock steps.* Within one replica lifetime, `last_now` never decreases, so a backward step cannot reopen a purged nonce: a request is admitted only when `now < ts + CLOCK_SKEW_S`, and a nonce is purged only when its expiry is at or before `now`, so a purged nonce's request always fails the re-check with `401` and creates no reservation.
  - *Capacity and retention hold only under normal clock progress.* The 240 s retention and the bound of at most 4,800 live nonces are claimed only while the effective acceptance instant advances with normal clock progress. Retention and purge run on the effective instant, while admissions are paced on monotonic time. While `last_now` is ahead of `raw_wall_now` (a backward wall-clock step, a clock that ran ahead and was then corrected, or a forward jump), `now` stays at `last_now` and nothing is purged, so a nonce's retention in real time can exceed 240 s, the live count can exceed 4,800, and repeated clock stalls or steps can reach the 16,384 cap. A full cache refuses `503 unavailable` with no provider attempt, no eviction of an unexpired nonce, no early release and no new replay acceptance. This contract states no other clock progression, no new TTL and no release or reset of reservations. The arithmetic of any single step is illustrative, not a normative capacity and not an exact bound: beyond 4,800 the stated limits are only the hard 16,384 cap and its fail-closed refusal.
  - *Effective instant ahead of the raw clock (a forward step, or a backward correction of a clock that ran ahead).* While `last_now > raw_wall_now`, the raw and effective skew screens can refuse otherwise valid requests: a request with `ts + CLOCK_SKEW_S ≤ now` is refused `401 unauthorized` at step 7 (and the raw screen of step 6 can refuse with `401`), and step 14 may refuse a seal whose `not_after` is at or before the effective instant (for a request that passed step 7 that instant is below `ts + CLOCK_SKEW_S`) with `422 sealed_invalid`, until the raw wall clock catches up with `last_now` or the operator restarts the relay. These refusals are availability only. The relay performs no automatic restart and no automatic reset of `last_now` or of the nonce reservations. HMP does not retry `401` or `422` (RES-C) and retires no registration on `401` (RES-E). A step 14 `422` follows RES-E's existing rule and marks that registration `expired`, so the phone must seal afresh; no other registration state changes.
  - *Memory only.* `last_now` is not persisted. A cold restart or a restore of process memory resets it and the nonce cache together, which is the existing residual of VER-1a and RES-26, with its timestamp bound stated in relay-clock time. This contract claims no nonce persistence and no restart immunity.
  - *Tests.* Causal tests that step the clock backward after a purge and forward across `ts + CLOCK_SKEW_S`, with matching vectors, are required before relay source is accepted. Further causal tests are required and likewise pending: retained-capacity tests under repeated backward steps (the live count may exceed 4,800 and no exact bound is promised), and a full-cache test under repeated steps that refuses `503` and evicts nothing. The 4,800 assertion excludes every clock-step test. **They are pending: none exists, and none is claimed.**
- **VER-2. Where the relay cannot check.** The relay never sees the host's `seal_expires_at`, so it cannot compare it with the sealed `not_after`; it enforces only the bound of step 14.
- **ENV-1. APNs environment policy (F5).** The relay has no single global APNs mode. Its configuration lists allowed `(app, env)` pairs; it may allow sandbox and production pairs at once, each pair with its own provider connection (§8.1). For an `apns` request the signed `env` and the sealed `env` must equal each other and must equal the environment of the selected allowed pair; a request is never sent to a different environment, and there is no environment fallback. The `iid` allowlist check of step 10 stays `401 unauthorized`; the app and `(app, env)` pair checks are seal bindings (steps 12 and 15) and stay `422 sealed_invalid`. This contract configures no real account, key, bundle ID or environment, and decides nothing about APNs credential or signing-key provisioning (pending O3).
- **VER-3. Seal is bound, not revocable.** A host that holds a valid seal can use it until `not_after`. Revocation on the host side retires the registration and never reaches the relay; the unrevocable-seal residual is recorded (`HMP_V1.md` §14 RES-16).

## 6. Sealed provider address (PN-SEAL)

### 6.1 Plaintext (PN-SEAL-1)

The sealed plaintext is **RFC 8785 JSON Canonicalization Scheme (JCS)** output, encoded as UTF-8 without a byte-order mark, at most 1,024 bytes (`⟨D10⟩`), with exactly these members (decision B2):

```
{"v": 1, "iid": <iid>, "platform": "apns"|"fcm",
 "addr_kind": "apns_token"|"fcm_token"|"fcm_fid",
 "env": "production"|"sandbox",        // apns only; absent for fcm
 "app": <bundle ID or package>, "addr": <provider address>,
 "not_after": <int>, "n": <b64u, 16 bytes>}
```

- **Restricted JCS domain.** Member names are the fixed ASCII names above. Every value is a string except `v`, which is the integer `1`, and `not_after`, which is a nonnegative JSON integer below 2^53 (never a boolean, a float, or a lexeme with a fraction or an exponent). The relay rejects duplicate member names, extra or missing members, invalid Unicode and lone surrogates, and any plaintext whose bytes are not equal to the JCS reserialization of the validated object (RFC 8785 §3.2.1 whitespace, §3.2.2 primitive serialization and string escaping, §3.2.3 member sorting by UTF-16 code units, §3.2.4 UTF-8). No Unicode normalization is applied to any value.
- **Canonical member order.** For `apns`: `addr`, `addr_kind`, `app`, `env`, `iid`, `n`, `not_after`, `platform`, `v`. For `fcm` the same without `env`. An HMP-specific example or vector is not given here (KAT-3).
- `addr_kind` must match `platform`; the relay rejects a mismatch as `sealed_invalid`.
- `not_after` equals the host-visible `seal_expires_at` (`HMP_V1.md` §7f PN-REG-2). It is a Unix-seconds integer.
- `addr` is the raw provider address. **Make no assumption about its size beyond the plaintext bound**: Apple warns not to assume device-token size, and FCM identifiers vary.
- Besides the JCS rules above, the relay checks canonical b64u `n` (16 decoded bytes, TR-11), that `iid` is a 52-character `iid` string, and that `env` is `production` or `sandbox` for `apns` and absent for `fcm`. Any failure is `422 sealed_invalid`.

### 6.2 HPKE suite `⟨D1⟩` (PN-SEAL-2)

The seal is HPKE per RFC 9180, **base mode**, to the relay public key named by `kid`, using the single-shot `SealBase` / `OpenBase` API of RFC 9180 §6.1 with the `info` and `aad` below.

| Parameter | Value | Source |
|---|---|---|
| Mode | `mode_base` = `0x00` | RFC 9180 §5, Table 1 |
| KEM | `DHKEM(P-256, HKDF-SHA256)`, `kem_id` = `0x0010`; Nsecret 32, Nenc 65, Npk 65, Nsk 32 | RFC 9180 §7.1; IANA HPKE registry |
| KDF | `HKDF-SHA256`, `kdf_id` = `0x0001` | RFC 9180 §7.2; IANA HPKE registry |
| AEAD | `AES-128-GCM`, `aead_id` = `0x0001`; Nk 16, Nn 12, Nt 16 | RFC 9180 §7.3; IANA HPKE registry |
| `info` | the 16 ASCII bytes `HMP push seal v1` (no terminator) | frozen design PN-SEAL-2 |
| `aad` | the UTF-8 bytes of the `kid` string | frozen design PN-SEAL-2 |

- Relay public keys ship in the app build as a **closed `kid → public key` list**. There is no runtime key fetch (PN-SEAL-2).
- The relay keeps the private key of each `kid` only in its secret store (§10). Rotation: add a `kid` to new app builds and to host `relay_kids`; keep the old private key for `⟨D9 max⟩` plus a margin; then retire it. A compromised `kid` is removed from host lists, so new registrations refuse it and dispatch skips rows sealed to it.
- **Wire framing of `sealed` (decision B3).** `sealed = b64u(enc ‖ ct)`. `enc` is exactly 65 bytes (an uncompressed SEC1 P-256 point). `ct` is the AES-128-GCM output of RFC 9180 `SealBase`, **including** its 16-byte tag. There is no version, key or length prefix inside the blob. `kid` and the suite come only from the outer `kid` field and the closed, configured `kid → key` mapping; nothing is negotiated.
  - **Sizes.** A nonempty plaintext of 1 to 1,024 bytes gives a decoded `sealed` of 65 + 16 + 1 = 82 to 65 + 16 + 1,024 = 1,105 bytes inclusive, inside the frozen 2,048-byte ceiling (`⟨D10⟩`).
  - **HMP never opens a seal.** It checks only canonical b64u and the 82 to 1,105 byte bounds (`HMP_V1.md` §7f PN-REG-2). A seal of any other decoded length is `400 bad_request` at HMP and at the relay's shape check (§5 step 1).
  - **Relay.** It performs the RFC 9180 §7.1.4 validation of inputs and outputs, then authenticates and opens, then checks the exact schema and JCS form (§6.1). A malformed `enc` point, an authentication-tag failure, or a bad plaintext is `422 sealed_invalid`; an invalid decoded length is `400 bad_request` (it never reaches the opener).
  - **Implementation rules.** Use a vetted HPKE implementation; no homemade curve validation. A production sealer draws a fresh CSPRNG ephemeral key for every seal; a deterministic-ephemeral-key hook exists only to run the RFC 9180 vectors and never ships (§6.3 KAT-1).

### 6.3 Known-answer vectors for the D1 suite

The RFC 9180 official vectors for this exact suite are the conformance bar for the HPKE primitive on the relay **and** in the app (task T030, T043):

| Reference | Pinned value |
|---|---|
| RFC | RFC 9180, "Hybrid Public Key Encryption" (Informational, February 2022) |
| Section | Appendix A.3, "DHKEM(P-256, HKDF-SHA256), HKDF-SHA256, AES-128-GCM"; **A.3.1, Base Setup Information** (`mode` 0, `kem_id` 16, `kdf_id` 1, `aead_id` 1) |
| Machine-readable file | `https://github.com/cfrg/draft-irtf-cfrg-hpke/blob/5f503c564da00b0687b3de75f1dfbdfc4079ad31/test-vectors.json`, the URL the RFC itself cites, at its pinned commit |
| Entry selector | the entry with `mode` = 0, `kem_id` = 16, `kdf_id` = 1, `aead_id` = 1 |

- **KAT-1.** An implementation MUST reproduce every value of that entry that its API exposes: `pkEm` and `enc`, `shared_secret`, `key_schedule_context`, `secret`, `key`, `base_nonce`, `exporter_secret`, and for every listed encryption the `nonce` and `ct` for the given `pt` and `aad`, and every listed export. A deterministic-key test hook is test-only and never ships in a production build.
- **KAT-2. The bytes are not reproduced here.** This document gives the authoritative reference above, **not** a retyped copy of the hex values. A copy typed or generated by a tool that cannot be checked would be a fabricated vector. Whoever implements KAT-1 copies the vector from the pinned source and checks the file's hash into the implementation's test data at that time.
- **KAT-3.** HMP-specific vectors (our `info`, our `aad`, our plaintext, the signature transcript of §4, the JCS bytes of §6.1) are **not** included, and this document does not invent them. They need an independent generator and independent review (the TR-14 practice). They are implementation follow-up (tasks T025, T030, T043), **not blocked** by any open contract gap, and not a claim of this document.

## 7. Responses (PN-REL-4)

The response body is JSON `{"result": <code>}`. **The closed set:**

| HTTP | `result` | Meaning |
|---|---|---|
| 202 | `accepted` | the relay made one provider attempt and the provider accepted the message |
| 410 | `provider_gone` | the provider reported the address gone (for APNs `410` `Unregistered` or `ExpiredToken`; for FCM `UNREGISTERED`). Stop sending to it |
| 422 | `sealed_invalid` | the seal failed RFC 9180 validation, failed to open, failed the plaintext or JCS rules, or failed a binding check (§5 steps 11 to 15) |
| 409 | `replayed` | a seen nonce |
| 429 | `rate_limited` | the **relay's own** limits only. **The provider was not attempted.** Provider throttling is never `429` |
| 401 | `unauthorized` | a well-formed signature that does not verify, a different audience, a `ts` outside the window, an unknown `kid`, or an allowlist miss (§5 steps 3, 4, 6, 9, 10) |
| 400 | `bad_request` | malformed request, shape, SPKI, signature encoding, identifier or `ttl_s`, including an invalid decoded `sealed` length (§5 steps 1 and 3). Always before any provider work |
| 502 | `provider_unavailable` | the provider **was attempted** and the result is anything other than accepted or a definitive gone: a 5xx, throttling (APNs `TooManyRequests`, FCM `QUOTA_EXCEEDED`), a timeout, an ambiguous outcome, **and every other provider refusal** (APNs `BadDeviceToken`, `DeviceTokenNotForTopic`, `Forbidden`, `PayloadTooLarge`; FCM topic, payload or permission refusals) |
| 503 | `unavailable` | the provider was **not** attempted |

- **RES-0. No new code (B6).** This closed set is unchanged and has no tenth value. The relay's response body is only `{"result": <code>}`; it never carries or echoes a provider response body or text.
- **RES-A. `unavailable` versus `provider_unavailable`.** The relay **never** returns `503 unavailable` after a provider attempt has begun, and **never** retries a provider call itself. After any provider attempt, a failure that is not a definitive `provider_gone` answer is `502 provider_unavailable`. `503 unavailable` is returned only when no provider attempt began (for example a full replay cache, or the relay unable to start a provider call).
- **RES-B. Client classification (HMP, PN-DSP-8).** HMP treats anything outside this closed set, any malformed, oversized (over 1 KiB) or unknown response, and any timeout or connection loss after the request was written, as **ambiguous**.
- **RES-C. Retry only before a provider attempt.** HMP may retry automatically only when the provider was certainly not attempted: a connection that failed before the request was written (DNS, TCP or TLS), or `503 unavailable`. At most 2 retries, after 1 s and 4 s, each with ±20% jitter, only while the alert's TTL has not run out, and each as a **new** signed request with a fresh `ts` and `nonce` and the same `hint` and `collapse` (`⟨D8⟩`). HMP never retries: a timeout or connection loss after the request was written, `502 provider_unavailable`, `409 replayed`, `429 rate_limited`, `400`, `401`, `410`, `422`, or any malformed, oversized or unknown response. Those are ambiguous or definitive and are dropped with a fixed code.
- **RES-D. Breaker.** A circuit breaker opens after 3 consecutive retriable failures or post-write timeouts, stays open 60 s with one half-open probe, and while open drops new events at once without waiting. Timeouts are 5 s to connect and 10 s in total. Listener close waits at most 1 s for in-flight requests and never waits on the relay (`⟨D8⟩`).
- **RES-E. Feedback.** `410 provider_gone` marks the registration `provider_gone`, and `422 sealed_invalid` marks it `expired`, on the host, only if the dispatched `(SHA-256(R), G)` is still the device's current active registration (`HMP_V1.md` §7f). Late feedback never touches a newer registration. **No other result retires or changes a registration**: `502 provider_unavailable` (including `BadDeviceToken` and other refusals), `401`, `400`, `409`, `429` and `503` leave it as it is (`HMP_V1.md` §14 RES-27).
- **RES-G. What `202` and `410` mean (P3).** `202 accepted` means the provider accepted the message for delivery. It does not say the alert was shown. `410 provider_gone` is the only provider-side result that is **definitive**: the address is gone. `502 provider_unavailable` is never definitive. It may mean the provider rejected the message, did not see it, or saw it, and HMP cannot tell which, so HMP never retries it and never retires a registration on it. No provider body or text reaches an HMP log or the response.
- **RES-F. No relay text is ever logged or echoed by HMP.**

## 8. Fixed payload templates (PN-REL-5)

The host contributes no visible text. The visible text is the literal "Approval needed" (`⟨D15⟩`, first stage; an app-bundled localization key is a later UX decision).

### 8.1 APNs (direct, iOS)

- Headers: `apns-push-type: alert`; `apns-priority: 10`; `apns-expiration: now + ttl_s` (nonzero, Unix seconds); `apns-topic: <bundle ID from the relay's app allowlist>`; `apns-collapse-id: C` (at most 64 bytes); a random `apns-id`.
- Body:

  ```
  {"aps": {"alert": {"title": "Approval needed"}, "sound": "default",
           "interruption-level": "time-sensitive"},
   "hmp": {"v": 1, "route": R, "hint": K}}
  ```

- Provider authentication is an ES256 token refreshed no more often than every 20 minutes and no less often than every 60 (Apple's token-based connection rules). The relay uses one separate HTTP/2 connection per allowed `(app, env)` pair of its configured allowlist (F5, ENV-1, N3), never sharing a connection across pairs and never sending to an environment other than the selected pair's (N3). Which credential or signing key each connection uses, and how it is provisioned, belongs to pending owner choice O3 and is not decided here; there is no environment fallback.
- **iOS through FCM is not used.** FCM's own APNs example uses `apns-priority: 5`. Direct APNs alerts use priority 10 and an explicit expiration. Mixing the two is a defect.

### 8.2 FCM HTTP v1 (Android)

- Target field, chosen from the sealed `addr_kind`: `token` for `fcm_token` (the v1 reference marks `token` deprecated in favor of `fid`), `fid` for `fcm_fid`. Both patterns are co-supported during the transition.
- `android.priority: "HIGH"`; `android.ttl: "<ttl_s>s"`; `android.collapse_key`: the **one global constant** `hmp_approval_v1`, the same for every message and every bot (FCM allows at most four distinct keys at a time; there is no per-bot FCM `collapse_key`; the per-bot pseudonym is the notification `tag`); `android.restricted_package_name: <package from the relay's app allowlist>`.
- `android.notification: {"title": "Approval needed", "channel_id": "hmp_approval_v1", "tag": C}`. The `channel_id` is the fixed literal `hmp_approval_v1`. The channel's user-visible name and its localization are separate app work, and the user's channel settings prevail.
- `android.data: {"hmp_v": "1", "hmp_route": R, "hmp_hint": K}`.
- **FCM requests carry no `env`.** The Play services notification proxy setting is `⟨D16⟩`: the default (`PROXY_UNSPECIFIED`), subject to physical measurement on a device (`PLATFORM_GAP`); switch to `proxy: DENY` only if the tap or data path fails.
- A notification message lets the system show the generic alert while the app is in the **background**, with no app code and no host fetch. In the foreground, app code decides presentation.
- Provider credentials are short-lived OAuth 2.0 access tokens from a service account or the platform's default credentials. The relay makes at most 8 concurrent FCM requests.

### 8.3 One provider attempt

The relay makes **one** provider attempt per request and **never retries** a provider call. A queued request waits inside its own timeout; on timeout the relay answers `502 provider_unavailable` if the provider call had begun, otherwise `503 unavailable`.

### 8.4 Provider result mapping

| Provider outcome | `result` |
|---|---|
| accepted | `202 accepted` |
| APNs `410` (`Unregistered`, `ExpiredToken`); FCM `UNREGISTERED` | `410 provider_gone` |
| 5xx; timeout; APNs `TooManyRequests`; FCM `QUOTA_EXCEEDED`, `UNAVAILABLE`, `INTERNAL`; any ambiguous outcome | `502 provider_unavailable` |
| every other provider refusal (for example APNs `BadDeviceToken`, `DeviceTokenNotForTopic`, `Forbidden`, `PayloadTooLarge`; FCM topic, payload or permission refusals) | `502 provider_unavailable`, never retried, and HMP does not retire the registration on it (decision B6; `HMP_V1.md` §14 RES-27) |

APNs retry-after rules (5xx after 15 minutes, `TooManyRequests` with a delay) exceed the alert's lifetime or are not applied, so **nobody retries** a provider outcome. After a provider attempt there is no result other than `202`, `410` and `502`.

## 9. Relay limits and bounds (PN-REL-6; plan §6.5)

Single replica (`⟨D27⟩`). `B` is the global hourly budget, **an owner deployment choice that is pending**. The proposals are R2 `B` = 600 per hour and R1 `B` = 6,000 per hour; they are not frozen.

| Limit (`⟨D17⟩`) | Frozen value |
|---|---|
| per host `iid` | 120 per hour |
| per destination (`HMAC(relay secret, provider address)`) | 60 per hour |
| per `(destination, iid)` | 30 per hour (at most the HMP per-device hourly rate `⟨D6⟩`) |
| per source address | 600 per rolling 3,600 s, monotonic clock (CLK-1) |
| global verify budget (signature checks) | at most 20 in any rolling 1-second interval on a monotonic clock, no additional burst |
| global hourly budget `B` | **pending (owner)** |

- **LIM-1. Two separate admissions (P2).**
  - **Pre-verification admission (§5 step 2).** The per-source limit and the global verify budget are checked together, atomically, before signature verification. Both are charged immediately and only if both admit, **even when the signature or the seal later fails**. CPU is never charged "later", for example at provider admission. The per-source limit is a rolling 3,600-second window and the global verify budget allows at most 20 checks in any rolling 1-second interval, with no additional burst; both are measured on monotonic elapsed time (CLK-1). Under normal clock progress that is what makes the bound of at most 4,800 live nonces valid (§5 VER-1); clock stalls and backward steps can exceed it (CLK-1, capacity bullet).
  - **Post-seal hourly admission (§5 step 16).** The four counters (per `iid`, per destination, per `(destination, iid)`, global `B`), each over a rolling 3,600-second window on a monotonic clock (LIM-3, CLK-1), are checked together, atomically, and charged **only if every one admits**, so only admitted requests charge `B`. A request refused at step 16 charges none of them (the pre-verification charge of step 2 and the nonce reservation of step 7 stay).
- **LIM-3. Rolling windows (F6).** The four post-seal counters use rolling 3,600-second windows, not fixed clock hours: a request is admitted only if, counting the requests admitted in the preceding 3,600 seconds, every one of the four stays within its cap after the charge, and the check and the charge are one atomic step (all admit or none charges). A fixed-window boundary therefore allows no double burst. No cap value changes and no deployment choice is made; any structure with identical admission results is acceptable. This covers the four post-seal counters. The per-source limit of step 2 is likewise a rolling 3,600-second window (CLK-1). All rolling windows are measured on monotonic elapsed time, never on a raw wall clock that can step backwards. The HMP per-device hourly dispatch rate (`HMP_V1.md` PN-CONST, D6) and its window are HMP's own frozen policy and are not changed here.
- **LIM-2.** The per-`(destination, iid)` cap stops **one** `iid` from exhausting the destination ceiling and suppressing another host's alerts to the same phone. The per-destination cap stays as a ceiling that bounds spam to one phone.

Every table has a cardinality and an overflow rule:

| Object | Cardinality bound | Overflow rule |
|---|---|---|
| Request body / response | 4 KiB / fixed small JSON | `400 bad_request` before any other work |
| Pre-verification signature checks | at most 20 in any rolling 1-second interval, global (a sliding log of at most 20 timestamps) | `429 rate_limited`, provider not attempted, nothing charged. Exhausting it with unauthenticated traffic denies every R1 alert |
| Per-source table (pre-verification) | 4,096 entries, LRU | Eviction can only loosen one source's limit; the global verify budget still bounds CPU |
| Replay nonce cache | 16,384 entries, each kept over `[receipt, ts + CLOCK_SKEW_S)` (at most 240 s under normal clock progress) and purged when its expiry is at or before `now`; at most 4,800 live at the verify budget under normal clock progress (clock stalls or backward steps can prolong retention and exceed it, CLK-1) | Atomic check-and-reserve; refuse `503 unavailable` when full (provider not attempted); never evict an unexpired nonce and never release a reservation early; repeated stalls or steps that reach 16,384 refuse `503` with no eviction. A full cache is a defensive path. Memory only, together with `last_now`: a restart empties both (VER-1a, RES-26, CLK-1) |
| Per-`iid`, per-destination, per-`(destination, iid)` tables | `B` entries each, over rolling 3,600-second windows (LIM-3); an entry is created only when the request is admitted by every per-key cap and the global budget | Cannot overflow while global admission holds. If full anyway, refuse `429 rate_limited` (fail closed, no eviction of a live counter) |
| `iid` allowlist (R2 mode) | at most 8 entries, from relay configuration | Not in list: `401 unauthorized` |
| Negative cache of gone destinations (optional) | 4,096 HMACs, LRU, 30-day entry lifetime | Eviction only costs one more provider attempt |
| Provider connections | APNs: one HTTP/2 connection per allowed `(app, env)` pair (ENV-1); FCM: at most 8 concurrent requests | Queue inside the request's own timeout; on timeout `502 provider_unavailable` if the provider call began, else `503 unavailable` |

**Residuals (recorded and not closed; see `HMP_V1.md` §14 and analysis A1, A14, A17):**

- Under open enrollment an `iid` costs nothing, so `n ≥ ⌈destination ceiling / pair cap⌉` sybil `iid`s (2 at the frozen 60 and 30) holding a leaked address still exhaust the destination ceiling and suppress a real host's alerts to that phone. Keeping the ceiling keeps the spam bound at the price of this suppression; dropping it would remove the suppression but allow unbounded spam across many `iid`s. The design keeps the ceiling.
- In public (R1) mode, unauthenticated traffic from many source addresses can exhaust the global verify budget, and sybil `iid`s sealing random addresses can exhaust the global hourly budget `B`. Those requests pass the seal checks, because the relay checks `app`, `env` and bindings, not whether an address is real. Either exhaustion denies all R1 alerts. Floods of garbage addresses may also affect the relay's standing with a provider (`EVIDENCE_GAP`, not checked).
- R2 is not immune: the allowlist limits reachability and stops non-allowlisted provider and hourly admission, but the global verify budget is consumed before the signature and allowlist checks, so a reachable peer can still exhaust it.
- Public R1 stays **inactive and owner-pending**.

## 10. Custody (PN-REL-7) and logging (PN-REL-8)

- **CUS-1.** The HPKE private keys (per `kid`), the APNs token-signing key and the FCM credentials live only in the relay's secret store. They never reach HMP, the app, CI logs or any repository. Generating the HPKE key pairs is an owner action whose custody is effectively irreversible once a distributed build ships the public key (pending).
- **CUS-2.** The relay keeps **no database of provider addresses**. It holds bounded in-memory rate and replay state, and optionally the bounded negative cache above.
- **LOG-1.** The relay logs only the `kid`, the result code, the provider status class and, at most, a relay-local keyed hash of the `iid` that rotates with the relay's log key. It **never** logs a raw `iid` or an `iid` prefix, a provider address, a sealed blob, `R`, `K`, `C`, a signature or a provider response body.

## 11. Provider facts relied on

Taken from primary sources fetched 2026-10-02 (`specs/014-approval-push-registration/analysis.md` §6). Anything not listed there is an assumption or a gap.

- APNs is best effort: it may reorder, stores one notification per bundle ID and may coalesce. With `apns-expiration` it tries to deliver at least once until that date; whether it can deliver after that date is not stated (`EVIDENCE_GAP`), so late taps are tolerated. Payloads are limited to 4 KB.
- FCM `HIGH` priority attempts immediate delivery and may wake a dozing device. Payloads are limited to 4096 bytes, TTL to at most four weeks, and at most four distinct `collapse_key` values at a time. A user who disabled notifications gets none, and high-priority messages to such an app are deprioritized.
- Physical delivery, Doze, Focus, force-quit and force-stop, Time Sensitive entitlement behavior, Play services proxy behavior and a hosting platform's HTTP/2 support are **not established here** and are measured on owner-authorized devices only (`PLATFORM_GAP`).

## 12. Constants

Values frozen by root on 2026-10-02. Owner deployment budgets stay pending. They are not rows of `HMP_V1.md` §13 (that table is checked against `contract.py`; see `HMP_V1.md` §7f).

| Constant | Value | Decision |
|---|---|---|
| Request body bound | 4,096 bytes | PN-REL-2 |
| Response read bound (client) | 1,024 bytes | `⟨D8⟩` |
| Relay replay window / skew | 120 s (`CLOCK_SKEW_S`) | `⟨D18⟩` |
| Nonce retention | until `ts + 120 s` | `⟨D18⟩` |
| Replay cache | 16,384 entries; 4,800 live at the verify budget under normal clock progress (CLK-1) | `⟨D18⟩` |
| Global verify budget | at most 20 in any rolling 1-second interval (monotonic clock), no extra burst | `⟨D17⟩`, P2, R-F1a |
| Limits per hour: `iid` / destination / `(destination, iid)` / source | 120 / 60 / 30 / 600; per `iid`, destination, `(destination, iid)` and `B` over rolling 3,600 s windows (LIM-3), and the per-source 600 over a rolling 3,600 s window, all on a monotonic clock (CLK-1) | `⟨D17⟩`, F6, R-F1a |
| Global hourly budget `B` | pending (owner); proposals R2 600, R1 6,000 | `⟨D17⟩` |
| `iid` allowlist size (R2) | at most 8 | `⟨D23⟩` |
| Relay replicas | exactly 1 | `⟨D27⟩` |
| Seal lifetime: minimum / maximum | 1 h (3,600 s) / 14 d (1,209,600 s) | `⟨D9⟩` |
| Sealed value (decoded): accepted range / frozen ceiling / seal plaintext | 82 to 1,105 bytes inclusive / 2,048 / 1 to 1,024 bytes (`enc` 65 + tag 16 + plaintext) | `⟨D10⟩`, B3 |
| `kid` / `aud` grammar | `[A-Za-z0-9][A-Za-z0-9._-]{0,63}` / `{0,127}`, ASCII, case-sensitive, exact | B4 |
| FCM `channel_id` and the one global FCM `collapse_key` | the fixed literal `hmp_approval_v1` for both | B4 |
| Signature transcript `R`, `K`, `C` | raw decoded 32, 32 and 24 bytes (wire 43, 43 and 32 characters) | B1 |
| `ts` / `ttl_s` | nonnegative integer below 2^53 / integer 60 to 900 inclusive | B6 |
| Nonce interval | `[receipt, ts + 120 s)`, purged when `expiry ≤ now`; at most 4,800 live under normal clock progress (CLK-1); skew re-checked at one effective acceptance instant `max(raw wall now, last_now)` inside the atomic nonce section, reused by step 14 (CLK-1) | P1, P2, F1, R-F1a |
| Optional relay TLS pins (host) | omitted, or exactly 1 to 8 distinct canonical unpadded base64url SHA-256 digests (43 characters, 32 bytes) of the leaf DER `SubjectPublicKeyInfo`; additional to chain and host-name validation | R-PIN |
| Provider TTL floor / cap / default | 60 s / 900 s / 330 s | `⟨D7⟩` |
| Client retries / backoff / timeouts | 2 / 1 s, 4 s with ±20% jitter / 5 s connect, 10 s total | `⟨D8⟩` |
| Client breaker | 3 failures, 60 s open, one probe; close waits at most 1 s | `⟨D8⟩` |
| HPKE suite | mode 0x00; kem 0x0010; kdf 0x0001; aead 0x0001 | `⟨D1⟩` |
| Visible text | literal "Approval needed" | `⟨D15⟩` |
| FCM notification proxy | default, subject to device measurement | `⟨D16⟩` |

## 13. Open items

### 13.1 Root interoperability amendment, 2026-10-02 (authoritative; addresses the six former relay-contract `HMP_CONTRACT_GAP` items)

Root architecture direction for **contract text only**. It authorizes no source, key, relay, deployment, provider action or owner choice, and independent contract review remains required. The B1 to B6 protocol choices are project architecture decisions. They rely on these primary sources, which define only the cryptographic and canonicalization primitives: RFC 9180 §§6.1, 7.1, 7.1.1, 7.1.4, 7.2, 7.3 and RFC 8785 §§3.1, 3.2.1 to 3.2.4. The labels B1 to B6 and P1 to P3 are this amendment's own; they are unrelated to the earlier review items B1 to B4 in `ROOT_DECISIONS.md`. The earlier text in this file that said "GAP-n" is superseded and has been replaced, not kept as a competing reading. Those removed relay-contract labels GAP-1 to GAP-6 are distinct from the live `GAP-1` and `GAP-2` rules of `HMP_V1.md` §12, which this amendment does not touch and makes no claim about.

| ID (former relay-contract item; labels removed) | Decision | Where applied |
|---|---|---|
| **B1** (GAP-1) | `R`, `K`, `C` enter the signature transcript as raw decoded 32, 32 and 24 bytes; wire forms stay canonical b64u of 43, 43 and 32 characters. `SHA-256(S)`, `SHA-256(R)` over raw decoded bytes. `ROUTE` and `COLLAPSE` field types and `scope` as UTF-8, `C` as the first 32 characters of the b64u HMAC. `iid` is derived from the supplied SPKI before the transcript is built | §4 SIG-1, §5 step 3, PR-4; `HMP_V1.md` PN-ISS-1, PN-KEY |
| **B2** (GAP-2) | Seal plaintext is RFC 8785 JCS, UTF-8, no BOM, at most 1,024 bytes, in a restricted domain (strings, plus `v` and `not_after` as integers below 2^53); exact reserialization required; canonical order given; no invented vector | §6.1 |
| **B3** (GAP-3) | `sealed = b64u(enc ‖ ct)`, `enc` 65 bytes, `ct` including the 16-byte tag; decoded size 82 to 1,105; HMP checks only canonical b64u and these bounds; relay does RFC 9180 §7.1.4 validation, open, then schema and JCS; `422` for point, tag or plaintext failure, `400` for invalid length | §3 REQ-3, §6.2, §5 steps 1 and 11 |
| **B4** (GAP-4) | `kid` and `aud` grammars; case-sensitive exact comparison; `channel_id` and the one global FCM `collapse_key` are both the literal `hmp_approval_v1`; no per-bot FCM `collapse_key` | PR-5, §8.2, §12 |
| **B5** (GAP-5) | `DELETE /push/registration` does not depend on push or relay availability and makes no Hermes, relay or provider call; `GET` stays readable while unavailable | `HMP_V1.md` §7f PN-REG-3, PN-ST |
| **B6** (GAP-6) | Result codes: `400` malformed (before any provider work), `401` well-formed but invalid, `422` seal failures, `409`, `429`, `503` unchanged; after a provider attempt every result other than accepted or gone is `502`; no automatic retry; no registration retired on those refusals; no new code | §5, §7, §8.4 |
| **P1** | No provider before step 17; atomic nonce check-and-reserve before decrypt, held until `ts + 120`, never released early; restart replay residual stays, no durable cache | §5 steps 7, 8 and 17, VER-1, VER-1a |
| **P2** | Separate pre-verification and post-seal admissions, each atomic and each charged as stated; at most 20 verify checks in any rolling second; nonce interval `[receipt, ts + 120)` purged at `expiry ≤ now` | §5 steps 2 and 16, VER-1, LIM-1, §9 |
| **P3** | `202` is provider acceptance, `410` is the only definitive provider result, `502` is never definitive; no provider text reaches HMP logs or the response; residuals and owner choices stay pending | RES-0, RES-E, RES-G, LOG-1; `HMP_V1.md` §14 |

**What the amendment does not decide or claim.** No HMP-specific signature, JCS or seal vector exists; they are implementation follow-up that needs an independent generator and review (§6.3 KAT-3). Nothing here shows interoperability, because no implementation exists. The skew-window boundary of §5 step 6 (`now < ts + CLOCK_SKEW_S`) is a consequence of the P1/P2 nonce interval, not a separate choice. Its clock source is refined by R-F1a (§13.5).

### 13.2 Pending owner or account choices (nothing is provisioned)

O1 relay stage; O2 R1 hosting; O3 Apple push key type; O4 Firebase project scope; O5 relay source visibility; O6 privacy declarations; plus HPKE key custody, App ID capabilities, any relay domain or DNS, and the global relay budget `B`. Root design choices authorize none of them.

### 13.3 Not claimed

No relay is built or deployed. No key, endpoint, account or provider capability exists. No alert has been delivered, and no physical-device, sandbox or production evidence exists. This document is not a release or feature-ready claim.

### 13.4 Root review clarifications, 2026-10-02 (authoritative; F1 to F7)

Root contract-text clarifications after an independent scoped review of an earlier candidate, which accepted that candidate with conditions. They preserve B1 to B6 and P1 to P3 and every authority and security requirement above. They authorize no source, key, relay, deployment, provider action or owner choice, and a later independent review accepted their other clauses while requiring the clock and pin source gates now written in §13.5 (contract text accepted, implementation pending). The relay-side items are:

| ID | Clarification | Where applied |
|---|---|---|
| **F1** | Step 7 reads one current `now` inside its atomic section, re-checks both skew inequalities, then purges, checks and reserves with that instant; a failed re-check is `401` with no new nonce and no provider. Step 6 is an early screen only. Concurrent and boundary conformance is required. The restart replay residual stays. The source of that instant is refined by R-F1a (§13.5) | §5 steps 6 and 7, VER-1, CLK-1, §12, §14 |
| **F3** | The removed relay-contract labels GAP-1 to GAP-6 are not `HMP_V1.md`'s live `GAP-1` and `GAP-2`; B1 to B6 are cited with that qualification and no broad gap-resolution claim is made | header, §13.1 |
| **F4** | The signature is a strict minimal DER `SEQUENCE` of two positive `INTEGER`s in `1` to `n − 1` with no trailing bytes; malformed is `400`, valid but not verifying is `401`; low-S and high-S both verify; no homemade verifier; vectors pending | §4 SIG-1, §5 steps 1 and 3, §14 |
| **F5** | The APNs environment policy is per allowed `(app, env)` pair, each with its own provider connection; signed and sealed `env` must equal each other and the selected pair; no fallback; step 10 stays `401` and the seal bindings stay `422` | §5 step 15, ENV-1, CF-2, §8.1, §9 |
| **F6** | The four post-seal counters use rolling 3,600-second windows, charged atomically all or none; no new cap value; HMP's per-device dispatch window is unchanged | §5 step 16, LIM-1, LIM-3, §9, §14 |

F2 (availability and kid liveness) and the status clarification of F7 are in `HMP_V1.md` §7f and the spec documents; F7 changes no relay behavior. Vectors for F1, F4 and F6 are implementation follow-up (KAT-3). Wording elsewhere in the project history that says a request "is never accepted for skew after its nonce was purged" is superseded by CLK-1, which states that guarantee with its clock condition.

### 13.5 Root clock and pin delta, 2026-10-02 (authoritative; R-F1a, R-PIN, N3 to N6; pre-review status recorded below)

Root contract-text direction after a later independent review of §13.4. That review accepted the other clauses of the clarified text and required two source gates: a relay clock source (its finding N1) and an optional pin grammar (N2). This section writes those gates as normative text. Pre-review history: **Written is not accepted:** the delta below is new, **has not been independently reviewed**, and needs a focused independent sentence review. The clock-count repair of 2026-10-02 followed a focused review of that delta: the review accepted the mechanism, the pins and N3 to N6, and required text repairs for the 4,800-nonce and 240 s qualification under clock steps (its finding D1) and for one APNs connection granularity per allowed `(app, env)` pair (D2), with editorial wording (D3). At that checkpoint, the repaired capacity and connection sentences awaited a focused check of those sentences only. That check has now accepted D1/D2/D3 as contract text; implementation and verification remain pending. It authorizes no source, vector, key, relay, deployment, provider action, device test or owner choice, and no scanner or constitution text changes with it.

| ID | Decision | Where applied |
|---|---|---|
| **R-F1a** | The relay's acceptance instant is `max(raw wall now, last_now)` computed and stored inside the atomic nonce section; step 7 and step 14 use it; step 6 may use the raw clock. Rolling windows of steps 2 and 16, including the per-source 600 per 3,600 s, use monotonic elapsed time. A backward clock step cannot reopen a purged nonce in one replica lifetime; while `last_now` is ahead of the raw wall clock the relay can refuse availability (`401`/`422`) until the wall clock catches up or the operator restarts, with no automatic restart or reserve reset. The 240 s retention and 4,800 live bound hold only under normal clock progress; stalls or backward steps can prolong retention, exceed 4,800 and reach the 16,384 cap (`503`, no eviction, no early release, no new replay), and no other progression, TTL or reset is stated (CLK-1). Baseline D18, P2 and C4 are history that this condition qualifies. `last_now` is memory only; the restart residual and its relay-clock-time bound stay. Causal rollback and forward-jump tests and vectors are pending | §5 steps 2, 6, 7, 14 and 16, VER-1, VER-1a, CLK-1, LIM-1, LIM-3, §9, §12, §14 |
| **R-PIN** | Host setting `push.relay_spki_pins`. Omitted means no optional pin; configured means exactly 1 to 8 distinct canonical unpadded base64url SHA-256 digests (43 characters, 32 bytes) of the leaf DER `SubjectPublicKeyInfo`; explicit `None`, an empty list, a non-list, a duplicate or a bad entry is malformed and gives `relay_unconfigured`. Chain and host-name validation against the standard trust store are always required; a pin is an additional leaf-only constraint, never a trust anchor or bypass. A mismatch is a pre-write TLS failure under the bounded RES-C retry, with no trust fallback. No environment-variable fallback | CF-1, CF-1a, REQ-2, §12, §14; `HMP_V1.md` §7f PN-AV |
| **N3** | The relay uses a separate provider connection per allowed `(app, env)` pair. Credential and signing-key provisioning belongs to pending owner choice O3 and is not decided here; there is no environment fallback | §8.1, ENV-1 |
| **N4** | The settings list includes the optional pins, and the all-off purge reasons include an empty kid list and malformed pins | `HMP_V1.md` §7f; spec PN-AV-2; task T020 |
| **N5** | An inert active row counts against the D24 active capacity, not the D25 retained capacity; no capacity invariant changes | `HMP_V1.md` §7f PN-BND; spec PN-BND; ROOT_DECISIONS |
| **N6** | The earlier "six gaps are resolved" and "never accepted for skew after its nonce was purged" wording is superseded history. The live `GAP-1` and `GAP-2` of `HMP_V1.md` §12 remain open and untouched | `ROOT_DECISIONS.md` |

## 14. Conformance obligations (for the relay repository and HMP)

Future work, listed so the contract is complete. None is evidence today.

- **Signature and request negatives.** Transcript with raw `R`, `K`, `C` and the derived `iid`; a wire `iid` field ignored; malformed SPKI, off-curve point, malformed signature header or DER (`400`); strict DER and range (F4): a non-minimal encoding, a zero, negative or out-of-range `r` or `s` (`0`, a negative encoding, `n`, above `n`), a wrong structure and trailing bytes are `400`, and a syntactically valid, in-range, non-verifying pair is `401`, with both low-S and high-S valid signatures verifying (vectors pending, KAT-3); a well-formed wrong signature (`401`); `aud` mismatch (`401`); `ts` outside the window including the exact boundaries (`ts = now + 120` accepted, `ts = now + 121` `401`, `now = ts + 119` accepted, `now = ts + 120` `401`); `ttl_s` of 59 and 901 and a non-integer (`400`); `ts` negative, fractional or 2^53 (`400`); a boolean or float `v`; unknown and known-but-disallowed `kid` (`401`); identifier grammar bounds for `kid` (64) and `aud` (128) and their one-over cases.
- **Replay and admission.** (F1) A request that passes the step 6 early screen before `ts + 120` and reaches step 7 after it is `401` with no reservation and no provider call; a request whose nonce another worker purged at `expiry ≤ now` is `401` at step 7 and, within one replica lifetime and while `last_now` never decreases, never reserves afresh; concurrent identical requests straddling that boundary never both reach a provider; the step 7 purge, check and reserve use the same instant as the re-check. A seen nonce (`409`); two concurrent identical requests never both reach a provider; the reservation stays after a later refusal; a full cache refuses and evicts nothing; nonce purge at `expiry ≤ now`; at most 20 verify checks in any rolling 1-second interval and no burst; the pre-verification pair charges both or neither, and keeps the charge when the signature or seal later fails; the four counters are charged only when all admit, over rolling 3,600-second windows with no boundary double burst (F6: no more admissions than a cap in any 3,600 seconds, including a burst split across a fixed clock-hour boundary); under normal clock progress (clock-step tests excluded) the cache never exceeds 4,800 live nonces at the verify budget; restart empties the cache and `last_now` (documented residual). **Clock (R-F1a, tests pending, none exists):** a backward wall-clock step after a purge cannot make the replayed request reserve afresh (it stays `401`); a forward step across `ts + 120` refuses `401` at step 7 until the clock catches up; step 14 uses the instant of step 7 and never a later raw reading; the four post-seal counters, the global verify budget and the per-source limit neither double-count nor un-count across a backward or forward wall-clock step because they use monotonic elapsed time; no automatic restart or reserve reset occurs; retained capacity under repeated backward steps (live count may exceed 4,800; no exact bound promised) and a full cache under repeated steps (`503`, nothing evicted, no replay accepted) are likewise pending tests.
- **Seal.** Decoded `sealed` length 81 and 1,106 (`400`) and 82 and 1,105 (accepted at shape); a malformed `enc` point, a flipped tag bit, a wrong `kid` AAD and a wrong `info` (`422`); plaintext with a duplicate name, an extra or missing member, a lone surrogate, whitespace, unsorted members, a float or exponent `not_after`, a boolean, a negative or oversized integer, an integer-as-string and a non-JCS escape (`422`); binding mismatches (`iid`, app, `env`, expiry, platform, `addr_kind`); an `fcm` seal carrying `env`.
- **APNs environment (F5).** Sandbox-only, production-only and both-pairs relays; an `(app, env)` pair not in the allowlist, a sealed `env` different from the signed `env`, and a pair whose environment differs from the signed one are `422`, with no fallback to another environment and a separate connection per allowed `(app, env)` pair; the `iid` allowlist miss stays `401`. No real account is used.
- **Provider.** Fixed templates with any host text ignored; `token` versus `fid` targeting; `hmp_approval_v1` as the channel id and the sole `collapse_key`; response mapping with `502 provider_unavailable` after every provider attempt that is not `202` or `410`, including `BadDeviceToken` and the other refusals, and never `503` after an attempt; provider throttling maps to `502`.
- **Limits and logs.** Per-`(destination, iid)` cap stops one `iid` (the two-`iid` destination-ceiling test documents the sybil residual); allowlist mode; limiter tables fail closed when full; verify-budget exhaustion gives `429` with no provider call; log canaries with no `iid` prefix and no provider body; no persistence of addresses; FCM requests carry no `env`.
- The RFC 9180 vector of §6.3 passes on the relay and in the app. HMP-specific vectors come from an independent generator after review (KAT-3) as implementation follow-up; they are not blocked by an open contract gap.
- **HMP side.** Redirects refused, proxy environment ignored, oversize, slow, malformed and unknown results treated as ambiguous, pre-write connect failure versus post-write timeout, optional-pin configuration (R-PIN: omitted allowed; explicit `None`, an empty list, a non-list, a duplicate, a wrong-length, padded, non-canonical or non-base64url entry, and more than 8 entries are `relay_unconfigured`; a leaf pin mismatch, a mismatch with only an issuing-certificate match, and a self-signed certificate with a matching pin all fail before any request byte, retried only under RES-C; chain and host-name validation always required; tests pending), the signature transcript including `aud`, `platform`, `addr_kind` and `env` with raw `R`, `K`, `C` (task T025), and no registration retired on a result other than `410` and `422`.
