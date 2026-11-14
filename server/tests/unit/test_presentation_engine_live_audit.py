"""Unwired fixed live target controls; never rooted dispatch/startup acceptance."""
import sys
import pytest
from hmp_plugin import presentation_native_link as link
from hmp_plugin import presentation_metadata_custody as custody


def test_fixed_live_row_is_literal_and_preheld_before_generic_callback():
    seen = []
    capture_code, generic_code = link._capture_engine.__code__, link._engine_origin_tail.__code__
    assert sys.getprofile() is None
    def observe(frame, event, value):
        if (event == 'call' and frame.f_code is generic_code and frame.f_back is not None
                and frame.f_back.f_code is capture_code):
            seen.append(frame.f_back.f_locals['live_checker_row'])
    sys.setprofile(observe)
    try:
        record = link._capture_engine()
    finally:
        sys.setprofile(None)
    rows = [row for row in record[0][2] if row[0] == '_engine_live_tail']
    assert len(rows) == len(seen) == 1 and rows[0] is seen[0]
    assert rows[0][1] is link._engine_live_tail
    assert record[2][0] == '_engine_origin_tail'  # record3 semantics unchanged
    assert link._engine_origin_tail(record[0]) is record[0]
    assert rows[0][1](record[0], record[1]) is record[0]


def test_live_target_cannot_accept_a_copied_layout_argument():
    record = link._capture_engine()
    copied = tuple(list(record[1]))
    assert copied is not record[1]
    with pytest.raises(link.ArtifactObservationError):
        link._engine_live_tail(record[0], copied)


@pytest.mark.parametrize('fault', ('missing_none', 'foreign_value', 'reordered'))
def test_live_target_keeps_fresh_class_key_and_value_checks(monkeypatch, fault):
    kind = custody._DirectoryPayload
    key = '_synthetic_live_audit_none'
    monkeypatch.setattr(kind, key, None, raising=False)
    record = link._capture_engine()
    assert link._engine_live_tail(record[0], record[1]) is record[0]
    if fault == 'foreign_value':
        monkeypatch.setattr(kind, key, object())
    else:
        monkeypatch.delattr(kind, key)
        monkeypatch.setattr(kind, key if fault == 'reordered' else key + '_renamed', None, raising=False)
    for function, args in ((link._engine_origin_tail, (record[0],)),
                           (link._engine_live_tail, (record[0], record[1]))):
        if fault == 'reordered':
            assert function(*args) is record[0]
        else:
            with pytest.raises(link.ArtifactObservationError):
                function(*args)


@pytest.mark.parametrize('fault', ('function_code', 'function_export', 'keyword_value'))
def test_live_target_rejects_mutable_drift_after_an_earlier_success(monkeypatch, fault):
    record = link._capture_engine()
    assert link._engine_live_tail(record[0], record[1]) is record[0]
    calls = []
    def foreign(*args, **kwargs):
        calls.append(True)
        raise AssertionError('foreign callback dispatched')
    if fault == 'function_code':
        def changed(*args, **kwargs):
            raise AssertionError('changed code dispatched')
        monkeypatch.setattr(link._snapshot, '__code__', changed.__code__)
    elif fault == 'function_export':
        monkeypatch.setattr(link, '_snapshot', foreign)
    else:
        monkeypatch.setitem(link._engine_origin_tail.__kwdefaults__, '_id', foreign)
    with pytest.raises(link.ArtifactObservationError):
        link._engine_live_tail(record[0], record[1])
    assert calls == []


@pytest.mark.parametrize('fault', ('code', 'keyword'))
def test_capture_rejoins_fixed_live_target_after_generic_return(monkeypatch, fault):
    generic_code, capture_code = link._engine_origin_tail.__code__, link._capture_engine.__code__
    changed_rows, foreign_calls = [], []
    def changed(*args, **kwargs):
        raise AssertionError('changed live checker code ran')
    def foreign(*args, **kwargs):
        foreign_calls.append(True)
        raise AssertionError('foreign live primitive ran')
    def observe(frame, event, value):
        if (event == 'return' and frame.f_code is generic_code and frame.f_back is not None
                and frame.f_back.f_code is capture_code):
            changed_rows.append(frame.f_back.f_locals['live_checker_row'])
            if fault == 'code':
                monkeypatch.setattr(link._engine_live_tail, '__code__', changed.__code__)
            else:
                monkeypatch.setitem(link._engine_live_tail.__kwdefaults__, '_id', foreign)
    assert sys.getprofile() is None
    sys.setprofile(observe)
    try:
        with pytest.raises(RuntimeError):
            link._capture_engine()
    finally:
        sys.setprofile(None)
    assert len(changed_rows) == 1 and foreign_calls == []
