"""F2 direct send: real fixture-gateway integration suite (`HMP_V1.md` §7a, review round 2's
"Missing suite (T-N015/T-N016), now required").

One real Hermes gateway (`tools/fixtures/build_fixture.py`'s offline build, unmodified, plus
`tools/fixtures/direct_send_fixture.py`'s additive api_server/model/lease setup), one real HMP
listener, real TLS, real pairing, a REAL `api_server` loopback call -- to a deterministic,
stdlib-only fake model (`tests/fakes/fake_llm_provider.py`, loaded straight from the target Hermes
build, never a real provider, never a real network call beyond 127.0.0.1). One fixture gateway
runs at a time (host load, matching `test_reads_fixture.py`'s own convention); every test stops it.

Fixture instance A / profile `f1-alpha` already has a canonical "Bot Chat" seeded by
`fixtures/f1/instances.yaml` itself (`other_sessions`, title "Bot Chat", hidden, two rows) --
exactly DS-4(2)'s target. Every `hermes profile create`d profile in this fixture (`f1-alpha`,
`f1-empty`, ...) is a NAMED profile from `bridge.py`'s own point of view -- a real, multiplexed
Hermes gateway ALWAYS also serves its own built-in, unconfigured `"default"` profile FIRST
(empirically confirmed against a live `stock-base` gateway's `/hmp/v1/bots` roster), so NONE of
these fixture profiles is ever `served[0]`. Each therefore gets its OWN scoped `API_SERVER_KEY`
via `.env` (`direct_send_fixture.write_named_profile_keys`), never `extra.key` -- the DEFAULT-
profile `extra.key` precedence itself has full, dedicated unit coverage instead
(`tests/unit/test_bridge.py::test_direct_send_endpoint_default_profile_prefers_extras_inline_key`).
Profile `f1-empty` (same instance, authorized for the same user, no `other_sessions` at all) has
no Bot Chat at all -- the `no_bot_chat` case.

Residuals, stated plainly (not silently narrowed):

- A true concurrent-second-writer interleave (a genuinely racing direct `api_server` call landing
  WHILE our own send's post-hoc check is running) is not exercised here: reliably synthesizing
  that race against a live gateway needs either a nested live `api_server` call issued from inside
  the fake model's own response callback (risking a second, recursive agent turn on the same
  session) or a direct `SessionDB` write while the gateway is live (not a supported fixture-tool
  operation today, `fixture-format.md` rule 3's "offline" discipline). The true-NEGATIVE case (an
  ordinary send, no other writer) is exercised by every happy-path test below, and the identity
  check's own true/false-positive logic has full unit coverage (`tests/unit/test_direct_send.py`).
- A compression rotation mid-turn is not re-exercised here either: BLOCKER #2's lease-lineage fix
  and the DS-7a `effective_session_id` handling both have dedicated unit coverage
  (`tests/unit/test_bridge.py::test_resolve_bot_chat_resolves_the_live_tip_and_full_chain`,
  `tests/unit/test_direct_send.py`'s interleave tests); triggering a REAL compaction reliably
  inside a short-lived fixture turn was judged not worth the added fixture complexity this round.
"""

from __future__ import annotations

import http.client
import json
import os
import ssl
import sys
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = REPO_ROOT / "tools" / "fixtures"
if str(FIXTURES_DIR) not in sys.path:
    sys.path.insert(0, str(FIXTURES_DIR))

import _fixture_common as fc  # noqa: E402
import direct_send_fixture as dsf  # noqa: E402

_DEFAULT_BUILDS = ("stock-base", "experimental", "owner-local")
BUILDS_DIR_ENV = os.environ.get("HMP_HERMES_BUILDS_DIR", "")
# Opt-in: one extra, uniquely named candidate build (never an alias of a default label).
BUILDS = _DEFAULT_BUILDS + dsf.candidate_build_labels(
    os.environ.get(dsf.CANDIDATE_LABEL_ENV, ""), BUILDS_DIR_ENV, _DEFAULT_BUILDS
)

DEFAULT_PROFILE = "f1-alpha"
NO_BOT_CHAT_PROFILE = "f1-empty"
BOT_CHAT_SESSION_ID = "A-f1-alpha-bot-chat-1"  # fixtures/f1/instances.yaml's own id-building rule

