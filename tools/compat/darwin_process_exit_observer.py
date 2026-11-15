"""Fixture-only kernel process-exit observation; no signal/reap/closure authority.

Caller has separately verified the job/peer/nonce and retains the target unreaped
until registration. Exclusive descriptor ownership and trusted native primitives
are required. An event timestamp is when read, never the kernel exit time.
"""

from __future__ import annotations

import errno
import os
import select
import sys
import threading
import time
from dataclasses import dataclass

_QTYPE = getattr(select, "kqueue", None)
_ETYPE = getattr(select, "kevent", None)
_QMAKE = _QTYPE
_QFD = None if _QTYPE is None else _QTYPE.fileno
_QCONTROL = None if _QTYPE is None else _QTYPE.control
_QCLOSE = None if _QTYPE is None else _QTYPE.close
_QCLOSED = None if _QTYPE is None else _QTYPE.closed
# Inspected Darwin SDK sys/event.h; Python does not expose EV_RECEIPT.
_RECEIPT = 0x0040
_PROC, _EXIT = -5, 0x80000000
_ADD, _ENABLE, _ONESHOT, _CLEAR, _ERROR, _EOF = 1, 4, 16, 32, 0x4000, 0x8000
_REG_FLAGS = _ADD | _ENABLE | _ONESHOT | _RECEIPT
_EXIT_FLAGS = _REG_FLAGS | _CLEAR | _EOF


class ObserverRefusedError(RuntimeError):
    pass


class ObserverAcquisitionError(ObserverRefusedError):
    def __init__(self, owner: ProcessExitObserver, code: str):
        super().__init__(code)
        self.failed_owner = owner


@dataclass(frozen=True)
class ExitEventObservation:
    pid: int
    observed_at_ns: int


class _PreexistingExitError(ObserverRefusedError):
    pass


def _require(value: bool) -> None:
    if value is not True:
        raise ObserverRefusedError("process_exit_observation_refused")


def _api() -> None:
    _require(sys.platform == "darwin" and type(_QTYPE) is type and type(_ETYPE) is type)
    expected = {"KQ_FILTER_PROC": _PROC, "KQ_NOTE_EXIT": _EXIT, "KQ_EV_ADD": _ADD,
                "KQ_EV_ENABLE": _ENABLE, "KQ_EV_ONESHOT": _ONESHOT,
                "KQ_EV_CLEAR": _CLEAR, "KQ_EV_ERROR": _ERROR, "KQ_EV_EOF": _EOF}
    for name, value in expected.items():
        observed = getattr(select, name, None)
        _require(type(observed) is int and observed == value)


def _identity(fd: int) -> tuple[int, int, int, int]:
    _require(type(fd) is int and fd >= 0)
    row = os.fstat(fd)
    return fd, row.st_dev, row.st_ino, row.st_mode


