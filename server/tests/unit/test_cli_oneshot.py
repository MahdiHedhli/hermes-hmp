"""`hermes hmp pair offer`'s one-command flow (owner requirement, 2026-09-27): after the QR, the
command stays running, polls the store for the phone's P2 claim, shows the code it expects and
asks the operator to compare it against the phone and press y (or n to deny) -- OD-F7,
2026-09-27, which replaces typing the SAS in this interactive flow (`pair confirm --sas` is
unchanged and untested here; see `test_cli.py`). On success it offers to allow the phone's served
bots right there in the terminal (OD-F8, 2026-09-27) before printing the next steps -- all in the
one `hermes hmp pair offer` invocation, instead of the old two-step `pair list` then `pair
confirm`.

Every scenario here uses a fake TTY, an injected clock (`hmp_kit.Env.clock`) and an injected
`sleep` (`cli.CliEnv.sleep`), against a real store in `tmp_path` -- no real waiting, and no real
stdin. `FakeSleep`'s queued actions stand in for "time passes" (a phone scans, the clock jumps
past an expiry) without a real delay; `FakeStdin` stands in for what the operator types, including
the `KeyboardInterrupt` a real Ctrl-C would raise out of a blocking read. OD-F8's tests additionally
inject a FAKE `hermes` runner (`cli.CliEnv.hermes_executable` / `run_hermes_cli`) -- no real
subprocess is ever spawned by this file.

`--no-wait` (kept for scripts) is exercised here as the one case that must reach neither `sleep`
nor `stdin` at all -- `test_cli.py`'s own offer tests (adapted to pass `--no-wait`) already cover
its output being identical to the pre-existing behavior.
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import cli, crypto, server, wire
from hmp_plugin.compat import CompatResult, CompatStatus
from hmp_plugin.contract import OFFER_TTL_S, PAIRING_CONFIRM_WINDOW_S, OtherWhy
from hmp_plugin.pairing import PairingService

from . import hmp_kit
from .test_cli import Cli

# A sentinel understood by both fakes below: raise `KeyboardInterrupt`, as a real Ctrl-C would.
INTERRUPT = object()


class FakeSleep:
    """Replaces `time.sleep` for the wait-for-scan poll. Each call consumes the next queued
    action instead of actually sleeping: a zero-arg callable runs (typically claiming the offer
    or advancing the fake clock), or `INTERRUPT` raises `KeyboardInterrupt`. Once the queue is
    empty, further calls are silent no-ops (the poll then re-queries immediately)."""

    def __init__(self, actions: list[Any]) -> None:
        self._actions = list(actions)
        self.calls = 0

    def __call__(self, _seconds: float) -> None:
        self.calls += 1
        if not self._actions:
            return
        action = self._actions.pop(0)
        if action is INTERRUPT:
            raise KeyboardInterrupt
        action()


class FakeStdin:
    """Replaces the prompt's `readline()`. Each queued item is a line (already ending in `\\n`,
    as a real `readline()` would return), `INTERRUPT` to raise `KeyboardInterrupt`, or is absent
    entirely -- an exhausted queue returns `""`, matching a real closed/EOF stdin."""

    def __init__(self, lines: list[Any]) -> None:
        self._lines = list(lines)

    def isatty(self) -> bool:
        return True

    def readline(self) -> str:
        if not self._lines:
            return ""
        item = self._lines.pop(0)
        if item is INTERRUPT:
            raise KeyboardInterrupt
        return item


class BoomSleep:
    """`--no-wait` must reach neither `sleep` nor `stdin` at all."""

    def __call__(self, _seconds: float) -> None:
        raise AssertionError("pair offer --no-wait must never sleep")


class BoomStdin:
    def isatty(self) -> bool:
        return True

    def readline(self) -> str:
        raise AssertionError("pair offer --no-wait must never read stdin")


@dataclass
class _FakeResult:
    returncode: int
    stdout: str = ""


def _boom_hermes_cli(*_a: Any, **_k: Any) -> Any:
    raise AssertionError("must not run hermes when there is nothing to grant (--no-grant, or no "
                          "profiles/nothing chosen)")


class FakeHermesRuns:
    """Fake `CliEnv.run_hermes_cli` (OD-F8): records every call's exact `(exe, argv, timeout)` so
    tests can assert the argv shape, and answers `hermes -p <profile> pairing list` /
    `pairing approve hmp <id>` from `pending`, a `{profile: [rows]}` map of `pairing list`'s own
    table rows (`"hmp <request_id> <user_id> <name...>"`, PR6-4's own column shape). No real
    subprocess is ever spawned. `fail_approve` names `(profile, request_id)` pairs whose approve
    call answers non-zero, to exercise the "not every request could be approved" path."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.pending: dict[str, list[str]] = {}
        self.approved: list[tuple[str, str]] = []
        self.fail_approve: set[tuple[str, str]] = set()

    def __call__(
        self, exe: str, argv: list[str], *, timeout: float, environ: Any
    ) -> _FakeResult:
        assert isinstance(argv, list), "argv must always be a list, never a shell string"
        self.calls.append({"exe": exe, "argv": list(argv), "timeout": timeout})
        if argv[2:4] == ["pairing", "list"]:
            profile = argv[1]
            return _FakeResult(0, "\n".join(self.pending.get(profile, [])))
        if argv[2:5] == ["pairing", "approve", "hmp"]:
            profile, request_id = argv[1], argv[5]
            if (profile, request_id) in self.fail_approve:
                return _FakeResult(1)
            self.approved.append((profile, request_id))
            self.pending[profile] = [
                row for row in self.pending.get(profile, []) if row.split()[1] != request_id
            ]
            return _FakeResult(0)
        raise AssertionError(f"unexpected hermes argv: {argv}")


def _claim_via_qr(c: Cli, dev: hmp_kit.Device) -> bytes:
    """The phone's real P2 claim against the offer this `pair offer` call just minted and
    rendered into the (fake) QR -- decoded from the QR payload, not read out of the store, since
    the real secret `S` is stored only as a hash. Returns the decoded secret (for tests that must
    confirm it is never printed)."""
    payload = c.qr.rendered[-1]
    offer = wire.decode_qr_payload(payload, now=c.env.clock.now)
    s = wire.b64u_decode(offer.s, length=32)
    body = c.env.p2_body(dev, hmp_kit.Offer(offer.oid, s))
    PairingService(c.env.store, c.env.identity, server.RateLimiter()).request(
        body, peer="127.0.0.1", now=c.env.clock.now
    )
    return s


def _run_offer(
    c: Cli,
    *extra_args: str,
    sleep: Any,
    stdin: Any,
    hermes_executable: Any = None,
    run_hermes_cli: Any = None,
) -> int:
    env = c.cli_env()
    env.sleep = sleep
    env.stdin = stdin
    if hermes_executable is not None:
        env.hermes_executable = hermes_executable
    if run_hermes_cli is not None:
        env.run_hermes_cli = run_hermes_cli
    parser = argparse.ArgumentParser(prog="hermes hmp")
    cli.setup_parser(parser)
    c.stdout.seek(0)
    c.stdout.truncate()
    c.stderr.seek(0)
    c.stderr.truncate()
    return cli.dispatch(parser.parse_args(["pair", "offer", *extra_args]), env)


def _device_row(env: hmp_kit.Env) -> Any:
    with env.store.transaction() as conn:
        return conn.execute("SELECT * FROM devices").fetchone()


def _pairing_row(env: hmp_kit.Env) -> Any:
    with env.store.transaction() as conn:
        return conn.execute("SELECT * FROM pairings").fetchone()


def _offer_row(env: hmp_kit.Env) -> Any:
    with env.store.transaction() as conn:
        return conn.execute("SELECT * FROM offers").fetchone()


@pytest.fixture
def env(tmp_path: Path) -> hmp_kit.Env:
    return hmp_kit.Env(tmp_path)


@pytest.fixture
def c(env: hmp_kit.Env) -> Cli:
    return Cli(env)


# --------------------------------------------------------------------------------------------------
# Happy path
# --------------------------------------------------------------------------------------------------


def test_happy_path_y_confirms_and_pairs(c: Cli) -> None:
    c.write_record()  # no `profiles`: the grant step falls back to the placeholder text
    dev = hmp_kit.Device(name="f1-fixture-device-1")
    expected_sas = crypto.device_sas(crypto.spki_fingerprint(dev.pub))

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-1",
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n"]),
    )

    assert code == cli.EXIT_OK, c.out
    assert "Waiting for the phone to scan" in c.out
    assert '"f1-fixture-device-1" (unverified' in c.out
    # OD-F7: the expected code IS shown, prominently, for the operator to compare (this is the
    # point of compare-and-confirm -- contrast the pre-OD-F7 typed-SAS flow, which never showed
    # it).
    assert "Expected code:" in c.out
    assert expected_sas in c.out
    assert "Does the phone show this code? [y/N]" in c.out
    assert "Paired ✓ f1-fixture-label-1" in c.out
    assert "Next steps" in c.out
    assert "Request access" in c.out
    assert "pairing approve hmp" in c.out
    assert _device_row(c.env)["state"] == "ACTIVE"
    assert _pairing_row(c.env)["state"] == "confirmed"
    # The raw QR payload (and the pairing secret it carries) is never printed (item 8).
    assert "hmp1:" not in c.out


