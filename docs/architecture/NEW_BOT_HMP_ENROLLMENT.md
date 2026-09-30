# Automatic preparation of new bots for HMP (architecture proposal)

**Status: PROPOSAL. NOT IMPLEMENTED. NOT FROZEN. Not released, not contract-frozen, not tested.** Neither
automatic bot preparation nor the bot access permission card exists in any shipped HMP build. This
document plans the architecture only. Feature spec: `specs/006-new-bot-enrollment/`. It builds on
`specs/005-new-profile-routing/` (`hermes hmp routes add`).

Only the explicit, operator-run `routes add` draft exists in this branch. It is not claimed as deployed or
live-tested. A scoped operator repair of the exact route and send prerequisites was verified on a real
host; the automatic feature is not implemented. Details are kept out of this public tree.

**Delivery binding.** Complete delivery means BOTH automatic scoped credentials AND activation of the
route in the running gateway process. A route-only result is a partial milestone, never "fully ready".
Definition of done per policy is in section 3.5.

**Governing amendments.** The requested architecture needs constitution and contract amendments that do
not exist yet (section 6.1). The current contracts continue to prohibit a phone approving bot access until
those amendments are made and the wire, role and security review freeze is done. The owner has directed
that these amendments be planned; planning needs no further permission. Implementing new authority is not
authorized by this document.

## 1. Goal

A bot created after HMP was installed should appear in HMP with everything HMP needs, without the
operator repeating per-bot commands:

1. Technical preparation is automatic after a **one-time host opt-in**.
2. Access is **never** automatic. A prepared bot shows **Request access**. A grant is a separate,
   explicit, owner-authorized decision, presented primarily as a device-targeted ephemeral permission card
   in the exact authorized bot chat (section 7.1), with the central Requests inbox as the aggregated inbox
   and fallback.

Automatic technical setup is not automatic access.

## 2. Verified source facts (Hermes build `ca705dbf7ef86425b381b542712aff310f1ee52c`)

The installed source fingerprint matched the `ca705` qualification in an owner-local check. That
fingerprint is private local evidence and is not reproducible from the public tree. The facts below come
from a local read of that source. Line numbers differ between trees, so symbols are cited.

