# Checklist: phone attachment native primitives

- [x] Source fingerprints equal before and after.
- [x] Output carries no prompt, transcript, id, key or cache path.
- [x] No HMP runtime/wire/API/auth/manifest/dependency file changed.
- [x] Every unsupported subcase is named as EVIDENCE_GAP with its reason.
- [x] No wire freeze or feature-ready claim.

The fixture checks the recorded behavior of one archive copy; it is not a qualification. Independent
root and focused review are pending, and no wire shape is frozen.
