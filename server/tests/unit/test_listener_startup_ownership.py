"""Synthetic runner/site stage ownership; real TLS behavior remains in test_server."""

import asyncio
from types import SimpleNamespace

import pytest

from hmp_plugin import server


def rig(monkeypatch, *, setup_error=False, cleanup_error=False, block_site=False):
    events = []
    site_entered, site_release = asyncio.Event(), asyncio.Event()
    if not block_site:
        site_release.set()

    class Runner:
        async def setup(self):
            events.append("setup")
            if setup_error:
                raise OSError("synthetic setup failure")

        async def cleanup(self):
            events.append("cleanup")
            if cleanup_error:
                raise OSError("synthetic cleanup acknowledgement loss")

    runner = Runner()

    class Site:
        def __init__(self, original_runner, *_args, **_kwargs):
            assert original_runner is runner
            self._server = SimpleNamespace(sockets=[])

        async def start(self):
            events.append("site-entered")
            site_entered.set()
            await site_release.wait()
            events.append("site-returned")

    ctx = SimpleNamespace(
        identity=object(), push_hints=SimpleNamespace(clear=lambda: None), direct_send_deps=None
    )
    listener = server.HmpServer(ctx, server.ListenerSettings("127.0.0.1", 12345))
    monkeypatch.setattr(server, "server_ssl_context", lambda *_args: None)
    monkeypatch.setattr(server, "build_app", lambda _ctx: object())
    monkeypatch.setattr(server, "_HmpAppRunner", lambda *_args, **_kwargs: runner)
    monkeypatch.setattr(server.web, "TCPSite", Site)

    async def no_op():
        return None

    async def idle():
        await asyncio.Event().wait()

    monkeypatch.setattr(listener, "_purge_push_once", no_op)
    monkeypatch.setattr(listener, "_start_push_dispatcher", no_op)
    monkeypatch.setattr(listener, "_watchdog", idle)
    monkeypatch.setattr(listener, "_push_purge_loop", idle)
    return listener, runner, events, site_entered, site_release


def test_setup_failure_retains_runner_until_explicit_actual_stop(monkeypatch):
    async def scenario():
        listener, runner, events, _, _ = rig(monkeypatch, setup_error=True)
        with pytest.raises(RuntimeError, match="startup incomplete"):
            await listener.start()
        assert listener._runner is runner and listener._start_runner is runner
        assert events == ["setup"] and not listener.closed.is_set()
        await listener.stop()
        assert events == ["setup", "cleanup"] and listener.closed.is_set()
        await listener.stop()
        assert events.count("cleanup") == 1

    asyncio.run(scenario())


def test_cancelled_start_waiter_and_stop_keep_actual_site_owner_until_it_returns(monkeypatch):
    async def scenario():
        listener, runner, events, entered, release = rig(monkeypatch, block_site=True)
        caller = asyncio.create_task(listener.start())
        stop = None
        try:
            await entered.wait()
            original = listener._start_owner
            caller.cancel()
            with pytest.raises(asyncio.CancelledError):
                await caller
            assert original is not None and not original.done()
            assert listener._runner is runner and listener._start_site is not None
            stop = asyncio.create_task(listener.stop())
            await asyncio.sleep(0)
            assert not stop.done() and "cleanup" not in events
            release.set()
            await stop
            assert original.done() and listener.closed.is_set()
            assert events.index("site-returned") < events.index("cleanup")
        finally:
            release.set()
            await asyncio.gather(
                caller, *([stop] if stop is not None else []), return_exceptions=True
            )

    asyncio.run(scenario())


def test_duplicate_start_waits_one_actual_owner_and_never_duplicates_runner(monkeypatch):
    async def scenario():
        listener, _runner, events, entered, release = rig(monkeypatch, block_site=True)
        first = asyncio.create_task(listener.start())
        await entered.wait()
        original = listener._start_owner
        second = asyncio.create_task(listener.start())
        await asyncio.sleep(0)
        release.set()
        await asyncio.gather(first, second)
        assert listener._start_owner is original and events.count("setup") == 1
        await listener.stop()
        assert events.count("cleanup") == 1

    asyncio.run(scenario())


