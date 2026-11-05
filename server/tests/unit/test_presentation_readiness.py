"""Real private socketpairs and metadata notifications, no host or broker work."""
import asyncio
import socket
import time

import pytest
import pytest_asyncio

from hmp_plugin import presentation_readiness as readiness
from hmp_plugin.presentation_jobs import FrameError

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def pair():
    left, right = socket.socketpair()
    left.setblocking(False)
    right.setblocking(False)
    try:
        yield left, right
    finally:
        # Test-owned disposal, including intentionally foreign registration cases;
        # not a production ownership/closure observation.
        loop = asyncio.get_running_loop()
        for sock in (left, right):
            if sock.fileno() >= 0:
                loop.remove_reader(sock.fileno())
                loop.remove_writer(sock.fileno())
                sock.close()


def end():
    return time.monotonic_ns() + 1_000_000_000


async def test_readiness_contains_no_payload_and_never_consumes_kernel_bytes(pair):
    left, right = pair
    owner = readiness.SelectorReadiness(left)
    right.send(b"SYNTHETIC_READINESS")
    assert await owner.wait(end()) is None
    assert owner._future_snapshot.result() is None
    assert owner._retired and not owner._unknown
    assert left.recv(64) == b"SYNTHETIC_READINESS"
    with pytest.raises(FrameError):
        await owner.wait(end())  # no second attempt or renewed wait


async def test_cancellation_after_notification_cannot_lose_consumed_payload(pair, monkeypatch):
    left, right = pair
    original = readiness.SelectorReadiness._readable
    retained = []
    def notified(owner, token):
        original(owner, token)
        assert owner._future_snapshot.done() and owner._future_snapshot.result() is None
        work.cancel()  # after notification but before original task resumes
    monkeypatch.setattr(readiness.SelectorReadiness, "_readable", notified)
    async def reader():
        owner = readiness.SelectorReadiness(left)
        retained.append(owner)
        await owner.wait(end())
        pytest.fail("cancelled original task resumed")
    work = asyncio.create_task(reader())
    await asyncio.sleep(0)
    right.send(b"SYNTHETIC_CANCEL_RACE")
    with pytest.raises(asyncio.CancelledError):
        await work
    assert retained[0]._retired and not retained[0]._unknown
    assert left.recv(64) == b"SYNTHETIC_CANCEL_RACE"


async def test_timeout_retires_only_registration_without_reading_or_renewal(pair):
    left, right = pair
    owner = readiness.SelectorReadiness(left)
    deadline = time.monotonic_ns() + 100_000_000
    with pytest.raises(TimeoutError):
        await owner.wait(deadline)
    assert owner._retired or not owner._attempted
    assert not owner._unknown
    right.send(b"SYNTHETIC_AFTER_TIMEOUT")
    assert left.recv(64) == b"SYNTHETIC_AFTER_TIMEOUT"


async def test_preexisting_reader_is_not_replaced_or_removed(pair):
    left, _ = pair
    loop = asyncio.get_running_loop()
    def callback():
        pass
    loop.add_reader(left.fileno(), callback)
    old = loop._selector.get_key(left.fileno()).data[0]
    owner = readiness.SelectorReadiness(left)
    with pytest.raises(FrameError):
        await owner.wait(end())
    assert loop._selector.get_key(left.fileno()).data[0] is old
    assert not owner._attempted and not owner._retired


