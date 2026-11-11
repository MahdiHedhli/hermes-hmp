"""Real Store/bearers, temporary files and native threads; synthetic bot bridge.

No actual GatewayRunner/listener/HTTP/device qualification follows. Fault tests
retain unresolved service debt and verify actual synthetic threads have ended
before fixture-only database disposal; they do not certify production drain.
"""

import asyncio
import hashlib
import json
import os
import threading
from types import SimpleNamespace

import pytest

from hmp_plugin.contract import AuthzState, ErrorCode, HmpError
from hmp_plugin.presentation_native_projection import NativePresentationProjection
from hmp_plugin.presentation_native_service import (
    NativePresentationOwner,
    NativePresentationUnavailableError,
)
from hmp_plugin.store import Store
from hmp_plugin.wire import b64u_encode


@pytest.fixture
def env(tmp_path):
    root = tmp_path.resolve()
    store = Store(root / "synthetic.sqlite3")
    store.migrate()
    iid, token = "a" * 52, b"A" * 32
    store.insert_user("user", "synthetic", 1000)
    store.insert_device(
        "device", "user", "synthetic", b"synthetic", "synthetic", 1000, state="ACTIVE"
    )
    store.insert_token_family("family", "device", 1000)
    store.insert_access_token(hashlib.sha256(token).digest(), "family", "device", iid, 100000)
    e = SimpleNamespace(
        store=store,
        iid=iid,
        authorization="Bearer " + b64u_encode(token),
        homes={},
        calls=[],
        gate=None,
        states={},
        services=[],
        live=True,
        worker_live=True,
    )

    def add(profile):
        home = root / profile
        home.mkdir(mode=0o700)
        path = home / "profile.yaml"
        path.write_bytes(b"display_name: Synthetic native fixture\n")
        path.chmod(0o600)
        for item in (home, path):
            os.chown(item, os.geteuid(), os.getegid())
        e.homes[profile] = home
        return home

    def home(profile):
        e.calls.append((profile, threading.get_ident()))
        if e.gate is not None:
            e.gate(profile)
        return e.homes[profile]

    def authz(user, profile):
        assert user == "user"
        return e.states.get(
            profile, AuthzState.AUTHORIZED if profile in e.homes else AuthzState.NOT_SERVED
        )

    e.add = add
    e.add("belac")
    e.ctx = SimpleNamespace(
        store=store,
        iid=iid,
        now=lambda: 1000,
        bridge=SimpleNamespace(authz_state=authz, _profile_home=home),
        identity=SimpleNamespace(still_current=lambda: e.live),
    )
    yield e
    # Faults may deliberately leave unknown *accounting* debt; never leave a
    # real synthetic worker accessing the DB on fixture cleanup.
    for service in e.services:
        for op in service._ops.values():
            assert op.worker is None or not op.worker.is_alive()
    store.close()


def bind(env):
    owner = NativePresentationOwner()
    service = owner.bind(env.ctx, current=lambda: env.live, worker_current=lambda: env.worker_live)
    env.services.append(service)
    return owner, service


def submit(env, service, profile="belac", **kwargs):
    return service.submit(env.authorization, env.iid, profile, **kwargs)


async def until(predicate):
    deadline = asyncio.get_running_loop().time() + 3.0
    while not predicate():
        assert asyncio.get_running_loop().time() < deadline
        await asyncio.sleep(0.005)


