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


@pytest.mark.parametrize("case", range(8))
@pytest.mark.parametrize("count", [1, 16, 128])
@pytest.mark.parametrize("scenario_request", ["control:ids0", "append:page", "deactivate:ids1",
    "eligibility:page", "tip_move:ids0", "aba:last", "residual:last"])
def test_general_writer_requests_keep_full_shape_selector_matrix(case, count, scenario_request):
    load().validate_request(case, count, scenario_request)


@pytest.mark.parametrize("case", [0, 3])
@pytest.mark.parametrize("scenario_request", ["ambiguous:page", "kind_swap:ids1",
                                     "title_guard:ids0", "archive:page"])
def test_native_bot_only_cases_do_not_invent_a_phone_guard_bypass(case, scenario_request):
    module = load()
    module.validate_request(case, 128, scenario_request)
    with pytest.raises(RuntimeError):
        module.validate_request(case + 4, 128, scenario_request)


@pytest.mark.parametrize(("case", "selector", "scenario_request"), [(True, 1, "control:page"),
    (-1, 1, "control:page"), (8, 1, "control:page"), (0, True, "control:page"),
    (0, 2, "control:page"), (0, 1, False), (0, 1, "residual:page"),
    (0, 1, "append:last"), (0, 1, "control:foreign"), (0, 1, "x'; execute()")])
def test_undeclared_writer_mode_refuses_before_filesystem(
    tmp_path, case, selector, scenario_request
):
    from .test_local_media_native_serving_driver import driver

    with pytest.raises(RuntimeError):
        driver.run_fixture(tmp_path, tmp_path, "a" * 40, sample_binding_seed=True,
            binding_cost_case=case, binding_cost_selector=selector, binding_writer=scenario_request)
    assert not tuple(tmp_path.iterdir())


def test_writer_request_cannot_combine_with_mint_rss_or_implicit_seed(tmp_path):
    from .test_local_media_native_serving_driver import driver

    for extra in ({"binding_mint": True}, {"binding_rss": True}, {"sample_binding_seed": False}):
        options = {"sample_binding_seed": True, "binding_cost_case": 0,
                   "binding_cost_selector": 1, "binding_writer": "control:page", **extra}
        with pytest.raises(RuntimeError):
            driver.run_fixture(tmp_path, tmp_path, "a" * 40, **options)
        assert not tuple(tmp_path.iterdir())


def test_second_deactivated_row_result_is_an_independent_surviving_subset():
    first, second = load().expected_outcomes("deactivate", "phone", (8,))
    assert first == ("rows_changed", None, ())
    assert second == ("ok", "phone", ())
    selected = tuple(range(128, 0, -1))
    assert load().expected_outcomes("deactivate", "bot_chat", selected)[1] == (
        "ok", "bot_chat", selected[1:])


def test_residual_and_aba_oracles_preserve_acceptances_as_limitations():
    module = load()
    selected = (2,)
    assert module.expected_outcomes("residual", "bot_chat", selected) == (
        ("ok", "bot_chat", selected), ("not_eligible", None, ()))
    assert module.expected_outcomes("aba", "phone", selected) == (
        ("ok", "phone", selected), ("ok", "phone", selected))
    assert module.expected_outcomes("kind_swap", "bot_chat", selected)[1] == (
        "ok", "phone", selected)


def test_writer_barrier_requires_settled_actors_and_exact_restored_hooks():
    m = load()
    writer, owners, _ = model(m)
    hooks = m.ReadHooks(db_model(m), owners, lambda _: None)
    assert not m.barrier(owners, [hooks])
    assert writer.settle()
    assert not m.barrier(owners, [hooks])
    hooks.install()
    hooks.restore()
    assert m.barrier(owners, [hooks])
    assert not m.barrier([object()], [hooks])
    assert not m.barrier(owners, [object()])