@pytest.mark.parametrize("change_args", [False, True])
async def test_replaced_registration_or_arguments_never_remove_foreign_slot(
    pair, monkeypatch, change_args
):
    left, _ = pair
    loop = asyncio.get_running_loop()
    retained, removals = [], []
    original_remove = readiness._remove_reader
    def remove(*args):
        removals.append(True)
        return original_remove(*args)
    monkeypatch.setattr(readiness, "_remove_reader", remove)
    async def reader():
        owner = readiness.SelectorReadiness(left)
        retained.append(owner)
        await owner.wait(end())
    task = asyncio.create_task(reader())
    await asyncio.sleep(0)
    owner = retained[0]
    if change_args:
        current = loop._selector.get_key(left.fileno()).data[0]
        current._args = (owner._token_snapshot,)  # same value, different captured tuple
    else:
        loop.add_reader(left.fileno(), lambda: None)
        current = loop._selector.get_key(left.fileno()).data[0]
    owner._future_snapshot.set_result(None)
    with pytest.raises(FrameError):
        await task
    assert removals == [] and not owner._retired and owner._unknown
    assert loop._selector.get_key(left.fileno()).data[0] is current


async def test_current_writer_subscription_survives_read_retirement(pair):
    left, right = pair
    loop = asyncio.get_running_loop()
    loop.add_writer(left.fileno(), lambda: None)
    retained = []
    async def reader():
        owner = readiness.SelectorReadiness(left)
        retained.append(owner)
        await owner.wait(end())
    task = asyncio.create_task(reader())
    await asyncio.sleep(0)
    loop.add_writer(left.fileno(), lambda: None)  # legitimate writer changed during wait
    writer = loop._selector.get_key(left.fileno()).data[1]
    right.send(b"SYNTHETIC_WRITER_PRESERVED")
    await task
    slots = loop._selector.get_key(left.fileno()).data
    assert slots[0] is None and slots[1] is writer and retained[0]._retired
    assert left.recv(64) == b"SYNTHETIC_WRITER_PRESERVED"


@pytest.mark.parametrize("after", [False, True])
async def test_partial_add_failure_needs_positive_owned_registration_observation(
    pair, monkeypatch, after
):
    left, _ = pair
    install = readiness._install_reader
    def fail(*args):
        if after:
            install(*args)
        raise OSError("synthetic partial add ambiguity")
    monkeypatch.setattr(readiness, "_install_reader", fail)
    owner = readiness.SelectorReadiness(left)
    with pytest.raises(FrameError):
        await owner.wait(end())
    assert owner._unknown and owner._retired is after
    assert owner._handle_snapshot is not None if after else owner._handle_snapshot is None


@pytest.mark.parametrize("after", [False, True])
async def test_future_allocation_is_retained_before_ambiguous_initialization(
    pair, monkeypatch, after
):
    left, _ = pair
    owner = readiness.SelectorReadiness.__new__(readiness.SelectorReadiness)
    initialize = readiness._initialize_future
    seen = []
    def fail(future, loop):
        seen.append(future)
        assert owner._future_snapshot is future and owner._future is future
        if after:
            initialize(future, loop)
        raise OSError("synthetic future initialization ambiguity")
    monkeypatch.setattr(readiness, "_initialize_future", fail)
    with pytest.raises(readiness.ReadinessAcquisitionError) as error:
        readiness.SelectorReadiness.__init__(owner, left)
    assert error.value.owner is owner and owner._future_snapshot is seen[0]
    assert not owner._future_initialized and not owner._attempted
    owner._retire()  # must not invoke methods on the ambiguously initialized Future
    assert owner._unknown and not owner._retired
    if after:
        assert not readiness._FUTURE.done(seen[0])  # injected native phase is known only to test


async def test_foreign_actor_cannot_install_or_remove_registration(pair):
    owner = readiness.SelectorReadiness(pair[0])
    task = asyncio.create_task(owner.wait(end()))
    with pytest.raises(FrameError):
        await task
    assert not owner._attempted


async def test_paired_scope_retarget_refuses_before_installing_on_other_socket(pair, monkeypatch):
    left, right = pair
    owner = readiness.SelectorReadiness(left)
    other = readiness.SelectorReadiness(right)
    original_scope = owner._scope_snapshot
    installs = []
    install = readiness._install_reader
    def watch(*args):
        installs.append(args[1])
        return install(*args)
    monkeypatch.setattr(readiness, "_install_reader", watch)
    owner._scope = owner._scope_snapshot = other._scope_snapshot
    with pytest.raises(FrameError):
        await owner.wait(end())
    assert installs == [] and owner._unknown and not other._attempted
    owner._scope = owner._scope_snapshot = original_scope
    with pytest.raises(FrameError):
        await owner.wait(end())  # restoring fields cannot revive the refused owner
    assert installs == []


