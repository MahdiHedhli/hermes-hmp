# Contract: HMP Server Plugin Module Boundaries (`server/hmp_plugin`)

The module skeleton and the Protocol classes below are created first (task T013). Workers implement
behind them in parallel. Only `bridge.py` may import a Hermes internal; an AST test enforces this
(PR-2, FR-054; `tools/ci/check_plugin_surface.py`). The controller approved three closed
exceptions, each an exact (module, name) allow-list entry in the surface check:

- `adapter.py` may import exactly `gateway.platforms.base.{BasePlatformAdapter, SendResult}` and
  `gateway.config.Platform`, the documented platform-plugin API. The adapter must run on
  unsupported builds, where `bridge.py` is never imported (ruling on T013).
- `identity.py` may import exactly `hermes_constants.get_default_hermes_root`, the documented plugin
  API (PLUGIN) that anchors the instance key. It is accepted on **every** build, including
  unsupported ones, since the listener must serve `/ready` with the instance certificate there. This
  imports `hermes_constants` and its module-level dependencies; that is accepted, because the
  adapter already imports the documented plugin base classes on every build, so it adds no new
  class of exposure (IR-6, ruling option (a); HMP v1 §12).
- `compat.py` may import Hermes modules dynamically, but only inside its dependency probe, and only
  for a build already on the read-compatible list (see "Startup order"; ruling on T013).
- Third-party modules restricted to one file: `qrcode` to `cli.py`, and `yaml` (PyYAML) to
  `routes.py`, imported lazily (specs/005-new-profile-routing). No other module may import either.

The spike is reference only. Code is rewritten and reviewed, never copied wholesale (constitution
VIII).

