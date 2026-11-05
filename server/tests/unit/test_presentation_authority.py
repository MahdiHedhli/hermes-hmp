"""Inert parent-only BI1 authority/JobOwner causals; no native or credential IO."""

from __future__ import annotations

import asyncio
import dataclasses
import unittest

import pytest

from hmp_plugin.presentation_authority import (
    AuthorityRefusalError,
    ListenerFence,
    NativeObservation,
    OpaqueOperation,
    OriginalHeaders,
    ParentAuthorityAdapter,
)
from hmp_plugin.presentation_cancel_budget import CancellationBudget
from hmp_plugin.presentation_jobs import JOB_SECONDS, CapturedLease, State, encode_output


@pytest.mark.parametrize("first,second", [(1.0, 1.1), (1.1, 1.0)])
def test_original_budget_binds_earliest_ceiling_before_native_observation(first, second):
    samples = iter((first, second))
    native = NativeFake()
    scope = ParentAuthorityAdapter("iid", service=native, clock=lambda: next(samples))
    operation = scope.reserve(lease(), "METADATA", headers(), listener=object(),
        fence=ListenerFence(1), store=object(), bridge=object(), identity=object(),
        native_owner=object())
    record = scope._record(operation)
    assert record.deadline == min(first, second) + JOB_SECONDS
    assert record.cleanup_budget is record.cleanup_budget_snapshot
    assert CancellationBudget.inspect(record.cleanup_budget) == (
        int(record.deadline * 1_000_000_000), None, None, False)
    assert native.calls == []


class Clock:
    def __init__(self) -> None:
        self.now = 1.0

    def __call__(self) -> float:
        return self.now


class Headers:
    def __init__(self, rows: dict[str, list[str]]) -> None:
        self.rows = rows

    def getall(self, key: str, default: list[str]) -> list[str]:
        return self.rows.get(key, default)


class Request:
    def __init__(self, rows: dict[str, list[str]]) -> None:
        self.headers = Headers(rows)


def original_rows() -> dict[str, list[str]]:
    return {"Authorization": ["Bearer " + "A" * 43], "HMP-Instance": ["iid"]}


def headers() -> OriginalHeaders:
    return OriginalHeaders.from_request(Request(original_rows()))


def lease() -> CapturedLease:
    return CapturedLease("iid", "device", "user", "family", "alpha", "b" * 64, "binding", 1)


class NativeFake:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.header_ids: list[int] = []
        self.home = "/native/home/alpha"
        self.allowed = True
        self.change: dict[str, object] = {}
        self.entered: asyncio.Event | None = None
        self.release: asyncio.Event | None = None
        self.stall_phase: str | None = None
        self.raise_phase: str | None = None
        self.swallow_cancel = False
        self.drain_result = True
        self.drain_calls = 0
        self.drain_entered: asyncio.Event | None = None
        self.drain_release: asyncio.Event | None = None

    async def observe(self, record, phase: str) -> NativeObservation | None:
        self.calls.append(phase)
        self.header_ids.append(id(record.headers))
        if self.entered is not None and self.release is not None and phase == self.stall_phase:
            self.entered.set()
            try:
                await self.release.wait()
            except asyncio.CancelledError:
                if not self.swallow_cancel:
                    raise
                await self.release.wait()
        if phase == self.raise_phase:
            raise RuntimeError("private native text must not escape")
        if not self.allowed:
            return None
        result = NativeObservation(
            record.lease.iid,
            record.lease.device_id,
            record.lease.user_id,
            record.lease.family_id,
            record.lease.profile,
            self.home,
            record.listener,
            record.store,
            record.bridge,
            record.identity,
            record.native_owner,
            True,
        )
        return dataclasses.replace(result, **self.change)

    async def drain(self, record) -> bool:
        del record
        self.drain_calls += 1
        if self.drain_entered is not None and self.drain_release is not None:
            self.drain_entered.set()
            try:
                await self.drain_release.wait()
            except asyncio.CancelledError:
                if not self.swallow_cancel:
                    raise
                await self.drain_release.wait()
        return self.drain_result


def adapter(service: NativeFake | None = None):
    clock = Clock()
    native = service or NativeFake()
    scope = ParentAuthorityAdapter(
        "iid", service=native, clock=clock, challenge_source=lambda: "a" * 64
    )
    originals = headers()
    fence = ListenerFence(1)
    owned = (object(), object(), object(), object(), object())
    operation = scope.reserve(
        lease(),
        "METADATA",
        originals,
        listener=owned[0],
        fence=fence,
        store=owned[1],
        bridge=owned[2],
        identity=owned[3],
        native_owner=owned[4],
    )
    return scope, native, clock, fence, operation, originals


def output(scope: ParentAuthorityAdapter, operation: OpaqueOperation) -> bytes:
    return encode_output(
        {
            "schema": 1,
            "challenge": scope.owner.challenge(scope.handle(operation)),
            "epoch": 1,
            "outcome": "OK",
            "fields": {"title": "Aster"},
            "mime": None,
            "width": 0,
            "height": 0,
            "avatar_sha": None,
            "avatar_length": 0,
            "source_proof": {
                "profile_meta": None,
                "profile_sha": None,
                "avatar_meta": None,
                "avatar_body_sha": None,
            },
            "absence_bitmap": 15,
            "chain": [],
            "ledger": {
                "body_bytes": 0,
                "opens": 0,
                "metadata": 0,
                "path_bytes": 0,
                "raster_units": 0,
                "yaml_nodes": 0,
            },
            "cleanup": {"known_fds_closed": True, "unknown_close": False},
        },
        b"",
    )


