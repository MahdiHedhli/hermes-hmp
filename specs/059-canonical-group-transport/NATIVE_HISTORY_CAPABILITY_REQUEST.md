# Required native capability: scoped group-history acquisition

## Decision and exact source

**HERMES_API_GAP — scoped to the existing canonical history route and published
plugin extension contracts.** Source-only recheck at native
`f8acc26834bf1275c34d09ccc3e51250bcd1e26b` on November16. No native handler, ticket,
room database, live host or phone was accessed. The complete Git tree is
untruncated. All56 previously pinned group/transport/extension source blobs are
unchanged from4162ecf1. The expanded137-file source inventory and116 published
import entries are bound in [history-extension-source-pins.json](history-extension-source-pins.json).
Inventory membership is not a claim that every operation in every file ran.

The required missing behavior is a supported native-owned acquisition that
checks the original remote-client member/history authorization scope in the same
snapshot as the room events it reads, with an equivalent attachment-provenance
contract. Neither current state→log composition nor the examined public plugin
surfaces provide that behavior. This is an integration prerequisite for HermesBot's
multi-device policy; native Hermes's personal-owner model is not called a bug or
a vulnerability. This document is a capability request/design input, not an
accepted native API, an upstream issue submission or permission to patch core.

## Existing capabilities that must not be overlooked

| Actual surface at the pinned source | Why it does not close this history boundary |
| --- | --- |
| Canonical `groups.log` | Its closed fields are room_id, since_seq, limit and include_disbanded (plus the common profile selector). It carries no original member/history predicate or authorizing native lease. |
| Native `read_events` | Opens its own native transaction and returns events/cursor/latest_seq/has_more/authority. Its arguments accept neither an existing read transaction nor an authorize-before-event-read callback. Current room authority is not HMP historical-member permission. |
| `ctx.register_rpc` / `emit_to_session` | Real supported plugin methods and session events. The handler receives copied params and an authorized session_id, not the original HMP permission owner or the native room read transaction. A new method name alone cannot replace the canonical read's transaction. |
| `ctx.register_hook` / middleware | Real extension registries. Tool/LLM execution middleware and incoming-message policy hooks do not surround this room-log SQL snapshot. Registering a new arbitrary hook name cannot create a native fire site. |
| `on_room_member_activity` | A real group-specific hook, not an absent API: it projects live member runtime frames through queued observers. It neither gates acquisition nor reads/replays the durable room log. Reconstructing history from it would be a shadow runtime and lose native replay semantics. |
| Public `hermes_state.SessionDB.transcript_read_snapshot` | An existing consistent SessionDB-read mechanism, not a missing snapshot facility. It pins reads through that SessionDB's read context (or validates its write generation). Native room `read_events` opens its own connector/transaction and does not adopt that context. Wrapping separate calls does not join them. |
| `ctx.platform_actions` | Consent-gated reactions/thread-title operations on live platform adapters; no native room/history transaction interface. Native plugin consent is not a phone grant. |
| Plugin state / scoped provider registrars | Own plugin storage and provider registration/replacement, not a native room-store read predicate. A registrar replacement transaction is not the room history snapshot. |

The published plugin import catalog contains116 entries and does not publish
`gateway.hosted_rooms`, `gateway.hosted_rooms_common` or
`gateway.session_hosted_service`. A module's existence or a reachable private
runner attribute is not a supported room-store extension contract. The public
adapter's runner reference is not evidence of a scoped history-read interface.
Do not join raw SQLite against private room tables, replace a core function,
forge an AuthorityConnection/native actor, borrow a Desktop/host identity or
acquire foreign history and post-filter it for the phone.

