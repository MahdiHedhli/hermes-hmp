"""Owned selector-readiness notification only; never recv, authority or closure.

The original protocol task must separately validate its mode/budget, receive and
commit cursor progress without another await. No task is created and no payload is captured.
"""
from __future__ import annotations

import asyncio
import os
import select
import selectors
import socket
import stat
import sys
import threading
import time
from collections import deque
from types import MethodType
from typing import NamedTuple

from .presentation_cancel_budget import MAX_NS
from .presentation_jobs import FrameError

_LOOP = asyncio.SelectorEventLoop
_FUTURE = asyncio.Future
_TASK = asyncio.Task
_HANDLE = asyncio.Handle
_BACKEND = select.kqueue if sys.platform == "darwin" else getattr(select, "epoll", None)
_FILENO = socket.socket.fileno
_NOW = time.monotonic_ns
_ADD_READER = _LOOP._add_reader
_REMOVE_READER = _LOOP._remove_reader
_LOOP_METHODS = {name: getattr(_LOOP, name) for name in (
    "_add_reader", "_remove_reader", "_check_closed", "is_closed", "get_debug",
    "call_soon", "_call_soon", "call_at", "time", "_timer_handle_cancelled",
    "_check_thread", "_check_callback")}
_SELECTOR_METHODS = {name: getattr(selectors.DefaultSelector, name) for name in (
    "get_key", "register", "modify", "unregister", "_fileobj_lookup")}
_CANCEL_HANDLE = _HANDLE.cancel


def _require(value):
    if value is not True:
        raise FrameError("BI1_READINESS_REFUSED")


def _initialize_future(future, loop):
    _FUTURE.__init__(future, loop=loop)


def _install_reader(loop, fd, callback, token):
    return _ADD_READER(loop, fd, callback, token)


def _remove_reader(loop, fd):
    return _REMOVE_READER(loop, fd)


def _fd_identity(fd):
    row = os.fstat(fd)
    return row.st_dev, row.st_ino, stat.S_IFMT(row.st_mode)


def _scheduler_safe(loop):
    _require(type(loop) is _LOOP and type(loop._closed) is bool and loop._closed is False
             and type(loop._debug) is bool and type(loop._ready) is deque
             and type(loop._scheduled) is list and type(loop._timer_cancelled_count) is int)
    for name in ("call_soon", "_call_soon", "call_at", "time", "_timer_handle_cancelled",
                 "_check_closed", "get_debug", "_check_thread", "_check_callback"):
        method = getattr(loop, name)
        _require(type(method) is MethodType and method.__self__ is loop
                 and method.__func__ is _LOOP_METHODS[name])


def _dispatch_safe(loop, selector):
    # Exact concrete class methods still redispatch internally. Fence those
    # mutable instance entry points BEFORE they can affect another registration.
    _scheduler_safe(loop)
    _require(type(loop) is _LOOP and type(selector) is selectors.DefaultSelector
             and type(loop._closed) is bool and loop._closed is False
             and type(loop._debug) is bool and _HANDLE.cancel is _CANCEL_HANDLE
             and type(selector._fd_to_key) is dict)
    for owner, methods in ((loop, _LOOP_METHODS), (selector, _SELECTOR_METHODS)):
        for name, function in methods.items():
            method = getattr(owner, name)
            _require(type(method) is MethodType and method.__self__ is owner
                     and method.__func__ is function)


class _Scope(NamedTuple):
    sock: object
    fd: int
    identity: tuple
    loop: object
    selector: object
    selector_keys: dict
    backend: object
    backend_fd: int
    backend_identity: tuple
    task: object
    context: tuple

    def __repr__(self):
        return "<ReadinessScope redacted>"


class ReadinessAcquisitionError(FrameError):
    def __init__(self, owner):
        super().__init__("BI1_READINESS_ACQUISITION_UNKNOWN")
        self.owner = owner


