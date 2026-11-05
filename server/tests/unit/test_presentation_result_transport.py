"""Synthetic result candidates, actual Unix/owned reader, mocked peer/clock.

No real host data, public image response, terminal proof or native release.
"""
import asyncio
import errno
import hashlib
import os
from contextlib import suppress
from dataclasses import replace
from pathlib import Path

import pytest
import pytest_asyncio

from hmp_plugin import presentation_result_transport as result
from hmp_plugin.presentation_authority import (
    AuthorityRefusalError,
    ListenerFence,
    ParentAuthorityAdapter,
)
from hmp_plugin.presentation_broker_codec import BrokerHeader, encode_header
from hmp_plugin.presentation_broker_registry import BrokerRegistry, RegistryStatus
from hmp_plugin.presentation_broker_service import SocketChannel
from hmp_plugin.presentation_jobs import RemotePhase, State
from hmp_plugin.presentation_output_v2 import decode_output_v2, encode_output_v2
from hmp_plugin.presentation_remote_cleanup import RemoteCleanupOwner

from .test_presentation_broker_resources import image
from .test_presentation_broker_service import local as local
from .test_presentation_clock import darwin_model
from .test_presentation_remote import adopt, prepare
from .test_presentation_supervisor import context as context

pytestmark = [pytest.mark.asyncio, pytest.mark.parametrize("local", [2], indirect=True)]


@pytest_asyncio.fixture
async def coupled_result(local, context, monkeypatch, request):
    import time

    variant = getattr(request, "param", "metadata")
    authority, op, native = context
    expected = None
    if variant != "metadata":
        asset = Path(native.home) / "assets" / "avatar.png"
        asset.parent.mkdir(mode=0o700)
        asset.write_bytes(image())
        asset.chmod(0o600)
        if variant == "avatar":
            expected = hashlib.sha256(asset.read_bytes()).hexdigest()
            original = authority._record(op)
            authority = ParentAuthorityAdapter(original.lease.iid, service=native)
            op = authority.reserve(original.lease, "AVATAR", original.headers,
                listener=object(), fence=ListenerFence(1), store=object(), bridge=object(),
                identity=object(), native_owner=object())
    spine, enrollment, client, _, _, _ = local
    darwin_model(monkeypatch)
    channel = SocketChannel(client(), replace(enrollment, gateway_pid=os.getpid(),
        service_pid=os.getpid() + 1), role="gateway", endpoint=spine._endpoint,
        observation=spine._observation)
    row = await prepare((authority, op, native), (channel, None, spine),
                        expected_avatar_sha=expected)
    remote = adopt(row)
    task = asyncio.create_task(spine.serve_once(time.monotonic_ns() + 2_000_000_000))
    yield remote, row, spine, task
    native.release.set()
    owner = remote._cleanup_owner_snapshot
    if owner is not None and owner._initialized is True:
        RemoteCleanupOwner.request(owner)
        with suppress(BaseException):
            await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
        work = owner._allocations_snapshot[1].task
        if work.done():
            with suppress(BaseException):
                work.result()
    if not task.done():
        task.cancel()
    with suppress(BaseException):
        await task
    channel.close()
    channel.close_clock()
    await spine.stop_local_sockets()


@pytest.mark.parametrize("coupled_result", ["metadata", "metadata_avatar", "avatar"], indirect=True)
async def test_actual_result_is_private_validated_candidate_not_completion(coupled_result):
    remote, row, spine, task = coupled_result
    authority, op, native, _, _, _, packet, binding = row
    assert await remote.begin_ready() and await remote.go()
    assert await remote.result_ready() is True
    record = authority._record(op)
    job = authority.owner._resolve(record.handle)
    receiver = remote._result_owner_snapshot
    writer = receiver._scope_snapshot.channel  # gateway side, no broker authority
    assert writer is row[3] and receiver._validated
    assert job.result[0]["fields"]["display_name"] == "Aster"
    assert job.remote_result_token is receiver._token_snapshot
    assert not receiver._scope_snapshot.buffer._buffer
    assert authority.owner.inspect(record.handle) == (State.RUNNING, True, False)
    assert authority.owner.inspect_remote(record.handle) is RemotePhase.RESULT_VALIDATED
    assert record.headers is not None and native.drain_calls == 0
    assert "PRE_EMIT" not in native.calls
    held = spine._registry._record(spine._registry._operations[binding.operation])
    assert held.resources._normal_complete and held.resources._result_taken
    assert held.resources._phase == "LOCAL_DRAINED"
    broker_writer = spine._records[0].result_writer
    assert broker_writer._write_completed and broker_writer._payload is None
    assert broker_writer._scope_snapshot.packet is not packet
    assert spine._registry.status(binding) is RegistryStatus.PENDING
    assert not remote._cleanup_owner_snapshot._allocations_snapshot[1].task.done()
    RemoteCleanupOwner.request(remote._cleanup_owner_snapshot)
    await asyncio.wait_for(asyncio.shield(
        remote._cleanup_owner_snapshot._allocations_snapshot[0].task), 1)
    await task
    assert job.result is None and job.remote_result_token is None
    assert not authority.owner.inspect(record.handle)[2]


