# Roadmap

HMP follows the [feature list](FEATURES.md) and the [upstream requests](NOUS_GATEWAY_OBSERVATIONS.md). Ordering can change as Hermes exposes new gateway contracts.

| Area | Next step | Dependency |
| --- | --- | --- |
| Compatibility | Attempt implemented features on versions at or above the supported minimum; diagnose actual feature failures. | Required native APIs, authorization and security checks; exact-build receipts are sampled evidence, never availability allowlists |
| Approvals and choices | Complete owner-local activation and physical card/answer acceptance for the independently reviewed minimum-version candidate. | Genuine runtime/device evidence; remaining shared-session gaps are recorded in the upstream requests |
| Priority approval notifications | Implement the accepted shared-ownership contract through a bounded native observer, resolve the close/registry evidence gap, then complete remote relay/HPKE, app and provider work. | [Desktop experiment](FEATURES.md#desktop-pending-approval-experiment-2026-10-03-utc); strict cleanup/resource review, new runtime evidence, explicit provisioning and device/release gates |
| Push cryptography | Complete native containment gates and independent Node/Python known-answer checks before consumer integration. | [151 unexecuted definitions](FEATURES.md#hpkejcs-vector-preparation); supervisor ownership repair accepted in source and 46 isolated synthetic controls passed; six pure codec methods / 33 subtests passed; actual trusted startup failures retained: v1 pre-fork descriptor refusal, v2 child setup failure with exact reap, v3 diagnostic attributes AS set to ValueError with no errno; supported fixed-limit runtime validation next; all crypto vectors remain unexecuted; no native startup or crypto qualification |
| Access and discovery hygiene | Complete native/device integration of the accepted combined scoped-key, device-list and full bounded inventory candidate. | [Access checkpoint](FEATURES.md#retained-access-and-availability-repairs); combined draft PR #96 passed exact-head CI (2,710 passed / 17 skipped); native/device integration and deployment remain pending |
| Host-local generated images | Complete native HTTP/T12/Linux and signed phone loading/codec acceptance after reviewed serving and renderer slices. | Bounded authorized output delivery; documented native materialization/history gaps |
| Phone photo/file attachments | Freeze encrypted staging after reviewed and tested pure codecs and implement shared slot/CAS and bounded picker/tray/custody; preserve bot/profile/instance authority. | Pure interfaces frozen; focused Python 56 + 115 regression and Dart 71 checks passed. [Inspected Phone atomic admission gap](FEATURES.md#phone-attachment-admission-checkpoint-2026-10-03), portable validator, own-row readback and complete-flow evidence remain open; Desktop multimodal gap separate |
| Bot tabs | Show and create the same tabs Desktop sees. | Shared server-side tab registry |
| Updates | Replace polling with a session change feed when available. | Hermes gateway event or long-poll API |
| Voice and screen | Add client features when authenticated API server routes are available. | Upstream routes and access controls |

Behavior changes belong in focused Spec Kit feature specs and must update the wire contract when applicable.

## Ownership and attachment source progress (2026-10-03 UTC)

### Desktop ownership seam

[HMP draft #97](https://github.com/MahdiHedhli/hermes-hmp/pull/97) at
`b65f6aa` adds the reviewed tri-state Desktop ownership port: `owned`, `unowned`
and `unknown`. The production default cannot observe. Unknown ownership hides
Bot approval cards; independent Phone cards and settled replay/conflict/expiry
handling remain. Open Bot answers check the injected port under their row lock
and cannot call the resolver for owned or unknown state.

Root passed 225 focused fake-port cases and the full HMP unit suite
(2,394 passed, 15 skipped). Three deliberately removed guards each failed their
targeted assertion. Exact-head [hosted CI](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37126002690)
passed lint, unit/tool tests, plugin surface, log hygiene and privacy checks.
The earlier 220-pass/5-fail fixture run is retained; its test-only repairs and
a snapshot file-mode correction are documented in the private evidence.

This draft is a source foundation, not a deployable ownership provider. No
native registry observer is included, and the point-in-time check/use race
remains open. It does not verify genuine Desktop interleaving, urgent
notification delivery, native approval coverage or physical-device behavior.

### Attachment parser review

The Python/Dart attachment DTO, hash, pending-record codec and declarative ports
are authored in isolated branches. Independent review found that the Python
raw parser checks object/member and array bounds during or after generic JSON
decoding, while the accepted contract requires them before decoding. This
source defect must be repaired and reviewed before candidate test execution.
No upload route, picker, native admission, custody store, encrypted staging
adapter or operational attachment Send is enabled.

### Push diagnostic test repair

A separate test copy repaired the missing-resource diagnostic fixture by using
an explicit delegate rather than a Mock side effect for builtin `getattr`.
All 20 guarded synthetic collector cases then passed with zero boundary
refusals; all 358 source/history pins matched after execution. The original
19-pass/1-error result remains retained. This verifies the mocked diagnostic
contract only: the actual macOS fixed-AS setup failure is unchanged, later
startup controls and 151 crypto case definitions remain unexecuted, and no
native resource, relay, provider or notification-delivery readiness is claimed.

## Attachment codec verification progress (2026-10-03 UTC)

The independently reviewed pure attachment candidate now has actual focused results on the
exact cleanup revision:

- **Python: 56 attachment cases passed**, including structural bounds before generic JSON
  decoding, exact UTF-8/hash vectors, duplicate-key and fixed-error controls.
- **Python: 115 existing contract/module regression checks passed**, covering table fidelity
  and the declared module inventory/import surface.
- **Dart: 71 attachment cases passed**, including combined/legacy pending-record fidelity,
  phase/classifier controls, immutable values and all 64 reference suffixes.

The first Dart run recorded **69 passes and one failure**: a noncanonical reference suffix
exposed an input-bearing Base64 exception instead of the fixed domain error. That failure is
preserved. A separately reviewed two-file repair rejects noncanonical suffixes before decoding
and maps decoder failures to the fixed error. The subsequent 71-case run passed; this resolves
that defect in the unreleased candidate without claiming a deployed attachment capability.

These are focused pure-codec results, not full CI, native admission, file-content validation or
physical-device proof. The subsequent cleanup preserved behavior and assertions under independent
review, then passed all 56 + 115 Python and 71 Dart checks again. Root Ruff checks on four Python
paths and strict Dart analysis on all eight new source/test/port paths are clean. No rules were
waived; the original failure and earlier diagnostics remain preserved as historical evidence.

The mobile **+** picker, encrypted asset storage, shared message-ID/CAS adapter, validated
upload/send routes, native admission and authorized own-row readback still require implementation
and separate verification. Local host `MEDIA:` output remains blocked by its provenance/read
authority gap. No upload route, device/provider qualification or release availability is implied.
