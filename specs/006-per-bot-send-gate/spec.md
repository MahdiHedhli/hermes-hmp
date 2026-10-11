# Per-bot send availability

Status: focused draft fix for a confirmed named-profile send refusal. No live-host change.

## User outcome

An owner sees whether each Bot Chat can accept a message before typing or sending. If a profile lacks its own API server key, that bot's composer is read-only while another correctly configured bot can still send. A failed send remains reviewable on the phone.

## Requirements

- HMP reports Bot Chat send availability for each authorized served profile in the roster. Earlier clients may ignore the additive field.
- Availability requires the owner send switch, any configured build qualification, a loopback-only endpoint, and the target profile's usable key. The actual route rechecks all conditions before submission.
- The owner switch applies even when Hermes advertises its full write guarantee. Its off state must make no endpoint or Hermes call.
- Do not disclose key presence for an unauthorized bot, key values, endpoint addresses, exception text, or message content.
- The roster's existing instance-wide gate stays conservative for older clients: it closes when any authorized bot cannot send.
- A port becoming unreachable after roster read remains a send-time failure, never proof of acceptance.

## Acceptance

Tests cover a missing named-profile key, profile A→B→A isolation, owner switch off on both full and guarded builds, qualification failure, unauthorized-bot omission, conservative old-client fallback, and a successful full-guarantee send with the switch on. No test touches the owner's live Hermes.

## Out of scope

Changing host secrets, probing ports during roster reads, automatic retries, and enabling draft Cron, model, or approvals routes.