@pytest.mark.parametrize("fault", ["challenge", "epoch", "chain", "totals"])
async def test_gateway_independently_rejects_broker_accepted_result(
    coupled_result, monkeypatch, fault
):
    remote, row, _, _ = coupled_result
    original = BrokerRegistry.take_resource_candidate
    tampered = []
    def take(registry, ticket):
        wire = original(registry, ticket)
        header, avatar = decode_output_v2(wire, remote._row_snapshot["challenge"],
                                        remote._row_snapshot["epoch"])
        if fault == "challenge":
            header["challenge"] = "0" * 64
        elif fault == "epoch":
            header["epoch"] += 1
        elif fault == "chain":
            header["chain"][0][0] += 1
        else:
            header["ledger"]["opens"] = 0
        tampered.append(True)
        return encode_output_v2(header, avatar)
    monkeypatch.setattr(BrokerRegistry, "take_resource_candidate", take)
    assert await remote.begin_ready()
    with pytest.raises(AuthorityRefusalError):
        assert await remote.go()
        await remote.result_ready()
    job = remote._job_origin_snapshot
    assert tampered and job.result is None and job.remote_result_token is None
    assert not job.output_buffer._buffer
    assert row[0]._record(row[1]).headers is not None and not job.credit_released


async def test_duplicate_candidate_wait_revokes_and_wipes_original(coupled_result):
    remote, _, _, _ = coupled_result
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    job = remote._job_origin_snapshot
    assert job.result is not None
    with pytest.raises(AuthorityRefusalError):
        await remote.result_ready()
    assert job.result is None and job.remote_result_token is None
    assert job.state is State.UNKNOWN and not job.credit_released


async def test_foreign_buffer_during_read_never_receives_feed_or_wipe(coupled_result, monkeypatch):
    remote, row, _, _ = coupled_result
    original = result.SelectorReadiness.wait
    callbacks, changed = [], []
    job = remote._job_origin_snapshot
    buffer = job.output_buffer
    class Foreign:
        def __getattribute__(self, name):
            callbacks.append(name)
            raise AssertionError("foreign buffer is not owned")
    async def recv(waiter, end):
        data = await original(waiter, end)
        sock = waiter._origin_scope.sock
        owner = remote._result_owner_snapshot
        if sock is row[3]._socket_snapshot and owner is not None and owner._header is not None:
            job.output_buffer = Foreign()
            changed.append(True)
        return data
    monkeypatch.setattr(result.SelectorReadiness, "wait", recv)
    assert await remote.begin_ready()
    try:
        with pytest.raises(AuthorityRefusalError):
            assert await remote.go()
            await remote.result_ready()
        assert changed and callbacks == []
        assert not buffer._buffer and job.result is None and job.remote_result_token is None
    finally:
        job.output_buffer = buffer  # test disposal only, after refusal


async def test_no_public_result_method_returns_data_or_local_custody(coupled_result):
    remote, row, _, _ = coupled_result
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    authority, op = row[:2]
    assert not await authority.reauthorize(op)
    await authority.owner.reauthorize(authority._record(op).handle)
    assert remote._job_origin_snapshot.result is None  # old local path refuses remote
    assert authority._record(op).headers is not None


async def test_bounded_header_encoding_has_no_body_copy(coupled_result):
    remote, _, _, _ = coupled_result
    binding = remote._binding_snapshot
    header = BrokerHeader(binding, "RESULT", 1, 2_008_196, 2)
    wire = encode_header(header)
    assert len(wire) < 1032 and wire.startswith(b"HBR1")


