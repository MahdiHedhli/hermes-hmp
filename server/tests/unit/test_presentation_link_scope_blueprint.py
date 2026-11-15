"""Actual fixed blueprint returns and publication DATA; no native admission."""
import sys

import pytest

from hmp_plugin import presentation_link_path_policy as policy
from hmp_plugin.presentation_startup_artifacts import (
    ArtifactObservationError, ExpectedArtifact, _RuntimeSource,
)
from hmp_startup import link_factory_origin as origins
from hmp_startup.runtime_files import ExecutableLinkPlan, LinkHop, RuntimeFilePlan


@pytest.fixture
def prepared(monkeypatch):
    monkeypatch.setattr(origins, '_CAPTURE_STARTED', False)
    origin = origins.capture()

    class Owner:
        pass

    class Activation:
        pass

    class Entry:
        pass

    owner, activation = Owner(), Activation()
    context, lineage = (7, 1000, 9), object()
    cells = [[], [None], [None], [None], [None]]
    classes = tuple((kind, tuple(vars(kind).items()), ())
                    for kind in (Owner, Entry, Activation, Owner, Entry))
    cohort = (((vars(owner), ()), (vars(activation), ()), ({}, ()), ({}, ()), ({}, ())),
              tuple((cell, tuple(cell)) for cell in cells), classes)

    def runtime(hops=1):
        links = []
        for index in range(hops):
            name = 'target' if index == hops - 1 else 'h' + str(index + 1)
            links.append(LinkHop('/p/h' + str(index), name.encode(), '/p/' + name))
        link = ExecutableLinkPlan(tuple(links), ExpectedArtifact('/p/target', 10, '0' * 64),
                                  1000, 0o700, sum(len(h.target) for h in links))
        plan = RuntimeFilePlan((), (), (), b'', b'', object(), (), (), (), (), (), (), (), (), link)
        return _RuntimeSource(object(), Entry, object(), (), None, None, plan, link,
                              cells[0], cells[1], cells[2], cells[3], 4096)

    return origin, owner, context, lineage, cohort, runtime, activation, cells


def make(prepared, hops=1):
    origin, owner, context, lineage, cohort, runtime, _, _ = prepared
    factory = origins.blueprint_factory(origin)
    assert factory is policy._new_scope_blueprint
    return factory(owner, runtime(hops), context, lineage, origin, cohort)


@pytest.mark.parametrize('hops', (1, 8))
def test_fixed_full_phase_blueprint_retains_actual_policy_returns(prepared, hops):
    actual = []
    code = policy._new_policy.__code__

    def observe(frame, event, value):
        if event == 'return' and frame.f_code is code:
            actual.append(value)
        return observe

    previous = sys.gettrace()
    sys.settrace(observe)
    try:
        blueprint = make(prepared, hops)
    finally:
        sys.settrace(previous)
    origin, owner, context, lineage, _, _, _, _ = prepared
    assert blueprint.owner is owner and blueprint.context is context
    assert blueprint.origin is origin and blueprint.lineage is lineage
    assert len(blueprint.rows) == len(actual) == 3 * (hops + 1)
    assert all(row is returned for row, returned in zip(blueprint.rows, actual, strict=True))
    assert [(row.phase, row.index) for row in blueprint.rows] == [
        (phase, index) for phase in ('before', 'after', 'recheck') for index in range(hops + 1)]
    assert policy._scope_blueprint_tail(blueprint) is blueprint


def test_delegated_factory_keyword_content_change_refuses_before_hook(prepared, monkeypatch):
    calls = []

    def foreign(value):
        calls.append(value)
        raise AssertionError('changed delegated default ran')

    monkeypatch.setitem(origins.factory.__kwdefaults__, '_type', foreign)
    with pytest.raises(RuntimeError, match='BI1_LINK_FACTORY_ORIGIN_REFUSED'):
        origins.blueprint_factory(prepared[0])
    assert calls == []


@pytest.mark.parametrize('which', ('plan', 'link'))
def test_typed_runtime_with_foreign_nested_plan_refuses_without_hooks(prepared, which):
    calls = []

    class Foreign:
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError('foreign runtime plan getter')

    origin, owner, context, lineage, cohort, runtime, _, _ = prepared
    changed = runtime()._replace(**{which: Foreign()})
    with pytest.raises(ArtifactObservationError):
        policy._new_scope_blueprint(owner, changed, context, lineage, origin, cohort)
    assert calls == []


@pytest.mark.parametrize('field', ('index', 'phase', 'actor_uid', 'bound'))
def test_typed_policy_with_foreign_comparison_field_refuses_without_hooks(prepared, field):
    blueprint = make(prepared)
    calls = []

    class Foreign:
        def __eq__(self, other):
            calls.append('equality')
            raise AssertionError('foreign comparison')
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError('foreign getter')

    row = blueprint.rows[0]._replace(**{field: Foreign()})
    changed = blueprint._replace(rows=(row, *blueprint.rows[1:]))
    with pytest.raises(ArtifactObservationError):
        policy._scope_blueprint_tail(changed)
    assert calls == []


@pytest.mark.parametrize('at', (1, 2, 6))
@pytest.mark.parametrize('fault', ('factory', 'need_code', 'owner_slot', 'io_slot'))
def test_first_and_later_policy_returns_refuse_changed_cohorts(prepared, monkeypatch, at, fault):
    origin, owner, _, _, _, _, _, cells = prepared
    code = policy._new_policy.__code__
    reached, calls = [], []
    foreign_slot = object()

    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('foreign blueprint helper ran')

    def changed_code(*args, **kwargs):
        raise AssertionError('changed need code executed')

    def trace(frame, event, result):
        if event == 'return' and frame.f_code is code:
            reached.append(result)
            if len(reached) == at:
                sys.settrace(None)
                if fault == 'factory':
                    monkeypatch.setattr(policy, '_new_policy', foreign)
                elif fault == 'need_code':
                    monkeypatch.setattr(policy._need, '__code__', changed_code.__code__)
                elif fault == 'owner_slot':
                    owner._scope = foreign_slot
                else:
                    cells[4][0] = foreign_slot
        return trace

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises((RuntimeError, ArtifactObservationError)):
            make(prepared)
    finally:
        sys.settrace(previous)
    assert len(reached) == at and calls == []
    if fault == 'owner_slot':
        assert owner._scope is foreign_slot
    if fault == 'io_slot':
        assert cells[4][0] is foreign_slot


def test_legacy_scope_has_no_blueprint_or_new_authority():
    from hmp_plugin.presentation_startup_artifacts import _Scope

    scope = _Scope(object(), object(), (), (), [])
    assert scope.native_link_blueprint is None
    assert scope.native_link_audit is None
