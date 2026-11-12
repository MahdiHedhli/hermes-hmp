# Read-only media inspection

Issue: #147. Base: HMP 9ab2695. This changes no wire protocol or permission.

`devices media-read` must inspect existing authority without constructing Store,
initializing state, migrating schema, or changing decisions. Preserve its JSON,
identity/custody, listener liveness and authenticated operator checks. Keep the
live decision/database comparison and final identity recheck. Missing, stale or
invalid state refuses. Do not add compatibility/profile-count setup gates.
Grant/deny retain their existing confirmation, mutable Store and CAS lifecycle.

A read-only connection sees committed WAL state. Without WAL, use immutable
read-only access to avoid side files. With WAL require existing shared memory;
refuse instead of creating it. No claims of physical/runtime qualification.
