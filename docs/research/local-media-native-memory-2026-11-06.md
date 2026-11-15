# Native-backed four-fetch memory sample — 2026-11-06

One fresh isolated Darwin run completed at HMP
`8f16c1f412321c88945a0910ffe4e7457a986bcd`, native
`ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df`, Python 3.14.9 and aiohttp 3.14.5.
It used real scratch SessionDB/registry and HMP HTTP routes, with explicitly
synthetic transport/owner/bot authority and compatibility. There was no live
plugin activation, real message or provider generation.

## Method

The existing serving/isolation/revocation controls ran first. Four additional
synthetic static PNGs of exactly 8 MiB were materialized with the real native
cache helper under restored private profile scope. One CRC-correct ancillary
chunk pads each image; structural acceptance is not a phone-decoder claim.

In each case, two requests on each of two scratch devices actually held all four
8 MiB buffers and all four workers. A fifth request from an independently
eligible third device returned 429 without starting another phase-one read.

- **Active:** phase-two workers were held after native phase-one reads. Gate
  release streamed four exact 8 MiB responses with matching headers and digest.
- **Cancelled:** workers were held after real native reading and before payload
  publication. Exactly four original server handler Tasks were cancelled; actual
  running Futures and all permits remained held. Gate release completed those
  original Futures with false publication results, empty released leases and no
  cancelled-client response/body. Automatic idempotent GET replay was disabled
  for the sample and restored after request settlement.

Clients ran in the measured process with at most 64 KiB streaming chunks and
incremental digest/count state. Their bounded overhead counts toward the limits;
this is conservative combined-process evidence, not an external-client network
test or an isolated native-allocation bound.

Each case has a separate tracemalloc session from before request creation through
full request/worker settlement and collection; there is no reset within either
case. Darwin `ru_maxrss` is cumulative. The reported increment subtracts that
case's current RSS baseline, not its prior high-water mark, so earlier preparation
or case peaks can conservatively increase a later increment.

## Observed values

| Case | Traced peak | RSS increment | Settled traced | Result |
|---|---:|---:|---:|---|
| Active | 42,702,643 bytes (40.72 MiB) | 41,615,360 bytes (39.69 MiB) | 210,295 bytes | Four 200 responses; 33,554,432 bytes |
| Cancelled, late workers | 42,648,222 bytes (40.67 MiB) | 12,533,760 bytes (11.95 MiB) | 66,985 bytes | Four cancelled handlers; no response/body |

Both satisfy the unchanged provisional **96 MiB traced peak** and **128 MiB RSS
increment** ceilings. Both recorded four held buffers, four held workers, four
phase-one starts and the fifth-request 429. Every service count returned to zero
after actual settlement; no late Future was cancelled to recover a permit.

Native borrows/releases balanced 46/46; the original database closed, scoped
sweep was zero, listener closed and actual owned workers joined. Seven total
cache-helper materializations include the three earlier small-image controls;
21 opaque registry entries remained within the unchanged production cap.
Eleven recorded commands reached known terminal state: nine exit 0 and two
expected absent-config exit 1, plus outer controller exit 0. There was no
observation expiry, replacement actor or settlement-only success.

Independent read-only review accepted all 28 artifact hashes/sizes/private modes,
12,185 native and 372 HMP source hashes and literal Git blob bindings, archive
commits, runtime, report and receipt. The reviewer performed no execution.
The source preflight's 114 guard/structure/fixture-driver tests passed separately;
they are not an additional native measurement.

## Limits and retained premises

The same explicitly disclosed fixture allowances remain: 28 synthetic absent
Linux probes on Darwin, three real names-only own-FD listings, two bounded public
OS metadata reads and zero unexpected audit denials. The final root-owned OS
metadata hash is `6151cb883e5b48d43a33d4d41956405a1cd502e0c8622319388d943e2cb804a1`.
These are Python audit guards and trusted-runtime premises, not an OS sandbox,
complete native-library IO observation or platform attestation.

The private immutable proof is `hermes-native-media-memory-proof-20261106.json`.
The [sample contract](../../specs/011-local-image-serving/NATIVE_MEMORY_SAMPLE.md)
records the exact mode and causal requirements. This completes the literal T12
sampled Darwin measurement row. The report deliberately retains `t12_qualified: false` and
`production_qualified: false`; no full release/platform qualification follows.
The bounded fixture history does not resolve G-M1's unbounded native history
materialization, accounting/pruning effects or non-atomic-read residuals.
Complete native binding-cost/concurrent-writer evidence, Linux serving, full
plugin loading, actual provider/deferred Desktop scope, phone display, owner
installation/flag and release acceptance remain open. No live settings, grants,
providers or deployments changed, and source pins never become version allowlists.
