"""Memory-only custody checks; these do not qualify the native metadata caller."""
import gc
import weakref

import pytest

from hmp_plugin.presentation_metadata_custody import (
    _allocate_directory_custody,
    _capture_payload_origin,
    _directory_payload_cells,
    _retire_directory_payload_data,
)
from hmp_plugin.presentation_startup_artifacts import ArtifactObservationError


def allocation():
    owner, operation, consumer, unset = object(), {}, {}, object()
    origin = _capture_payload_origin()
    link, slot = [None], [None]
    marker, payload = _allocate_directory_custody(
        owner, operation, consumer, origin, link, slot, unset)
    return owner, origin, marker, payload, unset


def test_detach_preserves_held_contents_and_forbids_duplicate():
    owner, origin, marker, payload, unset = allocation()
    cells = _directory_payload_cells(owner, origin, marker, payload)
    assert cells.raw[0] is unset
    raw = object()
    cells.raw[0] = raw
    record = _retire_directory_payload_data(owner, origin, marker, payload)
    assert record.detached and not record.unmatched_link
    assert marker.owner_link == [None]
    assert marker.state == [True, True, False]
    assert cells.raw[0] is raw
    with pytest.raises(ArtifactObservationError):
        _retire_directory_payload_data(owner, origin, marker, payload)
    with pytest.raises(ArtifactObservationError):
        _directory_payload_cells(owner, origin, marker, payload)


@pytest.mark.parametrize('replacement', [None, object()])
def test_foreign_link_is_preserved(replacement):
    owner, origin, marker, payload, _ = allocation()
    marker.owner_link[0] = replacement
    record = _retire_directory_payload_data(owner, origin, marker, payload)
    assert marker.owner_link[0] is replacement
    assert not record.detached and record.unmatched_link
    assert marker.state == [True, True, True]


def test_copied_marker_and_wrong_owner_cannot_retire():
    owner, origin, marker, payload, _ = allocation()
    for held_owner, held_marker in ((owner, marker._replace()), (object(), marker)):
        with pytest.raises(ArtifactObservationError):
            _retire_directory_payload_data(held_owner, origin, held_marker, payload)
        assert marker.owner_link[0] is payload
        assert marker.state == [False, False, False]


def test_copied_payload_cannot_replace_actual_weak_identity():
    owner, origin, marker, payload, _ = allocation()
    copied = object.__new__(origin.payload_type)
    for member in origin.members:
        member.__set__(copied, member.__get__(payload, origin.payload_type))
    marker.owner_link[0] = copied
    with pytest.raises(ArtifactObservationError):
        _retire_directory_payload_data(owner, origin, marker, copied)
    assert marker.owner_link[0] is copied
    assert marker.state == [False, False, False]


def test_owned_graph_reclaims_without_cyclic_gc():
    class Raw:
        pass

    enabled = gc.isenabled()
    gc.disable()
    try:
        owner, origin, marker, payload, _ = allocation()
        raw = Raw()
        cells = _directory_payload_cells(owner, origin, marker, payload)
        cells.raw[0] = raw
        cells.envelope[0] = (marker.operation, marker.consumer, raw)
        marker.operation['marker'] = marker
        marker.consumer['marker'] = marker
        payload_ref, raw_ref = weakref.ref(payload), weakref.ref(raw)
        record = _retire_directory_payload_data(owner, origin, marker, payload)
        del cells, payload, raw
        assert payload_ref() is None
        assert raw_ref() is None
        assert record.marker is marker
        assert marker.operation['marker'] is marker
    finally:
        if enabled:
            gc.enable()


def test_interruption_after_detach_never_reattaches_or_rearms():
    import inspect
    import sys

    owner, origin, marker, payload, _ = allocation()
    function = _retire_directory_payload_data
    lines, start = inspect.getsourcelines(function)
    target = start + next(i for i, line in enumerate(lines)
                          if 'record = tuple.__new__' in line)
    previous = sys.gettrace()
    injected = []

    def interrupt(frame, event, _arg):
        if frame.f_code is function.__code__ and event == 'line' and frame.f_lineno == target:
            assert marker.owner_link[0] is None
            assert marker.state == [True, False, False]
            injected.append(True)
            sys.settrace(previous)
            raise RuntimeError('synthetic interruption')
        return interrupt

    try:
        sys.settrace(interrupt)
        with pytest.raises(ArtifactObservationError):
            function(owner, origin, marker, payload)
    finally:
        sys.settrace(previous)
    assert injected == [True]
    assert marker.owner_link[0] is None
    assert marker.state == [True, False, False]
    record = function(owner, origin, marker, payload)
    assert not record.detached and record.unmatched_link
    assert marker.owner_link[0] is None
    assert marker.state == [True, True, True]


