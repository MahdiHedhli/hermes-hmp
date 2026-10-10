"""Process-aware native gateway readiness for the direct-send fixture (specs/005, amendment 3).

Causal tests use an injected clock, sleep, connect and process so every ordering is deterministic;
a few real spawned, synthetic loopback processes check the same semantics over real sockets. No
Hermes build, gateway, live home or network beyond 127.0.0.1 is used.
"""

from __future__ import annotations

import importlib.util
import json
import math
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import _fixture_common as fc
import direct_send_fixture as dsf
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
INTEGRATION = REPO_ROOT / "server" / "tests" / "integration" / "test_direct_send_fixture.py"
SECRETISH = "f1-fixture-apikey-0123456789abcdef"


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class FakeProc:
    """Only `poll` is part of the contract; `args`/`env` exist to prove they are never emitted."""

    def __init__(self, code: int | None = None) -> None:
        self.code = code
        self.polls = 0
        self.args = ["hermes", "gateway", "--token", SECRETISH]
        self.env = {"API_SERVER_KEY": SECRETISH}

    def poll(self) -> int | None:
        self.polls += 1
        return self.code

    def __repr__(self) -> str:  # a Popen repr includes argv; the helper must never use it
        return f"<FakeProc args={self.args}>"


class Connect:
    """Injected connect: records the timeout it was given and optionally consumes that time."""

    def __init__(self, clock: Clock, *, fail: Exception | None = None, consume: bool = False,
                 succeed_on: int | None = None, on_success=None) -> None:
        self.clock = clock
        self.fail = fail
        self.consume = consume
        self.succeed_on = succeed_on
        self.on_success = on_success
        self.timeouts: list[float] = []

    def __call__(self, port: int, timeout: float) -> None:
        self.timeouts.append(timeout)
        if self.succeed_on is not None and len(self.timeouts) >= self.succeed_on:
            if self.on_success is not None:
                self.on_success()
            return
        if self.consume:
            self.clock.now += timeout
        raise self.fail or ConnectionRefusedError()


def wait(proc, clock, connect, **kw):
    return dsf.wait_for_native_listener(
        proc, 1, clock=clock, sleep=clock.sleep, connect=connect, **kw
    )


# ---- core semantics ------------------------------------------------------------------------


def test_process_dead_before_first_connect_fails_immediately() -> None:
    clock, proc = Clock(), FakeProc(code=3)
    connect = Connect(clock, succeed_on=1)  # a listener IS reachable; it must not matter
    result = wait(proc, clock, connect)
    assert (result.outcome, result.exit_code, result.attempts) == ("process_exit", 3, 0)
    assert connect.timeouts == [] and clock.sleeps == [] and result.elapsed == 0.0


def test_process_dying_during_a_successful_connect_is_not_ready() -> None:
    clock, proc = Clock(), FakeProc()
    connect = Connect(clock, succeed_on=1, on_success=lambda: setattr(proc, "code", 7))
    result = wait(proc, clock, connect)
    assert (result.outcome, result.exit_code, result.attempts) == ("process_exit", 7, 1)
    assert proc.polls == 2  # once before the connect, once after it succeeded


def test_live_process_with_successful_connect_is_ready_with_elapsed() -> None:
    clock, proc = Clock(), FakeProc()
    connect = Connect(clock, succeed_on=3)
    result = wait(proc, clock, connect)
    assert (result.outcome, result.exit_code, result.attempts) == ("ready", None, 3)
    assert result.elapsed == pytest.approx(1.0)  # two 0.5s sleeps, no other time passed
    assert proc.polls == 4  # before each of three connects, once more after the successful one


def test_process_exiting_between_retries_stops_before_the_next_connect() -> None:
    clock, proc = Clock(), FakeProc()
    real_sleep = clock.sleep

    def sleep_then_die(seconds: float) -> None:
        real_sleep(seconds)
        proc.code = 1

    connect = Connect(clock)
    result = dsf.wait_for_native_listener(
        proc, 1, clock=clock, sleep=sleep_then_die, connect=connect
    )
    assert (result.outcome, result.exit_code, result.attempts) == ("process_exit", 1, 1)
    assert len(connect.timeouts) == 1


