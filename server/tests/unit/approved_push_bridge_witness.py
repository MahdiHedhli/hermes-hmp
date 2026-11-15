"""Exact test-only reversal of the already approved push diagnostics delta.

Snapshot 0cfd530 contains the helper introduced by 3aa27a5. This exception is
only its exact source bytes and import placement; no function-name whitelist
or dynamic-lookup detector relaxation. Media/S5 witness remains rooted at83a.
"""
from __future__ import annotations

import hashlib

APPROVED_PUSH_BLOCK_SHA256 = "009145d1d3c10d4014ea4c560afbaf0cea043d60af821b38b3602f48d206ecb2"
APPROVED_S5_BLOCK_SHA256 = "0e386a26dc9acdfbf5777ef54807c2a95272b198528970a56677dcfa93e487f0"
APPROVED_PUSH_BLOCK = r'''def read_push_settings_for_diagnostics(home: Path) -> object:
    """PN-OPS configured state, without loader hooks, backups or env bridging.

    Reuse Hermes's pure YAML parser, expansion, managed merge and platform
    precedence primitives. Read files directly so malformed inputs propagate
    to the CLI's fixed `config_unavailable`, never native recovery logging.
    This optional diagnostics API is not a runtime admission gate.
    """
    # Hermes's CLI/plugin bootstrap already imports this module. Its first
    # import can seed SOUL.md on some builds; diagnostics must not trigger it.
    if "hermes_cli.config" not in sys.modules:
        raise BridgeError()
    from gateway.config_loader import merge_platform_sections
    from hermes_cli.config import _deep_merge, _expand_env_vars, _normalize_root_model_keys
    from hermes_cli.managed_scope import get_managed_dir
    from utils import fast_safe_load

    def read_mapping(path: Path, *, legacy: bool = False) -> dict:
        try:
            # Native config reads follow symlinks. Inspect the opened target,
            # not a prior stat, so a path replacement cannot substitute a FIFO
            # between the check and open. O_NONBLOCK prevents FIFO open waits.
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        except FileNotFoundError:
            return {}
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise BridgeError()
            with os.fdopen(fd, "rb", closefd=False) as file:
                data = file.read(1024 * 1024 + 1)
        finally:
            os.close(fd)
        if len(data) > 1024 * 1024:
            raise BridgeError()
        text = data.decode("utf-8-sig")
        value = (json.loads(text) if legacy else fast_safe_load(text)) or {}
        if not isinstance(value, dict):
            raise BridgeError()
        return value

    legacy = read_mapping(home / "gateway.json", legacy=True)
    config = _expand_env_vars(read_mapping(home / "config.yaml"))
    managed_dir = get_managed_dir()
    if managed_dir is not None:
        managed = _normalize_root_model_keys(
            _expand_env_vars(read_mapping(managed_dir / "config.yaml"))
        )
        if isinstance(managed.get("model"), str):
            managed["model"] = {"default": managed["model"]}
        config = _deep_merge(config, managed)
    platforms = merge_platform_sections(config, config.get("gateway"), legacy)
    block = platforms.get("hmp")
    extra = block.get("extra") if isinstance(block, Mapping) else None
    # PlatformConfig.from_dict promotes untyped flat fields into `extra`;
    # explicit `extra` entries win, including a present null/disabled value.
    if isinstance(extra, Mapping) and "push" in extra:
        return extra["push"]
    return block.get("push") if isinstance(block, Mapping) else None


'''
_IMPORT_AFTER = "import secrets\nimport stat\nimport sys\nimport threading\n"
_IMPORT_BEFORE = "import secrets\nimport threading\n"
_SITE_BEFORE = "        super().__init__(what)\n\n\n"
_SITE_AFTER = (
    "# ------------------------------------------------------------"
    "--------------------------------------\n"
    "# HMP-side directory: the `chats` row and the operator label. Read only.\n"
)


