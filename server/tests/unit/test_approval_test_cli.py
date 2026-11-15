"""AT1 fake transport/stdio only; no sockets/native/home/metadata/permission effects.

Prepared source only. This file has not been imported, parsed or executed by its author.
"""

from __future__ import annotations

import argparse
import asyncio
import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from hmp_plugin import approval_test_cli as at1
from hmp_plugin import cli
from hmp_plugin.approval_test_host_codec import (
    HostBeginRequest,
    HostGeneration,
    HostOperationRequest,
    HostResponse,
)

IID = "a" * 52
OPERATION = "1" * 32
RECORD = Path("/synthetic/listener.json")
PRIVATE = "PRIVATE_SELECTOR_PATH_EXCEPTION_MARKER"


class Stdio(io.StringIO):
    def __init__(self, tty: bool = True):
        super().__init__()
        self.tty = tty

    def isatty(self):
        return self.tty


def generation(**changes):
    return HostGeneration(changes.get("iid", IID), changes.get("pid", 7),
                          changes.get("nonce", "0" * 32))


def binding(read=None):
    return at1.ListenerBinding(RECORD, generation(), read or generation)


def begin():
    return HostBeginRequest(generation(), PRIVATE, "synthetic-profile", "synthetic-session")


async def run(request, fake, *, bound=None, interrupts=None):
    out = Stdio()
    code = await at1.run_command(bound or binding(), request, out, exchange=fake,
                                 interrupts=interrupts, install_signals=False)
    assert PRIVATE not in out.getvalue()
    assert len(out.getvalue()) <= at1.OUTPUT_CAP
    return code, out.getvalue()


@pytest.mark.asyncio
@pytest.mark.parametrize("state,expected", [
    ("once_acknowledged", 0), ("denied", 0), ("cancelled", 0),
    ("expired", 0), ("unavailable", 1),
])
async def test_begin_requires_completed_same_id_and_clean_iterator_end(state, expected):
    calls = []

    async def fake(record, request):
        calls.append((record, request))
        yield HostResponse("accepted", OPERATION, timeout_ms=30000)
        yield HostResponse("completed", OPERATION, state=state)

    code, out = await run(begin(), fake)
    assert code == expected
    assert len(calls) == 1 and calls[0][0] == RECORD
    assert "accepted; completion pending" in out
    assert f"joined {state}" in out
    assert "executed" not in out


@pytest.mark.asyncio
async def test_accepted_alone_is_uncertain_retains_only_operation_id_no_retry():
    calls = []

    async def fake(record, request):
        calls.append(request)
        yield HostResponse("accepted", OPERATION, timeout_ms=30000)

    code, out = await run(begin(), fake)
    assert code == 2 and len(calls) == 1
    assert OPERATION in out and "do not resubmit begin" in out
    assert "joined" not in out


@pytest.mark.asyncio
@pytest.mark.parametrize("after_accept", [False, True])
async def test_transport_loss_never_echoes_error_or_retries_begin(after_accept):
    calls = []

    async def fake(record, request):
        calls.append(request)
        if after_accept:
            yield HostResponse("accepted", OPERATION, timeout_ms=30000)
        raise OSError(PRIVATE)

    code, out = await run(begin(), fake)
    assert code == 2 and len(calls) == 1 and "joined" not in out
    assert (OPERATION in out) is after_accept


@pytest.mark.asyncio
async def test_unavailable_is_refusal_only_after_clean_end():
    async def fake(record, request):
        yield HostResponse("unavailable")

    code, out = await run(begin(), fake)
    assert code == 1 and out == "Approval test unavailable.\n"


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", ["wrong_id", "duplicate", "after_completed", "finalizer"])
async def test_bad_order_id_or_finalizer_never_prints_joined(variant):
    async def fake(record, request):
        try:
            yield HostResponse("accepted", OPERATION, timeout_ms=30000)
            if variant == "duplicate":
                yield HostResponse("accepted", OPERATION, timeout_ms=30000)
            else:
                yield HostResponse("completed", "2" * 32 if variant == "wrong_id" else OPERATION,
                                   state="denied")
                if variant == "after_completed":
                    yield HostResponse("unavailable")
        finally:
            if variant == "finalizer":
                raise OSError(PRIVATE)

    code, out = await run(begin(), fake)
    assert code == 2 and "joined" not in out