def test_unsupported_build_pairs_without_bot_or_owner_grant(c: Cli) -> None:
    c.compat = CompatResult(CompatStatus.UNSUPPORTED, OtherWhy.HERMES_BUILD_UNSUPPORTED)
    c.write_record(profiles=[("default", "Default Bot")])
    dev = hmp_kit.Device(name="f1-fixture-unsupported")

    result = _run_offer(
        c,
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n", "GRANT\n"]),
        hermes_executable=lambda: "hermes",
        run_hermes_cli=_boom_hermes_cli,
    )

    assert result == cli.EXIT_OK, c.out
    assert "Paired ✓" in c.out
    assert "Bot Chat and controls remain unavailable" in c.out
    assert "Allow the phone to use all" not in c.out
    assert "Type GRANT" not in c.out
    row = _device_row(c.env)
    assert row["state"] == "ACTIVE"
    assert c.env.store.owner_controls_decision(row["device_id"]) is False


def test_host_grants_owner_controls_only_after_explicit_word(c: Cli) -> None:
    c.write_record()
    dev = hmp_kit.Device(name="f1-fixture-owner-phone")

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-owner-phone",
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n", "GRANT\n"]),
    )

    assert code == cli.EXIT_OK, c.out
    row = _device_row(c.env)
    assert c.env.store.owner_controls_decision(row["device_id"]) is True
    assert "separate from Bot Chat access" in c.out
    assert "control granted" in c.out


