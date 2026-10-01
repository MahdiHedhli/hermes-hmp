# Feature specs

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
| `003-approvals` | Approval and clarify draft (§7b) |
| `004-approval-qualification-lane` | Independent approval qualification gate |
| `004-mobile-cron` | Owner-gated scheduled jobs (§7c) |
| `005-approval-process-matrix` | Real-process approval matrix tooling |
| `005-new-profile-routing` | Root route for a bot created after install |
| `005-bot-default-model` | Owner-gated bot default model (§7d) |
| `006-per-bot-send-gate` | Per-bot send status |
| `006-phone-send-refusal` | Phone-send typed refusal |
| `007-host-setup-check` | Read-only host setup check |
| `008-bot-health-check` | Read-only bot channel health |
| `009-owner-pairing-controls` | Per-device jobs and model controls decision |
| `010-bot-chat-history-start` | Bot Chat history paging (SES-2a) |

Per-bot send, per-device controls, and approval gates are separate: a controls grant never opens an
approval route (see `docs/architecture/contracts/HMP_V1.md` §7b). A future owner-admission spec
should use an unoccupied number (`014` is currently free).
