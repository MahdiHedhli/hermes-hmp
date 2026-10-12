import pytest

from hmp_plugin.approval_test_answers import TestAnswers as Answers
from hmp_plugin.approval_test_producer import TestNotice as Notice
from hmp_plugin.approval_test_producer import TestOutcome as Outcome
from hmp_plugin.approval_test_producer import TestStatus as Status
from hmp_plugin.approval_test_projection import TestProjection as Projection
from hmp_plugin.prompts import PromptStore


@pytest.mark.asyncio
@pytest.mark.parametrize("revoke", ["before", "during", "after", "never"])
async def test_authority_and_projection_rechecked_across_awaits(revoke: str) -> None:
    store = PromptStore(clock=lambda: 100)
    projection = Projection(store, wall_clock=lambda: 100, monotonic=lambda: 10)
    notice = Notice("synthetic-instance", "synthetic-user", "default", "synthetic-session",
                    "synthetic-device", "synthetic-request", deadline_monotonic=20)
    assert projection.publish(notice)
    row = store.get((notice.instance_id, notice.user_id, notice.profile, notice.request_id))
    assert row is not None
    calls = []
    checks = []
    async def current(candidate):
        assert candidate is notice
        checks.append(candidate)
        if revoke == "during":
            projection.remove(notice)
        return revoke != "before" and not (revoke == "after" and len(checks) == 2)
    class Producer:
        async def answer_test(self, handle, device, choice):
            calls.append((handle, device, choice))
            return Outcome(Status.PENDING)
        async def wait_outcome(self, handle, device, timeout=None):  # noqa: ASYNC109
            return Outcome(Status.ONCE_ACKNOWLEDGED)
    answers = Answers(
        projection, Producer(), current=current, handle_for=lambda _: "synthetic-handle"
    )
    assert await answers.resolve(row, "synthetic-other-device", "once") == "stale"
    assert calls == [] and checks == []
    result = await answers.resolve(row, notice.device_id, "once")
    if revoke in ("before", "during"):
        assert result == "stale" and calls == []
    elif revoke == "after":
        assert result == "unavailable" and len(calls) == 1
    else:
        assert result == "accepted" and len(calls) == 1


@pytest.mark.asyncio
async def test_authority_exception_never_calls_producer_or_leaks_details() -> None:
    store = PromptStore(clock=lambda: 100)
    projection = Projection(store, wall_clock=lambda: 100, monotonic=lambda: 10)
    notice = Notice("synthetic-instance", "synthetic-user", "default", "synthetic-session",
                    "synthetic-device", "synthetic-request", deadline_monotonic=20)
    assert projection.publish(notice)
    row = store.get((notice.instance_id, notice.user_id, notice.profile, notice.request_id))
    async def current(_):
        raise RuntimeError("synthetic private dependency detail")
    class Producer:
        async def answer_test(self, *_):
            raise AssertionError("must not invoke")
    answers = Answers(projection, Producer(), current=current, handle_for=lambda _: "handle")
    assert await answers.resolve(row, notice.device_id, "once") == "unavailable"
