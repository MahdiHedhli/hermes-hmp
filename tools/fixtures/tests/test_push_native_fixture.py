"""Scratch wiring safety; no native gateway or network execution."""

from __future__ import annotations

from types import SimpleNamespace

import _fixture_common as fc
import push_native_fixture as fixture
import pytest
import yaml


def _paths(tmp_path):
    out = (tmp_path / "fixture").resolve()
    out.mkdir(mode=0o700)
    paths = fc.instance_paths(out, "A")
    (paths.home / "plugins").mkdir(parents=True)
    scratch = out / "_hmp_plugin"
    scratch.mkdir(mode=0o700)
    (paths.home / "plugins" / "hmp").symlink_to(scratch, target_is_directory=True)
    bootstrap = b'"""Synthetic fixture bootstrap."""\n'
    (scratch / "__init__.py").write_bytes(bootstrap)
    (paths.home / "config.yaml").write_text(yaml.safe_dump({
        "gateway": {"platforms": {"hmp": {"extra": {
            "owner_device_ids": ["synthetic-owner"], "direct_send": {"enabled": True},
        }}}},
    }))
    return paths, scratch, bootstrap


def test_install_is_confined_idempotent_and_preserves_actual_authority_settings(tmp_path):
    paths, scratch, bootstrap = _paths(tmp_path)
    relay = SimpleNamespace(url="https://127.0.0.1:32123/base", leaf_pin=b"p" * 32)
    root = fixture.install_fixture(paths, relay)
    fixture.install_fixture(paths, relay)
    assert (scratch / "__init__.py").read_bytes() == bootstrap + fixture.BOOTSTRAP_SUFFIX.encode()
    assert (scratch / "_push_native_observer.py").stat().st_mode & 0o777 == 0o600
    value = yaml.safe_load((paths.home / "config.yaml").read_text())
    extra = value["gateway"]["platforms"]["hmp"]["extra"]
    assert extra["owner_device_ids"] == ["synthetic-owner"]
    assert extra["direct_send"] == {"enabled": True}
    assert extra["push"]["relay_url"] == relay.url and len(extra["push"]["relay_spki_pins"]) == 1
    fixture.arm(root)
    fixture.release(root)
    with pytest.raises(ValueError, match="already released"):
        fixture.arm(root)


def test_install_refuses_bootstrap_symlink_without_changing_target(tmp_path):
    paths, scratch, bootstrap = _paths(tmp_path)
    target = tmp_path / "outside-bootstrap"
    target.write_bytes(bootstrap)
    (scratch / "__init__.py").unlink()
    (scratch / "__init__.py").symlink_to(target)
    relay = SimpleNamespace(url="https://127.0.0.1:32123/base", leaf_pin=b"p" * 32)
    with pytest.raises(fc.FixtureSafetyError, match="symlink"):
        fixture.install_fixture(paths, relay)
    assert target.read_bytes() == bootstrap