async def finish_child(scope: ParentAuthorityAdapter, operation: OpaqueOperation, child: object):
    handle = scope.handle(operation)
    scope.owner.feed_result(handle, output(scope, operation), child)
    for event in (
        "RESULT_EOF",
        "DIAGNOSTIC_EOF",
        "WAIT_OK",
        "GROUP_GONE",
        "IPC_CLOSED",
        "SIGNAL_CLOSED",
    ):
        scope.owner.custody(handle, event, child)
    assert scope.owner.inspect(handle)[0] is State.COMPLETE


class ParentAuthorityTests(unittest.IsolatedAsyncioTestCase):
    async def test_a01_exact_original_single_headers_and_no_secret_repr(self) -> None:
        for bad in (
            {"Authorization": [], "HMP-Instance": ["iid"]},
            {"Authorization": ["one", "two"], "HMP-Instance": ["iid"]},
            {"Authorization": ["one"], "HMP-Instance": ["iid", "iid"]},
            {"Authorization": ["Bearer invalid"], "HMP-Instance": ["iid"]},
        ):
            with self.subTest(bad=bad), self.assertRaises(AuthorityRefusalError):
                OriginalHeaders.from_request(Request(bad))
        with self.assertRaises(AuthorityRefusalError):
            OriginalHeaders("Bearer " + "A" * 43, "iid")
        scope, native, _, _, operation, exact = adapter()
        self.assertNotIn("Bearer", repr(exact))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            exact.authorization = "replacement"
        wrong = original_rows()
        wrong["HMP-Instance"] = ["other-iid"]
        with self.assertRaises(AuthorityRefusalError):
            scope.reserve(
                lease(),
                "METADATA",
                OriginalHeaders.from_request(Request(wrong)),
                listener=object(),
                fence=ListenerFence(1),
                store=object(),
                bridge=object(),
                identity=object(),
                native_owner=object(),
            )
        self.assertTrue(await scope.initialize(operation))
        self.assertEqual(native.header_ids, [id(exact), id(exact)])
        self.assertEqual(native.calls, ["INITIAL", "BEFORE"])

    async def test_a02_a03_changed_authority_tuple_refuses_without_go(self) -> None:
        for change in ({"allowed": False}, {"device_id": "new-device"}, {"family_id": "new"}):
            with self.subTest(change=change):
                native = NativeFake()
                if "allowed" in change:
                    native.allowed = False
                else:
                    native.change = change
                scope, _, _, _, operation, _ = adapter(native)
                self.assertFalse(await scope.initialize(operation))
                self.assertEqual(scope.owner.inspect(scope.handle(operation))[0], State.REFUSED)
                self.assertEqual(native.calls, ["INITIAL"])

    async def test_a04_foreign_operation_equal_lease_and_digest_do_not_grant(self) -> None:
        scope, _, _, _, operation, _ = adapter()
        with self.assertRaises(AuthorityRefusalError):
            scope.handle(OpaqueOperation())
        self.assertTrue(await scope.initialize(operation))
        record = scope._record(operation)
        self.assertIsNotNone(record.headers)
        self.assertNotIn("Bearer", repr(record))
        self.assertFalse(await scope.owner._authority.reauthenticate(lease(), "BEFORE"))

    async def test_a05_a06_a07_pre_go_rechecks_native_home_policy_and_fence(self) -> None:
        for mutation in ("deny", "home", "identity", "retire"):
            with self.subTest(mutation=mutation):
                scope, native, _, fence, operation, _ = adapter()
                self.assertTrue(await scope.initialize(operation))
                scope.start(operation)
                child = object()
                scope.bind_child(operation, child)
                if mutation == "deny":
                    native.allowed = False
                elif mutation == "home":
                    native.home = "/native/home/other"
                elif mutation == "identity":
                    native.change = {"identity": object()}
                else:
                    fence.retire()
                sent: list[object] = []
                self.assertFalse(
                    await scope.go_inline(
                        operation, child, lambda *args, sent=sent: sent.append(args)
                    )
                )
                self.assertEqual(sent, [])
                self.assertFalse(scope.owner.inspect(scope.handle(operation))[1])

    async def test_a05_delayed_child_and_cancel_during_pre_go_zero_send(self) -> None:
        scope, native, _, _, operation, _ = adapter()
        self.assertTrue(await scope.initialize(operation))
        scope.start(operation)
        child = object()
        scope.bind_child(operation, child)
        native.entered = asyncio.Event()
        native.release = asyncio.Event()
        native.stall_phase = "PRE_GO"
        sent: list[object] = []
        task = asyncio.create_task(
            scope.go_inline(operation, child, lambda *args, sent=sent: sent.append(args))
        )
        await native.entered.wait()
        scope.cancel(operation)
        native.release.set()
        self.assertFalse(await task)
        self.assertEqual(sent, [])
        self.assertEqual(scope.owner.inspect(scope.handle(operation))[0], State.UNKNOWN)

    async def test_a05_late_child_attach_is_drain_only(self) -> None:
        scope, _, _, _, operation, _ = adapter()
        self.assertTrue(await scope.initialize(operation))
        scope.start(operation)
        scope.cancel(operation)
        child = object()
        scope.bind_child(operation, child)
        sent: list[object] = []
        self.assertFalse(
            await scope.go_inline(operation, child, lambda *args, sent=sent: sent.append(args))
        )
        self.assertEqual(sent, [])
        self.assertEqual(scope.owner.inspect(scope.handle(operation))[0], State.DRAINING)

    async def test_a07_a10_foreign_child_and_expiry_never_send_go(self) -> None:
        for cause in ("foreign", "expired"):
            with self.subTest(cause=cause):
                scope, native, clock, _, operation, _ = adapter()
                self.assertTrue(await scope.initialize(operation))
                scope.start(operation)
                child = object()
                scope.bind_child(operation, child)
                if cause == "expired":
                    clock.now = 3.0
                sent: list[object] = []
                selected = object() if cause == "foreign" else child
                self.assertFalse(
                    await scope.go_inline(
                        operation, selected, lambda *args, sent=sent: sent.append(args)
                    )
                )
                self.assertEqual(sent, [])
                self.assertNotIn("PRE_GO", native.calls)

    async def test_a10_pre_go_permit_cannot_cross_child_or_replay(self) -> None:
        from hmp_plugin.presentation_authority import _Permit

        scope, _, _, _, operation, _ = adapter()
        self.assertTrue(await scope.initialize(operation))
        scope.start(operation)
        child = object()
        scope.bind_child(operation, child)
        record = scope._record(operation)
        valid = _Permit(
            operation, record.handle, child, scope.owner.challenge(record.handle), "PRE_GO", 1
        )
        record.permit = valid
        self.assertFalse(
            scope._consume(record, dataclasses.replace(valid, child=object()), "PRE_GO")
        )
        self.assertFalse(
            scope._consume(record, dataclasses.replace(valid, challenge="c" * 64), "PRE_GO")
        )
        self.assertTrue(scope._consume(record, valid, "PRE_GO"))
        self.assertFalse(scope._consume(record, valid, "PRE_GO"))

    async def test_a08_a11_unknown_native_owner_retained_and_disables(self) -> None:
        scope, native, _, _, operation, _ = adapter()
        native.raise_phase = "INITIAL"
        self.assertFalse(await scope.initialize(operation))
        self.assertTrue(scope.disabled)
        self.assertIsNotNone(scope._record(operation).headers)
        with self.assertRaises(AuthorityRefusalError):
            scope.reserve(
                lease(),
                "METADATA",
                headers(),
                listener=object(),
                fence=ListenerFence(1),
                store=object(),
                bridge=object(),
                identity=object(),
                native_owner=object(),
            )

    async def test_a09_a10_pre_emit_revoke_replay_and_exact_child(self) -> None:
        scope, native, _, _, operation, _ = adapter()
        self.assertTrue(await scope.initialize(operation))
        scope.start(operation)
        child = object()
        scope.bind_child(operation, child)
        sent: list[object] = []
        self.assertTrue(
            await scope.go_inline(operation, child, lambda *args, sent=sent: sent.append(args))
        )
        self.assertEqual(len(sent), 1)
        await finish_child(scope, operation, child)
        self.assertTrue(await scope.reauthorize(operation))
        record = scope._record(operation)
        permit = record.permit
        self.assertIsNotNone(permit)
        self.assertFalse(
            scope._consume(record, dataclasses.replace(permit, child=object()), "PRE_EMIT")
        )
        values: list[dict[str, object]] = []
        self.assertTrue(scope.emit_inline(operation, lambda header, body: values.append(header)))
        self.assertEqual(len(values), 1)
        self.assertFalse(scope._consume(record, permit, "PRE_EMIT"))
        self.assertFalse(scope.emit_inline(operation, lambda header, body: values.append(header)))
        self.assertEqual(len(values), 1)
        self.assertTrue(await scope.retire_known(operation))
        with self.assertRaises(AuthorityRefusalError):
            scope.handle(operation)
        self.assertEqual(native.calls, ["INITIAL", "BEFORE", "PRE_GO", "PRE_EMIT"])

    async def test_a09_late_pre_emit_return_after_cancel_discarded(self) -> None:
        scope, native, _, _, operation, _ = adapter()
        self.assertTrue(await scope.initialize(operation))
        scope.start(operation)
        child = object()
        scope.bind_child(operation, child)
        self.assertTrue(await scope.go_inline(operation, child, lambda *_: None))
        await finish_child(scope, operation, child)
        native.entered = asyncio.Event()
        native.release = asyncio.Event()
        native.stall_phase = "PRE_EMIT"
        task = asyncio.create_task(scope.reauthorize(operation))
        await native.entered.wait()
        scope.cancel(operation)
        native.release.set()
        self.assertFalse(await task)
        self.assertNotEqual(scope.owner.inspect(scope.handle(operation))[0], State.REAUTHORIZED)

    async def test_a10_go_callback_failure_is_unknown_not_replayed(self) -> None:
        for outcome in ("raise", "value"):
            with self.subTest(outcome=outcome):
                scope, _, _, _, operation, _ = adapter()
                self.assertTrue(await scope.initialize(operation))
                scope.start(operation)
                child = object()
                scope.bind_child(operation, child)

                def send_go(*_args, outcome=outcome):
                    if outcome == "raise":
                        raise RuntimeError("untrusted private text")
                    return True

                self.assertFalse(await scope.go_inline(operation, child, send_go))
                self.assertEqual(scope.owner.inspect(scope.handle(operation))[0], State.UNKNOWN)
                self.assertTrue(scope.disabled)
                self.assertIsNotNone(scope._record(operation).headers)

    async def test_a11_native_drain_failure_retains_credential_and_unknown(self) -> None:
        scope, native, _, _, operation, _ = adapter()
        native.allowed = False
        self.assertFalse(await scope.initialize(operation))
        native.drain_result = False
        self.assertFalse(await scope.retire_known(operation))
        self.assertTrue(scope.disabled)
        self.assertIsNotNone(scope._record(operation).headers)

    async def test_a18_unbound_known_refusal_can_retire_without_grant(self) -> None:
        scope = ParentAuthorityAdapter("iid", clock=Clock(), challenge_source=lambda: "a" * 64)
        owned = [object() for _ in range(5)]
        operation = scope.reserve(
            lease(),
            "METADATA",
            headers(),
            listener=owned[0],
            fence=ListenerFence(1),
            store=owned[1],
            bridge=owned[2],
            identity=owned[3],
            native_owner=owned[4],
        )
        self.assertFalse(await scope.initialize(operation))
        self.assertTrue(await scope.retire_known(operation))
        self.assertFalse(scope.disabled)
        with self.assertRaises(AuthorityRefusalError):
            scope.handle(operation)

    async def test_a14_shared_waiting_cap_and_no_second_queue(self) -> None:
        native = NativeFake()
        clock = Clock()
        scope = ParentAuthorityAdapter(
            "iid", service=native, clock=clock, challenge_source=lambda: "a" * 64
        )
        owned = [object() for _ in range(5)]
        operations = []
        for _ in range(16):
            operations.append(
                scope.reserve(
                    lease(),
                    "METADATA",
                    headers(),
                    listener=owned[0],
                    fence=ListenerFence(1),
                    store=owned[1],
                    bridge=owned[2],
                    identity=owned[3],
                    native_owner=owned[4],
                )
            )
        with self.assertRaises(AuthorityRefusalError):
            scope.reserve(
                lease(),
                "METADATA",
                headers(),
                listener=owned[0],
                fence=ListenerFence(1),
                store=owned[1],
                bridge=owned[2],
                identity=owned[3],
                native_owner=owned[4],
            )
        self.assertEqual(len(operations), 16)
        self.assertEqual(native.calls, [])
        self.assertEqual(len(scope.owner._waiting), 16)

    async def test_a17_positive_full_parent_owned_flow_and_a18_unbound(self) -> None:
        unbound = ParentAuthorityAdapter("iid", clock=Clock(), challenge_source=lambda: "a" * 64)
        objects = [object() for _ in range(5)]
        op = unbound.reserve(
            lease(),
            "METADATA",
            headers(),
            listener=objects[0],
            fence=ListenerFence(1),
            store=objects[1],
            bridge=objects[2],
            identity=objects[3],
            native_owner=objects[4],
        )
        self.assertFalse(await unbound.initialize(op))
        self.assertEqual(unbound.owner.inspect(unbound.handle(op))[0], State.REFUSED)

        scope, native, _, _, operation, exact = adapter()
        self.assertTrue(await scope.initialize(operation))
        scope.start(operation)
        child = object()
        scope.bind_child(operation, child)
        sent: list[object] = []
        self.assertTrue(
            await scope.go_inline(operation, child, lambda *args, sent=sent: sent.append(args))
        )
        await finish_child(scope, operation, child)
        self.assertTrue(await scope.reauthorize(operation))
        emitted: list[object] = []
        self.assertTrue(
            scope.emit_inline(operation, lambda header, body: emitted.append((header, body)))
        )
        self.assertTrue(await scope.retire_known(operation))
        self.assertEqual(len(sent), 1)
        self.assertEqual(len(emitted), 1)
        self.assertEqual(native.header_ids, [id(exact)] * 4)
        self.assertEqual(native.calls, ["INITIAL", "BEFORE", "PRE_GO", "PRE_EMIT"])

    async def test_native_initial_single_flight_for_thirty_callers(self) -> None:
        scope, native, _, fence, operation, exact = adapter()
        native.entered = asyncio.Event()
        native.release = asyncio.Event()
        native.stall_phase = "INITIAL"
        first = asyncio.create_task(scope.initialize(operation))
        await native.entered.wait()
        others = [asyncio.create_task(scope.initialize(operation)) for _ in range(29)]
        refused = await asyncio.gather(*others, return_exceptions=True)
        self.assertTrue(
            all(value is False or type(value) is AuthorityRefusalError for value in refused)
        )
        self.assertEqual(native.calls, ["INITIAL"])
        self.assertEqual(len(scope._by_operation), 1)
        self.assertEqual(len(scope.owner._jobs), 1)
        self.assertIs(scope._record(operation).headers, exact)
        self.assertFalse(fence.current)
        self.assertTrue(scope.disabled)
        self.assertIs(scope.owner.inspect(scope.handle(operation))[0], State.UNKNOWN)
        native.release.set()
        self.assertFalse(await first)
        self.assertEqual(native.calls, ["INITIAL"])

    async def test_native_overlap_across_initial_before_pre_go_pre_emit(self) -> None:
        for phase in ("INITIAL", "BEFORE", "PRE_GO", "PRE_EMIT"):
            with self.subTest(phase=phase):
                scope, native, _, _, operation, exact = adapter()
                if phase in ("PRE_GO", "PRE_EMIT"):
                    self.assertTrue(await scope.initialize(operation))
                    scope.start(operation)
                    child = object()
                    scope.bind_child(operation, child)
                    if phase == "PRE_EMIT":
                        self.assertTrue(await scope.go_inline(operation, child, lambda *_: None))
                        await finish_child(scope, operation, child)
                native.entered = asyncio.Event()
                native.release = asyncio.Event()
                native.stall_phase = phase
                if phase in ("INITIAL", "BEFORE"):
                    first = asyncio.create_task(scope.initialize(operation))
                elif phase == "PRE_GO":
                    first = asyncio.create_task(scope.go_inline(operation, child, lambda *_: None))
                else:
                    first = asyncio.create_task(scope.reauthorize(operation))
                await native.entered.wait()
                count = len(native.calls)
                if phase == "INITIAL":
                    self.assertFalse(
                        await scope.owner._authority.reauthenticate(
                            scope._record(operation).lease, "BEFORE"
                        )
                    )
                elif phase == "BEFORE":
                    self.assertFalse(await scope.initialize(operation))
                elif phase == "PRE_GO":
                    self.assertFalse(await scope.go_inline(operation, child, lambda *_: None))
                else:
                    self.assertFalse(await scope.reauthorize(operation))
                self.assertEqual(len(native.calls), count)
                self.assertTrue(scope.disabled)
                self.assertIs(scope._record(operation).headers, exact)
                native.release.set()
                self.assertFalse(await first)
                self.assertIs(scope.owner.inspect(scope.handle(operation))[0], State.UNKNOWN)

    async def test_task_cancellation_at_each_native_await_retains_unknown(self) -> None:
        for phase in ("INITIAL", "BEFORE", "PRE_GO", "PRE_EMIT"):
            with self.subTest(phase=phase):
                scope, native, _, fence, operation, exact = adapter()
                if phase in ("PRE_GO", "PRE_EMIT"):
                    self.assertTrue(await scope.initialize(operation))
                    scope.start(operation)
                    child = object()
                    scope.bind_child(operation, child)
                    if phase == "PRE_EMIT":
                        self.assertTrue(await scope.go_inline(operation, child, lambda *_: None))
                        await finish_child(scope, operation, child)
                native.entered = asyncio.Event()
                native.release = asyncio.Event()
                native.stall_phase = phase
                if phase in ("INITIAL", "BEFORE"):
                    task = asyncio.create_task(scope.initialize(operation))
                elif phase == "PRE_GO":
                    task = asyncio.create_task(scope.go_inline(operation, child, lambda *_: None))
                else:
                    task = asyncio.create_task(scope.reauthorize(operation))
                await native.entered.wait()
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertTrue(scope.disabled)
                self.assertFalse(fence.current)
                self.assertIs(scope._record(operation).headers, exact)
                self.assertIsNotNone(scope._record(operation).native_claim)
                self.assertIs(scope.owner.inspect(scope.handle(operation))[0], State.UNKNOWN)
                self.assertFalse(scope.owner.inspect(scope.handle(operation))[2])
                self.assertEqual(native.calls.count(phase), 1)

    async def test_cancel_during_pending_pre_go_blocks_late_success(self) -> None:
        scope, native, _, _, operation, exact = adapter()
        self.assertTrue(await scope.initialize(operation))
        scope.start(operation)
        child = object()
        scope.bind_child(operation, child)
        native.entered = asyncio.Event()
        native.release = asyncio.Event()
        native.stall_phase = "PRE_GO"
        sent: list[object] = []
        pending = asyncio.create_task(
            scope.go_inline(operation, child, lambda *args: sent.append(args))
        )
        await native.entered.wait()
        scope.cancel(operation)
        self.assertIs(scope.owner.inspect(scope.handle(operation))[0], State.UNKNOWN)
        native.release.set()
        self.assertFalse(await pending)
        self.assertEqual(sent, [])
        self.assertIs(scope._record(operation).headers, exact)
        self.assertIsNotNone(scope._record(operation).native_claim)

    async def test_swallowed_task_cancellation_cannot_grant_late_native_return(self) -> None:
        scope, native, _, fence, operation, exact = adapter()
        native.entered = asyncio.Event()
        native.release = asyncio.Event()
        native.stall_phase = "INITIAL"
        native.swallow_cancel = True
        pending = asyncio.create_task(scope.initialize(operation))
        await native.entered.wait()
        pending.cancel()
        native.release.set()
        self.assertFalse(await pending)
        self.assertTrue(scope.disabled)
        self.assertFalse(fence.current)
        self.assertIs(scope._record(operation).headers, exact)
        self.assertIsNotNone(scope._record(operation).native_claim)
        self.assertIs(scope.owner.inspect(scope.handle(operation))[0], State.UNKNOWN)
        self.assertEqual(native.calls, ["INITIAL"])

    async def test_drain_single_flight_and_cancel_retains_native_custody(self) -> None:
        scope, native, _, _, operation, exact = adapter()
        native.allowed = False
        self.assertFalse(await scope.initialize(operation))
        native.drain_entered = asyncio.Event()
        native.drain_release = asyncio.Event()
        first = asyncio.create_task(scope.retire_known(operation))
        await native.drain_entered.wait()
        self.assertFalse(await scope.retire_known(operation))
        self.assertEqual(native.drain_calls, 1)
        self.assertTrue(scope.disabled)
        native.drain_release.set()
        self.assertFalse(await first)
        self.assertIs(scope._record(operation).headers, exact)
        self.assertIsNotNone(scope._record(operation).native_claim)

        other, service, _, _, other_op, other_headers = adapter()
        service.allowed = False
        self.assertFalse(await other.initialize(other_op))
        service.drain_entered = asyncio.Event()
        service.drain_release = asyncio.Event()
        task = asyncio.create_task(other.retire_known(other_op))
        await service.drain_entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(other.disabled)
        self.assertEqual(service.drain_calls, 1)
        self.assertIs(other._record(other_op).headers, other_headers)
        self.assertIsNotNone(other._record(other_op).native_claim)

        suppressed, port, _, _, suppressed_op, suppressed_headers = adapter()
        port.allowed = False
        self.assertFalse(await suppressed.initialize(suppressed_op))
        port.drain_entered = asyncio.Event()
        port.drain_release = asyncio.Event()
        port.swallow_cancel = True
        pending = asyncio.create_task(suppressed.retire_known(suppressed_op))
        await port.drain_entered.wait()
        pending.cancel()
        port.drain_release.set()
        self.assertFalse(await pending)
        self.assertTrue(suppressed.disabled)
        self.assertEqual(port.drain_calls, 1)
        self.assertIs(suppressed._record(suppressed_op).headers, suppressed_headers)
        self.assertIsNotNone(suppressed._record(suppressed_op).native_claim)

    async def test_known_completed_refusal_drain_retires_once(self) -> None:
        scope, native, _, _, operation, exact = adapter()
        native.allowed = False
        self.assertFalse(await scope.initialize(operation))
        self.assertTrue(await scope.retire_known(operation))
        self.assertEqual(native.drain_calls, 1)
        self.assertNotIn(operation, scope._by_operation)
        with self.assertRaises(AuthorityRefusalError):
            await scope.retire_known(operation)
        self.assertNotIn("Bearer", repr(exact))