@pytest.mark.parametrize(
    "exc", [ConnectionRefusedError(), TimeoutError(), InterruptedError(), OSError(4, "io")]
)
def test_every_failed_or_interrupted_connect_is_just_not_ready_then_deadline(exc) -> None:
    clock = Clock()
    connect = Connect(clock, fail=exc)
    result = wait(FakeProc(), clock, connect)
    assert result.outcome == "deadline" and result.exit_code is None
    assert clock.now == 1000.0 + dsf.NATIVE_LISTENER_DEADLINE_SECONDS  # exactly, no overrun
    assert result.elapsed == pytest.approx(45.0)
    assert result.attempts == len(connect.timeouts) > 1


def test_interrupted_connect_is_retried_until_it_succeeds() -> None:
    clock = Clock()

    class Flaky(Connect):
        def __call__(self, port: int, timeout: float) -> None:
            self.timeouts.append(timeout)
            if len(self.timeouts) == 1:
                raise InterruptedError()
            if len(self.timeouts) == 2:
                raise TimeoutError()

    result = wait(FakeProc(), clock, Flaky(clock))
    assert (result.outcome, result.attempts) == ("ready", 3)


def test_remaining_deadline_bounds_socket_timeout_and_sleep() -> None:
    clock = Clock()
    connect = Connect(clock, consume=True)  # a hanging connect uses its whole timeout
    result = wait(FakeProc(), clock, connect, timeout=1.25)
    # connect(1.0) leaves 0.25: the sleep is clamped to 0.25, not 0.5, and nothing runs after.
    assert connect.timeouts == [1.0] and clock.sleeps == [0.25]
    assert result.outcome == "deadline" and clock.now == pytest.approx(1001.25)


def test_short_deadline_shrinks_the_connect_timeout_itself() -> None:
    clock = Clock()
    connect = Connect(clock, consume=True)
    result = wait(FakeProc(), clock, connect, timeout=0.75)
    assert connect.timeouts == [0.75] and clock.sleeps == []
    assert result.outcome == "deadline" and clock.now == pytest.approx(1000.75)


def test_every_connect_and_sleep_fits_inside_the_remaining_time() -> None:
    clock = Clock()
    start = clock.now
    seen: list[tuple[float, float]] = []

    class Watch(Connect):
        def __call__(self, port: int, timeout: float) -> None:
            seen.append((timeout, (start + 7.3) - clock.now))
            super().__call__(port, timeout)

    connect = Watch(clock, consume=True)
    wait(FakeProc(), clock, connect, timeout=7.3)
    assert seen and all(0 < t <= remaining + 1e-9 and t <= 1.0 for t, remaining in seen)
    assert clock.now == pytest.approx(start + 7.3)
    assert all(s <= 0.5 for s in clock.sleeps)


def test_deadline_is_hard_and_never_slides_on_activity() -> None:
    clock = Clock()
    connect = Connect(clock, consume=True)
    result = wait(FakeProc(), clock, connect)
    assert clock.now == pytest.approx(1045.0)
    assert result.elapsed == pytest.approx(45.0)


# ---- the ceiling also binds a successful connect ----------------------------------------------


class SlowPoll(FakeProc):
    """A process whose post-connect `poll` is delayed (OS scheduling) by `delay` seconds."""

    def __init__(self, clock: Clock, *, delay: float, code_after: int | None = None) -> None:
        super().__init__()
        self.clock, self.delay, self.code_after = clock, delay, code_after

    def poll(self) -> int | None:
        code = super().poll()
        if self.polls == 2:  # the poll after the successful connect
            self.clock.now += self.delay
            self.code = self.code_after
            return self.code
        return code


def test_failed_connect_at_the_deadline_that_exits_the_process_is_process_exit() -> None:
    clock, proc = Clock(), FakeProc()

    def connect(port: int, timeout: float) -> None:
        clock.now += timeout  # the failing connect consumes all the remaining time ...
        proc.code = 7  # ... and the process exits meanwhile
        raise ConnectionRefusedError

    result = wait(proc, clock, connect, timeout=0.5)
    assert (result.outcome, result.exit_code, result.attempts) == ("process_exit", 7, 1)
    assert clock.sleeps == []


