"""Original capture record DATA; not root custody, fast dispatch or startup acceptance."""
import sys
import pytest
from hmp_plugin import presentation_native_link as link


def test_record_retains_literal_engine_layout_and_early_checker_row():
    record = link._capture_engine()
    assert type(record) is tuple and len(record) == 3
    engine, layout, checker = record
    assert type(engine) is tuple and len(engine) == 6
    assert layout is engine[5] and sum(row is checker for row in engine[2]) == 1
    assert checker[0] == '_engine_origin_tail' and checker[1] is link._engine_origin_tail
    assert checker[1](engine) is engine  # Complete generic DATA validation remains.
    with pytest.raises(TypeError):
        record[0] = ()


def test_literal_record_and_checker_exist_before_full_validator_callback():
    observed = []
    capture_code = link._capture_engine.__code__
    checker_code = link._engine_origin_tail.__code__
    previous = sys.getprofile()
    assert previous is None
    def observe(frame, event, value):
        if event == 'call' and frame.f_code is checker_code and frame.f_back is not None and frame.f_back.f_code is capture_code:
            parent = frame.f_back.f_locals
            observed.append((parent['audit_record'], parent['checker_row']))
    sys.setprofile(observe)
    try:
        record = link._capture_engine()
    finally:
        sys.setprofile(previous)
    assert len(observed) == 1
    assert observed[0][0] is record and observed[0][1] is record[2]


def test_coherent_record_copy_is_distinct_not_an_original_root_claim():
    record = link._capture_engine()
    copied = tuple(list(record))
    assert copied is not record and all(a is b for a, b in zip(copied, record, strict=True))
    # Generic DATA remains generic: this result does not accept copied root custody.
    assert copied[2][1](copied[0]) is copied[0]
