"""Completed signed RESULT local transfer proof after payload withdrawal.

The counted original write and native local resource closure are separate facts.
This check neither revives output bytes nor grants terminal/ACK/release authority.
"""
from __future__ import annotations

import asyncio

from .presentation_broker_cancel import BrokerCancellationOwner
from .presentation_broker_registry import _Record
from .presentation_broker_resources import BrokerReaderResources
from .presentation_broker_service import SocketChannel
from .presentation_cancel_budget import CancellationBudget
from .presentation_control_binding import PreparedControlBinding
from .presentation_credential_result import CredentialResultProducer, _ResultScope
from .presentation_credential_result_write import (
    _MINT,
    CredentialResultWriter,
    _ResultTransfer,
    _WriteScope,
)
from .presentation_jobs import OUTPUT_LIMIT, FrameError
from .presentation_readiness import SelectorWriteReadiness
from .presentation_remote_cleanup import _TASK


def _require(value):
    if value is not True:
        raise FrameError("BI1_SIGNED_RESULT_COMPLETED_REFUSED")


def metadata(writer):
    """Historical counted delivery and cleared bytes; no native effects."""
    _require(type(writer) is CredentialResultWriter and type(writer._scope_snapshot) is _WriteScope
             and writer._scope is writer._scope_snapshot)
    s = writer._scope_snapshot
    _require(type(writer._scope_cell) is tuple and len(writer._scope_cell) == 2
             and writer._scope_cell[0] is writer and writer._scope_cell[1] is s
             and type(s.result_scope) is _ResultScope
             and type(s.result_scope.refs) is tuple and len(s.result_scope.refs) == 19
             and type(s.result_scope.control) is BrokerCancellationOwner
             and s.result_scope.control._credential_result is s.producer
             and s.result_scope.control._credential_result_snapshot is s.producer
             and type(s.result_scope.refs[4]) is _Record
             and s.result_scope.refs[4].resources is s.result_scope.resources
             and s.result_scope.refs[4].resources_snapshot is s.result_scope.resources
             and type(s.producer) is CredentialResultProducer
             and s.producer._scope is s.result_scope
             and s.producer._scope_snapshot is s.result_scope
             and s.producer._writer is writer and s.producer._writer_snapshot is writer
             and s.producer._retired is True and s.producer._failed is False
             and s.producer._complete is True
             and s.producer._payload is None and s.producer._payload_snapshot is None
             and s.producer._frozen is None and s.producer._frozen_snapshot is None
             and type(s.channel) is SocketChannel and s.channel is s.result_scope.refs[14]
             and s.channel._credential_result_writer is writer
             and s.channel._credential_result_writer_snapshot is writer
             and s.channel._socket is s.sock and s.channel._socket_snapshot is s.sock
             and type(s.task) is _TASK and s.task is s.result_scope.refs[15]
             and type(s.raw) is bytes and 0 < len(s.raw) <= 2048
             and type(s.header) is bytes and 8 < len(s.header) <= 1032
             and type(s.length) is int and 4 <= s.length <= OUTPUT_LIMIT
             and type(s.digest) is str and len(s.digest) == 64
             and type(s.payload_sha) is str and len(s.payload_sha) == 64
             and writer._attempted is True and writer._complete is True
             and writer._active is False and writer._inflight is False
             and writer._failed is False and writer._unknown is False
             and writer._retired is True and writer._cancel_requested is False
             and writer._grammar_attempted is True
             and writer._waiter is writer._waiter_origin
             and (writer._waiter_origin is None or (
                 type(writer._waiter_origin) is SelectorWriteReadiness
                 and writer._waiter_origin._initialized is True
                 and writer._waiter_origin._unknown is False
                 and writer._waiter_origin._retired is True))
             and writer._payload is None and writer._payload_snapshot is None
             and s.channel._writing is False
             and type(writer._offset) is int and writer._offset is writer._offset_snapshot
             and writer._offset == len(s.raw) + len(s.header) + s.length)
    fact = writer._fact_snapshot
    _require(type(fact) is _ResultTransfer and fact.mint is _MINT
             and writer._fact is fact and fact.owner is writer and fact.scope is s
             and type(fact.count) is int and fact.count == writer._offset
             and type(writer._completion_cell) is tuple and len(writer._completion_cell) == 2
             and writer._completion_cell[0] is writer and writer._completion_cell[1] is fact)
    return fact


def current(writer):
    """Original service actor/current role plus historical successful transfer."""
    fact = metadata(writer)
    s, refs = fact.scope, fact.scope.result_scope.refs
    _require(asyncio.current_task() is s.task and _TASK.cancelling(s.task) == 0)
    control = s.result_scope.control
    binding = control._credential_binding_snapshot
    _require(type(binding) is PreparedControlBinding
             and PreparedControlBinding._creator_local(binding) is refs
             and type(s.result_scope.resources) is BrokerReaderResources)
    PreparedControlBinding.creator_material_current(binding)
    _require(metadata(writer) is fact)
    BrokerReaderResources._check(s.result_scope.resources)
    _require(metadata(writer) is fact
             and PreparedControlBinding._creator_local(binding) is refs
             and control._retired is False and control._failed is False
             and control._io_unknown is False
             and s.result_scope.resources._normal_complete is True
             and s.result_scope.resources._invalidated is False
             and s.result_scope.resources._poisoned is False)
    work_end, cause, end, broken = CancellationBudget.inspect(refs[17])
    _require(type(work_end) is int and work_end == refs[4].deadline_ns
             and cause is None and end is None and broken is False)
    _require(PreparedControlBinding._creator_local(binding) is refs
             and metadata(writer) is fact
             and control._retired is False and control._failed is False
             and control._io_unknown is False
             and s.result_scope.resources._normal_complete is True
             and s.result_scope.resources._invalidated is False
             and s.result_scope.resources._poisoned is False)
    return fact
