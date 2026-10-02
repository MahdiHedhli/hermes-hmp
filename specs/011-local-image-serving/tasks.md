# Tasks

> **Amended 2026-10-02.** The owner's minimum-version policy replaces the exact-build manifest, fingerprints,
> process anchor and preload qualification (S6/S6a/S6b). Their records below are **historical evidence about the
> retired design**, not current policy and not runtime behavior. See
> [Minimum-version conversion](ROOT_DECISIONS.md#minimum-version-conversion-supersedes-s6-manifestfingerprintanchor-s6a-admission-semantics-s6b-preload-qualification-2026-10-02)
> and the slices M0-M3 below. The feature is **unimplemented**.

`[ ]` means not started or not independently reviewed. Workers do not self-certify. No implementation task starts before the contract revision (P0) is reviewed. A worker meeting unspecified behavior records a gap marker instead of inventing a rule.

## M0 Documents

- [x] **P0** Additive public contract revision: HMP v1 §7e, `media_unavailable` row, optional `media` on tool rows, constants, residual, conformance rows (this change). Root reviewed the additive transcription against the frozen design and the independent Opus pre-code PASS (2026-10-01). No serving or code gate is certified.
- [x] **E1** Native-generated bounded fixture: producer `image` string versus the routed-home lexical prefix on exact Hermes `8afaab3703e336d72a72c812dd2dd249f04f166a`. Root passed three isolated positive native flows and 37 focused string/helper tests (research `f9c542b`). Limited to the real `save_b64_image` producer and stated scratch layout; no live route or manifest admission is granted.

## Minimum-version conversion slices (M0 integration to M3)

Ordered. Workers tick no review boxes; every `[ ]` here is unchecked until root or an independent reviewer marks it.
Native fixtures and owner-local packaging are root-operated. No slice here authorizes a live, device, provider or
dependency action.

- [x] **M0 root integration checkpoint** (inert). Merge `0cdbbf5` of media source `6d400af` onto the converted
  approvals base (`2c153e2` plus probe fixture `f4045cd`). Root receipt status:
  `ROOT_M0_INERT_INTEGRATION_REVIEWED_NOT_FEATURE_COMPLETE`. The runtime media binder is a constant closed
  callback; the retired gate and its empty manifest were not carried. Carried media modules, the `reads.py` twins
  and the bridge twins are byte-identical to the accepted media lineage except the merged twin hunks. **Not green:**
  - converted focused 013/034 set: 1123 passed, 14 skipped, 3 failed; the three failures are
    `test_contract_tables.py` draft-contract-table cases (`media_unavailable` and `MEDIA_*` constants not in
    `contract.py`); the identical three fail on the unconverted media source and remain the S4 gate. They are
    visible, not skipped or hidden.
  - 114 legacy qualification tests fail (109 listener-binding, 4 gate-pinning layout, 1 bridge-inert) and the
    removed gate test has one collection error. They test the retired binder and are **explicit work in progress**
    pending M3. Nothing was skipped, deleted or ignored to change that, and no green full-suite claim is made.
  - The media helper suites (active batch, scan, binding, candidate, file safety, raster, registry, result,
    sidecar, reads media) passed at the checkpoint.
  - Not run: full server suite, `tools/*` suites, native or fixture matrices.
- [x] **M1** Documentation and contract amendments (this change): ROOT_DECISIONS section, spec, plan, tasks,
  checklists, HMP v1 §7e and GU-2d, conformance, specs 013/034 cross-references, `server-modules.md`, FEATURES and
  INSTALL. No code, tests, fixtures or data. Exit: root review. Independent documentation review
  accepted the frozen 13-file delta; root accepted it and added the existing D-M4 publication and D-M6
  no-await mint requirements explicitly to the contract. This certifies documentation only, not media delivery.
- [x] **M2** Eligibility member (D-M2, D-M3, D-M8): `Feature.LOCAL_MEDIA`, the three-row probe table,
  `FEATURE_FLOORS["local_media"]` at the write floor, `issue_draft`/`cli` member, labels and the single reportable
  code. Root accepted after independent bounded source review: 368 focused tests passed, six existing
  native-fixture skips; the new media file passed 61 cases with no xfail. Eight root scratch-copy
  guard mutations failed their targeted assertions; baseline and restored source passed. Thirteen
  compatibility/extraction/privacy-tool tests also passed with the tools collection boundary.
  Configured Ruff 0.16.9, explicit candidate privacy and surface checks passed. This certifies only
  eligibility and offline drafting: the runtime binder remains closed; no route or descriptor exists.
  The known M3/S4 failures below remain; no green full-suite claim.
- [x] **M3 source slice** Replace the retired binder with the D-M4 binding and coherence check: delete the gate-era components
  (manifest, fingerprints, anchor, GIL guard, origin checks, non-media core proof), add
  `ServerContext.media_available` and the bound modules, publish `_bridge_classes` as one tuple. Retire or adapt
  the 114 legacy tests as the architecture allows. Exit for the listener source slice: bounded A7-A12 and A14 evidence, then **mandatory independent
  exact-candidate security review**. Root accepted exact `f737197` after independent review: 3047 unit cases passed, three existing S4 contract-table failures and 16 native-dependent skips remained. This closes the listener source slice only; the route portions of A8/A10/A11 stay with S4/S5.

(The older headings "M1 Host" and "M2 Convergence" below are original document-phase names and are unrelated to slices M1-M3 above.) Later slices stay open exactly as listed under them: C6b exact-native cost and
concurrent-writer evidence (release-candidate evidence, not a per-version allowlist), S4 descriptor emission, S5
route, T12 memory on sampled builds, R2 independent exact-candidate review, and R3 owner-authorized install, flag
and physical-device acceptance. C6b and T12 sample evidence, independent review and device acceptance are pending;
the feature is not enabled by any of them.

### Acceptance matrix for M2/M3

Each case must fail when its named guard is removed. A1-A6 and A13 have bounded source evidence
from M2. M3 supplies bounded listener evidence for A7-A12 and A14; A8 owner/non-owner route responses, A10 mint/fetch identity and A11 route refusal are still S4/S5 requirements. No case proves media serving.

| ID | Setup | Expected | Guard mutated |
|---|---|---|---|
| A1 | version at or above floor, all three rows present | `local_media` probe eligibility available; no media build-list, manifest, fingerprint or SHA input (shared diagnostic evidence does not gate media) | re-introduce a media manifest reader |
| A2 | version unknown, `0.0.0`, newer or development | attempted (available if the probe passes) | floor treats unknown as below |
| A3 | version below floor | unavailable `hermes_version_below_floor`; media rows not imported | probe before floor check |
| A4 | media-table dependency missing, `**kwargs`-only, or resolved from `site-packages` | media-table failure closes only `local_media` (`dependency_missing`, fixed labels); an actually absent shared API also closes each sibling whose own table needs it | merge tables or close siblings |
| A5 | send unavailable or `direct_send.enabled` false | `local_media` unaffected | add `requires_send` |
| A6 | read core missing | `local_media` = `requires_read`; no media import | probe media without read |
| A7 | supported, `identity is None` (converted base) | media can open | require `BuildIdentity` |
| A8 | flag off, non-bool or malformed block | closed: exact old read bytes; owner `503 media_unavailable`; non-owner `404` first | truthy flag |
| A9 | media chain split (synthetic second package copy, foreign `candidate._scan`) | this listener's media closed with a fixed outcome; a second listener in the same process with coherent modules opens (no latch) | process latch or skip coherence |
| A10 | whole-package eviction after open | old listener keeps its bound tuple; mint and fetch use the same objects by identity | handler re-imports |
| A11 | use-time cache identity differs from the bound tuple | `503 media_unavailable`; this listener's media closed until reopen | skip fence |
| A12 | free-threaded interpreter flag simulated | no closure from interpreter mode alone; review confirms registry, permits and caches are lock-protected | GIL guard re-added |
| A13 | `--issue-draft --feature local_media --failure-code media_unavailable` | draft with bounded metadata; `not_found`, `rate_limited`, `forbidden` refused as their own reason; privacy canary (no ref, path, digest, profile or device) | allow 404 drafting |
| A14 | legacy process anchor present as `"closed"` in `sys.__dict__` | new code ignores it and never writes it | read the legacy key |
| Inherited | T1-T18 (T18 amended), C6b A1 identity, D4 uncertainty rule, registry CAS/TTL/LRU, leaf no-follow/nlink, raster, permits and cancellation, `ContextVar` copy, closed log enums | unchanged | as in plan.md |

Sampled evidence (E1 producer spelling, Linux leaf, C6 cost, rotation) stays recorded as tested-sample evidence.
No case requires an exact-build receipt for runtime admission. Release evidence still binds the tested
candidate and sample; that evidence does not prove behavior on future builds.

## M1 Host (after P0 review)

- [x] **S1** Promote the accepted scanner, leaf and raster modules into the plugin surface, logic unchanged except the shared result function; record content hashes. Root accepted the inert slice after independent Opus wrapper/hash review, module-contract repair, and 70 bounded layout/wrapper tests on 2026-10-01. No serving or admission claim.
- [x] **S2** Read-result sidecar and lexical name derivation; golden proof that closed-gate bytes are unchanged (T1). Root accepted S2a–S2d after independent reviews and 833 focused tests (three preexisting Hermes-build skips). Optional media twins remain unused by production handlers; no serving claim.
- [x] **S3** Registry: lock, TTL, LRU, idempotent mint, first-digest CAS (T2, T8). Root accepted the inert slice after independent Opus delta review, causal foreign-snapshot/caller tests, and 152 focused registry/layout tests on 2026-10-01. No fetch authority or serving claim.
- [ ] **S6** *(converted by the minimum-version policy; the manifest, file list, baseline and disk-equality parts are retired. The flag accessor already exists; remaining scope is the eligibility member and in-memory binding, tracked as M2/M3; T18 amended.)* Original text: `local_media.enabled` default-off flag, empty manifest, dedicated media file list, start baseline plus fresh disk equality, off-loop (T18).
- [x] **S6a** *(historical; retired design, not carried onto the converted base)* Inert process qualification gate and empty manifest. Root accepted source after independent Opus original review, Sonnet hardening delta review and 392 focused tests. No listener, flag, entry or admission; S6 remains open.
- [ ] **S6b** *(historical; retired design, superseded by M3)* Bind the S6a gate to the adapter, request context and per-load media caches (static required set, actual-object proofs, strict flag fields). Source and focused tests written under the [S6b freeze](ROOT_DECISIONS.md#s6b-listener-binding-freeze-2026-10-01); bounded source independently reviewed and accepted after repair, with 138 root cases passing. No entry, route consumer or admission; S6 stays open.
- [x] **C6a** Request-scoped active-history batch module and independent security review, following the C6 freeze; accepted single scanner unchanged. Source acceptance only; native cost/memory and C6b remain open.
- [ ] **C6b** Bind that reviewed batch to the same native database/home capture, then root exact-native cost, concurrent-writer and mint-memory evidence. C6 remains open.
- [ ] **S4** Descriptor emission in handlers, 128 cap (T1, T5, T6, T7). Needs S2, S3, S6 and C6 admission.
  Source written on `b07890e`, independently reviewed and accepted for the S4 source slice (2026-10-02; full task not ticked): the four read handlers select the old read or the media twin plus one `bind_media_batch` in one worker job, then mint newest-first (at most 128) on the loop through the listener's one registry; `media_unavailable` and the §13 media constants are in `contract.py`; no fetch route (S5). Native complete-binding cost and T12 are release-candidate evidence, not prerequisites for this source. Independent review accepted the exact source, with stale documentation repaired. Root reproduced 679 focused cases after seven added tests; full delivery, native cost, T12 and device evidence remain separate open gates.
- [ ] **S5** Route, dedicated executor, permits, `ContextVar` copy for both phases, constants, streaming, phase one, phase two, synchronous final section (T3, T9-T11, T13, T15-T17). Needs S1, S3, S6.
  Source slice independently reviewed and accepted after bounded amendments (2026-10-02; full task not ticked): the always-registered route, per-app executor/permits, both native bridge phases and synchronous final section. Clean locked CI: 3613 passed, 16 native-dependent skips, one existing warning. Synthetic four-fetch memory passed the unchanged provisional limits; native T12, native serving, phone binary loading, device and release evidence remain open. See [the S5 acceptance scope](ROOT_DECISIONS.md#s5-bounded-source-acceptance-2026-10-02).
- [ ] **T** Causal suite T1-T18 on a fake bridge and an exact-build disposable-home fixture.
- [ ] **T12** Memory measurement run recorded against the provisional ceilings.
- [x] **PG** Linux errno mapping for the file leaf only. Root reviewed and independently reran the accepted 89 tests plus 91 supplemental real-kernel checks on non-root Linux CPython 3.14.7/tmpfs. See the bounded evidence below; native HMP serving remains unqualified.

## M2 Convergence

- [ ] **R2** Independent security review of the exact candidate.
- [ ] **R3** Owner-authorized install, live flag and physical-device acceptance. No build-list or manifest entry is required. Any live Hermes change needs separate owner authorization.

## S1 reviewed source identity (2026-10-01)

These four modules remain inert; no production caller or route imports them. The three research copies are byte-identical. The wrapper uses the same accepted predicate after bounding the raw result before parsing. The module inventory now includes the optional modules and pins startup import inertness. A synthetic test home was normalized to the scanner-approved `user` placeholder; no runtime logic changed.

| Module | SHA-256 |
|---|---|
| `local_media_active_scan.py` | `81eb6880f396ad3c2a244c875753887332336da4c4a2a68569f3e7c455b8b4c2` |
| `local_media_file_safety.py` | `440c3cfa5c636d5d280f4cf8876f900ab9177b0421d55a8d5503fc398973ef74` |
| `local_media_raster_structure.py` | `f293d0c1e379d20ec5d466e9a92e9c0e6b961a2a2b7009b5aac3705410b47610` |
| `local_media_result.py` | `04d011cf8b805c2b285297e18f99a4ec1691f0133320948d2680d564c29b4336` |

Independent review found only the prior exact-tree contract mismatch; the reviewed wrapper had no defect. Root verified the repaired layout and wrapper (70 tests), configured Ruff 0.16.9, plugin-surface check and privacy scan. Earlier adapted research tests passed (289); no broad native matrix was rerun. S2, S4-S6, Linux, serving qualification and device tests remain open.

## S3 reviewed registry (2026-10-01)

`local_media_registry.py` remains inert and stdlib-only; no route, bridge, sidecar, flag, manifest or production caller uses it. A registry hit never authorizes a fetch. Binding types follow current `contract.py`: session and tip are `str`, tool row id is an exact non-bool `int`, and strings are bounded to 1..256 characters. One future instance server context must share the registry between mint and fetch.

Independent review cleared the foreign-snapshot/caller CAS guard, exact types, lower-only limits, monotonic clock, secure randomness and identity checks. Root ran 152 registry/layout tests, configured Ruff 0.16.9 and explicit candidate privacy scanning. The reviewer killed 27 of 28 mutants; the survivor was an equivalent grammar guard already enforced by exact lookup and entry identity. Tests were on macOS CPython; Linux and free-threaded behavior are not claimed.

| Module | SHA-256 |
|---|---|
| `local_media_registry.py` | `b49e6e6205805f38144e769f742f6e3ee918536aa6dd5f66e6c8096d8f77c2b2` |

S2, S4-S6, native serving qualification and device acceptance remain open.

## E1 bounded producer evidence (2026-10-01)

[Research evidence](https://github.com/MahdiHedhli/hermes-hmp/blob/f9c542b/docs/research/local-media-lexical-evidence-2026-10-01.md) compares the uncapped persisted producer string against the actual native routed-home helper's string, without normalizing the candidate. Desktop, Phone stand-in and deferred-tool flows matched the selected prefix and one flat 128-byte-bounded name; the foreign profile prefix did not match. The native pin, clean source and source fingerprints were checked before/after. Root retained the private native report and reviewed 37 focused lexical/helper tests.

This evidence is not a live HMP route, other-provider path proof, Linux qualification or device acceptance. All other serving gates remain open.

## S2a reviewed carrier (2026-10-01)

Root accepted the immutable non-wire carrier after independent bounded review. A test-only
follow-up closes the reviewer's class-spoof lookalike gap; the functional source is byte-identical
to the accepted candidate, with one prose correction about trusted in-process subclass spoofing.
Root passed 120 carrier/layout cases, configured Ruff 0.16.9 and explicit privacy/diff checks.
Serialization mutants demonstrate that accidental generic return fails closed, and a dataclass
mutant leaks the sentinel only in the causal test. No startup path or runtime reader imports the
carrier. It establishes no authority and holds no image path, name or raw result.

| Module | SHA-256 |
|---|---|
| `local_media_sidecar.py` | `c6abfd7684420a751023f4819bdc6810bd0d6b6ee2a04a8106976f7d4826c206` |

S2 remains open for shared native query plumbing and four read
cores with golden-byte proof. Serving, qualification, Linux, device and release gates remain open.

## S2b reviewed extraction (2026-10-01)

Root accepted bounded candidate extraction after independent Sonnet review and 215 focused
candidate/layout tests on the matrix interpreter. The reviewer ran separate refusal probes and
nine causal mutants; all mutants failed their targeted checks. Configured Ruff 0.16.9 and explicit
privacy/diff checks passed. The module is inert, performs no filesystem access, and emits only a
tool row id and the accepted scanner's canonical digest. A candidate grants no file authority.

| Module | SHA-256 |
|---|---|
| `local_media_candidate.py` | `6bd2cde98064b85b65831048a550787e4cd215ac5f5e74a050a683dcdb840e88` |

Exact shapes, bounded descending row-id order and duplicate behavior are recorded in
`ROOT_DECISIONS.md`. Native query/read plumbing, golden-byte proof, active-set rescan cost,
serving, qualification, Linux and device acceptance remain open; S2 is not complete.

## S2c reviewed bridge (2026-10-01)

Root accepts shared native query plumbing and its media-only downgrade after independent Opus
source review and independent Sonnet delta review. Root passed 473 focused bridge, carrier,
candidate and layout cases (three preexisting Hermes-build skips), configured Ruff 0.16.9 and
explicit privacy/diff checks. Old methods keep their query/release/conversion behavior.
The media twins are inert: no production reader or route selects them yet.

Native session/tip strings are unbounded. A carrier-only metadata refusal, or a native page above
the existing 1000-row carrier bound, returns the same exact old parsed list before extraction.
Native/conversion errors, other metadata exceptions and candidate invariant failures remain errors.
Carrier changes are return annotations and prose only; extraction changes are prose only.

| Module | SHA-256 |
|---|---|
| `bridge.py` | `a72b77634604c0598fa074edc990d3f0cb577091000636580034a632103b5736` |
| `local_media_candidate.py` | `4656d83b6adfa1a05a068f63c68111ad2147c5ce0b76b5414ad8082d4d9789d1` |
| `local_media_sidecar.py` | `e3872f8f013fc51f9e4f682d3ad96024817aa1585075433ede980649857410bf` |

Review residuals: the candidate import test currently allows any scope rather than module scope
only; tighten it in the S2d import-pin update. Syntactic pins do not detect arbitrary dynamic
imports. Narrow named-exception catch-widening mutants survive the test suite, although root
and independent review verify the exact catch in source. Native uncapped materialization and
non-atomic snapshots remain explicit residuals. S2 remains open for read cores and golden bytes.
Serving, cost qualification, Linux, memory, installation and device acceptance remain open.

## S2d reviewed read cores (2026-10-01)

Root accepted this inert read-core slice after fresh independent Sonnet review and root verification. S2 is complete for its stated sidecar/golden scope; serving and admission are separate gates.
`reads.py` now has four private shared cores; the four old methods are thin wrappers with the media
flag off and four optional `*_with_media` twins use the same cores with it on. The twins have no
route, handler or gate caller. The bridge opt-in is read from the class only; a bridge without the
explicit `True` marker keeps the old native calls and returns an empty `UNSUPPORTED_BRIDGE` sidecar.
An opted-in bridge may return its carrier, the exact old row list (unchanged text, empty
`UNSUPPORTED_BRIDGE`, never re-queried) or, for `after`, a `ResetReason`; any other shape is the
existing `500 internal_error`. A separately read lineage tip the carrier cannot hold gives the same
empty null-metadata downgrade, catching only the carrier refusal at that one construction.

Golden bytes, native event logs, baseline rows and observation discard sets were captured once from
a read-only `git archive` of `575a9bc` and are compared as static data. Old methods, the twins'
`.public` and unsupported-bridge twins all match them, as do the four routes over aiohttp. The
layout pins now allow the sidecar only below a function boundary in `reads.py` and `bridge.py`, and
the candidate module's imports at module scope only. Dynamic imports are not detected.

| File | SHA-256 |
|---|---|
| `reads.py` | `ee37573601c354fbbb12928bc6a3404fd6fcc784adb282287bf268f971581bea` |
| `test_reads_media.py` | `a79f077315ff2b63cc553bf50a23d551a822119dab15a0304a0cbf989f19810c` |
| `test_skeleton_layout.py` | `05cd947844971706eff2f05bd50332b50bb5141cae65668440f8754e0f8fb613` |
| `test_local_media_sidecar.py` | `ba426d685cbb64fb1fe4976e90bcfa594fc0f9f35501d2ba75b7eed0acabc901` |

The root-authorized S2c import-pin update now permits these optional read twins while keeping
server, routes, CLI and compatibility callers inert. Root and the independent reviewer each passed
833 focused tests, with three preexisting no-Hermes-build skips. Configured Ruff 0.16.9 and root
explicit privacy/diff checks passed. The reviewer independently regenerated golden data from
`575a9bc1cba5d5ec4c41741c5a5eb723f505f65c`; sorted JSON SHA-256 is
`7b87d0b9a7bfd98e4826b9b0e190360595eba00f9ab7ce0d7f215823102d70ac`.
The narrow constructor catch was reviewed: candidate invariants cannot downgrade silently, and
a failing fallback still surfaces. Syntactic pins do not detect arbitrary dynamic imports.
Native materialization, non-atomic reads, C6 cost, minting, S4-S6, qualification and device
gates remain open. Existing formatting differences in `reads.py` predate this slice.

## PG bounded Linux leaf evidence (2026-10-01)

[Evidence](../../docs/research/local-media-linux-leaf-evidence-2026-10-01.md) records accepted
source/test hashes, real errno and permission controls, race cases, root isolated rerun and limits.
The accepted leaf source is unchanged. This closes only the Linux file-leaf task on the stated
non-root tmpfs platform; it does not qualify native Hermes serving, other filesystems or kernels,
process manifests, memory ceilings, a phone build or release.

## C6a accepted inert batch module (2026-10-01)

`local_media_active_batch.py` is accepted in its inert source scope; production imports nothing
from it. `scan_active_batch(db, tip, selectors,
*, home, current_tip, seam=None)` takes an exact tuple of 1..128 unique `(positive int row id,
32-byte digest)` pairs and runs one bracketed active-set pass: tip, ids, 128-row pages through the
accepted scanner helpers by identity, ids, tip. Role, name, call id and declarations are charged
once into a shared base budget with no selected row; each selected content is bounded to 64 KiB
and surrogate-checked before it is retained, then judged against the base plus only its own charge,
the unchanged `_link`, constant-time digest equality and lexical derivation against the captured
home. A bracket failure refuses every selector; otherwise verdicts are independent. The result
holds row ids, closed reasons (the scanner's plus `digest_mismatch` and `lexical_mismatch`) and
counts only. Native call count does not grow with selector count; cost, concurrent-writer and
mint-memory evidence, C6b binding and S4 emission remain open.

Independent Opus accepted the original bounded source; root then required exact native-dict
capture, constructor re-init refusal and a non-str retention test. Independent Sonnet accepted
that narrow delta. The original focused scanner/candidate/carrier/result/layout batch passed
563 tests; the changed batch/layout slice passed 232 tests at root and review. Configured
Ruff 0.16.9, explicit privacy scan and diff checks pass. No serving, native cost or device
acceptance follows from these checks. Final module SHA-256:
`b30d3bcc37e246a193d00d599855b7abcc114d1a2812d8014cb7062566948ecc`;
test SHA-256: `aee82e9fefb96d2eee63937516f4f0618c1742167a7d01aaa8b425ed5e010a17`.
Public result constructors remain conventional immutable containers rather than tamper-resistant
authority; C6b must call the scanner itself and consume only that fresh result.

## C6b inert binding source accepted (2026-10-01)

The bounded source passed Opus review, its strict-walk repair passed independent Sonnet review,
and root verified the focused tests. **C6b, S4, S5 and S6 stay unchecked**: native binding cost and
serving qualification are still open. `local_media_batch_binding.py` holds the closed `MediaBatchBinding` result, `MintKind`,
the pure two-proof `classify` rule and a lexical `strict_home`. The bridge adds
`bind_media_batch(sidecar)` (an exact `MediaBatchBinding`, or `None` for a non-exact sidecar) and the
shared `media_eligibility(db, user_id, profile, session_id, expected_tip)` helper, with
`_phone_proof` and `_bot_chat_proof`. One `_db_home` capture, one fresh `scan_active_batch` and a
full both-kind reclassification at the initial check and both batch tip checks. Nothing calls them;
no route, flag, manifest entry, registry use or serving. The optional `MediaReadBridge` protocol
annotation was not added, so the accepted sidecar stays byte-identical; S4 must add it with its own
pin change. The strict walk re-read precedes lineage/membership negatives; malformed Phone refs
close the two-proof classification. The result constructor has no magnitude cap on its six counters;
actual batch counters are bounded. Independent delta verification: 411 tests passed (binding plus
layout); three pre-existing draft MEDIA contract-table failures remain outside this focused result.
Exact-native binding cost, concurrent-writer and ABA behavior, Phone evidence, fetch
integration and every other C6/S4/S5/S6 gate remain open.

## S6 design accepted, implementation open (2026-10-01) *(historical; superseded 2026-10-02)*

The [S6 root freeze](ROOT_DECISIONS.md#s6-media-qualification-design-freeze-2026-10-01) adopts the
independent Opus design amendments: persistent process-wide primitive baseline across reloads,
short anchor locking outside imports/I/O, free-threaded closure, this-load module-origin checks,
import-shadowing refusal and bounded fd-relative source reads. No gate module, listener binding,
manifest entry, live flag, media route or approval-gate change is accepted by this design.

## S6a reviewed inert gate (2026-10-01) *(historical evidence of the retired exact-build gate; superseded 2026-10-02, not current policy or runtime behavior)*

Source acceptance only; **S6 stays unchecked**. `local_media_gate.py` is
inert: nothing imports it, there is no flag, route, adapter or bridge binding, and the shipped
`local_media_supported_builds.json` has `builds: []` (preliminary native inventory of 22 files, every
top-level HMP `.py`). With no entry every call returns the constant closed callback and reads only the
media manifest. It implements the frozen S6 design: strict `hmp-local-media-1` parser, bounded
fd-relative no-follow source reads, directory-set equality for importable forms, the `sys` anchor
with its exact primitive layout, optional adapter-owned `preload` with this-load origin checks
(`preload=None` can never admit), and a fresh dependency probe on every check. The media probe table is
`READ_DEPENDENCIES` plus `SessionDB.get_session_by_title` and `SessionDB.get_compression_lineage`.
No qualification entry, native execution, callee-closure trace, cost measurement, Linux, T12 or
device result exists. Independent Opus review cleared the gate/manifest and required one test
repair: explicitly create the cache before testing its FIFO refusal, independent of bytecode
writing. Root also adopted precise origin hardening: refuse leaf-symlink aliases, preserve valid
whole-directory aliases, and bind the loader's own name/path to its spec. The factory now requires
an exact BuildIdentity and documents S6b's separate supported-read precondition. Independent
Sonnet delta review accepted the repaired source; root passed 392 gate/layout cases with `-B`,
configured Ruff 0.16.9, explicit privacy/diff and plugin-surface checks. The manifest remains empty.

S6b must bind only under `CompatResult.supported is True`, prove unsupported/missing-dependency
states leave the cell untouched, and supply the static required-module preload. Preliminary
native callee/producer coverage, bytecode/ABA, same-account tampering, public test seams,
BaseException propagation, blocking lock/kernel/Git latency and per-check cost remain residuals.
No approval gate, live plugin, source qualification entry or device build changed.

| File | SHA-256 |
| --- | --- |
| `local_media_gate.py` | `fb8ae21e8a67dfe382de2e283d5672044828b4c316bc33bce4e12fb1302439c4` |
| `local_media_supported_builds.json` | `4efc1f0a44fcd844d77a64320bd6fd92781604368cc018d6adbe8cdbb5db4f46` |
| `test_local_media_gate.py` | `4f3f02ae7a28f6a13ced3b5d0ff7ce85d0795fb0fdf864471b815f4a9841c416` |
| `test_skeleton_layout.py` | `52f19ad67250c3efda1d780b300afb5cd7dcc4fb2e77d8f2c01566fe1fde59ed` |

## S6b listener binding source written (2026-10-01, review pending) *(historical; the qualifier it binds is retired)*

Source and focused tests only; **S6, S6b, S4 and S5 stay unchecked** and no reviewer checklist item is
marked. Root review and an independent Opus security review of the exact implementation are still
required. Implements the [S6b freeze](ROOT_DECISIONS.md#s6b-listener-binding-freeze-2026-10-01): on a
SUPPORTED build only, `adapter.open_components` calls `local_media_gate.media_listener_qualifier` with
the exact identity and a static preload. The preload proves 21 required modules against the objects
this listener runs (plain-function and class-body-method globals, static module references, the
adapter's own namespace) and sweeps them for split copies by identity; any failure raises and the gate
closes. `ServerContext` gains callable `media_flag` and `media_qualified` fields (default closed) with
exact-True accessors; no route, manifest entry, consumer, dependency inventory or approval-gate change.
`bridge.py` and `reads.py` gain per-load set-once media module caches that their media sites read in
place of function-local imports; the old read methods are byte-identical. A first twin call on a
closed listener may fill a cache (the reviewed design), so the caches do not fill only inside the
preload. The gate edit is its module docstring only (AST-identical to `fb8ae21e` apart from the module
docstring; only the AST was compared, no loaded or compiled bytecode claim); its pin is renewed below.
An unlocked `adapter._bridge_classes()` can publish its two caches from different package copies if
first calls race a whole-package eviction; the preload then refuses and the first factory latches
closed. That is a fail-closed availability residual (restart to recover), not an authority gap. The native-inventory closure remains a separate later slice before any entry.
The full evidence, residuals and the unverified gates are in the S6b author report, not here.

| File | SHA-256 (S6b) |
| --- | --- |
| `local_media_gate.py` (docstring only) | `4cb4646a0722c7a28d4f4fc1c8afcf3ac492e709799af778deb067300b7d9e25` |
| `test_skeleton_layout.py` | `619497a5a68af36fca7bbcce3dfd6cde802ef71a49745dcc47bf67bc79602325` |
| `test_local_media_listener_binding.py` | `27fc47b49e2bae422e61b8e6a0b1f73dbac6688f2a76d0afa48f6e299ef755b4` |


## S6b repaired source acceptance (2026-10-01) *(historical; accepts the retired binder only)*

The source slice is accepted after independent review of the original implementation
and its comment/test repair. Root reverified the frozen 15-file candidate and the
138-case focused result. The independent delta review confirmed 138 cases and 13
causal mutant kills. Reviewer checkboxes and S6/S6b stay open for their full scope.
Three earlier baseline contract-table failures remain recorded; no full-suite green
is claimed. No build entry, native admission or serving route is present. See the
[root acceptance scope](ROOT_DECISIONS.md#s6b-bounded-source-acceptance--2026-10-01).


## C6b sampled complete-binding evidence (2026-10-02)

The [r2 native sample](../../docs/research/local-media-complete-binding-sample-2026-10-02.md)
completed 58 steps with 9,686 semantic checks and 500 writer phases. Root rechecked all 1,000
first/second outcomes, including closed refusal reasons. Public native prompts prove the declared
large-prompt fixture. This is M3 binding/mint research on the stated native sample, not S4 route
cost or S5/T12 evidence. Native materialization and non-atomic residual/ABA remain; no gate,
ceiling or release checkbox is implied. Earlier r1 measurement defects remain historical.

## S5 source checkpoint (2026-10-02)

The source slice is independently accepted after the three bounded amendments,
with root clean locked CI (3613 passed, 16 native-dependent skips, one existing
warning), 162 focused fetch cases and nine causal scratch-copy mutant kills.
The independent reviewer reproduced 162 fetch/amendment and 308 startup/layout
cases; all frozen candidate hashes stayed unchanged. See the
[S5 acceptance scope](ROOT_DECISIONS.md#s5-bounded-source-acceptance-2026-10-02).

S5's full serving task and T12 stay unchecked. The synthetic four-by-8-MiB
route measurement covers its stated macOS allocation/lifecycle scenario only;
native sample serving/cost/T12, Linux serving and phone/device/release evidence
remain open. No live install or flag was changed.