@pytest.mark.asyncio
@pytest.mark.parametrize("state,expected", [
    ("pending", 2), ("cleanup_pending", 2), ("once_acknowledged", 0),
    ("denied", 0), ("cancelled", 0), ("expired", 0), ("unavailable", 1),
])
async def test_status_exit_tracks_joined_retained_terminal_not_pending(state, expected):
    async def fake(record, request):
        assert type(request) is HostOperationRequest and request.op == "status"
        yield HostResponse("status", OPERATION, state=state, remaining_ms=0)

    code, out = await run(HostOperationRequest(generation(), "status", OPERATION), fake)
    assert code == expected and OPERATION in out


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["pending", "cancelled", "cleanup_pending"])
async def test_cancel_receipt_never_claims_joined_cleanup(state):
    async def fake(record, request):
        yield HostResponse("cancel_requested", OPERATION, state=state)

    code, out = await run(HostOperationRequest(generation(), "cancel", OPERATION), fake)
    assert code == 2 and "cancel requested" in out and "joined" not in out


@pytest.mark.asyncio
async def test_generation_reread_changed_refuses_before_exchange():
    calls = []

    async def fake(record, request):
        calls.append(request)
        yield HostResponse("unavailable")

    code, _out = await run(begin(), fake, bound=binding(lambda: generation(nonce="2" * 32)))
    assert code == 2 and calls == []


@pytest.mark.asyncio
async def test_status_total_exchange_is_bounded(monkeypatch):
    monkeypatch.setattr(at1, "CONTROL_SECONDS", 0.01)

    async def fake(record, request):
        await asyncio.Event().wait()
        yield HostResponse("unavailable")

    code, out = await run(HostOperationRequest(generation(), "status", OPERATION), fake)
    assert code == 2 and "unconfirmed" in out


@pytest.mark.asyncio
@pytest.mark.parametrize("interrupt_before_accept", [False, True])
async def test_first_interrupt_sends_separate_typed_cancel_retaining_begin(interrupt_before_accept):
    state = at1.Interrupts()
    started, allow_accept, accepted = asyncio.Event(), asyncio.Event(), asyncio.Event()
    terminal, begin_closed, cancel_seen = asyncio.Event(), asyncio.Event(), asyncio.Event()
    calls = []

    async def fake(record, request):
        calls.append(request)
        if type(request) is HostBeginRequest:
            try:
                started.set()
                await allow_accept.wait()
                yield HostResponse("accepted", OPERATION, timeout_ms=30000)
                accepted.set()
                await terminal.wait()
                yield HostResponse("completed", OPERATION, state="cancelled")
            finally:
                begin_closed.set()
        else:
            assert request.op == "cancel" and request.operation_id == OPERATION
            assert request.generation == generation() and not begin_closed.is_set()
            cancel_seen.set()
            yield HostResponse("cancel_requested", OPERATION, state="cleanup_pending")
            terminal.set()

    task = asyncio.create_task(run(begin(), fake, interrupts=state))
    await started.wait()
    if interrupt_before_accept:
        state.interrupt()
    allow_accept.set()
    await accepted.wait()
    if not interrupt_before_accept:
        state.interrupt()
    await cancel_seen.wait()
    code, out = await task
    assert code == 130 and len(calls) == 2
    assert "Cancel requested; awaiting joined completion" in out
    assert "joined cancelled" in out and begin_closed.is_set()