| Fact | Source |
| --- | --- |
| With a multiplexing root, `profiles_to_serve(multiplex=True)` returns the default plus every live named profile that is not parked and not `gateway.standalone: true`. A profile's own `multiplex_profiles` is not consulted. | `hermes_cli/profiles.py` `profiles_to_serve` |
| The host hot-serves new profiles: the `rescan-profiles` control verb (fired by profile create/delete) plus a supervised watcher every 30 s. It also rebuilds a served profile's adapters when its `config.yaml` or `.env` signature changes. A profile that still runs its own gateway is skipped with a warning. | `gateway/run_profile_reconcile.py` |
| The reconciler exposes `served_profile_names()`, which the HMP bridge already reads. | `gateway/run_profile_reconcile.py`, `server/hmp_plugin/bridge.py` |
| No plugin-facing profile create/delete/rename hook exists. The only notification is the internal control verb. | `hermes_cli/plugins.py` hook list, `hermes_cli/profiles.py` |
| A named profile's `API_SERVER_KEY` does not open a second listener under a multiplexer. The root listener serves `/p/<profile>/` and authenticates with that profile's own scoped key, which must pass `has_usable_secret(min_length=16)`. A scoped miss fails closed and never inherits the owner key. | `gateway/platforms/api_server.py` `_expected_api_key`, `_resolve_request_profile`; `gateway/config_env.py` `_enable_from_env`; `gateway/platforms/_shared.py` `get_scoped_secret` |
| Native pairing is per platform per profile: `PairingStore(profile=...)` keeps `<platform>-pending.json` and `<platform>-approved.json` under that profile's home. Pending entries carry `request_id`, `user_id`, `user_name`, and also private `created_at`, hash and salt fields (never copied or read to a phone). The native CLI lists age in whole minutes only. Pending TTL is 3600 s; at most 3 pending per platform per profile, with no eviction of other requests. | `gateway/pairing.py` |
| `approve_request(platform, request_id)` approves the **user** named in the pending entry, and returns `None` for unknown and expired ids alike. The approved list is keyed by user id, so it applies to every device paired under that user. `PairingStore` locks only in-process (`threading.RLock`). The CLI is a separate process, and its two JSON writes (pending, then approved, in `_finish_approval`) are not transactional: they can race with the gateway, and a crash between them removes the request without granting it. | `gateway/pairing.py` `approve_request`, `_approve_user`, `_finish_approval` |
| The native CLI offers `list`, `approve`, `revoke` and `clear-pending` only. There is **no per-request deny**. `clear-pending` removes every pending request. `revoke` removes an approved user. It builds `PairingStore()` without a profile, so the target resolves through `HERMES_HOME` or the sticky `active_profile`. `approve` treats any input that is not 16 hex characters as a pairing code (failed codes count toward lockout) and exits 0 regardless of outcome. | `hermes_cli/pairing.py` |
| Hermes writes `.env` values through `save_env_value` (validates name, strips newlines, checks non-ASCII, writes atomically). It has **no cross-process lock or compare-and-swap**, preserves the file's existing mode (a 0644 or 0640 `.env` would receive a secret at that mode), refuses silently when a managed write lock blocks it, and may publish the value into the shared `os.environ` when called inside the gateway (plausible, not verified). It targets the current `HERMES_HOME`, so a per-profile write needs a verified profile-scoped call (G5). | `hermes_cli/config.py` |
| The HMP bridge builds its own direct-send endpoint from the root listener and the profile's own key; any ambiguity fails closed. | `server/hmp_plugin/bridge.py` `direct_send_endpoint` |
| **Root routes are loaded once.** `gateway.profile_routes` is parsed into `self.config` when `GatewayRunner` is constructed. Profile resolution reads `self.config.profile_routes`. | `gateway/config.py` `from_dict`, `gateway/run.py` `GatewayRunner.__init__`, `_profile_name_for_source` |
| **The reconciler does not reload routes.** `run_profile_reconcile` rescans served profiles from `self.config` and reloads secondary profile configs, not the root route table. | `gateway/run_profile_reconcile.py` |
| **`reload-plugins` does not reload routes.** It only rewires plugin handlers. | `gateway/run_plugin_rewire.py` |
| **SIGUSR1/reload is drain and relaunch**, not a hot config reload. | `gateway/run.py` restart handling |

Consequences:

- A new bot on `ca705` is already served (adapters), but a newly written exact root route is **not
  proven to be picked up by the running process**. Writing the route and triggering a rescan does not
  activate it. This is concrete gap G4, not merely unknown.
- Route on disk and route in the running process are independent facts and are reported separately.
- No unsupported direct mutation of `runner.config` or a private route table is allowed.
- A truly zero-repeat-command target depends on a qualified upstream route-refresh primitive. The only
  legitimate restart in this proposal is the one-time install or configuration restart at opt-in (the
  opt-in keys live in the root config, which may also be loaded once, see G4). There is no per-bot
  automatic restart. A future, separately consented drain policy is the only alternative to evaluate; it
  is not part of this plan and is never deployed automatically.
- A root-route-only preparation must **not** change the profile's own `multiplex_profiles`. That flag
  changes the profile's session namespace. Zero history is therefore not required for route-only
  operation. An earlier draft wrongly changed this flag; that text is removed.
- The host's pairing identity is user-scoped, not device-scoped (see section 7).

Not verified: whether the root opt-in keys are read live or only at startup; upgrade behavior of other
builds; `.env` hot reload for the send key (the reconciler does rebuild adapters on an `.env` signature
change, but the scoped-key read path is unqualified); whether a profile-scoped native `.env` write can be
invoked without a Hermes subprocess.

