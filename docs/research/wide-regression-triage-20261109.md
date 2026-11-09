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
