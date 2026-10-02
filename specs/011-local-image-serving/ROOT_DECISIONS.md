# Root decisions

Public record of the architecture decisions this feature was frozen on. Where another document here differs, this file wins. It records design decisions; the task evidence separately identifies reviewed components. No serving process, device or release is qualified.

> **Superseding section (2026-10-02).** The exact-build gate described below (process-qualified
> manifest, fingerprints, process anchor, preload qualification) is superseded by
> [Minimum-version conversion](#minimum-version-conversion-supersedes-s6-manifestfingerprintanchor-s6a-admission-semantics-s6b-preload-qualification-2026-10-02),
> the last section of this file. The earlier S6, S6a and S6b text is preserved as **historical
> evidence about the retired design**. It is not current policy, and nothing there describes
> runtime behavior of the converted base.

## Accepted

| ID | Decision |
| --- | --- |
| C1 | Derive the flat cache name lexically from the raw `image` string; no `resolve()`, no legacy directories. A spelling mismatch refuses (`EVIDENCE_GAP` until E1 passes). |
| C2 | Authority is only a strict same-profile `image_generate` tool row. Assistant `MEDIA:` text and Markdown have none. |
| C3 | New ERR-2 code `media_unavailable`, `503`, "image delivery is unavailable". A non-owner device gets `404` first. |
| C4 | Overload is the existing `429 rate_limited`, no `why`. |
| C5 | The handle binds a session kind (`bot_chat` or `phone`), rechecked at fetch. |
| C8 | Mint is idempotent and never extends TTL; at most 128 newest descriptors per response. |
| C9 | The handle carries no path. Existing capped tool text may already contain it; rows are not claimed pathless. |
| Gate | Default-off owner-device gate (`is_approval_owner_device`; unrelated owner privilege never implies it), separate `local_media.enabled`, process-qualified manifest, shipped empty. |
| Bytes | Max 8 MiB; PNG, JPEG, WebP; host structural check plus phone decode with bounds. |
| Order | Bot Chat first, then Phone chat under the same contract. |

## Authoritative corrections

1. **Authorization ordering.** After the first worker returns, a second off-loop phase runs fresh native per-bot authorization, same-kind eligibility and tip. Then the loop synchronously runs bearer, owner, gate, TTL and digest CAS with no `await` before `prepare`. No native check runs on the loop. A causal change before the phase-two check refuses with `404`, zero bytes. A change after the last native check is an unavoidable residual (no atomic native API) and is not promised to refuse. There is no atomic snapshot claim.
2. **No wire leak.** The raw candidate travels in a non-wire sidecar. Gate closed yields the exact old bytes.
3. **Process qualification.** Loaded/start baseline plus fresh disk equality over a dedicated media file list and the exact dependencies, following the approval baseline discipline. No supported entry exists until an actual qualification. Approval gates are never waived.
4. **Phone card.** The host image card keeps the existing card's tap-to-load trigger, phases, Cancel and 2-operation screen limit, with no queue; no new tap, auto-load or queue; no public fallback.
5. **Memory.** Four active plus four late workers cannot run at once because buffer permits stay held for the real worker life. Provisional ceilings: 96 MiB traced peak, 128 MiB incremental RSS; no native-allocation bound is claimed; a failure changes the implementation, not the ceiling.
6. **Deadlines.** 20 s worker wait shared by both phases; 30 s total write deadline including EOF. Worker and buffer permits live until real future completion plus the handler `finally`. Copied `ContextVar`s keep profile scope on the dedicated executor.
7. **Client.** A separate pinned binary load path with the existing single `401` refresh, exact MIME and magic, static raster at most 8 MiB.
8. **Error mappings** come from current source (see the §7e table); the initial per-bot grant keeps ERR-3 exactly, later refusals are generic `404`.

## Clarifications accepted at freeze

- Instance admission is the buffer permit; the device permit has the same lifetime.
- A phase-two permit shortage is reachable only by fault injection; it is retained and tested by injecting a shortage.
- Qualification disk and dependency work and the initial native grant work use the shared default executor, leaving the four dedicated workers for the media phases.
- An immutable startup mismatch needs a restart; a later disk mismatch closes the gate while present, and restoring the startup baseline can reopen it.
- All constants are new choices for this feature; memory ceilings stay provisional; E1 and Linux qualification remain later admission gates.
- The existing phone transport timeout is 15 s; a slow fetch may show unavailable before the host deadlines. No transport change is authorized.

## Review status

An independent pre-code review of the frozen design passed. That review covers the design only: product, native serving, device and release gates remain open, and no reviewer, qualification, security or release checklist is certified by the authors of these documents.

## Residuals carried

No atomic snapshot (including ABA on unrelated rows); change after the last native check before `prepare`; coarse-timestamp torn buffer (the phone codec decides); out-of-tree providers unfingerprinted; no containment of same-account host code; bounded Linux file-leaf errno evidence accepted for its stated platform only; native serving and broader Linux coverage open; deadlines and memory ceilings provisional.

2026-10-01 root P0 disposition: additive transcription conforms to the frozen design and its
independent Opus pre-code PASS. Revision 1.6 draft and LM clause names are accepted. All
implementation, native qualification, platform, device and release gates remain open.

## S2 sidecar architecture freeze (2026-10-01)

Root accepts the independent bounded architecture proposal in four sequential slices: immutable
carrier, candidate derivation, shared bridge query, and four read cores with golden-byte checks.
Old read methods remain the gate-closed path. No S2 production handler or route is enabled.

- Carriers are plain immutable slots classes, never dataclasses, mappings or sequences. Fixed
  representations and blocked pickle/copy prevent private values reaching diagnostic or generic
  serialization. The wire serializer must fail closed if a carrier is accidentally returned.
- Candidates carry only a positive tool row id and the accepted scanner's canonical tool digest
  (row id, tool role/name, call id and uncapped content), never the image path or flat name.
- Bound parsing to the newest 128 `image_generate` attempts in one returned page, with no older-row
  backfill after rejection. The per-result 64 KiB byte bound precedes parsing.
- Lexical derivation uses exactly the home captured by the bridge's existing `_profile_home`
  call, without a second call or further normalization. On the qualified producer fixture the
  native helper returns a Path and its string equals the bridge's Path string. Other spellings
  may refuse. Reuse the accepted flat-name grammar; no filesystem lookup during derivation.
- Capture the exact native message-query tip. If it differs from the separately read lineage tip,
  emit no descriptors; preserve the old public result byte-for-byte. A history head is not a
  separate media authority binding.
- A class-level explicit bridge opt-in selects the media query extension. Unsupported bridges
  keep the old method and return an empty unsupported sidecar; do not probe dynamic attributes.
- S4 must freshly establish canonical Bot Chat title AND hidden status, chain and live tip, or
  the caller's own Phone session. A browsed own Phone session may qualify; foreign or arbitrary
  sessions never do. S2's read-origin label establishes none of this authority.
- S4 checks qualification and owner gating before selecting the media read and checks again
  afterwards. Closed gates use the old native call pattern and exact old response bytes.
- List/multimodal tool content is not a candidate. Native uncapped materialization and the lack
  of an atomic native snapshot remain residuals.

The cost of repeated active-set rescans for descriptor minting remains an explicit S4 decision
and measurement gate. This freeze neither changes accepted scanner logic nor accepts that cost
without measurement. S2 completion requires independent review and causal serialization/golden
tests. S4/S5/S6, Linux, qualification, live installation and device gates remain open.

S2a carrier detail dispositions: no-conversation/reset/unsupported results may have null session
or tips only with an empty non-candidate sidecar. Candidate status requires all three strings;
unequal tips remain representable and cannot authorize minting. Candidate uniqueness is checked
in the carrier; ordering and returned-tool-row filtering belong to the later extraction/read
slices. Public result types are exactly the existing SnapshotResponse, SessionSnapshot,
HistoryPage and HistoryReset. Row count uses the existing history maximum of 1000. The carrier
duplicates the fixed 256-character field bound to avoid importing the registry, and the optional
protocol adds no opt-in marker until the bridge implementation. These are internal type/shape
choices, not wire changes or authority.

S2b extraction detail dispositions: input is an exact list/tuple of at most 1000 native rows and
an exact frozenset of at most 1000 positive, non-bool returned tool ids. Sort the bounded page by
positive row id descending, never by timestamp. Duplicate ids are considered once, with the
first input occurrence winning; native pages have unique ids. Count the newest 128 strict
returned `image_generate` attempts before parsing, including rejected content; no older backfill.
Mapping access runs in trusted host code and exceptions close the candidate result. This is not
isolation or authority: S4 must independently rescan and compare the canonical tool digest.

S2c.1 media-only downgrade disposition: independent Opus review confirms native session/tip
strings have no 256-character bound, although the carrier and registry do. Preserve the successful
old text read when media metadata cannot be represented. After `_rows` succeeds, catch only
`MediaCarrierRefusal` from `MediaRowsQuery` and return the same exact parsed list; also return that
list for a page over the carrier's existing 1000-row bound. Both checks precede extraction. Do not
catch native/conversion errors, other metadata exceptions or candidate invariant errors. Construct
`BridgeMediaRows` outside the catch. The optional media protocol explicitly permits this list
fallback; production `ReadBridge` and wire types remain unchanged. Only its return annotations and
stale inertness prose may change in the accepted carrier; its functional guards remain frozen.

S2d must recognize the exact list as unchanged text plus an empty `UNSUPPORTED_BRIDGE` sidecar
with all session/tip fields null. If a separately read lineage tip cannot fit the sidecar, apply
the same empty null-metadata downgrade. Never retry the native query, truncate rows or tip strings,
or let this optional metadata failure turn a working text read into a 500. Golden-byte tests must
cover these cases. No downgrade grants media authority or opens a serving gate.

## C6 descriptor-mint batch freeze (2026-10-01)

Root accepts the independent Opus conditional design, not its implementation or cost admission.
The exact-native private fixture measured 128 sequential scans at median 4.58 seconds for small
4096-row histories and 9.11 seconds near the scanner's 4 MiB processing budget. These are warm,
isolated measurements, not upper bounds: native reads materialize uncharged content as well.
Repeated scanning per candidate is not admitted. The 128-descriptor cap, TTL and idempotence stay
unchanged. A new inert batch module requires independent security review before S4 uses it.

- **C6.1 One response, one batch.** A CANDIDATES sidecar permits at most one fresh request-scoped
  active-history batch scan. The accepted single scanner remains byte-identical to S1; fetch uses
  that single scan and recheck unchanged. A new module reuses its helpers by identity: `_inspect_row`,
  `_link`, `_read_active_ids`, `_check_tip`, `_Budget`, `utf8_weight` and constants. The new page
  loop mirrors the accepted scanner; a base `_State` with selected id zero charges no candidate
  content, since accepted active row ids are positive. No exception serves as a success signal.
- **C6.2 Inputs and eligibility.** One profile/session/tip and the home captured by the same
  `_profile_home` call as database acquisition; an exact tuple of 1..128 unique positive non-bool
  row-id / exact 32-byte digest pairs copied unchanged from the returned sidecar. Query tip,
  lineage tip and fresh S4 eligible tip must agree. Canonical Bot Chat title AND lineage-root hidden
  status (as clarified by the C6b freeze below), chain/live tip, or the caller's own Phone session
  remain mandatory. Hints, assistant text,
  Markdown and MEDIA never confer authority. The batch never adds, replaces or backfills selectors.
- **C6.3 Shared bracket.** Before/after eligibility tip checks, before/after equal active ids,
  at most 4096 strictly increasing positive ids, 128-row paging with unchanged count/order checks.
  Native call count and shared 4 MiB base budget are independent of candidate count. Bracket failure
  refuses every candidate; paging may be skipped only if none is active. No replay facade or
  cross-request cache, and no registry hit substitutes for this scan.
- **C6.4 Independent verdicts.** Each selected row independently passes active/tool membership,
  the 64 KiB content bound and surrogate check, base budget plus only its own content charge,
  unchanged strict `_link`, constant-time canonical tool-digest equality and lexical flat-name
  derivation against the captured home. A candidate refusal cannot affect another's acceptance.
  For identical native reads, acceptance equals the accepted single scanner plus digest/derivation
  equality for every selector. Internal reason precedence need not equal the single scanner.
- **C6.5 Closed result.** Only accepted row ids, closed reasons and counts leave the batch.
  No image/path/name/digest/call id/content/ScanClaim, logging, durable bytes or session cache.
  It runs off-loop inside the emitting read's own work, with that profile ContextVar, on the
  shared default executor. It does not consume dedicated fetch workers or permits.
- **C6.6 Mint boundary.** After the batch, recheck owner, flag and qualification gates on the
  loop and mint newest-first with no await between that check and mint. A media refusal, gate
  change or exception at this optional S4 boundary adds no descriptors for affected candidates
  and preserves exact successful text bytes; no optional failure becomes a text-read 500.
- **C6.7 Fetch unchanged.** Every fetch still performs accepted single scan/recheck, both
  off-loop phases, owner/grant/qualification checks, final synchronous section and digest CAS.
  Minting a reference authorizes no file read. No file access or stat occurs at mint.
- **C6.8 Admission open.** Require independent security review, causal differential tests for
  all accepted scanner refusals and selection independence, budget/call-count/bracket/digest/
  lexical/leakage/inertness tests, and root-run exact-native single-batch measurement covering the
  three recorded shapes plus large uncharged content and concurrent writing. No threshold is
  invented by this freeze; mint-path memory and native allocation remain unqualified.

LM-5's draft heading is clarified to allow this active-history linkage scan while forbidding
file access/stat at mint. This is an internal authority/cost clarification, not a wire change.
S2d may finish independently. C6a batch source follows S2d to avoid shared layout-test edits;
C6b bridge binding and S4 emission follow its independent review. Existing non-atomic/ABA,
trusted native materialization, Linux, T12, process qualification and device gates remain open.

## C6b binding design freeze (2026-10-01)

These resolve the independent Opus D1-D5 choices. They are not implementation or admission.
Root verified the actual native public rotation/title helpers; the bounded
[rotation evidence](../../docs/research/local-media-canonical-rotation-evidence-2026-10-01.md)
passed 15 cases and 51 checks. Root adopts the bounded independent design check's A1-A5
amendments below. Source acceptance and complete binding cost remain separate gates.

- **D1 Root-hidden canonical lineage.** On exact 8afa, publication creates a visible child and
  title transfer leaves the hidden root untitled. Require the title lookup to return an exact
  dict with exact canonical title and exact nonempty string id T. Resolve T to the query tip.
  Require a nonempty exact list from `get_compression_lineage(T)`, unique nonempty string ids,
  at most 100 ids, equal
  to the bounded root-first parent walk from that tip. T and the bound sidecar session must be
  in that chain, and the bound session must independently resolve to that same tip. Read every
  chain row as an exact dict with its exact matching id. The root's re-read parent must be exactly
  `None`, and its hidden value must be exact integer `1`. Root, T and live tip must have exact
  integer `archived == 0`. Every chain row other than T must have a null or exact empty-string
  title. T's re-read row must still have an exact string equal to the canonical title. The holder may
  be visible. Interrupted transfers (title on root or middle ancestor) are valid under the same
  proof. A missing, malformed, divergent, ambiguous or unprovable state refuses.
  Retained residual: any native title writer can retitle a hidden ordinary compressed
  lineage and create indistinguishable metadata. No assistant text, hint or media path supplies
  this proof; native session metadata is trusted, including model-generated or operator-set
  titles and automatic titling if it can produce this state while the canonical title is free.
  Separate bearer/profile gates and
  fetch validation remain mandatory.
- **D2 Native equality, no mirrored fork predicate.** Reuse the existing `_parent_chain` helper
  unchanged, then enforce exact row checks and native-lineage equality in the new media helper.
  Do not use `resolve_bot_chat`'s union, its fallback tip, or copied SQL. Ordinary child, fork,
  reset or divergent resume-walker paths must refuse. Re-run the complete classification,
  including exclusion of the other kind, in both batch tip brackets on the same captured
  database, without a verdict cache. A kind change or loss of uniqueness refuses every selector.
- **D3 One home/database capture, lexical mint check.** One `_db_home(profile)` supplies both.
  The home must be an exact nonempty absolute normalized string, no NUL or `..` component.
  No image/home stat or file open at mint; the existing database-file check is retained.
  Non-symlink file-root/leaf proof belongs to fetch. E1 is spelling evidence, not authority.
- **D4 Exact own Phone bound session.** A fresh existing `conversation_ref(user, profile)` must
  match the sidecar's bound profile/session, then native resolution must equal its query tip.
  A compressed bound ancestor qualifies; a browsed projected tip that differs from the own
  bound id does not. Foreign Phone sessions refuse. Evaluate both kinds with three outcomes:
  proven, closed negative, or uncertain. Any native exception, wrong type, missing required row
  field or unprovable parent walk in either proof closes the whole binding as
  `ELIGIBILITY_UNCERTAIN`, even when the other proof succeeds. Known negative facts (no title
  row, no own conversation, different bound session, non-hidden root, archived lineage, native
  lineage/parent-chain inequality or another nonempty chain title) mean "not this kind".
  Exactly one kind must prove; both or neither give `NOT_ELIGIBLE`. Do not consult `MediaOrigin`.
- **D5 Authorization placement.** C6b runs inside the already authorized read; it performs no
  new native auth call, request-access trigger or grant. S4 separately checks current owner,
  flag and fresh qualification before mint. References alone authorize no file access;
  both fetch phases recheck native per-bot authorization. A grant change after a read can thus
  leave a useless opaque reference, but cannot authorize its fetch.
- **D6 Invalid internal input.** `bind_media_batch` returns `None` for a non-exact sidecar,
  because an exact identity-bound result cannot hold that input. Its optional protocol return
  is `MediaBatchBinding | None`; S4 requires the exact result and `binding.sidecar is result.sidecar`.
  Never fabricate a sidecar, widen its frozen constructor or let invalid optional input become
  a successful text-read error. A valid sidecar with a refusal receives a closed result.
  Binding session/tip views are `str | None`, matching closed sidecars. Only an OK result may
  hold a kind or accepted ids; an OK batch with no accepted candidates mints zero descriptors.
  S4 checks exact wrapper, sidecar identity and OK before consuming these views.
- **A1 Fetch uses the same proof.** Phase two calls the same C6b eligibility helper by identity
  for the handle's user/profile/bound session/expected tip, on that phase's one captured database.
  Re-evaluate both kinds with D4's uncertainty rule and require the original kind to remain the
  unique proven kind and its tip to equal the handle tip. Never use a weaker send resolver,
  `resolve_bot_chat` or `MediaOrigin`. The helper accepts primitive bound inputs so fetch need
  not reconstruct a sidecar. Phase-one/two native authorization remains separate.

Source tests must causally cover the private evidence's unexercised predicate paths: mismatched
bound-session resolution, an empty-string rather than null root parent, other chain titles,
malformed shapes and native exceptions. Also cover classification becoming ambiguous or uncertain
in either batch bracket, and the same identity-bound helper at future fetch integration.

The new inert module reuses accepted batch primitives and selectors by identity; no accepted
batch, sidecar guards, old read or send methods change. Bind at most once per response; mint only
fresh accepted ids newest-first. Native metadata reads may materialize unbounded prompts and
flush token counts. Exact-native complete binding cost, concurrent-writer controls, non-atomic/ABA,
T12, S4-S6, callee closure, manifest and device acceptance remain open. Component batch timing
does not establish this binding's cost or authority.

## S6 media qualification design freeze (2026-10-01)

Root adopts the independent Opus architecture review and its five required amendments as design.
This accepts no implementation, manifest entry, listener binding, serving route, live flag,
approval-gate change or device result. S6a follows accepted C6a; S6b binds listeners in a separately
reviewed slice. The approval qualification matrix cannot qualify media, or vice versa.

### Manifest, source coverage and dependency probes

- Use a separate strict `hmp-local-media-1` manifest with exact keys, types and path grammar.
  Require the exact native Git SHA where present, native fingerprint and HMP fingerprint;
  `source_sha` is provenance only. Do not reuse the read-list parser for additional fields.
  Keep builds empty until separate native/HMP execution evidence and root admission.
- HMP coverage is every top-level plugin Python source, including authorization, transport,
  context and media dependencies. Require sorted exact directory-set equality. Enumerate at most
  512 top-level entries; extra importable source, extension or sourceless-bytecode forms identified
  by `importlib.machinery.all_suffixes()` close the gate. Refuse extra directories other than
  `__pycache__`, and non-regular entries inside that cache. Manifests and `plugin.yaml` are permitted
  metadata, not recursive hash inputs; validate the current manifest semantically on every check.
  Bytecode content and loader metadata remain explicit residuals.
- The preliminary native inventory is the 16 read files, `gateway/session_context.py`,
  `hermes_state_titles.py`, `hermes_state_common.py`, `tools/image_generation_tool.py`,
  `tools/image_generation_managed.py` and `tools/image_source.py`. Those files exist on `8afaab37`;
  they do not establish callee closure. Before any entry, verify actual reaching symbols, owning
  modules and native execution traces. Add the actual producer callees rather than infer coverage.
- A separate media dependency specification includes READ_DEPENDENCIES and the actual title,
  lineage, home and profile APIs used by media. Probe their real owning files and signatures.
  Containment/signature checks do not prove behavior or qualify providers, site-packages,
  C extensions, the interpreter or monkeypatching.

### Process identity across reloads and homes

The first supported factory process-wide fixes the baseline across module reloads and Hermes
homes. A different native root or plugin directory closes subsequent listeners. Only a full OS
process restart clears that baseline. Unknown read compatibility does not initialize it; capture
is independent of the live media flag. A startup closed state cannot reopen. A matching listener
can close on later disk mismatch and reopen after a fresh restoration check; a listener captured
with a mismatch stays closed for its lifetime.

- Use the stable, unversioned private key `_hermes_hmp_local_media_process_state` in
  `sys.__dict__`, created only by atomic `setdefault`. No reset, delete, setter or environment bypass.
  Anchor shape is exactly `(1, lock, cell)`: exact tuple length 3, exact integer schema 1,
  exact `_thread.LockType`, exact list length 1. No plugin-defined object, callable, module,
  Path, label, secret, receipt or media claim is stored there.
- `cell[0]` is `None`, exact string `"closed"`, or an exact baseline tuple:
  `("b1", native_root, plugin_dir, read_files, read_fp, native_files, native_fp, git_sha,
  hmp_files, hmp_fp)`. Resolved roots are exact strings; file lists are exact sorted tuples of
  exact strings; fingerprints and optional SHA use strict hex grammar. Validate the complete
  layout on every read. A future layout change requires a schema change and therefore closure
  against an existing incompatible anchor, never replacement.
- The sole transitions, under the anchor lock, are `None` to `"closed"` or `None` to baseline.
  Foreign, malformed or incompatible anchors/cells return a constant closed callback unchanged.
  A plugin-local dataclass may be a decoded view only, never the persistent value.
- Module top level does only `setdefault` and never acquires the lock. Under lock, inspect the
  cell and release; perform manifest work, disk fingerprints, imports and probes unlocked; then
  reacquire to make the one first transition and compare the candidate with the fixed cell.
  Never hold this lock over import/preload or disk work: abandoned Hermes loader threads and
  concurrent old/new package copies can otherwise deadlock. Racing factories compare against
  whichever candidate won the first transition.
- If `sys._is_gil_enabled` exists and returns False, close before touching the anchor.
  Free-threaded and sub-interpreter runtimes remain unqualified; each sub-interpreter has its
  own sys module. Same-account host code can tamper with the anchor and is outside containment.

### Preload and loaded origins

After an exact nonempty manifest match: fingerprint disk before, call an adapter-owned static
preload helper, fingerprint disk after, check loaded origins, then construct the candidate.
Empty manifests perform no native/HMP source reads or preload. The inert gate imports neither
adapter, bridge, server nor native Hermes. Its optional preload callable returns an exact tuple
of module objects; wrong type or exception closes. It supplies no baseline and cannot reset one.

Check the objects actually bound by this load, never hard-coded `sys.modules` names: Hermes may
load a home-suffixed package while old listeners retain the old objects after reload. Derive any
package name from the gate's own `__package__`. Each returned module must have equal spec origin
and file, a resolved file exactly `plugin_dir / (stem + ".py")`, listed source, and an exact
`importlib.machinery.SourceFileLoader`. Store no module objects in the anchor. These checks narrow
origins; they do not attest loaded bytecode against disk or close lazy-import/ABA gaps.

### Bounded reads and final request check

- Manifest maximum is 256 KiB, with at most 256 native paths, 256 HMP paths and 128 entries;
  labels are at most 256 characters and paths at most 1024 UTF-8 bytes, unique and sorted.
- Resolve a root once. Open each intermediate component relative to a directory fd with
  `O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC`, and the leaf with
  `O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC`. Check regular-file type before reading, including
  immediate FIFO refusal. No absolute paths, traversal or symlink components.
- Source cap is 8 MiB per file and 64 MiB combined native/HMP bytes per check, charged before
  reading. Read no more than declared size plus one byte, and require exact length and identical
  `(st_dev, st_ino, st_size, st_mtime_ns, st_ctime_ns)` before/after. Close every fd in finally.
  Short read, growth, metadata change or cap failure closes. Pure digest over sorted
  `path\0len\0bytes` pairs is byte-compatible with the existing read fingerprint algorithm.
  Tooling and runtime share this pure function.
- After the batch or fetch phase two completes, await a fresh qualification check on the default
  executor, then immediately consume that request-local bool with synchronous owner, exact-bool
  flag, TTL/CAS and mint/prepare checks. No await, async lock, awaited log or metrics operation
  intervenes; the bool is never cached on a module or ServerContext. This clarifies C6.6's
  qualification check: source hashing is off-loop, its result is consumed on-loop.
- No asynchronous deadline is added in S6a. Canceling an awaiter does not stop a worker thread.
  Any later timeout must prove worker lifetime/resource accounting first. Kernel/FUSE/NFS read
  latency, default-executor capacity and inherited Git-metadata reads remain unbounded by time.
  The final off-loop check to mint/prepare is non-atomic. Local manifests/receipts are unauthenticated.

### Required causal checks and later admission

S6a must cover real module eviction/re-import, aliases and differing directories, plugin-class
identity regression, foreign/schema/lock/cell corruption without replacement, eight racing
factories, and a blocked preload proving no anchor-lock deadlock. Cover import shadowing forms,
module-origin decoys, disk change during preload, symlink components, FIFO/device/directory and
source-size/growth refusal, exact digest equivalence, free-threaded short-circuit and no reset path.
Test fixtures alone may snapshot/restore the private sys key. S4/S5 must prove the final check
starts after scan/phase two and no coroutine runs before synchronous mint/prepare.

Later media receipts bind exact native/HMP fingerprints and native SHA to E1, PG, C6, the route
test suite and T12. They confer no approval/write qualification. Compatibility wording is deferred.
Native callee closure, bytecode equivalence, process admission, memory ceilings, platform and
phone gates remain open. The existing approval gate's native-only fingerprint and reloadable
module latch limitations remain separately recorded; this new media design does not repair them.

## S6b listener binding freeze (2026-10-01)

Root adopts the independent Opus `READY_WITH_DECISIONS` advice as architecture, with RC1–RC5
resolved below. It accepts no implementation, route, manifest entry, live installation or phone
result. The current C6b source is included in the module set; the older architecture review did
not inspect that source. Security review of the exact implementation remains required.

- **RC1:** Allow per-load, set-once module caches in `bridge.py` and `reads.py`. Preload fills
  them inside the qualification disk bracket; media twins subsequently use those same objects.
  Replace only media-twin function-local imports. Old read/send behavior stays unchanged.
- **RC2:** The static required set is adapter, server, request_ctx, auth, crypto, contract,
  reads, authorize, store, compat, wire, logging_policy, bridge, local_media_gate,
  local_media_sidecar, local_media_candidate, local_media_active_scan, local_media_result,
  local_media_file_safety, local_media_active_batch and local_media_batch_binding. Registry and
  raster join the set when S4/S5 reach them. Captured modules are candidates until proven against
  actual listener use. Plain function globals (unwrap at most eight steps), class-body method
  globals, static module references and adapter namespace identity supply the proof. Sweep the
  set for split module/function/top-level-class references using identity; names only route the
  comparison. No fabricated module, heap scan or preload-time module-name lookup is allowed.
- **RC3:** Capture `_LOAD_SELF` as a module candidate at adapter import and prove
  `vars(_LOAD_SELF) is globals()` inside the preload. Capture the other non-media candidates
  through static adapter imports. Preserve the lazy bridge cache, extended to hold its actual
  module, and prove concrete context instances/classes and the shared error/context objects.
- **RC4:** Permit a docstring-only change to `local_media_gate.py`, with its pin renewed. Gate
  behavior, manifest and `MEDIA_DEPENDENCIES` are unchanged. Only `supported is True` with an exact
  BuildIdentity may import the gate; prove the gate's package and compat binding before calling
  its factory. Call the factory with only the identity and `preload=`. It runs regardless of the
  live media flag and cannot rebaseline. Ordinary exceptions close; BaseException propagates
  after closing the store, before hooks/listener activation.
- **RC5:** Before any manifest entry, perform a separate native-inventory slice covering actual
  profile/secret/terminal scope owners, profile-home resolution, SessionDB MRO method owners,
  image-provider storage and the format-only postprocessor callees. Include terminal lifecycle
  and credential-file mapping rather than omit them. This is not permission to edit the native
  inventory in S6b, and does not claim recursive closure or producer/provider qualification.

ServerContext gets callable `media_flag` and `media_qualified` fields, both default closed, and
strict exact-True accessors that close on exceptions and log only the exception type. The flag
re-reads live configuration. Qualification is blocking and must later be invoked on the default
executor; no route consumes it in S6b. S4/S5 must consume a fresh request-local result immediately
before synchronous owner/flag/TTL/CAS mint or prepare, with no intervening await and no cache.

Require causal coverage of unsupported/truthy/missing-dependency states, empty-manifest closure,
synthetic admission using actual objects, whole-package eviction and old-listener cache identity,
split edges, foreign homes, inert init, strict/live flag, callable fields, no profile authority,
BaseException cleanup, unchanged approval binding and existing route bytes, AST import/preload
constraints, and reconnect in the same load. Synthetic admissions use isolated package/native
copies; fixture-only anchor restoration never becomes a production seam.

Residuals remain: import/eviction races can latch closure until process restart; abandoned module
loader threads can block preload indefinitely; native lazy-import objects are not bound; the
sweep does not attest partial/lru-cache callables or modules outside its set; bytecode/ABA,
same-account tampering, interpreter/platform, unbounded Git/kernel latency and per-check cost
are not qualified. The source slice does not fix local MEDIA display or deliver a media feature.


S6b root interpretation after the author handoff: keep the reviewed lazy, set-once cache
helpers. An inert media twin can first fill them on an unadmitted listener; no production
handler selects those twins. The later preload proves and returns the actual existing cache
objects inside its disk bracket, rather than claiming that every cached module's first import
occurred there. This is part of the retained loaded-bytecode/first-import limitation, not new
media authority. A future S4 handler must qualify before selecting a twin and use the old read
path when closed. Reconnect must not refill an existing cache or switch its objects after
whole-package eviction. Exact source security review remains required.


### S6b root repair checkpoint — 2026-10-01

The bounded repair changes only comments/docstrings and tests; root compared the five runtime
module ASTs against the original frozen bytes with docstrings stripped and found no behavior
change. The original and repair inventories remain private immutable evidence. Acceptance is
still pending an independent delta review of the exact root-frozen repaired files.

Retain the availability residual found by that review: `_bridge_classes()` publishes its
module and class caches in two unlocked assignments. Concurrent first calls racing whole-package
eviction can give the preload split copies. Its identity proofs refuse that mixture and the first
factory latches closed until restart. This is fail-closed availability behavior; no receipt,
serving admission or arbitrary concurrent-reload recovery is claimed.

The repair author's required developer-skill read was omitted after searching the wrong skill
location. That omission remains in the original private report. Root has loaded installed skill
1.3.50 at its actual path and requires the independent delta reviewer to read it explicitly.
Do not rewrite historical reading records or claim the author read guidance they did not read.
The slice changes no native integration, wire, inventory, manifest entry or serving consumer.


### S6b bounded source acceptance — 2026-10-01

Root accepted the repaired listener-binding source after independent Opus delta review.
The 15 repaired file hashes matched root's immutable inventory; the repair changed
comments/docstrings and tests, with runtime AST behavior unchanged. Root's focused
138 cases passed. Independent review confirmed 138 cases and 13 causal mutant kills.
The earlier full suite retains three baseline contract-table failures; no full-suite
green claim is made. The original review and repaired delta together cover this source
slice only. S6, S4/S5 serving consumers and every admission/release gate remain open.

The cache race closes the process until restart when it affects the first supported
factory. Otherwise the affected load stays closed until coherent reload or restart.
With the empty build manifest the preload is not reached, so this race currently has
no media effect; ordinary text and send paths are unaffected. Dynamic-lookup pins are
syntactic and bounded; causal eviction tests cover the exercised sites. Fixture spies
prove module selection, not native cost. No arbitrary-callback termination claim is made.

Native inventory ownership, real-loader registration, native binding cost, registry/raster
joining, serving routes, T12 memory, device and release checks remain required. No manifest
entry, production media consumer, live installation or local image display is added here.


## Minimum-version conversion (supersedes S6 manifest/fingerprint/anchor, S6a admission semantics, S6b preload qualification) (2026-10-02)

Source of authority: the owner policy of 2026-10-01 ([spec 013](../013-minimum-version-compatibility/OWNER_POLICY.md))
and the [spec 034](../034-approval-minimum-version-admission/ROOT_DECISIONS.md) precedent (exact gate
removed, object-identity fence kept, no process latch, sampled evidence only). Root adopted the
independent architecture proposal's decisions D-M1 through D-M10 **for documentation only (M1)**.
This section accepts no runtime source, serving route, manifest entry, qualification or release.
No live, device or provider action is authorized by it.

**M0 integration checkpoint.** Local media was merged onto the converted minimum-version base as an
inert integration checkpoint (merge `0cdbbf5`; converted approvals base `2c153e2` plus the relative
nonexecuting approval-probe fixture `f4045cd`; media source `6d400af`). Root reviewed it as
`ROOT_M0_INERT_INTEGRATION_REVIEWED_NOT_FEATURE_COMPLETE`. It is never a release candidate and is
never installed. In it the runtime media binder is a **constant closed callback** (`_media_qualifier`
always closed, no gate import, no identity read), so no media route, descriptor, registry mint or
delivery exists. The M2 member now computes probe eligibility, but that M0 constant stays the current
runtime behavior until M3 lands.
The retired gate module and its empty manifest were not carried onto the converted base because the
converted guard tests forbid a module that reads a supported-builds list or calls the deleted probe.

### Decisions

| ID | Decision |
|---|---|
| D-M1 | Integration base is the converted approvals line (`2c153e2` with the `f4045cd` probe fixture), merged with `6d400af` by a root-reviewed finite/remerge process. The gate and manifest are removed because they are incompatible with the owner's minimum-version policy; byte-identical helpers and twins are retained. |
| D-M2 | New eligibility member `local_media`. It depends on `READ`, **not** on `SEND` or `SESSION_BROWSING`. Its probe table is exactly the three native callables the media path reaches beyond the read core: `SessionDB.get_session`, `SessionDB.get_session_by_title`, `SessionDB.get_compression_lineage`. Computed once at listener open. No image-producer probe: a changed producer spelling is caught per candidate by the retained lexical check. |
| D-M3 | Floor inherited from the write floor, `0.21.5` / `2026.9.24`. Unknown, `0.0.0`, unlisted, newer and development versions are attempted. |
| D-M4 | Genuine media-chain identity binding only. Verify the media-chain cross-references once at listener open (this listener only; never latch the process), bind the verified strong references to that listener, and adopt a cheap in-memory use-time identity fence that closes only that listener. Cache publication uses a lock and a **single tuple assignment**, including the bridge module together with its classes; imports happen outside the publication lock. No GIL assumption, no process latch, no origin, fingerprint or manifest authentication claim, no generic all-route core proof. Accepted helpers and their provenance are unchanged. The M3 exact-candidate independent security review is mandatory. |
| D-M5 | Gate: valid bearer, approval-owner device, live `local_media.enabled` exactly `true` (default off), and actual media availability. Every per-bot, surface and history grant check remains. A non-owner device gets `404` first. No automatic grants. |
| D-M6 | The per-request "fresh qualification" await is replaced by a synchronous immediate check of owner, flag, availability, TTL and CAS, with no `await` between the check and mint/`prepare`. The two off-loop bounded native phases, deadlines, permits and copied `ContextVar`s are unchanged. |
| D-M7 | The existing runtime bounds apply on every version. Native C6b cost and T12 memory sampling are **release-candidate evidence, never a per-version allowlist**; a failure changes the implementation, not a ceiling. |
| D-M8 | User-reviewed offline issue drafts only, and only for an owner flag-on actual `media_unavailable` failure; fixed labels; no paths, refs, digests, profiles or device ids; never automatic. |
| D-M9 | An assistant `MEDIA:` string remains ordinary text with no authority. The `image_generate` tool row supplies the local image. Root's presentation choice: keep the `MEDIA:` text **unmodified**: no suppression, de-emphasis, duplicate detection or assistant-path fetch. No presentation question is pending. Other producers are a recorded typed-artifact API gap (G-M2). |
| D-M10 | A legacy process anchor is ignored: new code never reads or writes it, and no reset helper exists. Any live install still uses a separately authorized idle gateway restart. |

### Superseded items (historical text kept above, not rewritten)

- Accepted table: the **Gate** row ("process-qualified manifest, shipped empty").
- Authoritative corrections: **3** (process qualification) and, in correction 5/clarifications, the
  qualification-executor and immutable-startup-mismatch clarifications; residual "out-of-tree providers unfingerprinted".
- The whole **S6 media qualification design freeze** subsections "Manifest, source coverage and
  dependency probes" (except that the three native probe rows survive as D-M2), "Process identity across
  reloads and homes", "Preload and loaded origins", and "Bounded reads and final request check" (except the
  rule that no `await` runs between the final check and mint/`prepare`, which is kept as D-M6), together with
  "Required causal checks and later admission" insofar as it binds receipts to exact fingerprints.
