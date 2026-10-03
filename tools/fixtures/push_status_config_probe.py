"""Isolated native pure-config parity probe for PN-OPS; never loads a gateway."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--hermes-source", type=Path, required=True)
args = parser.parse_args()
native = args.hermes_source.resolve(strict=True)
plugin = Path(__file__).resolve().parents[2] / "server"
sha = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=native, check=True, capture_output=True, text=True
).stdout.strip()
sys.path.insert(0, str(native))
sys.path.insert(0, str(plugin))
with tempfile.TemporaryDirectory(prefix="hmp-push-status-native-") as t:
    root = Path(t) / "home"
    root.mkdir()
    managed = Path(t) / "managed"
    managed.mkdir()
    for key in list(os.environ):
        if key.startswith("HERMES_"):
            os.environ.pop(key)
    os.environ.update(
        HERMES_HOME=str(root),
        HERMES_MANAGED_DIR=str(managed),
        STATUS_RELAY="https://relay.invalid/base",
    )
    # Native `hermes hmp` has already bootstrapped PluginContext/config before
    # dispatch. Keep its first-run SOUL seed distinct from diagnostic I/O.
    import hermes_cli.plugins  # noqa: F401 - reproduce native CLI bootstrap

    bootstrap_files = sorted(str(p.relative_to(t)) for p in Path(t).rglob("*") if p.is_file())
    initial_files = {str(p) for p in Path(t).rglob("*") if p.is_file()}
    initial_env = dict(os.environ)
    from gateway.config import PlatformConfig
    from gateway.config_loader import merge_platform_sections, read_yaml_layers
    from hmp_plugin.bridge import read_push_settings_for_diagnostics
    from hmp_plugin.push_config import configuration_summary

    assert {str(p) for p in Path(t).rglob("*") if p.is_file()} == initial_files
    assert initial_env == dict(os.environ)

    def snap():
        return {
            str(p.relative_to(t)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path(t).rglob("*")
            if p.is_file()
        }

    base = {
        "enabled": True,
        "relay_url": "${STATUS_RELAY}",
        "relay_audience": "synthetic",
        "relay_kids": ["kid-a"],
    }
    disabled = base | {"enabled": False}
    cases = [
        (
            "nested",
            {"gateway": {"platforms": {"hmp": {"extra": {"push": base}}}}},
            {},
            {},
            (True, True, 1),
        ),
        ("flat", {"platforms": {"hmp": {"push": base}}}, {}, {}, (True, True, 1)),
        (
            "flat-extra-collision",
            {"platforms": {"hmp": {"push": base, "extra": {"push": disabled}}}},
            {},
            {},
            (False, True, 1),
        ),
        (
            "top-nested-collision",
            {
                "gateway": {"platforms": {"hmp": {"extra": {"push": base}}}},
                "platforms": {"hmp": {"extra": {"push": disabled}}},
            },
            {},
            {},
            (False, True, 1),
        ),
        (
            "legacy",
            {},
            {
                "platforms": {
                    "hmp": {"extra": {"push": base | {"relay_url": "https://relay.invalid/base"}}}
                }
            },
            {},
            (True, True, 1),
        ),
        (
            "managed-leaf",
            {"platforms": {"hmp": {"extra": {"push": base}}}},
            {},
            {"platforms": {"hmp": {"extra": {"push": {"enabled": False}}}}},
            (False, True, 1),
        ),
        ("absent", {}, {}, {}, (False, False, 0)),
        (
            "null-extra-overrides-flat",
            {"platforms": {"hmp": {"push": base, "extra": {"push": None}}}},
            {},
            {},
            (False, False, 0),
        ),
    ]
    rows = []
    for name, config, legacy, mng, expected in cases:
        (root / "config.yaml").write_text(json.dumps(config))
        (root / "gateway.json").write_text(json.dumps(legacy))
        (managed / "config.yaml").write_text(json.dumps(mng))
        from hermes_cli.managed_scope import invalidate_managed_cache

        invalidate_managed_cache()
        before = snap()
        env_before = dict(os.environ)
        actual = configuration_summary(read_push_settings_for_diagnostics(root))
        resolved = merge_platform_sections(
            read_yaml_layers(root),
            read_yaml_layers(root).get("gateway"),
            json.loads((root / "gateway.json").read_text()),
        )
        block = resolved.get("hmp", {})
        native = configuration_summary(PlatformConfig.from_dict(block).extra.get("push"))
        assert actual == native == expected, (name, actual, native, expected)
        assert before == snap() and env_before == dict(os.environ)
        rows.append(
            {
                "case": name,
                "expected": expected,
                "native_matches": True,
                "files_unchanged": True,
                "environment_unchanged": True,
            }
        )
    print(
        json.dumps(
            {
                "hermes_git_sha": sha,
                "cases": rows,
                "native_cli_bootstrap_files": bootstrap_files,
                "scope": "isolated native pure config parity; no loader hooks or gateway traffic",
            }
        )
    )
