# C6 evidence: history of a profile without its own multiplex flag

Status: **root-reviewed fixture evidence.** Root independently reproduced all seven cases with
zero skips on 2026-09-30 (106.74 s; 81 pre-existing pytest temporary-directory cleanup warnings).
The profile/history preservation assertions and before/after source binding passed. This refines
open item C6; the remaining disposable-host gateway-loop and authorization qualification stays
unchecked in `tasks.md`.
Nothing here is a release certification, a read-compatibility manifest change or an approval.

## Question

On Hermes build `ca705dbf7ef86425b381b542712aff310f1ee52c`, with the root multiplexing and a
named profile whose own `gateway.multiplex_profiles` is absent or false: can HMP read that
profile's history, after the route helper wrote only the exact root route?

## Source binding

The Hermes source is an archive, not a git checkout, so `git_sha` is not observable and no SHA is
attested from the tree. The binding is the read-bridge fingerprint plus a digest of the whole tree.

| Item | Value |
| --- | --- |
| Read-bridge fingerprint (`compute_read_bridge_fingerprint` over the committed `bridge_files`) | `d45f9a132819e7b18c9a653323409f386ff272e1824b90d0899cf3d45f11f627` |
| Same fingerprint recorded for the `omarchy` candidate in the owner-local matrix (label, fingerprint, `source_sha` provenance, `qualified`, `selfcheck_ok`, `read_suite_ok` only were read) | equal; `source_sha` there is provenance and plays no part in matching |
| Source tree digest (regular, non-symlink files except `.venv`, `__pycache__`, `.git`, `node_modules`; `path`, size, bytes) | `4cff27fe80ccdbf092fecce4d95d6a1a41ce3ba490add244a155c4196a82c12e` |
| Before and after the fixture run | identical (asserted by the module fixture) |
| Interpreter | the source's own `.venv/bin/python` (Python 3.14) |

The read fingerprint omits `session_recovery.py`, `session_persistence.py` and
`session_identity.py`, which decide the key namespace and the store a key resolves to. The tree
digest covers them. The owner-local matrix file was not dumped; no private home or session value
was read.

## What was run

- Worker: `tools/fixtures/flagless_history_worker.py` (test tooling; the plugin never imports it).
- Test: `server/tests/integration/test_flagless_profile_history.py`, 7 tests: the binding test plus
  three scenarios, each for own flag absent and own flag false.
- Each child is a fresh process with an isolated `HERMES_HOME` and `HOME`, a minimal environment
  (no inherited `HERMES_*` or `XDG_*`), non-local sockets refused and counted, and
  `TIRITH_ENABLED=false`. Every child reported zero blocked network attempts and no runtime
  bootstrap directory. No model turn, no credential, no grant, no live home, no SSH.
- Real Hermes: `load_gateway_config`, `GatewayRunner`, `SessionStore` (new process, loaded from
  disk), `SessionDB`, `canonical_identity`, `build_session_key`, the route matcher through the
  real `BasePlatformAdapter.build_source`, `profiles_to_serve`, and the real `HermesReadBridge`.
- Doubles, all unrelated to the thing under test: an `hmp` platform registry entry, a no-network
  adapter subclass, and the HMP chat-id directory. The authorization gate is not exercised.
- Real route helper (`hmp_plugin.routes.add_route`) in the test process, with a full tree snapshot
  (bytes digest, size, mtime, inode, mode, for every entry) of the profile before and after.
- Messages are synthetic (`synthetic message N`); session ids are reported only as truncated
  digests, compared inside the test.

## Results

Identical for own flag absent and own flag false.