def test_failed_connect_at_the_deadline_with_a_live_process_is_deadline() -> None:
    clock, proc = Clock(), FakeProc()
    result = wait(proc, clock, Connect(clock, consume=True), timeout=0.5)
    assert (result.outcome, result.exit_code, result.attempts) == ("deadline", None, 1)
    assert clock.sleeps == []


def _connect_taking(clock: Clock, seconds: float) -> Connect:
    def advance() -> None:
        clock.now += seconds

    return Connect(clock, succeed_on=1, on_success=advance)


def test_connect_succeeding_just_before_the_deadline_is_ready() -> None:
    clock = Clock()
    result = wait(FakeProc(), clock, _connect_taking(clock, 0.49), timeout=0.5)
    assert (result.outcome, result.attempts) == ("ready", 1)
    assert result.elapsed == pytest.approx(0.49)


def test_connect_succeeding_exactly_at_the_deadline_is_deadline() -> None:
    clock = Clock()
    result = wait(FakeProc(), clock, _connect_taking(clock, 0.5), timeout=0.5)
    assert (result.outcome, result.exit_code, result.attempts) == ("deadline", None, 1)
    assert result.elapsed == pytest.approx(0.5)


def test_connect_succeeding_after_the_deadline_is_deadline() -> None:
    # The reproduced hole: timeout 0.5, the connector returns successfully after 0.6.
    clock = Clock()
    result = wait(FakeProc(), clock, _connect_taking(clock, 0.6), timeout=0.5)
    assert (result.outcome, result.exit_code, result.attempts) == ("deadline", None, 1)
    assert result.elapsed == pytest.approx(0.6)  # reported honestly, never as ready


def test_default_ceiling_also_binds_a_late_successful_connect() -> None:
    clock = Clock()

    def late(port: int, timeout: float) -> None:
        if clock.now < 1000.0 + 43.0:
            clock.now += timeout
            raise ConnectionRefusedError
        clock.now += 2.0  # a slow success that lands past the 45s ceiling

    result = wait(FakeProc(), clock, late)
    assert result.outcome == "deadline" and result.exit_code is None
    assert result.elapsed > 45.0


def test_delayed_post_connect_poll_past_the_deadline_is_deadline() -> None:
    clock = Clock()
    proc = SlowPoll(clock, delay=0.3)  # connect is instant; the poll after it is what is late
    result = wait(proc, clock, Connect(clock, succeed_on=1), timeout=0.25)
    assert result.outcome == "deadline" and result.exit_code is None
    assert result.elapsed == pytest.approx(0.3)


def test_delayed_post_connect_poll_within_the_deadline_is_ready() -> None:
    clock = Clock()
    proc = SlowPoll(clock, delay=0.2)
    result = wait(proc, clock, Connect(clock, succeed_on=1), timeout=0.25)
    assert result.outcome == "ready" and result.elapsed == pytest.approx(0.2)


def test_dead_process_keeps_precedence_over_a_late_success() -> None:
    clock = Clock()
    # The poll after the connect is both late (past the ceiling) and reports an exit code.
    proc = SlowPoll(clock, delay=1.0, code_after=6)
    result = wait(proc, clock, _connect_taking(clock, 1.0), timeout=0.5)
    assert (result.outcome, result.exit_code) == ("process_exit", 6)


def test_late_success_does_not_loop_again_or_sleep() -> None:
    clock = Clock()
    connect = _connect_taking(clock, 0.6)
    wait(FakeProc(), clock, connect, timeout=0.5)
    assert len(connect.timeouts) == 1 and clock.sleeps == []


def test_late_success_after_failures_is_still_deadline() -> None:
    clock = Clock()

    def flaky_then_late(port: int, timeout: float) -> None:
        attempts.append(timeout)
        if len(attempts) < 3:
            raise ConnectionRefusedError
        clock.now += 5.0

    attempts: list[float] = []
    result = wait(FakeProc(), clock, flaky_then_late, timeout=2.0)
    assert (result.outcome, result.attempts) == ("deadline", 3)


def test_connect_errors_stay_classified_not_ready_near_the_deadline() -> None:
    clock = Clock()
    connect = Connect(clock, consume=True, fail=TimeoutError())
    result = wait(FakeProc(), clock, connect, timeout=0.5)
    assert result.outcome == "deadline" and clock.now == pytest.approx(1000.5)


