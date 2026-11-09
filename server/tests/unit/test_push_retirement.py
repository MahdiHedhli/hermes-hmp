"""Single relay-close owner, using synthetic callbacks only."""
import asyncio
from types import SimpleNamespace

import pytest

from hmp_plugin.push_retirement import RelayCloseOwner


@pytest.mark.parametrize("after_enqueue", (False, True))
def test_unknown_relay_close_publication_never_replays_or_certifies(monkeypatch, after_enqueue):
    async def scenario():
        calls, actual = [], []

        async def close():
            calls.append("close")

        owner = RelayCloseOwner(SimpleNamespace(close=close))
        loop = asyncio.get_running_loop()
        original = loop.create_task

        def create(coro, *args, **kwargs):
            if getattr(getattr(coro, "cr_code", None), "co_name", None) == "_run":
                if after_enqueue:
                    actual.append(original(coro, *args, **kwargs))
                raise MemoryError("synthetic relay close publication loss")
            return original(coro, *args, **kwargs)

        monkeypatch.setattr(loop, "create_task", create)
        try:
            for _ in range(2):
                with pytest.raises(RuntimeError, match="ownership unresolved"):
                    owner.begin()
            if actual:
                await actual[0]  # fixture-only observation cannot restore production ownership
            assert not owner.successful and calls == (["close"] if after_enqueue else [])
            with pytest.raises(RuntimeError, match="ownership unresolved"):
                await owner.wait_drained()
        finally:
            if not after_enqueue:
                owner.coro.close()
                owner.operation.close()  # fixture knows enqueue was refused

    asyncio.run(scenario())


@pytest.mark.parametrize("field", ("ctx", "store", "prompt_store", "push_hints",
                                  "_operator_read_drained", "_push_dispatcher_drained",
                                  "_push_relay_owner"))
def test_server_drain_rejects_resource_replacement_during_wait(field):
    from hmp_plugin.server import HmpServer

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def wait_drained():
            entered.set()
            await release.wait()

        ctx = SimpleNamespace(store=object(), prompt_store=object(), push_hints=object())
        srv = HmpServer.__new__(HmpServer)
        srv.ctx = ctx
        srv._operator_read_drained = SimpleNamespace(wait_drained=wait_drained)
        srv._push_dispatcher_drained = None
        srv._push_relay_owner = None
        srv.operator_worker_debt = 1
        waiter = asyncio.create_task(srv.wait_operator_drain())
        await entered.wait()
        target = ctx if field in ("store", "prompt_store", "push_hints") else srv
        setattr(target, field, object())
        release.set()
        with pytest.raises(RuntimeError, match="drain scope changed"):
            await waiter
        assert srv.operator_worker_debt == 1

    asyncio.run(scenario())
