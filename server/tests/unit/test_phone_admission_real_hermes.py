"""AP-6 against the REAL `BasePlatformAdapter.handle_message` of an installed Hermes build.

A busy session with `busy_text_mode=queue` retains the phone event in its text debounce buffer
but never sets `_gateway_accepted` (it stays False). That event WILL run later, so reporting it as
a definitive refusal (`applied:false`) invites a duplicate user resend. The bridge must report
unknown, AP-6 must store and replay `unknown`, and a replay must never redeliver.

The probe runs in the build's own interpreter against an isolated HERMES_HOME and a synthetic
private instance/profile: no gateway, sockets, model, credentials or live home. Only builds whose
`MessageEvent` has no reject-policy admission ticket are exercised (the no-ticket branch); a build
with tickets is skipped, because there the ticket, not this flag, is authoritative.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

SERVER_DIR = Path(__file__).resolve().parents[2]


def _build_sources() -> list[Path]:
    found: list[Path] = []
    if os.environ.get("HMP_HERMES_SRC"):
        found.append(Path(os.environ["HMP_HERMES_SRC"]))
    builds_dir = os.environ.get("HMP_HERMES_BUILDS_DIR")
    if builds_dir:
        for label in ("stock-base", "experimental"):
            src = Path(builds_dir) / label / "src"
            if src.is_dir() and src not in found:
                found.append(src)
    return found


BUILD_SOURCES = _build_sources()

PROBE = r"""
import asyncio, json, os, sys, tempfile

SRC, SERVER = sys.argv[1], sys.argv[2]
home = tempfile.mkdtemp(prefix="hmp-phone-admission-")
for name in list(os.environ):
    if name.startswith("HERMES_"):
        del os.environ[name]
os.environ["HERMES_HOME"] = home
sys.path[:0] = [SRC, SERVER]

import dataclasses
from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import BasePlatformAdapter
from gateway.platforms.event import MessageEvent
from hmp_plugin import prompts
from hmp_plugin.bridge import HermesReadBridge

if "defer_policy" in {f.name for f in dataclasses.fields(MessageEvent)}:
    print(json.dumps({"skipped": "build has reject-policy admission tickets"}))
    raise SystemExit(0)

USER, PROFILE, CHAT = "u_user", "alpha", "c_chat"
CMID_1 = "01900000-0000-7000-8000-000000000001"
CMID_2 = "01900000-0000-7000-8000-000000000002"


class Adapter(BasePlatformAdapter):
    async def connect(self, *, is_reconnect=False):
        return True

    async def disconnect(self):
        return None

    async def send(self, chat_id, content, reply_to=None, metadata=None):
        raise AssertionError("the probe must never send")

    async def get_chat_info(self, chat_id):
        return {"name": "synthetic", "type": "dm"}


class Directory:
    def chat_id(self, user_id, profile):
        return CHAT

    def operator_label(self, user_id):
        return "synthetic-operator"


class Sqlite:
    def __init__(self):
        self.rows = {}

    def reserve_phone_cmid(self, iid, user_id, profile, cmid, payload_hash, now):
        key = (iid, user_id, profile, cmid)
        if key in self.rows:
            return self.rows[key], False
        self.rows[key] = {"payload_hash": payload_hash, "status": "pending", "result_json": None}
        return self.rows[key], True

    def finalize_phone_cmid(self, iid, user_id, profile, cmid, *, status, result_json, updated_at):
        row = self.rows[(iid, user_id, profile, cmid)]
        row["status"] = status
        row["result_json"] = result_json


async def main():
    adapter = Adapter(PlatformConfig(), Platform.LOCAL)
    adapter.set_owner_profile(PROFILE)

    async def handler(event):
        raise AssertionError("the probe must never run a turn")

    adapter._message_handler = handler
    adapter._busy_text_mode = "queue"
    adapter._busy_text_debounce_seconds = 60.0
    adapter._busy_text_hard_cap_seconds = 120.0

    captured = []
    real_handle = adapter.handle_message

    async def spy(event):
        captured.append(event)
        await real_handle(event)

    adapter.handle_message = spy
    bridge = HermesReadBridge(adapter, Directory())

    # Make the phone's session busy exactly as Hermes does: a guard plus a live owner task.
    probe_event = await asyncio.to_thread(
        bridge._phone_event, user_id=USER, profile=PROFILE, text="warm", message_id="hmp:c_chat:x"
    )
    key = adapter._event_session_key(probe_event)
    adapter._active_sessions[key] = asyncio.Event()
    owner = asyncio.create_task(asyncio.sleep(3600))
    adapter._track_session_task(key, owner)

    store, sqlite, iid = prompts.PromptStore(clock=lambda: 1), Sqlite(), "iid-1"

    async def send(cmid):
        async def deliver():
            return await bridge.deliver_phone_message(
                user_id=USER, profile=PROFILE, text="hello", message_id=f"hmp:{CHAT}:{cmid}"
            )

        return await prompts.handle_phone_send(
            prompts=store, sqlite_store=sqlite, iid=iid, user_id=USER, profile=PROFILE,
            chat_id=CHAT, cmid=cmid, text="hello", now=10, resolver=None,
            session_key=lambda: key, pending_approvals=lambda _k: [], deliver=deliver,
        )

    first = await send(CMID_1)
    debounced = adapter._text_debounce_store().get(key)
    out = {
        "deliveries_after_first": len(captured),
        "flag": repr(getattr(captured[0], "_gateway_accepted", "<missing>")),
        "retained": debounced is not None,
        "retained_message_id": getattr(getattr(debounced, "event", None), "message_id", None),
        "first_status": first.status,
        "first_body": first.body,
        "stored_status": sqlite.rows[(iid, USER, PROFILE, CMID_1)]["status"],
        "observations": len(store.observations(iid, USER, PROFILE)),
    }
    replay = await send(CMID_1)
    out["replay_body"] = replay.body
    out["deliveries_after_replay"] = len(captured)
    out["retained_after_replay"] = len(adapter._text_debounce_store())
    adapter._discard_text_debounce(key)
    owner.cancel()
    print(json.dumps(out))


asyncio.run(main())
"""


@pytest.mark.skipif(
    not BUILD_SOURCES, reason="no Hermes build: set HMP_HERMES_SRC or HMP_HERMES_BUILDS_DIR"
)
@pytest.mark.parametrize("src", BUILD_SOURCES, ids=lambda p: p.parent.name)
def test_busy_queued_phone_event_is_unknown_and_replay_does_not_redeliver(src: Path) -> None:
    python = src / ".venv" / "bin" / "python"
    if not python.is_file():
        pytest.skip("this build has no venv")
    proc = subprocess.run(
        [str(python), "-c", PROBE, str(src), str(SERVER_DIR)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    if "skipped" in out:
        pytest.skip(out["skipped"])
    # Causal premise: real Hermes retained the event while leaving the scheduling flag False.
    assert out["flag"] == "False"
    assert out["retained"] is True
    assert out["retained_message_id"].endswith(":01900000-0000-7000-8000-000000000001")
    # Bridge + AP-6: unknown, never applied:false, nothing recorded as sent.
    assert out["first_status"] == 200
    assert out["first_body"] == {"state": "unknown"}
    assert out["stored_status"] == "unknown"
    assert out["observations"] == 0
    # Replay returns the stored unknown and never reaches handle_message again.
    assert out["replay_body"] == {"state": "unknown"}
    assert out["deliveries_after_first"] == 1
    assert out["deliveries_after_replay"] == 1
    assert out["retained_after_replay"] == 1
