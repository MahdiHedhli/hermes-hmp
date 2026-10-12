import os

import pytest

from hmp_plugin.approval_test_host_codec import HostBeginRequest, HostGeneration
from hmp_plugin.approval_test_operator import OperatorHandler


@pytest.mark.asyncio
async def test_refused_admission_never_starts_producer() -> None:
    generation = HostGeneration("a" * 52, os.getpid(), "b" * 32)
    request = HostBeginRequest(generation, "synthetic-device", "default", "synthetic-session")
    async def admit(_):
        return None
    class Producer:
        async def begin_test(self, *_):
            raise AssertionError("must not invoke")
    handler = OperatorHandler(generation, Producer(), admit=admit)
    replies = [reply async for reply in handler.responses(request)]
    assert len(replies) == 1 and replies[0].result == "unavailable"
    await handler.shutdown()
