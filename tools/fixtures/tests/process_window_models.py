"""Explicit inert windows for source tests; importing this never opens an issuer.

No actual parent plan, process, native module, DB, socket or channel is qualified.
The context restores all three refusing source seams even when a test fails.
"""

from __future__ import annotations

import copy
import time
from types import SimpleNamespace

import native_media_process_windows as windows

MODEL_P4 = {"A1": "1" * 64, "A2": "2" * 64, "B1": "3" * 64}
MODEL_CAPS = {
    "commands": 64,
    "read_bytes": 67108864,
    "written_bytes": 8388608,
    "read_calls": 65536,
    "write_calls": 65536,
    "produced": 4,
    "messages": 64,
    "held": 128,
}


def command(value, role="A", sequence=1):
    result = copy.deepcopy(value)
    result.setdefault("role", role)
    result.setdefault("sequence", sequence)
    result.setdefault(
        "phase",
        "PRODUCE_SEED_GRANTS" if result["op"] in ("PRODUCE", "SEED", "GRANT") else "LATE_GUARDS",
    )
    result.setdefault("actor", "A1" if result["op"] in ("SEED", "GRANT") else None)
    result.setdefault("profile", None)
    result.setdefault("args", {})
    return result


class InertScope:
    def __init__(self):
        self.issued = set()
        self.retired = set()
        self.hook = self.readback_hook = None
        self.states = {}
        self.old = None
        self.seams = (
            self.issuer,
            self.readback,
            self.retirement,
            self.transition,
            self.acquisition,
            self.cleanup,
        )

    def __enter__(self):
        assert self.old is None
        self.old = (
            windows._require_root_continuation_issuer,
            windows._require_root_persistent_readback,
            windows._require_root_process_retirement,
            windows._require_root_transition,
            windows._require_root_handle_acquisition,
            windows._require_root_cleanup_ownership,
        )
        (
            windows._require_root_continuation_issuer,
            windows._require_root_persistent_readback,
            windows._require_root_process_retirement,
            windows._require_root_transition,
            windows._require_root_handle_acquisition,
            windows._require_root_cleanup_ownership,
        ) = self.seams
        return self

    def __exit__(self, *_args):
        (
            windows._require_root_continuation_issuer,
            windows._require_root_persistent_readback,
            windows._require_root_process_retirement,
            windows._require_root_transition,
            windows._require_root_handle_acquisition,
            windows._require_root_cleanup_ownership,
        ) = self.old
        self.old = None

    def issuer(self, issuance):
        assert type(issuance) is windows._RootContinuationIssuance and issuance in self.issued
        if issuance.journal.observation is None:
            issuance.journal.observation = self.observation(0, issuance.journal.snapshot())
        if self.hook is not None:
            self.hook(issuance)

    def readback(self, issuance, runtime, lease):
        self.issuer(issuance)
        if self.readback_hook is not None:
            self.readback_hook(runtime, lease)
        record = lease.record
        state = self.states[record.name]
        assert state == ("ACTIVE", record.user, record.iid, record.bearer)
        ctx = getattr(runtime, "ctx", None)
        if ctx is not None:
            assert ctx.iid == record.iid
            row = ctx.store.get_device(record.device)
            assert row is not None and row["state"] == "ACTIVE" and row["user_id"] == record.user

    def retirement(self, issuance, previous):
        self.issuer(issuance)
        assert type(previous) is windows.ProcessWindowLease
        assert previous in self.retired and previous.stopped

    @staticmethod
    def observation(revision, state):
        value = object.__new__(windows._ParentObservation)
        object.__setattr__(value, "revision", revision)
        object.__setattr__(value, "state", state)
        return value

    def transition(self, issuance, candidate):
        assert issuance in self.issued
        assert candidate.before is issuance.journal.observation
        assert candidate.revision == candidate.before.revision + 1
        assert candidate.after == issuance.journal.snapshot()
        return self.observation(candidate.revision, candidate.after)

    def acquisition(self, issuance, debt, handle):
        assert issuance in self.issued and debt.issuance is issuance
        assert debt.handle == handle and debt.returned_handle == handle

    def cleanup(self, issuance, debt):
        assert issuance in self.issued and debt.issuance is issuance
        assert debt in debt.ledger._handles and debt.state == "OWNED"

    def actor_records(self, journal, role, actors=None, iid=None):
        names = tuple(actors) if actors else (("A1", "A2") if role == "A" else ("B1",))
        for name in names:
            actor = actors.get(name) if actors else None
            record = windows._ActorRecord(
                name,
                role,
                actor.iid if actor else iid or "iid-" + role,
                actor.device_id if actor else "device-" + name,
                actor.user_id if actor else "user-" + name,
                actor.bearer if actor else "inert-private-bearer-" + name,
                MODEL_P4[name],
            )
            journal.actor_records[name] = record
            journal.enrolled[name] = record.p4
            self.states[name] = ("ACTIVE", record.user, record.iid, record.bearer)

    def window(
        self,
        commands,
        role="A",
        *,
        journal=None,
        positions=None,
        ordinal=None,
        actors=None,
        iid=None,
        enrolled=True,
        deadline=None,
        purpose=None,
        dispatcher_type=SimpleNamespace,
        runtime_type=None,
    ):
        if journal is None:
            journal = windows._JournalState(
                tuple(windows._command_bytes(c) for c in commands),
                MODEL_CAPS,
                deadline or time.monotonic() + 30,
                time.monotonic,
            )
        if positions is None:
            positions = tuple(range(len(commands)))
        if enrolled and not journal.actor_records:
            self.actor_records(journal, role, actors, iid)
        description = windows.WindowDescription(
            role,
            purpose or ("LISTENER" if ordinal else "STOPPED_PRODUCER_SEED"),
            ordinal,
            positions,
            object(),
            object(),
            object(),
            object(),
            journal.deadline,
        )
        issuance = object.__new__(windows._RootContinuationIssuance)
        issuance.journal, issuance.description = journal, description
        issuance.dispatcher_type, issuance.runtime_type = dispatcher_type, runtime_type
        journal.issuances[issuance] = description
        self.issued.add(issuance)
        return windows.ProcessWindowLease(issuance)

    def dispatcher(self, owner, spec, ledger):
        window = self.window(
            spec["commandPlan"], spec["role"], deadline=ledger.end, dispatcher_type=owner
        )
        return owner(spec, window.ledger, window=window)

    def bind_gate(self, dispatcher, gate):
        gate.window = dispatcher.window
        return gate

    def mutate_actor(self, gate, name):
        record = gate.window._journal.actor_records[name]
        object.__setattr__(record, "p4", "f" * 64)

    def attach(self, runtime, commands, role="A", enrolled=True, ordinal=None):
        actors = getattr(runtime, "actors", None)
        runtime.spec.setdefault("role", role)
        runtime.spec.setdefault("port", 54321)
        runtime.spec.setdefault("iid", "iid-" + role)
        if not hasattr(runtime, "actors"):
            runtime.actors = {}
        runtime.media = SimpleNamespace(
            Actor=lambda name, port, iid, device, user, bearer: SimpleNamespace(
                name=name, port=port, iid=iid, device_id=device, user_id=user, bearer=bearer
            )
        )
        if not hasattr(runtime, "minted"):
            runtime.minted = False
        if not hasattr(runtime, "routed"):
            runtime.routed = set()
        window = self.window(
            commands,
            role,
            actors=actors,
            iid=runtime.spec["iid"],
            enrolled=enrolled,
            runtime_type=type(runtime),
            ordinal=ordinal,
        )
        runtime.attach_continuation(window)
        runtime.ledger = window.ledger
        window.claim(SimpleNamespace())
        # Existing synthetic local actors are explicitly joined to issued model
        # leases. This is not a product continuation or native enrollment proof.
        for name in tuple(runtime.actors):
            window.actor(name).restored = True
        runtime._inert_scope = self
        return window

    def begin(self, runtime, command_value):
        return runtime.window.consume(runtime.window.dispatcher, command_value)