@pytest.mark.asyncio
async def test_second_interrupt_abandons_observation_without_claiming_cleanup():
    state = at1.Interrupts()
    accepted, cancel_started, closed = asyncio.Event(), asyncio.Event(), asyncio.Event()
    calls = []

    async def fake(record, request):
        calls.append(request)
        if type(request) is HostBeginRequest:
            try:
                yield HostResponse("accepted", OPERATION, timeout_ms=30000)
                accepted.set()
                await asyncio.Event().wait()
            finally:
                closed.set()
        else:
            cancel_started.set()
            await asyncio.Event().wait()
            yield HostResponse("cancel_requested", OPERATION, state="pending")

    task = asyncio.create_task(run(begin(), fake, interrupts=state))
    await accepted.wait()
    state.interrupt()
    await cancel_started.wait()
    state.interrupt()
    code, out = await task
    assert code == 130 and closed.is_set() and len(calls) == 2
    assert "joined" not in out and "Cancel requested" not in out
    assert "host cleanup is not confirmed" in out


@pytest.mark.asyncio
async def test_cancel_delivery_failure_keeps_begin_draining_until_real_terminal():
    state = at1.Interrupts()
    accepted, cancel_failed, terminal = asyncio.Event(), asyncio.Event(), asyncio.Event()
    calls = []

    async def fake(record, request):
        calls.append(request)
        if type(request) is HostBeginRequest:
            yield HostResponse("accepted", OPERATION, timeout_ms=30000)
            accepted.set()
            await terminal.wait()
            yield HostResponse("completed", OPERATION, state="expired")
        else:
            cancel_failed.set()
            raise OSError(PRIVATE)

    task = asyncio.create_task(run(begin(), fake, interrupts=state))
    await accepted.wait()
    state.interrupt()
    await cancel_failed.wait()
    assert not task.done()
    terminal.set()
    code, out = await task
    assert code == 130 and len(calls) == 2
    assert "Cancel delivery unconfirmed" in out and "joined expired" in out


@pytest.mark.asyncio
async def test_cancel_generation_change_never_targets_new_listener():
    state = at1.Interrupts()
    accepted, terminal, reread_cancel = asyncio.Event(), asyncio.Event(), asyncio.Event()
    calls, reads = [], []

    def reread():
        reads.append(True)
        if len(reads) == 2:
            reread_cancel.set()
            return generation(nonce="2" * 32)
        return generation()

    async def fake(record, request):
        calls.append(request)
        yield HostResponse("accepted", OPERATION, timeout_ms=30000)
        accepted.set()
        await terminal.wait()
        yield HostResponse("completed", OPERATION, state="expired")

    task = asyncio.create_task(run(begin(), fake, bound=binding(reread), interrupts=state))
    await accepted.wait()
    state.interrupt()
    await reread_cancel.wait()
    terminal.set()
    code, out = await task
    assert code == 130 and len(calls) == 1 and "Cancel delivery unconfirmed" in out


def namespace(argv):
    parser = argparse.ArgumentParser()
    cli.setup_parser(parser)
    return parser.parse_args(argv)


def env(*, tty=True, environ=None):
    def forbidden(*args, **kwargs):
        raise AssertionError("prohibited diagnostic/native/subprocess port")
    return cli.CliEnv(stdin=Stdio(tty), stdout=Stdio(tty), stderr=Stdio(),
                      environ={} if environ is None else environ,
                      compat=forbidden, verify_listener_live=forbidden,
                      hermes_executable=forbidden, run_hermes_cli=forbidden)


@pytest.mark.parametrize("argv,action", [
    (["approval-test", "begin", "--device", PRIVATE, "--profile", "selected-target",
      "--session", "tip"], "begin"),
    (["approval-test", "status", OPERATION], "status"),
    (["approval-test", "cancel", OPERATION], "cancel"),
])
def test_parser_classifies_exact_group_target_profile_and_mutation_guards(argv, action):
    args = namespace(argv)
    assert cli._command(args) == ("approval-test", action)
    assert (("approval-test", action) in cli.MUTATING_COMMANDS) is (action != "status")
    if action == "begin":
        assert args.target_profile == "selected-target" and args.timeout_ms == 30000
        assert not hasattr(args, "profile")


