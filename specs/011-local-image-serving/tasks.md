# Tasks

`[ ]` means not started or not independently reviewed. Workers do not self-certify. No implementation task starts before the contract revision (P0) is reviewed. A worker meeting unspecified behavior records a gap marker instead of inventing a rule.

## M0 Documents

- [x] **P0** Additive public contract revision: HMP v1 §7e, `media_unavailable` row, optional `media` on tool rows, constants, residual, conformance rows (this change). Root reviewed the additive transcription against the frozen design and the independent Opus pre-code PASS (2026-10-01). No serving or code gate is certified.
- [x] **E1** Native-generated bounded fixture: producer `image` string versus the routed-home lexical prefix on exact Hermes `8afaab3703e336d72a72c812dd2dd249f04f166a`. Root passed three isolated positive native flows and 37 focused string/helper tests (research `f9c542b`). Limited to the real `save_b64_image` producer and stated scratch layout; no live route or manifest admission is granted.

## M1 Host (after P0 review)

- [x] **S1** Promote the accepted scanner, leaf and raster modules into the plugin surface, logic unchanged except the shared result function; record content hashes. Root accepted the inert slice after independent Opus wrapper/hash review, module-contract repair, and 70 bounded layout/wrapper tests on 2026-10-01. No serving or admission claim.
- [x] **S2** Read-result sidecar and lexical name derivation; golden proof that closed-gate bytes are unchanged (T1). Root accepted S2a–S2d after independent reviews and 833 focused tests (three preexisting Hermes-build skips). Optional media twins remain unused by production handlers; no serving claim.
- [x] **S3** Registry: lock, TTL, LRU, idempotent mint, first-digest CAS (T2, T8). Root accepted the inert slice after independent Opus delta review, causal foreign-snapshot/caller tests, and 152 focused registry/layout tests on 2026-10-01. No fetch authority or serving claim.
- [ ] **S6** `local_media.enabled` default-off flag, empty manifest, dedicated media file list, start baseline plus fresh disk equality, off-loop (T18).
- [x] **S6a** Inert process qualification gate and empty manifest. Root accepted source after independent Opus original review, Sonnet hardening delta review and 392 focused tests. No listener, flag, entry or admission; S6 remains open.
- [x] **C6a** Request-scoped active-history batch module and independent security review, following the C6 freeze; accepted single scanner unchanged. Source acceptance only; native cost/memory and C6b remain open.
- [ ] **C6b** Bind that reviewed batch to the same native database/home capture, then root exact-native cost, concurrent-writer and mint-memory evidence. C6 remains open.
- [ ] **S4** Descriptor emission in handlers, 128 cap (T1, T5, T6, T7). Needs S2, S3, S6 and C6 admission.
- [ ] **S5** Route, dedicated executor, permits, `ContextVar` copy for both phases, constants, streaming, phase one, phase two, synchronous final section (T3, T9-T11, T13, T15-T17). Needs S1, S3, S6.
- [ ] **T** Causal suite T1-T18 on a fake bridge and an exact-build disposable-home fixture.
- [ ] **T12** Memory measurement run recorded against the provisional ceilings.
- [x] **PG** Linux errno mapping for the file leaf only. Root reviewed and independently reran the accepted 89 tests plus 91 supplemental real-kernel checks on non-root Linux CPython 3.14.7/tmpfs. See the bounded evidence below; native HMP serving remains unqualified.

## M2 Convergence

- [ ] **R2** Independent security review of the exact candidate.
- [ ] **R3** Owner-authorized manifest entry for a qualified build and device acceptance. Any live Hermes change needs separate owner authorization.

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

## S6 design accepted, implementation open (2026-10-01)

The [S6 root freeze](ROOT_DECISIONS.md#s6-media-qualification-design-freeze-2026-10-01) adopts the
independent Opus design amendments: persistent process-wide primitive baseline across reloads,
short anchor locking outside imports/I/O, free-threaded closure, this-load module-origin checks,
import-shadowing refusal and bounded fd-relative source reads. No gate module, listener binding,
manifest entry, live flag, media route or approval-gate change is accepted by this design.

## S6a reviewed inert gate (2026-10-01)

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
