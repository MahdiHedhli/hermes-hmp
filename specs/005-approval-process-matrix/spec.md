# Approval process qualification matrix (draft test tooling)

Status: draft test/qualification tooling. Approvals stay unreleased and closed: the public
`approval_supported_builds.json` remains empty and nothing here promotes a receipt to it. This spec
is the frozen architecture decision for the slice; changing it needs a new spec revision.
Amendment 1 (`amendment-1-safety-review.md`) records the later review rulings on copy safety,
receipt tightening and lifecycle evidence; it does not change the architecture below.
Amendment 2 (`amendment-2-git-install-fixture.md`) covers the independent Git-install fixture.
Amendment 3 (`amendment-3-native-start-readiness.md`) makes the fixture's native listener wait
process-aware (same 45 s deadline) and records start timing; it is tooling only and leaves the
startup-delay cause unresolved.

## Problem

Spec 004 wired a fail-closed, process-latched approval gate and proved it with unit tests against
an empty manifest. Nothing could yet open it on a real Hermes, so the lane was closed by
construction, not qualified. The previous fixture receipts (`hmp-approval-matrix-results-4`)
predate the gate wiring and qualify nothing about the current diff.

## Decisions (frozen)

1. Separate lane and runner. `tools/compat/approval_matrix.py` is a small sibling of
   `run_matrix.py`. It reuses `direct_send_entry`, `integration_report_passed`,
   `resolve_source_sha` and the existing probe scripts. `run_matrix.py`'s read and direct-send
   targets stay independent; the direct-send target stops selecting `test_approvals_fixture.py`
   because approvals are no longer part of that lane.
2. Provisional entries only in a disposable fixture plugin copy. `tools/fixtures/approval_fixture.py`
   writes a fixture-only entry into `<fixture>/_hmp_plugin/approval_supported_builds.json` after
   exact boundary/import and behavior probes. The entry covers that manifest's own ordered file
   list and the current source fingerprint. The public manifest stays empty.
3. A direct-send receipt alone never opens approvals. Each lane has its own installer, environment
   knob and manifest file. `HMP_DIRECT_SEND_QUALIFICATION` never touches the approval manifest and
   `HMP_APPROVAL_QUALIFICATION` never touches the direct-send one. Both knobs are read only by
   fixture tooling (`direct_send_fixture.build_offline`); the plugin runtime never reads them.
4. Receipt validation uses the runtime schema (`hmp_plugin.compat.load_read_compat_list`) plus bound
   identity. It rejects an absent, wrong, malformed, stale or cross-build receipt: format, ordered
   file boundary equal to the target manifest, exactly one entry, label, recomputed fingerprint
   over the approval files, `git_sha` null (extracted archive), and for a final receipt the
   plugin source digest, all-stages-passed evidence and non-provisional provenance.
5. Pinned inputs are read-only: upstream archive `ac0cfa7db94cefa90cf3e35191f38b53888b9e17`,
   original source, the pinned Python 3.14 interpreter and the extracted build. Any source
   mutation happens in a fresh copy under the run's scratch output whose venv finder and shebangs
   are rewritten to the copy and verified to import from it. Originals are never written.
6. Real gateway lifecycle, not a simulation. Full gateway process restarts (new PID) are done with
   the existing fixture. Listener-only reconnect has no public daemon path, so it is exercised by
   a test-only subprocess (`approval_reconnect_harness.py`) in the build interpreter that drives the
   real `adapter.open_components` twice in one process. A full restart is never claimed to
   prove listener-only behavior, and the reverse.
7. Required JUnit selection is explicit. The runner passes explicit node IDs, then checks the
   report: the set of test IDs equals the required set, all passed, none skipped/failed/errored,
   and the count is non-zero. The final receipt is written only after every stage passed and the
   source fingerprints (read, direct-send and approval) and plugin digest are unchanged from
   before the first stage.
8. Synthetic only. Synthetic credentials, homes and XDG roots, a loopback fake model, the real
   gateway and PTY pairing. The fake-model dangerous command targets only a per-test sentinel.

## Required proof

| Area | Evidence |
| --- | --- |
| T7 Bot Chat | exact-ID approve (executes), exact-ID deny (does not), no card when desktop-held, replay opens no second stream |
| T8 Phone | approval, clarify with Other + text, unknown ID 404, phone text and slash input never resolve a pending approval |
| Waits | gateway restart mid-wait does not apply; in-process interrupt and timeout waits fail closed (Hermes probe) and a real short-timeout wait expires without running the command |
| Cross-profile | same-device answer through the other profile is refused and does not settle |
| Refusals | owner, flag, direct-send list, approval list each close AP-3/4/6 on real routes |
| Empty-start lifecycle | full gateway with an empty approval manifest: reads and ordinary guarded send work, AP-3/4/6 closed; installing the entry in the same process stays closed; a full restart (new PID) opens AP-3 and a real approval round trip works |
| Admitted-start lifecycle | removing the entry closes the next request even with a cached probe; restoring the same startup entry can reopen |
| In-place swap | in a disposable copy, swap an approval-only file (outside the read fingerprint) plus a matching new entry: closed while the same PID runs, open only after a full restart; before/after fingerprints and PIDs recorded |
| Listener reconnect | in one process, a reconnect never reopens a baseline that started closed and never redefines it |
| Timing | cold and cached qualifier timing at the real pinned source, bounded repeats, reported as local evidence only |

## Explicit limits (not claimed)

- No memory attestation: already-imported modules are not re-verified; unload/reimport is not defended.
- The fixture build is an extracted archive with no `.git`. The git-SHA branch of the gate is covered
  only by the existing unit tests; there is no git-install gateway lifecycle here. The receipt
  records `git_lifecycle: not_covered`.
- Timing is a local measurement on one host, not a performance guarantee.
- No physical device, release or security clearance. Receipts are never committed or promoted.
- Restart-mid-wait proves the row and queue are lost on process death; it is not an in-process
  interrupt through HMP (no such route exists). The in-process interrupt is proven at the Hermes
  level by `approval_probes.py`.

## Out of scope

Behavior changes to the plugin, the committed manifests, live Hermes homes, network extraction, and
dependency upgrades.
