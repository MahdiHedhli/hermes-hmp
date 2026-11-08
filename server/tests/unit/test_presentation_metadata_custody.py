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
