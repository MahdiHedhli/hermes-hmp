# Local generated-media delivery paths: source census (2026-09-30)

Read-only discovery for root review. Not a design, not a wire shape, not a qualification. Root owns
shared contracts and bounds; root security review is mandatory before any implementation. Upload
(spec028) is out of scope except where noted.

**Revision 2.** Applies the Opus review (reviewed this note at SHA-256 `b92cec46…1308`) and the root
decisions in `LOCAL_OUTPUT_MEDIA_ROOT_DECISIONS_2026-09-30.md`, and adds the source reads S1-S5 and a
fixture plan. **No local-media feature works today and nothing here was run.** Every claim is a source
observation of the pinned installed tree unless it says otherwise. Statements in revision 1 that
treated same-profile planted files as an open blocker, called row evidence "not producer proof" as if
that decided the route, or asserted that the O15 truncation hits `image` are corrected below
(sections "Trust framing" and "Corrections to revision 1").

## Binding and method

| Item | Value |
| --- | --- |
| HMP worktree | `docs/local-media-delivery-discovery`, base `9d91ca1` |
| Hermes read | installed tree at `8afaab3703e336d72a72c812dd2dd249f04f166a` (`git status` clean), read as text only; no CLI, import or runtime |
| HMP call paths | `f4730ebb901933f34c69c609e718f3984c6e62d9` (`hmp-seed-timeout-diagnosis`), read only via `git show` (`server/hmp_plugin/*`) |
| Archive `ca705` | **not read.** Of 17 files hashed, 12 differ from the installed tree (`gateway/run.py`, `run_turn.py`, `run_turn_runner.py`, `platforms/base.py`, `platforms/api_server.py`, `tools/image_generation_tool.py`, `agent/image_gen_provider.py`, `agent/video_gen_provider.py`, `agent/session_persistence.py`, `hermes_state_messages.py`, `model_tools.py`, `hermes_cli/web_routers/files.py`, `gateway/platforms/api_server.py`). The prior fixture ran on the archive, so its results do not transfer. Every claim below is about the installed tree until the archive is re-censused |
| Runtime probes | **none run.** Everything below is a **source observation** unless labelled otherwise. No controlled runtime result is claimed |
| Not read | `hmp-flagless-history`, `hmp-new-profile-routing` were only checked for how HMP resolves a profile home (`bridge.py:604`); their evidence notes were not relied on |
| Revision 2 inputs | Opus report `/private/tmp/hmp-local-media-opus-review-worker.out`; root decisions `/private/tmp/hermes-mobile-plus-media-plan/docs/architecture/LOCAL_OUTPUT_MEDIA_ROOT_DECISIONS_2026-09-30.md`. Source reads S1-S5 used `git grep` and `sed` over the installed tree at `8afaab37` only (no import, no execution, no network, no upstream fetch). HMP `bridge.py` was re-read from `f4730ebb` via `git show` |

`AGENTS.md` is not in the HMP worktree; the file read was the Hermes tree's own `AGENTS.md`, which
does not govern this note. Line numbers are in the pinned trees above. Paths are relative to the
Hermes root unless prefixed `hmp:` (= `server/hmp_plugin/`).

## Source observations

### Producer: what `image_generate` returns

- O1 `tools/image_generation_tool.py:758` `_handle_image_generate` dispatches plugin provider, managed
  route, then in-tree FAL, then `_postprocess_image_generate_result` (`:330`).
- O2 The in-tree FAL path puts the **remote URL** in `image` (`:476`), not a local file. A local
  path exists only when a plugin provider materialises bytes: `agent/image_gen_provider.py:75`
  (`save_b64_image`) and `save_url_image` write `$HERMES_HOME/cache/images/` through
  `agent/provider_media.py:31` (`<prefix>_<ts>_<uuid8>.<ext>`). The provider decides the `image` string;
  nothing in the base class constrains it to the cache.
- O3 `_postprocess_image_generate_result` (`:330-362`) adds `host_image` / `agent_visible_image` only for
  non-local terminal backends. `agent_visible_image` is a container/remote path, never a host path.
- O4 The result JSON shape (`success`, `image`, `host_image`, `agent_visible_image`) is **not documented**.
  Documented: files are saved to `cache/images/` (`website/docs/user-guide/features/image-generation.md`,
  "saved to"), and a bare absolute path in reply text is delivered by design
  (`.../deliverable-mode.md:16`). So the field names are private internals.
- O5 Video: `agent/video_gen_provider.py:278` returns `video` (a cache path under `cache/videos` or the bare
  URL on a failed save). `video_generate` is **not** in the gateway auto-append allowlist (O7), so native
  never adds a tag for it; the model must write one.

### Gateway: current-turn append

- O6 `gateway/run.py:1388` `_AUTO_APPEND_MEDIA_TOOL_NAMES = {text_to_speech, text_to_speech_tool, image_generate}`;
  `:1418` path fields `("host_image", "image", "agent_visible_image")`; `:1434` `_collect_auto_append_media_tags`
  maps `tool_call_id` to tool name from assistant `tool_calls` (`gateway/media_repair.py:34`) and reads
  only current-turn rows (slice at `history_offset`; full scan with path dedup when compression shrank
  the list).
- O7 Append is skipped entirely if the final text already contains `MEDIA:` (`gateway/run_turn_runner.py:1861`).
  A reply that mentions some other MEDIA tag therefore loses the generated image.
- O8 The append changes `final_response`, i.e. the **delivered** text (`run_turn_runner.py:1994`). The durable
  rows come from the agent's own messages (`gateway/run_turn.py:1866`, `:1900`; the fallback branch
  writes `response` only when there are no new messages). Reading the source, the appended tag is not
  in the stored assistant row; the stored evidence is the assistant text as the model wrote it plus
  the tool row. **Not proven at runtime.**
- O9 *(superseded by P1 below.)* Desktop turns do **not** use the gateway turn runner, so O6-O8 (auto-append)
  do not apply to them. The Desktop client renders from the `image_generate` tool-call result
  (`apps/desktop/src/lib/generated-images.ts:17`) and reads local files through Electron IPC
  (`apps/desktop/electron/hardening.ts:552`), so it is a local-filesystem consumer.

### Native extract, filter, validate

- O10 Delivery: `base.py:4206` `_deliver_media_attachments`; images go through `send_multiple_images` (`:2920`)
  as `file://` URLs to `send_image_file` (`:3166`); video to `send_video` (`:3127`); everything else to
  `send_document` (`:3134`). The base defaults for those three are a **failure notice** with no
  file (`_send_media_fallback_notice`, `:3011`).
- O11 `validate_media_delivery_path` (`:1106`): default mode accepts any existing regular file outside a
  credential/system denylist. Allowed roots (`:850`) include `_profile_cache_roots` (`:795`), which
  enumerates **every** `<root>/profiles/*/cache/*`. Strict mode is opt-in. This is a leak guard for
  chat platforms, not authorization: it does not know which profile, chat or turn a path belongs to
  and by design accepts other profiles' caches. It cannot be reused as HMP profile authority.
- O12 Policy comes from process env or, under multiplexing, the routed profile's config
  (`gateway/media_policy.py:36-52`). Neither is an HMP authority.

### Outbound adapter identity