@pytest.mark.asyncio
async def test_real_bearer_source_thread_join_status_mailbox_and_explicit_discard(env):
    owner, service = bind(env)
    main_thread = threading.get_ident()
    before = tuple(env.store.get_device("device"))
    handle = submit(env, service)
    assert not hasattr(handle, "result")
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    assert op.future.result() is None and op.joined and not op.worker.is_alive()
    assert all(thread != main_thread for _, thread in env.calls)
    assert json.loads(op.result.metadata)["display_name"] == "Synthetic native fixture"
    assert op.memory.snapshot()[0] > 0
    assert tuple(env.store.get_device("device")) == before
    with pytest.raises(NativePresentationUnavailableError, match="previous_generation_not_drained"):
        owner.bind(env.ctx, current=lambda: True, worker_current=lambda: env.worker_live)
    service.abandon(handle)
    assert op.result is None and op.memory.snapshot()[:2] == (0, 0) and not service._ops
    assert await service.close_and_join() is True
    replacement = owner.bind(
        env.ctx, current=lambda: env.live, worker_current=lambda: env.worker_live
    )
    env.services.append(replacement)
    assert replacement._registry is not service._registry
    assert await replacement.close_and_join() is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state",
    [
        AuthzState.NOT_SERVED,
        AuthzState.NOT_ROUTED,
        AuthzState.PENDING_OPERATOR,
        AuthzState.UNVERIFIABLE,
    ],
)
async def test_native_bot_policy_refuses_before_any_home_or_file(env, state):
    _, service = bind(env)
    env.states["belac"] = state
    handle = submit(env, service)
    assert await service.wait(handle) == "bot_" + state.value
    assert not env.calls
    op = service._ops[handle]
    assert op.result is None and op.memory.snapshot()[:2] == (0, 0)
    service.abandon(handle)
    assert await service.close_and_join() is True


@pytest.mark.asyncio
@pytest.mark.parametrize("wrong", ["instance", "bearer"])
async def test_original_authentication_precedes_admission_and_native_lookup(env, wrong):
    _, service = bind(env)
    with pytest.raises(HmpError) as error:
        service.submit(
            "bad" if wrong == "bearer" else env.authorization,
            "b" * 52 if wrong == "instance" else env.iid,
            "belac",
        )
    assert error.value.code is (
        ErrorCode.WRONG_INSTANCE if wrong == "instance" else ErrorCode.UNAUTHENTICATED
    )
    assert not service._ops and not env.calls
    assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_cancellation_and_close_cannot_release_blocked_native_worker_or_replace_generation(
    env,
):
    owner, service = bind(env)
    entered, release = threading.Event(), threading.Event()

    def gate(profile):
        entered.set()
        assert release.wait(5)

    env.gate = gate
    handle = submit(env, service)
    waiting_entered = asyncio.Event()

    async def waiting():
        waiting_entered.set()
        return await service.wait(handle)

    task = asyncio.create_task(waiting())
    try:
        await waiting_entered.wait()
        await until(entered.is_set)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        op = service._ops[handle]
        assert op.retired and not op.joined and op.worker.is_alive()
        assert await service.close_and_join(0.02) is False
        assert env.store.get_device("device") is not None  # no store close by the service
        with pytest.raises(NativePresentationUnavailableError):
            owner.bind(env.ctx, current=lambda: True, worker_current=lambda: env.worker_live)
    finally:
        release.set()
        assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_revoke_during_native_wait_is_rechecked_before_source_and_never_returns_payload(env):
    _, service = bind(env)
    entered, release = threading.Event(), threading.Event()
    env.gate = lambda profile: (entered.set(), release.wait(5))
    handle = submit(env, service)
    op = service._ops[handle]
    try:
        await until(entered.is_set)
        env.store.revoke_family("family", 1001)
        release.set()
        assert await service.wait(handle) == "revoked"
        assert op.result is None and op.memory.snapshot() == (0, 0, 0)
    finally:
        release.set()
        assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_changed_source_after_projection_refuses_final_observation(env, monkeypatch):
    _, service = bind(env)
    actual = service._projector.run

    def changed(*args, **kwargs):
        result = actual(*args, **kwargs)
        (env.homes["belac"] / "profile.yaml").write_bytes(b"display_name: Changed after parse\n")
        return result

    monkeypatch.setattr(service._projector, "run", changed)
    handle = submit(env, service)
    assert await service.wait(handle) == "unavailable"
    op = service._ops[handle]
    assert op.result is None and op.memory.snapshot()[:2] == (0, 0)
    assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_one_profile_busy_and_original_two_second_timeout_keep_worker_debt(env):
    _, service = bind(env)
    entered, release = threading.Event(), threading.Event()
    env.gate = lambda profile: (entered.set(), release.wait(5))
    handle = submit(env, service)
    try:
        await until(entered.is_set)
        with pytest.raises(NativePresentationUnavailableError, match="busy"):
            submit(env, service)
        assert await service.wait(handle) == "unavailable"  # actual original2s expires
        op = service._ops[handle]
        assert op.retired and not op.joined and op.worker.is_alive()
        assert len(service._ops) == 1
    finally:
        release.set()
        assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_six_slots_four_metadata_two_avatar_and_sixteen_empty_waiting_descriptors(env):
    _, service = bind(env)
    release = threading.Event()
    env.gate = lambda profile: release.wait(5)
    handles = []
    try:
        for index in range(23):
            env.add(f"bot{index}")
        for index in range(6):
            handles.append(
                submit(env, service, f"bot{index}", kind="metadata" if index < 4 else "avatar")
            )
        await until(lambda: len({profile for profile, _ in env.calls}) == 6)
        for index in range(6, 22):
            handles.append(submit(env, service, f"bot{index}"))
        assert len(service._ops) == 22 and len(service._queue) == 16
        active = [op for op in service._ops.values() if op.state != "waiting"]
        assert len(active) == 6 and sum(op.kind == "metadata" for op in active) == 4
        for handle in service._queue:
            op = service._ops[handle]
            assert op.worker is None and op.result is None and op.memory.snapshot() == (0, 0, 0)
        with pytest.raises(NativePresentationUnavailableError, match="busy"):
            submit(env, service, "bot22")
        release.set()
        await until(lambda: all(service._ops[h].joined for h in handles[:6]))
        # Finished results STILL own their six slots; queued requests cannot start.
        assert len({profile for profile, _ in env.calls}) == 6 and len(service._queue) == 16
    finally:
        release.set()
        assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_ambiguous_start_without_target_entry_never_resets_pool(env):
    owner, service = bind(env)

    class NoLaunch(threading.Thread):
        def start(self):
            raise OSError("synthetic start uncertainty")

    service._thread_type = NoLaunch  # internal fault port, never request-selected
    handle = submit(env, service)
    assert await service.wait(handle) == "unavailable"
    assert await service.close_and_join(0.02) is False
    op = service._ops[handle]
    assert op.start_uncertain and not op.entered and not op.joined
    with pytest.raises(NativePresentationUnavailableError):
        owner.bind(env.ctx, current=lambda: True, worker_current=lambda: env.worker_live)