def test_old_yes_answer_cannot_grant_owner_controls(c: Cli) -> None:
    c.write_record()
    dev = hmp_kit.Device(name="f1-fixture-chat-only-phone")

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-chat-only-phone",
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n", "y\n"]),
    )

    assert code == cli.EXIT_OK, c.out
    row = _device_row(c.env)
    assert c.env.store.owner_controls_decision(row["device_id"]) is False
    assert "control stays off" in c.out


def test_offer_for_the_intended_user_shares_without_a_second_prompt(c: Cli) -> None:
    """Item 4: when the offer named `--user`, the one-shot flow completes the existing
    `--user ... --yes-share` confirm path automatically -- the operator already made that choice
    at `pair offer --user` time -- while still showing the share preview `_do_confirm` prints."""
    c.write_record()
    user = "hmpu_" + "7" * 32
    c.env.store.insert_user(user, "f1-fixture-label-0", c.env.clock.now)
    dev = hmp_kit.Device(name="f1-fixture-device-1b")

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-1b",
        "--user",
        user,
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n"]),
    )

    assert code == cli.EXIT_OK, c.out
    assert f"User {user} already has:" in c.out  # the share preview still shows
    assert "Paired ✓ f1-fixture-label-1b" in c.out
    assert _device_row(c.env)["user_id"] == user


# --------------------------------------------------------------------------------------------------
# Garbage input re-asks; 'n' (and a blank line) denies (OD-F7: there is no typed-SAS mismatch to
# test in this flow any more -- `test_cli.py` covers `pair confirm --sas`'s mismatch/burn-limit
# rules, which are unchanged).
# --------------------------------------------------------------------------------------------------


def test_garbage_input_reasks_then_y_confirms(c: Cli) -> None:
    c.write_record()
    dev = hmp_kit.Device(name="f1-fixture-device-2")

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-2",
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["maybe\n", "sure\n", "y\n"]),
    )

    assert code == cli.EXIT_OK, c.out
    assert c.out.count("Please answer y or n.") == 2
    assert "Paired ✓ f1-fixture-label-2" in c.out
    assert _device_row(c.env)["state"] == "ACTIVE"


def test_typing_n_denies(c: Cli) -> None:
    c.write_record()
    dev = hmp_kit.Device(name="f1-fixture-device-4")

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-4",
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["n\n"]),
    )

    assert code == cli.EXIT_OK, c.out
    assert "Denied." in c.out
    assert _pairing_row(c.env)["state"] == "denied"
    assert _device_row(c.env) is None


def test_blank_line_denies_the_bracket_default(c: Cli) -> None:
    """"[y/N]": a blank line takes the bracket's capital default, N -- deny, not a re-ask."""
    c.write_record()
    dev = hmp_kit.Device(name="f1-fixture-device-4b")

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-4b",
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["\n"]),
    )

    assert code == cli.EXIT_OK, c.out
    assert "Denied." in c.out
    assert _pairing_row(c.env)["state"] == "denied"


# --------------------------------------------------------------------------------------------------
# Offer expiry while waiting for a scan; confirm_by expiry while waiting for input
# --------------------------------------------------------------------------------------------------


def test_offer_expires_before_a_scan(c: Cli) -> None:
    c.write_record()

    def bump() -> None:
        c.env.clock.now += OFFER_TTL_S + 1

    code = _run_offer(
        c, "--label", "f1-fixture-label-5", sleep=FakeSleep([bump]), stdin=FakeStdin([])
    )

    assert code == cli.EXIT_OK, c.out
    assert "expired before it was scanned" in c.out
    assert "hermes hmp pair offer --label f1-fixture-label-5" in c.out
    assert _offer_row(c.env)["state"] == "open"  # left to expire naturally, nothing forced


def test_confirm_window_closes_before_typing(c: Cli) -> None:
    c.write_record()
    dev = hmp_kit.Device(name="f1-fixture-device-6")

    def claim_then_jump() -> None:
        _claim_via_qr(c, dev)
        c.env.clock.now += PAIRING_CONFIRM_WINDOW_S + 1

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-6",
        sleep=FakeSleep([claim_then_jump]),
        stdin=FakeStdin([]),  # never reached: the deadline check runs before any read
    )

    assert code == cli.EXIT_OK, c.out
    assert "confirm window" in c.out and "closed" in c.out
    assert "hermes hmp pair offer" in c.out  # resume hint: make a new offer
    assert _pairing_row(c.env)["state"] == "awaiting_operator"  # untouched, just unreachable now


# --------------------------------------------------------------------------------------------------
# Ctrl-C: while waiting for a scan, and while prompting for the code
# --------------------------------------------------------------------------------------------------


def test_ctrl_c_before_any_scan_leaves_the_offer_to_expire(c: Cli) -> None:
    c.write_record()

    code = _run_offer(
        c, "--label", "f1-fixture-label-7", sleep=FakeSleep([INTERRUPT]), stdin=FakeStdin([])
    )

    assert code == cli.EXIT_INTERRUPTED, c.out
    assert "Cancelled" in c.out
    assert "hermes hmp pair offer --label f1-fixture-label-7" in c.out
    assert _offer_row(c.env)["state"] == "open"  # nothing mutated; left to expire


