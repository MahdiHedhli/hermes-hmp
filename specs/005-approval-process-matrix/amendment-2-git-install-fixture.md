# Amendment 2: git-install fixture matrix mode (tooling only)

Status: proposed by the tooling worker for root review; nothing here has been run against a real
Hermes clone yet. Scope is fixture tooling and its tests. No runtime plugin file, shipped manifest,
live home, original Hermes source or package changes, and nothing here grants runtime admission.

This is a fixture-only mode. It is **not** a release gate, **not** memory attestation and **not**
device or owner admission. The production `approval_supported_builds.json` stays empty and there is
no environment override in the runtime. A git receipt is trusted local evidence for catching
accidental or stale receipts, exactly like the archive receipt (amendment 1, R3): a JSON file cannot
authenticate that tests ran.

## G1. The mode

`approval_matrix.py --git-install` runs the same seven stages, the same ordered required tests and
the same lifecycle and reconnect evidence as the archive mode. Only the identity differs:

- The build's `src` must be an isolated, independent git clone. `.git` must be a real directory
  (never a link or a `gitdir:` pointer), hold no symlink, no `objects/info/alternates`, no
  `commondir`, no hard-linked file (a `git clone --local` shares inodes with its source), and no
  `remote`, `include`, `includeIf` or `url` config section. It must not resolve into, or contain, the
  optional `--upstream-source`.
- `git rev-parse HEAD`-equivalent (`compat.resolve_git_head_sha`, the runtime's own reader) must be
  the full 40-hex `--expected-source-sha`, before and after the run (stability stage), together with
  an identity digest of HEAD, `packed-refs`, `config`, loose refs and the object file listing (never
  the index, logs or locks).
- Without the flag a `.git` is still refused ("qualifies an extracted archive fixture"), and with the
  flag a missing `.git` is refused. The archive mode and its receipt format are unchanged.
- `--upstream-source` stays optional for debug runs and required with `--receipt-out`, as before. It
  is only read (`git -C <upstream> rev-parse HEAD` with `GIT_OPTIONAL_LOCKS=0`, plus a fingerprint
  compare).

## G2. Receipt binding

- Evidence kind `approval-fixture-qualification-git` (`RECEIPT_KIND_GIT`) with `install_kind: git`
  and `git_sha`. The archive kind is unchanged and carries `git_sha: null`.
- The entry carries `git_sha == source_sha ==` the build's resolved HEAD. The runtime matches a git
  install only to an entry with the same `git_sha` and an archive only to a fingerprint-only entry,
  so `validate_approval_receipt` now requires exactly that:
  a `.git` build needs a git entry bound to its HEAD and evidence of the git kind; a no-`.git` build
  needs `git_sha: null` and evidence of the archive kind. A mismatched archive/git source, a missing
  `.git`, a moved HEAD, a wrong, short or differing `source_sha`, or evidence of the other kind is
  refused, for provisional and final receipts alike. The required test list is identical.
- The direct-send fixture installer (`install_fixture_qualification`), `rebind_fixture_entry` and
  the read bootstrap (`build_fixture.bootstrap_compat_entry`) bind the build's HEAD the same way
  (`None` for an archive, so archive behavior is byte-for-byte what it was). Each obtains HEAD
  only through `independent_git_head`, which runs `assert_git_fixture_clone` whenever a `.git` is
  present (a dangling link counts as present and is refused), so a standalone helper run can never
  bind a HEAD borrowed from a linked worktree, pointer file or shared object store.
- The provisional direct-send and approval receipts written by the runner carry the verified SHA.

## G3. Copy and swap safety

`copy_build_for_mutation` first asserts the original `.git` is independent, **before** anything is
copied, re-pointed or written; an unsafe source (missing or pointer `.git`, `commondir`,
`include`, alternates, links) is refused with no copy and no destination directory created. It then
additionally verifies, before the copy is used: the original `.git` is independent; the copy's `.git` is independent of it (copies are fresh inodes, never links); HEAD and
the identity digest are equal; an archive copy did not grow a `.git`. A refused copy is removed and
the original and every link target stay byte-for-byte unchanged. `rebind_fixture_entry` keeps the
entry's `git_sha` and refuses if the copy's HEAD moved. The in-place swap test asserts, for a git
receipt, that the swap moved the approval fingerprint only: HEAD and the `.git` identity digest are
unchanged before, after the swap and after the full restart, and the gate stays closed until the
full restart with the re-issued (provisional, fixture-only) entry. `check_lifecycle_evidence`
machine-checks those values (`git_sha_before/after`, `git_identity_before/after`).

## G4. Integration tests

The required IDs are unchanged (same names, same parameters). Each lifecycle case asserts the real
`.git` identity of the gateway's build equals the receipt entry's; the gateway's own first-supported
factory reads that `.git` through `GitFingerprintReader`, so a wrong SHA closes reads and sends
before any approval assertion. Unit tests (`test_approval_git_fixture.py`) run the real
`GitFingerprintReader` and `_capture_approval_baseline` over real `.git` directories in `tmp_path`.

## G5. Root instructions to prepare the fixture (the tool mutates nothing of the original)

```sh
BUILDS=/private/tmp/<scratch>/builds; LABEL=<new-label-not-in-builds.yaml>; SHA=<40-hex>
SRC="$BUILDS/$LABEL/src"
git clone --no-local --no-checkout <original-hermes-source> "$SRC"
git -C "$SRC" checkout --detach "$SHA"      # or the exact branch, then confirm HEAD
git -C "$SRC" remote remove origin          # nothing left to push or fetch
git -C "$SRC" rev-parse HEAD                # must print $SHA
# The fixture's own venv is built by Hermes PM's pinned isolated build env (NOT `uv sync`), from a
# compatible pinned interpreter, into a fresh destination that does not exist yet:
<compatible-pinned-python> -m pm.build_env --source "$SRC" --out "$SRC/.venv" --group dev --group test
python3.14 tools/compat/approval_matrix.py --git-install --builds-dir "$BUILDS" --label "$LABEL" \
  --expected-source-sha "$SHA" --upstream-source <original-hermes-source> \
  --out <scratch>/out --receipt-out <scratch>/out/receipt.json
```

`--no-local` is required (the default local clone hard-links objects and is refused). The prior
archive matrix receipt is never reused: a git receipt needs its own full run.

HMP tool tests use the repo's pytest configuration explicitly (from the HMP repo root):

```sh
uv run --frozen --project server --extra dev pytest -c server/pyproject.toml --rootdir server \
  tools/fixtures/tests -q
```

## G6. Limits

Same as amendment 1, plus: the git mode proves the runtime's identity reader, factory and gate over
one real clone at one commit and branch state; it does not prove release, memory, device or owner
admission, and it does not widen the runtime. A branch checkout (`ref:` HEAD) resolves through the
same reader, but only the HEAD SHA and the metadata digest are bound, not the branch name.

## G7. Unresolved: runtime dangling-`.git` archive fallback (separate future review)

**UNRESOLVED, out of scope here.** The runtime's `resolve_git_head_sha` (`server/hmp_plugin/
compat.py`) tests `.git.exists()`, so a dangling `.git` symlink reads as "no git" and could be
matched against an archive-style (fingerprint-only) entry. The tooling in this amendment is
stricter (`assert_git_fixture_clone`, `independent_git_head` refuse any `.git` link), but that is
a fixture-side guard only: it does **not** resolve, and must not be read as resolving, the runtime
production behavior. It needs its own focused security review and a runtime change in a separate
task; nothing in this amendment edits runtime code.