```text
server/
  pyproject.toml                  # package metadata, test deps (pytest); runtime deps come from Hermes
  hmp_plugin/
    __init__.py                   # register(ctx): register_platform + register_cli_command ONLY
    plugin.yaml                   # name: hmp, kind: platform, version: 1.0.0-f1
    contract.py                   # constants (§13), wire identifiers (V-1), ErrorCode table (ERR-2, ERR-2a),
                                  #   reset reasons, AuthzState, dataclasses for wire bodies
    wire.py                       # I-JSON parsing (TR-9), int typing (TR-10), canonical b64u (TR-11), limits
    crypto.py                     # P-256 SPKI checks (TR-12), transcripts HMP1-* (TR-13), sign/verify,
                                  #   secret_hash, SAS, iid/device_fp, self-signed cert
    identity.py                   # instance key custody, host binding, clone/backup detection, rotation (ID-2, PR7-2, PR7-6);
                                  #   k_grace custody: 32 B, own file, mode 0600, outside every Hermes home,
                                  #   regenerated on rotate-key and on clone/backup/host-change detection (R16, CS-13);
                                  #   custody layout and the server-internal HMP1-HOST input: research R17
    store.py                      # SQLite schema + migrations (data-model.md); the only module that writes the store;
                                  #   also session_refs, other_session_baselines (amendment A1, SES-1a/SES-2);
                                  #   also direct_send_idempotency (amendment F2, DS-3)
    compat.py                     # build identity (git SHA / fingerprint), read_compat_builds.json, dependency probe (GU-2c, ERR-2a);
                                  #   READ_DEPENDENCIES also lists SessionDB.list_sessions_rich/get_session (amendment A1);
                                  #   WRITE_DEPENDENCIES (amendment F2) lists active_session_registry_snapshot and
                                  #   find_canonical_owner, probed only when direct_send's flag is on
    bridge.py                     # the ONLY module importing Hermes internals: read subset + P6 trigger (§12);
                                  #   also list_sessions/resolve_session (amendment A1, SES-1/SES-2);
                                  #   also resolve_bot_chat/registry_snapshot/direct_send_target (amendment F2, DS-4/DS-6);
                                  #   v1.3: list/resolve_gateway_approval, resolve_gateway_clarify,
                                  #   mark_awaiting_text, approval/clarify timeouts, phone session key
                                  #   (function-local, only after the direct-send gate is open)
    direct_send.py                # amendment F2: DS-2..DS-8 orchestration (gate order, guard, idempotency,
                                  #   the api_server loopback call, post-hoc verification). Never imports a Hermes
                                  #   internal itself -- reads bridge.py for Hermes state, and speaks api_server's
                                  #   HTTP contract directly over aiohttp (GAP-2, not a bridge_files concern).
                                  #   v1.3 (§7b AP-1): the loopback URL is /chat/stream, held until the SSE ends;
                                  #   approval.request is stored as it arrives; POST /v1/runs/{run_id}/approval
                                  #   uses the stored run_id. No sync /chat fallback.
    prompts.py                    # amendment F3 (§7b): process-memory prompt rows, answer idempotency,
                                  #   Phone-chat send, adapter hooks. No Hermes import.
    mobile_cron.py                # mobile cron (§7c, CR-1..CR-6): bounded projection and loopback job calls; no Hermes import
    mobile_model.py               # bot default model (§7d, MD-1..MD-3): projection and options loopback call; no Hermes import
    pairing.py                    # P2, P4 (PR2-*, PR4-*), sanitization (PR2-3)
    tokens.py                     # P5 exchange, rotation, retry grace (successor = HMAC over the RAW presented
                                  #   token, length-prefixed; R16, CS-13), family revoke (PR5-*)
    auth.py                       # bearer + HMP-Instance middleware (TR-5, PR5-6)
    reads.py                      # roster (RO-1/RO-2), snapshot (RO-3/RO-4/RO-5), history + resets (RO-6/RO-8), baselines;
                                  #   also list_sessions/session_snapshot/session_history (amendment A1, SES-1/SES-2)
                                  #   and the OD-F11 bot-view selector, _is_bot_view_session (title=="Bot Chat" and
                                  #   hidden; cross-checked against hermes-agent's canonical-chat.ts/bot_mode_probe.py/
                                  #   hermes_state.py, HMP_V1.md §6a SES-7 -- no new Hermes dependency)
    authorize.py                  # P6 outcome table (PR6-*), via bridge
    revoke.py                     # P7-3 self-revoke; operator revoke helpers (PR7-1)
    gate.py                       # GU-2/GU-4 guarantee derivation + write gate (implemented, unused by F1 routes)
    server.py                     # aiohttp app, route table (F1 subset), middlewares: peer policy (TR-4),
                                  #   size limits, rate limits (TR-6), error shaping (ERR-1), compat refusal (ERR-2a)
    request_ctx.py                # leaf module: ServerContext, CTX_KEY, context(), body/response helpers,
                                  #   peer_key, bearer -- imported at module level by server.py, pairing.py,
                                  #   tokens.py and revoke.py so a plugin reload (sys.modules eviction of
                                  #   hermes_plugins.hmp*) cannot split a running app from the CTX_KEY/helpers
                                  #   it was built with (see the module's own docstring)
    adapter.py                    # HmpAdapter(BasePlatformAdapter): lifecycle only (start/stop listener)
    cli.py                        # `hermes hmp …` operator commands (PR1-*, PR3-*, PR7-1, PR7-2, routes add, compat);
                                  #   `pair offer` is one command end to end unless `--no-wait` (owner
                                  #   requirement, 2026-09-27): it waits, shows the expected code and asks
                                  #   "Does the phone show this code? [y/N]" (OD-F7, replacing the typed
                                  #   SAS in this interactive path), confirms or denies, then -- unless
                                  #   `--no-grant` -- offers to allow the phone's served bots and approves
                                  #   their pending `hmp` requests through Hermes's own public CLI as a
                                  #   subprocess (OD-F8), before printing the next steps; reuses
                                  #   `pair list`/`confirm`/`deny`'s own internals throughout
    routes.py                     # `hermes hmp routes add <profile>` (specs/005-new-profile-routing): writes one
                                  #   exact root `gateway.profile_routes` entry only; lazy `yaml` import here only;
                                  #   no Hermes import, no store, no network, no profile config write
    logging_policy.py             # allow-listed log fields (SEC-4, SR-007): plugin logger; aiohttp access log
                                  #   disabled or reduced to method, route template, status, duration; bridge
                                  #   exceptions logged by type only; P6 reply dropped unlogged (CS-22)
    local_media_active_scan.py    # OPTIONAL, inert, unimplemented as a feature: reviewed local-image active-content scanner
                                  #   (stdlib only, Python 3.11+). Imported by nothing at start-up and by no route;
                                  #   only local_media_result.py may import it (local image contract amendment)
    local_media_file_safety.py    # OPTIONAL, inert: reviewed file-safety checks for a future local image reader (stdlib only);
                                  #   no caller, route, claim or manifest uses it yet
    local_media_raster_structure.py  # OPTIONAL, inert: reviewed raster structure validator (stdlib only); no caller yet
    local_media_result.py         # OPTIONAL, inert: bounded result parser wrapping local_media_active_scan; no caller yet.
                                  #   No production module (start-up, reads, compat, server, adapter, registration)
                                  #   imports any local_media_* module; a test pins this
    local_media_registry.py       # OPTIONAL, inert: process-local image ref registry (LM-9; stdlib only, no hmp_plugin imports):
                                  #   lock, TTL 1800 s, 512/4096 LRU, idempotent mint, first-served digest CAS. A registry
                                  #   hit never authorizes a fetch. No production caller, route or module-level instance yet
    read_compat_builds.json       # GU-2c list (starts empty). Entries: {git_sha|null, fingerprint, source_sha?
                                  #   (provenance only), label, qualified_by, qualified_at}; matching per research
                                  #   R8 steps 4-6 (CS-19); plus "bridge_files", the mechanically computed superset
                                  #   of files defining every symbol the bridge reaches (CS-21)
    write_supported_builds.json   # GU-2a write-supported matrix (stays empty in F1)
    direct_send_supported_builds.json  # amendment F2 (DS-2(b)/GAP-2): guarded-write qualification list, distinct
                                  #   from write_supported_builds.json (data-model.md "Direct-send qualification list");
                                  #   starts empty (OD-F3 discipline applied to the new guarantee tier)
    approval_supported_builds.json  # amendment F3 (§7b) approval qualification list (starts empty; bridge_files
                                  #   mechanically computed); independent of the direct-send list
    mobile_cron_supported_builds.json   # §7c exact-build cron qualification list
    mobile_model_supported_builds.json  # §7d exact-build model-management qualification list
  tests/unit/…                    # per module
  tests/integration/…             # real gateway in isolated homes (tools/fixtures)
  HOST_HARDENING.md               # SEC-3 guidance
```