@pytest.mark.parametrize("phase", ["", "boot", "RESTART", "first_start "])
def test_unknown_phase_is_refused_before_anything_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    spawned: list[object] = []
    monkeypatch.setattr(dsf, "start_gateway", lambda *a, **k: spawned.append(1))
    clock = Clock()
    with pytest.raises(ValueError, match="phase"):
        dsf.require_native_listener(
            FakeProc(), 1, phase=phase, out_dir=tmp_path, log_path=_log(tmp_path),
            clock=clock, sleep=clock.sleep, connect=Connect(clock, succeed_on=1),
        )
    with pytest.raises(ValueError, match="phase"):
        dsf.start_native_gateway(
            SimpleNamespace(), SimpleNamespace(), port=1, phase=phase, log_path=tmp_path / "g"
        )
    assert spawned == [] and not (tmp_path / dsf.NATIVE_START_RECORD).exists()


@pytest.mark.parametrize("bad", [45.5, 300.0, -1.0, math.nan, math.inf])
def test_callers_cannot_widen_or_corrupt_the_deadline(bad: float) -> None:
    clock = Clock()
    connect = Connect(clock, succeed_on=1)
    with pytest.raises(ValueError, match="45"):
        wait(FakeProc(), clock, connect, timeout=bad)
    assert connect.timeouts == []


def test_default_deadline_is_the_historical_45_seconds() -> None:
    assert dsf.NATIVE_LISTENER_DEADLINE_SECONDS == 45.0


def test_a_zero_deadline_never_connects_but_still_reports_a_dead_process() -> None:
    clock = Clock()
    connect = Connect(clock, succeed_on=1)
    assert wait(FakeProc(), clock, connect, timeout=0).outcome == "deadline"
    assert connect.timeouts == []
    assert wait(FakeProc(code=2), clock, connect, timeout=0).outcome == "process_exit"


# ---- classified errors, artifact record, content-freedom ------------------------------------


def _read_records(out: Path) -> list[dict]:
    path = out / dsf.NATIVE_START_RECORD
    return [json.loads(line) for line in path.read_text().splitlines()]


def _log(tmp_path: Path, text: str = "gateway: starting\n") -> Path:
    log = tmp_path / "gateway.log"
    log.write_text(text)
    return log


def test_require_raises_classified_process_exit_and_records_it(tmp_path: Path) -> None:
    clock = Clock()
    proc = FakeProc(code=4)
    with pytest.raises(dsf.NativeProcessExitError) as err:
        dsf.require_native_listener(
            proc, 1, phase="restart", out_dir=tmp_path / "out", log_path=_log(tmp_path),
            clock=clock, sleep=clock.sleep, connect=Connect(clock, succeed_on=1),
        )
    assert err.value.classification == "process_exit"
    assert err.value.result.exit_code == 4
    assert "code 4" in str(err.value) and "gateway: starting" in str(err.value)  # local log tail
    assert _read_records(tmp_path / "out") == [
        {"phase": "restart", "outcome": "process_exit", "elapsed_seconds": 0.0,
         "attempts": 0, "exit_code": 4}
    ]


def test_require_raises_classified_deadline_and_records_it(tmp_path: Path) -> None:
    clock = Clock()
    with pytest.raises(dsf.NativeListenerDeadlineError) as err:
        dsf.require_native_listener(
            FakeProc(), 1, phase="first_start", out_dir=tmp_path, log_path=_log(tmp_path),
            clock=clock, sleep=clock.sleep, connect=Connect(clock, consume=True),
        )
    assert err.value.classification == "deadline"
    assert "within 45s" in str(err.value)
    (record,) = _read_records(tmp_path)
    assert record["outcome"] == "deadline" and record["exit_code"] is None
    assert record["elapsed_seconds"] == pytest.approx(45.0)


def test_require_returns_ready_and_records_elapsed(tmp_path: Path) -> None:
    clock = Clock()
    result = dsf.require_native_listener(
        FakeProc(), 1, phase="first_start", out_dir=tmp_path, log_path=_log(tmp_path),
        clock=clock, sleep=clock.sleep, connect=Connect(clock, succeed_on=2),
    )
    assert result.outcome == "ready"
    assert _read_records(tmp_path) == [
        {"phase": "first_start", "outcome": "ready", "elapsed_seconds": 0.5,
         "attempts": 2, "exit_code": None}
    ]