def test_ctrl_c_while_prompting_leaves_the_pairing_pending(c: Cli) -> None:
    c.write_record()
    dev = hmp_kit.Device(name="f1-fixture-device-8")

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-8",
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin([INTERRUPT]),
    )

    assert code == cli.EXIT_INTERRUPTED, c.out
    assert "still pending" in c.out
    assert "hermes hmp pair list" in c.out
    assert "hermes hmp pair confirm" in c.out
    assert "hermes hmp pair deny" in c.out
    assert _pairing_row(c.env)["state"] == "awaiting_operator"  # untouched
    assert _device_row(c.env) is None


# --------------------------------------------------------------------------------------------------
# --no-wait keeps the old behavior for scripts
# --------------------------------------------------------------------------------------------------


def test_no_wait_never_waits_or_prompts(c: Cli) -> None:
    c.write_record()

    code = _run_offer(
        c, "--label", "f1-fixture-label-9", "--no-wait", sleep=BoomSleep(), stdin=BoomStdin()
    )

    assert code == cli.EXIT_OK, c.out
    assert "Waiting for the phone" not in c.out
    assert "Next steps" not in c.out
    assert "Scan with Hermes Bot Mobile" in c.out


# --------------------------------------------------------------------------------------------------
# OD-F7: the expected SAS IS shown (the whole point of compare-and-confirm); the raw QR payload
# and the offer's own pairing secret S never are, across the whole flow.
# --------------------------------------------------------------------------------------------------


def test_offer_secret_never_printed_but_expected_sas_is_shown(c: Cli) -> None:
    c.write_record()
    dev = hmp_kit.Device(name="f1-fixture-device-9")
    expected_sas = crypto.device_sas(crypto.spki_fingerprint(dev.pub))
    captured: dict[str, bytes] = {}

    def claim() -> None:
        captured["s"] = _claim_via_qr(c, dev)

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-9b",
        sleep=FakeSleep([claim]),
        stdin=FakeStdin(["y\n"]),
    )

    assert code == cli.EXIT_OK, c.out
    combined = c.out + c.err
    assert "hmp1:" not in combined
    assert expected_sas in combined  # OD-F7: shown for the operator's own visual compare
    assert wire.b64u_encode(captured["s"]) not in combined


# --------------------------------------------------------------------------------------------------
# OD-F8 (2026-09-27): in-terminal bot access right after "Paired ✓".
# --------------------------------------------------------------------------------------------------


def _confirm_with_user(c: Cli, *, label: str) -> str:
    """A `hmpu_` user this test controls (so the request rows below can name a known, exact
    `user_id`), used as `pair offer --user <id>`'s intended user. Returns the user id."""
    user = "hmpu_" + crypto.random_bytes(16).hex()
    c.env.store.insert_user(user, label, c.env.clock.now)
    return user


def test_grant_all_happy_path(c: Cli) -> None:
    user = _confirm_with_user(c, label="f1-fixture-label-g0")
    c.write_record(profiles=[("default", "Default Bot"), ("netmin", "Net Admin")])
    dev = hmp_kit.Device(name="f1-fixture-device-g0")
    fake = FakeHermesRuns()
    fake.pending["default"] = [f"hmp beefbeefbeef0001 {user} Default Bot"]
    fake.pending["netmin"] = [f"hmp beefbeefbeef0002 {user} Net Admin"]

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-g0",
        "--user",
        user,
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n", "y\n"]),  # confirm, then an explicit grant-all
        hermes_executable=lambda: "hermes",
        run_hermes_cli=fake,
    )

    assert code == cli.EXIT_OK, c.out
    assert "Default Bot (default)" in c.out
    assert "Net Admin (netmin)" in c.out
    assert "Allow the phone to use all of these? [y/n/pick]" in c.out
    assert "✓ Default Bot (default)" in c.out
    assert "✓ Net Admin (netmin)" in c.out
    assert sorted(fake.approved) == [
        ("default", "beefbeefbeef0001"),
        ("netmin", "beefbeefbeef0002"),
    ]
    assert "Next steps" not in c.out  # the grant flow ran; the old placeholder is not shown too


def test_grant_step_rereads_the_record_after_offer_started(c: Cli) -> None:
    """Live-bug fix (multiplexed gateway): the multiplexer can bring a profile online strictly
    AFTER `pair offer` reads the record for its own endpoint, while the operator is still waiting
    for the phone to scan. The grant step -- built only after confirmation, from its own fresh
    `_served_bots` read, well after that first offer-start read -- must see the newly served
    profile too, not whatever was on disk when the offer began."""
    user = _confirm_with_user(c, label="f1-fixture-label-g5")
    c.write_record(profiles=[("default", "Default Bot")])
    dev = hmp_kit.Device(name="f1-fixture-device-g5")
    fake = FakeHermesRuns()
    fake.pending["default"] = [f"hmp beefbeefbeef0005 {user} Default Bot"]
    fake.pending["netmin"] = [f"hmp beefbeefbeef0006 {user} Net Admin"]

    def _bring_netmin_online() -> None:
        # Simulates `gateway.run_profile_reconcile`'s hot-add landing while the operator is still
        # waiting for the phone to scan -- well before "Paired ✓", the record on disk changes
        # underneath the still-running `pair offer` process.
        c.write_record(profiles=[("default", "Default Bot"), ("netmin", "Net Admin")])
        _claim_via_qr(c, dev)

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-g5",
        "--user",
        user,
        sleep=FakeSleep([_bring_netmin_online]),
        stdin=FakeStdin(["y\n", "y\n"]),  # confirm, then an explicit grant-all
        hermes_executable=lambda: "hermes",
        run_hermes_cli=fake,
    )

    assert code == cli.EXIT_OK, c.out
    assert "Default Bot (default)" in c.out
    assert "Net Admin (netmin)" in c.out  # only on disk after the offer's own initial read
    assert sorted(fake.approved) == [
        ("default", "beefbeefbeef0005"),
        ("netmin", "beefbeefbeef0006"),
    ]