Primary pinned owners:
[canonical fields/dispatch](https://github.com/NousResearch/hermes-agent/blob/f8acc26834bf1275c34d09ccc3e51250bcd1e26b/gateway/session_group_controls.py#L37),
[native read](https://github.com/NousResearch/hermes-agent/blob/f8acc26834bf1275c34d09ccc3e51250bcd1e26b/gateway/hosted_rooms.py#L1393),
[published imports](https://github.com/NousResearch/hermes-agent/blob/f8acc26834bf1275c34d09ccc3e51250bcd1e26b/hermes_cli/data/plugin_api.json),
[plugin RPC dispatch](https://github.com/NousResearch/hermes-agent/blob/f8acc26834bf1275c34d09ccc3e51250bcd1e26b/gateway/session_plugin_rpc.py),
[live room observer](https://github.com/NousResearch/hermes-agent/blob/f8acc26834bf1275c34d09ccc3e51250bcd1e26b/tui_gateway/hosted_room_member_activity.py),
[SessionDB snapshot](https://github.com/NousResearch/hermes-agent/blob/f8acc26834bf1275c34d09ccc3e51250bcd1e26b/hermes_state_stored_reads.py#L130),
[native transaction connector](https://github.com/NousResearch/hermes-agent/blob/f8acc26834bf1275c34d09ccc3e51250bcd1e26b/gateway/hosted_rooms_common.py#L145).

## Requested generic behavior, not an invented implementation

A supported capability or extension hook should let a trusted adapter compose its
own remote-client policy with native room acquisition. Keep core generic, with no
HermesBot-specific dependency and no new model tool or implicit privilege.
Concrete API names, data types, lock ordering and callback/lease mechanics remain
for native-owner design/review; no arbitrary HTTP-supplied callable or JSON grant
is an authority object.

- HGR1: Native authenticates/owns the request and binds exact instance/profile,
  room identity and native authority generation. The adapter's original current
  device/token-family/bot scope remains distinct from native owner identity.
- HGR2: Before event bodies are acquired, native determines the complete relevant
  member/history provenance in that same read snapshot. Cover local/peer members,
  legacy adoption, replication/promotion and attachment origins; current roster
  equality alone is insufficient. Unknown lineage refuses without foreign data.
- HGR3: Evaluate the original authorized scope at that boundary. Define ownership,
  expiry/deadline, cancellation and revocation ordering explicitly; a copied list
  or second state check is not automatically a permission lease.
- HGR4: Return an immutable bounded page with its authoritative snapshot identity
  and a defined publication-validity/retirement contract. HMP must fence current
  rights and old-generation output before exposing it, retaining debt/cleanup on
  uncertainty. Do not claim that response fields alone close lifecycle ownership.
- HGR5: Preserve complete native pagination, durable event IDs, authority lineage
  and attachment semantics. No smaller attachment cap, omitted history or live
  observer reconstruction may substitute for the complete requested feature.
- HGR6: Explicit authorization precedes resource-specific diagnostics. Unrecognized,
  revoked or foreign scope must not reveal rooms, members, counts or content.
  Missing service/capability is distinguishable only within an authorized scope.
- HGR7: Advertise the actual optional capability and negotiate its supported
  contract; check API/dependencies/security gates. Do not introduce version
  equality/qualification allowlists or reject newer/unknown versions solely for
  lacking a test entry. Existing owner-only/native clients retain their behavior.

## Acceptance needed before product wiring

Exercise a real native temporary store/driver through the supported path, not a
fake authority or SQL clone. Causal tests must cover missing/partial/foreign and
revoked bot rights; wrong device/family/instance/profile; member/lineage changes
before and during acquisition; legacy/replica and attachment provenance; denied
reads that never acquire event bodies; full pagination; cancellation/revocation
and late publication; lost/unknown cleanup and reconnect without budget reset.
A separate true-control case must still retrieve all authorized native content.

HMP's explicit phone group grants, native connection/process identity, full frame/
decoder accounting, worker ownership and mobile UX remain independent open tasks.
The existing ledger/codec/socket Linux component results are not transferred to
this newer native source or to room authority. Source metadata is not deployment
or current-phone qualification. Complete group chat remains the target; an
informational browser is not substituted for creation, messaging or member control.
