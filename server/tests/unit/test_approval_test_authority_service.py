"""AT1 causal fake ports only; no native modules/listeners/providers are installed."""

from __future__ import annotations

import asyncio
import os
import threading
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from aiohttp.test_utils import make_mocked_request

from hmp_plugin.approval_test_authority import AuthorityUnavailable
from hmp_plugin.approval_test_host_codec import (
    HostBeginRequest,
    HostGeneration,
    HostOperationRequest,
)
from hmp_plugin.approval_test_producer import (
    TestBeginReceipt,
    TestCleanupReceipt,
    TestControlReceipt,
    TestNotice,
    TestOutcome,
    TestStatus,
)
from hmp_plugin.approval_test_service import ApprovalTestService
from hmp_plugin.contract import ApprovalTestTarget, AuthzState
from hmp_plugin.request_ctx import CTX_KEY, ServerContext

IID = 'a' * 52


class Store:
    def __init__(self) -> None:
        self.device = {
            'device_id': 'phone', 'user_id': 'owner', 'device_fp': 'fp', 'state': 'ACTIVE',
        }
        self.family = {'family_id': 'family', 'device_id': 'phone', 'revoked_at': None}
        self.token = {'iid': IID, 'family_id': 'family', 'device_id': 'phone', 'expires_at': 2000}
        self.controls: bool | None = None

    def get_device(self, device_id):
        return self.device if device_id == 'phone' else None

    def get_access_token(self, _digest):
        return self.token

    def get_token_family(self, _family):
        return self.family

    def owner_controls_decision(self, _device):
        return self.controls


class Bridge:
    def __init__(self) -> None:
        self.target = ApprovalTestTarget(Path('/synthetic/profile'), 'root', 'tip')
        self.profiles = ['bot']
        self.authorized = True
        self.calls = 0
        self.block: threading.Event | None = None
        self.entered = threading.Event()

    def served_profiles(self):
        return self.profiles

    def authz_state(self, _user, _profile):
        return AuthzState.AUTHORIZED if self.authorized else AuthzState.UNVERIFIABLE

    def approval_test_target(self, _profile):
        self.calls += 1
        self.entered.set()
        if self.block is not None:
            assert self.block.wait(5)
        return self.target

    def resolve_bot_chat(self, *_args):
        raise AssertionError('ordinary resolver forbidden')

    def get_messages(self, *_args):
        raise AssertionError('message access forbidden')


class Ctx:
    is_approval_owner_device = ServerContext.is_approval_owner_device

    def __init__(self) -> None:
        self.iid = IID
        self.store = Store()
        self.bridge = Bridge()
        self.current = True
        self.available = True
        self.enabled = True
        self.owners = frozenset({'phone'})
        self.identity = SimpleNamespace(still_current=lambda: self.current)

    def owner_device_ids(self):
        return self.owners

    def now(self):
        return 1000

    def is_approvals_available(self):
        return self.available

    def direct_send_effective(self):
        return self.enabled


class Producer:
    def __init__(self, publish, remove) -> None:
        self.publish = publish
        self.remove = remove
        self.notice = None
        self.begin_calls = 0
        self.answer_calls = []
        self.cancel_calls = 0
        self.close_calls = 0
        self.join_calls = 0
        self.status = TestStatus.PENDING
        self.done = asyncio.Event()
        self.joinable = asyncio.Event()
        self.joinable.set()
        self.partial = False
        self.emit = True
        self.bad_deadline = False
        self.begin_hook = None

    async def begin_test(self, binding, timeout_ms):
        self.begin_calls += 1
        deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
        if self.emit:
            self.notice = TestNotice(
                binding.instance_id, binding.user_id, binding.profile, binding.session_id,
                binding.device_id, 'c' * 32, deadline_monotonic=deadline,
            )
            assert self.publish(self.notice) is True
        if self.begin_hook is not None:
            self.begin_hook()
        if self.partial:
            return TestOutcome(TestStatus.UNAVAILABLE)
        return TestBeginReceipt('d' * 64, deadline + (1 if self.bad_deadline else 0), timeout_ms)

    def settle(self, status):
        if self.status is TestStatus.PENDING:
            self.status = status
        if self.notice is not None:
            assert self.remove(self.notice) is True
        self.done.set()

    async def answer_test(self, _handle, _device, choice):
        self.answer_calls.append(choice)
        self.settle(TestStatus.ONCE_ACKNOWLEDGED if choice == 'once' else TestStatus.DENIED)
        return TestControlReceipt('accepted', TestOutcome(self.status))

    async def cancel_test(self, _handle, _device):
        self.cancel_calls += 1
        self.settle(TestStatus.CANCELLED)
        return TestControlReceipt('accepted', TestOutcome(self.status))

    async def outcome(self, _handle, _device):
        return TestOutcome(self.status)

    # Fake port preserves the reviewed producer's timeout=None call signature.
    async def wait_outcome(self, _handle, _device, timeout=None):  # noqa: ASYNC109
        await self.done.wait()
        return TestOutcome(self.status)

    async def close(self):
        self.close_calls += 1
        self.settle(TestStatus.CANCELLED)
        return TestOutcome(self.status)

    async def close_and_join(self):
        self.join_calls += 1
        await self.joinable.wait()
        return TestCleanupReceipt(True, TestOutcome(self.status))


