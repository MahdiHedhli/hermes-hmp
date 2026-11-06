"""Writer ownership/scheduling models; no Hermes, SQLite, file or network operations."""
import importlib.util
import threading
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[3] / "tools/compat/local_media_native_writer_sample.py"


def load():
    spec = importlib.util.spec_from_file_location("_owned_writer_guard_tests", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def model(module, *, job_error=False, acquire_error=False, release_error=False, none_handle=False):
    owners, calls, handle = [], [], object()

    def acquire():
        calls.append("acquire")
        if acquire_error:
            raise ValueError("synthetic acquisition failure")
        return None if none_handle else handle

    def release(value):
        assert value is handle
        calls.append("release")
        if release_error:
            raise ValueError("synthetic release failure")
        return True

    def job(value):
        assert value is handle
        calls.append("job")
        if job_error:
            raise ValueError("synthetic job failure")

    writer = module.OwnedWriter(owners, acquire, release, job)
    return writer, owners, calls


def test_import_does_not_start_an_actor():
    before = set(threading.enumerate())
    assert callable(load().OwnedWriter)
    assert set(threading.enumerate()) == before


def test_native_access_waits_for_one_explicit_fire_and_release_join_are_separate():
    m = load()
    writer, owners, calls = model(m)
    assert owners == [writer] and not writer.start_attempted
    writer.start()
    try:
        assert writer.ready.is_set() and calls == [] and not writer.safe_to_close()
        writer.fire()
        assert calls == ["acquire", "job", "release"]
        assert writer.committed and writer.release_known and not writer.safe_to_close()
        with pytest.raises(RuntimeError):
            writer.fire()
    finally:
        assert writer.settle()
    assert writer.joined and not writer.thread.is_alive() and writer.handle is None
    assert writer.settle() and calls == ["acquire", "job", "release"]
    with pytest.raises(RuntimeError):
        writer.start()


def test_abort_before_fire_skips_borrow_and_job_then_joins_the_same_actor():
    writer, owners, calls = model(load())
    writer.start()
    thread = writer.thread
    assert writer.settle() and owners[0].thread is thread and not thread.is_alive()
    assert calls == [] and not writer.acquire_attempted and not writer.committed
    with pytest.raises(RuntimeError):
        writer.fire()


def test_sealing_before_start_prevents_late_admission_without_thread_effects():
    writer, _, calls = model(load())
    assert writer.settle() and writer.safe_to_close() and not writer.start_attempted
    with pytest.raises(RuntimeError):
        writer.start()
    assert calls == []


def test_start_exception_with_no_observed_actor_does_not_certify_nonexistence(monkeypatch):
    writer, owners, calls = model(load())

    def fail():
        raise OSError("synthetic pre-start refusal")

    monkeypatch.setattr(writer.thread, "start", fail)
    with pytest.raises(OSError):
        writer.start()
    assert writer.start_attempted and not writer.started and calls == []
    assert not writer.settle() and not writer.safe_to_close()
    assert owners == [writer]  # Uncertain attempted start stays retained; no replacement.


def test_start_exception_after_os_actor_creation_still_joins_actual_retained_thread(monkeypatch):
    writer, owners, calls = model(load())
    start = writer.thread.start

    def start_then_fail():
        start()
        raise OSError("synthetic post-start refusal")

    monkeypatch.setattr(writer.thread, "start", start_then_fail)
    with pytest.raises(OSError):
        writer.start()
    assert writer.settle() and writer.joined and not owners[0].thread.is_alive()
    assert calls == [] and isinstance(writer.error, OSError)


@pytest.mark.parametrize("failure", ["job", "acquire", "none_handle", "release"])
def test_failure_settles_actual_actor_without_replaying_an_ambiguous_release(failure):
    writer, _, calls = model(load(), job_error=failure == "job",
        acquire_error=failure == "acquire", none_handle=failure == "none_handle",
        release_error=failure == "release")
    writer.start()
    try:
        with pytest.raises(RuntimeError):
            writer.fire()
    finally:
        safe = writer.settle()
    assert writer.joined and not writer.thread.is_alive()
    assert safe is (failure == "job")
    assert writer.safe_to_close() is safe
    previous = list(calls)
    assert writer.settle() is safe and calls == previous
    assert calls.count("acquire") == 1 and calls.count("release") <= 1


def test_running_writer_cannot_release_or_be_closed_just_because_abort_was_requested():
    m, entered, finish, fire_done = load(), threading.Event(), threading.Event(), threading.Event()
    calls, owners, handle = [], [], object()

    def job(value):
        assert value is handle
        entered.set()
        finish.wait()

    def release(_):
        calls.append("release")
        return True

    writer = m.OwnedWriter(owners, lambda: handle, release, job)
    writer.start()

    def fire():
        writer.fire()
        fire_done.set()

    controller = threading.Thread(target=fire)
    controller.start()
    try:
        assert entered.wait(2)  # Test watchdog, never a native fixture acceptance deadline.
        writer.abort_event.set()
        assert not writer.safe_to_close() and calls == [] and not fire_done.is_set()
    finally:
        finish.set()
        controller.join(2)
        assert not controller.is_alive()
        assert writer.settle()
    assert fire_done.is_set() and calls == ["release"]


def db_model(module):
    class DB:
        pass

    for name in module.READS:
        setattr(DB, name, lambda self, *args, _name=name, **kwargs: (_name, args, kwargs))
    return DB()


def test_hooks_keep_native_result_and_exact_instance_attributes_and_log_no_arguments():
    m = load()
    db = db_model(m)
    def custom(*args):
        return ("custom", args)

    db.get_session = custom
    original = dict(vars(db))
    events = []
    hooks = m.ReadHooks(db, [], events.append)
    hooks.install()
    assert db.get_session("PRIVATE_SYNTHETIC_SENTINEL") == (
        "custom", ("PRIVATE_SYNTHETIC_SENTINEL",))
    assert events == [("before", "get_session", 1), ("after", "get_session", 1)]
    assert "PRIVATE_SYNTHETIC_SENTINEL" not in repr(hooks.events)
    hooks.restore()
    assert vars(db) == original and db.get_session is custom
    with pytest.raises(RuntimeError):
        hooks.restore()


def test_writer_verification_reads_do_not_recursively_fire_reader_hooks():
    m = load()
    db, owners, events = db_model(m), [], []
    writer = m.OwnedWriter(owners, lambda: db, lambda _: True,
                           lambda handle: handle.get_messages("synthetic"))

    def hook(event):
        events.append(event)
        if event == ("after", "get_messages", 1):
            writer.fire()

    hooks = m.ReadHooks(db, owners, hook)
    writer.start()
    hooks.install()
    try:
        db.get_messages("synthetic")
    finally:
        assert writer.settle()
        hooks.restore()
    assert events == [("before", "get_messages", 1), ("after", "get_messages", 1)]
    assert writer.committed and vars(db) == {}


def test_hooks_cannot_restore_under_an_unsettled_or_uncertain_writer():
    m = load()
    writer, owners, _ = model(m)
    db = db_model(m)
    hooks = m.ReadHooks(db, owners, lambda _: None)
    hooks.install()
    with pytest.raises(RuntimeError):
        hooks.restore()
    assert writer.settle()
    hooks.restore()
    assert vars(db) == {}


@pytest.mark.parametrize("after_assignment", [False, True])
def test_partial_hook_install_restores_recorded_debt_exactly(after_assignment):
    m = load()
    base = db_model(m)

    class Failing(type(base)):
        armed = True

        def __setattr__(self, name, value):
            if name == "get_messages" and self.armed:
                object.__setattr__(self, "armed", False)
                if after_assignment:
                    object.__setattr__(self, name, value)
                raise ValueError("synthetic setter refusal")
            object.__setattr__(self, name, value)

    db = Failing()
    hooks = m.ReadHooks(db, [], lambda _: None)
    with pytest.raises(ValueError):
        hooks.install()
    hooks.restore()
    assert all(name not in vars(db) for name in m.READS)
    assert db.get_messages("synthetic")[0] == "get_messages"


def test_read_event_cap_refuses_instead_of_retaining_unbounded_metadata(monkeypatch):
    m = load()
    db = db_model(m)
    monkeypatch.setattr(m, "MAX_READ_EVENTS", 2)
    hooks = m.ReadHooks(db, [], lambda _: None)
    hooks.install()
    try:
        db.get_session("synthetic")
        with pytest.raises(RuntimeError):
            db.get_session("synthetic")
        assert len(hooks.events) == 2
    finally:
        hooks.restore()


@pytest.mark.parametrize("witness", [False, None, 1, "ok"])
def test_ambiguous_release_return_retains_handle_and_blocks_hook_restoration(witness):
    m = load()
    db, owners, calls = db_model(m), [], []

    def release(value):
        assert value is db
        calls.append("release")
        return witness

    writer = m.OwnedWriter(owners, lambda: db, release, lambda _: None)
    hooks = m.ReadHooks(db, owners, lambda _: None)
    hooks.install()
    writer.start()
    try:
        with pytest.raises(RuntimeError):
            writer.fire()
    finally:
        assert not writer.settle()
    assert writer.joined and not writer.thread.is_alive()
    assert writer.committed and writer.release_attempted and not writer.release_known
    assert writer.handle is db and not writer.safe_to_close()
    with pytest.raises(RuntimeError):
        hooks.restore()
    assert not hooks.restored
    assert not writer.settle() and calls == ["release"]