def test_cleanup_acknowledgement_loss_keeps_runner_and_never_replays_cleanup(monkeypatch):
    async def scenario():
        listener, runner, events, _, _ = rig(monkeypatch, setup_error=True, cleanup_error=True)
        with pytest.raises(RuntimeError):
            await listener.start()
        for _ in range(2):
            with pytest.raises(OSError, match="cleanup acknowledgement"):
                await listener.stop()
        assert listener._runner is runner and not listener.closed.is_set()
        assert events.count("cleanup") == 1

    asyncio.run(scenario())


@pytest.mark.parametrize("after_enqueue", (False, True))
def test_unknown_start_owner_creation_cannot_retry_or_certify_shutdown(monkeypatch, after_enqueue):
    async def scenario():
        listener, runner, events, _, _ = rig(monkeypatch)
        loop, actual, calls = asyncio.get_running_loop(), [], []
        original = loop.create_task

        def create(coro, *args, **kwargs):
            if getattr(getattr(coro, "cr_code", None), "co_name", None) != "_start_joined":
                return original(coro, *args, **kwargs)
            calls.append(1)
            if after_enqueue:
                actual.append(original(coro, *args, **kwargs))
            raise MemoryError("synthetic start task creation return loss")

        monkeypatch.setattr(loop, "create_task", create)
        try:
            with pytest.raises(RuntimeError, match="ownership unresolved"):
                await listener.start()
            if actual:
                await actual[0]  # only the fixture retained the unacknowledged actual Task
            with pytest.raises(RuntimeError, match="ownership unresolved"):
                await listener.start()
            with pytest.raises(RuntimeError, match="ownership unresolved"):
                await listener.stop()
            assert len(calls) == 1 and not listener.closed.is_set() and "cleanup" not in events
        finally:
            if not after_enqueue:
                listener._start_coro.close()  # fixture knows creation was never attempted
            else:
                for task in (listener._watch, listener._push_watch):
                    if task is not None:
                        task.cancel()
                await asyncio.gather(
                    *[t for t in (listener._watch, listener._push_watch) if t is not None],
                    return_exceptions=True,
                )
                await runner.cleanup()  # fixture-only cleanup, never a listener drain proof

    asyncio.run(scenario())


@pytest.mark.parametrize("after_enqueue", (False, True))
def test_unknown_stop_owner_creation_never_replays_cleanup(monkeypatch, after_enqueue):
    async def scenario():
        listener, _runner, events, _, _ = rig(monkeypatch, setup_error=True)
        with pytest.raises(RuntimeError):
            await listener.start()
        loop, actual, calls = asyncio.get_running_loop(), [], []
        original = loop.create_task

        def create(coro, *args, **kwargs):
            if getattr(getattr(coro, "cr_code", None), "co_name", None) != "_stop_owned":
                return original(coro, *args, **kwargs)
            calls.append(1)
            if after_enqueue:
                actual.append(original(coro, *args, **kwargs))
            raise MemoryError("synthetic stop task acknowledgement loss")

        monkeypatch.setattr(loop, "create_task", create)
        try:
            with pytest.raises(RuntimeError, match="shutdown ownership unresolved"):
                await listener.stop()
            if actual:
                await actual[0]  # fixture observation is not a retained production owner
            with pytest.raises(RuntimeError, match="shutdown ownership unresolved"):
                await listener.stop()
            assert len(calls) == 1
            assert events.count("cleanup") == int(after_enqueue)
            assert listener._stop_owner is None
            with pytest.raises(RuntimeError):
                await listener.wait_operator_drain()
        finally:
            if not after_enqueue:
                listener._stop_coro.close()  # only the fixture knows no Task was created

    asyncio.run(scenario())


@pytest.mark.parametrize("replacement", ("context", "dependencies", "runner"))
def test_shutdown_rejoins_original_cohort_after_read_service_wait(monkeypatch, replacement):
    async def scenario():
        listener, runner, events, _, _ = rig(monkeypatch, setup_error=True)
        with pytest.raises(RuntimeError):
            await listener.start()
        ctx = listener.ctx
        clears = []
        ctx.push_hints = SimpleNamespace(clear=lambda: clears.append("original"))
        foreign = SimpleNamespace(
            push_hints=SimpleNamespace(clear=lambda: clears.append("foreign")),
            direct_send_deps=None,
        )

        async def stop_read():
            await asyncio.sleep(0)
            if replacement == "context":
                listener.ctx = foreign
            elif replacement == "dependencies":
                ctx.direct_send_deps = object()
            else:
                listener._runner = object()
            return 0

        read = SimpleNamespace(stop=stop_read)
        listener._operator_read = read
        for _ in range(2):
            with pytest.raises(RuntimeError, match="shutdown scope changed"):
                await listener.stop()
        assert not clears and "cleanup" not in events
        assert listener._operator_read is read
        assert listener._operator_read_drained is read
        assert not listener.closed.is_set()
        assert listener._start_runner is runner

    asyncio.run(scenario())