def rig():
    ctx = Ctx()
    generation = HostGeneration(IID, os.getpid(), 'b' * 32)
    made = []
    gate_calls = []
    gate_hook = []
    setup = []
    alive = [True]
    native = [True]

    async def gate(context, profile, *, member):
        gate_calls.append((context, profile, member))
        await asyncio.sleep(0)
        if gate_hook:
            gate_hook[0]()

    def factory(*, publish, remove):
        value = Producer(publish, remove)
        if setup:
            setup[0](value)
        made.append(value)
        return value

    service = ApprovalTestService(ctx, generation, generation_current=lambda: alive[0],
                                  approvals_gate=gate, producer_factory=factory,
                                  native_current=lambda: native[0])
    request = make_mocked_request('GET', '/', headers={
        'Authorization': 'Bearer ' + 'A' * 43, 'HMP-Instance': IID,
    })
    request.app[CTX_KEY] = ctx
    begin = HostBeginRequest(generation, 'phone', 'bot', 'tip')
    return SimpleNamespace(ctx=ctx, gen=generation, service=service, made=made, phone=request,
                           begin=begin, gate_calls=gate_calls, gate_hook=gate_hook, setup=setup,
                           alive=alive, native=native)


async def admitted(r):
    lease = r.service.responses(r.begin)
    response = await anext(lease)
    assert response.result == 'accepted'
    return lease, response


async def finish(r, lease):
    await lease.aclose()
    await r.service.shutdown()


def test_fixed_card_provisional_callback_and_typed_receipts():
    async def run():
        r = rig()
        provisional = []
        r.setup.append(lambda p: setattr(p, 'begin_hook', lambda: provisional.append(
            r.service._visible(r.service._operation))))
        lease, accepted = await admitted(r)
        assert provisional == [False]
        card = await r.service.phone_card(r.phone, 'bot')
        assert (card.title, card.message, card.choices) == (
            'Synthetic approval test', 'No action will run.', ('once', 'deny'))
        assert card.test_id != accepted.operation_id and card.test_id != 'c' * 32
        with pytest.raises(FrozenInstanceError):
            card.title = 'real action'
        result = await r.service.phone_answer(r.phone, card.test_id, 'once')
        assert result.admission == 'accepted'
        assert await r.service.phone_card(r.phone) is None
        completed = await anext(lease)
        assert completed.state == 'once_acknowledged'
        assert r.made[0].answer_calls == ['once'] and r.made[0].join_calls == 1
        await finish(r, lease)
    asyncio.run(run())


@pytest.mark.parametrize('mutate', [
    lambda r: setattr(r.ctx, 'current', False),
    lambda r: setattr(r.ctx, 'available', False),
    lambda r: setattr(r.ctx, 'enabled', False),
    lambda r: setattr(r.ctx, 'owners', frozenset()),
    lambda r: setattr(r.ctx.store, 'controls', False),
    lambda r: r.ctx.store.device.update(state='PENDING'),
    lambda r: r.ctx.store.device.update(state='REVOKED'),
    lambda r: setattr(r.ctx.bridge, 'profiles', []),
    lambda r: setattr(r.ctx.bridge, 'authorized', False),
    lambda r: setattr(r.ctx.bridge, 'target', None),
    lambda r: setattr(
        r.ctx.bridge, 'target', ApprovalTestTarget(Path('/synthetic/profile'), 'root', 'other')
    ),
    lambda r: r.native.__setitem__(0, False),
])
def test_initial_authority_refuses_before_any_producer(mutate):
    async def run():
        r = rig()
        mutate(r)
        lease = r.service.responses(r.begin)
        assert (await anext(lease)).result == 'unavailable'
        await lease.aclose()
        assert r.made == []
        await r.service.shutdown()
    asyncio.run(run())