pytestmark = [
    pytest.mark.skipif(
        not dsf.BUILD_FIXTURE.is_file(),
        reason="needs T060 tools/fixtures/build_fixture.py",
    ),
    pytest.mark.skipif(
        not BUILDS_DIR_ENV, reason="needs HMP_HERMES_BUILDS_DIR with extracted builds (T004)"
    ),
]


# --------------------------------------------------------------------------------------------------
# A tiny HTTPS client (mirrors test_reads_fixture.py's `Served.get`, extended with POST -- the pin
# itself is not under test here, T041 covers that).
# --------------------------------------------------------------------------------------------------


class Client:
    def __init__(self, port: int, iid: str, access_token: str) -> None:
        self.port = port
        self.iid = iid
        self.access_token = access_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "HMP-Instance": self.iid,
            "Content-Type": "application/json",
        }

    def _ctx(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def get(self, path: str) -> tuple[int, Any]:
        conn = http.client.HTTPSConnection("127.0.0.1", self.port, context=self._ctx(), timeout=30)
        try:
            conn.request("GET", path, headers=self._headers())
            resp = conn.getresponse()
            return resp.status, json.loads(resp.read() or b"null")
        finally:
            conn.close()

    def post(self, path: str, body: dict[str, Any]) -> tuple[int, Any]:
        conn = http.client.HTTPSConnection("127.0.0.1", self.port, context=self._ctx(), timeout=30)
        try:
            conn.request("POST", path, body=json.dumps(body).encode(), headers=self._headers())
            resp = conn.getresponse()
            return resp.status, json.loads(resp.read() or b"null")
        finally:
            conn.close()


def send(client: Client, profile: str, *, cmid: str, expected_head: int | None, text: str):
    body: dict[str, Any] = {"client_message_id": cmid, "expected_head": expected_head, "text": text}
    return client.post(f"/hmp/v1/bots/{profile}/chat/messages", body)


def lookup(client: Client, profile: str, cmid: str):
    return client.get(f"/hmp/v1/bots/{profile}/chat/messages/by-client-id/{cmid}")


def bot_chat_ref(client: Client, profile: str) -> str:
    status, body = client.get(f"/hmp/v1/bots/{profile}/sessions?limit=100")
    assert status == 200, body
    by_title = {item["title"]: item for item in body["sessions"]}
    assert "Bot Chat" in by_title, body
    return str(by_title["Bot Chat"]["session_ref"])


def bot_chat_head(client: Client, profile: str, ref: str) -> int:
    status, body = client.get(f"/hmp/v1/bots/{profile}/sessions/{ref}/messages")
    assert status == 200, body
    return int(body["head_message_id"])


def wait_for(predicate, *, timeout: float, interval: float = 0.25):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval)
    return last


# --------------------------------------------------------------------------------------------------
# Fixture: one served instance-A gateway, api_server + a deterministic fake model, per build.
# --------------------------------------------------------------------------------------------------


