# Implementation plan: approvals under the minimum-version policy

Status: root-frozen D1-D8 (2026-10-01); independent source review accepted (2026-10-02).
The two prepared native samples and the exact private source package are accepted.
Target installation and physical card/answer verification remain pending. See the
[root source review record](../../docs/research/approval-minimum-policy-source-review-2026-10-02.md).

## Constitution check

| Principle | Effect |
|---|---|
| I. Hermes owns agent behavior | Hermes decides every approval; HMP forwards one exact ID through Hermes's own route or helper. Floors refuse only older declared versions; unknown and newer builds are attempted; a member closes only on its own missing API or a security check. |
| II. Device trust is explicit | Approval owner = allowlist AND no host denial; controls grants stay separate; bearer, revocation and per-bot authorization unchanged. |
| III. Public by default | No device IDs, hosts or owner evidence in tracked files. Private receipts stay out of the repository. |
| IV. Contract before code | Amend HMP v1 §7b, GU-2d and the error table, spec 013 and `specs/003-approvals/DESIGN.md` status before code. |
| V. Verify on Hermes | Fingerprints remain sampled evidence only. Fixtures use isolated homes and existing pinned builds. |
| VI. Review security findings | Conversion is new code: `SECURITY_REVIEW_REQUIRED` before any install. SD3/SD5 remain open and are not waived. |

## Integration sequence (D1a)

1. Branch from `4d6863e`. `git merge --no-ff 1bcb586`. Resolve the eight conflicts and three clean
   but wrong auto-merges with the rules below; keep approvals closed. Both suites must pass.
2. Exclusion commit: remove new-bot routing (D5), the owner package tool and its tests, the
   approval and send exact-manifest runtime code, process-latch lifecycle tests and receipt binding.
3. Conversion commit: eligibility members, gates, transport selection, bindings.
4. Operation-bound classification and binding fence.
5. Contract, spec, design and runbook amendments.
6. Tests and fixture cases; then independent focused review; then sampled candidate evidence.

### Merge resolution rules

| Path | Rule |
|---|---|
| `server/hmp_plugin/compat.py` | Keep `4d6863e` (eligibility, `probe_dependencies`, unchanged `DIRECT_SEND_DEPENDENCIES`). Drop the package's F3 rows that auto-merged into the send table, `direct_send_build_qualified`, the approval manifest, latch, cache and qualifier. The auto-merged approval lane also calls `probe_read_dependencies` and `_DEFAULT_READ_COMPAT_PATH`, which `4d6863e` no longer defines. |
| `server/hmp_plugin/bridge.py` | Clean merge, but delete the top-level `from .compat import direct_send_build_qualified` and `direct_send_qualified`; otherwise importing the bridge fails and read breaks. |
| `server/hmp_plugin/direct_send.py` | Clean merge; drop `DirectSendDeps.qualified` and its check; keep the stream consumer and approval call; restore `4d6863e`'s synchronous call for non-owner sends (D2b). |
| `server/hmp_plugin/adapter.py` | `4d6863e` availability wiring plus the package prompt store, hooks and overrides; bind approval availability from eligibility. |
| `server/hmp_plugin/request_ctx.py`, `server.py` | Clean merge; replace `approval_qualified` with eligibility-derived availability. |
| `server/hmp_plugin/cli.py` | `4d6863e` compat/issue-draft/wizard text; add the approval members through the eligibility renderer; drop the "Approval qualification (on-disk source)" line and, under D5, the `routes` group. |
| `*_supported_builds.json` | `direct_send_supported_builds.json` stays byte-for-byte `4d6863e`. Delete `approval_supported_builds.json` or keep it as non-runtime evidence (no reader). |
| `HMP_V1.md`, `DEPLOYMENT.md`, tests | `4d6863e` compatibility text, then the §7b amendment in step 5. |

## Affected modules and contracts

| Area | Planned change | Verification |
| --- | --- | --- |
| `compat.py`, `hermes_version.py` | `Feature.APPROVALS`, `Feature.PHONE_CHAT`; `PHONE_CHAT_DEPENDENCIES`; a dataclass-field spec; floors at the send floor; neutral stream-hook diagnostic | probe/eligibility unit tests; below-floor imports nothing |
| `adapter.py`, `request_ctx.py` | `approvals_available`, `phone_chat_available` (default False); `is_approval_owner_device` retained | constructor default tests (fail closed) |
| `server.py` | `_require_approvals_gate` uses flag, send, member and endpoint; `phone_chat` checked for AP-6 and `phone_chat` rows | route order and no-call tests |
| `direct_send.py` | owner-only stream selection before the lock; answer status classification | parity and status table tests |
| `bridge.py` | remove exact-gate import; binding capture and comparison | rebinding test |
| `prompts.py` | generation stamp; drop per-call `approval_qualified` thread hops | generation tests |
| `issue_draft.py`, `cli.py` | two new reportable features; diagnostic line; owner-without-controls-decision notice in `setup check` (not `devices list`, SD3 pending) | golden drafts, privacy canary |
| HMP v1 §7b, GU-2d, error table | replace "Independent approval qualification" with availability; AP-1 transport selection; AP-5 status mapping | contract table tests |
| Fixtures | replace 8 exact-gate cases with capability, generation and transport cases; fixture source only. Native fixtures are root-operated (T14). | sampled runs after review |
| Native answer (R14) | `direct_send.aiohttp_approval_call` parses a bounded JSON error code; only `409 approval_not_active\|approval_not_pending` and `404 run_not_found` are stale; every other result is unavailable and leaves the row open; `200` needs a non-bool integer `resolved` greater than zero | status table tests |
| Binding fence (R10) | closes the local Phone-chat generation, never claims native expiry, keeps `approvals` independent, and a source-bound stale stream cannot insert into a new generation | rebinding tests |

## Security and compatibility review

Trust boundaries are unchanged: phone to HMP (bearer, owner, bot), HMP to Hermes (in-process helper
or loopback route with the profile's own key). Removing the exact gate removes no authority check;
it never verified behavior and never attested loaded code. Remaining protections for Phone chat
self-approval are Hermes honoring `allow_gateway_control=False`, HMP's pending preflight and the
prompt-only answer route. These are sampled on `8afaab37` and older development builds; a future
Hermes that ignores the flag would not be detected statically (residual, documented).
