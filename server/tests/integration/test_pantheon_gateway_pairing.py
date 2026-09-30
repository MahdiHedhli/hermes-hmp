"""Optional two-profile, real-gateway pairing check on exact Hermes ``v2026.8.31``.

Requires ``HMP_PANTHEON_CLONE`` and an isolated interpreter in
``HMP_PANTHEON_RUNTIME_PYTHON`` containing the tag's frozen base dependencies
plus HMP's declared dependencies. Every Hermes home, plugin copy, key, token,
and database lives under pytest's disposable scratch directory. The old read
bridge stays closed: this proves live pairing, not Bot Chat qualification.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import os
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import time
from pathlib import Path

import pytest
from aiohttp import ClientConnectionError, ClientSession, Fingerprint

from hmp_plugin import crypto, wire
from hmp_plugin.contract import TAG_OFFER, TAG_PAIR_DONE, TAG_PAIR_REQ
from hmp_plugin.pairing import confirm_pairing
from hmp_plugin.store import Store

_EXTRACT_SPEC = importlib.util.spec_from_file_location(
    "pantheon_live_extract",
    Path(__file__).resolve().parents[3] / "tools" / "hermes_builds" / "extract.py",
)
assert _EXTRACT_SPEC is not None and _EXTRACT_SPEC.loader is not None
_extract = importlib.util.module_from_spec(_EXTRACT_SPEC)
sys.modules[_EXTRACT_SPEC.name] = _extract
_EXTRACT_SPEC.loader.exec_module(_extract)

PANTHEON_TAG = "v2026.8.31"
PANTHEON_SHA = "29112bef099274229cadff79cdff7bf7b99c4b77"


def _free_loopback_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _prepare_home(tmp_path: Path, port: int) -> tuple[Path, Path]:
    home = tmp_path / "home"
    state = tmp_path / "state"
    plugin = home / "plugins" / "hmp"
    source_plugin = Path(__file__).resolve().parents[2] / "hmp_plugin"
    plugin.parent.mkdir(parents=True)
    shutil.copytree(source_plugin, plugin, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (home / "profiles" / "serenity").mkdir(parents=True)
    state.mkdir()
    (home / "config.yaml").write_text(
        "plugins:\n"
        '  enabled: ["hmp"]\n'
        "  disabled: []\n"
        "  entries:\n"
        "    hmp:\n"
        "      allow_tool_override: false\n"
        "gateway:\n"
        "  multiplex_profiles: true\n"
        '  multiplex_profile_allowlist: ["serenity"]\n'
        "  profile_routes:\n"
        "    - name: hmp-default\n"
        "      platform: hmp\n"
        "      guild_id: default\n"
        "      profile: default\n"
        "    - name: hmp-serenity\n"
        "      platform: hmp\n"
        "      guild_id: serenity\n"
        "      profile: serenity\n"
        "  platforms:\n"
        "    hmp:\n"
        "      enabled: true\n"
        "      extra:\n"
        '        bind: "127.0.0.1"\n'
        f"        port: {port}\n",
        encoding="utf-8",
    )
    (home / "profiles" / "serenity" / "config.yaml").write_text(
        "gateway:\n  platforms: {}\n", encoding="utf-8"
    )
    return home, state


def _store_pairing_state(home: Path, oid: str, secret: bytes, user_id: str, now: int) -> None:
    store = Store(home / "plugin-data" / "hmp" / "hmp.sqlite3")
    try:
        store.migrate()
        store.insert_offer(oid, crypto.secret_hash(TAG_OFFER, secret), now + 300)
        store.insert_user(user_id, "synthetic", now)
    finally:
        store.close()


async def _exercise_gateway(home: Path, port: int, proc: subprocess.Popen[bytes]) -> None:
    cert_path = home / "plugin-data" / "hmp" / "instance" / "instance_cert.pem"
    base = f"https://127.0.0.1:{port}/hmp/v1"
    async with ClientSession() as client:
        for _ in range(200):
            if proc.poll() is not None:
                raise AssertionError("scratch gateway exited before HMP readiness")
            if cert_path.is_file():
                cert = ssl.PEM_cert_to_DER_cert(cert_path.read_text(encoding="utf-8"))
                pin = Fingerprint(hashlib.sha256(cert).digest())
                try:
                    async with client.get(base + "/ready", ssl=pin) as response:
                        if response.status == 200:
                            ready = await response.json()
                            break
                except (ClientConnectionError, OSError):
                    pass
            await asyncio.sleep(0.25)
        else:
            raise AssertionError("scratch gateway did not expose pinned HMP readiness")

        assert ready["write_gate"]["state"] == "closed"
        status = json.loads((home / "gateway_state.json").read_text(encoding="utf-8"))
        assert set(status["served_profiles"]) == {"default", "serenity"}
        assert status["hermes_home"] == str(home)
        iid = ready["iid"]

        key = crypto.generate_private_key()
        pub = crypto.spki_der(key.public_key())
        nd = crypto.random_bytes(32)
        name = "synthetic paired client"
        oid_raw, secret = crypto.random_bytes(16), crypto.random_bytes(32)
        oid = wire.b64u_encode(oid_raw)
        user_id = "hmpu_" + crypto.random_bytes(16).hex()
        now = int(time.time())
        _store_pairing_state(home, oid, secret, user_id, now)
        request_text = crypto.transcript(
            TAG_PAIR_REQ, iid, oid_raw, crypto.sha256(secret), pub, name, nd
        )
        body = {
            "v": 1,
            "oid": oid,
            "s": wire.b64u_encode(secret),
            "device_name": name,
            "device_pub": wire.b64u_encode(pub),
            "nd": wire.b64u_encode(nd),
            "sig": wire.b64u_encode(crypto.sign(key, request_text)),
        }
        async with client.post(
            base + "/pair/request", data=wire.dump_json(body), ssl=pin
        ) as response:
            assert response.status == 202
            pending = await response.json()
        pairing_id = pending["pairing_id"]
        ni = wire.b64u_decode(pending["ni"], length=32)

        store = Store(home / "plugin-data" / "hmp" / "hmp.sqlite3")
        try:
            store.migrate()
            confirm_pairing(store, pairing_id, user_id=user_id, label="synthetic", now=now)
        finally:
            store.close()
        done_text = crypto.transcript(
            TAG_PAIR_DONE, iid, wire.b64u_decode(pairing_id, length=16), nd, ni, now
        )
        done_body = {
            "pairing_id": pairing_id,
            "ts": now,
            "sig": wire.b64u_encode(crypto.sign(key, done_text)),
        }
        async with client.post(
            base + "/pair/complete", data=wire.dump_json(done_body), ssl=pin
        ) as response:
            assert response.status == 200
            complete = await response.json()
        assert isinstance(complete.get("access_token"), str)
        headers = {
            "Authorization": "Bearer " + complete["access_token"],
            "HMP-Instance": iid,
        }
        async with client.get(base + "/bots", headers=headers, ssl=pin) as response:
            assert response.status == 503
            assert (await response.json())["error"]["why"] == "hermes_build_unsupported"


@pytest.mark.skipif(
    not os.environ.get("HMP_PANTHEON_CLONE") or not os.environ.get("HMP_PANTHEON_RUNTIME_PYTHON"),
    reason="set the exact-tag clone and isolated pinned runtime to run the live fixture",
)
def test_pantheon_gateway_pairs_with_two_profiles_but_refuses_reads(tmp_path: Path) -> None:
    _extract.assert_outside_real_home(tmp_path, "Pantheon live gateway scratch")
    clone = Path(os.environ["HMP_PANTHEON_CLONE"]).resolve()
    # Keep the venv launcher path: resolving its symlink would invoke the base
    # interpreter without the pinned package set.
    runtime = Path(os.environ["HMP_PANTHEON_RUNTIME_PYTHON"]).expanduser().absolute()
    assert (clone / ".git").exists() and runtime.is_file()
    assert _extract.ref_resolves(clone, PANTHEON_TAG) == PANTHEON_SHA
    source = tmp_path / "pantheon" / "src"
    _extract.extract_tree(clone, PANTHEON_SHA, source)
    port = _free_loopback_port()
    home, state = _prepare_home(tmp_path, port)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "HERMES_HOME": str(home),
        "XDG_STATE_HOME": str(state),
        "PYTHONPATH": str(source),
    }
    log_path = tmp_path / "gateway.log"
    with log_path.open("wb") as log:
        # The old CLI's launchd guard can see the owner's unrelated supervised
        # service. Force is confined to this checked disposable HERMES_HOME;
        # never use this fixture against the owner's live profile.
        proc = subprocess.Popen(
            [str(runtime), "-m", "hermes_cli.main", "gateway", "run", "--force"],
            cwd=source,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            asyncio.run(_exercise_gateway(home, port, proc))
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=10)