def test_callback_bearing_reference_is_refused_before_detach():
    owner, origin, marker, payload, _ = allocation()
    callback_calls = []
    modified = marker._replace(reference=weakref.ref(payload, callback_calls.append))
    marker.marker_slot[0] = modified
    with pytest.raises(ArtifactObservationError):
        _retire_directory_payload_data(owner, origin, modified, payload)
    assert marker.owner_link[0] is payload
    assert modified.state == [False, False, False]
    assert callback_calls == []


@pytest.mark.parametrize('fault', ['state_after_weakref', 'cell_after_getter'])
def test_post_descriptor_line_fault_refuses_without_foreign_callbacks(fault):
    """Actual source-line faults; this is not a C-profile callback claim."""
    import ast
    import inspect
    import sys

    from hmp_plugin.presentation_metadata_custody import _marker_tail

    owner, origin, marker, payload, _ = allocation()
    calls = []

    class Foreign:
        def __eq__(self, _other):
            calls.append('equality')
            raise AssertionError('foreign equality')

        def __getattr__(self, _name):
            calls.append('getter')
            raise AssertionError('foreign getter')

    function = _marker_tail if fault == 'state_after_weakref' else _directory_payload_cells
    lines, start = inspect.getsourcelines(function)
    tree = ast.parse(''.join(lines)).body[0]
    expressions = [node for node in tree.body if isinstance(node, ast.Expr)
                   and isinstance(node.value, ast.Call)
                   and isinstance(node.value.func, ast.Name)]
    if fault == 'state_after_weakref':
        target = [node for node in expressions if node.value.func.id == '_require'][-1]
    else:
        target = [node for node in expressions if node.value.func.id == '_marker_tail'][1]
    target_line = start + target.lineno - 1
    previous, injected = sys.gettrace(), []

    def interrupt(frame, event, _arg):
        if frame.f_code is function.__code__ and event == 'line' and frame.f_lineno == target_line:
            assert frame.f_locals['marker'] is marker
            assert frame.f_locals['payload'] is payload
            injected.append(True)
            sys.settrace(previous)
            if fault == 'state_after_weakref':
                marker.state[0] = Foreign()
            else:
                assert frame.f_locals['cells'].raw is origin.members[0].__get__(payload)
                origin.members[0].__set__(payload, Foreign())
        return interrupt

    try:
        sys.settrace(interrupt)
        with pytest.raises(ArtifactObservationError):
            function(owner, origin, marker, payload)
    finally:
        sys.settrace(previous)
    assert injected == [True]
    assert calls == []
    assert marker.owner_link[0] is payload


def test_cell_replacement_after_last_marker_return_is_not_adopted():
    """Trace the actual final marker return, not an assumed C-profile event."""
    import ast
    import inspect
    import sys

    from hmp_plugin.presentation_metadata_custody import _marker_tail

    owner, origin, marker, payload, _ = allocation()
    held_cell = origin.members[0].__get__(payload)
    foreign_cell = [object()]
    source = inspect.getsource(_directory_payload_cells)
    calls = [node for node in ast.walk(ast.parse(source))
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == '_marker_tail']
    assert len(calls) >= 2
    previous, observed, injected = sys.gettrace(), [], []

    def interrupt(frame, event, arg):
        if (frame.f_code is _marker_tail.__code__ and event == 'return'
                and frame.f_back.f_code is _directory_payload_cells.__code__):
            assert arg is marker
            assert frame.f_locals['payload'] is payload
            observed.append(True)
            if len(observed) == len(calls):
                assert origin.members[0].__get__(payload) is held_cell
                sys.settrace(previous)
                origin.members[0].__set__(payload, foreign_cell)
                injected.append(True)
        return interrupt

    try:
        sys.settrace(interrupt)
        with pytest.raises(ArtifactObservationError):
            _directory_payload_cells(owner, origin, marker, payload)
    finally:
        sys.settrace(previous)
    assert observed == [True] * len(calls)
    assert injected == [True]
    assert origin.members[0].__get__(payload) is foreign_cell
    assert marker.owner_link[0] is payload
    assert marker.state == [False, False, False]


@pytest.mark.parametrize('replacement', [None, object()])
def test_retirement_preserves_foreign_marker_slot_and_detaches_original(replacement):
    owner, origin, marker, payload, _ = allocation()
    marker.marker_slot[0] = replacement
    with pytest.raises(ArtifactObservationError):
        _directory_payload_cells(owner, origin, marker, payload)
    copied = marker._replace()
    with pytest.raises(ArtifactObservationError):
        _retire_directory_payload_data(owner, origin, copied, payload)
    assert marker.owner_link[0] is payload
    assert marker.marker_slot[0] is replacement
    assert marker.state == [False, False, False]
    record = _retire_directory_payload_data(owner, origin, marker, payload)
    assert record.detached and not record.unmatched_link and record.unmatched_marker
    assert marker.owner_link[0] is None
    assert marker.marker_slot[0] is replacement
    assert marker.state == [True, True, True]