- O13 Metadata handed to `send` and the media senders is `_thread_metadata_for_source` (`base.py:114-139`):
  `thread_id`, platform-specific routing keys, and `hermes_profile` when the source carries one. There
  is **no session id, turn id, tool call id or durable row id**. `chat_id` is the only HMP-meaningful
  key; `hmp:adapter.py:428` `send` takes text and `prompts.py:664` `on_send` stores an observation of
  text only.
- O14 `HmpAdapter` (`hmp:adapter.py:214`) does not override `send_image_file`, `send_video`, `send_document`.
  Today a Phone turn that produces an image gets the base failure notice. No source path today puts
  bytes or an attachment identity into the Phone store.
- O15 `hmp:contract.py:636` `TOOL_OUTPUT_CAP = 4000`; `bridge.py:824` caps tool-row text before it is returned
  and keeps no uncapped copy. **Narrowed in revision 2 (S4):** `success_response` emits `image` before
  `prompt` (`agent/image_gen_provider.py:98-113`), so on the local backend `image` sits near the start of
  the JSON and a long prompt does not push it past the cut. The truncation risk is for `host_image` /
  `agent_visible_image`, which `_postprocess_image_generate_result` appends after `prompt` with `setdefault`
  (`tools/image_generation_tool.py:360-361`, non-local backends only), and for provider `extra` keys
  (for example openrouter `additional_images`, `plugins/image_gen/openrouter/__init__.py:489`). The earlier
  claim that `image` itself is pushed past the cut is withdrawn. `TOOL_ARGUMENTS_CAP = 500` likewise
  compacts assistant call arguments (`contract.py:635`); call `id` and `name` survive (`contract.py:640`,
  `WireToolCall`). Parsing inside the bridge before the cap is still required: a capped row is not JSON
  and the wire row cannot be re-parsed afterwards, so a capped row yields no artifact.

### Durable rows

- O16 Tool rows persist `tool_name` and `tool_call_id` (`agent/tool_dispatch_helpers.py:453`;
  `agent/session_persistence.py:212`); assistant rows persist `tool_calls` JSON. The tool JSON is stored as
  returned (`image_generate` is not wrapped as untrusted, not spilled while small). Multimodal content
  becomes a `[screenshot]` summary (`session_persistence.py:108`), which loses any path.
- O17 `SessionDB.get_messages` (`hermes_state_messages.py:1161`) returns `id`, `role`, `content`,
  `tool_call_id`, `tool_calls`, `tool_name`; inactive rows (rewind soft-delete, `:1532`) are excluded by
  default. HMP already reads exactly this through `bridge.py:786` `_db` with a profile home from
  `bridge.py:604` (`runner._routed_profile_home`, compat-gated at `bridge.py:184`).
- O18 `resolve_resume_session_id` (`:1225`) follows the compression chain but skips branch/delegate children.
  Branch seeding differs by surface, see P5. *(The earlier statement that branching copies tool rows was
  too broad: it holds for gateway and CLI `/branch`, not for the Desktop branch.)*

### Canonical ownership and read APIs

- O19 API server: `gateway/platforms/api_server.py:888` `_resolve_media_to_data_urls` inlines images
  (size-capped, extension-limited, native validator) into the **response** (`:3544`, `:3621`). It is a
  delivery transform, not stored, not a read API for history, and not reachable by HMP.
- O20 `tui_gateway/methods_images.py:13` returns data URLs for UI-initiated generation, also response only.
  The dashboard `GET /api/media` (`hermes_cli/web_routers/files.py:251`) serves images from
  `home/{images,screenshots,cache}` of the active profile as data URLs, behind dashboard auth. Roots
  include all of `cache/` (documents, spillover) restricted only by image suffix. It is a Hermes
  dashboard route with a different auth domain than HMP and a broader root; no supported route
  serves a **history row's** media by row identity.
- O21 Caches: inbound images are written to the same `cache/images` (`base.py:617`), so confinement to
  that directory does not separate generated output from inbound attachments. Sweep is a 24h mtime
  prune run hourly by gateway housekeeping (`gateway/run.py:4611`, `base.py:669`); CLI-only installs
  never sweep.

### Documented hook

- O22 `post_tool_call` is a documented observer (`website/docs/user-guide/features/hooks.md:452`) carrying
  `tool_name`, `args`, `result`, `session_id`, `tool_call_id`, `turn_id` and firing inside the producing
  process (`model_tools.py:679`). It is the only documented producer-side signal with identity. HMP's
  manifest forbids hooks today (`hmp:plugin.yaml:2`, FR-054, enforced by `tools/ci/check_plugin_surface.py`),
  so use would need a root contract change. **Revision 2:** under root decision 4 no hook registration is
  justified and FR-054 stays closed. The `post_tool_call` suppression ContextVar is **not** a coverage gap:
  the executor owns the hook for registry tools and suppresses the inner observer
  (`agent/tool_executor.py:1669-1673`, `model_tools.suppress_post_tool_call_hook`). Whether a
  `kind: platform` plugin's hooks load in Desktop or CLI processes was not needed and is not pursued.


## Durable provenance trace (second pass, source only)

Paths relative to the Hermes root. Nothing here was executed; "source shows" means a reading of the code.

- P1 **Desktop turn persistence.** `tui_gateway/prompt_turn.py:739` calls `agent.run_conversation`
  directly; the gateway runner and its auto-append (O6-O8) are not on that path. Phone turns do go through
  the gateway runner. Both end in the agent's own persistence (P2).
- P2 **Row linkage and timing.** The tool row is built by `make_tool_result_message`
  (`agent/tool_dispatch_helpers.py:434`) from the *executing tool's name* and the call id, appended at
  `agent/tool_executor.py:1138`, then flushed by `_flush_session_db_after_tool_progress` (`:194`, called at
  `:1139`) before `tool.completed` is projected to the UI. The flush is one write transaction
  (`append_messages_batch`, `hermes_state_messages.py:364`; `agent/session_persistence.py:258`). If the flush
  fails the turn flags `_incremental_persistence_failed` (`tool_executor.py:207`): a file can exist with no
  row. The assistant call row is written earlier (`session_persistence.py:370` comment: saved before the tools
  ran). Whether Phone native delivery runs after that flush was **not traced**.
- P3 **Spill and wrapper.** `image_generate` is not untrusted-wrapped (`_maybe_wrap_untrusted`,
  `tool_dispatch_helpers.py:549`: `web_extract`, `web_search`, `browser_*`, `mcp_*` only). Results over the
  per-tool threshold (default 100000 chars, `tools/budget_config.py:13`) are replaced by a 1500-char preview
  plus a spill path (`tools/tool_result_storage.py:242`), so a very large result would lose `image` from the
  row. Whether a plugin can register a tool under the name `image_generate` was not traced.
- P4 **Row schema has no provenance.** `messages` (`hermes_state_common.py:415-442`) has no producer, origin,
  digest or file column. A row made by a tool, a branch copy, an import or a compression handoff is the same
  shape.
