# Local-media native phase and service sample — 2026-10-02

Status: one completed isolated native worker sample. **Not native HTTP serving,
full T12, phone or Linux delivery, integrated packaging, deployment or release
acceptance.** HMP production source and provisional memory limits were unchanged.

## Inputs and scope

- HMP source: `d924f28ab64eb9993af73f902ff5f5adf3555f33`, clean candidate,
  with 38 top-level Python files pinned to the accepted source manifest.
- Native Hermes: `8afaab3703e336d72a72c812dd2dd249f04f166a`, clean checkout.
- Protected relocated Python: 3.14.7. No dependency installation or live-home
  mutation. Fresh private homes, runtime and temporary directories per child.
- Independently accepted probe: SHA-256
  `5812039ac72b36c11df54d35c77b5ef1a9bd5a6d3cb644c25ba4b28e3e0da36b`.
- Private aggregate receipt: SHA-256
  `090b18a04b7185f131e169ae44a76c52a37097112d77b28a28b5a60d0f72463b`.
  All three modes passed strict result validation; checked before/after inputs
  matched. Raw fixtures and process streams remain private.

Real operations: native SessionDB public methods and registry acquisition,
complete read/bind, accepted HMP phase one and phase two, file/raster/payload
helpers, and MediaFetchService futures, permits, mailboxes and done callbacks.

Synthetic inputs: authorization runner, gateway directory/session routing and
store, device/instance identities, producer rows and image contents. The seed
uses two ten-session compression chains, 256 KiB prompts, four image tool rows,
two unrelated sessions and a database trio no larger than 48 MiB. Four copies
of a structurally valid 1×1 RGB PNG padded to exactly 8 MiB exercise payload
cost; this is not a representative image corpus or a physical codec check.

## Phase results

Both Bot Chat and Phone passed all nine required flags: exact payload and fresh
phase two; wrong-kind refusals in both phases; denied-grant refusals in both
phases; restored-grant phase two; changed-session phase two; and malformed-file
refusal. A fresh exact payload and positive phase two immediately before file
corruption made the malformed-file check causal. Fixture title/source and Phone
routing were restored through the declared checked paths.

| Scope | Positive phase one plus phase two elapsed |
| --- | ---: |
| Bot Chat | 38.966 ms |
| Phone | 39.556 ms |

These are single elapsed samples on this fixture, not latency percentiles or
worst-case limits. The positive-path cost snapshots each observed 120 public
`get_session` calls, six compression-lineage calls, three active-message reads,
three message reads and two holder acquisitions/releases. They do not cover
every refusal call. Counters remain observational and are not synchronized.

## Four-worker lifecycle and memory

Two synthetic devices held two leases each. Four actual phase-one workers
reached the barrier with exact payloads; a fifth admission was refused. Active
workers performed real phase-two calls before lease settlement. The cancelled
sample finished leases before workers returned, retained permits while the
futures were live and refused late publication. Futures were never cancelled.
Callbacks settled; no mailbox retained payloads and all leases were released.

| Sample | Traced peak | Conservative RSS increment | Traced bytes after GC/settlement |
| --- | ---: | ---: | ---: |
| Active | 41.858 MiB | 49.812 MiB | 143,091 |
| Cancelled lease | 41.230 MiB | 43.969 MiB | 144,972 |

All samples meet the unchanged provisional ceilings: traced peak ≤96 MiB,
RSS high-water minus current baseline ≤128 MiB, traced settlement <1 MiB.
These samples are not worst-case bounds for arbitrary native history. Cancellation
models `lease.finish()` and handler cleanup, not actual HTTP cancellation.
Tracked phase-two futures settle before shared native holders are released.

## Probe repairs and retained limits

Three preceding native attempts remain failed. Pure controls reproduced a probe
instrumentation collision: wrapping `os.stat` before the file helper captured
its platform-capability identities made supported reads refuse. The reviewed
repair preloads only that hash-pinned stdlib leaf before the audit; native
imports remain after audit installation and network denial. A reviewed one-line
repair initializes the genuine lazy bridge cache before asserting leaf identity.
Neither change alters production source or relaxes acceptance flags or limits.

Observed live-home events were zero and positive audit controls passed. The
protected audit categorizes absolute paths only: descriptor-relative cache
operations are not categorized. Zero events are not proof of complete I/O
coverage. Python audit/network hooks are not an OS sandbox and omit C-level
I/O. Clone checks omit regular venv site-package hashes; loaded native/other
module hash maps are discarded by this probe. Checked input equality is not
complete dependency immutability or protection against same-account races.

G-M1 native allocation/materialization, pruning and non-atomic observations,
G-M2 artifact authority and previously documented replacement/ABA residuals
remain. HTTP bearer/binder/final-section/stream lifetimes, full sampled native
T12, Linux, Android/iOS loading and codecs, packaging and release gates remain
open. The pinned source identifies this sample; it is not a runtime build
allowlist. No live flag, host install, phone build or external beta changed.