def test_grant_blank_line_reasks_instead_of_granting_all(c: Cli) -> None:
    """NIT fix, independent review of OD-F8: a blank line at the grant prompt used to silently mean
    "yes, all". It must now re-ask, exactly like garbage input at the compare-and-confirm prompt,
    and only an explicit `y`/`yes` actually grants."""
    user = _confirm_with_user(c, label="f1-fixture-label-g0b")
    c.write_record(profiles=[("default", "Default Bot")])
    dev = hmp_kit.Device(name="f1-fixture-device-g0b")
    fake = FakeHermesRuns()
    fake.pending["default"] = [f"hmp 0123456789abcdef {user} Default Bot 1m ago"]

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-g0b",
        "--user",
        user,
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n", "\n", "y\n"]),  # confirm; blank (must re-ask); then explicit yes
        hermes_executable=lambda: "hermes",
        run_hermes_cli=fake,
    )

    assert code == cli.EXIT_OK, c.out
    assert "Type y, n or pick:" in c.out  # the re-ask actually happened
    assert fake.approved == [("default", "0123456789abcdef")]  # the later explicit "y" still ran


def test_grant_pick_subset(c: Cli) -> None:
    user = _confirm_with_user(c, label="f1-fixture-label-g1")
    c.write_record(profiles=[("default", "Default Bot"), ("netmin", "Net Admin")])
    dev = hmp_kit.Device(name="f1-fixture-device-g1")
    fake = FakeHermesRuns()
    fake.pending["default"] = [f"hmp beefbeefbeef0003 {user} Default Bot"]
    # never chosen: must stay untouched
    fake.pending["netmin"] = [f"hmp beefbeefbeef0004 {user} Net Admin"]

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-g1",
        "--user",
        user,
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n", "pick\n", "y\n", "n\n"]),  # confirm; pick; yes default; no netmin
        hermes_executable=lambda: "hermes",
        run_hermes_cli=fake,
    )

    assert code == cli.EXIT_OK, c.out
    assert "✓ Default Bot (default)" in c.out
    assert "✓ Net Admin (netmin)" not in c.out
    assert fake.approved == [("default", "beefbeefbeef0003")]
    assert not any(call["argv"][1] == "netmin" for call in fake.calls)


def test_grant_timeout_prints_fallback_command(c: Cli) -> None:
    user = _confirm_with_user(c, label="f1-fixture-label-g2")
    c.write_record(profiles=[("default", "Default Bot")])
    dev = hmp_kit.Device(name="f1-fixture-device-g2")
    fake = FakeHermesRuns()  # nothing ever arrives in `pending`

    def past_deadline() -> None:
        c.env.clock.now += cli.BOT_GRANT_WAIT_S + 1

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-g2",
        "--user",
        user,
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev), past_deadline]),
        stdin=FakeStdin(["y\n", "y\n"]),
        hermes_executable=lambda: "hermes",
        run_hermes_cli=fake,
    )

    assert code == cli.EXIT_OK, c.out
    assert "Still waiting for the phone to request access to:" in c.out
    assert "Default Bot (default)" in c.out
    assert cli._combined_approve_command(["default"], user) in c.out
    assert fake.approved == []


def test_grant_drops_an_invalid_profile_name(c: Cli) -> None:
    """Defence in depth (OD-F8): a served profile name that fails Hermes's own naming rule never
    reaches the prompt, the argv, or the fallback command text."""
    user = _confirm_with_user(c, label="f1-fixture-label-g3")
    c.write_record(profiles=[("bad profile!", "Weird"), ("default", "Default Bot")])
    dev = hmp_kit.Device(name="f1-fixture-device-g3")
    fake = FakeHermesRuns()
    fake.pending["default"] = [f"hmp beefbeefbeef0005 {user} Default Bot"]

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-g3",
        "--user",
        user,
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n", "y\n"]),
        hermes_executable=lambda: "hermes",
        run_hermes_cli=fake,
    )

    assert code == cli.EXIT_OK, c.out
    assert "Weird" not in c.out
    assert "bad profile!" not in c.out
    assert "✓ Default Bot (default)" in c.out
    assert all(call["argv"][1] != "bad profile!" for call in fake.calls)


def test_grant_approves_only_this_pairings_user_id(c: Cli) -> None:
    """A `pairing list` row for another user is ignored, never approved."""
    user = _confirm_with_user(c, label="f1-fixture-label-g4")
    other = "hmpu_" + "9" * 32
    c.write_record(profiles=[("default", "Default Bot")])
    dev = hmp_kit.Device(name="f1-fixture-device-g4")
    fake = FakeHermesRuns()
    fake.pending["default"] = [
        f"hmp beefbeefbeef0006 {other} Someone Else",
        f"hmp beefbeefbeef0007 {user} Default Bot",
    ]

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-g4",
        "--user",
        user,
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n", "y\n"]),
        hermes_executable=lambda: "hermes",
        run_hermes_cli=fake,
    )

    assert code == cli.EXIT_OK, c.out
    assert fake.approved == [("default", "beefbeefbeef0007")]


