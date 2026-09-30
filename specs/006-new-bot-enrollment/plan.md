# Plan: automatic preparation of new bots and access permission cards

**PROPOSAL. NOT IMPLEMENTED. NOT FROZEN.** Planning only. See `docs/architecture/NEW_BOT_HMP_ENROLLMENT.md`
for facts and threat analysis.

## Phases

1. **Read-only scan and status.** `routes scan` lists served profiles without an exact root route and
   orphan routes; per-bot independent states. No writes.
2. **Route write (partial milestone).** Provisioner module reusing the 005 `routes.py` safety helpers
   (strict YAML, path checks, backup), adding an advisory lock and digest-plus-inode compare-and-swap. Root
   route only; the profile's own config is never written. Gated by the one-time host opt-in. The result is
   `route_on_disk` only; it is not completion (G4).
3. **Approver role and permission card** (parallel with phase 4 once the role contract is fixed). First the
   planned amendments (constitution II, PR6-5, SEC-1, host-only authorization boundary) and the wire, role
   and security review freeze. Then the HMP v1.x contract revision: approver role bootstrap, device-targeted
   ephemeral event (not stored in the user-wide transcript), answer operation, expiry and scope fields,
   bounds. Then bridge and store changes.
4. **Credential provisioning.** Only after an independent focused security review, exact-build
   qualification and a qualified out-of-gateway profile-scoped secure write route (G5). The current native
   `save_env_value` is not sufficient.
5. **Route activation.** A qualified upstream route-refresh primitive so the running gateway loads the new
   root route (G4). No direct mutation of `runner.config`. Root opt-in is assumed loaded at startup: a
   one-time install or configuration restart is permitted; no per-bot automatic restart. A separately
   consented drain policy is the only alternative to evaluate.

**Binding:** under the full auto read and send policy, delivery is complete only when phases 2, 4 and 5 all
hold. Route-only is partial read preparation (complete for that policy once loaded), never "fully ready".
The Reject fallback copy states that Reject is not implemented.

## Trust boundaries

- The provisioner is same-OS-user code, not client authority; it is no defence against same-user code.
- The bridge performs no raw writes to Hermes grant files. The blanket "bridge never writes Hermes state"
  needs a planned amendment caveat (H1): a native owner-authorized grant operation is the new authority and
  is not permitted by the current contract. The answer operation runs
  `hermes -p <validated profile> pairing approve hmp <16-hex request_id>` in a sanitized environment,
  re-reads the authoritative store, and never reads or returns a pairing code. HMP owns only its
  single-flight ticket; cross-writer settlement is a future API (G3a).
- The permission card is an ephemeral device-targeted overlay, not stored in the user-wide transcript and
  not broadcast. The exact authorized bot chat is its primary review destination; central Requests is the
  aggregated inbox and fallback, deduplicated by exact scoped request. It is labelled as a bot access
  request, distinct from a tool approval.
- Approver authority is separate from every other grant.

## Compatibility assumptions (to qualify per exact build)

Hot serving and the 30 s reconciler; `served_profile_names()`; per-profile `PairingStore`; `approve_request`
semantics; absence of per-request deny; scoped secret read and 16-character key floor; root routes are
loaded once into the runner config (no hot refresh; G4, current source gap); root opt-in live reload is
unverified; hot reload of a new `.env` key is unverified; native `.env` write lacks cross-process CAS
(G5); CLI `approve` exits 0 regardless and resolves the profile from the environment (H4).

## Open items

H1, G1-G8 and D1-D6 from the architecture document. Phases 3 and 4 are blocked until their decisions,
amendments and reviews complete.
