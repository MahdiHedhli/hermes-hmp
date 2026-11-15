# Amendment 1: safety-review rulings (tooling only)

Status: frozen by root after the independent tooling review. Scope is fixture tooling and its tests.
No runtime plugin file, shipped manifest, live home, original Hermes source or venv changes, and
nothing here grants runtime admission. Nothing in this amendment has been run yet (see `tasks.md`).

## R1. Mutation copy cannot write through links (safety)

`copytree(symlinks=True)` keeps links, so a linked `.venv`, `bin`, `site-packages` or `tools`
pointing into the original build would send a retarget or swap write into the original.

- `approval_fixture.assert_copy_contained(dest, original)` runs on the copy BEFORE any write. It
  refuses any symlinked directory that resolves outside the copy, any dangling link that leaves the
  copy, and any link that resolves into the original build. A refused copy is removed.
- A link to a FILE outside the copy is normal and allowed (`.venv/bin/python3` to a system
  interpreter): it is read and executed, never rewritten, and imports must still come from the copy
  (`verify_copy_isolation` is unchanged).
- Retarget candidates are collected and validated first: a symlinked candidate is refused unless it
  is a `bin/*` interpreter link (skipped, never written); every candidate must resolve inside the
  copy. `_retarget_file` and `mutate_swap_file` re-check the resolved path (and, for the swap file,
  that no ancestor is a link) before writing.
- Regressions (`test_approval_copy_safety.py`): ten hazard variants (linked venv, bin, site-packages
  and tools directories; relative and absolute escapes; dangling directory; script link into the
  original; symlinked `pyvenv.cfg` and `.pth`) each raise with byte-for-byte snapshots of the
  original and every link target unchanged; an external interpreter link is allowed and unwritten.
  Only fresh synthetic copies under `tmp_path` are used.

## R2. Plain `.pth` entries are retargeted

`*.pth` files in the copied `site-packages` join the retarget candidates. A test builds a real
venv whose plain `.pth` points at the source tree: a verbatim copy imports the ORIGINAL and is
refused by the isolation check; the retargeted copy passes the real check.

## R3. Final receipt structure and identities

A final receipt is accepted only when, in addition to the earlier checks: `source_sha` is 40 hex
and equals the entry's `source_sha`; `required_tests` equals `required_test_names(label)` exactly
(order, no omission, extra or duplicate); `junit_sha256` is a valid 64-hex digest; `read_fingerprint`
and `direct_send_fingerprint` equal the CURRENT fingerprints over the read and direct-send lists
(the caller's lists, else the plugin's own manifests) on every consumer; `plugin_sha256` matches;
every stage is exactly `true`; and `upstream_verified` is `true`. The full runner therefore needs
`--upstream-source` whenever `--receipt-out` is given; `--only` debug runs may omit both and stay
unverified. Provisional fixture bootstrap semantics are unchanged, and a mislabeled final or
provisional receipt is still refused. The required-test table moved to `approval_fixture` (shared,
no import cycle); `approval_matrix` re-exports it.

Limit: this is trusted local evidence for catching accidental or stale receipts. A JSON file cannot
authenticate that tests ran, there is no signing authority, and no environment override exists.

## R4. Lifecycle and reconnect evidence

- The reconnect harness no longer hard-codes `supported`: a recheck reports the support of its
  originating (first) live context. The report also carries the harness `pid`.
- `approval_matrix.check_lifecycle_evidence` machine-checks the saved values: the swap file is the
  approval-only `tools/approval_prompt.py`; approval fingerprint before/after differ while read and
  direct-send fingerprints (now recorded before and after the swap) stay equal; full restarts
  (empty start, swap) change the gateway PID; the admitted-start evidence (`admitted-start-<label>`,
  now required) stays in one PID with closed-after-removal and reopened proven; reconnect steps equal
  `RECONNECT_EXPECTED` exactly, all supported, from a harness process separate from the gateways.
- Limit (unchanged): route 200 after a swap or restore is gate admission only, not full resolution.
  A full approval round trip is proven only in the empty-start and T7/T8 cases; other cases need
  their own round trip before any stronger claim.

## R5. Labels and test IDs

Identity refuses a label that collides with a default fixture build (`stock-base`, `experimental`,
`owner-local`, plus every label in `builds.yaml`). Before the run, `pytest --collect-only -q` on the
required invocation paths must produce exactly the server-root collected IDs (`logs/collect.log`).
Both retain the full file, function and parameters; only the known root-relative prefix differs.
Actual output is tested, and omissions, extras and duplicates are refused.

## R6. Status documents

`tasks.md` and `checklist.md` carry one current status block. The Python 3.14 local 1399 passed /
12 skipped and Ruff-clean results apply to the pre-amendment diff only. The ORIGINAL run 5
baseline completed: 27/27 real gateway tests and all seven stages passed on pre-safety tooling.
Current root evidence and active run are recorded in `tasks.md`; old local counts above are
historical. No shipped qualification or live enablement is claimed. Still open: git-install
lifecycle and git-branch coverage, physical device gate, memory attestation, release gate.

## Focused follow-up review limits

Opus cleared the six assigned findings on the current tooling. Root repaired the dangerous
documentation example that reused run-5 output and corrected the harness/stability description.
Remaining evidence limits are explicit:

- The T8 refusal-absence check is made after clarification settlement, not after a separately
  observed completed turn. It covers the two profiles' own default conversations only.
- Lifecycle metadata is checked at generation. Final consumers check required IDs, JUnit digest,
  source identity and current lane/plugin fingerprints, but do not re-evaluate embedded lifecycle
  values or bind before-swap fields again to the identity-stage values. Cleared per-run evidence
  and the actual test assertions support the local result; the receipt is not authenticated proof.
- The phone-correlation JSON is supplementary boolean metadata. The runner relies on the T8
  assertions and its required JUnit result, rather than separately validating that JSON.
- External file links may be read outside `.venv/bin`; they are never retargeted or mutated.
  Import isolation checks two named Hermes modules, not every imported dependency. Root audited
  the pinned run input: only the three normal Python interpreter links leave it.