@pytest.mark.asyncio
async def test_unknown_join_is_retained_and_not_retried(env, monkeypatch):
    owner, service = bind(env)
    original = threading.Thread.join
    calls = []

    def unknown_join(worker, *args, **kwargs):
        original(worker, *args, **kwargs)
        calls.append(worker)
        raise OSError("synthetic lost join acknowledgement")

    monkeypatch.setattr(threading.Thread, "join", unknown_join)
    handle = submit(env, service)
    await until(lambda: service._ops[handle].join_unknown)
    assert len(calls) == 1
    service.abandon(handle)
    assert await service.close_and_join(0.02) is False and len(calls) == 1
    with pytest.raises(NativePresentationUnavailableError):
        owner.bind(env.ctx, current=lambda: True, worker_current=lambda: env.worker_live)


@pytest.mark.asyncio
async def test_unknown_file_close_retains_capacity_and_blocks_listener_replacement(env):
    owner, service = bind(env)
    ops = service._reader._ops
    original = ops.close
    failed, calls = [], []

    def lost(fd):
        original(fd)
        calls.append(fd)
        if not failed:
            failed.append(fd)
            raise OSError("synthetic lost close acknowledgement")

    ops.close = lost
    handle = submit(env, service)
    assert await service.wait(handle) == "unavailable"
    op = service._ops[handle]
    assert op.joined and op.claim._unknown and op.result is None
    service.abandon(handle)
    assert op.state == "debt" and op.memory.snapshot()[:2] == (0, 0)
    assert calls.count(failed[0]) == 1
    assert await service.close_and_join(0.02) is False
    with pytest.raises(NativePresentationUnavailableError):
        owner.bind(env.ctx, current=lambda: True, worker_current=lambda: env.worker_live)


