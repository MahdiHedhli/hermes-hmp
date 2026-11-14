"""Named-profile mobile jobs through the real HMP gates on a real fixture gateway.

Opt-in only: set `HMP_JOBS_FIXTURE_BUILD=<label>` (an extracted build under
`HMP_HERMES_BUILDS_DIR`) and run this file alone. Without it the module skips, so a default
integration run never creates a job.

It reuses `test_direct_send_fixture.py`'s gateway (isolated `HERMES_HOME`, real HMP listener, real
pairing, fake model, per-profile scoped `API_SERVER_KEY`). Everything is explicit test wiring:

- the cron flag is written into the scratch config; production default stays off;
- the build gate is admitted ONLY in the fixture's scratch plugin copy
  (`direct_send_fixture.set_jobs_test_admission`); no production manifest entry is read or written;
- the device owner-controls grant is the real host decision, answered in the real pairing CLI.

What this proves, per build: the request order (controls grant, bot authorization, flag, build
gate, profile endpoint and its own key), that a job lives only in its own profile's native store
(A-B-A), the native per-profile key boundary, and that a corrupt store never yields a success that
did not persist. A job is only ever created paused and is never resumed, so the native scheduler is
not exercised; no job name, prompt or key is printed.

Native callees beyond the 11 files `mobile_cron_supported_builds.json` fingerprints (for example
`cron/scheduler_delivery.py`, `cron/scheduler_prompt.py`) are not attested here: this suite never
runs a scheduled job, so Bot Chat delivery and `context_from` continuity at run time stay
unqualified by it.
"""

from __future__ import annotations

import http.client
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from .test_direct_send_fixture import (  # noqa: F401  (`gateway` is the reused fixture)
    DEFAULT_PROFILE,
    NO_BOT_CHAT_PROFILE,
    Client,
    DirectSendFixture,
    dsf,
    gateway,
)

_BUILD = os.environ.get("HMP_JOBS_FIXTURE_BUILD", "")
# A candidate build with an auto-repair-on-corrupt-store history may legitimately report a repaired
# success; set this where the build is known to refuse instead (`RuntimeError` on an unreadable
# store) so the weaker "never a false success" check tightens to "must refuse".
_CORRUPT_MUST_FAIL = os.environ.get("HMP_JOBS_CORRUPT_MUST_FAIL") == "1"

pytestmark = [
    pytest.mark.skipif(not _BUILD, reason="needs HMP_JOBS_FIXTURE_BUILD (opt-in; creates jobs)"),
    pytest.mark.parametrize("gateway", [_BUILD], indirect=True),
]

PENDING_PROFILE = "f1-pending"  # not authorized for the fixture user (`authorize_for: []`)


def call(client: Client, method: str, path: str, body: dict[str, Any] | None = None):
    conn = http.client.HTTPSConnection("127.0.0.1", client.port, context=client._ctx(), timeout=30)
    try:
        payload = json.dumps(body).encode() if body is not None else None
        conn.request(method, path, body=payload, headers=client._headers())
        resp = conn.getresponse()
        return resp.status, json.loads(resp.read() or b"null")
    finally:
        conn.close()


def code(body: Any) -> str | None:
    """The error code only; never the body, which could carry job fields."""
    error = body.get("error") if isinstance(body, dict) else None
    return error.get("code") if isinstance(error, dict) else None


def jobs_path(profile: str, job_id: str | None = None) -> str:
    base = f"/hmp/v1/bots/{profile}/jobs"
    return f"{base}/{job_id}" if job_id else base


def list_ids(client: Client, profile: str) -> list[str]:
    status, body = call(client, "GET", jobs_path(profile))
    assert status == 200, f"list {profile}: {status} {code(body)}"
    return sorted(job["id"] for job in body["jobs"])


def create(client: Client, profile: str, name: str) -> str:
    status, body = call(client, "POST", jobs_path(profile), {
        "name": name, "schedule": "every 1h", "prompt": "fixture status check",
    })
    assert status == 200, f"create {profile}: {status} {code(body)}"
    assert body["job"]["enabled"] is False  # a mobile create is always paused
    return str(body["job"]["id"])


