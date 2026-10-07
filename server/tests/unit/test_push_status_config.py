"""Diagnostic configuration reads refuse malformed files without native recovery logs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest
import yaml

from hmp_plugin import bridge


@pytest.fixture
def primitives(monkeypatch):
    """Pure fake dependencies; native primitive parity has a separate isolated probe."""

    def module(name, **attrs):
        monkeypatch.setitem(sys.modules, name, types.SimpleNamespace(**attrs))

    def merge(config, gateway, legacy):
        del gateway, legacy
        return config.get("platforms", {})

    module("gateway.config_loader", merge_platform_sections=merge)
    module(
        "hermes_cli.config",
        _deep_merge=lambda user, managed: user | managed,
        _expand_env_vars=lambda value: value,
        _normalize_root_model_keys=lambda value: value,
    )
    module("hermes_cli.managed_scope", get_managed_dir=lambda: None)
    module("utils", fast_safe_load=yaml.safe_load)


def test_flat_and_explicit_extra_precedence(tmp_path, primitives):
    flat = {"enabled": True}
    for block, expected in (
        ({"push": flat}, flat),
        ({"push": flat, "extra": {"push": None}}, None),
        ({"push": flat, "extra": {"push": {"enabled": False}}}, {"enabled": False}),
    ):
        (tmp_path / "config.yaml").write_text(json.dumps({"platforms": {"hmp": block}}))
        assert bridge.read_push_settings_for_diagnostics(tmp_path) == expected


@pytest.mark.parametrize("text", ["[private-malformed-canary", "- private-nonmapping-canary"])
def test_bad_yaml_raises_without_recovery_logging(tmp_path, primitives, text, caplog, capsys):
    (tmp_path / "config.yaml").write_text(text)
    with pytest.raises((yaml.YAMLError, bridge.BridgeError)):
        bridge.read_push_settings_for_diagnostics(tmp_path)
    assert not caplog.records
    assert capsys.readouterr() == ("", "")


def test_bad_legacy_does_not_silently_fall_back(tmp_path, primitives, caplog):
    (tmp_path / "gateway.json").write_text("private-invalid-json-canary")
    with pytest.raises(ValueError):
        bridge.read_push_settings_for_diagnostics(tmp_path)
    assert not caplog.records


def test_oversize_configuration_is_bounded_and_never_creates_state(tmp_path, primitives):
    path = tmp_path / "config.yaml"
    path.write_bytes(b"#" * (1024 * 1024 + 1))
    before = path.read_bytes()
    with pytest.raises(bridge.BridgeError):
        bridge.read_push_settings_for_diagnostics(tmp_path)
    assert path.read_bytes() == before
    assert set(tmp_path.iterdir()) == {path}


def test_missing_optional_native_primitive_is_not_a_false_disabled_result(
    tmp_path, primitives, monkeypatch
):
    monkeypatch.setitem(sys.modules, "gateway.config_loader", None)
    with pytest.raises(ImportError):
        bridge.read_push_settings_for_diagnostics(tmp_path)
    assert not list(tmp_path.iterdir())


def test_no_native_config_bootstrap_is_triggered(tmp_path, monkeypatch):
    monkeypatch.delitem(sys.modules, "hermes_cli.config", raising=False)
    with pytest.raises(bridge.BridgeError):
        bridge.read_push_settings_for_diagnostics(tmp_path)
    assert "hermes_cli.config" not in sys.modules
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("filename", ["config.yaml", "gateway.json"])
@pytest.mark.parametrize("symlink", [False, True])
def test_fifo_configuration_refused_without_wait(tmp_path, filename, symlink):
    # Use a subprocess timeout: an accidental blocking open must fail the test
    # rather than hang the entire diagnostics regression suite.
    target = tmp_path / ("fifo-target" if symlink else filename)
    os.mkfifo(target)
    if symlink:
        (tmp_path / filename).symlink_to(target)
    code = """
import sys, types
from pathlib import Path
sys.modules['hermes_cli.config'] = types.SimpleNamespace(
    _deep_merge=lambda a, b: a | b, _expand_env_vars=lambda a: a,
    _normalize_root_model_keys=lambda a: a)
sys.modules['gateway.config_loader'] = types.SimpleNamespace(
    merge_platform_sections=lambda a, b, c: {})
sys.modules['hermes_cli.managed_scope'] = types.SimpleNamespace(get_managed_dir=lambda: None)
sys.modules['utils'] = types.SimpleNamespace(fast_safe_load=lambda a: {})
from hmp_plugin.bridge import BridgeError, read_push_settings_for_diagnostics
try:
    read_push_settings_for_diagnostics(Path(sys.argv[1]))
except BridgeError:
    sys.exit(0)
sys.exit(1)
"""
    env = dict(os.environ, PYTHONPATH=str(Path(bridge.__file__).resolve().parents[1]))
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        env=env,
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert result.stdout == result.stderr == b""
    assert target.stat().st_size == 0


def test_symlink_to_regular_configuration_remains_supported(tmp_path, primitives):
    target = tmp_path / "regular-target"
    target.write_text('{"platforms":{"hmp":{"push":{"enabled":true}}}}')
    (tmp_path / "config.yaml").symlink_to(target)
    assert bridge.read_push_settings_for_diagnostics(tmp_path) == {"enabled": True}
