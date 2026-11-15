# Checklist: approval process qualification matrix

Unchecked means not yet confirmed at root for the CURRENT tooling diff (including amendment 1).
Current results live only in `tasks.md` ("Current status").

## Design invariants (review)

- [ ] `server/hmp_plugin/approval_supported_builds.json` still has `"builds": []`; no plugin file changed.
- [ ] No plugin runtime file mentions `HMP_APPROVAL_QUALIFICATION` or `HMP_DIRECT_SEND_QUALIFICATION`.
- [ ] Direct-send receipt alone leaves AP-3/4/6 closed (`test_direct_send_receipt_never_opens_approvals`).
- [ ] Receipt validator rejects absent, wrong, malformed, stale and cross-build receipts (unit tests).
- [ ] Final receipt: source_sha, exact ordered required_tests, JUnit digest, read/direct fingerprints,
      plugin digest, stages and `upstream_verified` all checked on every final consumer.
- [ ] Mutation only in a scratch copy; links are validated before any write; the copy imports itself.
- [ ] Final receipt written only after all stages pass and source fingerprints are unchanged.
- [ ] Sentinel-only dangerous commands; synthetic homes, XDG roots, credentials; loopback only.

## Root commands (run from the repo root, pinned Python 3.14)

Unit and tool tests, then pinned Ruff for the server tools as CI does:

    uv run --frozen --python 3.14 --project server --extra dev pytest \
      server/tests/unit tools/ci/tests tools/fixtures/tests tools/hermes_builds/tests \
      tools/vectors/tests tools/acceptance/tests -q
    uvx ruff==0.16.9 check --config server/pyproject.toml server tools

The full lane writes only under `--out`. Choose a fresh output directory for every run:
reusing one deletes its previous receipt and integration evidence. A final receipt needs
`--upstream-source`; the label must not be a default fixture build label. Replace the
`<fresh-out>` placeholder before running:

    export HMP_HERMES_BUILDS_DIR=/private/tmp/hmp-approval-matrix-builds
    python3 tools/compat/approval_matrix.py \
      --builds-dir /private/tmp/hmp-approval-matrix-builds --label approval-main-ac0 \
      --expected-source-sha ac0cfa7db94cefa90cf3e35191f38b53888b9e17 \
      --upstream-source /private/tmp/hermes-approval-ac0 \
      --out <fresh-out> \
      --receipt-out <fresh-out>/approval-fixture-receipt.json

Stage-by-stage debugging: `--only boundary,behavior` runs those stages and never writes the final
receipt (no `--upstream-source` needed). `--timing-repeats N` bounds the timing probes (default 5
cold, 200 cached calls).

## Evidence to record after the run

- [ ] Amendment-1 unit/tool tests and pinned Ruff on the current diff (root).
- [ ] Matrix JSON, junit XML, `logs/collect.log`, per-stage logs, PIDs and before/after
      fingerprints (approval, read, direct-send) from the swap test, plus admitted-start evidence.
- [ ] Timing (cold/cached) as local evidence only.
- [ ] Any failure with its log tail, reported as a failure.
