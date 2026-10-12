"""Private fixture work mechanics. Real issuance and serving remain unbound.

S2 callsites use private retained references; normal owner-None paths retain their
original operations. Local completion is not native/process quiescence or context
close permission. Real issuance and S3 resource/serving ownership remain closed.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Coroutine
from concurrent.futures import Future as ConcurrentFuture
from contextvars import ContextVar
from enum import Enum
from types import CoroutineType, FunctionType, MethodType
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
    OPERATOR_CLIENT = "operator_read.OperatorReadService._handle"
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
        self.cancel_attempted = False
        self.completed_task_id: int | None = None
        self.unknown = False
        self.registry: Any = None
        self.registry_key: Any = None
        self.cleanup: Any = None
        self.cmid_acquisition: Any = None
        self.budget: Any = None
        self.operator: Any = None
        self.budget_loop: Any = None
        self.budget_release_claimed = False
        self.budget_released = False


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
        self._resource_scope: _ServingResources | None = None
        self._submissions: list[Any] = []
        self._media_service: Any = None
        self._cmid_acquisitions: list[_CmidAcquisition] = []
        self._transition: object | None = None
        # S3 must install these exact source components before serving. This is
        # an identity set, never a registry of caller-provided permission flags.
        self._carriers = (context, self.adapter)
        self._context_objects: tuple[tuple[str, Any], ...] = ()
        self._component_bind_complete = False
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
        _notify_resources(self)

    def _context_current(self, *, draining: bool = False) -> bool:
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
            and (
                draining
                or (
                    alias.get("first_failure") is None
                    and not lifecycle.get("stopping")
                    and lifecycle.get("first_failure") is None
                )
            )
            and adapter.get("config") is binding.get("config")
            and (
                not self._context_objects
                or all(vars(self.context).get(key) is saved for key, saved in self._context_objects)
            )
            and len(binding) == len(self._binding_context)
            and all(binding.get(key) is saved for key, saved in self._binding_context)
        )

    def _live_locked(self, current: bool) -> None:
        if not current or self.stopping or self.first_failure is not None:
            error = _WorkRefusedError()
            self._poison_locked(error)
            raise error

    def _check(self, record: _WorkRecord, *, transition: bool = False) -> None:
        cleanup = type(record) is _WorkRecord and record.cleanup is not None
        current = self._context_current(draining=cleanup)
        with self._mutex:
            self._record_live_locked(record, current)
            if (
                type(record) is not _WorkRecord
                or record.owner is not self
                or not any(owned is record for owned in self._records)
                or (transition and self._transition is not record.token)
            ):
                error = _WorkRefusedError()
                self._poison_locked(error)
                raise error

    def _record_live_locked(self, record: _WorkRecord, current: bool) -> None:
        if type(record) is _WorkRecord and record.cleanup is not None:
            reserve = record.cleanup
            if (
                type(reserve) is not _CmidReservation
                or reserve.owner is not self
                or reserve.claim is not record
                or not _cmid_scope_current(reserve)
                or not current
                or (reserve.acquisition is None and not self._parent_live_locked(reserve.parent))
                or (
                    reserve.acquisition is not None
                    and (
                        type(reserve.acquisition) is not _CmidAcquisition
                        or reserve.acquisition.owner is not self
                        or reserve.acquisition.ticket is not reserve
                        or reserve.acquisition.unknown
                        or not any(
                            known is reserve.acquisition for known in self._cmid_acquisitions
                        )
                    )
                )
            ):
                error = _WorkRefusedError()
                self._poison_locked(error)
                raise error
        else:
            self._live_locked(current)

    def _begin(self, site: _WorkSite, kind: str, parent: _WorkRecord | None) -> _WorkRecord:
        current = self._context_current()
        with self._mutex:
            self._live_locked(current)
            sites = (
                {_WorkSite.CW011}
                if kind == "p6"
                else _WORKER_SITES
                if kind == "worker"
                else _TASK_SITES
            )
            if (
                type(site) is not _WorkSite
                or site not in sites
                or self._transition is not None
                or getattr(self._foreign_local, "busy", False)
                or (parent is not None and not self._parent_live_locked(parent))
            ):
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
                    or getattr(self._foreign_local, "busy", False)
                    or (self._resource_scope is not None
                        and not self._resource_scope.serving_ready)):
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
            if (
                type(record) is not _WorkRecord
                or record.owner is not self
                or not any(owned is record for owned in self._records)
                or record.kind != "ingress"
                or record.body_exited
            ):
                error = _WorkRefusedError()
                self._poison_locked(error)
                raise error
            record.body_exited = True
            abandoned = [item for item in self._cmid_acquisitions if item.parent is record]
            for item in abandoned:
                item.abandoned = True
        for item in abandoned:
            _schedule_cmid_disposition(item)
        _notify_resources(self)

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
            if record.budget is not None:
                record.budget_loop = loop
            if record.cmid_acquisition is not None and record.kind == "worker":
                record.cmid_acquisition.loop = loop
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
            if record.registry is not None:
                # Exact source-owned pending map is populated before user work.
                if record.site is _WorkSite.CW020:
                    record.registry.put(record.registry_key, returned)
                elif record.site is _WorkSite.CW071:
                    record.registry.put_phone_task(record.registry_key, returned)
                else:
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
        frame_token = _CURRENT_FRAME.set(record)
        try:
            await record.gate
            self._check(record)
            running = asyncio.current_task()
            self._check(record)
            with self._mutex:
                self._record_live_locked(record, True)
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
                    self._record_live_locked(record, True)
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
            _CURRENT_FRAME.reset(frame_token)
            _notify_resources(self)

    def _invoke_worker(self, record: _WorkRecord) -> Any:
        # Claim the one actual invocation before any context-check callback.
        # A duplicate cannot mark the first, still-running invocation exited.
        with self._mutex:
            if (
                type(record) is not _WorkRecord
                or record.owner is not self
                or not any(owned is record for owned in self._records)
                or not record.worker_submitting
                or record.worker_entered
            ):
                error = _WorkRefusedError()
                record.unknown = True
                self._poison_locked(error)
                raise error
            record.worker_entered = True
        try:
            self._check(record)
            if record.cleanup is not None and not _cmid_callback_current(
                record.cleanup, record.cleanup_kind, record.payload, record.args, record.kwargs
            ):
                raise _WorkRefusedError
            if record.cleanup is not None and not _cmid_arguments_current(record):
                raise _WorkRefusedError
            self._check(record)
            with self._mutex:
                self._record_live_locked(record, True)
            # This final mutex-ordered admission precedes the foreign callback.
            # Stop can still race after unlock; registration retains the body.
            result = record.payload(*record.args, **record.kwargs)
            with self._mutex:
                record.worker_result = result
            return result
        except BaseException as error:
            with self._mutex:
                record.worker_failure = error
                if record.cleanup is not None and record.cleanup.acquisition is not None:
                    record.cleanup.acquisition.unknown = True
                    record.cleanup.acquisition.failure = error
                    self._poison_locked(error)
            raise
        finally:
            with self._mutex:
                record.worker_exited = True
            _budget_completed(record)
            if record.cleanup is None:
                _cmid_body_completed(record)
            _notify_resources(self)

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
            _notify_resources(self)
            raise
        except BaseException:
            with self._mutex:
                record.collected = record.body_exited
            _notify_resources(self)
            raise
        with self._mutex:
            record.collected = True
        _notify_resources(self)
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
            record.unknown
            or (record.budget is not None and not record.budget_released)
            or not record.body_exited
            or (record.kind != "ingress" and not record.collected)
            or (record.kind == "worker" and record.worker_submitting and not record.worker_exited)
        )

    def local_debt(self) -> tuple[Any, ...]:
        """Diagnostic exact records only. S1 can never certify local closure."""
        with self._mutex:
            return (
                "S2_CALLSITE_COVERAGE_UNBOUND",
                "S3_RESOURCE_OWNERS_UNBOUND",
                *(record for record in self._records if self._pending_locked(record)),
                *self._resources,
                *(record for record in self._submissions if record.pending()),
                *(record for record in self._cmid_acquisitions if record.pending()),
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


_WORKER_SITES = frozenset(
    {
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
    }
)

_TASK_SITES = frozenset(
    {
        _WorkSite.CW002,
        _WorkSite.CW006,
        _WorkSite.CW020,
        _WorkSite.CW057,
        _WorkSite.CW071,
        _WorkSite.CW076,
        _WorkSite.CW106,
        _WorkSite.CW108,
    }
)

_INGRESS_SITES = frozenset(
    {
        _WorkSite.OPERATOR_CLIENT,
        _WorkSite.HTTP_REQUEST,
        _WorkSite.NATIVE_INERT,
        _WorkSite.NATIVE_SEND,
        _WorkSite.NATIVE_APPROVAL,
        _WorkSite.NATIVE_CLARIFY,
        _WorkSite.NATIVE_RETIRE,
    }
)


_CURRENT_FRAME: ContextVar[_WorkRecord | None] = ContextVar("hmp_fixture_work", default=None)


def _owner(carrier: Any) -> _ServingWork | None:
    """Resolve a retained private reference; absence on a bound fixture refuses."""
    fields = vars(carrier)
    owner = fields.get("_fixture_work")
    adapter = fields.get("_fixture_adapter")
    if owner is None:
        if (
            fields.get("_fixture_binding_attempted")
            or (adapter is not None and vars(adapter).get("_fixture_binding_attempted"))
            or _CURRENT_FRAME.get() is not None
        ):
            frame = _CURRENT_FRAME.get()
            if type(frame) is _WorkRecord:
                frame.owner.request_stop(_WorkRefusedError())
            raise _WorkRefusedError
        return None
    if (
        type(owner) is not _ServingWork
        or not owner._component_bind_complete
        or not any(carrier is known for known in owner._carriers)
    ):
        if type(owner) is _ServingWork:
            owner.request_stop(_WorkRefusedError())
        raise _WorkRefusedError
    current = owner._context_current()
    with owner._mutex:
        owner._live_locked(current)
    return owner


def _parent(owner: _ServingWork) -> _WorkRecord:
    record = _CURRENT_FRAME.get()
    owner._check(record)
    with owner._mutex:
        if not owner._parent_live_locked(record):
            error = _WorkRefusedError()
            owner._poison_locked(error)
            raise error
    return record


def _publication(carrier: Any) -> None:
    """Point-in-time output fence, never atomic authorization over future I/O."""
    owner = _owner(carrier)
    if owner is not None:
        _parent(owner)


class _Ingress:
    def __init__(self, carrier: Any, site: _WorkSite) -> None:
        self.owner = _owner(carrier)
        self.site = site
        self.record: _WorkRecord | None = None
        self.token: Any = None

    def __enter__(self) -> _WorkRecord | None:
        if self.owner is not None:
            self.record = self.owner.enter(self.site)
            self.token = _CURRENT_FRAME.set(self.record)
        return self.record

    def __exit__(self, _kind: Any, _error: Any, _trace: Any) -> None:
        if self.owner is not None:
            try:
                self.owner.leave(self.record)
            finally:
                _CURRENT_FRAME.reset(self.token)


async def _worker(
    carrier: Any, site: _WorkSite, call: Callable[..., Any], *args: Any, **kwargs: Any
) -> Any:
    owner = _owner(carrier)
    if owner is None:
        return await asyncio.to_thread(call, *args, **kwargs)
    parent = _parent(owner)
    record = owner.launch_worker(site, call, *args, parent=parent, **kwargs)
    result = await owner.collect(record)
    owner._check(record)
    _parent(owner)
    owner.discard_collected_payload(record)
    return result


def _send_task(
    carrier: Any,
    site: _WorkSite,
    coroutine: Coroutine[Any, Any, Any],
    registry: Any,
    key: tuple[str, str, str, str],
) -> Any:
    owner = _owner(carrier)
    if owner is None:
        return asyncio.ensure_future(coroutine)
    parent = _parent(owner)
    expected = (
        vars(owner.context).get("direct_send_deps")
        if site is _WorkSite.CW020
        else vars(owner.context).get("prompt_store")
    )
    if (
        (site is _WorkSite.CW020 and (carrier is not expected or registry is not carrier.tasks))
        or (site is _WorkSite.CW071 and (carrier is not expected or registry is not carrier))
        or site not in (_WorkSite.CW020, _WorkSite.CW071)
        or type(key) is not tuple
        or len(key) != 4
        or any(type(part) is not str for part in key)
    ):
        owner.request_stop(_WorkRefusedError())
        raise _WorkRefusedError
    record = owner._begin(site, "task", parent)
    record.payload = coroutine
    record.registry, record.registry_key = registry, key
    _join_cmid_task(owner, parent, record, key)
    if (
        type(coroutine) is not CoroutineType
        or coroutine.cr_running
        or coroutine.cr_suspended
        or coroutine.cr_frame is None
    ):
        record.unknown = True
        owner.request_stop(_WorkRefusedError())
        raise _WorkRefusedError
    return owner._spawn(record).task


async def _await_publication(carrier: Any, awaitable: Any) -> Any:
    # The original awaitable is created in the original source scope. No new
    # executor, timeout, retry or payload transformation is introduced here.
    try:
        _publication(carrier)
    except BaseException:
        # This helper has not transferred the supplied awaitable anywhere.
        # Close only a demonstrably fresh coroutine; retained Tasks/Futures stay.
        if (
            type(awaitable) is CoroutineType
            and not awaitable.cr_running
            and not awaitable.cr_suspended
            and awaitable.cr_frame is not None
        ):
            awaitable.close()
        raise
    result = await awaitable
    _publication(carrier)
    return result


class _MediaSubmission:
    def __init__(self, owner: _ServingWork, parent: _WorkRecord, lease: Any) -> None:
        self.owner, self.parent, self.lease = owner, parent, lease
        self.token = object()
        self.signal_attempted = False
        self.site = _WorkSite.CW046
        self.gate: Any = None
        self.future: Any = None
        self.submit_thread: int | None = None
        self.transferred = False
        self.released = False
        self.entered = False
        self.exited = False
        self.collected = False
        self.unknown = False
        self.failure: BaseException | None = None

    def pending(self) -> bool:
        return self.unknown or not self.exited or not self.collected


def _media_submit(owner: _ServingWork, lease: Any, copied: Any, run: Callable[[], bool]) -> Any:
    # Called only after the original lease acquired its existing permits.
    parent = _parent(owner)
    if lease._service is not owner._media_service:
        owner.request_stop(_WorkRefusedError())
        raise _WorkRefusedError
    record = _MediaSubmission(owner, parent, lease)
    with owner._mutex:
        owner._live_locked(True)
        if owner._transition is not None or getattr(owner._foreign_local, "busy", False):
            error = _WorkRefusedError()
            owner._poison_locked(error)
            raise error
        owner._submissions.append(record)
        owner._transition = record.token
        owner._foreign_local.busy = True
    try:
        _parent(owner)
        record.gate = threading.Event()
        _parent(owner)
        # Diagnostic deadlock avoidance only. Retained object identity, the
        # mutex and release latch supply membership; a thread ID never does.
        record.submit_thread = threading.get_ident()
        _parent(owner)
        record.transferred = True
        returned = lease._service._executor.submit(copied.run, _media_body, record, run)
        record.future = returned
        if type(returned) is not ConcurrentFuture:
            raise _WorkRefusedError
        _parent(owner)
        returned.add_done_callback(lambda future: _media_finished(record, future))
        _parent(owner)
        with owner._mutex:
            owner._live_locked(True)
            record.released = True
        record.signal_attempted = True
        record.gate.set()
        _parent(owner)
        return returned
    except BaseException as error:
        with owner._mutex:
            record.failure = error
            record.unknown = True
            owner._poison_locked(error)
        if record.gate is not None and not record.signal_attempted:
            record.signal_attempted = True
            record.gate.set()  # Refused waiter only; never retry uncertain signaling.
        if not isinstance(error, Exception):
            raise
    finally:
        with owner._mutex:
            if owner._transition is record.token:
                owner._transition = None
            owner._foreign_local.busy = False
    raise _WorkRefusedError from None


def _media_body(record: _MediaSubmission, run: Callable[[], bool]) -> bool:
    owner = record.owner
    with owner._mutex:
        if record.entered:
            record.unknown = True
            owner._poison_locked(_WorkRefusedError())
            raise _WorkRefusedError
        record.entered = True
    admitted = False
    token = _CURRENT_FRAME.set(record.parent)
    try:
        if not record.released and threading.get_ident() == record.submit_thread:
            # An inline executor cannot wait for the handle it must return.
            raise _WorkRefusedError
        record.gate.wait()
        current = owner._context_current()
        with owner._mutex:
            owner._live_locked(current)
            if not record.released or record.future is None or record.unknown:
                raise _WorkRefusedError
            admitted = True
        # The retained submission owns this callback even when its request
        # waiter has left. Late mailbox publication has a separate live fence.
        return run()
    except BaseException as error:
        with owner._mutex:
            record.failure = error
            record.unknown = True
            owner._poison_locked(error)
        raise
    finally:
        try:
            if admitted:
                record.lease._done(record.future)
        except BaseException as error:
            with owner._mutex:
                record.unknown = True
                owner._poison_locked(error)
            raise
        finally:
            with owner._mutex:
                record.exited = True
            _CURRENT_FRAME.reset(token)
            _notify_resources(owner)


def _media_finished(record: _MediaSubmission, future: Any) -> None:
    owner = record.owner
    cancelled = future.cancelled()
    with owner._mutex:
        if future is not record.future or not record.exited or cancelled:
            record.unknown = True
            owner._poison_locked(_WorkRefusedError())
        else:
            record.collected = True
    _notify_resources(owner)


def _p6_submit(bridge: Any, coroutine: Coroutine[Any, Any, Any], loop: Any) -> Any:
    owner = _owner(bridge)
    if owner is None:
        return asyncio.run_coroutine_threadsafe(coroutine, loop)
    parent = _parent(owner)
    if bridge is not vars(owner.context).get("bridge"):
        raise _WorkRefusedError
    record = owner._begin(_WorkSite.CW011, "p6", parent)
    record.payload = coroutine
    try:
        owner._check(record, transition=True)
        record.gate = ConcurrentFuture()
        owner._check(record, transition=True)
        record.coroutine = _p6_body(record)
        record.transferred = True
        returned = asyncio.run_coroutine_threadsafe(record.coroutine, loop)
        record.returned_handle = returned
        if type(returned) is not ConcurrentFuture:
            raise _WorkRefusedError
        owner._check(record, transition=True)
        bridge._pending_triggers.add(returned)
        returned.add_done_callback(lambda future: _p6_returned(record, future))
        owner._check(record, transition=True)
        returned.add_done_callback(bridge._trigger_done)
        owner._check(record, transition=True)
        record.released = True
        record.gate.set_result(None)
        owner._check(record, transition=True)
        return returned
    except BaseException as error:
        with owner._mutex:
            record.failure = error
            record.unknown = True
            owner._poison_locked(error)
        if not record.transferred and record.coroutine is not None:
            record.coroutine.close()
        if not isinstance(error, Exception):
            raise
    finally:
        with owner._mutex:
            if owner._transition is record.token:
                owner._transition = None
            owner._foreign_local.busy = False
    raise _WorkRefusedError from None


async def _p6_body(record: _WorkRecord) -> Any:
    owner = record.owner
    token = _CURRENT_FRAME.set(record)
    try:
        # This executes in the actual loop task, not the submitter thread.
        task = asyncio.current_task()
        record.task = task
        if type(task) is not asyncio.Task or task.get_coro() is not record.coroutine:
            raise _WorkRefusedError
        await asyncio.shield(asyncio.wrap_future(record.gate))
        owner._check(record)
        with owner._mutex:
            owner._live_locked(True)
            if not record.released or record.returned_handle is None:
                raise _WorkRefusedError
            record.body_entered = True
        result = await record.payload
        owner._check(record)
        return result
    except BaseException as error:
        with owner._mutex:
            record.failure = error
            if not record.body_entered:
                record.unknown = True
            owner._poison_locked(error)
        raise
    finally:
        with owner._mutex:
            record.body_exited = True
        _CURRENT_FRAME.reset(token)


class _CmidReservation:
    """One exact already-owned send row, never permission for a new send."""

    def __init__(
        self, owner: _ServingWork, parent: _WorkRecord, key: Any, calls: tuple[Any, Any, Any]
    ) -> None:
        self.owner, self.parent, self.key, self.calls = owner, parent, key, calls
        self.identity = (owner, parent, key, calls)
        self.claim: _WorkRecord | None = None
        self.acquisition: _CmidAcquisition | None = None


def _cmid_key_matches(left: Any, right: Any) -> bool:
    return (
        type(left) is tuple
        and type(right) is tuple
        and len(left) == len(right) == 4
        and all(type(part) is str for part in (*left, *right))
        and left == right
    )


def _cmid_arguments_current(record: _WorkRecord) -> bool:
    kind, call, args, keywords = record.cleanup_arguments
    return (
        record.cleanup_kind is kind
        and record.payload is call
        and record.args is args
        and len(record.kwargs) == len(keywords)
        and all(record.kwargs.get(key) is value for key, value in keywords)
    )


def _cmid_scope_current(reserve: _CmidReservation) -> bool:
    """Exact retained row custody; a cleanup ticket is never a general Store grant."""
    acquisition = reserve.acquisition
    owner, parent = reserve.owner, reserve.parent
    return (
        type(acquisition) is _CmidAcquisition
        and all(current is saved for current, saved in zip(
            (owner, parent, reserve.key, reserve.calls), reserve.identity, strict=True
        ))
        and acquisition.site in (_WorkSite.CW017, _WorkSite.CW068)
        and parent.owner is owner
        and any(known is parent for known in owner._records)
        and all(current is saved for current, saved in zip(
            (acquisition.owner, acquisition.parent, acquisition.site, acquisition.store,
             acquisition.key, acquisition.now), acquisition.identity, strict=True
        ))
        and acquisition.owner is owner
        and acquisition.ticket is reserve
        and acquisition.store is owner.context.store
        and acquisition.inserted is True
        and not acquisition.unknown
        and any(known is acquisition for known in owner._cmid_acquisitions)
        and _cmid_key_matches(reserve.key, acquisition.key)
        and (
            (
                acquisition.handoff is parent
                and parent.cmid_acquisition is acquisition
                and _cmid_key_matches(parent.registry_key, reserve.key)
                and parent.site is (
                    _WorkSite.CW020 if acquisition.site is _WorkSite.CW017 else _WorkSite.CW071
                )
            )
            or (
                acquisition.handoff is None
                and parent is acquisition.parent
                and (acquisition.abandoned or parent.body_exited or owner.stopping)
            )
        )
    )


def _cmid_callback_current(
    reserve: _CmidReservation, kind: str, call: Any,
    args: tuple[Any, ...], kwargs: dict[str, Any],
) -> bool:
    if not _cmid_scope_current(reserve):
        return False
    acquisition = reserve.acquisition
    if acquisition.site is _WorkSite.CW068 or acquisition.handoff is None:
        method = (
            "delete_cmid_reservation"
            if acquisition.site is _WorkSite.CW017 else "finalize_phone_cmid"
        )
        return (
            type(call) is MethodType
            and call.__self__ is acquisition.store
            and call.__func__ is getattr(type(acquisition.store), method, None)
            and _cmid_key_matches(args, reserve.key)
            and (
                (method == "delete_cmid_reservation" and kind == "release" and not kwargs)
                or (
                    method == "finalize_phone_cmid"
                    and kind == "finalize"
                    and set(kwargs) == {"status", "result_json", "updated_at"}
                    and type(kwargs["status"]) is str
                    and type(kwargs["updated_at"]) is type(acquisition.now)
                    and kwargs["updated_at"] == acquisition.now
                )
            )
        )
    if type(call) is not FunctionType or kind not in ("release", "finalize", "unknown"):
        return False
    name = {"release": "_release", "finalize": "_finalize", "unknown": "_finalize_unknown"}[kind]
    if (
        call.__code__.co_qualname != "_execute.<locals>." + name
        or call.__code__.co_filename != call.__globals__.get("__file__")
    ):
        return False
    cells = dict(zip(call.__code__.co_freevars,
                     (cell.cell_contents for cell in call.__closure__), strict=True))
    deps = cells.get("deps")
    request = cells.get("request")
    key = (cells.get("iid"), cells.get("user_id"), cells.get("profile"),
           vars(request).get("client_message_id") if hasattr(request, "__dict__") else None)
    return (
        deps is reserve.owner.context.direct_send_deps
        and deps.store is acquisition.store
        and _cmid_key_matches(key, reserve.key)
        and (
            (kind in ("release", "unknown") and not args and not kwargs)
            or (kind == "finalize" and len(args) == 1 and type(args[0]) is str
                and set(kwargs) <= {"code", "outcome"})
        )
    )


def _reserve_cmid_cleanup(
    deps: Any, key: Any, release: Any, finalize: Any, unknown: Any
) -> _CmidReservation | None:
    owner = _owner(deps)
    if owner is None:
        return None
    parent = _parent(owner)
    if (
        parent.site is not _WorkSite.CW020
        or parent.registry is not deps.tasks
        or parent.registry_key != key
        or deps is not owner.context.direct_send_deps
    ):
        raise _WorkRefusedError
    for call, name in zip(
        (release, finalize, unknown), ("_release", "_finalize", "_finalize_unknown"), strict=True
    ):
        if (
            type(call) is not FunctionType
            or call.__code__.co_qualname != "_execute.<locals>." + name
            or call.__code__.co_filename != call.__globals__.get("__file__")
        ):
            raise _WorkRefusedError
        cells = dict(
            zip(
                call.__code__.co_freevars,
                (cell.cell_contents for cell in call.__closure__),
                strict=True,
            )
        )
        if cells.get("deps") is not deps:
            raise _WorkRefusedError
    ticket = _CmidReservation(owner, parent, key, (release, finalize, unknown))
    acquisition = parent.cmid_acquisition
    if acquisition is None or acquisition.handoff is not parent or acquisition.ticket is not None:
        raise _WorkRefusedError
    ticket.acquisition = acquisition
    acquisition.ticket = ticket
    return ticket


def _claim_cmid(
    reserve: _CmidReservation, kind: str, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> _WorkRecord:
    owner = reserve.owner
    callback_current = (
        kind in ("release", "finalize", "unknown")
        and _cmid_callback_current(
            reserve, kind, reserve.calls[("release", "finalize", "unknown").index(kind)],
            args, kwargs,
        )
    )
    current = owner._context_current(draining=True)
    with owner._mutex:
        if (
            type(reserve) is not _CmidReservation
            or reserve.claim is not None
            or not current
            or _CURRENT_FRAME.get() is not reserve.parent
            or not owner._parent_live_locked(reserve.parent)
            or owner._transition is not None
            or getattr(owner._foreign_local, "busy", False)
            or kind not in ("release", "finalize", "unknown")
            or not _cmid_scope_current(reserve)
            or not callback_current
        ):
            error = _WorkRefusedError()
            owner._poison_locked(error)
            if type(reserve.acquisition) is _CmidAcquisition:
                reserve.acquisition.unknown = True
                reserve.acquisition.failure = error
            raise error
        record = _WorkRecord(owner, _WorkSite.CW020, "worker", reserve.parent)
        record.cleanup = reserve
        record.payload = reserve.calls[("release", "finalize", "unknown").index(kind)]
        record.args, record.kwargs = args, kwargs
        record.cleanup_kind = kind
        record.cleanup_arguments = (kind, record.payload, args, tuple(kwargs.items()))
        reserve.claim = record
        owner._records.append(record)
        owner._transition = record.token
        owner._foreign_local.busy = True
        return record


async def _cmid_worker(
    reserve: _CmidReservation | None, kind: str, call: Any, *args: Any, **kwargs: Any
) -> Any:
    if reserve is None:
        return await asyncio.to_thread(call, *args, **kwargs)
    _cmid_call_current(reserve, kind, call)
    record = _claim_cmid(reserve, kind, args, kwargs)
    reserve.owner._spawn(record)
    # Exact cleanup completion may be collected while draining; it is not an
    # output permission. Its caller still fences every positive response.
    return await reserve.owner.collect(record)


def _cmid_sync(
    reserve: _CmidReservation | None, kind: str, call: Any, *args: Any, **kwargs: Any
) -> Any:
    if reserve is None:
        return call(*args, **kwargs)
    _cmid_call_current(reserve, kind, call)
    if reserve.claim is not None:
        # Never retry an uncertain or completed one-use cleanup. Preserve its
        # retained debt and the original exception being propagated by caller.
        return None
    record = _claim_cmid(reserve, kind, args, kwargs)
    record.body_entered = record.worker_submitting = True
    try:
        return reserve.owner._invoke_worker(record)
    finally:
        with reserve.owner._mutex:
            record.body_exited = record.collected = True
            if reserve.owner._transition is record.token:
                reserve.owner._transition = None
            reserve.owner._foreign_local.busy = False


def _cmid_call_current(reserve: _CmidReservation, kind: str, call: Any) -> None:
    if (
        type(kind) is str
        and kind in ("release", "finalize", "unknown")
        and type(reserve.calls) is tuple
        and len(reserve.calls) == 3
        and call is reserve.calls[("release", "finalize", "unknown").index(kind)]
    ):
        return
    error = _WorkRefusedError()
    with reserve.owner._mutex:
        reserve.owner._poison_locked(error)
        if type(reserve.acquisition) is _CmidAcquisition:
            reserve.acquisition.unknown = True
            reserve.acquisition.failure = error
    raise error


def _budget_task(
    carrier: Any, site: _WorkSite, call: Any, *args: Any, operator: Any = None, **kwargs: Any
) -> Any:
    owner = _owner(carrier)
    if owner is None:
        return asyncio.create_task(asyncio.to_thread(call, *args, **kwargs))
    parent = _parent(owner)
    if (
        carrier is not owner.context
        or site not in (_WorkSite.CW058, _WorkSite.CW077)
        or ((operator is None) != (site is _WorkSite.CW077))
        or (operator is not None and operator.ctx is not owner.context)
    ):
        raise _WorkRefusedError
    record = owner._begin(site, "worker", parent)
    record.payload, record.args, record.kwargs = call, args, kwargs
    record.budget = carrier.read_worker_budget
    record.operator = operator
    return owner._spawn(record).task


def _budget_completed(record: _WorkRecord) -> None:
    # Exact physical wrapper exit schedules the original loop-side permit and
    # operator accounting. A cancelled asyncio waiter cannot schedule this.
    if record.budget is None:
        return
    try:
        record.budget_loop.call_soon_threadsafe(_budget_release_loop, record)
    except BaseException as error:
        with record.owner._mutex:
            record.unknown = True
            record.owner._poison_locked(error)
        raise


def _budget_release_loop(record: _WorkRecord) -> None:
    owner = record.owner
    with owner._mutex:
        if (
            not record.worker_exited
            or record.budget_release_claimed
            or record.budget is not owner.context.read_worker_budget
            or not any(known is record for known in owner._records)
        ):
            record.unknown = True
            owner._poison_locked(_WorkRefusedError())
            raise _WorkRefusedError
        record.budget_release_claimed = True
    try:
        record.budget.release(operator=record.operator is not None)
        if record.operator is not None:
            service = record.operator
            service._outstanding -= 1
            if service._stopping and service._outstanding == 0:
                service._drained.set()
        with owner._mutex:
            record.budget_released = True
    except BaseException as error:
        with owner._mutex:
            record.unknown = True
            owner._poison_locked(error)
        raise


def _reserve_phone_cleanup(prompts: Any, store: Any, key: Any) -> _CmidReservation | None:
    owner = _owner(prompts)
    if owner is None:
        return None
    parent = _parent(owner)
    if (
        parent.site is not _WorkSite.CW071
        or parent.registry is not prompts
        or parent.registry_key != key
        or store is not owner.context.store
        or prompts is not owner.context.prompt_store
    ):
        raise _WorkRefusedError
    call = store.finalize_phone_cmid
    ticket = _CmidReservation(owner, parent, key, (call, call, call))
    acquisition = parent.cmid_acquisition
    if acquisition is None or acquisition.handoff is not parent or acquisition.ticket is not None:
        raise _WorkRefusedError
    ticket.acquisition = acquisition
    acquisition.ticket = ticket
    return ticket


def _p6_returned(record: _WorkRecord, future: Any) -> None:
    owner = record.owner
    cancelled = future.cancelled()
    task = record.task
    task_done = task is not None and task.done()
    with owner._mutex:
        if future is not record.returned_handle or cancelled:
            owner._poison_locked(_WorkRefusedError())
            # Cancellation is not completion of the actual loop task.
        elif task_done and record.body_exited:
            record.collected = True
        else:
            record.unknown = True
            owner._poison_locked(_WorkRefusedError())

    _notify_resources(owner)


class _CmidAcquisition:
    """Retained before reserve call: row disposition survives a lost HTTP waiter."""

    def __init__(
        self,
        owner: _ServingWork,
        parent: _WorkRecord,
        site: _WorkSite,
        store: Any,
        key: tuple[str, str, str, str],
        now: Any,
    ) -> None:
        self.owner, self.parent, self.site = owner, parent, site
        self.store, self.key, self.now = store, key, now
        self.identity = (owner, parent, site, store, key, now)
        self.record: _WorkRecord | None = None
        self.loop: Any = None
        self.inserted: bool | None = None
        self.abandoned = False
        self.unknown = False
        self.failure: BaseException | None = None
        self.handoff: _WorkRecord | None = None
        self.ticket: _CmidReservation | None = None

    def pending(self) -> bool:
        if self.unknown or self.inserted is None:
            return True
        if self.inserted is False:
            return False
        return (
            self.ticket is None
            or self.ticket.claim is None
            or self.owner._pending_locked(self.ticket.claim)
        )


async def _reservation_worker(carrier: Any, site: _WorkSite, call: Any, *args: Any) -> Any:
    owner = _owner(carrier)
    if owner is None:
        return await asyncio.to_thread(call, *args)
    parent = _parent(owner)
    method = "reserve_cmid" if site is _WorkSite.CW017 else "reserve_phone_cmid"
    store = owner.context.store
    if (
        site not in (_WorkSite.CW017, _WorkSite.CW068)
        or len(args) != 6
        or type(call) is not MethodType
        or call.__self__ is not store
        or call.__func__ is not getattr(type(store), method)
        or any(type(part) is not str for part in args[:4])
    ):
        owner.request_stop(_WorkRefusedError())
        raise _WorkRefusedError
    record = owner._begin(site, "worker", parent)
    acquisition = _CmidAcquisition(owner, parent, site, store, args[:4], args[-1])
    acquisition.record = record
    record.cmid_acquisition = acquisition
    record.payload, record.args = call, args
    with owner._mutex:
        owner._cmid_acquisitions.append(acquisition)
    try:
        owner._spawn(record)
        result = await owner.collect(record)
        owner._check(record)
        _parent(owner)
        return result
    except BaseException:
        with owner._mutex:
            acquisition.abandoned = True
        _schedule_cmid_disposition(acquisition)
        raise


def _cmid_body_completed(record: _WorkRecord) -> None:
    acquisition = record.cmid_acquisition
    if acquisition is None:
        return
    owner = record.owner
    with owner._mutex:
        result = record.worker_result
        if (
            record.worker_failure is not None
            or type(result) is not tuple
            or len(result) != 2
            or type(result[1]) is not bool
        ):
            acquisition.unknown = True
            acquisition.failure = record.worker_failure or _WorkRefusedError()
            owner._poison_locked(acquisition.failure)
        else:
            acquisition.inserted = result[1]
    # Even if its supervisor was cancelled, physical completion has this exact
    # retained loop callback. No Future cancellation acts as this observation.
    try:
        acquisition.loop.call_soon_threadsafe(_schedule_cmid_disposition, acquisition)
    except BaseException as error:
        with owner._mutex:
            acquisition.unknown = True
            acquisition.failure = error
            owner._poison_locked(error)
        raise


def _schedule_cmid_disposition(acquisition: _CmidAcquisition) -> None:
    owner = acquisition.owner
    current = owner._context_current(draining=True)
    with owner._mutex:
        if (
            acquisition.unknown
            or acquisition.inserted is not True
            or acquisition.handoff is not None
            or acquisition.ticket is not None
        ):
            return
        if not (acquisition.abandoned or acquisition.parent.body_exited or owner.stopping):
            return
        if (
            not current
            or owner._transition is not None
            or getattr(owner._foreign_local, "busy", False)
        ):
            acquisition.unknown = True
            acquisition.failure = _WorkRefusedError()
            owner._poison_locked(acquisition.failure)
            return
        # Retain the disposition attempt before any bound-method lookup/factory.
        ticket = _CmidReservation(owner, acquisition.parent, acquisition.key, ())
        ticket.acquisition = acquisition
        acquisition.ticket = ticket
        record = _WorkRecord(owner, acquisition.site, "worker", acquisition.parent)
        record.cleanup = ticket
        ticket.claim = record
        owner._records.append(record)
        owner._transition = record.token
        owner._foreign_local.busy = True
    try:
        if acquisition.site is _WorkSite.CW017:
            record.cleanup_kind = "release"
            record.payload = acquisition.store.delete_cmid_reservation
            record.args = acquisition.key
        else:
            record.cleanup_kind = "finalize"
            record.payload = acquisition.store.finalize_phone_cmid
            record.args = acquisition.key
            record.kwargs = {
                "status": "unknown",
                "result_json": None,
                "updated_at": acquisition.now,
            }
        ticket.calls = (record.payload,) * 3
        ticket.identity = (owner, ticket.parent, ticket.key, ticket.calls)
        record.cleanup_arguments = (
            record.cleanup_kind, record.payload, record.args, tuple(record.kwargs.items())
        )
        owner._spawn(record)
    except BaseException as error:
        with owner._mutex:
            acquisition.unknown = True
            acquisition.failure = error
            owner._poison_locked(error)
            if owner._transition is record.token:
                owner._transition = None
            owner._foreign_local.busy = False
        # The retained source disposition is never retried. The original
        # caller's cancellation/failure remains the public causal outcome.


def _join_cmid_task(
    owner: _ServingWork, parent: _WorkRecord, record: _WorkRecord, key: Any
) -> None:
    site = _WorkSite.CW017 if record.site is _WorkSite.CW020 else _WorkSite.CW068
    with owner._mutex:
        matches = [
            acquisition
            for acquisition in owner._cmid_acquisitions
            if acquisition.parent is parent
            and acquisition.site is site
            and acquisition.key == key
            and acquisition.inserted is True
            and not acquisition.unknown
            and not acquisition.abandoned
            and acquisition.handoff is None
            and acquisition.ticket is None
        ]
        if len(matches) != 1:
            record.unknown = True
            owner._poison_locked(_WorkRefusedError())
            raise _WorkRefusedError
        acquisition = matches[0]
        acquisition.handoff = record
        record.cmid_acquisition = acquisition


class _ResourceSite(Enum):
    SERVER = "server"
    APP = "application"
    TLS = "tls-context"
    RUNNER = "runner"
    LISTENER_ALIAS = "listener-alias"
    LISTENER = "listener-site"
    MEDIA = "media-service"
    EXECUTOR = "media-executor"
    OPERATOR = "operator-service"
    OPERATOR_PARENT = "operator-parent"
    OPERATOR_DIRECTORY = "operator-directory"
    OPERATOR_SOCKET = "operator-socket"
    OPERATOR_ACCEPTOR = "operator-acceptor"
    OPERATOR_WRITER = "operator-writer"
    HTTP_TRANSPORT = "http-transport"
    PUBLICATION = "listener-record"


def _require_fixture_resource_policy(lifecycle: Any) -> None:
    # Exact Unix endpoint/umask concurrency, kernel handoff and runtime source
    # qualification is absent. No caller-supplied capability can replace it.
    raise _WorkRefusedError


class _OwnedResource:
    """Source acquisition journal, not a closure certificate or runtime authority."""

    def __init__(self, scope: _ServingResources, site: _ResourceSite, parent: Any) -> None:
        self.scope, self.site, self.parent = scope, site, parent
        self.object: Any = None
        self.acquiring = True
        self.acquired = False
        self.unknown = False
        self.failure: BaseException | None = None
        self.close_attempted = False
        self.close_returned = False
        self.close_failure: BaseException | None = None
        self.transferred = False
        self.transfer_target: Any = None
        self.start_attempted = False
        self.start_returned = False
        self.site_stop_attempted = False
        self.site_stop_returned = False
        self.wait_attempted = False
        self.wait_returned = False


class _ServingResources:
    """Retain every source-known object independently of legacy maps and counters."""

    def __init__(self, work: _ServingWork) -> None:
        if type(work) is not _ServingWork or work._resource_scope is not None:
            raise _WorkRefusedError
        self.work = work
        self.lifecycle = work.lifecycle
        self.resources: list[_OwnedResource] = []
        self.server: Any = None
        self.listener: _OwnedResource | None = None
        self.site: _OwnedResource | None = None
        self.runner: _OwnedResource | None = None
        self.operator: _OwnedResource | None = None
        self.start_failure: BaseException | None = None
        self.cleanup_failures: list[BaseException] = []
        self.publication: Any = None
        self.start: _WorkRecord | None = None
        self.background: list[_WorkRecord] = []
        self.serving_ready = False
        self.stop_started = False
        self.stop_returned = False
        self.context_close_started = False
        self.waiter: Any = None
        self.wait_loop: Any = None
        self.notification_unknown = False
        self.stop_signal_attempted = False
        self.stop_signal_returned = False
        self.loop: Any = None
        work._resource_scope = self
        self.loop = asyncio.get_running_loop()

    def check(self, *, draining: bool = False) -> None:
        work = self.work
        current = work._context_current(draining=draining)
        with work._mutex:
            if (work._resource_scope is not self or self.lifecycle is not work.lifecycle
                    or not current or (not draining and work.stopping)):
                error = _WorkRefusedError()
                work._poison_locked(error)
                raise error

    def attempt(self, site: _ResourceSite, parent: Any) -> _OwnedResource:
        self.check()
        if type(site) is not _ResourceSite:
            raise _WorkRefusedError
        with self.work._mutex:
            if (site not in (
                _ResourceSite.OPERATOR_WRITER, _ResourceSite.HTTP_TRANSPORT,
                _ResourceSite.OPERATOR_DIRECTORY,
            ) and any(owned.site is site for owned in self.resources)):
                error = _WorkRefusedError()
                self.work._poison_locked(error)
                raise error
            record = _OwnedResource(self, site, parent)
            self.resources.append(record)
        return record

    def returned(self, record: _OwnedResource, value: Any) -> None:
        # Retain the actual returned object before any post-return checks.
        with self.work._mutex:
            if record.scope is not self or not any(r is record for r in self.resources):
                raise _WorkRefusedError
            record.object = value
            record.acquiring = False
            record.acquired = True
        self.check()

    def failed(self, record: _OwnedResource, error: BaseException) -> None:
        with self.work._mutex:
            record.failure = error
            record.unknown = True
            record.acquiring = False
            self.work._poison_locked(error)
        self.notify()

    def owned(self, site: _ResourceSite, value: Any) -> _OwnedResource:
        self.check(draining=True)
        with self.work._mutex:
            matches = [r for r in self.resources if r.site is site and r.object is value]
            if len(matches) != 1 or not matches[0].acquired:
                raise _WorkRefusedError
            return matches[0]

    def retain_request_transport(self, request: Any) -> _OwnedResource:
        self.check(draining=True)
        with self.work._mutex:
            record = _OwnedResource(self, _ResourceSite.HTTP_TRANSPORT, self.server)
            record.request = request
            self.resources.append(record)
        try:
            app = next(r.object for r in self.resources if r.site is _ResourceSite.APP)
            if request.app is not app:
                raise _WorkRefusedError
            record.object = request.transport
            record.acquiring = False
            record.acquired = True
            if record.object is None:
                raise _WorkRefusedError
            return record
        except BaseException as error:
            self.failed(record, error)
            raise

    def notify(self) -> None:
        # Stop scheduling is retained before touching the loop, including a
        # thread-safe notification that throws after queueing the callback.
        signal = False
        with self.work._mutex:
            if self.work.stopping and not self.stop_signal_attempted:
                self.stop_signal_attempted = True
                signal = True
            waiter, loop = self.waiter, self.wait_loop
        if signal:
            try:
                self.loop.call_soon_threadsafe(
                    self.lifecycle.request_stop, self.work.first_failure or _WorkRefusedError()
                )
                self.stop_signal_returned = True
            except BaseException as error:
                with self.work._mutex:
                    self.notification_unknown = True
                    self.work._poison_locked(error)
        if waiter is None:
            return
        try:
            loop.call_soon_threadsafe(self._wake, waiter)
        except BaseException as error:
            with self.work._mutex:
                self.notification_unknown = True
                self.work._poison_locked(error)

    def _wake(self, waiter: Any) -> None:
        with self.work._mutex:
            if self.waiter is not waiter:
                return
            self.waiter = None
        if not waiter.done():
            waiter.set_result(None)

    async def wait_users(self) -> None:
        # The caller applies the existing shutdown bound. Registration is
        # closed first; notifications cause finite reinspection, never credits.
        while True:
            self.check(draining=True)
            for record in tuple(self.work._records):
                if (record.kind not in ("ingress", "p6") and record.task is not None
                        and not record.collected and record.body_exited):
                    try:
                        await self.work.collect(record)
                    except BaseException:
                        if not record.collected:
                            raise
            loop = asyncio.get_running_loop()
            waiter = loop.create_future()
            with self.work._mutex:
                if self.notification_unknown:
                    raise _WorkRefusedError
                if (self.work._resources
                        or any(record.unknown for record in self.work._records)
                        or any(r.unknown for r in self.resources)
                        or any(r.unknown for r in self.work._submissions)
                        or any(r.unknown for r in self.work._cmid_acquisitions)):
                    raise _WorkRefusedError
                pending = [r for r in self.work._records if self.work._pending_locked(r)]
                pending += [r for r in self.work._submissions if r.pending()]
                pending += [r for r in self.work._cmid_acquisitions if r.pending()]
                pending += [r for r in self.resources if r.site in (
                    _ResourceSite.OPERATOR_WRITER, _ResourceSite.HTTP_TRANSPORT,
                ) and not r.wait_returned]
                if not pending:
                    return
                self.waiter, self.wait_loop = waiter, loop
            await waiter


def _resources(carrier: Any, *, draining: bool = False) -> _ServingResources | None:
    fields = vars(carrier)
    work = fields.get("_fixture_work")
    if work is None:
        return _owner(carrier)  # None only for an ordinary, unbound component.
    if type(work) is not _ServingWork or type(work._resource_scope) is not _ServingResources:
        raise _WorkRefusedError
    scope = work._resource_scope
    scope.check(draining=draining)
    return scope


def _notify_resources(work: _ServingWork) -> None:
    scope = work._resource_scope
    if scope is not None:
        scope.notify()
