"""S1 source with inert scheduler/mutex/worker models; no runtime qualification."""

import contextvars
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

CAUSALS = []


def _load_subject():
    source = Path(__file__).resolve().parents[2] / "hmp_plugin/fixture_work.py"
    spec = importlib.util.spec_from_file_location("fixture_work_test_subject", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        self.context = contextvars.copy_context()
        self.waiting = None
        loop.tasks.append(self)

    def step(self, completed=None, *, error=None):
        return self.context.run(self._step, completed, error=error)

    def _step(self, completed=None, *, error=None):
        if self.finished:
            return
        if completed is not None and self.waiting is not completed:
            return
        self.waiting = None
        previous, self.loop.current = self.loop.current, self
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
        finally:
            self.loop.current = previous

    def cancelled(self):
        return isinstance(self.error, ModelCancellation)

    def exception(self):
        if self.cancelled():
            raise self.error
        return self.error

    def get_coro(self):
        return self.coroutine

    def cancel(self):
        self.loop.ready.append((lambda _: self.step(error=ModelCancellation()), None))


class ModelLoop:
    def __init__(self, factory="normal"):
        self.factory = factory
        self.current = None
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

    def call_soon_threadsafe(self, call, *args):
        self.ready.append((lambda _: call(*args), None))

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
        copied = contextvars.copy_context()
        self.workers.append((result, copied.run, (function, *args)))
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
        owned = {id(task.coroutine) for task in self.tasks}
        for coroutine in self.transferred:
            if id(coroutine) not in owned:
                coroutine.close()
        for task in self.tasks:
            task.context.run(task.coroutine.close)


class ModelMutex:
    def __init__(self):
        self.held = False

    def __enter__(self):
        assert not self.held
        self.held = True
        return self

    def __exit__(self, *_args):
        self.held = False


class WorkTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_subject()
        self.loops = []

    def tearDown(self):
        for loop in self.loops:
            loop.dispose_models()

    def scenario(self, factory="normal"):
        module = self.module
        loop = ModelLoop(factory)
        self.loops.append(loop)
        module.asyncio = SimpleNamespace(
            get_running_loop=lambda: loop,
            Task=ModelTask,
            current_task=lambda: loop.current,
            to_thread=loop.to_thread,
            shield=loop.shield,
            CancelledError=ModelCancellation,
        )
        module.threading = SimpleNamespace(Lock=ModelMutex, local=SimpleNamespace)
        # Inert namespace substitution only. No real issuer is installed.
        module._require_serving_issuer = lambda lifecycle, context: None
        config, context = object(), object()
        binding = SimpleNamespace(config=config, generation=object())
        alias = SimpleNamespace(binding=binding, first_failure=None)
        adapter = SimpleNamespace(config=config)
        lifecycle = SimpleNamespace(
            alias=alias,
            binding=binding,
            adapter=adapter,
            ctx=context,
            stopping=False,
            first_failure=None,
        )
        owner = module._ServingWork(lifecycle, context)

        async def ingress_caller():
            return None

        loop.current = ModelTask(loop, ingress_caller())
        worker = next(iter(module._WORKER_SITES))
        task = next(iter(module._TASK_SITES))
        return owner, loop, worker, task

    def case(self, name):
        CAUSALS.append(name)

    def test_real_default_refuses_before_mutex_or_context_access(self):
        module = self.module
        module.threading = SimpleNamespace(Lock=lambda: self.fail("mutex acquired"))
        with self.assertRaises(module._WorkRefusedError):
            module._ServingWork(object(), object())
        self.case("default issuer before acquisition")

    def test_worker_result_collected_independently_and_payload_retired(self):
        owner, loop, site, _task = self.scenario()
        calls = []
        record = owner.launch_worker(site, lambda: calls.append("body") or 7)
        assert record.task is not None and calls == []
        loop.run()
        assert calls == [] and record.worker_submitting and not record.worker_exited
        waiter = loop.start_caller(owner.collect(record))
        loop.run()
        loop.finish_worker()
        assert waiter.value == 7 and record.worker_entered and record.worker_exited
        assert record.body_exited and record.collected and record not in owner.local_debt()
        owner.discard_collected_payload(record)
        assert record.payload is record.result is record.worker_result is None
        assert record.task is record.returned_handle is record.coroutine is None
        assert len(owner.local_debt()) == 2  # S2/S3 blockers remain even with no local work.
        self.case("actual body completion and no closure certificate")

    def test_eager_factory_stops_at_gate_until_handle_retained(self):
        owner, loop, site, _task = self.scenario("eager")
        loop.before_return = lambda task: self.assertEqual(loop.workers, [])
        record = owner.launch_worker(site, lambda: 1)
        assert record.task is not None and record.released and not record.worker_entered
        loop.run()
        loop.finish_worker()
        self.case("eager supervisor gated before retained handle")

    def test_factory_throw_and_wrong_handle_preserve_unknown_without_effect(self):
        for mode in (
            "throw_before",
            "throw_after",
            "throw_after_eager",
            "return_none",
            "return_foreign",
        ):
            owner, loop, site, _task = self.scenario(mode)
            with self.assertRaises(self.module._WorkRefusedError) as caught:
                owner.launch_worker(site, lambda: self.fail("worker effect"))
            record = owner._records[0]
            loop.run()
            assert record.unknown and not record.released and not loop.workers
            assert record in owner.local_debt() and owner.first_failure is record.failure
            assert caught.exception.__context__ is None and caught.exception.__cause__ is None
            self.case("factory unknown " + mode)

    def test_stop_and_caught_reentry_during_factory_block_release(self):
        for action in ("stop", "reenter", "generation"):
            owner, loop, site, _task = self.scenario()

            def callback(_returned, owner=owner, action=action, site=site):
                assert not owner._mutex.held
                if action == "stop":
                    owner.request_stop(RuntimeError("PRIVATE"))
                elif action == "generation":
                    owner.binding.generation = object()
                else:
                    with self.assertRaises(self.module._WorkRefusedError):
                        owner.launch_worker(site, lambda: None)

            loop.before_return = callback
            with self.assertRaises(self.module._WorkRefusedError):
                owner.launch_worker(site, lambda: self.fail("effect"))
            loop.run()
            assert not loop.workers and owner.stopping and not owner._records[0].released
            self.case("caught factory boundary " + action)

    def test_terminal_launch_refuses_before_gate_or_factory(self):
        owner, loop, site, _task = self.scenario()
        owner.request_stop(RuntimeError("PRIVATE"))
        with self.assertRaises(self.module._WorkRefusedError):
            owner.launch_worker(site, lambda: None)
        assert loop.factory_calls == 0 and owner._records == []
        self.case("terminal launch has zero factory effects")

    def test_caller_cancel_during_actual_worker_body_does_not_finish_worker(self):
        owner, loop, site, _task = self.scenario()
        waiters = []

        def work():
            assert not owner._mutex.held
            waiters[0].cancel()
            loop.run()
            assert record.worker_entered and not record.worker_exited
            assert not record.body_exited and not record.collected
            assert record in owner.local_debt()
            return "late context"

        record = owner.launch_worker(site, work)
        waiters.append(loop.start_caller(owner.collect(record)))
        loop.run()
        loop.finish_worker()
        assert isinstance(waiters[0].error, ModelCancellation)
        assert record.worker_exited and record.result == "late context"
        second = loop.start_caller(owner.collect(record))
        loop.run()
        assert second.value == "late context" and record.collected
        self.case("caller cancelled after body entry, late actual result retained")

    def test_supervisor_cancel_during_body_keeps_distinct_worker_debt(self):
        owner, loop, site, _task = self.scenario()

        def work():
            record.task.cancel()
            loop.run()
            assert record.body_exited and not record.worker_exited
            assert record.unknown and record in owner.local_debt()
            return "late"

        record = owner.launch_worker(site, work)
        loop.run()
        loop.finish_worker()
        assert record.worker_exited and record.worker_result == "late" and record.unknown
        assert record in owner.local_debt()
        self.case("supervisor cancelled while actual body active, unknown remains")

    def test_duplicate_worker_invocation_cannot_finish_original(self):
        owner, loop, site, _task = self.scenario()

        def work():
            with self.assertRaises(self.module._WorkRefusedError):
                owner._invoke_worker(record)
            assert not record.worker_exited and record.unknown
            return 9

        record = owner.launch_worker(site, work)
        loop.run()
        loop.finish_worker()
        assert record.worker_exited and record.unknown and owner.stopping
        self.case("caught duplicate physical callback cannot settle original")

    def test_ingress_exit_after_stop_preserves_independent_child_worker(self):
        owner, loop, site, _task = self.scenario()
        frame = owner.enter(self.module._WorkSite.HTTP_REQUEST)
        record = owner.launch_worker(site, lambda: 1, parent=frame)
        loop.run()
        owner.request_stop(RuntimeError("stop"))
        owner.leave(frame)
        assert frame not in owner.local_debt() and record in owner.local_debt()
        with self.assertRaises(self.module._WorkRefusedError):
            owner.enter(self.module._WorkSite.NATIVE_SEND)
        loop.finish_worker()
        assert owner.stopping
        self.case("request exit does not release queued child")

    def test_foreign_stale_and_repeated_ingress_membership_refuses(self):
        for mode in ("foreign", "repeat", "context"):
            owner, _loop, _site, _task = self.scenario()
            frame = owner.enter(self.module._WorkSite.NATIVE_SEND)
            if mode == "foreign":
                other, *_ = self.scenario()
                with self.assertRaises(self.module._WorkRefusedError):
                    other.leave(frame)
                assert not frame.body_exited
            elif mode == "repeat":
                owner.leave(frame)
                with self.assertRaises(self.module._WorkRefusedError):
                    owner.leave(frame)
            else:
                owner.lifecycle.ctx = object()
                with self.assertRaises(self.module._WorkRefusedError):
                    owner.enter(self.module._WorkSite.NATIVE_SEND)
            self.case("ingress membership " + mode)

    def test_known_callback_error_and_cancel_keep_original_identity(self):
        for error in (ValueError("PRIVATE"), ModelCancellation()):
            owner, loop, site, _task = self.scenario()

            def work(error=error):
                raise error

            record = owner.launch_worker(site, work)
            waiter = loop.start_caller(owner.collect(record))
            loop.run()
            loop.finish_worker()
            assert record.worker_failure is error and waiter.error is error
            assert record.worker_exited and record.body_exited and not record.unknown
            self.case("original worker error " + type(error).__name__)

    def test_unknown_acquisition_retained_without_generic_success_settler(self):
        owner, _loop, site, _task = self.scenario()
        error = ValueError("PRIVATE")
        debt = owner.retain_unknown_acquisition(site, error)
        assert debt.failure is error and debt in owner.local_debt() and owner.stopping
        assert not hasattr(owner, "mark_drained") and not hasattr(owner, "close_ok")
        self.case("unknown acquisition cannot clear local debt")

    def test_task_payload_runs_only_after_retention_and_cannot_authorize_close(self):
        owner, loop, _site, task_site = self.scenario("eager")
        effects = []

        async def body():
            assert not owner._mutex.held
            effects.append("effect")
            return 4

        record = owner.launch(task_site, body())
        assert effects == [] and record.task is not None
        waiter = loop.start_caller(owner.collect(record))
        loop.run()
        assert effects == ["effect"] and waiter.value == 4
        assert len(owner.local_debt()) == 2
        self.case("task body retention and permanent S2/S3 blockers")

    def test_thread_submission_throw_before_and_after_hidden_enqueue(self):
        for mode in ("before", "after"):
            owner, loop, site, _task = self.scenario()
            error = ValueError("PRIVATE_SUBMIT")
            hidden = []

            async def submit(function, *args, mode=mode, error=error, hidden=hidden):
                if mode == "after":
                    hidden.append((function, args))
                raise error

            self.module.asyncio.to_thread = submit
            record = owner.launch_worker(site, lambda: self.fail("late ordinary effect"))
            waiter = loop.start_caller(owner.collect(record))
            loop.run()
            assert record.unknown and record in owner.local_debt() and owner.stopping
            assert record.failure is error and not record.worker_entered
            assert isinstance(waiter.error, self.module._WorkRefusedError)
            for function, args in hidden:
                with self.assertRaises(self.module._WorkRefusedError):
                    function(*args)
            assert record.unknown and record in owner.local_debt()
            self.case("hidden executor submission " + mode)

    def test_before_gate_and_before_factory_effect_boundaries(self):
        for boundary in ("loop", "gate", "get_coro"):
            owner, loop, site, _task = self.scenario()
            error = RuntimeError("stop")
            if boundary == "loop":

                def get_loop(owner=owner, loop=loop, error=error):
                    owner.request_stop(error)
                    return loop

                self.module.asyncio.get_running_loop = get_loop
            elif boundary == "gate":
                old = loop.create_future

                def make_gate(owner=owner, old=old, error=error):
                    owner.request_stop(error)
                    return old()

                loop.create_future = make_gate
            else:

                def before_return(task, owner=owner, error=error):
                    original = task.get_coro

                    def get_coro():
                        owner.request_stop(error)
                        return original()

                    task.get_coro = get_coro

                loop.before_return = before_return
            with self.assertRaises(self.module._WorkRefusedError):
                owner.launch_worker(site, lambda: self.fail("effect"))
            loop.run()
            assert not loop.workers
            if boundary != "get_coro":
                assert loop.factory_calls == 0
            self.case("ordinary effect fence " + boundary)

    def test_wrong_actual_task_coroutine_and_wrong_ingress_task_refused(self):
        owner, loop, site, _task = self.scenario()
        loop.before_return = lambda task: setattr(task, "get_coro", lambda: object())
        with self.assertRaises(self.module._WorkRefusedError):
            owner.launch_worker(site, lambda: self.fail("effect"))
        loop.run()
        assert not loop.workers
        self.case("returned task must wrap owned coroutine")
        owner, loop, _site, _task = self.scenario()
        self.module.asyncio.current_task = lambda: object()
        with self.assertRaises(self.module._WorkRefusedError):
            owner.enter(self.module._WorkSite.HTTP_REQUEST)
        assert owner._records[0].unknown and owner.stopping
        self.case("async ingress must retain actual Task")

    def test_overlapping_ingress_frames_stop_without_thread_id_authority(self):
        owner, _loop, _site, _task = self.scenario()
        a = owner.enter(self.module._WorkSite.NATIVE_INERT)
        b = owner.enter(self.module._WorkSite.NATIVE_INERT)
        owner.request_stop(RuntimeError("stop"))
        owner.leave(a)
        assert b in owner.local_debt() and a not in owner.local_debt()
        with self.assertRaises(self.module._WorkRefusedError):
            owner.enter(self.module._WorkSite.NATIVE_INERT)
        owner.leave(b)
        assert len(owner.local_debt()) == 2
        self.case("overlapping sync frames independently retained across stop")

    def test_wrong_site_or_foreign_parent_has_zero_factory_effects(self):
        for mode in ("site", "parent"):
            owner, loop, site, _task = self.scenario()
            other, *_ = self.scenario()
            parent = other.enter(self.module._WorkSite.NATIVE_INERT)
            with self.assertRaises(self.module._WorkRefusedError):
                owner.launch_worker(
                    "forged" if mode == "site" else site,
                    lambda: None,
                    parent=parent if mode == "parent" else None,
                )
            assert loop.factory_calls == 0
            self.case("launch refuses " + mode)

    def test_stop_between_check_and_ingress_body_entry(self):
        owner, _loop, _site, _task = self.scenario()
        original = owner._check

        def checked(record, **kwargs):
            original(record, **kwargs)
            owner.request_stop(RuntimeError("stop between check and entry"))

        owner._check = checked
        with self.assertRaises(self.module._WorkRefusedError):
            owner.enter(self.module._WorkSite.HTTP_REQUEST)
        record = owner._records[0]
        assert not record.body_entered and record.unknown and record in owner.local_debt()
        self.case("stop between context check and ingress body admission")

    def test_stop_between_worker_check_and_foreign_effect(self):
        owner, loop, site, _task = self.scenario()
        effects = []
        record = owner.launch_worker(site, lambda: effects.append("effect"))
        loop.run()
        original = owner._check

        def checked(record, **kwargs):
            original(record, **kwargs)
            owner.request_stop(RuntimeError("stop between check and worker call"))

        owner._check = checked
        loop.finish_worker()
        assert effects == [] and record.worker_entered and record.worker_exited
        self.case("stop between worker check and final callback admission")

    def test_stop_between_task_check_and_body_entry(self):
        owner, loop, site, _task = self.scenario()
        record = owner.launch_worker(site, lambda: self.fail("effect"))
        original = owner._check
        checks = []

        def checked(record, **kwargs):
            original(record, **kwargs)
            checks.append(record)
            if len(checks) == 2:
                owner.request_stop(RuntimeError("stop before body entry"))

        owner._check = checked
        loop.run()
        assert not record.body_entered and record.body_exited and not loop.workers
        assert not record.collected and record in owner.local_debt()
        self.case("stop between task check and body admission")

    def test_collect_late_result_after_stop_is_not_publication_permission(self):
        owner, loop, site, _task = self.scenario()
        context = object()

        def work():
            owner.request_stop(RuntimeError("stop during callback"))
            return context

        record = owner.launch_worker(site, work)
        loop.run()
        loop.finish_worker()
        waiter = loop.start_caller(owner.collect(record))
        loop.run()
        assert waiter.value is context and record.collected and owner.stopping
        with self.assertRaises(self.module._WorkRefusedError):
            owner.launch_worker(site, lambda: self.fail("new output effect"))
        assert len(owner.local_debt()) == 2
        self.case("known late context collected for cleanup, serving stays unbound")

    def test_caught_ingress_capture_reentry_has_zero_nested_launch_effects(self):
        for mode in ("launch", "enter"):
            owner, loop, site, _task = self.scenario()

            def current_task(owner=owner, loop=loop, site=site, mode=mode):
                with self.assertRaises(self.module._WorkRefusedError):
                    if mode == "launch":
                        owner.launch_worker(site, lambda: self.fail("nested effect"))
                    else:
                        owner.enter(self.module._WorkSite.NATIVE_INERT)
                return loop.current

            self.module.asyncio.current_task = current_task
            with self.assertRaises(self.module._WorkRefusedError):
                owner.enter(self.module._WorkSite.HTTP_REQUEST)
            assert loop.factory_calls == 0 and len(owner._records) == 1
            assert not owner._records[0].body_entered and owner.stopping
            self.case("caught ingress task capture reentry " + mode)

    def serving(self, factory="normal"):
        owner, loop, site, task_site = self.scenario(factory)
        context = SimpleNamespace(
            bridge=None,
            prompt_store=None,
            direct_send_deps=None,
            read_worker_budget=None,
            store=None,
        )
        owner.context = owner.lifecycle.ctx = context
        context._fixture_work = owner
        context._fixture_adapter = owner.adapter
        owner.adapter._fixture_work = owner
        owner._carriers = (context, owner.adapter)
        owner._component_bind_complete = True  # Inert namespace issuance only.
        return owner, loop, site, task_site

    def model_reservation(self, owner, key, site):
        # Focused task-gate tests model an already completed reserve operation.
        # Actual pre-submission/late-write mechanics have separate causal tests.
        parent = self.module._CURRENT_FRAME.get()
        acquisition = self.module._CmidAcquisition(owner, parent, site, owner.context.store, key, 0)
        acquisition.inserted = True
        owner._cmid_acquisitions.append(acquisition)
        return acquisition

    def test_s2_lost_or_foreign_carrier_poison_is_sticky(self):
        for mode in ("missing", "foreign", "stale"):
            owner, _loop, _site, _ = self.serving()
            with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
                carrier = (
                    SimpleNamespace(_fixture_work=owner) if mode == "foreign" else owner.context
                )
                if mode == "missing":
                    carrier._fixture_work = None
                if mode == "stale":
                    owner.binding.generation = object()
                with self.assertRaises(self.module._WorkRefusedError):
                    self.module._publication(carrier)
                assert owner.stopping
            self.case("S2 carrier " + mode + " poisons before context work")

    def test_s2_worker_late_result_is_not_published(self):
        owner, loop, site, _ = self.serving()
        calls = []

        def body():
            calls.append("actual context use")
            owner.request_stop(RuntimeError("stop during actual body"))
            return "late private result"

        async def request():
            with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
                return await self.module._worker(owner.context, site, body)

        request_task = loop.start_caller(request())
        loop.run()
        loop.finish_worker()
        assert calls == ["actual context use"]
        assert isinstance(request_task.error, self.module._WorkRefusedError)
        assert request_task.value is None
        assert owner._records[1].worker_exited
        self.case("S2 actual late worker result refuses publication")

    def test_s2_default_worker_preserves_callback_args_and_keywords(self):
        _owner, loop, site, _ = self.serving()
        effects = []

        async def ordinary_to_thread(call, *args, **kwargs):
            effects.append((call, args, kwargs))
            return call(*args, **kwargs)

        self.module.asyncio.to_thread = ordinary_to_thread
        carrier = SimpleNamespace()

        def callback(a, *, b):
            return a + b

        task = loop.start_caller(self.module._worker(carrier, site, callback, 2, b=3))
        loop.run()
        assert task.value == 5 and effects == [(callback, (2,), {"b": 3})]
        assert loop.factory_calls == 0
        self.case("S2 ordinary worker preserves callback args keywords and default executor API")

    def test_s2_send_maps_are_populated_before_eager_body(self):
        for site_name in ("CW020", "CW071"):
            owner, loop, _site, _ = self.serving("eager")
            entries, effects = {}, []
            carrier = SimpleNamespace(_fixture_work=owner)
            registry = SimpleNamespace(
                put=lambda key, task, entries=entries: entries.setdefault(key, task)
            )
            if site_name == "CW020":
                carrier.tasks = registry
                owner.context.direct_send_deps = carrier
            else:
                registry = carrier
                registry.put_phone_task = lambda key, task, entries=entries: entries.setdefault(
                    key, task
                )
                owner.context.prompt_store = carrier
            owner._carriers += (carrier,)
            key = ("iid", "user", "profile", "cmid")

            async def body(effects=effects, entries=entries, key=key, loop=loop):
                effects.append(entries[key] is loop.current)
                return 9

            with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
                self.model_reservation(
                    owner,
                    key,
                    self.module._WorkSite.CW017
                    if site_name == "CW020"
                    else self.module._WorkSite.CW068,
                )
                task = self.module._send_task(
                    carrier, getattr(self.module._WorkSite, site_name), body(), registry, key
                )
                assert entries[key] is task and effects == []
                loop.run()
                assert effects == [True] and task.value == 9
            self.case("S2 " + site_name + " exact map before eager body")

    def test_s2_budget_survives_supervisor_cancel_until_physical_exit(self):
        for operator_mode in (False, True):
            owner, loop, _site, _ = self.serving()
            released = []
            budget = SimpleNamespace(
                release=lambda released=released, **kwargs: released.append(kwargs)
            )
            owner.context.read_worker_budget = budget
            operator = (
                SimpleNamespace(
                    ctx=owner.context,
                    _outstanding=1,
                    _stopping=True,
                    _drained=SimpleNamespace(
                        set=lambda released=released: released.append("drain")
                    ),
                )
                if operator_mode
                else None
            )
            loop.call_soon_threadsafe = lambda call, *args, loop=loop: loop.ready.append(
                (lambda _: call(*args), None)
            )
            site = self.module._WorkSite.CW058 if operator_mode else self.module._WorkSite.CW077
            with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
                task = self.module._budget_task(owner.context, site, lambda: 4, operator=operator)
                loop.run()
                task.cancel()
                loop.run()
                assert released == [] and owner._records[-1].unknown
                loop.finish_worker()
                assert released[0] == {"operator": operator_mode}
                assert len(released) == (2 if operator_mode else 1)
                assert owner._records[-1].unknown  # Physical exit cannot erase uncertainty.
            self.case(
                "S2 physical completion alone releases "
                + ("operator" if operator_mode else "readiness")
                + " budget"
            )

    def media_models(self, owner, loop, mode="normal"):
        module = self.module

        class Concurrent(ModelFuture):
            def __init__(self):
                super().__init__(loop)
                self.was_cancelled = False

            def cancelled(self):
                return self.was_cancelled

            def cancel(self):
                self.was_cancelled = True
                self.set_exception(ModelCancellation())

        class Event:
            def __init__(self):
                self.opened = False

            def set(self):
                self.opened = True

            def wait(self):
                assert self.opened, "modeled gate must be released before synchronous continuation"

        module.ConcurrentFuture = Concurrent
        module.threading.Event = Event
        module.threading.ident = 1
        module.threading.get_ident = lambda: module.threading.ident
        pending = []

        def submit(call, *args):
            future = Concurrent()
            pending.append((future, call, args))
            if mode == "inline":
                call(*args)
            if mode == "throw_after":
                raise RuntimeError("private queued submission")
            if mode == "wrong":
                return object()
            return future

        service = SimpleNamespace(_fixture_work=owner, _executor=SimpleNamespace(submit=submit))
        owner._media_service = service
        owner._carriers += (service,)
        return service, pending, Concurrent

    def test_s2_media_future_retained_before_actual_body(self):
        owner, loop, _site, _ = self.serving()
        service, pending, _ = self.media_models(owner, loop)
        done, effects = [], []
        lease = SimpleNamespace(
            _service=service, _done=lambda future, done=done: done.append(future)
        )
        with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
            future = self.module._media_submit(
                owner,
                lease,
                contextvars.copy_context(),
                lambda effects=effects: effects.append("phase") or True,
            )
            assert effects == [] and done == []
            actual, call, args = pending.pop()
            assert actual is future
            self.module.threading.ident = 2
            value = call(*args)
            assert done == [future] and effects == ["phase"]
            future.set_result(value)
            loop.run()
            assert not owner._submissions[0].pending()
        self.case("S2 retained concurrent Future and gate precede actual phase body")

    def test_s2_media_unknown_and_inline_never_refund_or_publish(self):
        for mode in ("throw_after", "wrong", "inline"):
            owner, loop, _site, _ = self.serving()
            service, pending, _ = self.media_models(owner, loop, mode)
            effects, done = [], []
            lease = SimpleNamespace(
                _service=service, _done=lambda future, done=done: done.append(future)
            )
            with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
                with self.assertRaises(self.module._WorkRefusedError):
                    self.module._media_submit(
                        owner,
                        lease,
                        contextvars.copy_context(),
                        lambda effects=effects: effects.append("phase") or True,
                    )
                assert effects == done == []
                assert owner._submissions[0].unknown and owner.stopping
                if mode != "inline":
                    _future, call, args = pending.pop()
                    self.module.threading.ident = 2
                    with self.assertRaises(self.module._WorkRefusedError):
                        call(*args)
                    assert effects == done == []
            self.case("S2 media " + mode + " retains unknown without permit refund")

    def test_s2_media_cancelled_future_does_not_finish_actual_worker(self):
        owner, loop, _site, _ = self.serving()
        service, _pending, _ = self.media_models(owner, loop)
        done = []
        lease = SimpleNamespace(
            _service=service, _done=lambda future, done=done: done.append(future)
        )
        with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
            future = self.module._media_submit(
                owner, lease, contextvars.copy_context(), lambda: True
            )
            future.cancel()
            loop.run()
            assert done == [] and owner._submissions[0].unknown
            assert not owner._submissions[0].exited
        self.case("S2 cancelled media Future never substitutes for physical worker exit")

    def test_s2_p6_tracks_actual_task_and_unknown_submission(self):
        for mode in ("normal", "throw_after", "cancel"):
            owner, loop, _site, _ = self.serving("eager")
            _service, _pending, concurrent = self.media_models(owner, loop)
            bridge = SimpleNamespace(
                _fixture_work=owner, _pending_triggers=set(), _trigger_done=lambda future: None
            )
            owner.context.bridge = bridge
            owner._carriers += (bridge,)
            native = []
            self.module.asyncio.wrap_future = lambda future: future

            def submit(coroutine, _real_loop, loop=loop, mode=mode, concurrent=concurrent):
                loop.create_task(coroutine)
                if mode == "throw_after":
                    raise RuntimeError("private created loop task")
                return concurrent()

            self.module.asyncio.run_coroutine_threadsafe = submit

            async def body(native=native):
                native.append("handoff")
                return True

            payload = body()
            with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
                if mode == "throw_after":
                    with self.assertRaises(self.module._WorkRefusedError):
                        self.module._p6_submit(bridge, payload, loop)
                    assert owner._records[-1].unknown
                else:
                    future = self.module._p6_submit(bridge, payload, loop)
                    assert native == [] and future in bridge._pending_triggers
                    assert owner._records[-1].task is not None
                    if mode == "cancel":
                        future.cancel()
                        loop.run()
                    loop.run()
                    assert native == ([] if mode == "cancel" else ["handoff"])
            payload.close()
            self.case("S2 P6 " + mode + " retained future and actual loop task")

    def test_s2_reserved_cleanup_runs_after_stop_only_for_exact_original_operation(self):
        owner, loop, _site, _ = self.serving()
        effects = []
        prompts = SimpleNamespace(_fixture_work=owner, put_phone_task=lambda key, task: None)
        key = ("iid", "user", "profile", "cmid")

        class Store:
            def finalize_phone_cmid(self, *args, **kwargs):
                assert args == key and kwargs == {
                    "status": "unknown", "result_json": None, "updated_at": 0
                }
                effects.append("reserved finalize")

        store = Store()
        owner.context.store, owner.context.prompt_store = store, prompts
        owner._carriers += (prompts,)

        async def body():
            reserve = self.module._reserve_phone_cleanup(prompts, store, key)
            call = reserve.calls[1]
            owner.request_stop(RuntimeError("stop before finalization"))
            await self.module._cmid_worker(
                reserve, "finalize", call, *key,
                status="unknown", result_json=None, updated_at=0,
            )
            self.module._cmid_sync(
                reserve, "finalize", call, *key,
                status="unknown", result_json=None, updated_at=0,
            )
            return "known cleanup"

        with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
            self.model_reservation(owner, key, self.module._WorkSite.CW068)
            task = self.module._send_task(
                prompts, self.module._WorkSite.CW071, body(), prompts, key
            )
            loop.run()
            assert effects == []
            loop.finish_worker()
            assert effects == ["reserved finalize"] and task.value == "known cleanup"
            assert owner.stopping
        self.case("S2 exact pre-owned cleanup allowed during drain once; no new send")

    def selected(self, filename, names, extra):
        import ast
        import json

        source = Path(__file__).resolve().parents[2] / ("hmp_plugin/" + filename + ".py")
        tree = ast.parse(source.read_bytes(), filename=str(source))
        selected = [ast.ImportFrom(module="__future__", names=[ast.alias("annotations")], level=0)]
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
                node.decorator_list = []
                selected.append(node)
            elif isinstance(node, ast.ClassDef) and node.name in names:
                methods = names[node.name]
                node.bases = []
                node.decorator_list = []
                node.body = [
                    method
                    for method in node.body
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and method.name in methods
                ]
                selected.append(node)
        space = {"__name__": "inert_selected_source", "__file__": str(source), "json": json}
        space.update(vars(self.module))
        space.update(__name__="inert_selected_source", __file__=str(source), **extra)
        from types import FunctionType

        code = compile(
            ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])),
            str(source),
            "exec",
        )
        # Execute only the selected source declarations in the inert namespace.
        FunctionType(code, space)()
        return SimpleNamespace(**space)

    def test_s2_actual_native_ingress_refuses_before_hooks_after_stop(self):
        methods = (
            "note_inert_reply",
            "send",
            "_send_exec_approval_prompt",
            "send_clarify",
            "retire_clarify_card",
        )
        for method in methods:
            owner, loop, _site, _ = self.serving()
            selected = self.selected("adapter", {"HmpAdapter": methods}, {})
            adapter = selected.HmpAdapter()
            adapter.config = owner.binding.config
            adapter._fixture_work = owner
            owner.adapter = owner.lifecycle.adapter = adapter
            owner._carriers = (owner.context, adapter)
            calls = []
            adapter._hooks = lambda calls=calls: calls.append("hooks")
            owner.request_stop(RuntimeError("stop before native hook"))
            args = {
                "note_inert_reply": ("chat",),
                "send": ("chat", "content"),
                "_send_exec_approval_prompt": (object(),),
                "send_clarify": ("chat", "question", [], "clarify", "session"),
                "retire_clarify_card": ("clarify",),
            }[method]
            if method == "note_inert_reply":
                with self.assertRaises(self.module._WorkRefusedError):
                    getattr(adapter, method)(*args)
            else:
                task = loop.start_caller(getattr(adapter, method)(*args))
                loop.run()
                assert isinstance(task.error, self.module._WorkRefusedError)
            assert calls == []
            self.case("S2 actual native " + method + " no post-stop hooks access")

    def test_s2_actual_http_frame_before_handler_and_late_response_refusal(self):
        for stop in ("before", "inside", "none"):
            owner, loop, _site, _ = self.serving()
            owner.lifecycle.request_stop = lambda error: None
            scope = self.module._ServingResources(owner)
            scope.serving_ready = True
            scope.server = object()
            app = object()
            resource = scope.attempt(self.module._ResourceSite.APP, scope.server)
            scope.returned(resource, app)
            request = SimpleNamespace(app=app, transport=object())
            selected = self.selected(
                "server",
                {"_fixture_request_frame": None},
                {"context": lambda request, ctx=owner.context: ctx},
            )
            effects = []

            async def handler(_request, owner=owner, effects=effects, stop=stop):
                effects.append(self.module._CURRENT_FRAME.get().body_entered)
                if stop == "inside":
                    owner.request_stop(RuntimeError("stop during request"))
                return "response"

            if stop == "before":
                owner.request_stop(RuntimeError("queued after stop"))
            task = loop.start_caller(selected._fixture_request_frame(request, handler))
            loop.run()
            assert effects == ([] if stop == "before" else [True])
            assert (task.value == "response") == (stop == "none")
            if stop != "none":
                assert isinstance(task.error, self.module._WorkRefusedError)
            self.case("S2 actual outer request frame " + stop)

    def test_s2_actual_lease_submission_debt_and_late_mailbox(self):
        for mode in ("normal", "throw_after", "late"):
            owner, loop, _site, _ = self.serving()
            service, pending, concurrent = self.media_models(
                owner, loop, "throw_after" if mode == "throw_after" else "normal"
            )
            service._lock = ModelMutex()
            service._closed = False
            service._worker_cap = 4
            service._workers_active = 0
            service._instance_used = 1
            service._device_used = {"device": 1}
            selected = self.selected(
                "media_fetch",
                {
                    "_Lease": (
                        "__init__",
                        "_publish",
                        "_done",
                        "_release_if_ready",
                        "start",
                        "take",
                        "finish",
                    ),
                    "_runner": None,
                },
                {
                    "STARTED": "started",
                    "CLOSED": "closed",
                    "BUSY": "busy",
                    "SUBMISSION_FAILED": "submission_failed",
                    "contextvars": contextvars,
                    "Future": concurrent,
                },
            )
            lease = selected._Lease(service, "device")
            frame = self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST)
            frame.__enter__()
            payload = SimpleNamespace(data=b"inert")
            status, future = lease.start(lambda payload=payload: payload, SimpleNamespace)
            if mode == "throw_after":
                assert status == "submission_failed" and future is None
                assert service._workers_active == lease._pending == 1
                assert owner._submissions[0].unknown
            else:
                if mode == "late":
                    lease.finish()
                    frame.__exit__(None, None, None)
                _future, call, args = pending.pop()
                self.module.threading.ident = 2
                result = call(*args)
                future.set_result(result)
                loop.run()
                assert service._workers_active == lease._pending == 0
                assert lease.take() is (payload if mode == "normal" else None)
                if mode == "late":
                    assert service._instance_used == 0
            if mode != "late":
                frame.__exit__(None, None, None)
            self.case("S2 actual lease " + mode + " original permits/mailbox physical ownership")

    def test_s2_actual_direct_send_closures_keep_scope_and_original_failure(self):
        for mode in ("no_endpoint", "stopped_worker", "cleanup_throws"):
            owner, loop, _site, _ = self.serving()
            calls = []
            failure = RuntimeError("private cleanup failure")

            def delete(*scope, calls=calls, mode=mode, failure=failure):
                calls.append(scope)
                if mode == "cleanup_throws":
                    raise failure

            def resolve(_profile, owner=owner):
                owner.request_stop(RuntimeError("stop in actual read"))
                return object()

            deps = SimpleNamespace(
                _fixture_work=owner,
                tasks=SimpleNamespace(put=lambda *args: None),
                store=SimpleNamespace(delete_cmid_reservation=delete),
                bridge=SimpleNamespace(resolve_bot_chat=resolve),
                now=lambda: 0,
            )
            owner.context.direct_send_deps = deps
            owner.context.store = deps.store
            owner._carriers += (deps,)
            error_type = type("DirectSendError", (Exception,), {})
            selected = self.selected(
                "direct_send",
                {"_execute": None, "_cmid_key": None},
                {
                    "DirectSendError": error_type,
                    "ErrorCode": SimpleNamespace(
                        API_SERVER_UNAVAILABLE="no_api", SESSION_BUSY="busy"
                    ),
                    "_refuse": lambda *args, error_type=error_type, **kwargs: error_type("refused"),
                    "log_bridge_exception": lambda error: None,
                },
            )
            key = ("iid", "user", "profile", "cmid")
            with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
                self.model_reservation(owner, key, self.module._WorkSite.CW017)
                task = self.module._send_task(
                    deps,
                    self.module._WorkSite.CW020,
                    selected._execute(
                        deps,
                        iid=key[0],
                        user_id=key[1],
                        profile=key[2],
                        request=SimpleNamespace(client_message_id=key[3]),
                        endpoint=object() if mode == "stopped_worker" else None,
                        stream=False,
                    ),
                    deps.tasks,
                    key,
                )
                loop.run()
                if mode == "stopped_worker":
                    loop.finish_worker()
                    loop.finish_worker()
                assert calls == [key]
                assert (
                    task.error is failure
                    if mode == "cleanup_throws"
                    else isinstance(task.error, error_type)
                )
            self.case("S2 actual direct-send " + mode + " exact row cleanup once")

    def test_s2_actual_phone_cancel_keeps_reserved_finalization_owned(self):
        owner, loop, _site, _ = self.serving("eager")
        pending, finalizations = {}, []
        prompts = SimpleNamespace(_fixture_work=owner)
        prompts.put_phone_task = lambda key, task: pending.setdefault(key, task)
        prompts.drop_phone_task = lambda key, task: pending.pop(key, None)
        prompts.phone_task = lambda key: pending.get(key)

        class Store:
            def reserve_phone_cmid(self, *args):
                return {"payload_hash": b"digest"}, True

            def finalize_phone_cmid(self, *args, **kwargs):
                finalizations.append((args, kwargs))

        store = Store()
        owner.context.prompt_store, owner.context.store = prompts, store
        owner._carriers += (prompts,)
        native_wait = loop.create_future()

        async def turn(**_kwargs):
            await native_wait

        selected = self.selected(
            "prompts",
            {"handle_phone_send": None},
            {"phone_text_hash": lambda text: b"digest", "_phone_turn": turn},
        )

        async def request():
            with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
                return await selected.handle_phone_send(
                    prompts=prompts,
                    sqlite_store=store,
                    iid="iid",
                    user_id="user",
                    profile="profile",
                    chat_id="chat",
                    cmid="cmid",
                    text="text",
                    now=9,
                    resolver=None,
                    session_key=None,
                    pending_approvals=None,
                    deliver=None,
                )

        caller = loop.start_caller(request())
        loop.run()
        loop.finish_worker()
        key = ("iid", "user", "profile", "cmid")
        task = pending[key]
        assert finalizations == []
        owner.request_stop(RuntimeError("stop during phone turn"))
        task.cancel()
        loop.run()
        assert finalizations == [(key, {"status": "unknown", "result_json": None, "updated_at": 9})]
        assert isinstance(caller.error, ModelCancellation)
        assert owner._records[-1].cleanup is not None and owner._records[-1].worker_exited
        self.case("S2 actual phone cancellation finalizes exact reserved row once while draining")

    def test_s2_media_caught_submit_reentry_poison_blocks_both_effects(self):
        owner, loop, _site, _ = self.serving()
        service, _pending, concurrent = self.media_models(owner, loop)
        lease = SimpleNamespace(_service=service, _done=lambda future: None)
        effects = []

        def submit(*_args):
            with self.assertRaises(self.module._WorkRefusedError):
                self.module._media_submit(
                    owner, lease, contextvars.copy_context(), lambda: effects.append("nested")
                )
            return concurrent()

        service._executor.submit = submit
        with (
            self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST),
            self.assertRaises(self.module._WorkRefusedError),
        ):
            self.module._media_submit(
                owner, lease, contextvars.copy_context(), lambda: effects.append("outer")
            )
        assert effects == [] and owner.stopping and owner._submissions[0].unknown
        assert not owner._submissions[0].released and len(owner._submissions) == 1
        self.case("S2 caught media submission reentry blocks nested and outer phase bodies")

    def test_s2_budget_unknown_factory_keeps_original_reservation(self):
        for factory in ("throw_before", "throw_after_eager", "return_foreign"):
            owner, _loop, _site, _ = self.serving(factory)
            released = []
            owner.context.read_worker_budget = SimpleNamespace(
                release=lambda released=released, **kwargs: released.append(kwargs)
            )
            with (
                self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST),
                self.assertRaises(self.module._WorkRefusedError),
            ):
                self.module._budget_task(owner.context, self.module._WorkSite.CW077, lambda: 1)
            assert released == [] and owner._records[-1].unknown
            self.case("S2 budget " + factory + " retains reservation and unknown launch")

    def test_s2_pre_submission_cmid_owner_distinguishes_late_known_and_unknown(self):
        for site_name in ("CW017", "CW068"):
            for mode in ("no_insert", "insert_late", "cancel_late", "unknown"):
                owner, loop, _site, _ = self.serving()
                effects, tasks = [], []

                class Store:
                    def reserve_cmid(
                        self, *args, owner=owner, loop=loop, tasks=tasks, mode=mode, effects=effects
                    ):
                        assert len(owner._cmid_acquisitions) == 1
                        assert owner._cmid_acquisitions[0].inserted is None
                        if mode == "cancel_late":
                            tasks[0].cancel()
                            loop.run()
                            assert owner._cmid_acquisitions[0].abandoned
                        else:
                            owner.request_stop(RuntimeError("stop during reserve"))
                        if mode != "no_insert":
                            effects.append("inserted")
                        if mode == "unknown":
                            raise RuntimeError("private failure after possible write")
                        return ({"payload_hash": b"digest"}, mode != "no_insert")

                    reserve_phone_cmid = reserve_cmid

                    def delete_cmid_reservation(self, *key, effects=effects):
                        effects.append(("delete", key))

                    def finalize_phone_cmid(self, *key, effects=effects, **kwargs):
                        effects.append(("finalize", key, kwargs))

                store = Store()
                owner.context.store = store
                key = ("iid", "user", "profile", "cmid")
                site = getattr(self.module._WorkSite, site_name)
                method = store.reserve_cmid if site_name == "CW017" else store.reserve_phone_cmid

                async def request(owner=owner, site=site, method=method, key=key):
                    with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
                        return await self.module._reservation_worker(
                            owner.context, site, method, *key, b"digest", 7
                        )

                task = loop.start_caller(request())
                tasks.append(task)
                loop.run()
                assert owner._cmid_acquisitions[0].record.worker_submitting
                loop.finish_worker()
                acquisition = owner._cmid_acquisitions[0]
                if mode in ("insert_late", "cancel_late"):
                    assert acquisition.ticket is not None and len(loop.workers) == 1
                    assert effects == ["inserted"]
                    loop.finish_worker()
                    if site_name == "CW017":
                        assert effects == ["inserted", ("delete", key)]
                    else:
                        assert effects == [
                            "inserted",
                            (
                                "finalize",
                                key,
                                {"status": "unknown", "result_json": None, "updated_at": 7},
                            ),
                        ]
                    assert acquisition.ticket.claim.worker_exited
                    assert acquisition.handoff is None
                    self.module._schedule_cmid_disposition(acquisition)
                    assert loop.workers == []  # No replay or repeated cleanup.
                elif mode == "unknown":
                    assert acquisition.unknown and acquisition.ticket is None
                    assert acquisition.pending() and effects == ["inserted"]
                else:
                    assert acquisition.inserted is False and not acquisition.pending()
                    assert effects == [] and acquisition.ticket is None
                assert task.value is None
                assert all(
                    record.site not in (self.module._WorkSite.CW020, self.module._WorkSite.CW071)
                    for record in owner._records
                )
                self.case(
                    "S2 exact pre-submission "
                    + site_name
                    + " "
                    + mode
                    + " row disposition; zero send-task handoffs"
                )

    def test_s2_incomplete_component_bind_and_replaced_context_resource_refuse(self):
        for field in (None, "store", "identity", "bridge", "direct_send_deps", "prompt_store"):
            owner, _loop, _site, _ = self.serving()
            if field is None:
                owner._component_bind_complete = False
            else:
                original = object()
                setattr(owner.context, field, original)
                owner._context_objects = ((field, original),)
                setattr(owner.context, field, object())
            with self.assertRaises(self.module._WorkRefusedError):
                self.module._owner(owner.context)
            assert owner.stopping
            self.case("S2 source component join refuses " + str(field))

    def phone_cleanup_probe(self, mode):
        owner, loop, _site, _ = self.serving("eager")
        effects = []
        key = ("iid", "user", "profile", "cmid")
        prompts = SimpleNamespace(_fixture_work=owner, put_phone_task=lambda key, task: None)

        class Store:
            def finalize_phone_cmid(self, *args, **kwargs):
                effects.append((args, kwargs))

        class Text(str):
            pass

        store = Store()
        owner.context.store, owner.context.prompt_store = store, prompts
        owner._carriers += (prompts,)

        async def body():
            reserve = self.module._reserve_phone_cleanup(prompts, store, key)
            owner.request_stop(RuntimeError("stop before reserved cleanup"))
            args = list(key)
            if mode.startswith("wrong"):
                args[int(mode[-1])] = "foreign"
            elif mode.startswith("typed"):
                args[int(mode[-1])] = Text(args[int(mode[-1])])
            elif mode == "boolean":
                args[0] = True
            elif mode == "generation":
                owner.binding.generation = object()
            elif mode == "acquisition":
                reserve.acquisition.key = ("iid", "other", "profile", "cmid")
            elif mode == "ticket":
                reserve.acquisition.ticket = object()
            elif mode == "operation":
                reserve.parent.registry_key = ("iid", "user", "profile", "other")
            elif mode == "store":
                owner.context.store = Store()
            kwargs = {"status": "unknown", "result_json": None, "updated_at": 0}
            if mode == "time":
                kwargs["updated_at"] = 9
            if mode == "correct":
                self.module._cmid_sync(reserve, "finalize", reserve.calls[1], *args, **kwargs)
            else:
                with self.assertRaises(self.module._WorkRefusedError):
                    self.module._cmid_sync(
                        reserve, "release" if mode == "kind" else "finalize",
                        (lambda: None) if mode == "callback" else reserve.calls[1],
                        *args, **kwargs,
                    )
                # An invalid attempt cannot be retried with repaired arguments.
                with self.assertRaises(self.module._WorkRefusedError):
                    self.module._cmid_sync(reserve, "finalize", reserve.calls[1], *key, **kwargs)
                assert reserve.acquisition.unknown

        with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
            self.model_reservation(owner, key, self.module._WorkSite.CW068)
            task = self.module._send_task(
                prompts, self.module._WorkSite.CW071, body(), prompts, key
            )
            loop.run()
            assert task.error is None
        assert len(effects) == (1 if mode == "correct" else 0)
        if effects:
            assert effects[0][0] == key
        self.case("S2 V3 phone cleanup " + mode + " exact key before effect")

    def test_s2_phone_cleanup_full_key_types_and_stale_scope(self):
        for mode in (
            "correct", "wrong0", "wrong1", "wrong2", "wrong3",
            "typed0", "typed1", "typed2", "typed3", "boolean",
            "generation", "acquisition", "ticket", "operation", "store", "time",
            "callback", "kind",
        ):
            self.phone_cleanup_probe(mode)

    def direct_cleanup_probe(self, mode):
        owner, loop, _site, _ = self.serving()
        calls = []
        key = ("iid", "user", "profile", "cmid")
        request = SimpleNamespace(client_message_id=key[3])
        deps = SimpleNamespace(
            _fixture_work=owner, tasks=SimpleNamespace(put=lambda *args: None),
            store=SimpleNamespace(delete_cmid_reservation=lambda *args: calls.append(args)),
        )
        owner.context.direct_send_deps, owner.context.store = deps, deps.store
        owner._carriers += (deps,)
        error_type = type("DirectSendError", (Exception,), {})

        def reserve(*args):
            result = self.module._reserve_cmid_cleanup(*args)
            owner.request_stop(RuntimeError("stop before direct cleanup"))
            if mode == "late_request":
                request.client_message_id = "foreign"
            elif mode == "generation":
                owner.binding.generation = object()
            return result

        selected = self.selected(
            "direct_send", {"_execute": None, "_cmid_key": None},
            {"DirectSendError": error_type,
             "ErrorCode": SimpleNamespace(API_SERVER_UNAVAILABLE="no_api"),
             "_refuse": lambda *args, **kwargs: error_type("refused"),
             "_reserve_cmid_cleanup": reserve},
        )
        args = list(key)
        if mode.startswith("wrong"):
            args[int(mode[-1])] = "foreign"
        if mode.startswith("typed"):
            args[int(mode[-1])] = True
        request.client_message_id = args[3]
        with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
            self.model_reservation(owner, key, self.module._WorkSite.CW017)
            task = self.module._send_task(
                deps, self.module._WorkSite.CW020,
                selected._execute(deps, iid=args[0], user_id=args[1], profile=args[2],
                                  request=request, endpoint=None),
                deps.tasks, key,
            )
            loop.run()
            assert task.error is not None
        assert calls == ([key] if mode == "correct" else [])
        self.case("S2 V3 actual direct closure " + mode + " zero foreign row effects")

    def test_s2_direct_cleanup_full_key_types_and_stale_closure(self):
        for mode in (
            "correct", "wrong0", "wrong1", "wrong2", "wrong3",
            "typed0", "typed1", "typed2", "typed3", "late_request", "generation",
        ):
            self.direct_cleanup_probe(mode)

    def delayed_cleanup_probe(self, mode):
        owner, loop, _site, _ = self.serving()
        effects = []
        key = ("iid", "user", "profile", "cmid")
        prompts = SimpleNamespace(_fixture_work=owner, put_phone_task=lambda key, task: None)

        class Store:
            def finalize_phone_cmid(self, *args, **kwargs):
                effects.append((args, kwargs))

        store = Store()
        owner.context.store, owner.context.prompt_store = store, prompts
        owner._carriers += (prompts,)

        async def body():
            reserve = self.module._reserve_phone_cleanup(prompts, store, key)
            owner.request_stop(RuntimeError("drain while cleanup worker is pending"))
            await self.module._cmid_worker(
                reserve, "finalize", reserve.calls[1], *key,
                status="unknown", result_json=None, updated_at=0,
            )

        with self.module._Ingress(owner.context, self.module._WorkSite.HTTP_REQUEST):
            self.model_reservation(owner, key, self.module._WorkSite.CW068)
            task = self.module._send_task(
                prompts, self.module._WorkSite.CW071, body(), prompts, key
            )
            loop.run()
            record = owner._records[-1]
            assert record.cleanup is not None and not record.worker_entered
            if mode == "args":
                record.args = ("iid", "foreign", "profile", "cmid")
            elif mode == "kwargs":
                record.kwargs["status"] = "accepted"
            elif mode == "payload":
                record.payload = lambda *args, **kwargs: effects.append("foreign")
            elif mode == "generation":
                owner.binding.generation = object()
            elif mode == "acquisition":
                record.cleanup.acquisition.key = ("iid", "user", "profile", "other")
            loop.finish_worker()
            assert (task.error is None) == (mode == "correct")
            if mode != "correct":
                assert record.cleanup.acquisition.unknown
        assert len(effects) == (1 if mode == "correct" else 0)
        self.case("S2 V3 delayed cleanup " + mode + " rechecked at actual worker boundary")

    def test_s2_delayed_cleanup_rechecks_arguments_and_custody(self):
        for mode in ("correct", "args", "kwargs", "payload", "generation", "acquisition"):
            self.delayed_cleanup_probe(mode)

    def test_s2_unbound_cmid_sync_preserves_original_arguments(self):
        calls = []
        def callback(*args, **kwargs):
            calls.append((args, kwargs))
        self.module._cmid_sync(None, "finalize", callback, "original", status="unchanged")
        assert calls == [(("original",), {"status": "unchanged"})]
        self.case("S2 V3 owner-None cleanup retains original callback and arguments")
