# Feature specification: automatic preparation of new bots and access permission cards

**Status: PROPOSAL. NOT IMPLEMENTED. NOT FROZEN.** Automatic preparation and permission cards do not exist
in any build. No wire, store or grant change is made by this document. Not tested. Design and verified
source facts: `docs/architecture/NEW_BOT_HMP_ENROLLMENT.md`. Extends `specs/005-new-profile-routing/`; its
route rules R1, R5-R9 apply to every route written here.

## Problem

A bot created after install needs a manual root route and, for sending, per-bot prerequisites. Operators
should not repeat commands per bot. Access to the new bot must still be an explicit, owner-authorized
decision that is easy to give from the phone.

## Requirements

### Preparation

- **E1 Opt-in.** Nothing is prepared unless a one-time host setting (proposed
  `gateway.platforms.hmp.extra.prepare_new_profiles`) is boolean `true`. Other values are off and reported.
- **E2 Baseline and identity.** Eligibility is a one-time policy generation plus a persistent identity
  baseline recorded at opt-in, not creation timestamps. Baseline profiles need an explicit migration
  command. Inode and owner are not durable identity; an HMP policy-generation registry detects but cannot
  prove an unseen name replacement. Ambiguous names are quarantined and HMP name-keyed rows are invalidated
  through a reviewed migration; native grants are never raw-deleted (G7). No promise that no grant is
  inherited based on inode alone.
- **E3 Detection, no hook.** A qualified served-profile snapshot compared with root routes, plus a
  reconciliation fallback. No core patch, no undocumented lifecycle hook, no change to a profile's own
  `multiplex_profiles`, no history relocation. A lifecycle hook is an upstream opportunity only.
- **E4 Scoped provisioner.** Same-OS-user, not requester or client authority. Inputs come only from host
  directories and are validated.
- **E5 Route write.** Atomic, locked, compare-and-swap, backed up; exact root HMP route only for one valid
  profile; refuse overlap or conflict; validate inode, owner, symlinks, policy, config races and profile
  identity. Parked, standalone and own-gateway profiles are excluded.
- **E6 No history requirement.** Root-route-only preparation works with existing history and leaves the
  profile's config bytes unchanged.
- **E7 Credentials (draft, separately authorized).** A fresh unique own-profile `API_SERVER_KEY` only if
  absent and a separate policy expressly permits it. The provisioner REQUIRES secure, atomic, locked or CAS
  owner-0600 writes. Current native `save_env_value` does not provide cross-process CAS or lock, preserves
  insecure modes, can refuse silently under a managed lock, and may publish to the shared environment; this
  requirement is not lowered and native atomic behavior is not claimed (G5). It needs a qualified
  out-of-gateway profile-scoped write route; the secret never passes argv or public logs; stdin or a
  bounded in-memory handoff is an unverified native capability. Check managed write authority and
  owner-correct 0600 or refuse; re-read privately and verify; never generate over or approve an existing
  invalid key. Preserve user config and any existing usable key; never overwrite an ambiguous or invalid
  secret; never reuse or copy the root or another profile's key. Needs independent security review and
  qualification before enabling.
- **E8 No per-bot restarts, route activation (G4).** No automatic per-bot gateway restart. The running
  gateway loads root `profile_routes` once; neither the reconciler, `reload-plugins` nor SIGUSR1 reload them
  (current source gap). A written route is `route_on_disk`, not `route_loaded`. No direct mutation of
  `runner.config` or a private route table. Zero-repeat-command depends on a qualified upstream
  route-refresh primitive. Root opt-in is assumed loaded at startup (unverified): a one-time install or
  configuration restart is permitted. A separately consented drain policy is the only future alternative to
  evaluate, never deployed automatically here.
- **E9 Honest status.** Per-bot independent states with fixed reason codes (`served`, `route_on_disk`,
  `route_loaded`, `prepared`, `read_available`, `send_key_present`, `send_configured`, `access_state`);
  `prepared` means provisioned prerequisites only; route on disk and route loaded are independent;
  `route_loaded` comes only from a qualified adapter routing result or a future public authoritative
  primitive, never disk inference, and is `unverifiable` when absent (G8); the readiness request is
  available only once the route is loaded; passive checks say `send_configured`, never `send_ready`; a real
  owner-run send is qualification evidence, not a per-bot chore, and a qualified capability plus
  authenticated own-key reads sets configured/available. Partial or failed provisioning is never green; no
  aggregate healthy value.
