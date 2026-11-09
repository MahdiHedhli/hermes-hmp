# Wide regression triage — November 9, 2026

Broad unit source `428583f`: 8,244 collected top-level cases; JUnit additionally records 190 passing subtests (8,434 nodes total). Result: 47 failed, 8,182 passed, 15 skipped. This is not qualified. Native integration fixtures were collected separately, not run.

Private immutable broad results: `/private/tmp/hermes-qa-all-unit-lifecycle-regression-current-q2gkcaqg/receipt.json`; classification `/private/tmp/hermes-wide-regression-triage-20261109.json`. Failed temporary fixtures and all logs/XML/receipts remain retained. Successful fixtures were disposed by pytest's documented failed-only retention policy. Initial directory selections were refused by runner guards before pytest execution; the executed selection is an explicit file list.

Repair `7f3ac82`: readonly push diagnostics now accept exact known schema 3/4; schema 4 adds media decisions without changing queried push tables. Unknown/future schemas still refuse. No migration, keys, authorization or write path was added. Two immutable byte-before/after cases cover the common push-table query; schema 3 positive uses a schema-4 fixture relabeled 3, not independent historical fixture validation. One synthetic adapter-ordering port was brought up to the retained drain interface with a stop assertion. Finite independent read-only review accepted this delta.

544 selected lifecycle/push-status/approval cases pass unchanged on both pinned runtimes:
- `/private/tmp/hq-ri97kp0u/receipt.json`
- `/private/tmp/hq-j_htmjkj/receipt.json`

Seventeen original fixture failures were caused by the runner's long Unix socket root. A short private owned test root fixes the harness; production path bounds remain unchanged. All 67 cases in the three affected fixture modules pass on both pinned runtimes:
- `/private/tmp/hq-kdk9wwbf/receipt.json`
- `/private/tmp/hq-ncbusa2t/receipt.json`

Nineteen original failures remain unresolved: frozen registry digest (1), local-media source inverse/route-binding claims (13), legacy push migration schema expectation (2), S5 foreign genuine media reference expectations (2), exact module manifest (1). Do not repin or waive these automatically; compare actual source/authority contracts and obtain bounded review. There has been no full rerun after the repair; no claim that these are the only possible current failures.

Fresh readonly device inventory: iPad connected/developer services available, installed `com.hermesbotmobile.app` build `2026110702`; Android Gemini connected, beta code 6 with APK SHA-256 `ee3685771630ced73a8a671b8b2bb0faef65361dba225f87680d63b7cc4446fa`; exact iPhone 15 pairing device is disconnected. Device metadata is not UI/feature qualification. No launch, install, app-data access, permission/provider/host change occurred. Source/archive comparison for the Android hash remains distinct from version metadata.

Next: reconcile remaining contract/security-sensitive broad failures before whole-plugin qualification; preserve native media authority/migration and physical/release gates. Visible local sections/static icons remain in mobile candidate source, not freshly device-qualified by this work.

## Reviewed provenance, migration and historical-composition reconciliation

Test-complete source `1afc81853cae00a24b0ec787182a58b29eda67a6` changes no production authorization logic. S5 fixtures now read the actual current permission generation, explicitly reject unversioned/wrong-generation callers, and reach the original native kind-forgery refusal. No explicit grant is created; legacy effective authority is not mislabeled as explicit allowed=True. The initial incorrect fixture assertion is retained in `/private/tmp/hq-it5b8igu/receipt.json` (622 passed, 2 failed).

Legacy schema1/2 fixtures now expect target4 and additionally prove zero explicit media decision rows, allowed=None/revision0, retained exact legacy controls, and unchanged prior data/DDL/audit/FK/idempotence checks. This is not full migration/rollback qualification.

Historical source checks retain their original hashes. Exact test-only inverse blocks project adapter→f7f5084, server→5e247a64, registry→8fb2c99; adapter still passes unchanged readiness/AT1 inverses to the original f8a5... hash, registry retains original b49e... hash. Canonical candidate hashes are checked. Unknown edits inside exact blocks refuse; outside edits survive to the parent gates. Duplicate/relocated owner captures and ordinary method/import mutants remain detected. Eleven new modules are individually documented and enumerated; there is no runtime version allowlist or broad module glob acceptance.

Review caught a byte-reader normalization regression in the first candidate `4f5fafa`, despite 1,121 tests passing. That result is not accepted as byte-fence proof. Final `1afc818` uses the same read_bytes().decode('utf-8') reader in all affected gates; six actual-file CRLF/lone-CR cases prove exact byte roundtrip and old-hash mismatch or inverse refusal. Independent read-only review accepted the corrected source-composition witness, not semantic/native qualification of all functional deltas.

1,127 selected cases now pass unchanged on Python3.14.9 and3.11.15, zero failures/errors/skips:
- `/private/tmp/hq-hm_em6jb/receipt.json`
- `/private/tmp/hq-ug0roqum/receipt.json`

Together with the prior 67-case short-path checks, selected checks address all original47 failure cases. A complete unit rerun remains required; do not infer no new failures or release readiness. Original15 skips comprise14 missing native build/extraction/probe prerequisites and1 Linux-only own-process case on this Mac. Native integration fixtures remain unexecuted. Builder allocation ownership, native media publication/migration and device/release gates remain separate. No deployment or device/permission change occurred.