class DirectSendFixture:
    def __init__(
        self,
        build: fc.BuildInfo,
        paths: fc.InstancePaths,
        *,
        hmp_port: int,
        api_server_port: int,
        api_key: str,
        gateway_proc,
        fake_model,
        fake_model_module,
        client: Client,
        no_bot_chat_key: str,
        user_id: str,
    ) -> None:
        self.build = build
        self.paths = paths
        self.hmp_port = hmp_port
        self.api_server_port = api_server_port
        self.api_key = api_key
        self.gateway_proc = gateway_proc
        self.fake_model = fake_model
        self.fake_model_module = fake_model_module
        self.client = client
        self.no_bot_chat_key = no_bot_chat_key
        self.user_id = user_id
        self._lease_holders: list[Any] = []

    def acquire_lease(self, profile: str, session_id: str) -> None:
        """A synthetic lease that stays live until this fixture tears down (`stop`) -- see
        `direct_send_fixture.start_lease_holder`'s own docstring for why the holder process must
        keep running rather than exit after acquiring."""
        self._lease_holders.append(dsf.start_lease_holder(
            self.build, self.paths, profile=profile, session_id=session_id
        ))

    def stop(self) -> None:
        for proc in self._lease_holders:
            dsf.stop_lease_holder(proc)
        self._lease_holders.clear()

    def _rewrite_config(
        self, *, direct_send_enabled: bool = True, api_server_host: str = "127.0.0.1",
        cron_enabled: bool = False, model_enabled: bool = False,
    ) -> None:
        dsf.write_direct_send_config(
            self.paths, (DEFAULT_PROFILE, NO_BOT_CHAT_PROFILE, "f1-pending", "f1-roles"),
            hmp_port=self.hmp_port, api_server_port=self.api_server_port, api_key=self.api_key,
            model_base_url=self.fake_model.base_url,
            named_profile_keys={NO_BOT_CHAT_PROFILE: self.no_bot_chat_key},
            direct_send_enabled=direct_send_enabled, api_server_host=api_server_host,
            cron_enabled=cron_enabled, model_enabled=model_enabled,
        )

    def set_api_server_host(self, host: str) -> None:
        """Flips `platforms.api_server.extra.host` (on EVERY profile's own `config.yaml` -- see
        `write_direct_send_config`'s own docstring on why the per-profile copy is the one that
        actually matters here) -- `bridge.direct_send_endpoint` calls `load_gateway_config()`
        itself, live, per call, inside `profile_runtime_scope`, never through Hermes's own cached
        `adapter.config` object -- so this takes effect on the very next request, no restart
        needed (unlike `set_direct_send_flag`, below)."""
        self._rewrite_config(api_server_host=host)

    def set_direct_send_flag(self, enabled: bool) -> None:
        """Round 2 should-fix: `adapter.py`'s closure re-reads `adapter.config.extra` fresh on
        EVERY request rather than a value cached once at connect time (round 1's bug) -- but
        Hermes's own top-level `platforms:` block is only loaded from `config.yaml` when that
        platform (re)connects, not hot-reloaded off a live file-system watch the way per-profile
        config is. Making the new value visible to a running gateway therefore still needs this
        fixture to restart it (`restart_gateway`) -- this is a property of the HOST Hermes build,
        not a limitation this round's fix leaves in place: once `adapter.config` IS updated by
        whatever means, the very next request reflects it, with no separate HMP-side code path to
        also update."""
        self._rewrite_config(direct_send_enabled=enabled)
        self.restart_gateway()

    def base_gate_state(self) -> str:
        """The UN-gated `write_gate.state` (`GET /hmp/v1/ready`) -- `"open"` on a build whose own
        capability map genuinely satisfies GU-4 (e.g. `experimental`; see this round's own
        "additional finding" in `specs/002-send-messages/DESIGN.md`), `"closed"` otherwise (e.g.
        `stock-base`). DS-2(b): once this is genuinely `"open"`, neither the owner-dogfood flag
        nor the loopback endpoint's own health can close the gate at all -- both
        `test_flag_off_is_503` and `test_non_loopback_bind_configured_closes_the_gate` branch on
        this rather than assume every build is gated."""
        status, body = self.client.get("/hmp/v1/ready")
        assert status == 200, body
        return str(body["write_gate"]["state"])

    def restart_gateway(self) -> None:
        dsf.stop_gateway(self.gateway_proc)
        log_path = self.paths.out_dir / f"gateway-restart-{int(time.time())}.log"
        self.gateway_proc = dsf.start_gateway(self.build, self.paths, log_path=log_path)
        if not dsf.wait_for_port(self.hmp_port, timeout=45.0):
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
            raise RuntimeError(f"HMP listener did not come back up after restart.\n{tail}")
        # The TLS listener accepting connections does not mean Hermes's own profile-reconcile
        # scan has finished re-populating `served_profile_names()` yet -- poll the roster until
        # the default profile this suite targets is actually served again, so a request sent
        # right after a restart never spuriously sees `not_routed`/`not_served`.
        found = wait_for(
            lambda: any(
                b["profile"] == DEFAULT_PROFILE
                for b in self.client.get("/hmp/v1/bots")[1].get("bots", [])
            ),
            timeout=30.0,
        )
        if not found:
            raise RuntimeError(f"{DEFAULT_PROFILE!r} never reappeared in the roster after restart")