- **E10 No side effects.** Readiness and preparation never send a message, create a job, or trigger a turn.
- **E11 Logging.** Reason codes and profile names only; no key material, prefix or length.
- **E12 Delivery binding, done per policy.** The owner's full goal requires BOTH automatic scoped
  credentials (E7) AND route activation (E8): the full policy plus its activation. Route-only is partial
  read preparation, complete for that policy once the route is loaded, and never "fully ready". In the
  one-time setup the owner may explicitly choose full automatic read and send, with credential provisioning
  separately disclosed and accepted in that same flow. Both default off until host opt-in. No extra
  per-bot authorization or probe.

### Access (separate from preparation)

- **P1 Request access.** A prepared bot shows **Request access**. Preparation never grants access, creates
  a grant, or approves a pairing request.
- **P2 Approver and amendments (H1).** Normal bot read or send grants and scheduling or model-change
  privileges never confer permission to approve others. A host-selected owner/approver device or role is
  required, bootstrapped locally on the host; the approver must already have access to the target and hold
  a distinct device-approver privilege. The current contract prohibits a phone approving. Required
  amendments (planned, not made): constitution II, `HMP_V1.md` PR6-5, SEC-1, the host-only authorization
  boundary, and a caveat to the plan's blanket "bridge never writes Hermes state" for a native
  owner-authorized grant operation (no raw grant-file writes). The wire, role and security review freeze
  remains required.
- **P3 Card (H2).** The card is a device-targeted, ephemeral, trusted UI overlay/event to the approver
  device only. It is not inserted into the stored user-wide `(user_id, profile)` transcript and not
  broadcast to all owner devices. The exact authorized bot chat is the primary contextual review
  destination; central Requests is an aggregated inbox and fallback, not a competing primary presentation.
  A pending request still reaches the inbox when the target chat is not open or available (or not accessible
  to the approver), without automatically switching the active instance. Opening the exact authorized bot
  chat shows the same pending card, deduplicated by the exact scoped request, never a new request. An
  unprivileged requester sees only its own pending status. The bot cannot grant or decide; nothing is
  approved automatically. It starts no model turn, involves no model in the decision, and accepts no raw
  JSON grants. No command, text or details in ordinary push, group chat or LLM context; labels are
  untrusted, escaped and bounded. No new wire field, TTL or role scope is defined here.
- **P4 Card content.** Target bot, instance, host-known paired-device label (claimed names marked
  unverified), the actual authorization scope, status, expiry only from a qualified authoritative field
  else "unavailable" (G6; never an invented deadline or upper bound; the native private `created_at`, hash
  and salt are not copied or read to the phone; the CLI gives whole-minute age only), and **Allow** and
  **Reject** (requested UX target). Expired requests are blocked on answer by native authority.
- **P5 User scope.** Native bot grants are user-scoped and can apply to multiple paired devices sharing the
  user. The card states this. Device-specific UX needs a contract decision.
- **P6 Allow.** Uses the Hermes-supported authoritative operation
  `hermes -p <validated profile> pairing approve hmp <request_id>` with a strictly 16-hex request id, a
  sanitized environment and a resolved-pairing-directory check; no sticky active or default-profile
  fallback; no pairing-code approval mode. Verifies pending freshness from the known per-profile store (no
  global fallback), requires authenticated approver privilege and a non-revoked device, allows no wildcard
  or approve-all. HMP owns only its single-flight ticket and idempotency. At most one settlement across all
  writers is a REQUIRED future qualified API, not promised by the native CLI (G3a): native `PairingStore`
  locks in-process only and the CLI's two JSON writes are non-transactional. Native exit 0 is not
  settlement; the authoritative state is re-read. A vanished pending request with no grant, or uncertain
  execution, is `unknown` ("Check access status"), never retried automatically; a re-read reports current state,
  not causal attribution. The current request verification still has this race gap. No LLM or native
  private grant-write workaround.
- **P7 Reject.** Native `ca705` has no per-request deny. HMP reports this missing upstream primitive, never
  clears all pending requests, and never presents a local dismissal as a host rejection. Reject stays
  unavailable until a qualified native per-request deny exists; dismissal never implies rejection. The
  fallback dismiss copy must state that Reject is not implemented; no raw-JSON workaround.
- **P8 Separate contract.** Card visuals and notification plumbing are reused for future tool approvals,
  but bot access grants are a separate privileged contract and not a tool-approval ticket. The access-request
  card is labelled as a bot access request, distinct from a tool-execution approval. Future
  priority-notification plumbing shared with tool approvals is a hint only (future APNs/FCM), not authority,
  not current behavior, and carries no sensitive push fields.
- **P9 Bounds.** Proposed, to freeze (not current limits): bounded refresh candidate count; bounded
  per-device and per-profile pending rate and cooldown; total owner inbox cap with a suppressed repeat
  nonce; native 3 slots per platform per profile with no eviction of other requests; dedup of generic
  notifications.
