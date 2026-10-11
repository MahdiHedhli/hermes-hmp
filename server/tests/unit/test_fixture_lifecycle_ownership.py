"""Actual selected own-HMP source with inert scheduling; no native/DB/socket imports.

The scheduler models eager/throwing factories and late thread results. It does
not qualify CPython task factories, root issuance, actual threads or serving.
"""

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import pytest

from .test_adapter import adapter_module as adapter_module

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "tools/fixtures/native_media_listener_factory.py"
CAUSALS = []


class ModelCancellation(BaseException):
    pass


class ModelFuture:
    def __init__(self, loop):
        self.loop = loop
        self.finished = False
        self.value = None
        self.error = None
        self.callbacks = []

    def __await__(self):
        if not self.finished:
            yield self
        if self.error is not None:
            raise self.error
        return self.value

    def done(self):
        return self.finished

    def set_result(self, value):
        assert not self.finished
        self.finished, self.value = True, value
        self.loop.ready.extend((callback, self) for callback in self.callbacks)
        self.callbacks.clear()

    def set_exception(self, error):
        assert not self.finished
        self.error = error
        self.set_result(None)

    def add_done_callback(self, callback):
        if self.finished:
            self.loop.ready.append((callback, self))
        else:
            self.callbacks.append(callback)


class ModelTask(ModelFuture):
    def __init__(self, loop, coroutine):
        super().__init__(loop)
        self.coroutine = coroutine
        self.waiting = None
        loop.tasks.append(self)

    def step(self, completed=None, *, error=None):
        if self.finished:
            return
        if completed is not None and self.waiting is not completed:
            return
        self.waiting = None
        try:
            future = self.coroutine.throw(error) if error else self.coroutine.send(None)
        except StopIteration as stop:
            self.set_result(stop.value)
        except BaseException as failure:
            self.set_exception(failure)
        else:
            assert isinstance(future, ModelFuture)
            self.waiting = future
            future.add_done_callback(self.step)

    def cancel(self):
        self.loop.ready.append((lambda _: self.step(error=ModelCancellation()), None))


class ModelLoop:
    def __init__(self, factory="normal"):
        self.factory = factory
        self.ready = []
        self.tasks = []
        self.workers = []
        self.factory_calls = 0
        self.before_return = None
        self.future_error = None
        self.transferred = []

    def create_future(self):
        if self.future_error is not None:
            raise self.future_error
        return ModelFuture(self)

    def create_task(self, coroutine):
        self.factory_calls += 1
        self.transferred.append(coroutine)
        if self.factory == "throw_before":
            raise RuntimeError("SYNTHETIC_PRIVATE_FACTORY")
        task = ModelTask(self, coroutine)
        if self.factory in ("eager", "throw_after_eager"):
            task.step()
        else:
            self.ready.append((lambda _: task.step(), None))
        if self.before_return is not None:
            self.before_return(task)
        if self.factory in ("throw_after", "throw_after_eager"):
            raise RuntimeError("SYNTHETIC_PRIVATE_FACTORY")
        if self.factory == "return_none":
            return None
        if self.factory == "return_foreign":
            return object()
        return task

    def start_caller(self, coroutine):
        task = ModelTask(self, coroutine)
        self.ready.append((lambda _: task.step(), None))
        return task

    def run(self):
        limit = 200
        while self.ready:
            limit -= 1
            assert limit > 0
            callback, value = self.ready.pop(0)
            callback(value)

    def shield(self, task):
        shield = ModelFuture(self)

        def completed(done):
            if done.error is not None:
                shield.set_exception(done.error)
            else:
                shield.set_result(done.value)

        task.add_done_callback(completed)
        return shield

    async def to_thread(self, function, *args):
        result = ModelFuture(self)
        self.workers.append((result, function, args))
        return await result

    def finish_worker(self):
        result, function, args = self.workers.pop(0)
        try:
            value = function(*args)
        except BaseException as failure:
            result.set_exception(failure)
        else:
            result.set_result(value)
        self.run()

    def dispose_models(self):
        # Test teardown only. Product launch code must never use this to erase
        # a transferred/no-handle launch. Its unknown debt is asserted first.
        for coroutine in self.transferred:
            coroutine.close()
        for task in self.tasks:
            task.coroutine.close()