- The **S6b listener binding freeze** `media_qualified` paragraph, RC4 and the preload-bracket wording
  of RC1-RC3; the S6b repair checkpoint and bounded source acceptance remain accurate historical records of
  the retired binder only.
- **C6.6** "recheck owner, flag and **qualification** gates" and the S6 "fresh qualification" wording:
  read "owner, flag and availability" (D-M5, D-M6).
- Process-wide exact-build qualification statements elsewhere in this directory.

Retained: the C6b identity proofs and one-capture rule; the typed tool-row authority (C2); RC1's per-load,
set-once module caches (publication fixed per D-M4); RC2's media-chain coherence and identity edges
(reduced to a listener-open in-memory check); the registry, permits, 20 s/30 s deadlines, 8 MiB, raster
and leaf rules; and every accepted security and resource bound. No authorization is broadened.

A direct-send switch that is off does **not** close media. Media is a read-path feature.

### Evidence and gaps

- Existing S6/S6a/S6b results, hashes and test counts are historical evidence of the retired design.
  E1 (producer spelling), the Linux leaf run, C6 cost and rotation evidence remain sampled evidence for the
  builds and platform they describe. They do not prove behavior on other builds and are not an admission input.
- **Pending, not done:** C6b exact-native complete binding cost and concurrent-writer evidence; T12 memory
  on sampled builds; independent exact-candidate security review; owner-authorized install, flag and
  physical-device acceptance. The feature is **unimplemented**; no route exists.
