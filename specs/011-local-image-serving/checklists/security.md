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
- [ ] Causal negatives exist for revocation, cross-device, cross-profile, tip change and async cancel.
- [ ] E1, Linux qualification, exact-candidate review and device acceptance are complete before any shipping claim.