- P5 **Branch / import / compression / rewind.**
  - Desktop branch (`tui_gateway/methods_session.py:2040`, `:2073`) copies user/assistant text only; no tool
    rows, no `tool_calls`.
  - Gateway `/branch` (`gateway/slash_commands_session.py:37-39`, `:96`, `:1062`) and CLI `/branch`
    (`hermes_cli/cli_commands_mixin.py:209`, `:1431`) copy `content`, `tool_calls`, `tool_call_id` and
    `tool_name`: a copied tool row is indistinguishable from a produced one (new row id, same call id).
  - Import (`hermes_state_portability.py:576`, `:145`) accepts `tool_call_id` and `tool_name` text fields
    from the payload (`:29`); a bundle can carry any tool row.
  - Compression publishes a **new child session** holding the compressed handoff in one write transaction
    (`hermes_state_compression.py:~255-310`); older tool rows stay in the closed parent. Revision 2 (S2):
    handoff messages are inserted as fresh rows from message dicts, and a watermark tail is cloned into the
    child as byte-exact new rows; whether the compressor keeps an `image_generate` call/result pair at all
    was not read and is a fixture question. **In-place compaction was missing from revision 1**: see S2.
  - Rewind soft-deletes (`active=0`) rows at or after the target (`hermes_state_messages.py:1532`).
- P6 **Profile-local cache ownership.** Producers write with `path.write_bytes` to
  `<home>/cache/<kind>/<prefix>_<ts>_<uuid8>.<ext>` (`agent/provider_media.py:31-50`): default mode, no
  exclusive create, no atomic rename, no recorded digest. Inbound images share `cache/images` (O21).
- P7 **Model write access to the cache.** `_HERMES_PROTECTED_SUBPATHS` (`agent/file_safety.py:244`) lists
  `state.db`, `sessions`, `mcp-tokens`, `pairing`, `vault`, `browser-profile`; `cache/images` is **not**
  listed, so the generic file tools may write there unless the opt-in `HERMES_WRITE_SAFE_ROOT` is set
  (`:219`). The terminal approval patterns read (`tools/approval_detection.py:17-37`) do not name `cache/`
  or `state.db`. Terminal backend confinement (local vs container) was not traced by this note. So, on the
  local backend as far as the source read shows, a model with terminal access can create, replace, symlink
  or hardlink files in the same profile's `cache/images`, and it is not shown that it cannot write
  `state.db`. **Revision 2: this is not an open blocker.** It is a consequence of the posture Hermes
  already documents (`SECURITY.md` §2.2: the OS is the only boundary against an adversarial model; §3.2:
  "shell or file tools reaching host state under the local backend" is a consequence of a chosen isolation
  posture, not a vulnerability), and root adopted the existing host-OS/DB/operator-plugin trust
  (decisions doc, "Evidence and trust framing"). The Docker-backend mount behaviour is Opus's reading
  (`tools/environments/docker.py:465-497`, `tools/credential_files.py:243-262`) and was not re-read here.
- P8 **What a Hermes-recorded generation result is.** A tool row plus its assistant call row, written by the
  executor in the selected profile's database, records that Hermes' executor received this string for this
  call id (P2). It is a **Hermes-recorded generation result**, not a cryptographic production claim: it
  does not show that the bytes now at the path are the bytes a producer wrote, that a provider kept the
  string inside the cache (O2), or that the row was not copied or imported (P4, P5). HMP therefore claims
  only "recorded result, confined to the selected profile's cache, and still a valid bounded raster", never
  "these bytes came from that producer". Because the claim is not about the producer's bytes, it does not
  need a producer digest, exclusive create or a registration hook to keep the *current* grant boundaries.

### Trust framing (root-adopted) and the boundaries HMP still enforces

Revision 1 mixed two different questions. They are separated here.

**Excluded, not defended (existing deployment trust; not a new claim by HMP or Hermes):** compromise of
the host OS account, an adversarial model with unrestricted host execution, tampering with `state.db` by
such code, and operator-installed plugins (arbitrary code under operator review, `SECURITY.md` §2.5).
Under this trust, a model that plants a raster in its own profile's cache gains nothing it could not get
by reading any account-readable file and sending it as text to the same authorized chat (Opus opinion,
adopted by root; not tested).

**Enforced by HMP on its own network surface regardless of that trust:**

| Boundary | What fails closed |
| --- | --- |
| Device / bot / chat | A caller that is not authorized for that bot and does not hold a `session_ref` minted for that session gets nothing; authorization re-runs on every serve |
| Profile and instance | Only the selected profile's own cache (`<routed home>/cache/images`); another profile's cache, another instance's state, or an out-of-cache `image` string is refused |
| Path authority | `MEDIA:` text, bare paths, the native validator and any generic path endpoint grant no read; the path comes only from the executor-written tool row |
| Parser / decoder | File bytes (including provider-downloaded GIF/WebP, `agent/provider_media.py` `save_url`) are untrusted decoder input: strict, bounded raster validation before any decoding or response |
| Confused deputy | Provider bugs, copied/imported/branched rows, stale rows, symlink or hardlink or special files reached through an otherwise valid row: refused by descriptor-confined open, regular-file and `nlink == 1` checks. These are cheap guards, **not** a claim to contain a malicious same-account process |

| Party | Treated as | Consequence |
| --- | --- | --- |
| Host `state.db` | Hermes truth, as for every message HMP already displays | Not defended against code that can write it (excluded above); HMP still rechecks row and database identity per request (S1) |
| Plugins / image providers | Arbitrary operator-installed host code | Can return any path string and name result fields (O2, O4); HMP confines the string and exact-build-gates the shape, and does not trust the file |
| Model | Influences tool arguments and, with terminal/file tools on a local backend, the cache directory | Cannot make `MEDIA:` text or a path a read grant; planting a file in its own profile cache is inside the existing posture |
| Imports, branch copies, rewind, compression | Create, copy, hide or drop rows with no marker (P4, P5, S2) | Row presence is Hermes history, not proof of a new generation; never claim "generated in this child" |
| Producer contract | None documented: field names private (O4), no file mode/exclusivity/digest/atomicity (P6) | The recorded-result claim is a private-shape read; exact-build gating decides acceptance (S4) |

## Transactional primitive in SessionDB (exact lines, or gap)

- Write transaction: `SessionDB._execute_write`, `hermes_state.py:962` (`BEGIN IMMEDIATE`, whole callback
  retried on lock). Private; writes only.
- Read: `SessionDB._read_ctx`, `hermes_state.py:889`, yields a pooled `mode=ro` connection opened
  `isolation_level=None` (`:728`), i.e. autocommit. `_read_one`/`_read_all` (`:1099`, `:1103`) are one
  statement each. A single `get_messages` call (`hermes_state_messages.py:1161`) is one statement for the
  plain path.
- **Gap:** no public or generic multi-statement read-snapshot primitive was found. The only explicit read
  transaction is private and display-specific: `conn.execute("BEGIN")` in `_legacy_display_page`
  (`hermes_state_messages.py:1056-1061`); `_display_messages_from_conn` (`:1145`) expects an already-held
  transaction. `get_messages_around` (`:1206-1219`) issues three statements inside `_read_ctx` with no
  `BEGIN`; the source gives no snapshot guarantee for it. **No source-based claim of transaction
  consistency is made**, and none was tested.
- HMP's current two-read race stays: `_tip` (`bridge.py:799`, `resolve_resume_session_id`) then
  `get_messages` (`:854`, `:864`, `:892`) are separate reads; `after` adds a third (`:878`).
- Constraint for any opaque grant: it must not weaken that. It may not cache "this session is the tip" or
  "this row is active"; each serve re-reads and fails to *unavailable* on any mismatch; verification that
  needs more than one read inherits the race and must be written as such. HMP must not copy SQLite source
  to obtain a snapshot; if root needs one, that is a Hermes-side request.