@pytest.fixture(params=BUILDS)
def gateway(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[DirectSendFixture]:
    label = request.param
    if label not in ("stock-base",) and not (
        Path(BUILDS_DIR_ENV) / label / "src"
    ).is_dir():
        pytest.skip(f"build {label!r} not extracted on this host")
    build = fc.resolve_build(BUILDS_DIR_ENV, label)
    out = tmp_path / "fixture"
    info = dsf.build_offline(label, out, builds_dir=BUILDS_DIR_ENV, instances="A")
    paths = fc.instance_paths(out, "A")
    profile_names = tuple(p["name"] for p in info["instances"][0]["profiles"])
    assert profile_names[0] == DEFAULT_PROFILE, profile_names

    hmp_port = fc.find_free_port()
    api_server_port = fc.find_free_port()
    api_key = dsf.synthetic_api_key()
    no_bot_chat_key = dsf.synthetic_api_key()

    fake_model_module = dsf.load_fake_llm_provider(build)
    fake_model = fake_model_module.FakeLLMServer(default_text="fixture default reply")
    fake_model.start()
    try:
        dsf.write_direct_send_config(
            paths, profile_names,
            hmp_port=hmp_port, api_server_port=api_server_port, api_key=api_key,
            model_base_url=fake_model.base_url,
            named_profile_keys={NO_BOT_CHAT_PROFILE: no_bot_chat_key},
        )
        log_path = out / "gateway.log"
        proc = dsf.start_gateway(build, paths, log_path=log_path)
        direct_send_fixture: DirectSendFixture | None = None
        try:
            if not dsf.wait_for_port(hmp_port, timeout=45.0):
                tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                raise RuntimeError(f"HMP listener did not come up.\nLog tail:\n{tail}")
            authorized_user_id = next(
                p["user_id"] for p in info["instances"][0]["profiles"] if p.get("user_id")
            )
            ref = dsf.pair_reference_device(
                build, paths, port=hmp_port, user_id=authorized_user_id,
                label="direct-send-fixture",
            )
            client = Client(hmp_port, ref["iid"], ref["device"]["access_token"])
            direct_send_fixture = DirectSendFixture(
                build, paths, hmp_port=hmp_port, api_server_port=api_server_port,
                api_key=api_key, gateway_proc=proc, fake_model=fake_model,
                fake_model_module=fake_model_module, client=client,
                no_bot_chat_key=no_bot_chat_key, user_id=authorized_user_id,
            )
            try:
                yield direct_send_fixture
            finally:
                direct_send_fixture.stop()
        finally:
            # `direct_send_fixture.gateway_proc` -- NOT the local `proc` captured above -- is the
            # live one: `restart_gateway` (`set_direct_send_flag`/any future caller) replaces it in
            # place after stopping the old one, and a test that restarts an odd number of times
            # would otherwise leak the LATEST process if this teardown stopped the now-stale
            # original reference instead.
            # Setup can fail before the fixture exists (e.g. pairing): stop the original proc.
            dsf.stop_gateway(
                direct_send_fixture.gateway_proc if direct_send_fixture is not None else proc
            )
    finally:
        fake_model.stop()


# --------------------------------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------------------------------


def test_send_reply_visible_via_ses2(gateway: DirectSendFixture) -> None:
    client = gateway.client
    ref = bot_chat_ref(client, DEFAULT_PROFILE)
    head = bot_chat_head(client, DEFAULT_PROFILE, ref)
    cmid = str(uuid.uuid4())

    status, body = send(client, DEFAULT_PROFILE, cmid=cmid, expected_head=head, text="hello there")
    assert status == 200, body
    assert body["state"] == "accepted"
    assert body["reply"]["content"] == "fixture default reply"
    assert body.get("interleave_detected") is not True

    status, body = client.get(f"/hmp/v1/bots/{DEFAULT_PROFILE}/sessions/{ref}/messages")
    assert status == 200, body
    roles = [m["role"] for m in body["messages"]]
    assert roles[-2:] == ["user", "assistant"]
    assert body["messages"][-2]["text"] == "hello there"
    assert body["messages"][-1]["text"] == "fixture default reply"


def test_duplicate_cmid_never_runs_a_second_turn(gateway: DirectSendFixture) -> None:
    client = gateway.client
    ref = bot_chat_ref(client, DEFAULT_PROFILE)
    head = bot_chat_head(client, DEFAULT_PROFILE, ref)
    cmid = str(uuid.uuid4())

    status1, body1 = send(client, DEFAULT_PROFILE, cmid=cmid, expected_head=head, text="only once")
    assert status1 == 200, body1
    status2, body2 = send(client, DEFAULT_PROFILE, cmid=cmid, expected_head=head, text="only once")
    assert status2 == 200, body2
    assert body2 == body1  # exact idempotent replay, DS-3

    status, body = client.get(f"/hmp/v1/bots/{DEFAULT_PROFILE}/sessions/{ref}/messages")
    assert status == 200, body
    assistant_rows = [m for m in body["messages"] if m["role"] == "assistant"]
    user_rows = [m for m in body["messages"] if m["text"] == "only once"]
    assert len(user_rows) == 1  # the retry never reached Hermes a second time
    assert len([m for m in assistant_rows if m["text"] == "fixture default reply"]) == 1


def test_stale_head_refused_before_any_loopback_call(gateway: DirectSendFixture) -> None:
    client = gateway.client
    ref = bot_chat_ref(client, DEFAULT_PROFILE)
    head = bot_chat_head(client, DEFAULT_PROFILE, ref)
    cmid = str(uuid.uuid4())

    status, body = send(client, DEFAULT_PROFILE, cmid=cmid, expected_head=head - 1, text="stale")
    assert status == 409, body
    assert body["error"]["code"] == "stale_head"

    # Never handed to Hermes: no new row for this text.
    status, body = client.get(f"/hmp/v1/bots/{DEFAULT_PROFILE}/sessions/{ref}/messages")
    assert status == 200, body
    assert not any(m["text"] == "stale" for m in body["messages"])


def test_no_bot_chat_on_a_profile_with_none(gateway: DirectSendFixture) -> None:
    client = gateway.client
    cmid = str(uuid.uuid4())
    status, body = send(
        client, NO_BOT_CHAT_PROFILE, cmid=cmid, expected_head=0, text="nobody home"
    )
    assert status == 409, body
    assert body["error"]["code"] == "no_bot_chat"


def test_session_busy_via_synthetic_lease(gateway: DirectSendFixture) -> None:
    client = gateway.client
    ref = bot_chat_ref(client, DEFAULT_PROFILE)
    head = bot_chat_head(client, DEFAULT_PROFILE, ref)
    # A synthetic lease on the Bot Chat's OWN session id (the review's baseline busy case; the
    # pre-compression-ancestor variant is unit-tested directly against `bridge.resolve_bot_chat`'s
    # now-full lineage, `tests/unit/test_bridge.py`).
    gateway.acquire_lease(DEFAULT_PROFILE, BOT_CHAT_SESSION_ID)
    cmid = str(uuid.uuid4())
    status, body = send(client, DEFAULT_PROFILE, cmid=cmid, expected_head=head, text="busy now")
    assert status == 409, body
    assert body["error"]["code"] == "session_busy"

    # BLOCKER #1: a pre-call guard failure releases the reservation -- the SAME cmid can be
    # retried later (once the busy state clears) without an idempotency_conflict.
    status, body = lookup(client, DEFAULT_PROFILE, cmid)
    assert status == 200, body
    assert body["state"] == "unknown"  # released, never reserved to begin with


def test_flag_off_is_503(gateway: DirectSendFixture) -> None:
    """Round 2 should-fix: the flag is re-read per request (`adapter.py`'s closure over the LIVE
    `adapter.config.extra`, not a one-time snapshot). Flipping it off on this same running
    gateway, no restart, must close the gate on the very next call -- and flipping it back on
    must re-open it just as fast, so the rest of this suite's fixture (which relies on the flag
    being on) is left exactly as it was.

    A full-guarantee build still requires this owner switch; no build may bypass it."""
    client = gateway.client
    gateway.set_direct_send_flag(False)
    try:
        ref = bot_chat_ref(client, DEFAULT_PROFILE)
        head = bot_chat_head(client, DEFAULT_PROFILE, ref)
        status, body = send(
            client, DEFAULT_PROFILE, cmid=str(uuid.uuid4()), expected_head=head,
            text="closed while off",
        )
        assert status == 503, body
        assert body["error"]["code"] == "write_gate_closed"
    finally:
        gateway.set_direct_send_flag(True)

    ref = bot_chat_ref(client, DEFAULT_PROFILE)
    head = bot_chat_head(client, DEFAULT_PROFILE, ref)
    status, body = send(
        client, DEFAULT_PROFILE, cmid=str(uuid.uuid4()), expected_head=head, text="open again"
    )
    assert status == 200, body  # re-enabling the flag takes effect immediately too


def test_non_loopback_bind_configured_closes_the_gate(gateway: DirectSendFixture) -> None:
    """Round 2 BLOCKER #3: a configured non-loopback (or unverifiable) bind must fail closed, on
    a REAL config read against a live gateway -- not only the unit-level fake.

    The route closes on either a full- or reduced-guarantee build when its only
    implemented delivery endpoint is not loopback-bound."""
    client = gateway.client
    gateway.set_api_server_host("0.0.0.0")  # noqa: S104 -- deliberately refused, never connected
    try:
        status, body = send(
            client, DEFAULT_PROFILE, cmid=str(uuid.uuid4()), expected_head=0, text="never sent"
        )
        assert status == 503, body
        assert body["error"]["code"] == "write_gate_closed"
    finally:
        gateway.set_api_server_host("127.0.0.1")  # restore for any later test in this session


def test_timeout_then_lookup_reaches_accepted_without_a_resend(gateway: DirectSendFixture) -> None:
    """Round 2 BLOCKER #1: a call that outlives `ADMISSION_WAIT_S` (5s) gets `202 submitted`
    immediately, and the SAME background task finalizes the row on its own -- polled via DS-8,
    never resent."""
    client = gateway.client
    ref = bot_chat_ref(client, DEFAULT_PROFILE)
    head = bot_chat_head(client, DEFAULT_PROFILE, ref)
    text_response = gateway.fake_model_module.Text(
        "slow reply", delay_per_chunk=1.0, chunk_chars=1
    )
    gateway.fake_model.push(text_response)
    cmid = str(uuid.uuid4())

    started = time.monotonic()
    status, body = send(client, DEFAULT_PROFILE, cmid=cmid, expected_head=head, text="be slow")
    elapsed = time.monotonic() - started
    assert status == 202, body
    assert body["state"] == "submitted"
    assert elapsed < 20  # bounded by ADMISSION_WAIT_S, not by the model's own delay

    settled = wait_for(
        lambda: lookup(client, DEFAULT_PROFILE, cmid)[1].get("state") == "accepted",
        timeout=60.0,
    )
    assert settled, "the background task never finalized the row"
    status, body = lookup(client, DEFAULT_PROFILE, cmid)
    assert status == 200 and body["state"] == "accepted", body

    # A retry under the SAME cmid, issued only after settling: idempotent replay, never a second
    # turn (the response is exactly the finalized outcome, no network call).
    status, body = send(client, DEFAULT_PROFILE, cmid=cmid, expected_head=head, text="be slow")
    assert status == 200 and body["state"] == "accepted", body


def test_host_grant_is_per_device_on_real_gateway(gateway: DirectSendFixture) -> None:
    """Pairing one privileged phone must not elevate a sibling of the same user."""
    gateway._rewrite_config(cron_enabled=True, model_enabled=True)
    gateway.restart_gateway()
    jobs_path = f"/hmp/v1/bots/{DEFAULT_PROFILE}/jobs"
    model_path = f"/hmp/v1/bots/{DEFAULT_PROFILE}/model/default"

    # The first reference client explicitly declined controls at the host
    # prompt. Both routes hide themselves from it even with feature flags on.
    for path in (jobs_path, model_path):
        status, body = gateway.client.get(path)
        assert status == 404, body

    granted_ref = dsf.pair_reference_device(
        gateway.build, gateway.paths, port=gateway.hmp_port,
        user_id=gateway.user_id, label="granted-fixture-phone",
        grant_owner_controls=True,
    )
    granted = Client(
        gateway.hmp_port, granted_ref["iid"], granted_ref["device"]["access_token"]
    )
    status, body = granted.get(jobs_path)
    assert status == 200 and body["jobs"] == [], body
    status, body = granted.post(jobs_path, {
        "name": "owner-grant fixture", "schedule": "every 1h",
        "prompt": "Summarize fixture status",
    })
    assert status == 200 and body["job"]["enabled"] is False, body
    if gateway.build.label == "stock-base":
        status, body = granted.get(model_path)
        assert status == 200 and "model" in body, body
    else:
        # Experimental Hermes retains the qualified cron bridge fingerprint,
        # but its model bridge fingerprint is not in the separate allowlist.
        # A device grant must not bypass that build gate.
        status, body = granted.get(model_path)
        assert status == 503 and body["error"]["code"] == "model_unavailable", body
    for path in (jobs_path, model_path):
        status, body = gateway.client.get(path)
        assert status == 404, body
