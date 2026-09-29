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

Current draft feature specs: [scheduled jobs](004-mobile-cron/spec.md),
[bot default model](005-bot-default-model/spec.md),
[per-bot send gate](006-per-bot-send-gate/spec.md), and
[host setup check](007-host-setup-check/spec.md), and
[bot channel health](008-bot-health-check/spec.md). The setup-check branch
originally used `004`; this integration gives each feature a unique number.
