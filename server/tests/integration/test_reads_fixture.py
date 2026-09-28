"""T030 acceptance, fixture-mutation integration (needs T060 build_fixture.py and T062 mutate.py).

Each mutation from `fixtures/f1/instances.yaml` must yield the expected history outcome on a real
gateway, on both builds:
- `append` gives the new rows after the cursor;
- `rewrite` (in-place compaction) gives `history_rewritten`;
- `new_session` gives `session_replaced`, including when HMP restarts between the read and the
  next history call;
- an unresolvable cursor gives `cursor_not_resolvable`;
- a conversation id other than `default` gives `404`.

This module uses the interface `contracts/fixture-format.md` describes:

    tools/fixtures/build_fixture.py --build <label> --out <scratch dir> [--serve]
    tools/fixtures/mutate.py --out <scratch dir> --instance <key> --mutation <name>

`<name>` is a `mutations` key of the manifest: `append`, `rewrite` or `new_session`. It assumes
that `--serve` on an existing `--out` serves it without rebuilding (so a restart keeps the
mutations and the HMP store), and that it prints one JSON object per instance (`A` then `B`) on
stdout, with at least
`{"key", "port", "iid", "device": {"device_id", "access_token"}}`. That is the
reference-client state the build leaves for these tests. Until T060 and T062 land, every test
here is skipped with that reason. When they land, align these helpers with the real flags. Do not
weaken an assertion.

Every mutation targets a specific instance's `f1-alpha`, per `fixtures/f1/instances.yaml`'s own
`conversations`/`mutations` blocks: `rewrite` names `conv-long`, which only instance A's
`f1-alpha` has; `append` and `new_session` name `conv-b`, which only instance B's `f1-alpha` has
(A's `f1-alpha` uses `conv-long` instead -- "SAME profile name as on A, different content" is the
manifest's own deliberate edge case). Each test below reads from the instance that actually holds
its mutation's conversation, never assumes "A" for all three.

At most one gateway runs at a time (host load); every test stops its gateway.
"""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BUILD_FIXTURE = REPO_ROOT / "tools" / "fixtures" / "build_fixture.py"
MUTATE = REPO_ROOT / "tools" / "fixtures" / "mutate.py"
# Machine-local optional builds (tools/hermes_builds/builds.yaml `optional: true`) join the read
# suite only where they have actually been extracted, so `-k <label>` for one of them selects real
# tests there and nothing is parametrized over a build absent from this machine.
_OPTIONAL_BUILDS = ("owner-local",)
_BUILDS_DIR_ENV = os.environ.get("HMP_HERMES_BUILDS_DIR", "")
BUILDS = (
    "stock-base",
    "experimental",
    *(
        label
        for label in _OPTIONAL_BUILDS
        if _BUILDS_DIR_ENV and (Path(_BUILDS_DIR_ENV) / label / "src").is_dir()
    ),
)
CONVERSATION = "/hmp/v1/bots/f1-alpha/conversations/default"

pytestmark = [
    pytest.mark.skipif(
        not BUILD_FIXTURE.is_file(),
        reason="needs T060 tools/fixtures/build_fixture.py (fixture builder not landed yet)",
    ),
    pytest.mark.skipif(
        not MUTATE.is_file(),
        reason="needs T062 tools/fixtures/mutate.py (fixture mutations not landed yet)",
    ),
    pytest.mark.skipif(
        not os.environ.get("HMP_HERMES_BUILDS_DIR"),
        reason="needs HMP_HERMES_BUILDS_DIR with extracted builds and venvs (T004)",
    ),
]


class Served:
    """One fixture instance served by a real gateway (T060 `--serve`)."""

    def __init__(self, proc: subprocess.Popen[str], info: dict[str, Any]) -> None:
        self.proc = proc
        self.info = info

    def get(self, path: str) -> tuple[int, Any]:
        # The reference client pins the iid; here the TLS pin is not what is under test, so the
        # certificate is not verified. T035 covers the pin.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            f"https://127.0.0.1:{self.info['port']}{path}",
            headers={
                "Authorization": f"Bearer {self.info['device']['access_token']}",
                "HMP-Instance": self.info["iid"],
            },
        )
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:  # noqa: S310
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read() or b"null")

    def stop(self) -> None:
        self.proc.terminate()
        self.proc.wait(timeout=30)


def _build(label: str, out: Path) -> None:
    subprocess.run(
        [sys.executable, str(BUILD_FIXTURE), "--build", label, "--out", str(out)], check=True
    )