def test_controls_grant_alone_never_opens_approval_owner():
    async def run():
        r = rig()
        r.ctx.store.controls = True
        r.ctx.owners = frozenset()
        lease = r.service.responses(r.begin)
        assert (await anext(lease)).result == 'unavailable'
        await lease.aclose()
        assert not r.made
        await r.service.shutdown()
    asyncio.run(run())


@pytest.mark.parametrize('field,value', [
    ('profile_home', Path('/changed')), ('root_session_id', 'changed'),
    ('live_tip_session_id', 'changed'),
])
def test_target_change_during_gate_await_prevents_producer(field, value):
    async def run():
        r = rig()
        r.gate_hook.append(lambda: setattr(
            r.ctx.bridge, 'target', replace(r.ctx.bridge.target, **{field:value})
        ))
        lease = r.service.responses(r.begin)
        assert (await anext(lease)).result == 'unavailable'
        await lease.aclose()
        assert not r.made and r.ctx.bridge.calls == 2
        await r.service.shutdown()
    asyncio.run(run())


@pytest.mark.parametrize('mutate', [
    lambda r: r.ctx.store.family.update(revoked_at=1),
    lambda r: r.ctx.store.family.update(device_id='other'),
    lambda r: r.ctx.store.token.update(expires_at=999),
    lambda r: r.ctx.store.device.update(device_fp='replacement'),
    lambda r: r.ctx.store.device.update(state='REVOKED'),
    lambda r: setattr(r.ctx, 'owners', frozenset()),
])
def test_reauthentication_after_await_fences_without_resolver(mutate):
    async def run():
        r = rig()
        lease, _ = await admitted(r)
        card = await r.service.phone_card(r.phone)
        r.gate_hook.append(lambda: mutate(r))
        result = await r.service.phone_answer(r.phone, card.test_id, 'once')
        assert result.admission == 'unavailable' and r.made[0].answer_calls == []
        assert await r.service.phone_card(r.phone) is None
        await finish(r, lease)
    asyncio.run(run())


def test_foreign_profile_and_id_do_not_cancel_owner():
    async def run():
        r = rig()
        lease, _ = await admitted(r)
        assert await r.service.phone_card(r.phone, 'foreign') is None
        assert (await r.service.phone_answer(r.phone, 'f'*32, 'once')).admission == 'unavailable'
        assert r.made[0].close_calls == 0 and r.made[0].answer_calls == []
        assert await r.service.phone_card(r.phone, 'bot') is not None
        await finish(r, lease)
    asyncio.run(run())


def test_same_user_other_device_is_not_test_target(monkeypatch):
    async def run():
        from hmp_plugin import request_ctx
        from hmp_plugin.auth import AuthContext
        r = rig()
        lease, _ = await admitted(r)
        monkeypatch.setattr(
            request_ctx, 'bearer', lambda _req: AuthContext('other', 'owner', 'other-family')
        )
        assert await r.service.phone_card(r.phone) is None
        assert r.made[0].close_calls == 0 and not r.made[0].answer_calls
        await finish(r, lease)
    asyncio.run(run())


def test_valid_new_family_for_same_device_remains_valid():
    async def run():
        r = rig()
        lease, _ = await admitted(r)
        r.ctx.store.family['family_id'] = 'new-family'
        r.ctx.store.token['family_id'] = 'new-family'
        assert await r.service.phone_card(r.phone) is not None
        await finish(r, lease)
    asyncio.run(run())


def test_native_drift_after_authority_read_has_no_accepted_control():
    async def run():
        r = rig()
        lease, _ = await admitted(r)
        card = await r.service.phone_card(r.phone)
        r.gate_hook.append(lambda: r.native.__setitem__(0, False))
        assert (
            await r.service.phone_answer(r.phone, card.test_id, 'deny')
        ).admission == 'unavailable'
        assert r.made[0].answer_calls == []
        await finish(r, lease)
    asyncio.run(run())