class SelectorReadiness:
    """One borrowed FD/read-slot attempt, retained by caller before initialization."""

    def __init__(self, sock):
        _require(type(self) is SelectorReadiness)
        self._scope = self._scope_snapshot = self._origin_scope = None
        self._future = self._future_snapshot = self._future_origin = None
        self._future_initialized = False
        self._callback = self._callback_snapshot = SelectorReadiness._readable.__get__(
            self, SelectorReadiness)
        self._token = self._token_snapshot = object()
        self._args = self._args_snapshot = (self._token,)
        self._handle = self._handle_snapshot = None
        self._handle_args = self._handle_args_snapshot = None
        self._initialized = self._attempted = self._unknown = self._retired = False
        try:
            loop, task = asyncio.get_running_loop(), asyncio.current_task()
            _require(type(sock) is socket.socket and type(loop) is _LOOP and type(task) is _TASK
                     and _BACKEND is not None
                     and asyncio.BaseEventLoop.get_task_factory(loop) is None)
            selector = loop._selector
            _require(type(selector) is selectors.DefaultSelector
                     and type(selector._selector) is _BACKEND)
            _dispatch_safe(loop, selector)  # before Future initialization can call loop hooks
            fd = _FILENO(sock)
            _require(type(fd) is int and fd >= 0 and os.get_blocking(fd) is False
                     and sock.gettimeout() == 0.0 and os.get_inheritable(fd) is False)
            identity = _fd_identity(fd)
            _require(stat.S_ISSOCK(identity[2]))
            backend = selector._selector
            backend_fd = _BACKEND.fileno(backend)
            self._scope = self._scope_snapshot = self._origin_scope = _Scope(
                sock, fd, identity, loop, selector, selector._fd_to_key, backend, backend_fd,
                _fd_identity(backend_fd), task,
                (os.getpid(), threading.get_ident()))
            self._future = self._future_snapshot = self._future_origin = _FUTURE.__new__(_FUTURE)
            _initialize_future(self._future_snapshot, loop)
            self._future_initialized = True
            self._initialized = True
            SelectorReadiness._guard(self)
        except BaseException:
            self._unknown = True
            raise ReadinessAcquisitionError(self) from None

    def __repr__(self):
        return "<SelectorReadiness no-payload redacted>"

    def _guard(self, *, actor=True):
        _require(type(self) is SelectorReadiness and type(actor) is bool)
        s = self._scope
        _require(self._initialized is True and type(s) is _Scope
                 and s is self._scope_snapshot and s is self._origin_scope
                 and type(s.sock) is socket.socket and type(s.fd) is int
                 and type(s.identity) is tuple and len(s.identity) == 3
                 and all(type(v) is int for v in s.identity)
                 and type(s.loop) is _LOOP and asyncio.get_running_loop() is s.loop
                 and s.loop._selector is s.selector
                 and type(s.selector) is selectors.DefaultSelector
                 and s.selector._selector is s.backend and type(s.backend) is _BACKEND
                 and type(s.selector_keys) is dict and s.selector._fd_to_key is s.selector_keys
                 and type(s.backend_fd) is int
                 and type(s.backend_identity) is tuple and len(s.backend_identity) == 3
                 and all(type(v) is int for v in s.backend_identity)
                 and type(s.context) is tuple and len(s.context) == 2
                 and all(type(v) is int for v in s.context)
                 and s.context == (os.getpid(), threading.get_ident())
                 and type(s.task) is _TASK and (not actor or asyncio.current_task() is s.task)
                 and self._future is self._future_snapshot and self._future is self._future_origin
                 and type(self._future) is _FUTURE
                 and self._future_initialized is True
                 and self._callback is self._callback_snapshot
                 and type(self._callback) is MethodType and self._callback.__self__ is self
                 and self._callback.__func__ is SelectorReadiness._readable
                 and time.monotonic_ns is _NOW
                 and self._token is self._token_snapshot and type(self._token) is object
                 and self._args is self._args_snapshot and type(self._args) is tuple
                 and len(self._args) == 1 and self._args[0] is self._token
                 and self._handle is self._handle_snapshot
                 and self._handle_args is self._handle_args_snapshot
                 and (self._handle_args is None or (type(self._handle_args) is tuple
                      and len(self._handle_args) == 1
                      and self._handle_args[0] is self._token_snapshot))
                 and all(type(v) is bool for v in (
                     self._attempted, self._unknown, self._retired)))

    def _native(self, *, actor=True):
        SelectorReadiness._guard(self, actor=actor)
        s = self._scope_snapshot
        _dispatch_safe(s.loop, s.selector)
        _require(_FILENO(s.sock) == s.fd and _fd_identity(s.fd) == s.identity
                 and os.get_blocking(s.fd) is False and s.sock.gettimeout() == 0.0
                 and os.get_inheritable(s.fd) is False
                 and _BACKEND.fileno(s.backend) == s.backend_fd
                 and _fd_identity(s.backend_fd) == s.backend_identity)
        SelectorReadiness._guard(self, actor=actor)

    def _slots(self):
        s = self._scope_snapshot
        try:
            key = _SELECTOR_METHODS["get_key"](s.selector, s.fd)
        except KeyError:
            return None, None
        _require(type(key) is selectors.SelectorKey and type(key.fd) is int and key.fd == s.fd
                 and type(key.events) is int and key.events in (1, 2, 3)
                 and ((type(key.fileobj) is int and key.fileobj == s.fd)
                      or key.fileobj is s.sock)
                 and type(key.data) is tuple and len(key.data) == 2)
        return key.data

    def _owned(self, handle):
        _require(type(handle) is _HANDLE and handle._loop is self._scope_snapshot.loop
                 and handle._callback is self._callback_snapshot
                 and type(handle._args) is tuple and len(handle._args) == 1
                 and handle._args[0] is self._token_snapshot
                 and type(handle._cancelled) is bool and handle._cancelled is False
                 and (self._handle_snapshot is None or handle is self._handle_snapshot)
                 and (self._handle_args_snapshot is None
                      or handle._args is self._handle_args_snapshot))

    def _future_effects_safe(self):
        # Failure handling cannot redispatch through a scheduler that just failed
        # its fence, or touch a substituted Future/foreign event-loop thread.
        origin = self._origin_scope
        if (type(origin) is not _Scope or self._future_initialized is not True
                or type(self._future_origin) is not _FUTURE
                or origin.context != (os.getpid(), threading.get_ident())):
            return False
        try:
            _require(asyncio.get_running_loop() is origin.loop)
            _scheduler_safe(origin.loop)
            return True
        except BaseException:
            self._unknown = True
            return False

    def _readable(self, token):
        try:
            SelectorReadiness._native(self, actor=False)
            _require(token is self._token_snapshot and self._attempted is True
                     and self._retired is False and self._unknown is False)
            handle, _ = SelectorReadiness._slots(self)
            SelectorReadiness._owned(self, handle)
            if not _FUTURE.done(self._future_snapshot):
                _FUTURE.set_result(self._future_snapshot, None)  # no recv, payload or authority
        except BaseException:
            self._unknown = True
            if (SelectorReadiness._future_effects_safe(self)
                    and not _FUTURE.done(self._future_origin)):
                _FUTURE.set_exception(self._future_origin,
                                         FrameError("BI1_READINESS_CALLBACK_UNKNOWN"))

    def _retire(self):
        # Foreign actors cannot even cancel this owner's metadata Future.
        _require(type(self) is SelectorReadiness)
        origin = self._origin_scope
        _require(type(origin) is _Scope and origin.context == (os.getpid(), threading.get_ident())
                 and asyncio.get_running_loop() is origin.loop
                 and asyncio.current_task() is origin.task)
        # Retire only the exact local subscription; this is not deadline/operation closure.
        try:
            SelectorReadiness._native(self)
            handle, writer = SelectorReadiness._slots(self)
            SelectorReadiness._owned(self, handle)
            # Includes a positively observed registration after partial native add.
            self._handle = self._handle_snapshot = handle
            self._handle_args = self._handle_args_snapshot = handle._args
            s = self._scope_snapshot
            _require(_remove_reader(s.loop, s.fd) is True)
            SelectorReadiness._native(self)
            read_after, write_after = SelectorReadiness._slots(self)
            _require(read_after is None and write_after is writer)
            self._retired = True
        except BaseException:
            self._unknown = True
        finally:
            # Do not touch an ambiguously initialized Future.
            if SelectorReadiness._future_effects_safe(self):
                future = self._future_origin
                if not _FUTURE.done(future):
                    _FUTURE.cancel(future)
                elif not _FUTURE.cancelled(future):
                    # Observe the constant private refusal, never an application payload.
                    _FUTURE.exception(future)

    async def wait(self, end_ns):
        try:
            SelectorReadiness._native(self)
        except BaseException:
            self._unknown = True
            raise FrameError("BI1_READINESS_SCOPE_UNKNOWN") from None
        _require(type(end_ns) is int and 0 < end_ns <= MAX_NS and _NOW() < end_ns
                 and self._attempted is False
                 and self._unknown is False and self._retired is False)
        current, _ = SelectorReadiness._slots(self)
        _require(current is None)  # never replace another reader
        self._attempted = True  # registration intent before the possibly partial native add
        try:
            s = self._scope_snapshot
            _install_reader(s.loop, s.fd, self._callback_snapshot, self._token_snapshot)
            SelectorReadiness._native(self)
            handle, _ = SelectorReadiness._slots(self)
            SelectorReadiness._owned(self, handle)
            self._handle = self._handle_snapshot = handle
            self._handle_args = self._handle_args_snapshot = handle._args
            async with asyncio.timeout_at(end_ns / 1_000_000_000):
                value = await asyncio.shield(self._future_snapshot)
            SelectorReadiness._native(self)
            _require(value is None and self._unknown is False)
        except (asyncio.CancelledError, TimeoutError):
            raise
        except BaseException:
            self._unknown = True
            raise FrameError("BI1_READINESS_WAIT_UNKNOWN") from None
        finally:
            SelectorReadiness._retire(self)
            if not self._retired or self._unknown:
                raise FrameError("BI1_READINESS_RETIREMENT_UNKNOWN") from None
