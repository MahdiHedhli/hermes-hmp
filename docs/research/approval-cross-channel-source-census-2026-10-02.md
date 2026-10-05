# Approval notifications across surfaces — source census (2026-10-02)

Static inspection binds to Hermes `ca705dbf7ef86425b381b542712aff310f1ee52c`,
HMP relay contract `92a719f303fa5ef9f1e542089a70118924e1ce89`, and accepted HMP
notification-input source `6a139bae6646eb6e7584336c94ef611609833fe3`.
Twenty source/contract inputs were hash-checked without changing the source.
This is not runtime loading, card rendering, answer, push or deployment evidence.

## Existing Hermes observer seams

Hermes already declares `pre_approval_request` and `post_approval_response`
[observer hooks](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/hermes_cli/plugins.py#L144).
They actually fire around the
[interactive CLI prompt](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/tools/approval.py#L907)
and [shared gateway wait](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/tools/approval_gateway_wait.py#L197).
Return values cannot veto or answer. A loaded subscriber can observe these events
without a new generic approval callback. The hooks are synchronous and outside
[the callback-timeout allowlist](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/hermes_cli/plugins_dispatch.py#L24);
any notification consumer must use a bounded, nonblocking handoff, not perform
network delivery in the callback.

## Surface coverage

| Surface | Source path and current HMP boundary |
| --- | --- |
| HMP Bot Chat | Session-chat approval events become HMP `bot_chat` prompt rows. The accepted 015 insertion/settlement/visibility seam is present; no push consumer is registered. |
| HMP Phone chat | Active HMP adapter maps an exact pending request for its bound session into a `phone_chat` row. This is adapter-local, not a subscription to every platform. |
| Desktop/TUI | TUI registers its own gateway notifier and resolves its own queued exact request. The shared approval wait also fires plugin observer hooks; HMP's adapter does not own the TUI renderer or answer route. |
| Interactive CLI | Existing hooks fire, but loading the HMP subscriber in the actual CLI process has not been demonstrated. No HMP prompt row is created by that path today. |
| Other gateway platforms / API runs | The active adapter or per-run callback presents the approval. Shared observer hooks can support a loaded plugin; HMP's adapter-local callback alone does not cover other adapters. |
| Cron | Unattended context applies `approvals.cron_mode` automatic approve/deny policy rather than an answerable human prompt. Alerts for these decisions need a separate event/product requirement. |
| Clarify | A separate callback and prompt kind; do not count it as dangerous-command approval coverage. |

The native gateway's [per-session notifier](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/run_turn_runner.py#L1684)
uses the active adapter. [API runs](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/gateway/platforms/api_server_runs.py#L850)
have their own event callback. [Cron context](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/tools/approval_context.py#L127)
is distinct. These are creation/observation paths, not authority grants.

## Remaining work and gap classification

No generic `HERMES_API_GAP` is established. HMP needs a reviewed consumer and
process-loading evidence before claiming broader notifications. An observer hint
is insufficient for durable prompt identity, generation, visibility, freshness,
settlement reconciliation or a cross-surface answer. If the product needs a
common Hermes-owned lifecycle rather than observer-only alerts, define that
primitive precisely before claiming it is absent.

The loader's [bundled-platform deferral](https://github.com/NousResearch/hermes-agent/blob/ca705dbf7ef86425b381b542712aff310f1ee52c/hermes_cli/plugins_discovery.py#L289)
is conditional on bundled origin; it does not prove all external platform plugins
are deferred. Actual CLI process topology remains an evidence gap. The existing
014 alert scope remains HMP Bot Chat and Phone-chat rows. No contract, owner
choice, runtime feature, live authorization or push capability changes here.
