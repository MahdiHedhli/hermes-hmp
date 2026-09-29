# Hermes Unified Gateway Research

**Research date:** September 28, 2026

**HMP implementation checkpoint:** the phone already persists a UUIDv7
`client_message_id` before a Bot Chat send, treats ambiguous outcomes as
unconfirmed, and uses an authoritative snapshot when its current history
window resets. Those safeguards do not constitute a `SessionAuthority`
admission receipt, durable FIFO, or canonical event replay. Reuse the existing
parts where their semantics match; do not label a legacy mailbox `queued`
result as a unified-gateway admission. The [roadmap](ROADMAP.md) sets the
resulting investment priorities and adoption gates.

**Primary sources**
- https://github.com/NousResearch/hermes-agent/pull/106742
- https://gist.github.com/unsupportedpastels/765f9d551ce88ee01630c18367763e75

## Executive summary

PR #106742 is a major Hermes runtime architecture change. Its goal is to stop individual surfaces such as CLI, TUI, Desktop, API, bots, cron, and messaging integrations from independently owning conversations and execution state. Instead, those surfaces converge on a profile-scoped canonical `SessionAuthority`.

The authority owns session creation, durable prompt admission, FIFO ordering, execution, controls, recovery, and canonical state transitions.

The companion Gist, **"One Gateway: Entry-Point and Session Ownership Plan,"** is the follow-on architecture plan. It acknowledges that PR #106742 does not complete the migration for every entry point, particularly standalone `hermes serve`, remote Desktop, browser clients, and other remote callers.

Most importantly for Hermes Bot Mobile / HMP, the Gist explicitly includes a **future mobile client** in the target architecture:

```text
Desktop        Web        TUI / CLI        Future Mobile
    \           |             |                 /
             Authenticated Gateway API
          discovery / attach / events / controls
                         |
             Profile-scoped SessionAuthority
          sessions / FIFO / execution / recovery
                         |
                   Agent execution
```

This closely matches what HMP needs. The phone should be a remote viewer, submitter, and controller. It should never become the owner of the Hermes session or agent process.

The important caveat is that the clean authenticated remote entry point Mobile needs is not fully delivered yet. HMP should adopt the canonical gateway semantics now, while avoiding freezing today's legacy `hermes serve` behavior as our permanent mobile protocol.

## 1. Why Hermes is doing this

Hermes has accumulated many entry points. If multiple surfaces can independently host a session runtime against the same state, they can compete over queueing, execution, mutation, recovery, and persistence.

The old shape can become:

```text
Desktop -> runtime --\
CLI ----> runtime ----> shared state
API ----> runtime --/
```

The target is:

```text
Desktop --\
CLI -------\
API --------> canonical gateway/session authority -> agent execution
Mobile ----/
```

Clients become consumers of the authority instead of session owners.

## 2. SessionAuthority

A central implementation is `gateway/session_authority.py`.

Conceptually:

```python
submit(actor, request):
    authorize(actor, session, "session:submit")
    persist_durable_admission(request_id, payload)
    publish_pending_state()
    schedule_fifo_drain()
    return admission_receipt

drain(session):
    if any_admission_is_unknown:
        pause_fifo()
    claim_next_queued_admission()
    execute()
    settle_durable_outcome()
    publish_completion()
```

Submission and execution are separate. A successful submit means Hermes accepted durable work. It does not mean the originating client must remain connected until inference completes.

That is ideal for mobile.

## 3. Durable FIFO admission

The queue belongs to Hermes, not the UI.

```text
Prompt A -> running
Prompt B -> queued
Prompt C -> queued

Phone disconnects

A finishes
B runs
C runs
```

HMP should therefore avoid a synchronous chatbot model where Send is disabled until Hermes finishes. The app should eventually expose authoritative queued, running, and completed work.

## 4. Request identity and lost acknowledgements

Mobile networks fail at inconvenient moments:

```text
Mobile -> submit
Gateway accepts
Gateway -> ACK
        X connection dies
```