def test_first_answer_fences_concurrent_or_repeated_control():
    async def run():
        r = rig()
        lease, _ = await admitted(r)
        card = await r.service.phone_card(r.phone)
        results = await asyncio.gather(r.service.phone_answer(r.phone, card.test_id, 'deny'),
                                       r.service.phone_answer(r.phone, card.test_id, 'once'))
        assert sum(x.admission == 'accepted' for x in results) == 1
        assert len(r.made[0].answer_calls) == 1
        await finish(r, lease)
    asyncio.run(run())


def test_wrong_generation_and_boolean_timeout_cannot_admit():
    async def run():
        r = rig()
        request = replace(r.begin, generation=replace(r.gen, nonce='e'*32))
        lease = r.service.responses(request)
        assert (await anext(lease)).result == 'unavailable'
        await lease.aclose()
        with pytest.raises(ValueError):
            replace(r.begin, timeout_ms=True)
        assert not r.made
        await r.service.shutdown()
    asyncio.run(run())


def test_callbacks_exact_token_notice_and_removal_idempotence():
    async def run():
        r = rig()
        lease, _ = await admitted(r)
        op = r.service._operation
        notice = r.made[0].notice
        assert r.service.publish(object(), notice) is False
        assert r.service.publish(
            op.identity.closure_token, replace(notice, request_id='f'*32)
        ) is False
        assert r.service.remove(op.identity.closure_token, replace(notice)) is False
        assert r.service.remove(op.identity.closure_token, notice) is True
        assert r.service.remove(op.identity.closure_token, notice) is True
        assert r.service.publish(op.identity.closure_token, notice) is False
        await finish(r, lease)
    asyncio.run(run())


def test_deadline_receipt_mismatch_refuses_but_still_joins():
    async def run():
        r = rig()
        r.setup.append(lambda p: setattr(p, 'bad_deadline', True))
        lease = r.service.responses(r.begin)
        assert (await anext(lease)).result == 'unavailable'
        await lease.aclose()
        assert r.made[0].join_calls == 1 and r.service._operation is None
        await r.service.shutdown()
    asyncio.run(run())


def test_status_before_callback_uses_actual_receipt_deadline():
    async def run():
        r = rig()
        r.setup.append(lambda p: setattr(p, 'emit', False))
        lease, accepted = await admitted(r)
        status = r.service.responses(HostOperationRequest(r.gen, 'status', accepted.operation_id))
        result = await anext(status)
        assert result.state == 'pending' and 0 < result.remaining_ms <= 30000
        assert await r.service.phone_card(r.phone) is None
        await status.aclose()
        await finish(r, lease)
    asyncio.run(run())


def test_partial_start_without_handle_retains_owner_until_actual_join():
    async def run():
        r = rig()
        def setup(p):
            p.partial = True
            p.joinable.clear()
        r.setup.append(setup)
        lease = r.service.responses(r.begin)
        assert (await anext(lease)).result == 'unavailable'
        closing = asyncio.create_task(lease.aclose())
        await asyncio.sleep(0.02)
        assert not closing.done() and r.service._operation is not None
        second = r.service.responses(r.begin)
        assert (await anext(second)).result == 'unavailable'
        await second.aclose()
        assert len(r.made) == 1
        r.made[0].joinable.set()
        await closing
        assert r.service._operation is None
        await r.service.shutdown()
    asyncio.run(run())


def test_write_failure_closes_once_and_observer_cancel_cannot_release_debt():
    async def run():
        r = rig()
        lease, _ = await admitted(r)
        producer = r.made[0]
        producer.joinable.clear()
        observer = asyncio.create_task(r.service.write_failed(r.begin))
        await asyncio.sleep(0.02)
        observer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await observer
        assert r.service._operation is not None and producer.close_calls == 1
        assert not r.service._operation.cleanup.done()
        producer.joinable.set()
        await finish(r, lease)
        assert producer.close_calls == 1 and producer.join_calls == 1
    asyncio.run(run())