## Key protocols (shape)

```python
class ReadBridge(Protocol):                  # implemented only in bridge.py
    def served_profiles(self) -> list[str]: ...
    def authz_state(self, user_id: str, profile: str) -> AuthzState: ...           # fails closed → UNVERIFIABLE
    def instance_wide_grant(self, profile: str) -> bool: ...                       # PR6-3 note
    def request_authorization(self, user_id: str, profile: str) -> AuthorizeResult: ...  # inert trigger (GU-4 exception)
    def conversation_ref(self, user_id: str, profile: str) -> ConversationRef | None:    # never mints
    def head(self, ref: ConversationRef) -> int | None: ...
    def latest(self, ref: ConversationRef, limit: int) -> list[Row]: ...
    def after(self, ref: ConversationRef, after_id: int, limit: int) -> list[Row] | ResetReason: ...
    def lineage(self, ref: ConversationRef) -> LineageInfo: ...                    # for baselines/resets
    def capability_versions(self) -> Mapping[str, int]: ...                        # GU-2 (gate.py)
    # amendment A1 (session browsing, OD-F9/OD-F10):
    def list_sessions(self, user_id, profile, *, sources_excluded, limit, offset) -> list[SessionSummary]: ...
    def resolve_session(self, user_id, profile, session_id) -> ConversationRef | None: ...

class Compat(Protocol):
    def evaluate(self) -> CompatResult: ...   # SUPPORTED | UNSUPPORTED(build_unsupported|read_dependency_missing)
```