def reverse_approved_push_diagnostics(source: str) -> str:
    """Refuse changed, duplicate or relocated helper/imports; strip exact approved bytes."""
    assert (
        hashlib.sha256(APPROVED_PUSH_BLOCK.encode("utf-8")).hexdigest()
        == APPROVED_PUSH_BLOCK_SHA256
    )
    assert source.count("def read_push_settings_for_diagnostics(") == 1
    site = _SITE_BEFORE + APPROVED_PUSH_BLOCK + _SITE_AFTER
    assert source.count(site) == 1
    assert source.count(_IMPORT_AFTER) == 1
    assert source.count("import sys\n") == 1
    assert source.count("import stat\n") == 1
    restored = source.replace(site, _SITE_BEFORE + _SITE_AFTER, 1)
    return restored.replace(_IMPORT_AFTER, _IMPORT_BEFORE, 1)


def assert_approved_s5_block(block: str) -> None:
    """Exact approved83 media body witness; never learn a replacement hash from current source."""
    assert hashlib.sha256(block.encode("utf-8")).hexdigest() == APPROVED_S5_BLOCK_SHA256


# Exact independently accepted AT1 accessor/factory addition on 9535. Test-only
# restoration; production and dynamic lookup detectors are not changed.
APPROVED_PRE_AT1_BRIDGE_SHA256 = (
    "2e3e3a509c73aac54c93bbf1a6c5965e5c9fb29b2b9c0ead331e104ef29bb25f"
)
APPROVED_AT1_BRIDGE_BLOCK_SHA256 = (
    "06ec0263ad2aa29e980354e7fba74de0620b69ab3d793fa82055597c93ad5f88"
)
APPROVED_AT1_BRIDGE_BLOCK = (
    r'''    def approval_test_target(self, profile: str) -> ApprovalTestTarget | None:
        """AT1 reads only routed home and canonical identity metadata in HMP.

        Native helpers can materialize rows/perform usage or registry housekeeping.
        No HMP message-head/body/prompt access, session lease or fallback is admitted.
        """
        def valid_id(value: object) -> bool:
            if type(value) is not str or not value or len(value) > 256:
                return False
            try:
                return len(value.encode('utf-8')) <= 256 and not any(
                    ord(char) < 32 or 127 <= ord(char) <= 159 for char in value
                )
            except UnicodeError:
                return False

        def run() -> ApprovalTestTarget | None:
            home = self._profile_home(profile)
            if not isinstance(home, Path) or not home.is_absolute():
                raise BridgeError('approval test target unavailable')
            with self._db(profile) as db:
                if self._profile_home(profile) != home:
                    raise BridgeError('approval test target unavailable')
                row = db.get_session_by_title(_CANONICAL_BOT_CHAT_TITLE)
                if row is None:
                    return None
                if not isinstance(row, Mapping):
                    raise BridgeError('approval test target unavailable')
                titled_id = row.get('id')
                del row
                if not valid_id(titled_id):
                    raise BridgeError('approval test target unavailable')
                # Same native resume helper as _tip, but AT1 cannot use its malformed-result
                # fallback. Ordinary _tip/resolve_bot_chat retain their existing behavior.
                tip = db.resolve_resume_session_id(titled_id)
                if not valid_id(tip):
                    raise BridgeError('approval test target unavailable')
                lineage = db.get_compression_lineage(titled_id)
                if (
                    not isinstance(lineage, (list, tuple)) or not 1 <= len(lineage) <= 100
                    or not all(valid_id(value) for value in lineage)
                    or len(set(lineage)) != len(lineage)
                ):
                    raise BridgeError('approval test target unavailable')
                class ParentMetadata:
                    def get_session(self, session_id: str) -> Mapping[str, object]:
                        native_row = db.get_session(session_id)
                        if not isinstance(native_row, Mapping):
                            raise BridgeError('approval test target unavailable')
                        row_id = native_row.get('id')
                        parent_id = native_row.get('parent_session_id')
                        del native_row
                        if not valid_id(row_id) or row_id != session_id:
                            raise BridgeError('approval test target unavailable')
                        if parent_id not in (None, '') and not valid_id(parent_id):
                            raise BridgeError('approval test target unavailable')
                        return {'id': row_id, 'parent_session_id': parent_id}

                metadata = ParentMetadata()
                from_tip = _parent_chain(metadata, tip)
                from_title = from_tip if titled_id == tip else _parent_chain(metadata, titled_id)
                if (
                    not from_tip or not from_title or from_tip[0] != from_title[0]
                    or not all(valid_id(value) for value in (*from_tip, *from_title))
                ):
                    raise BridgeError('approval test target unavailable')
                chain = _union_session_ids(from_tip, from_title, lineage, titled_id, tip)
                if not 1 <= len(chain) <= 100 or tip not in chain or titled_id not in chain:
                    raise BridgeError('approval test target unavailable')
                if self._profile_home(profile) != home:
                    raise BridgeError('approval test target unavailable')
                target = ApprovalTestTarget(home, chain[0], tip)
            return target  # Release failure propagates; no native row/DB escapes.

        return self._read(run)

    def approval_test_producer_factory(self, loop: asyncio.AbstractEventLoop) -> Any:
        """Unwired, feature-gated caller prerequisite; capture exact native helper objects.

        Missing/changed sampled helper signatures refuse. No commit allowlist, native
        implementation copy, private-table write, synthetic module or fallback is installed.
        """
        try:
            from tools import approval, approval_gateway_wait, interrupt

            from .approval_test_producer import ApprovalTestProducer, NativeApprovalBindings

            native = NativeApprovalBindings(
                waiter_module=approval_gateway_wait, approval_module=approval,
                interrupt_module=interrupt,
            )
            if not native.current():
                raise BridgeError('approval test helper unavailable')
        except Exception:
            raise BridgeError('approval test helper unavailable') from None

        def factory(*, publish: Any, remove: Any) -> ApprovalTestProducer:
            if not native.current():
                raise BridgeError('approval test helper unavailable')
            return ApprovalTestProducer(loop=loop, native=native, publish=publish, remove=remove)

        return factory, native.current

'''
)
_AT1_SITE_BEFORE = (
    "    # Amendment F2 (direct send, HMP_V1.md §7a DS-4/DS-6)\n"
    "    # ------------------------------------------------------------"
    "------------------------------\n"
    "\n"
)
_AT1_SITE_AFTER = "    def resolve_bot_chat(self, profile: str) -> BotChatTarget | None:\n"
_AT1_IMPORT_BEFORE = "    TOOL_OUTPUT_CAP,\n    AuthorizeResult,\n"
_AT1_IMPORT_AFTER = "    TOOL_OUTPUT_CAP,\n    ApprovalTestTarget,\n    AuthorizeResult,\n"


def reverse_approved_at1_bridge(source: str) -> str:
    """Strip only the reviewed exact block/import at their original sites."""
    assert hashlib.sha256(APPROVED_AT1_BRIDGE_BLOCK.encode()).hexdigest() == (
        APPROVED_AT1_BRIDGE_BLOCK_SHA256
    )
    assert source.count("    def approval_test_target(") == 1
    assert source.count("    def approval_test_producer_factory(") == 1
    assert source.count("    ApprovalTestTarget,\n") == 1
    assert source.count(_AT1_IMPORT_AFTER) == 1
    site = _AT1_SITE_BEFORE + APPROVED_AT1_BRIDGE_BLOCK + _AT1_SITE_AFTER
    assert source.count(site) == 1
    restored = source.replace(site, _AT1_SITE_BEFORE + _AT1_SITE_AFTER, 1)
    return restored.replace(_AT1_IMPORT_AFTER, _AT1_IMPORT_BEFORE, 1)
