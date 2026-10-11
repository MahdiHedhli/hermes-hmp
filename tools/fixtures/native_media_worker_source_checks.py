"""Inert selected-function and published 37-step source checks; no native/socket/SDK."""

import asyncio
import base64
import copy
import hashlib
import importlib.machinery
import importlib.util
import json
import pathlib
import runpy
import sys
import time
from types import FunctionType, ModuleType, SimpleNamespace

HERE = pathlib.Path(__file__).resolve().parent
WORKER = HERE / "native_media_worker.py"
ORCH = HERE / "python8_orchestrator.py"
ORCH_TEST = ORCH.parent / "tests" / "test_python8_orchestrator.py"
assert (
    hashlib.sha256(ORCH.read_bytes()).hexdigest()
    == "1931dfc245ea1a4d60e2c40b5d16f7a758b859d420745539f748ee0c61aa5380"
)
assert (
    hashlib.sha256(ORCH_TEST.read_bytes()).hexdigest()
    == "3354a5d0597b0f1de1b90550e6ac0bcac1fab39bbfa393c74dfc5a9d15b48721"
)


def manual_run(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    raise AssertionError("unexpected suspension")


async def manual_wait_for(coroutine, **kwargs):
    assert set(kwargs) == {"timeout"} and kwargs["timeout"] > 0
    return await coroutine


w = runpy.run_path(str(WORKER), run_name="_inert_worker_source")
w["Dispatcher"].dispatch.__globals__["asyncio"] = SimpleNamespace(
    wait_for=manual_wait_for, CancelledError=asyncio.CancelledError
)
Gate, RefusalError, Dispatcher, Ledger = (
    w[n] for n in ("LatePermitGate", "RefusalError", "Dispatcher", "Ledger")
)


# Published test module contains only source fakes.
# Its collected test function is not called here.
def _existing_published_cases(registry):
    """Reuse one collector-owned module; never replace another module's ownership."""
    assert type(registry) is dict and len(registry) <= 16384
    matches = []
    for name, module in tuple(registry.items()):
        if type(module) is not ModuleType:
            continue
        namespace = vars(module)
        if namespace.get("__file__") == str(ORCH_TEST):
            matches.append((name, module))
    assert len(matches) <= 1, "ambiguous_published_test_modules"
    if not matches:
        return None
    name, module = matches[0]
    namespace = vars(module)
    spec = namespace.get("__spec__")
    assert type(spec) is importlib.machinery.ModuleSpec
    assert spec.origin == str(ORCH_TEST) and spec.name == name
    assert namespace.get("__name__") == name and spec.loader is not None
    orchestrator = registry.get("_hmp_python8_orchestrator_v2_fixture")
    assert type(orchestrator) is ModuleType and namespace.get("m") is orchestrator
    source = vars(orchestrator)
    source_spec = source.get("__spec__")
    assert type(source_spec) is importlib.machinery.ModuleSpec
    assert source.get("__file__") == str(ORCH)
    assert source.get("__name__") == "_hmp_python8_orchestrator_v2_fixture"
    assert source_spec.name == "_hmp_python8_orchestrator_v2_fixture"
    assert source_spec.origin == str(ORCH) and source_spec.loader is not None
    assert namespace.get("spec") is source_spec
    for function_name in ("create", "run_all", "test_python8_inert_causal_groups"):
        function = namespace.get(function_name)
        assert type(function) is FunctionType
        assert function.__globals__ is namespace
        assert function.__code__.co_filename == str(ORCH_TEST)
    fake_port = namespace.get("FakePort")
    assert type(fake_port) is type and fake_port.__module__ == name
    owner = source.get("PhaseOrchestrator")
    assert type(owner) is type and owner.__module__ == source_spec.name
    assert type(owner.__init__) is FunctionType
    assert owner.__init__.__globals__ is source
    assert owner.__init__.__code__.co_filename == str(ORCH)
    return module


def _published_cases():
    # The two exact source hashes above are mandatory before either branch.
    existing = _existing_published_cases(sys.modules)
    if existing is not None:
        return existing
    test_name = "_inert_published_python8_cases"
    assert test_name not in sys.modules, "unowned_test_namespace"
    assert "_hmp_python8_orchestrator_v2_fixture" not in sys.modules, "unowned_orchestrator"
    spec = importlib.util.spec_from_file_location(test_name, ORCH_TEST)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # This installs only our previously absent slot. Failure retains it;
    # never erase/pop/replace a collected or partially loaded module.
    sys.modules[test_name] = module
    spec.loader.exec_module(module)
    assert _existing_published_cases(sys.modules) is module
    return module


m = _published_cases()
assert len(m.m.STEPS) == 37
assert len([s for s in m.m.STEPS if s.case in ("NM07", "NM08") and s.action == "fetch"]) == 6
full = m.create(port=m.FakePort())
selection = m.run_all(full)
assert selection is not None and len(full.port.calls) == 37

REF = "R" * 43
ROOT = "/hmp/v1/bots/media-alpha/media/"
SOURCE = "a" * 64
PARENT = "b" * 64
GEN = "c" * 64
P4 = {"A1": "1" * 64, "A2": "2" * 64, "B1": "3" * 64}
KINDS = [
    ("NM07", "before_revoke", "A1", "A"),
    ("NM07", "after_revoke", "A1", "A"),
    ("NM07", "control_revoke", "A2", "A"),
    ("NM08", "before_rotate", "B1", "B"),
    ("NM08", "after_rotate", "B1", "B"),
    ("NM08", "control_rotate", "A1", "A"),
]


def fixture(role):
    iid, port = ("iid-A", 21211) if role == "A" else ("iid-B", 21212)
    binds = [
        {"op": "BIND_ACTOR", "actor": actor, "args": {"p4CaptureSHA256": P4[actor]}}
        for actor in (("A1", "A2") if role == "A" else ("B1",))
    ]
    data = {
        "role": role,
        "iid": iid,
        "port": port,
        "lateGeneration": GEN,
        "commandPlan": binds,
        "gates": {"parentAdmission": {"SHA256": PARENT}, "sourceGraph": {"SHA256": SOURCE}},
    }
    entries = []
    for i, (case, key, actor, worker) in enumerate(KINDS):
        if worker != role:
            continue
        entries.append(
            {
                "case": case,
                "key": key,
                "actor": actor,
                "role": role,
                "profile": "media-alpha",
                "path": ROOT + (REF if not key.startswith("control_") else "C" * 43),
                "oldRef": REF,
                "permit": format(i + 1, "064x"),
                "iid": iid,
                "port": port,
                "actorP4SHA256": P4[actor],
                "sourceGraphSHA256": SOURCE,
            }
        )
    body = {
        "format": "native-media-late-permit-plan-v1",
        "generation": GEN,
        "parentAdmissionSHA256": PARENT,
        "entries": entries,
    }
    return data, body


def make(role):
    data, body = fixture(role)
    return Gate(json.dumps(body).encode(), data), body, data


def refuse(fn):
    try:
        fn()
    except RefusalError:
        return
    raise AssertionError("expected refusal")


def cmd(row):
    return {
        "op": "LATE_OWN_READ",
        "role": row["role"],
        "actor": row["actor"],
        "profile": row["profile"],
        "phase": "LATE_GUARDS",
        "args": {"path": row["path"], "permit": row["permit"]},
    }


def obs(status=200, body=b"PNG", typ="image/png"):
    return {
        "event": "actual_pinned_http_observation",
        "status": status,
        "rawBodyB64": base64.b64encode(body).decode(),
        "contentType": typ,
        "bodySHA256": hashlib.sha256(body).hexdigest(),
        "bodyBytes": len(body),
    }


def mutation_obs(case, before_sha):
    """Inert schema fixture only; no native or parent qualification proof."""
    union = {"event": "actual_native_union_readback", "noIndependentGrantObserved": True}
    before = {"approved": True, "authz": "authorized", "noIndependentGrant": True}
    if case == "NM07":
        after = {"approved": False, "authz": "pending_operator", "noIndependentGrant": True}
        result = {
            "event": "public_native_revoke_observation",
            "unionBefore": union,
            "unionAfter": union,
            "actualAuthzAfter": "pending_operator",
        }
    else:
        key_hash = w["_opaque_native_hash"]("session-key", "key")
        before.update(
            sessionKeySHA256=key_hash,
            sessionIdSHA256=w["_opaque_native_hash"]("session-id", "ses1_" + "A" * 22),
        )
        after = {
            "approved": True,
            "authz": "authorized",
            "noIndependentGrant": True,
            "sessionKeySHA256": key_hash,
            "sessionIdSHA256": w["_opaque_native_hash"]("session-id", "ses1_" + "B" * 22),
        }
        result = {
            "event": "actual_running_public_store_rotation",
            "oldSessionId": "ses1_" + "A" * 22,
            "newSessionId": "ses1_" + "B" * 22,
            "sessionKeySHA256": key_hash,
            "unionBefore": union,
            "unionAfter": union,
        }
    evidence = {"case": case, "actorScopeSHA256": "e" * 64, "before": before, "after": after}
    result.update(
        nativeEvidence=evidence,
        beforeCaptureSHA256=before_sha,
        afterNativeSHA256=w["native_evidence_hash"](case, before_sha, evidence),
    )
    return result


checks = []
a, ap, ad = make("A")
b, bp, bd = make("B")
assert len(a.rows) == 4 and len(b.rows) == 2
checks.append("role_inventory")
for role in "AB":
    data, body = fixture(role)
    for mutation in (
        "generation",
        "parent",
        "source",
        "duplicate",
        "wrongrole",
        "wrongref",
        "wrongpath",
        "wronglease",
    ):
        x = copy.deepcopy(body)
        if mutation == "generation":
            x["generation"] = "f" * 64
        if mutation == "parent":
            x["parentAdmissionSHA256"] = "f" * 64
        if mutation == "source":
            x["entries"][0]["sourceGraphSHA256"] = "f" * 64
        if mutation == "duplicate":
            x["entries"].append(copy.deepcopy(x["entries"][0]))
        if mutation == "wrongrole":
            x["entries"][0]["role"] = "B" if role == "A" else "A"
        if mutation == "wrongref":
            x["entries"][0]["oldRef"] = "Z" * 43
        if mutation == "wrongpath":
            x["entries"][0]["path"] = "/outside"
        if mutation == "wronglease":
            x["entries"][0]["actorP4SHA256"] = "f" * 64
        refuse(lambda x=x, data=data: Gate(json.dumps(x).encode(), data))
        checks.append(role + mutation)

a, ap, ad = make("A")
rows = {r["key"]: r for r in ap["entries"]}
before = rows["before_revoke"]
after = rows["after_revoke"]
control = rows["control_revoke"]
refuse(lambda: a.pre({"op": "REVOKE"}))
checks.append("mutation_before_missing")
refuse(lambda: a.pre(cmd(after)))
checks.append("after_before_missing")
refuse(lambda: a.pre(cmd(control)))
checks.append("control_before_missing")
wrong = cmd(before)
wrong["args"]["path"] = ROOT + "Z" * 43
refuse(lambda: a.pre(wrong))
checks.append("wrong_target")
r = a.pre(cmd(before))
a.post(cmd(before), r, obs())
checks.append("before_creates_seal")
refuse(lambda: a.pre(cmd(before)))
checks.append("before_replay")
refuse(lambda: a.pre(cmd(after)))
checks.append("after_mutation_missing")
mutation = {
    "op": "REVOKE",
    "phase": "LATE_GUARDS",
    "role": "A",
    "actor": "A1",
    "profile": "media-alpha",
}
ticket = a.pre(mutation)
a.post(mutation, ticket, mutation_obs("NM07", ticket[3][1]))
r = a.pre(cmd(after))
a.post(cmd(after), r, obs(403, b"denied", "application/json"))
r = a.pre(cmd(control))
a.post(cmd(control), r, obs())
checks.append("revoke_after_control_order")
b, bp, bd = make("B")
br = {r["key"]: r for r in bp["entries"]}
r = b.pre(cmd(br["before_rotate"]))
b.post(cmd(br["before_rotate"]), r, obs())
rotation = {
    "op": "ROTATE",
    "phase": "LATE_GUARDS",
    "role": "B",
    "actor": "B1",
    "profile": "media-alpha",
}
ticket = b.pre(rotation)
b.post(rotation, ticket, mutation_obs("NM08", ticket[3][1]))
r = b.pre(cmd(br["after_rotate"]))
b.post(cmd(br["after_rotate"]), r, obs(404, b"missing", "application/json"))
checks.append("rotate_before_after")
# A's NM08 control is a root-issued cross-worker permit. Only the separately
# reviewed parent can bind B's fresh before/native action/after proof to it.
a, ap, ad = make("A")
cross = next(x for x in ap["entries"] if x["key"] == "control_rotate")
r = a.pre(cmd(cross))
a.post(cmd(cross), r, obs())
checks.append("cross_worker_boundary_unqualified")
for bad in [obs(404), {**obs(), "bodySHA256": "0" * 64}, {**obs(), "bodyBytes": 4}]:
    a, ap, ad = make("A")
    row = next(x for x in ap["entries"] if x["key"] == "before_revoke")
    x = a.pre(cmd(row))
    refuse(lambda bad=bad, a=a, row=row, x=x: a.post(cmd(row), x, bad))
    checks.append("bad_before_response")
# Direct actual dispatcher method; bind_runtime is replaced only by a pure fake.
a, ap, ad = make("A")
row = next(x for x in ap["entries"] if x["key"] == "before_revoke")
command = {**cmd(row), "sequence": 1}


class FakeRuntime:
    async def action(self, command):
        return obs()


ledger = Ledger(time.monotonic() + 5)
D = Dispatcher(
    {
        "format": "native-media-worker-input-v1",
        "role": "A",
        "commandPlan": [command],
        "phaseEnds": {"LATE_GUARDS": time.monotonic() + 4},
    },
    ledger,
)


def inert_bind():
    D.runtime = FakeRuntime()
    D.late = a


D.bind_runtime = inert_bind
result = manual_run(D.dispatch(command))
assert result["status"] == "OBSERVATION_ONLY" and a.before["NM07"][1] == obs()["bodySHA256"]
assert manual_run(D.dispatch(command))["status"] == "FAILED_UNQUALIFIED" and D.failed
checks.append("actual_dispatcher_oneuse")
for op, role, actor, profile in (
    ("REVOKE", "A", "A2", "media-alpha"),
    ("REVOKE", "A", "A1", "media-beta"),
    ("ROTATE", "B", "B1", "media-beta"),
    ("REVOKE", "B", "B1", "media-alpha"),
):
    worker = "A" if op == "REVOKE" else "B"
    local, lp, _ = make(worker)
    target = next(x for x in lp["entries"] if x["key"].startswith("before_"))
    first = {**cmd(target), "sequence": 1}
    bad = {
        "sequence": 2,
        "phase": "LATE_GUARDS",
        "op": op,
        "role": role,
        "actor": actor,
        "profile": profile,
        "args": {} if op == "REVOKE" else {"chatId": "chat", "oldSessionId": "ses1_" + "A" * 22},
    }
    # The wrong-role tuple is a pure local-gate check because the dispatcher's
    # worker-role check deliberately rejects it even earlier.
    if role != worker:
        local.pre(first)
        refuse(lambda bad=bad, local=local: local.pre(bad))
        checks.append("wrong_mutation_role_pre_runtime")
        continue
    calls = []

    class CountRuntime:
        async def action(self, command, *, before_capture_sha=None, calls=calls, op=op):
            calls.append(command["op"])
            return (
                obs()
                if command["op"] == "LATE_OWN_READ"
                else mutation_obs("NM07" if op == "REVOKE" else "NM08", before_capture_sha)
            )

    DD = Dispatcher(
        {
            "format": "native-media-worker-input-v1",
            "role": worker,
            "commandPlan": [first, bad],
            "phaseEnds": {"LATE_GUARDS": time.monotonic() + 4},
        },
        Ledger(time.monotonic() + 5),
    )

    def bind_target(dispatcher=DD, local=local):
        dispatcher.runtime = CountRuntime()
        dispatcher.late = local

    DD.bind_runtime = bind_target
    assert manual_run(DD.dispatch(first))["status"] == "OBSERVATION_ONLY"
    assert manual_run(DD.dispatch(bad))["status"] == "FAILED_UNQUALIFIED"
    assert calls == ["LATE_OWN_READ"] and not local.mutated and DD.failed
    checks.append("actual_dispatcher_wrong_mutation_target_" + actor + "_" + profile)
for stale in ("ref", "generation", "p4", "source"):
    local, lp, _ = make("A")
    target = next(x for x in lp["entries"] if x["key"] == "before_revoke")
    x = local.pre(cmd(target))
    local.post(cmd(target), x, obs())
    bound = local.rows[target["permit"]]
    if stale == "ref":
        bound["oldRef"] = "Z" * 43
    if stale == "generation":
        local.generation = "f" * 64
    if stale == "p4":
        bound["actorP4SHA256"] = "f" * 64
    if stale == "source":
        bound["sourceGraphSHA256"] = "f" * 64
    refuse(lambda local=local: local.pre(mutation))
    assert not local.mutated
    checks.append("stale_before_" + stale)
local, lp, _ = make("A")
target = next(x for x in lp["entries"] if x["key"] == "before_revoke")
x = local.pre(cmd(target))
local.post(cmd(target), x, obs())
t = local.pre(mutation)
local.post(mutation, t, mutation_obs("NM07", t[3][1]))
refuse(lambda: local.pre(mutation))
checks.append("duplicate_mutation_refused")
local, lp, _ = make("A")
target = next(x for x in lp["entries"] if x["key"] == "before_revoke")
first = {**cmd(target), "sequence": 1}
second = {
    "sequence": 2,
    "phase": "LATE_GUARDS",
    "op": "REVOKE",
    "role": "A",
    "actor": "A1",
    "profile": "media-alpha",
    "args": {},
}
DC = Dispatcher(
    {
        "format": "native-media-worker-input-v1",
        "role": "A",
        "commandPlan": [first, second],
        "phaseEnds": {"LATE_GUARDS": time.monotonic() + 4},
    },
    Ledger(time.monotonic() + 5),
)


class CancelDuringMutation:
    async def action(self, command, *, before_capture_sha=None):
        if command["op"] == "REVOKE":
            DC.cancelled = True
            return mutation_obs("NM07", before_capture_sha)
        return obs()


def bind_cancel():
    DC.runtime = CancelDuringMutation()
    DC.late = local


DC.bind_runtime = bind_cancel
assert manual_run(DC.dispatch(first))["status"] == "OBSERVATION_ONLY"
assert manual_run(DC.dispatch(second))["status"] == "FAILED_UNQUALIFIED"
assert DC.failed and DC.cancelled and not local.mutated
checks.append("late_mutation_return_after_cancel_not_sealed")
for role, op, case in (("A", "REVOKE", "NM07"), ("B", "ROTATE", "NM08")):
    local, lp, _ = make(role)
    before_row = next(x for x in lp["entries"] if x["key"].startswith("before_"))
    after_row = next(x for x in lp["entries"] if x["key"].startswith("after_"))
    first = {**cmd(before_row), "sequence": 1}
    mut = {
        "sequence": 2,
        "phase": "LATE_GUARDS",
        "op": op,
        "role": role,
        "actor": before_row["actor"],
        "profile": "media-alpha",
        "args": {} if op == "REVOKE" else {"chatId": "chat", "oldSessionId": "ses1_" + "A" * 22},
    }
    third = {**cmd(after_row), "sequence": 3}

    class OrderedRuntime:
        async def action(self, command, *, before_capture_sha=None, op=op):
            if command["op"] in ("REVOKE", "ROTATE"):
                return mutation_obs("NM07" if op == "REVOKE" else "NM08", before_capture_sha)
            return (
                obs(403 if op == "REVOKE" else 404, b"denied", "application/json")
                if command["sequence"] == 3
                else obs()
            )

    DP = Dispatcher(
        {
            "format": "native-media-worker-input-v1",
            "role": role,
            "commandPlan": [first, mut, third],
            "phaseEnds": {"LATE_GUARDS": time.monotonic() + 4},
        },
        Ledger(time.monotonic() + 5),
    )

    def bind_ordered(dispatcher=DP, local=local):
        dispatcher.runtime = OrderedRuntime()
        dispatcher.late = local

    DP.bind_runtime = bind_ordered
    for c in (first, mut, third):
        assert manual_run(DP.dispatch(c))["status"] == "OBSERVATION_ONLY"
    assert case in local.before and case in local.mutated and case in local.after
    checks.append("actual_dispatcher_correct_" + case + "_before_mutation_after")
new_command = {**cmd(next(x for x in ap["entries"] if x["key"] == "after_revoke")), "sequence": 2}
D2 = Dispatcher(
    {
        "format": "native-media-worker-input-v1",
        "role": "A",
        "commandPlan": [command, new_command],
        "phaseEnds": {"LATE_GUARDS": time.monotonic() + 4},
    },
    Ledger(time.monotonic() + 5),
)


class ReenteringRuntime:
    async def action(self, command):
        nested = await D2.dispatch(new_command)
        assert nested["status"] == "FAILED_UNQUALIFIED"
        return obs()


def inert_reentry_bind():
    D2.runtime = ReenteringRuntime()
    D2.late = make("A")[0]


D2.bind_runtime = inert_reentry_bind
outer = manual_run(D2.dispatch(command))
assert outer["status"] == "FAILED_UNQUALIFIED" and D2.failed
checks.append("actual_dispatcher_caught_reentry_sticky")
assert w["OPS"]["OWN_READ"] == {"CLOSED_NONOWNER_CASES", "FINAL_START_POSITIVES", "NM06_DART_INPUT"}
assert w["OPS"]["CROSS_PROBE"] == {"NM06_DART_INPUT"}
assert w["OPS"]["LATE_OWN_READ"] == {"LATE_GUARDS"}
checks.append("old_op_phases_unchanged")
translated = []
for step in m.m.STEPS:
    if step.action == "fetch":
        opcode = "LATE_OWN_READ" if step.case in ("NM07", "NM08") else "OWN_READ"
    elif step.action == "cross":
        opcode = "CROSS_PROBE"
    elif step.action == "mutation":
        opcode = "REVOKE" if step.case == "NM07" else "ROTATE"
    else:
        opcode = "OWN_READ"
    translated.append(opcode)
assert len(translated) == 37 and translated.count("LATE_OWN_READ") == 6
assert translated.count("REVOKE") == 1 and translated.count("ROTATE") == 1
checks.append("published37_closed_opcode_selection")
for role, op, case in (("A", "REVOKE", "NM07"), ("B", "ROTATE", "NM08")):
    for drift in (
        "generation",
        "row_ref",
        "row_route",
        "row_p4",
        "row_source",
        "row_permit",
        "spec_parent",
        "row_actor",
        "row_profile",
        "spec_p4",
        "spec_iid",
        "before_seal",
        "command_actor",
        "command_profile",
    ):
        gate, plan, gate_spec = make(role)
        before_row = next(x for x in plan["entries"] if x["key"].startswith("before_"))
        first = {**cmd(before_row), "sequence": 1}
        mutation_command = {
            "sequence": 2,
            "phase": "LATE_GUARDS",
            "op": op,
            "role": role,
            "actor": before_row["actor"],
            "profile": "media-alpha",
            "args": {}
            if op == "REVOKE"
            else {"chatId": "chat", "oldSessionId": "ses1_" + "A" * 22},
        }
        actions = []
        expected_event = (
            "public_native_revoke_observation"
            if op == "REVOKE"
            else "actual_running_public_store_rotation"
        )

        class DriftRuntime:
            async def action(
                self,
                command,
                *,
                actions=actions,
                before_row=before_row,
                case=case,
                drift=drift,
                expected_event=expected_event,
                gate=gate,
                gate_spec=gate_spec,
                role=role,
                before_capture_sha=None,
            ):
                actions.append(command["op"])
                if command["op"] == "LATE_OWN_READ":
                    return obs()
                current = gate.rows[before_row["permit"]]
                if drift == "generation":
                    gate.generation = "f" * 64
                if drift == "row_ref":
                    current["oldRef"] = "Z" * 43
                if drift == "row_route":
                    current["path"] = ROOT + "Z" * 43
                if drift == "row_p4":
                    current["actorP4SHA256"] = "f" * 64
                if drift == "row_source":
                    current["sourceGraphSHA256"] = "f" * 64
                if drift == "row_permit":
                    current["permit"] = "f" * 64
                if drift == "spec_parent":
                    gate_spec["gates"]["parentAdmission"]["SHA256"] = "f" * 64
                if drift == "row_actor":
                    current["actor"] = "A2" if role == "A" else "A1"
                if drift == "row_profile":
                    current["profile"] = "media-beta"
                if drift == "spec_p4":
                    next(x for x in gate_spec["commandPlan"] if x["actor"] == before_row["actor"])[
                        "args"
                    ]["p4CaptureSHA256"] = "f" * 64
                if drift == "spec_iid":
                    gate_spec["iid"] = "rebound"
                if drift == "before_seal":
                    ident, _digest, permit = gate.before[case]
                    gate.before[case] = (ident, "0" * 64, permit)
                if drift == "command_actor":
                    command["actor"] = "A2" if role == "A" else "A1"
                if drift == "command_profile":
                    command["profile"] = "media-beta"
                return mutation_obs(case, before_capture_sha)

        DD = Dispatcher(
            {
                "format": "native-media-worker-input-v1",
                "role": role,
                "commandPlan": [first, mutation_command],
                "phaseEnds": {"LATE_GUARDS": time.monotonic() + 4},
            },
            Ledger(time.monotonic() + 5),
        )

        def bind_drift(dispatcher=DD, gate=gate):
            dispatcher.runtime = DriftRuntime()
            dispatcher.late = gate

        DD.bind_runtime = bind_drift
        assert manual_run(DD.dispatch(first))["status"] == "OBSERVATION_ONLY"
        old_observation = DD.last_observation
        assert manual_run(DD.dispatch(mutation_command))["status"] == "FAILED_UNQUALIFIED"
        assert DD.failed and not gate.mutated and DD.last_observation is old_observation
        assert actions == ["LATE_OWN_READ", op]
        checks.append("actual_post_mutation_drift_" + case + "_" + drift)
for drift in (
    "generation",
    "row_ref",
    "row_route",
    "row_p4",
    "row_source",
    "row_permit",
    "spec_parent",
    "command_actor",
):
    gate, plan, _ = make("A")
    before_row = next(x for x in plan["entries"] if x["key"] == "before_revoke")
    first = {**cmd(before_row), "sequence": 1}

    class DriftReadRuntime:
        async def action(self, command, *, before_row=before_row, drift=drift, gate=gate):
            current = gate.rows[before_row["permit"]]
            if drift == "generation":
                gate.generation = "f" * 64
            if drift == "row_ref":
                current["oldRef"] = "Z" * 43
            if drift == "row_route":
                current["path"] = ROOT + "Z" * 43
            if drift == "row_p4":
                current["actorP4SHA256"] = "f" * 64
            if drift == "row_source":
                current["sourceGraphSHA256"] = "f" * 64
            if drift == "row_permit":
                current["permit"] = "f" * 64
            if drift == "spec_parent":
                gate.spec["gates"]["parentAdmission"]["SHA256"] = "f" * 64
            if drift == "command_actor":
                command["actor"] = "A2"
            return obs()

    DD = Dispatcher(
        {
            "format": "native-media-worker-input-v1",
            "role": "A",
            "commandPlan": [first],
            "phaseEnds": {"LATE_GUARDS": time.monotonic() + 4},
        },
        Ledger(time.monotonic() + 5),
    )

    def bind_read_drift(dispatcher=DD, gate=gate):
        dispatcher.runtime = DriftReadRuntime()
        dispatcher.late = gate

    DD.bind_runtime = bind_read_drift
    assert manual_run(DD.dispatch(first))["status"] == "FAILED_UNQUALIFIED"
    assert DD.failed and not gate.before and DD.last_observation is None
    checks.append("actual_post_read_drift_" + drift)
for role, op, case in (("A", "REVOKE", "NM07"), ("B", "ROTATE", "NM08")):
    for drift in (
        "op",
        "sequence",
        "phase",
        "actor",
        "profile",
        "role",
        "args_value",
        "args_add",
        "args_remove",
        "caller_op",
        "caller_sequence",
        "plan_args",
    ):
        gate, plan, _ = make(role)
        before_row = next(x for x in plan["entries"] if x["key"].startswith("before_"))
        first = {**cmd(before_row), "sequence": 1}
        mutation = {
            "sequence": 2,
            "phase": "LATE_GUARDS",
            "op": op,
            "role": role,
            "actor": before_row["actor"],
            "profile": "media-alpha",
            "args": {}
            if op == "REVOKE"
            else {"chatId": "chat", "oldSessionId": "ses1_" + "A" * 22},
        }
        actions = []
        accepted_event = (
            "public_native_revoke_observation"
            if op == "REVOKE"
            else "actual_running_public_store_rotation"
        )

        class MutatingRuntime:
            async def action(
                self,
                current,
                *,
                accepted_event=accepted_event,
                actions=actions,
                drift=drift,
                mutation=mutation,
                op=op,
                role=role,
                before_capture_sha=None,
            ):
                actions.append(current["op"])
                if current["op"] == "LATE_OWN_READ":
                    return obs()
                target = mutation if drift.startswith("caller_") else current
                if drift == "op" or drift == "caller_op":
                    target["op"] = "OBSERVE_FINAL"
                elif drift == "sequence" or drift == "caller_sequence":
                    target["sequence"] = 999
                elif drift == "phase":
                    target["phase"] = "TERMINAL_AUDIT"
                elif drift == "actor":
                    target["actor"] = "A2" if role == "A" else "A1"
                elif drift == "profile":
                    target["profile"] = "media-beta"
                elif drift == "role":
                    target["role"] = "B" if role == "A" else "A"
                elif drift == "args_value":
                    target["args"]["oldSessionId"] = (
                        "other" if op == "ROTATE" else target["args"].update({"x": "y"})
                    )
                elif drift == "args_add":
                    target["args"]["unexpected"] = "x"
                elif drift == "args_remove" and target["args"]:
                    target["args"].pop(next(iter(target["args"])))
                elif drift == "args_remove":
                    target["args"] = None
                elif drift == "plan_args":
                    mutation["args"]["unexpected"] = "x"
                return mutation_obs("NM07" if op == "REVOKE" else "NM08", before_capture_sha)

        dd = Dispatcher(
            {
                "format": "native-media-worker-input-v1",
                "role": role,
                "commandPlan": [first, mutation],
                "phaseEnds": {"LATE_GUARDS": time.monotonic() + 4},
            },
            Ledger(time.monotonic() + 5),
        )

        def bind_mutation(dd=dd, gate=gate):
            dd.runtime = MutatingRuntime()
            dd.late = gate

        dd.bind_runtime = bind_mutation
        assert manual_run(dd.dispatch(first))["status"] == "OBSERVATION_ONLY"
        prior = dd.last_observation
        result = manual_run(dd.dispatch(mutation))
        assert result["status"] == "FAILED_UNQUALIFIED" and result["sequence"] == 2
        assert result["op"] == op and dd.failed and dd.last_observation is prior
        assert case not in gate.mutated and actions == ["LATE_OWN_READ", op]
        checks.append("full_command_mutation_" + case + "_" + drift)
    for drift in (
        "op",
        "sequence",
        "phase",
        "actor",
        "profile",
        "role",
        "args_value",
        "args_add",
        "args_remove",
        "caller_op",
        "caller_sequence",
    ):
        gate, plan, _ = make(role)
        before_row = next(x for x in plan["entries"] if x["key"].startswith("before_"))
        first = {**cmd(before_row), "sequence": 1}
        actions = []

        class MutatingReadRuntime:
            async def action(
                self, current, *, actions=actions, drift=drift, first=first, role=role
            ):
                actions.append(current["op"])
                target = first if drift.startswith("caller_") else current
                if drift in ("op", "caller_op"):
                    target["op"] = "OBSERVE_FINAL"
                elif drift in ("sequence", "caller_sequence"):
                    target["sequence"] = 999
                elif drift == "phase":
                    target["phase"] = "TERMINAL_AUDIT"
                elif drift == "actor":
                    target["actor"] = "A2" if role == "A" else "A1"
                elif drift == "profile":
                    target["profile"] = "media-beta"
                elif drift == "role":
                    target["role"] = "B" if role == "A" else "A"
                elif drift == "args_value":
                    target["args"]["path"] = ROOT + "Z" * 43
                elif drift == "args_add":
                    target["args"]["unexpected"] = "x"
                elif drift == "args_remove":
                    target["args"].pop("permit")
                return obs()

        dd = Dispatcher(
            {
                "format": "native-media-worker-input-v1",
                "role": role,
                "commandPlan": [first],
                "phaseEnds": {"LATE_GUARDS": time.monotonic() + 4},
            },
            Ledger(time.monotonic() + 5),
        )

        def bind_read(dd=dd, gate=gate):
            dd.runtime = MutatingReadRuntime()
            dd.late = gate

        dd.bind_runtime = bind_read
        result = manual_run(dd.dispatch(first))
        assert result["status"] == "FAILED_UNQUALIFIED" and result["sequence"] == 1
        assert result["op"] == "LATE_OWN_READ" and dd.failed and dd.last_observation is None
        assert case not in gate.before and len(gate.used) == 1 and actions == ["LATE_OWN_READ"]
        checks.append("full_command_read_mutation_" + case + "_" + drift)

# Gate-only regression: a late ticket cannot become an unrelated opcode's no-op.
gate, plan, _ = make("A")
target = next(x for x in plan["entries"] if x["key"] == "before_revoke")
before = {**cmd(target), "sequence": 1}
ticket = gate.pre(before)
changed = {**before, "op": "OBSERVE_FINAL"}
refuse(lambda: gate.post(changed, ticket, obs()))
assert not gate.before
checks.append("ticket_kind_precedes_mutated_opcode")

print(
    json.dumps(
        {
            "kind": "PY8_LATE_WORKER_SOURCE_INERT",
            "checks": checks,
            "count": len(checks),
            "publishedFullSteps": len(m.m.STEPS),
            "runtimeQualified": False,
        },
        sort_keys=True,
    )
)
