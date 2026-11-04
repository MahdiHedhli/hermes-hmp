"""Composed fixed-reader OS checks with synthetic native authority only."""

import asyncio
import tempfile
import time
from pathlib import Path

import pytest

from hmp_plugin.presentation_authority import (
    AuthorityRefusalError,
    ListenerFence,
    NativeObservation,
    OriginalHeaders,
    ParentAuthorityAdapter,
)
from hmp_plugin.presentation_jobs import CapturedLease, State
from hmp_plugin.presentation_supervisor import ReaderSupervisor


class Request:
    class Headers:
        def getall(self, key, default):
            return {"Authorization": ["Bearer " + "A" * 43], "HMP-Instance": ["a" * 52]}.get(
                key, default
            )

    headers = Headers()


class Native:
    def __init__(self, home):
        self.home = str(home)
        self.block = None
        self.block_occurrence = 1
        self.calls = {}
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.ignore_cancel = False
        self.drain_calls = 0

    async def observe(self, record, phase):
        self.calls[phase] = self.calls.get(phase, 0) + 1
        if phase == self.block and self.calls[phase] == self.block_occurrence:
            self.entered.set()
            try:
                await self.release.wait()
            except asyncio.CancelledError:
                if not self.ignore_cancel:
                    raise
                await self.release.wait()
        lease = record.lease
        return NativeObservation(
            lease.iid,
            lease.device_id,
            lease.user_id,
            lease.family_id,
            lease.profile,
            self.home,
            record.listener,
            record.store,
            record.bridge,
            record.identity,
            record.native_owner,
            True,
        )

    async def drain(self, record):
        self.drain_calls += 1
        if self.block == "DRAIN":
            self.entered.set()
            try:
                await self.release.wait()
            except asyncio.CancelledError:
                if not self.ignore_cancel:
                    raise
                await self.release.wait()
        return True


@pytest.fixture
def context():
    with tempfile.TemporaryDirectory(
        prefix="hmp-supervisor-synthetic-", dir=Path.cwd()
    ) as directory:
        root = Path(directory)
        home = root / "profiles" / "alpha"
        home.mkdir(parents=True, mode=0o700)
        (home / "profile.yaml").write_text(
            "display_name: Aster\n"
            "ui_meta: {hermes-bots: {shape: hexagon, color: '#8b5cf6', custom: true}}\n"
        )
        (home / "profile.yaml").chmod(0o600)
        native = Native(home)
        authority = ParentAuthorityAdapter("a" * 52, service=native)
        operation = authority.reserve(
            CapturedLease("a" * 52, "device", "user", "family", "alpha", "b" * 64, "binding", 1),
            "METADATA",
            OriginalHeaders.from_request(Request()),
            listener=object(),
            fence=ListenerFence(1),
            store=object(),
            bridge=object(),
            identity=object(),
            native_owner=object(),
        )
        yield authority, operation, native


@pytest.mark.asyncio
async def test_complete_policy_child_native_emit_and_retirement(context):
    authority, operation, native = context
    supervisor = ReaderSupervisor(authority, operation)
    results = []
    assert await supervisor.run(
        source_sha="b" * 64,
        fallback="Hermes",
        observed_at=100,
        sink=lambda header, body: results.append((header, body)),
    )
    assert supervisor.retired and supervisor.phase == "CLOSED"
    assert len(results) == 1 and results[0][0]["fields"]["display_name"] == "Aster"
    assert supervisor.process.reaped and supervisor.process.group_absent
    assert supervisor.pipes.drained and supervisor.control.closed
    assert native.drain_calls == 1 and operation not in authority._by_operation
    with pytest.raises(AuthorityRefusalError):
        await supervisor.run(
            source_sha="b" * 64, fallback="Hermes", observed_at=100, sink=lambda *_: None
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "phase, occurrence, launched",
    [
        ("INITIAL", 1, False),
        ("BEFORE", 1, False),
        ("PRE_GO", 1, False),
        ("PRE_GO", 2, True),
        ("PRE_EMIT", 1, True),
    ],
)
async def test_cancelled_native_await_cannot_resume_normal_work(
    context, phase, occurrence, launched
):
    authority, operation, native = context
    native.block = phase
    native.block_occurrence = occurrence
    native.ignore_cancel = True
    supervisor = ReaderSupervisor(authority, operation)
    results = []
    running = asyncio.create_task(
        supervisor.run(
            source_sha="b" * 64,
            fallback="Hermes",
            observed_at=100,
            sink=lambda *row: results.append(row),
        )
    )
    await native.entered.wait()
    started = time.monotonic()
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running
    assert time.monotonic() - started < 0.75
    assert supervisor.phase == "DEBT" and not supervisor.retired
    assert (supervisor.process is not None) is launched
    if launched:
        assert supervisor.process.reaped and supervisor.process.group_absent
        assert supervisor.pipes.drained and supervisor.control.closed
        assert supervisor.pipes.output == b""
    assert not results and native.drain_calls == 0
    assert authority._record(operation).headers is not None
    native.release.set()
    await asyncio.wait({supervisor.task}, timeout=1.0)
    assert supervisor.task.done() and not results
    assert (supervisor.process is not None) is launched
    assert authority.owner.inspect(authority.handle(operation))[0] is State.UNKNOWN


