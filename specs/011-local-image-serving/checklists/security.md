# Security checklist

Reviewer-owned. Nothing here is certified by the authors.

- [ ] Bearer authentication precedes every other check; the non-owner `404` precedes the gate.
- [ ] A ref authorizes nothing alone; every fetch re-authenticates and rescans.
- [ ] Binding covers device, user, instance, profile, session kind, session, tip, row id and content digest.
- [ ] Name derivation is lexical, flat and bounded; no `resolve()` and no legacy directory.
- [ ] No native call on the event loop; no atomic-snapshot claim.
- [ ] Permits are held through cancellation until the real future completes.
- [ ] No byte is sent before the final synchronous check; failure after `prepare` aborts the transport.
- [ ] Logs carry closed enums only.
- [ ] Gate closed adds no wire bytes and no file access.
- [ ] Availability is minimum version plus required APIs plus in-memory binding; no exact-build gate and no runtime reader of any build list, manifest, fingerprint or Git SHA for media.
- [ ] No process latch; a media-chain split or use-time identity mismatch closes only that listener, with a fixed outcome.
- [ ] Cache publication is one locked tuple assignment; no media component relies on GIL atomicity.
- [ ] No authorization is broadened: owner device, live exact-`true` flag, per-bot grants, typed tool-row authority and C6b identity proofs are retained.
- [ ] A disabled direct-send switch does not close media; a failed media binding does not close read, send or approvals.
- [ ] Assistant `MEDIA:` text is unmodified and confers no authority.
- [ ] Causal negatives exist for revocation, cross-device, cross-profile, tip change and async cancel.
- [ ] Exact-candidate independent security review (M3, S5), C6b and T12 sample evidence, and owner-authorized device acceptance are complete before any shipping claim. Sampled evidence never becomes a per-version allowlist.