def test_grant_a_newline_in_a_crafted_name_cannot_forge_a_second_row(c: Cli) -> None:
    """SHOULD-FIX, independent review of OD-F8: `gateway/run_inbound.py` stores `user_name` from
    the inbound sender with no sanitizer, and Hermes's own `pairing list` printer
    (`hermes_cli/pairing.py`) writes it unescaped. A single crafted name containing a literal
    newline followed by a fake `hmp <id> <our user id>` line therefore splices a second, fully
    attacker-chosen row into this CLI's own `pairing list` stdout -- indistinguishable, byte for
    byte, from a second genuine pending request for the same user. The fix cannot tell a forged row
    from a real second one, so it must approve NEITHER: the crafted id must never appear in
    `fake.approved`, and neither must the real one -- fail closed, not "pick one"."""
    user = _confirm_with_user(c, label="f1-fixture-label-g4b")
    c.write_record(profiles=[("default", "Default Bot")])
    dev = hmp_kit.Device(name="f1-fixture-device-g4b")
    fake = FakeHermesRuns()
    real_id = "0123456789abcdef"
    forged_id = "deadbeefcafef00d"
    # One `pairing list` "row" as `FakeHermesRuns` stores it (joined with "\n" exactly as a real
    # subprocess's stdout would be) whose own `user_name` field carries a raw newline, splicing in
    # a second well-formed-looking line for the SAME user id.
    fake.pending["default"] = [f"hmp {real_id} {user} Legit Name\nhmp {forged_id} {user} evil"]

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-g4b",
        "--user",
        user,
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n", "y\n"]),
        hermes_executable=lambda: "hermes",
        run_hermes_cli=fake,
    )

    assert code == cli.EXIT_OK, c.out
    assert fake.approved == []  # neither id -- ambiguity fails closed
    assert real_id not in c.out and forged_id not in c.out  # neither ever printed as approved
    assert "more than one pending request" in c.out  # reported plainly, not swallowed
    assert not any(call["argv"][2:5] == ["pairing", "approve", "hmp"] for call in fake.calls)


def test_pending_row_parser_rejects_malformed_request_ids(c: Cli) -> None:
    """The strict row pattern (SHOULD-FIX, independent review of OD-F8) rejects anything that is
    not exactly 16 lowercase hex digits for the request id -- too short, uppercase, non-hex, or
    embedded in a larger token -- even though the old whitespace-split parser accepted all of
    these as long as the first field was `hmp` and the third equalled the user id."""
    user = "hmpu_" + "3" * 32
    bad_rows = [
        f"hmp short {user} Name 1m ago",  # not hex at all
        f"hmp DEADBEEFCAFEF00D {user} Name 1m ago",  # uppercase hex
        f"hmp deadbeefcafef00 {user} Name 1m ago",  # 15 hex chars, one short
        f"hmp deadbeefcafef00d0 {user} Name 1m ago",  # 17 hex chars, one long
        f"hmpxdeadbeefcafef00d {user} Name 1m ago",  # platform token is not exactly "hmp"
        f"hmp deadbeefcafef00d{user} Name 1m ago",  # id and user id glued together
    ]
    fake = FakeHermesRuns()
    fake.pending["default"] = bad_rows

    ids = cli._list_pending_hmp_requests(
        cli.CliEnv(environ={"PATH": "/usr/bin"}, run_hermes_cli=fake), "hermes", "default", user
    )

    assert ids == []


def test_no_grant_skips_the_prompt_and_never_runs_hermes(c: Cli) -> None:
    user = _confirm_with_user(c, label="f1-fixture-label-g5")
    c.write_record(profiles=[("default", "Default Bot")])
    dev = hmp_kit.Device(name="f1-fixture-device-g5")

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-g5",
        "--user",
        user,
        "--no-grant",
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n"]),  # only the compare-and-confirm answer; no grant prompt follows
        hermes_executable=_boom_hermes_cli,
        run_hermes_cli=_boom_hermes_cli,
    )

    assert code == cli.EXIT_OK, c.out
    assert "Allow the phone to use all" not in c.out
    assert "Next steps" in c.out


def test_no_profiles_in_record_falls_back_without_running_hermes(c: Cli) -> None:
    """An older gateway's record (no `profiles`): the grant step never runs `hermes` at all."""
    user = _confirm_with_user(c, label="f1-fixture-label-g6")
    c.write_record()  # no `profiles`
    dev = hmp_kit.Device(name="f1-fixture-device-g6")

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-g6",
        "--user",
        user,
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n"]),
        hermes_executable=_boom_hermes_cli,
        run_hermes_cli=_boom_hermes_cli,
    )

    assert code == cli.EXIT_OK, c.out
    assert "Next steps" in c.out


def test_default_run_hermes_cli_uses_argv_list_never_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real `subprocess.run` call (not the fake): argv is always a list, and `shell` is never
    passed as `True` (OD-F8's one subprocess entry point, `_default_run_hermes_cli`)."""
    captured: dict[str, Any] = {}

    def fake_subprocess_run(argv: Any, **kwargs: Any) -> Any:
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_subprocess_run)

    result = cli._default_run_hermes_cli(
        "hermes",
        ["-p", "default", "pairing", "list"],
        timeout=5.0,
        environ={"PATH": "/usr/bin"},
    )

    assert isinstance(captured["argv"], list)
    assert captured["argv"] == ["hermes", "-p", "default", "pairing", "list"]
    assert captured["kwargs"].get("shell", False) is False
    assert result is not None and result.returncode == 0 and result.stdout == "ok"


