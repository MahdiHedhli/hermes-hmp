# Read-only push diagnostics

Run `hermes hmp push status` in the default profile's host terminal. It prints:

```text
push_enabled: yes
relay_configured: yes
configured_kid_count: 1
active_registration_count: 0
non_revoked_generation_count: 0
```

These are configuration and stored-state facts. They do not prove relay reachability, provider
acceptance, phone registration, notification permission, or delivery. Push enabled is the literal
host opt-in; a disabled host can still have valid relay configuration. Stored active rows include
rows awaiting expiry cleanup. Generation counts exclude rows for REVOKED devices.

Configuration or store failure prints `unavailable` for that source and the fixed code
`config_unavailable` or `store_unavailable`. Unknown counts are not zero. Exit status is 0 when both
reads succeed, 2 when either is unavailable. Missing/older/newer schema is not migrated. If the
Hermes build lacks the optional pure settings APIs, diagnostics become unavailable; app feature
admission remains governed by each actual feature's APIs and minimum supported version.

The command reads no identity key, prints no identifier, URL, audience, kid, handle, pin, signature,
profile name or dispatch outcome, makes no relay or gateway request, and saves no status file.
It changes no grant, controls decision, registration, expiry, key, or `devices list` behavior.
Native `hermes hmp` startup remains Hermes-owned: its plugin bootstrap can seed SOUL.md on a new
home. The diagnostic bridge requires that configuration bootstrap already be present and refuses
to cause that first import. Its own configuration path accepts only opened regular files, follows
symlinks to regular files as native configuration does, opens nonblocking to refuse FIFO targets
without waiting, and reads at most 1 MiB per file. It uses the native pure expansion/merge/precedence
primitives without loader hooks or recovery logging. Regular file I/O on an unresponsive filesystem
can still stall; this command is not a universal wall-clock timeout for filesystem operations.

A checkpointed store uses an immutable read. A live WAL store uses a read-only/query-only SQLite
connection, retaining committed WAL rows. Missing SHM yields unavailable rather than creating a
sidecar. Existing SHM reader bookkeeping may change; authoritative database data and WAL are not
written, checkpointed or pruned. One SQL statement reads schema and both counters together.

## Source verification

Unit tests use synthetic configuration and isolated schema-3 stores: stored active versus retired
states, non-revoked generation counts, committed WAL rows, no migration/key/authority opening,
checkpointed file hashes, missing SHM, malformed config/store, unavailable optional APIs, and
redacted fixed output. Scratch FIFO and symlink-FIFO tests have a subprocess timeout so a regression
cannot hang the suite. Existing CLI and bridge suites remain the regression gate.

The repeatable isolated native configuration probe is:

```sh
python tools/fixtures/push_status_config_probe.py --hermes-source /path/to/hermes-source
```

Use the supplied Hermes environment's Python. The probe always creates a disposable home and
managed directory, records native bootstrap files separately, compares eight cases with native
configuration primitives, and checks diagnostic file/environment preservation. It loads no gateway,
plugin discovery, hook, live home, provider or network client. A sample is evidence, not a version
allowlist or remote/provider/device qualification.
