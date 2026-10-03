"""The package matches the module tree in contracts/server-modules.md (T013)."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"

CONTRACT_MODULES = {
    "__init__.py",
    "contract.py",
    "wire.py",
    "crypto.py",
    "identity.py",
    "store.py",
    "compat.py",
    "hermes_version.py",
    "issue_draft.py",
    "bridge.py",
    "pairing.py",
    "tokens.py",
    "push_issuer.py",
    "push_config.py",
    "push_registration.py",
    "push_hints.py",
    "push_resolve.py",
    "push_dispatch.py",
    "push_relay.py",
    "auth.py",
    "reads.py",
    "authorize.py",
    "revoke.py",
    "gate.py",
    "direct_send.py",
    "prompts.py",
    "mobile_cron.py",
    "mobile_model.py",
    "server.py",
    "request_ctx.py",
    "adapter.py",
    "cli.py",
    "logging_policy.py",
}
DATA_FILES = {
    "plugin.yaml",
    "read_compat_builds.json",
    "write_supported_builds.json",
    "mobile_cron_supported_builds.json",
    "mobile_model_supported_builds.json",
}


def test_module_set_is_exactly_the_contract_tree() -> None:
    assert {p.name for p in PACKAGE.glob("*.py")} == CONTRACT_MODULES
    assert not [p for p in PACKAGE.iterdir() if p.is_dir() and p.name != "__pycache__"]


def test_data_files_present() -> None:
    assert {p.name for p in PACKAGE.iterdir()} >= DATA_FILES


# adapter.py subclasses Hermes's BasePlatformAdapter, so it imports only inside a Hermes env.
@pytest.mark.parametrize(
    "module", sorted(m[:-3] for m in CONTRACT_MODULES - {"__init__.py", "adapter.py"})
)
def test_module_imports_without_hermes(module: str) -> None:
    importlib.import_module(f"hmp_plugin.{module}")


def test_read_compat_list_shape() -> None:
    data = json.loads((PACKAGE / "read_compat_builds.json").read_text(encoding="utf-8"))
    assert set(data) == {"format", "bridge_files", "builds"}
    assert data["format"] == 1
    assert isinstance(data["builds"], list)
    files = data["bridge_files"]
    assert files == sorted(set(files)) and all(f.endswith(".py") for f in files)


def test_write_supported_list_shape() -> None:
    data = json.loads((PACKAGE / "write_supported_builds.json").read_text(encoding="utf-8"))
    assert data == {"format": 1, "builds": []}  # GU-2a matrix stays empty in F1 (T064)