def _serve(label: str, out: Path) -> dict[str, Served]:
    """Both instances run under ONE gateway subprocess (`--serve` starts `A` and `B` together);
    this reads one JSON line per instance and returns `{key: Served}` sharing that one `proc`.
    Call `_stop(served)` once per dict, not once per `Served` (they share the underlying
    process)."""
    proc = subprocess.Popen(
        [sys.executable, str(BUILD_FIXTURE), "--build", label, "--out", str(out), "--serve"],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    served: dict[str, Served] = {}
    for _ in range(2):
        info = json.loads(proc.stdout.readline())
        served[info["key"]] = Served(proc, info)
    return served


def _stop(served: dict[str, Served]) -> None:
    next(iter(served.values())).stop()


def _mutate(out: Path, mutation: str, instance: str = "A") -> None:
    subprocess.run(
        [
            sys.executable,
            str(MUTATE),
            "--out",
            str(out),
            "--instance",
            instance,
            "--mutation",
            mutation,
        ],
        check=True,
    )


@pytest.fixture(params=BUILDS)
def fixture_home(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[tuple[str, Path]]:
    out = tmp_path / "fixture"
    _build(request.param, out)
    yield request.param, out


def _head(served: Served) -> int:
    status, body = served.get(CONVERSATION + "?limit=500")
    assert status == 200, body
    return int(body["head_message_id"])


def test_append_gives_rows(fixture_home: tuple[str, Path]) -> None:
    # `append` names `conv-b` (fixtures/f1/instances.yaml), which only instance B's `f1-alpha` has.
    label, out = fixture_home
    served = _serve(label, out)
    try:
        b = served["B"]
        head = _head(b)
        _mutate(out, "append", instance="B")
        status, body = b.get(f"{CONVERSATION}/messages?after={head}")
        assert status == 200 and len(body["messages"]) == 3
        assert all(m["id"] > head for m in body["messages"])
    finally:
        _stop(served)


def test_in_place_compaction_is_history_rewritten(fixture_home: tuple[str, Path]) -> None:
    # `rewrite` names `conv-long` (fixtures/f1/instances.yaml), which only instance A's
    # `f1-alpha` has.
    label, out = fixture_home
    served = _serve(label, out)
    try:
        head = _head(served["A"])
        _stop(served)
        _mutate(out, "rewrite", instance="A")  # offline, gateway stopped (fixture-format rule 3)
        served = _serve(label, out)
        status, body = served["A"].get(f"{CONVERSATION}/messages?after={head}")
        assert status == 200 and body["reset"]["reason"] == "history_rewritten"
    finally:
        _stop(served)


def test_new_session_is_session_replaced_across_restart(fixture_home: tuple[str, Path]) -> None:
    # `new_session` names `conv-b` (fixtures/f1/instances.yaml), which only instance B's
    # `f1-alpha` has.
    label, out = fixture_home
    served = _serve(label, out)
    try:
        head = _head(served["B"])  # persists the session baseline
        _stop(served)  # HMP restarts; the replacement happens while it is down
        _mutate(out, "new_session", instance="B")
        served = _serve(label, out)
        status, body = served["B"].get(f"{CONVERSATION}/messages?after={head}")
        assert status == 200 and body["reset"]["reason"] == "session_replaced"
    finally:
        _stop(served)


def test_a1_session_browsing_multi_source_fixture(fixture_home: tuple[str, Path]) -> None:
    """Amendment A1 (session browsing, OD-F9/OD-F10, OD-F11), on a real gateway: `fixtures/f1/
    instances.yaml`'s `f1-alpha`/A `other_sessions` (a canonical hidden "Bot Chat", a cli session,
    a compression lineage, telegram, discord, one archived, one hidden-but-not-"Bot Chat") read
    back with ONLY the phone's own session and the canonical "Bot Chat" listed -- never a channel
    session -- exactly as `reads._is_bot_view_session` selects them (independently verified
    against the real Hermes source for this amendment; see also `hermes-agent`'s
    `apps/desktop/src/plugins/hermes-bots/canonical-chat.ts`)."""
    label, out = fixture_home
    served = _serve(label, out)
    try:
        a = served["A"]
        status, body = a.get("/hmp/v1/bots/f1-alpha/sessions?limit=100")
        assert status == 200, body
        by_title = {item["title"]: item for item in body["sessions"]}
        # OD-F11: cli-1, telegram-1, discord-1, desktop-1 (title "Desktop chat", not "Bot Chat"),
        # the compression lineage, archived-1 and hidden-1 are ALL excluded -- only the canonical
        # "Bot Chat" and the phone's own (untitled) session are listed.
        assert set(by_title) == {"Bot Chat", None}
        bot_chat = by_title["Bot Chat"]
        assert bot_chat["source"] == "desktop" and bot_chat["is_mobile"] is False
        assert by_title[None]["source"] == "hmp" and by_title[None]["is_mobile"] is True
        ref = bot_chat["session_ref"]
        assert ref.startswith("ses1_")

        status, body = a.get(f"/hmp/v1/bots/f1-alpha/sessions/{ref}/messages")
        assert status == 200 and body["session_ref"] == ref
        assert [m["role"] for m in body["messages"]] == ["user", "assistant"]

        status, body = a.get("/hmp/v1/bots/f1-alpha/sessions/ses1_doesnotexist/messages")
        assert status == 404 and body["error"]["code"] == "not_found"
    finally:
        _stop(served)


def test_unresolvable_cursor_and_other_ids(fixture_home: tuple[str, Path]) -> None:
    label, out = fixture_home
    served = _serve(label, out)
    try:
        a = served["A"]
        head = _head(a)
        status, body = a.get(f"{CONVERSATION}/messages?after={head + 100_000}")
        assert status == 200 and body["reset"]["reason"] == "cursor_not_resolvable"
        for path in (
            "/hmp/v1/bots/f1-alpha/conversations/other",
            "/hmp/v1/bots/f1-alpha/conversations/other/messages?after=1",
        ):
            status, body = a.get(path)
            assert status == 404 and body["error"]["code"] == "not_found"
    finally:
        _stop(served)
