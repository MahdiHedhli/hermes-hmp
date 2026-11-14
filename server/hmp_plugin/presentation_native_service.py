"""Owned native presentation acquisition/HTTP, bound by the adapter and server.

Original bearer auth is on the owning loop; real per-bot policy/home and fixed
source/projection work run in one retained native thread. Futures carry status
only. A result stays in its operation slot until explicitly abandoned or the
owned HTTP writer settles. Request cancellation is not thread drain.
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import os
import threading
from collections import deque
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

from . import wire
from .auth import AuthContext, Authenticator
from .contract import AuthzState, HmpError
from .presentation import HEX64, PROFILE
from .presentation_budget import PresentationWorkLedger
from .presentation_memory import PresentationMemoryBudget
from .presentation_native_claim import NativeReadRegistry, NativeSourceError
from .presentation_native_files import NativePresentationFileReader
from .presentation_native_http import (
    NATIVE_RESPONSE_TYPE,
    NativePresentationHttpWrite,
    NativePresentationStreamAbortedError,
    native_http_mode_available,
)
from .presentation_native_projection import NativePresentationProjector


class NativePresentationUnavailableError(ValueError):
    def __init__(self, reason="unavailable"):
        super().__init__(reason)
        self.reason = reason


class _Handle:
    """Opaque identity only: no result, authority or service graph in a future."""

    __slots__ = ()


class _PolicyRefusalError(ValueError):
    def __init__(self, state):
        super().__init__("native_policy_refused")
        self.state = state


class _ActorRefusalError(ValueError):
    def __init__(self, status):
        super().__init__("native_actor_refused")
        self.status = status


@dataclass(frozen=True, repr=False)
class _Authority:
    service: object
    listener: object
    bridge: object
    identity: object
    actor: AuthContext
    profile: str
    home: str


@dataclass(eq=False, repr=False)
class _Operation:
    handle: _Handle
    profile: str
    kind: str
    authorization: str
    instance: str
    actor: AuthContext
    deadline: float
    observed_at: int
    revision: str | None
    future: asyncio.Future
    memory: PresentationMemoryBudget = field(default_factory=PresentationMemoryBudget)
    state: str = "waiting"
    outcome: str = "unavailable"
    retired: bool = False
    worker: threading.Thread | None = None
    entered: bool = False
    start_uncertain: bool = False
    joined: bool = False
    join_unknown: bool = False
    cleanup_unknown: bool = False
    claim: object = None
    result: object = None
    timer: object = None
    poll: object = None
    writer: object = None
    native_context: object = None


class NativePresentationOwner:
    """Retain this on the actual adapter across listener replacement.

    A new six-slot generation is forbidden while any old thread/result/debt
    survives. The actual adapter retains this owner before service binding.
    """

    def __init__(self):
        self._service = None

    def bind(self, ctx, *, current, worker_current):
        if self._service is not None and not self._service.drained:
            raise NativePresentationUnavailableError("previous_generation_not_drained")
        service = NativePresentationService(ctx, current=current, worker_current=worker_current)
        self._service = service
        return service


class NativePresentationService:
    def __init__(self, ctx, *, current, worker_current):
        wire.require_iid(ctx.iid)
        if not native_http_mode_available():
            raise NativePresentationUnavailableError("http_mode_unavailable")
        self._ctx, self._current = ctx, current
        # Native setup must supply a cheap thread-safe original listener fence.
        # No request callback or event-loop-only predicate may substitute for it.
        self._worker_current = worker_current
        self._loop = asyncio.get_running_loop()
        self._clock = self._loop.time
        self._bridge, self._store, self._identity = ctx.bridge, ctx.store, ctx.identity
        self._iid = ctx.iid
        if not callable(self._bridge.authz_state) or not callable(self._bridge._profile_home):
            raise NativePresentationUnavailableError()
        self._retired = False
        self._drain_event = asyncio.Event()
        self._ops = {}
        self._queue = deque()
        self._profiles = {}
        self._registry = NativeReadRegistry(self, object(), self._clock)
        # Actual fixed backend and installed parser are bound before admission.
        self._reader = NativePresentationFileReader(self._registry)
        self._projector = NativePresentationProjector(self._registry, self._reader)
        self._thread_type = threading.Thread
        self._response_type = NATIVE_RESPONSE_TYPE

    def _local(self):
        try:
            return (
                not self._retired
                and asyncio.get_running_loop() is self._loop
                and self._current() is True
                and self._worker_current() is True
                and self._ctx.bridge is self._bridge
                and self._ctx.store is self._store
                and self._ctx.identity is self._identity
                and self._ctx.iid == self._iid
                and self._identity.still_current() is True
            )
        except Exception:
            return False

    @property
    def available(self):
        return self._local()

    @property
    def drained(self):
        return self._retired and not self._ops

    def _authenticate(self, op):
        if not self._local() or op.retired or self._clock() >= op.deadline:
            return "unavailable"
        return self._actor_current(op)

    def _actor_current(self, op):
        try:
            actor = Authenticator(self._store, self._iid, self._ctx.now).authenticate(
                op.authorization, op.instance
            )
            return "ready" if actor == op.actor else "unauthenticated"
        except HmpError as error:
            return error.code.value
        except Exception:
            return "unavailable"

    def submit(self, authorization, instance, profile, *, kind="metadata", revision=None):
        deadline = self._clock() + 2.0
        if not self._local():
            raise NativePresentationUnavailableError()
        if (
            type(profile) is not str
            or PROFILE.fullmatch(profile) is None
            or type(kind) is not str
            or kind not in ("metadata", "avatar")
            or type(authorization) is not str
            or len(authorization) > 256
            or type(instance) is not str
            or len(instance) > 256
            or (
                revision is not None
                and (type(revision) is not str or HEX64.fullmatch(revision) is None)
            )
        ):
            raise NativePresentationUnavailableError("bad_request")
        actor = Authenticator(self._store, self._iid, self._ctx.now).authenticate(
            authorization, instance
        )
        if type(actor) is not AuthContext or any(
            type(x) is not str or len(x) > 512
            for x in (actor.device_id, actor.user_id, actor.family_id)
        ):
            raise NativePresentationUnavailableError()
        # UTF8 logical descriptor; raw source/parser/result data are never queued.
        size = sum(
            len(x.encode("utf-8"))
            for x in (
                authorization,
                instance,
                profile,
                actor.device_id,
                actor.user_id,
                actor.family_id,
                revision or "",
                kind,
            )
        )
        if size > 4096:
            raise NativePresentationUnavailableError("bad_request")
        if profile in self._profiles or len(self._queue) >= 16 or len(self._ops) >= 22:
            raise NativePresentationUnavailableError("busy")
        handle = _Handle()
        op = _Operation(
            handle,
            profile,
            kind,
            authorization,
            instance,
            actor,
            deadline,
            self._ctx.now(),
            revision,
            self._loop.create_future(),
        )
        # Preserve original native instance/profile secret-scope like the other
        # server reads. This borrows trusted runtime context references; no HMP
        # source/result bytes are placed in ContextVars or copied into the queue.
        op.native_context = contextvars.copy_context()
        self._registry._begin(self, op, profile, deadline)
        self._ops[handle] = op
        self._profiles[profile] = handle
        self._queue.append(handle)
        op.timer = self._loop.call_at(deadline, self._expire, handle)
        self._dispatch()
        return handle

    def _capacity(self, kind):
        active = [op for op in self._ops.values() if op.state != "waiting"]
        return len(active) < 6 and sum(op.kind == kind for op in active) < (
            4 if kind == "metadata" else 2
        )

    def _dispatch(self):
        if self._retired:
            return
        for handle in tuple(self._queue):
            op = self._ops.get(handle)
            if op is None:
                continue
            if self._clock() >= op.deadline:
                self._retire_operation(op)
            elif self._capacity(op.kind):
                self._queue.remove(handle)
                op.state = "running"
                try:
                    op.worker = self._thread_type(
                        target=op.native_context.run,
                        args=(self._work, op),
                        name="hmp-native-presentation",
                        daemon=False,
                    )
                except BaseException:
                    op.joined = True  # no start call, no native thread/effect
                    self._settle(op)
                    continue
                try:
                    op.worker.start()
                except BaseException:
                    # Could have launched: only observed target entry+join may settle it.
                    op.start_uncertain = True
                    op.outcome = "unavailable"
                    self._retire_operation(op)
                self._schedule_reap(handle)

    def _tick_worker(self, op):
        if (
            self._retired
            or op.retired
            or not self._clock() < op.deadline
            or self._ctx.bridge is not self._bridge
            or self._ctx.store is not self._store
            or self._ctx.identity is not self._identity
            or self._ctx.iid != self._iid
            or self._worker_current() is not True
            or self._identity.still_current() is not True
        ):
            raise NativeSourceError()

    def _home(self, op):
        self._tick_worker(op)
        # Store's shared connection is explicitly thread-safe (cached statements
        # disabled). Reauthenticate after queue/native waits, before home/source.
        actor = self._actor_current(op)
        if actor != "ready":
            raise _ActorRefusalError(actor)
        try:
            state = self._bridge.authz_state(op.actor.user_id, op.profile)
        except BaseException:
            state = AuthzState.UNVERIFIABLE
        if type(state) is not AuthzState or state is not AuthzState.AUTHORIZED:
            raise _PolicyRefusalError(
                state if type(state) is AuthzState else AuthzState.UNVERIFIABLE
            )
        self._tick_worker(op)
        actor = self._actor_current(op)
        if actor != "ready":
            raise _ActorRefusalError(actor)
        home = self._bridge._profile_home(op.profile)
        if not isinstance(home, Path) or not home.is_absolute():
            raise NativeSourceError()
        self._tick_worker(op)
        return str(home)

    def _work(self, op):
        op.entered = True
        outcome = "unavailable"
        try:
            home = self._home(op)
            authority = _Authority(
                self, self._ctx, self._bridge, self._identity, op.actor, op.profile, home
            )
            if self._home(op) != home:
                raise NativeSourceError()
            op.claim = self._registry._issue(
                self, op, home=home, uid=os.geteuid(), gid=os.getegid(), authority=authority
            )
            work = PresentationWorkLedger(clock=self._clock, deadline=op.deadline)
            # Adopt the actual return before another call/cleanup can fail.
            op.result = self._projector.run(
                op.claim,
                work,
                op.memory,
                iid=self._iid,
                observed_at=op.observed_at,
                expected_avatar_revision=op.revision,
            )
            if self._home(op) != home:
                raise NativeSourceError()
            self._reader.recheck(op.claim, work, op.result._source)
            if self._home(op) != home:
                raise NativeSourceError()
            self._tick_worker(op)
            outcome = "ready"
        except _PolicyRefusalError as error:
            outcome = "bot_" + error.state.value
        except _ActorRefusalError as error:
            outcome = error.status
        except NativeSourceError as error:
            if error.reason == "native_avatar_revision_changed":
                outcome = "not_found"
        except BaseException:
            outcome = "unavailable"
        # Cleanup is loop-owned AFTER actual observed thread termination. The
        # operation retains the actual result through every subsequent failure.
        op.outcome = outcome
        # Owner retains actual worker/result/debt even if its loop closed.
        with suppress(BaseException):
            self._loop.call_soon_threadsafe(self._schedule_reap, op.handle)

    def _schedule_reap(self, handle):
        op = self._ops.get(handle)
        if op is not None and op.poll is None and not op.joined:
            op.poll = self._loop.call_later(0.005, self._reap, handle)

    def _reap(self, handle):
        op = self._ops.get(handle)
        if op is None or op.joined or op.join_unknown:
            return
        op.poll = None
        try:
            if op.worker.is_alive():
                self._schedule_reap(handle)
                return
            if op.start_uncertain and not op.entered:
                return  # no proof of either failed start or actual target termination
            op.worker.join(timeout=0)
            if op.worker.is_alive():
                op.join_unknown = True
                return
            op.joined = True
            op.native_context = None
        except BaseException:
            op.join_unknown = True
            return
        self._settle(op)
        self._dispatch()

    def _settle(self, op):
        if not op.joined:
            return
        try:
            if op.retired or self._retired:
                self._discard(op)
            elif op.outcome != "ready" and not self._drop_payload(op):
                op.retired = True
                self._registry._retire(self, op)
            else:
                op.state = "complete"
        except BaseException:
            op.cleanup_unknown = op.retired = True
            op.state, op.outcome = "debt", "unavailable"
        finally:
            if not op.future.done():
                op.future.set_result(None)

    def _drop_payload(self, op):
        if op.cleanup_unknown:
            return False
        try:
            if op.result is not None:
                op.result.discard()
                op.result = None
            if op.memory.snapshot()[:2] != (0, 0):
                raise NativeSourceError()
        except BaseException:
            op.cleanup_unknown = True
            op.state, op.outcome = "debt", "unavailable"
            return False
        return True

    def _discard(self, op):
        if not op.joined:
            return False
        if op.writer is not None:
            if not op.writer.settled or op.writer.unknown:
                op.state = "writer_debt" if op.retired else "emitting"
                return False
            try:
                op.writer.release()
            except BaseException:
                op.cleanup_unknown = True
                op.state, op.outcome = "debt", "unavailable"
                return False
        if not self._drop_payload(op):
            return False
        try:
            self._registry._retire(self, op)
            self._registry._forget_closed(self, op)
        except BaseException:
            op.state = "debt"
            op.cleanup_unknown = True
            return False
        for timer in (op.timer, op.poll):
            if timer is not None:
                timer.cancel()
        if op.handle in self._queue:
            self._queue.remove(op.handle)
        self._profiles.pop(op.profile, None)
        self._ops.pop(op.handle, None)
        op.authorization = ""
        op.native_context = None
        if self.drained:
            self._drain_event.set()
        return True

    def _retire_operation(self, op):
        op.retired = True
        if op.state == "waiting":
            op.joined = True  # never constructed/started a worker
        try:
            self._registry._retire(self, op)
            if op.writer is not None and not op.writer.settled:
                op.writer.abort()
            if op.joined:
                self._discard(op)
        except BaseException:
            op.cleanup_unknown = True
            op.state, op.outcome = "debt", "unavailable"
        finally:
            if not op.future.done():
                op.future.set_result(None)

    def _expire(self, handle):
        op = self._ops.get(handle)
        if op is not None:
            op.outcome = "unavailable"
            self._retire_operation(op)
            self._dispatch()

    async def wait(self, handle):
        op = self._ops.get(handle) if type(handle) is _Handle else None
        if op is None:
            return "unavailable"
        try:
            await asyncio.wait_for(asyncio.shield(op.future), max(0.0, op.deadline - self._clock()))
        except TimeoutError:
            self.abandon(handle)
            return "unavailable"
        except asyncio.CancelledError:
            self.abandon(handle)
            raise
        if op.retired:
            return "unavailable"
        # Fresh original actor authority precedes *all* precise status disclosure,
        # including native bot denials and stale revisions, not only payloads.
        current = self._authenticate(op)
        if current != "ready":
            self.abandon(handle)
            return current
        return op.outcome

    def abandon(self, handle):
        op = self._ops.get(handle) if type(handle) is _Handle else None
        if op is not None:
            self._retire_operation(op)
            self._dispatch()

    def _request_matches(self, op, request):
        try:
            return (
                request.method == "GET"
                and request.match_info.get("p") == op.profile
                and request.headers.getall("Authorization", []) == [op.authorization]
                and request.headers.getall("HMP-Instance", []) == [op.instance]
                and (op.kind != "avatar" or request.match_info.get("revision") == op.revision)
            )
        except Exception:
            return False

    def _write_current(self, op, writer, *, transport_required=True):
        try:
            return (
                self._ops.get(op.handle) is op
                and op.writer is writer
                and not op.retired
                and self._local()
                and self._clock() < writer.deadline
                and self._actor_current(op) == "ready"
                and self._request_matches(op, writer.request)
                and (
                    not transport_required
                    or (
                        writer.transport is not None
                        and writer.request.transport is writer.transport
                        and not writer.transport.is_closing()
                    )
                )
            )
        except Exception:
            return False

    def _writer_finished(self, handle):
        op = self._ops.get(handle)
        if op is None or op.writer is None:
            return
        if op.retired or op.writer.status != "sent" or op.writer.unknown:
            self._retire_operation(op)
        else:
            self._discard(op)
        self._dispatch()

    def _output_shape(self, op):
        result = op.result
        if result is None or type(result.metadata) is not bytes or len(result.metadata) > 4096:
            raise NativePresentationUnavailableError()
        if op.kind == "metadata":
            return "application/json", len(result.metadata)
        if op.revision is None:
            raise NativePresentationUnavailableError("bad_request")
        avatar = json.loads(result.metadata).get("avatar")
        if avatar is None or result.avatar is None:
            raise NativePresentationUnavailableError("not_found")
        if (
            type(avatar) is not dict
            or avatar.get("revision") != op.revision
            or avatar.get("mime") not in ("image/png", "image/jpeg", "image/webp")
            or type(result.avatar) is not bytes
            or not 1 <= len(result.avatar) <= 2_000_000
            or avatar.get("bytes") != len(result.avatar)
        ):
            raise NativePresentationUnavailableError()
        return avatar["mime"], len(result.avatar)

    async def emit(self, handle, request):
        op = self._ops.get(handle) if type(handle) is _Handle else None
        if op is None or not op.joined or op.state != "complete" or op.outcome != "ready":
            raise NativePresentationUnavailableError()
        status = self._authenticate(op)
        if status != "ready" or not self._request_matches(op, request):
            self.abandon(handle)
            raise NativePresentationUnavailableError(
                status if status != "ready" else "unauthenticated"
            )
        mime, length = self._output_shape(op)
        writer = NativePresentationHttpWrite()
        op.writer, op.state = writer, "emitting"  # adopt before any prepare/task/lease effect
        if op.timer is not None:
            op.timer.cancel()
        try:
            started = writer.start(self, op, request, mime, length)
        except BaseException:
            writer.start_unknown = True
            started = False
        if not started:
            self.abandon(handle)
            if writer.unknown or writer.attempted:
                raise NativePresentationStreamAbortedError()
            raise NativePresentationUnavailableError()
        try:
            await asyncio.wait_for(
                asyncio.shield(writer.signal), max(0.0, writer.deadline - self._clock())
            )
        except asyncio.CancelledError:
            self.abandon(handle)
            raise
        except TimeoutError:
            self.abandon(handle)
            raise NativePresentationStreamAbortedError() from None
        if writer.status != "sent" or writer.unknown:
            self.abandon(handle)
            raise NativePresentationStreamAbortedError()
        return writer.response

    def retire(self):
        self._retired = True
        self._registry._retire(self)
        for op in tuple(self._ops.values()):
            self._retire_operation(op)
        if self.drained:
            self._drain_event.set()

    async def close_and_join(self, wait_seconds=2.0):
        if type(wait_seconds) is not float or not 0 <= wait_seconds <= 2.0:
            raise NativePresentationUnavailableError()
        self.retire()
        deadline = self._clock() + wait_seconds
        while self._ops and self._clock() < deadline:
            for handle in tuple(self._ops):
                self._reap(handle)
            await asyncio.sleep(0.005)
        return self.drained

    async def wait_drained(self):
        """Dependency owner waits without renewing work or retrying unknown cleanup.

        Actual worker/writer completion callbacks settle known work. Unknown
        start/join/close debt deliberately keeps this original generation alive.
        """
        if not self._retired:
            raise NativePresentationUnavailableError("service_not_retired")
        await self._drain_event.wait()
        if not self.drained:
            raise NativePresentationUnavailableError("drain_unavailable")
