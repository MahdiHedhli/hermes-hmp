# Approval metadata validation overhead

The original normal operator/cache-input test exceeds its unchanged60-second deadline. An interrupted20-second diagnostic on962b38ca observes83,422 API-state checks and11,595,589 registry-key generator calls. These are repeated data checks, not native reads/admissions; this does not establish the sole timeout cause.

Replace only the three current dictionary-key generator scans in gateway_approval._api_state with inline loops. Keep exact dictionary/type/descriptor checks, each scan before its corresponding lookup, existing field checks and every seal/current-binding call. No saved-good cache, registry-length shortcut, second-seal removal, deadline increase, new authority or live state change.

Acceptance: complete original metadata/import-order cases and44 fixed operator cases; added collision-bearing str-subclass controls for registry/module/spec; actual isolated operator mutation between retained-binding and closed-custody seals; negative omission controls. Independent source and terminal review. A microbenchmark may measure only the helper; full cache/operator/native/host/phone and release qualification remain separate.