@pytest.mark.parametrize("witness", [False, None, 1])
def test_db_cell_refuses_before_allocation_without_exact_writer_barrier(tmp_path, witness):
    from .test_local_media_native_binding_sample import cell_fixture

    fixture = cell_fixture(tmp_path)
    with pytest.raises(RuntimeError), fixture.context(writer_barrier=lambda: witness):
        pytest.fail("uncertain actor must not allocate a DB")
    assert fixture.acquired == [] and not (tmp_path / "binding-cells").exists()


def test_db_cell_cannot_release_or_restore_scope_under_late_writer_debt(tmp_path):
    from .test_local_media_native_binding_sample import cell_fixture

    fixture, safe = cell_fixture(tmp_path), [True]
    with pytest.raises(RuntimeError), fixture.context(writer_barrier=lambda: safe[0]) as db:
        safe[0] = False
    assert fixture.released == [] and db._conn is not None
    assert fixture.selection[0][1] is db and fixture.fx.native.home_path != fixture.original
    assert fixture.owners[0]["closed"] is False


def test_global_failure_cleanup_keeps_all_native_store_and_patch_owners_under_writer_debt(tmp_path):
    import types

    from .test_local_media_native_serving_fixture import load as load_fixture

    def forbidden(*args):
        pytest.fail("must retain every owner under uncertain writer debt")

    registry = types.SimpleNamespace(release=forbidden, close_all_under=forbidden)
    fx = types.SimpleNamespace(rig=types.SimpleNamespace(env=types.SimpleNamespace(
        store=types.SimpleNamespace(close=forbidden))))
    patch = types.SimpleNamespace(undo=forbidden)
    owners = {"workers_joined": True, "writer_barrier": lambda: False}
    assert load_fixture()._cleanup_setup(
        owners, registry, object(), fx, patch, tmp_path, {}) is False


def writer_report():
    return {"case": 0, "request": "control:page", "kind": "bot_chat", "selector": 1,
        "first": {"reason": "ok", "kind": "bot_chat", "accepted_count": 1,
                  "selection_verified": True},
        "second": {"reason": "ok", "kind": "bot_chat", "accepted_count": 1,
                   "selection_verified": True},
        "native_mutations_verified": 1, "synthetic_store_calls": 0, "native_guard_refused": False,
        "job_verified": True, "writer_joined": True, "release_verified": True,
        "hooks_restored": True, "read_events": 12, "trigger": ["before", "get_messages", 1],
        "residual_acceptance": False, "aba_acceptance": False}


@pytest.mark.parametrize("field", ["job_verified", "writer_joined", "release_verified",
    "hooks_restored", "native_mutations_verified", "trigger", "first", "raw_content"])
def test_writer_report_refuses_missing_witnesses_wrong_outcomes_or_private_data(field):
    m, report = load(), writer_report()
    m.validate_report(report, 0, 1, "control:page")
    if field in ("job_verified", "writer_joined", "release_verified", "hooks_restored"):
        report[field] = False
    elif field == "native_mutations_verified":
        report[field] = 0
    elif field == "trigger":
        report[field] = ["after", "get_messages", 1]
    elif field == "first":
        report[field]["accepted_count"] = 0
    else:
        report[field] = "forbidden"
    with pytest.raises(RuntimeError):
        m.validate_report(report, 0, 1, "control:page")


def test_writer_report_requires_its_mode_and_cannot_be_cost_or_mint_evidence():
    from .test_local_media_native_binding_sample import preparation_report
    from .test_local_media_native_serving_driver import driver, good

    report = good()
    prep = preparation_report()
    prep["cells"], prep["databases_closed"] = [prep["cells"][0], prep["cells"][4]], 1
    report["native_binding_preparation"] = prep
    report["native_binding_writer"] = writer_report()
    args = (report, report["native_source_hashes"], report["hmp_source_hashes"],
            report["runtime_executable_sha256"])
    driver.validate_report(*args, sample_binding_seed=True, binding_cost_case=0,
                           binding_cost_selector=1, binding_writer="control:page")
    with pytest.raises(RuntimeError):
        driver.validate_report(*args, sample_binding_seed=True,
                               binding_cost_case=0, binding_cost_selector=1)


