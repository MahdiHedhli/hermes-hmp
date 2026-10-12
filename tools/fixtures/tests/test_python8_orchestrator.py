"""Collected pure NM01-NM08 orchestrator causals; no native or network runtime."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "_hmp_python8_orchestrator_v2_fixture", ROOT / "python8_orchestrator.py"
)
assert spec is not None and spec.loader is not None
assert spec.name not in sys.modules
assert Path(spec.origin) == ROOT / "python8_orchestrator.py"
m = importlib.util.module_from_spec(spec)

sys.modules[spec.name] = m
spec.loader.exec_module(m)
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mMQMgn7DwAClAGcwgVUTwAAAABJRU5ErkJggg=="
)
assert len(PNG) == 70 and hashlib.sha256(PNG).hexdigest() == m.PNG_SHA256
REFS = {
    k: chr(65 + i) * 43
    for i, k in enumerate(
        (
            "closed",
            "A1-alpha",
            "A2-alpha",
            "A1-beta",
            "B1-alpha",
            "NM07",
            "NM08",
            "NM07-control",
            "NM08-control",
        )
    )
}
SESSIONS = {
    "A-alpha": "ses1_" + "A" * 22,
    "Phone-alpha": "ses1_" + "P" * 22,
    "A-beta": "ses1_" + "C" * 22,
    "B-alpha": "ses1_" + "B" * 22,
}
_a = "/hmp/v1/bots/media-alpha"
_b = "/hmp/v1/bots/media-beta"
_aa = _a + "/sessions/" + SESSIONS["A-alpha"]
_pa = _a + "/sessions/" + SESSIONS["Phone-alpha"]
_ab = _b + "/sessions/" + SESSIONS["A-beta"]
_bb = _a + "/sessions/" + SESSIONS["B-alpha"]
PATHS = {
    "NM01:NM01": _aa + "/messages?after=0&limit=64",
    "NM02:NM02": _aa + "/messages?after=0&limit=64",
    "NM03:SES2": _aa + "/messages?after=0&limit=64",
    "NM03:SES2a": _aa + "/messages/from-start?limit=64",
    "NM04:RO3": _a + "/conversations/default?limit=64",
    "NM04:RO6": _a + "/conversations/default/messages?after=0&limit=64",
    "NM04:SES2": _pa + "/messages?after=0&limit=64",
    "NM04:SES2a": _pa + "/messages/from-start?limit=64",
    "NM05:decoy": _aa + "/messages?after=0&limit=64",
    "NM06:A1-alpha": _aa + "/messages?after=0&limit=64",
    "NM06:A2-alpha": _aa + "/messages?after=0&limit=64",
    "NM06:A1-beta": _ab + "/messages?after=0&limit=64",
    "NM06:B1-alpha": _bb + "/messages?after=0&limit=64",
}
ROWS = {case: i + 1 for i, case in enumerate(m.CASES) if case != "NM06"}
ROWS.update(
    {
        "NM06:" + key: 100 + i
        for i, key in enumerate(("A1-alpha", "A2-alpha", "A1-beta", "B1-alpha"))
    }
)
A = {"iid": "a" * 51 + "q", "deviceId": "A1-device", "userId": "A1-user", "port": 21211}
A2 = {**A, "deviceId": "A2-device", "userId": "A2-user"}
B = {"iid": "b" * 51 + "q", "deviceId": "B1-device", "userId": "B1-user", "port": 21212}
CTX = {
    "actors": {"A1": A, "A2": A2, "B1": B},
    "paths": PATHS,
    "refs": REFS,
    "sessionRefs": SESSIONS,
    "sourcePin": "a" * 64,
    "nativeRows": ROWS,
    "closedRows": {
        "NM01": [{"id": 1, "text": "preserved"}],
        "NM02": [{"id": 2, "text": "preserved"}],
    },
    "decoys": [
        {"id": 88, "role": "assistant", "tool_name": None, "text": "assistant text"},
        {"id": 89, "role": "tool", "tool_name": "other_tool", "text": "tool text"},
    ],
}


def refuse(fn, code):
    try:
        fn()
    except m.PhaseRefusalError as error:
        assert str(error) == code, (str(error), code)
    else:
        raise AssertionError("expected " + code)


class FakePort:
    def __init__(self, mutate_before=False, wrong=None):
        self.calls = []
        self.before = None
        self.mutate_before = mutate_before
        self.wrong = wrong

    def observe(self, req):
        self.calls.append((req.step.phase, req.step.case, req.step.action, req.step.key))
        step = req.step
        if step.expected_status == 200 and step.action == "fetch":
            body = PNG
            typ = "image/png"
        elif step.expected_error:
            obj = {"error": step.expected_error}
            if step.case == "NM07" and step.key.startswith("after_"):
                obj["authz"] = "pending_operator"
            body = json.dumps(obj).encode()
            typ = "application/json"
        elif step.action == "descriptor":
            ref = REFS.get(step.key)
            if ref is None:
                ref = ("C" if step.case == "NM03" else "D") * 43
            body = json.dumps(
                {
                    "messages": [
                        {
                            "id": req.native_row,
                            "role": "tool",
                            "tool_name": "image_generate",
                            "media": {"kind": "image", "ref": ref},
                        }
                    ]
                }
            ).encode()
            typ = "application/json"
        elif step.action == "decoys":
            body = json.dumps(
                {
                    "messages": [
                        {
                            "id": 88,
                            "role": "assistant",
                            "tool_name": None,
                            "text": "assistant text",
                            "media": None,
                        },
                        {
                            "id": 89,
                            "role": "tool",
                            "tool_name": "other_tool",
                            "text": "tool text",
                            "media": None,
                        },
                    ]
                }
            ).encode()
            typ = "application/json"
        else:
            body = json.dumps(
                {
                    "messages": [
                        {"id": req.native_row, "role": "tool", "text": "preserved", "media": None}
                    ]
                }
            ).encode()
            typ = "application/json"
        result = {
            "phase": step.phase,
            "sequence": req.sequence,
            "actor": step.actor,
            "profile": step.profile,
            "path": req.path,
            "iid": req.iid,
            "headerIid": req.header_iid,
            "status": step.expected_status,
            "contentType": typ,
            "body": body,
            "sourcePin": req.source_pin,
            "nativeRow": req.native_row,
        }
        if self.wrong == "phase":
            result["phase"] = "FINAL_START_POSITIVES"
        if self.wrong == "actor":
            result["actor"] = "B1" if step.actor != "B1" else "A1"
        if self.wrong == "pin":
            result["sourcePin"] = "b" * 64
        if self.wrong == "body":
            result["body"] = b"X"
        if self.wrong == "header":
            result["headerIid"] = "z" * 52
        if self.wrong == "status":
            result["status"] = 201
        if step.key.startswith("before_"):
            self.before = hashlib.sha256(body).hexdigest()
        return result

    def mutate(self, req):
        self.calls.append((req.step.phase, req.step.case, req.step.action, req.step.key))
        return {
            "phase": req.step.phase,
            "sequence": req.sequence,
            "api": req.step.key,
            "target": req.step.actor,
            "sourcePin": req.source_pin,
            "beforeCaptureSHA256": ("0" * 64 if self.mutate_before else self.before),
            "afterNativeSHA256": "b" * 64,
        }


def create(port=None, **changes):
    context = {**CTX, **changes}
    return m.PhaseOrchestrator(context, port=port, deadline=5, clock=lambda: 1)


def run_all(o):
    for step in m.STEPS:
        o.advance(step.case, step.action)
    return o.source_selection()


def test_python8_inert_causal_groups():
    checks = []
    port = FakePort()
    out = run_all(create(port))
    assert (
        out["assertedCases"] == list(m.CASES)
        and out["qualifiedCases"] == []
        and out["runtimeQualified"] is False
        and out["unqualifiedCases"]
        == {"NM09": "owned_fault_unimplemented", "NM10": "real_Dart_consumer_unrun"}
    )
    assert len(port.calls) == len(m.STEPS) == 37
    checks.append("positive_source_only_37_actual_port_method_calls")
    o = create(FakePort())
    refuse(lambda: o.advance("NM02", "closed_read"), "out_of_order")
    assert not o.closed and not o.unknown and not o.in_flight and o.index == 0
    run_all(o)
    checks.append("out_of_order_predispatch_not_poisoned")
    o = create(FakePort())
    o.advance("NM01", "closed_read")
    refuse(lambda o=o: o.advance("NM01", "closed_read"), "out_of_order")
    checks.append("duplicate_step")
    o = create(FakePort())
    o.cancel()
    refuse(lambda o=o: o.advance("NM01", "closed_read"), "closed_or_complete")
    checks.append("cancel_sticky")
    o = create()
    refuse(lambda o=o: o.advance("NM01", "closed_read"), "real_runtime_port_unbound")
    refuse(lambda o=o: o.advance("NM01", "closed_read"), "closed_or_complete")
    checks.append("unbound_no_retry")
    for wrong, code in (
        ("phase", "capture_binding"),
        ("actor", "capture_binding"),
        ("pin", "capture_binding"),
        ("header", "capture_binding"),
        ("status", "status"),
        ("body", "response_json"),
    ):
        o = create(FakePort(wrong=wrong))
        refuse(lambda o=o: o.advance("NM01", "closed_read"), code)
        refuse(lambda o=o: o.advance("NM01", "closed_read"), "closed_or_complete")
        checks.append("wrong_" + wrong)
    for deadline, clock in ((1, lambda: 1), (5, lambda: float("nan")), (5, lambda: -1)):
        refuse(
            lambda deadline=deadline, clock=clock: m.PhaseOrchestrator(
                CTX, port=FakePort(), deadline=deadline, clock=clock
            ),
            "clock_initial",
        )
        checks.append("deadline_refusal")
    for name, bad in (
        ("actors", {"A1": A, "A2": A2}),
        ("nativeRows", {"NM01": 1}),
        ("sourcePin", "bad"),
    ):
        refuse(
            lambda name=name, bad=bad: create(FakePort(), **{name: bad}),
            {"actors": "actors", "nativeRows": "native_rows", "sourcePin": "source_pin"}[name],
        )
        checks.append("context_" + name)
    o = create(FakePort())
    o.advance("NM01", "closed_read")
    refuse(o.source_selection, "incomplete")
    checks.append("no_early_selection")
    p = FakePort(mutate_before=True)
    o = create(p)
    for step in m.STEPS:
        if step.action == "mutation":
            break
        o.advance(step.case, step.action)
    refuse(lambda: o.advance(step.case, step.action), "mutation_before")
    checks.append("mutation_before_exact_capture")
    # Actual callback results cannot fabricate actor, profile, source, sequence or body.
    for field, bad in (
        ("sequence", 99),
        ("profile", "media-beta"),
        ("nativeRow", 999),
        ("body", None),
    ):

        class Bad(FakePort):
            def observe(self, req, field=field, bad=bad):
                result = super().observe(req)
                result[field] = bad
                return result

        o = create(Bad())
        refuse(
            lambda o=o: o.advance("NM01", "closed_read"),
            "body_cap" if field == "body" else "capture_binding",
        )
        checks.append("capture_" + field)
    # Context is copied before first GO, and unknown never yields source selection.
    external = {**CTX, "refs": dict(REFS)}
    o = create(FakePort(), **external)
    external["refs"]["closed"] = "Z" * 43
    o.advance("NM01", "closed_read")
    assert o.context["refs"]["closed"] == "A" * 43
    checks.append("immutable_context_snapshot")
    try:
        o.context["refs"]["closed"] = "Y" * 43
    except TypeError:
        checks.append("immutable_nested_snapshot")
    else:
        raise AssertionError("nested context remained mutable")
    # A late opaque capture replacement is observable at the closed source consumer.
    o = create(FakePort())
    run_all(o)
    o._raw[0] = b"X" * len(o._raw[0])
    refuse(o.source_selection, "raw_capture_drift")
    checks.append("retained_raw_replacement")
    # A missing/extra route, wrong source identity or broadened route fails before callback.
    for change, code in (
        ({"paths": {}}, "read_paths_exact"),
        ({"paths": {**PATHS, "extra": "/hmp/v1/bots/media-alpha/secrets"}}, "read_paths_exact"),
        ({"paths": {**PATHS, "NM01:NM01": "/hmp/v1/bots/media-alpha/secrets"}}, "read_paths_exact"),
        ({"refs": {**REFS, "extra": "Z" * 43}}, "refs_inventory"),
    ):
        refuse(lambda change=change: create(FakePort(), **change), code)
        checks.append("pre_go_" + code)
    # No actor mixing or same-instance substitution.
    refuse(lambda: create(FakePort(), actors={**CTX["actors"], "B1": A}), "instance_bind")
    checks.append("iid_collision")

    # All four NM06 refs remain distinct; source selection cannot bless duplicate refs.
    class DupRef(FakePort):
        def observe(self, req):
            result = super().observe(req)
            if req.step.case == "NM06" and req.step.action == "descriptor":
                obj = json.loads(result["body"])
                obj["messages"][0]["media"]["ref"] = REFS["A1-alpha"]
                result["body"] = json.dumps(obj).encode()
            return result

    o = create(DupRef())
    for step in m.STEPS:
        try:
            o.advance(step.case, step.action)
        except m.PhaseRefusalError as error:
            assert str(error) == "descriptor_ref"
            break
    else:
        raise AssertionError("duplicate NM06 source")
    checks.append("nm06_ref_mismatch")

    # Cancellation inside a potentially effectful callback cannot be cleared by a late success.
    class CancelPort(FakePort):
        def observe(self, req):
            result = super().observe(req)
            self.owner.cancel()
            return result

    p = CancelPort()
    o = create(p)
    p.owner = o
    refuse(lambda o=o: o.advance("NM01", "closed_read"), "cancel_during_callback")
    assert o.closed and o.unknown and o.index == 0 and not o.captures
    checks.append("cancel_during_observe_no_capture")

    class CancelMutation(FakePort):
        def mutate(self, req):
            result = super().mutate(req)
            self.owner.cancel()
            return result

    p = CancelMutation()
    o = create(p)
    p.owner = o
    for step in m.STEPS:
        if step.action == "mutation":
            break
        o.advance(step.case, step.action)
    prior = len(o.captures)
    refuse(lambda: o.advance(step.case, step.action), "cancel_during_callback")
    assert o.closed and o.unknown and len(o.captures) == prior
    checks.append("cancel_during_mutation_no_capture")
    # Bool/float replay values must not pass Python == comparison as valid sequence/row IDs.
    for field, bad in (
        ("sequence", True),
        ("sequence", 1.0),
        ("nativeRow", True),
        ("nativeRow", 1.0),
    ):

        class Forged(FakePort):
            def observe(self, req, field=field, bad=bad):
                result = super().observe(req)
                result[field] = bad
                return result

        o = create(Forged())
        refuse(lambda o=o: o.advance("NM01", "closed_read"), "capture_types")
        checks.append("exact_type_" + field + "_" + str(bad))

    class ForgedMutation(FakePort):
        def mutate(self, req):
            result = super().mutate(req)
            result["sequence"] = True
            return result

    o = create(ForgedMutation())
    for step in m.STEPS:
        if step.action == "mutation":
            break
        o.advance(step.case, step.action)
    refuse(lambda: o.advance(step.case, step.action), "mutation_types")
    checks.append("exact_mutation_sequence_type")
    # A clock that runs backward across callback is sticky and cannot certify an event.
    clock_values = iter((1, 2, 1))
    o = m.PhaseOrchestrator(CTX, port=FakePort(), deadline=5, clock=lambda: next(clock_values))
    refuse(lambda o=o: o.advance("NM01", "closed_read"), "deadline")
    assert o.closed and o.unknown and o.index == 0
    checks.append("backward_clock_sticky")

    # Reentry during an effectful callback poisons owner even when swallowed.
    class ReenterObserve(FakePort):
        def __init__(self, swallow):
            super().__init__()
            self.swallow = swallow

        def observe(self, req):
            if req.sequence == 1:
                if self.swallow:
                    refuse(
                        lambda: self.owner.advance(req.step.case, req.step.action),
                        "in_flight_reentry",
                    )
                else:
                    self.owner.advance(req.step.case, req.step.action)
            return super().observe(req)

    for swallow in (True, False):
        p = ReenterObserve(swallow)
        o = create(p)
        p.owner = o
        refuse(
            lambda o=o: o.advance("NM01", "closed_read"),
            "cancel_during_callback" if swallow else "in_flight_reentry",
        )
        assert o.closed and o.unknown and not o.in_flight and o.index == 0 and not o.captures
        assert len(p.calls) == (1 if swallow else 0)
        refuse(lambda o=o: o.advance("NM01", "closed_read"), "closed_or_complete")
        refuse(o.source_selection, "incomplete")
        checks.append("caught_observe_reentry" if swallow else "propagated_observe_reentry")

    class ReenterMutation(FakePort):
        def mutate(self, req):
            refuse(lambda: self.owner.advance(req.step.case, req.step.action), "in_flight_reentry")
            return super().mutate(req)

    p = ReenterMutation()
    o = create(p)
    p.owner = o
    for step in m.STEPS:
        if step.action == "mutation":
            break
        o.advance(step.case, step.action)
    prior = len(o.captures)
    refuse(lambda: o.advance(step.case, step.action), "cancel_during_callback")
    assert len(o.captures) == prior and o.closed and o.unknown and not o.in_flight
    assert sum(call[2] == "mutation" for call in p.calls) == 1
    refuse(o.source_selection, "incomplete")
    checks.append("caught_mutation_reentry")

    # Same native row across all read routes must retain one exact case ref.
    class ChangedRef(FakePort):
        def __init__(self, case, key):
            super().__init__()
            self.case, self.key = case, key

        def observe(self, req):
            result = super().observe(req)
            if (
                req.step.case == self.case
                and req.step.key == self.key
                and req.step.action == "descriptor"
            ):
                obj = json.loads(result["body"])
                obj["messages"][0]["media"]["ref"] = "X" * 43
                result["body"] = json.dumps(obj).encode()
            return result

    for case, key in (("NM03", "SES2a"), ("NM04", "RO6"), ("NM04", "SES2"), ("NM04", "SES2a")):
        p = ChangedRef(case, key)
        o = create(p)
        for step in m.STEPS:
            if step.case == case and step.key == key and step.action == "descriptor":
                before = len(p.calls)
                refuse(
                    lambda step=step, o=o: o.advance(step.case, step.action),
                    "case_source_ref_changed",
                )
                assert len(p.calls) == before + 1 and p.calls[-1][2] == "descriptor"
                assert o.closed and o.unknown and not o.in_flight
                refuse(o.source_selection, "incomplete")
                break
            o.advance(step.case, step.action)
        else:
            raise AssertionError("changed source route was not reached")
        checks.append("same_case_ref_" + case + "_" + key)

    p = FakePort()
    o = create(p)
    run_all(o)
    assert o.case_ref["NM03"][1] == "C" * 43
    assert o.case_ref["NM04"][1] == "D" * 43
    assert (
        len({o.derived[("NM06", key)] for key in ("A1-alpha", "A2-alpha", "A1-beta", "B1-alpha")})
        == 4
    )
    checks.append("healthy_case_refs_independent_and_nm06_distinct")
    assert all(s.phase in m.PHASES and s.case in m.CASES for s in m.STEPS)
    assert [s.case for s in m.STEPS[:4]] == ["NM01", "NM01", "NM02", "NM02"]
    assert all(s.case not in ("NM07", "NM08") for s in m.STEPS[:-8])
    checks.append("phase_order_and_late_mutations")
    assert len(checks) == 49
    assert len(m.STEPS) == 37