if __name__ == "__main__":
    unittest.main()


def test_one_process_cannot_be_retained_by_two_authorities():
    from hmp_plugin.presentation_jobs import FrameError
    from hmp_plugin.presentation_process import PresentationProcessOwner

    async def run():
        first, _, _, _, one, _ = adapter()
        second, _, _, _, two, _ = adapter()
        assert await first.initialize(one)
        assert await second.initialize(two)
        first.start(one)
        second.start(two)
        process = PresentationProcessOwner()
        first.retain_process(one, process)
        import pytest

        with pytest.raises(FrameError):
            second.retain_process(two, process)
        assert first._record(one).process_owner is process
        assert second._record(two).process_owner is None

    asyncio.run(run())


def test_retained_unlaunched_process_requires_explicit_closure_before_drain():
    from hmp_plugin.presentation_process import PresentationProcessOwner

    async def run():
        scope, native, _, _, operation, _ = adapter()
        assert await scope.initialize(operation)
        scope.start(operation)
        process = PresentationProcessOwner()
        scope.retain_process(operation, process)
        scope.owner.refuse_prelaunch(scope.handle(operation))
        assert not await scope.retire_known(operation)
        assert native.drain_calls == 0
        assert scope._record(operation).headers is not None
        process.seal_unlaunched()
        assert await scope.retire_known(operation)
        assert native.drain_calls == 1

    asyncio.run(run())


