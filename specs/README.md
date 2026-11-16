# Feature specs

[Fresh historic-image Linux qualification](../docs/research/NATIVE_IMAGE_CACHE_LINUX_2026-11-16.md) is source-reviewed/prepared:
new HMP a4a157a5,13,206 source files and124 source/DATA checks. The original two
full scenarios remain, with a third full native historic-cache scenario added.
No new runtime result or deployment is claimed; older b86 proof is not transferred.

HMP uses [GitHub Spec Kit](https://github.com/github/spec-kit) conventions for collaborative changes. Each feature lives in `specs/<number>-<short-name>/` with:

| File | Review question |
| --- | --- |
| `spec.md` | What user or operator behavior changes, and what are the acceptance scenarios? |
| `plan.md` | Which modules, trust boundaries, and Hermes compatibility assumptions change? |
| `tasks.md` | What ordered implementation and verification work remains? |
| `contracts/` | Which observable wire or API contracts change? |

Start from the [constitution](../.specify/memory/constitution.md) and the [spec](../.specify/templates/spec-template.md), [plan](../.specify/templates/plan-template.md), and [tasks](../.specify/templates/tasks-template.md) templates. Write acceptance scenarios before implementation. Link security findings and explicitly mark unresolved blockers. Keep host and device evidence out of this public tree. Update [HMP v1](../docs/architecture/contracts/HMP_V1.md) and [FEATURES.md](../FEATURES.md) when a change ships.

The migrated F1 and send design notes are reference material. New work should use the structure above.

Several early number prefixes are shared by two directories. Directory names are historical and
are never renumbered; always refer to a spec by its full directory name.

| Directory | Topic |
| --- | --- |
| `000-public-migration` | Public repository migration |
| `001-connect-and-browse` | Pairing, transport, and read routes |
| `002-send-messages` | Guarded Bot Chat send |
| `003-approvals` | Approval and clarify design (§7b); historical, see 034 |
| `004-approval-qualification-lane` | Exact-build approval gate; historical, superseded by 034 |
| `004-mobile-cron` | Owner-gated scheduled jobs (§7c) |
| `005-approval-process-matrix` | Real-process approval matrix tooling; historical, superseded by 034 |
| `005-bot-default-model` | Owner-gated bot default model (§7d) |
| `006-per-bot-send-gate` | Per-bot send status |
| `006-phone-send-refusal` | Phone-send typed refusal |
| `007-host-setup-check` | Read-only host setup check |
| `008-bot-health-check` | Read-only bot channel health |
| `009-owner-pairing-controls` | Per-device jobs and model controls decision |
| `010-bot-chat-history-start` | Bot Chat history paging (SES-2a) |
| `011-local-image-serving` | Host-local generated images (§7e draft; source and native sampling implemented, delivery/activation/device qualification open) |
| `013-minimum-version-compatibility` | Minimum supported Hermes version policy |
| `015-approval-notification-inputs` | In-process insertion, settlement and visibility inputs; source accepted, push unwired |
| `034-approval-minimum-version-admission` | Approvals and Phone chat under the minimum-version policy |
| `047-canonical-group-capability-input` | Internal bounded native group advertisement DATA; not a group route, grant or complete mobile feature |

Per-bot send, per-device controls, and approval availability are separate: a controls grant never
opens an approval route (see `docs/architecture/contracts/HMP_V1.md` §7b). Spec 034 replaces the exact-build
approval gate described by specs 003-005 (approval line).

## Restore reviewed historic native image cache support — November 16, 2026

Current-source native run43926962041 passes matrix/mutation but fails the historic
case before descriptor mint; offline-XAI was not attempted. The candidate branch
omits the previously reviewed exact `image_cache` layout amendment0590f453.
Restore that exact same-profile flat-name layout, no-follow leaf and strict
historical witnesses; do not broaden arbitrary paths or search/fallback.
Targeted current tests and a new complete four-case qualification remain required.
No host, provider, grant or device changes are included in source restoration.