def test_record_holds_one_line_per_start_with_a_closed_key_set(tmp_path: Path) -> None:
    clock = Clock()
    for phase in ("first_start", "restart"):
        dsf.require_native_listener(
            FakeProc(), 1, phase=phase, out_dir=tmp_path, log_path=_log(tmp_path),
            clock=clock, sleep=clock.sleep, connect=Connect(clock, succeed_on=1),
        )
    records = _read_records(tmp_path)
    assert [r["phase"] for r in records] == ["first_start", "restart"]
    for record in records:
        assert set(record) == {"phase", "outcome", "elapsed_seconds", "attempts", "exit_code"}


def test_nothing_from_the_process_object_reaches_errors_or_records(tmp_path: Path) -> None:
    clock = Clock()
    proc = FakeProc(code=9)
    with pytest.raises(dsf.NativeProcessExitError) as err:
        dsf.require_native_listener(
            proc, 1, phase="restart", out_dir=tmp_path, log_path=_log(tmp_path),
            clock=clock, sleep=clock.sleep, connect=Connect(clock),
        )
    assert SECRETISH not in str(err.value) and "hermes" not in str(err.value)
    assert SECRETISH not in (tmp_path / dsf.NATIVE_START_RECORD).read_text()
    assert SECRETISH not in repr(err.value.result)


def test_only_the_existing_local_log_tail_is_emitted(tmp_path: Path) -> None:
    clock = Clock()
    log = _log(tmp_path, "x" * 10_000 + "TAIL-MARKER\n")
    with pytest.raises(dsf.NativeProcessExitError) as err:
        dsf.require_native_listener(
            FakeProc(code=1), 1, phase="first_start", out_dir=tmp_path, log_path=log,
            clock=clock, sleep=clock.sleep, connect=Connect(clock),
        )
    assert "TAIL-MARKER" in str(err.value)
    assert len(str(err.value)) < 4500  # the same 4000-char tail bound as before
    assert "TAIL-MARKER" not in (tmp_path / dsf.NATIVE_START_RECORD).read_text()


# ---- start_native_gateway cleanup -----------------------------------------------------------


class _Spawned(FakeProc):
    def __init__(self, code: int | None) -> None:
        super().__init__(code)
        self.stopped = False


def _patch_spawn(
    monkeypatch: pytest.MonkeyPatch, proc: _Spawned, *, make_log: bool = True
) -> list[object]:
    """Stubs only the OS boundary (spawn/stop); like the real `start_gateway` it creates the log
    (unless `make_log` is False, to model a log that is missing on the failure path)."""
    stopped: list[object] = []

    def fake_start(build, paths, *, log_path):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if make_log:
            log_path.write_text("gateway: boot\n")
        return proc

    monkeypatch.setattr(dsf, "start_gateway", fake_start)
    monkeypatch.setattr(dsf, "stop_gateway", stopped.append)
    return stopped


def test_failed_native_start_stops_the_spawned_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proc = _Spawned(code=2)
    stopped = _patch_spawn(monkeypatch, proc)
    paths = fc.instance_paths(tmp_path / "fixture", "A")
    with pytest.raises(dsf.NativeProcessExitError):
        dsf.start_native_gateway(
            SimpleNamespace(), paths, port=1, phase="first_start", log_path=tmp_path / "g.log"
        )
    assert stopped == [proc]


def test_interrupt_during_the_wait_still_stops_the_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proc = _Spawned(code=None)
    stopped = _patch_spawn(monkeypatch, proc)

    def interrupted(port: int, timeout: float) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(dsf, "_connect_loopback", interrupted)
    paths = fc.instance_paths(tmp_path / "fixture", "A")
    with pytest.raises(KeyboardInterrupt):
        dsf.start_native_gateway(
            SimpleNamespace(), paths, port=1, phase="restart", log_path=tmp_path / "g.log"
        )
    assert stopped == [proc]