async def test_writer_change_during_remove_is_unknown_and_foreign_writer_remains(pair, monkeypatch):
    left, right = pair
    loop = asyncio.get_running_loop()
    loop.add_writer(left.fileno(), lambda: None)
    remove = readiness._remove_reader
    after = []
    def changed(*args):
        value = remove(*args)
        loop.add_writer(left.fileno(), lambda: None)
        after.append(loop._selector.get_key(left.fileno()).data[1])
        return value
    monkeypatch.setattr(readiness, "_remove_reader", changed)
    owner = readiness.SelectorReadiness(left)
    right.send(b"SYNTHETIC_WRITE_SLOT_DRIFT")
    with pytest.raises(FrameError):
        await owner.wait(end())
    assert owner._unknown and not owner._retired
    assert loop._selector.get_key(left.fileno()).data[1] is after[0]
    assert left.recv(64) == b"SYNTHETIC_WRITE_SLOT_DRIFT"


@pytest.mark.parametrize("invalid", [True, 0, -1, 1 << 63, "later", None])
async def test_invalid_deadline_cannot_install_or_allocate_another_wait(pair, monkeypatch, invalid):
    owner = readiness.SelectorReadiness(pair[0])
    calls = []
    monkeypatch.setattr(readiness, "_install_reader", lambda *args: calls.append(args))
    with pytest.raises(FrameError):
        await owner.wait(invalid)
    assert calls == [] and not owner._attempted


async def test_foreign_retirement_cannot_cancel_original_metadata_future(pair):
    owner = readiness.SelectorReadiness(pair[0])
    async def foreign():
        owner._retire()
    task = asyncio.create_task(foreign())
    with pytest.raises(FrameError):
        await task
    assert not owner._future_snapshot.done() and not owner._attempted
    assert not owner._retired and not owner._unknown


async def test_real_peer_eof_is_readiness_and_original_task_receives_empty_bytes(pair):
    left, right = pair
    owner = readiness.SelectorReadiness(left)
    right.close()  # Darwin changes permission bits, not the socket's file type
    await owner.wait(end())
    assert owner._retired and not owner._unknown
    assert left.recv(64) == b""


@pytest.mark.parametrize("target,name", [
    ("loop", "_add_reader"), ("loop", "_remove_reader"),
    ("loop", "_check_closed"), ("loop", "is_closed"), ("loop", "get_debug"),
    ("loop", "call_soon"), ("loop", "_call_soon"), ("loop", "call_at"),
    ("loop", "time"), ("loop", "_timer_handle_cancelled"),
    ("loop", "_check_thread"), ("loop", "_check_callback"),
    ("selector", "get_key"), ("selector", "modify"), ("selector", "register"),
    ("selector", "unregister"), ("selector", "_fileobj_lookup"),
])
async def test_instance_dispatch_override_refuses_before_foreign_callback(
    pair, monkeypatch, target, name
):
    loop = asyncio.get_running_loop()
    owner = readiness.SelectorReadiness(pair[0])
    calls = []
    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError("foreign dispatch ran")
    object_target = loop if target == "loop" else loop._selector
    with monkeypatch.context() as patch:
        patch.setattr(object_target, name, foreign)
        with pytest.raises(FrameError):
            await owner.wait(end())
    assert calls == [] and not owner._attempted


