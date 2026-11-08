"""Pre-effect directory payload custody DATA; no IO, actor or receipt authority.

This component is not integrated. The fixed metadata caller must hold its actual
origin/marker/link/payload before effects, prove original actor and ended-call
state before retirement, and migrate every raw-bearing reverse reference first.
"""
from __future__ import annotations

import _weakref
import sys
from types import MemberDescriptorType, ModuleType, WrapperDescriptorType
from typing import NamedTuple

from .presentation_startup_artifacts import ArtifactObservationError, _require

_FIELDS = ('raw', 'category', 'snapshot', 'envelope', 'consumption')


class _DirectoryPayload:
    __slots__ = (*_FIELDS, '__weakref__')

    def __repr__(self):
        return '<DirectoryPayload private DATA redacted>'


class _PayloadOrigin(NamedTuple):
    payload_type: type
    marker_type: type
    record_type: type
    members: tuple
    reference_type: type
    reference_call: object
    reference_callback: object

    def __repr__(self):
        return '<PayloadOrigin construction DATA redacted>'


class _RetirementMarker(NamedTuple):
    owner: object
    operation: object
    consumer: object
    origin: _PayloadOrigin
    owner_link: list
    marker_slot: list
    reference: object
    state: list

    def __repr__(self):
        return '<RetirementMarker no result authority redacted>'


class _RetirementRecord(NamedTuple):
    marker: _RetirementMarker
    detached: bool
    unmatched_link: bool

    def __repr__(self):
        return '<RetirementRecord historical DATA redacted>'


class _PayloadCells(NamedTuple):
    raw: list
    category: list
    snapshot: list
    envelope: list
    consumption: list

    def __repr__(self):
        return '<PayloadCells temporary private DATA redacted>'


def _origin_tail(origin):
    _require(type(origin) is _PayloadOrigin
             and type(origin.payload_type) is type
             and origin.payload_type is _DirectoryPayload
             and origin.marker_type is _RetirementMarker
             and origin.record_type is _RetirementRecord
             and type(origin.members) is tuple and len(origin.members) == len(_FIELDS)
             and type(origin.reference_type) is type
             and type(origin.reference_call) is WrapperDescriptorType
             and origin.reference_call.__objclass__ is origin.reference_type
             and type(origin.reference_call.__name__) is str
             and origin.reference_call.__name__ == '__call__'
             and type(origin.reference_callback) is MemberDescriptorType
             and origin.reference_callback.__objclass__ is origin.reference_type
             and type(origin.reference_callback.__name__) is str
             and origin.reference_callback.__name__ == '__callback__')
    for name, descriptor in zip(_FIELDS, origin.members, strict=True):
        _require(type(descriptor) is MemberDescriptorType
                 and descriptor.__objclass__ is origin.payload_type
                 and type(descriptor.__name__) is str and descriptor.__name__ == name)
    return origin


def _capture_payload_origin():
    """Capture fixed construction types before caller callbacks/effects."""
    _require(type(_weakref) is ModuleType and type(sys.modules) is dict
             and sys.modules.get('_weakref') is _weakref)
    namespace = vars(_weakref)
    reference_type = namespace.get('ReferenceType')
    _require(type(reference_type) is type and namespace.get('ref') is reference_type
             and type(reference_type.__name__) is str
             and reference_type.__name__ == 'ReferenceType'
             and type(reference_type.__module__) is str
             and reference_type.__module__ == 'weakref')
    origin = tuple.__new__(_PayloadOrigin, (
        _DirectoryPayload, _RetirementMarker, _RetirementRecord,
        tuple(vars(_DirectoryPayload).get(name) for name in _FIELDS), reference_type,
        vars(reference_type).get('__call__'), vars(reference_type).get('__callback__')))
    return _origin_tail(origin)


def _payload_state_is_clear(state):
    """Identity-only checks: foreign entries never receive equality callbacks."""
    return (type(state) is list and len(state) == 3
            and state[0] is False and state[1] is False and state[2] is False)


def _marker_tail(owner, origin, marker, payload):
    """Held original allocation joins, not a current-slot nomination or receipt."""
    _origin_tail(origin)
    _require(type(marker) is origin.marker_type and marker.owner is owner
             and marker.origin is origin and type(payload) is origin.payload_type
             and type(marker.owner_link) is list and len(marker.owner_link) == 1
             and type(marker.marker_slot) is list and len(marker.marker_slot) == 1
             and marker.owner_link is not marker.marker_slot
             and marker.marker_slot[0] is marker
             and type(marker.reference) is origin.reference_type
             and origin.reference_callback.__get__(marker.reference, origin.reference_type) is None
             and type(marker.state) is list and len(marker.state) == 3
             and all(type(value) is bool for value in marker.state)
             and origin.reference_call(marker.reference) is payload)
    # Revalidate after the captured C weakref call, which is a profile boundary.
    # Do not compare lists: an injected foreign state value must never get __eq__.
    _require(type(marker.owner_link) is list and len(marker.owner_link) == 1
             and type(marker.marker_slot) is list and len(marker.marker_slot) == 1
             and marker.owner_link is not marker.marker_slot
             and marker.marker_slot[0] is marker
             and type(marker.state) is list and len(marker.state) == 3
             and type(marker.state[0]) is bool and type(marker.state[1]) is bool
             and type(marker.state[2]) is bool)
    return marker