- **`get_resume_conversations` (revision 2, checked).** `hermes_state_messages.py:1376` is public but is not
  a transactional snapshot: it first resolves its lineage with separate reads (`_resume_lineage_ids`,
  `:1396`, via `_is_explicit_branch_session` and `_session_lineage_root_to_tip`,
  `hermes_state_sessions.py:1424-1446`) and only then runs one `SELECT` (`_fetch_conversation_rows`,
  `:1266`). "From ONE SELECT, byte-identical to the separate reads" in its docstring means equal output,
  not isolation. It also does not resolve a tip, and its display projection includes compacted rows
  (`active = 1 OR compacted = 1`, `:47`), which is a different history semantics from HMP's active-only
  reads. HMP does not call it (`REACHED_METHODS`, `bridge.py:181-200`). Adopting it would be a root
  history-semantics choice, not a consistency fix. No transaction-strength claim is made anywhere in this
  note.
- Scope of row rechecks and the database-replacement question are in S1.

## Authority assessment

| Candidate | Verdict |
| --- | --- |
| Assistant `MEDIA:` text or bare path | **Not authority.** Model-written; native validator accepts almost any host file (O11). A claim to match, at most |
| Native `validate_media_delivery_path` / allow roots | **Not authority** (O11, O12). Native validator is not authorization |
| `HERMES_HOME` / process env / native global caches | **Not authority**; wrong profile under multiplexing (O12, O21) |
| Same-profile `cache/images` confinement alone | **Necessary, not sufficient.** Location only (O21, P7) |
| Active tool row `image_generate` + assistant `tool_calls` id in the same eligible session, from that profile's DB | **Hermes-recorded generation result** (P8), taken as Hermes truth under the adopted trust. Not a cryptographic claim about the bytes. It is Hermes history: copies, branches and imports reproduce it (P4, P5, S2), so it never means "newly generated here". Necessary filter, not sufficient without confinement and strict raster validation |
| Producer-time grant via `post_tool_call` (O22) | Not needed under root decision 4; FR-054 stays closed. Would not prove bytes either |
| Wire rows as HMP exposes them | Provenance lost (O15); parse inside the bridge before the cap |

**Combined route (selected-profile cache + active recorded row + current-session binding + strict bounded
raster validation) is the architecture candidate for isolated fixtures.** It is not working, not
qualified and not claimed secure. Its byte-safety conditions below must be met at the *first* open and
re-checked before release of any buffered bytes; source reading cannot show that they are.

## Dispositions (conditions, not conclusions)

| Hazard | Condition required before any bytes are read or copied | Status |
| --- | --- | --- |
| Cross-profile | Home from the chat's own binding (`bridge.py:604`); path under **that** profile's `cache/images` (`cache/videos`); never a root list | Source-supported; untested |
| Symlink / ancestors | Every ancestor directory opened by descriptor with no-follow from a pinned profile-home descriptor; final component opened no-follow; no path-string re-resolution | Needs fixture proof |
| Not a regular file | `fstat` on the **opened descriptor** must be a regular file | Needs fixture proof |
| Hardlink | `st_nlink == 1` on the opened descriptor **before any copy or serve**. A file with `nlink > 1` is refused, not copied. This is a confused-deputy guard (a link to a file outside the cache), not a containment claim against a same-account process | Needs fixture proof |
| Same-profile planted or replaced file | **Resolved by root adoption, not by a new producer requirement.** Same-account or model-with-host-exec planting is inside the existing trust (P7, P8). What remains required is that the bytes pass strict bounded raster validation (decoder safety) and that the open is confined (rows above). A producer digest, exclusive create or registration hook is not required to keep current grant boundaries | Closed as a blocker; the validation and confinement rows above stay mandatory |
| Recorded-result check before copy | Active row + call linkage + executing tool name + confinement verified **before** any copy; a copy is never the first authorization step | Constraint |
| Scope change (profile, route, unpair, auth) | Ref bound to user, device, profile, chat; per-bot authorization re-run on every serve (`reads.py` `require_bot_authorized`) | Pattern exists; extend |
| Row removal / rewind / in-place compaction | Same active-row history HMP serves today (root M1). Re-check the bound row is active, with the same `tool_call_id`, `tool_name` and content, before the open and again after the read and before release (O17, S1). A retired row's grant is unavailable; an active clone is re-evaluated, not inherited (S2) | Source-supported; untested |
| Compression (child session) | Tip carries only what the handoff and tail clone wrote (P5, S2); a grant bound to a parent row is unavailable once the tip no longer serves that row | Fixture |
| Fork / import | Root M2: within an already eligible authorized session, branch/import history is still Hermes history and is not excluded for having been produced in a parent; exact active row/call linkage and selected-profile confinement remain mandatory; never claim "generated in the child"; foreign or invalid imported paths fail confinement | Decided by root; fixture |
| Cache sweep (24h, O21, S5) | Root M3: serve from the existing cache only. A swept or absent file is *unavailable*, never a path fallback or another profile. No retained copy or HMP custody category is introduced by this research; retention beyond Hermes's cache needs its own reviewed amendment | Decided by root; fixture |
| Ambiguous wire metadata | Missing call id, unnamed call, capped, spilled or non-JSON tool text, `success` not true, non-string/non-absolute `image`, unknown result shape: **no ref**. A repeated call id is judged within the **active** row set only (S2): compaction legitimately leaves the same id on retired rows | Fail closed |
| Remote URL result (O2) | The **local route** does not fetch remote URLs and does not authorize them. The existing public-CDN renderer is a separate path, not examined or changed here | Scope note only |
| Wrapper/spill hiding `image` (P3) | Parse inside the bridge before the 4000-char cap (O15); a spilled or truncated row yields no ref | Constraint |

## Options

| # | Option | Verdict |
| --- | --- | --- |
| A | Row-bound grant minted in the bridge (parse before cap, profile-cache confinement, descriptor-confined open, nlink 1, strict bounded raster validation, recheck before release) | **Architecture candidate for isolated fixtures; not working, not qualified.** The planted-file question (P7) is closed by root's trust adoption; lineage is decided by root M1/M2; no new wire or serve route is specified here |
| B | A plus `post_tool_call` producer-time registration (O22) | Not justified (root decision 4); FR-054 stays closed |
| C | Phone adapter overrides trusting the native-validated path | Reject: authorizes arbitrary host files (O11), no turn identity (O13) |
| D | Reuse Hermes read APIs (`/api/media`, API-server data URLs, `methods_images`) | Reject: other auth domain, broad roots, response-only (O19, O20) |
| E | Inline data URLs in assistant text | Reject here: changes canonical rows, touches upstream |
| F | Upstream change | Not shown to be required. Private result-field shapes may be exact-build gated after qualification; their being private is not itself proof an upstream change is required. Revisit only if the fixtures fail |

## Disposition of the recommendation

1. Treat A as the candidate for isolated fixtures, not a recommendation to build. The research does not
   show it is safe; it shows what must be true for it to be.
2. An active Hermes-recorded row is a *necessary* filter, never sufficient authority; assistant paths and
   the native validator are claims only.
3. Any copy must follow, not replace, the open-time checks (no-follow ancestors, regular file on the
   descriptor, `nlink == 1`, selected-profile confinement, active row and call linkage) and strict bounded
   raster validation.
4. Same-profile model write access to `cache/images` (and possibly `state.db`) is inside the adopted
   existing trust (root decisions, "Evidence and trust framing"); it is not an open question and does not
   call for option B or an upstream producer contract.