## 3. Architecture overview

```
new profile created  --(no hook)-->  detection: served-profile snapshot vs root routes
                                          |
                     host opt-in on?  -- no --> report only (read-only)
                                          | yes
                                          v
                              scoped provisioner (same OS user)
                     route add (CAS, backup)   send key (only if policy permits)
                                          |
                                          v
                   per-bot status: route on disk / route loaded / prepared (never "ready" by itself)
                                          |
                                          v
              phone sees "Request access"  --> pairing request (native, user-scoped)
                                          |
                                          v
        approver device: ephemeral card in the bot chat (primary); central Requests inbox (aggregate/fallback)
                                          |
                                          v
                      Hermes-native approve, re-read outcome, then report
```

### 3.1 One-time host opt-in

Performed once on the host by the operator, never by a phone or a bot:

- a feature switch, proposed name `gateway.platforms.hmp.extra.prepare_new_profiles` (boolean `true`
  only; any other value is off and reported);
- a **separate** authorization for credential provisioning, proposed
  `gateway.platforms.hmp.extra.provision_send_credentials`, default off;
- the root loopback `api_server` listener and `direct_send` settings (today's documented setup);
- selection of the owner/approver device or role (section 6).

Whether the root config is read live or only at startup is unverified (G4). The opt-in therefore
assumes the root config is **loaded at startup**, and a one-time install or configuration restart is
permitted to activate it. No per-bot automatic restart is part of this proposal. The names are proposals,
not contract.

**Owner policy choice (one-time setup).** Route-only preparation is the partial read preparation policy.
In the same one-time setup flow the owner may explicitly choose full automatic read and send, in which
case credential provisioning is separately disclosed and accepted in that same flow. Both default off
until the host opts in. No additional per-bot authorization or probe is required.

### 3.2 Detection (no hook)

Gateway hot-serving already covers discovery. HMP needs only to know which served profiles lack an
exact root route. Detection is a **qualified served-profile snapshot and reconciliation fallback**:

- compare the bridge-observed served list against the root `gateway.profile_routes`, plus a bounded
  directory scan for staging-dot and invalid names;
- run on the bridge's existing periodic refresh or an operator-managed timer (decision D1);
- a missed cycle only delays preparation.

A plugin lifecycle hook would be cleaner. It is an **upstream opportunity** and not a present API. No
core patch and no undocumented lifecycle hook is used.

### 3.3 Scoped provisioner

The provisioner is a same-OS-user component with narrow authority. It is **not** the requester's or a
client's authority: no phone, bot, or model input selects a path, name, or key.

Route addition rules (extend 005 R1, R5-R9; the profile's own config is not written):

- **Atomic, locked, CAS.** Take an advisory lock; re-read and compare a content digest plus inode
  identity immediately before rename; keep a private backup; write with same-directory temp file,
  fsync, rename. Refuse on any drift.
- **Exact route only.** Add exactly one route for one validated profile name. Refuse any overlap,
  broad, disabled or extra-key route. Existing exact route is a no-op.
- **Path safety.** Validate directory and file ownership, modes, regular files, size bounds, no
  symlinks below the Hermes root, and strict YAML. Re-validate after the lock.
- **Identity.** Directory inode and owner are **not** a durable identity (inodes are reused). The
  provisioner may record them as a tamper signal only. A new HMP policy-generation registry helps detect,
  but cannot prove, an unseen name replacement. A Hermes durable profile identity and lifecycle primitive
  is needed (G7). Until then an ambiguous name is quarantined and HMP name-keyed rows are invalidated
  through a reviewed migration. Native grants are never raw-deleted. This proposal does not promise that
  no grant is inherited based on inode alone; the lower layer may retain native grant stores.
- **Exclusions.** Parked, standalone, tombstoned and own-gateway profiles are excluded and reported.
- **Baseline.** Eligibility is a one-time **policy generation** plus a persistent identity baseline
  (profile identities recorded at opt-in), not creation timestamps. Profiles in the baseline need an
  explicit migration command.
- **No per-bot restarts.** It never restarts the gateway. Because the running process does not reload
  root routes (section 2, G4), a written route stays `route_on_disk` and not `route_loaded` until a
  qualified refresh primitive exists or the operator performs the one-time install restart (not per
  bot). It is never reported green and never counted as A1 passing.

### 3.4 Credential provisioning for sending (separately authorized, draft)

Per-bot sending needs the bot's own unique `API_SERVER_KEY` (section 2). Provisioning rules:

- Only if `provision_send_credentials` is on **and** the profile has no key at all. No key is generated
  to replace an existing invalid one; that is `needs_operator_review`.
- Generate a fresh random key, unique per profile (at least 256 bits). Never echoed, logged, placed in
  argv, or sent anywhere.
- Preserve user config and any existing usable key. **Never overwrite** an ambiguous or invalid existing
  secret. Never reuse, derive, or copy the root key or another profile's key.
- **Requirements of the proposed provisioner (not current native behavior).** Secure, atomic, locked or
  compare-and-swap owner-0600 writes. Current `save_env_value` provides no cross-process CAS or lock,
  preserves insecure modes, refuses silently under a managed lock, and may publish to the shared
  environment (section 2). This proposal does **not** lower these requirements to fit the native helper,
  and does not claim the native helper has atomic or complete behavior today. Recorded under G5.
- Needed: a qualified, out-of-gateway, profile-scoped write route. The secret never passes argv or public
  logs. A stdin route or another bounded in-memory handoff is an **unverified** native capability.
- Before writing: check managed write authority, and check the file is owner-correct with mode 0600 or
  refuse. After writing: re-read privately and verify. Never approve or generate a key over an existing
  invalid one.
- The send-path rules from the current contract are unchanged. Gateway `.env` hot reload is not assumed.

**This section is a draft.** Changing send configuration or credentials needs a focused, independent
security review and exact-build qualification before it is enabled (constitution V and VI). Until then
the plan ships route preparation and read-only diagnostics first.

### 3.5 Definition of done per policy

- **Route-only (default, partial read preparation).** Complete when the route is on disk and loaded in
  the running process.
- **Full auto read and send (the owner's one-time choice).** Complete only with credential provisioning
  (G5) and route activation (G4). The full owner goal (E12) requires the full policy plus its
  activation; under route-only, "fully ready" is never claimed.

## 4. Status model

Per bot, independent states with fixed reason codes: `served`, `route_on_disk`, `route_loaded`,
`prepared`, `read_available`, `send_key_present`, `send_configured`, `access_state`. No aggregate
"healthy" value. Partial or failed provisioning is never green. Readiness checks never send a message,
start a job, or trigger a model turn.

- `prepared` means provisioned prerequisites only (route on disk, scoped credentials). It says nothing
  about the running process.
- `route_loaded` is reported only from a qualified adapter routing result or a future public
  authoritative primitive (G8), never inferred from disk. If neither is available, the state is
  `unverifiable`.
- The readiness request is available only after the route is **loaded in the running process**
  (`route_loaded`).
- Passive checks report `send_configured`, never `send_ready`. A real owner-run send is separate
  qualification evidence, not a perpetual per-bot operator chore: once the capability is qualified on
  the build, authenticated own-key reads and the like set `send_configured` and `read_available`, and
  the UI does not require every future user to send a probe to become writable.

## 5. Send prerequisites (unchanged, reported per bot)

Exact root route loaded in the running process; served; root `direct_send.enabled`; root `api_server`
on loopback with a root key; the bot's own unique key. None implies another. A real send is qualification
evidence only. Where an instance-wide env allowlist is present (PR6-3), it is broader than one bot; no
qualified per-bot isolation is claimed.

## 6. Approver authority

Normal per-bot read or send grants, and scheduling or model-change privileges, must **not** confer the
right to approve others. An independently **host-selected owner/approver** device or role is required,
bootstrapped locally on the host (for example during `pair` confirmation), revocable, and recorded in the
HMP store. A client cannot designate itself. The approver must already have access to the target bot and
hold a distinct device-approver privilege. This is a new privileged contract; it is not in HMP v1.

### 6.1 Required amendments (HUMAN host-designated device remote access management)

The current contract **prohibits** a phone approving bot access. The owner's latest request directs that
these amendments be planned. They are not implemented and do not confer new authority now. All are needed
before any implementation:

- **Constitution II** (host-side confirmation of authorization): amend to admit an explicitly designated,
  host-bootstrapped device as a human authorization channel for bot access.
- **`HMP_V1.md` PR6-5** ("HMP still never approves a P6 request itself"): amend so a human-initiated,
  owner-authorized grant operation through a native owner-authorized primitive is permitted and defined.
- **SEC-1** (no HMP-owned approval layer replacing upstream gap P11): amend or re-scope so the approver
  role is not an approval layer that replaces the upstream primitive.
- **Host-only authorization boundary**: amend to allow the host-designated approver-device role.
- **Plan trust boundary "bridge never writes Hermes state"**: replace the blanket statement with a caveat.
  A native owner-authorized grant operation is the new amendment; the bridge still performs no raw grant
  file writes.

The wire, role and security review freeze remains required (blocker H1, section 9).

## 7. Bot access permission card (PROPOSAL)

A prepared bot shows **Request access**. Requesting creates the native pending pairing request for that
user (existing behavior). A **device-targeted notification event**, not a chat prompt, then reaches the
approver.

### 7.1 Presentation

The permission card is a **device-targeted, ephemeral, trusted UI overlay/event** delivered to the
host-selected approver device only. It is **not** inserted into the stored user-wide `(user_id, profile)`
transcript and is **not** broadcast to all of the owner's devices.

Preconditions: the approver device already has access to the target bot and holds the distinct
device-approver privilege. An unprivileged requester sees only its own pending status.

**Primary destination and inbox fallback.** The bot chat of the exact authorized instance and profile is
the primary, contextual review destination. Central **Requests** is an aggregated inbox and fallback, not a
competing primary presentation. A pending request must still reach the inbox when the target chat is not
open or available (or the target is not accessible to the approver), without automatically switching the
active instance. When the approver opens the exact authorized bot chat, it shows the same pending card,
deduplicated by the exact scoped request (instance, profile, `request_id`); opening the chat never creates a
new request. The card is an ephemeral, device-targeted event for the host-designated approver device only,
never a stored transcript, group chat or LLM-context entry. The bot cannot grant or decide, and nothing is
approved automatically. No new wire field, TTL or role scope is defined here (D6).

**Distinct from tool approval.** The card is labelled as a **bot access request** and is visibly distinct
from a tool-execution approval (section 7.6).

The command, text and details never enter ordinary push, group chat or LLM context. Labels are untrusted,
escaped and bounded. The card shows:

- target bot, instance, and host-known paired-device label (a claimed, unverified name is marked
  unverified);
- the actual authorization scope;
- status, and expiry only if a qualified authoritative expiry field exists; otherwise "unavailable";
- **Allow** and **Reject** (the requested UX target; see 7.5 for what Reject can truthfully do today).

**Expiry (G6).** The native pending file holds `created_at`, hash and salt; these stay private and are
not copied or read to the phone. The native CLI reports age in whole minutes only. Expiry is
"unavailable" until a qualified authoritative expiry field exists upstream. No deadline or upper bound is
invented. An expired request is blocked on answer by the native authority.

**Bounds (values proposed for freezing; not current limits).** A bounded refresh candidate count; a
bounded per-device and per-profile pending rate and cooldown; a total owner inbox cap with a suppressed
repeat nonce; native limit of 3 slots per platform per profile, with no eviction of other requests;
deduplication of generic notifications.

### 7.2 Scope consequence (must be shown)

Native bot grants are **user-scoped**. Allowing a request grants the bot to that user, which can apply to
every paired device sharing that user, not only the requesting device. The card states this. Device-specific
UX needs a separate contract decision (D4) and is not assumed.

### 7.3 Not a chat turn

The card is an ephemeral event and overlay. It is not a normal user prompt, triggers no model turn, no
model or tool decides the grant, and nothing is stored in the transcript. No raw JSON grants are accepted.

### 7.4 Allow path

Allow runs one Hermes-supported authoritative operation bound to the exact instance, profile,
`platform=hmp`, `request_id` and user, with these checks:

1. the approver device is authenticated, holds the approver privilege, and is not revoked;
2. the pending record is fresh and still matches (re-read, same user and request id, from the
   known per-profile store, **no global fallback**);
3. HMP owns only a single-flight ticket and idempotency on `(approval_ticket, request_id)`. It does
   **not** own settlement. At most one settlement across all writers (gateway, CLI, dashboard) is a
   REQUIRED future qualified API (G3a) and is **not** promised by the native CLI, which today can race;
4. no wildcard and no approve-all;
5. execution uses the native approval operation for the exact profile:
   `hermes -p <validated profile> pairing approve hmp <request_id>`, with a strictly 16-hex `request_id`
   validated before the call, a sanitized environment, and a check that the resolved pairing directory
   matches the profile. There is no sticky active or default-profile fallback and no pairing-code
   approval mode. **Native exit status 0 is not settlement**: re-read the authoritative approved list and
   report only what it shows. The current request verification still has the race gap of item 3;
6. if native execution is uncertain (timeout, crash), or the pending request vanished with no grant, the
   outcome is `unknown` ("Check access status") and is **not retried automatically**. An authoritative re-read
   reports the current state, not causal attribution: the dashboard or CLI may have approved it.

No LLM path and no native private grant write is used as a workaround for the missing safe remote
settlement API (G3a).

### 7.5 Reject path

`ca705` has approve, revoke and clear-pending but **no per-request deny**. This is a missing upstream
primitive (gap G2). Consequences:

- HMP must never clear all pending requests to reject one;
- Reject remains unavailable until a qualified native per-request deny exists; a local dismissal in the
  app never implies rejection and must never be described as a host rejection; the request simply
  remains pending until it expires or a future native deny exists;
- The current fallback is "Dismiss (request stays pending on the host)". Its copy must explicitly state
  that **Reject is not implemented**. Native per-request deny is a gap needing an upstream primitive;
  no raw-JSON or file-edit workaround is used.

### 7.6 Relationship to tool approvals

The card reuses the visuals and the notification plumbing planned for tool approvals. Bot access grants
are a **separate privileged contract** and not a tool-approval ticket; the UI labels an access-request card
distinctly from a tool-execution approval. Future priority-notification plumbing shared with tool approvals
is a hint only: it is not authority, not current functionality, and carries no sensitive push fields.

## 8. Security analysis

| Threat | Mitigation |
| --- | --- |
| Client or model steers the provisioner | Provisioner takes no client input; names come from host directories, validated |
| Config tamper or race between read and write | Lock + CAS (digest and inode) + backup; refuse on drift |
| Symlink or ownership swap | No symlinks below root, owner/mode checks, re-validate after lock |
| Name reuse after delete inherits access | HMP policy-generation registry detects but cannot prove replacement; quarantine ambiguous names; reviewed migration invalidates name-keyed HMP rows; no raw native grant deletion (G7) |
| Key reuse or root-key exposure | Unique key per profile, never root or copied, never logged, never in argv |
| Insecure `.env` write | Require owner 0600, locked or CAS write, private re-read; refuse otherwise (G5) |
| Self-approval, approver escalation | Separate host-selected approver; grants do not confer it |
| Forged, expired, revoked, wrong-profile card | Bind to exact request, re-read on answer, device revocation check |
| Double approval | HMP single-flight ticket; cross-writer single settlement is a required future API (G3a) |
| Wrong-profile native approve | `hermes -p` validated profile, 16-hex id, sanitized env, directory check |
| LLM or transcript path to grant | Ephemeral device-targeted event only, nothing stored in the transcript, no model turn |
| Card reaches other devices | Targeted to the approver device; not broadcast; not in the user-wide transcript |
| Card content injection | Labels untrusted, escaped, bounded; no command/details in push, group chat or LLM context |
| Approval request flood | Bounded rate, cooldown, inbox cap, repeat nonce, dedup (values to freeze) |
| Instance-wide env allowlist | Broader than one bot where present; no per-bot isolation claimed (PR6-3) |
| Same-user code | Same-user code can already edit these files (SEC-1); the provisioner mitigates mistakes and races and is not a boundary against it |

## 9. Gaps and decisions

| ID | Item |
| --- | --- |
| H1 | Amendments to constitution II, PR6-5, SEC-1, the host-only authorization boundary and the bridge-never-writes caveat (section 6.1), plus the wire, role and security review freeze. Blocker |
| G1 | No plugin profile-lifecycle hook (upstream opportunity) |
| G2 | No native per-request deny (upstream primitive) |
| G3 | Pairing grants are user-scoped, not device-scoped |
| G3a | No qualified cross-writer single-settlement API. Native `PairingStore` locks in-process only; the CLI is a separate process with non-transactional JSON writes; a vanished pending request stays `unknown`. No safe remote grant settlement API has been qualified on this build; model decisions and private grant-file writes are rejected as substitutes |
| G4 | **Current source gap:** root `profile_routes` are loaded once into `self.config`; no hot route refresh exists (reconciler, `reload-plugins` and SIGUSR1 do not reload them). Needs a qualified upstream route-refresh primitive. Root opt-in keys are assumed loaded at startup (unverified); a one-time install or configuration restart is permitted and no per-bot automatic restart is proposed. Send-key hot reload is separately unverified |
| G5 | No qualified out-of-gateway profile-scoped secure `.env` write route. Current `save_env_value` has no cross-process CAS or lock, keeps insecure modes, refuses silently under a managed lock, and may publish to the shared environment. A stdin or bounded in-memory handoff is unverified. Nothing claims native atomic behavior |
| G6 | No exposed authoritative expiry field through the public CLI (the private native record has `created_at`, hash and salt; CLI shows whole minutes only) |
| G7 | No durable Hermes profile identity or lifecycle primitive (inode/owner is not identity) |
| G8 | No public authoritative primitive reporting the running route table (`route_loaded` is `unverifiable` without a qualified adapter routing result) |
| D1 | Detection placement: in-gateway refresh or operator timer |
| D2 | Approver bootstrap, storage and revocation |
| D3 | Whether credential provisioning is ever on by default (recommend off; the owner may choose full auto read and send in the one-time setup, disclosed and accepted separately) |
| D4 | Device-specific grant UX |
| D5 | Reject semantics without native deny |
| D6 | Wire contract for the ephemeral event and answer operation, and the freeze of the proposed bounds |

## 10. Rollout order

1. Read-only `routes scan` and per-bot status.
2. Route-only write behind opt-in. This is **partial, not completion**: the route stays `route_on_disk`
   until the running process loads it (G4).
3. Amendments (section 6.1), then approver role, permission card, answer operation (HMP v1.x contract
   change first). This runs in parallel with phase 4 once the role contract is fixed.
4. Credential provisioning, only after independent security review, exact-build qualification and a
   qualified write route (G5).
5. Route activation in the running process via a qualified upstream refresh primitive (G4).

Under the full auto read and send policy, delivery is complete only when phases 2, 4 and 5 all hold.
Under route-only policy, phases 2 and 5 complete it (section 3.5). The approver card is parallel after the
amendments and the role contract.
