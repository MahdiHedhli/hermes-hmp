"""Authenticated TERMINAL/2 frame on the original read owner.

Only bounded frame/hash consistency. Domain claim acceptance, cleanup-budget
inheritance, ACK, lifecycle/native release and publication remain separate.
"""
from __future__ import annotations

from . import presentation_credential_cleanup_frame as core
from . import presentation_credential_cleanup_terminal as auth_read
from .presentation_broker_codec import BrokerBinding
from .presentation_credential_cleanup_notice import SignedReadNotice
from .presentation_credential_frame_discard import CommittedFrameDiscard
from .presentation_jobs import FrameError


def _require(value):
    if value is not True:
        raise FrameError("BI1_NATIVE_TERMINAL_FRAME_REFUSED")


def _scope(native, read_scope):
    auth = auth_read._scope(native, read_scope)
    frame = native._terminal_frame_origin
    _require(type(frame) is core._Frame and native._terminal_frame is frame
             and type(native._terminal_frame_allocation) is tuple
             and len(native._terminal_frame_allocation) == 2
             and native._terminal_frame_allocation[0] is native
             and native._terminal_frame_allocation[1] is frame
             and type(frame.scope) is core._FrameScope and frame.scope is frame.scope_origin
             and type(frame.scope_cell) is tuple and len(frame.scope_cell) == 2
             and frame.scope_cell[0] is frame and frame.scope_cell[1] is frame.scope)
    s = frame.scope
    _require(
        s.native is native
        and s.read_scope is read_scope
        and s.auth is auth
        and auth.complete is True
        and auth.finish_returned is True
        and type(s.receipt) is auth_read._AuthFact
        and s.receipt is auth.fact
        and s.receipt.scope is auth.scope
        and type(auth.fact_cell) is tuple
        and len(auth.fact_cell) == 2
        and auth.fact_cell[0] is auth
        and auth.fact_cell[1] is s.receipt
        and type(auth.checked_cell) is tuple
        and len(auth.checked_cell) == 2
        and auth.checked_cell[0] is auth
        and auth.checked_cell[1] is s.receipt.checked
        and type(s.binding) is BrokerBinding
        and s.binding
        is read_scope.idle_scope[0].reservation.capture.scope.write_scope.intent.binding
        and type(s.phase) is str
        and s.phase == "TERMINAL"
        and type(s.sequence) is int
        and s.sequence == 2
        and type(s.outer) is bytes
        and s.outer == b""
        and type(s.parser) is CommittedFrameDiscard
        and not any(k in vars(s.parser) for k in ("feed", "finish", "needed"))
        and frame.parser is s.parser
        and frame.parser_origin is s.parser
        and type(frame.parser_cell) is tuple
        and len(frame.parser_cell) == 2
        and frame.parser_cell[0] is frame
        and frame.parser_cell[1] is s.parser
        and all(
            type(v) is bool
            for v in (
                frame.initialized,
                frame.failed,
                frame.finish_attempted,
                frame.finish_returned,
                frame.complete,
                frame.outer_attempted,
            )
        )
        and frame.failed is False
    )
    return frame


def _current_work(native, s):
    frame = _scope(native, s)
    held_scope = frame.scope
    stage = auth_read._current(native, s)
    _require(_scope(native, s) is frame and frame.scope is held_scope
             and stage is held_scope.auth and stage.fact is held_scope.receipt)
    if frame.initialized:
        seal = core._ledger(frame)
        if frame.finish_returned:
            core._finished(frame, seal)
        else:
            core._same(core._snapshot(frame, held_scope=held_scope), seal)
        _require(_scope(native, s) is frame and frame.scope is held_scope
                 and core._ledger(frame) is seal)
    return frame


def start(native):
    from .presentation_credential_cleanup_read import NativeCleanupRead

    s = NativeCleanupRead._origin(native)
    SignedReadNotice._actor(s.notice)
    auth = auth_read._scope(native, s)
    _require(native._terminal_frame is None and native._terminal_frame_origin is None
             and native._terminal_frame_allocation is None
             and auth.complete is True and auth.finish_returned is True
             and type(auth.fact) is auth_read._AuthFact
             and type(auth.fact_cell) is tuple and len(auth.fact_cell) == 2
             and auth.fact_cell[0] is auth and auth.fact_cell[1] is auth.fact
             and auth.fact.scope is auth.scope
             and type(auth.fact.total_received) is int and auth.fact.total_received > 0)
    receipt, total = auth.fact, auth.fact.total_received
    parser = CommittedFrameDiscard.__new__(CommittedFrameDiscard)
    frame = core._Frame.__new__(core._Frame)
    held_scope = core._FrameScope(native, s, auth, receipt,
        s.idle_scope[0].reservation.capture.scope.write_scope.intent.binding,
        "TERMINAL", 2, b"", parser)
    frame.scope = frame.scope_origin = held_scope
    frame.scope_cell = (frame, held_scope)
    frame.parser = frame.parser_origin = parser
    frame.parser_cell = (frame, parser)
    frame.initialized = frame.failed = frame.finish_attempted = False
    frame.finish_returned = frame.complete = frame.outer_attempted = False
    frame.ledger = frame.ledger_origin = frame.ledger_cell = None
    frame.step = frame.step_origin = frame.step_cell = frame.active_step_cell = None
    frame.result = frame.result_origin = frame.result_cell = frame.done = frame.done_cell = None
    frame.finish_cell = None
    native._terminal_frame = native._terminal_frame_origin = frame
    native._terminal_frame_allocation = (native, frame)
    try:
        _current_work(native, s)
        CommittedFrameDiscard.__init__(parser, receipt.checked, binding=held_scope.binding,
                                      phase="TERMINAL", sequence=2)
        frame.outer_attempted = True  # empty by construction; no prefix is replayed
        seal = core._snapshot(frame, held_scope=held_scope)
        ledger = core._Ledger(0, total, total, seal)
        frame.ledger = frame.ledger_origin = ledger
        frame.ledger_cell = (frame, ledger)
        frame.initialized = True
        _current_work(native, s)
        return held_scope
    except BaseException:
        core._fail(native, s, frame)
    raise FrameError("BI1_NATIVE_TERMINAL_FRAME_START_UNKNOWN") from None


def read_next(native):
    return core._read_frame_next(native, core._TERMINAL_FRAME)


def finish(native):
    return core._finish_frame(native, core._TERMINAL_FRAME)


def current_for_cleanup(native):
    return core._current_frame_for_cleanup(native, core._TERMINAL_FRAME)


def retire(native):
    cell = native._terminal_frame_allocation
    if (type(cell) is tuple and len(cell) == 2 and cell[0] is native
            and type(cell[1]) is core._Frame):
        cell[1].failed = True
        core._wipe(cell[1])