## Startup order

1. `compat.evaluate()` runs **before** anything imports `bridge.py`. It finds the Hermes root with
   `importlib.util.find_spec("hermes_constants").origin`, which imports nothing. Identity comes from
   file reads only. An unidentifiable or unlisted build is UNSUPPORTED at once, with no Hermes
   import of any kind.
2. If the result is not SUPPORTED, `bridge.py` is never imported. The route table keeps only
   `/ready`. Every other path, pairing included, answers `503 other {why}` (ERR-2a). The CLI refuses
   offers.
3. If it is SUPPORTED, the dependency probe (import plus signature shape, no calls) must pass, and
   every reached internal's `inspect.getsourcefile` must be inside `bridge_files`; otherwise
   `hermes_read_dependency_missing` (CS-21). Then the bridge is constructed.

**Matching rule (CS-19; research R8).** A git install is supported only if its resolved SHA equals an
entry's `git_sha` **and** the computed fingerprint equals that entry's. An install without `.git` is
supported only if a fingerprint-only entry (`git_sha` null) has the computed fingerprint; its
`source_sha` is provenance only. A listed fingerprint never qualifies a git install at an unlisted
SHA. Unresolvable git metadata or a missing listed file is unidentifiable, hence unsupported.

## F1 route table

| Method | Path | Clause | Auth |
|---|---|---|---|
| GET | `/hmp/v1/ready` | PR0-1 | none |
| POST | `/hmp/v1/pair/request` | PR2-* | none (offer secret + signature) |
| POST | `/hmp/v1/pair/complete` | PR4-* | none (signature) |
| POST | `/hmp/v1/auth/token` | PR5-* | signature |
| POST | `/hmp/v1/devices/self/revoke` | PR7-3 | bearer + signature |
| GET | `/hmp/v1/bots` | RO-1 | bearer |
| POST | `/hmp/v1/bots/{p}/authorize` | PR6-1 | bearer |
| GET | `/hmp/v1/bots/{p}/conversations/default?limit=` | RO-3 | bearer + per-bot gate (ERR-3) |
| GET | `/hmp/v1/bots/{p}/conversations/default/messages?after=&limit=` | RO-6 | bearer + per-bot gate |
| GET | `/hmp/v1/bots/{p}/sessions?cursor=&limit=` | SES-1 (amendment A1, v1.1) | bearer + per-bot gate; only when `gateway.platforms.hmp.extra.session_browsing` is not `false` |
| GET | `/hmp/v1/bots/{p}/sessions/{ref}/messages?after=&limit=` | SES-2 (amendment A1, v1.1) | bearer + per-bot gate; same kill switch |
| GET | `/hmp/v1/bots/{p}/sessions/{ref}/messages/from-start?limit=` | SES-2a (phone Bot Chat history paging) | bearer + per-bot gate; same kill switch and read limiter; an older HMP has no route |
| POST | `/hmp/v1/bots/{p}/chat/messages` | DS-1..DS-7 (amendment F2, v1.2) | bearer + per-bot gate; **always registered** (unlike SES-1/SES-2's kill switch), answers `503 write_gate_closed` rather than `404` when `direct_send`'s flag is off or the guard/gate otherwise fails closed |
| GET | `/hmp/v1/bots/{p}/chat/messages/by-client-id/{cmid}` | DS-8 (amendment F2, v1.2) | bearer + per-bot gate; always registered, read-only, never re-sends |
| GET | `/hmp/v1/bots/{p}/prompts` | AP-3 (amendment F3, v1.3) | bearer + per-bot gate; always registered; `503 write_gate_closed` when the direct-send gate is closed |
| POST | `/hmp/v1/bots/{p}/prompts/{request_id}` | AP-4 (amendment F3, v1.3) | bearer + per-bot gate; answer is bound to the stored id and the authorized user |
| POST | `/hmp/v1/bots/{p}/phone/messages` | AP-6 (amendment F3, v1.3) | bearer + per-bot gate; Phone chat hand-off (GU-4b), not SUB-1 |
| GET/POST | `/hmp/v1/bots/{p}/jobs` | CR-1, CR-2 (§7c) | bearer + per-bot gate + controls decision; `404` non-owner, `503 cron_unavailable` otherwise closed |
| PATCH/DELETE | `/hmp/v1/bots/{p}/jobs/{job_id}` | CR-3, CR-4 (§7c) | same as CR-1 |
| POST | `/hmp/v1/bots/{p}/jobs/{job_id}/pause` and `/resume` | CR-5, CR-6 (§7c) | same as CR-1 |
| GET/PUT | `/hmp/v1/bots/{p}/model/default` | MD-1, MD-3 (§7d) | bearer + per-bot gate + controls decision; `503 model_unavailable` when closed |
| GET | `/hmp/v1/bots/{p}/model/options` | MD-2 (§7d) | same as MD-1 |

Not registered in F1 (FR-053): lookup (`SUB-1`'s own `by-client-id` route — the original submit path
itself is unregistered too, matching v1.0's write gate that is never open on a supported build),
events (SSE), approvals, clarify, stop. Requests to those paths get `404` and hand nothing to
Hermes. A test asserts zero bridge calls and zero `handle_message` calls. The two amendment A1
routes above follow the same non-registration pattern when the kill switch is off (`server.
build_app` never adds them to the router at all). The two amendment F2 routes above, and the three amendment F3 routes, are the exception to
"not registered": they are always in the router, and a request reaching any of them with the
`direct_send` flag off (or a stale direct-send fingerprint) gets `503 write_gate_closed`, never a
bridge call. The original SUB-1 / SSE / `…/approvals` / `…/clarify` / stop paths stay unregistered.

## Operator CLI (F1 subset)

- `hermes hmp pair offer [--label L] [--user U] [--no-wait] [--no-grant]`
- `hermes hmp pair list`
- `hermes hmp pair confirm <pairing_id> --sas <SAS> --label <L> [--new-user | --user U --yes-share]`
- `hermes hmp pair deny <pairing_id>`
- `hermes hmp devices list`
- `hermes hmp devices revoke <device_id>`
- `hermes hmp instance show`
- `hermes hmp instance rotate-key`
- `hermes hmp compat` — prints the build identity, the list match and the probe result; it never
  prints secrets.

Every mutating command has the TTY and `HERMES_SESSION_*` refusals (PR1-2, PR3-2; mitigations only,
SEC-1).

**`pair offer` is one command end to end (owner requirement, 2026-09-27; compare-and-confirm per
OD-F7, and in-terminal bot access per OD-F8, both 2026-09-27).** After the QR and the offer
details, unless `--no-wait`, the command stays running instead of exiting:

1. It prints "Waiting for the phone to scan… (Ctrl-C to cancel)" and polls the store (the same
   read path `pair list` uses) about once a second for a P2 claim against this offer's own `oid`.
   It stops at the offer's own expiry with a message and the command to make a new offer.
2. Once a request arrives, it shows the sanitized, unverified device name, then the code this
   pairing expects — the same `_sas_of` value `pair list`/`pair confirm` use — large and clearly,
   and asks "Does the phone show this code? [y/N]" (OD-F7). `y`/`yes` confirms through the same
   activation internals `pair confirm` uses (`_do_confirm`); anything else — `n`, a blank line, or
   unrecognised input, which re-asks — denies or re-prompts. This **replaces** typing the full
   20-character SAS in this interactive path: the operator's own visual compare against the
   phone's screen is what HMP_V1 PR4-2's "confirmation" now means here. `pair confirm --sas <SAS>`
   is unchanged: its typed-value constant-time compare, durable mismatch counter and burn limit
   stay exactly as they were, for the non-interactive and scripted path. It stops at the pairing's
   own `confirm_by` deadline with a message.
3. On success it runs the same activation as `pair confirm` (the offer's own `--label`, and its
   intended `--user` if one was given, sharing that user's grants automatically since the operator
   already chose it at offer time) and prints "Paired ✓ ⟨label⟩".
4. **OD-F8.** Unless `--no-grant`, the same run then offers to allow the phone's served bots: it
   lists them (from the listener record's `profiles` field — see "Startup order" below — falling
   back to the placeholder next-steps text when the record has none, an older gateway or an
   unsupported build), asks "Allow ⟨label⟩ to use all of these? [Y/n/pick]" (`pick` asks per bot,
   `[y/N]` each), then waits up to `BOT_GRANT_WAIT_S` (90 s), polling every
   `BOT_GRANT_POLL_INTERVAL_S` (2 s) for this user's own pending `hmp` requests on each chosen
   profile via `hermes -p <profile> pairing list` (the app auto-sends P6 `authorize` right after
   pairing) and approving each with `hermes -p <profile> pairing approve hmp <request_id>` —
   Hermes's own public CLI, run as a subprocess with a fixed argv list, never `shell=True`
   (`cli._default_run_hermes_cli`; S1 forbids importing `gateway.pairing` from this separate
   process). This reverses the earlier rule that the plugin never creates bot grants; it still
   never writes Hermes's approved-users files itself, and it only ever approves a pending request
   that already carries this pairing's own `user_id`. A ✓ is printed per bot as it is approved.
   Bots still waiting at the timeout are listed with the exact single-line approve-all command
   (`authorize.py`'s `approve_command` shape, looped over the remaining profiles) and "tap Request
   access to all on the phone".
5. Ctrl-C at any point leaves the store consistent — an unclaimed offer is left to expire, a
   pending pairing stays for `pair confirm`/`pair deny` — and prints how to resume with the old
   two-step commands. Ctrl-C during step 4's wait only stops waiting; the pairing itself is
   already complete.

`--no-wait` keeps the original print-and-exit behavior, for scripts and for the fixture CLI
(`tools/fixtures/fixture_pairing_cli.py`, which mints its own loopback offer by hand and is
unaffected either way). `--no-grant` skips step 4 only, printing the placeholder next steps
instead. `pair list`, `pair confirm` and `pair deny` are unchanged and remain the fallback the
one-command flow itself resumes into.

**Served profiles in the listener record (OD-F8).** The adapter writes the instance's served
`(profile, display_name)` pairs into the same listener record `pair offer` already reads for `ep`
(PR1-4), from the bridge's `served_profiles()` and `reads._fallback_display_name` — the exact rule
the roster uses. This is best-effort and additive: a build with no bridge (unsupported), or a
bridge call that fails, writes no `profiles` field at all, and an older gateway's record never had
one either; `pair offer` treats both the same, falling back to the placeholder text.

**S1 residual: known plugin-scanner findings.** Approving a pending request from this separate
`hermes hmp` process cannot go through a Hermes internal (S1) — it goes through Hermes's own
public `hermes` CLI, run as a subprocess. Hermes's own plugin installer security scan already
flags two findings for this plugin (`cli.py`'s `dispatch` entry point, and the fixed-path
`subprocess.run` in `identity.py`'s host-id lookup); OD-F8 adds a third, the same shape, in
`cli.py`'s `_default_run_hermes_cli`. All three are the accepted, documented findings a force
re-install (`--force`) is expected to see; see
`docs/research/f1-acceptance/LIVE_LOCAL_PAIRING.md` "known findings".

## Residuals (security review `reviews/security-server-reads.md`)

Findings the review recorded rather than fixed, or whose fix leaves a stated residual. Not new
gaps; each is either inherent to the SEC-1 operator boundary or a Hermes-side dependency HMP
cannot close from its own code.

- **SR-7 (SEC-1 residual): listener-record redirect.** Same-user code can still write a listener
  record (`listener.json`) naming any tailnet host and port, alongside the public `iid` --
  `read_listener_record`'s directory-safety, `O_NOFOLLOW`/`fstat`, mode/uid and live
  `/ready`-plus-pin liveness checks (SR-7) all defend against a *stale* record (a reused pid, a
  swapped file, a symlink), not against a same-user attacker who writes a *fresh*, fully
  consistent one. `pair offer` would then derive `ep` from that record and mint a QR pointing the
  phone at it. Impact stays bounded by the client's SPKI pin (TR-2): the handshake fails before
  any P2 byte crosses the wire, so the pairing secret `S` is never disclosed to the redirect
  target. Same-user code can already read the private key directly (SEC-1's own boundary), so
  this adds no capability beyond redirect/DoS of a single pairing attempt. Mitigation stays what
  SEC-1 already states: the boundary is the Hermes OS-user account, not this file.
- **SR-10 (HERMES_API_GAP; Hermes-side): per-bot pairing-store fallback.** Hermes's
  `_pairing_store_for` (`gateway/authz_mixin.py`) falls back to the global pairing store when a
  profile has no entry in `pairing_stores`. An approval on the default bot then also authorizes
  the user on any profile missing its own store. The bridge correctly mirrors whatever Hermes
  itself decides (PR6-1), so this is not an HMP defect, but OD-5 per-bot isolation depends on
  Hermes populating a store for every served profile, and the compat/canary probe cannot detect
  the fallback (it is a routing decision inside Hermes, not a signature or file-list mismatch).
  Add "every served profile has its own pairing store" to the GU-2c qualification checklist for
  each build.
- **HERMES_API_GAP (host-side): process-wide client-trust injection breaks plugin TLS servers.**
  Some Hermes builds install platform client trust for the whole process at CLI start
  (`truststore.inject_into_ssl()`, which replaces the `ssl.SSLContext` module global). Every
  `ssl.SSLContext(...)` a plugin creates afterwards, including a *server* context, is then the
  injected client-trust class. On macOS that class verifies the (absent) client certificate
  against the platform store on every server-side handshake and fails with `errSecParam`, so a
  plugin's TLS listener serves nothing. While the injection is active, the stdlib `SSLContext`
  property setters also recurse forever, because they resolve the replaced global. A pin-only
  client context gets a platform-trust evaluation it did not ask for, which fails for a
  self-signed certificate even with `CERT_NONE`. Hermes offers plugins no documented way to get
  an unpatched context, or to opt out of the injection. HMP works around it on its own side,
  without importing Hermes internals (branch `f1/fix-truststore`). `identity.new_stdlib_ssl_context`
  builds the listener context, and `pair offer`'s SR-7 liveness client, from the standard
  library's own class, found by identity in the MRO rather than through the global. It writes
  their settings through the C-level `_ssl._SSLContext` descriptors. The listener's TR-1
  configuration is unchanged. `server/tests/unit/test_tls_trust_injection.py` asserts both
  contexts on real handshakes, with and without the injection. The residual: a future host change
  that patches the stdlib class itself, or `ssl.SSLObject`, is outside this workaround. The GU-2c
  self-check (`tools/compat/run_matrix.py`) on that build would then fail, as it did for the
  owner-local build before this change. The generic ask upstream
  is to keep trust injection to client contexts, or to give plugins an unpatched server context.
  Not filed upstream.
- **SR-11 (test hygiene): the CS-21 reach test is name-based, not receiver-typed.**
  `server/tests/unit/test_bridge.py`'s `_attribute_calls` (feeding `test_reached_methods_match_
  the_source`) matches attribute access by the LOCAL VARIABLE NAME it is called through (`runner`,
  `adapter`, `session_store`, `db`), not by what that name actually refers to. A future
  `self._adapter.foo()`, or any renamed local, would escape it undetected. `bridge.py`'s current
  reach is correct (verified by hand in the review); the test's precision is a residual to
  tighten, not a live gap. Suggested fix: flag any `Attribute` node on `self._adapter`, on
  `self._hermes` call results and on values returned from `REACHED_METHODS`-table calls, and
  compare `(receiver, method)` pairs against `compat.READ_DEPENDENCIES` instead of bare names.
