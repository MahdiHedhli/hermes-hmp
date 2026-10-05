# Gateway observations for Nous Research

## Feature priority and host-image recovery checkpoint (October 5, 2026)

The owner-selected order remains **device-local bot sections and static icons**,
then **host-local chat images**, while essential release checks continue in
parallel. LB1 has reviewed local source and Android code 4/iOS 2026100403 build
candidates. Physical organization, sealed persistence, cold reload and accessibility
checks remain pending; those artifacts predate the later host-image changes.

The host-image applied-read prerequisite is locally committed at `ee519d1`.
Its 161 core and 10 logger checks passed, with clean scoped strict analysis.
The Bot Chat recovery adapter is locally committed at `e173f47` after 195
focused synthetic/fake app checks and clean strict analysis of five changed files.
Independent terminal review accepted the exact source and execution evidence. These checks do not establish native production descriptors, host serving,
phone codec/loading, signed device functionality or release readiness.

Recovery occurs only on explicit Retry after a completed not-found image load.
It uses a separate, applied transcript read scoped to the current owner, instance,
profile and canonical session; only a proven changed tool-result descriptor allows
one binary refetch. An unchanged descriptor stays unavailable without a refetch.
Other failures and legacy descriptors without a tool-call identity retain ordinary
binary Retry. The two-operation budget includes cancelled work until it actually
settles. Exact row/session/access loss clears card pixels and viewer clones.
Assistant MEDIA paths remain text and never authorize arbitrary host file reads.

In the parallel release lane, structural BundleTool validation passed for the
separate, existing Android code 3 AAB (`7ef4bdb`, source `255280b`) and its bounded
execution evidence was independently accepted. The earlier failed helper and
consumer attempts remain preserved; their exact VerifyError cause is unresolved.
This pass does not qualify the newer feature artifacts or close signature-reader,
physical-device, operational-security, provider/Data safety or reviewer-access
gates. No source history, host configuration/grant/provider change, new install,
store upload/submission, Support resend or report Send is claimed here.


## Current policy and source checkpoint (2026-10-01)