def test_host_status_cleanup_remains_available_after_phone_owner_revocation():
    async def run():
        r = rig()
        lease, accepted = await admitted(r)
        r.ctx.owners = frozenset()
        r.ctx.available = False
        status = r.service.responses(HostOperationRequest(r.gen, 'status', accepted.operation_id))
        assert (await anext(status)).result == 'status'
        await status.aclose()
        cancel = r.service.responses(HostOperationRequest(r.gen, 'cancel', accepted.operation_id))
        assert (await anext(cancel)).result == 'cancel_requested'
        await cancel.aclose()
        await finish(r, lease)
    asyncio.run(run())


def test_four_authority_workers_no_fifth_submission_or_cancellation_release():
    async def run():
        r = rig()
        gate = threading.Event()
        r.ctx.bridge.block = gate
        tasks = [
            asyncio.create_task(r.service._authority.select_current_target(r.ctx, r.gen, r.begin))
            for _ in range(4)
        ]
        await asyncio.sleep(0.05)
        assert len(r.service._authority._reads) == 4
        with pytest.raises(AuthorityUnavailable):
            await r.service._authority.select_current_target(r.ctx, r.gen, r.begin)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        assert len(r.service._authority._reads) == 4
        gate.set()
        await r.service.shutdown()
        assert not r.service._authority._reads and not r.made
    asyncio.run(run())


def test_authority_timeout_keeps_worker_until_join_and_never_admits_late():
    async def run():
        r = rig()
        gate = threading.Event()
        r.ctx.bridge.block = gate
        value = await r.service._authority.select_current_target(r.ctx, r.gen, r.begin)
        assert value is None and len(r.service._authority._reads) == 1 and not r.made
        gate.set()
        await r.service.shutdown()
        assert not r.service._authority._reads and not r.made
    asyncio.run(run())


def test_shutdown_observer_cancel_keeps_owned_cleanup_and_reads():
    async def run():
        r = rig()
        lease, _ = await admitted(r)
        r.made[0].joinable.clear()
        task = asyncio.create_task(r.service.shutdown())
        await asyncio.sleep(0.02)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert r.service._retired and r.service._operation is not None
        assert not r.service._shutdown_task.done()
        r.made[0].joinable.set()
        await r.service.shutdown()
        await lease.aclose()
        assert r.service._operation is None
    asyncio.run(run())


def test_partial_read_only_context_replacement_is_not_same_authority():
    async def run():
        r = rig()
        r.gate_hook.append(lambda: setattr(r.ctx, 'bridge', Bridge()))
        lease = r.service.responses(r.begin)
        assert (await anext(lease)).result == 'unavailable'
        await lease.aclose()
        assert not r.made
        await r.service.shutdown()
    asyncio.run(run())


def test_invalid_control_choices_do_not_call_producer():
    async def run():
        r = rig()
        lease, _ = await admitted(r)
        card = await r.service.phone_card(r.phone)
        for value in ['always', '', None, True, 1]:
            assert (
                await r.service.phone_answer(r.phone, card.test_id, value)
            ).admission == 'unavailable'
        assert r.made[0].answer_calls == [] and r.made[0].close_calls == 0
        await finish(r, lease)
    asyncio.run(run())


def test_terminal_record_has_one_bounded_expiry_and_stale_generation_refuses():
    async def run():
        r = rig()
        lease, accepted = await admitted(r)
        r.made[0].settle(TestStatus.DENIED)
        assert (await anext(lease)).result == 'completed'
        assert r.service._terminal_timer is not None
        assert 0 < r.service._terminal.retain_until - asyncio.get_running_loop().time() <= 60
        wrong = r.service.responses(HostOperationRequest(
            replace(r.gen, nonce='e'*32), 'status', accepted.operation_id
        ))
        assert (await anext(wrong)).result == 'unavailable'
        await wrong.aclose()
        await finish(r, lease)
    asyncio.run(run())


def test_expired_projection_fences_and_requests_owner_cleanup():
    async def run():
        r = rig()
        r.begin = replace(r.begin, timeout_ms=40)
        lease, _ = await admitted(r)
        await asyncio.sleep(0.06)
        assert await r.service.phone_card(r.phone) is None
        assert r.made[0].close_calls == 1 and r.made[0].answer_calls == []
        await finish(r, lease)
    asyncio.run(run())


