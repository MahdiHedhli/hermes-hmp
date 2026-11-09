## November 9 — complete runtime/cache metadata sequence implemented; deployment pending

Source `41100a4` wires the complete runtime-source and declared-cache file sequence through the shared metadata engine: original opened-directory observations, no-follow leaf-before stat, opened-leaf identity, actual EOF followed by leaf checks, and final ancestor checks including the root. Each step carries the caller’s literal prior return and original baseline. The actual final return is held across reserved descriptor closes; finish checks the original complete ACK chain, EOF, capsule retirement, closed descriptor chain, exact debit/reserve accounting and current lifecycle. Unwired owner policies retain the zero-cursor guard. This is complete runtime/cache file integration, not completion of the entire character pipeline.

Causal controls exposed two finish defects in the earlier uninstalled source: a late weak-reference callback could alter earlier custody/ACK mirrors before acceptance, and a foreign final ordinal could invoke a comparison hook before refusal. The repaired finish observes weak-reference death before a final callback-free mirror seal and checks exact integer types before comparisons. The preserved baseline has one normal pass and three expected failing controls. The repaired four-case suite passes, with independent read-only source/evidence review. Four cache controls also pass, including normal integrated reading, copied-plan rejection, late ledger drift and interrupted EOF. Test successor `e3a78c6` adds two passing integration cases: a complete empty file with a real EOF and loss of the actual final return, which refuses without adopting a matching history entry or replaying work. Production bytes are unchanged across these test successors.

All ten selected current-interpreter cases pass across three unchanged-source runs. The combined ten-case Python 3.11.15 suite also passes: ten tests, zero failures/errors/skips, unchanged source. The prior post-read 13-case minimum-interpreter run has also finished with 13 passes, zero failures/errors/skips and unchanged source. The earlier post-read nine-case suite and leaf-before/opened thirteen-case suite now run through the actual integrated calls and pass on Python 3.14.9 with unchanged source; independent read-only review found no lost causal coverage. They preserve real file changes, actual native-call/debit counts, original EOF/ACK and capsule retirement, and copied/missing predecessor or EOF refusal. Other standalone metadata tests still need migration; no legacy production opt-out is being added for them.

Test successor `e12df99` adds final-directory cases without changing production bytes. Three substituted-input cases pass before any native call/debit: copied directory baseline, a different original directory baseline, and a non-None root parent. A real synthetic-directory mode change after EOF refuses after exactly one charged native observation, retaining its original failed pending consumer without ACK or file completion. The initial four-case run had three passes and one fixture assertion failure: it incorrectly expected that charged failure’s pending consumer to be cleared. The corrected case passes separately, received independent review, and the original failed evidence is retained. The combined 26-case Python 3.11.15 migration/directory suite at `e12df99` passes: 26 tests, zero failures/errors/skips and unchanged source. This qualifies those selected causal checks on the minimum interpreter, not the whole startup pipeline.

