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