def test_record_write_error_on_ready_stops_the_process_and_returns_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proc = _Spawned(code=None)
    stopped = _patch_spawn(monkeypatch, proc)

    def failing_record(out_dir, phase, result) -> None:
        assert result.outcome == "ready"  # the write is attempted before anything is returned
        raise OSError("disk full")

    monkeypatch.setattr(dsf, "record_native_start", failing_record)
    paths = fc.instance_paths(tmp_path / "fixture", "A")
    got = None
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        with pytest.raises(OSError, match="disk full"):
            got = dsf.start_native_gateway(
                SimpleNamespace(), paths, port=listener.getsockname()[1],
                phase="first_start", log_path=tmp_path / "g.log",
            )
    assert got is None and stopped == [proc]


@pytest.mark.parametrize(
    ("code", "outcome"), [(3, "process_exit"), (None, "deadline")]
)
def test_missing_log_on_failure_keeps_the_record_stops_the_process_and_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int | None, outcome: str
) -> None:
    proc = _Spawned(code=code)
    stopped = _patch_spawn(monkeypatch, proc, make_log=False)
    real_wait = dsf.wait_for_native_listener
    monkeypatch.setattr(  # a live process never listens; shorten only (never widen) the wait
        dsf, "wait_for_native_listener",
        lambda p, port, **kw: real_wait(p, port, **{**kw, "timeout": 0.0}),
    )
    paths = fc.instance_paths(tmp_path / "fixture", "A")
    log_path = tmp_path / "g.log"
    got = None
    with pytest.raises(FileNotFoundError):
        got = dsf.start_native_gateway(
            SimpleNamespace(), paths, port=1, phase="restart", log_path=log_path
        )
    assert got is None and stopped == [proc] and not log_path.exists()
    records = _read_records(paths.out_dir)  # written before the log tail was read
    assert [(r["phase"], r["outcome"]) for r in records] == [("restart", outcome)]


def test_successful_native_start_returns_the_live_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proc = _Spawned(code=None)
    stopped = _patch_spawn(monkeypatch, proc)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        paths = fc.instance_paths(tmp_path / "fixture", "A")
        got = dsf.start_native_gateway(
            SimpleNamespace(), paths, port=port, phase="first_start", log_path=tmp_path / "g.log"
        )
    assert got is proc and stopped == []
    assert _read_records(paths.out_dir)[0]["outcome"] == "ready"


# ---- both fixture paths use the helper (real integration-module code, stubbed boundaries) ----