def test_clock_reentry_cannot_overwrite_first_retained_process():
    import pytest

    from hmp_plugin.presentation_process import PresentationProcessOwner

    async def run():
        scope, _, clock, _, operation, _ = adapter()
        assert await scope.initialize(operation)
        scope.start(operation)
        inner, outer = PresentationProcessOwner(), PresentationProcessOwner()
        entered = False

        def reenter():
            nonlocal entered
            if not entered:
                entered = True
                scope.retain_process(operation, inner)
            return clock.now

        scope._clock = reenter
        with pytest.raises(AuthorityRefusalError):
            scope.retain_process(operation, outer)
        record = scope._record(operation)
        assert record.process_owner is inner
        assert inner.owns(record.process_binding)
        assert outer._binding is None

    asyncio.run(run())


def test_cancellation_retires_output_before_termination_request(monkeypatch):
    from types import SimpleNamespace

    from hmp_plugin import presentation_process as module
    from hmp_plugin.presentation_process import PresentationProcessOwner

    async def run():
        scope, _, _, fence, operation, _ = adapter()
        assert await scope.initialize(operation)
        scope.start(operation)
        child = SimpleNamespace(pid=123456, returncode=None)
        monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: child)
        process = PresentationProcessOwner()
        scope.retain_process(operation, process)
        process.start()
        scope.bind_child(operation, child)
        monkeypatch.setattr(module.os, "getpgid", lambda pid: pid)
        observed = []
        monkeypatch.setattr(module.os, "killpg", lambda *a: observed.append(fence.current))
        assert scope.terminate_cancelled_reader(operation)
        assert observed == [False]
        assert not process.reaped and not process.group_absent
        assert not await scope.retire_known(operation)

    asyncio.run(run())