class ProcessExitObserver:
    def __init__(self, binding: object, pid: int, *, observe_end_ns: int, cleanup_end_ns: int):
        self._binding = self._binding_snapshot = binding
        self._pid = self._pid_snapshot = pid
        self._observe_end = self._observe_snapshot = observe_end_ns
        self._cleanup_end = self._cleanup_snapshot = cleanup_end_ns
        self._context = self._context_snapshot = (os.getpid(), os.geteuid())
        self._primitives = self._primitive_snapshot = (
            _QTYPE, _ETYPE, _QMAKE, _QFD, _QCONTROL, _QCLOSE, _QCLOSED
        )
        self._queue = self._queue_snapshot = None
        self._fd = self._fd_snapshot = None
        self._registered = self._eligible = self._work_refused = False
        self._resource_uncertain = self._close_attempted = self._closed_known = False
        self._integrity_lost = False
        self._close_fact = self._close_fact_snapshot = None
        self._fact = self._fact_snapshot = self._fact_values = None
        self._cookie = self._cookie_snapshot = (
            int.from_bytes(os.urandom(8), "big") % ((1 << 63) - 1) + 1
        )
        self._lock = threading.Lock()
        self._lock.acquire()
        try:
            now = time.monotonic_ns()
            _require(binding is not None and type(pid) is int and 1 < pid < (1 << 31)
                     and pid != self._context[0])
            _require(type(observe_end_ns) is int and type(cleanup_end_ns) is int
                     and now < observe_end_ns <= cleanup_end_ns <= now + 20_000_000_000)
            _api()
            _require(time.monotonic_ns() < self._observe_end)
            queue = _QMAKE()
            self._queue = self._queue_snapshot = queue  # retain before methods/registration
            self._metadata(self._binding_snapshot)
            _require(type(queue) is _QTYPE)
            closed = _QCLOSED.__get__(queue, _QTYPE)
            self._metadata(self._binding_snapshot)
            _require(closed is False)
            fd = _QFD(queue)
            self._metadata(self._binding_snapshot)
            _require(type(fd) is int and fd >= 0)
            identity = _identity(fd)
            self._metadata(self._binding_snapshot)
            _require(type(identity) is tuple and len(identity) == 4
                     and all(type(v) is int and v >= 0 for v in identity))
            self._fd = self._fd_snapshot = identity
            self._held()
            _require(time.monotonic_ns() < self._observe_end)
            change = _ETYPE(pid, filter=_PROC, flags=_REG_FLAGS, fflags=_EXIT, udata=self._cookie)
            rows = _QCONTROL(queue, [change], 1, 0)
            self._held()
            _require(time.monotonic_ns() < self._observe_end)
            _require(type(rows) is list and len(rows) == 1)
            ident, filt, flags, fflags, data, cookie = self._row(rows[0])
            self._bindings(self._binding_snapshot)
            _require(ident == pid and filt == _PROC and cookie == self._cookie)
            _require(flags & _ERROR == _ERROR and flags & ~(_REG_FLAGS | _ERROR) == 0
                     and data == 0 and fflags in (0, _EXIT))
            self._registered = True
            # A successful receipt includes requested NOTE_EXIT; it is NOT exit.
            if self._read_exit():
                self._work_refused = True
                raise _PreexistingExitError("preexisting_process_exit")
            _require(time.monotonic_ns() < self._observe_end)
            self._eligible = True
        except _PreexistingExitError as error:
            raise ObserverAcquisitionError(self, str(error)) from None
        except BaseException:
            self._resource_uncertain = self._work_refused = True
            raise ObserverAcquisitionError(self, "process_exit_registration_unknown") from None
        finally:
            self._lock.release()

    def _poison_integrity(self) -> None:
        self._integrity_lost = self._resource_uncertain = self._work_refused = True
        self._eligible = False

    def _metadata(self, binding: object) -> None:
        try:
            self._metadata_native(binding)
        except BaseException:
            self._poison_integrity()
            raise ObserverRefusedError("process_exit_integrity_lost") from None

    def _metadata_native(self, binding: object) -> None:
        _require(self._integrity_lost is False)
        _require(binding is not None and binding is self._binding_snapshot
                 and self._binding is self._binding_snapshot)
        _require(type(self._context_snapshot) is tuple and len(self._context_snapshot) == 2
                 and all(type(v) is int for v in self._context_snapshot))
        _require(self._context is self._context_snapshot
                 and (os.getpid(), os.geteuid()) == self._context_snapshot)
        _require(type(self._pid) is int and self._pid is self._pid_snapshot
                 and 1 < self._pid < (1 << 31) and self._pid != self._context_snapshot[0])
        _require(type(self._cookie) is int and self._cookie is self._cookie_snapshot
                 and 0 < self._cookie < (1 << 63))
        _require(type(self._observe_end) is int and self._observe_end is self._observe_snapshot
                 and type(self._cleanup_end) is int and self._cleanup_end is self._cleanup_snapshot)
        _require(type(self._primitive_snapshot) is tuple and len(self._primitive_snapshot) == 7
                 and self._primitives is self._primitive_snapshot)
        _require(all(a is b for a, b in zip(
            (_QTYPE, _ETYPE, _QMAKE, _QFD, _QCONTROL, _QCLOSE, _QCLOSED),
            self._primitive_snapshot, strict=True)))
        _require(all(type(v) is bool for v in (self._registered, self._eligible,
                 self._work_refused, self._resource_uncertain, self._close_attempted,
                 self._closed_known, self._integrity_lost)))
        _require(not self._eligible or (self._registered and not self._work_refused))
        _require(self._fact is None or self._registered)
        _require(not self._closed_known or (self._close_attempted
                 and type(self._close_fact) is object
                 and self._close_fact is self._close_fact_snapshot))
    def _bindings(self, binding: object) -> None:
        self._metadata(binding)
        try:
            self._descriptor_bindings()
        except BaseException:
            self._poison_integrity()
            raise ObserverRefusedError("process_exit_descriptor_drift") from None

    def _descriptor_bindings(self) -> None:
        _require(self._queue is self._queue_snapshot and type(self._queue) is _QTYPE)
        _require(type(self._fd_snapshot) is tuple and len(self._fd_snapshot) == 4
                 and all(type(v) is int and v >= 0 for v in self._fd_snapshot)
                 and self._fd is self._fd_snapshot)

    def _held(self) -> None:
        try:
            self._bindings(self._binding_snapshot)
            closed = _QCLOSED.__get__(self._queue, _QTYPE)
            self._bindings(self._binding_snapshot)
            _require(closed is False)
            fd = _QFD(self._queue)
            self._bindings(self._binding_snapshot)
            _require(type(fd) is int and fd == self._fd_snapshot[0])
            identity = _identity(fd)
            self._bindings(self._binding_snapshot)
            _require(type(identity) is tuple and len(identity) == 4
                     and all(type(v) is int for v in identity) and identity == self._fd_snapshot)
            inheritable = os.get_inheritable(fd)
            self._bindings(self._binding_snapshot)
            _require(inheritable is False)
        except BaseException:
            self._poison_integrity()
            raise ObserverRefusedError("process_exit_handle_integrity_lost") from None

    def _row(self, event: object) -> tuple:
        _require(type(event) is _ETYPE)
        row = (event.ident, event.filter, event.flags, event.fflags, event.data, event.udata)
        _require(all(type(v) is int for v in row))
        return row

    def _read_exit(self) -> bool:
        try:
            return self._read_exit_native()
        except BaseException:
            self._resource_uncertain = self._work_refused = True
            self._eligible = False
            raise ObserverRefusedError("process_exit_io_unknown") from None

    def _read_exit_native(self) -> bool:
        self._held()
        rows = _QCONTROL(self._queue, None, 1, 0)
        self._held()
        _require(type(rows) is list and len(rows) <= 1)
        if not rows:
            return False
        ident, filt, flags, fflags, _data, cookie = self._row(rows[0])
        self._bindings(self._binding_snapshot)
        _require(ident == self._pid and filt == _PROC and cookie == self._cookie)
        _require(flags & _ERROR == 0 and flags & ~_EXIT_FLAGS == 0
                 and flags & _EOF == _EOF and fflags == _EXIT)
        _require(self._fact is None)  # one-shot registration; never re-register
        observed_at = time.monotonic_ns()
        self._bindings(self._binding_snapshot)
        _require(type(observed_at) is int and observed_at >= 0)
        self._fact = self._fact_snapshot = ExitEventObservation(self._pid, observed_at)
        self._fact_values = (self._fact.pid, self._fact.observed_at_ns)
        self._bindings(self._binding_snapshot)
        return True

    def _enter(self, binding: object) -> None:
        if self._binding is not self._binding_snapshot:
            self._poison_integrity()
            raise ObserverRefusedError("process_exit_binding_drift")
        _require(binding is not None and binding is self._binding_snapshot)
        if not self._lock.acquire(blocking=False):
            self._poison_integrity()
            raise ObserverRefusedError("process_exit_observer_reentry")
        try:
            self._bindings(binding)
        except BaseException:
            self._poison_integrity()
            self._lock.release()
            raise

    def _known_fact(self) -> ExitEventObservation:
        _require(type(self._fact) is ExitEventObservation and self._fact is self._fact_snapshot)
        _require(type(self._fact_values) is tuple and len(self._fact_values) == 2
                 and all(type(v) is int for v in self._fact_values))
        _require(type(self._fact.pid) is int and type(self._fact.observed_at_ns) is int
                 and (self._fact.pid, self._fact.observed_at_ns) == self._fact_values)
        self._bindings(self._binding_snapshot)
        return self._fact

    def ensure_pending(self, binding: object) -> None:
        self._enter(binding)
        try:
            _require(self._eligible and not self._work_refused and not self._resource_uncertain)
            _require(time.monotonic_ns() < self._observe_end and self._fact is None)
            if self._read_exit():
                self._work_refused = True
                self._eligible = False
                raise _PreexistingExitError("process_exit_before_stimulus")
            _require(time.monotonic_ns() < self._observe_end)
            self._bindings(binding)
        except _PreexistingExitError:
            raise
        except BaseException:
            self._work_refused = True
            self._eligible = False
            raise ObserverRefusedError("process_exit_pending_unknown") from None
        finally:
            self._lock.release()

    def poll(self, binding: object, *, cleanup: bool = False) -> ExitEventObservation | None:
        self._enter(binding)
        try:
            _require(type(cleanup) is bool and self._registered and not self._resource_uncertain)
            if not cleanup:
                _require(self._eligible and not self._work_refused)
            end = self._cleanup_end if cleanup else self._observe_end
            _require(time.monotonic_ns() < end)
            if self._fact is None:
                self._read_exit()
            _require(time.monotonic_ns() < end)
            self._bindings(binding)
            return None if self._fact is None else self._known_fact()
        except BaseException:
            self._work_refused = True
            self._eligible = False
            raise ObserverRefusedError("process_exit_poll_unknown") from None
        finally:
            self._lock.release()

    def fact(self, binding: object) -> ExitEventObservation:
        self._enter(binding)
        try:
            _require(self._registered and not self._resource_uncertain)
            return self._known_fact()
        finally:
            self._lock.release()

    def close(self, binding: object) -> bool:
        try:
            self._enter(binding)
        except ObserverRefusedError:
            return False
        try:
            self._work_refused = True
            self._eligible = False
            if self._close_attempted:
                known = (self._closed_known and type(self._close_fact) is object
                         and self._close_fact is self._close_fact_snapshot)
                if not known:
                    return False
                closed = _QCLOSED.__get__(self._queue, _QTYPE)
                self._bindings(binding)
                return closed is True
            self._close_attempted = True
            self._held()
            fd = self._fd_snapshot[0]
            _QCLOSE(self._queue)
            self._bindings(binding)
            closed = _QCLOSED.__get__(self._queue, _QTYPE)
            self._bindings(binding)
            _require(closed is True)
            try:
                os.fstat(fd)
            except OSError as error:
                self._bindings(binding)
                _require(error.errno == errno.EBADF)
            else:
                raise ObserverRefusedError("process_exit_queue_close_unknown")
            self._bindings(binding)
            self._close_fact = self._close_fact_snapshot = object()
            self._closed_known = True
            self._bindings(binding)
            return True
        except BaseException:
            self._poison_integrity()
            return False
        finally:
            self._lock.release()