async def test_remove_override_after_install_is_not_invoked_and_preserves_slot(pair, monkeypatch):
    left, _ = pair
    loop = asyncio.get_running_loop()
    held, calls = [], []
    async def reader():
        owner = readiness.SelectorReadiness(left)
        held.append(owner)
        await owner.wait(end())
    task = asyncio.create_task(reader())
    await asyncio.sleep(0)
    handle = loop._selector.get_key(left.fileno()).data[0]
    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError("foreign remove ran")
    with monkeypatch.context() as patch:
        patch.setattr(loop, "_remove_reader", foreign)
        held[0]._future_snapshot.set_result(None)
        with pytest.raises(FrameError):
            await task
    assert calls == [] and held[0]._unknown and not held[0]._retired
    assert loop._selector.get_key(left.fileno()).data[0] is handle


async def test_constructor_fences_debug_override_before_native_future_init(pair, monkeypatch):
    loop = asyncio.get_running_loop()
    calls = []
    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError("foreign debug hook ran")
    with monkeypatch.context() as patch:
        patch.setattr(loop, "get_debug", foreign)
        with pytest.raises(readiness.ReadinessAcquisitionError) as error:
            readiness.SelectorReadiness(pair[0])
    assert calls == [] and error.value.owner._future_snapshot is None


@pytest.mark.parametrize("field", ["events", "fileobj"])
async def test_selector_key_field_drift_refuses_before_foreign_dispatch(pair, monkeypatch, field):
    left, _ = pair
    loop = asyncio.get_running_loop()
    held, callbacks, removals = [], [], []
    class Foreign:
        def __eq__(self, value):
            callbacks.append("eq")
            raise AssertionError("foreign selector field equality")
        def __and__(self, value):
            callbacks.append("and")
            raise AssertionError("foreign selector event mask")
    async def reader():
        owner = readiness.SelectorReadiness(left)
        held.append(owner)
        await owner.wait(end())
    task = asyncio.create_task(reader())
    await asyncio.sleep(0)
    key = loop._selector.get_key(left.fileno())
    loop._selector._fd_to_key[left.fileno()] = key._replace(**{field: Foreign()})
    monkeypatch.setattr(readiness, "_remove_reader", lambda *args: removals.append(args))
    try:
        held[0]._future_snapshot.set_result(None)
        with pytest.raises(FrameError):
            await task
        assert callbacks == [] and removals == [] and held[0]._unknown
    finally:
        loop._selector._fd_to_key[left.fileno()] = key  # test disposal after refusal


@pytest.mark.parametrize("name", ["call_soon", "_call_soon"])
async def test_callback_failure_does_not_redispatch_through_foreign_scheduler(
    pair, monkeypatch, name
):
    left, _ = pair
    loop = asyncio.get_running_loop()
    held, calls = [], []
    async def reader():
        owner = readiness.SelectorReadiness(left)
        held.append(owner)
        await owner.wait(end())
    task = asyncio.create_task(reader())
    await asyncio.sleep(0)
    owner = held[0]
    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError("foreign scheduler ran")
    with monkeypatch.context() as patch:
        patch.setattr(loop, name, foreign)
        owner._readable(owner._token_snapshot)
        assert not owner._future_origin.done()  # failure cannot schedule through unsafe hook
    task.cancel()
    with pytest.raises(FrameError):
        await task
    assert calls == [] and owner._unknown and owner._retired


async def test_current_future_retarget_does_not_mutate_foreign_future(pair):
    left, _ = pair
    loop = asyncio.get_running_loop()
    held = []
    async def reader():
        owner = readiness.SelectorReadiness(left)
        held.append(owner)
        await owner.wait(end())
    task = asyncio.create_task(reader())
    await asyncio.sleep(0)
    owner = held[0]
    original = owner._future_origin
    other = loop.create_future()
    owner._future = owner._future_snapshot = other
    owner._readable(owner._token_snapshot)
    with pytest.raises(FrameError):
        await task
    assert not other.done() and original.done() and owner._unknown
    other.cancel()  # test-owned disposal only


