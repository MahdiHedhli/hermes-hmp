"""Private fixture work mechanics. Real issuance and serving remain unbound.

No production callsite imports this module in S1. Local body completion is not
native/process quiescence or permission to close a context. S2/S3 must supply
reviewed callsite coverage and source-specific resource ownership first.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Coroutine
from enum import Enum
from types import CoroutineType
from typing import Any


class _WorkRefusedError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("FIXTURE_WORK_UNAVAILABLE")


def _require_serving_issuer(lifecycle: Any, context: Any) -> None:
    # No callback, Boolean, config value or caller-created context mints this.
    raise _WorkRefusedError


# These names are pinned to CALLSITE-PLAN.json / INGRESS-SINK-PLAN.json.
# Only the relevant subset is admitted by each S1 primitive.
class _WorkSite(Enum):
    HTTP_REQUEST = "server.build_app:outer_request_frame"
    NATIVE_INERT = "adapter.HmpAdapter.note_inert_reply"
    NATIVE_SEND = "adapter.HmpAdapter.send"
    NATIVE_APPROVAL = "adapter.HmpAdapter._send_exec_approval_prompt"
    NATIVE_CLARIFY = "adapter.HmpAdapter.send_clarify"
    NATIVE_RETIRE = "adapter.HmpAdapter.retire_clarify_card"
    CW001 = "CW001"
    CW002 = "CW002"
    CW003 = "CW003"
    CW004 = "CW004"
    CW005 = "CW005"
    CW006 = "CW006"
    CW007 = "CW007"
    CW008 = "CW008"
    CW009 = "CW009"
    CW010 = "CW010"
    CW011 = "CW011"
    CW012 = "CW012"
    CW013 = "CW013"
    CW014 = "CW014"
    CW015 = "CW015"
    CW016 = "CW016"
    CW017 = "CW017"
    CW018 = "CW018"
    CW019 = "CW019"
    CW020 = "CW020"
    CW021 = "CW021"
    CW022 = "CW022"
    CW023 = "CW023"
    CW024 = "CW024"
    CW025 = "CW025"
    CW026 = "CW026"
    CW027 = "CW027"
    CW028 = "CW028"
    CW029 = "CW029"
    CW030 = "CW030"
    CW031 = "CW031"
    CW032 = "CW032"
    CW033 = "CW033"
    CW034 = "CW034"
    CW035 = "CW035"
    CW036 = "CW036"
    CW037 = "CW037"
    CW038 = "CW038"
    CW039 = "CW039"
    CW040 = "CW040"
    CW041 = "CW041"
    CW042 = "CW042"
    CW043 = "CW043"
    CW044 = "CW044"
    CW045 = "CW045"
    CW046 = "CW046"
    CW047 = "CW047"
    CW048 = "CW048"
    CW049 = "CW049"
    CW050 = "CW050"
    CW051 = "CW051"
    CW052 = "CW052"
    CW053 = "CW053"
    CW054 = "CW054"
    CW055 = "CW055"
    CW056 = "CW056"
    CW057 = "CW057"
    CW058 = "CW058"
    CW059 = "CW059"
    CW060 = "CW060"
    CW061 = "CW061"
    CW062 = "CW062"
    CW063 = "CW063"
    CW064 = "CW064"
    CW065 = "CW065"
    CW066 = "CW066"
    CW067 = "CW067"
    CW068 = "CW068"
    CW069 = "CW069"
    CW070 = "CW070"
    CW071 = "CW071"
    CW072 = "CW072"
    CW073 = "CW073"
    CW074 = "CW074"
    CW075 = "CW075"
    CW076 = "CW076"
    CW077 = "CW077"
    CW078 = "CW078"
    CW079 = "CW079"
    CW080 = "CW080"
    CW081 = "CW081"
    CW082 = "CW082"
    CW083 = "CW083"
    CW084 = "CW084"
    CW085 = "CW085"
    CW086 = "CW086"
    CW087 = "CW087"
    CW088 = "CW088"
    CW089 = "CW089"
    CW090 = "CW090"
    CW091 = "CW091"
    CW092 = "CW092"
    CW093 = "CW093"
    CW094 = "CW094"
    CW095 = "CW095"
    CW096 = "CW096"
    CW097 = "CW097"
    CW098 = "CW098"
    CW099 = "CW099"
    CW100 = "CW100"
    CW101 = "CW101"
    CW102 = "CW102"
    CW103 = "CW103"
    CW104 = "CW104"
    CW105 = "CW105"
    CW106 = "CW106"
    CW107 = "CW107"
    CW108 = "CW108"


class _WorkRecord:
    """Retained before transfer; task disposition and worker exit are distinct."""

    def __init__(self, owner: _ServingWork, site: _WorkSite, kind: str, parent: Any) -> None:
        self.owner = owner
        self.site = site
        self.kind = kind
        self.parent = parent
        self.token = object()
        self.gate: Any = None
        self.coroutine: Any = None
        self.payload: Any = None
        self.args: tuple[Any, ...] = ()
        self.kwargs: dict[str, Any] = {}
        self.returned_handle: Any = None
        self.task: Any = None
        self.transferred = False
        self.released = False
        self.body_entered = False
        self.body_exited = False
        self.worker_submitting = False
        self.worker_entered = False
        self.worker_exited = False
        self.worker_result: Any = None
        self.worker_failure: BaseException | None = None
        self.failure: BaseException | None = None
        self.result: Any = None
        self.collected = False
        self.completed_task_id: int | None = None
        self.unknown = False


class _ResourceRecord:
    """S1 retains unknown acquisitions; source-specific settlement is still absent."""

    def __init__(self, owner: _ServingWork, site: _WorkSite, error: BaseException) -> None:
        self.owner = owner
        self.site = site
        self.failure = error
        self.returned_handle: Any = None
        self.unknown = True


class _ServingWork:
    def __init__(self, lifecycle: Any, context: Any) -> None:
        _require_serving_issuer(lifecycle, context)
        self.lifecycle = lifecycle
        self.context = context
        self.alias = lifecycle.alias
        self.binding = lifecycle.binding
        self.adapter = lifecycle.adapter
        self._binding_context = tuple(vars(self.binding).items())
        self._mutex = threading.Lock()
        self._foreign_local = threading.local()
        self._records: list[_WorkRecord] = []
        self._resources: list[_ResourceRecord] = []
        self._transition: object | None = None
        self.stopping = False
        self.first_failure: BaseException | None = None

    def _poison_locked(self, error: BaseException) -> None:
        if self.first_failure is None:
            self.first_failure = error
        self.stopping = True

    def request_stop(self, error: BaseException) -> None:
        # No foreign callback or record-publication lock under this mutex.
        with self._mutex:
            self._poison_locked(error)

    def _context_current(self) -> bool:
        # Source-bound object checks outside the state mutex: no foreign
        # descriptor/callback is permitted to execute under that lock.
        binding = vars(self.binding)
        lifecycle = vars(self.lifecycle)
        adapter = vars(self.adapter)
        alias = vars(self.alias)
        return (
            lifecycle.get("ctx") is self.context
            and lifecycle.get("alias") is self.alias
            and lifecycle.get("binding") is self.binding
            and lifecycle.get("adapter") is self.adapter
            and alias.get("binding") is self.binding
            and alias.get("first_failure") is None
            and not lifecycle.get("stopping")
            and lifecycle.get("first_failure") is None
            and adapter.get("config") is binding.get("config")
            and len(binding) == len(self._binding_context)
            and all(binding.get(key) is saved for key, saved in self._binding_context)
        )

    def _live_locked(self, current: bool) -> None:
        if not current or self.stopping or self.first_failure is not None:
            error = _WorkRefusedError()
            self._poison_locked(error)
            raise error

    def _check(self, record: _WorkRecord, *, transition: bool = False) -> None:
        current = self._context_current()
        with self._mutex:
            self._live_locked(current)
            if (type(record) is not _WorkRecord or record.owner is not self
                    or not any(owned is record for owned in self._records)
                    or (transition and self._transition is not record.token)):
                error = _WorkRefusedError()
                self._poison_locked(error)
                raise error

    def _begin(self, site: _WorkSite, kind: str, parent: _WorkRecord | None) -> _WorkRecord:
        current = self._context_current()
        with self._mutex:
            self._live_locked(current)
            sites = _WORKER_SITES if kind == "worker" else _TASK_SITES
            if (type(site) is not _WorkSite or site not in sites or self._transition is not None
                    or getattr(self._foreign_local, "busy", False)
                    or (parent is not None and not self._parent_live_locked(parent))):
                error = _WorkRefusedError()
                self._poison_locked(error)
                raise error
            record = _WorkRecord(self, site, kind, parent)
            self._records.append(record)
            self._transition = record.token
            self._foreign_local.busy = True
            return record

    def _parent_live_locked(self, parent: _WorkRecord) -> bool:
        return (
            type(parent) is _WorkRecord and parent.owner is self
            and any(owned is parent for owned in self._records)
            and parent.body_entered and not parent.body_exited
        )

    def enter(self, site: _WorkSite) -> _WorkRecord:
        """Source-bound ingress only; thread identifiers confer no membership."""
        current = self._context_current()
        with self._mutex:
            self._live_locked(current)
            if (type(site) is not _WorkSite or site not in _INGRESS_SITES
                    or getattr(self._foreign_local, "busy", False)):
                error = _WorkRefusedError()
                self._poison_locked(error)
                raise error
            record = _WorkRecord(self, site, "ingress", None)
            self._records.append(record)
            self._foreign_local.busy = True
        try:
            if site is not _WorkSite.NATIVE_INERT:
                record.returned_handle = asyncio.current_task()
                if type(record.returned_handle) is not asyncio.Task:
                    raise _WorkRefusedError
                record.task = record.returned_handle
            self._check(record)
            with self._mutex:
                self._live_locked(True)
                record.body_entered = True
            return record
        except BaseException as error:
            with self._mutex:
                record.unknown = True
                record.failure = error
                self._poison_locked(error)
            if not isinstance(error, Exception):
                raise
        finally:
            self._foreign_local.busy = False
        raise _WorkRefusedError from None

    def leave(self, record: _WorkRecord) -> None:
        # Admitted ingress must be allowed to exit after stop. It cannot settle
        # a different record or the independent child workers it launched.
        with self._mutex:
            if (type(record) is not _WorkRecord or record.owner is not self
                    or not any(owned is record for owned in self._records)
                    or record.kind != "ingress" or record.body_exited):
                error = _WorkRefusedError()
                self._poison_locked(error)
                raise error
            record.body_exited = True

    def launch(
        self, site: _WorkSite, coroutine: Coroutine[Any, Any, Any],
        *, parent: _WorkRecord | None = None,
    ) -> _WorkRecord:
        record = self._begin(site, "task", parent)
        record.payload = coroutine
        if (type(coroutine) is not CoroutineType or coroutine.cr_running
                or coroutine.cr_suspended or coroutine.cr_frame is None):
            error = _WorkRefusedError()
            with self._mutex:
                record.failure = error
                record.unknown = True
                self._transition = None
                self._foreign_local.busy = False
                self._poison_locked(error)
            raise error
        return self._spawn(record)

    def launch_worker(
        self, site: _WorkSite, call: Callable[..., Any], *args: Any,
        parent: _WorkRecord | None = None, **kwargs: Any,
    ) -> _WorkRecord:
        record = self._begin(site, "worker", parent)
        record.payload, record.args, record.kwargs = call, args, kwargs
        return self._spawn(record)

    def _spawn(self, record: _WorkRecord) -> _WorkRecord:
        try:
            self._check(record, transition=True)
            loop = asyncio.get_running_loop()
            self._check(record, transition=True)
            make_gate = loop.create_future
            self._check(record, transition=True)
            record.gate = make_gate()
            self._check(record, transition=True)
            record.coroutine = self._body(record)
            make_task = loop.create_task
            self._check(record, transition=True)
            record.transferred = True
            returned = make_task(record.coroutine)
            record.returned_handle = returned
            if type(returned) is not asyncio.Task:
                raise _WorkRefusedError
            record.task = returned
            self._check(record, transition=True)
            if returned.get_coro() is not record.coroutine:
                raise _WorkRefusedError
            self._check(record, transition=True)
            record.released = True
            record.gate.set_result(None)
            self._check(record, transition=True)
            return record
        except BaseException as error:
            with self._mutex:
                record.failure = error
                record.unknown = True
                self._poison_locked(error)
            # Only our own coroutine, never transferred to a factory, is known
            # safe to close. Never infer no task from a missing returned handle.
            if not record.transferred and record.coroutine is not None:
                record.coroutine.close()
            if not isinstance(error, Exception):
                raise
        finally:
            with self._mutex:
                if self._transition is record.token:
                    self._transition = None
                self._foreign_local.busy = False
        # Outside handled exception context: keep foreign details private.
        raise _WorkRefusedError from None

    async def _body(self, record: _WorkRecord) -> Any:
        try:
            await record.gate
            self._check(record)
            running = asyncio.current_task()
            self._check(record)
            with self._mutex:
                self._live_locked(True)
                if running is not record.task:
                    record.unknown = True
                    error = _WorkRefusedError()
                    self._poison_locked(error)
                    raise error
                if not record.released or record.task is None:
                    raise _WorkRefusedError
                record.body_entered = True
            if record.kind == "worker":
                with self._mutex:
                    self._live_locked(True)
                    record.worker_submitting = True
                try:
                    result = await asyncio.to_thread(self._invoke_worker, record)
                except BaseException as error:
                    with self._mutex:
                        if not record.worker_exited or record.worker_failure is not error:
                            record.unknown = True
                            self._poison_locked(error)
                    raise
            else:
                result = await record.payload
            with self._mutex:
                record.result = result
            return result
        except BaseException as error:
            with self._mutex:
                if record.failure is None:
                    record.failure = error
            raise
        finally:
            with self._mutex:
                record.body_exited = True

    def _invoke_worker(self, record: _WorkRecord) -> Any:
        # Claim the one actual invocation before any context-check callback.
        # A duplicate cannot mark the first, still-running invocation exited.
        with self._mutex:
            if (type(record) is not _WorkRecord or record.owner is not self
                    or not any(owned is record for owned in self._records)
                    or not record.worker_submitting or record.worker_entered):
                error = _WorkRefusedError()
                record.unknown = True
                self._poison_locked(error)
                raise error
            record.worker_entered = True
        try:
            self._check(record)
            with self._mutex:
                self._live_locked(True)
            # This final mutex-ordered admission precedes the foreign callback.
            # Stop can still race after unlock; registration retains the body.
            result = record.payload(*record.args, **record.kwargs)
            with self._mutex:
                record.worker_result = result
            return result
        except BaseException as error:
            with self._mutex:
                record.worker_failure = error
            raise
        finally:
            with self._mutex:
                record.worker_exited = True

    async def collect(self, record: _WorkRecord) -> Any:
        # Collection is permitted while draining; it never grants a new effect
        # or publication. S2 must fence every source-specific output separately.
        with self._mutex:
            if (type(record) is not _WorkRecord or record.owner is not self
                    or not any(owned is record for owned in self._records)
                    or record.task is None or record.unknown):
                raise _WorkRefusedError
            task = record.task
        try:
            result = await asyncio.shield(task)
        except asyncio.CancelledError as error:
            # Distinguish the known completed body's original cancellation
            # from an unrelated cancelled shield waiter. Neither finishes a worker.
            with self._mutex:
                if record.body_exited and record.failure is error:
                    record.collected = True
            raise
        except BaseException:
            with self._mutex:
                record.collected = record.body_exited
            raise
        with self._mutex:
            record.collected = True
        return result

    def discard_collected_payload(self, record: _WorkRecord) -> None:
        """Private data retirement, never a completion or resource-close signal."""
        with self._mutex:
            if (type(record) is not _WorkRecord or record.owner is not self
                    or not any(owned is record for owned in self._records)
                    or not record.collected or self._pending_locked(record)):
                raise _WorkRefusedError
            record.completed_task_id = id(record.task)  # Diagnostic only, never authority.
            record.task = record.returned_handle = record.coroutine = None
            record.payload = record.result = record.worker_result = None
            record.args, record.kwargs = (), {}

    @staticmethod
    def _pending_locked(record: _WorkRecord) -> bool:
        return (
            record.unknown or not record.body_exited
            or (record.kind != "ingress" and not record.collected)
            or (record.kind == "worker" and record.worker_submitting and not record.worker_exited)
        )

    def local_debt(self) -> tuple[Any, ...]:
        """Diagnostic exact records only. S1 can never certify local closure."""
        with self._mutex:
            return (
                "S2_CALLSITE_COVERAGE_UNBOUND", "S3_RESOURCE_OWNERS_UNBOUND",
                *(record for record in self._records if self._pending_locked(record)),
                *self._resources,
            )

    def retain_unknown_acquisition(
        self, site: _WorkSite, error: BaseException, *, returned_handle: Any = None,
    ) -> _ResourceRecord:
        # Records unresolved debt only; there is deliberately no generic API
        # to certify successful acquisition/transfer/close or clear this debt.
        with self._mutex:
            record = _ResourceRecord(self, site, error)
            record.returned_handle = returned_handle
            self._resources.append(record)
            self._poison_locked(error)
            return record


_WORKER_SITES = frozenset({
    _WorkSite.CW001,
    _WorkSite.CW007,
    _WorkSite.CW008,
    _WorkSite.CW013,
    _WorkSite.CW016,
    _WorkSite.CW017,
    _WorkSite.CW024,
    _WorkSite.CW025,
    _WorkSite.CW026,
    _WorkSite.CW028,
    _WorkSite.CW029,
    _WorkSite.CW030,
    _WorkSite.CW031,
    _WorkSite.CW032,
    _WorkSite.CW033,
    _WorkSite.CW034,
    _WorkSite.CW035,
    _WorkSite.CW036,
    _WorkSite.CW037,
    _WorkSite.CW038,
    _WorkSite.CW039,
    _WorkSite.CW040,
    _WorkSite.CW041,
    _WorkSite.CW042,
    _WorkSite.CW044,
    _WorkSite.CW045,
    _WorkSite.CW052,
    _WorkSite.CW058,
    _WorkSite.CW065,
    _WorkSite.CW066,
    _WorkSite.CW067,
    _WorkSite.CW068,
    _WorkSite.CW070,
    _WorkSite.CW074,
    _WorkSite.CW075,
    _WorkSite.CW077,
    _WorkSite.CW081,
    _WorkSite.CW082,
    _WorkSite.CW083,
    _WorkSite.CW084,
    _WorkSite.CW085,
    _WorkSite.CW086,
    _WorkSite.CW087,
    _WorkSite.CW088,
    _WorkSite.CW089,
    _WorkSite.CW090,
    _WorkSite.CW091,
    _WorkSite.CW092,
    _WorkSite.CW093,
    _WorkSite.CW094,
    _WorkSite.CW095,
    _WorkSite.CW096,
    _WorkSite.CW097,
    _WorkSite.CW098,
    _WorkSite.CW099,
    _WorkSite.CW100,
    _WorkSite.CW101,
    _WorkSite.CW102,
    _WorkSite.CW103,
    _WorkSite.CW107,
})

_TASK_SITES = frozenset({
    _WorkSite.CW002,
    _WorkSite.CW020,
    _WorkSite.CW057,
    _WorkSite.CW071,
    _WorkSite.CW076,
    _WorkSite.CW106,
    _WorkSite.CW108,
})

_INGRESS_SITES = frozenset({
    _WorkSite.HTTP_REQUEST,
    _WorkSite.NATIVE_INERT,
    _WorkSite.NATIVE_SEND,
    _WorkSite.NATIVE_APPROVAL,
    _WorkSite.NATIVE_CLARIFY,
    _WorkSite.NATIVE_RETIRE,
})