async def test_cross_operation_accumulator_retarget_never_feeds_or_wipes_other(
    coupled_result, monkeypatch
):
    from hmp_plugin.presentation_output_v2 import BoundedResultBufferV2

    remote, row, _, _ = coupled_result
    original = result.SelectorReadiness.wait
    job = remote._job_origin_snapshot
    own = job.output_buffer._buffer
    other = BoundedResultBufferV2()
    other._buffer.extend(b"OTHER_OPERATION_SYNTHETIC_PRIVATE_PAYLOAD")
    held = bytes(other._buffer)
    changed = []
    async def recv(waiter, end):
        data = await original(waiter, end)
        sock = waiter._origin_scope.sock
        receiver = remote._result_owner_snapshot
        if (sock is row[3]._socket_snapshot and receiver is not None
                and receiver._header is not None):
            job.output_buffer._buffer = other._buffer
            changed.append(True)
        return data
    monkeypatch.setattr(result.SelectorReadiness, "wait", recv)
    assert await remote.begin_ready()
    try:
        with pytest.raises(AuthorityRefusalError):
            assert await remote.go()
            await remote.result_ready()
        assert changed and bytes(other._buffer) == held
        assert not own and job.result is None and job.remote_result_token is None
    finally:
        job.output_buffer._buffer = own  # test disposal only after the refusal outcome


@pytest.mark.parametrize("partial", [False, True])
async def test_transferred_writer_payload_cannot_be_retargeted_or_retried(
    coupled_result, monkeypatch, partial
):
    remote, _, spine, _ = coupled_result
    original = result._LOOP.sock_sendall
    attempted, emitted, changed = [], [], []
    foreign = b"FOREIGN_OPERATION_SYNTHETIC_RESULT"
    async def send(loop, sock, data):
        writer = spine._records[0].result_writer if spine._records else None
        if writer is not None and sock is writer._scope_snapshot.channel._socket_snapshot:
            attempted.append(data)
            if not changed and data.startswith(b"HBR1"):
                await original(loop, sock, data)
                emitted.append(data)
                if not partial:
                    writer._payload = writer._payload_snapshot = foreign
                    changed.append(True)
                return
            if partial:
                changed.append(True)
                await original(loop, sock, data[:1])
                emitted.append(data[:1])
                raise OSError("synthetic partial RESULT")
        return await original(loop, sock, data)
    monkeypatch.setattr(result._LOOP, "sock_sendall", send)
    assert await remote.begin_ready()
    with pytest.raises(AuthorityRefusalError):
        assert await remote.go()
        await remote.result_ready()
    assert changed and foreign not in b"".join(emitted)
    assert len(attempted) == (2 if partial else 1)
    assert remote._job_origin_snapshot.result is None
    assert not remote._job_origin_snapshot.credit_released


@pytest.mark.parametrize("fault", ["size", "sequence", "version", "binding"])
async def test_outer_result_header_refuses_before_body_read(coupled_result, monkeypatch, fault):
    import json
    import struct

    from hmp_plugin.presentation_jobs import OUTPUT_LIMIT

    remote, _, _, _ = coupled_result
    original = result.encode_header
    def invalid(header):
        wire = original(header)
        fields = json.loads(wire[8:])
        if fault == "size":
            fields["body_length"] = OUTPUT_LIMIT + 1
        elif fault == "sequence":
            fields["sequence"] = 2
        elif fault == "version":
            fields["v"] = 1
        else:
            fields["operation"] = "e" * 64
        raw = json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()
        return b"HBR1" + struct.pack(">I", len(raw)) + raw  # deliberately bypass closed encoder
    monkeypatch.setattr(result, "encode_header", invalid)
    assert await remote.begin_ready()
    with pytest.raises(AuthorityRefusalError):
        assert await remote.go()
        await remote.result_ready()
    receiver = remote._result_owner_snapshot
    assert receiver._header is None and not receiver._scope_snapshot.accumulator
    assert receiver._scope_snapshot.job.result is None


async def test_native_result_clock_never_invokes_foreign_jobs_map(coupled_result, monkeypatch):
    remote, row, _, _ = coupled_result
    jobs = row[0].owner._jobs
    original = ParentAuthorityAdapter._current
    changed, callbacks = [], []
    class Foreign:
        def get(self, *args):
            callbacks.append("get")
            raise AssertionError("foreign jobs map must never run")
        def __contains__(self, value):
            callbacks.append("contains")
            raise AssertionError("foreign jobs map must never run")
    def current(a, r):
        okay = original(a, r)
        receiver = remote._result_owner_snapshot
        if (a is row[0] and receiver is not None and receiver._initialized is True
                and asyncio.current_task() is (
                    remote._cleanup_owner_snapshot._allocations_snapshot[1].task)
                and not changed):
            changed.append(True)
            a.owner._jobs = Foreign()
        return okay
    monkeypatch.setattr(ParentAuthorityAdapter, "_current", current)
    try:
        assert await remote.begin_ready()
        with pytest.raises(AuthorityRefusalError):
            assert await remote.go()
            await remote.result_ready()
        assert changed and callbacks == [] and remote._job_origin_snapshot.result is None
    finally:
        row[0].owner._jobs = jobs  # test disposal only after refusal