@pytest.mark.parametrize("action", ["begin", "cancel"])
@pytest.mark.parametrize("tty,session_env", [(False, {}), (True, {"HERMES_SESSION_ANY": ""})])
def test_mutation_refuses_before_binding_and_without_echo(monkeypatch, action, tty, session_env):
    def forbidden(*args):
        raise AssertionError("binding must not run after mutation guard refusal")
    monkeypatch.setattr(cli, "_approval_test_binding", forbidden)
    args = namespace(["approval-test", action, OPERATION] if action == "cancel" else
                     ["approval-test", action, "--device", PRIVATE, "--profile", "p",
                      "--session", "s"])
    runtime = env(tty=tty, environ=session_env)
    assert cli.dispatch(args, runtime) == 1
    assert runtime.stdout.getvalue() == "Approval test unavailable.\n"


def test_status_dispatch_uses_no_store_or_probe_and_allows_non_tty_session(monkeypatch):
    seen = []
    monkeypatch.setattr(cli, "_approval_test_binding", lambda runtime: binding())
    monkeypatch.setattr(cli, "_open", lambda *a, **kw: pytest.fail("writable store"))
    monkeypatch.setattr(cli, "_checked_setup", lambda *a: pytest.fail("setup diagnostic"))

    async def fake(bound, request, out):
        seen.append(request)
        return 0
    monkeypatch.setattr(at1, "run_command", fake)
    runtime = env(tty=False, environ={"HERMES_SESSION_ANY": ""})
    assert cli.dispatch(namespace(["approval-test", "status", OPERATION]), runtime) == 0
    assert len(seen) == 1 and seen[0].op == "status"
    assert runtime.stdout.getvalue() == runtime.stderr.getvalue() == ""


def test_preflight_exception_is_fixed_environment_output(monkeypatch):
    def fail(runtime):
        raise OSError(PRIVATE)
    monkeypatch.setattr(cli, "_approval_test_binding", fail)
    runtime = env()
    assert cli.dispatch(namespace(["approval-test", "status", OPERATION]), runtime) == 2
    assert PRIVATE not in runtime.stdout.getvalue() and runtime.stderr.getvalue() == ""


@pytest.mark.parametrize("timeout", ["0", "60001"])
def test_invalid_timeout_refuses_without_transport_or_selector_output(monkeypatch, timeout):
    monkeypatch.setattr(cli, "_approval_test_binding", lambda runtime: binding())

    async def forbidden(*args):
        pytest.fail("invalid selector must not reach transport")
    monkeypatch.setattr(at1, "run_command", forbidden)
    runtime = env()
    args = namespace(["approval-test", "begin", "--device", PRIVATE, "--profile", "p",
                      "--session", "s", "--timeout-ms", timeout])
    assert cli.dispatch(args, runtime) == 2 and PRIVATE not in runtime.stdout.getvalue()


def test_existing_commands_classification_is_preserved():
    for argv, expected in [(["pair", "list"], ("pair", "list")),
                           (["devices", "list"], ("devices", "list")),
                           (["setup", "check"], ("setup", "check")),
                           (["health", "check"], ("health", "check")),
                           (["push", "status"], ("push", "status")),
                           (["compat"], ("compat", None))]:
        assert cli._command(namespace(argv)) == expected


