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
