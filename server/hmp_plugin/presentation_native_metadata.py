"""Unwired original metadata intent/result preparation; no syscall dispatcher."""
from __future__ import annotations

from typing import NamedTuple

from .presentation_startup_artifacts import (
    _native_declared_metadata_plan_tail,
    _native_work_origin_tail,
    _NativeMetadataResource,
    _prepare_native_metadata_resource,
    _require,
)


class _MetadataResult(NamedTuple):
    attempt: list
    consumer: list
    unset: object
    raw: list
    category: list
    snapshot: list
    acknowledged: list
    envelope: list

    def __repr__(self):
        return '<MetadataResult unqualified original DATA redacted>'


class _MetadataOperation(NamedTuple):
    owner: object
    resource: _NativeMetadataResource
    registration: object
    ledger: object
    phase: object
    native: object
    context: tuple
    operation: int
    callee: object
    arguments: tuple
    index: int
    attempts: list
    budget: tuple
    result: _MetadataResult
    state: list
    ended: list

    def __repr__(self):
        return '<MetadataOperation unqualified original intent redacted>'


def _resource_tail(owner, resource):
    """Rejoin the held actual resource; never adopt a current replacement."""
    _require(type(resource) is _NativeMetadataResource and resource.owner is owner
             and type(resource.site) is tuple and len(resource.site) == 3
             and type(resource.site[0]) is int and resource.site[0] in (3, 4)
             and type(resource.arguments) is tuple
             and len(resource.arguments) == (2 if resource.site[0] == 3 else 1))
    metadata = _native_declared_metadata_plan_tail(owner, resource.registration,
                                                  resource.held_walk)
    _require(metadata is resource.metadata and metadata.progress[0] is resource.ordinal
             and metadata.definitions[resource.ordinal] is resource.site)
    actual = _prepare_native_metadata_resource(
        owner, resource.registration, resource.held_walk, resource.descriptor,
        resource.arguments[0] if resource.site[0] == 3 else None)
    _require(actual.metadata is resource.metadata and actual.site is resource.site
             and actual.ordinal is resource.ordinal and actual.descriptor is resource.descriptor
             and all(before is after for before, after in
                     zip(resource.arguments, actual.arguments, strict=True)))
    return resource


def _prepare_metadata_operation(owner, resource):
    """Preallocate original result cells and fixed call DATA without a debit.

    The future fixed producer must retain this actual allocation across admission,
    bind its independently held one-use policy consumer, and recheck every budget,
    resource and phase join before effects. This preparation is not admission.
    """
    _resource_tail(owner, resource)
    registration = resource.registration
    native, ledger, phase = (registration.native_origin, registration.native_ledger,
                             registration.native_phase)
    _native_work_origin_tail(owner, registration, native)
    _require(ledger.phase is phase and type(phase.current) is list
             and len(phase.current) == 1 and phase.current[0] is phase.idle
             and type(phase.result) is list and len(phase.result) == 1
             and phase.result[0] is None and type(ledger.inflight) is list
             and len(ledger.inflight) == 1 and ledger.inflight[0] is None
             and type(ledger.failed) is list and len(ledger.failed) == 1
             and ledger.failed[0] is False)
    attempts, counts = ledger.attempts, ledger.counts
    _require(type(attempts) is list and len(attempts) < 1048576
             and type(counts) is list and len(counts) == 2
             and all(type(value) is int for value in counts)
             and 0 <= counts[0] < 1048576
             and 0 <= counts[1] < 1048576 - counts[0])
    used, reserved, index = counts[0], counts[1], len(attempts)
    operation = resource.site[0]
    callee = native.operations[operation]
    unset = object()
    result = _MetadataResult([None], [None], unset, [unset], [None], [None], [None], [None])
    intent = _MetadataOperation(owner, resource, registration, ledger, phase, native,
                                registration.context, operation, callee, resource.arguments,
                                index, attempts, (counts, used, reserved, used + 1), result,
                                [False, False, False], [False])
    result.attempt[0] = intent
    _require(_resource_tail(owner, resource) is resource
             and ledger.attempts is attempts and len(attempts) == index
             and ledger.counts is counts and counts[0] is used and counts[1] is reserved
             and phase.current[0] is phase.idle and phase.result[0] is None
             and ledger.inflight[0] is None and ledger.failed[0] is False
             and native.operations[operation] is callee)
    return intent