def test_real_sigint_handler_is_scoped_restored_and_does_not_raise(monkeypatch):
    captured, previous = [], object()
    monkeypatch.setattr(at1.signal, "getsignal", lambda signum: previous)
    monkeypatch.setattr(at1.signal, "signal", lambda signum, handler: captured.append(handler))
    callbacks = []
    loop = SimpleNamespace(call_soon_threadsafe=lambda callback: callbacks.append(callback))
    monkeypatch.setattr(at1.asyncio, "get_running_loop", lambda: loop)
    state = at1.Interrupts()
    with at1._operator_signals(state):
        captured[0](at1.signal.SIGINT, None)
        assert state.count == 0
        callbacks.pop()()
        assert state.count == 1
    assert captured[-1] is previous


def test_binding_reuses_only_load_existing_epoch_and_record_primitives(monkeypatch):
    import hmp_plugin

    calls = []
    anchor = Path("/synthetic/hmp/instance")
    store = SimpleNamespace(is_file=lambda: True,
                            with_name=lambda name: SimpleNamespace(exists=lambda: False),
                            name="hmp.sqlite3")
    fake_identity = SimpleNamespace(
        resolve_custody=lambda **kw: SimpleNamespace(anchor_dir=anchor),
        load_existing=lambda epoch, **kw: calls.append((epoch, kw)) or SimpleNamespace(iid=IID),
    )
    monkeypatch.setattr(hmp_plugin, "identity", fake_identity, raising=False)
    monkeypatch.setattr(hmp_plugin, "server", SimpleNamespace(store_path=lambda path: store),
                        raising=False)
    monkeypatch.setattr(cli, "_ReadOnlyEpoch", lambda path: ("readonly-epoch", path))
    records = []

    def record(path, *, iid, pid_alive):
        records.append((path, iid))
        return cli.ListenerRecord("127.0.0.1", 1, IID, 7, "0" * 32)
    monkeypatch.setattr(cli, "read_listener_record", record)
    bound = cli._approval_test_binding(env())
    assert calls == [(("readonly-epoch", store), {})]
    assert bound.generation == generation()
    bound.check()
    assert len(records) == 2 and records[0] == records[1]


@pytest.mark.parametrize("field,value", [("pid", True), ("nonce", "opaque-old-record"),
                                          ("iid", "not-canonical")])
def test_record_validated_again_by_typed_generation(monkeypatch, field, value):
    import hmp_plugin

    anchor = Path("/synthetic/hmp/instance")
    store = SimpleNamespace(is_file=lambda: True,
                            with_name=lambda name: SimpleNamespace(exists=lambda: False),
                            name="hmp.sqlite3")
    monkeypatch.setattr(hmp_plugin, "identity", SimpleNamespace(
        resolve_custody=lambda **kw: SimpleNamespace(anchor_dir=anchor),
        load_existing=lambda epoch, **kw: SimpleNamespace(iid=IID)), raising=False)
    monkeypatch.setattr(hmp_plugin, "server", SimpleNamespace(store_path=lambda path: store),
                        raising=False)
    monkeypatch.setattr(cli, "_ReadOnlyEpoch", lambda path: object())
    raw = {"host": "127.0.0.1", "port": 1, "iid": IID, "pid": 7, "nonce": "0" * 32}
    raw[field] = value
    monkeypatch.setattr(cli, "read_listener_record", lambda *a, **kw: cli.ListenerRecord(**raw))
    runtime = env()
    assert cli.dispatch(namespace(["approval-test", "status", OPERATION]), runtime) == 2
    assert PRIVATE not in runtime.stdout.getvalue()


def test_missing_wal_shared_sidecar_refuses_before_epoch_or_identity_load(monkeypatch):
    import hmp_plugin

    anchor = Path("/synthetic/hmp/instance")
    store = SimpleNamespace(is_file=lambda: True, name="hmp.sqlite3",
                            with_name=lambda name: SimpleNamespace(
                                exists=lambda: name.endswith("-wal")))
    def forbidden(*a, **kw):
        pytest.fail("no identity or SQLite read while read-only sidecar custody fails")
    monkeypatch.setattr(hmp_plugin, "identity", SimpleNamespace(
        resolve_custody=lambda **kw: SimpleNamespace(anchor_dir=anchor),
        load_existing=forbidden), raising=False)
    monkeypatch.setattr(hmp_plugin, "server", SimpleNamespace(store_path=lambda path: store),
                        raising=False)
    monkeypatch.setattr(cli, "_ReadOnlyEpoch", forbidden)
    runtime = env()
    assert cli.dispatch(namespace(["approval-test", "status", OPERATION]), runtime) == 2


