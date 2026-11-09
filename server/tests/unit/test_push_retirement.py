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
