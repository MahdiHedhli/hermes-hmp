import pytest

from hmp_plugin.approval_test_producer import TestOutcome as Outcome
from hmp_plugin.approval_test_producer import TestStatus as Status
from hmp_plugin.approval_test_service import TestService as Service


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [Status.PENDING, Status.CLEANUP_PENDING, Status.UNAVAILABLE])
async def test_shutdown_never_certifies_residual_producer_debt(status) -> None:
    calls = []
    class Operator:
        async def shutdown(self):
            calls.append("operator")
    class Producer:
        async def close(self):
            calls.append("producer")
            return Outcome(status)
    service = object.__new__(Service)
    service.operator, service.producer = Operator(), Producer()
    with pytest.raises(RuntimeError, match="^approval test cleanup unavailable$"):
        await service.shutdown()
    assert calls == ["operator", "producer"]
