# Approval and app-pin integration: source and test evidence

Date: 2026-09-30. Status: integrated candidate, frozen for independent review after the first local
draft `821ddcb`, the root-only routing addition and the CI/documentation corrections below. Nothing here qualifies, admits or
packages a Hermes build, and no live host, device, bot or provider was touched.

## Inputs

- Tested approval revision `f4730ebb901933f34c69c609e718f3984c6e62d9`.
- App HMP pin `0f02af0760972345f41c3cd4e9a3bd1f762f1721`, merged with `--no-commit --no-ff`.
  Merge base `be94121bde3e36a28987e09215343b88865fb132`.
- New-profile routing command, source `4e270f0201e6825d90f0cae998d4522db13a2292` (final,
  independently reviewed root-only form). It is not an ancestor of the pin; the pin has no
  `routes.py`. Its branch is **not** merged. In that branch `routes.py` is a modification of an
  earlier module; here it is added as a new module. It is brought in by exact-tree `git show`
  only (see "New-profile routing" below).

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

## New-profile routing (added after the first draft)

Taken byte-for-byte from `4e270f0` (verified with `cmp` against `git show`):

| File | SHA-256 |
| --- | --- |
| `server/hmp_plugin/routes.py` | `2ec01ae90e0641d3f26584eb324e76bde97ac9ec8acd03fbce55259c610b3fab` |
| `server/tests/unit/test_routes.py` | `5aaffe81d83cf752ee66e709d7d63bea913f038fe28e4a0d19b7cf4b876fc20f` |
| `specs/005-new-profile-routing/spec.md` | `cfe1ef673ee95f0f799ef910f3fa059ee21e1a0071cb74b140ebb017988fdcf3` |
| `specs/005-new-profile-routing/plan.md` | `631d13f7fa9caa7a1e4fcc384210f7776c3343510cd2f2246a19bcfa863de0e8` |
| `specs/005-new-profile-routing/tasks.md` | `eb13723a34044d2d2915176e135e5709b2929a26bb2b610ed6047db7fb7f7597` |
| `specs/005-new-profile-routing/REVIEW.md` | `748e85fbe5b5f44f310b8b91593523b83f44a6cbea6c7213222f2ee5c63671e7` |

Hand-merged into the current files (not copies): `server/hmp_plugin/cli.py`
(`e9458bce4956077bcbcd6aad91a1ce1fea7d0bf9f4f500059e481404486c5d2a`). Added only the `routes add`
parser, `("routes", "add")` in `MUTATING_COMMANDS`, a `_resolve_custody` helper, `_cmd_routes_add`,
its dispatch branch (TTY and `HERMES_SESSION_*` refusal first) and the usage text. Setup, health,
controls, approval and every other command are unchanged. The final CLI's other differences
(older compat output, launcher tests) were not carried.

Also changed, from the same source: `PyYAML>=6,<7` in both `plugin.yaml` files, `pyproject.toml`
(moved from dev to runtime) and `uv.lock`; `tools/ci/check_plugin_surface.py` allows `yaml` in
`routes.py` only (lazy import); `test_plugin_surface.py`, `test_skeleton_layout.py` and `test_cli.py`
hunks for those (routes in the mutating set, PyYAML declarations). `test_cli.py` was edited, not
replaced. Docs: `docs/INSTALL.md` and `server/DEPLOYMENT.md` gain "a bot created after
installation" sections with root-route-only semantics; the `server-modules.md` contract lists
`routes.py` and the two single-module third-party imports; `specs/README.md` indexes
`005-new-profile-routing` by full name without renumbering.

Behavior: the command writes only the exact route into the root `config.yaml`, refuses unless root
`multiplex_profiles` is already `true`, never writes a profile config, and prints that the route is
on disk only and needs a gateway restart. No device approval, restart, send-key provisioning,
route hot-activation, HTTP route or agent tool. Approval and direct-send build lists are still 0
builds (46 and 34 bridge files); the read, cron and model lists and the 26/23 route tables are
untouched.

## CI bug: synthetic Git fixture on Python 3.11

CI runs Python 3.11. The four failing tests (`test_git_mode_identity_accepts_an_independent_clone_at_the_expected_sha`,
`test_archive_mode_refuses_a_git_build_and_git_mode_refuses_an_archive`,
`test_git_mode_identity_needs_the_upstream_head_to_agree`,
`test_stability_closes_on_source_drift_or_a_moved_head`) were reproduced on Python 3.11.15 with the
failure `the runner needs pinned Python 3.14, not (3, 11)`, raised at
`tools/compat/approval_matrix.py` `stage_identity`. The `git_identity_env` fixture stubbed
`approval_matrix._python_version`, which covers only the *build interpreter* probe; the runner's own
`sys.version_info[:2] != PINNED_PYTHON` check was not stubbed, so these synthetic identity tests
never reached the Git boundaries they state to test.