@pytest.mark.parametrize("coupled_result", ["avatar"], indirect=True)
@pytest.mark.parametrize("fault", ["hash", "expected_revision"])
async def test_gateway_checks_avatar_body_and_original_expected_revision(
    coupled_result, monkeypatch, fault
):
    from hmp_plugin.presentation_jobs import HEADER_LIMIT, _envelope

    remote, _, _, _ = coupled_result
    original = BrokerRegistry.take_resource_candidate
    changed = []
    def take(registry, ticket):
        wire = original(registry, ticket)
        header, avatar = decode_output_v2(wire, remote._row_snapshot["challenge"],
                                        remote._row_snapshot["epoch"])
        damaged = avatar[:-1] + bytes([avatar[-1] ^ 1])
        if fault == "expected_revision":
            digest = hashlib.sha256(damaged).hexdigest()
            header["avatar_sha"] = digest
            header["source_proof"]["avatar_body_sha"] = digest
        changed.append(True)
        return _envelope(header, HEADER_LIMIT) + damaged  # bypass broker hash validation only
    monkeypatch.setattr(BrokerRegistry, "take_resource_candidate", take)
    assert await remote.begin_ready()
    with pytest.raises(AuthorityRefusalError):
        assert await remote.go()
        await remote.result_ready()
    assert changed and remote._job_origin_snapshot.result is None
    assert not remote._job_origin_snapshot.credit_released


async def test_custody_tuple_retarget_cannot_redirect_central_cancel_wipe(
    coupled_result, monkeypatch
):
    from hmp_plugin.presentation_output_v2 import BoundedResultBufferV2

    remote, row, _, _ = coupled_result
    job = remote._job_origin_snapshot
    original = result.SelectorReadiness.wait
    origin = job._remote_output_custody_snapshot
    other = BoundedResultBufferV2()
    other._buffer.extend(b"OTHER_CUSTODY_SYNTHETIC_PAYLOAD")
    held, changed = bytes(other._buffer), []
    async def recv(waiter, end):
        data = await original(waiter, end)
        sock = waiter._origin_scope.sock
        receiver = remote._result_owner_snapshot
        if (sock is row[3]._socket_snapshot and receiver is not None
                and receiver._header is not None):
            job.remote_output_custody = (job, other, other._buffer)
            changed.append(True)
        return data
    monkeypatch.setattr(result.SelectorReadiness, "wait", recv)
    assert await remote.begin_ready()
    try:
        with pytest.raises(AuthorityRefusalError):
            assert await remote.go()
            await remote.result_ready()
        assert changed and bytes(other._buffer) == held
        assert job._remote_output_custody_snapshot is origin and not origin[2]
        assert job.result is None and job.remote_result_token is None
    finally:
        job.remote_output_custody = origin  # test-only disposal after refusal


async def test_forged_notification_cannot_report_unvalidated_candidate(coupled_result, monkeypatch):
    remote, _, _, _ = coupled_result
    monkeypatch.setattr(BrokerRegistry, "poll_resource_result", lambda *args: False)
    assert await remote.begin_ready() and await remote.go()
    owner = remote._cleanup_owner_snapshot
    assert owner._result_token is None
    owner._result_notice_snapshot.set_result(True)  # no validation token exists
    with pytest.raises(AuthorityRefusalError):
        await remote.result_ready()
    assert remote._job_origin_snapshot.result is None
    assert not remote._job_origin_snapshot.credit_released