def test_default_run_hermes_cli_forwards_only_the_allowlisted_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SHOULD-FIX, independent review of OD-F8: the child gets an explicit allow-list, never the
    full parent environment. A secret-shaped variable that happens to be in this operator's shell
    must never reach the subprocess env, while `PATH`/`HOME`/`HERMES_HOME`/`LANG`/`LC_*`/`TMPDIR`
    do."""
    captured: dict[str, Any] = {}

    def fake_subprocess_run(argv: Any, **kwargs: Any) -> Any:
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_subprocess_run)

    parent_env = {
        "PATH": "/usr/bin",
        "HOME": "/home/user",
        "HERMES_HOME": "/home/user/.hermes",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "TMPDIR": "/private/var/tmp/example",
        "OPENAI_API_KEY": "sk-should-never-be-forwarded",  # synthetic test value, never forwarded
        "SOME_RANDOM_SHELL_VAR": "unrelated",
    }

    cli._default_run_hermes_cli(
        "hermes", ["-p", "default", "pairing", "list"], timeout=5.0, environ=parent_env
    )

    forwarded = captured["kwargs"]["env"]
    assert forwarded == {
        "PATH": "/usr/bin",
        "HOME": "/home/user",
        "HERMES_HOME": "/home/user/.hermes",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "TMPDIR": "/private/var/tmp/example",
    }
    assert "OPENAI_API_KEY" not in forwarded
    assert "SOME_RANDOM_SHELL_VAR" not in forwarded


def test_minimal_hermes_env_drops_unlisted_vars_and_keeps_lc_prefix() -> None:
    """Direct unit coverage of the allow-list helper: exact names, the `LC_` prefix family, and
    that an unrelated variable (however plausible-looking) is dropped."""
    out = cli._minimal_hermes_env(
        {
            "PATH": "/bin",
            "LC_CTYPE": "C",
            "LC_TIME": "C",
            "AWS_SECRET_ACCESS_KEY": "not-forwarded",  # synthetic test value, never forwarded
        }
    )
    assert out == {"PATH": "/bin", "LC_CTYPE": "C", "LC_TIME": "C"}


# --------------------------------------------------------------------------------------------------
# Executable resolution (SHOULD-FIX, independent review of OD-F8): never a bare `$PATH` lookup of
# an unhardened path, and "the exact launcher that started this process" is preferred over it.
# --------------------------------------------------------------------------------------------------


def _make_launcher(path: Path, *, mode: int = 0o700) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(mode)
    return path


def test_is_safe_executable_rejects_relative_path(tmp_path: Path) -> None:
    assert cli._is_safe_executable(Path("hermes"), cwd=tmp_path) is False


def test_is_safe_executable_rejects_a_path_inside_the_cwd(tmp_path: Path) -> None:
    launcher = _make_launcher(tmp_path / "hermes")
    assert cli._is_safe_executable(launcher, cwd=tmp_path) is False


def test_is_safe_executable_rejects_world_writable(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    launcher = _make_launcher(outside / "hermes", mode=0o777)
    assert cli._is_safe_executable(launcher, cwd=tmp_path / "cwd") is False


def test_is_safe_executable_rejects_group_writable(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    launcher = _make_launcher(outside / "hermes", mode=0o770)
    assert cli._is_safe_executable(launcher, cwd=tmp_path / "cwd") is False


def test_is_safe_executable_accepts_a_safe_absolute_file(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    launcher = _make_launcher(outside / "hermes", mode=0o755)
    assert cli._is_safe_executable(launcher, cwd=tmp_path / "cwd") is True


def test_is_safe_executable_rejects_a_directory(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "hermes").mkdir()
    assert cli._is_safe_executable(outside / "hermes", cwd=tmp_path / "cwd") is False


def test_is_safe_executable_rejects_a_symlink(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    real = _make_launcher(outside / "real-hermes")
    link = outside / "hermes"
    link.symlink_to(real)
    assert cli._is_safe_executable(link, cwd=tmp_path / "cwd") is False


def test_repo_root_from_sys_path_finds_the_installation_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "install"
    (repo_root / "hermes_cli").mkdir(parents=True)
    (repo_root / "hermes_cli" / "main.py").write_text("# stand-in\n")
    monkeypatch.setattr(cli.sys, "path", ["", str(repo_root), "/some/other/path"])

    assert cli._repo_root_from_sys_path() == repo_root.resolve()


def test_repo_root_from_sys_path_none_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli.sys, "path", ["", "/nonexistent/one", "/nonexistent/two"])
    assert cli._repo_root_from_sys_path() is None


def test_resolve_hermes_executable_prefers_the_launcher_from_sys_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tier 1: the installation directory this process's own `sys.path` already carries (evidence
    of the launcher that started it), never a `$PATH` lookup."""
    repo_root = tmp_path / "install"
    (repo_root / "hermes_cli").mkdir(parents=True)
    (repo_root / "hermes_cli" / "main.py").write_text("# stand-in\n")
    launcher = _make_launcher(repo_root / ".hermes" / "bin" / "hermes")
    monkeypatch.setattr(cli.sys, "path", [str(repo_root)])
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    def boom_which(_name: str) -> str | None:
        raise AssertionError("must not consult $PATH when the launcher is resolved from sys.path")

    monkeypatch.setattr(cli.shutil, "which", boom_which)

    assert cli._default_resolve_hermes_executable() == str(launcher)