def native_status(port: int, profile: str, key: str) -> int:
    """The profile's own loopback API with an explicit key; status only."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request("GET", f"/p/{profile}/api/jobs", headers={"Authorization": f"Bearer {key}"})
        return conn.getresponse().status
    finally:
        conn.close()


def store_files(gw: DirectSendFixture, profile: str) -> list[Path]:
    return sorted((gw.paths.home / "profiles" / profile).rglob("jobs.json"))


@dataclass
class Jobs:
    gateway: DirectSendFixture
    client: Client  # paired with a real host owner-controls GRANT

    def admit(self, admitted: bool) -> None:
        dsf.set_jobs_test_admission(self.gateway.build, self.gateway.paths, admitted=admitted)


@pytest.fixture
def jobs(gateway: DirectSendFixture) -> Iterator[Jobs]:  # noqa: F811
    # Closed first: flag on, controls granted, but no build admission.
    dsf.set_jobs_test_admission(gateway.build, gateway.paths, admitted=False)
    gateway._rewrite_config(cron_enabled=True)
    gateway.restart_gateway()
    ref = dsf.pair_reference_device(
        gateway.build, gateway.paths, port=gateway.hmp_port, user_id=gateway.user_id,
        label="jobs-fixture-phone", grant_owner_controls=True,
    )
    yield Jobs(gateway, Client(gateway.hmp_port, ref["iid"], ref["device"]["access_token"]))


def test_each_gate_closes_and_nothing_is_default_open(jobs: Jobs) -> None:
    gw, path = jobs.gateway, jobs_path(DEFAULT_PROFILE)

    # Flag on + controls granted, but the build is not admitted: closed.
    status, body = call(jobs.client, "GET", path)
    assert (status, code(body)) == (503, "cron_unavailable")

    jobs.admit(True)
    assert list_ids(jobs.client, DEFAULT_PROFILE) == []

    # A device without the host controls grant sees a missing route, even with flag + admission.
    status, body = call(gw.client, "GET", path)
    assert (status, code(body)) == (404, "not_found")
    # A write is refused the same way and creates nothing.
    status, body = call(gw.client, "POST", path, {
        "name": "never created", "schedule": "every 1h", "prompt": "never created",
    })
    assert (status, code(body)) == (404, "not_found")
    assert list_ids(jobs.client, DEFAULT_PROFILE) == []

    # Controls do not stand in for bot authorization.
    status, body = call(jobs.client, "GET", jobs_path(PENDING_PROFILE))
    assert (status, code(body)) == (403, "forbidden")

    # The flag is a separate gate; admission and the grant do not substitute for it.
    gw._rewrite_config(cron_enabled=False)
    gw.restart_gateway()
    status, body = call(jobs.client, "GET", path)
    assert (status, code(body)) == (503, "cron_unavailable")


def test_jobs_stay_in_their_own_profile_a_b_a(jobs: Jobs) -> None:
    gw, client = jobs.gateway, jobs.client
    a, b = DEFAULT_PROFILE, NO_BOT_CHAT_PROFILE
    jobs.admit(True)
    assert list_ids(client, a) == [] and list_ids(client, b) == []

    a_id = create(client, a, "jobs-fixture-a")  # in-process writer, paused
    assert list_ids(client, a) == [a_id]  # native API, same store
    assert list_ids(client, b) == []
    a_stores = store_files(gw, a)
    assert len(a_stores) == 1, "expected one native store under profile A"
    for other in gw.paths.home.rglob("jobs.json"):
        if other not in a_stores:
            assert a_id not in other.read_text(encoding="utf-8"), "job leaked to another store"

    b_id = create(client, b, "jobs-fixture-b")
    assert list_ids(client, a) == [a_id]
    assert list_ids(client, b) == [b_id]

    # Another profile's job id is not reachable through this profile's route.
    status, body = call(client, "PATCH", jobs_path(a, b_id), {"name": "renamed"})
    assert (status, code(body)) == (404, "not_found")
    status, body = call(client, "DELETE", jobs_path(a, b_id))
    assert (status, code(body)) == (404, "not_found")
    assert list_ids(client, b) == [b_id]

    # In-process edit: changes only HMP's fields and never resumes the job.
    status, body = call(client, "PATCH", jobs_path(a, a_id), {
        "name": "jobs-fixture-a2", "deliver": "bot-chat", "continuity": True, "repeat": 3,
    })
    assert status == 200, f"edit: {status} {code(body)}"
    job = body["job"]
    assert (job["enabled"], job["deliver"], job["continuity"], job["repeat"]) == (
        False, "bot-chat", True, 3,
    )

    # A -> B -> A: A's job survived B's activity, then goes away on A only.
    assert list_ids(client, a) == [a_id]
    status, body = call(client, "DELETE", jobs_path(a, a_id))
    assert (status, body) == (200, {"deleted": True})
    assert list_ids(client, a) == []
    assert list_ids(client, b) == [b_id]
    status, body = call(client, "DELETE", jobs_path(b, b_id))
    assert (status, body) == (200, {"deleted": True})


def test_profile_key_is_never_borrowed_across_profiles(jobs: Jobs) -> None:
    gw, client = jobs.gateway, jobs.client
    a, b = DEFAULT_PROFILE, NO_BOT_CHAT_PROFILE
    jobs.admit(True)

    # Native boundary: each profile's own key opens its own prefix; the other's key does not.
    assert native_status(gw.api_server_port, a, gw.api_key) == 200
    assert native_status(gw.api_server_port, b, gw.no_bot_chat_key) == 200
    assert native_status(gw.api_server_port, b, gw.api_key) in (401, 403)
    assert native_status(gw.api_server_port, a, gw.no_bot_chat_key) in (401, 403)

    # HMP boundary: B without its own scoped key is unavailable, not served with A's or the
    # instance-level key, for list, create (needs a usable endpoint) and edit alike.
    b_id = create(client, b, "jobs-fixture-b")  # B has a real store before its key goes away
    (b_store,) = store_files(gw, b)
    b_before = b_store.read_bytes()
    dsf.remove_named_profile_key(gw.paths, b)
    status, body = call(client, "GET", jobs_path(b))
    assert (status, code(body)) == (503, "cron_unavailable")
    status, body = call(client, "POST", jobs_path(b), {
        "name": "never created", "schedule": "every 1h", "prompt": "never created",
    })
    assert (status, code(body)) == (503, "cron_unavailable")
    assert store_files(gw, b) == [b_store]  # no new store appeared
    assert b_store.read_bytes() == b_before  # and B's own store is byte-for-byte unchanged

    # A is unaffected.
    assert list_ids(client, a) == []

    # Restoring B's own key reopens B, with B's own job intact.
    dsf.write_named_profile_keys(gw.paths, {b: gw.no_bot_chat_key})
    assert list_ids(client, b) == [b_id]
    status, body = call(client, "DELETE", jobs_path(b, b_id))
    assert (status, body) == (200, {"deleted": True})


def test_corrupt_store_never_reports_a_success_that_did_not_persist(jobs: Jobs) -> None:
    gw, client = jobs.gateway, jobs.client
    a = DEFAULT_PROFILE
    jobs.admit(True)
    kept_id = create(client, a, "jobs-fixture-kept")
    (store,) = store_files(gw, a)
    original = store.read_bytes()
    corrupt = b"{ not json"
    try:
        store.write_bytes(corrupt)
        status, body = call(client, "POST", jobs_path(a), {
            "name": "jobs-fixture-new", "schedule": "every 1h", "prompt": "fixture status check",
        })
        if status == 200:
            assert not _CORRUPT_MUST_FAIL, "build was expected to refuse a corrupt store"
            # A success must be durable: the new job is visible on a fresh read.
            assert body["job"]["id"] in list_ids(client, a)
        else:
            assert (status, code(body)) == (503, "cron_unavailable")
            assert store.read_bytes() == corrupt, "a refused create must not touch the store"
    finally:
        store.write_bytes(original)
    assert list_ids(client, a) == [kept_id]
    status, body = call(client, "DELETE", jobs_path(a, kept_id))
    assert (status, body) == (200, {"deleted": True})