@pytest.mark.asyncio
async def test_supervisor_single_owner_binding(context):
    authority, operation, _ = context
    owner = ReaderSupervisor(authority, operation)
    with pytest.raises(AuthorityRefusalError):
        ReaderSupervisor(authority, operation)
    assert authority._record(operation).reader_supervisor is owner


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["launch", "pipes", "control"])
async def test_partial_acquisition_is_retained_without_replay(context, monkeypatch, failure):
    from hmp_plugin import presentation_process
    from hmp_plugin.presentation_control_pipe import OwnedControlPipe
    from hmp_plugin.presentation_jobs import FrameError
    from hmp_plugin.presentation_pipes import OwnedPresentationPipes, PipeAcquisitionError

    authority, operation, _ = context
    supervisor = ReaderSupervisor(authority, operation)
    attempts = []
    if failure == "launch":

        def fail(*args, **kwargs):
            attempts.append("launch")
            raise OSError("synthetic launch failure")

        monkeypatch.setattr(presentation_process.subprocess, "Popen", fail)
    elif failure == "pipes":
        original = OwnedPresentationPipes.__init__

        def fail(owner, *args, **kwargs):
            attempts.append("pipes")
            original(owner, *args, **kwargs)
            owner.uncertain = True
            raise PipeAcquisitionError(owner, OSError("synthetic acquisition failure"), None)

        monkeypatch.setattr(OwnedPresentationPipes, "__init__", fail)
    else:
        original = OwnedControlPipe.__init__

        def fail(owner, *args, **kwargs):
            attempts.append("control")
            original(owner, *args, **kwargs)
            owner.uncertain = True
            raise FrameError("BI1_SYNTHETIC_CONSTRUCTOR_FAILURE")

        monkeypatch.setattr(OwnedControlPipe, "__init__", fail)
    try:
        assert not await supervisor.run(
            source_sha="b" * 64,
            fallback="Hermes",
            observed_at=100,
            sink=lambda *_: pytest.fail("partial failure emitted"),
        )
        assert attempts == [failure] and supervisor.phase == "DEBT"
        assert not supervisor.retired and authority._record(operation).headers is not None
        assert supervisor.process is not None
        if failure != "launch":
            assert supervisor.process.reaped and supervisor.process.group_absent
            assert supervisor.pipes is not None
            if failure == "control":
                assert supervisor.control is not None and not supervisor.control_constructed
    finally:
        # Test teardown only: retained ambiguous owners are not retirement evidence.
        child = supervisor.process._child if supervisor.process else None
        if child is not None:
            for stream in (child.stdin, child.stdout, child.stderr):
                if stream is not None and not stream.closed:
                    stream.close()
            if supervisor.pipes and supervisor.pipes._selector:
                supervisor.pipes._selector.close()


@pytest.mark.asyncio
async def test_expired_original_deadline_cannot_launch(context):
    authority, operation, native = context
    native.block = "INITIAL"
    native.ignore_cancel = True
    supervisor = ReaderSupervisor(authority, operation)
    began = time.monotonic()
    assert not await supervisor.run(
        source_sha="b" * 64,
        fallback="Hermes",
        observed_at=100,
        sink=lambda *_: pytest.fail("expired result emitted"),
    )
    assert 1.5 < time.monotonic() - began < 3.0
    assert supervisor.phase == "DEBT" and supervisor.process is None
    deadline = supervisor.cleanup_deadline
    native.release.set()
    await asyncio.wait({supervisor.task}, timeout=1.0)
    assert supervisor.task.done() and supervisor.process is None
    assert supervisor.cleanup_deadline == deadline and native.drain_calls == 0


@pytest.mark.asyncio
async def test_cleanup_budget_exhaustion_after_signal_prevents_close_and_probe(
    context, monkeypatch
):
    from hmp_plugin.presentation_process import PresentationProcessOwner

    authority, operation, native = context
    native.block, native.block_occurrence, native.ignore_cancel = "PRE_GO", 2, True
    supervisor = ReaderSupervisor(authority, operation)
    original = PresentationProcessOwner.terminate_once

    def exhaust(owner):
        result = original(owner)
        supervisor.cleanup_deadline = time.monotonic() - 1.0
        return result

    monkeypatch.setattr(PresentationProcessOwner, "terminate_once", exhaust)
    running = asyncio.create_task(
        supervisor.run(
            source_sha="b" * 64,
            fallback="Hermes",
            observed_at=100,
            sink=lambda *_: pytest.fail("late emission"),
        )
    )
    await native.entered.wait()
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running
    assert supervisor.phase == "DEBT" and not supervisor.control.closed
    assert not supervisor.process._group_probe_attempted
    assert supervisor.control._close_attempted is False
    native.release.set()
    await asyncio.wait({supervisor.task}, timeout=1.0)
    # Explicit test teardown of the known synthetic child, outside claimed cleanup.
    limit = time.monotonic() + 2.0
    while not supervisor.process.poll_wait():
        assert time.monotonic() < limit
        await asyncio.sleep(0.005)
    for stream in (
        supervisor.process.child.stdin,
        supervisor.process.child.stdout,
        supervisor.process.child.stderr,
    ):
        if not stream.closed:
            stream.close()
    supervisor.pipes._selector.close()


