"""Optional exact-tag regression for pairing on an unqualified Hermes build.

Set ``HMP_PANTHEON_CLONE`` to a local Hermes git clone containing ``v2026.8.31``.
The test archives that immutable tag into pytest's scratch directory, leaving the clone and
the owner's live Hermes home untouched. It exercises HMP's real compat gate and HTTP handlers;
it does not claim that an old Hermes gateway process has been started or qualified for Bot Chat.

Set ``HMP_PANTHEON_RUNTIME_PYTHON`` to an isolated interpreter populated from
that tag's frozen base lock plus HMP's declared runtime packages to run the
additional old-ingress authorization probe. The base pairing fixture works
without it, using only HMP's own test environment.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient

from hmp_plugin import compat
from hmp_plugin.compat import CompatGate, CompatStatus, GitFingerprintReader
from hmp_plugin.contract import OtherWhy

from .hmp_kit import Env, get, pair, post, run

_EXTRACT_SPEC = importlib.util.spec_from_file_location(
    "pantheon_fixture_extract",
    Path(__file__).resolve().parents[3] / "tools" / "hermes_builds" / "extract.py",
)
assert _EXTRACT_SPEC is not None and _EXTRACT_SPEC.loader is not None
_extract = importlib.util.module_from_spec(_EXTRACT_SPEC)
sys.modules[_EXTRACT_SPEC.name] = _extract
_EXTRACT_SPEC.loader.exec_module(_extract)

PANTHEON_TAG = "v2026.8.31"
PANTHEON_SHA = "29112bef099274229cadff79cdff7bf7b99c4b77"
MISSING_BRIDGE_FILES = frozenset(
    {
        "gateway/platforms/_shared.py",
        "gateway/platforms/event.py",
        "gateway/run_adapters.py",
        "gateway/run_profile_reconcile.py",
        "hermes_state_compression.py",
        "hermes_state_messages.py",
        "hermes_state_registry.py",
        "hermes_state_sessions.py",
    }
)


@pytest.mark.skipif(
    not os.environ.get("HMP_PANTHEON_CLONE"),
    reason="set HMP_PANTHEON_CLONE to a local clone with the v2026.8.31 tag",
)
def test_pantheon_allows_pairing_but_no_hermes_routes(tmp_path: Path) -> None:
    _extract.assert_outside_real_home(tmp_path, "Pantheon fixture scratch")
    clone = Path(os.environ["HMP_PANTHEON_CLONE"]).resolve()
    assert (clone / ".git").exists(), "fixture must be a git clone"
    assert _extract.ref_resolves(clone, PANTHEON_TAG) == PANTHEON_SHA
    before = _extract.clone_snapshot(clone)
    root = tmp_path / "pantheon" / "src"
    _extract.extract_tree(clone, PANTHEON_SHA, root)
    assert _extract.clone_snapshot(clone) == before

    manifest = compat.load_read_compat_list(
        Path(compat.__file__).with_name(compat.READ_COMPAT_FILE)
    )
    assert (root / "hermes_constants.py").is_file()
    missing = {name for name in manifest.bridge_files if not (root / name).is_file()}
    assert missing == MISSING_BRIDGE_FILES
    assert compat.compute_read_bridge_fingerprint(root, manifest.bridge_files) is None

    def forbidden_probe() -> tuple[()]:
        raise AssertionError("unqualified build must not probe Hermes imports")

    hermes_modules_before = {
        name for name in sys.modules if name.split(".")[0] in {"gateway", "hermes_state"}
    }
    result = CompatGate(
        GitFingerprintReader(manifest.bridge_files),
        manifest,
        forbidden_probe,
        root_locator=lambda: root,
    ).evaluate()
    assert result.status is CompatStatus.UNSUPPORTED
    assert result.why is OtherWhy.HERMES_BUILD_UNSUPPORTED
    assert {
        name for name in sys.modules if name.split(".")[0] in {"gateway", "hermes_state"}
    } == hermes_modules_before

    # Use the old platform registry and the real HMP TLS listener in a fresh interpreter.
    # Both Hermes and XDG state stay in the scratch fixture. The parent below separately
    # exercises signed pairing and self-revoke through the same server handlers.
    server_root = Path(__file__).resolve().parents[2]
    import_probe = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("pantheon_adapter_probe.py"))],
        cwd=root,
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.pathsep.join((str(root), str(server_root))),
            "HERMES_HOME": str(tmp_path / "isolated-hermes-home"),
            "XDG_STATE_HOME": str(tmp_path / "isolated-xdg-state"),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert import_probe.returncode == 0, import_probe.stderr[-2000:]

    runtime_python = os.environ.get("HMP_PANTHEON_RUNTIME_PYTHON")
    if runtime_python:
        assert Path(runtime_python).is_file(), "old Hermes runtime interpreter is missing"
        ingress_probe = subprocess.run(
            [runtime_python, str(Path(__file__).with_name("pantheon_authz_probe.py"))],
            cwd=root,
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONPATH": os.pathsep.join((str(root), str(server_root))),
                "HERMES_HOME": str(tmp_path / "isolated-authz-home"),
                "XDG_STATE_HOME": str(tmp_path / "isolated-authz-state"),
            },
            capture_output=True,
            text=True,
            check=False,
        )
        assert ingress_probe.returncode == 0, ingress_probe.stderr[-2000:]

    env = Env(tmp_path / "hmp-home", compat=result)
    assert env.ctx.bridge is None and env.ctx.reads is None

    async def scenario(client: TestClient) -> None:
        status, ready = await get(client, "/ready")
        assert status == 200
        assert ready["write_gate"]["state"] == "closed"

        device = await pair(env, client)
        status, refreshed = await post(client, "/auth/token", env.p5_body(device))
        assert status == 200
        device.access = refreshed["access_token"]

        for path in ("/bots", "/jobs", "/models"):
            status, body = await get(client, path, headers=env.headers(device))
            assert status == 503, path
            assert body["error"]["why"] == "hermes_build_unsupported"

        status, revoked = await post(
            client,
            "/devices/self/revoke",
            env.self_revoke_body(device),
            headers=env.headers(device),
        )
        assert (status, revoked) == (200, {})

    run(env, scenario)
    assert env.ctx.bridge is None and env.ctx.reads is None