async def test_cancel_during_blocked_body_stops_original_writer_before_work_deadline(
    coupled_result, monkeypatch
):
    remote, _, spine, task = coupled_result
    original = result._LOOP.sock_sendall
    entered, release = asyncio.Event(), asyncio.Event()
    continued = []
    async def send(loop, sock, data):
        writer = spine._records[0].result_writer if spine._records else None
        if (writer is not None and sock is writer._scope_snapshot.channel._socket_snapshot
                and not data.startswith(b"HBR1")):
            await original(loop, sock, data[:1])
            entered.set()
            await release.wait()  # deterministic backpressure under original service task
            continued.append(True)
            return await original(loop, sock, data[1:])
        return await original(loop, sock, data)
    monkeypatch.setattr(result._LOOP, "sock_sendall", send)
    async def flow():
        assert await remote.begin_ready() and await remote.go()
        return await remote.result_ready()
    public = asyncio.create_task(flow())
    try:
        await asyncio.wait_for(entered.wait(), 1)
        writer = spine._records[0].result_writer
        public.cancel()
        with pytest.raises(asyncio.CancelledError):
            await public
        owner = remote._cleanup_owner_snapshot
        await asyncio.wait_for(asyncio.shield(owner._allocations_snapshot[0].task), 1)
        await asyncio.wait_for(asyncio.shield(task), 1)
        assert writer._cancel_requested and not continued
        assert writer._payload is None and not writer._write_completed
        assert not remote._job_origin_snapshot.remote_output_origin._buffer
        assert remote._job_origin_snapshot.result is None
        assert not owner._result_notice_snapshot.cancelled()
    finally:
        release.set()
        if not public.done():
            public.cancel()
        with suppress(BaseException):
            await public


async def test_candidate_fact_tracks_original_wire_without_retaining_payload(coupled_result):
    remote, _, _, _ = coupled_result
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    receiver = remote._result_owner_snapshot
    job = remote._job_origin_snapshot
    fact = receiver._candidate_fact_snapshot
    assert fact.header_wire == result._candidate_header_wire(job.result[0])
    wire = encode_output_v2(*job.result)
    assert fact.wire_sha256 == hashlib.sha256(wire).hexdigest()
    assert fact.wire_length == len(wire)
    assert receiver._candidate_snapshot is job.result
    assert fact.owner is receiver and fact.token is job.remote_result_token
    assert not any(value is job.result or value is job.result[0] or value is job.result[1]
                   for value in fact)


@pytest.mark.parametrize("fault", [
    "fields", "ledger", "chain", "tuple", "body", "token", "paired_candidate",
])
async def test_changed_private_candidate_refuses_readiness_and_drops_owned_refs(
    coupled_result, monkeypatch, fault
):
    remote, row, _, _ = coupled_result
    original = result.RemoteResultOwner.receive
    changed = []
    async def receive(receiver):
        accepted = await original(receiver)
        if accepted:
            job = receiver._scope_snapshot.job
            header, body = job.result
            if fault == "fields":
                header["fields"]["display_name"] = "substituted"
            elif fault == "ledger":
                header["ledger"]["opens"] += 1
            elif fault == "chain":
                header["chain"][0][0] += 1
            elif fault == "tuple":
                job.result = (header, body)
            elif fault == "body":
                job.result = (header, b"foreign")
            elif fault == "token":
                job.remote_result_token = object()
            else:
                receiver._candidate = receiver._candidate_snapshot = (header, b"foreign")
                job.result = receiver._candidate
            changed.append(True)
        return accepted
    monkeypatch.setattr(result.RemoteResultOwner, "receive", receive)
    assert await remote.begin_ready()
    with pytest.raises(AuthorityRefusalError):
        assert await remote.go()
        await remote.result_ready()
    receiver = remote._result_owner_snapshot
    job = remote._job_origin_snapshot
    assert changed and job.result is None and job.remote_result_token is None
    assert receiver._candidate is None and receiver._candidate_snapshot is None
    assert receiver._candidate_fact is None and receiver._candidate_fact_snapshot is None
    assert receiver._discarded and not job.credit_released
    assert row[0]._record(row[1]).headers is not None


@pytest.mark.parametrize("fault", [
    "object", "key", "depth", "wide", "text", "surrogate", "integer", "cycle",
])
async def test_bounded_header_integrity_refuses_foreign_or_unbounded_shapes(local, fault):
    callbacks = []
    class Foreign:
        def __eq__(self, other):
            callbacks.append("eq")
            raise AssertionError("foreign equality")
        def __str__(self):
            callbacks.append("str")
            raise AssertionError("foreign text")
    if fault == "object":
        value = {"fields": Foreign()}
    elif fault == "key":
        value = {object(): "x"}
    elif fault == "depth":
        value = {"x": [[[[[1]]]]]}
    elif fault == "wide":
        value = {"x": [0] * (result.HEADER_LIMIT + 1)}
    elif fault == "text":
        value = {"x": "x" * (result.HEADER_LIMIT + 1)}
    elif fault == "surrogate":
        value = {"x": chr(0xD800)}
    elif fault == "integer":
        value = {"x": 1 << 10000}
    else:
        value = {"x": []}
        value["x"].append(value)
    with pytest.raises(AuthorityRefusalError):
        result._candidate_header_wire(value)
    assert callbacks == []