def test_actual_empty_reader_closure_releases_only_after_exact_observations():
    import time

    from hmp_plugin.presentation_control_pipe import OwnedControlPipe
    from hmp_plugin.presentation_pipes import OwnedPresentationPipes
    from hmp_plugin.presentation_process import PresentationProcessOwner

    async def run():
        scope, _, _, _, operation, _ = adapter()
        assert await scope.initialize(operation)
        scope.start(operation)
        process = PresentationProcessOwner()
        scope.retain_process(operation, process)
        process.start()
        child = process.child
        scope.bind_child(operation, child)
        pipes = OwnedPresentationPipes(child.stdout, child.stderr)
        control = OwnedControlPipe(
            child.stdin, handle=scope.handle(operation), child=child, current=lambda: False
        )
        scope.cancel(operation)
        assert not scope.collect_reader_closure(operation, pipes, control)
        control.close_for_drain()
        deadline = time.monotonic() + 2.0
        while not pipes.drained:
            pipes.poll(deadline=deadline)
        while not process.poll_wait():
            assert time.monotonic() < deadline
            await asyncio.sleep(0.005)
        assert process.probe_group_absence()
        assert scope.collect_reader_closure(operation, pipes, control)
        assert not scope.collect_reader_closure(operation, pipes, control)
        assert await scope.retire_known(operation)

    asyncio.run(run())