The next complete implementation boundary is the fresh cache-probe traversal, documented in [the reviewed contract](https://github.com/MahdiHedhli/hermes-hmp/blob/feat/startup-bytecode-headers-20261107/specs/046-bot-presentation-integration/FRESH_CACHE_PROBE_METADATA.md). Its original two-part scope/cache location and missing-component branches cannot use the declared-file/EOF consumer. Exact reported-missing diagnostics need distinct charged, one-use acknowledgement without becoming successful syscall receipts, kernel-absence proof or fallback authority. This is local HMP work still to implement; startup before/after probe effects remain a separate migration. A separate test-only branch `fc8fadf` migrates five resource-preparation and three predecessor-chain cases onto actual integrated resources/returns; independent source review found no fixture blocker, and its eight-case current run is in progress.

Bot-character images and host-local chat images remain unfinished and undeployed. Other metadata policies/all39 sites, remaining native operations, startup/factory/service/runtime integration, resource/deadline limits and physical/release acceptance remain open. No candidate host/app deployment, restart, grants, model/provider change, pairing, job execution or release submission occurred. The full roadmap goal remains active.


The following design notes are historical where superseded above; remaining acceptance requirements still apply.

# Fixed declared-file metadata integration plan

Source planning checkpoint: November 8, 2026. Independent read-only review used
candidate `b29baaa` and the current declared-walker source. This is an
implementation plan, not native/site/runtime qualification. The full feature
goal, all39 metadata sites and the other native operations remain required.

## First complete integration boundary

Complete runtime/cache `_file` end to end: initial directory fstat observations,
leaf-before stat, leaf-opened fstat, post-read leaf fstat/stat, and ordered final
ancestor fstat/stat pairs. Keep artifact/package and link/diagnostic policies
separate until their actual material/lifecycle closures are qualified.

Use one shared custody/admission/produce/consume/ACK/retirement engine with fixed
site-specific wrappers. Do not copy the entire directory engine per site. Do
not accept an operation, callback, policy, variant or dispatch name from a
caller. A closed internal variant must derive from the actual original plan
row and held walk/site allocation, retain immutable original identity, and
rejoin that provenance before and after every effectful callback. Merely
constructing a matching token/tuple is DATA, not authority.

## Required original joins

- Initial directory fstat: the actual opened-directory allocation, declaration,
  component and ordinal; its actual commit retains primitive five-field identity.
- Leaf-before stat: the original expected row/size and opened parent/name, literal
  no-follow call, actual returned full-nine-field identity, regular-file uid/
  mode/link/size policy. Preserve the actual same-result `st_mtime` primitive and
  original checked integer conversion for source hashing; never derive it from
  nanoseconds. This commit does not grant an open operation.
- Leaf-opened fstat: the actual opened leaf FD/allocation and the same original
  leaf-before commit; compare full identity. Existing open provenance and parent/
  name/no-follow checks remain independently required.
- Post-read fstat/stat: the same original leaf/parent/allocation and original
  full identity, after actual EOF read ACK, including an empty file. A byte
  count or synthetic EOF marker is not the actual read completion.
- Final ancestors: each actual original directory allocation and its earlier
  actual commit identity, in original walker order, including the root's None
  parent. New observations cannot become replacement baselines. Fixed wrappers
  use literal stat kwargs or the literal fstat signature; unknown variants refuse.

Every site shares the original budget/debit and reserved-close accounting.
The fixed caller preholds actual factory operation/marker/payload and original
predecessor commits, then carries actual producer/policy/ACK/retirement returns.
Keep history raw-free and payload ownership behind conditional original links.
Never retry effects, refund ambiguous native entry or overwrite foreign values.
Failure prevents subsequent site admission; cleanup retains original owned/
ended/nonpending and reserved-close constraints. Preserve source hash/header,
actual EOF, timestamp and final identity/source-fact checks.

## Shared engine predecessor and source-effect contract

The original integer cursor alone is insufficient predecessor evidence. Before
enabling leaf roles, retain the actual raw-free ACK commits under the original
plan and one immutable predecessor link per consumer. Rejoin each original
indexed ledger attempt, acknowledged result and consumer commit, registration,
held walk and site. Do not retain a copied prefix per consumer. Exact primitive
ordinal checks must precede comparisons and indexing. Recheck history after
callback-bearing material/native closure; matching reconstructed DATA is not an
actual ACK. The current isolated history extension and its pending/verified
execution scope are tracked in [ACK history](NATIVE_METADATA_ACK_HISTORY.md).

For leaf-before, the fixed caller must retain the actual return of the original
`source_digest.begin` call. The source-effect operand is that held `_DigestRoot`,
not a current `effects[-1]` lookup, a boolean or a caller-selected policy callback.
An absent operand must agree with the original inactive source-digest condition;
cache/non-source reads must not acquire a timestamp requirement. Rejoin the
actual source root/effect, original owner/scope/expected row and buffer before
and after callbacks. Keep source-only timestamp DATA tied to that actual root
and the same native snapshot, then carry it into the original source fact.
This is a required implementation contract, not a claim those joins are wired.

Use the original closed site variant to choose the literal stat/fstat call and
fixed policy internally. No operation index, policy callback or dispatch name
may be selected by a client. Preserve the normal directory engine while adding
leaf-before, opened-leaf, post-EOF and final-ancestor roles to shared machinery.
An ACK-list append interrupted before cursor advancement is partial history:
retain it with sticky failure, no rollback/refund and no automatic replay.
One retained predecessor link bounds reference storage linearly; repeated chain
audits still need separate CPU/time qualification.

## Completion and acceptance

Do not remove the current zero-cursor guard as a shortcut. Replace it only when
the real sequence is wired and exact completion proves the original definitions
all consumed, pending slot empty, actual last commit/history joined, required
predecessors and resource identities retained, no failure/raw capsule/inflight
work, and original declaration/file-walk progress intact.

Before integrating: complete current actor-preflight causal controls, retain
existing directory behavior, then test both supported interpreters for copied/
foreign tokens, reordered sites, wrong parents/FDs, revoked/stale lifetimes,
EOF/hash ordering, zero-size files, finalizer drift, actual return loss and
partial ACK interruption. Preserve existing time bounds and failure evidence.
Independent review follows exact source and causal outcomes. Pure policy tests
cannot qualify these joins. All39-site migration, reported-missing diagnostics,
readlink/enumeration, remaining six-operation accounting, service/runtime and
physical device/release acceptance remain explicit unfinished work.

## November 9 source checkpoint

Shared caller source72c5e4b supports original directory, leaf-before and
leaf-opened roles. The opened role binds the actual leaf allocation and the
literal previous leaf-before return. Its pre-admission closure checks the same
walk/expected row and original predecessor; its policy compares all nine fields
of the actual fstat identity against that held earlier identity before ACK.
Current source passes five focused opened-leaf cases across two runs. The
combined28 floor selection is pending. These are runtime-source fixtures, not
cache/fullwalker/native/device qualification.

Next integrate the actual EOF receipt, post-read pair and final ancestors with
held original baselines. A current closed-read guard requires the latest read
debit and IDLE; it cannot be repurposed unchanged after later metadata debits.
Keep it strict and add a separately bound historical receipt join for the
literal actual EOF return. Final metadata receipt closure also requires live
FDs/current debit; after reserved closes, use an actual pre-close sequence-finish
return with strict historical cleanup joins. Do not replace either proof with
current cursor/history alone or caller-selected bypass flags. Change terminal
cursor/cohort and fullwalker completion together with complete wiring, while
preserving the zero-cursor guard for every unwired policy.

## Retained EOF/post-read source checkpoint

Sourcee8320e4 implements the two original post-read roles with literal baseline,
EOF and predecessor inputs held across callbacks. Historical runtime/cache read
receipt guards retain original ACK/raw-clear/step/accumulator/journal joins;
current wrappers still demand latest debit, healthy IDLE and no inflight work.
The post-read consumer additionally accounts for every attempt/debit between
actual EOF and each of the two fixed metadata rows, preserving close reserves.
No historical guard by itself admits work or nominates a current receipt.

Independent source review accepted the accounting/current-wrapper split and
required exact resource/variant types before baseline nested access. Those
fences and two zero-hook controls are implemented. The pre-fix normal control
reached both actual metadata ACKs and refused renewal of current-read closure;
malformed typed baselines reproduced foreign hooks before any new metadataC.
Repaired12 current checks PASS at e8320e4. Test-only676bb62 separately passes
an empty declared file with exactly one actual native EOF read and both post-read
metadata ACKs; production bytes match e8320e4. Combined13 floor checks are running.
Previous72 floor28 PASS belongs only to that earlier source. Final ancestors, pre-close finish receipt, complete _file
wiring and terminal-cursor handling remain unimplemented; preserve the old
unwired finish guard until the entire proof is integrated.
