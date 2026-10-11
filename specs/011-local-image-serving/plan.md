# Plan

Amended 2026-10-02 for the minimum-version policy; the earlier exact-build qualification design is historical.

Authority: [`spec.md`](spec.md), [HMP v1 §7e](../../docs/architecture/contracts/HMP_V1.md) and [`ROOT_DECISIONS.md`](ROOT_DECISIONS.md). This plan is documents only; no code is authorized by it. Implementation starts only after the contract revision is merged and reviewed.

## Trust-boundary impact

| Boundary | Change | Control |
| --- | --- | --- |
| Host file system | New read of one profile image-cache file | Lexical flat-name derivation, accepted leaf read, structural raster check, tool-row rescan on every fetch |
| Handle registry | New process-local capability tokens | 32 random bytes, TTL, caps, binding to device/user/instance/profile/kind/tip/row digest; never authorizes alone; no process latch |
| Network | New binary response | Owner-only, no query or body, fixed headers, no range, bounded streaming, abort on failure |
| Native Hermes | Reads of the database and authorization | Existing bridge calls only, never on the event loop; second bounded post-worker native check before the loop's synchronous section |
| Memory and DoS | Up to 4 x 8 MiB buffers | Dedicated 4-worker executor, buffer permits, device 2 and instance 4, provisional ceilings |
| Wire | Additive optional field | Non-wire sidecar; gate closed yields identical bytes |

## Design

1. **Shared result rule.** One function decides "valid `image_generate` result"; mint and fetch both call it.
2. **Sidecar.** The bridge hands the raw candidate to the server handler in an explicit read-result carrier. It never enters a wire dataclass. Golden bytes prove the closed gate.
3. **Registry.** Lock, TTL, LRU, idempotent mint without TTL extension, first-digest compare-and-set.
4. **Availability.** The `local_media` eligibility member (floor `0.21.5` / `2026.9.24`, three native probe rows, depends on read, not on send) plus an in-memory media-chain coherence and binding check (D-M4). It is computed at listener open and does no disk work, reads no build list, manifest, fingerprint or Git SHA, and sets no process latch. Owner-device gate and default-off flag remain.
5. **Route.** Order per LM-10 (the gate step reads owner, flag and `media_available()`). Initial per-bot grant runs on the shared default executor with the existing ERR-3 mapping. Phase one and phase two run on the dedicated 4-worker executor with copied `ContextVar`s and one shared 20 s deadline. Phase two takes a worker permit without queueing (busy is `429`, no retry). Then, with no `await` before `prepare`, only the synchronous bearer, owner, gate, TTL and digest steps run on the loop.
6. **Permits.** A worker permit is released by its future's done callback, including after cancellation. The buffer permit (the instance admission permit) spans both futures and the handler `finally`; the device permit shares that lifetime.
7. **Streaming.** 64 KiB slices within one 30 s deadline including EOF; abort after `prepare` on any failure; return only after EOF or abort.
8. **Conformance.** [`HMP_V1_CONFORMANCE.md`](../../docs/architecture/contracts/HMP_V1_CONFORMANCE.md) lists every future test as unimplemented until it exists.

## Test plan

Each test must fail when its named guard is removed. Unit tests use a fake bridge; exact-build tests use disposable homes with the network denied and clearly synthetic paths.

| ID | Subject | Guard mutated |
| --- | --- | --- |
| T1 | Gate closed: golden bytes for RO-3, RO-6, SES-2, SES-2a; candidate not serialized | emit regardless; serialize candidate |
| T2 | Cross-device, user, profile, expired, evicted: one 404 shape | drop one binding field |
| T3 | Revoke between worker return and the loop check: existing 401, no bytes | skip loop bearer check |
| T4 | Compression, rewind, retire; restored identical row 200; changed content 404 | skip rescan |
| T5 | Phone conversation replaced 404; non-canonical Bot Chat no descriptor | skip kind recheck |
| T6 | Assistant `MEDIA:` or Markdown: no descriptor, no read | parse assistant text |
| T7 | `image` outside lexical `<home>/cache/images/`: no descriptor; forced into registry gives 404 | relax derivation |
| T8 | File replaced after first 200 gives 404; concurrent first fetches serve at most one digest | skip CAS |
| T9 | Causal changes between phase-one return and phase-two check give 404; initial grant refusals keep ERR-3; loop flips refuse; busy phase two gives 429; shared 20 s deadline; residual not tested as refused | skip phase two; merge phases; native call on loop; queue permit |
| T10 | Third device or fifth instance gives 429; permits held through cancellation | release on cancel |
| T11 | Slow reader and EOF stall abort at 30 s; no return before EOF | return a buffered response |
| T12 | Four active fetches; four cancelled late workers block then release; synthetic 4 x 8 MiB against provisional ceilings | failure changes code, not ceilings |
| T13 | Query, body, HEAD, `Range`: 400/404 or full 200; exact headers | permit range or extra headers |
| T14 | Phone-side behavior (separate repository) | n/a in this tree |
| T15 | Logs and access log: closed enums only | log ref, path or digest |
| T16 | One test per error-table row plus causal negatives (revocation, cross-device, cross-profile, tip change, async cancel) | per row |
| T17 | `ContextVar` profile scope survives the dedicated executor in both phases | skip context copy |
| T18 | Eligibility and coherence closed states: below floor, missing probe row, split media chain close this listener only with a fixed outcome; a second coherent listener in the same process opens (no latch); use-time identity mismatch closes that listener until reopen; no media component reads a build list. See tasks A1-A14 | per case |

## Review gates

Independent review of the merged contract before server code; independent review of the exact candidate after implementation; owner-authorized qualification and device acceptance last. No gate is self-certified in this tree.