@pytest.mark.parametrize('field,value', [
    ('device_id', 'other'), ('session_id', 'old-tip'), ('instance_id', 'z' * 52),
    ('user_id', 'other'), ('profile', 'other'), ('request_id', 'not-shaped'),
    ('command', 'run something'), ('description', 'not fixed'),
    ('choices', ('deny', 'once')), ('choices', ['once', 'deny']),
    ('deadline_monotonic', True), ('deadline_monotonic', float('nan')),
    ('deadline_monotonic', float('inf')), ('deadline_monotonic', -1.0),
])
def test_invalid_callback_cannot_create_provisional_or_visible_card(field, value):
    async def run():
        r = rig()
        r.setup.append(lambda producer: setattr(producer, 'emit', False))
        lease, _ = await admitted(r)
        op = r.service._operation
        binding = op.selected.binding
        notice = TestNotice(
            binding.instance_id, binding.user_id, binding.profile, binding.session_id,
            binding.device_id, 'c' * 32, deadline_monotonic=op.begin.deadline_monotonic,
        )
        assert r.service.publish(
            op.identity.closure_token, replace(notice, **{field: value})
        ) is False
        assert op.notice is None
        assert await r.service.phone_card(r.phone) is None
        assert r.made[0].answer_calls == []
        await finish(r, lease)
    asyncio.run(run())



def test_host_status_observes_autonomous_cleanup_without_releasing_owner():
    async def run():
        r = rig()
        lease, accepted = await admitted(r)
        op = r.service._operation
        producer = r.made[0]
        producer.joinable.clear()
        producer.status = TestStatus.CLEANUP_PENDING
        assert producer.remove(producer.notice) is True
        completion = asyncio.create_task(anext(lease))
        await asyncio.sleep(0)
        status = r.service.responses(HostOperationRequest(r.gen, 'status', accepted.operation_id))
        result = await anext(status)
        assert result.state == 'cleanup_pending'
        assert op.fenced and r.service._operation is op
        assert r.service._terminal is None and not completion.done()
        assert producer.close_calls == 0 and producer.join_calls == 0
        await status.aclose()
        second = r.service.responses(r.begin)
        assert (await anext(second)).result == 'unavailable'
        await second.aclose()
        assert len(r.made) == 1
        producer.status = TestStatus.EXPIRED
        producer.done.set()
        for _ in range(3):
            await asyncio.sleep(0)
        assert producer.join_calls == 1 and not completion.done()
        assert r.service._operation is op and r.service._terminal is None
        producer.joinable.set()
        completed = await completion
        assert completed.result == 'completed' and completed.state == 'expired'
        assert r.service._operation is None
        assert r.service._terminal.outcome.status is TestStatus.EXPIRED
        await finish(r, lease)
    asyncio.run(run())


@pytest.mark.parametrize('now,expected', [(99.9995, 1), (100.0, 0), (0.0, 1234)])
def test_remaining_milliseconds_ceil_expiry_and_receipt_timeout_cap(now, expected):
    service = object.__new__(ApprovalTestService)
    service._loop = SimpleNamespace(time=lambda: now)
    op = SimpleNamespace(begin=TestBeginReceipt('d' * 64, 100.0, 1234))
    assert service._remaining(op) == expected


def test_authority_thread_start_failure_before_start_releases_only_empty_reservation(monkeypatch):
    async def run():
        r = rig()
        original_start = threading.Thread.start
        original_join = threading.Thread.join
        refused = []
        joins = []

        def fail_before_start(worker, *args, **kwargs):
            if worker.name != 'hmp-at1-authority':
                return original_start(worker, *args, **kwargs)
            refused.append(worker)
            raise RuntimeError('synthetic authority start refused before startup')

        def record_join(worker, *args, **kwargs):
            if worker.name == 'hmp-at1-authority':
                joins.append(worker)
            return original_join(worker, *args, **kwargs)

        monkeypatch.setattr(threading.Thread, 'start', fail_before_start)
        monkeypatch.setattr(threading.Thread, 'join', record_join)
        try:
            # More attempts than the four-slot bound prove empty failures do not leak slots.
            for _ in range(5):
                lease = r.service.responses(r.begin)
                try:
                    assert (await anext(lease)).result == 'unavailable'
                finally:
                    await lease.aclose()
                assert not r.service._authority._reads
                assert r.service._operation is None and r.service._terminal is None
            assert len(refused) == 5 and not joins
            assert all(worker.ident is None and not worker.is_alive() for worker in refused)
            assert r.ctx.bridge.calls == 0 and not r.gate_calls and not r.made
        finally:
            await r.service.shutdown()
    asyncio.run(run())


