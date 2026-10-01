# Approval and app-pin integration: source and test evidence

Date: 2026-09-30. Status: integrated draft, uncommitted merge. Nothing here qualifies, admits or
packages a Hermes build, and no live host, device, bot or provider was touched.

## Inputs

- Tested approval revision `f4730ebb901933f34c69c609e718f3984c6e62d9`.
- App HMP pin `0f02af0760972345f41c3cd4e9a3bd1f762f1721`, merged with `--no-commit --no-ff`.
  Merge base `be94121bde3e36a28987e09215343b88865fb132`.
- New-profile fix `4e270f0201e6825d90f0cae998d4522db13a2292` is **not** an ancestor of the pin
  (`merge-base --is-ancestor` exits 1) and no patch-equivalent commit is in the pin. It adds a
  `routes.py` module that neither line has. It was not merged. The pin's own current-bot-route
  behavior is what is integrated.

## Resolved security wiring

1. **Approval owner gate stays narrower than the controls gate.** The pin's `is_owner_device`
   lets a per-device host grant (`device_owner_controls`) replace the `owner_device_ids`
   allowlist. Left shared, an explicit controls grant would have opened the AP-3/AP-4/AP-6
   routes and snapshot `open_requests`. A separate `ServerContext.is_approval_owner_device`
   now requires the allowlist entry AND no explicit host denial, and fails closed on a read
   error. The four approval handlers use it. Jobs and model routes keep the pin's decision
   order (explicit decision, else legacy list). Contract text updated in HMP_V1 §7b-§7d.
2. **Direct send requires the owner flag on every build, and the fingerprint check stays.**
   The pin's `flag_enabled`-only endpoint resolution and the approval line's qualification
   check are both kept: an off flag makes no endpoint or Hermes call, and an unqualified
   direct-send build never resolves an endpoint or reads the key. A missing endpoint is the
   pin's definitive `write_gate_closed`, raised before any idempotency reservation.
3. **Per-bot send gate** (`reported_send_gate`, roster `send_gate`) is unchanged and also
   honors the direct-send qualification result.
4. **Approval process latch, held-Desktop state and `/chat/stream` handling** are untouched:
   the pin does not modify `compat.py`, and `direct_send.py` keeps the stream consumer, bounded
   frames and run-scoped expiry. The latch is never reset by listener reconnect.
5. **Routes** are the union of the two reviewed tables (26 with session browsing on, 23 off).
   No new route was added.

## Build lists (unchanged from the reviewed lines)

| List | Bridge files | Builds |
| --- | --- | --- |
| approval | 46 | 0 |
| direct send | 34 (plus `requalification_required`) | 0 |
| read | 16 | 3 |
| mobile cron | 11 | 3 |
| mobile model | 13 | 3 |
| write | n/a | 0 |

The obsolete 18-file direct-send fingerprint is not restored. Cron and model entries are
byte-identical to the pin.

## Tests run

- Ruff 0.16.9, repo CI command: all checks passed.
- Python 3.11 locked environment: `server/tests/unit` 1343 passed, 15 skipped. The remaining
  tool suites have 4 failures that only assert the approval runner's pinned Python 3.14.
- Python 3.14 environment with the same dependencies: CI unit and tool suites
  (`server/tests/unit`, `tools/ci`, `tools/fixtures`, `tools/hermes_builds`, `tools/vectors`,
  `tools/acceptance`) 1708 passed, 13 skipped, 0 failed.
- New tests: a controls grant alone cannot reach any approval route; a controls denial closes an
  allowlisted approval device.
- `check_plugin_surface`: OK. `scan_logs`: nothing captured to scan. `scan_private`: clean.
- Integration tests (`server/tests/integration`, 136) were only collected, not run.

## Limits

- No real Hermes fixture, gateway or approval matrix ran. Integration with real Hermes is not
  evidenced by this document.
- Source digest of `server/hmp_plugin` (sorted path plus per-file SHA-256, excluding bytecode):
  `4c98c994ccddba311631e5b13ec2e532ce66225830dc6a9b78c73111ea0a7fd8`. It describes this
  working tree before any commit and is not a package digest.
- Device acceptance of the approval card is still open. Historical receipts do not qualify this
  integrated revision.