- **P10 Env allowlist scope.** Where an instance-wide env allowlist is present (PR6-3), treat it as broader
  than one bot; no qualified per-bot isolation is claimed.

## Acceptance scenarios

- **A1 New bot after install.** Opt-in on; a new bot's own `multiplex_profiles` is false or absent and its
  history is unchanged; it is served, gets exactly its root route, the route is **loaded in the running
  process**, and it shows Request access. A route written but not loaded does not pass A1.
- **A2 Unique keys.** With credential provisioning on, each new bot gets a distinct key; none matches the
  root or another bot's key; existing usable keys are untouched.
- **A3 Ambiguous secret.** An invalid or ambiguous existing key is not overwritten; status is
  `needs_operator_review`.
- **A4 Partial failure.** Route written but key write fails (or the reverse): status shows the failed part;
  never green; other bots continue.
- **A5 Policy disable.** Turning a policy off stops further preparation; written routes stay; existing
  profiles are unchanged on turning it on.
- **A6 Delete and name reuse.** A deleted bot leaves a reported orphan route (no auto-delete); an ambiguous
  re-created name is quarantined and HMP name-keyed rows are invalidated through a reviewed migration;
  native grants are never raw-deleted. No claim that no grant is inherited based on inode alone.
- **A7 Races.** Config changed between read and write, swapped inode or owner, and symlinks below the root
  cause refusal with nothing written; concurrent provisioners write at most once.
- **A8 Conflicts.** Overlapping or extra-key routes refuse only that profile.
- **A9 No per-bot restart.** Preparation never restarts the gateway per bot; a route not yet loaded reports
  `route_on_disk` without `route_loaded` (`unverifiable` if there is no qualified source).
- **A10 No triggered work.** Readiness and preparation create no job and no model turn.
- **A11 No self-approval.** A device with only ordinary grants cannot answer a card; scheduling or model
  privileges do not confer approval; the requester cannot approve itself; an unprivileged requester sees
  only its own pending status.
- **A12 No LLM approval.** No model output or transcript content can cause a grant.
- **A13 Forged cards.** Expired, revoked, replayed, wrong-profile, wrong-user and wrong-instance cards are
  refused and change nothing.
- **A14 Scope copy and targeting.** The card reaches only the approver device and is absent from the stored
  transcript and other devices; it shows the user-scope consequence; allowing does not silently claim
  device-only effect.
- **A15 Native deny unavailable.** Reject never clears other requests; UI reports the host request still
  pending.
- **A16 Single-flight.** A duplicated Allow through HMP yields one HMP ticket execution; a vanished pending
  request with no grant, or an uncertain result, is `unknown` and not retried. Cross-writer single
  settlement is not claimed (G3a).
- **A17 Outcome re-read.** A native command that exits zero without an approved record is reported as
  unconfirmed; a re-read is reported as current state, not causal attribution. A bad request id shape,
  wrong-profile resolution or sticky-profile fallback refuses before any native call.
- **A18 Expiry.** Expiry is "unavailable" until a qualified authoritative field exists; none is invented;
  expired requests are blocked on answer by native authority.
- **A19 Secret hygiene.** No output or log holds a key value, prefix or length; the secret is never in
  argv.
- **A20 Bounds.** Flooding requests respects the proposed rate, cooldown, inbox cap and dedup, and never
  evicts other requests.
- **A21 Bot-chat primary, inbox fallback, dedup.** A pending access request is shown as a card in the exact
  authorized bot chat of the approver device. With that chat not open or available, it appears in central
  Requests without switching the active instance. Opening the exact chat shows the same pending card
  (deduplicated by exact scoped request), creating no new request. The card is labelled as a bot access
  request, distinct from a tool approval, and is absent from the stored transcript, group chat and LLM
  context. The bot cannot grant, and nothing is approved automatically.

## Out of scope

Automatic access grants; device-specific grants; changing a profile's session namespace; per-bot gateway
restarts; core Hermes patches; push delivery; tool approvals.

## Open decisions and gaps

Decisions D1-D6, gaps G1-G8 and blocker H1 are listed in `NEW_BOT_HMP_ENROLLMENT.md` section 9.
Consolidated upstream gaps: G1 lifecycle hook; G2 per-request deny; G3a cross-writer single settlement;
G4 route refresh; G5 secure profile-scoped `.env` write route; G6 authoritative expiry field; G7 durable
profile identity; G8 public running-route primitive. Blockers: the H1 amendments and the wire, role and
security review freeze; independent security review of E7; a qualified route-refresh primitive (G4); the
approver contract (P2); and an HMP v1.x contract revision for the ephemeral event and answer operation.
