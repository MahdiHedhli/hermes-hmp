# GT1 member/history fence: current native route and extension findings

Source-only follow-up at native `4162ecf11f611400fa6e5c42d2f360188ce50b39`.
The expanded source-pins.json binds56 inspected public files. Only public source
was read: no native code/handler ran and no runtime database, host or phone was
accessed. These findings concern the
named routes, not proof that every possible supported extension is absent.

## Existing canonical composition

- `gateway/session_group_controls.py` lines117–249 dispatches native owner-scoped
  room methods. Its closed `_FIELDS` accepts no member predicate, roster digest
  or expected room revision on `groups.log`; `groups.state` is a separate call.
- `gateway/hosted_rooms.py` `read_events` reads authority/sequence and log rows
  within a native transaction. It returns no members or room revision. Native
  owner/epoch checks are not HMP per-device, token-family or bot authorization.
- Normal `create_room` reuse requires the same roster. This is not a general
  historical-membership proof: legacy adoption can add routing targets, while
  replica ingestion/promotion can combine supplied roster and retained history.
  Authority lineage is not equivalent to phone permission for that history.
- `gateway/session_hosted_service.py` `authorize_room` checks native actor subject
  ownership and native epoch. It can use a writer transaction. It does not
  evaluate the HMP device's current/previously permitted profiles.
- `groups_state_result` composes room, context and driver status separately. The
  peer-route publication lock orders routes with Disband; the inspected lock is
  not a shared phone grant/member/history snapshot primitive.
- Native attachment viewer authorization binds room/event/attachment authority;
  it does not create or validate HMP phone grants or historical-member access.

## Supported plugin RPC is not itself that fence

`hermes_cli/plugin_rpc.py` exposes `ctx.register_rpc`. This is a real supported
extension point, not a missing-method claim. `gateway/session_plugin_rpc.py`
checks native session-control authority (and an optional session), then invokes
`handler(dict(params), session_id=...)` off the gateway loop. It does not pass an
original HMP authority owner or native transaction/member snapshot to the handler.
The closed canonical group dispatch still uses its own handlers; registering a
plugin RPC does not replace their read transaction or inject a predicate into it.

Plugin-relative settings/state, hooks and capability probing in the inspected
PluginContext/mixin are not documented native room-store snapshot access. Raw
native-authenticated RPC parameters must not be interpreted as an HMP device grant.
A custom RPC name alone adds neither phone authorization nor worker settlement;
its off-loop work also requires original worker/cleanup custody before use.

## Transaction helper is present, not an injectable read predicate

`gateway/hosted_rooms_common.py` exports a `transaction(connect, db_path, *,
immediate)` helper. `hosted_rooms.py` binds `_transaction` to its own connector;
`read_events(db_path, *, room_id, since_seq, limit, include_disbanded)` opens it
internally. There is no existing connection or authorize-before-read callback in
that function's inspected signature. Opening another transaction around an RPC
or around a second call does not join that internal read snapshot. Calling raw
SQL against private room tables is not a supported substitute. Plugin registrar
replacement transactions concern registrations, not room-history snapshots.

## Implementation consequence and remaining decision

The existing `groups.state → groups.log` sequence and this supported RPC facade do
not establish the required authorize-before-history-acquisition boundary. Do not
fetch foreign history and filter it afterwards; do not reach into private native
DB/AuthorityConnection internals or forge an actor to make the composition pass.
This establishes a pinned integration-surface gap for the history operation's GT1
fence, not absence of all group APIs or a deployed vulnerability. No version
allowlist is introduced. Broader extension availability, explicit phone policy,
publication/revocation lifetime and cleanup remain open.

To close GT1, identify and review a supported native-owned operation that checks
an original HMP-authorized member/history scope in the same read snapshot, or a
supported extension hook with equivalent authority, transaction and cleanup
semantics. Its policy must cover local and peer members, routing adoption,
replicated history, attachments, revocation and publication. If no such supported
surface exists after the remaining extension/contract trace, record that precise
primitive as an upstream dependency; do not reduce the requested group feature.
Explicit phone group grants and full frame/decoder accounting remain independently
open. Transport components, source tests and native OS identity are not those grants.