def test_equal_counts_with_wrong_row_ids_cannot_become_selection_verified():
    from types import SimpleNamespace

    m, candidate = load(), object()
    reference = SimpleNamespace(sidecar=candidate, reason="ok", accepted=(8,),
                                kind=SimpleNamespace(value="bot_chat"))
    wrong = SimpleNamespace(sidecar=candidate, reason="ok", accepted=(10,), kind=reference.kind)
    with pytest.raises(RuntimeError):
        m._checked_outcome(wrong, reference, candidate, ("ok", "bot_chat", (8,)))


@pytest.mark.parametrize("job_ok", [True, False])
@pytest.mark.parametrize("release_ok", [True, False])
def test_scenario_controller_requires_actual_job_release_and_join_even_if_bridge_returns_ok(
    tmp_path, job_ok, release_ok
):
    from types import SimpleNamespace

    m = load()
    db, owners, hooks, effects = db_model(m), [], [], []
    candidate = SimpleNamespace(user_id="U", profile="alpha", session_id="R", query_tip="C",
                                provenance_consistent=True)
    reference = SimpleNamespace(sidecar=candidate, reason="ok", accepted=(8,), ok=True,
                                kind=SimpleNamespace(value="bot_chat"))

    read_state = [None]

    def set_read(sid, value):
        assert sid == "R" and value is True and threading.current_thread().name.endswith("writer")
        effects.append("native-model-write")
        if job_ok:
            read_state[0] = 7
        return job_ok

    db.set_session_read = set_read
    db.get_session = lambda sid: {"id": sid, "last_read_at": read_state[0]}

    def bind(sidecar):
        assert sidecar is candidate
        db.get_active_message_ids("C")
        db.get_messages("C")
        db.get_active_message_ids("C")
        return reference  # Deliberately cannot manufacture a writer acknowledgment.

    def acquire(path):
        assert path == tmp_path / "state.db"
        effects.append("borrow")
        return db

    def release(value):
        assert value is db
        effects.append("release")
        return release_ok

    fx = SimpleNamespace(native=SimpleNamespace(home_path=tmp_path,
                                                bridge=SimpleNamespace(bind_media_batch=bind)))
    options = {"case": 0, "request": "control:page", "user": "U", "profile": "alpha",
               "chat": "chat", "owners": owners, "hooks": hooks,
               "acquire_native": acquire, "release_native": release}
    if job_ok and release_ok:
        report = m.run_scenario(fx, db, candidate, reference, (8,),
                               {"kind": "bot_chat", "root": "R", "tip": "C"}, "extra", **options)
        m.validate_report(report, 0, 1, "control:page")
    else:
        with pytest.raises(RuntimeError):
            m.run_scenario(fx, db, candidate, reference, (8,),
                           {"kind": "bot_chat", "root": "R", "tip": "C"}, "extra", **options)
    assert len(owners) == 1 and owners[0].joined and not owners[0].thread.is_alive()
    assert effects == ["borrow", "native-model-write", "release"]
    assert m.barrier(owners, hooks) is release_ok


def test_writer_uses_captured_profile_context_instead_of_a_later_reader_value():
    import contextvars

    m, owners, seen, handle = load(), [], [], object()
    scope = contextvars.ContextVar("synthetic_writer_profile_scope", default="missing")
    token = scope.set("private-profile-at-construction")
    writer = m.OwnedWriter(owners, lambda: handle, lambda _: True,
                           lambda _: seen.append(scope.get()))
    try:
        scope.set("different-reader-profile-before-start")
        writer.start()
        writer.fire()
    finally:
        assert writer.settle()
        scope.reset(token)
    assert seen == ["private-profile-at-construction"]
    assert scope.get() == "missing"


