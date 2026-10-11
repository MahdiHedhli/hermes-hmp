"""Source-only NM01-NM08 phase assertion engine.

A real runtime port is deliberately unbound. Root must separately qualify its
source/native/TLS/c018 provenance. Completed source assertions never certify it.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

PHASES = ("CLOSED_NONOWNER_CASES", "FINAL_START_POSITIVES", "NM06_DART_INPUT", "LATE_GUARDS")
CASES = tuple(f"NM{i:02d}" for i in range(1, 9))
REF = re.compile(r"[A-Za-z0-9_-]{43}\Z")
IID = re.compile(r"[a-z2-7]{51}[aq]\Z")
READ_ROUTE = re.compile(
    r"/hmp/v1/bots/(media-alpha|media-beta)/(conversations/default\?limit=64|conversations/default/messages\?after=0&limit=64|sessions/ses1_[A-Za-z0-9_-]{22}/messages\?after=0&limit=64|sessions/ses1_[A-Za-z0-9_-]{22}/messages/from-start\?limit=64)\Z"
)
PNG_SHA256 = "fdde404f4138c9fc441564a4272169f9d288545b96b7cb2bb3b7e3d548376db1"
MAX_EVENTS = 40
MAX_BODY = 1048576
MAX_TOTAL_BODY = 1048576


class PhaseRefusalError(RuntimeError):
    pass


def need(value: bool, code: str) -> None:
    if not value:
        raise PhaseRefusalError(code)


def immutable_copy(value):
    if type(value) is dict:
        return MappingProxyType({key: immutable_copy(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(immutable_copy(item) for item in value)
    return copy.deepcopy(value)


def strict_json(body: bytes) -> object:
    def pairs(items):
        out = {}
        for key, value in items:
            need(key not in out, "duplicate_json")
            out[key] = value
        return out

    try:
        return json.loads(body, object_pairs_hook=pairs)
    except (ValueError, UnicodeError) as error:
        raise PhaseRefusalError("response_json") from error


@dataclass(frozen=True)
class Step:
    case: str
    phase: str
    action: str
    actor: str
    profile: str
    key: str
    expected_status: int | None = None
    expected_error: str | None = None


@dataclass(frozen=True)
class Request:
    sequence: int
    step: Step
    path: str
    iid: str
    header_iid: str
    device_id: str
    user_id: str
    source_pin: str
    native_row: int


class RuntimePort(Protocol):
    def observe(self, request: Request) -> dict: ...
    def mutate(self, request: Request) -> dict: ...


class UnboundRuntimePort:
    def observe(self, request: Request) -> dict:
        raise PhaseRefusalError("real_runtime_port_unbound")

    def mutate(self, request: Request) -> dict:
        raise PhaseRefusalError("real_runtime_port_unbound")


def steps() -> tuple[Step, ...]:
    rows = [
        Step("NM01", PHASES[0], "closed_read", "A1", "media-alpha", "NM01", 200),
        Step("NM01", PHASES[0], "fetch", "A1", "media-alpha", "closed", 503, "media_unavailable"),
        Step("NM02", PHASES[0], "closed_read", "A2", "media-alpha", "NM02", 200),
        Step("NM02", PHASES[0], "fetch", "A2", "media-alpha", "closed", 404, "not_found"),
    ]
    for case, actor, profile, keys in (
        ("NM03", "A1", "media-alpha", ("SES2", "SES2a")),
        ("NM04", "A1", "media-alpha", ("RO3", "RO6", "SES2", "SES2a")),
    ):
        for key in keys:
            rows.append(Step(case, PHASES[1], "descriptor", actor, profile, key, 200))
            rows.append(Step(case, PHASES[1], "fetch", actor, profile, key, 200))
    rows.append(Step("NM05", PHASES[1], "decoys", "A1", "media-alpha", "decoy", 200))
    for actor, profile, key in (
        ("A1", "media-alpha", "A1-alpha"),
        ("A2", "media-alpha", "A2-alpha"),
        ("A1", "media-beta", "A1-beta"),
        ("B1", "media-alpha", "B1-alpha"),
    ):
        rows.append(Step("NM06", PHASES[2], "descriptor", actor, profile, key, 200))
        rows.append(Step("NM06", PHASES[2], "fetch", actor, profile, key, 200))
    for code, actor, profile, error, status in (
        ("D", "A2", "media-alpha", "not_found", 404),
        ("P", "A1", "media-beta", "not_found", 404),
        ("I", "B1", "media-alpha", "not_found", 404),
        ("H", "B1", "media-alpha", "wrong_instance", 401),
    ):
        rows.append(Step("NM06", PHASES[2], "cross", actor, profile, code, status, error))
    for case, actor, key, api, status, error in (
        ("NM07", "A1", "revoke", "PairingStore.revoke", 403, "forbidden"),
        ("NM08", "B1", "rotate", "SessionStore.get_or_create_session", 404, "not_found"),
    ):
        rows.extend(
            (
                Step(case, PHASES[3], "fetch", actor, "media-alpha", "before_" + key, 200),
                Step(case, PHASES[3], "mutation", actor, "media-alpha", api),
                Step(case, PHASES[3], "fetch", actor, "media-alpha", "after_" + key, status, error),
                Step(
                    case,
                    PHASES[3],
                    "fetch",
                    "A2" if case == "NM07" else "A1",
                    "media-alpha",
                    "control_" + key,
                    200,
                ),
            )
        )
    need(len(rows) <= MAX_EVENTS and {x.case for x in rows} == set(CASES), "closed_plan")
    return tuple(rows)


STEPS = steps()


class PhaseOrchestrator:
    """One-use requests; source-only completion, never runtime qualification."""

    def __init__(
        self,
        context: dict,
        *,
        port: RuntimePort | None = None,
        deadline: float,
        clock=time.monotonic,
    ):
        need(
            type(context) is dict
            and set(context)
            == {
                "actors",
                "paths",
                "refs",
                "sourcePin",
                "nativeRows",
                "closedRows",
                "decoys",
                "sessionRefs",
            },
            "context_shape",
        )
        need(
            type(context["sourcePin"]) is str
            and re.fullmatch(r"[a-f0-9]{64}", context["sourcePin"]) is not None,
            "source_pin",
        )
        need(
            type(context["nativeRows"]) is dict
            and set(context["nativeRows"])
            == (
                (set(CASES) - {"NM06"})
                | {"NM06:" + k for k in ("A1-alpha", "A2-alpha", "A1-beta", "B1-alpha")}
            ),
            "native_rows",
        )
        need(all(type(v) is int and v > 0 for v in context["nativeRows"].values()), "native_row")
        actors = context["actors"]
        need(type(actors) is dict and set(actors) == {"A1", "A2", "B1"}, "actors")
        for actor in actors.values():
            need(
                type(actor) is dict and set(actor) == {"iid", "deviceId", "userId", "port"},
                "actor_shape",
            )
            need(type(actor["iid"]) is str and IID.fullmatch(actor["iid"]) is not None, "iid")
            need(type(actor["deviceId"]) is str and 0 < len(actor["deviceId"]) <= 4096, "device")
            need(type(actor["userId"]) is str and 0 < len(actor["userId"]) <= 4096, "user")
            need(type(actor["port"]) is int and 1 <= actor["port"] <= 65535, "port")
        need(actors["A1"]["iid"] == actors["A2"]["iid"] != actors["B1"]["iid"], "instance_bind")
        need(actors["A1"]["port"] == actors["A2"]["port"] != actors["B1"]["port"], "port_bind")
        need(actors["A1"]["deviceId"] != actors["A2"]["deviceId"], "device_bind")
        need(
            type(context["sessionRefs"]) is dict
            and set(context["sessionRefs"]) == {"A-alpha", "Phone-alpha", "A-beta", "B-alpha"},
            "session_refs",
        )
        need(
            all(
                type(ref) is str and re.fullmatch(r"ses1_[A-Za-z0-9_-]{22}", ref) is not None
                for ref in context["sessionRefs"].values()
            ),
            "session_ref",
        )
        need(len(set(context["sessionRefs"].values())) == 4, "session_distinct")
        need(type(context["paths"]) is dict and type(context["refs"]) is dict, "route_maps")
        a = "/hmp/v1/bots/media-alpha"
        b = "/hmp/v1/bots/media-beta"
        aa = a + "/sessions/" + context["sessionRefs"]["A-alpha"]
        pa = a + "/sessions/" + context["sessionRefs"]["Phone-alpha"]
        ab = b + "/sessions/" + context["sessionRefs"]["A-beta"]
        bb = a + "/sessions/" + context["sessionRefs"]["B-alpha"]
        expected_paths = {
            "NM01:NM01": aa + "/messages?after=0&limit=64",
            "NM02:NM02": aa + "/messages?after=0&limit=64",
            "NM03:SES2": aa + "/messages?after=0&limit=64",
            "NM03:SES2a": aa + "/messages/from-start?limit=64",
            "NM04:RO3": a + "/conversations/default?limit=64",
            "NM04:RO6": a + "/conversations/default/messages?after=0&limit=64",
            "NM04:SES2": pa + "/messages?after=0&limit=64",
            "NM04:SES2a": pa + "/messages/from-start?limit=64",
            "NM05:decoy": aa + "/messages?after=0&limit=64",
            "NM06:A1-alpha": aa + "/messages?after=0&limit=64",
            "NM06:A2-alpha": aa + "/messages?after=0&limit=64",
            "NM06:A1-beta": ab + "/messages?after=0&limit=64",
            "NM06:B1-alpha": bb + "/messages?after=0&limit=64",
        }
        need(context["paths"] == expected_paths, "read_paths_exact")
        need(
            set(context["paths"])
            == {
                s.case + ":" + s.key
                for s in STEPS
                if s.action in ("descriptor", "decoys", "closed_read")
            },
            "paths_inventory",
        )
        need(
            set(context["refs"])
            == {
                "closed",
                "A1-alpha",
                "A2-alpha",
                "A1-beta",
                "B1-alpha",
                "NM07",
                "NM08",
                "NM07-control",
                "NM08-control",
            },
            "refs_inventory",
        )
        for key, path in context["paths"].items():
            profile = next(
                s.profile
                for s in STEPS
                if s.case + ":" + s.key == key
                and s.action in ("descriptor", "decoys", "closed_read")
            )
            need(
                type(path) is str
                and len(path) <= 1024
                and READ_ROUTE.fullmatch(path) is not None
                and path.startswith("/hmp/v1/bots/" + profile + "/"),
                "path",
            )
        for ref in context["refs"].values():
            need(type(ref) is str and REF.fullmatch(ref) is not None, "ref")
        need(
            type(context["closedRows"]) is dict and set(context["closedRows"]) == {"NM01", "NM02"},
            "closed_rows",
        )
        for rows in context["closedRows"].values():
            need(
                type(rows) is list
                and 0 < len(rows) <= 64
                and all(
                    type(r) is dict
                    and set(r) == {"id", "text"}
                    and type(r["id"]) is int
                    and r["id"] > 0
                    and type(r["text"]) is str
                    and len(r["text"]) <= 4096
                    for r in rows
                ),
                "closed_row",
            )
        need(
            type(context["decoys"]) is list
            and len(context["decoys"]) == 2
            and all(
                type(r) is dict
                and set(r) == {"id", "role", "tool_name", "text"}
                and type(r["id"]) is int
                and r["id"] > 0
                and type(r["text"]) is str
                and len(r["text"]) <= 4096
                for r in context["decoys"]
            ),
            "decoys",
        )
        need(
            [(r["role"], r["tool_name"]) for r in context["decoys"]]
            == [("assistant", None), ("tool", "other_tool")],
            "decoy_roles",
        )
        need(
            type(deadline) in (int, float) and math.isfinite(deadline) and deadline >= 0, "deadline"
        )
        initial = clock()
        need(
            type(initial) in (int, float) and math.isfinite(initial) and 0 <= initial < deadline,
            "clock_initial",
        )
        self.last_clock = initial
        self.context = immutable_copy(context)
        self.port = port if port is not None else UnboundRuntimePort()
        self.deadline = deadline
        self.clock = clock
        self.index = 0
        self.closed = False
        self.unknown = False
        self.in_flight = False
        self.captures = []
        self._raw = []
        self._body_bytes = 0
        self.derived = {}
        self.case_ref = {}
        self.phase_index = 0

    def _tick(self) -> float:
        now = self.clock()
        need(
            type(now) in (int, float)
            and math.isfinite(now)
            and self.last_clock <= now < self.deadline,
            "deadline",
        )
        self.last_clock = now
        return now

    def cancel(self) -> None:
        self.closed = True
        self.unknown = True

    def _path(self, step: Step) -> str:
        if step.action in {"descriptor", "decoys", "closed_read"}:
            value = self.context["paths"].get(step.case + ":" + step.key)
            need(
                type(value) is str and value.startswith("/hmp/v1/bots/" + step.profile + "/"),
                "read_path",
            )
            return value
        if step.action == "mutation":
            return ""
        refkey = "A1-alpha" if step.action == "cross" else step.key
        if step.key == "closed":
            refkey = "closed"
        elif step.key.startswith("before_") or step.key.startswith("after_"):
            refkey = step.case
        elif step.key.startswith("control_"):
            refkey = "NM07-control" if step.case == "NM07" else "NM08-control"
        ref = self.derived.get((step.case, refkey), self.context["refs"].get(refkey))
        need(type(ref) is str and REF.fullmatch(ref) is not None, "fetch_ref")
        return "/hmp/v1/bots/" + step.profile + "/media/" + ref

    def _response(self, step: Step, req: Request, result: dict) -> bytes:
        need(
            type(result) is dict
            and set(result)
            == {
                "phase",
                "sequence",
                "actor",
                "profile",
                "path",
                "iid",
                "headerIid",
                "status",
                "contentType",
                "body",
                "sourcePin",
                "nativeRow",
            },
            "capture_shape",
        )
        need(
            type(result["sequence"]) is int
            and type(result["nativeRow"]) is int
            and all(
                type(result[k]) is str
                for k in ("phase", "actor", "profile", "path", "iid", "headerIid", "sourcePin")
            ),
            "capture_types",
        )
        need(
            (
                result["phase"],
                result["sequence"],
                result["actor"],
                result["profile"],
                result["path"],
                result["iid"],
                result["headerIid"],
                result["sourcePin"],
                result["nativeRow"],
            )
            == (
                step.phase,
                req.sequence,
                step.actor,
                step.profile,
                req.path,
                req.iid,
                req.header_iid,
                req.source_pin,
                req.native_row,
            ),
            "capture_binding",
        )
        need(type(result["status"]) is int and result["status"] == step.expected_status, "status")
        body = result["body"]
        need(type(body) is bytes and len(body) <= MAX_BODY, "body_cap")
        need(
            type(result["contentType"]) is str and len(result["contentType"]) <= 128, "content_type"
        )
        if step.expected_status == 200 and step.action == "fetch":
            need(
                result["contentType"] == "image/png"
                and len(body) == 70
                and hashlib.sha256(body).hexdigest() == PNG_SHA256,
                "png",
            )
        elif step.expected_error is not None:
            need(
                not result["contentType"].startswith("image/") and len(body) <= 4096,
                "negative_image",
            )
            obj = strict_json(body)
            need(type(obj) is dict and obj.get("error") == step.expected_error, "error")
            if step.case == "NM07" and step.key.startswith("after_"):
                need(obj.get("authz") == "pending_operator", "revoke_authz")
        else:
            need(result["contentType"] == "application/json", "json_type")
            obj = strict_json(body)
            need(
                type(obj) is dict
                and type(obj.get("messages")) is list
                and len(obj["messages"]) <= 64,
                "messages",
            )
            if step.action == "descriptor":
                matches = []
                for row in obj["messages"]:
                    need(type(row) is dict, "row")
                    if row.get("media") is not None:
                        media = row["media"]
                        need(
                            type(row.get("id")) is int
                            and row.get("id") == req.native_row
                            and row.get("role") == "tool"
                            and row.get("tool_name") == "image_generate"
                            and type(media) is dict
                            and media.get("kind") == "image"
                            and type(media.get("ref")) is str
                            and REF.fullmatch(media["ref"]) is not None,
                            "descriptor_origin",
                        )
                        matches.append(media["ref"])
                need(len(matches) == 1, "descriptor_count")
                existing = self.context["refs"].get(step.key)
                need(existing is None or existing == matches[0], "descriptor_ref")
                if step.case in {"NM03", "NM04"}:
                    prior = self.case_ref.get(step.case)
                    current = (req.native_row, matches[0])
                    need(prior is None or prior == current, "case_source_ref_changed")
                    self.case_ref[step.case] = current
                self.derived[(step.case, step.key)] = matches[0]
            elif step.action == "closed_read":
                need(
                    len(obj["messages"]) == len(self.context["closedRows"][step.case])
                    and all(
                        type(r) is dict
                        and type(r.get("id")) is int
                        and r.get("media") is None
                        and type(r.get("text")) is str
                        for r in obj["messages"]
                    ),
                    "closed_descriptors",
                )
                need(
                    [(r["id"], r["text"]) for r in obj["messages"]]
                    == [(r["id"], r["text"]) for r in self.context["closedRows"][step.case]],
                    "closed_text_binding",
                )
            elif step.action == "decoys":
                rows = obj["messages"]
                need(
                    len(rows) == 2
                    and [(r.get("role"), r.get("tool_name")) for r in rows]
                    == [("assistant", None), ("tool", "other_tool")],
                    "decoy_roles",
                )
                need(
                    all(
                        type(r.get("id")) is int
                        and type(r.get("text")) is str
                        and r.get("media") is None
                        for r in rows
                    ),
                    "decoy_media",
                )
                need(
                    [(r["id"], r["text"]) for r in rows]
                    == [(r["id"], r["text"]) for r in self.context["decoys"]],
                    "decoy_text_binding",
                )
        return body

    def advance(self, expected_case: str, expected_action: str) -> dict:
        if self.in_flight:
            self.closed = True
            self.unknown = True
            raise PhaseRefusalError("in_flight_reentry")
        need(not self.closed and not self.unknown and self.index < len(STEPS), "closed_or_complete")
        step = STEPS[self.index]
        need(step.case == expected_case and step.action == expected_action, "out_of_order")
        phase = PHASES.index(step.phase)
        need(phase >= self.phase_index, "phase_rollback")
        self._tick()
        path = self._path(step)
        actor = self.context["actors"][step.actor]
        header_iid = (
            self.context["actors"]["A1"]["iid"]
            if step.case == "NM06" and step.key == "H"
            else actor["iid"]
        )
        row_key = (
            "NM06:"
            + (
                step.key
                if step.key in ("A1-alpha", "A2-alpha", "A1-beta", "B1-alpha")
                else "A1-alpha"
            )
            if step.case == "NM06"
            else step.case
        )
        req = Request(
            self.index + 1,
            step,
            path,
            actor["iid"],
            header_iid,
            actor["deviceId"],
            actor["userId"],
            self.context["sourcePin"],
            self.context["nativeRows"][row_key],
        )
        # First potentially effectful boundary. Any exception or timeout is sticky unknown.
        self.unknown = True
        self.in_flight = True
        try:
            result = self.port.mutate(req) if step.action == "mutation" else self.port.observe(req)
            need(not self.closed and self.unknown, "cancel_during_callback")
            self._tick()
            if step.action == "mutation":
                need(
                    type(result) is dict
                    and set(result)
                    == {
                        "phase",
                        "sequence",
                        "api",
                        "target",
                        "sourcePin",
                        "beforeCaptureSHA256",
                        "afterNativeSHA256",
                    },
                    "mutation_shape",
                )
                need(
                    type(result["sequence"]) is int
                    and all(
                        type(result[k]) is str for k in ("phase", "api", "target", "sourcePin")
                    ),
                    "mutation_types",
                )
                need(
                    result["phase"] == step.phase
                    and result["sequence"] == req.sequence
                    and result["api"] == step.key
                    and result["target"] == step.actor
                    and result["sourcePin"] == req.source_pin,
                    "mutation_binding",
                )
                for key in ("beforeCaptureSHA256", "afterNativeSHA256"):
                    need(
                        type(result[key]) is str
                        and re.fullmatch(r"[a-f0-9]{64}", result[key]) is not None,
                        "mutation_hash",
                    )
                need(
                    self.captures
                    and self.captures[-1]["case"] == step.case
                    and self.captures[-1]["key"].startswith("before_")
                    and self.captures[-1]["bodySHA256"] == result["beforeCaptureSHA256"],
                    "mutation_before",
                )
                digest = result["afterNativeSHA256"]
                raw = b""
            else:
                raw = self._response(step, req, result)
                need(self._body_bytes + len(raw) <= MAX_TOTAL_BODY, "body_budget")
                digest = hashlib.sha256(raw).hexdigest()
            capture = {
                "case": step.case,
                "phase": step.phase,
                "action": step.action,
                "key": step.key,
                "sequence": req.sequence,
                "actor": step.actor,
                "profile": step.profile,
                "path": req.path,
                "bodySHA256": digest,
            }
            self.captures.append(capture)
            self._raw.append(raw)
            self._body_bytes += len(raw)
            self.index += 1
            self.phase_index = phase
            self.unknown = False
            self.in_flight = False
            return dict(capture)
        except BaseException:
            self.closed = True
            self.unknown = True
            self.in_flight = False
            raise

    def source_selection(self) -> dict:
        need(not self.closed and not self.unknown and self.index == len(STEPS), "incomplete")
        need(
            len(self.captures) == len(STEPS)
            and [c["sequence"] for c in self.captures] == list(range(1, len(STEPS) + 1)),
            "capture_inventory",
        )
        need(
            len(self._raw) == len(STEPS)
            and sum(map(len, self._raw)) == self._body_bytes <= MAX_TOTAL_BODY,
            "raw_inventory",
        )
        need(
            all(
                step.action == "mutation"
                or hashlib.sha256(raw).hexdigest() == capture["bodySHA256"]
                for step, raw, capture in zip(STEPS, self._raw, self.captures, strict=True)
            ),
            "raw_capture_drift",
        )
        need(
            len(
                {
                    self.derived.get(("NM06", key))
                    for key in ("A1-alpha", "A2-alpha", "A1-beta", "B1-alpha")
                }
            )
            == 4,
            "nm06_distinct_refs",
        )
        return {
            "scope": "native-media-python8-v1",
            "status": "SOURCE_ASSERTIONS_COMPLETE_RUNTIME_UNQUALIFIED",
            "qualifiedCases": [],
            "assertedCases": list(CASES),
            "unqualifiedCases": {
                "NM09": "owned_fault_unimplemented",
                "NM10": "real_Dart_consumer_unrun",
            },
            "captureSHA256": hashlib.sha256(
                json.dumps(self.captures, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "runtimeQualified": False,
            "custodyCertified": False,
        }
