"""Child process for the optional exact-Pantheon-tag HMP adapter fixture.

The parent test pins PYTHONPATH to the archived Hermes tag plus this HMP source and points
HERMES_HOME/XDG_STATE_HOME at disposable scratch directories. This child never starts the
Hermes gateway, but does use the old platform registry and HMP's real TLS listener.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import socket
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from aiohttp import ClientSession, Fingerprint
from gateway.platform_registry import PlatformEntry, platform_registry

import hmp_plugin
from hmp_plugin.adapter import HmpAdapter
from hmp_plugin.compat import CompatStatus


def _scratch_env(name: str) -> Path:
    path = Path(os.environ[name]).resolve()
    real_home = Path.home().resolve()
    assert path.is_absolute() and path != real_home and real_home not in path.parents
    return path


class RegistryContext:
    def __init__(self) -> None:
        self.cli_registered = False

    def register_platform(self, **kwargs: Any) -> None:
        platform_registry.register(PlatformEntry(**kwargs))

    def register_cli_command(self, **kwargs: Any) -> None:
        assert kwargs["name"] == "hmp"
        self.cli_registered = True


async def main() -> None:
    home = _scratch_env("HERMES_HOME")
    state = _scratch_env("XDG_STATE_HOME")
    (home / "plugin-data" / "hmp" / "instance").mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    registration = RegistryContext()
    hmp_plugin.register(registration)
    assert registration.cli_registered
    adapter = platform_registry.create_adapter(
        "hmp", SimpleNamespace(extra={"bind": "127.0.0.1", "port": port})
    )
    assert isinstance(adapter, HmpAdapter)
    try:
        assert await adapter.connect()
        listener = adapter._server
        assert listener is not None and listener.bound is not None
        assert listener.ctx.compat.status is CompatStatus.UNSUPPORTED
        assert listener.ctx.bridge is None and listener.ctx.reads is None
        assert "hmp_plugin.bridge" not in sys.modules

        # Pin the self-signed listener certificate to the exact HMP instance for this fixture.
        pin = Fingerprint(hashlib.sha256(listener.ctx.identity.certificate_der()).digest())
        base = f"https://127.0.0.1:{listener.bound[1]}/hmp/v1"
        async with ClientSession() as client:
            async with client.get(base + "/ready", ssl=pin) as response:
                assert response.status == 200
                assert (await response.json())["write_gate"]["state"] == "closed"
            async with client.get(base + "/bots", ssl=pin) as response:
                assert response.status == 503
                assert (await response.json())["error"]["why"] == "hermes_build_unsupported"
    finally:
        await adapter.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
