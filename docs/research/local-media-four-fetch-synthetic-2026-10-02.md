# Local media: synthetic four-fetch memory sample

2026-10-02. **Synthetic macOS source evidence only. Native T12 release evidence
and physical-device delivery remain open.** The measurement ran against the
independently reviewed S5 source; source hashes are below.

## Method

A separate server process exercised the actual authenticated aiohttp route,
HermesReadBridge phases, scanner, leaf reader, raster structure check and registry
with synthetic native database fixtures and disposable files. Each image was
exactly 8 MiB and structurally accepted; this does not qualify a phone decoder.
Pairing, reference minting and file preparation preceded the memory baseline.
Four raw socket clients ran outside the server process, consuming bounded chunks
and checking byte counts/digests without accumulating image buffers.

- Active case: four actual phase-two workers held four independent image
  buffers. A fifth request from a third device got 429 without starting another
  phase-one worker. Releasing the workers streamed four exact 8 MiB responses
  with matching digests and all lease/worker/device counts returned to zero.
- Cancelled case: four actual phase-one workers were held after reading their
  buffers, before publication. Cancelling the four handlers cleared their
  mailboxes, but retained all worker/buffer/device permits. A fifth request got
  429 without additional work. Actual futures stayed uncancelled, dropped their
  late results, released all permits, and clients received no response/body.

Tracemalloc covered server allocations from before the requests through complete
release. RSS is macOS ru_maxrss minus the current baseline RSS: a conservative
observed increment, not an allocator guarantee or isolated native-call cost.

## Observed values

| Case | Traced peak | Conservative RSS increment | Settled traced memory | Result |
|---|---:|---:|---:|---|
| Active | 44,616,205 bytes (42.55 MiB) | 55,459,840 bytes (52.89 MiB) | 105,196 bytes | Four full 200 responses |
| Cancelled, late workers | 43,282,181 bytes (41.28 MiB) | 43,024,384 bytes (41.03 MiB) | 76,122 bytes | No response/body |

Both remained below the **unchanged** provisional 96 MiB traced peak and 128 MiB
RSS increment limits. The root-operated harness completed with exit 0; the
independent source reviewer inspected its full source and receipt but did not
rerun the measurement. Private receipts preserve the exact results and hashes.

## Candidate identity and limits

| Source | SHA-256 |
|---|---|
| adapter.py | 2f29797193fe878572f2e3202608a7c237356b4ebf70d77a8c0b2e8cb4e93737 |
| bridge.py | f59db72f9fd82ddd90ba5cee608d7de8950df70725bd0a0a08d4f3d35f4ee9ba |
| media_fetch.py | 5c85e05d5a1575026bbcf6c3ca19f0358c53d7ea4342ab12ed010598cbf87fda |
| media_payload.py | 01b2fca36b8922afe636c50f63f8d3aeff24a20e384a2a8cefec2bedbc7b8f87 |

This does not establish native Hermes materialization bounds, a native serving
fixture result, Linux serving, exact-sample native T12, network performance,
provider output compatibility, phone rendering or release readiness. Native
reads remain non-atomic and can allocate, flush accounting and prune (G-M1).
Stalled native workers retain their permits until real completion. No live home,
provider, installation, device or feature flag was involved.
