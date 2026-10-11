"""Merge regressions for carrying the reviewed approval lane (`1bcb586`) onto `4d6863e` (spec 034).

Each test pins one named hazard that a plain `git merge` introduces or hides. They read the
tracked tree only. The recorded hashes are the `4d6863e` bytes of the tested-sample manifests,
which spec 013 requires to stay byte for byte.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import re
import sys
import types
from pathlib import Path

import pytest

from hmp_plugin import cli, compat

PACKAGE = Path(compat.__file__).parent
SERVER = PACKAGE.parent
REPO = SERVER.parent

# sha256 of each sample manifest as committed at 4d6863e. A change here is a decision, not a drift.
MANIFEST_SHA256 = {
    "read_compat_builds.json": "7d3c4363fddd8c8c39da32b3aaf515414aba33cc90bda2e1ef81b14c68185d6d",
    "write_supported_builds.json": (
        "c0cd8aa6036b7e60569163e08cd6c7b930efeb271aa6231d426801753d1896c9"
    ),
    "direct_send_supported_builds.json": (
        "449c65c0c5bda076a050c43423cd280307f10abf41d3d3318b12ea99e558cdbe"
    ),
    "mobile_cron_supported_builds.json": (
        "fae6df719a1625ff478407d3b4f0bbbea9fe262aaba8efc76387f186588ac0a2"
    ),
    "mobile_model_supported_builds.json": (
        "cddd825b8378fddc25a2edb4f5a2361bd7f2f66a202a09339c1623feb08924b3"
    ),
}

# The four send rows of 4d6863e. H1: the package's F3 rows auto-merged into this table.
BASE_SEND_LABELS = (
    "hermes_cli.active_sessions.active_session_registry_snapshot",
    "hermes_state.SessionDB.get_session",
    "hermes_state.SessionDB.get_session_by_title",
    "hermes_state.SessionDB.get_compression_lineage",
)


def _module_sources() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(PACKAGE.glob("*.py"))}


def test_h1_the_send_table_is_exactly_the_four_base_rows() -> None:
    labels = tuple(spec.label for spec in compat.DIRECT_SEND_DEPENDENCIES)
    assert labels == BASE_SEND_LABELS
    for forbidden in ("tools.approval", "tools.clarify_gateway", "api_server", "gateway.run_busy"):
        assert not any(forbidden in label for label in labels), forbidden


def test_h1_phone_chat_rows_are_in_their_own_table_and_the_send_table_is_untouched() -> None:
    send = {spec.label for spec in compat.DIRECT_SEND_DEPENDENCIES}
    phone = {spec.label for spec in compat.PHONE_CHAT_DEPENDENCIES}
    assert not send & phone
    assert any("resolve_gateway_approval" in label for label in phone)


def test_h2_the_bridge_imports_without_any_exact_gate_symbol() -> None:
    """A top-level `from .compat import direct_send_build_qualified` made the bridge unimportable
    once compat was resolved to the base, which aborts `open_components` and loses read."""
    tree = ast.parse((PACKAGE / "bridge.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "compat":
            pytest.fail("bridge.py imports from compat")
    from hmp_plugin import bridge

    assert not hasattr(bridge.HermesReadBridge, "direct_send_qualified")
    # Importing it fresh against a compat module that has none of the legacy names also works.
    stub = types.ModuleType("hmp_plugin.compat")
    for name in list(sys.modules):
        if name == "hmp_plugin.bridge":
            saved = sys.modules.pop(name)
            break
    else:
        saved = None
    real = sys.modules["hmp_plugin.compat"]
    sys.modules["hmp_plugin.compat"] = stub
    try:
        importlib.import_module("hmp_plugin.bridge")
    finally:
        sys.modules["hmp_plugin.compat"] = real
        sys.modules.pop("hmp_plugin.bridge", None)
        if saved is not None:
            sys.modules["hmp_plugin.bridge"] = saved


def test_h3_no_module_references_a_name_the_base_removed() -> None:
    """The auto-merged approval lane called `probe_read_dependencies` and
    `_DEFAULT_READ_COMPAT_PATH`, which `4d6863e` no longer defines. The resulting NameError was
    swallowed in a `try`, so approvals stayed silently closed."""
    removed = {
        "probe_read_dependencies",
        "_DEFAULT_READ_COMPAT_PATH",
        "direct_send_build_qualified",
        "approval_build_qualified",
        "approval_listener_qualifier",
        "probe_approval_dependencies",
        "ApprovalProcessBaseline",
        "_approval_process_latch",
        "APPROVAL_DEPENDENCIES",
        "approval_qualified",
        "approval_qualification_open",
    }
    for name, text in _module_sources().items():
        for token in removed:
            assert token not in text, (name, token)
    defined = set(dir(compat))
    assert "probe_dependencies" in defined and "probe_read_dependencies" not in defined


def test_h3_every_compat_name_the_other_modules_import_exists() -> None:
    for name, text in _module_sources().items():
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "compat" and node.level == 1:
                for alias in node.names:
                    assert hasattr(compat, alias.name), (name, alias.name)
            is_compat_attr = (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "compat"
                and name != "compat.py"
            )
            if is_compat_attr:
                assert hasattr(compat, node.attr), (name, node.attr)


@pytest.mark.parametrize(("name", "digest"), sorted(MANIFEST_SHA256.items()))
def test_h4_the_sample_manifests_are_byte_for_byte_the_base(name: str, digest: str) -> None:
    assert hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() == digest


def test_h4_the_direct_send_manifest_keeps_its_four_sampled_builds() -> None:
    import json

    data = json.loads((PACKAGE / "direct_send_supported_builds.json").read_text("utf-8"))
    assert len(data["builds"]) == 4 and len(data["bridge_files"]) == 18
    assert "requalification_required" not in data


def test_h5_new_bot_routing_the_yaml_dependency_and_the_config_writer_are_absent() -> None:
    assert not (PACKAGE / "routes.py").exists()
    for manifest in (SERVER / "hmp_plugin" / "plugin.yaml", REPO / "plugin.yaml"):
        text = manifest.read_text(encoding="utf-8")
        deps = re.findall(r'^\s*-\s*"([^"]+)"', text.split("python_dependencies:", 1)[1], re.M)
        assert deps == ["qrcode>=7.4.2,<9"], manifest
    pyproject = (SERVER / "pyproject.toml").read_text(encoding="utf-8")
    runtime = pyproject.split("dependencies = [", 1)[1].split("]", 1)[0]
    assert "pyyaml" not in runtime.lower()
    surface = (REPO / "tools" / "ci" / "check_plugin_surface.py").read_text(encoding="utf-8")
    assert "ROUTES_MODULE" not in surface and '"yaml"' not in surface
    for name, text in _module_sources().items():
        assert "profile_routes" not in text or name in {"bridge.py", "authorize.py"}, name
        assert "routes add" not in text, name
    parser = __import__("argparse").ArgumentParser(prog="hermes hmp")
    cli.setup_parser(parser)
    with pytest.raises(SystemExit):
        parser.parse_args(["routes", "add", "x"])


def test_h5_the_owner_package_tool_and_the_exact_manifest_lane_are_absent() -> None:
    assert not (REPO / "tools" / "compat" / "owner_package.py").exists()
    assert not (REPO / "tools" / "fixtures" / "approval_fixture.py").exists()
    assert not (REPO / "tools" / "compat" / "approval_matrix.py").exists()
    assert not (PACKAGE / "approval_supported_builds.json").exists()
    package_data = (SERVER / "pyproject.toml").read_text(encoding="utf-8")
    assert "approval_supported_builds" not in package_data


def test_the_removed_gate_leaves_no_per_call_thread_hop_in_the_routes() -> None:
    """Member availability is a cached boolean: no `asyncio.to_thread` hop to ask it."""
    for name in ("server.py", "direct_send.py", "prompts.py"):
        text = (PACKAGE / name).read_text(encoding="utf-8")
        for hop in ("approval_qualif", "to_thread(self.approval_qualified"):
            assert hop not in text, (name, hop)


def test_no_runtime_module_reads_a_supported_builds_manifest_for_availability() -> None:
    """Only the evidence matcher in compat.py touches the tested-sample manifests."""
    readers = [
        name
        for name, text in _module_sources().items()
        if "_supported_builds" in text or "read_compat_builds" in text
    ]
    # bridge.py only names the file in a docstring; mobile_cron/model are the jobs/model features'
    # own evidence helpers, unchanged from the base and not wired into any availability decision.
    assert set(readers) <= {"bridge.py", "compat.py", "mobile_cron.py", "mobile_model.py"}, readers
    for name in ("server.py", "adapter.py", "request_ctx.py", "prompts.py", "direct_send.py"):
        assert name not in readers, name
    text = (PACKAGE / "compat.py").read_text(encoding="utf-8")
    assert "def match_evidence" in text
    for forbidden in ("latch", "ApprovalProcessBaseline"):
        assert forbidden not in text
