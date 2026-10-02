# Requirement checklist

Reviewer-owned. Unchecked until an independent reviewer marks an item; the authors do not certify.

## Documents

- [ ] ROOT_DECISIONS corrections 1-8 appear in spec, plan and §7e without contradiction.
- [ ] Gate is default-off, `is_approval_owner_device` scoped, and needs actual availability (minimum version, required APIs, in-memory binding); no build list exists; closed-gate bytes are identical.
- [ ] Availability is minimum-version plus required APIs plus in-memory binding; no exact-build gate. No runtime reader of any build list, manifest, fingerprint or Git SHA for media. A disabled direct-send switch does not close media. Approval gates not waived.
- [ ] Authority is only a strict same-profile tool row; assistant `MEDIA:` has none.
- [ ] Sidecar keeps the candidate out of wire serialization.
- [ ] Two off-loop phases, shared 20 s wait, non-queueing phase-two permit, synchronous final section, no native check on the loop, no atomic-snapshot claim, residual stated.
- [ ] §7e error table matches current HMP source (bearer codes, ERR-3 extras, generic 404 rows, `internal_error`).
- [ ] Constants are labelled new choices; memory ceilings are provisional.
- [ ] Ref grammar, TTL, caps, idempotent mint and the 128 limit are exact.
- [ ] Permit lifetimes under cancellation are stated.
- [ ] E1 and the Linux leaf run are stated as sampled evidence; delivery review, C6b/T12 sample evidence and device acceptance are stated as pending; no shipping, enablement or qualification claim is made.
- [ ] Conformance rows list every future test as unimplemented.
- [ ] Public text contains no private path, personal identifier, secret or transcript.
- [ ] Superseded S6/S6a/S6b text is preserved as historical and not presented as current; the accepted M3 listener binding is described as source-only, with descriptor emission, fetching and device acceptance still open.
- [ ] Known carried failures are scoped to their checkpoint: the 114 legacy failures and collection error were retired or adapted in M3; three S4 contract-table failures remain visible, not green.

## Open gates (not satisfiable by documents)

- [ ] Independent review of this contract revision.
- [ ] C6b exact-native cost and T12 memory sample evidence recorded (evidence, not a per-version gate).
- [ ] Independent review of the exact candidate (M3 and S5), owner-authorized install and flag, and device acceptance.