The HMP owner replaced exact-build runtime allowlists with a minimum supported Hermes
version policy: session reads and browsing from `0.21.4` (`2026.9.21`); send, jobs and
model from `0.21.5` (`2026.9.24`); later or unknown builds attempt the required APIs.
Exact commit or fingerprint tests are sample evidence. Reviewed HMP source
[`4d6863e`](https://github.com/MahdiHedhli/hermes-hmp/tree/4d6863ef8a311462adb68fc82dd3835657739f81)
([spec 013](https://github.com/MahdiHedhli/hermes-hmp/tree/4d6863ef8a311462adb68fc82dd3835657739f81/specs/013-minimum-version-compatibility))
implements it and is active on an owner Linux host. The native graceful restart completed,
and the fresh running gateway, matching listener process, expected TLS identity and per-bot
health were verified. Actual job execution and per-phone controls remain separate checks. The version stamp is
authoritative before the literal `__version__`, then `release_date`. Send and session
browsing both need `SessionDB.get_session`. The stable interfaces requested below remain
useful because a version number cannot prove behavior. The installed baseline has no
approval lane. The integrated minimum-policy approval candidate passed independent source review (spec 034),
including a bounded setup-wording correction and three added defensive regressions verified by root.
Its corrected two-sample native matrix and private packaging are recorded below; deployment remains pending. The app-side lifecycle fix is
[`3cfe4d0`](https://github.com/MahdiHedhli/HermesBotMobile/commit/3cfe4d0), installed
in iPhone dogfood build `2026100202`; physical behavior still awaits owner testing.

The app's [governance amendment](https://github.com/MahdiHedhli/HermesBotMobile/commit/3cd9cf80412167c5d708b2e246cbf7cf61e52a13)
now records this owner policy in the constitution, Master Plan, Beta Plan and
owner decisions. Runtime support and tested-sample evidence are distinct;
authentication, authorization, API availability, idempotency and independent
review remain required. This documentation does not convert a legacy runtime
gate or make unfinished approval/media transport available.

## Mobile availability and draft-recovery review checkpoint (2026-10-01)

The visible instance-switcher heartbeat and Dismiss draft recovery are independently
reviewed source in [app draft #66](https://github.com/MahdiHedhli/HermesBotMobile/pull/66)
at `097f4a1`, now installed in owner iPhone dogfood build `2026100203`.
Independent review reproduced bounded client defects in shared
credential retirement from an unauthenticated ready answer, stale probe quarantine,
delivery-notice lifetime on reopen, ID redaction and saved success timestamps after
lifecycle changes. All five repairs passed independent delta review and root source acceptance.
Five permanent real-controller and Navigator tests cover signal lifetime, reopen and queued
replacement; root reran those and sixteen released-draft cases (21 passed). These are
client responsibilities, not a request for upstream to remove authorization checks.
Server transcript rows remain authoritative; matching text alone cannot identify an
ambiguous send, and original send evidence must survive refresh before a retry.

The approval-alert handoff foundation now includes the independently accepted paired timer-ownership
repair. It is published at [`6cfd688`](https://github.com/MahdiHedhli/HermesBotMobile/commit/6cfd6880e56dac3665f3df7e10f49a17141e8d44);
root verified 1,328 client/machine tests (one real-server fixture skip), seven required causal
mutants and static scans. It remains unwired and is absent from latest installed build `2026100204`.
Physical draft recovery remains open: the owner reported a message surviving refresh,
but its build and whether the row returns from canonical server history are not yet confirmed.
No public release, operational approvals or push-delivery result follows.

A subsequent source diagnostic found a client contract gap: explicit refresh reloads the
transcript but does not reconcile a dismissed send's original delivery ID. The app repair is
independently reviewed and published at [app `0ae5667`](https://github.com/MahdiHedhli/HermesBotMobile/commit/0ae5667bea8b1e339517823471e49834f2c423e3),
using one read-only original-ID status lookup with no automatic resend, no text-equality proof
and no deletion of server history. Signed owner dogfood build `2026100204` is installed and its
version verified. Root passed the three explicit-refresh invariant cases; independent review
passed 266 selected client cases, and the final dismiss file passed 37. A causal revocation
regression prevents silently swallowing a definitive lifecycle answer. Physical behavior awaits
owner testing. This is a client repair, not an upstream defect.

## Bot Chat send identity and Dismiss follow-up (2026-10-02)

The owner confirms that Dismiss restores the draft, while an ordinary user bubble remains.
The screenshot does not identify its build. Source inspection of app `0ae5667` shows that
Bot Chat renders host snapshot/live-tail rows, not optimistic local user bubbles. Preserving
those rows is necessary; a text match cannot identify an individual attempt.

On inspected HMP `4d6863e` and `150bd0f`, the DS-7 session-chat request sends text without the
phone's caller message ID. On Hermes `ca705dbf`, the session-chat endpoint does not forward an
optional caller ID to user-row persistence or Desktop live-mailbox delivery. HMP's history
parser can expose an ID from a stamped `platform_message_id`, but this inspected Bot Chat
send path does not produce the stamp. The separate candidate Phone-chat path is different;
this is not a claim that all HMP-originated rows lack IDs. DS-8 status remains independent
of row correlation. Its unresolved outcomes must retain the original evidence.

A generic optional caller-message identity preserved across both native session-chat routes
would let HMP reconcile an exact history row. The interface needs defined profile/session
scoping, restart deduplication, queued delivery and acknowledgement semantics. This is an
upstream API gap, not a reason to delete host rows by matching text or bypass authorization.
The current reply-derived `message_id` also does not reliably identify a user row; its client
comment needs correction. No core patch or follow-up runtime fix has been deployed.
See the [bounded source diagnosis and required verification](https://github.com/MahdiHedhli/HermesBotMobile/blob/d8b0f55/docs/research/bot-chat-send-identity-gap-2026-10-02.md).
The user-visible bug remains open.

## Approval admission and notification findings (2026-10-02)

The spec 034 candidate removes the approval exact-build runtime gate while retaining actual
authorization, explicit settings, required APIs and separate Bot Chat/Phone-chat availability.
Independent source review accepted it at [`150bd0f`](https://github.com/MahdiHedhli/hermes-hmp/commit/150bd0f1535b41495e5fc31ded128b9452221052) ([draft #73](https://github.com/MahdiHedhli/hermes-hmp/pull/73)); CI passed at that head. Locked native preflight, imports and capability probes passed on two samples. The first 13-case approval attempt failed in setup before any case body: our fixture builder still required a fingerprint that the minimum-policy gate does not emit. The bounded test-tool correction at `2c153e2` has independent source acceptance; root passed 166 fixture-tool cases and 17 final focused cases, plus configured lint and privacy checks. The corrected isolated matrix has now passed all 13 selected cases on each prepared sample: `8afaab37` on locked Python 3.14.7 and release-floor `f97608f1` on locked Python 3.11.15, with zero skips and unchanged candidate/protected inputs. The floor sample lacks the Bot Chat notifier; its dependent cases are negative availability checks, not evidence of operational cards. Root has prepared an exact private source export from `150bd0f`: all 239 files match, including 32 runtime files, with no manifest changes and private custody modes. The [packaging record](https://github.com/MahdiHedhli/hermes-hmp/blob/b1956b2/docs/research/approval-minimum-owner-package-2026-10-02.md) distinguishes this unsigned copy from installation. Deployment, an additional candidate `ca705dbf` run and physical card/answer behavior remain unperformed. This is our test setup defect, not an upstream capability failure. The installed
`4d6863e` baseline remains unchanged and has no approval lane.

On inspected Hermes `f97608f1`, `8afaab37` and `ac0cfa7d`, `retire_clarify_card` is optional
hook documentation on `BasePlatformAdapter`, not a required base method. The actual gateway
resolves the adapter's optional hook. Requiring that attribute on the base class would
incorrectly disable Phone chat. This is a source finding on those samples, not a universal
private-API guarantee.

The notification registration/issuer/resolver/relay design (spec 014) is independently reviewed
in [draft #74](https://github.com/MahdiHedhli/hermes-hmp/pull/74). It preserves Desktop-owned prompt
visibility, the accepted app resolver interface, post-commit cleanup that cannot roll back revocation,
bounded registration generations and explicit error-envelope additions. Its prerequisite is now
accepted at `66874cf`, with push allocated contract section 7f (media already owns 7e).

The separate insertion, authoritative settlement and shared visibility inputs (015) are independently
source accepted at [`6a139ba`](https://github.com/MahdiHedhli/hermes-hmp/commit/6a139bae6646eb6e7584336c94ef611609833fe3)
in [draft #76](https://github.com/MahdiHedhli/hermes-hmp/pull/76), with handoff record `b0fe113`.
Root passed 482 final focused cases with 3 explained skips and 2,004 complete source cases with
16 explained native/Python-version skips. Fifteen final causal mutants failed assertions, in
addition to earlier component checks whose counts overlap. Transformation/collection errors were
retained and excluded. Replay adjacency is source-reading evidence; its semantically equivalent
mutant survives. Local expiry, generation closure, binding changes and run completion remain
non-authoritative, and no authorization or native answer authority was added.

The inert issuer is independently source-accepted in
[draft #82](https://github.com/MahdiHedhli/hermes-hmp/pull/82) at
`9611b5d8761f77edfa34d4d306d8aff29e934919`. It implements pure route/collapse
derivation and saved-hash validation, and async read-only push access to `k_grace`.
It never creates, repairs, chmods or logs a key; existing identity/token callers and
V1 transcript domains remain unchanged. Root and reviewer each passed the same
224 focused cases. Two independent derivation vectors match and seven causal scratch
mutants fail. The complete root locked suite passed 1,387 cases, with 10 existing
skips and one existing warning. A narrow independent amendment review accepted the
explicit module-tree addition and showed unexpected modules are still refused.
These overlapping source checks do not establish registration authority or delivery.
The contract task audit at `ef94560` closes research/text only. The bounded storage
checkpoint below advances migration and post-commit cleanup; listener scheduling, live
settings, registration routes/writers, resolver, dispatch, relay/seal interoperability and app/native
integration remain implementation work; owner provisioning and physical delivery
remain pending. No additional upstream Hermes API is required by these pure helpers.

At that earlier amendment checkpoint, no production observer, registration route,
notification resolver or dispatcher was wired. The newer registration checkpoint
below adds source routes; the newer resolver and dispatcher checkpoints record their bounded acceptance. HTTPS transport and delivery remain unfinished. This amendment
has no native, provider or device acceptance, and no operational push exists. Initial alert scope
covers HMP Bot Chat and Phone-chat rows. The static
[cross-surface census](https://github.com/MahdiHedhli/hermes-hmp/blob/docs/nous-observations-sync/docs/research/approval-cross-channel-source-census-2026-10-02.md)
at Hermes `ca705dbf` confirms existing `pre_approval_request` / `post_approval_response`
observer hooks fire around CLI prompts and shared gateway waits. A loaded plugin can
observe them without a new generic approval callback; synchronous callbacks require
a bounded nonblocking handoff. Current HMP adapter/local-store inputs do not register
that consumer. CLI process loading and durable cross-surface lifecycle mapping remain
evidence/design work; observer events are not answer authority. Cron applies unattended
automatic policy, and clarify is separate. No generic upstream API gap is established
by this census. Provider setup and physical delivery remain pending.

## Approval push HTTPS client checkpoint (2026-10-03)

[Draft PR #88](https://github.com/MahdiHedhli/hermes-hmp/pull/88), source
`fcd10e0370be185a445f25a1f77ce1e6b7a1d62b`, adds the signed HTTPS client
and production adapter factory. Independent source review accepted the client
and its integrated independent synthetic vectors: all 52 frozen pins matched,
22 fixed-vector/DER reference cases passed, and a scratch raw-route framing
mutation failed. Root passed 277 focused and 2,562 full tests, with 16 existing
skips and one existing warning. Both exact-source hosted CI runs `37089728685` and `37089727146` passed.

The client requires standard certificate-chain and hostname validation; optional
leaf SPKI pins are additional constraints checked before HTTP request bytes. It
ignores proxy environment variables, refuses redirects, caps responses, signs
raw fields and distinguishes certain pre-write failure from post-write timeout
and ambiguous outcomes. Local HTTPS tests establish this source behavior. The
DER cases verify vetted primitive/reference classifications, not the separate
remote relay's verifier.

This supersedes the dispatcher checkpoint's pending-client source status only.
Remote relay/seal interoperability, app registration/taps, provider provisioning,
physical notification delivery and release remain unverified. No live host,
app, flag, grant, credential, provider or deployment changed. Push remains a
navigation hint and never authorizes an approval answer.

## Approval push dispatcher checkpoint (2026-10-03)

[Draft PR #87](https://github.com/MahdiHedhli/hermes-hmp/pull/87), source
`e6e20a61ddcaf44d76c73e0a1ff35688e8e27e96`, adds the bounded insertion
worker and listener lifecycle through an injected relay port. Independent v2
review accepted all 48 frozen source pins after resolving v1's recipient-order
defect: registration insertion order now remains correct when wall-clock
timestamps tie or move backwards. Focused verification passed 380 tests; the
full suite passed 2,486 tests with 16 existing skips and one existing warning.
Both exact-source hosted CI runs passed.

The worker bounds queued callbacks, recipients, concurrent requests, coalescing
slots and per-device counters; repeats current owner, grant, family, generation,
visibility and live-setting checks; restricts retry to certain pre-write failures
and relay `unavailable`; and applies feedback only to the matching active
registration. Listener close detaches the observer, cancels work and bounds client
shutdown. These tests use a fake relay port and establish source behavior only.

**Still open:** the T025 HTTPS/signing client and production adapter factory are
under development and independent review, with no accepted transport or delivery
claim yet. Relay/seal interoperability, app registration/taps, provider setup,
physical delivery, owner deployment choices and release gates remain incomplete.
No live host, app, credential, grant or provider was changed by this checkpoint.
The generation-ceiling disposition remains open. Push carries navigation hints
and never authorizes an approval answer.

## Approval push hint resolver checkpoint (2026-10-02)

HMP [draft #86](https://github.com/MahdiHedhli/hermes-hmp/pull/86), source
`ef11d01cdcda6194169fd16e4a64cfc4a0379e07`, adds the authenticated,
owner-gated `POST /push/hints/resolve` route and a 256-entry listener-local
hint map. Resolution is navigation only. It rechecks exact device/family,
registration H/G/hash, DELETE fence, prompt generation, bot grant and current
visibility after async boundaries; hidden or stale rows disclose nothing.
Only recorded authoritative settlement can return `not_pending`. Immutable
row snapshots now carry actual settlement time for the 60-second margin;
this additive input changes neither native answer authority nor AP3 wire data.

Root passed 463 focused and 2,389 full configured tests (16 existing/native
skips, one existing warning). Independent review passed 694 overlapping cases,
matched all 41 frozen hashes and detected four causal mutants: hidden visibility,
non-authoritative settlement, settlement margin and live hint collision. Counts
are not additive. Both hosted runs `37085947620` and `37085944710` passed on
the exact commit; configured lint and privacy/log/surface checks passed.

This accepts the bounded T023 source slice. Production insertion dispatch and
hint minting (T024), HTTPS/signing relay transport (T025), relay/seal and app
integration, owner provisioning, physical delivery and release remain open.
T022 is incomplete at feature scope. No host, phone, provider or release changed;
there was no operational push delivery at this resolver checkpoint. The later
dispatcher checkpoint above supersedes its source-consumer status; transport and
delivery remain incomplete. The separate dispatcher work was unreviewed
and is not credited by this checkpoint. Earlier checkpoints below preserve the
scope and unfinished work at their own dates.

## Approval push registration route checkpoint (2026-10-02)

HMP [draft #85](https://github.com/MahdiHedhli/hermes-hmp/pull/85), source
`71385bb5a7b9352cec62fbe44c7e20e8e90f90a4`, adds authenticated GET/PUT/DELETE
registration routes to the reviewed runtime. Effective approval ownership is
separate from controls grants. Reads expose no route; writers validate bounded
opaque seals, recheck liveness after awaits, enforce replay/CAS and advance G
once atomically. DELETE works independently of delivery gates; failed DELETE database writes
fence the route in listener memory. Future resolver and dispatcher consumers
must enforce that fence. The shared COMMIT-failure rollback defect is repaired
in this isolated source; no deployed store incident is claimed.

Root passed 247 focused and 2,285 full configured tests (16 existing/native skips,
one existing warning); independent review passed 326 overlapping cases and
verified all 33 frozen hashes before and after. Scratch mutations caught owner,
transactional liveness, CAS, replay-hash, COMMIT rollback and DELETE-fence
regressions. Both hosted CI runs `37084551333` and `37084527827` passed on the
exact source commit. Configured lint and privacy/log/surface checks passed.

T022 remains incomplete at full feature scope: resolver/dispatch, hint lifecycle,
relay and app/native integration are not supplied by these routes. The G-ceiling
contract tension and volatile-fence restart residual remain open. No live host,
phone, provider, provisioning or release changed; push delivery is not available.

## Approval push configuration and listener checkpoint (2026-10-02)

HMP [draft #84](https://github.com/MahdiHedhli/hermes-hmp/pull/84), source
`22e92b168ede7b8398a970fd58b5722ea27cc673`, composes reviewed approval inputs
with issuer/storage and adds strict live host-only push availability. Invalid keys,
audience, relay URL or configured pins close the lane; omitted pins remain distinct
from malformed pins. Existing approval authority and minimum-version behavior stay
intact. Maintenance runs before listener open and hourly, reads the non-repairing key
once off-loop, and yields only between committed bounded transactions. Stop cancels
and awaits maintenance. Missing keys skip only hash expiry; other cleanup continues.

Independent v1 review found empty URL query/fragment delimiters could misroute a
future appended endpoint. The repaired v2 rejects the literal delimiters; six scratch
mutant failures demonstrate regression coverage. Root and reviewer each passed the
same 149 focused cases. Root's complete locked suite passed 2,210 cases, with 16
existing/native-dependent skips and one existing warning; configured Ruff passed.
All 26 frozen hashes matched after tests. Counts overlap. Hosted CI remains a
separate exact-commit check.

At this earlier runtime checkpoint, registration routes/writers were unfinished;
the newer route checkpoint above records their source acceptance. Resolver,
observer/dispatch, relay/app integration, provider provisioning and physical
delivery remain unfinished. T020/T021/T022 stay
open at feature scope, including the documented G-ceiling disposition. This checkpoint
proves source and isolated listener/SQLite/key behavior only; it enables no delivery,
live host activation, new phone build or release.

## Approval push storage source checkpoint (2026-10-02)

HMP [draft #83](https://github.com/MahdiHedhli/hermes-hmp/pull/83), source
`d41f5e7b271338bd2af88f1674c3115d3d9c237b`, builds on the reviewed issuer.
It adds additive schema 3 migration, bounded generation/capacity and purge helpers,
a terminal REVOKED setter guard, and separate post-commit retirement at five existing
HMP cause sites. Retirement advances G, wipes the sealed/request/body fields and
records a device-prefix-only audit before a later purge deletes revoked rows.
Cause cleanup does not purge historical backlogs. An independent source review
accepted the third revision after two concrete recovery/bounding repairs; the earlier
rejected receipts remain preserved. Root and reviewer each passed the same 63 focused
cases, including 15 actual SQLite disk-full cases (five causes by three cleanup write
stages). Independent post-COMMIT reads prove recovery retirement is durable before
deletion; a scratch mutation that bypassed the active-state deletion guard was caught.
Root's full locked suite passed 1,450 cases, with 10 existing skips and one existing
warning. These counts overlap and prove only the tested source slice.

The integer-ceiling contract disposition remains open: at G = 2^53 - 1 an increment
fails closed with 503 and leaves the row/G unchanged, while unconditional capacity
reclamation and G-advance wording are in tension at that boundary. No overflow,
wrap, reset or invariant waiver was introduced. At this storage checkpoint, listener
scheduling and live configuration were unfinished; the newer checkpoint above reviews
those source changes. Registration routes/writers, resolver, dispatch, relay/app
interoperability, owner provisioning and device/release evidence remain unfinished. T020/T021/T022 are not marked complete. No new phone build, host
activation or operational push delivery follows from this checkpoint.

## Installer and local-media integration checkpoint (2026-10-02)

The exact `150bd0f` source export encountered a native installer critical finding in a
nonexecuting approval-probe input. The independently reviewed one-file repair
[draft #78](https://github.com/MahdiHedhli/hermes-hmp/pull/78), `c1d3d0b`, uses a relative synthetic
target while preserving real classification and fake-executor behavior. It passed all 32 required
changed-input checks on isolated native `8afaab37`; no command executes. Root made a fresh private
export of all 239 regular files and compared every file with Git objects. Its 32 runtime files are
byte-identical to `150bd0f`, and only the probe input differs. The original export is preserved.

The actual native `plugin-guard-v8` scanned that new export read-only inside the protected sandbox:
**caution, 121 findings, zero critical** (2 high, 112 medium, 7 low). All findings match the earlier
reviewed corrected-source scan. Both high findings were inspected individually; remaining groups
retain the recorded sampling limit. The scanner is enabled and protected inputs are unchanged.
See the [superseding packaging record](https://github.com/MahdiHedhli/hermes-hmp/blob/79508f7/docs/research/approval-minimum-owner-package-2026-10-02.md).
No live install, restart or physical card/answer acceptance occurred. This corrected package does
not contain the separate 015 amendment.

The old local-media branch has now been integrated inertly onto the converted minimum-version
base (`0cdbbf5`). The contract amendment (`028a946`) passed independent documentation and root
review. It removes runtime build-list/SHA/fingerprint admission while retaining required APIs,
owner access, listener-bound media object coherence, active-history provenance, digest/CAS and
file/raster bounds. The eligibility and offline-diagnostics slice now has independent source
acceptance at [`a4f347b`](https://github.com/MahdiHedhli/hermes-hmp/commit/a4f347b4add54fb50352e6a6863836668490bc95):
root and the reviewer each passed 368 focused cases with six existing native-fixture skips; the
new media file passed 61 cases without xfail. Eight root guard-removal mutations failed their
targeted assertions, with restored source passing; 13 selected tool tests and pinned lint/privacy
checks passed. The three native methods require the positional argument the bridge actually passes.
Media depends on read alone; a genuinely absent shared API can also close siblings whose own
tables need it. A compat `available` line is probe eligibility, not working image delivery.
Offline drafts are labelled operator reports, not attestations of requester or flag. The M3 listener
binding now has independent exact-candidate source acceptance at [`f737197`](https://github.com/MahdiHedhli/hermes-hmp/commit/f737197): genuine module/cache identities are retained per listener, an identity change closes only that listener until reopen, and bridge module/classes publish together under a lock. The default-off flag and owner checks remain separate requirements. At that M3 checkpoint no route emitted descriptors or fetched local images; the S4 source update below supersedes the descriptor status.
Root and the reviewer each passed 3047 unit cases, retaining three existing S4 contract-table failures and 16 native-dependent skips. The old qualification tests were explicitly retired or adapted; no unrelated skip or xfail was introduced. At that M3 checkpoint complete native binding cost, concurrent-writer and mint-memory evidence remained open; the sampled r2 evidence below supersedes that measurement status. Delivery review and device acceptance remain open. S4/S5 must snapshot and verify the listener-bound tuple at mint/fetch; a mutable context field alone supplies no new authority. Root restored the omitted 8-step/9-step/cycle coverage at [`b07890e`](https://github.com/MahdiHedhli/hermes-hmp/commit/b07890e): five focused cases passed, including four scratch-copy guard mutations detected by the property; production bytes are unchanged. This test-only result does not replace the earlier full-suite receipt. There is no green full-suite or image-delivery claim. Assistant `MEDIA:` text confers no file-read authority;
recognized native tool history will supply the proposed image card. Unbounded native materialization
and nontransactional session/message reads remain upstream gaps. The S6 text below is historical.

## Local image descriptor and sampled binding update (2026-10-02)

S4 source [`6b2fb82`](https://github.com/MahdiHedhli/hermes-hmp/commit/6b2fb82a1924e76f84a329dea5d75cdbe8462cbf)
is independently security-reviewed in [draft #79](https://github.com/MahdiHedhli/hermes-hmp/pull/79).
It emits optional image references on RO-3, RO-6, SES-2 and SES-2a through one listener-bound
registry. The read and one batch classification share a context-copying worker; optional failures
keep the exact successful text without rereading. Owner, flag, object identity and row/digest
bindings are checked before synchronous mint. Assistant MEDIA/Markdown grants no authority.

The independent source review reproduced 3,424 CI-shaped cases with 16 native-dependent skips
and an existing warning. Root reviewed the required status-document repair and seven added tests,
then reproduced 679 focused cases, including 110 descriptor cases. Added causal checks cover the
outer mint-failure boundary and request context copying. No fetch route or image bytes are delivered
by this slice. S5 two-phase fetching is being implemented; phone loading and physical verification
remain open, and the installed phone still shows host-local MEDIA as text.

The [r2 complete-binding sample](https://github.com/MahdiHedhli/hermes-hmp/blob/8f4e571/docs/research/local-media-complete-binding-sample-2026-10-02.md)
on disposable native `8afaab37` completed 58 child steps and 9,686 semantic checks, with unchanged
source/runtime inputs and cleanup confirmed. The repaired public system_prompt checks prove the
declared 262,144-character prompts, including 196 distinct prompts in the 98-session shape.
All 500 writer phases matched both expected outcomes: 194 native-mutation refusals, 42 synthetic
store refusals, accepted controls/pre-window cases, 60 accepted non-atomic residual-window cases
and 50 accepted ABA controls. These last two groups remain limitations, not fixes.

The measurements exercise genuine native reads/writes and HMP binding/mint with synthetic gateway
authority inputs. They do not prove route latency, four-fetch T12 memory, cancellation/streaming,
Linux serving, device behavior or deployment. Native C allocations are outside Python tracing.
Unbounded native materialization/pruning and non-atomic session/history reads remain upstream
G-M1; a stable scoped artifact/provenance interface remains G-M2. No build allowlist is introduced.

The spec 014 follow-up protocol review accepted its concurrency and availability clarifications
with two bounded source gates: a non-decreasing relay acceptance instant (prevent clock rollback
from reopening a purged nonce) and exact additional TLS leaf-SPKI pin grammar/trust semantics.
Those amendments are being written; no registration, relay, provider or device acceptance follows.
A notification remains a generic alert with no execution authority.

## Local image fetch source update (2026-10-02)

The earlier S5 implementation status is superseded by independent source
acceptance in [draft #80](https://github.com/MahdiHedhli/hermes-hmp/pull/80):
source `c9a47b7`, status-doc head `d924f28`. The always-registered authenticated
GET route retains owner and fresh per-bot grant checks, two native bridge
phases, listener-bound identities, active tool-history provenance, captured-home
lexical/leaf/raster bounds and first-served digest CAS. Four dedicated workers,
two per-device/four instance leases and actual-future accounting retain permits
through cancellation until the real workers finish. No assistant MEDIA text
authorizes a filesystem read.

Independent original and amendment reviews resolved fixed submission-error
mapping, complete new namespace binding and causal route-test gaps. Root's
fresh locked CI passed 3613 cases, with 16 existing native-dependent skips and
one existing warning. The reviewer reproduced 162 fetch/amendment plus 308
startup/layout cases. Nine root scratch-copy guard removals failed targeted
assertions; two misselected pytest nodes are excluded. All production/test
bytes stayed exact after integration with the accepted S4 test-only repair.

The [synthetic four-fetch sample](https://github.com/MahdiHedhli/hermes-hmp/blob/d924f28/docs/research/local-media-four-fetch-synthetic-2026-10-02.md)
used actual routes/bridge/leaf work, synthetic native DBs and four exact 8 MiB
structural images, with clients in a separate process. Active/cancelled traced
peaks were 42.55/41.28 MiB; conservative observed RSS increments were 52.89/41.03
MiB, below unchanged provisional limits. It checked fifth-request refusal and
permit retention until actual completion. This is macOS synthetic evidence,
**not native T12 release evidence or a phone codec result**.

Native serving/fetch cost/T12 samples, broader Linux serving, phone binary
loading, independent delivery review and owner-authorized activation/device
acceptance remain open. Native materialization/pruning and non-atomic reads
(G-M1), artifact authority (G-M2), ABA/torn-buffer and same-account replacement
residuals remain. No runtime build allowlist or live change is introduced.

### Mobile contract alignment (2026-10-02)

The mobile [spec 029 amendment](https://github.com/MahdiHedhli/HermesBotMobile/commit/57fb3394af8c61026074abf8ebe3387942d67a75)
has independent documentation acceptance. It removes stale exact-build runtime
admission wording and follows the HMP minimum-version/required-API policy, retaining
owner activation, per-bot grants, listener identity and image bounds. This is client
documentation alignment, not a new upstream requirement or serving result.
Phone image UI/controller wiring and physical delivery remain open. The combined
Bot Chat media / separate Phone screen source baseline has independent acceptance
in [mobile draft #68](https://github.com/MahdiHedhli/HermesBotMobile/pull/68); it does
not enable Phone image cards or change installed hosts/devices.

The [v2 Phone media contract](https://github.com/MahdiHedhli/HermesBotMobile/blob/4fa4764bbad7799850755ce4e7262b2fc38b0b28/specs/029-host-local-images/phone-media-contract.md)
now has independent architecture acceptance. Its separate media stamp/activity,
exact owned-viewer routing, actual applied-read proof and stable screen budget
preserve the existing send fences. Every participating card must retain its
original permit through the actual shared refresh Future, including cancellation
and binding replacement, plus fetch/decode settlement. This closes the design
gap where UI abandonment could outlive accounting while a read kept running.
The bounded controller/read ports (A5-P) and shared card/viewer prerequisites
(A5-V) now have independent source acceptance and are published at mobile
`ba0f619` in [draft #70](https://github.com/MahdiHedhli/HermesBotMobile/pull/70).
Root passed 218 focused client cases, seven dev-support, 12 logging and 112
card/viewer cases; independent P review passed 112 selected causal/preservation
cases and V review passed the 112 widget cases. These counts overlap. Accepted
source now captures media reads separately from sends, returns actual applied
window proof, exposes the exact owned-clone viewer seam and retains each original
card permit through actual refresh/fetch/decode termination even after UI loss.
Phone screen ownership/registration, stable final budget, actual controller
singleflight and fresh applied/current target-row checks now have independent
source-only acceptance at mobile `1a4641e`. Root passed 276 focused cases; the
independent review passed 122 overlapping cases and analysis, verifying all eight
frozen source pins. Combined hosted CI, native/host/device and release gates
remain open. This adds
no upstream Hermes API requirement or installed capability. Hosted mobile run `37060192148` failed the legacy S11 immediate-release expectation and inherited late-TLS case. A corrected S11 retains the original shared-read permit until terminal; root's isolated 42-case binding suite passes. Personal SDK paths in two handoffs were sanitized at `19a5ba6`, and hosted security hygiene passes in run `37061780872`, closing the current-document privacy finding. Historical Git bytes remain in public history. Historical source freeze pins are not current documentation-byte pins.

### Mobile public-image lifetime (2026-10-02)

MEDIA-C1 is a mobile resource-accounting defect, not a missing Hermes API. Repeated
public-image cancellation previously freed the visible count while injected DNS
work remained pending. Its bounded repair contracts have independent acceptance;
independent source review of initial candidate `5f98477` found one cleanup-error
issue, F1. Independent follow-up accepted `eb450db` and closed F1 plus the
demonstrated early-release/reset mechanism within the screen budget/caller-owned
API settlement boundary. The exact registry delta is separately accepted and
published in [mobile draft #69](https://github.com/MahdiHedhli/HermesBotMobile/pull/69)
(`4a93cc5`). Root passed 219 focused cases and nine-item analysis. Local serial
CI passed: client 1,191 / 1 skip, dev support 9, device key 155, app 925 / 3
skips; all analyzers/guards pass. Python CI 145 passes retains 81 prior cleanup
warnings. A failed overlapping run encountered checkout-mutating guard fixtures;
the generated lockfile was restored exactly before the passing serial run.
Hosted run `37054562001` on `4a93cc5` failed the successful late-TLS
delivery case after three seconds. Exact `a26aea6` diagnostic run `37062811599`
records `before-cancel/tlsFailure` then `timer-selection`, before successful TLS
delivery. The fixture trust anchors are under investigation; no cleanup failure
or resolved hosted result is inferred. Original timeouts and settlement
assertions remain. No deployment or release occurred.

A stronger loopback check found that raw close/peer EOF could leave the actual
Dart 3.12.2 TLS handshake Future pending. The candidate forwards a fixed cancellation
error through the SDK's public subscription API and joins caller-owned TLS, HTTP,
subscription and socket-close API Futures under a stable shared screen budget.
Causal cases include late socket ownership, held cleanup, redirects, real stalled
TLS cancel/deadline/dispose, successful HTTP body forwarding, wrong-host refusal
and cancellation before successful handshake delivery. Synthetic relay cancellation
controls are models; no held real SDK cancellation or physical-device result is
claimed. Private SDK filter quiescence and all OS allocations are outside this proof.
The F1 diagnostic reproduced a synthetic cancellation error escaping because the
SDK ignores its subscription cancellation Future; no native failure, crash or data
disclosure was observed. The amended candidate retains the exact original Future
and an immediately observing successful join, including synchronous throws. The
SDK-facing join cannot end early, and no-test-only-consumer regressions pass. Independent checks added eight causal cases and one no-consumer regression,
reusing 25 earlier cases for unchanged source. Source/registry acceptance does
not prove global or native allocation bounds; uncancellable work may hold slots
indefinitely, and different screen States/direct callers have separate budgets.
Installed app code is unchanged.
Standard PKI, hostname/address checks, explicit tap, media bounds and credential
exclusion remain unchanged. Phone activity/fresh-read architecture and host/native
serving/device gates remain separate. See the [mobile finding and checkpoint](https://github.com/MahdiHedhli/HermesBotMobile/blob/docs/a1-session-review/docs/research/public-image-cancel-accounting-2026-10-02.md).

### Native fetch probe diagnosis (2026-10-02)

Three isolated native phase-probe attempts ended in failure; none produced a
worker-memory receipt. Closed diagnostics on the latest attempt identified a
failed positive image payload for both Bot Chat and Phone, with valid pre/post
integrity metadata and no observed live-home events. These failed attempts do
not qualify serving or establish an upstream defect.

A separate stdlib-only control on the same interpreter reproduced an
instrumentation collision: the audit wrapped `os.stat` before the file leaf
captured its real capability identity. The leaf then reported an unsupported
platform. Loading the hash-pinned leaf first preserved its real capability
check and allowed an exact 8 MiB PNG read with the audit installed. Native
imports were absent from this control. The probe amendment retains audit
installation before native imports, restores the original fixture state, and
requires a positive fetch immediately before the corruption-refusal test.
Independent source review accepted the import-order and fixture amendment after
repairing a probe-only lazy-cache initialization error. The corrected isolated
native phase/service run completed with exact before/after checked inputs.

Both Bot Chat and Phone returned exact rehashed 8 MiB PNG payloads, passed fresh
phase two and refused the tested wrong-kind, denied-grant, changed-session and
malformed-file cases. Each corruption refusal followed an immediate successful
fetch. Four real service workers retained their permits until completion,
refused fifth admission, settled callbacks and released payload mailboxes. The
cancelled-lease sample refused late publication without cancelling the futures.

| Native worker sample | Traced peak | Conservative RSS increment | Traced bytes after settlement |
| --- | ---: | ---: | ---: |
| Active | 41.858 MiB | 49.812 MiB | 143,091 |
| Cancelled lease | 41.230 MiB | 43.969 MiB | 144,972 |

These values satisfy the unchanged provisional ceilings of 96 MiB traced peak,
128 MiB incremental RSS and less than 1 MiB traced settlement. This is one
bounded native sample with synthetic authority/routing/producer rows and a
padded PNG, not a worst-case bound or HTTP cancellation test. The three previous
attempts remain failed. The [sanitized sample record](docs/research/local-media-native-phase-service-2026-10-02.md)
separates the actual native methods and worker lifecycle from the synthetic
fixture and remaining gates.

The protected audit categorizes absolute paths only; descriptor-relative cache
operations are not categorized. Positive controls are not complete leaf-I/O
coverage. Python hooks, the finite loaded-source pins and runtime checks do not
prove an OS sandbox or complete dependency immutability. All memory limits,
native HTTP/T12, Linux, codec/device and release gates remain unchanged.

## Native observation and access diagnostics checkpoint (2026-10-01)

Source inspection on exact Hermes `8afaab37` confirms that a session lookup is not
necessarily a side-effect-free observation. `SessionStore.lookup_by_session_key` calls
`_entry_locked`, which can lazily load the store, create its directory and prune stale
routing entries. Pruning can save metadata. Separately, `SessionDB.get_session` and
`list_sessions_rich` can flush queued token deltas, and first database construction can
initialize or migrate schema. These are source findings, not observed live incidents.
HMP's native qualification uses disposable homes; a diagnostic must not treat these
helpers as guaranteed read-only operations. The owning source is
[session persistence](https://github.com/NousResearch/hermes-agent/blob/8afaab3703e336d72a72c812dd2dd249f04f166a/gateway/session_persistence.py#L219)
and [session reads](https://github.com/NousResearch/hermes-agent/blob/8afaab3703e336d72a72c812dd2dd249f04f166a/hermes_state_sessions.py#L786).

The local-media dependency census now proposes 69 native paths, distinguishing actual
read-path owners from producer-format evidence. Root verified 82 inspected source hashes.
This is a finite source proposal; recursive imports, external providers, runtime callable
ownership, the complete native binding cost and serving admission remain unqualified.
It adds no manifest entry and does not enable local image reads.

Separately, HMP needs clearer access diagnostics. A device's persistent controls grant,
per-bot authorization, host feature activation, build validation and profile endpoint
readiness are independent checks. Linux support does not establish all of them, and an
unvalidated newer build does not prove incompatibility. HMP can expose its own authenticated
device status and improve recovery wording without an upstream change; that contract is
being designed. It must preserve resource concealment, never grant privileges automatically
and never use a job-list or job execution as a health check.

**Secret-read uncertainty.** On both inspected `ca705dbf` and `8afaab37`,
`hydrate_profile_secret_sources` can return an empty mapping after a configuration
or external-source exception. The profile scope is then built from the remaining
available values, and `get_scoped_secret` returns its supplied default for a scoped
miss. HMP therefore cannot distinguish a genuinely absent API key from a failed
external-secret lookup using an empty string alone. A diagnostic must keep this case
`unknown`, rather than assert that setup is missing. The write gate remains closed
without a usable key. This is a source finding, not a live credential incident;
no native helper was executed for this inspection. See the exact-build
[hydration path](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/hermes_cli/env_loader.py#L114),
[scope construction](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/run.py#L1801)
and [scoped reader](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/_shared.py#L22).

## Local image contract checkpoint (2026-10-01)

Follow-up owner screenshots confirm the public CDN image renders while generated
host-local `MEDIA:` remains text. The independently reviewed local-image design is
now [recorded as an additive HMP draft contract](https://github.com/MahdiHedhli/hermes-hmp/blob/6186e55/docs/architecture/contracts/HMP_V1.md#7e-host-local-generated-images-v16-draft-not-implemented).
Reviewed components are published in [HMP draft #70](https://github.com/MahdiHedhli/hermes-hmp/pull/70) (`5e63839`) and [app draft #63](https://github.com/MahdiHedhli/HermesBotMobile/pull/63) (`8d32657`): bounded scanner/file/raster guards, a result parser, temporary reference registry, non-wire read carriers and candidate extraction, shared native query/read cores, typed descriptors, pinned reads and a tap-to-load card. Root and an independent reviewer each passed 833 focused HMP cases with three preexisting no-Hermes-build skips. Golden text bodies, native call events, baseline tables and observation sets were independently regenerated from `575a9bc`; unsupported media metadata preserves successful text. Production handlers do not select these optional media twins yet. The app's bounded one-refresh retry is accepted with 99 root card/screen cases and clean scoped analysis. Equal handles from idempotent minting require a freshly replaced target row under the unchanged instance/epoch binding; cancellation never auto-resumes. No serving route, qualified media entry, new phone build or public release is claimed.

The design derives device/profile/session-bound opaque handles from scoped successful tool
results; assistant paths never authorize file reads. Native checks stay off the event loop,
with a final native authorization/tip check followed by fresh bearer/owner checks before bytes.
The gap after the last native check is explicit because no atomic native authorization/session
snapshot API exists. Native lexical-path evidence is accepted for the exact-build synthetic
producer/layout below. Root's [Linux file-leaf run](https://github.com/MahdiHedhli/hermes-hmp/blob/c0f2343/docs/research/local-media-linux-leaf-evidence-2026-10-01.md)
passed 89 accepted tests and 91 supplemental real-kernel checks on non-root Linux CPython
3.14.7/tmpfs, with unchanged source and isolated cleanup. This qualifies only that file-reader
slice, not native serving, other filesystems or kernels, raster decoding or a phone build.

The descriptor-mint batch is independently reviewed inert source at `f1bc986`: 563 original
focused checks and 232 hardening/layout checks passed. Root's [exact-build component measurement](https://github.com/MahdiHedhli/hermes-hmp/blob/5e63839/docs/research/local-media-native-batch-cost-evidence-2026-10-01.md)
observed a median 71.93 ms for 128 selectors over 4096 near-budget rows, versus 9.111 seconds
in the prior separate sequential-scan fixture. Native page calls are 33 per batch rather than
4224, independent of selector count; all twelve native concurrent-writer controls passed.
A bounded 42.99 MB uncharged-content scenario and registry mint memory were measured separately.
These observations qualify neither full eligibility/handler cost nor allocation bounds, T12,
serving or a device. C6b source is accepted below; complete native binding cost and
request/process/device admission remain open. The
[conditional C6 design](https://github.com/MahdiHedhli/hermes-hmp/blob/f1bc986/specs/011-local-image-serving/ROOT_DECISIONS.md#c6-descriptor-mint-batch-freeze-2026-10-01)
keeps each fetch's single scan/recheck unchanged. No cache, registry hit or assistant path grants
authority.

The [S6 media gate design](https://github.com/MahdiHedhli/hermes-hmp/blob/f1bc986/specs/011-local-image-serving/ROOT_DECISIONS.md#s6-media-qualification-design-freeze-2026-10-01)
requires fresh native/HMP source equality and a process-wide primitive baseline preserved across
Hermes module reloads, with bounded no-follow reads and import-shadowing refusal. Independent
Opus design amendments are adopted; the inert gate source is now accepted as described below.
The bounded listener integration is now source-reviewed below. Native binding, runtime ownership and media entries remain open. This does not change or qualify the separate approval gate.

**Historical inert source scope (HMP `6d400af`; minimum-policy integration pending).** The inert S6a gate source (`e5e6d40`, module
`fb8ae21e...`) is accepted after an independent Opus review, one test-only repair and a delta
review; root and the reviewer passed 392 focused cases. Its manifest build list is empty and
the listener binding calls it only under the supported-read precondition; the empty manifest admits nothing. It keeps a persistent stdlib
`sys` anchor that survives module reload and alias homes, checks exact origin/loader/source
files, and does bounded descriptor-based source reads with fresh checks. The reviewed listener binding
enforces the supported-read precondition. Source-versus-bytecode/ABA, callee closure, kernel/Git
latency, same-account tampering, sub-interpreters and free-threaded runtimes remain open.

The [C6b binding design](https://github.com/MahdiHedhli/hermes-hmp/blob/0dd2a37/specs/011-local-image-serving/ROOT_DECISIONS.md#c6b-binding-design-freeze-2026-10-01)
is frozen after amendments A1-A5. A native public-helper replay on exact `8afaab37` passed 15
cases and 51 checks (23 accepted, 28 refused, including one known retitle accept). It ran no Agent,
lease, model or gateway, and it qualifies no media. Any native title writer that can produce this state can create metadata that looks like a
canonical lineage; the fixture demonstrated an operator retitle. On the
real flow the title moves to a visible compression child while the root stays hidden `1`.
The design therefore requires a unique native compression lineage equal to the parent chain,
and mint and fetch will share one classification helper that treats uncertainty in either kind as
closed. The inert binding source is independently accepted at `d1e55d2` after strict-walk
and own-Phone proof repairs; root passed 411 binding/layout cases. This is source acceptance
only: complete exact-native binding cost, actual Phone-path evidence and request/process/device
admission remain open. Three preexisting contract-table failures remain in the full unit suite;
a full-green suite is not claimed. The listener binding is now independently source-accepted
in [HMP draft #70](https://github.com/MahdiHedhli/hermes-hmp/pull/70) at `6d400af`.
Root and the independent delta reviewer passed 138 repaired cases, and the reviewer confirmed
13 causal mutant kills. Its preload binds actual module and class objects; split-package
observations close media availability. Concurrent first-load cache races can require a reload
or restart to recover. Source and bytecode, arbitrary callbacks and native cost remain distinct
limits. No production handler selects the media twins, and no manifest entry or serving build is
admitted. The native component cost evidence is unchanged
at `5e63839`; it is not a full binding cost, T12 or a scalar performance promise.

The [bounded producer fixture](https://github.com/MahdiHedhli/hermes-hmp/blob/f9c542b/docs/research/local-media-lexical-evidence-2026-10-01.md) now compares the raw persisted `image` string with the actual native routed-home helper's string plus `/cache/images/`, without normalizing the candidate. Root repeated three positive native flows on exact `8afaab37` (Desktop, Phone stand-in, deferred tool), retained private evidence, and passed 37 focused string/helper cases. All matched the selected profile prefix and one flat 128-byte-bounded name, not the foreign prefix; native source was clean and unchanged. This is one synthetic provider using real `save_b64_image`, one scratch layout and no live HMP media endpoint. Other producers/home spellings remain uncharacterized.

HMP is a mobile gateway plugin for Hermes. These are proposals for upstream discussion, not claims that Hermes currently provides every requested API. Findings were checked against Hermes `main` at `81f481b2` and the qualified older `8afaab37` build on 2026-09-28. Search, bot lifecycle, and plugin installation were rechecked against `main` at `39faafb6` on 2026-09-29; the approval session stream was rechecked at `ac0cfa7` on 2026-09-29. The Bot Mode baseline tag `v2026.8.31` was also inspected on 2026-09-29; later releases may differ. Chat media and attachment handling was checked against exact Hermes `ca705dbf7ef86425b381b542712aff310f1ee52c` on 2026-09-30, together with an owner-observed display result in HMP's own mobile app.

The [unified gateway research](https://github.com/MahdiHedhli/hermes-hmp/blob/main/HermesUnifiedGatewayResearch.md) and Nous's [one-gateway PR](https://github.com/NousResearch/hermes-agent/pull/106742) support one profile-scoped execution authority. The companion [entry-point plan](https://gist.github.com/unsupportedpastels/765f9d551ce88ee01630c18367763e75) puts a future mobile client behind an authenticated gateway API but treats remote entry as follow-on work. The requests below concern that remaining remote contract; they do not ask Nous to create another session owner.

| Area | Current constraint | Requested upstream contract |
| --- | --- | --- |
| Bot tabs | Desktop stores its bot tab list locally. A remote client cannot identify or create the same tabs. | Server-side tab metadata and list/create operations shared by Desktop and other clients. |
| Safe sends | The canonical Bot Chat has a live-owner mailbox, but other session chat routes do not use the same active-session lease. Session chat also lacks an idempotency key. | Apply the active-session lease to session chat and support retry-safe idempotency. |
| Forward compatibility | HMP's read bridge calls undocumented Hermes internals. Bot Chat reads still require a reviewed bridge fingerprint and exact Git SHA, so a newer but unreviewed build can be refused. An HMP-owned pairing path is in draft that warns but does not grant bot access on such a build. At the Bot Mode baseline tag `v2026.8.31`, 8 of the current bridge's 16 fingerprinted Hermes source paths do not exist, including the split gateway and session modules; merely accepting that version cannot make the present bridge work. An isolated exact-tag adapter fixture exercises the old platform registry, HMP's pinned-TLS listener, and HMP-owned pairing/token/revoke while Bot Chat and controls return the compatibility refusal. In a repeatable disposable two-profile gateway fixture, the full old gateway connected HMP, served both profiles, completed pairing with a certificate-pinned synthetic client, and still returned `/bots` 503 (`hermes_build_unsupported`). Its base Python environment lacked `aiohttp`, which Hermes treats as an optional messaging dependency and does not install from the plugin manifest; the isolated run installed the declared requirement before boot. The exact-tag source also contains a profile-home resolver that falls back to the root home for a missing or invalid explicit profile, so HMP must not substitute it for a fail-closed profile lookup. An isolated two-profile ingress probe found that the old adapter stamps a profile only when an explicit route matches; a matching `scope_id` alone does not stamp one. Its authorization check can use a transport-profile secret scope that differs from the routed runtime scope, and a routed allow-all scope would admit a never-enrolled user if evaluated without the transport stamp. These are scratch findings, not evidence of a qualified Bot Chat bridge or physical-device pairing. The release-watch fixture suite can qualify a build, but it is not part of the runtime-only plugin. A version number or import-signature probe alone cannot establish profile isolation and authorization behavior. | Expose versioned, authenticated, profile-scoped roster, canonical Bot Chat, authorization, and history contracts with declared capability guarantees. A missing, invalid, unserved, or unrouted explicit profile should be rejected rather than served from another home. Include the effective ingress authorization scope in that contract. HMP could then warn on an unvalidated newer release, exercise those supported contracts, and reserve fail-closed behavior for missing or failed capabilities rather than every new Git SHA. |
| Bot lifecycle | Profile creation is available to Desktop's TUI gateway and dashboard, while deletion uses the profile CLI or Desktop host. The gateway platform API server has no profile lifecycle routes. A profile by itself is not a Bot Mode bot with a canonical chat. | Authenticated, owner-scoped profile create/delete routes with explicit identity, partial-delete results, and a canonical Bot Chat outcome. |
| First Bot Chat | The API server can look up a hidden chat by exact title and create a titled session, but creation, hidden state, and profile-following behavior are not one atomic create-or-get operation. Desktop coordinates this through its own TUI RPC and adopts a concurrent winner. | A supported, idempotent create-or-get API for a bot's hidden canonical chat that preserves the profile's current runtime settings. |
| Turn state | A client can read history but cannot reliably tell when a session is waiting for approval or clarification. | A session-scoped turn-state read or event stream. |
| Bot Chat approvals | The two older fixture builds (`04fa849e` and `7e8c8f07`) have no Bot Chat session-stream approval notifier. Untagged `ac0cfa7` registers one and emits an answerable `approval.request`, and an isolated fixture passed on it. HMP has no released, approval-qualified build entry; Desktop-owned cross-client answers remain an upstream gap. The `/v1/runs` route has a different lifecycle and is not an equivalent replacement for a guarded Bot Chat send. | Preserve the session-chat notifier with stable request IDs and offered choices, and provide a supported, authenticated exact-ID answer contract with Hermes-owned expiry and termination semantics across execution owners. |
| Pairing access | A platform plugin currently synthesizes an inert inbound message to create a standard pairing request. | A documented plugin API to request access for a platform user. |
| Gateway setup status | On `8afaab37`, the resolved config default can say multiplexing is on while the gateway's boot preflight keeps it standalone. Explicitly setting `true` can skip that preflight and change profile API ingress and secret scoping. HMP needs this state to guide setup safely. | Expose the effective served-profile topology and migration blocker through a machine-readable, read-only operator interface. Keep topology changes in Hermes's own migration workflow. |
| Plugin install footprint | A bare `owner/repo` install stages the repository root, and the plugin guard scans its tests, tools, and docs along with runtime code. HMP keeps those files public for review, so its full-tree install prompts on numerous heuristic findings. | Let a root plugin manifest declare a bounded install file set. Verify the selected paths and source revision, reject escaping symlinks or imports outside the selected tree, and scan exactly the tree that will be activated. Keep dangerous findings blocking. |
| Message origin | Session rows do not identify the client surface that submitted a turn. | An optional, non-model-visible client/surface field stored with user rows. |
| Updates | A mobile client discovers new rows by polling. | A session change feed or bounded long poll. |
| Scheduled-job parity | On qualified `8afaab37`, the profile API's `POST /api/jobs` passes delivery and repeat settings but ignores `context_from`; the PATCH allowlist excludes it. Desktop's scheduler writer supports previous-run continuity. HMP uses that exact-build, profile-scoped writer for its owner-gated preview, so it cannot assume this path is stable across Hermes updates. | Accept and validate `context_from` in the authenticated profile-scoped jobs create/update API, with the same lifecycle checks and scheduler notification as Desktop, and return the persisted job. This removes HMP's private writer dependency. |
| Private session search | `SessionDB.search_messages` logs up to 200 characters of the query at INFO when a search crosses its slow threshold (`hermes_state_search.py` in the checked build). Hermes-wide search could put private conversation terms in host logs. HMP can separately page its authorized canonical Bot Chats and match on the phone without sending a query. | Log timing, path, and row count without query text, and cover the slow path with a regression test before any remote feature invokes native Hermes search. |
| Session management | The profile-scoped API server already lists sessions, reads messages, changes title/pin/archive/hidden state, and deletes sessions. Its `/fork` ends the source session, so it cannot implement a non-destructive branch. Project moves, export, and opening a session in a terminal are not API server operations. | Preserve the existing safe metadata routes; add a non-destructive branch operation and explicit project/export capabilities where appropriate. A canonical Bot Chat must not be accidentally archived or deleted by a remote client. |
| Scoped session read | HMP's draft session-ref repair checks whether a ref still selects an allowed Bot Chat before reading its messages, but Hermes exposes those as separate database reads. An archive, retitle, or replacement between them can leave one page based on the earlier eligibility decision. Per-bot authorization still applies; [HMP's extra session routes](https://github.com/MahdiHedhli/hermes-hmp/pull/51) now require an explicit boolean-true host opt-in, and the phone's picker remains hidden. | Provide an authenticated, profile-scoped read that selects an allowed session and returns its eligibility, canonical lineage, and message page from one consistent snapshot. Unknown and no-longer-eligible refs should have the same refusal. |
| Read-only session observation | On inspected `8afaab37`, a routing lookup can lazily initialize and prune the session store; database session reads can flush queued usage writes. A diagnostic cannot assume these helpers only observe existing state. | Provide an explicit profile-scoped observation contract with declared side effects and freshness. A read-only snapshot should not implicitly migrate, repair, prune or flush state; keep maintenance in Hermes's own lifecycle. |
| Chat media and attachments | Displaying a linked image was an HMP renderer gap, not a Hermes API gap; a bounded renderer is now in an unreleased mobile draft. Sending attachments into a Desktop-owned canonical Bot Chat, and reading generated local media back later, have no equivalent canonical contract on the inspected source. | Attachment-aware canonical single-owner admission and stable, authorized, reusable generated-media reads with capability flags. See [Chat media and attachment parity](#chat-media-and-attachment-parity). |
| Canonical remote attachment | Current HMP reaches a qualified legacy Bot Chat path; the unified runtime PR is a local/gateway cutover, while remote Desktop/web/mobile entry is staged separately. | Expose authenticated, profile-scoped remote attach/submit/event/control operations with explicit capability negotiation, target-session authorization, durable request identity, and replay-or-snapshot recovery. Keep one execution owner. |

## Bot Mode baseline verification

The exact `v2026.8.31` source has two session-key modes: a standalone named
profile uses the legacy `agent:main` namespace, while multiplexing uses the
routed profile namespace. HMP's scratch fixture now verifies both through the
old `SessionStore._generate_session_key`, cross-checks an explicit HMP route
with Hermes's matcher, and reads synthetic compression lineage from two
profile databases opened read-only. Database and sidecar hashes are unchanged
by those reads. This remains unwired: the paired full-gateway fixture still
refuses Bot Chat, and authorization plus canonical history must be proven
through that gateway before support for this tag can be listed. A supported
versioned read contract would eliminate these private per-build adapters.
The pinned old runtime uses Hermes's safe DELETE journal fallback for its
SQLite 3.50.4, and a writer-open read interleave passes in that mode. HMP has
not overridden Hermes's WAL guard; a patched-runtime WAL test remains open.

HMP is also drafting an [opt-in exact-commit compatibility matrix](https://github.com/MahdiHedhli/hermes-hmp/pull/46)
and a [consent-gated advisory report](https://github.com/MahdiHedhli/hermes-hmp/pull/47)
for unlisted builds. Neither qualifies a build or relaxes Bot Chat authorization.
The matrix executes candidate code, so an unreviewed commit needs a separate
disposable environment without live credentials. Its receipt is unsigned and
can be forged by code running as the same user. Community reports therefore
cannot replace a versioned, authenticated Hermes remote contract.

## Canonical Bot Chat through compression

At the qualified `8afaab37` source and the `f97608f` snapshot, Hermes's
`publish_compression_child` inserts a continuation row without copying the
parent's `hidden` column. The hidden canonical Bot Chat root can therefore have
a visible child; the exact `Bot Chat` title may also move onto that child when
Hermes transfers a title along the compression lineage. A bridge that requires
the *titled child* to be hidden can lose the existing chat after compaction.
[HMP's draft scope repair](https://github.com/MahdiHedhli/hermes-hmp/pull/49)
checks the hidden lineage root and refuses inconsistent lineage answers; its
isolated read fixture passed on two qualified build labels. A supported
profile-scoped API that returns canonical Bot Chat identity, lineage, and
visibility together would remove this per-build inference.

That identity check and the later message read currently use separate Hermes
database snapshots. [The draft HMP scope repair](https://github.com/MahdiHedhli/hermes-hmp/pull/49)
records the remaining race: an archive or retitle after eligibility is checked
may leave one message page readable under the prior state. This is a
read-consistency limit, not a bypass of HMP's per-bot authorization. A
profile-scoped canonical read that binds selection and rows to one snapshot
would close it without HMP copying Hermes's private database logic.

## Approval and clarify events

Desktop-owned Bot Chat turns still surface prompts through Desktop's process-local channel; a remote client cannot answer those same prompts through session chat. The two older Hermes builds used for HMP's draft approval matrix lacked a Bot Chat session-stream notifier. The inspected untagged Hermes `main` revision at [`ac0cfa7`](https://github.com/NousResearch/hermes-agent/commit/ac0cfa7db94cefa90cf3e35191f38b53888b9e17) registers one on the session-chat stream and emits `approval.request` for the existing run-approval route. An [HMP socket-free handler probe and isolated gateway/PTY matrix](https://github.com/MahdiHedhli/hermes-hmp/pull/44) passed on this exact archive: 32 focused checks and 17/17 integration cases, including T7 Bot Chat, T8 Phone chat, a same-device cross-profile exact-ID refusal, and fail-closed gates. The fixture used a fake model and synthetic credentials; no runtime compatibility entry was added. The tag inspected in that earlier check (`v2026.9.24`) predated the session-stream change; this file makes no claim about current release status. Each exact installed candidate, whether tagged or source, needs its own qualification; HMP does not require a future tag. Live multiplex profiles, physical devices, and Desktop-owned cross-client prompts also still need qualification or an upstream contract. This is not yet a released mobile approval capability.

Current HMP status (draft, not released): an independent approval manifest gates prompt reads, exact-ID answers and Phone sends (AP-3, AP-4 and AP-6). The production manifest is empty, so no production approval is admitted, live approval is not enabled, and there is no execution-owner fallback. Loaded memory is not attested. Ordinary guarded sends remain independent. [Draft route-qualification PR #53](https://github.com/MahdiHedhli/hermes-hmp/pull/53) captures one source baseline at the first supported factory call, prevents listener reconnects from redefining it, and caches successful dependency probes while rechecking the manifest and source on every call. Ambiguous normalized clarification labels are refused rather than guessed.

- **Current HMP candidate (draft).** [HMP PR #56](https://github.com/MahdiHedhli/hermes-hmp/pull/56) at `86f2a23760369749018c2e97d895696ffb0c9970` fixes an HMP bug: a stock queued `_gateway_accepted=False` was treated as a definitive refusal. Stock Hermes admission is known only for strict `True`; `False`, missing or non-boolean values are unknown. Where an AdmissionTicket is available, only a reported, enumerated known refusal proves no admission; `refused_other`, missing, unfamiliar or timed-out outcomes remain unknown. An unknown send is stored under the same id as unknown, is not observed, and is never retried automatically. This is not an upstream requirement. The root full suite passed 1493 tests with 13 skips and one existing warning.
- **Historical archive (Run 10).** The root-checked archive matrix reports all seven stages passed with exact 27/27 integration JUnit cases, on exact Hermes `8afaab3703e336d72a72c812dd2dd249f04f166a` with HMP runtime `86f2a23`. It is a disposable, fixture-only run (fake model, synthetic credentials) with an unsigned receipt. It **cannot qualify a git-install**. The independent-clone Git-install matrix (Run 2) has also passed all seven stages and the exact 27 required integration cases without failures, errors or skips. Its receipt binds the independent clone's full SHA; it does not admit a live installation or the later build-identity fix. It is not live or release qualification.
- **Combined candidate history.** Identity fix `3e66e6b` and independent Git-install tooling were combined in `6a83cec`. Run 3 selected all 27 cases: 25 passed and two errored during native-listener setup at the unchanged 45-second deadline. Reviewed tooling `853aa2d` records process-aware startup outcomes without extending that limit. Run 4 on combined candidate `847696d` passed identity, boundary and behavior; 24 of 27 integration cases passed and three T7 cases errored before gateway startup. Offline per-profile seeding stopped with build-process exit 1. These are different from Run 3's readiness errors. Neither run issued a final receipt; the discarded child output leaves Run 4's cause unconfirmed.
- **Accepted diagnostic tooling.** `d8b8b08` ([draft PR #60](https://github.com/MahdiHedhli/hermes-hmp/pull/60)) limits the offline builder's environment and retains failed-build output in a new private 0600 file under a descriptor-validated private directory. Exceptions carry closed phase/status metadata. Root independently passed 312 fixture/CI-tool tests, configured Ruff, private-content and plugin-surface scans.
- **Historical `d8b8b08` attempt: terminal failure (superseded as latest by the `f4730eb` pass below).** An unchanged complete seven-stage/27-case attempt on `d8b8b08` and independent Git `8afaab3703e336d72a72c812dd2dd249f04f166a` ended terminal with exit 1.
  - Identity, boundary and behavior passed.
  - Selected integration ran exactly 27 cases: 24 passed, 3 setup errors, 0 failures, 0 skipped. Later stages were not reached; the run is not complete and no receipt was written.
  - In every final private log root inspected, the offline per-profile seed step timed out at its 120-second limit before the gateway started. The exception metadata is public and closed. The three final logs are preserved privately and are not published.
  - The cause is not confirmed. This newly captured run does not prove the original Run 4 cause.
- **Bounded diagnostic reproduction.** Three real offline builds in a scratch environment passed in 15.7-16.6 s with seeding at 2.11-2.15 s, and the timer was never reached. Database file and row metadata alone does not locate a stuck frame or measure time from kill to exit. No native bug or cause is claimed. Tool-only nonfatal 90-second faulthandler diagnostics are root-accepted in draft at `f4730eb` ([HMP PR #61](https://github.com/MahdiHedhli/hermes-hmp/pull/61)); final root checks passed 15 focused diagnostic tests, with 300 earlier fixture and 23 CI-tool passes recorded separately. A later unchanged complete attempt on `f4730eb` is recorded below; the 120-second deadline is unchanged, with no SIGABRT or core dump, relaxed deadline, retry or gate change.
- **Partial rerun, not qualification.** The three formerly setup-failing T7 cases passed earlier against the same independent Git commit (3 passed, zero failures, errors or skips, snapshot unchanged, provisional fixture-only receipts, allowlisted parent environment). That recorded result does not qualify: it is not all 27 cases or seven stages, writes no final receipt, enables nothing and does not identify any failure cause. The partial run alone was not qualification; the later full fixture pass below supersedes it for fixture status, while live and release gates remain pending.
- **Historical: full matrix passed on `f4730eb`.** An unchanged complete seven-stage attempt on tooling `f4730eb` ([draft PR #61](https://github.com/MahdiHedhli/hermes-hmp/pull/61)) against the independent Git `8afaab3703e336d72a72c812dd2dd249f04f166a` exited 0: all seven stages passed, exactly 27 selected integration cases ran with 27 passed and no errors, failures or skips, and a final fixture receipt was written and independently validated against current fingerprints and case identities. Limits: the receipt is unsigned fixture-only evidence (fake model, synthetic credentials), not a live, process, release or device attestation, and the public approval manifest remains empty. The original seed-timeout cause was not found; the nonfatal diagnostics did not hit a stall. PR #61 is tooling only. This does not erase the earlier failed runs above.
- **Current integrated candidate (2026-10-01).** [HMP draft PR #65](https://github.com/MahdiHedhli/hermes-hmp/pull/65) combines the approval bridge with the mobile app's HMP features and root-only new-profile route preparation. Root verified a fresh full Git-install matrix at `f584b91c5b5b157444b3875528ec034c6b83c4f9` against independent Hermes `8afaab3703e336d72a72c812dd2dd249f04f166a`/Python 3.14.7: all seven stages and exactly 27 required gateway cases passed, without failures, errors or skips. The actual JUnit selection and current-source receipt were independently checked. An earlier run of this candidate failed because its generic fixture pairing explicitly declined host controls; only approval fixtures now opt into primary-device owner enrollment, with production permissions unchanged. Approval ownership still requires the configured owner list and no explicit host denial; a controls grant alone does not open it. Both production write manifests remain empty. The unsigned fixture result is not package, live host, device, memory or release admission; separate owner-local packaging and device acceptance remain next. Earlier failures and receipts retain their exact-revision limits.
- **Private package tooling (2026-10-01).** [HMP draft PR #68](https://github.com/MahdiHedhli/hermes-hmp/pull/68) derives a private candidate with only the two qualification `builds` arrays changed. Root and Opus reverified the full receipt against the clean integrated source, the strict package delta and the package's own exact-Git parser match. The source receipt is stale for the separate package digest and is not relabelled. Root pinned the candidate's tree/plugin/manifest hashes; `verify` alone reports hashes and does not pin a prior package. The public source manifests remain empty. This is candidate evidence only, with live flags/grants, drain/restart, native crypto/artifact evidence and real phone acceptance still required.
- **Remaining limits.** Other fixture helpers still inherit their caller environment; the parent was manually contained for this rerun. Captured streams remain unbounded in memory, and `--showlocals` can expose test internals. Earlier historical results do not qualify other candidates; the historical `f4730eb` fixture pass and current integrated candidate are validated separately above; it is fixture-only and not final live admission, and all privacy, memory and environment limits above still apply. The public approval manifest remains empty; no fixture receipt is promoted into a live installation.

- Earlier Run 8 (source `ac0cfa7`, runtime draft `8934993`) is historical. It predates these diffs and cannot qualify them.
- Source checks do not attest already-loaded module bytes: a full gateway process restart is required after source/plugin changes. The final combined runtime candidate, live profiles, physical devices and release review remain.
- **Mobile.** [PR #50](https://github.com/MahdiHedhli/HermesBotMobile/pull/50) (draft) holds the combined S2/S3 store API at `a1f9515`; the root full run passed 967 client (1 skip) and 587 app (3 skips) tests. The separate Phone chat read controller is reviewed in [app PR #52](https://github.com/MahdiHedhli/HermesBotMobile/pull/52) at `7429b3f`: root passed the full client (1,013 / 1 existing skip), app (692 / 3 existing skips) and dev-support (8) suites before a small reconnect repair, then all 48 controller tests on the final candidate. Opus independently cleared the bounded read/concurrency surface. Reads preserve the sealed Bot Chat and Phone pending records; a stored Phone `sending` is displayed as unknown without a POST or store rewrite. The controller send slice is accepted in [draft app PR #55](https://github.com/MahdiHedhli/HermesBotMobile/pull/55) at `91f8cd0`: root's final client run passed 1,147 tests with one existing skip, and the sealed store passed 8. Its evidence uses a synthetic server and crypto; no real-device crypto, Keychain, process-restart, live-gateway proof or live approval admission is claimed. The Phone chat screen is accepted and pushed in [draft app PR #56](https://github.com/MahdiHedhli/HermesBotMobile/pull/56) at `56177bf`, based on PR #55's `91f8cd0`: root passed 60 widget tests and clean analysis; Opus cleared the preceding cover, dialog and cleanup candidate, then root independently reviewed the final departure fence. The screen shows plain-text Phone rows only; images remain the existing Bot Chat dogfood (`acc9543`, build 2026093002) on two owner iPhones after explicit tap, and the live approval gate stays closed. S6 reconciliation is assigned and in progress. The new Phone composer is not deployed; its physical-device and release gates remain open.

The [earlier ac0 fixture evidence](https://github.com/MahdiHedhli/hermes-hmp/pull/44) cannot qualify the current candidate.

**Priority notifications (architecture only).** An urgent approval alert remains unimplemented.
Independent architecture review separates a testable client tap-handoff from real APNs/FCM
registration and delivery. A strict opaque hint cannot create a pairing or confer authority:
explicit instance switching, current registration/pairing generation and context-epoch checks,
and a fresh authoritative prompt read are required. An alert supplies no command, bot name,
answer, pin or attachment URL, and its opaque references must not be logged. Approval-owner
eligibility is separate from the jobs/model controls grant and must be rechecked per device.
The HMP broker's configuration-derived expiry is an estimate, not evidence of a native
execution deadline; pending state and Hermes's answer boundary remain authoritative.
Registration, recipient eligibility, revocation and provider dispatch are an HMP contract and
provider-infrastructure work item, not proof of a missing Nous notification API. Stable native
expiry and cross-owner settlement remain useful upstream contracts. Current dogfood is
foreground-only, and provider custody, signed capabilities, lifecycle cleanup and physical
background delivery are unqualified. No ETA.

**Watch exploration (not implemented).** A standalone Family Setup watch without its own iPhone is future exploration only. An optional parent companion phone does not prove an always-on relay. No ETA.

This is the next major HermesBot Mobile feature after beta release work. We
request a supported, authenticated, session-scoped contract that carries exact
request IDs, offered choices, session/profile ownership, and authoritative
expiry and settlement across Desktop and remote clients. The current-main
session-stream candidate passed an isolated fixture matrix. The fixture evidence is
historical, and the minimum-version policy supersedes exact-build availability gating for
read, send, jobs and model. Before the first approvals release, the implementation must
pass wrong-ID, cross-profile, timeout, disconnect, restart, and live-owner handoff tests.
These tests validate authority and settlement; they are not an allowlist of future Hermes
versions. The draft approvals' legacy exact gate needs conversion before merge, while
actual owner permission and required API checks remain enforced. HMP must not infer approvals from tool text or create
another execution owner.

## Chat media and attachment parity

Checked against exact Hermes `ca705dbf7ef86425b381b542712aff310f1ee52c` on 2026-09-30. The source census and owner observation are supplemented by isolated native primitive tests on an archive with matching `ca705dbf` provenance; that archive is not a re-attested Git install. No live gateway upload was exercised.

**Display was the mobile app's gap.** The owner observed that an assistant's HTTPS Markdown image string reaches the HMP mobile app intact but was shown as literal text, because the app rendered plain text and fenced code only. That needed a mobile renderer change, not a new Hermes API. It is now addressed in draft, not released: [mobile PR #51](https://github.com/MahdiHedhli/HermesBotMobile/pull/51) at `acc9543` (root full run: app 690 passed / 3 skipped, client 967 passed / 1 skipped; clean app analysis; an independent review cleared the bounded renderer and its policy exception).

- **Scope.** It renders public HTTPS images from canonical assistant Markdown, only after an explicit tap. It uses a separate public-PKI transport without Hermes credentials or Hermes instance pins; per-hop public-only DNS with single resolution; TLS server-hostname checks; at most 3 redirects; 8 MiB and 15 s limits; PNG, JPEG and static WebP only; 20 MP, 8192-pixel edge and 2048 decode bounds; at most 2 fetch-and-decode operations; lifecycle fences and cache clearing.
- **Not included.** No automatic or background fetch of public URLs, no browser, video, audio, native upload or localhost media.
- **Evidence.** A signed local dogfood build was installed on one connected owner iPhone, and the app's metadata was confirmed. No new external TestFlight build with these approval or media changes has been submitted. The same installed build also contains the existing approval screen, which is unusable while the live host gate is closed. The owner reported a public-CDN card failing to load. Root reproduced a 200 response with an allowed PNG header but JPEG image bytes; the current equality check returns `unsupportedType`. The focused fix is root-accepted at `dba5c93` ([app PR #57](https://github.com/MahdiHedhli/HermesBotMobile/pull/57)): allowed raster MIME and signatures are checked independently, preserving all other bounds. Root passed 106 focused cases; Opus cleared the exact code/test hashes. The production CDN probe now downloads and decodes the image successfully. Signed and scanned local build `2026093003` is installed and launched on one owner iPhone. The owner screenshot confirms the public CDN image renders on the phone; the separate local `MEDIA:` output remains text-only. This is not a TestFlight update. Authorized local host media, NAT64 and app-switch snapshot proof remain open.
- **Limits that remain.** The existing native hooks and the Desktop-owned canonical handoff's string-only constraint and session API's rejection of file parts are unchanged. Linked video and audio look feasible, but codecs, URL authorization and expiry, and device behavior are unverified.

**Priority:** approvals first, then media/file/photo attachment support (planning only: spec 028), then full desktop-composer parity. Phone-side Photos, Files and pasted-image selection is possible app work, but upload and native adapter media-fixture qualification are not complete. HMP does not plan a second execution owner beside a Desktop-owned canonical chat, or browser-control artifact reuse.

**Composer inventory.** Desktop's composer plus menu offers Files, Folder, Images, Paste image, URL and Prompt snippets, and `@` inline file references. HMP plans to cover all of these and does not claim any as complete. Phone-local file, photo and clipboard selection and draft snippets need app work. Host-folder references need grant-scoped handles. Canonical uploads are separately gated on the upstream contract below.

**Existing building blocks.** Hermes's `gateway/platforms/event.py` `MessageEvent` has `media_urls`, `media_types` and `media_text_inlined` plus photo, video, audio and document types. `gateway/platforms/base.py` has `cache_document_from_bytes`, `cache_image_from_bytes` and `cache_media_bytes` (`cache_media_from_bytes` is not present in that source), and native image, video, document and audio send methods. A different `cache_media_bytes` (different signature and return type) lives in `gateway/platforms/media_cache.py`, so a plugin must name the module. These are plugin building blocks. HMP's current Phone-chat inbound event is text-only and it overrides no native outbound media hook; its bridge's `_text_of` drops non-text structured parts, and `_rows` carries no media handles. A bounded native adapter delivery path, with profile-, conversation- and device-authorized opaque handles for generated local files, is needed. The current native platform extension can be investigated without a core change, but it does not by itself provide canonical Desktop media or history.

**Native primitive evidence, not upload qualification.** Root reviewed and reproduced an isolated
fixture on the `ca705dbf` archive: 73 checks across real cache helpers, `MessageEvent`, inbound
preparation, the runner's queue-policy method and durable-row flush helpers. All 12 exercised
source files were byte-identical before/after. Root passed 30 focused fixture tests and 315
fixture/CI-tool tests together; this is not the full CI-equivalent suite. The private scratch home
was removed, no Python-level IP attempt occurred and no model or full gateway was started.
Python socket instrumentation is not an OS sandbox and does not cover DNS, C extensions or
subprocesses. An earlier wider worker run reported four failures that did not reproduce; the cause
is unconfirmed and no full CI gate is claimed. The archive provenance is not a Git attestation.
Evidence is on the unmerged discovery branch at `9d91ca1`:
[fixture and limitations](https://github.com/MahdiHedhli/hermes-hmp/blob/test/phone-attachment-native-primitives/docs/research/phone-attachment-native-primitives-2026-09-30.md).

- *Validation and private storage.* The document helper kept hostile names inside the profile
  cache but accepted a document above the configured image cap. Under umask 022, the tested
  file was 0644 and its cache directory 0755; native did not enforce private modes. Newlines
  survived in a name and reached the document note. The image helper rejected cap+1 and invalid
  magic, but accepted a magic prefix with an undecodable body. HMP must enforce bounds, MIME/
  content checks, decode/pixel/metadata policy, generated names and private storage before
  delivery. Only paths HMP created may become event media paths; inbound preparation trusted
  an outside-cache path in this isolated test. No live exploit or universal build claim is made.
- *Inline contract.* Absent or None text-inline flags made the same claim as True without
  actually inlining content. False changed the note; binary notes ignored the flag. An adapter
  that does not inline text must explicitly set `media_text_inlined=[False]`.
- *Busy sessions.* The real base fallback merged media; the runner's tested queue method merged
  matching-scope PHOTO/TEXT while documents used FIFO. Different scope or gateway-control flags
  prevented merge. The merged event kept only the first client identifier. A later client send
  therefore cannot be reconciled merely by that merged event's id. Full busy authorization, ack,
  steering and durable admission were not exercised, and `defer_policy` was absent on this build.
- *Persisted identity.* Actual flush helpers wrote/read real SessionDB rows with controlled agent
  shapes. Documents stored the prepared host-path note; an image-part list plus a string override
  projected to caption plus `[screenshot]`, without a path or attachment identity. Client ids
  round-tripped as `platform_message_id`. This was not a real agent turn or an HMP read-back;
  model-dependent enrichment, profile re-homing, cache sweep and audio/video remain unproven.

Separately, a source census and persistence fixture ran on independent Git Hermes `8afaab3703e336d72a72c812dd2dd249f04f166a`. [HMP draft PR #62](https://github.com/MahdiHedhli/hermes-hmp/pull/62) (commit `5a688c7`) records five synthetic scenarios through real native Desktop and Phone turns, including failed writes and Desktop deferred tools. The model and image provider were synthetic; Phone used a stand-in adapter, not `HmpAdapter`. Root accepted this research, not a media feature. Observed:

- On normal turns the assistant call row and the tool row are linked by call id, the tool row carries the executing tool name `image_generate`, and the tool-row flush precedes the Desktop completion frame and the Phone reply and media sends. With default deferred tools the Desktop assistant call is named `tool_call` (the single-entry bridge) while the tool row is `image_generate`, so linkage cannot require the assistant call name. A follow-up ([HMP draft PR #63](https://github.com/MahdiHedhli/hermes-hmp/pull/63), commit `97316ad`; four new native Desktop/Phone cases; root 37 non-native plus the 1 native aggregate of those four cases passed, with the older five-case aggregate deselected) saw the modern one-entry `calls` bridge execute and record an `image_generate` row linked to the outer call id, while a two-local-entry batch was rejected before any provider call and left an error row, which must not become a candidate. A matching id alone is not execution proof. On Phone, a bridged image was generated and persisted but native auto-append media sends were 0 (the reason it keys on the outer assistant call name is source inference, not an isolated causal native experiment); that differs from the direct-send shape and does not contradict it. This does not require upstream delivery for an HMP history-based route, which remains unimplemented and unqualified. Still unseen: other providers, flush failure for these shapes, connector batches, `HmpAdapter`.
- The full tool result parsed as one JSON object with `image` near the start, while its first 4000 characters did not parse: any parse has to see the uncapped result.
- A failed tool-row flush left the cache file and the assistant call row but no tool row, and the Phone path still sent media. A cache file or a native delivery is therefore not evidence of a stored row.

A later accepted G2 storage characterization ([HMP draft PR #64](https://github.com/MahdiHedhli/hermes-hmp/pull/64), commit `b437888`; synthetic seed, native `SessionDB` methods only) found that an active call/result pair can be retired or re-cloned, and that a closed compression parent keeps active rows, so "active" is meaningful only at the current tip. An imported session with a parent edge can change the Hermes resume tip, and foreign image values are stored verbatim, so stored values are not serving authority. A same-inode restore rolled back row ids, conversation generation and rewind count while the examined file identity fields stayed unchanged, so no monotonic epoch is assumed or invented, and sampled sequential reads give no atomic snapshot claim. This is not generation, HMP adapter, authorization or service qualification, and it needs no new producer hook; current local `MEDIA:` text remains unsupported. Branch handlers, a different-file or swapped-inode restore, and concurrency remain open.

Accepted G3 research now addresses selected file/raster hazards: [HMP draft PR #66](https://github.com/MahdiHedhli/hermes-hmp/pull/66), `6470379`, pins flat selected-profile cache descriptors and bounds regular single-link reads; [draft PR #67](https://github.com/MahdiHedhli/hermes-hmp/pull/67), `8a74190`, checks a static PNG/JPEG/WebP structural subset with 8 MiB, 8192 edge, 20 MP declared dimensions, 10000 units and 64 JPEG scans. Late file mutation and an empty-SOS bounds error were repaired causally and independently reviewed. These are research prototypes, not a host decoder, authority or integrity proof against a trusted same-account writer. A many-scan availability case motivated the conservative cap; no phone freeze was observed. Public CDN bytes bypass host validation, so a separate phone preflight is reviewed in [app draft PR #62](https://github.com/MahdiHedhli/HermesBotMobile/pull/62), still uninstalled.

Limits: no native media network, grant or wire qualification. [HMP draft #69](https://github.com/MahdiHedhli/hermes-hmp/pull/69) now accepts bounded G4 active-history linkage/rechecks research at b32d913 (71 expected native storage outcomes, independent 28-case unit review and causal repair checks); fresh device/profile/conversation authorization and complete worker/buffer transport lifetimes remain unimplemented. The earlier `ca705dbf` fixture is not evidence for `8afaab37`. We do not claim that an upstream change is required for a possible HMP-owned route; a generic reusable upstream media contract remains the request below. The only end-to-end evidence so far is public-CDN image display in the mobile app, which is a separate path from local `MEDIA:` text.

These observations constrain our adapter design. They do not qualify a release, freeze the
upload wire or make an attachment send available on the phone. Canonical owner handoff and
reusable authorized media history still need the contract below.

**Source constraint on this build.** `api_server.py` `_session_chat_user_message` normalizes text and `image_url`/`input_image` lists and rejects `file`/`input_file`. `_admit_to_live_bot_chat` returns `None` for non-string content, and `tools/bot_live_delivery.py` `deliver_to_live_owner` requires a string. On this source, multimodal input therefore does not take the Desktop-owned canonical Bot Chat handoff. No live attachment submit or adversarial test was performed during this investigation; this describes a source constraint, not an exercised bypass. HMP must not use this path to create a second execution owner beside Desktop.

**Generic upstream request.** Attachment-aware canonical single-owner admission; per-profile and per-conversation media handles; and stable, reusable, authorized generated-media reads with retention, recovery and capability flags. The existing primitives do not substitute for that contract:

- `_resolve_media_to_data_urls` validates bounded `MEDIA` image tags in the API server's own completions. It does not cover all persisted history or Desktop-mailbox outputs, and does not cover video or documents.
- `/v1/artifacts` upload and download require browser-control to be enabled, an API bearer, and a principal/family match; receipts are one-shot, TTL-bound and held in memory. It is not a durable ordinary-chat media API, and HMP will not enable browser control to implement attachments.

Source references (exact commit): [`api_server.py` L493-L586](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/api_server.py#L493-L586), [L663-L672](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/api_server.py#L663-L672), [L890-L931](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/api_server.py#L890-L931), [L2859](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/api_server.py#L2859), [L3463-L3489](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/api_server.py#L3463-L3489); [`event.py`](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/event.py); [`base.py`](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/base.py). Hermes's [deliverable-mode](https://hermes-agent.nousresearch.com/docs/user-guide/features/deliverable-mode) and [adding platform adapters](https://hermes-agent.nousresearch.com/docs/developer-guide/adding-platform-adapters) docs are contextual reading, not exact proof of HMP's behavior.

## Already usable without a new Hermes contract

### Newly created profiles

On the inspected `ca705dbf` build, the gateway can discover and serve a newly created profile
without adding its exact HMP route to the root configuration. Serving, routing and phone access
are separate states. HMP's [draft host-only routing command](https://github.com/MahdiHedhli/hermes-hmp/pull/52)
prepares that route without granting phone access or enabling multiplexing for the whole gateway.
The command is an unmerged draft. The correction at `4e270f0` removes every profile-config write:
it adds only an exact root route and preserves the profile's history settings. Root passed the
repository CI-equivalent suite (1,322 tests / 10 existing skips) and all 138 final route tests;
Opus cleared the bounded code review. The command itself was not verified live.
The profile flag must stay unchanged because it selects the session-history namespace.

History for a profile whose own multiplex flag is absent or false, on the same `ca705dbf` build
(an archive, so no Git SHA is attestable; bound by read-bridge fingerprint `d45f9a13…f11f627` and a
source-tree digest), was checked with a real-Hermes fixture in an isolated home: the native gateway
runner, `SessionStore` and `SessionDB`, the real HMP read bridge and the route helper, with synthetic
messages and no model turn, credential or Phone transport. Its Python socket instrumentation
recorded no attempted IP connections; it is not an OS network sandbox. Authorization was not tested.
Root independently reproduced 7 of 7 passing
with no skips. The result is split by where the history came from, and is identical for the flag
absent and false:

- **A, created by the root for a routed source.** The canonical conversation resolves (4 of 4 rows)
  and the conversation is visible in the Phone list. The profile's own flag is not needed.
- **B, created earlier by a standalone gateway of that profile.** Its rows are intact and readable by
  session id, but they sit under the legacy `agent:main` key. The canonical read is empty, not an
  error, and the Phone list does not show them. A first routed conversation then starts a new session
  and leaves the earlier one unlinked.

The route helper left the profile tree byte-, mtime-, inode- and mode-identical and wrote no flag or
history. Route-only preparation therefore does not make existing standalone history readable, and is
not a migration. One origin per case, one user and chat, and this one build were covered; the real
gateway loop, authorization and a physical device were not. Evidence:
[`C6-EVIDENCE.md`](https://github.com/MahdiHedhli/hermes-hmp/blob/test/flagless-profile-history/specs/005-new-profile-routing/C6-EVIDENCE.md)
on the unmerged `test/flagless-profile-history` branch. Disposable-host qualification of the full
gateway loop stays open.

**Generic upstream request.** A stable, versioned, profile-scoped read contract for legacy history:
for an authorized profile, resolve its canonical conversation and lineage whichever session-key
namespace created the rows, or report explicitly that legacy history exists and is not addressable.
It should need no change to the profile's multiplex flag and no history rewrite. Until then HMP treats
legacy history as unqualified rather than repairing it from the mobile side. This is an observation
from one build, not a new upstream submission.

On one selected host, a manual operator-scoped
root-route repair and distinct per-profile send keys were verified for passive reads and cross-key isolation,
and a native, explicitly requested access approval matched its request. A real owner send remains unverified.
This is an HMP setup/workflow finding, not evidence that Hermes must grant access automatically.

Automatic preparation and the bot-access permission card are an unimplemented proposal; nothing is
released. The plan has one host opt-in, per-bot keys and a running route activation. Gaps:

- **Route activation.** Root routes are read at startup. Profile rescan and plugin reload do not refresh them, and SIGUSR1 is a drain and relaunch. Activation needs a qualified route-refresh primitive or a separately evaluated, consented drain policy.
- **Access card.** The primary destination is the exact authorized bot chat, with central Requests as the aggregated fallback. It is a device-targeted ephemeral event for a separate host-selected approver role, not stored in the transcript, group chat or model context. It needs a host-only contract amendment.
- **Grant scope.** Native grants are user-scoped and can cover multiple paired devices. The card must say so.
- **Reject.** Native pairing has no per-request deny. `clear-pending` clears all requests and is not a substitute. A local dismissal is not a rejection. This is a generic upstream gap.
- **Settlement.** `PairingStore` locks only within a process, and the CLI approval makes two non-atomic JSON writes. An unknown outcome is never automatically resent. A cross-writer settlement API is needed.
- **Key writes.** Native `.env` writing lacks compare-and-swap and owner-0600 enforcement, so automatic key provisioning requires a qualified writer. Durable profile identity and safe same-name replacement are a separate gap.

### Scheduled jobs

The profile-scoped API server has list, create, edit, pause, resume, and delete
routes for scheduled jobs. HMP's mobile cron preview uses those existing
read/pause/resume/delete routes with an owner-device gate and a closed-by-default
host flag. The current minimum-version policy above replaces the earlier
exact-build runtime allowlist: jobs and model operations require Hermes `0.21.5`
(`2026.9.24`), while later or unknown builds attempt the required APIs. Authorization,
feature settings and actual API behavior still govern availability; an untested
commit alone does not turn a supported feature off.

New jobs start paused. A narrow profile-scoped Hermes writer also saves Bot Chat
delivery, finite repeats and previous-run continuity for create/edit. A complete
public API contract for continuity would remove that version-specific writer.
Earlier qualification samples recorded two completed runs of a phone-created job,
with Bot Chat delivery receipts and persisted replies. The second run's input
contained the first answer, establishing continuity in that sample. Those historical
runs do not establish job execution or phone controls on the currently deployed
Linux host, and do not make the private writer a supported public API. Mobile
push remains separate work; the approval notification contract and inputs above
are not a deployed notification service.

Bot default-model reads and writes also use Hermes's profile-scoped validation
under the current minimum-version policy. HMP keeps this preview off by default
and does not send model credentials to the phone.

Named profiles need their own API server keys under the existing multiplexed
gateway contract. HMP now reports Bot Chat send availability per authorized bot
and requires its owner send switch on every build. This is an HMP/client fix;
it does not request a new Hermes API. A failed loopback connection after a
roster read remains a send-time failure.

## Additional API parity requests

- Make model overrides apply to live Desktop-owned turns as well as API-owned turns.
- Expose safe checkpoint rewind and non-destructive branch operations.
- Expose profile lifecycle, voice routes, and view-only bot-screen access through the API server with their existing safeguards.

Please discuss proposals in [repository issues](https://github.com/MahdiHedhli/hermes-hmp/issues). This file is the reviewable source for any companion public Gist.

### Follow-up: accepted active-history research and phone safeguard

The bounded G4 prototype checks whole-tip call-ID uniqueness with active-ID/tip
brackets and selected-row digest rechecks. Callback errors close without private
text; row caps precede HMP-side iteration. Single observed legacy and modern image
bridge shapes work. Native allocation remains uncapped; provider call-ID reuse and
large/malformed active histories can refuse image availability. There is no atomic
snapshot or restore epoch, media grant, network route or serving qualification.

At that historical checkpoint, app draft #62 was installed only as owner dogfood
build 2026100101, with a conservative JPEG pre-decode complexity cap. Signed artifact checks and installation passed; the
locked phone refused automatic launch. The owner confirmed CDN image rendering on
the preceding build, while host-local MEDIA output remains text-only. No live HMP
package or new external beta was deployed in this checkpoint.


## Source checkpoint — 2026-10-02, approval notification contract

[HMP draft PR #74](https://github.com/MahdiHedhli/hermes-hmp/pull/74) now publishes the independently accepted relay contract text at `92a719f`. It uses one atomic effective acceptance instant, `max(raw_wall_now, last_now)`, for nonce admission and seal bounds; monotonic time for rolling rate budgets; explicitly qualified normal-clock retention/capacity bounds; and separate APNs connections for each allowed `(app, env)` pair. Clock stalls/steps may prolong retention and fill the hard cache cap, which fails closed without evicting live nonces. Optional leaf pins constrain an otherwise valid TLS chain/hostname. This paragraph records contract acceptance only; the separate issuer checkpoint records its bounded source evidence. Registration/resolver/dispatch source, relay signature/seal vectors and interoperability, provider/device/deployment/release and owner choices remain pending. No push capability is enabled.

The related mobile image branches passed hosted CI: public repair `16c2095` in [37064933078](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37064933078), and accepted Phone image wiring plus the fixture repair `11cbf29` in [37065452665](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37065452665). The actual successful-TLS late-delivery cancellation case passed. The former fixture collision is resolved; native serving/allocation, physical device and release gates remain. No new deployed media or approval capability is claimed.

## Read-only push status implementation checkpoint

The independently accepted T026 source slice at `25324c664d7f6147669498562ec7da4bb366ad11` ([HMP PR #89](https://github.com/MahdiHedhli/hermes-hmp/pull/89)) adds `hermes hmp push status`: configured opt-in, validated relay
configuration, configured kid count, active registration count, and non-revoked generation-row
count. It emits only fixed names/codes, booleans and counts; unreadable configuration/store data is
unavailable rather than zero. It loads no identity key, mutates no grant, migrates no store, sends no
push and reports no dispatch or delivery outcome. A disabled host may still have valid relay config;
stored active rows are not a claim of current dispatch eligibility.

Local source verification: **2,591 passed, 16 skipped**, one existing aiohttp warning; lint, closed
surface and privacy checks passed. Eight isolated cases against Hermes source `ac0cfa7db94cefa90cf3e35191f38b53888b9e17`
matched the native pure configuration primitives, including flat versus explicit `extra` precedence,
legacy state, environment references and managed leaf overrides. No diagnostic file/environment
change was observed. Native CLI bootstrap is accounted for separately; the bridge refuses to cause
Hermes configuration's first import because it can seed SOUL.md. Live WAL uses read-only/query-only
SQLite; missing SHM reports unavailable, and existing SHM may update ordinary reader bookkeeping.

Independent v3 source review accepted the frozen implementation, verifying pins and inspecting the exact test logs; the reviewer did not rerun pytest. Initial hosted CI stopped at import formatting because the local lint used the wrong configuration. The whitespace-only followup passed canonical repository lint locally and [hosted CI run 37092782098](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37092782098) succeeded on exact head `25324c664d7f6147669498562ec7da4bb366ad11`, including tests, surface, log hygiene and privacy gates. It changes no minimum-version
policy or app feature gate. Missing optional configuration primitives affect diagnostics only.
A supported read-only Hermes settings projection would remove HMP's private parser/expansion/merge
primitive dependencies. Provider/device delivery, relay/seal interoperability, app registration,
provisioning and remote release gates remain open.

The diagnostics reader now rejects opened nonregular targets before reading, uses nonblocking open to avoid FIFO waits, and preserves native symlinks to regular configuration files. Four isolated FIFO/symlink tests have subprocess timeouts; regular filesystem stalls remain outside a universal wall-clock guarantee. The accepted v3 fixes the blocking-read edge identified by the v2 rejection. No live installation or notification delivery is implied.

## Native approval relay fixture component checkpoint (2026-10-03 UTC)

The independently accepted receiver/client component at
`9e21614f44edf984072353a21d94ce78d9457365`
([HMP draft PR #90](https://github.com/MahdiHedhli/hermes-hmp/pull/90)) adds a disposable
loopback HTTPS receiver. The real production relay client sends requests through verified chain
and hostname checks plus the configured leaf pin; the receiver independently frames and verifies
the P-256 signature. Untrusted CA and wrong-pin cases fail before a request is captured.

The receiver has bounded headers, body, capture count and connection/close time, fixed responses,
no request logging, and synthetic private certificate files in fresh scratch directories.
Independent review found that deeply nested JSON could reach the standard traceback path;
the accepted repair returns fixed 400 with no capture or stderr. No request-body disclosure was
demonstrated. Independent focused tests passed 2/2; the full local CI-equivalent suite passed
2,610 cases, with 16 skips and one existing aiohttp warning. Exact-head hosted CI
[run 37094865602](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37094865602)
also completed successfully.

**At this component checkpoint, T029 remained incomplete.** These tests used a synthetic
signing identity rather than a native approval. The later native checkpoint below adds bounded
approval/revocation/restart evidence; the genuine Desktop-held interleave remains unverified. HPKE opening, relay admission/replay/provider behavior, app registration,
APNs/FCM delivery, runtime privacy canaries and release qualification remain separate work.
No production module, live home, deployment, provider or device was changed by this component.

## Native approval push origin, revocation and restart checkpoint (2026-10-03 UTC)

The isolated fixture at `871ebb0d322140e834e99b585844ebfa2b0ddf4a`
([HMP draft PR #91](https://github.com/MahdiHedhli/hermes-hmp/pull/91)) drives actual
Hermes approval callbacks, AP3/AP4 routes, the production dispatcher and the verified-TLS fake
receiver. Independent source/confinement review preceded the run; independent receipt review
accepted these three selected cases on Hermes `8afaab3703e336d72a72c812dd2dd249f04f166a`,
Python 3.14.7 and its locked messaging dependency set (3 passed, 0 skips, 9 unrelated parameters
deselected):

- A native approval produced a request whose signature the fake relay independently verified.
- After positively observing pending work and the real coalescing delay, native device revocation
  invalidated the bearer and prevented a second relay request.
- Graceful restart cancelled positively pending work; the test assertions verified cleared
  queue/slots/hints, old-hint 404 and no second relay request.

**Receipt limitation:** final teardown overwrote the old dispatcher's close journal with the new
listener's zero counters. The old current journal retains cancellation and the in-test close
assertion passed, but the final close file is not the old dispatcher's snapshot. This limit is
retained alongside the accepted receipt, not repaired retroactively.

Fresh sandbox preflight and native imports passed. Prepared/shared/protected tree digests stayed
unchanged and no child processes remained. An earlier preflight failed its offline package check
from a working directory denied by the sandbox; the successful check used the private fixture
directory. Both receipts and the causal diagnostic are retained. The sandbox was not weakened.
Dependency wheel-byte provenance remains a residual.

The observer exists only in disposable copied fixture code, follows the actual coalescing sleep
and records bounded counters/booleans. Independent review required a notifier-absent sample to
fail the positive prerequisite and FIFO reads to fail without blocking; the runner requires a
passed current-receipt preflight before native imports. Those repairs were independently
confirmed. Six focused helper tests, Ruff, privacy and closed surface checks passed locally.
Hosted unit/tool CI initially failed because the FIFO regression's child could not import the
observer from CI's working directory (2,614 passed, 17 skips, one failure). The independently
accepted test-only repair at `3e676ec10266ef958ca631b6f8384c6aa297745e` binds that child to
the imported observer directory, retaining its no-writer setup and three-second timeout. Six
helper tests passed independently. Exact-head hosted
[run 37098887364](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37098887364)
then completed successfully: 2,615 passed, 17 skips and one existing warning, with lint, closed
surface and privacy checks passing. The native test/observer/wiring code is unchanged by this
repair; the three native cases retain their original sealed receipt, not a new native rerun.

**T029 remains incomplete:** the genuine combined Desktop-held interleave is unverified. HPKE
opening, remote relay admission/replay, app registration, APNs/FCM delivery, physical devices and
release acceptance remain separate gates. The fake relay accepts opaque seal syntax; it does not
open a seal or contact a provider. This one development sample is not a runtime allowlist or a
qualification of future versions. No production module, live home, device, deployment or provider
configuration changed.

## Desktop ownership source trace (2026-10-03 UTC)

Historical source-only checkpoint; the actual experiment below supersedes its
runtime-pending status.

Independent source and fixture-plan review on Hermes
`8afaab3703e336d72a72c812dd2dd249f04f166a` and HMP
`3e676ec10266ef958ca631b6f8384c6aa297745e` distinguishes two native leases:
the API agent holds a durable SessionDB turn lease, while Desktop claims the
active-session registry lease at `prompt.submit`. The durable lease serializes
model turns. Desktop submit-time transcript persistence precedes its worker's
turn-lease admission. HMP's shared AP3 visibility currently uses a stream-derived
held marker, which does not observe a new Desktop registry claim during an
already-open API approval. This is a source hypothesis for stale visibility and
transcript ordering; no causal runtime defect or concurrent model execution is
claimed. The native snapshot read exists, so an upstream missing primitive has
not been established.

The independently accepted experiment warms the real Desktop backend before
arming one pending push barrier, uses actual `/api/ws` resume/submit, observes
registry ownership, transcript ordering, AP3 and relay capture, then denies the
original approval for cleanup. Implementation and fresh confinement/runtime
review remain required. The prior three-case native receipt is unchanged;
**T029 remains open**. No production module, deployed build or availability gate
changed, and this sample is not an exact-version allowlist.


## Desktop pending approval experiment (2026-10-03 UTC)

A fresh isolated four-case native run on Hermes
`8afaab3703e336d72a72c812dd2dd249f04f166a`, with HMP base
`3e676ec10266ef958ca631b6f8384c6aa297745e` and the independently accepted
Desktop fixture v4, ended **3 passed, 1 failed, 0 skipped**. The full 292-file
candidate was frozen before preparation; production modules were unchanged.
The original three-case receipt remains intact.

- The real Desktop `prompt.submit` returned streaming, persisted the exact new
  user row in shared Bot Chat history, and held the exact native registry claim
  through the completed dispatch observation.
- The original pending API approval remained visible in AP3 while that owner
  was active. Verified fake-relay captures increased from the warm-up baseline
  of one to two. The pending sentinel and later exact-ID denial support that
  this was the original nonterminal request, not an expired request.
- After the fixture closed Desktop, its raw registry claim remained; this was
  the first failing assertion. The same original approval was still visible
  and exact-ID denial applied, but this does not prove a hide-and-reappear
  transition. WebSocket close followed by process termination is not evidence
  of graceful native session/registry release. That lifecycle question remains
  separate from the observed live-owner visibility and capture failure.

Current-receipt preflight proved same-sandbox child signal delivery and denied
signaling of a disposable external test sentinel, which survived. Native imports
passed without owner/old source modules. The run reported no leftover child
processes and no prepared/shared/protected byte changes. Failed fixture state
and private causal artifacts are retained; broad process-information isolation
and independent dependency wheel-byte provenance are not claimed.

Independent database inspection later created SQLite WAL/SHM sidecars inside
the retained private fixture despite `mode=ro` and `query_only`. The primary
database, registry and original test artifacts stayed unchanged; the private
sidecars are preserved and the review footprint is explicitly corrected. Future
inspection uses immutable database access or an isolated copy. This was not a
live host/database action.

**T029 remains failing.** The next repair must cover shared approval visibility,
answer and push consumers, with independent review and a new bounded runtime
receipt. There is no concurrent model-execution claim, upstream missing-primitive
claim, live installation, device, provider or release qualification. The fake
relay verifies signatures and captures requests; it does not open HPKE seals or
contact APNs/FCM. The live visibility/capture failure is distinct from the
unqualified close/release transition.

### Phone attachment admission checkpoint (2026-10-03)

The revised Photos/Files contract is accepted as input for normative amendments
and pure interface work only. It preserves attachment-first composition, the
existing Phone pending-send slot, bounded device-upload custody and fresh native
own-CMID row authority. The exact encrypted staging envelope, portable host
validator, complete upload/admission/readback implementation and OS/device tests
remain pending. No operational attachment Send or product + entry is available.

On inspected Hermes `8afaab3703e336d72a72c812dd2dd249f04f166a`, a synchronous
adapter busy refusal cannot guarantee no deferred execution: [startup restore
queues before plugin hooks](https://github.com/NousResearch/hermes-agent/blob/8afaab3703e336d72a72c812dd2dd249f04f166a/gateway/run_inbound.py#L212-L217),
and [cold entry can encounter runner busy handling or orphan FIFO rescue](https://github.com/NousResearch/hermes-agent/blob/8afaab3703e336d72a72c812dd2dd249f04f166a/gateway/run_inbound.py#L1243-L1344).
That [event type](https://github.com/NousResearch/hermes-agent/blob/8afaab3703e336d72a72c812dd2dd249f04f166a/gateway/platforms/event.py#L36-L123)
has no reject-policy admission ticket. This is a separate
`PHONE_ATTACHMENT_ATOMIC_ADMISSION_GAP`: native settlement must cover all
retaining/effectful exits, preserve the original CMID and ordered media, and
compare/create an exact absent session for an attachment-first Send. A refusal
must leave no deferred instruction or user row; an unresolved outcome remains
unknown. HMP will not patch private runner queues or ship FIFO as an alternative.
Later builds use actual required APIs under the minimum-version policy; this
revision is source evidence, not an availability allowlist or a universal
absence claim. Desktop-owned canonical multimodal admission remains a separate
upstream gap.

### HPKE/JCS vector preparation

The test-only source in [draft PR #92](https://github.com/MahdiHedhli/hermes-hmp/pull/92)
contains 151 finite case definitions and six pure-test methods. The earlier repaired
protocol source and lint-only delta passed their separate independent reviews.
The current eight-file metadata-minimization delta also passed a separate
source/data review; none of these verdicts admits vector execution.
It uses the frozen D1 suite, exact 16-byte `HMP push seal v1` info, an independent
Node generator/Python opener, and the original official RFC corpus. Package
archives and member digests are pinned as data. CI exposed lint and public
publisher-contact hygiene failures; the repair minimizes the five registry
records to selected provenance fields while preserving original-response hashes
and the existing privacy scanner. Package/archive/license bytes are unchanged.

**All 151 crypto case definitions remain unexecuted.** The separate fixed
stdlib-only codec run passed six methods and 33 subtests, with zero boundary
refusals and all 226 pinned inputs unchanged. It extracted ten pure functions
and two classes from the exact PR #92 checker source without importing the
whole checker, crypto packages, preflight or main. This verifies only the tested
JSON/base64/request-shape/transcript rules. No generated known-answer corpus,
installed/imported crypto package, production consumer,
relay/provider delivery or native app interoperability is qualified. Independent
containment review requires a startup watchdog, specific allocation-failure
observations with small positive controls, and exact accepted-canary/profile
receipt bindings. Runtime startup, hard resource enforcement, immutable input
and mount lifetime, loader closure and other denial/reaping controls still need
verification. Native and crypto execution admission remains closed. Owner provisioning choices
are not prerequisites for this test-only work.

The startup-supervisor v2 ownership repair is independently accepted in source.
The caller retains the exact child handle before startup and through observation,
handoff and receipt failures. All 140 source-review input hashes matched. A
separately reviewed fixed recipe then ran all 46 isolated synthetic controls:
46 passed, zero boundary refusals, and all 206 execution-review inputs remained
unchanged. The prior failed v1 source review and both failed recipe attempts are
preserved. This verifies the ownership repair under mocked failure cases; it
does not qualify native startup or runtime cleanup, or execute any crypto vector.
Exceptional holding can remain indefinite. Actual resource collectors, trusted
receipt provenance and immutable runtime/mount lifetime remain open. Native
startup and crypto admission remain NONE.

A separate root-admitted trusted startup attempt was refused before fork. The
collector exited 125 with no bound child or child log files. A fresh stdlib
context check identified the inherited macOS file-descriptor hard limit above
the supervisor's supported ceiling; all 247 source/history inputs remained
unchanged. This is a launcher-context refusal, not a failed controlled-child
startup. The failed attempt is retained.

The replacement trusted launcher lowers only its own file-descriptor limit to
32/32 before the existing preexec-free process launch. The collector and child
inherit that limit; the configured child limits, including `NOFILE` 32, remain
unchanged. Its ordinary child actually forked and was reaped, but exited 125
during limit setup: `FORKED, SETUP_ERROR`, no payload or child log bytes, no
signals or identity loss. The collector correctly failed, and all 270 pinned
inputs remained unchanged. That attempt did not identify the failing resource
or error. No startup-stall or TERM/KILL case was attempted, and neither failed
ordinary attempt is a startup/resource/crypto pass.

A later diagnostic-only ordinary attempt identified the exact failing call on
this macOS test runtime: setting the unchanged 256 MiB address-space limit raised
`ValueError`, with no errno available. The child was actually reaped after
`FORKED, SETUP_ERROR`, exit 125, with no child log bytes, signals or identity loss.
All 296 pinned source/history inputs remained unchanged. This identifies the
resource call, not the operating-system cause or resource enforcement. The
limits remain unchanged; no later startup-stall or TERM/KILL case ran. Supported
fixed-limit runtime validation remains open, and all 151 crypto definitions
remain unexecuted.

### Shared Desktop ownership repair contract

Independent review accepted the revised contract only; backend/mobile integration
and a new bounded native receipt remain pending. Explicit `owned`, `unowned` and
`unknown` state stays distinct from a legacy absent field. Unknown Bot ownership
hides answerable Bot cards while preserving reserved/releasable and other pending
state. Phone approvals keep their existing independent path. AP4 must preserve
settled replay/conflict/expiry handling before checking open Bot ownership, and
must not apply an answer under owned/unknown state. A point-in-time ownership
check does not eliminate the check/use race.

The native snapshot API exists, so a missing upstream primitive is not established.
Its default lenient mode can prune unknown-liveness entries; strict mode aborts
on unknown and can prune proven-dead entries. HMP currently omits strict mode.
The snapshot lacks hard parsing, entry-count, lock, probe and deadline bounds;
two worker threads and a caller timeout alone do not resolve this. Bounded
observation, native cleanup/read-route semantics and worker termination require
separate review before integration. HMP must not parse or mutate the native
registry as a second authority. The failing T029 receipt above is unchanged.

### Retained access and availability repairs

[Draft PR #93](https://github.com/MahdiHedhli/hermes-hmp/pull/93), at
`7b8138e4e62bd7cff975909f1a1cc09b6cee73c5`, applies the existing stripped
16-character API-key floor to the default profile's scoped fallback. Ten new
regression cases cover invalid types, empty/whitespace, below-boundary and valid
boundary values while retaining inline precedence and named-profile isolation.
Independent source review accepted the repair. Both exact-head hosted CI runs
passed; [PR run 37110174546](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37110174546)
reports 2,625 passed and 17 skipped, with lint, closed-surface and privacy gates
passing. Native startup already checks key strength; this was a false-availability
prerequisite, not a demonstrated authentication bypass. No live deployment or
credential change is claimed.

[Draft PR #94](https://github.com/MahdiHedhli/hermes-hmp/pull/94), at
`69bd1d6f2d03d78ebe0ea8cfe36d1e5ac039dfc1`, adds the existing Hermes-session
presence guard to device listings before store opening. Operator listings still
work without a TTY; mutation ordering and other read paths are unchanged.
Independent source review accepted the three-file repair. Twenty new cases cover
18 session refusals and two populated operator controls. Exact-head hosted
[run 37112555432](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37112555432)
passed 2,635 cases with 17 skips and one existing warning, including lint,
closed-surface and privacy checks. This mitigates accidental metadata disclosure;
the same OS user remains the authority boundary. No live deployment is claimed.

[Draft PR #95](https://github.com/MahdiHedhli/hermes-hmp/pull/95), at
`c0d0945b64058e3f337c8ff7181ec3294387df9a`, repairs the large-inventory finding
in reviewed source. The local listener-file read/write/removal limit is 64 KiB;
legacy small-record parsing and the pinned network ready-read limit remain
16 KiB. Larger records require a closed schema, canonical identity, bounded
ASCII fields and complete unique profile/health coverage. All 128 supported
maximum-length profiles and derived names are preserved without truncation.
Bounded projection and incremental encoding retain atomic failure behavior.

Independent source review accepted the four-file repair. Author and independent
focused runs each passed 113 cases: 65 new and 48 existing controls. Exact-head
[run 37114626278](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37114626278)
passed 2,680 cases with 17 skips and one existing warning, including lint,
closed-surface and hygiene gates. Combined source/CI status is recorded below.
Old readers may reject large records; an out-of-domain (>128) failed refresh can
retain an older snapshot fresh for up to 45 seconds. Freshness does not prove
current live roster completeness. The same OS user remains the authority
boundary. Neither finding establishes an owner incident.

The three repairs are now composed in [draft PR #96](https://github.com/MahdiHedhli/hermes-hmp/pull/96),
at `df30e09309569550232af6fbec4596817a75f464`. Independent source review verified
exact CLI composition, eight unchanged carried files and 283 untouched common-parent
files. Exact combined-head [CI run 37116039263](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37116039263)
passed: 2,710 tests, 17 skips and one existing warning, with lint, closed-surface,
log hygiene and privacy checks. This accepts the combined source and configured
CI scope. Native, mobile/device integration, activation and deployment remain
pending; the residual limits above still apply. No new upstream API is required
for these three repairs.

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

## Published attachment codec CI (2026-10-03 UTC)

The pure codec slice is now published in draft [HMP PR 98](https://github.com/MahdiHedhli/hermes-hmp/pull/98)
at `7cbdf8199e0b372911d02e15fc41cd1dc9babc59` and draft
[Mobile PR 72](https://github.com/MahdiHedhli/HermesBotMobile/pull/72)
at `b0107a70b22cabfa3e2f134da888714141f3aae6`.
[HMP source CI](https://github.com/MahdiHedhli/hermes-hmp/actions/runs/37130502909)
passed, including 2,767 unit/tool tests with 17 skips and one warning.
[Mobile source CI](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37130507541)
passed app/client analysis and tests, security hygiene, source gates, and 145
release-wrapper/scanner regression checks. The second same-commit
[Mobile CI run](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37130504615)
also passed. These are complete results for the named source workflows, with
no skip or warning recast as a pass and no release security gate waiver.

The next checkpoint below supersedes the earlier shared-slot implementation
status. The public feature remains incomplete: asset encryption, picker ownership,
custody/upload/send, native atomic admission, authorized readback and physical
device gates are still open. Source CI does not qualify those missing capabilities
or make the **+** media route available.


## Signed Android reporting validation (2026-10-03)

The exact signed Free Android code 2 (`8671061`, APK SHA-256
`04c247fff5e4e35ec2d6e4df2127aaf62d9bdd2443dd6a364d846c362d0a96df`)
passed a bounded, independently inspected emulator-5570 report walkthrough.
Initial excerpt-off, privacy/consent, editable opt-in synthetic preview, Cancel
and reopened reset were observed. One explicitly sent synthetic report with
excerpt off produced the Android success acknowledgement and one independently
correlated receiver record with a receipt and approximately 30-day expiry.
No private receipt token, KV key or test content is published here.

This supersedes earlier locked-emulator/report-pending checkpoints. Physical
Android, paired/live reviewer coverage and an opt-in excerpt submission were not
tested. No wire capture, extra Send/retry, host or receiver deployment, Play upload
or submission occurred. Provider-aware Data safety, full reviewer access,
exact-source automated release-security-review PASS and replacement upload/submission
remain open. No usable Android beta install link or release acceptance is claimed.


## Android provider and staged-build review (2026-10-03)

Historical initial review; the later supported-draft/publication checkpoint below
supersedes its prepared-only and unsent-support statements.

The provider inventory and exact-build reviewer matrix are complete with independent
factual acceptance; final Data safety answers and release certification remain open.
Fresh Console reads distinguish Free code 1 (`150dd06`) available to internal
testers from the closed Alpha release marked **not yet sent for review**. There
are 13 unsubmitted changes. Verified local replacement code 2 (`8671061`) is not
among uploaded bundles; no public Android enrollment/install link is verified.

The existing bounded emulator report acknowledgement and independent KV receipt
correlation remain valid; they do not certify physical, live-host or full reviewer
access. The saved no-restrictions answer is inaccurate for live pairing and host
approval. The owner-selected synthetic/BYO-host scope remains: no exposed reviewer
Hermes, local LLM or automatic removal of product features. A Google access
clarification is prepared, not sent; no full-access certification is made.

Data-flow review includes HMP host recipients, Cloudflare content versus network
metadata, consented Android recognizer fallback, TTS, public/host-local image
requests and relevant-version aggregation. **PLAY-QR-METADATA-1** records ML Kit
diagnostics/usage metrics separately from on-device QR input processing. Code 2
APK barcode metadata versions 17.3.0 and 18.3.1 match current primary guidance;
that is not a telemetry/network capture. Recipient/controller purposes, sharing
basis, category/retention mapping and the older inactive upload's relevance remain
explicit gaps. **PLAY-VOICE-1** remains open. No new report Send/retry, host or
receiver deployment, permission/provider connection, Play upload or submission
occurred during this review.

## Supported Android provider drafts and published privacy — 2026-10-03 UTC

This supersedes the earlier prepared-only scanner/privacy and unsent-support
status. Independent provider review accepted source/policy-supported mappings;
Console draft-save confirmations were observed. Messages are required collected
content; other user-generated content/actions and voice remain optional. ML Kit
Diagnostics and Device IDs are conservatively collected/shared, required and
non-ephemeral, with analytics and security purposes; collected identifiers also
serve app functionality. Code 2's optional report route includes conservative
Cloudflare IP-derived approximate-location handling. No GPS/QR-frame upload,
advertising ID, Firebase Analytics or shipped phone photo/video upload is claimed.

The [privacy policy](https://hermes-bot.app/privacy.html) now includes the reviewed
ML Kit and Cloudflare network-metadata disclosures. Site
[PR #10](https://github.com/MahdiHedhli/Hermes-Bot-Site/pull/10) retains the October 2
effective date and adds an October 3 revision date; exact live bytes were verified.
The single authorized Google Play Support BYO-host clarification was sent and
confirmed. No reply or policy exception is established by the ticket.

This is a saved draft, not a final Data safety declaration or full-feature reviewer
certification. Actual OEM speech processing/retention, provider metadata retention
and native transport remain qualified; the report-record 30-day TTL is not global.
The saved no-restrictions access answer remains inaccurate. Last inspected code 1
is internal available/closed unsubmitted; older code 2026092917 has a Draft track
with zero releases and unpinned source, while code 2 remains local/unuploaded.
Truthful reviewer access, exact-source automated security review, independent
signed-artifact acceptance and required physical/native gates remain open. No
support resend, report Send, device/provider/permission change, host exposure,
Play upload/submission or feature deployment occurred in this documentation update.

## Published Phone pending-slot adapter (2026-10-03 UTC)

The scoped shared-slot persistence adapter is published in draft
[Mobile PR 73](https://github.com/MahdiHedhli/HermesBotMobile/pull/73), exact source
`416dbe5b5a1e351ad446232a4c2aea4d7f71fa22`, stacked on the reviewed attachment
contract branch. Its fourteen committed files match the frozen V5 source.
Independent reviews accepted the bounded persistence/source changes. Root cached
focused app suites passed **110 cases with zero failures**; unchanged client
source retains **19 passing cases**. Earlier compile and V3/V4 failures remain
historical evidence. Transparent real type-query delegation in the tests does
not establish the original SDK failure cause or qualify native OS cryptography.

The adapter reads one sealed pending slot for legacy text or attachments, uses
registered read revisions and lifecycle-scoped compare-and-write, and preserves
malformed/unavailable distinctions. This is source implementation, not a working
mobile picker or attachment Send feature. Hosted source CI failed at this exact
commit: the network guard rejected two local `File.open` calls, and the app
analyzer reported two warnings. A focused reviewed repair is needed; no CI pass,
physical durability or release qualification is claimed.

The next-contract status below is historical; the implemented owner checkpoint follows.
That independently accepted contract covers private pending-slot inspection,
conservative restart normalization from `messageMayTransmit` to `unknown`, actual
operation accounting through invalidation/close, and explicit clear refusal.
Source authoring has begun on the exact published adapter base; no source tests
or production Phone route are accepted yet. A lifecycle-admitted conservative
normalization may finish after page/session loss; stale work must issue no
current capture. Successful clear needs a separate publication-currency decision
and actual native/owned-cleanup proofs. Full D4-S, encrypted assets, native atomic
admission/upload/readback and the **+** media route remain open. No upstream
Hermes change, live host change, deployment or release is implied.

## Phone pending owner and repaired source CI (2026-10-03 UTC)

The scoped slot parent is now `a3fa1febb95127762ae936edec70663a9b98edfd`, in
[draft PR #73](https://github.com/MahdiHedhli/HermesBotMobile/pull/73).
Actual hosted App CI [37147527021](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37147527021)
passed on that exact head. Earlier failures remain historical evidence: local File.open calls
needed a reviewed exact-blob lexical allowance; test lint and a shallow-checkout historical-object
assertion also needed correction. The allowance exempts only `open` for unchanged reviewed local
file bytes. All network/import/type/acceptance guards remain enforced, with matched negative
controls and actual depth-one regression checks.

The internal pending owner is published at `d31fafa520a5f1c505f35ec8d591d8104a29b9e6`, in
[draft PR #74](https://github.com/MahdiHedhli/HermesBotMobile/pull/74), stacked on that parent.
Independent review accepted the exact two source/test paths and their disjoint composition.
Root's cached pure Dart owner/lower-slot/send suites passed 83 aggregate checks, with zero failures;
those executed source bytes are unchanged in the published composition. Cached client analysis
exited zero with three infos, including one new initializing-formal suggestion; the existing public
named environment parameter is retained. Current combined-source network and privacy scans passed;
new-head hosted CI was pending at the initial checkpoint. Subsequently, exact-head App CI
[37148001498](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37148001498) and
[37147969675](https://github.com/MahdiHedhli/HermesBotMobile/actions/runs/37147969675) passed.
These CI results do not establish full D4-S, native/device behaviour or release qualification. The adapter's earlier 110 app and
19 client focused results remain separate evidence, not extra owner tests.

This owner permits current scoped inspection and only conservative restart normalization of
attachment `messageMayTransmit` to `unknown`. Private captures compare instance/profile, all
foreground/lifecycle/slot/page/session generations and exact identities. Its single actual pipeline
stays reserved through reads, admitted CAS, fresh typed post-read, invalidation and close. It joins
already admitted normalization after UI currency loss and returns stale without claiming the write
was prevented. Every clear request still refuses with no I/O.

Production Phone environment/route/session derivation, successful clear with native and joined
cleanup proof, encrypted owned assets/quotas/orphans, picker/tray, upload, atomic native admission,
actual own-row readback and physical/device/provider/release gates remain open. Full D4-S and the
complete attachment flow are not complete. The next independent local prerequisite is the D4-A/F
encrypted-asset/file-custody contract; no real native crypto or file-attacker custody is established
by synthetic storage tests. No attachment UI or release is enabled by these source publications.

## Pure phone asset layout source (2026-10-03 UTC)

[Draft PR #75](https://github.com/MahdiHedhli/HermesBotMobile/pull/75), source
`c998ef9edb880798864f40650d050aaa301a5fef`, adds the internal canonical context/header,
chunk AAD and completion encoders on the reviewed pending-owner branch. Interface and exact
three-path source received independent review. The seven byte-layout fixtures are synthetic
encoding data; their declared hashes do not establish authenticated ciphertext or key entropy.

Root ran 64 focused cached synthetic tests: 17 new layout tests and 47 existing attachment-domain
tests, with no failures. Controls cover all six MIME discriminants, 128 chunk ordinals, exact
integer timestamp endpoints, malformed Unicode/IDs/hex, field bounds, buffer mutation and fixed
error privacy. Focused analysis exited zero with one nonblocking test-local const style info.
The network guard and source private-value scan passed. The unchanged captured-log scanner passed
against four historical logs and its existing reviewed baseline; this creates no new runtime-log
or device evidence. Hosted exact-source CI was in progress at publication; it is separate from
these focused results.

The new class only encodes bounded declared data. It does not encrypt, verify digests or tags,
create a file/key/source capability, publish a tray, upload or enable attachment Send. Full D4-A/F
remains open: native purpose and ABI, cryptographic controls, catalog/current generation, clocks,
quotas/orphans, descriptor custody, normalization/picker integration, atomic native admission,
actual own-row readback, complete device flow and release verification are still required.
Native AES preparation can follow the existing iOS Keychain construction and an Android path
that verifies StrongBox/TEE protection and refuses unverified/software outcomes. No optional
software fallback or new native operation is adopted by this encoder checkpoint; existing
release residuals remain open.


## Approval mode and operator test planning — October 4, 2026

**AM1 is officially planned:** mobile read/change of native `manual`, `smart`, and
`off` approval mode. Native mode is persistent and profile-wide; a future HMP
capability and explicit gateway-admin write contract must expose that scope,
confirm weakening, preserve hard-deny safeguards, and provide authoritative
saved/effective readback. Approval-answer ownership or jobs/model control grants
do not confer mode-write authority. This is backlog/specification work; no mode
selector or live setting change is implemented.

**AT1 remains separate:** an operator-invoked, explicitly device/profile/session
scoped synthetic approval card for a harmless no-op. Its in-process producer
contract has independent acceptance and bounded source authoring is active.
The proposed `hermes hmp approvals test --device <paired-device-id> --profile
<bot-profile> --session <existing-test-session-id>` command is not implemented
or runnable. Native `hermes approvals test` is verdict-only and does not prompt.
Local operator IPC, current grants and target-device projection, exact native
lifecycle integration, and phone qualification remain pending; no tool, model,
message send or persistent permission rule may be produced by the test.


## Asset cipher runtime and approval-test source checkpoint (2026-10-04 UTC)

The current isolated asset-cipher candidate compiled on the host-JVM and
unhosted macOS XCTest routes. Actual named results match the complete selected
classes: all 24 Swift tests passed; Kotlin executed 22 tests with 20 passes and
two failures, with zero skips or assumptions. The failing Kotlin tests are
`officialNistSevenPrimitiveKnownAnswersOnly` and
`corruptionHasNoReceiptAndDoesNotRetryOpen`. Their exception locations remain
unknown in the captured name-only reporter; a bounded diagnostic is being
prepared. This checkpoint supersedes earlier statements that no selected native
tests had executed, within this isolated host scope.

The candidate remains incomplete. The two Kotlin failures require diagnosis and
repair; Android keystore, iOS device key storage, production asset custody,
current-owner integration, picker/upload and full media-send qualification
remain open. These host results provide selected synthetic coverage only.

AT1's in-process synthetic approval producer has a frozen source candidate and
eleven unexecuted fake-test definitions. Independent review requires explicit
loop-applied completion fences before terminal reconciliation, distinct local
pre-invocation cancellation provenance, and the remaining causal
lifecycle/schema/identity/privacy controls. Source repair is active. The
operator command, authenticated target binding, bridge factory and phone-card
projection still require implementation and verification. AM1 approval-mode
control remains an official planning feature.


## Planned device permission readiness (2026-10-04)

**AR1 is an official planning feature**, with nine unchecked tasks in the
[mobile permission-readiness plan](https://github.com/MahdiHedhli/HermesBotMobile/blob/056a48120460542dcd097479d687ac3850b004bb/docs/planning/MOBILE_PERMISSION_READINESS_2026-10-04.md).
Pairing and subsequent refresh should distinguish authenticated per-device
capability, current entitlement, and host/API availability. Missing rights
should have safe, actionable explanations within already authorized scope;
unauthorized resource existence must remain private. A jobs404 alone cannot
distinguish a controls refusal from a native endpoint404.

Request access creates a request. Fix access requires an explicit authorized
administrator decision, current device/profile checks, and authoritative
stored/effective readback. There must be no silent grants or broader defaults.
The plan covers revocation, stale state, concurrency, denied requests and lost
acknowledgements, with negative tests and separate physical/release acceptance.
Current jobs/default-model controls remain separate from approval-answer
ownership and approval-mode/gateway administration. AM1 mode planning and AT1
synthetic approval testing remain separate. AR1 is not implemented or deployed.


## Asset cipher repair and approval-test verification (2026-10-04 UTC)

A bounded diagnostic localized the two earlier Kotlin failures. Independently
reviewed repairs changed the complete-record matcher for the pinned NIST fixture
and declared the private fake-backend checked exception contract. A fresh
focused host-JVM run compiled and executed the same 22 named methods: all passed,
with zero failures, skips or assumptions. The previous failed runs remain
historical evidence. The unchanged Swift candidate retains its earlier 24
passing unhosted macOS tests; it was not rerun for these Android-only changes.

These are selected synthetic host tests. Production owner/catalog and encrypted
file custody, Android hardware keystore and iOS device key behavior, picker,
upload, attachment Send and full D4/release qualification remain open.

AT1's repaired in-process synthetic approval producer has independent source
acceptance and 31 passing isolated fake tests. The operator command is still
not implemented or runnable: local-operator authentication and paired-phone
projection/answer contracts require separate integration. No native approval
card, tool execution, permission grant or phone delivery was exercised by those
fake tests. AM1 and AR1 remain official planning features.


## Planned Desktop bot identity on Mobile (2026-10-04 UTC)

BI1 is an owner-authorized official planning feature with nine unchecked tasks
in the Mobile roadmap. It covers host-backed display names, recognizable
shape/color/eye characters and static custom images across roster, chat header
and bot details. The inspected Desktop has presentation metadata and separate
avatar assets; the inspected HMP roster and Mobile model lack that projection.
Desktop-local customization may be unsynced, so fallback provenance stays explicit.

The plan binds presentation to authenticated instance/canonical profile and
current credential generation, without changing routing or privileges. It allows
only a small negotiated presentation DTO, never private prompts, SOUL/personality,
chat or general settings. Older hosts retain a usable safe fallback.

The inspected native get_asset helper reads the whole file before responding.
Future exposure requires a fixed-avatar authenticated primitive bounded before
host reads, plus transport/decode limits; an after-read cap is insufficient.
Arbitrary paths, URLs, redirects and active content are excluded. Separate image
and metadata revisions, cache invalidation, stale-read fencing, revoke/unpair,
accessibility and reduced motion are part of the acceptance plan. Implementation,
wire-contract approval, physical parity and release qualification remain pending.
AM1, AT1 and AR1 remain separate.


## Physical jobs access and current feature integration (2026-10-04 UTC)

An owner supplied a populated Bot Jobs screenshot after an explicit per-device
controls grant. This confirms the Jobs read view on that iOS phone. It does not
confirm job creation, edits, deletion, scheduler execution or delivery, and no
authenticated HTTP trace was captured. The third, controls-denied device was
unchanged. A second physical phone remains unverified because its supported
public pairing-metadata read reports the device locked; no identity was inferred
from enrollment timing and no grant was made to an unidentified pairing.

Default-model controls are already allowed on the verified phone, but the host
model-management flag is absent and fresh per-profile health reports disabled.
The inspected host runs native `ca705dbf` / `0.21.5` with exact installed HMP
`4d6863e` bytes, meeting the model floor. Required model-reader/writer definitions
are present in that native source; no provider catalogue or current model was
read and no model was changed. This is a separate host setting, rather than a
minimum-version allowlist refusal.

The exact native CLI canonicalizes the nested gateway spelling to
`platforms.hmp.extra.model_management.enabled`. The HMP gate reads the live
adapter config object, not a fresh disk file; the inspected supported reload
signal performs a graceful drain/relaunch. Proposed enablement therefore needs
the one Boolean leaf and a supported graceful host restart, with explicit owner
approval, unchanged phone grants and post-restart readback. It enables the host
surface for controls-approved devices and their separately authorized bot
profiles; it must not grant a denied device, alter an approval mode or select a
model/provider. That change is pending and has not been performed. AR1 remains
the official permission-readiness/remediation plan, not deployed automation.

The inert native asset-cipher slice is published in Mobile draft
[PR76](https://github.com/MahdiHedhli/HermesBotMobile/pull/76), exact head
`b675b96b4593d4893c9ccb0557218fc097b44436`. Both recorded exact-head hosted CI
runs succeeded. Selected synthetic prerequisites remain Kotlin 22 passes and
the unchanged earlier Swift 24 passes; neither is physical key-store evidence.
Production composition stays unavailable. The iOS protected-catalog codec and
transaction contract is now a frozen proposal pending independent review.
Android protected-head custody, genuine pairing/draft ownership, key/file
handoffs, native clocks, descriptor custody, picker/upload/Send and complete
media/device/release qualification remain open.

AT1's unwired no-op approval producer is published in HMP draft
[PR99](https://github.com/MahdiHedhli/hermes-hmp/pull/99). Finite lint repair
`d33f4c34cd390c3f1ac2210e72194587598728e1` received independent review and a
fresh isolated run of the same 31 fake cases passed with three collection
warnings. Its hosted CI passed lint, then reported 2,671 passes, 17 skips and one
failure: the producer filename was missing from the explicit module inventory.
Later security-check steps were skipped, so this checkpoint does not claim
that CI passed. A finite inventory/documentation correction is under review;
the equality/import checks and all security scanners remain intact.

The CLI/paired-phone bridge remains unimplemented. Its independent contract
review requires precise direct-await ordering, a distinction between framing
half-close and operator abandonment, and fixed phone refusal responses. The
proposed `hermes hmp approval-test begin` syntax is not runnable. Fake tests do
not demonstrate a real native approval card, paired-phone delivery, grant, tool
execution or deployment. AM1 approval-mode control and BI1 Desktop identity
remain official planning features with separate implementation gates.


### AT1 source-check follow-up (2026-10-04 04:50 UTC)

The five-line inventory/documentation repair is published at HMP
`736662caafb26ecb58c7906530e4ebd561c26d04`. Its two existing targeted inventory
and import checks passed; exact-head hosted CI run `37178015906` then passed
lint, 2,673 unit/tool cases (17 skips, four warnings), closed plugin surface,
log hygiene and privacy checks. This supersedes the preceding pending-inventory
checkpoint. Caller bridge contract v4 received independent contract-only
acceptance; source integration and phone/native/card/release verification remain
open. No operator command is runnable and no host setting was changed.


## Cross-platform candidate and readiness checkpoint (2026-10-04 UTC)

The cross-platform test candidate retains Mobile source
`8671061b85c8019e31172ed497cbf27dc327c6dd` and its pinned HMP dependency.
Production source is unchanged; newer feature branches have not been silently
mixed into this candidate and existing features have not been removed.

| Item | Observed result and remaining qualification |
| --- | --- |
| Android beta 1.0.0 / code 2 | Existing exact signed APK/AAB retained and independently rehashed. Prior emulator report consent/cancel and one synthetic acknowledgement remain bounded evidence; physical Android qualification is pending. This candidate has not been uploaded or submitted. |
| iOS local dogfood 1.0.0 / 2026100401 | Guarded release-mode build and independent signed-artifact inspection passed. Installed on one owner physical phone; fresh app metadata confirms the build and public pairing registry bytes remained identical across upgrade. UI, sealed draft readability and hardware qualification remain pending. |
| Native qualification harnesses | Separate iOS example and Android self-instrumented test package built and signing/isolation inspected. Neither has been installed or executed. Generic PASS, hardware-unavailable branches and API skips cannot establish positive physical hardware evidence. These artifacts do not replace shipping-app qualification. |
| Release gates | Physical Android/iOS acceptance, exact-source release security review, truthful whole-package declarations and reviewer access remain open. The iOS owner artifact is development signed, not an App Store/TestFlight distribution export. No release submission occurred. |

Public HTTPS image handling remains distinct from host-local output. The
candidate has host-image seams without production composition; an emitted
MEDIA path is not authority to read an arbitrary host file. Existing model
confirmation concurrency and report failure/ordinary-chat acknowledgement UX
are retained as finite qualification/repair findings, rather than falsely
reported as observed device failures or fixed by removing functionality. No
additional report submission was made.

### Host model readiness follow-up

This supersedes the preceding pending-enablement checkpoint for one owner
deployment. At 05:02 UTC, an explicitly approved single Boolean
`platforms.hmp.extra.model_management.enabled=true` and supported graceful
gateway restart completed. Sanitized before/after evidence verified unchanged
other settings, model/provider selections, device grants and profile membership.
Three profiles reported send/jobs/model readiness; one pre-existing unavailable
profile remained unavailable. This is point-in-time host readiness, not proof of
phone current/options rendering, an actual model change or later host state.

### AR1 source progress remains separate

Mobile readiness warnings and local remediation guidance are published in draft
[PR77](https://github.com/MahdiHedhli/HermesBotMobile/pull/77), exact source
`3c5e5b9edd84fb93d1351b3b97120449bb0ee369`. Recorded exact-head hosted CI runs
`37185279303` and `37185274691` succeeded after the reviewed large-text repair.
This source/fake verification does not establish a deployed HMP readiness
endpoint, physical pairing/permissions, a mutating Fix action or release
acceptance. It is not part of the 8671061 installed candidate. AM1, AT1, BI1 and
complete media composition retain their separate implementation and integration
gates. No automatic grant, flag change, restart, model selection or job execution
is introduced by this documentation checkpoint.


### AR1 reviewed local source checkpoint (2026-10-04 UTC)

The separate HMP read-only readiness slice is now locally committed at
`982bc034a7e87346e6959ca5477a0b3bc5e33bab`. Independent review accepted the
exact source checkpoint in the recorded synthetic environment. The focused
readiness/actor checks passed. The full unit run had 2,433 passes, 16 skips and
one offline packaging-cache setup failure; the unchanged packaging case passed
in a separate offline follow-up using the existing cache. This is composite
source evidence, not a new all-suite pass or supported-version matrix.

The slice provides authenticated fixed capability and authorized bot-scoped
readiness diagnostics. It keeps host flags, device controls, endpoint
configuration and unprobed API reachability distinct. It adds no live probe,
automatic grant, actual request send, administrator Fix, model selection or job
execution. Mobile warnings/local guidance remain the separate PR77 source.
The HMP checkpoint remains local; neither slice has been composed into the
installed 8671061 candidate or deployed as part of it. Runtime, native version,
physical phone, security and release gates remain open.

The latest verified owner iOS candidate is **2026100401** on iPhone15, superseding
the earlier 2026100204 installation checkpoint above. Android remains the exact
signed beta code2 candidate; the attached physical Android is USB-debugging
unauthorized and has not been installed or qualified.


## Reviewed UI repairs and next test candidate (2026-10-04 UTC)

A separate local test candidate has been built from the retained `8671061`
baseline and reviewed finite corrections. Current functionality, declared
dependencies, native permissions and connection routes are preserved. The
original candidate and its artifacts remain available; new feature branches
have not been silently mixed in.

| Item | Current evidence and limits |
| --- | --- |
| Report delivery feedback | Reviewed app repair `ba148c4` passed 109 focused fake tests and changed-file analysis. Uncertain delivery remains explicit; ordinary chat gives local feedback for confirmed report acknowledgement. No extra report was submitted, and physical acceptance remains open. |
| Model confirmation | Reviewed app repair `47cbd97` passed 22 focused app tests, five fake client tests and changed-file analysis. One confirmation remains reserved through settlement and retires when its owning view changes. No actual host model or permission was changed; native persistence and phone checks remain open. |
| Android local beta 1.0.0 / code 3 | APK and AAB built through the unchanged guarded wrapper; scans and expected upload-signature checks passed. Earlier cache-related guard refusals were retained and regenerated outputs rechecked. A bundle reader warning remains under assessment. Neither artifact is installed, uploaded, submitted or physically qualified. |
| iOS local dogfood 1.0.0 / 2026100402 | Guarded build and strict signature check passed. This is an owner development artifact, not a distribution export. It has not been installed; the last verified owner installation remains `2026100401`. UI, preserved saved content and native hardware checks remain pending. |

Independent source-composition review accepted the exact finite changes. Binary
review, physical Android/iOS journeys, hardware outcomes, exact-source security
review, whole-package declarations and reviewer access remain separate release
gates. Source/fake results cannot establish installed functionality. The last
scoped USB Android inventory was unauthorized; no device installation or UI
test followed from that inventory. Public-image handling and uncomposed
host-local media remain distinct; the latest candidate does not enable complete
media upload or host-local image rendering.

### AT1 prerequisite documentation reconciled

The no-op producer remains an unwired source prerequisite in draft
[PR99](https://github.com/MahdiHedhli/hermes-hmp/pull/99). Its separate pure host
request/frame DATA codec is now documented in draft
[PR100](https://github.com/MahdiHedhli/hermes-hmp/pull/100), exact source
`ffb2d9b2bb24d8f35488427a6c234024d3fba196`. The codec passed 135 focused
synthetic/inventory checks; exact-head hosted CI `37179997382` succeeded with
2,807 passes, 17 skips and four warnings. Counts overlap. These are not genuine
operator authentication, native card, socket or paired-phone delivery checks.

The proposed command is `hermes hmp approval-test begin`; it is not runnable.
Caller contract v4 permits bounded source authoring, while CLI/IPC admission,
current target-device/session authority, normal approval-lifecycle binding and
phone projection remain unfinished. AR1, AM1, BI1 and full media integration
retain their separate scope and qualification gates. No grant, provider, model,
job, live host or release changed through this documentation update.


## Approval-test transport and installed-device checkpoint (October 4, 2026)

AT1 now has a separately reviewed private local operator transport in
[draft PR101](https://github.com/MahdiHedhli/hermes-hmp/pull/101), exact source
`41daef17ab2e2fcd69f7d54c67469c8418cfd7e4`, stacked on codec PR100. Root passed
227 focused transport, codec and module-inventory tests after independent
source review. Counts overlap earlier codec results. The original 225-pass,
two-failure run is preserved; the independently reviewed fixture-only repair
restricts failed-write injection to the intended accepted response, without
weakening assertions or changing the accepted production source.

This covers isolated macOS Unix sockets and kernel peer UID, Linux credential
mocks, bounded framing and fake-handler lifecycle. Exceptional response or
notification errors retain the operation until its owned cleanup joins;
unknown finalization retires the generation. It is not a Linux kernel run,
a genuine different-UID adversarial test, native producer settlement or a
phone-card check. No current CLI, adapter or server registers the endpoint,
and no production handler exists. Current device/profile/session admission,
normal lifecycle binding, typed phone projection/answer/cancel and physical
qualification remain unfinished. The proposed `hermes hmp approval-test begin`
command is still unavailable; AT1-T003 remains open.

The finite cross-platform candidate's artifact identity review is accepted
only for local dogfood. iOS build `2026100402` was subsequently installed on
the owner iPhone 15 Pro Max through a data-preserving update. Fresh native app
metadata confirms that build. The source-declared non-secret public pairing
registry was byte-identical before and after, with two saved instances. There
was no uninstall, launch, UI/hardware test, keychain or sealed-content read;
this does not verify all saved chat content. The iPhone 12 Pro remains pending
its last lock/access blocker. Android code 3 artifacts remain uninstalled and
unqualified; the connected USB Android still reports unauthorized debugging.

The AAB streaming-reader warning, exact-source security review, whole-package
provider/declaration and reviewer-access gates, and physical Android/iOS
journeys remain open. Public HTTPS image rendering has earlier owner evidence;
host-local `MEDIA:` rendering and complete photo/file upload remain unfinished.
No host grant, actual model, job, provider or release changed in this checkpoint.


## LB1 priority and pure-source checkpoint — October 4, 2026

The owner selected device-local bot sections and bundled static icons next,
then host-local chat images. Essential release checks continue in parallel.
AT1 remains at its separate reviewed transport checkpoint; no runnable approval
test command or complete phone card flow is inferred from it.

LB1 planning is in `specs/044-local-bot-sections-icons`. Root locally committed
`5e6458c`: a bounded immutable section/preference model, eight closed static
icon IDs, typed edits, and a canonical depth-limited codec. Independent source
and execution-evidence reviews accepted that pure slice for local commit. The
exact focused run passed 16 tests; strict analysis found no issues. The prior
failed analysis is preserved as a failed gate, followed by the reviewed correction.
No dependency, SDK, native permission or host capability was changed.

This is source progress, not a phone feature or release pass. The dedicated
sealed storage/CAS/controller seam is still a proposal for independent review;
section management, icon picker, roster/header/details integration, encrypted
persistence and actual Android/iOS UI/accessibility checks remain outstanding.
Custom sections are the stated working assumption, not an invented owner answer.
Pending request-access rows and saved-content disclosure must stay intact.
Host-local `MEDIA:` text remains unrendered until authenticated producer and
bounded serving authority are composed; a path string alone grants no file read.

The separate release lane freshly observed only Android version code 1 Active
and 2026092917 Inactive in Play's complete two-bundle inventory; local code 2/code 3
were absent. Publishing showed 13 changes not submitted. Saved Sign in details
No does not certify the QR/paired-host flow is freely reviewable. Exact consumer
validation still needs a verified resolved dependency closure; physical device,
provider/Data safety, reviewer-access and security-release gates remain open.
No upload, submission, provider/permission change, live host operation or report
Send occurred in these source/release-read checkpoints.


## LB1 source-integration checkpoint — October 4, 2026

Device-local bot sections and static icons remain the current feature priority;
host-local images follow. Essential release checks continue separately.

The local implementation now includes custom section creation, rename, ordering
and removal; one section per current roster bot; eight bundled static icons and
reset to initials; grouped roster and scoped chat/session headers. Each phone and
paired instance has its own layout. Removing a section moves its bots to Other
bots without deleting chats, pairings or grants. Pending access rows keep their
existing behavior. Local decoration is never authorization or routing authority.

The dedicated sealed slot, opaque context capability, production forwarding and
presentation controller are independently reviewed and locally committed. Writes
use bounded canonical data, lifecycle/partition locks, exact compare-and-set and
verified readback. A failed or uncertain save blocks further edits until explicit
scoped Reload; stale dialogs and callbacks cannot write for a replacement owner
or instance. Corruption is not silently treated as empty writable state. No new
SDK, dependency, permission, host flag or upstream API is introduced by LB1.

Recorded focused outcomes: 16 pure-model tests; 13 core capability tests; 52 new
slot/existing native-adapter tests; 23 controller/logger tests; 10 new widget cases;
and 115 existing Home/privacy/avatar/header regression cases. These scopes overlap
and are not a unique-test total or one end-to-end run. Strict scoped analysis is
clean. Earlier compiler/fixture failures remain historical failures followed by
reviewed repairs and new passing receipts. Final exact source composition is
accepted for guarded build preparation; signed artifacts and physical/native
storage, cold reload, accessibility and large-text qualification remain separate.
No deployment or release completion follows from the local source reviews.

The next host-image census identified already reviewed HMP descriptor/fetch source,
so that work will be reused rather than recreated. Remaining app Bot Chat loader/
card lifecycle wiring and ref recovery need exact integration review. Minimum
version eligibility remains distinct from API, authorization and operational
security gates. Assistant MEDIA text is not authority to read arbitrary host files.

The release lane observed the existing AGP loader's exact bundletool 1.18.3 resource
origins. Its one structural-consumer attempt stopped on a VerifyError before
validation invocation; no consumer pass is claimed. The prior streaming-signature
reader warning remains open. Android dev USB authorization, physical iOS/Android
qualification, exact-source release security checks, package/provider Data safety
and truthful paired-host reviewer access remain open. No new store inventory,
upload, submission, Support ticket, host change or report Send is claimed here.

## Local bot organizer: build checkpoint (October 4, 2026)

The next feature order remains device-local bot sections/static icons, then host-local chat images; essential release checks stay parallel. LB1 now has two independently reviewed local test candidates: Android Free beta **1.0.0+4** APK and iOS **1.0.0+2026100403** Runner.app. Both sanctioned release-wrapper builds and artifact scans completed; signature checks passed. Tracked source and committed dependency locks stayed unchanged. Generated SwiftPM resolution metadata is preserved separately and not silently committed. These are local development candidates, not store uploads or installed/device-qualified features.

Physical organizer/icon behavior, native persistence/cold reload, accessibility/large text and release qualification remain open. The Android dev phone still needs USB-debugging authorization. The separate existing AAB consumer check remains blocked by a pre-validation VerifyError; these APK/iOS build successes do not resolve it. Provider/Data safety, reviewer-access and operational security release gates remain distinct.

Host-image integration now has a reviewed minimum-version/lifetime contract: reuse the authenticated host descriptor/fetch source, wire Bot Chat only, share its bounded photo-operation budget, clear pixels on owner/access/lifecycle loss, and keep MEDIA text non-authoritative. The narrow visibility prerequisite is being reviewed/tested before wiring; bounded 404 recovery and Phone integration remain later slices. No host enablement, grant, provider, device-install or release claim follows.

## Bot Chat host-image source checkpoint (October 4, 2026)

Feature order remains device-local bot sections/static icons, followed by host-local
images, with essential release checks in parallel. LB1 Android code 4 and iOS
2026100403 are local build candidates; physical organization, sealed persistence,
cold reload and accessibility checks remain pending. Neither candidate contains
the later Bot Chat changes described here, and no new installation is claimed.

Bot Chat integration is independently reviewed and locally committed at `22af540`.
Only typed image_generate tool-result descriptors select the authenticated host
loader. MEDIA paths stay unmodified text and cannot authorize arbitrary file reads.
Public and host cards share a stable two-operation budget, including cancelled
fetch/decode work that has not actually settled. Media loses validity on a different
controller owner, instance, epoch, profile, missing or revoked bot access, blocking
state, app pause or screen teardown. Resume does not fetch automatically. Loaded
card images and viewer clones are cleared on scope loss; send/write eligibility
does not supply read authority. The narrow sticky saved-text visibility repair is
also locally reviewed; no whole-chat/privacy certification follows.

The focused nine-file fake/synthetic suite passed 158 cases, including 14 new
Bot Chat cases and the production loader epoch-fence test; strict analysis of the
five changed files is clean. The first fixture-timing failure and later unused-import
warning remain preserved, followed by reviewed test-only corrections. These are
source checks, not native host serving, networking/codec, signed device or release
qualification. Explicit bounded 404 descriptor recovery is the next separate slice.
Phone/session surfaces retain their separate evidence; no new host install, flag,
grant, provider, permission or upstream API was introduced.

Essential release checks remain open. A separate
non-invoking Android tooling diagnostic failed with VerifyError at its hash-helper
definition, before its own input checks or any BundleTool class/method lookup;
root pre/post source/artifact bindings were preserved. The exact failing class is
unknown, and this does not attribute the error to the app bundle or resolve the
earlier structural-consumer failure. Physical devices, operational security,
provider/Data safety and truthful reviewer access remain release gates. No store
upload/submission, Support resend or report Send occurred.

## October 5, 2026: composed local organizer/host-image build evidence

A reviewed local app composition (`ff99b6a`, HMP source pin `83a5943`) now produces signed Android Free beta 1.0.0+5 and iOS 1.0.0+2026100501 test candidates through the unchanged guarded release wrapper. Independent terminal review joined source/tool hashes, package/build/signature identity, all 57 iOS bundle files and preserved dependency identities. The previous iOS bundle was retained. Android APK SHA-256: `8348fbba3b96e3bd9cac67c30ef3c5d347f14a79785faa65841e7f9a36e039c7`; iOS manifest SHA-256: `1e482103292756bbf772eda2207a97471730e44f25bb935726900a2709d42746`.

Bot Chat media loader/card wiring and bounded explicit 404 recovery are now included in this local source. Retry revalidates the original current tool row/session/access owner and fetches only a changed authenticated descriptor; unchanged descriptors stay unavailable. Assistant MEDIA text is never host-file authority. Phone/session integration remains a separate prerequisite. This evidence does not demonstrate installed phone behavior or a deployed host serving the new media route.

The separate older code-3 AAB file-based structural check passed after the preserved tooling failure; streaming JAR manifest-order limits remain a separate observation. Physical/native media and organizer behavior, live operational auth-cache remediation, exact release security CI, active-package/provider declarations and truthful reviewer access remain open. This checkpoint is not store submission or release certification and introduces no upstream API, provider, permission, host flag, grant or live deployment.