@pytest.mark.asyncio
async def test_second_run_cannot_create_competing_cleanup(context):
    authority, operation, native = context
    native.block = "INITIAL"
    supervisor = ReaderSupervisor(authority, operation)
    running = asyncio.create_task(
        supervisor.run(
            source_sha="b" * 64, fallback="Hermes", observed_at=100, sink=lambda *_: None
        )
    )
    await native.entered.wait()
    with pytest.raises(AuthorityRefusalError):
        await supervisor.run(
            source_sha="b" * 64, fallback="Hermes", observed_at=100, sink=lambda *_: None
        )
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running
    assert supervisor.task.done() and supervisor.cleanup_task.done()
    assert supervisor.process is None


@pytest.mark.asyncio
async def test_late_native_drain_cannot_retire_or_repeat_emission(context):
    authority, operation, native = context
    native.block, native.ignore_cancel = "DRAIN", True
    supervisor = ReaderSupervisor(authority, operation)
    emitted = []
    assert await supervisor.run(
        source_sha="b" * 64,
        fallback="Hermes",
        observed_at=100,
        sink=lambda *row: emitted.append(row),
    )
    assert len(emitted) == 1 and native.drain_calls == 1
    assert not supervisor.retired and supervisor.phase == "DEBT"
    assert authority._record(operation).headers is not None
    assert authority._record(operation).native_claim is not None
    deadline = supervisor.cleanup_deadline
    native.release.set()
    await asyncio.wait({supervisor.cleanup_task}, timeout=1.0)
    assert supervisor.cleanup_task.done() and not supervisor.retired
    assert authority._record(operation).headers is not None
    assert supervisor.cleanup_deadline == deadline and len(emitted) == 1


@pytest.mark.asyncio
async def test_cancelled_policy_thread_is_retained_until_actual_join(context, monkeypatch):
    import threading

    from hmp_plugin.presentation_parent_policy import ParentPolicyReadOwner

    authority, operation, _ = context
    entered, release = threading.Event(), threading.Event()
    original = ParentPolicyReadOwner._stat

    def blocked(owner, *args):
        entered.set()
        assert release.wait(timeout=3.0)
        return original(owner, *args)

    monkeypatch.setattr(ParentPolicyReadOwner, "_stat", blocked)
    supervisor = ReaderSupervisor(authority, operation)
    running = asyncio.create_task(
        supervisor.run(
            source_sha="b" * 64,
            fallback="Hermes",
            observed_at=100,
            sink=lambda *_: pytest.fail("late policy emitted"),
        )
    )
    limit = time.monotonic() + 2.0
    while not entered.is_set():
        assert time.monotonic() < limit
        await asyncio.sleep(0.005)
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running
    work = authority._record(operation).policy_work
    assert supervisor.phase == "DEBT" and supervisor.process is None
    assert not work.resources_closed and not work._thread.joined
    assert authority._record(operation).headers is not None
    deadline = supervisor.cleanup_deadline
    release.set()
    limit = time.monotonic() + 2.0
    while not work.poll_join():
        assert time.monotonic() < limit
        await asyncio.sleep(0.005)
    assert work.resources_closed
    assert authority._record(operation).headers is not None
    assert supervisor.cleanup_deadline == deadline and not supervisor.retired


@pytest.mark.asyncio
async def test_sink_failure_after_write_never_replays_or_claims_retirement(context):
    authority, operation, _ = context
    supervisor = ReaderSupervisor(authority, operation)
    writes = []

    def lost_ack(*row):
        writes.append(row)
        raise OSError("synthetic lost sink acknowledgement")

    assert not await supervisor.run(
        source_sha="b" * 64, fallback="Hermes", observed_at=100, sink=lost_ack
    )
    assert len(writes) == 1 and supervisor.phase == "DEBT" and not supervisor.retired
    assert authority._record(operation).headers is not None
    assert authority.owner.inspect(authority.handle(operation))[0] is State.UNKNOWN
    with pytest.raises(AuthorityRefusalError):
        await supervisor.run(source_sha="b" * 64, fallback="Hermes", observed_at=100, sink=lost_ack)
    assert len(writes) == 1