def test_collected_large_v2_avatar_reaches_codec_without_oversized_feed(monkeypatch):
    """Inert closure projection/codec composition, not OS custody qualification."""
    import hashlib
    from types import SimpleNamespace

    from hmp_plugin.presentation_control_pipe import OwnedControlPipe
    from hmp_plugin.presentation_jobs import decode_output
    from hmp_plugin.presentation_output_v2 import BoundedResultBufferV2, encode_output_v2
    from hmp_plugin.presentation_pipes import OwnedPresentationPipes
    from hmp_plugin.presentation_process import PresentationProcessOwner

    async def run():
        scope, _, _, _, operation, _ = adapter()
        assert await scope.initialize(operation)
        scope.start(operation)
        process = PresentationProcessOwner()
        scope.retain_process(operation, process)
        child = SimpleNamespace(stdout=object(), stderr=object(), stdin=object())
        process._child = child
        process._wait_status = 0
        process.group_absent = process.signals_retired = True
        scope.bind_child(operation, child)
        challenge = scope.owner.challenge(scope.handle(operation))
        row, _ = decode_output(output(scope, operation), challenge, 1)
        avatar = b"synthetic-avatar-codec-fixture" * 5000
        digest = hashlib.sha256(avatar).hexdigest()
        row.update(
            schema=2,
            mime="image/png",
            width=256,
            height=256,
            avatar_length=len(avatar),
            avatar_sha=digest,
        )
        row["source_proof"].update(avatar_meta=[1] * 9, avatar_body_sha=digest)
        row["ledger"].update(hash_bytes=len(avatar), yaml_tokens=0)
        wire = encode_output_v2(row, avatar)
        assert len(wire) > 65536
        pipes = object.__new__(OwnedPresentationPipes)
        pipes._streams = {"result": child.stdout, "diagnostic": child.stderr}
        pipes._output = bytearray(wire)
        pipes._cleanup_deadline = None
        pipes._closed = pipes._eof = {"result", "diagnostic"}
        pipes._selector_closed = True
        pipes.uncertain = False
        pipes.diagnostic_bytes = 0
        control = object.__new__(OwnedControlPipe)
        control._stream, control._child = child.stdin, child
        control._handle = scope.handle(operation)
        control.closed, control.uncertain = True, False
        buffer = BoundedResultBufferV2()
        chunks = []

        def feed(handle, chunk, exact_child):
            assert handle is control._handle and exact_child is child
            chunks.append(len(chunk))
            buffer.feed(chunk)

        monkeypatch.setattr(scope.owner, "feed_result", feed)
        monkeypatch.setattr(scope.owner, "diagnostic", lambda *args: None)
        monkeypatch.setattr(scope.owner, "custody", lambda *args: None)
        scope.collect_reader_closure(operation, pipes, control)
        assert len(chunks) > 1 and max(chunks) <= 65536
        assert buffer.finish(challenge, 1) == (row, avatar)
        assert not scope.collect_reader_closure(operation, pipes, control)

    asyncio.run(run())


