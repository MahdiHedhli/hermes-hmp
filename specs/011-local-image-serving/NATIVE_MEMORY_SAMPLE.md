# Native four-fetch memory sample

This optional fixture mode measures the existing native-backed HMP image route
with synthetic files, scratch native SessionDB/registry and synthetic transport,
owner, bot and compatibility authority. It activates no live plugin or provider.
It leaves the production 8 MiB image bound, four workers/buffers, two buffers per
device, 20-second work deadline and 30-second streaming deadline unchanged.

## Cases and observations required

After the ordinary serving/isolation/revocation controls, the real pinned native
cache helper materializes four fixed synthetic, CRC-correct static PNGs of
exactly 8 MiB. This qualifies structural fixtures, not a phone image decoder or
provider generation. Three freshly paired scratch devices each mint their own
references before either measurement. No unverified device, live credential or
real message is used.

1. **Active:** two requests on each of two devices hold all four real buffers
   while their phase-two workers wait. Service state must be `(4, 4, 2)` and
   four native phase-one reads must actually have started. A fifth request from
   the independently eligible third device must return 429 without a new read.
   Releasing the gate must stream four exact 8 MiB responses with expected
   headers, byte counts and SHA-256 values.
2. **Cancelled, late workers:** hold four workers after actual native phase-one
   reading and before mailbox publication. Cancel exactly their original server
   handler Tasks. All four buffers/worker/device permits and actual uncancelled
   running Futures must remain held; the fifth-request control again refuses
   without new phase-one work. Release only the original gate, then verify every
   Future completes without cancellation and returns false, every lease is
   finished/released with no payload, and all service counts return to zero.
   No cancelled client receives an HTTP response or image body. Pinned aiohttp's
   automatic idempotent-request replay is disabled only for this sample and
   restored after actual request settlement.

Streaming clients run in the measured process, read at most 64 KiB per chunk,
and retain only incremental digest/count state. Their bounded overhead counts
toward the server limits. Thus a pass is a conservative combined-process sample,
not an isolated native allocation bound or an external-client network test.

Each case starts a fresh tracemalloc session before request creation and keeps it
through gate release, complete request/worker settlement and collection. No reset
occurs within a case. Each must actually hold at least four image buffers in the
traced heap; traced peak must be at most the unchanged **96 MiB** provisional
ceiling. Darwin current RSS is sampled for this process with pinned psutil;
`ru_maxrss - baseline_current_rss` must be at most the unchanged **128 MiB**
incremental ceiling. RSS high-water is cumulative: earlier preparation/active
peaks can conservatively increase the reported increment in a later case.
The method does not subtract a prior high-water mark to make a smaller result.

The observation schema is closed, integer-only and requires both cases, four
held buffers/workers, exact response/body/cancellation counts and refusal controls.
Only an explicit boolean sample mode accepts it. Normal serving reports retain
their original narrower schema and limits. Source copies, import-origin guards,
audit restrictions, owned command observation budget, original actor settlement,
source/runtime binding and database/listener/worker cleanup are unchanged.

## Acceptance scope

Root's 114 guard/structure/fixture-driver checks pass before native execution.
Independent read-only source review accepted one fresh isolated sample, without
reviewer execution. Native memory execution and artifact readback are pending
until a separately recorded terminal outcome. The existing `t12_qualified` and
`production_qualified` report fields remain false: an observation does not grant
platform, installation, provider, phone, release or live runtime authority.

Failure changes the implementation or identifies an unmet prerequisite; it never
raises a ceiling, changes a production deadline, replaces an unsettled actor or
turns delayed cleanup into a successful observation. Earlier attempts remain
preserved with exact terminal outcomes.
