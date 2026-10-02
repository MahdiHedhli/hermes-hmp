# Complete local-media binding: sampled native evidence (2026-10-02)

## Scope

Root ran the independently reviewed r2 measurement harness against disposable native Hermes
`8afaab3703e336d72a72c812dd2dd249f04f166a` and locked Python 3.14.7. The 17 supplied HMP
source pins and two reviewed harness foundations matched before and after. HMP's measured
base was `b07890ec7af4e773f575e13b3db801aa1d3e5fd3`: genuine Reads media twins, complete
HermesReadBridge.bind_media_batch, classification and registry mint. The bridge/read logic is
byte-identical to the subsequent S4 source, but no descriptor route or fetch route was measured.
Gateway routing, authorization and Phone-store inputs were synthetic. Native SessionDB reads
and writes and shared-registry acquire/release were genuine. Python-level network denial is
not an OS sandbox; loaded-source and no-live-home audit receipts were checked.

## Results

Preflight and the full run both completed with semantic assertions passing. Full run: 58 child
steps, 9,686 explicit report checks, zero failed checks or codes, no stopped/refused execution,
unchanged native/HMP/foundation/runtime inputs, and disposable scratch cleanup confirmed.
Root additionally rechecked all 1,000 first/second outcomes, including refusal reason sets.

- 72 timing cells, 44 Python allocation trace cells, 20 fresh-process RSS rows.
- 500 writer phases: 236 expected refusals (194 native DB mutations, 42 synthetic store flips),
  100 accepted controls, 54 accepts before their observation window, 60 accepted residual-window
  cases and 50 accepted ABA controls. All phases committed and both outcomes matched expectations.
  Accepted residual/ABA cases are observed limitations, never detections or fixes.
- Public native `system_prompt` reads verify 262,144 exact characters in each declared session:
  four distinct prompts in the two-session sample and 196 in the 98-session sample. Canonical
  title-holder prompt and unprompted extras were checked. The earlier r1 report's zero prompt
  field was a measurement defect; r1 is retained and does not establish the large-prompt result.

For 128 candidates in the 258-row shape, median complete binding cost over three measured
runs after one warmup was:

| Lineage and prompt shape | Bot Chat | Phone |
| --- | ---: | ---: |
| 2 sessions, no large prompt | 6.084 ms | 6.122 ms |
| 98 sessions, no large prompt | 68.577 ms | 69.408 ms |
| 98 sessions, 262,144 characters per session | 155.617 ms | 156.848 ms |

This is sampled latency, not a ceiling. Maximum measured Python traced binding peak above
baseline was 26,772,332 bytes. Native C allocations are outside tracemalloc; RSS is separate.
The mint-memory stages use a private modeled loop with shared field objects and before-GC
measurements; they do not measure production event-loop latency or retained request buffers.

## Remaining gates and upstream limits

This evidence does not establish S4 route cost, S5 two-phase fetching, four concurrent 8 MiB
buffers, T12 ceilings, Linux integration, physical phone behavior, live activation or deployment.
No build allowlist, manifest or admission threshold follows. Minimum version and required APIs
remain the runtime policy. Non-atomic history and eligibility reads leave the documented last-check
window and ABA limitations. Unbounded native session/prompt materialization, token-delta flushing
and store pruning remain G-M1; a stable scoped artifact/provenance interface remains G-M2.

Independent source review accepted the finite harness repair; this sampled execution is root
evidence only. No raw session row, path, name, content, reference, image or private identifier is
published. S5 must separately prove its bounded executor, cancellation lifetimes and streaming.