Fix (test file only, `tools/fixtures/tests/test_approval_git_fixture.py`): the fixture now also
replaces the module-local name `approval_matrix.sys` with a shim (`RunnerSys`) that reports the
pinned version and delegates everything else to the real `sys`; the real `sys` is not modified. A new
separate test, `test_runner_refuses_an_unpinned_python`, overrides the fixture's pinned shim with (3, 11) and
asserts the production refusal. `approval_matrix.py`, `PINNED_PYTHON`, the minimum runtime and CI
are unchanged. No test of the 3.14 refusal existed before; that test is new.

Outcomes: file `test_approval_git_fixture.py` 4 failed / 61 passed before on 3.11; 66 passed
(65 + the new test) on 3.11.15 and on 3.14.6 after. Full CI suite on 3.11.15 (`/private/tmp/hmp-app-parity-venv`, same six test directories, run with `-c server/pyproject.toml --rootdir=.`): 1850 passed, 15 skipped, 0 failed, 1 existing warning (3.14 count 1851 + 13 skips predates the new test and differs in skips by interpreter).
Limit: this exercises the synthetic Git fixtures only; no real Hermes build, venv or approval matrix ran.

Root repeated the actual CI command with `uv run --frozen --project server --extra dev` in a fresh,
isolated Python 3.11 project environment after the repair: **1850 passed, 15 skipped, 0 failed**.
One existing aiohttp test-subclass deprecation warning remains. This verifies the committed lockfile
and the CI interpreter together; it does not run native approval fixtures or admit the candidate.

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
  tool suites had 4 failures in `tools/fixtures/tests/test_approval_git_fixture.py`. An earlier
  note dismissed them as an environment mismatch; that was wrong. They were a CI bug (see
  "CI bug: synthetic Git fixture on Python 3.11" below), now fixed.
- Python 3.14 environment with the same dependencies: CI unit and tool suites
  (`server/tests/unit`, `tools/ci`, `tools/fixtures`, `tools/hermes_builds`, `tools/vectors`,
  `tools/acceptance`) 1708 passed, 13 skipped, 0 failed.
- New tests: a controls grant alone cannot reach any approval route; a controls denial closes an
  allowlisted approval device.
- `check_plugin_surface`: OK. `scan_logs`: nothing captured to scan. `scan_private`: clean.
- Integration tests (`server/tests/integration`, 136) were only collected, not run.

### Tests after the routing addition (Python 3.14.6, `/private/tmp/hmp-approval-matrix-venv`)

- Ruff 0.16.9 (`uvx`), CI command: all checks passed.
- Routes, CLI, one-shot CLI, plugin-surface and skeleton tests: 370 passed.
- CI unit and tool suites, same set as above: 1851 passed, 13 skipped, 0 failed (prior 1708; the
  difference is `test_routes.py` and the new surface tests).
- `check_plugin_surface`: OK. `scan_private`: clean.
- `scan_logs` on the pytest output reported 858 findings, all redacted fragments of test names and
  paths in verbose pytest output; the log is a 0600 scratch file outside the repository. It is not
  a fixture or gateway log and is not evidence of a leak or of cleanliness.
- Not run: the approval matrix, native fixtures and integration tests.

## Deployment documentation correction

`server/DEPLOYMENT.md` previously still told operators to set `gateway.multiplex_profiles: true` in
every served profile's own config and had a checklist line for it. The final reviewed `4e270f0`
deployment text, the 005 spec/history and Hermes source at
`ca705dbf7ef86425b381b542712aff310f1ee52c` (read-only `git show`: `hermes_cli/profiles.py`
`profiles_to_serve`, `gateway/session_recovery.py` `_resolve_profile_for_key`) show: root
multiplexing is the routing prerequisite; a multiplexing root serves live named profiles without the
profile's flag; the flag selects the session-key namespace, so changing it changes history
namespace. Now documented in place: root prerequisite; the profile flag is neither required nor
written; the dated older-fixture observation (`04fa849e70`, `7e8c8f07a1`) is kept with its limits;
the checklist now says not to add it. Not claimed: that route-only preparation makes an older
standalone profile's existing history canonical or readable. History readability of a flag-less
profile on `ca705` remains an open integration item. The Hermes `8afaab3703` topology notice from
the approval line is kept.

## Boundary-tool repair after the first failed native matrix

First native matrix on `ffe55bb` (`approval-dogfood-8afa-git-public`, Git install): identity **true**,
boundary **false**, no receipt, nothing admitted. The failure was in the checker, not in the product:

1. `tools/compat/bridge_files.py` mapped `fastapi` (lazily imported in `HermesApi.write_profile_model`
   only to recognise the native writer's validation refusal) to a Hermes source file. `fastapi` is now
   classified as an external, non-Hermes package alongside the plugin's runtime packages. That is a
   classification, not an attestation of the installed package.
2. With that fixed, the direct-send check reported 6 AST files missing. The tool's AST walk covers all
   of `bridge.py`, and all 6 modules are imported only inside four `HermesApi` methods: `model_config`
   (`hermes_cli.config`), `write_profile_model` (`hermes_cli.web_routers.profiles`),
   `create_mobile_cron` (`cron.scheduler`, `tools.cronjob_prompt_scan`) and `edit_mobile_cron`
   (`cron.jobs`, `cron.lifecycle_guard`, `cron.scheduler`, `tools.cronjob_prompt_scan`). Traced callers:
   they are reached only through `HermesReadBridge.profile_default_model` / `set_profile_default_model` /
   `create_mobile_cron` / `edit_mobile_cron`, which `server.py` calls only from the model and cron route
   handlers, behind `model_qualified` / `cron_qualified`. None of the 6 modules is in the READ, DIRECT or
   APPROVAL dependency tuples, and no read, direct-send or approval path reaches them. The separate
   read/direct/approval vs cron/model qualification boundaries are kept: neither the 34-file direct list
   nor the 46-file approval list was extended.

Scoped checker change (`tools/compat/bridge_files.py` only): an audited, exact
`(class, method) -> (feature manifest, modules)` table, `FEATURE_METHOD_IMPORTS`, and a scope-aware
import visit. An import is feature-classified only at one of those four method sites and only for a
listed module. Each classified module must map to a real Hermes source file (path lookup, nothing
imported) and that file must be in its own feature's `bridge_files` (`mobile_model_supported_builds.json`
or `mobile_cron_supported_builds.json`); an unreadable or malformed manifest, a missing file or an
uncovered file fails. The same module anywhere else (another method, a nested function, another class,
module level) stays in the target AST set. A module in the selected target's own typed
READ/DIRECT/APPROVAL tuple is never feature-classified. An unmapped unknown import still fails as
before. The READ-vs-DIRECT cross-target exclude and the approval superset are unchanged. The
feature results are reported under `feature:*` and are not part of the target union, so `--write`
cannot merge them into a target list.
Limit: this proves declared source-file coverage of the imports the AST scan sees. It is not a complete
call graph and not an attestation of installed third-party packages. No manifest, build list, table,
product, runtime or compat file changed.

Tests (synthetic bridge source, temporary Hermes trees and manifests; no wording assertions): own-feature
coverage verified; a file covered only by the other feature's manifest refused; missing Hermes file,
missing/invalid-JSON/non-object/bad-list manifest refused; the same modules outside the reviewed
methods (including nested, wrong class, wrong method) stay in the target set; a module not listed for
that method is not classified; a typed-tuple module is retained; the real bridge's feature set is
exactly the six modules above. The three earlier fastapi tests are kept (one assertion updated: the
native writer module is now in the model feature set instead of the target set).
`test_bridge.py`: 112 passed, 3 skipped (Python 3.14.6). Ruff 0.16.9 (CI command), `check_plugin_surface`
and `scan_private`: clean.

Real boundary check, `--check` only, never `--write`, with the 8afa build's own interpreter
(`.venv/bin/python`, `approval-dogfood-8afa-git-public/src`), `env -i`, fresh private scratch
`HOME`/`TMPDIR`/`XDG_CONFIG_HOME`/`HERMES_HOME`:

| Target | AST set | Probe set | Union | Committed | Result | Feature boundary (model / cron) |
| --- | --- | --- | --- | --- | --- | --- |
| read | 7 | 14 | 14 | 16 | pass | 2 / 4 files, all covered |
| direct send | 11 | 34 | 34 | 34 | pass | 2 / 4 files, all covered |
| approval | 11 | 34 | 34 | 46 | pass | 2 / 4 files, all covered |

The 8afa tree was not modified. This is the boundary stage only: the matrix itself was not re-run, no
native approval receipt exists, and nothing is admitted. The runtime plugin digest is unchanged:
`45a188f2450669a2bd06bf5dffb72ea5a3fada9f053b5d4eda6548b15e87dfe3`. A fresh native matrix is still
required after independent review of this checker change.

## Limits

- No real Hermes fixture, gateway or approval matrix ran. Integration with real Hermes is not
  evidenced by this document.
- Source digest of `server/hmp_plugin` after the routing addition (sorted path plus per-file SHA-256,
  excluding bytecode): `1d979a54979de4a5fdd5a48afa0cdf12d6e505d2b35dc7c77ea029d38cbb517c`
  (before it: `4c98c994ccddba311631e5b13ec2e532ce66225830dc6a9b78c73111ea0a7fd8`). It describes
  this working tree and is not a package digest.
- The actual `approval_fixture.plugin_source_digest` algorithm (relative path, length and raw
  bytes, not the per-file-hash census above) gives
  `45a188f2450669a2bd06bf5dffb72ea5a3fada9f053b5d4eda6548b15e87dfe3` for this candidate.
  The earlier `f4730eb` receipt does not bind this digest. A fresh native matrix is required after
  independent review; no supported-build entry was promoted.
- `hermes hmp routes add` was exercised only by the unit tests against temporary homes. It was not
  run against a real Hermes home, gateway restart or phone request, and the route's effect in a
  running gateway is not qualified here.
- Device acceptance of the approval card is still open. Historical receipts do not qualify this
  integrated revision.
