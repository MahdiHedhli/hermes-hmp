# Host-local generated images

Status: **draft specification. Feature unimplemented: no route, not qualified, not released.** Amended 2026-10-02 for the owner's minimum-version policy (see [`ROOT_DECISIONS.md`](ROOT_DECISIONS.md#minimum-version-conversion-supersedes-s6-manifestfingerprintanchor-s6a-admission-semantics-s6b-preload-qualification-2026-10-02)); the exact-build manifest described by earlier revisions is retired. The normative wire text is [HMP v1 §7e](../../docs/architecture/contracts/HMP_V1.md) (clauses `LM-1`..`LM-20`); this spec is the feature-level view and must not contradict it. Decisions and their authority are in [`ROOT_DECISIONS.md`](ROOT_DECISIONS.md). There is no build list. Availability follows the minimum version and the required Hermes APIs (HMP v1 GU-2d). This feature makes no qualification, shipping or platform claim.

## User outcome

On a host at or above the media floor whose required APIs are present, with the owner flag on, for an approval-owner device, an image the bot generated with `image_generate` and stored in that profile's image cache appears on the tool row that produced it. The phone fetches it through one authenticated HMP route using an opaque, short-lived handle. Hermes stays the source of truth; the phone gains no authority.

Out of scope: upload, video, audio, file browsing, arbitrary host paths, local `MEDIA:` resolution (assistant `MEDIA:` stays text), public fallback, durable image cache.

## Inherited invariants

- Hermes is the source of truth; one explicit active instance; no cross-instance fallback.
- A missing Hermes capability is an explicit `HERMES_API_GAP`, not a mobile shadow path.
- [SECURITY.md](../../SECURITY.md) applies: `SECURITY_REVIEW_REQUIRED` for the handle, route, gate and listener binding.

## Acceptance scenarios

1. **Gate closed.** Flag off, feature unavailable, or a non-owner device: reads are byte-identical to a server without this feature. Non-owner gets `404 not_found` first; an owner device gets `503 media_unavailable`.
2. **Descriptor.** With the gate open, a valid `image_generate` tool row in an eligible Bot Chat or Phone session carries `media:{kind:"image",ref}` and nothing else. Assistant rows and `MEDIA:` text never do.
3. **Binding.** A ref used by another device, user, instance, profile or session kind, or after expiry or eviction, gives one `404 not_found`.
4. **Authorization.** Every fetch re-authenticates and rescans. Revocation, grant loss, tip change or a replaced conversation refuses with zero bytes (causal cases only; see residuals).
5. **Bytes.** Only PNG, JPEG or WebP at most 8 MiB, with the fixed headers, streamed within a 30 s deadline.
6. **Overload.** Permit exhaustion is `429 rate_limited` with no `why`; no queue.
7. **Cancellation.** A cancelled client leaves worker and buffer permits held until the real work ends.

## Requirement map

| Topic | Contract clause |
| --- | --- |
| Owner gate (`is_approval_owner_device`), flag (`local_media.enabled`), availability (floor, probe, in-memory binding) | LM-1, LM-2, LM-3 |
| Descriptor and client rules | LM-4 |
| Mint preconditions, lexical name derivation | LM-5 |
| Session kind and device/user/profile/instance binding | LM-6, LM-9 |
| Strict same-profile tool authority | LM-7 |
| Non-wire sidecar | LM-8 |
| Registry (TTL 1800 s, 512/4096, LRU, idempotent mint, 128 per response) | LM-9 |
| Route order, two off-loop phases, shared 20 s wait, synchronous final section | LM-10, LM-11, LM-12 |
| Worker, buffer and device permit lifetimes; copied `ContextVar`s | LM-11, LM-13 |
| Success response and 30 s write deadline | LM-14 |
| Error table | LM-15 |
| Logging | LM-16 |
| Client behavior and the existing 15 s phone timeout | LM-17 |
| Provisional memory ceilings | LM-18 |
| Sampled release-candidate evidence (E1, Linux leaf, C6, T12) and review | LM-19 |
| Residuals | LM-20 |

## Reused accepted modules

The scanner, file-leaf and raster-structure checks were accepted by earlier independent review as G3 and G4 research:

- Filesystem leaf: [HMP draft #66](https://github.com/MahdiHedhli/hermes-hmp/pull/66), `6470379`.
- Raster structure: [HMP draft #67](https://github.com/MahdiHedhli/hermes-hmp/pull/67), `8a74190`.
- Active-history linkage: [HMP draft #69](https://github.com/MahdiHedhli/hermes-hmp/pull/69), `b32d913`.

These are research evidence, not qualified serving. Implementation promotes them into the plugin surface with logic unchanged except the one shared result function used by both mint and fetch. The task list records content hashes of the promoted copies.

## Gaps and non-goals

- E1 (producer spelling): the producer's `image` string must begin lexically with the routed home string plus `/cache/images/`. The bounded exact-build fixture passed for its stated producer and layout. That is **sampled evidence, not an admission prerequisite per build**; a mismatch on any build refuses that candidate (`lexical_mismatch`).
- `PLATFORM_GAP`: the bounded Linux file-leaf run passed on its stated platform; native serving and broader platform coverage are unqualified, and no Linux support claim is made.
- No atomic snapshot guarantee. A grant or tip change after the last native check and before `prepare` is a stated residual and is not promised to refuse. No native check runs on the event loop.
- Memory ceilings (96 MiB traced peak, 128 MiB incremental RSS) are provisional verification ceilings, not a native-allocation bound.
- The constants (20 s, 30 s, 1800 s, 512/4096, 128, 2/4, 120 per minute) are new choices for this feature, not existing Hermes or HMP constants.
- Install bounds are not broadened and no upper version bound is added.
- Under the minimum-version policy no build list, fingerprint, Git SHA, qualification manifest or process latch gates this feature. A disabled direct-send switch does not close it. Unknown, newer and development versions are attempted; only a version below the floor, a missing required API, a failed in-memory binding check or a per-candidate security check closes it.
- `HERMES_API_GAP` G-M1 (no bounded, side-effect-free, snapshot-consistent session read; native reads may materialize unbounded content, flush token counts and prune) and G-M2 (no typed tool-artifact record, so producers other than `image_generate` cannot gain authority) are retained and unsolved.
- Assistant `MEDIA:` text stays ordinary, unmodified text on every build (root choice D-M9). The image appears on the tool row. No presentation question is pending.
- C6b exact-native binding cost, T12 memory, independent exact-candidate review and physical-device acceptance are pending release-candidate evidence, not feature enablement.
- The existing phone transport timeout is 15 s; a slow fetch may show unavailable before the host deadlines. No transport change is authorized here.
- Phone app work lives in a separate private repository and is out of this tree.