@pytest.mark.asyncio
async def test_interrupt_before_any_begin_reply_does_not_guess_id_or_retry():
    state = at1.Interrupts()
    started, failed = asyncio.Event(), asyncio.Event()
    calls = []

    async def fake(record, request):
        calls.append(request)
        started.set()
        await failed.wait()
        raise OSError(PRIVATE)
        yield HostResponse("unavailable")

    task = asyncio.create_task(run(begin(), fake, interrupts=state))
    await started.wait()
    state.interrupt()
    failed.set()
    code, out = await task
    assert code == 130 and len(calls) == 1
    assert OPERATION not in out and "joined" not in out and "Cancel requested" not in out


def test_timeout_parser_error_does_not_echo_private_token(capsys):
    with pytest.raises(SystemExit) as caught:
        namespace(["approval-test", "begin", "--device", "d", "--profile", "p",
                   "--session", "s", "--timeout-ms", PRIVATE])
    assert caught.value.code == 2
    assert PRIVATE not in capsys.readouterr().err


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_created_before_loss", [False, True])
async def test_first_interrupt_after_accepted_loss_still_attempts_one_cancel(
    monkeypatch, cancel_created_before_loss,
):
    state = at1.Interrupts()
    accepted, fail, cancel_entered, release_cancel = (
        asyncio.Event(), asyncio.Event(), asyncio.Event(), asyncio.Event()
    )
    calls, observations = [], []
    observer_finished = asyncio.Event()
    original_cancel = at1._interrupt_cancel
    original_observe = at1._observe

    async def observe_finished(*args):
        result = await original_observe(*args)
        observer_finished.set()
        return result

    async def delayed_cancel(bound, observation, exchange, output):
        observations.append(observation)
        cancel_entered.set()
        await release_cancel.wait()
        # Causal ordering: local observation has ended without a joined receipt.
        assert observation.finished and not observation.joined
        await original_cancel(bound, observation, exchange, output)

    if cancel_created_before_loss:
        monkeypatch.setattr(at1, "_interrupt_cancel", delayed_cancel)
        monkeypatch.setattr(at1, "_observe", observe_finished)

    async def fake(record, request):
        calls.append(request)
        if type(request) is HostBeginRequest:
            yield HostResponse("accepted", OPERATION, timeout_ms=30000)
            accepted.set()
            if cancel_created_before_loss:
                await fail.wait()
            else:
                # Both first interrupt and failed observer are ready before the
                # controller gets another turn.
                state.interrupt()
            raise OSError(PRIVATE)
        assert request.op == "cancel" and request.operation_id == OPERATION
        assert request.generation == generation()
        yield HostResponse("cancel_requested", OPERATION, state="cleanup_pending")

    task = asyncio.create_task(run(begin(), fake, interrupts=state))
    if cancel_created_before_loss:
        await accepted.wait()
        state.interrupt()
        await cancel_entered.wait()
        fail.set()
        # The real observer has returned through its finalizer; this event does
        # not manufacture a native completion or alter that observer's result.
        await observer_finished.wait()
        release_cancel.set()
    code, out = await task
    assert code == 130 and len(calls) == 2
    assert type(calls[0]) is HostBeginRequest
    assert type(calls[1]) is HostOperationRequest
    assert "Cancel requested; awaiting joined completion" in out
    assert "joined" not in out.replace("awaiting joined completion", "")
    assert "do not resubmit begin" in out
