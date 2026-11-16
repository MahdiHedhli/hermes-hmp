# Source verification — November16, 2026

Scope: pure internal capability observations, **not a native runtime or mobile group pass**.
Python3.11.15; exact parser SHA256
`fb8c96120abde3fdcffe182fa72c131c583bc187deb0e41e50d9d41b305f93a8`,
test SHA256 `ffefc61c34c10340397e15cb594454436d49738bdef4f3605926a845e41c529b`.

- 83 focused tests pass, zero failures/errors/skips. Coverage includes native-shaped
  advertisements, all driver/persistence combinations, future additions, missing
  and malformed data, resource limits, non-retention, frozen outputs and foreign
  keys/containers/scalars/query callbacks.
- Removing exact Boolean typing in a disposable module copy causes16 failures.
  Removing the known-vocabulary filter causes five; removing the shallow key
  fence causes two. Each runs the same83 unchanged tests, zero errors/skips.
  The production source was never replaced or edited during causal runs.
- AST-only source comparison verifies19 method names and four feature names from
  Hermes4162ecf11f611400fa6e5c42d2f360188ce50b39 owning source
  `gateway/session_group_controls.py`, SHA256
  `828ba909260d5aa44aa9d631794308421573ebf33b72d7743b35643fa27e0114`.
  This pin is sample attribution, never a runtime admission gate.
- Pinned ruff0.16.9 lint/format, closed plugin surface, private-data scan and diff
  checks pass. The log scanner reports no captured acceptance logs in this tree;
  that is not runtime logging coverage.
- Independent pre-code and final source/security reviews accept this bounded task.
  The pre-code key-collision finding was corrected before implementation. Initial
  lint suffix/format findings were corrected without changing the accepted scope.

The caller must own stable decoded built-in containers through the synchronous
parse and separately bound the frame/decoder. No concurrent-input, native transport,
credential, grant, room lifecycle, Linux, physical, cross-platform or release
qualification is claimed. No runtime caller/importer, registration, dependency,
Store/schema/config or host/device state changes. Full group tasks remain open.