@pytest.mark.asyncio
async def test_foreign_handle_cannot_touch_or_release_another_service(env):
    _, a = bind(env)
    _, b = bind(env)
    handle = submit(env, a)
    assert await b.wait(handle) == "unavailable"
    b.abandon(handle)
    assert await a.wait(handle) == "ready" and handle in a._ops
    a.abandon(handle)
    assert await a.close_and_join() and await b.close_and_join()


@pytest.mark.asyncio
async def test_revocation_precedes_precise_native_failure_disclosure(env):
    _, service = bind(env)
    entered, release = threading.Event(), threading.Event()

    def refusal(user, profile):
        entered.set()
        assert release.wait(5)
        return AuthzState.NOT_SERVED

    env.ctx.bridge.authz_state = refusal
    handle = submit(env, service)
    try:
        await until(entered.is_set)
        env.store.revoke_family("family", 1001)
        release.set()
        assert await service.wait(handle) == "revoked"  # never bot_not_served
        assert not env.calls and handle not in service._ops
    finally:
        release.set()
        assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_home_rebinding_after_parse_cannot_publish_old_profile_result(env):
    _, service = bind(env)
    replacement = env.add("replacement")
    seen = []

    def change(profile):
        seen.append(profile)
        if len(seen) == 3:
            env.homes["belac"] = replacement

    env.gate = change
    handle = submit(env, service)
    assert await service.wait(handle) == "unavailable"
    op = service._ops[handle]
    assert op.result is None and op.memory.snapshot()[:2] == (0, 0)
    assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_listener_identity_change_during_native_wait_prevents_source_read(env):
    _, service = bind(env)
    entered, release = threading.Event(), threading.Event()
    env.gate = lambda profile: (entered.set(), release.wait(5))
    handle = submit(env, service)
    op = service._ops[handle]
    try:
        await until(entered.is_set)
        env.ctx.identity = SimpleNamespace(still_current=lambda: True)
        release.set()
        assert await service.wait(handle) == "unavailable"
        assert op.result is None and op.memory.snapshot() == (0, 0, 0)
    finally:
        release.set()
        assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_waiting_request_expires_on_original_deadline_without_entering_native_home(env):
    _, service = bind(env)
    release = threading.Event()
    env.gate = lambda profile: release.wait(5)
    try:
        for index in range(5):
            env.add(f"waiting{index}")
        for index in range(4):
            submit(env, service, f"waiting{index}")
        await until(lambda: len(env.calls) == 4)
        handle = submit(env, service, "waiting4")
        op = service._ops[handle]
        assert op.state == "waiting"
        assert await service.wait(handle) == "unavailable"
        assert op.worker is None and op.joined and op.memory.snapshot() == (0, 0, 0)
        assert all(profile != "waiting4" for profile, _ in env.calls)
        assert len(service._ops) == 4  # actual blocked workers keep their slots
    finally:
        release.set()
        assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_lost_start_ack_can_settle_only_after_actual_target_entry_and_join(env):
    _, service = bind(env)

    class LostStartAck(threading.Thread):
        def start(self):
            super().start()
            raise OSError("synthetic lost start acknowledgement after actual launch")

    service._thread_type = LostStartAck
    handle = submit(env, service)
    assert await service.wait(handle) == "unavailable"
    assert await service.close_and_join() is True
    assert not service._ops and service.drained