@pytest.mark.parametrize("scenario", ["branch_child", "reset_child", "delegate_child"])
@pytest.mark.parametrize("kind", ["phone", "bot_chat"])
def test_constructed_children_preserve_parent_binding_oracle(scenario, kind):
    module = load()
    for seam in module.SEAMS:
        module.validate_request(0 if kind == "bot_chat" else 4, 16, scenario + ":" + seam)
    expected = ("ok", kind, (9,))
    assert module.expected_outcomes(scenario, kind, (9,)) == (expected, expected)


@pytest.mark.parametrize("scenario", ["branch_child", "reset_child", "delegate_child"])
@pytest.mark.parametrize("fault", [None, "existing", "wrong_parent", "wrong_marker",
                                   "no_message", "hijack"])
def test_child_construction_requires_fresh_identity_marker_history_and_parent_isolation(
    scenario, fault
):
    module = load()
    calls = []
    marker = {"branch_child": "_branched_from", "reset_child": "_reset_from",
              "delegate_child": "_delegate_from"}[scenario]

    class DB:
        def get_session(self, sid):
            if not calls:
                return {} if fault == "existing" else None
            return {"id": sid,
                    "parent_session_id": "foreign" if fault == "wrong_parent" else "parent",
                    "model_config": {marker: "foreign" if fault == "wrong_marker" else "parent"}}

        def create_session(self, sid, source, **kwargs):
            calls.append(("create", sid, source, kwargs))
            return sid

        def append_message(self, sid, role, **kwargs):
            calls.append(("append", sid, role, kwargs))
            return 77

        def get_active_message_ids(self, sid):
            return [] if fault == "no_message" else [77]

        def resolve_resume_session_id(self, sid):
            return "foreign" if fault == "hijack" else sid

    if fault:
        with pytest.raises(RuntimeError):
            module.construct_isolated_child(DB(), "parent", scenario)
        if fault == "existing":
            assert calls == []
    else:
        assert module.construct_isolated_child(DB(), "parent", scenario) == 2
        assert [call[0] for call in calls] == ["create", "append"]
        assert calls[0][3] == {"parent_session_id": "parent", "model_config": {marker: "parent"}}


def test_pair_plan_preserves_every_declared_phase_without_execution():
    module = load()
    before = set(threading.enumerate())
    plan = module.paired_plan()
    assert set(threading.enumerate()) == before
    assert len(plan) == 456
    phases = [(case, selector, request) for case, selector, pair in plan for request in pair]
    expected = {(case, selector, request) for case in range(8) for selector in (1, 16, 128)
                for request in module.declared_requests(case)}
    assert len(phases) == len(set(phases)) == len(expected) == 912
    assert set(phases) == expected
    assert all(type(pair) is tuple and len(pair) == 2 and pair[0] != pair[1]
               for _, _, pair in plan)
    assert all(case < 4 for case, _, request in phases
               if request.split(":")[0] in module.BOT_ONLY)
    assert len(module.declared_requests(0)) == 44
    assert len(module.declared_requests(4)) == 32


@pytest.mark.parametrize("case", [True, -1, 8, None, "0"])
def test_inventory_refuses_invalid_case_before_planning(case):
    with pytest.raises(RuntimeError):
        load().declared_requests(case)


@pytest.mark.parametrize("scenario_pair", [(), ("control:page",),
    ("control:page", "control:page"), ("control:page", "bad:page"),
    ["control:page", "append:page"], ("control:page", None),
    (("control:page", "append:page"), "deactivate:page")])
def test_invalid_pair_refuses_before_source_or_filesystem(tmp_path, scenario_pair):
    from .test_local_media_native_serving_driver import driver

    with pytest.raises(RuntimeError):
        driver.run_fixture(tmp_path, tmp_path, "a" * 40, sample_binding_seed=True,
            binding_cost_case=0, binding_cost_selector=1, binding_writer=scenario_pair)
    assert not tuple(tmp_path.iterdir())


def test_all_planned_pairs_are_explicitly_validated_before_admission():
    module = load()
    for case, selector, pair in module.paired_plan():
        module.validate_request(case, selector, pair)