@pytest.mark.parametrize('observation_end', ['cancel', 'timeout'])
def test_authority_partial_thread_start_holds_four_slots_until_actual_join(
    monkeypatch, observation_end,
):
    async def run():
        r = rig()
        authority = r.service._authority
        release = threading.Event()
        r.ctx.bridge.block = release
        original_start = threading.Thread.start
        original_join = threading.Thread.join
        started = []
        joined = []

        def start_then_raise(worker, *args, **kwargs):
            if worker.name != 'hmp-at1-authority':
                return original_start(worker, *args, **kwargs)
            task = asyncio.current_task()
            owner = next((item for item in authority._reads if item.task is task), None)
            original_start(worker, *args, **kwargs)
            started.append((worker, owner))
            raise RuntimeError('synthetic authority start raised after actual startup')

        def record_join(worker, *args, **kwargs):
            if worker.name != 'hmp-at1-authority':
                return original_join(worker, *args, **kwargs)
            owner = next((item for thread, item in started if thread is worker), None)
            held_before = owner is not None and owner in authority._reads
            result = original_join(worker, *args, **kwargs)
            joined.append((worker, held_before, owner in authority._reads, not worker.is_alive()))
            return result

        monkeypatch.setattr(threading.Thread, 'start', start_then_raise)
        monkeypatch.setattr(threading.Thread, 'join', record_join)
        lease = r.service.responses(r.begin)
        host_observer = asyncio.create_task(anext(lease))
        readers = [asyncio.create_task(authority.select_current_target(r.ctx, r.gen, r.begin))
                   for _ in range(3)]
        observers = [host_observer, *readers]
        try:
            # Wait only for the real Thread.start calls, not a synthetic worker-completion flag.
            for _ in range(100):
                if len(started) == 4:
                    break
                await asyncio.sleep(0.005)
            assert len(started) == 4 and len(authority._reads) == 4
            owners = [owner for _, owner in started]
            assert all(owner is not None for owner in owners)
            assert len({id(owner) for owner in owners}) == 4
            assert all(worker.ident is not None and worker.is_alive() for worker, _ in started)
            assert not joined and not r.made and not r.gate_calls
            op = r.service._operation
            assert op is not None and op.begin is None
            status = r.service.responses(HostOperationRequest(
                r.gen, 'status', op.identity.operation_id
            ))
            try:
                assert (await anext(status)).result == 'unavailable'
            finally:
                await status.aclose()
            assert len(authority._reads) == 4 and not joined and r.service._terminal is None
            with pytest.raises(AuthorityUnavailable):
                await authority.select_current_target(r.ctx, r.gen, r.begin)
            assert len(started) == 4
            if observation_end == 'cancel':
                for task in observers:
                    task.cancel()
                endings = await asyncio.gather(*observers, return_exceptions=True)
                assert all(isinstance(value, asyncio.CancelledError) for value in endings)
            else:
                endings = await asyncio.gather(*observers)
                assert endings[0].result == 'unavailable' and endings[1:] == [None, None, None]
            await lease.aclose()
            assert len(authority._reads) == 4 and not joined
            assert all(owner.abandoned and not owner.task.done() for owner in owners)
            assert all(worker.is_alive() for worker, _ in started)
            assert r.service._operation is None and r.service._terminal is None
            with pytest.raises(AuthorityUnavailable):
                await authority.select_current_target(r.ctx, r.gen, r.begin)
            assert len(started) == 4 and not r.made
            release.set()
            # Observe the actual owned completion tasks: only _read's Thread.join permits removal.
            await asyncio.gather(*(owner.task for owner in owners))
            assert len(joined) == 4
            assert {id(worker) for worker, *_ in joined} == {id(worker) for worker, _ in started}
            assert all(held_before and held_after and ended
                       for _, held_before, held_after, ended in joined)
            assert not authority._reads and not r.made and not r.gate_calls
            assert r.service._terminal is None
        finally:
            release.set()
            for task in observers:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*observers, return_exceptions=True)
            await lease.aclose()
            await r.service.shutdown()
        assert all(not worker.is_alive() for worker, _ in started)
    asyncio.run(run())