async def test_central_wipe_discards_original_owner_even_when_current_result_owner_drifts(
    coupled_result
):
    from hmp_plugin.presentation_jobs import JobOwner

    remote, _, _, _ = coupled_result
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    job = remote._job_origin_snapshot
    receiver = remote._result_owner_snapshot
    callbacks = []
    class Foreign:
        def __getattribute__(self, name):
            callbacks.append(name)
            raise AssertionError("foreign owner must not be followed")
    foreign = Foreign()
    remote._result_owner = remote._result_owner_snapshot = foreign
    job.result = foreign
    JobOwner._wipe_remote_candidate(job)
    assert callbacks == [] and job.result is None and job.remote_result_token is None
    assert receiver._candidate is None and receiver._candidate_snapshot is None
    assert receiver._candidate_fact is None and receiver._token_snapshot is None
    assert receiver._discarded


async def test_candidate_custody_retarget_cannot_discard_other_owner(coupled_result):
    from hmp_plugin.presentation_jobs import JobOwner

    remote, _, _, _ = coupled_result
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    job = remote._job_origin_snapshot
    receiver = remote._result_owner_snapshot
    other = result.RemoteResultOwner.__new__(result.RemoteResultOwner)
    other._candidate_job_origin = object()  # distinct synthetic operation owner
    other._candidate = other._candidate_snapshot = ({}, b"OTHER_PRIVATE_SYNTHETIC")
    held = other._candidate
    other._discarded = False
    origin = job._remote_candidate_custody_snapshot
    job._remote_candidate_custody_origin = (other, job)
    JobOwner._wipe_remote_candidate(job)
    assert job._remote_candidate_custody_snapshot is origin
    assert receiver._discarded and receiver._candidate_snapshot is None
    assert other._candidate is held and other._candidate_snapshot is held
    assert not other._discarded
    # Even a separately corrupted snapshot cannot use same-job tuple text as authority.
    job._remote_candidate_custody_snapshot = (other, job)
    JobOwner._wipe_remote_candidate(job)
    assert other._candidate is held and not other._discarded
    job._remote_candidate_custody_snapshot = origin  # fixture disposal only


async def test_receiver_wipe_uses_original_custody_not_replaced_scope(coupled_result):
    from hmp_plugin.presentation_output_v2 import BoundedResultBufferV2

    remote, _, _, _ = coupled_result
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    receiver = remote._result_owner_snapshot
    original = receiver._scope_snapshot
    other = BoundedResultBufferV2()
    other._buffer.extend(b"OTHER_OPERATION_SYNTHETIC")
    held = bytes(other._buffer)
    receiver._scope = receiver._scope_snapshot = original._replace(
        accumulator=other._buffer, buffer=other)
    result.RemoteResultOwner.wipe(receiver)
    assert bytes(other._buffer) == held and not other._done
    assert original.job.result is None and original.job.remote_result_token is None
    assert receiver._candidate_snapshot is None and receiver._candidate_fact_snapshot is None
    receiver._scope = receiver._scope_snapshot = original  # fixture disposal only


async def test_inflight_reader_scope_retarget_cannot_cancel_or_reset_other_operation(
    coupled_result, monkeypatch
):
    remote, row, _, _ = coupled_result
    foreign_channel = SocketChannel.__new__(SocketChannel)
    foreign_channel._reading = True
    foreign_cleanup = RemoteCleanupOwner.__new__(RemoteCleanupOwner)
    original_recv, original_request = result.SelectorReadiness.wait, RemoteCleanupOwner.request
    changed, foreign_requests = [], []
    def request(owner):
        if owner is foreign_cleanup:
            foreign_requests.append(True)
            return
        return original_request(owner)
    async def recv(waiter, end):
        data = await original_recv(waiter, end)
        sock = waiter._origin_scope.sock
        receiver = remote._result_owner_snapshot
        if sock is row[3]._socket_snapshot and receiver is not None and not changed:
            original = receiver._scope_snapshot
            foreign_channel._result_receiver_snapshot = receiver
            receiver._scope = receiver._scope_snapshot = original._replace(
                cleanup=foreign_cleanup, channel=foreign_channel)
            changed.append((receiver, original))
        return data
    monkeypatch.setattr(RemoteCleanupOwner, "request", request)
    monkeypatch.setattr(result.SelectorReadiness, "wait", recv)
    try:
        assert await remote.begin_ready()
        with pytest.raises(AuthorityRefusalError):
            assert await remote.go()
            await remote.result_ready()
        assert changed and foreign_requests == [] and foreign_channel._reading is True
        assert row[3]._reading is False
        assert remote._job_origin_snapshot.result is None
    finally:
        for receiver, original in changed:
            receiver._scope = receiver._scope_snapshot = original


