import asyncio
import os

import pytest

from hmp_plugin.approval_test_host_codec import HostBeginRequest, HostGeneration
from hmp_plugin.approval_test_operator import OperatorHandler


async def synthetic_current(_):
    return True


@pytest.mark.asyncio
async def test_refused_admission_never_starts_producer() -> None:
    generation = HostGeneration("a" * 52, os.getpid(), "b" * 32)
    request = HostBeginRequest(generation, "synthetic-device", "default", "synthetic-session")
    async def admit(_):
        return None
    class Producer:
        async def begin_test(self, *_):
            raise AssertionError("must not invoke")
    handler = OperatorHandler(generation, Producer(), admit=admit, current=synthetic_current)
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
    handler = OperatorHandler(generation, Producer(), admit=admit, current=synthetic_current)
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
    handler = OperatorHandler(generation, object(), admit=admit, current=synthetic_current)
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
    handler = OperatorHandler(generation, Producer(), admit=admit, current=synthetic_current)
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
    handler = OperatorHandler(generation, Producer(), admit=admit, current=synthetic_current)
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


@pytest.mark.asyncio
async def test_shutdown_during_admission_cannot_start_waiter() -> None:
    from hmp_plugin.approval_test_producer import TargetBinding

    generation = HostGeneration("a" * 52, os.getpid(), "b" * 32)
    request = HostBeginRequest(generation, "synthetic-device", "default", "synthetic-session")
    entered, resume = asyncio.Event(), asyncio.Event()
    async def admit(_):
        entered.set()
        await resume.wait()
        return TargetBinding(generation.iid, "synthetic-user", request.profile,
                             request.session_id, request.device_id)
    class Producer:
        async def begin_test(self, *_):
            raise AssertionError("shutdown must prevent invocation")
    handler = OperatorHandler(generation, Producer(), admit=admit, current=synthetic_current)
    responses = handler.responses(request)
    reply = asyncio.create_task(anext(responses))
    await entered.wait()
    shutdown = asyncio.create_task(handler.shutdown())
    await asyncio.sleep(0)
    resume.set()
    assert (await reply).result == "unavailable"
    await responses.aclose()
    await shutdown
    await responses.aclose()


@pytest.mark.asyncio
async def test_concurrent_begin_cannot_enter_second_admission() -> None:
    generation = HostGeneration("a" * 52, os.getpid(), "b" * 32)
    request = HostBeginRequest(generation, "synthetic-device", "default", "synthetic-session")
    entered, resume = asyncio.Event(), asyncio.Event()
    admissions = []
    async def admit(candidate):
        admissions.append(candidate)
        entered.set()
        await resume.wait()
        return None
    handler = OperatorHandler(generation, object(), admit=admit, current=synthetic_current)
    first = handler.responses(request)
    reply = asyncio.create_task(anext(first))
    await entered.wait()
    second = [r async for r in handler.responses(request)]
    assert second[0].result == "unavailable" and len(admissions) == 1
    resume.set()
    assert (await reply).result == "unavailable"
    await first.aclose()
    assert not handler._admitting


@pytest.mark.asyncio
async def test_shutdown_waits_for_suspended_begin_and_cancels_late_handle() -> None:
    from hmp_plugin.approval_test_producer import TargetBinding, TestOutcome, TestStatus

    generation = HostGeneration("a" * 52, os.getpid(), "b" * 32)
    request = HostBeginRequest(generation, "synthetic-device", "default", "synthetic-session")
    entered, resume = asyncio.Event(), asyncio.Event()
    cancelled = []
    async def admit(_):
        return TargetBinding(generation.iid, "synthetic-user", request.profile,
                             request.session_id, request.device_id)
    class Producer:
        async def begin_test(self, *_):
            entered.set()
            await resume.wait()
            return "synthetic-handle"
        async def cancel_test(self, *args):
            cancelled.append(args)
            return TestOutcome(TestStatus.CANCELLED)
        async def wait_outcome(self, *_, **kwargs):
            return TestOutcome(TestStatus.CANCELLED)
    handler = OperatorHandler(generation, Producer(), admit=admit, current=synthetic_current)
    responses = handler.responses(request)
    reply = asyncio.create_task(anext(responses))
    await entered.wait()
    shutdown = asyncio.create_task(handler.shutdown())
    await asyncio.sleep(0)
    assert not shutdown.done()
    resume.set()
    assert (await reply).result == "unavailable"
    await responses.aclose()
    await shutdown
    assert cancelled and handler._active is None


@pytest.mark.asyncio
async def test_lost_current_authority_cancels_and_joins_open_test() -> None:
    from hmp_plugin.approval_test_producer import TargetBinding, TestOutcome, TestStatus

    generation = HostGeneration("a" * 52, os.getpid(), "b" * 32)
    request = HostBeginRequest(generation, "synthetic-device", "default", "synthetic-session")
    target = TargetBinding(generation.iid, "synthetic-user", request.profile,
                           request.session_id, request.device_id)
    calls = []
    async def admit(_):
        return target
    async def current(_):
        return False
    class Producer:
        async def begin_test(self, *_):
            return "synthetic-handle"
        async def wait_outcome(self, *_, **kwargs):
            return TestOutcome(TestStatus.CANCELLED if calls else TestStatus.PENDING)
        async def outcome(self, *_):
            return TestOutcome(TestStatus.CANCELLED)
        async def cancel_test(self, *args):
            calls.append(args)
            return TestOutcome(TestStatus.CANCELLED)
    handler = OperatorHandler(generation, Producer(), admit=admit, current=current)
    replies = [r async for r in handler.responses(request)]
    assert replies[0].result == "accepted"
    assert replies[1].state == "cancelled" and calls
    assert handler._active is None