@pytest.mark.parametrize("post_go_fixture", [False, True])
def test_actual_expired_reader_drains_only_after_exit_and_never_emits(post_go_fixture):
    """Actual empty child; post-GO JobOwner state is an inert lifecycle fixture."""
    import time

    import pytest

    from hmp_plugin.presentation_control_pipe import OwnedControlPipe
    from hmp_plugin.presentation_jobs import FrameError
    from hmp_plugin.presentation_pipes import OwnedPresentationPipes
    from hmp_plugin.presentation_process import PresentationProcessOwner

    async def run():
        scope, native, _, fence, operation, _ = adapter()
        assert await scope.initialize(operation)
        scope.start(operation)
        process = PresentationProcessOwner()
        scope.retain_process(operation, process)
        process.start()
        child = process.child
        scope.bind_child(operation, child)
        pipes = OwnedPresentationPipes(child.stdout, child.stderr)
        control = OwnedControlPipe(
            child.stdin, handle=scope.handle(operation), child=child, current=lambda: False
        )
        if post_go_fixture:
            scope.owner.go(
                scope.handle(operation), child, scope.owner.challenge(scope.handle(operation))
            )
        with pytest.raises(FrameError, match="BI1_PIPE_DEADLINE"):
            pipes.poll(deadline=time.monotonic() - 1.0)
        assert not scope.drain_cancelled_reader(operation, pipes, control)
        assert pipes._cleanup_deadline is None and fence.current
        control.close_for_drain()
        deadline = time.monotonic() + 2.0
        while not process.poll_wait():
            assert time.monotonic() < deadline
            await asyncio.sleep(0.005)
        assert not scope.drain_cancelled_reader(operation, pipes, control)
        assert pipes._cleanup_deadline is None
        assert process.probe_group_absence()
        exact_handle = control._handle
        control._handle = object()
        assert not scope.drain_cancelled_reader(operation, pipes, control)
        assert pipes._cleanup_deadline is None
        control._handle = exact_handle
        while not scope.drain_cancelled_reader(operation, pipes, control):
            assert time.monotonic() < deadline
            await asyncio.sleep(0.005)
        assert not fence.current and pipes.output == b""
        collected = scope.collect_reader_closure(operation, pipes, control)
        assert collected
        assert not await scope.reauthorize(operation)
        assert not scope.emit_inline(operation, lambda *_: pytest.fail("must not emit"))
        assert await scope.retire_known(operation)
        assert native.drain_calls == 1

    asyncio.run(run())


