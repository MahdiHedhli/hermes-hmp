"""HMP cron against the real Hermes API adapter in an isolated home.

Run with a version-matched extracted Hermes build on PYTHONPATH. Without that
fixture this test skips; unit tests still cover the closed default gate.
"""

from __future__ import annotations

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from hmp_plugin import mobile_cron
from hmp_plugin.contract import DirectSendEndpoint

_TEST_KEY = "x" * 24


@pytest.mark.asyncio
async def test_real_hermes_cron_create_paused_and_manage(tmp_path, monkeypatch) -> None:
    api_server = pytest.importorskip("gateway.platforms.api_server")
    from gateway.config import PlatformConfig

    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes-home"))
    adapter = api_server.APIServerAdapter(
        PlatformConfig(enabled=True, extra={"key": _TEST_KEY})
    )
    app = web.Application()
    app.router.add_get("/api/jobs", adapter._handle_list_jobs)
    app.router.add_post("/api/jobs", adapter._handle_create_job)
    app.router.add_patch("/api/jobs/{job_id}", adapter._handle_update_job)
    app.router.add_delete("/api/jobs/{job_id}", adapter._handle_delete_job)
    app.router.add_post("/api/jobs/{job_id}/pause", adapter._handle_pause_job)
    app.router.add_post("/api/jobs/{job_id}/resume", adapter._handle_resume_job)
    server = TestServer(app)
    await server.start_server()
    try:
        endpoint = DirectSendEndpoint(
            host="127.0.0.1", port=server.port,
            api_key=_TEST_KEY, path_prefix="",
        )
        created = await mobile_cron.call(
            endpoint, method="POST", body=mobile_cron.create_body({
                "name": "fixture brief", "schedule": "every 1h", "prompt": "Summarize status",
            }),
        )
        job = created["job"]
        assert job["enabled"] is False
        listed = await mobile_cron.call(endpoint, method="GET")
        assert listed["jobs"] == [job]  # paused jobs must be included
        changed = await mobile_cron.call(
            endpoint, method="PATCH", job=job["id"], body={"name": "new brief"},
        )
        assert changed["job"]["name"] == "new brief"
        resumed = await mobile_cron.call(
            endpoint, method="POST", job=job["id"], action="resume",
        )
        assert resumed["job"]["enabled"] is True
        paused = await mobile_cron.call(
            endpoint, method="POST", job=job["id"], action="pause",
        )
        assert paused["job"]["enabled"] is False
        assert await mobile_cron.call(endpoint, method="DELETE", job=job["id"]) == {
            "deleted": True,
        }
        assert await mobile_cron.call(endpoint, method="GET") == {"jobs": []}
    finally:
        await server.close()