5. Retention after sweep is outside this research: no retained copy, no HMP custody category; a separate
   reviewed amendment would be needed (root M3).
6. Missing generic primitive: a multi-statement snapshot read in SessionDB (gap above). Not worked around
   by copying SQLite code, and no strong transaction claim is made.

## Exact APIs involved

Hermes (private unless noted): `SessionDB.get_messages`, `resolve_resume_session_id`, `_read_ctx`,
`_execute_write`, `append_messages_batch`; `BasePlatformAdapter.send_image_file`, `send_video`,
`send_document`, `send_multiple_images`; `image_generate` result JSON; `post_tool_call` (**documented**).
HMP: `bridge.py` `_db`, `_profile_home`, `_tip`, `_rows`, `_cap_chars`; `adapter.py` `HmpAdapter.send`.
Private internals already used by HMP are compat-gated (`bridge.py:184`); any new one must join that gate.

Revision 2 additions: `SessionDB.get_meta` (public, `hermes_state.py:1595`), `stat_db_file_identity`
(`hermes_state_common.py:301`), `SessionDB._db_file_was_replaced` (private, `:1189`),
`get_resume_conversations` (public, not used by HMP); `agent.provider_media.cache_dir` and
`gateway.platforms.base.get_image_cache_dir` (private, ambient-context, directory-creating: not for HMP use,
see S5). None of these appears in `COMPAT_MANIFEST.md`.

## Source reads S1-S5 (revision 2; installed tree `8afaab37`; nothing executed)

Method: `git grep` / `sed` over tracked files of the installed tree. Tests are excluded. `evals/` are
harnesses that open `state.db` with raw `sqlite3`; they are not product paths and are not counted.

### S1 Writers of `active`, deletion and database replacement

| Writer | Effect on rows / `active` | Where |
| --- | --- | --- |
| Insert (`_INSERT_MESSAGE_SQL`) | Fresh `active` rows for append, batch, replace, compact and import | `hermes_state_messages.py:26`, `_insert_message_rows` `:515` |
| Clone (`_clone_message_rows`) | New id, `active=1, compacted=0`, payload byte-exact (including `tool_call_id`, `tool_name`, `content`); may be retargeted to another session (child compression) | `:658-670` |
| Rewind | `active=0` for rows at or after the target; may insert a split replacement row | `rewind_to_message` `:1532`, UPDATE `:1563`, `_split_rewind_target` `:1513` |
| `replace_messages` | `archive_dropped`: `active=0` (`:593`); default: **`DELETE FROM messages`** then re-insert with new ids (`:596`); `active_only` spares archived rows. Callers `acp_adapter/session.py:370`, `gateway/session_transcript.py:507`, `tui_gateway/methods_prompt.py:412` | `:557` |
| In-place compaction | Old active rows `active=0, compacted=1` (`:63`); carried duplicates `active=0, compacted=0` (`:796`, `:879`); clones as above | `archive_and_compact` `:815` |
| `deactivate_message` | `active=0` for one row | `:961`, UPDATE `:970` |
| `clear_messages` | `DELETE FROM messages` for a session | `:1649`, `:1652` |
| Schema migration | `active` NULL to 1 | `hermes_state_schema.py:968` |
| Session delete / prune | Rows and sessions deleted | `hermes_state_sessions.py:165-168`, `delete_session` `:1554` (`:1580-1581`), `delete_sessions` `:1617` (`:1636-1637`, `:1672-1675`); `hermes_state_maintenance.py:81` (`:96`), `prune_sessions` `:272` (`:295-296`) |
| Profile move | Messages inserted **without** `id` (`_MESSAGE_MOVE_SKIP`), so new ids in the target store; source deleted by `delete_moved_session` | `hermes_state_profile_repair.py:58`, `:230`, `:~245-253` |
| Content-only rewrites | Blank active assistant row content (`agent/transcript_repair.py:49-51`); assistant tool-call marker rows set to `''` (`hermes_state_messages.py:~1683`); one active user row (`:958`); timestamps (`hermes_cli/session_recovery.py:962`). **No path rewrites a tool row's content in place** | as listed |

- Outside `hermes_state*.py`, `agent/transcript_repair.py`, `hermes_cli/session_recovery.py` and `evals/`, no tracked
  non-test Python (plugin directories included) matched `UPDATE messages`, `INSERT INTO messages` or
  `DELETE FROM messages`. Raw SQL from out-of-tree plugins or operators cannot be covered by source reading.
- **No code path was found that sets `active` from 0 to 1.** The only writes of 1 are inserts, clones (new
  ids) and the NULL-to-1 migration. So within one database file, with no restore or replacement, an
  existing row id only goes active to inactive or is deleted.

Database replacement and restore (these break "within one file"):

- `hermes_cli/backup_restore.py:73` `_safe_restore_db` (used by `hermes import` and `/snapshot restore`,
  `:5`) writes a snapshot into the live destination through the SQLite backup API
  (`src_conn.backup(dst_conn)`, `:111`), which **preserves the inode**. The fallback unlink-and-move
  (`:~160-185`) runs only when no process or in-process handle holds the file (`offline_file_access`) and
  changes the inode. Effect: rows, `active` flags, deletions and the AUTOINCREMENT counter all return to the
  snapshot's state together.
- `hermes_state_repair.py:~1015-1030` promotes a repaired scratch snapshot into the live database with
  `_copy_database_snapshot(scratch, db_path, destination_connection=live_guard)`, deliberately not
  `os.replace`.
- `hermes_cli/session_recovery.py:1-5` builds a **fresh** database from copies and "is never installed
  over the active database"; installing it is an operator step outside this source.
- Import (`hermes_state_portability.py:145-171`) mints a new session id (`new_session_id(hex_len=12)`)
  and new row ids.

Identity reuse (inference from SQLite semantics plus the restore behaviour above; not tested):

- Row ids are `INTEGER PRIMARY KEY AUTOINCREMENT` (`hermes_state_common.py:416`). The counter lives in the
  same file, so ids are not reused while the file continues, but a restore of an earlier snapshot resets the
  counter and the same id can later name a different row.
- Session ids are text. Generated forms: `<YYYYMMDD_HHMMSS>_<hex6>` (`gateway/slash_commands_session.py:1019`),
  `new_session_id(...)`, and deterministic families `cron_<job>_<timestamp>` (`cron/scheduler.py:2496`) and
  `room_<sha256[:32]>` (`gateway/platforms/api_server_room_dispatch.py:28`). There is no counter, so an
  id can be re-presented after a delete or a restore.

Generation-read primitives and their limits:

- `state_meta['db_file_generation']` (`hermes_state_errors.py:192`) is minted once per file together with
  `PRAGMA application_id` (`_ensure_db_file_generation`, `hermes_state.py:1132`). `SessionDB.get_meta`
  (`:1595`) is public and reads under `self._lock` on the writer connection, not the pooled reader.
  `stat_db_file_identity(path)` returns `(st_dev, st_ino)` (`hermes_state_common.py:301`).
  `_db_file_was_replaced` (`:1189`) and `_halt_if_db_generation_changed` (`:1230`) are private, bound to one
  handle, and sit on the write and reopen paths (`:940`, `:946`); `_read_ctx` (`:889`) has no per-read
  replacement check in the source read.