def _allocate_directory_custody(owner, operation, consumer, origin, owner_link, marker_slot, unset):
    """Return actual marker/payload to a fixed caller before native admission.

    The caller must not store this returned pair or the payload in retained
    history: only the designated owner_link may strongly reach the payload.
    """
    _origin_tail(origin)
    _require(type(owner_link) is list and len(owner_link) == 1 and owner_link[0] is None
             and type(marker_slot) is list and len(marker_slot) == 1 and marker_slot[0] is None
             and owner_link is not marker_slot)
    payload = object.__new__(origin.payload_type)
    for index, descriptor in enumerate(origin.members):
        descriptor.__set__(payload, [unset if index == 0 else None])
    reference = origin.reference_type(payload)  # no weak-reference callback
    marker = tuple.__new__(origin.marker_type, (
        owner, operation, consumer, origin, owner_link, marker_slot, reference,
        [False, False, False]))
    _require(type(marker) is origin.marker_type and marker.owner is owner
             and marker.operation is operation and marker.consumer is consumer
             and marker.origin is origin and marker.owner_link is owner_link
             and marker.marker_slot is marker_slot and marker.reference is reference
             and type(marker.state) is list and _payload_state_is_clear(marker.state)
             and type(reference) is origin.reference_type
             and origin.reference_callback.__get__(reference, origin.reference_type) is None
             and origin.reference_call(reference) is payload
             and len(owner_link) == len(marker_slot) == 1
             and owner_link[0] is marker_slot[0] is None)
    try:
        owner_link[0] = payload
        marker_slot[0] = marker
        _marker_tail(owner, origin, marker, payload)
        _require(owner_link[0] is payload and _payload_state_is_clear(marker.state))
        return marker, payload
    except BaseException:
        if len(owner_link) == 1 and owner_link[0] is payload:
            owner_link[0] = None
        if len(marker_slot) == 1 and marker_slot[0] is marker:
            marker_slot[0] = None
        raise


def _directory_payload_cells(owner, origin, marker, payload):
    """Temporary held cells, never retain these outside the caller's lifetime."""
    _marker_tail(owner, origin, marker, payload)
    _require(marker.owner_link[0] is payload and _payload_state_is_clear(marker.state))
    cells = _PayloadCells(*(descriptor.__get__(payload, origin.payload_type)
                             for descriptor in origin.members))
    _require(all(type(cell) is list and len(cell) == 1 for cell in cells))
    _marker_tail(owner, origin, marker, payload)
    _require(marker.owner_link[0] is payload and _payload_state_is_clear(marker.state))
    # Rejoin the captured cells, rather than adopting a replacement from a later
    # descriptor lookup. A fixed native caller still has to hold these before IO.
    _require(all(descriptor.__get__(payload, origin.payload_type) is cell
                 for descriptor, cell in zip(origin.members, cells, strict=True)))
    _marker_tail(owner, origin, marker, payload)
    _require(marker.owner_link[0] is payload and _payload_state_is_clear(marker.state)
             and all(type(cell) is list and len(cell) == 1 for cell in cells))
    return cells


def _retire_directory_payload_data(owner, origin, marker, payload):
    """Detach held original memory only; outer caller proves actor/ended state.

    No payload contents are read, erased or adopted as native results. Foreign
    outer links and inner values remain untouched. This is not a native ACK.
    """
    record = None
    try:
        _marker_tail(owner, origin, marker, payload)
        _require(marker.state[1] is False)
        marker.state[0] = True
        detached = marker.owner_link[0] is payload
        if detached:
            marker.owner_link[0] = None
        else:
            marker.state[2] = True
        record = tuple.__new__(origin.record_type, (marker, detached, not detached))
        _marker_tail(owner, origin, marker, payload)
        _require(type(record) is origin.record_type and record.marker is marker
                 and type(record.detached) is bool and record.detached is detached
                 and type(record.unmatched_link) is bool and record.unmatched_link is (not detached)
                 and marker.state[0] is True and marker.state[1] is False
                 and ((detached and marker.owner_link[0] is None)
                      or (not detached and marker.owner_link[0] is not payload)))
        marker.state[1] = True
        return record
    except BaseException:  # noqa: S110 - never log private payload-bearing exceptions
        pass
    finally:
        payload = marker = origin = record = None
    raise ArtifactObservationError(owner) from None
