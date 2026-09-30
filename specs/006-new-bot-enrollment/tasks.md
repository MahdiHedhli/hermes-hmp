# Tasks: automatic preparation of new bots and access permission cards

**PROPOSAL. NOT IMPLEMENTED. NOT FROZEN.** Nothing below is done. Tests are written before code.

## Contract and decisions

- [ ] T1 Resolve D1-D6 (architecture doc section 9) with the owner.
- [ ] T1a Plan the amendments (H1): constitution II, `HMP_V1.md` PR6-5, SEC-1, host-only authorization
      boundary, and the "bridge never writes Hermes state" caveat for a native owner-authorized grant
      operation (no raw grant writes). Wire, role and security review freeze required before T2.
- [ ] T2 Draft HMP v1.x revision: approver role, device-targeted ephemeral event, answer operation, expiry
      and scope fields, proposed bounds. Update `HMP_V1.md` and the conformance matrix in the same change.
- [ ] T3 Record upstream requests: per-request deny (G2), lifecycle hook (G1), cross-writer single
      settlement API (G3a), authoritative expiry field (G6), durable profile identity (G7), public running
      route primitive (G8).

## Phase 1: scan and status

- [ ] T4 Tests: per-bot independent states; orphan route; no writes; no model turn.
- [ ] T5 Implement `routes scan` and status reason codes.

## Phase 2: route-only preparation

- [ ] T6 Tests A1, A5-A10 and A19 in isolated temp homes (history unchanged, own flag untouched, races,
      inode or owner swap, symlinks, conflicts, no restart).
- [ ] T7 Provisioner: lock, digest-plus-inode CAS, backup, exact route, exclusions, opt-in baseline.
- [ ] T8 Report `route_on_disk` vs `route_loaded` separately. Root routes are loaded once (G4); do not
      claim A1 until the route is loaded. No mutation of `runner.config` or a private route table.
- [ ] T8a Request or qualify an upstream route-refresh primitive; verify whether the root opt-in keys load
      at startup (one-time install restart permitted, no per-bot restart). Optionally evaluate a separately
      consented drain policy (not automatic).
- [ ] T8b `route_loaded` only from a qualified adapter routing result or a public primitive; otherwise
      `unverifiable`.
- [ ] T8c Quarantine ambiguous names and invalidate HMP name-keyed rows via reviewed migration; never
      raw-delete native grants (G7).

## Phase 3: approver and card

- [ ] T9 Tests A11-A18, A20 and A21 (self-approval, LLM path, forged and expired cards, targeting, scope copy,
      native deny unavailable, single-flight, outcome re-read, request id shape and profile resolution,
      bounds).
- [ ] T10 Approver bootstrap on the host and revocation.
- [ ] T11 Ephemeral device-targeted event and answer operation in the bridge; per-profile store, no global
      fallback; `hermes -p <profile> pairing approve hmp <16-hex id>` with sanitized env and path check;
      exit 0 is not settlement; vanished or uncertain is `unknown`, no auto retry; labels escaped and
      bounded; no details in push or LLM context.
- [ ] T11a Fallback dismiss copy states Reject is not implemented; record native per-request deny as a gap.
- [ ] T11b Bounds: refresh candidate count, per-device/profile rate and cooldown, owner inbox cap with
      repeat nonce, dedup (values to freeze in T2).
- [ ] T12 Device-side card UI in the app repository (separate change).
- [ ] T12a Card UI: render the access-request card in the exact authorized bot chat (primary), with central
      Requests as aggregated inbox and fallback when the chat is not open or available, without switching the
      active instance; opening the chat shows the same pending card (dedup by exact scoped request, no new
      request); label it a bot access request, distinct from a tool approval. Covers A21.

## Phase 4: credentials (blocked)

- [ ] T13 Qualify an out-of-gateway profile-scoped secure `.env` write route (G5): cross-process CAS or
      lock, owner-0600 or refuse, managed-lock authority check, stdin or bounded in-memory handoff, no
      shared environment publication, private re-read. Do not lower requirements to fit native
      `save_env_value`. Verify send-key hot reload.
- [ ] T14 Tests A2-A4 and A19.
- [ ] T15 Implement provisioning behind its own policy.
- [ ] T16 Independent focused security review and exact-build qualification. Do not enable before this.

## Delivery gate

- [ ] T16a The full auto read and send policy is complete only with automatic scoped credentials (phase 4)
      AND running-process route activation (T8a). Route-only policy is complete once the route is loaded,
      and is never "fully ready". The approver card (phase 3) proceeds in parallel after the amendments
      (T1a) and role contract (T2).

## Release

- [ ] T17 Update `FEATURES.md`, `docs/INSTALL.md`, `server/DEPLOYMENT.md`; run the privacy and plugin
      surface scans.
