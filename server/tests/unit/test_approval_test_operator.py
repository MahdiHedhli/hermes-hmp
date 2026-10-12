import asyncio
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


@pytest.mark.asyncio
async def test_accepted_begin_reports_only_joined_completion() -> None:
    from hmp_plugin.approval_test_producer import TargetBinding, TestOutcome, TestStatus

    generation = HostGeneration("a" * 52, os.getpid(), "b" * 32)
    request = HostBeginRequest(generation, "synthetic-device", "default", "synthetic-session")
    target = TargetBinding(generation.iid, "synthetic-user", request.profile,
                           request.session_id, request.device_id)
    joined = asyncio.Event()
    calls = []
    async def admit(_):
        return target
    class Producer:
        async def begin_test(self, *_):
            return "synthetic-handle"
        async def wait_outcome(self, *_, **kwargs):
            await joined.wait()
            return TestOutcome(TestStatus.DENIED)
        async def outcome(self, *_):
            assert joined.is_set()
            return TestOutcome(TestStatus.DENIED)
        async def cancel_test(self, *args):
            calls.append(args)
            return TestOutcome(TestStatus.DENIED)
    handler = OperatorHandler(generation, Producer(), admit=admit)
    responses = handler.responses(request)
    first = await anext(responses)
    assert first.result == "accepted"
    next_reply = asyncio.create_task(anext(responses))
    await asyncio.sleep(0)
    assert not next_reply.done()
    joined.set()
    final = await next_reply
    assert final.result == "completed" and final.state == "denied"
    assert final.operation_id == first.operation_id
    await responses.aclose()
    assert len(calls) == 1 and handler._active is None


@pytest.mark.asyncio
async def test_unknown_status_and_cancel_do_not_touch_producer() -> None:
    from hmp_plugin.approval_test_host_codec import HostOperationRequest

    generation = HostGeneration("a" * 52, os.getpid(), "b" * 32)
    async def admit(_):
        raise AssertionError("operation must not admit a new test")
    handler = OperatorHandler(generation, object(), admit=admit)
    for op in ("status", "cancel"):
        request = HostOperationRequest(generation, op, "c" * 32)
        replies = [reply async for reply in handler.responses(request)]
        assert len(replies) == 1 and replies[0].result == "unavailable"


@pytest.mark.asyncio
async def test_active_status_cancel_and_wrong_generation_isolation() -> None:
    from hmp_plugin.approval_test_host_codec import HostOperationRequest
    from hmp_plugin.approval_test_producer import TargetBinding, TestOutcome, TestStatus

    generation = HostGeneration("a" * 52, os.getpid(), "b" * 32)
    request = HostBeginRequest(generation, "synthetic-device", "default", "synthetic-session")
    target = TargetBinding(generation.iid, "synthetic-user", request.profile,
                           request.session_id, request.device_id)
    joined = asyncio.Event()
    calls = []
    async def admit(_):
        return target
    class Producer:
        async def begin_test(self, *_):
            return "synthetic-handle"
        async def wait_outcome(self, *_, **kwargs):
            await joined.wait()
            return TestOutcome(TestStatus.CANCELLED)
        async def outcome(self, *_):
            return TestOutcome(TestStatus.CANCELLED if joined.is_set() else TestStatus.PENDING)
        async def cancel_test(self, *args):
            calls.append(args)
            joined.set()
            return TestOutcome(TestStatus.CANCELLED)
    handler = OperatorHandler(generation, Producer(), admit=admit)
    responses = handler.responses(request)
    first = await anext(responses)
    wrong = HostGeneration(generation.iid, generation.pid, "d" * 32)
    rejected = [r async for r in handler.responses(
        HostOperationRequest(wrong, "cancel", first.operation_id))]
    assert rejected[0].result == "unavailable" and not calls
    status = [r async for r in handler.responses(
        HostOperationRequest(generation, "status", first.operation_id))]
    assert status[0].state == "pending" and 0 <= status[0].remaining_ms <= 30000
    cancelled = [r async for r in handler.responses(
        HostOperationRequest(generation, "cancel", first.operation_id))]
    assert cancelled[0].result == "cancel_requested" and len(calls) == 1
    final = await anext(responses)
    assert final.result == "completed" and final.state == "cancelled"
    await responses.aclose()
    assert handler._active is None


@pytest.mark.asyncio
async def test_cancelled_shutdown_observer_still_waits_for_owned_cleanup() -> None:
    from hmp_plugin.approval_test_producer import TargetBinding, TestOutcome, TestStatus

    generation = HostGeneration("a" * 52, os.getpid(), "b" * 32)
    request = HostBeginRequest(generation, "synthetic-device", "default", "synthetic-session")
    target = TargetBinding(generation.iid, "synthetic-user", request.profile,
                           request.session_id, request.device_id)
    joined = asyncio.Event()
    cancelled = asyncio.Event()
    async def admit(_):
        return target
    class Producer:
        async def begin_test(self, *_):
            return "synthetic-handle"
        async def wait_outcome(self, *_, **kwargs):
            await joined.wait()
            return TestOutcome(TestStatus.CANCELLED)
        async def outcome(self, *_):
            return TestOutcome(TestStatus.CANCELLED)
        async def cancel_test(self, *_):
            cancelled.set()
            return TestOutcome(TestStatus.CLEANUP_PENDING)
    handler = OperatorHandler(generation, Producer(), admit=admit)
    responses = handler.responses(request)
    assert (await anext(responses)).result == "accepted"
    shutdown = asyncio.create_task(handler.shutdown())
    await cancelled.wait()
    shutdown.cancel()
    await asyncio.sleep(0)
    assert not shutdown.done() and not handler._shutdown_task.done()
    joined.set()
    with pytest.raises(asyncio.CancelledError):
        await shutdown
    assert handler._shutdown_task.done() and not handler._shutdown_task.cancelled()
    await responses.aclose()
    assert handler._active is None