- Inference, untested: the stamp and the inode distinguish a *different file* (moved or copied database)
  from the handle's file. A restore of an earlier snapshot **of the same file** carries the same stamp, and
  through the backup API the same inode, so neither detects a same-lineage rollback. HMP holds no database
  file identity today (`bridge.py` `_db` only checks `is_file()` and acquires a shared handle).

Scope of the monotonicity argument (this is the scoped statement; no global claim):

- **Allowed:** within one database file lineage, with no restore, repair promotion, session delete or
  prune, default-mode `replace_messages`, `clear_messages` or profile move between the two observations
  (and no out-of-tree raw SQL), a row id observed active with the same session id, `tool_call_id`,
  `tool_name` and content before the open and again after the read and before release was active for the
  whole interval. HMP already has a single-statement probe that returns the flag
  (`get_messages(tip, include_inactive=True, after_id=id-1, limit=1)`, `bridge.py:878-896`).
- **Not allowed:** that `active` is globally monotonic; that an unchanged row id means the same row after
  a restore, repair promotion or file replacement; that a tip and a row are observed at one instant.
- The `_tip` then `get_messages` race stays documented, not fixed. It cannot widen authorization:
  `resolve_resume_session_id` follows continuation children only and skips branch children
  (`_branched_from IS NULL`, `hermes_state_messages.py:1225-1257`, `:1252`), and the `session_ref` is
  minted for the caller's own session (Opus's reading of `reads.py:229-255, 610-618`; not re-read here).
- Root's note stands: the monotonicity argument is an inference until restores, replacements and race
  fixtures are covered. This S1 covers the source writers; fixtures G2-5 to G2-7 cover the rest.

### S2 Import provenance, branch versus compaction

Provenance fields (installed tree):

- `sessions.origin_json` (`hermes_state_common.py:360`) is **routing origin** for gateway sessions
  (`gateway/session_recovery.py:23`, `:346`, `:430`), copied unchanged to compression children
  (`hermes_state_compression.py:219-227`) and set from the destination source by gateway `/branch`
  (`gateway/slash_commands_session.py:1035-1050`). Only foreign-history import writes
  `{"imported_from": origin}` with `source = origin["tool"]` (`hermes_state_portability.py:145-171`,
  `hermes_cli/foreign_sessions.py:256`).
- Generic transcript import (`_import_session_row`, `hermes_state_portability.py:519`) writes **no**
  `origin_json`, defaults `source` to `"import"` unless the payload names one, and takes message
  `tool_call_id`, `tool_name`, `platform_message_id` and similar as passthrough text
  (`_IMPORT_MESSAGE_TEXT_FIELDS`, `:28-30`). `_attach_import_parents` (`:542`) can re-attach imported children to
  an existing parent; whether that can make an imported session a continuation that
  `resolve_resume_session_id` follows was **not read**.
- `model_config._branched_from` is the durable branch marker for gateway `/branch`
  (`slash_commands_session.py:1047`), CLI (`cli_commands_mixin.py:1420`) and the API server
  (`gateway/platforms/api_server.py:3270`). Whether the Desktop branch (`tui_gateway/methods_session.py:280`
  `_seed_branch_row`) writes it was **not read**.
- Child compression is marked by `parent_session_id` plus the parent's `end_reason = 'compression'`
  (`hermes_state_compression.py:~300-310`).
- Message rows carry no provenance column (P4 stands): `_INSERT_MESSAGE_SQL` has `tool_call_id`,
  `tool_calls`, `tool_name`, `platform_message_id`, `active` and display fields only.

Row and call shapes HMP would read: a tool row has `role='tool'`, `tool_name`, `tool_call_id` and text
`content`; the assistant row has `tool_calls` JSON holding the call `id` and function name. HMP's `Row`
already carries all three (`bridge.py` `_rows`).

| | In-place compaction (`archive_and_compact`, `hermes_state_messages.py:815`) | Child compression (`publish_compression_child`, `hermes_state_compression.py:~255-310`) |
| --- | --- | --- |
| Session id | Same | New child; parent gets `end_reason='compression'` |
| Old rows | `active=0, compacted=1` | Stay in the closed parent |
| Carried rows | Originals `active=0, compacted=0`; byte-exact clones with new ids, `active=1` | Handoff messages re-inserted from dicts; watermark tail cloned into the child, byte-exact, new ids |
| HMP active-only read | Archived image row leaves Phone history with its text; a clone can appear with a new id and the same `tool_call_id` | Tip is the child; parent rows are not read |
| Grant bound to the old row | Unavailable | Unavailable once the tip no longer serves that row |
| Active clone | Re-evaluated from scratch; needs its own active assistant call row linked by call id | Same |

- A repeated call id is ambiguous only **within the active set**. Across retired rows it is expected (clones
  share the id). HMP's history reads are active-only (`bridge.py:854-892`), so the check runs on what HMP
  reads. If only the tool row, or only the assistant row, was cloned into the active set, the linkage is
  incomplete and the result is no artifact (fail closed; fixture G2-1).
- Root M1/M2 applied: the first slice serves active history only; retired grants are unavailable; an eligible
  active clone is re-evaluated; an eligible same-profile branch or import is allowed as **Hermes-recorded
  history**, never as proof the image was newly generated in the child; foreign or invalid imported paths
  fail confinement. Unread: whether `_validate_import_payload` bounds `tool_name` / `tool_call_id`.

### S3 Tool-thread profile scope, provider home, cache ownership

- The override is a `ContextVar` (`hermes_constants.py:18`); `get_hermes_home()` consults it before
  `HERMES_HOME` (`hermes_constants.py:111-118`). `set_hermes_home_override` does not touch `os.environ`.
- Gateway multiplexing sets it per turn in `_profile_runtime_scope` (`gateway/run.py:1776`), and its comment
  says it reaches the agent worker through `copy_context()` (`:1780`). Tool dispatch keeps it:
  `DaemonThreadPoolExecutor.submit` copies the context (`tools/daemon_pool.py:26-35`), the sequential
  timeout path wraps the worker in `propagate_context_to_thread` (`agent/tool_executor.py:936`;
  `tools/thread_context.py:36`, which snapshots with `copy_context()` on the parent thread), and `_run_async`
  does the same for coroutine tools (`model_tools.py:124-127`).
- `agent.provider_media.cache_dir(kind)` is `get_hermes_home() / "cache" / kind` (`provider_media.py:23-28`), so
  under a scoped turn a provider writes into the **routed** profile's cache. Bundled providers save inside the
  synchronous `provider.generate(...)` call (`_dispatch_to_plugin_provider`), so they run in the same context.
  Not covered: a bare thread started inside an out-of-tree provider, which would not inherit the context
  unless it uses the helpers (unread, unknown).
- Desktop: `tui_gateway/server.py:539` `_profile_home` resolves a named profile with the same
  `hermes_cli.profiles.get_profile_dir` the gateway uses (`gateway/run_adapters.py:1510`), returns `None` for
  the launch profile, and each turn binds the profile's home, secrets and terminal scope
  (`tui_gateway/prompt_turn.py:457`, `:610`, `:1060`; `methods_session.py:70`). So a Desktop turn on profile P
  writes `<P home>/cache/images`, the same directory the gateway scope resolves for P. Whether the launch
  home and `get_profile_dir(name)` are the same path for symlinked homes is a path-identity fixture
  question (`tui_gateway/server.py:550` compares `resolve()` values).