def operator_rig(monkeypatch, *, fail=False):
    from hmp_plugin import operator_read

    listener, runner, events, _, _ = rig(monkeypatch)
    entered, release = asyncio.Event(), asyncio.Event()

    class ReadService:
        def __init__(self, ctx, *_args):
            assert ctx is listener._operator_origin_ctx
            events.append("read-created")

        async def start(self):
            events.append("read-start")
            entered.set()
            await release.wait()
            events.append("read-return")
            if fail:
                raise OSError("synthetic startup failure")

        async def stop(self):
            events.append("read-stop")
            return 0

    monkeypatch.setattr(operator_read, "OperatorReadService", ReadService)
    return listener, runner, events, entered, release


def test_operator_start_caller_cancellation_retains_owner_and_stop_joins(monkeypatch, tmp_path):
    async def scenario():
        listener, _, events, entered, release = operator_rig(monkeypatch)
        await listener.start()
        caller = asyncio.create_task(listener.start_operator_read(tmp_path, "a" * 32))
        await entered.wait()
        retained = listener._operator_read
        owner = listener._operator_start_owner
        caller.cancel()
        with pytest.raises(asyncio.CancelledError):
            await caller
        stop = asyncio.create_task(listener.stop())
        await asyncio.sleep(0)
        assert not stop.done() and "read-stop" not in events and "cleanup" not in events
        release.set()
        await stop
        assert owner.done() and listener._operator_read_drained is retained
        assert events.index("read-return") < events.index("read-stop") < events.index("cleanup")
        assert listener.closed.is_set()
        with pytest.raises(RuntimeError):
            await listener.start_operator_read(tmp_path, "a" * 32)
        assert events.count("read-created") == 1

    asyncio.run(scenario())


def test_operator_start_failure_retains_service_for_explicit_stop(monkeypatch, tmp_path):
    async def scenario():
        listener, _, events, _, release = operator_rig(monkeypatch, fail=True)
        await listener.start()
        release.set()
        with pytest.raises(RuntimeError, match="startup incomplete"):
            await listener.start_operator_read(tmp_path, "a" * 32)
        assert listener._operator_read is not None
        await listener.stop()
        assert events.count("read-stop") == 1 and listener.closed.is_set()

    asyncio.run(scenario())


@pytest.mark.parametrize("after_enqueue", (False, True))
def test_unknown_operator_start_owner_cannot_retry_or_certify_stop(
    monkeypatch, tmp_path, after_enqueue
):
    async def scenario():
        listener, runner, events, _, release = operator_rig(monkeypatch)
        await listener.start()
        loop, actual, calls = asyncio.get_running_loop(), [], []
        original = loop.create_task

        def create(coro, *args, **kwargs):
            if getattr(getattr(coro, "cr_code", None), "co_name", None) != "_start_operator_owned":
                return original(coro, *args, **kwargs)
            calls.append(1)
            if after_enqueue:
                actual.append(original(coro, *args, **kwargs))
            raise MemoryError("synthetic operator startup return loss")

        monkeypatch.setattr(loop, "create_task", create)
        try:
            with pytest.raises(RuntimeError, match="startup ownership unresolved"):
                await listener.start_operator_read(tmp_path, "a" * 32)
            release.set()
            if actual:
                await actual[0]  # fixture-only observation cannot restore the lost owner
            with pytest.raises(RuntimeError):
                await listener.start_operator_read(tmp_path, "a" * 32)
            with pytest.raises(RuntimeError, match="startup ownership unresolved"):
                await listener.stop()
            assert len(calls) == 1 and not listener.closed.is_set()
            assert "read-stop" not in events and "cleanup" not in events
        finally:
            release.set()
            if not after_enqueue:
                listener._operator_start_coro.close()
            for task in (listener._watch, listener._push_watch):
                task.cancel()
            await asyncio.gather(listener._watch, listener._push_watch, return_exceptions=True)
            await runner.cleanup()  # fixture cleanup is not production drain evidence

    asyncio.run(scenario())