def test_resolve_hermes_executable_falls_back_to_sys_executable_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tier 2: no installation directory on `sys.path`, but a console-script sibling of this
    interpreter (a `pip`/venv install's own `bin/hermes`) resolves safely."""
    venv_bin = tmp_path / "venv" / "bin"
    launcher = _make_launcher(venv_bin / "hermes")
    monkeypatch.setattr(cli.sys, "path", ["/nonexistent"])
    monkeypatch.setattr(cli.sys, "executable", str(venv_bin / "python3"))
    (venv_bin / "python3").write_text("#!/bin/sh\n")
    (venv_bin / "python3").chmod(0o755)
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    def boom_which(_name: str) -> str | None:
        raise AssertionError("must not consult $PATH when the sys.executable sibling resolves")

    monkeypatch.setattr(cli.shutil, "which", boom_which)

    assert cli._default_resolve_hermes_executable() == str(launcher)


def test_resolve_hermes_executable_rejects_an_unsafe_path_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tier 3, `shutil.which`, still goes through the same hardening: a world-writable file on
    `$PATH` is never accepted, and resolution reports `None` rather than silently falling back to
    an unsafe path."""
    monkeypatch.setattr(cli.sys, "path", ["/nonexistent"])
    monkeypatch.setattr(cli.sys, "executable", "/nonexistent/python3")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    unsafe = _make_launcher(tmp_path / "unsafe-bin" / "hermes", mode=0o777)
    monkeypatch.setattr(cli.shutil, "which", lambda _name: str(unsafe))

    assert cli._default_resolve_hermes_executable() is None


def test_resolve_hermes_executable_accepts_a_safe_path_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli.sys, "path", ["/nonexistent"])
    monkeypatch.setattr(cli.sys, "executable", "/nonexistent/python3")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    safe = _make_launcher(tmp_path / "safe-bin" / "hermes", mode=0o755)
    monkeypatch.setattr(cli.shutil, "which", lambda _name: str(safe))

    assert cli._default_resolve_hermes_executable() == str(safe)


# --------------------------------------------------------------------------------------------------
# Display-name sanitization (NIT fix, independent review of OD-F8): listener-record display names
# are written straight to the operator's terminal.
# --------------------------------------------------------------------------------------------------


def test_sanitize_display_name_strips_ansi_and_control_chars() -> None:
    raw = "\x1b[31mRed Alert\x1b[0m\x07"
    cleaned = cli._sanitize_display_name(raw)
    assert "\x1b" not in cleaned
    assert "\x07" not in cleaned
    assert "Red Alert" in cleaned


def test_sanitize_display_name_strips_embedded_newlines() -> None:
    raw = "Legit Bot\nhmp deadbeefcafef00d hmpu_" + "1" * 32
    cleaned = cli._sanitize_display_name(raw)
    assert "\n" not in cleaned
    assert "\r" not in cleaned


def test_sanitize_display_name_caps_length() -> None:
    raw = "x" * 500
    cleaned = cli._sanitize_display_name(raw)
    assert len(cleaned.encode("utf-8")) <= cli.DISPLAY_NAME_MAX_BYTES


def test_sanitize_display_name_falls_back_when_everything_is_stripped() -> None:
    raw = "\x1b\x07\x00\n\r"
    assert cli._sanitize_display_name(raw) == "(unnamed)"


def test_grant_prompt_shows_a_sanitized_display_name(c: Cli) -> None:
    """End-to-end: a listener record with a control-character/newline-laden display name never
    writes those raw bytes to the operator's terminal. Declines the grant itself (so this never
    needs a `hermes` runner at all) -- the bots list, sanitized name included, is printed by
    `_prompt_grant_selection` before it ever asks y/n/pick."""
    user = _confirm_with_user(c, label="f1-fixture-label-g8")
    evil_name = "Evil\x1b[31m\nhmp deadbeefcafef00d " + user
    c.write_record(profiles=[("default", evil_name)])
    dev = hmp_kit.Device(name="f1-fixture-device-g8")

    code = _run_offer(
        c,
        "--label",
        "f1-fixture-label-g8",
        "--user",
        user,
        sleep=FakeSleep([lambda: _claim_via_qr(c, dev)]),
        stdin=FakeStdin(["y\n", "n\n"]),  # confirm; decline the grant
        hermes_executable=_boom_hermes_cli,
        run_hermes_cli=_boom_hermes_cli,
    )

    assert code == cli.EXIT_OK, c.out
    assert "\x1b" not in c.out
    assert "\nhmp deadbeefcafef00d" not in c.out
    assert "Evil" in c.out  # the harmless part of the name still shows


# --------------------------------------------------------------------------------------------------
# A non-TTY is still refused (the wait/prompt code must never even be reached)
# --------------------------------------------------------------------------------------------------


def test_non_tty_still_refused(env: hmp_kit.Env) -> None:
    c = Cli(env, tty=False)
    c.write_record()

    code = _run_offer(c, sleep=BoomSleep(), stdin=BoomStdin())

    assert code == cli.EXIT_REFUSED
    assert "interactive terminal" in c.err
    assert _offer_row(c.env) is None  # nothing was minted either