- SD3 and SD5 unresolved scoped-authorization risks are retained, not remediated here.
- **G-M1 (HERMES_API_GAP):** Hermes lacks a bounded, side-effect-free, snapshot-consistent session and
  message read. Native reads may materialize unbounded content, flush queued token counts and prune; these
  residuals apply on every build and are neither solved nor hidden.
- **G-M2 (HERMES_API_GAP):** no typed, profile-scoped tool-artifact record exists in session history, so
  producers other than `image_generate` cannot gain authority. Retained as a broader artifact API gap.
- **E-M1 (EVIDENCE_GAP):** whether `get_session_by_title` and `get_compression_lineage` exist at the read
  floor is unverified; the write floor is chosen because the three rows are already in the send table there.
- **E-M2 (EVIDENCE_GAP):** hidden-root title rotation was observed on one sampled build only. On other builds
  the proof fails closed (`NOT_ELIGIBLE` or `ELIGIBILITY_UNCERTAIN`), which is correct behavior.

### Known state of the integration checkpoint (not green)

Three carried contract-table failures in `test_contract_tables.py` remain because the draft contract carries
`media_unavailable` and `MEDIA_*` constants that `contract.py` does not yet define; the same three fail on the
unconverted media source. 114 legacy qualification tests fail (109 listener-binding, 4 gate-pinning layout, 1 bridge-inert
case) and the removed gate test has one collection error. They test
the retired binder and are **explicit work in progress, not green**, until M3 replaces or retires them.
Nothing was skipped or hidden to change that.