The phone cannot know whether Hermes accepted the task. A naive retry can execute it twice.

HMP should generate and persist a `request_id` before transmission:

```text
User taps Send
 -> generate request_id
 -> persist request locally
 -> submit
 -> receive admission_id
 -> persist admission_id
 -> observe authoritative state
```

If acknowledgement is lost, retry using the same request identity.

## 5. `unknown` is a first-class execution state

Suppose Hermes invokes an external tool and the gateway crashes before recording whether it completed. Retrying automatically may duplicate an external side effect.

The architecture therefore distinguishes:

```text
queued
started
terminal
unknown
```

When execution becomes `unknown`, later FIFO work can be paused until ambiguity is resolved.

HMP must not render this as a generic failure with blind Retry. It needs dedicated UX explaining that the result is uncertain and retrying may repeat an action.

## 6. Multiple clients, one canonical session

The target architecture allows multiple clients to attach to the same session:

```text
              SessionAuthority
             /       |        \
           TUI    Desktop    Mobile
```

Detaching one viewer does not terminate execution.

This enables a key HMP workflow:

1. Start a long task from Desktop.
2. Leave the computer.
3. Open Hermes Bot Mobile.
4. Attach to the same canonical session.
5. Watch progress.
6. Answer clarification or approval requests.
7. Stop or redirect work.
8. Return to Desktop later.

There is still one execution authority.

## 7. Replay and snapshot recovery

Mobile apps cannot assume a permanent WebSocket. iOS and Android suspend applications, networks change, and Tailscale reconnects.

The gateway design uses replay epochs and event sequence watermarks. On reconnect, HMP should attempt incremental replay. If the replay window is no longer available, it should fetch an authoritative snapshot.

```text
Reconnect
  |
validate installation/profile
  |
replay available?
  | yes -> replay missing events
  | no  -> fetch authoritative snapshot
                |
                + preserve unsent local drafts
                + replace server-owned state
```

Replay gaps should be normal mobile behavior, not exceptional failures.

## 8. Revision and execution-generation fencing

HMP needs to track two concurrency concepts.

**Revision** protects session mutations. If Desktop changes revision 41 to 42, a stale Mobile mutation based on revision 41 should be rejected instead of overwriting newer state.

**Execution generation** protects runtime controls. A delayed Stop intended for generation 17 must not kill a newer generation 18.

Generation fencing applies to Stop, approval, clarification, cancellation, interruption, and ambiguous-execution resolution.

## 9. Profiles and multiple Hermes installations

The architecture is profile scoped and uses a multiplexer rather than assuming one daemon per profile.

HMP identity should therefore look more like:

```text
Hermes Installation
  -> Profile
      -> Session
```

This maps naturally to HMP's requirement to pair with multiple independent Hermes deployments and explicitly switch between them.

## 10. What the Gist adds

PR #106742 builds much of the canonical runtime foundation, but the Gist explains the remaining entry-point migration.

Its staged direction is approximately:

1. Inventory existing `serve` callers.
2. Establish behavioral acceptance tests.
3. Prove the smallest `serve` to canonical-owner connection.
4. Route conversational HTTP/WebSocket behavior through SessionAuthority.
5. Align remote Desktop and browser lifecycle.
6. Revalidate other producers.
7. Remove the alternate session host after parity is demonstrated.

The Gist explicitly positions future Mobile behind the authenticated gateway API. For HMP, this is arguably the most important upstream design document.

## 11. Recommended HMP architecture

```text
Hermes Bot Mobile
 |
 +-- Instance/Profile Resolver
 +-- Authentication
 +-- Canonical Gateway Client
 +-- Session Sync Store
 |    +-- replay epoch
 |    +-- event sequence
 |    +-- revision
 |    +-- execution generation
 +-- Durable Submission Tracker
 |    +-- request_id
 |    +-- admission_id
 |    +-- queued/running/unknown/terminal
 +-- UI
      +-- chat
      +-- queue
      +-- approvals
      +-- clarifications
      +-- controls

              |
              v

     Authenticated Hermes Gateway
              |
       Profile Multiplexer
              |
       SessionAuthority
              |
         Durable FIFO
              |
       Hermes execution
```