class ModelAlias:
    """Inert authority substitute only in source-selected ownership tests."""

    def __init__(self):
        self.begin_error = None
        self.post_error = None
        self.close_error = None
        self.close_calls = 0
        self.begin_calls = 0
        self.check_calls = 0
        self.first_failure = None
        self.lifecycle = None
        self.binding = None

    def poison(self, error):
        if self.first_failure is None:
            self.first_failure = error

    def begin_setup(self, lifecycle):
        self.begin_calls += 1
        if self.begin_error is not None:
            raise self.begin_error
        self.lifecycle = lifecycle

    def setup_checkpoint(self, lifecycle):
        self.check_calls += 1
        if self.post_error is not None:
            raise self.post_error

    def retire_unconsumed(self):
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


class LifecycleTests(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def actual_adapter(self, adapter_module, monkeypatch):
        self.module = adapter_module
        self.patch = monkeypatch

    def setUp(self):
        self.loops = []

    def tearDown(self):
        for loop in self.loops:
            loop.dispose_models()

    def scenario(self, factory="normal"):
        loop = ModelLoop(factory)
        self.loops.append(loop)
        alias = ModelAlias()
        calls = {"setup": 0, "prompt": 0, "store": 0}
        faults = {}

        def close_store():
            calls["store"] += 1
            if "store" in faults:
                raise faults["store"]

        ctx = SimpleNamespace(store=SimpleNamespace(close=close_store))

        def close_prompt(_ctx):
            self.assertIs(_ctx, ctx)
            calls["prompt"] += 1
            if "prompt" in faults:
                raise faults["prompt"]

        adapter = SimpleNamespace(
            _close_generation=close_prompt, config=SimpleNamespace(extra={})
        )

        def components(actual):
            self.assertIs(actual, adapter)
            calls["setup"] += 1
            if "setup" in faults:
                raise faults["setup"]
            return ctx

        alias.binding = SimpleNamespace(**{
            name: object() for name in self.module._FIXTURE_CONTEXT_FIELDS
        })
        alias.binding.config = adapter.config
        alias.binding.listener_owner = alias
        self.patch.setattr(self.module, "asyncio", SimpleNamespace(
            get_running_loop=lambda: loop, Task=ModelTask, shield=loop.shield,
            to_thread=loop.to_thread, CancelledError=ModelCancellation,
        ))
        self.patch.setattr(self.module, "open_components", components)
        self.patch.setattr(self.module, "server", SimpleNamespace(
            listener_settings=lambda _extra: object(),
        ))
        lifecycle = self.module._FixtureLifecycle(adapter, alias)
        return loop, lifecycle, alias, ctx, calls, faults

    def record(self, name):
        CAUSALS.append(name)

    def test_default_preflight_no_launch(self):
        loop, owner, alias, _ctx, calls, _faults = self.scenario()
        original = RuntimeError("ISSUER_UNBOUND")
        alias.begin_error = original
        caller = loop.start_caller(owner.connect())
        loop.run()
        self.assertIs(owner.first_failure, original)
        self.assertIsInstance(caller.error, RuntimeError)
        self.assertEqual(loop.factory_calls, 0)
        self.assertEqual(calls["setup"], 0)
        self.assertIsNone(owner.setup)
        self.record("preflight-refusal-zero-task-effects")

    def test_late_context_after_connect_cancellation(self):
        for factory in ("normal", "eager"):
            loop, owner, alias, ctx, calls, _faults = self.scenario(factory)
            caller = loop.start_caller(owner.connect())
            loop.run()
            self.assertEqual(len(loop.workers), 1)
            self.assertEqual(calls["setup"], 0)
            caller.cancel()
            loop.run()
            self.assertIsInstance(caller.error, ModelCancellation)
            self.assertIs(owner.first_failure, caller.error)
            self.assertFalse(owner.setup.task.done())
            cleanup = owner.cleanup.task
            self.assertFalse(cleanup.done())
            loop.finish_worker()
            self.assertIs(owner.ctx, ctx)
            self.assertTrue(cleanup.done())
            self.assertIsNone(cleanup.error)
            self.assertEqual(calls, {"setup": 1, "prompt": 1, "store": 1})
            self.assertEqual(alias.close_calls, 1)
            owner.request_stop(RuntimeError("repeat"))
            self.assertIs(owner.cleanup.task, cleanup)
            self.assertEqual(calls["store"], 1)
            self.record("late-context-cancel:" + factory)

    def test_eager_body_held_until_handle_and_postcheck(self):
        loop, owner, alias, _ctx, calls, _faults = self.scenario("eager")

        def before_return(_task):
            self.assertTrue(owner.setup.started)
            self.assertIsNone(owner.setup.task)
            self.assertFalse(owner.setup.gate.done())
            self.assertEqual(loop.workers, [])
            self.assertEqual(alias.check_calls, 0)

        loop.before_return = before_return
        owner.begin_connect(owner.adapter)
        launch = owner._launch("setup")
        loop.before_return = None
        self.assertIsNotNone(launch.task)
        self.assertEqual(alias.check_calls, 1)
        self.assertEqual(calls["setup"], 0)
        loop.run()
        self.assertEqual(len(loop.workers), 1)
        self.record("eager-held-before-return-and-postcheck")

    def test_factory_no_handle_retains_unknown_gate(self):
        for factory in (
            "throw_before", "throw_after", "throw_after_eager", "return_none", "return_foreign"
        ):
            loop, owner, _alias, _ctx, calls, _faults = self.scenario(factory)
            owner.begin_connect(owner.adapter)
            with self.assertRaises(RuntimeError):
                owner._launch("setup")
            launch = owner.setup
            loop.run()
            self.assertTrue(launch.unknown)
            self.assertIsNone(launch.task)
            self.assertFalse(launch.gate.done())
            self.assertFalse(launch.released)
            self.assertIsNotNone(launch.coroutine.cr_frame)
            self.assertEqual(loop.workers, [])
            self.assertEqual(calls["setup"], 0)
            previous = loop.factory_calls
            with self.assertRaises(RuntimeError):
                owner._launch("setup")
            self.assertEqual(loop.factory_calls, previous)
            self.record("unknown-launch:" + factory)

    def test_postcheck_failure_retains_task_then_cancels_before_worker(self):
        loop, owner, alias, _ctx, calls, _faults = self.scenario("eager")
        alias.post_error = RuntimeError("GENERATION_CHANGED")
        owner.begin_connect(owner.adapter)
        with self.assertRaises(RuntimeError):
            owner._launch("setup")
        self.assertIsNotNone(owner.setup.task)
        self.assertFalse(owner.setup.released)
        owner.request_stop(alias.post_error)
        loop.run()
        self.assertEqual(calls["setup"], 0)
        self.assertEqual(loop.workers, [])
        self.assertTrue(owner.setup.collected)
        self.record("postcheck-failure-no-worker")

    def test_cleanup_waiter_cancel_does_not_cancel_cleanup(self):
        loop, owner, _alias, _ctx, calls, _faults = self.scenario()
        caller = loop.start_caller(owner.connect())
        loop.run()
        caller.cancel()
        loop.run()
        for _ in range(2):
            waiter = loop.start_caller(owner.wait_stopped())
            loop.run()
            waiter.cancel()
            loop.run()
            self.assertIsInstance(waiter.error, ModelCancellation)
            self.assertFalse(owner.cleanup.task.done())
        loop.finish_worker()
        self.assertEqual(calls["store"], 1)
        self.record("repeated-cleanup-waiter-cancel-retained")

    def test_late_setup_and_cleanup_fault_debt(self):
        for fault in ("setup", "prompt", "store", "alias"):
            loop, owner, alias, ctx, calls, faults = self.scenario()
            original = RuntimeError("SYNTHETIC_PRIVATE_FAILURE")
            if fault == "alias":
                alias.close_error = original
            else:
                faults[fault] = original
            caller = loop.start_caller(owner.connect())
            loop.run()
            caller.cancel()
            loop.run()
            loop.finish_worker()
            self.assertIn(original, owner.cleanup_failures)
            self.assertIsNotNone(owner.cleanup.task.error)
            if fault == "setup":
                self.assertIsNone(owner.ctx)
                self.assertTrue(owner.unknown_context)
                self.assertEqual(calls["store"], 0)
            else:
                self.assertIs(owner.ctx, ctx)
                self.assertEqual(calls["store"], 1)
            before = dict(calls)
            owner.request_stop(RuntimeError("repeat"))
            loop.run()
            self.assertEqual(calls, before)
            self.record("retained-failure:" + fault)

    def test_successful_setup_still_cannot_serve(self):
        loop, owner, _alias, ctx, calls, _faults = self.scenario()
        caller = loop.start_caller(owner.connect())
        loop.run()
        loop.finish_worker()
        self.assertIsInstance(caller.error, RuntimeError)
        self.assertEqual(str(caller.error), "FIXTURE_LIFECYCLE_UNAVAILABLE")
        self.assertEqual(str(owner.first_failure), "FIXTURE_SERVING_WORK_UNBOUND")
        self.assertIs(owner.ctx, ctx)
        self.assertEqual(calls["store"], 1)
        self.record("setup-success-serving-stays-closed")

    def test_reentry_during_launch_poison_prevents_worker(self):
        loop, owner, alias, _ctx, calls, _faults = self.scenario("eager")

        def reenter(_task):
            with self.assertRaises(RuntimeError):
                owner.begin_connect(owner.adapter)

        loop.before_return = reenter
        owner.begin_connect(owner.adapter)
        with self.assertRaises(RuntimeError):
            owner._launch("setup")
        loop.before_return = None
        owner.request_stop(RuntimeError("drain"))
        loop.run()
        self.assertEqual(loop.workers, [])
        self.assertEqual(calls["setup"], 0)
        self.assertIs(alias.first_failure, owner.first_failure)
        self.record("caught-eager-reentry-poisons-before-effect")

    def test_caught_preflight_reentry_stops_before_settings_or_setup(self):
        for claimed in (False, True):
            loop, owner, alias, _ctx, calls, _faults = self.scenario("eager")
            settings = []
            self.module.server.listener_settings = lambda _extra, events=settings: events.append(1)

            def preflight(lifecycle, retain=claimed, owned_alias=alias):
                if retain:
                    owned_alias.lifecycle = lifecycle
                with self.assertRaises(RuntimeError):
                    lifecycle.begin_connect(lifecycle.adapter)

            alias.begin_setup = preflight
            caller = loop.start_caller(owner.connect())
            loop.run()
            self.assertIsNotNone(caller.error)
            self.assertEqual(settings, [])
            self.assertIsNone(owner.setup)
            self.assertEqual(loop.workers, [])
            self.assertEqual(calls["setup"], 0)
            self.assertEqual(loop.factory_calls, 1 if claimed else 0)
            self.assertEqual(alias.close_calls, 1 if claimed else 0)
            self.record("caught-preflight-reentry:" + ("owned-cleanup" if claimed else "no-claim"))

    def test_effect_boundaries_check_caught_stop_operation_and_generation(self):
        for stage in ("preflight", "settings", "loop", "gate", "factory", "checkpoint"):
            for fault in ("reentry", "cancel", "operation", "source", "worker"):
                self.check_effect_boundary(stage, fault)

    def check_effect_boundary(self, stage, fault):
        loop, owner, alias, _ctx, calls, _faults = self.scenario("eager")
        observed = []
        settings = []
        gates = []

        def mutate(kind=fault):
            if observed:
                return
            observed.append(kind)
            if kind == "reentry":
                with self.assertRaises(RuntimeError):
                    owner.begin_connect(owner.adapter)
            elif kind == "cancel":
                owner.request_stop(ModelCancellation())
            elif kind == "operation":
                owner.operation = owner.connect_token = object()
            else:
                setattr(alias.binding, kind + "_generation", object())

        def settings_call(_extra, current=stage):
            settings.append(1)
            if current == "settings":
                mutate()
            return object()

        self.module.server.listener_settings = settings_call
        if stage == "preflight":
            original = alias.begin_setup

            def begin(lifecycle, actual=original):
                actual(lifecycle)
                mutate()

            alias.begin_setup = begin
        elif stage == "loop":
            def get_loop():
                mutate()
                return loop

            self.module.asyncio.get_running_loop = get_loop
        elif stage == "gate":
            original = loop.create_future

            def gate(actual=original):
                gates.append(1)
                result = actual()
                mutate()
                return result

            loop.create_future = gate
        elif stage == "factory":
            loop.before_return = lambda _task: mutate()
        elif stage == "checkpoint":
            original = alias.setup_checkpoint

            def checkpoint(lifecycle, actual=original):
                actual(lifecycle)
                mutate()

            alias.setup_checkpoint = checkpoint
        caller = loop.start_caller(owner.connect())
        loop.run()
        self.assertIsNotNone(caller.error)
        self.assertTrue(observed)
        self.assertTrue(owner.stopping)
        self.assertIsNotNone(owner.first_failure)
        self.assertEqual(calls["setup"], 0)
        self.assertEqual(loop.workers, [])
        self.assertEqual(len(settings), 0 if stage == "preflight" else 1)
        if stage in ("preflight", "settings"):
            self.assertIsNone(owner.setup)
        elif stage in ("loop", "gate"):
            self.assertIsNone(owner.setup.task)
            self.assertIsNone(owner.setup.coroutine)
        else:
            self.assertIsNotNone(owner.setup.task)
            self.assertFalse(owner.setup.released)
        self.record("ordinary-effect-fence:" + stage + ":" + fault)

    def test_cleanup_cannot_launch_without_reserved_owned_debt(self):
        loop, owner, _alias, _ctx, _calls, _faults = self.scenario()
        with self.assertRaisesRegex(RuntimeError, "FIXTURE_CLEANUP_NOT_OWNED"):
            owner._launch("cleanup")
        self.assertEqual(loop.factory_calls, 0)
        self.assertIsNone(owner.cleanup)
        self.record("cleanup-requires-owned-reservation")
        owner.begin_connect(owner.adapter)
        original = RuntimeError("already terminal")
        owner._fail(original)
        with self.assertRaises(RuntimeError):
            owner._launch("setup")
        self.assertIs(owner.first_failure, original)
        self.assertIsNone(owner.setup)
        self.assertEqual(loop.factory_calls, 0)
        self.assertEqual(loop.workers, [])
        self.record("terminal-direct-setup-zero-gate-and-factory")

    def test_gate_acquisition_failure_is_recorded_before_launch(self):
        loop, owner, _alias, _ctx, calls, _faults = self.scenario()
        original = RuntimeError("future creation")
        loop.future_error = original
        owner.begin_connect(owner.adapter)
        with self.assertRaises(RuntimeError):
            owner._launch("setup")
        self.assertIs(owner.setup.failure, original)
        self.assertIsNone(owner.setup.coroutine)
        self.assertEqual(loop.factory_calls, 0)
        self.assertEqual(calls["setup"], 0)
        self.record("gate-creation-failure-no-task-factory")

    def test_both_close_errors_preserve_both_actual_failures(self):
        loop, owner, _alias, ctx, calls, faults = self.scenario()
        faults.update(prompt=ValueError("prompt close"), store=RuntimeError("store close"))
        caller = loop.start_caller(owner.connect())
        loop.run()
        caller.cancel()
        loop.run()
        loop.finish_worker()
        self.assertIs(owner.ctx, ctx)
        self.assertEqual(owner.cleanup_failures, [faults["prompt"], faults["store"]])
        self.assertEqual(calls["prompt"], 1)
        self.assertEqual(calls["store"], 1)
        self.assertTrue(owner.unknown_context)
        self.record("both-close-errors-retained-once")

    def test_task_cancellation_after_worker_submission_is_unknown(self):
        loop, owner, _alias, _ctx, calls, _faults = self.scenario()
        caller = loop.start_caller(owner.connect())
        loop.run()
        owner.setup.task.cancel()
        loop.run()
        self.assertIsInstance(caller.error, ModelCancellation)
        self.assertTrue(owner.unknown_context)
        self.assertEqual(calls["store"], 0)
        self.assertEqual(len(loop.workers), 1)
        self.record("external-task-cancel-retains-worker-debt")


class AliasTests(unittest.TestCase):
    def setUp(self):
        self.previous = sys.modules.get("native_media_listener_factory")
        spec = importlib.util.spec_from_file_location("native_media_listener_factory", HELPER)
        self.helper = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.helper
        spec.loader.exec_module(self.helper)

    def tearDown(self):
        if self.previous is None:
            sys.modules.pop("native_media_listener_factory", None)
        else:
            sys.modules["native_media_listener_factory"] = self.previous

    def test_real_issuer_has_no_constructor_or_callback_escape(self):
        h = self.helper
        with self.assertRaisesRegex(h.ScopeRefusedError, "LISTENER_ROOT_ISSUER_UNBOUND"):
            h._ListenerAliasIssuance()
        entry = object.__new__(h._ListenerAliasIssuance)
        with self.assertRaisesRegex(h.ScopeRefusedError, "LISTENER_ROOT_ISSUER_UNBOUND"):
            h.ListenerAliasOwner(entry)
        for wrong in (None, True, {}, object()):
            with self.assertRaisesRegex(h.ScopeRefusedError, "ALIAS_ISSUANCE_TYPE"):
                h.ListenerAliasOwner(wrong)
        CAUSALS.append("actual-unbound-issuer-refuses-all-issuance")

    def test_model_alias_close_exactly_once_unknown_never_retried(self):
        h = self.helper
        # Explicit inert source test substitution. This is not real issuance,
        # which the previous test proves closed and no product input can select.
        for failure in (None, RuntimeError("close unknown")):
            entry = object.__new__(h._ListenerAliasIssuance)
            entry.binding = object()
            calls = []

            def close(error=failure, events=calls):
                events.append("close")
                if error is not None:
                    raise error

            entry.listener = SimpleNamespace(close=close)
            h._require_root_listener_issuance = (
                lambda actual, expected=entry: self.assertIs(actual, expected)
            )
            owner = h.ListenerAliasOwner(entry)
            if failure is None:
                owner.retire_unconsumed()
                owner.retire_unconsumed()
                self.assertEqual(owner.state, "CLOSED")
            else:
                with self.assertRaises(RuntimeError):
                    owner.retire_unconsumed()
                with self.assertRaises(h.ScopeRefusedError):
                    owner.retire_unconsumed()
                self.assertIs(owner.close_failure, failure)
                self.assertIs(owner.first_failure, failure)
            self.assertEqual(calls, ["close"])
            CAUSALS.append("alias-close-once:" + ("normal" if failure is None else "unknown"))

    def test_alias_claim_uses_actual_owned_factory_hook(self):
        h = self.helper
        path = ROOT / "tools/fixtures/tests/test_native_media_listener_factory.py"
        spec = importlib.util.spec_from_file_location("pure_fixture_models", path)
        models = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models)
        scenario = models.Scenario()
        alias = object.__new__(h.ListenerAliasOwner)
        object.__setattr__(scenario.binding, "listener_owner", alias)
        scenario.authority.listener_owner = alias
        entry = object.__new__(h._ListenerAliasIssuance)
        entry.binding = scenario.binding
        entry.listener = SimpleNamespace(close=lambda: None)
        h._require_root_listener_issuance = lambda actual: self.assertIs(actual, entry)
        alias.__init__(entry)
        scenario.install()
        adapter = scenario.delegate.factory(scenario.config)
        self.assertIs(alias.adapter, adapter)
        self.assertIs(alias.slot, scenario.slot)
        self.assertEqual(alias.state, "ADAPTER_BOUND")
        original = RuntimeError("late cancellation")
        alias.poison(original)
        self.assertIs(scenario.owner.first_failure, original)
        self.assertEqual(scenario.owner.state, "POISONED")
        with self.assertRaises(h.ScopeRefusedError):
            alias.claim_adapter(scenario.slot, adapter)
        self.assertIs(alias.first_failure, original)
        CAUSALS.append("actual-hook-alias-claim-and-whole-owner-poison")

    def test_serving_and_handoff_stay_closed(self):
        h = self.helper
        owner = object.__new__(h.ListenerAliasOwner)
        with self.assertRaisesRegex(h.ScopeRefusedError, "FIXTURE_SERVING_WORK_UNBOUND"):
            owner.handoff(object())
        owner.server = object()
        owner.state = "HANDOFF_PENDING"
        with self.assertRaisesRegex(h.ScopeRefusedError, "FIXTURE_SERVING_WORK_UNBOUND"):
            owner.observe_handoff(owner.server)
        CAUSALS.append("real-serving-handoff-unbound")