def _load_integration(monkeypatch: pytest.MonkeyPatch):
    spec = importlib.util.spec_from_file_location("hmp_f2_fixture_under_test", INTEGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)  # scoped to the calling test
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def unrelated_listener():
    """A listener owned by this test, unrelated to any spawned gateway."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        yield s.getsockname()[1]


def test_restart_path_refuses_a_dead_gateway_even_with_a_listener_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unrelated_listener: int
) -> None:
    f2 = _load_integration(monkeypatch)
    dead = _Spawned(code=11)
    old = _Spawned(code=0)
    calls = _patch_spawn(monkeypatch, dead)
    paths = fc.instance_paths(tmp_path / "fixture", "A")
    paths.out_dir.mkdir(parents=True, exist_ok=True)
    gw = f2.DirectSendFixture.__new__(f2.DirectSendFixture)
    gw.build, gw.paths, gw.hmp_port, gw.gateway_proc = None, paths, unrelated_listener, old
    t0 = time.monotonic()
    with pytest.raises(dsf.NativeProcessExitError):
        gw.restart_gateway()
    assert time.monotonic() - t0 < 5  # immediate, not a 45s wait
    assert calls == [old, dead]  # old stopped first, then the failed new process
    assert gw.gateway_proc is old  # never replaced by a process that did not reach readiness
    (record,) = _read_records(paths.out_dir)
    assert (record["phase"], record["outcome"], record["exit_code"]) == (
        "restart", "process_exit", 11
    )


def test_first_start_path_refuses_a_dead_gateway_even_with_a_listener_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unrelated_listener: int
) -> None:
    f2 = _load_integration(monkeypatch)
    dead = _Spawned(code=12)
    model = SimpleNamespace(base_url="http://127.0.0.1:1", started=False, stopped=False)
    model.start = lambda: setattr(model, "started", True)
    model.stop = lambda: setattr(model, "stopped", True)
    provider = SimpleNamespace(FakeLLMServer=lambda default_text: model)
    profiles = [{"name": "f1-alpha", "user_id": "u"}]
    build = SimpleNamespace(label="stock-base")
    monkeypatch.setattr(fc, "resolve_build", lambda *a, **k: build)
    monkeypatch.setattr(fc, "find_free_port", lambda: unrelated_listener)
    info = {"instances": [{"profiles": profiles}]}
    monkeypatch.setattr(dsf, "build_offline", lambda *a, **k: info)
    monkeypatch.setattr(dsf, "load_fake_llm_provider", lambda build: provider)
    monkeypatch.setattr(dsf, "write_direct_send_config", lambda *a, **k: None)
    stopped = _patch_spawn(monkeypatch, dead)
    monkeypatch.setattr(f2, "BUILDS_DIR_ENV", str(tmp_path))
    request = SimpleNamespace(param="stock-base")
    gen = f2.gateway.__wrapped__(request, tmp_path)
    with pytest.raises(dsf.NativeProcessExitError):
        next(gen)
    assert stopped == [dead] and model.started and model.stopped
    record = _read_records(tmp_path / "fixture")[0]
    assert (record["phase"], record["outcome"], record["exit_code"]) == (
        "first_start", "process_exit", 12
    )


# ---- real spawned synthetic loopback processes ----------------------------------------------

_SERVER = (
    "import socket, sys, time\n"
    "time.sleep(float(sys.argv[2]))\n"
    "s = socket.socket(); s.bind(('127.0.0.1', int(sys.argv[1]))); s.listen()\n"
    "time.sleep(60)\n"
)


def _spawn(code: str, *args: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-c", code, *args],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


@pytest.fixture
def reaper():
    procs: list[subprocess.Popen[bytes]] = []
    yield procs.append
    for proc in procs:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)


def test_real_live_server_becomes_ready_after_a_delayed_bind(reaper) -> None:
    port = fc.find_free_port()
    proc = _spawn(_SERVER, str(port), "0.5")
    reaper(proc)
    result = dsf.wait_for_native_listener(proc, port)
    assert result.outcome == "ready" and result.exit_code is None
    assert result.attempts >= 1 and 0 < result.elapsed < 30


def test_real_already_exited_process_cannot_qualify_an_unrelated_listener(
    reaper, unrelated_listener: int
) -> None:
    proc = _spawn("raise SystemExit(5)")
    reaper(proc)
    proc.wait(timeout=30)
    # The unrelated listener accepts a connect, yet the exact spawned process is gone.
    with socket.create_connection(("127.0.0.1", unrelated_listener), timeout=2):
        pass
    result = dsf.wait_for_native_listener(proc, unrelated_listener)
    assert (result.outcome, result.exit_code, result.attempts) == ("process_exit", 5, 0)


def test_real_live_process_that_never_listens_hits_the_deadline_without_overrun(reaper) -> None:
    port = fc.find_free_port()  # nothing will listen here
    proc = _spawn("import time; time.sleep(60)")
    reaper(proc)
    start = time.monotonic()
    result = dsf.wait_for_native_listener(proc, port, timeout=1.0)
    wall = time.monotonic() - start
    assert result.outcome == "deadline"
    # Requested waits are clamped to the time left, so no extra 1 s connect or 0.5 s sleep is
    # requested. The hard-deadline proof is the injected-clock tests; this bound only leaves
    # scheduler slack and is not a wall-clock guarantee.
    assert 1.0 <= wall < 1.0 + 1.0
    assert result.elapsed <= wall + 0.05


def test_real_process_exiting_while_unreachable_is_reported_promptly(reaper) -> None:
    port = fc.find_free_port()
    proc = _spawn("import time; time.sleep(0.6)")
    reaper(proc)
    start = time.monotonic()
    result = dsf.wait_for_native_listener(proc, port, timeout=20.0)
    assert result.outcome == "process_exit" and result.exit_code == 0
    assert time.monotonic() - start < 10


def test_legacy_wait_for_port_is_unchanged(unrelated_listener: int) -> None:
    assert dsf.wait_for_port(unrelated_listener, timeout=2.0) is True
    closed = fc.find_free_port()
    assert dsf.wait_for_port(closed, timeout=0.0) is False
