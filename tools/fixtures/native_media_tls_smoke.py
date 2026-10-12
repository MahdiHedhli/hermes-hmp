"""Opt-in disposable native/TLS/Dart smoke check; not physical qualification.

Arguments: private root, native source, HMP source, Dart binary, package config, Dart probe.
Caller must create the private home/plugin configuration and set HERMES_HOME/runtime.
Synthetic keys/tokens only; no live home or external provider is used.
"""

import json
import os
import pathlib
import sys


def produce_native_image(home, source):
    """One real native tool call against a fixed loopback response, no external provider."""
    import base64
    import http.server
    import threading

    import yaml

    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mMQMgn7DwAClAGc"
        "wgVUTwAAAABJRU5ErkJggg=="
    )
    requests = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            assert 0 < length <= 4096
            assert self.path == "/v1/images/generations"
            assert self.headers.get("Authorization") == "Bearer synthetic-only-key"
            request = json.loads(self.rfile.read(length))
            assert request["prompt"] == "[media-fixture] fixed raster"
            requests.append(request)
            body = json.dumps(
                {
                    "created": 0,
                    "data": [
                        {
                            "b64_json": base64.b64encode(png).decode(),
                        }
                    ],
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    worker = None
    worker_started = False
    try:
        server.timeout = 15
        config_path = home / "config.yaml"
        config = yaml.safe_load(config_path.read_text())
        config["image_gen"] = {
            "provider": "openai",
            "openai": {
                "provider": "synthetic",
                "model": "gpt-image-2",
            },
        }
        config["providers"] = {
            "synthetic": {
                "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                "api_key": "synthetic-only-key",
            }
        }
        config_path.write_text(yaml.safe_dump(config))
        worker = threading.Thread(target=server.handle_request)
        worker.start()
        worker_started = True
        import model_tools

        assert pathlib.Path(model_tools.__file__).resolve().is_relative_to(source)

        raw = model_tools.handle_function_call(
            "image_generate",
            {"prompt": "[media-fixture] fixed raster"},
            task_id="synthetic-media",
            tool_call_id="synthetic-fetch-call",
        )
        result = json.loads(raw)
        assert result.get("success") is True
        image = pathlib.Path(result["image"])
        assert image.is_relative_to(home / "cache/images")
        assert image.read_bytes() == png
        assert len(requests) == 1
        return raw, image
    finally:
        try:
            if worker_started:
                worker.join(21)
                assert not worker.is_alive()
        finally:
            server.server_close()


def main():
    root = pathlib.Path(sys.argv[1]).resolve()
    source = pathlib.Path(sys.argv[2]).resolve()
    hmp = pathlib.Path(sys.argv[3]).resolve()
    assert os.environ.get("HERMES_HOME") == str(root / "home")
    assert os.environ.get("HERMES_RUNTIME_DIR") == str(root / "runtime")
    for directory in (root, root / "home", root / "runtime"):
        metadata = directory.stat()
        assert metadata.st_uid == os.getuid()
        assert metadata.st_mode & 0o777 == 0o700
    assert not (root / "home" / "state.db").exists(), "requires a fresh disposable home"
    assert not (root / "dart-request.json").exists(), "existing token file refused"
    sys.path.insert(0, str(source))
    from gateway.config import GatewayConfig, PlatformConfig
    from gateway.pairing import PairingStore
    from gateway.platform_registry import platform_registry
    from gateway.profile_routing import ProfileRoute
    from gateway.run import GatewayRunner
    from hermes_cli.plugins import discover_plugins

    discover_plugins()
    adapter = platform_registry.get("hmp").adapter_factory(
        PlatformConfig(
            enabled=True,
            extra={
                "local_media": {"enabled": True},
                "owner_device_ids": ["synthetic-fetch-device"],
            },
        )
    )
    runner = GatewayRunner(
        GatewayConfig(
            multiplex_profiles=True,
            profile_routes=[
                ProfileRoute(
                    name="synthetic-default",
                    platform="hmp",
                    profile="default",
                    guild_id="default",
                )
            ],
        )
    )
    adapter.gateway_runner = runner
    module = sys.modules[type(adapter).__module__]
    assert pathlib.Path(module.__file__).resolve().is_relative_to(hmp)
    import gateway.run
    import hermes_constants

    for native in (gateway.run, hermes_constants):
        assert pathlib.Path(native.__file__).resolve().is_relative_to(source)
    ctx = module.open_components(adapter)
    try:
        assert ctx.identity.custody.anchor_dir.is_relative_to(root)
        import asyncio
        import types

        from hermes_state import SessionDB

        user = "synthetic-fetch-user"
        sid = "synthetic-fetch-session"
        cid = "synthetic-fetch-call"
        pair = PairingStore()
        code = pair.generate_code("hmp", user, "Synthetic")
        assert code
        assert pair.approve_code("hmp", code)
        home = root / "home"
        raw_result, image = produce_native_image(home, source)
        db = SessionDB(home / "state.db")
        try:
            db.create_session(sid, "cli")
            db.set_session_title(sid, "Bot Chat")
            db.set_session_hidden(sid, True)
            db.append_message(
                sid,
                "assistant",
                content="",
                tool_calls=[
                    {
                        "id": cid,
                        "type": "function",
                        "function": {"name": "image_generate", "arguments": "{}"},
                    }
                ],
            )
            db.append_message(
                sid,
                "tool",
                content=raw_result,
                tool_name="image_generate",
                tool_call_id=cid,
            )
        finally:
            db.close()

        async def http_check():
            sys.path.insert(0, str(hmp / "server"))
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "synthetic_hmp_kit", str(hmp / "server/tests/unit/hmp_kit.py")
            )
            hmp_kit = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = hmp_kit
            spec.loader.exec_module(hmp_kit)
            from aiohttp.test_utils import TestClient, TestServer

            env = object.__new__(hmp_kit.Env)
            env.store = ctx.store
            env.identity = ctx.identity
            env.clock = types.SimpleNamespace(now=ctx.now())
            import hashlib

            from aiohttp import Fingerprint, TCPConnector

            test_server = TestServer(module.server.build_app(ctx), scheme="https")
            try:
                await test_server.start_server(ssl=ctx.identity.server_ssl_context())
                connector = TCPConnector(
                    ssl=Fingerprint(
                        hashlib.sha256(ctx.identity.certificate_der()).digest()
                    )
                )
                async with TestClient(test_server, connector=connector) as client:
                    dev = hmp_kit.Device()
                    offer = env.offer()
                    response = await client.post(
                        "/hmp/v1/pair/request", json=env.p2_body(dev, offer)
                    )
                    body = await response.json()
                    assert response.status == 202, body
                    dev.pairing_id = body["pairing_id"]
                    dev.ni = hmp_kit.wire.b64u_decode(body["ni"], length=32)
                    env.confirm(dev, user_id=user)
                    response = await client.post(
                        "/hmp/v1/pair/complete", json=env.p4_body(dev)
                    )
                    body = await response.json()
                    assert response.status == 200, body
                    dev.device_id = body["device_id"]
                    dev.access = body["access_token"]
                    adapter.config.extra["owner_device_ids"] = [dev.device_id]
                    ref = ctx.store.mint_or_get_session_ref(
                        user, "default", sid, "synthetic-session-ref", ctx.now()
                    )
                    headers = env.headers(dev)
                    response = await client.get(
                        "/hmp/v1/bots/default/sessions/" + ref + "/messages",
                        headers=headers,
                    )
                    body = await response.json()
                    assert response.status == 200, body
                    descriptors = [
                        m["media"] for m in body["messages"] if m.get("media")
                    ]
                    assert len(descriptors) == 1
                    media = descriptors[0]
                    response = await client.get(
                        "/hmp/v1/bots/default/media/" + media["ref"], headers=headers
                    )
                    data = await response.read()
                    assert response.status == 200
                    assert data == image.read_bytes()
                    config_file = root / "dart-request.json"
                    child = None
                    token_created = False
                    try:
                        fd = os.open(
                            config_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                        )
                        token_created = True
                        with os.fdopen(fd, "w") as output:
                            json.dump(
                                {
                                    "iid": ctx.iid,
                                    "endpoint": str(test_server.make_url("/")).rstrip(
                                        "/"
                                    ),
                                    "path": "/hmp/v1/bots/default/media/"
                                    + media["ref"],
                                    "token": dev.access,
                                    "sha256": hashlib.sha256(data).hexdigest(),
                                },
                                output,
                            )
                        child = await asyncio.create_subprocess_exec(
                            sys.argv[4],
                            "--packages=" + sys.argv[5],
                            sys.argv[6],
                            str(config_file),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        dart_out, dart_err = await asyncio.wait_for(
                            child.communicate(), 20
                        )
                        (root / "dart.stdout").write_bytes(dart_out)
                        (root / "dart.stderr").write_bytes(dart_err)
                        assert child.returncode == 0, (
                            "Dart probe failed; inspect private diagnostics"
                        )
                    finally:
                        try:
                            if child is not None and child.returncode is None:
                                child.terminate()
                                try:
                                    await asyncio.wait_for(child.wait(), 5)
                                except TimeoutError:
                                    child.kill()
                                    await child.wait()
                        finally:
                            if token_created:
                                config_file.unlink()
                    pair.revoke("hmp", user)
                    denied = await client.get(
                        "/hmp/v1/bots/default/media/" + media["ref"], headers=headers
                    )
                    assert denied.status == 403
                    return {
                        "actualBearerPairingHTTP": True,
                        "actualNativeDescriptorHTTP": True,
                        "actualNativeImageHTTP": True,
                        "byteCount": len(data),
                        "revokedStatus": denied.status,
                        "scope": (
                            "Native TLS and Dart SPKI smoke; "
                            "Flutter screen and physical devices unverified"
                        ),
                    }
            finally:
                await test_server.close()

        out = asyncio.run(http_check())
        q = home.parent / "http-result.json"
        q.write_text(json.dumps(out))
        q.chmod(0o600)
        print(json.dumps(out))
    finally:
        try:
            adapter._close_generation(ctx)
        finally:
            ctx.store.close()


if __name__ == "__main__":
    main()