- `UNRESOLVED_PROFILE_HOME` (`gateway/run_adapters.py:51`) is a sentinel object, not a path; HMP's
  `_as_path` already maps it to `None` (`bridge.py:368`), so an unresolved profile yields no home and no
  artifact.
- Not traced: which profile scope the gateway enters for an HMP-origin turn (`hermes_profile` metadata,
  O13); this note shows only the mechanism, not that an HMP turn uses it.
- Non-local image path translation: `_postprocess_image_generate_result` (`tools/image_generation_tool.py:330-362`)
  leaves `image` as the **host** path and only adds `host_image` (the same host path, `setdefault`) and
  `agent_visible_image` (a container or remote path from `map_cache_path_to_container`,
  `tools/credential_files.py:301`) when the routed terminal backend is non-local and `image` is an absolute
  file path. `agent_visible_image` is never a host path and must not be read as one; both keys come after
  `prompt` (O15). The backend is read through the per-turn terminal scope (`terminal_env`), not process env.

### S4 Result shapes of the bundled providers (read at the call sites; no provider was run)

Bundled image backends: `fal`, `openai`, `openai-codex`, `openrouter` (also Nous Portal), `xai`,
`deepinfra`, `krea`, `meta-ai`.

| Shape | Providers |
| --- | --- |
| `image` = local cache path from `save_b64_image` / `save_url_image` (`agent/image_gen_provider.py:75`, `:85`) | openai, deepinfra, xai (via `materialize_image`, `plugins/image_gen/_common.py:199`); openai-codex (`:303`, base64 only); openrouter (`:475-478`, `:742-744`); krea (`:499`); meta-ai (`:113-115`) |
| `image` = **bare remote URL** when caching the URL fails | `cache_url_best_effort` (`_common.py:217`, used by openai, deepinfra, xai); krea (`plugins/image_gen/krea/__init__.py:499-504`); meta-ai not traced for its fallback |
| `image` = a provider URL directly | xai when the response carries `public_url` (`plugins/image_gen/xai/__init__.py:319`); FAL in-tree path (`image_generation_tool.py:476`), which the `fal` plugin returns |

- Order of keys: `success_response` builds `success, image, model, prompt, aspect_ratio, modality, provider`,
  then `extra` (`agent/image_gen_provider.py:98-113`); `_provider_result` encodes it with `json.dumps`
  (`image_generation_tool.py` `_provider_result`), which keeps that order. The FAL path encodes with
  `indent=2` first and is re-encoded after the `fal` plugin adds `provider`, `prompt`, `aspect_ratio`,
  `model` with `setdefault` after `image`. Failures are `success: false, image: null`.
- No success site read puts the caller's input `image_url` or reference images into `image`; inputs show up
  only as counts or notes in `extra` (openrouter `reference_images_used`, `_image_api_extra`,
  `plugins/image_gen/openrouter/__init__.py:482-499`). meta-ai and the openrouter chat path were read at the
  `success_response` call only.
- `extra` is open-ended and provider-specific: `additional_images` (a list of cache paths, openrouter
  `:489`), `public_url`, `storage_*`, `usage`, `job_id`, and others. The result shape is not a stable
  documented API (O4). **This is the unknown/private-field compatibility question:** it points to an
  exact-build gate on a small set of top-level keys with everything else ignored or refused, decided by root
  after qualification. It is not shown to need an upstream API, and nothing here qualifies the shape.
- Video: `agent/video_gen_provider.py:111` `success_response` builds `success, video, model, prompt, modality,
  aspect_ratio, duration, provider`, then `extra`. `video` is a local cache path (`save_url_video` /
  `save_bytes_video`) or, if the save fails, the bare URL (`:276`); the `fal` video plugin returns the
  remote URL (`plugins/video_gen/fal/__init__.py:422-423`); xai uses its public URL (`:314`); openrouter
  `video_path` (`:346-347`) was not traced. `video_generate` is not in the gateway auto-append set (O5/O6),
  and root keeps video out of the first image slice.

### S5 Sweep roots, TTL and Desktop cache sharing

- The sweep is the gateway housekeeping chore `_housekeeping_media_caches` (`gateway/run.py:4611-4631`), run
  by the chore list entry `(60, "Media cache cleanup", _housekeeping_media_caches)` (`:4813`). Unlike the
  curator, sync and state-database chores right after it, it is **not** wrapped in `profile_scoped_chore`
  (`gateway/run_profile_reconcile.py`), and it does not iterate profiles itself. By source reading it runs once
  in the housekeeping thread under the ambient (launch/process) home, so a non-launch profile's
  `cache/images` and `cache/videos` are not swept by this chore. Source reading only; not run.
- Each cleanup is `_cleanup_cache_dir` (`gateway/platforms/base.py:669`): top-level files only, `is_file()` and
  `st_mtime < now - 24h`, unlink, errors suppressed. mtime is the write time (P6); there is no per-profile
  or per-grant retention.
- The directory it prunes is not always the one producers write. Accessors resolve with
  `get_hermes_dir("cache/images", "image_cache")` (`base.py:578`, `hermes_constants.py:413`), which prefers a
  **populated legacy** `<home>/image_cache`. Producers write `<home>/cache/<kind>` unconditionally
  (`provider_media.py:23-28`). On a home with a populated legacy directory the sweep prunes the legacy
  directory and not the producer directory. The accessors also `mkdir` as a side effect.
- No other caller of the cleanup functions exists outside `gateway/run.py` (`git grep`), so Desktop-only and
  CLI-only processes never sweep. Desktop writes the same selected-profile cache as the gateway (S3), so a
  Desktop-generated file persists beyond 24 hours unless a gateway for that home is running, and a gateway
  turn's file can be swept before a phone asks for it.
- Inbound attachments share `cache/images` with a different name shape: `<prefix>_<uuid12><ext>`
  (`base.py:610-614`) against producer `<prefix>_<YYYYMMDD_HHMMSS>_<uuid8>.<ext>` (`provider_media.py:31-34`).
  Any process able to write the directory can use either shape, so the name is not a discriminator, and
  this note proposes no name heuristic.
- Generic helper roots, none usable as HMP authority: `validate_media_delivery_path` allow-roots enumerate
  every profile's cache (O11); `/api/media` roots include all of `home/cache` (O20); the accessors above are
  ambient-context, create directories and are private. HMP would derive `<routed home>/cache/images` from its
  own profile binding (`bridge.py:604`) and open it by descriptor, never through these.

## Corrections to revision 1

1. P7 and the disposition "same-profile planted or replaced file" were presented as an open root decision
   that might require option B or an upstream producer contract. Root adopted the existing trust; both are
   withdrawn as blockers. What replaces them is the enforced-boundary table plus strict raster validation.
2. "Evidence, not proof" for the tool row is restated as a **Hermes-recorded generation result**, not a
   cryptographic production claim, and not a verdict on whether the route may proceed.
3. O15: the claim that a long prompt pushes `image` past the 4000-character cut is withdrawn; `image`
   precedes `prompt`. The risk is for fields appended after `prompt`. Parsing before the cap stays.
4. In-place compaction was missing; it is now S2. The "duplicate call id: no ref" rule is scoped to the
   active set.
5. `get_resume_conversations` is public but not a transactional snapshot (lineage reads precede its single
   `SELECT`), and HMP does not use it.
6. The `post_tool_call` suppression ContextVar is not a coverage gap, option B is not justified, FR-054 stays
   closed. Test 16 of revision 1 is dropped.