async def test_inflight_writer_scope_retarget_cannot_reset_other_channel(
    coupled_result, monkeypatch
):
    remote, _, spine, _ = coupled_result
    original_send = result._LOOP.sock_sendall
    foreign = SocketChannel.__new__(SocketChannel)
    foreign._writing = True
    changed = []
    async def send(loop, sock, data):
        await original_send(loop, sock, data)
        records = spine._records
        writer = records[0].result_writer_snapshot if records else None
        if (writer is not None and writer._write_attempted and not changed
                and sock is writer._scope_snapshot.channel._socket_snapshot):
            original = writer._scope_snapshot
            foreign._result_writer_snapshot = writer
            writer._scope = writer._scope_snapshot = original._replace(channel=foreign)
            changed.append((writer, original))
    monkeypatch.setattr(result._LOOP, "sock_sendall", send)
    try:
        assert await remote.begin_ready()
        with pytest.raises(AuthorityRefusalError):
            assert await remote.go()
            await remote.result_ready()
        assert changed and foreign._writing is True
        assert changed[0][1].channel._writing is False
    finally:
        for writer, original in changed:
            writer._scope = writer._scope_snapshot = original


@pytest.mark.parametrize("stage", ["outer", "body"])
async def test_partial_cursor_cancel_keeps_consumed_offsets_and_wipes_payload(
    coupled_result, monkeypatch, stage
):
    remote, row, _, _ = coupled_result
    original_recv, original_wait = result._SOCKET_RECV, result.SelectorReadiness.wait
    observations = []

    def short_recv(sock, count):
        return original_recv(sock, min(count, 3))

    async def wait(waiter, end):
        await original_wait(waiter, end)
        owner = remote._result_owner_snapshot
        if owner is None or waiter._origin_scope.sock is not row[3]._socket_snapshot:
            return
        cursor = owner._cursor_origin
        ready = (cursor.outer_committed == 3 if stage == "outer"
                 else cursor.body_committed == 3)
        if ready and not observations:
            observations.append((cursor.received, cursor.outer_committed,
                                 cursor.body_received, cursor.body_committed))
            asyncio.current_task().cancel()
            await asyncio.sleep(0)  # after retired readiness, before next concrete recv

    monkeypatch.setattr(result, "_SOCKET_RECV", short_recv)
    monkeypatch.setattr(result.SelectorReadiness, "wait", wait)
    assert await remote.begin_ready() and await remote.go()
    with pytest.raises(AuthorityRefusalError):
        await remote.result_ready()
    cursor = remote._result_owner_snapshot._cursor_origin
    assert observations == [(cursor.received, cursor.outer_committed,
                              cursor.body_received, cursor.body_committed)]
    assert not cursor.outer_origin and cursor.pending is None
    assert cursor.recv_intent is False and cursor.commit_intent is False
    assert cursor.io_unknown is False and row[3]._reading is False
    assert remote._job_origin_snapshot.result is None
    assert cursor.received == cursor.outer_committed + cursor.body_committed
    assert (cursor.body_committed == 0 if stage == "outer" else cursor.body_committed == 3)


async def test_uncertain_recv_never_fabricates_cursor_or_reader_retirement(
    coupled_result, monkeypatch
):
    remote, row, _, _ = coupled_result
    original_recv = result._SOCKET_RECV
    consumed = []

    def interrupted(sock, count):
        part = original_recv(sock, count)
        consumed.append(len(part))
        raise RuntimeError("synthetic interruption after syscall")

    monkeypatch.setattr(result, "_SOCKET_RECV", interrupted)
    assert await remote.begin_ready() and await remote.go()
    with pytest.raises(AuthorityRefusalError):
        await remote.result_ready()
    receiver = remote._result_owner_snapshot
    cursor = receiver._cursor_origin
    assert consumed == [8] and cursor.recv_intent is True
    assert cursor.io_unknown is True and cursor.received == 0
    assert row[3]._reading is True and not row[3]._closed_known
    assert remote._job_origin_snapshot.result is None
    # Test-only disposal of our exact synthetic socket, not a production close fact.
    row[3]._socket_snapshot.close()


