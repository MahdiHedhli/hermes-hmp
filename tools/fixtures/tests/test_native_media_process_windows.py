"""Finite source-owner obligations with explicit inert issuer/readback/close models."""

import json
import runpy
import time
import unittest
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import native_media_process_windows as windows
import native_media_worker as worker

ROOT = Path(__file__).resolve().parents[1]
M = SimpleNamespace(
    **runpy.run_path(str(ROOT / "tests/process_window_models.py"), run_name="_inert_window_models")
)
CAUSALS = []


def graph(role="A", sequence=1):
    return M.command({"op": "CHECK_GRAPH", "phase": "GRAPH_IMPORT"}, role, sequence)


def finish(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    raise AssertionError("unexpected suspension")


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.scope = M.InertScope()
        self.scope.__enter__()
        self.addCleanup(self.scope.__exit__, None, None, None)

    def window(self, commands=None, **kwargs):
        value = self.scope.window([graph()] if commands is None else commands, **kwargs)
        owner = SimpleNamespace()
        value.claim(owner)
        return (value, owner)

    def runtime(self, commands, **kwargs):
        runtime = object.__new__(worker.NativeRuntime)
        runtime.spec = {"role": "A", "port": 54321, "iid": "iid-A"}
        runtime.runner = runtime.ctx = None
        runtime.raw, runtime.producer_receipts, runtime.seeded_profiles = ({}, {}, set())
        window = self.scope.attach(runtime, commands, **kwargs)
        calls = []

        async def action(command, **_kwargs):
            calls.append(command["op"])
            return {"event": "inert"}

        runtime._action = action
        return (runtime, window, calls)

    def record(self, name):
        CAUSALS.append(name)

    def test_cw01(self):
        with patch.object(windows, "_require_root_continuation_issuer", self.scope.old[0]):
            for value in (None, True, {}, object.__new__(windows._RootContinuationIssuance)):
                with self.assertRaises(windows.WindowRefusedError):
                    windows.ProcessWindowLease(value)
        self.assertFalse(hasattr(windows.WindowLedger, "close_known"))
        forged = object.__new__(windows.ProcessWindowLease)
        forged._journal = windows._JournalState(
            (), M.MODEL_CAPS, time.monotonic() + 10, time.monotonic
        )
        forged._journal.held = 1
        with self.assertRaises(windows.WindowRefusedError):
            windows.WindowLedger(forged)
        self.assertEqual(forged._journal.held, 1)
        self.record("CW01")

    def test_cw02(self):
        with self.assertRaises(windows.WindowRefusedError):
            windows._JournalState(
                (windows._command_bytes(graph()), windows._command_bytes(graph())),
                M.MODEL_CAPS,
                10,
                lambda: 0,
            )
        window, _ = self.window()
        with self.assertRaises(windows.WindowRefusedError):
            self.scope.window([graph()], journal=window._journal, positions=(0,))
        self.assertIsNotNone(window._journal.first_failure)
        self.record("CW02")

    def test_cw03(self):
        commands = [graph("A", 1), graph("B", 1), graph("A", 2)]
        journal = windows._JournalState(
            tuple(windows._command_bytes(c) for c in commands),
            M.MODEL_CAPS,
            time.monotonic() + 10,
            time.monotonic,
        )
        a, ao = self.window(commands, journal=journal, positions=(0, 2), role="A")
        b, bo = self.window(commands, journal=journal, positions=(1,), role="B", enrolled=False)
        a.complete(a.consume(ao, commands[0]), {})
        b.complete(b.consume(bo, commands[1]), {})
        a.complete(a.consume(ao, commands[2]), {})
        self.assertEqual(journal.consumed, {0, 1, 2})
        c, co = self.window([graph(), graph(sequence=2)], positions=(1,))
        with self.assertRaises(windows.WindowRefusedError):
            c.consume(co, graph(sequence=2))
        self.assertEqual(c._journal.consumed, set())
        self.record("CW03")

    def test_cw04(self):
        window, _ = self.window()
        with self.assertRaises(windows.WindowRefusedError):
            window.claim(SimpleNamespace())
        self.assertIsNotNone(window._journal.first_failure)
        fresh, _ = self.window()
        with (
            patch.object(windows, "CommandLease", type("Foreign", (), {})),
            self.assertRaises(windows.WindowRefusedError),
        ):
            fresh.ledger.tick()
        self.assertIsNotNone(fresh._journal.first_failure)
        self.record("CW04")

    def test_cw05(self):
        window, owner = self.window()
        ticket = window.consume(owner, graph())
        original = RuntimeError("private unknown")
        window.poison(original)
        with self.assertRaises(windows.WindowRefusedError):
            window.consume(owner, graph())
        self.assertEqual(window._journal.consumed, {0})
        self.assertEqual(window._journal.unknown, {ticket.position})
        self.assertIs(window._journal.first_failure, original)
        self.record("CW05")

    def test_cw06(self):
        window, owner = self.window()
        ticket = window.consume(owner, graph())

        def reentry(_issuance):
            with suppress(windows.WindowRefusedError):
                window.checkpoint(owner, ticket)

        self.scope.hook = reentry
        with self.assertRaises(windows.WindowRefusedError):
            window.checkpoint(owner, ticket)
        self.assertIsNotNone(window.first_failure)
        self.assertFalse(window._journal.observations)
        for field in ("credits", "peak", "next_position"):
            self.scope.hook = None
            other, _ = self.window()
            other.ledger.charge("commands", 1)
            other._journal.peak = 1
            other._journal.observation = self.scope.observation(
                other._journal.observation.revision + 1, other._journal.snapshot()
            )

            def mutate(_issuance, target=other, name=field):
                if name == "credits":
                    target._journal.credits["commands"] = 0
                elif name == "peak":
                    target._journal.peak = 0
                else:
                    target._journal.next_position = 1

            self.scope.hook = mutate
            with self.assertRaises(windows.WindowRefusedError):
                other.ledger.tick()
            self.assertIsNotNone(other._journal.first_failure)
        self.scope.hook = None
        self.record("CW06")

    def test_cw07(self):
        window, _ = self.window()
        window.ledger.charge("commands", 1)
        debt = window.ledger.open()
        window.ledger.acquired(debt, 900001)
        closed = []
        with patch.object(
            windows, "os", SimpleNamespace(close=lambda handle: closed.append(handle))
        ):
            window.ledger.close_owned(debt)
        self.assertEqual(closed, [900001])
        self.assertEqual((window._journal.held, window._journal.peak), (0, 1))
        self.assertEqual(window._journal.credits["commands"], 1)
        with self.assertRaises(windows.WindowRefusedError):
            window.ledger.close_owned(debt)
        self.assertEqual(closed, [900001])
        other, _ = self.window()
        uncertain = other.ledger.open()
        other.ledger.acquired(uncertain, 900002)
        first = RuntimeError("first")
        other.poison(first)
        with (
            patch.object(
                windows,
                "os",
                SimpleNamespace(close=lambda _handle: (_ for _ in ()).throw(RuntimeError("close"))),
            ),
            self.assertRaises(windows.WindowRefusedError),
        ):
            other.ledger.close_owned(uncertain)
        self.assertEqual((other._journal.held, uncertain.state), (1, "CLOSE_UNKNOWN"))
        self.assertIs(other._journal.first_failure, first)
        self.record("CW07")

    def test_cw08(self):
        window, owner = self.window()
        ticket = window.consume(owner, graph())
        window.complete(ticket, {"event": "inert"})
        window.poison(OSError("lost receipt"))
        self.assertEqual(window._journal.unknown, {0})
        self.assertFalse(window._journal.observations)
        self.assertIn(0, window._journal.rejected_observations)
        self.record("CW08")

    def test_cw09(self):
        window, owner = self.window()
        ticket = window.consume(owner, graph())
        ticket.body = windows._command_bytes(graph(sequence=2))
        with self.assertRaises(windows.WindowRefusedError):
            window.complete(ticket, {})
        self.assertFalse(window._journal.observations)
        self.record("CW09")

    def test_cw10(self):
        window, _ = self.window(ordinal=1)
        window.stopped = True
        with patch.object(windows, "_require_root_process_retirement", self.scope.old[2]):
            next_window = self.scope.window([], journal=window._journal, positions=(), ordinal=2)
            with self.assertRaises(windows.WindowRefusedError):
                next_window.claim(SimpleNamespace())
        self.assertIsNotNone(window._journal.first_failure)
        self.record("CW10")

    def test_cw11(self):
        window, _ = self.window(ordinal=1)
        error = RuntimeError("failed stop")
        window.poison(error)
        self.scope.retired.add(window)
        window.stopped = True
        with self.assertRaises(windows.WindowRefusedError):
            self.scope.window([], journal=window._journal, positions=(), ordinal=2)
        self.assertIs(window._journal.first_failure, error)
        self.record("CW11")

    def test_cw12(self):
        read = M.command(
            {
                "op": "OWN_READ",
                "phase": "FINAL_START_POSITIVES",
                "actor": "A1",
                "profile": "media-alpha",
                "args": {"path": "/inert"},
            }
        )
        runtime, window, calls = self.runtime([read])

        async def refuse(_command, **_kwargs):
            calls.append("read_started")
            raise RuntimeError("unknown descriptor")

        runtime._action = refuse
        self.scope.begin(runtime, read)
        with self.assertRaises(worker.RefusalError):
            finish(runtime.action(read))
        self.assertIn("A", window._journal.final_read_started)
        self.assertEqual(calls, ["read_started"])
        with self.assertRaises(windows.WindowRefusedError):
            window.before_action(runtime, M.command({"op": "START_GATEWAY"}))
        self.record("CW12")

    def test_cw13(self):
        window = self.scope.window([graph()], dispatcher_type=worker.Dispatcher)
        spec = {
            "format": "native-media-worker-input-v1",
            "role": "A",
            "commandPlan": [graph()],
            "phaseEnds": {"GRAPH_IMPORT": time.monotonic() + 5},
        }
        dispatcher = worker.Dispatcher(spec, window.ledger, window=window)
        error = OSError("private IO")
        dispatcher.fail(error)
        self.assertIs(window._journal.first_failure, error)
        self.assertTrue(dispatcher.failed)
        with self.assertRaises(windows.WindowRefusedError):
            window.ledger.charge("commands", 1)
        self.record("CW13")

    def test_ac01(self):
        window, _ = self.window()
        record = window.actor("A1").current()
        self.assertEqual(window._journal.enrolled["A1"], record.p4)
        runtime, child, _ = self.runtime([graph()])
        lease = child.actor("A1")
        runtime.restore_actor(lease)
        self.assertTrue(lease.restored)
        self.assertEqual(child._journal.enrolled["A1"], record.p4)
        with self.assertRaises(windows.WindowRefusedError):
            runtime.restore_actor(lease)
        self.record("AC01")

    def test_ac02(self):
        runtime, window, _ = self.runtime([graph()])
        for dto in (True, {}, {"actor": "A1"}):
            with self.assertRaises(windows.WindowRefusedError):
                window.restore_actor(runtime, dto)
        self.assertFalse(runtime.actors)
        self.record("AC02")

    def test_ac03(self):
        start = M.command({"op": "START_GATEWAY", "phase": "PUBLIC_ENROLLMENT"})
        runtime, window, calls = self.runtime([start], ordinal=1)
        self.scope.states["A1"] = ("REVOKED", "wrong-user", "wrong-iid", "wrong-bearer")
        self.scope.begin(runtime, start)
        with self.assertRaises(worker.RefusalError):
            finish(runtime.action(start))
        self.assertFalse(calls)
        self.assertFalse(window.started)
        self.record("AC03")

    def test_ac04(self):
        runtime, window, calls = self.runtime([graph()])
        with (
            patch.object(windows, "_require_root_persistent_readback", self.scope.old[1]),
            self.assertRaises(windows.WindowRefusedError),
        ):
            window.restore_actor(runtime, window.actor("A1"))
        self.assertFalse(calls)
        self.record("AC04")

    def test_ac05(self):
        runtime, window, _ = self.runtime([graph()])
        runtime.window = object()
        with self.assertRaises(windows.WindowRefusedError):
            window.runtime_checkpoint(runtime)
        self.assertIsNotNone(window._journal.first_failure)
        self.record("AC05")

    def test_ac06(self):
        command = graph()
        window = self.scope.window([command], dispatcher_type=worker.Dispatcher)
        spec = {
            "format": "native-media-worker-input-v1",
            "role": "A",
            "commandPlan": [command],
            "phaseEnds": {"GRAPH_IMPORT": time.monotonic() + 5},
        }
        dispatcher = worker.Dispatcher(spec, window.ledger, window=window)
        secret = worker.RefusalError("bearer-private-secret")
        secret.add_note("private note")
        secret.__cause__ = RuntimeError("private cause")

        def thrown():
            raise secret

        dispatcher.bind_runtime = thrown
        result = finish(dispatcher.dispatch(command))
        self.assertNotIn("private", json.dumps(result))
        self.assertEqual(result["observation"], {"errorCode": "worker_refused"})
        self.assertIs(window._journal.first_failure, secret)
        self.record("AC06")

    def test_pc01(self):
        command = M.command(
            {"op": "PRODUCE", "profile": "media-alpha", "args": {"invocation": "P01"}}
        )
        runtime, window, calls = self.runtime([command])

        async def throw(_command, **_kwargs):
            calls.append("producer")
            raise RuntimeError("unknown raw")

        runtime._action = throw
        self.scope.begin(runtime, command)
        with self.assertRaises(worker.RefusalError):
            finish(runtime.action(command))
        self.assertEqual(window._journal.produce_claims, {"P01"})
        self.assertFalse(window._journal.producers)
        with self.assertRaises(windows.WindowRefusedError):
            window.consume(window.dispatcher, command)
        self.assertEqual(calls, ["producer"])
        self.record("PC01")

    def test_pc02(self):
        window, _ = self.window()
        with self.assertRaises(windows.WindowRefusedError):
            window.producer("P01", "media-alpha")
        self.assertFalse(window._journal.producers)
        self.record("PC02")

    def test_pc03(self):
        command = M.command(
            {"op": "PRODUCE", "profile": "media-alpha", "args": {"invocation": "P01"}}
        )
        runtime, window, _ = self.runtime([command])

        async def producer(_command, **_kwargs):
            runtime.raw["P01"] = "private raw"
            runtime.producer_receipts["P01"] = {"event": "inert receipt"}
            return {"event": "inert"}

        runtime._action = producer
        self.scope.begin(runtime, command)
        observation = finish(runtime.action(command))
        self.assertNotIn("private raw", json.dumps(observation))
        record = window._journal.producers["P01"]
        self.assertEqual(record.raw, "private raw")
        self.assertNotIn("private raw", repr(record))
        self.record("PC03")

    def test_pc04(self):
        command = M.command(
            {"op": "SEED", "actor": "A1", "profile": "media-alpha", "args": {"invocation": "P01"}}
        )
        runtime, window, calls = self.runtime([command])
        window._journal.producers["P01"] = windows._ProducerRecord(
            "P01", "media-alpha", "raw", b"{}", object()
        )
        window._journal.observation = self.scope.observation(
            window._journal.observation.revision + 1, window._journal.snapshot()
        )

        async def throw(_command, **_kwargs):
            calls.append("seed")
            raise RuntimeError("unknown seed")

        runtime._action = throw
        self.scope.begin(runtime, command)
        with self.assertRaises(worker.RefusalError):
            finish(runtime.action(command))
        self.assertIn("media-alpha", window._journal.seed_claims)
        self.assertEqual(calls, ["seed"])
        self.record("PC04")

    def test_dc01(self):
        runtime, window, calls = self.runtime([graph()])
        self.scope.states["A1"] = ("ACTIVE", "other-user", "iid-A", "inert-private-bearer-A1")
        with self.assertRaises(windows.WindowRefusedError):
            runtime.restore_actor(window.actor("A1"))
        self.assertFalse(calls)
        self.record("DC01")

    def test_dc02(self):
        window, _ = self.window()
        object.__setattr__(window.description, "custody", object())
        with self.assertRaises(windows.WindowRefusedError):
            window.ledger.tick()
        self.assertIsNotNone(window._journal.first_failure)
        self.record("DC02")

    def test_dc03(self):
        with self.assertRaisesRegex(windows.WindowRefusedError, "ROOT_PERSISTENT_READBACK_UNBOUND"):
            self.scope.old[1](None, None, None)
        self.assertNotIn("sqlite", windows.__dict__)
        self.record("DC03")

    def test_lg01(self):
        window, _ = self.window()
        self.assertEqual(window.actor("A1").current().p4, M.MODEL_P4["A1"])
        self.assertFalse(any(b"BIND_ACTOR" in body for body in window._plan))
        with self.assertRaises(windows.WindowRefusedError):
            window.actor("B1")
        self.record("LG01")

    def test_lg02(self):
        command = M.command(
            {
                "op": "LATE_OWN_READ",
                "actor": "A1",
                "profile": "media-alpha",
                "args": {"permit": "1" * 64},
            }
        )
        runtime, window, _ = self.runtime([command])
        self.scope.begin(runtime, command)
        finish(runtime.action(command))
        self.assertEqual(window._journal.late_used, {"1" * 64})
        with self.assertRaises(windows.WindowRefusedError):
            window.before_action(runtime, command)
        self.record("LG02")

    def check_w1_transition(self, mode):
        outer_scope = self.scope
        # Separate exact inert attempt, preserving the original unbound seams.
        outer_scope.__exit__(None, None, None)

        class Scope(M.InertScope):
            trigger = False
            now = 1

            def transition(self, issuance, candidate):
                if self.trigger and candidate.kind == "reserve_handle":
                    self.trigger = False
                    if mode == "caught_refusal":
                        with suppress(windows.WindowRefusedError):
                            self.window_ref.ledger.close_owned(object())
                    else:
                        self.now = 101
                return super().transition(issuance, candidate)

        try:
            with Scope() as scope:
                journal = windows._JournalState((), M.MODEL_CAPS, 100, lambda: scope.now)
                window = scope.window([], journal=journal, enrolled=False)
                scope.window_ref, scope.trigger = window, True
                effects = []
                with (
                    patch.object(
                        worker,
                        "os",
                        SimpleNamespace(open=lambda *_args: effects.append(1) or 900123),
                    ),
                    self.assertRaises(windows.WindowRefusedError),
                ):
                    worker._open_pinned_handle(window.ledger, "inert", 0)
                self.assertEqual(effects, [])
                self.assertEqual(journal.held, 1)
                self.assertEqual(journal.handle_debts[0].state, "RESERVED")
                self.assertIsNotNone(journal.first_failure)
        finally:
            outer_scope.__enter__()

    def test_w1_caught_transition_refusal(self):
        self.check_w1_transition("caught_refusal")

    def test_w1_transition_deadline(self):
        self.check_w1_transition("deadline_elapsed")

    def test_compat01(self):
        with self.assertRaises(worker.RefusalError):
            worker.Dispatcher({"role": "A"}, worker.Ledger(time.monotonic() + 1))
        self.assertEqual(worker.decode_command(windows._command_bytes(graph())), graph())
        self.assertEqual(worker.OPS["LATE_OWN_READ"], {"LATE_GUARDS"})
        self.record("COMPAT01")