7. Revision-1 test 11 (attempting to write `state.db` from a model terminal "to decide P7") is dropped: it
   characterizes a posture root already adopted and is not needed for any claim here.
8. The sweep text now matches S5 (not profile-scoped, legacy-directory shadowing). The statement that a copy
   "may preserve bytes" is not a plan: no retained copy or custody category is introduced.
9. The monotonicity argument is stated only with its scope (S1); it is not asserted globally.

## Fixture plan (not run; frozen only after root has these facts and freezes the prototype interface)

Common setup, all groups: the exact independent `8afaab37` build; disposable homes (no real profile, no
`~/.hermes`); synthetic credentials and a synthetic provider that writes through `save_b64_image`; sockets
denied; prototype code kept separate from product code; no SQLite implementation copied into HMP; Desktop
and Phone persistence both exercised, not a fabricated response; the archive `ca705` is not used and its
results are not reused. Each case records the exact observed result; a case with no run is "not run".

**G1 Producer persistence and uncapped parse**

- G1-1 Phone and Desktop turns: assistant call row and tool row exist, linked by call id and executing tool
  name, before the UI sees the result; a forced flush failure leaves a file with no row, so no artifact;
  Phone row persistence versus native delivery order (P2 gap).
- G1-2 Truncation and size: a prompt over 4000 characters on a local backend still parses `image` before the
  cap; a simulated non-local result with `host_image` / `agent_visible_image` after `prompt` ignores both;
  a capped row without a prior parse gives no artifact; a result over the spill threshold (P3) gives none.
- G1-3 Shapes: per bundled provider, stubbed outputs with the key sets from S4 (cache path, bare URL,
  `public_url`, `additional_images`, `success: false`, non-absolute or non-string `image`, unknown extra
  keys); only the exact-build-gated form yields an artifact; remote URLs never do.
- G1-4 Linkage: tool-row name different from the assistant call's function name, missing or repeated call id
  inside the active set, a tool row with no assistant call row, a row under another tool name (and whether a
  plugin can register `image_generate`, P3): no artifact.

**G2 Compaction, replacement, rewind**

- G2-1 In-place compaction: a grant on the archived row is unavailable; the active clone is re-evaluated; a
  clone of only one half of the pair gives none; the same call id on retired rows does not block the active one.
- G2-2 Child compression: a grant bound to the parent is unavailable; the tail clone in the child is
  re-evaluated; whether the compressor keeps an `image_generate` pair at all (S2 gap).
- G2-3 Branch and import inside an eligible session: gateway and CLI `/branch` copies are served as history;
  the Desktop branch has no tool rows; an imported bundle with a foreign or invalid path is refused; a
  same-profile name collision is served only if it passes validation; none is described as newly generated.
- G2-4 Rewind, `replace_messages` (archive and default DELETE modes), `clear_messages`, `deactivate_message`
  between open and release: the second check refuses.
- G2-5 Database replacement between checks: a backup-API restore of an earlier snapshot of the same file
  (same id, different content; reactivated flag; deleted row), a swapped file (new inode), a deleted and
  re-presented session id, and a profile move: each refuses or is shown not to be detected. The same-lineage
  rollback result decides how much "current database identity" can claim (S1).
- G2-6 The row recheck before the open, after the read and before release, with the per-bot gate re-run at
  the second point.
- G2-7 Tip change interleaved between `_tip` and `get_messages` (a continuation child appears; a branch or
  delegate child must not be followed): nothing outside the eligible lineage is served. No snapshot claim.

**G3 File-type and path hazards, cross-profile**

- G3-1 Open confinement: symlink as final component, symlink as ancestor, `..` and absolute out-of-cache
  strings, another profile's cache, `cache/documents`, a directory, a FIFO, a socket, a hardlink
  (`nlink > 1`, including one created after mint), replacement between open and read.
- G3-2 Bounds and validation: oversize file, empty and truncated files, non-raster content, a polyglot,
  extension/content mismatch, animated GIF/APNG/WebP beyond policy, over-large dimensions (decompression
  bomb), unsupported formats. Exact bounds and the validation library are root review items.
- G3-3 Cross-profile and instance: a row in profile A naming profile B's cache is refused; under multiplexing
  the provider writes the routed profile's cache (S3); Desktop and Phone resolve the same directory,
  including a symlinked home; `UNRESOLVED_PROFILE_HOME` gives no home; a second instance's state is refused.
- G3-4 Observation only: names in a shared `cache/images` (producer shape, inbound shape, any other); no
  name heuristic is proposed.

**G4 Revocation, sweep, tip**

- G4-1 Revoking the grant (unpair, bot authorization, profile re-route) between mint and serve refuses.
- G4-2 Sweep: serve after the file is removed is unavailable with no path or other-profile fallback;
  mtime boundary at 24 hours; legacy `image_cache` shadowing; a non-launch profile under the housekeeping
  chore (S5) is observed, not assumed; Desktop-only home never sweeps.
- G4-3 A concurrent request while a grant is revoked and a tip changes: the result is unavailable or the
  previously eligible bytes, never a widened set. No transaction-strength claim.

## Provenance verdict

**Hermes-recorded generation results are not a cryptographic production claim, and nothing here upgrades
them to one.** Source shows the agent writes an assistant-call and tool-row pair in one transaction before
the UI sees the result (P2). The schema carries no provenance (P4), several writers reproduce rows (P5,
S2), plugins are arbitrary operator code (P8), and database restore or replacement can reset identity (S1).
Under the adopted trust, that is enough to define an eligible candidate for isolated fixtures, provided the
selected-profile confinement, descriptor-confined open, strict bounded raster validation and per-request
rechecks hold, which no fixture has shown. Source reading gives no transaction-consistency claim.

## Remaining evidence gaps (new in revision 2)

1. Whether the compressor keeps an `image_generate` call/result pair into a child or a clone (S2).
2. Desktop `_seed_branch_row` branch marker; `_attach_import_parents` effect on tip resolution;
   `_validate_import_payload` limits on `tool_name` / `tool_call_id` (S2).
3. Which profile scope the gateway enters for an HMP-origin turn; bare threads inside out-of-tree providers (S3).
4. meta-ai URL-failure fallback; openrouter video `video_path`; the exact top-level key set each provider
   emits at runtime (S4).
5. Same-lineage database rollback is not detectable by stamp or inode (inference, S1); whether row-level
   checks suffice after an id is reused is a fixture result.
6. Whether the housekeeping sweep really skips non-launch profiles at runtime, and legacy-directory
   shadowing (S5); source only.
7. Phone persistence versus native delivery order (P2); spill and `image_generate` name registration (P3).
8. Raster validation library, bounds and animated-form policy: root review.
9. Claims taken from Opus and not re-read: `reads.py` bind and gate lines, Docker read-only cache mounts,
   `SECURITY.md` §2.5/§2.6 beyond what is cited.
10. Archive `ca705` re-census (12 differing files) before any claim about the prior fixture.
11. The installed tree and the independent build were compared by root for four files; this note read the
    installed tree only.

## Status

Source census, three passes. No local-media feature works today; no behaviour was tested. Nothing in HMP or
Hermes was changed; no runtime, import, network, store, browser, device, commit, push or subagent was used.
Root independent security review is mandatory before any implementation, and root receives these facts and
freezes the prototype interface before any fixture runs.