@pytest.mark.parametrize("fault", [None, "one_preparation", "one_writer", "wrong_order",
                                   "wrong_outcome", "single_mode"])
def test_pair_report_requires_two_independently_valid_ordered_phases(fault):
    import copy

    from .test_local_media_native_binding_sample import preparation_report
    from .test_local_media_native_serving_driver import driver, good

    report, prep = good(), preparation_report()
    prep["cells"], prep["databases_closed"] = [prep["cells"][0], prep["cells"][4]], 1
    first, second = writer_report(), writer_report()
    second["request"] = "title_guard:page"
    second["native_mutations_verified"] = 0
    second["native_guard_refused"] = True
    report["native_binding_preparation"] = [prep, copy.deepcopy(prep)]
    report["native_binding_writer"] = [first, second]
    mode = ("control:page", "title_guard:page")
    if fault == "one_preparation":
        report["native_binding_preparation"].pop()
    if fault == "one_writer":
        report["native_binding_writer"].pop()
    if fault == "wrong_order":
        report["native_binding_writer"].reverse()
    if fault == "wrong_outcome":
        second["second"]["accepted_count"] = 0
    if fault == "single_mode":
        mode = "control:page"
    args = (report, report["native_source_hashes"], report["hmp_source_hashes"],
            report["runtime_executable_sha256"])
    if fault:
        with pytest.raises(RuntimeError):
            driver.validate_report(*args, sample_binding_seed=True, binding_cost_case=0,
                                   binding_cost_selector=1, binding_writer=mode)
    else:
        driver.validate_report(*args, sample_binding_seed=True, binding_cost_case=0,
                               binding_cost_selector=1, binding_writer=mode)


@pytest.mark.parametrize("kind, fresh", [("bot_chat", "not_eligible"),
                                        ("phone", "provenance_mismatch")])
def test_ordinary_child_oracle_refuses_the_old_parent_binding(kind, fresh):
    module = load()
    assert module.expected_outcomes("ordinary_child", kind, (7,)) == (
        ("tip_changed", None, ()), (fresh, None, ()))
    for seam in module.SEAMS:
        module.validate_request(0 if kind == "bot_chat" else 4, 128, "ordinary_child:" + seam)


@pytest.mark.parametrize("fault", [None, "existing", "ended_parent", "wrong_parent",
    "marked_child", "wrong_source", "absent_message", "unchanged_resume", "changed_lineage"])
def test_ordinary_child_requires_actual_native_divergence_facts(fault):
    module, calls = load(), []

    class DB:
        def get_compression_lineage(self, root):
            return ["root", "child"] if calls and fault == "changed_lineage" else ["root", "tip"]

        def get_session(self, sid):
            if sid == "tip":
                return {"end_reason": "compression" if fault == "ended_parent" else None}
            if not calls:
                return {} if fault == "existing" else None
            return {"id": sid,
                    "parent_session_id": "foreign" if fault == "wrong_parent" else "tip",
                    "source": "tool" if fault == "wrong_source" else "api_server",
                    "model_config": {"_reset_from": "tip"} if fault == "marked_child" else None}

        def create_session(self, sid, source, **kwargs):
            calls.append(("create", sid, source, kwargs))
            return sid

        def append_message(self, sid, role, **kwargs):
            calls.append(("append", sid, role, kwargs))
            return 77

        def get_active_message_ids(self, sid):
            return [] if fault == "absent_message" else [77]

        def resolve_resume_session_id(self, root):
            if len(calls) < 2 or fault == "unchanged_resume":
                return "tip"
            return calls[0][1]

    if fault:
        with pytest.raises(RuntimeError):
            module.construct_divergent_child(DB(), "root", "tip")
        if fault in ("existing", "ended_parent"):
            assert calls == []
    else:
        assert module.construct_divergent_child(DB(), "root", "tip") == 2
        assert [call[0] for call in calls] == ["create", "append"]
        assert calls[0][3] == {"parent_session_id": "tip"}
