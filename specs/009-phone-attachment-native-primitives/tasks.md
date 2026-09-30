# Tasks: phone attachment native primitives

- [x] Discovery: README, SECURITY, CONTRIBUTING, PRIVACY_GATE, skill, census, flagless fixture read.
- [x] Fixture tool with isolated roots and IP-socket denial.
- [x] Subcase 1 cache helpers.
- [x] Subcase 2 MessageEvent representation.
- [x] Subcase 3 inbound preparation, `media_text_inlined` None/False/True.
      Gap: text-mode image enrichment needs a vision/model call; not run.
- [x] Subcase 4 busy fallback versus runner queue policy, with scope negative control.
      Gap: the runner's full busy handler (auth, ack, steer) was not entered; only its queue policy.
- [x] Subcase 5 durable row through the real flush helpers.
      Gap: duck-typed agent; no real agent turn, no HMP read bridge.
- [x] Focused tests.
- [x] Research note with fingerprints, results and gaps.
- [x] Pinned Ruff, plugin surface, privacy/log scans, diff check.
- [x] Worker fix: `connect_ex` self-test probe (four denial methods, four counted attempts).
- [x] Root prior reproduction of the earlier run (73 checks, all held).
- [x] Repair: parent exit requires every run boundary (fail closed, names only the boundary);
      focused predicate tests. Status stays PASS_WITH_EVIDENCE_GAP.
- [x] Root review of this repair: exact code and tests, repaired native run and 30 focused tests.
- [x] Independent root focused discovery review; 315 fixture/CI-tool tests passed together.
      Earlier four worker-run failures did not reproduce; cause unconfirmed. No product qualification.