@pytest.mark.parametrize("native_closed", [False, True])
def test_actual_go_write_then_termination_releases_refusal_not_output(native_closed):
    """Synthetic native authority; actual fixed child, input/GO, kill and cleanup."""
    import os
    import stat
    import tempfile
    import time
    from pathlib import Path

    from hmp_plugin.presentation_control_pipe import OwnedControlPipe
    from hmp_plugin.presentation_input_v2 import prefixes
    from hmp_plugin.presentation_input_v3 import encode_input_v3
    from hmp_plugin.presentation_pipes import OwnedPresentationPipes
    from hmp_plugin.presentation_process import PresentationProcessOwner

    async def run(root):
        home = root / "profiles" / "alpha"
        home.mkdir(parents=True, mode=0o700)
        native = NativeFake()
        native.home = str(home)
        iid = "a" * 52
        scope = ParentAuthorityAdapter(iid, service=native)
        operation = scope.reserve(
            dataclasses.replace(lease(), iid=iid),
            "METADATA",
            OriginalHeaders.from_request(
                Request({"Authorization": ["Bearer " + "A" * 43], "HMP-Instance": [iid]})
            ),
            listener=object(),
            fence=ListenerFence(1),
            store=object(),
            bridge=object(),
            identity=object(),
            native_owner=object(),
        )
        assert await scope.initialize(operation)
        scope.start(operation)
        process = PresentationProcessOwner()
        scope.retain_process(operation, process)
        process.start()
        child = process.child
        scope.bind_child(operation, child)
        pipes = OwnedPresentationPipes(child.stdout, child.stderr)
        record = scope._record(operation)
        control = OwnedControlPipe(
            child.stdin,
            handle=scope.handle(operation),
            child=child,
            current=lambda: scope._current(record),
        )
        chain = prefixes(str(home))
        counts = {
            "read_bytes": 0,
            "hash_bytes": 0,
            "opens": len(chain),
            "metadata": 4 * len(chain),
            "path_bytes": 3 * (1 + sum(len(p.encode()) for p in str(home)[1:].split("/"))),
            "yaml_nodes": 0,
            "yaml_tokens": 0,
            "raster_units": 0,
        }
        packet = encode_input_v3(
            {
                "schema": 3,
                "challenge": scope.owner.challenge(scope.handle(operation)),
                "epoch": 1,
                "profile": "alpha",
                "root": str(root),
                "home": str(home),
                "operation": "METADATA",
                "expected_avatar_sha": None,
                "uid": os.geteuid(),
                "gid": os.getegid(),
                "dir_modes": [0o700, 0o750, 0o755],
                "leaf_modes": [0o600, 0o640, 0o644],
                "source_manifest_sha": "b" * 64,
                "deadline_ns": int(record.deadline * 1e9),
                "directory_policy": [
                    [os.stat(p).st_uid, os.stat(p).st_gid, stat.S_IMODE(os.stat(p).st_mode)]
                    for p in chain
                ],
                "iid": iid,
                "canonical_fallback": "Hermes",
                "observed_at": 100,
                "parent_work_counts": counts,
            }
        )
        control.write_input(packet)
        assert await scope.go_inline(operation, child, control.send_go)
        assert control.closed and scope.owner.inspect(scope.handle(operation))[1]
        assert scope.terminate_cancelled_reader(operation)
        limit = time.monotonic() + 2.0
        while not process.poll_wait():
            assert time.monotonic() < limit
            await asyncio.sleep(0.005)
        assert process.probe_group_absence()
        while not scope.drain_cancelled_reader(operation, pipes, control):
            assert time.monotonic() < limit
            await asyncio.sleep(0.005)
        assert scope.collect_reader_closure(operation, pipes, control)
        assert scope.owner.inspect(scope.handle(operation)) == (State.REFUSED, True, True)
        assert not await scope.reauthorize(operation)
        assert not scope.emit_inline(operation, lambda *_: pytest.fail("aborted output"))
        native.drain_result = native_closed
        assert await scope.retire_known(operation) is native_closed
        assert native.drain_calls == 1
        if not native_closed:
            assert scope._record(operation).headers is not None
            assert scope._record(operation).native_claim is not None
            assert scope.disabled

    with tempfile.TemporaryDirectory(prefix="hmp-abort-synthetic-", dir=Path.cwd()) as directory:
        asyncio.run(run(Path(directory)))


@pytest.mark.parametrize("late", [False, True])
def test_cancel_freezes_original_budget_at_first_cause(late):
    scope, native, clock, fence, operation, _ = adapter()
    record = scope._record(operation)
    clock.now = record.deadline + 1 if late else 1.1
    scope.cancel(operation)
    end = min(int(clock.now * 1_000_000_000), int(record.deadline * 1_000_000_000)) + 250_000_000
    assert CancellationBudget.inspect(record.cleanup_budget)[2:] == (end, False)
    clock.now += 0.1
    scope.cancel(operation)
    assert CancellationBudget.inspect(record.cleanup_budget)[2:] == (end, False)
    assert native.calls == [] and not fence.current


def test_cancel_clock_reentry_cannot_create_fresh_allowance():
    scope, native, clock, fence, operation, _ = adapter()
    record = scope._record(operation)
    def reenter():
        scope.cancel(operation)
        return clock.now
    scope._clock = reenter
    scope.cancel(operation)
    assert CancellationBudget.inspect(record.cleanup_budget)[2:] == (None, True)
    assert scope.disabled and native.calls == [] and not fence.current