| Surface | A: routed shared store | B: earlier standalone history | B then a routed conversation |
| --- | --- | --- | --- |
| Session key namespace | `agent:<profile>` | `agent:main` (legacy) | routed: `agent:<profile>` |
| 1. Canonical conversation (`conversation_ref`, `lineage`, `latest` = snapshot, `after` = history) | resolved; 4 rows, history 4, lineage 4, head is the newest row | **not resolved**; empty snapshot and empty history | resolved to the new routed session only; 4 rows |
| 2. Id-addressed session read (`list_sessions`, `resolve_session`, `lineage`, `latest`) | listed, resolves, 4 rows | listed, resolves, **4 rows** | both sessions listed; old one resolves with 4 rows |
| Phone list visibility (`own session or hidden "Bot Chat"`, the predicate `Reads.list_sessions` applies) | visible | **not visible** | new visible; old **not visible** |

What this shows:

- **A passes on both surfaces.** History the root gateway creates for an exact routed source is in
  the profile's own `state.db` and is found by the routed key. The profile's own flag is not needed.
- **B does not pass the canonical read.** A standalone gateway of the profile keys in
  `agent:main` (its `canonical_identity` is not multiplexed), and stores the routing entry in the
  profile's own index. The bridge builds an `agent:<profile>` key and looks it up in the root's
  shared `SessionStore`, so it finds nothing and the Phone sees an empty conversation. No error is
  raised: the read is empty, not refused. The earlier rows are intact in the profile's `state.db`.
- **B's rows are reachable only by session id**, and the Phone's list filter does not show them.
  The id-addressed read works at the bridge; whether any Phone flow supplies that id is not shown.
- **B then A.** The first routed conversation creates a new session. Hermes itself logs that it
  ignored the `agent:main` row for the `agent:<profile>` key because it belongs to a different
  profile. The canonical read then shows only the new session; the earlier history stays in the
  database, unlinked.
- The route helper changed no profile byte or metadata (profile tree identical, 27 entries in B,
  2 in A); in the root tree only the directory entry, `config.yaml` and its backup changed.
  Neither the seeding nor the reads changed the profile's own `config.yaml`.

## Gaps and limits

1. **Concrete gap.** Existing history from a standalone profile gateway (origin B) is not readable
   by the canonical Phone read on `ca705` after route-only preparation. Route-only preparation does
   not make every existing history accessible. A safe upstream/HMP contract for legacy-namespace
   history is still needed. This fixture does not prove a migration design; profile flag changes
   and history rewrites are not authorized repairs and were not performed.
2. Only one conversation origin per case and one user/chat. Compression lineages, archived or
   hidden sessions, other platforms' history, a flag set to true, and profiles with the launch
   profile's own name are not covered. Other builds are not covered.
3. The authorization gate, Phone transport and the live gateway loop are not exercised.
4. "Own-default Phone read" is interpreted as the canonical default conversation (surface 1) next
   to the separate id-addressed session read (surface 2). If root meant something else, say so.
5. A real gateway run on a disposable host remains the final check; this fixture builds the
   runner and store from native code but does not run the gateway loop.
6. Network isolation here is test instrumentation of Python `socket.connect`, not an OS network
   sandbox. It allows Unix-domain sockets and refuses IP connections; it does not instrument
   `connect_ex` or datagram sends. No gateway loop or model turn runs, the optional downloader is
   disabled, and the fixture recorded no attempted IP connection through that guard.

## Reproduce

```sh
HMP_FLAGLESS_FIXTURE_SOURCE=<hermes source with .venv/bin/python> \
HMP_FLAGLESS_FIXTURE_FINGERPRINT=d45f9a132819e7b18c9a653323409f386ff272e1824b90d0899cf3d45f11f627 \
uv run --frozen --project server --extra dev pytest \
  server/tests/integration/test_flagless_profile_history.py --import-mode=importlib -v -rs
```

Without `HMP_FLAGLESS_FIXTURE_SOURCE` all seven tests skip. The evidence run must show zero skips.
The run takes about 90 s, most of it the source tree digest.

## Sandbox note

Fresh Hermes homes start a background download of an optional security scanner at gateway
construction (`tools/tirith_security.py`, which stages a package-manager runtime). The worker
disables it with `TIRITH_ENABLED=false` and refuses non-local sockets; each child records that
no attempt was made and no runtime directory appeared. No dependency was installed into the
Hermes source.