async def test_eagain_consumes_no_offset_and_does_not_renew_deadline(
    coupled_result, monkeypatch
):
    remote, _, _, _ = coupled_result
    original_recv, original_wait = result._SOCKET_RECV, result.SelectorReadiness.wait
    ends, calls = [], []

    def recv(sock, count):
        if not calls:
            calls.append(True)
            raise BlockingIOError(errno.EAGAIN, "synthetic EAGAIN")
        return original_recv(sock, count)

    async def wait(waiter, end):
        ends.append(end)
        return await original_wait(waiter, end)

    monkeypatch.setattr(result, "_SOCKET_RECV", recv)
    monkeypatch.setattr(result.SelectorReadiness, "wait", wait)
    assert await remote.begin_ready() and await remote.go() and await remote.result_ready()
    receiver = remote._result_owner_snapshot
    cursor = receiver._cursor_origin
    assert calls == [True] and len(ends) >= 4
    assert set(ends) == {receiver._scope_snapshot.deadline}
    assert cursor.body_received == cursor.body_committed == receiver._header.body_length
    assert cursor.received == cursor.outer_committed + cursor.body_committed
    assert cursor.pending is None and cursor.io_unknown is False


async def test_non_eagain_blocking_error_keeps_read_claim(coupled_result, monkeypatch):
    remote, row, _, _ = coupled_result

    def recv(sock, count):
        raise BlockingIOError(errno.EIO, "synthetic unknown receive")

    monkeypatch.setattr(result, "_SOCKET_RECV", recv)
    assert await remote.begin_ready() and await remote.go()
    with pytest.raises(AuthorityRefusalError):
        await remote.result_ready()
    cursor = remote._result_owner_snapshot._cursor_origin
    assert cursor.recv_intent and cursor.io_unknown and row[3]._reading
    assert cursor.received == 0 and remote._job_origin_snapshot.result is None
    row[3]._socket_snapshot.close()  # test-only disposal, no production closure proof


@pytest.mark.parametrize("field", ["received", "body_received"])
async def test_recv_boundary_counter_drift_never_runs_foreign_arithmetic(
    coupled_result, monkeypatch, field
):
    remote, row, _, _ = coupled_result
    original = result._SOCKET_RECV
    callbacks = []

    class Foreign:
        def __add__(self, value):
            callbacks.append("add")
            raise AssertionError("foreign arithmetic")
        __iadd__ = __add__
        def __eq__(self, value):
            callbacks.append("eq")
            raise AssertionError("foreign comparison")

    def recv(sock, count):
        part = original(sock, count)
        setattr(remote._result_owner_snapshot._cursor_origin, field, Foreign())
        return part

    monkeypatch.setattr(result, "_SOCKET_RECV", recv)
    assert await remote.begin_ready() and await remote.go()
    with pytest.raises(AuthorityRefusalError):
        await remote.result_ready()
    cursor = remote._result_owner_snapshot._cursor_origin
    assert callbacks == [] and cursor.received == 8
    assert cursor.io_unknown and row[3]._reading
    assert cursor.pending is None and not cursor.outer_origin
    row[3]._socket_snapshot.close()  # test-only disposal, no production closure proof


async def test_eagain_after_cancellation_has_no_second_readiness_registration(
    coupled_result, monkeypatch
):
    remote, row, _, _ = coupled_result
    original_init = result.SelectorReadiness.__init__
    registrations = []

    def initialize(waiter, sock):
        if sock is row[3]._socket_snapshot:
            registrations.append(waiter)
        return original_init(waiter, sock)

    def recv(sock, count):
        RemoteCleanupOwner.request(remote._cleanup_owner_snapshot)
        raise BlockingIOError(errno.EAGAIN, "synthetic cancellation at zero-byte boundary")

    monkeypatch.setattr(result.SelectorReadiness, "__init__", initialize)
    monkeypatch.setattr(result, "_SOCKET_RECV", recv)
    assert await remote.begin_ready() and await remote.go()
    with pytest.raises(AuthorityRefusalError):
        await remote.result_ready()
    cursor = remote._result_owner_snapshot._cursor_origin
    assert len(registrations) == 1 and cursor.waiter is registrations[0]
    assert cursor.received == cursor.body_received == cursor.body_committed == 0
    assert cursor.pending is None and cursor.io_unknown is False
    assert row[3]._reading is False and remote._job_origin_snapshot.result is None