async def test_elapsed_valid_end_is_known_no_registration_timeout(pair):
    left, right = pair
    owner = readiness.SelectorReadiness(left)
    with pytest.raises(TimeoutError):
        await owner.wait(time.monotonic_ns() - 1)
    assert not owner._attempted and not owner._unknown
    right.send(b"SYNTHETIC_NOT_CONSUMED")
    assert left.recv(64) == b"SYNTHETIC_NOT_CONSUMED"


async def test_completed_wake_precedes_registration_readiness_and_expiry(pair):
    left, right = pair
    right.send(b"SYNTHETIC_ALREADY_READABLE")
    cause = asyncio.get_running_loop().create_future()
    cause.set_result(None)
    owner = readiness.SelectorReadiness(left)
    with pytest.raises(readiness.ReadinessWakeError):
        await owner.wait(time.monotonic_ns() - 1, wake=cause)
    assert not owner._attempted and not owner._unknown and not cause.cancelled()
    assert left.recv(64) == b"SYNTHETIC_ALREADY_READABLE"


@pytest.mark.parametrize("hint", [False, True])
async def test_original_wait_wake_retires_subscription_without_payload_or_shared_cancel(pair, hint):
    left, right = pair
    cause = asyncio.get_running_loop().create_future()
    retained = []

    async def wait():
        owner = readiness.SelectorReadiness(left)
        retained.append(owner)
        await owner.wait(time.monotonic_ns() + 1_000_000_000, wake=cause)

    task = asyncio.create_task(wait())
    await asyncio.sleep(0)
    owner = retained[0]
    assert owner._attempted and not owner._retired
    right.send(b"SYNTHETIC_REVOKED_BYTES")
    if hint:
        owner._readable(owner._token)  # exact original callback, before Task resumes
        assert owner._future_origin.done()
    cause.set_result(None)
    with pytest.raises(readiness.ReadinessWakeError):
        await task
    assert owner._retired and not owner._unknown
    assert cause.done() and not cause.cancelled() and cause.result() is None
    assert left.recv(64) == b"SYNTHETIC_REVOKED_BYTES"


async def test_external_task_cancel_stays_cancelled_with_simultaneous_wake(pair):
    left, right = pair
    cause = asyncio.get_running_loop().create_future()
    retained = []

    async def wait():
        owner = readiness.SelectorReadiness(left)
        retained.append(owner)
        await owner.wait(time.monotonic_ns() + 1_000_000_000, wake=cause)

    task = asyncio.create_task(wait())
    await asyncio.sleep(0)
    cause.set_result(None)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert retained[0]._retired and not retained[0]._unknown
    assert cause.done() and not cause.cancelled()
    right.send(b"SYNTHETIC_AFTER_CANCEL")
    assert left.recv(64) == b"SYNTHETIC_AFTER_CANCEL"


async def test_wake_pair_retarget_cannot_touch_other_future(pair):
    left, _ = pair
    loop = asyncio.get_running_loop()
    cause, other = loop.create_future(), loop.create_future()
    retained = []

    async def wait():
        owner = readiness.SelectorReadiness(left)
        retained.append(owner)
        await owner.wait(time.monotonic_ns() + 1_000_000_000, wake=cause)

    task = asyncio.create_task(wait())
    await asyncio.sleep(0)
    owner = retained[0]
    owner._wake = owner._wake_snapshot = other
    cause.set_result(None)
    with pytest.raises(FrameError):
        await task
    assert owner._unknown and not owner._retired
    assert not other.done() and not cause.cancelled()


async def test_foreign_create_future_dispatch_is_refused_before_future_init(pair, monkeypatch):
    loop = asyncio.get_running_loop()
    calls = []
    with monkeypatch.context() as change:
        change.setattr(loop, "create_future", lambda: calls.append(True))
        with pytest.raises(readiness.ReadinessAcquisitionError):
            readiness.SelectorReadiness(pair[0])
    assert calls == []
