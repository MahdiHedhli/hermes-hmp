"""S1 source with inert scheduler/mutex/worker models; no runtime qualification."""

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
        self.waiting = None
        loop.tasks.append(self)

    def step(self, completed=None, *, error=None):
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
            get_running_loop=lambda: loop, Task=ModelTask, current_task=lambda: loop.current,
            to_thread=loop.to_thread, shield=loop.shield, CancelledError=ModelCancellation,
        )
        module.threading = SimpleNamespace(Lock=ModelMutex, local=SimpleNamespace)
        # Inert namespace substitution only. No real issuer is installed.
        module._require_serving_issuer = lambda lifecycle, context: None
        config, context = object(), object()
        binding = SimpleNamespace(config=config, generation=object())
        alias = SimpleNamespace(binding=binding, first_failure=None)
        adapter = SimpleNamespace(config=config)
        lifecycle = SimpleNamespace(alias=alias, binding=binding, adapter=adapter,
                                    ctx=context, stopping=False, first_failure=None)
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
        for mode in ("throw_before", "throw_after", "throw_after_eager",
                     "return_none", "return_foreign"):
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
                    lambda: None, parent=parent if mode == "parent" else None,
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
