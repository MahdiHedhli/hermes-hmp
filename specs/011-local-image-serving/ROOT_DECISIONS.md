# Root decisions

Public record of the architecture decisions this feature was frozen on. Where another document here differs, this file wins. It records decisions only: nothing is implemented, qualified or released.

## Accepted

| ID | Decision |
| --- | --- |
| C1 | Derive the flat cache name lexically from the raw `image` string; no `resolve()`, no legacy directories. A spelling mismatch refuses (`EVIDENCE_GAP` until E1 passes). |
| C2 | Authority is only a strict same-profile `image_generate` tool row. Assistant `MEDIA:` text and Markdown have none. |
| C3 | New ERR-2 code `media_unavailable`, `503`, "image delivery is unavailable". A non-owner device gets `404` first. |
| C4 | Overload is the existing `429 rate_limited`, no `why`. |
| C5 | The handle binds a session kind (`bot_chat` or `phone`), rechecked at fetch. |
| C8 | Mint is idempotent and never extends TTL; at most 128 newest descriptors per response. |
| C9 | The handle carries no path. Existing capped tool text may already contain it; rows are not claimed pathless. |
| Gate | Default-off owner-device gate (`is_approval_owner_device`; unrelated owner privilege never implies it), separate `local_media.enabled`, process-qualified manifest, shipped empty. |
| Bytes | Max 8 MiB; PNG, JPEG, WebP; host structural check plus phone decode with bounds. |
| Order | Bot Chat first, then Phone chat under the same contract. |

## Authoritative corrections

1. **Authorization ordering.** After the first worker returns, a second off-loop phase runs fresh native per-bot authorization, same-kind eligibility and tip. Then the loop synchronously runs bearer, owner, gate, TTL and digest CAS with no `await` before `prepare`. No native check runs on the loop. A causal change before the phase-two check refuses with `404`, zero bytes. A change after the last native check is an unavoidable residual (no atomic native API) and is not promised to refuse. There is no atomic snapshot claim.
2. **No wire leak.** The raw candidate travels in a non-wire sidecar. Gate closed yields the exact old bytes.
3. **Process qualification.** Loaded/start baseline plus fresh disk equality over a dedicated media file list and the exact dependencies, following the approval baseline discipline. No supported entry exists until an actual qualification. Approval gates are never waived.
4. **Phone card.** The host image card keeps the existing card's tap-to-load trigger, phases, Cancel and 2-operation screen limit, with no queue; no new tap, auto-load or queue; no public fallback.
5. **Memory.** Four active plus four late workers cannot run at once because buffer permits stay held for the real worker life. Provisional ceilings: 96 MiB traced peak, 128 MiB incremental RSS; no native-allocation bound is claimed; a failure changes the implementation, not the ceiling.
6. **Deadlines.** 20 s worker wait shared by both phases; 30 s total write deadline including EOF. Worker and buffer permits live until real future completion plus the handler `finally`. Copied `ContextVar`s keep profile scope on the dedicated executor.
7. **Client.** A separate pinned binary load path with the existing single `401` refresh, exact MIME and magic, static raster at most 8 MiB.
8. **Error mappings** come from current source (see the §7e table); the initial per-bot grant keeps ERR-3 exactly, later refusals are generic `404`.

## Clarifications accepted at freeze

- Instance admission is the buffer permit; the device permit has the same lifetime.
- A phase-two permit shortage is reachable only by fault injection; it is retained and tested by injecting a shortage.
- Qualification disk and dependency work and the initial native grant work use the shared default executor, leaving the four dedicated workers for the media phases.
- An immutable startup mismatch needs a restart; a later disk mismatch closes the gate while present, and restoring the startup baseline can reopen it.
- All constants are new choices for this feature; memory ceilings stay provisional; E1 and Linux qualification remain later admission gates.
- The existing phone transport timeout is 15 s; a slow fetch may show unavailable before the host deadlines. No transport change is authorized.

## Review status

An independent pre-code review of the frozen design passed. That review covers the design only: product, native serving, device and release gates remain open, and no reviewer, qualification, security or release checklist is certified by the authors of these documents.

## Residuals carried

No atomic snapshot (including ABA on unrelated rows); change after the last native check before `prepare`; coarse-timestamp torn buffer (the phone codec decides); out-of-tree providers unfingerprinted; no containment of same-account host code; Linux errno unrun; deadlines and memory ceilings provisional.

2026-10-01 root P0 disposition: additive transcription conforms to the frozen design and its
independent Opus pre-code PASS. Revision 1.6 draft and LM clause names are accepted. All
implementation, native qualification, platform, device and release gates remain open.