@pytest.mark.asyncio
@pytest.mark.parametrize("fence", ["listener", "identity"])
async def test_worker_currentness_change_without_retire_blocks_remaining_source_work(env, fence):
    _, service = bind(env)
    entered, release = threading.Event(), threading.Event()
    env.gate = lambda profile: (entered.set(), release.wait(5))
    handle = submit(env, service)
    op = service._ops[handle]
    try:
        await until(entered.is_set)
        if fence == "listener":
            env.worker_live = False
        else:
            env.ctx.identity.still_current = lambda: False
        release.set()
        assert await service.wait(handle) == "unavailable"
        assert not service.available and op.memory.snapshot() == (0, 0, 0)
        assert op.result is None and len(env.calls) == 1
    finally:
        release.set()
        assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_revoke_during_authorized_policy_wait_precedes_home_resolution(env):
    _, service = bind(env)
    entered, release = threading.Event(), threading.Event()

    def policy(user, profile):
        entered.set()
        assert release.wait(5)
        return AuthzState.AUTHORIZED

    env.ctx.bridge.authz_state = policy
    handle = submit(env, service)
    op = service._ops[handle]
    try:
        await until(entered.is_set)
        env.store.revoke_family("family", 1001)
        release.set()
        assert await service.wait(handle) == "revoked"
        assert not env.calls and op.memory.snapshot() == (0, 0, 0)
    finally:
        release.set()
        assert await service.close_and_join() is True


@pytest.mark.asyncio
async def test_failed_postprojection_cleanup_retains_actual_result_and_settles_status(
    env, monkeypatch
):
    owner, service = bind(env)
    actual_run = service._projector.run
    actual_discard = NativePresentationProjection.discard
    failed, unhandled = [], []

    def projected(*args, **kwargs):
        result = actual_run(*args, **kwargs)
        # Final source check must fail AFTER the producer returns its real result.
        (env.homes["belac"] / "profile.yaml").write_bytes(b"display_name: Changed\n")
        return result

    def unknown(result):
        failed.append(result)
        raise OSError("synthetic cleanup acknowledgement lost")

    monkeypatch.setattr(service._projector, "run", projected)
    monkeypatch.setattr(NativePresentationProjection, "discard", unknown)
    monkeypatch.setattr(threading, "excepthook", lambda args: unhandled.append(True))
    handle = submit(env, service)
    try:
        assert await asyncio.wait_for(service.wait(handle), 1.0) == "unavailable"
        op = service._ops[handle]
        assert op.joined and op.cleanup_unknown and op.state == "debt"
        assert op.result is failed[0] and op.memory.snapshot()[0] > 0
        assert op.future.result() is None and not unhandled
        assert await service.close_and_join(0.02) is False
        assert len(failed) == 1  # no ambiguous cleanup retry
        with pytest.raises(NativePresentationUnavailableError):
            owner.bind(env.ctx, current=lambda: True, worker_current=lambda: True)
    finally:
        # Fixture-only buffer disposal, not a service debt reset/drain pass.
        for result in failed:
            actual_discard(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("retirement", ["abandon", "expire"])
async def test_loop_cleanup_failure_retains_slot_and_result_without_hanging_wait(
    env, monkeypatch, retirement
):
    owner, service = bind(env)
    handle = submit(env, service)
    assert await service.wait(handle) == "ready"
    op = service._ops[handle]
    actual_discard = NativePresentationProjection.discard
    calls = []

    def unknown(result):
        calls.append(result)
        raise OSError("synthetic loop cleanup uncertainty")

    monkeypatch.setattr(NativePresentationProjection, "discard", unknown)
    try:
        if retirement == "abandon":
            service.abandon(handle)
        else:
            service._expire(handle)
        assert await asyncio.wait_for(service.wait(handle), 0.2) == "unavailable"
        assert op.result is calls[0] and op.cleanup_unknown and op.memory.snapshot()[0] > 0
        assert op.future.result() is None and op.state == "debt"
        assert await service.close_and_join(0.02) is False and len(calls) == 1
        with pytest.raises(NativePresentationUnavailableError):
            owner.bind(env.ctx, current=lambda: True, worker_current=lambda: True)
    finally:
        actual_discard(op.result)  # synthetic test cleanup; service debt remains
