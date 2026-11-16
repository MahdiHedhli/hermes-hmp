# Read current push registration counts without migrating the store

## Specify and clarify

`hermes hmp push status` returns store_unavailable on the current plugin database:
its readonly count helper accepts only schema3 while Store creates schema4. An
original isolated WAL-count case reproduces exit2 instead of0. Schema4's media
migration adds independent media decision tables/triggers; the legacy/current
base DDL containing every queried push/device field is byte-identical.

Accept these two verified diagnostic formats,3 and4. Keep unknown/old/malformed
format refusal. This is a local SQLite-format guard, not a Hermes gateway-version
allowlist, feature-disable condition or phone eligibility decision. Preserve
minimum native-version/dependency gates for optional configuration loading.

## Plan and security analysis

Change only the format predicate of the existing single committed SELECT. Keep
live WAL reads, missing-SHM refusal, checkpointed immutable reads, query_only,
short connection timeout, fixed booleans/counts/status output and unavailable
rather than zero. No migration/pruning/write, identity/key/token load, network,
provider, grant, model, job, approval ownership or host action. Stored active and
non-revoked counts remain stored state, not delivery eligibility or permission.

No SCHEMA_VERSION/migration change and no automatic acceptance of a future format.
No private config, store path, identifiers, relay URL or errors may reach output.
The legacy3 fixture models the query's metadata/table format only; it is not an
entire legacy-native installation or authority receipt.

## Tasks / acceptance

- [x] Reproduce original failure; inspect schema3/4 source and unchanged base DDL.
- [x] Add causal current/legacy WAL and checkpointed read cases; demonstrate red.
- [ ] Repair the single predicate; run complete diagnostic and related store tests.
- [ ] Verify unknown formats, no migration/authority/network action, unchanged stored
  rows during WAL reads and unchanged checkpointed-file hashes.
- [ ] Independently review source/results and publish focused repair with limits.

Use fresh synthetic test homes. Local Darwin/Python qualification is separate
from native/Linux, installed private source, device and release. Preserve prior
broad-suite failures and test-global filesystem reporting trap as separate work.


## Red reproduction

Original production predicate plus the extended21-case diagnostic file yields
10 failures, zero errors/skips. Both legacy3 positive reads pass; the current4
WAL/checkpointed cases and eight existing current-store diagnostic cases fail.
This reproduces an actual readonly diagnostic defect, not a fixture-only issue.

The WAL path keeps ordinary SQLite read-lock/SHM bookkeeping; it is not a claim
that every file byte or access timestamp stays unchanged during a live read.
Checkpointed immutable-read tests compare the complete fixture file hashes.


## Related migration fixture correction

The first six-file regression run has381 passes and two failures: the genuine
legacy1/2 migration tests still expect literal3 after migration, although Store
now declares and creates4. Their migrated-data, original DDL, controls decision,
foreign-key and idempotent-reopen assertions remain unchanged. Compare the final
metadata with the declared SCHEMA_VERSION rather than the obsolete literal; no
migration code or acceptance of future diagnostic formats changes.
