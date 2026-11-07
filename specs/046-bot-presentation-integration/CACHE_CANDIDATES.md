# Source-cache location planning

Status: independently reviewed pure path-mapping DATA. This does not observe a
cache, prove absence or source equivalence, select loaded code, or admit runtime.

planned_cache_path accepts only exact bounded primitives for canonical selected
POSIX source, original interpreter tag/optimization/cache-prefix values and,
when required, original observed CWD. It calls neither a loader nor an OS API.
It produces the canonical absolute location a standard CPython source loader
could use, with a redacted representation and explicit CWD-dependency metadata.
Those inputs are DATA, not operator approval or authoritative observations.

Both normal and root-level sources, empty basename .py, dotted/space/Unicode
names, no/root/custom cache prefixes and numeric optimization levels are covered.
For /root.py, CPython may return a relative cache path; the mapping resolves its
actual location against the supplied original CWD. Therefore parity means equal
absolute location, not necessarily equal raw text from cache_from_source.
The implementation is POSIX-specific; no Windows path or loader policy is claimed.
Foreign values, bool/negative/unbounded optimization, slash/ASCII-control tags, noncanonical
or private resource paths refuse without invoking coercion/equality hooks.

## Mandatory pre-IO integration

Retain original entry/recipe/plugin/interpreter/cache-policy context BEFORE the
combined entry file IO plan is constructed. Capture original CWD through a fixed
owned native read only where resolution depends on it; do not invalidate
CWD-independent absolute candidates merely because unrelated code changes CWD.
Keep OS reads out of callback-free lineage seals. Rejoin held allocations after
callbacks and before publication, with sticky own-context refusal and no recapture.

The complete source/cache candidate set, declared cache files and unresolved
absence probes must be reserved in the SAME original aggregate plan/counters
before IO. A completed artifact owner cannot be extended or receive a fresh
allowance. Later continuation must retain that actual original context.

Distinguish an individually declared cache with its original receipt/header,
absence established by an actual original exhaustive tree observation, and a
loose candidate still requiring owned no-follow absence observation. An undeclared
outside-tree candidate is not absent. No path helper or caller flag can replace
those facts. Current plugin/import machinery, archive/member, ABI/library and
listener/native/key/physical character qualification remain separate requirements.

Tests compare actual isolated CPython cache_from_source locations after absolute
resolution; they load no planned candidate. They do import ordinary test/helper
and interpreter code, so this is not a claim that Python never reads bytecode.
The pinned local3.14.9 source and actual3.11 API were inspected for the root edge.

The original context retention component is now source implemented in
[CACHE_CONTEXT.md](CACHE_CONTEXT.md): it attaches to the fixed base plan/inputs
before IO allocation. Actual cache/absence acquisition and admission remain open.
