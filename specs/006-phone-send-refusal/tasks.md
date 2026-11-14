# Tasks: phone send definitive refusal

- [x] Write spec, plan, tasks, checklist.
- [x] Runtime: exact-`False` refusal with `applied:false`; non-bool results are unknown.
- [x] Contract AP-6 text.
- [x] Tests: known false, replay without redelivery, exact true, None, exception, session key,
      probe list, malformed results, gate order, bridge unaccepted-event path.
- [x] Root: pinned Ruff 0.16.9, surface and staged privacy checks passed; independent source review
      checked exact-boolean classification and the actual Hermes admission-ticket call path.
- [x] Root full CI-equivalent Python 3.14 suite: 1,388 passed, 12 skipped, one existing aiohttp warning.
- [ ] Real gateway matrix against this exact runtime diff; device and release security gates.
      The matrix on the older approval-gate candidate does not qualify this runtime amendment.