### M2 bounded source acceptance (2026-10-02)

Root accepted the four-file eligibility/CLI/draft slice after independent bounded source review.
Each of the three native instance methods requires two positional parameters (self and the argument
used by the existing bridge), through the unchanged signature/containment discipline. Native AST
inspection on two sampled builds supports that shape; it is not a runtime build allowlist.
Root and the reviewer each passed 368 focused cases with six existing no-native-fixture skips;
the new media file passed 61 cases with no xfail. Eight root scratch-copy guard removals failed
their targeted assertions, and restored source passed. Thirteen selected tool tests passed.
Pinned Ruff 0.16.9, surface and explicit privacy checks passed. Earlier root tool attempts had a
missing test path and package collection errors; they executed no test bodies and are not passes.
The corrected tools collection boundary passed all 13 selected cases.

A table-isolated media failure does not close siblings. An actually absent API shared with send
or browsing can independently close those members through their own tables. Compat's media line
is probe eligibility only, not live serving or a host-flag verdict. The offline media failure draft
is an operator declaration, not an attestation of an owner requester or enabled flag; rate limits,
permissions and routing keep their own explanations. Shared version/evidence diagnostics may still
read metadata, but no media admission consumes a build list, manifest, SHA or fingerprint.

M3 binding, S4/S5 descriptors/fetch, C6b/T12 sample evidence, independent exact-candidate security
review and device acceptance remain open. The binder is still constant closed. The known 114
retired gate-test failures, three draft-contract failures and removed-gate collection error remain
visible; no full-suite green or shipping claim follows. Sibling signature rows were reviewed
unchanged in the finite diff; a mutation broadening one sibling row survived the reviewer's tests,
so that constraint is source-reviewed rather than mutation-certified.