## 12. Authentication and Tailscale

Local Desktop can use local-machine authentication mechanisms that do not translate directly to a phone.

The remote model should be:

```text
Device pairing/authentication
 -> authenticated Hermes gateway
 -> explicit Hermes profile
 -> SessionAuthority
```

Tailscale still fits perfectly. It provides reachability and transport-level device networking. Hermes authentication still provides application identity, profile authorization, and session permissions.

Tailscale access should not itself be treated as Hermes authorization.

## 13. Attachments are an important unresolved mobile API

A local client can stage a filesystem path that exists on the Hermes host. A phone cannot hand a remote Hermes machine an iOS-local path.

HMP will need a canonical remote media flow, conceptually:

```text
Mobile -> upload attachment -> Hermes media service
                             -> media_id/digest

prompt.submit
  attachments: [media_id]
```

The exact upstream contract is not settled. HMP should avoid inventing a permanent incompatible upload protocol before the canonical remote gateway interface stabilizes.

## 14. Background execution

This architecture solves the central mobile-agent problem cleanly:

```text
Mobile sends task
 -> gateway durably accepts
 -> Mobile sleeps
 -> Hermes continues
 -> task completes
 -> Mobile wakes
 -> replay or snapshot
 -> result appears
```

The phone does not need to keep the execution socket alive.

Push notifications can later notify HMP about completion, approvals, clarification requests, or ambiguous execution without becoming the execution transport.

## 15. Suggested HMP client state

```text
SessionIdentity
  installation_id
  profile_id
  session_id
  revision
  execution_generation

SessionSyncState
  replay_epoch
  last_sequence
  last_snapshot_revision

SubmissionRecord
  request_id
  admission_id?
  session_id
  created_at
  payload
  state:
    local_draft
    submitting
    queued
    started
    terminal
    unknown
```

The `request_id` should be persisted before network transmission.

## 16. Protocol states HMP should model explicitly

Do not collapse every server response into a generic network error.

Expected domain/protocol states include:

- `permission_denied`
- `profile_mismatch`
- `revision_conflict`
- `stale_generation`
- `unknown_execution`
- `replay_gap`
- `snapshot_required`
- unsupported capability
- incompatible protocol version

## 17. Backward compatibility

HMP will likely encounter several generations of Hermes installations. Use capability negotiation rather than assuming every server supports every feature.

Potential capabilities include:

```text
canonical_sessions
durable_admission
replay
snapshots
generation_controls
profile_multiplexing
remote_uploads
```

Do not silently fall back to creating an independent session owner if canonical mode fails. That would recreate the dual-writer architecture upstream is removing.

## 18. Upstream progress at research time

At the September 28 research checkpoint, PR #106742 was open and unmerged. GitHub reported the branch as not currently mergeable cleanly into `main`, although the exact researched head had successful top-level CI workflows.

A September 28 review also identified a significant hot-profile reconciliation issue: a profile whose adapter startup fails with `MultiplexConfigError` can remain advertised as served instead of being fully parked/unserved.

Relevant area:
`gateway/run_profile_reconcile.py`

This matters to HMP because profile discovery and routing need to reflect actual runtime availability.

The larger takeaway is that the architecture is advanced, but the remote/mobile contract is still moving.

## 19. What HMP can build now

We do not need to wait for the entire upstream migration.

Safe work to begin now:

1. Introduce a gateway capability abstraction.
2. Model Installation -> Profile -> Session identity.
3. Persist request IDs before send.
4. Model queued, started, terminal, and unknown admissions.
5. Build replay/snapshot synchronization abstractions.
6. Track session revision and execution generation.
7. Separate local drafts from server-accepted admissions.
8. Design approval and clarification UI around shared authority state.
9. Keep the network transport replaceable.
10. Build fixtures for canonical event streams and reconnect behavior.

Work that should remain adaptable until upstream settles:

- final remote authentication handshake
- exact remote endpoint discovery
- attachment upload contract
- final WebSocket/HTTP RPC shapes
- protocol/version negotiation details

## 20. HMP acceptance tests derived from upstream

Before declaring canonical gateway support production ready, test:

| Scenario | Expected result |
|---|---|
| Desktop starts task, Mobile attaches | Same canonical session and running admission |
| Mobile backgrounds mid-turn | Execution continues |
| Mobile reconnects inside replay window | Missing events replay exactly once |
| Replay window expired | Snapshot restores correct state |
| Submit succeeds but ACK is lost | Same request ID maps to one execution |
| Gateway dies mid-side-effect | Admission becomes unknown, no blind retry |
| Unknown is resolved | FIFO advances exactly once |
| Two clients answer one approval | One authoritative settlement |
| Stop targets stale generation | Newer execution is unaffected |
| Two clients mutate metadata | Stale revision is rejected |
| Profile A identity targets B | Authorization/profile mismatch |
| Profile startup fails | Profile is not advertised healthy |
| Old Hermes server | Explicit capability downgrade, no dual owner |
| Repeated background/foreground cycles | No duplicate turns |

## 21. Recommended implementation sequence

### Phase 1: protocol foundation
Build capability negotiation, instance/profile/session identity, durable request IDs, and admission-state modeling.

### Phase 2: synchronization
Implement replay watermarks, snapshot fallback, event reduction, and foreground/background recovery.

### Phase 3: shared controls
Implement revision-fenced mutations and generation-fenced Stop, approvals, clarifications, and unknown resolution.

### Phase 4: upstream remote gateway
Integrate the authenticated canonical remote entry point once its contract stabilizes.

### Phase 5: attachments
Adopt the canonical remote upload/media contract rather than local filesystem-path semantics.

### Phase 6: cross-surface validation
Exercise Desktop/TUI -> Mobile -> Web handoff, gateway restarts, ambiguous acknowledgements, profile changes, and version skew.

## Bottom line

The upstream work strongly validates HMP's architecture.

Hermes Bot Mobile should not be a thin remote terminal and should not create its own agent runtime. It should be a first-class remote client of a durable, canonical Hermes session authority.

The important mental model is:

> **Hermes owns the work. Mobile attaches to it.**

That gives HMP durable background execution, seamless Desktop-to-phone handoff, safe retry semantics, shared approvals and clarifications, reliable recovery after mobile suspension, and a clean foundation for multiple Hermes deployments.

PR #106742 provides most of the difficult runtime semantics beneath that model. The Gist describes the remaining remote-entry-point migration and explicitly places future Mobile in the target architecture.

We should align HMP with that target now while keeping authentication, uploads, and final wire-protocol details adaptable until the upstream canonical remote gateway stabilizes.

## Primary-source references

- PR #106742: https://github.com/NousResearch/hermes-agent/pull/106742
- PR files: https://github.com/NousResearch/hermes-agent/pull/106742/files
- Entry-point/session ownership Gist: https://gist.github.com/unsupportedpastels/765f9d551ce88ee01630c18367763e75
- Session authority: https://github.com/NousResearch/hermes-agent/blob/feat/unified-gateway-runtime/gateway/session_authority.py
- Runtime ownership: https://github.com/NousResearch/hermes-agent/blob/feat/unified-gateway-runtime/gateway/runtime_ownership.py
- Session events: https://github.com/NousResearch/hermes-agent/blob/feat/unified-gateway-runtime/gateway/session_events.py
- Profile reconciliation: https://github.com/NousResearch/hermes-agent/blob/feat/unified-gateway-runtime/gateway/run_profile_reconcile.py
- Desktop canonical adapter: https://github.com/NousResearch/hermes-agent/blob/feat/unified-gateway-runtime/apps/desktop/src/api/canonical-protocol.ts
- Shared gateway client: https://github.com/NousResearch/hermes-agent/blob/feat/unified-gateway-runtime/apps/shared/src/json-rpc-gateway.ts
