"""Selected schema factory DATA only; no parent-capsule or rooted live dispatch."""
import sys
import pytest
from hmp_startup import retained_binding_origin as selected


def test_bound_capture_retains_actual_packet_columns_and_preheld_checker_row():
    seen, live_calls = [], []
    factory_code = selected.capture_bound.__code__
    checker_code, live_code = selected.current.__code__, selected.current_live.__code__
    assert sys.getprofile() is None
    def observe(frame,event,value):
        if event=='call' and frame.f_code is live_code:live_calls.append(True)
        if (event=='call' and frame.f_code is checker_code and frame.f_back is not None
                and frame.f_back.f_code is factory_code):
            local=frame.f_back.f_locals
            seen.append((local.get('record'),local['live_row']))
    sys.setprofile(observe)
    try:record=selected.capture_bound()
    finally:sys.setprofile(None)
    assert type(record) is tuple and len(record)==3
    packet,layout,row=record
    assert len(packet)==6 and layout[0] is packet and row[1] is selected.current_live
    assert len(seen)==2 and seen[0][0] is None and seen[1][0] is record
    assert seen[0][1] is seen[1][1] is row and live_calls==[]
    for columns,rows,pair_index in ((layout[1],packet[3],2),
                                    (layout[2],packet[4],2),(layout[3],packet[5],5)):
        assert len(columns)==len(rows)
        for (actual,keys,values),original in zip(columns,rows,strict=True):
            assert actual is original
            assert type(keys) is type(values) is tuple
            for pair,key,value in zip(original[pair_index],keys,values,strict=True):
                assert pair[0] is key and pair[1] is value
    assert selected.current(packet) is packet
    assert selected.current_live(packet,layout) is packet  # actual captured layout; no admission authority
    with pytest.raises(TypeError):record[1]=()


def test_generic_capture_api_is_unchanged_and_copies_are_not_root_authority():
    packet=selected.capture()
    assert type(packet) is tuple and len(packet)==6 and selected.current(packet) is packet
    record=selected.capture_bound();copied=tuple(list(record))
    assert copied is not record and all(a is b for a,b in zip(copied,record,strict=True))
    assert selected.current(copied[0]) is copied[0]
    # No original EntryOrigin/STARTED/CELL/capsule receipt is created by this DATA test.


@pytest.mark.parametrize('boundary',(1,2))
@pytest.mark.parametrize('fault',('live_code','live_export','checker_code','checker_export','live_kwdict','error_and_live_code'))
def test_bound_factory_rejoins_fixed_checker_after_each_callback(monkeypatch,boundary,fault):
    factory_code,checker_code=selected.capture_bound.__code__,selected.current.__code__
    reached,changes,foreign_calls=[],[],[]
    def foreign(*args,**kwargs):raise AssertionError('foreign selected checker executed')
    def observe(frame,event,value):
        if event=='call' and frame.f_code is foreign.__code__:foreign_calls.append(True)
        if (event=='return' and frame.f_code is checker_code and frame.f_back is not None
                and frame.f_back.f_code is factory_code):
            reached.append(True)
            if len(reached)==boundary:
                changes.append(True)
                if fault=='error_and_live_code':
                    def foreign_error(*args,**kwargs):
                        foreign_calls.append(True)
                        raise AssertionError('changed error constructor executed')
                    monkeypatch.setattr(selected.RetainedBindingOriginError,'__init__',foreign_error)
                    monkeypatch.setattr(selected.current_live,'__code__',foreign.__code__)
                elif fault=='live_code':monkeypatch.setattr(selected.current_live,'__code__',foreign.__code__)
                elif fault=='live_export':monkeypatch.setattr(selected,'current_live',foreign)
                elif fault=='checker_code':monkeypatch.setattr(selected.current,'__code__',foreign.__code__)
                elif fault=='checker_export':monkeypatch.setattr(selected,'current',foreign)
                else:monkeypatch.setattr(selected.current_live,'__kwdefaults__',{})
    assert sys.getprofile() is None
    sys.setprofile(observe)
    try:
        with pytest.raises(RuntimeError,match='BI1_RETAINED_HELPER_ORIGIN_REFUSED') as refused:
            selected.capture_bound()
        assert type(refused.value) is RuntimeError and refused.value.args==('BI1_RETAINED_HELPER_ORIGIN_REFUSED',)
    finally:sys.setprofile(None)
    assert len(reached)==boundary and changes==[True] and foreign_calls==[]


def test_live_target_refusal_does_not_use_a_changed_custom_error_constructor(monkeypatch):
    packet,layout,_=selected.capture_bound()
    changed=(False,*packet[1:]);calls=[]
    def foreign_error(*args,**kwargs):
        calls.append(True)
        raise AssertionError('custom error constructor dispatched')
    monkeypatch.setattr(selected.RetainedBindingOriginError,'__init__',foreign_error)
    with pytest.raises(RuntimeError) as refused:
        selected.current_live(changed,(changed,*layout[1:]))
    assert type(refused.value) is RuntimeError
    assert refused.value.args==('BI1_RETAINED_HELPER_ORIGIN_REFUSED',) and calls==[]