### M3 listener-scoped source acceptance (2026-10-02)

Root accepted exact `f737197` after mandatory independent Opus-alias review. All 13 candidate paths
and all nine protected media helpers matched the frozen root inventory after review. Bridge and reads
logic is unchanged; their only M3 edits are comments. Binding checks the genuine media cache chain and
reads sidecar by identity, holds strong per-listener references, accepts absent build identity, and uses
a synchronous cache-identity fence with no import, native call or disk read. A failure closes only that
listener until reopen. Bridge module/classes publish in one locked tuple with imports outside the lock.
The fixed outcomes are `media_binding_incoherent` and `media_binding_changed`.

Root's full unit run passed 3047 cases, with three existing S4 contract-table failures, 16 existing
native-dependent skips and one preexisting warning. No full-green claim follows. The obsolete gate test
collection error and 114 legacy design failures were explicitly retired or adapted; no unrelated skip
or xfail was introduced. The reviewer independently reproduced the candidate results and named causal
guard failures. Its aggregate mutant count is not adopted because the headline and survivor list differ.

Carry-forward requirements: S4/S5 must snapshot the bound module tuple synchronously beside the
availability check, refuse missing or foreign tuples, and use the same bound objects at mint and fetch.
The mutable context field itself is not fenced by M3. Restore the live helper's omitted eight-step,
nine-step and cyclic unwrap test coverage. Existing same-account in-process mutation, no bytecode
attestation, non-atomic native reads and G-M1/G-M2 residuals remain. No serving, native complete-binding
cost, T12 fetch memory, physical-device, free-threaded or deployment acceptance is implied. The A8
owner/non-owner route responses and A10 mint/fetch identity remain unproved until S4/S5.


M3 test follow-up: root restored the omitted unwrap-bound coverage without changing production code.
Five focused cases passed: eight steps reach the original function; nine steps and a cycle refuse;
raising/removing the bound and shortening/skipping the chain each make the scratch-copy property
fail. A watched function dictionary bounds runaway-cycle execution. Ruff, explicit privacy and
diff checks pass. This closes T-1 only; the full 3047-case result above predates this test-only delta.
