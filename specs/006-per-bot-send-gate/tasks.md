# Tasks: per-bot send availability

1. [x] Confirm the live failure class and the distinct roster/send gate call paths without reading or changing live keys.
2. [x] Specify the additive, authorized-only per-bot roster field and conservative legacy fallback.
3. [x] Require the owner switch and target-profile endpoint on both full and guarded send paths.
4. [x] Add server tests for gate bypass, profile scoping, authorization omission, and wire serialization.
5. [x] Add app parser/context tests for per-bot choice, malformed fail-closed value, refresh, and old-HMP fallback.
6. [x] Run full HMP checks (1,182 passed, 10 skipped), Ruff, plugin-surface/log/privacy scans, and stock-base direct-send fixture (8 passed, 16 non-stock cases skipped). App checks follow the pinned commit.
7. [ ] Push focused draft HMP and app PRs with exact base and pin.
8. [ ] Verify on a paired owner device after the separate live host-key repair is approved.
