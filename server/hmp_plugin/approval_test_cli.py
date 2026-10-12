"""AT1 finite operator observation, not registered until independent binding review.

Only the same-UID host transport sends selectors. No native producer, metadata,
phone credential, grants, migration, provider or process is created here.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from .approval_test_host_codec import (
    HostBeginRequest,
    HostGeneration,
    HostOperationRequest,
    HostResponse,
    encode_host_response,
)
from .approval_test_host_transport import HostTransportError, host_exchange

CONTROL_SECONDS = 8.0
OUTPUT_CAP = 1024
_TERMINAL = frozenset({"once_acknowledged", "denied", "cancelled", "expired", "unavailable"})
_UNCERTAIN = "Approval test completion unconfirmed; do not resubmit begin.\n"
_INTERRUPTED = "Operator interrupted; host cleanup is not confirmed by interruption.\n"
_CANCEL_UNCONFIRMED = "Cancel delivery unconfirmed; host cleanup remains unconfirmed.\n"
_REQUESTED = "Cancel requested; awaiting joined completion.\n"
Exchange = Callable[
    [Path, HostBeginRequest | HostOperationRequest], AsyncIterator[HostResponse]
]


@dataclass(frozen=True, slots=True, repr=False)
class ListenerBinding:
    """Private record comparison DATA. Transport independently checks server UID."""

    record: Path
    generation: HostGeneration
    reread: Callable[[], HostGeneration]

    def check(self) -> None:
        observed = self.reread()
        if type(observed) is not HostGeneration or observed != self.generation:
            raise HostTransportError()


class Interrupts:
    """First interrupt requests typed cancel; second abandons local observation only."""

    def __init__(self) -> None:
        self.count = 0
        self.changed = asyncio.Event()

    def interrupt(self) -> None:
        self.count += 1
        self.changed.set()


@contextlib.contextmanager
def _operator_signals(interrupts: Interrupts) -> Iterator[None]:
    loop = asyncio.get_running_loop()
    previous = signal.getsignal(signal.SIGINT)

    def on_interrupt(_number: int, _frame: object) -> None:
        # Do not let asyncio.run cancel the begin lease on the first SIGINT.
        loop.call_soon_threadsafe(interrupts.interrupt)

    signal.signal(signal.SIGINT, on_interrupt)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


class _Output:
    def __init__(self, stream: TextIO) -> None:
        self.stream = stream
        self.written = 0

    def write(self, text: str) -> None:
        # All callers supply fixed text or validated operation-id/state tokens only.
        if self.written + len(text) > OUTPUT_CAP:
            raise HostTransportError()
        self.stream.write(text)
        self.stream.flush()
        self.written += len(text)


class _Observation:
    def __init__(self) -> None:
        self.operation_id: str | None = None
        self.admitted_or_done = asyncio.Event()
        self.finished = False
        self.joined = False


def _terminal_code(state: str) -> int:
    return 1 if state == "unavailable" else 0 if state in _TERMINAL else 2


async def _observe(
    binding: ListenerBinding,
    request: HostBeginRequest | HostOperationRequest,
    exchange: Exchange,
    observation: _Observation,
    output: _Output,
) -> int:
    replies = 0
    code = 2
    final_line = None
    lease: AsyncIterator[HostResponse] | None = None
    try:
        binding.check()  # Immediate reread before this exchange; no health/TLS authority.
        lease = exchange(binding.record, request)
        async for reply in lease:
            encode_host_response(reply)  # Defensive closed DTO check, no response body print.
            if replies and code == 1:
                raise HostTransportError()
            if replies == 0 and reply.result == "unavailable":
                final_line = "Approval test unavailable.\n"
                code = 1
            elif type(request) is HostBeginRequest:
                if (replies == 0 and reply.result == "accepted"
                        and reply.timeout_ms == request.timeout_ms):
                    observation.operation_id = reply.operation_id
                    observation.admitted_or_done.set()
                    output.write(f"Operation {reply.operation_id}: accepted; completion pending.\n")
                elif (replies == 1 and reply.result == "completed"
                      and reply.operation_id == observation.operation_id):
                    code = _terminal_code(reply.state)
                    final_line = f"Operation {reply.operation_id}: joined {reply.state}.\n"
                else:
                    raise HostTransportError()
            elif (replies == 0 and reply.operation_id == request.operation_id
                  and reply.result == ("status" if request.op == "status" else "cancel_requested")):
                if request.op == "status":
                    code = _terminal_code(reply.state)
                    final_line = f"Operation {reply.operation_id}: {reply.state}.\n"
                else:
                    # A control-intent receipt never proves producer join, even with a
                    # terminal state snapshot. Explicit read-only status can reconcile it.
                    code = 2
                    final_line = f"Operation {reply.operation_id}: cancel requested.\n"
            else:
                raise HostTransportError()
            replies += 1
            if replies > (2 if type(request) is HostBeginRequest else 1):
                raise HostTransportError()
        # host_exchange yields its final frame only after exact response EOF. It then
        # returns/owns socket close. Require iterator termination as well as that frame.
        if replies == 0 or (type(request) is HostBeginRequest and replies == 1 and code != 1):
            raise HostTransportError()
        if lease is not None:
            close = getattr(lease, "aclose", None)
            if close is not None:
                await close()
            lease = None
        if final_line is None:
            raise HostTransportError()
        # Only a validated terminal begin frame, clean EOF and closed iterator
        # establish joined completion. Local transport failure does not.
        observation.joined = type(request) is HostBeginRequest and replies == 2 and code != 2
        output.write(final_line)
        if code == 2:
            output.write(_UNCERTAIN)
        return code
    except Exception:
        output.write(_UNCERTAIN)  # Never expose paths, selectors or exception strings.
        return 2
    finally:
        observation.finished = True
        observation.admitted_or_done.set()
        if lease is not None:
            close = getattr(lease, "aclose", None)
            if close is not None:
                await close()  # Local observation close is never native cleanup proof.


async def _interrupt_cancel(
    binding: ListenerBinding,
    observation: _Observation,
    exchange: Exchange,
    output: _Output,
) -> None:
    await observation.admitted_or_done.wait()
    if observation.joined or observation.operation_id is None:
        return
    request = HostOperationRequest(binding.generation, "cancel", observation.operation_id)
    lease: AsyncIterator[HostResponse] | None = None
    try:
        # Separate bounded same-UID connection; do not cancel/close the begin observer.
        async with asyncio.timeout(CONTROL_SECONDS):
            binding.check()
            lease = exchange(binding.record, request)
            replies = []
            async for reply in lease:
                encode_host_response(reply)
                if len(replies) or reply.result not in ("cancel_requested", "unavailable"):
                    raise HostTransportError()
                if reply.result != "unavailable" and reply.operation_id != request.operation_id:
                    raise HostTransportError()
                replies.append(reply)
            if len(replies) != 1 or replies[0].result != "cancel_requested":
                raise HostTransportError()
        output.write(_REQUESTED)
    except Exception:
        output.write(_CANCEL_UNCONFIRMED)
    finally:
        if lease is not None:
            close = getattr(lease, "aclose", None)
            if close is not None:
                await close()


async def run_command(
    binding: ListenerBinding,
    request: HostBeginRequest | HostOperationRequest,
    stdout: TextIO,
    *,
    exchange: Exchange = host_exchange,
    interrupts: Interrupts | None = None,
    install_signals: bool = True,
) -> int:
    """One invocation/one begin attempt. Pending cleanup has no success timeout.

    Injection parameters are fake-test seams, not CLI arguments or authority ports.
    Production uses the reviewed host_exchange and installs its SIGINT handler.
    """
    output = _Output(stdout)
    if request.generation != binding.generation:
        output.write(_UNCERTAIN)
        return 2
    interrupts = interrupts if interrupts is not None else Interrupts()
    observation = _Observation()
    observer = wake = control = None
    signal_scope = _operator_signals(interrupts) if install_signals else contextlib.nullcontext()
    try:
        with signal_scope:
            if type(request) is HostBeginRequest:
                observer = asyncio.create_task(
                    _observe(binding, request, exchange, observation, output)
                )
            else:
                async def bounded_observe() -> int:
                    async with asyncio.timeout(CONTROL_SECONDS):
                        return await _observe(binding, request, exchange, observation, output)
                observer = asyncio.create_task(bounded_observe())
            while True:
                wake = asyncio.create_task(interrupts.changed.wait())
                await asyncio.wait({observer, wake}, return_when=asyncio.FIRST_COMPLETED)
                if interrupts.count:
                    interrupts.changed.clear()
                    if interrupts.count >= 2 or type(request) is not HostBeginRequest:
                        output.write(_INTERRUPTED)
                        return 130
                    if control is None and not observation.joined:
                        control = asyncio.create_task(
                            _interrupt_cancel(binding, observation, exchange, output)
                        )
                if observer.done():
                    result = observer.result()
                    # No need to cancel a settled operation; finish any already-started,
                    # bounded cancel exchange while still honoring a second interrupt.
                    if control is not None and not control.done():
                        if not wake.done():
                            wake.cancel()
                        await asyncio.gather(wake, return_exceptions=True)
                        wake = asyncio.create_task(interrupts.changed.wait())
                        await asyncio.wait({control, wake}, return_when=asyncio.FIRST_COMPLETED)
                        if interrupts.count >= 2:
                            output.write(_INTERRUPTED)
                            return 130
                        await control
                    if interrupts.count:
                        output.write(_INTERRUPTED)
                        return 130
                    return result
                if not wake.done():
                    wake.cancel()
                await asyncio.gather(wake, return_exceptions=True)
    except Exception:
        output.write(_UNCERTAIN)
        return 130 if interrupts.count else 2
    finally:
        # Only local transport tasks/observations are abandoned. Closing them cannot
        # release the listener's server-owned producer debt or assert cleanup.
        tasks = [task for task in (observer, wake, control) if task is not None]
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
