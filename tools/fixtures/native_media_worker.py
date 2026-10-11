"""Private root-only native-media worker SOURCE proposal; not execution admission.

Native/HMP/SDK imports occur only after qualified pinned inputs and controlled bootstrap.
Every receipt is candidate observation, never provider/native/runtime qualification.
The separately reviewed c018 parent owns processes, listeners, captures and final audits.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import json
import os
import re
import select
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PHASES = (
    "BIND",
    "GRAPH_IMPORT",
    "ALLOCATE_PRIVATE_SETUP",
    "PUBLIC_ENROLLMENT",
    "PRODUCE_SEED_GRANTS",
    "CLOSED_NONOWNER_CASES",
    "FINAL_START_POSITIVES",
    "NM06_DART_INPUT",
    "DART_CONSUMER",
    "LATE_GUARDS",
    "TERMINAL_AUDIT",
    "REPORT_JOIN",
)
OPS = {
    "CHECK_GRAPH": {"GRAPH_IMPORT"},
    "CREATE_PROFILES": {"ALLOCATE_PRIVATE_SETUP"},
    "CHECK_CONFIG": {
        "ALLOCATE_PRIVATE_SETUP",
        "PRODUCE_SEED_GRANTS",
        "CLOSED_NONOWNER_CASES",
        "FINAL_START_POSITIVES",
    },
    "START_GATEWAY": {"PUBLIC_ENROLLMENT", "CLOSED_NONOWNER_CASES", "FINAL_START_POSITIVES"},
    "BIND_ACTOR": {"PUBLIC_ENROLLMENT", "FINAL_START_POSITIVES"},
    "STOP_GATEWAY": {"PUBLIC_ENROLLMENT", "CLOSED_NONOWNER_CASES", "LATE_GUARDS"},
    "PRODUCE": {"PRODUCE_SEED_GRANTS"},
    "SEED": {"PRODUCE_SEED_GRANTS"},
    "GRANT": {"PRODUCE_SEED_GRANTS"},
    "OWN_READ": {"CLOSED_NONOWNER_CASES", "FINAL_START_POSITIVES", "NM06_DART_INPUT"},
    "LATE_OWN_READ": {"LATE_GUARDS"},
    "CROSS_PROBE": {"NM06_DART_INPUT"},
    "REVOKE": {"LATE_GUARDS"},
    "ROTATE": {"LATE_GUARDS"},
    "OWNED_FAULT": {"LATE_GUARDS"},
    "DART_HANDOFF": {"DART_CONSUMER"},
    "OBSERVE_FINAL": {"TERMINAL_AUDIT", "REPORT_JOIN"},
}
PROFILES = {"media-alpha", "media-beta"}
ACTORS = {"A": {"A1", "A2"}, "B": {"B1"}}
GATES = (
    "parentAdmission",
    "sourceGraph",
    "runtimeGraph",
    "ABI",
    "bootstrap",
    "bootReadWriteProfile",
    "portHandoff",
    "TLS",
    "configRoles",
    "libraryWorkerReview",
    "latePermitPlan",
)
ARG_FIELDS = {
    "CHECK_GRAPH": set(),
    "CREATE_PROFILES": set(),
    "CHECK_CONFIG": {"variant"},
    "START_GATEWAY": set(),
    "STOP_GATEWAY": set(),
    "BIND_ACTOR": {"deviceId", "userId", "bearer", "p4CaptureSHA256"},
    "PRODUCE": {"invocation"},
    "SEED": {"invocation", "chatId", "botSessionId"},
    "GRANT": set(),
    "OWN_READ": {"path"},
    "LATE_OWN_READ": {"path", "permit"},
    "CROSS_PROBE": {"path", "instanceHeader"},
    "REVOKE": set(),
    "ROTATE": {"chatId", "oldSessionId"},
    "OWNED_FAULT": {"fault", "invocation"},
    "DART_HANDOFF": {"inputHash"},
    "OBSERVE_FINAL": set(),
}
ACTOR_OPS = {
    "BIND_ACTOR",
    "SEED",
    "GRANT",
    "OWN_READ",
    "LATE_OWN_READ",
    "CROSS_PROBE",
    "REVOKE",
    "ROTATE",
}
PROFILE_OPS = {
    "PRODUCE",
    "SEED",
    "GRANT",
    "OWN_READ",
    "LATE_OWN_READ",
    "CROSS_PROBE",
    "REVOKE",
    "ROTATE",
}
COMMAND_CAP = 4096
RECEIPT_CAP = 131072
# Byte-identical route grammar from pinned local_media_fixture.get; no arbitrary GET route.
READ_ROUTE = (
    r"/hmp/v1/bots/media-(alpha|beta)/(media/[A-Za-z0-9_-]{43}|"
    r"conversations/default\?limit=64|conversations/default/messages\?after=0&limit=64|"
    r"sessions/ses1_[A-Za-z0-9_-]{22}/messages\?after=0&limit=64|"
    r"sessions/ses1_[A-Za-z0-9_-]{22}/messages/from-start\?limit=64)"
)


class RefusalError(RuntimeError):
    pass


def require(condition, code):
    if not condition:
        raise RefusalError(code)


def identity(s):
    values = (
        s.st_dev,
        s.st_ino,
        s.st_mode,
        s.st_uid,
        s.st_gid,
        s.st_nlink,
        s.st_size,
        s.st_mtime_ns,
        s.st_ctime_ns,
    )
    require(all(type(value) is int for value in values), "metadata")
    return values


@dataclass
class Ledger:
    end: float
    commands: int = 0
    read_bytes: int = 0
    written_bytes: int = 0
    read_calls: int = 0
    write_calls: int = 0
    held: int = 0
    peak: int = 0
    produced: int = 0
    messages: int = 0

    def tick(self):
        require(time.monotonic() < self.end, "deadline")

    def charge(self, kind, amount):
        self.tick()
        require(type(amount) is int and amount >= 0, "charge")
        caps = {
            "commands": 64,
            "read_bytes": 67108864,
            "written_bytes": 8388608,
            "read_calls": 65536,
            "write_calls": 65536,
            "produced": 4,
            "messages": 64,
        }
        require(kind in caps and getattr(self, kind) + amount <= caps[kind], "budget")
        setattr(self, kind, getattr(self, kind) + amount)

    def open(self):
        self.tick()
        require(self.held < 128, "fd_cap")
        self.held += 1
        self.peak = max(self.peak, self.held)

    def close_known(self):
        require(self.held > 0, "fd_accounting")
        self.held -= 1


def read_pin(pin, ledger):
    """Exact descriptor leaf, stable ns identity, no alias/follow/blocking leaf fallback."""
    require(type(pin) is dict and set(pin) == {"path", "bytes", "SHA256", "identity"}, "pin_shape")
    path = Path(pin["path"])
    require(path.is_absolute() and ".." not in path.parts, "pin_path")
    require(type(pin["bytes"]) is int and 0 < pin["bytes"] <= 8388608, "pin_size")
    parent = None
    leaf = None
    try:
        ledger.open()
        parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for name in path.parts[1:-1]:
            ledger.open()
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            previous = parent
            parent = None
            try:
                os.close(previous)
                ledger.close_known()
            except BaseException as parent_error:
                try:
                    os.close(child)
                    ledger.close_known()
                except BaseException as child_error:
                    raise child_error from parent_error
                raise
            parent = child
        ledger.open()
        leaf = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(leaf)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "pin_leaf")
        require(
            identity(before) == tuple(pin["identity"]) and before.st_size == pin["bytes"],
            "pin_metadata",
        )
        remaining = before.st_size
        parts = bytearray()
        while remaining:
            ledger.charge("read_bytes", min(8192, remaining))
            ledger.charge("read_calls", 1)
            part = os.read(leaf, min(8192, remaining))
            require(type(part) is bytes and 0 < len(part) <= min(8192, remaining), "pin_short")
            remaining -= len(part)
            parts.extend(part)
        ledger.charge("read_bytes", 1)
        ledger.charge("read_calls", 1)
        require(os.read(leaf, 1) == b"", "pin_growth")
        require(hashlib.sha256(parts).hexdigest() == pin["SHA256"], "pin_hash")
        require(
            identity(os.fstat(leaf)) == tuple(pin["identity"])
            and identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False))
            == tuple(pin["identity"]),
            "pin_drift",
        )
        return bytes(parts)
    finally:
        try:
            if leaf is not None:
                os.close(leaf)
                ledger.close_known()
        finally:
            if parent is not None:
                os.close(parent)
                ledger.close_known()


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, "json_duplicate")
        obj[key] = value
    return obj


def decode_command(body):
    require(type(body) is bytes and 0 < len(body) <= COMMAND_CAP, "command_cap")
    try:
        command = json.loads(body, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError) as error:
        raise RefusalError("command_json") from error
    require(
        type(command) is dict
        and set(command) == {"sequence", "phase", "op", "role", "actor", "profile", "args"},
        "command_shape",
    )
    require(type(command["sequence"]) is int and 1 <= command["sequence"] <= 64, "sequence")
    require(command["phase"] in PHASES and command["op"] in OPS, "opcode")
    require(command["phase"] in OPS[command["op"]], "op_phase")
    require(command["role"] in ACTORS, "role")
    require(command["actor"] is None or command["actor"] in ACTORS[command["role"]], "actor_role")
    require(command["profile"] is None or command["profile"] in PROFILES, "profile")
    require(
        type(command["args"]) is dict and set(command["args"]) == ARG_FIELDS[command["op"]], "args"
    )
    require(command["op"] not in ACTOR_OPS or command["actor"] is not None, "actor_required")
    require(command["op"] not in PROFILE_OPS or command["profile"] is not None, "profile_required")
    for key, value in command["args"].items():
        if key == "instanceHeader" and value is None:
            continue
        require(
            type(value) is str
            and 0 < len(value.encode("utf-8")) <= 1024
            and "\r" not in value
            and "\n" not in value,
            "arg_string",
        )
        if key in {"p4CaptureSHA256", "inputHash"}:
            require(len(value) == 64 and all(c in "0123456789abcdef" for c in value), "arg_hash")
        if key == "invocation":
            require(value in {"P01", "P02", "P03", "P04"}, "invocation")
        if key == "fault":
            require(value in {"symlink", "hardlink", "raster", "digest"}, "fault_kind")
        if key == "variant":
            require(value in {"initial", "closed", "final"}, "config_variant")
        if key == "path":
            require(value.startswith("/hmp/v1/bots/" + command["profile"] + "/"), "path_profile")
            require(re.fullmatch(READ_ROUTE, value) is not None, "request_route")
        if key == "permit":
            require(
                len(value) == 64 and all(c in "0123456789abcdef" for c in value),
                "late_permit_shape",
            )
    return command


class LatePermitGate:
    """Closed worker-side late GET permits; parent cross-worker proof remains separate."""

    def __init__(self, body, spec):
        try:
            plan = json.loads(body, object_pairs_hook=unique_object)
        except (ValueError, UnicodeError) as error:
            raise RefusalError("late_plan_json") from error
        require(
            type(plan) is dict
            and set(plan) == {"format", "generation", "parentAdmissionSHA256", "entries"},
            "late_plan_shape",
        )
        require(plan["format"] == "native-media-late-permit-plan-v1", "late_plan_format")
        generation = plan["generation"]
        require(
            type(generation) is str
            and len(generation) == 64
            and all(c in "0123456789abcdef" for c in generation),
            "late_generation",
        )
        require(generation == spec.get("lateGeneration"), "late_generation_binding")
        require(
            plan["parentAdmissionSHA256"] == spec["gates"]["parentAdmission"]["SHA256"],
            "late_parent_admission_binding",
        )
        entries = plan["entries"]
        expected_all = {
            ("NM07", "before_revoke", "A1", "A"),
            ("NM07", "after_revoke", "A1", "A"),
            ("NM07", "control_revoke", "A2", "A"),
            ("NM08", "before_rotate", "B1", "B"),
            ("NM08", "after_rotate", "B1", "B"),
            ("NM08", "control_rotate", "A1", "A"),
        }
        expected = {item for item in expected_all if item[3] == spec["role"]}
        require(type(entries) is list and len(entries) == len(expected), "late_entry_count")
        self.rows = {}
        self.spec = spec
        self.generation = generation
        found = set()
        permits = set()
        case_refs = {}
        for row in entries:
            require(
                type(row) is dict
                and set(row)
                == {
                    "case",
                    "key",
                    "actor",
                    "role",
                    "profile",
                    "path",
                    "oldRef",
                    "permit",
                    "iid",
                    "port",
                    "actorP4SHA256",
                    "sourceGraphSHA256",
                },
                "late_entry_shape",
            )
            role = (row["case"], row["key"], row["actor"], row["role"])
            require(role in expected and role not in found, "late_entry_role")
            found.add(role)
            require(row["profile"] == "media-alpha", "late_entry_profile")
            for key in ("permit", "actorP4SHA256", "sourceGraphSHA256"):
                value = row[key]
                require(
                    type(value) is str
                    and len(value) == 64
                    and all(c in "0123456789abcdef" for c in value),
                    "late_entry_hash",
                )
            require(row["permit"] not in permits, "late_permit_duplicate")
            permits.add(row["permit"])
            require(
                row["role"] == spec["role"]
                and row["sourceGraphSHA256"] == spec["gates"]["sourceGraph"]["SHA256"],
                "late_source_binding",
            )
            require(
                type(row["oldRef"]) is str
                and re.fullmatch(r"[A-Za-z0-9_-]{43}", row["oldRef"]) is not None,
                "late_old_ref",
            )
            require(
                type(row["path"]) is str
                and row["path"].startswith("/hmp/v1/bots/media-alpha/")
                and re.fullmatch(READ_ROUTE, row["path"]) is not None,
                "late_route",
            )
            if row["case"] in case_refs:
                require(row["oldRef"] == case_refs[row["case"]], "late_case_ref_change")
            case_refs[row["case"]] = row["oldRef"]
            if row["key"].startswith(("before_", "after_")):
                require(
                    row["path"] == "/hmp/v1/bots/media-alpha/media/" + row["oldRef"],
                    "late_target_ref",
                )
            else:
                require(
                    row["path"] != "/hmp/v1/bots/media-alpha/media/" + row["oldRef"],
                    "late_control_is_target",
                )
            require(
                row["iid"] == spec["iid"]
                and type(row["port"]) is int
                and row["port"] == spec["port"],
                "late_listener_binding",
            )
            bind = [
                command
                for command in spec["commandPlan"]
                if command["op"] == "BIND_ACTOR" and command["actor"] == row["actor"]
            ]
            require(
                len(bind) == 1 and bind[0]["args"]["p4CaptureSHA256"] == row["actorP4SHA256"],
                "late_actor_lease_binding",
            )
            self.rows[row["permit"]] = row
        require(found == expected, "late_entry_inventory")
        self.used = set()
        self.before = {}
        self.mutated = set()
        self.after = set()

    def target_identity(self, row):
        """Immutable local before-target identity; a body digest alone has no authority."""
        return (
            row["case"],
            row["role"],
            row["actor"],
            row["profile"],
            row["oldRef"],
            row["path"],
            self.generation,
            row["sourceGraphSHA256"],
            row["actorP4SHA256"],
            row["iid"],
            row["port"],
            self.spec["gates"]["parentAdmission"]["SHA256"],
        )

    def command_identity(self, command):
        # Include the complete closed command, particularly sequence and args.
        # This immutable byte ticket is not an authority from a caller.
        return json.dumps(command, sort_keys=True, separators=(",", ":")).encode()

    def binding_current(self, identity):
        (
            case,
            role,
            actor,
            profile,
            old_ref,
            path,
            generation,
            source,
            p4,
            iid,
            port,
            parent_admission,
        ) = identity
        require(
            self.generation == generation
            and self.spec["lateGeneration"] == generation
            and self.spec["role"] == role
            and self.spec["iid"] == iid
            and self.spec["port"] == port
            and self.spec["gates"]["sourceGraph"]["SHA256"] == source,
            "late_current_source_generation_listener",
        )
        require(
            self.spec["gates"]["parentAdmission"]["SHA256"] == parent_admission,
            "late_current_parent_admission",
        )
        bind = [
            item
            for item in self.spec["commandPlan"]
            if item["op"] == "BIND_ACTOR" and item["actor"] == actor
        ]
        require(
            len(bind) == 1 and bind[0]["args"]["p4CaptureSHA256"] == p4, "late_current_actor_lease"
        )
        require(
            case in {"NM07", "NM08"}
            and profile == "media-alpha"
            and type(old_ref) is str
            and type(path) is str,
            "late_current_target_shape",
        )

    def pre(self, command):
        op = command["op"]
        if op == "LATE_OWN_READ":
            permit = command["args"]["permit"]
            require(
                permit in self.rows and permit not in self.used, "late_permit_unissued_or_replayed"
            )
            row = self.rows[permit]
            require(
                command["role"] == row["role"]
                and command["actor"] == row["actor"]
                and command["profile"] == row["profile"]
                and command["args"]["path"] == row["path"],
                "late_command_binding",
            )
            case, key = row["case"], row["key"]
            if key.startswith("before_"):
                require(case not in self.before, "late_before_replay")
            elif key.startswith("after_"):
                require(case in self.before and case in self.mutated, "late_after_before_mutation")
                require(
                    self.before[case][0] == self.target_identity(row), "late_after_target_changed"
                )
            elif case == "NM07":
                require(case in self.after and case in self.mutated, "late_control_order")
            # NM08 control is on A, whereas its before/mutation/after are on B.
            # The parent must separately prove and bind that cross-worker sequence
            # before issuing this one-use command; a worker cannot infer B's state.
            identity = self.target_identity(row)
            self.binding_current(identity)
            ticket = (
                "read",
                permit,
                identity,
                key,
                self.command_identity(command),
                self.before.get(case),
                case in self.mutated,
                case in self.after,
            )
            self.used.add(permit)
            return ticket
        if op in {"REVOKE", "ROTATE"}:
            case = "NM07" if op == "REVOKE" else "NM08"
            require(
                case in self.before and case not in self.mutated, "late_mutation_requires_before"
            )
            identity = self.before[case][0]
            targets = [
                row
                for row in self.rows.values()
                if row["case"] == case and row["key"].startswith("before_")
            ]
            require(
                len(targets) == 1 and identity == self.target_identity(targets[0]),
                "late_mutation_before_identity_drift",
            )
            permit = self.before[case][2]
            require(
                permit in self.rows
                and self.rows[permit] is targets[0]
                and targets[0]["permit"] == permit,
                "late_mutation_before_permit_drift",
            )
            self.binding_current(identity)
            require(
                command["phase"] == "LATE_GUARDS"
                and (case, command["role"], command["actor"], command["profile"]) == identity[:4]
                and (case, command["role"], command["actor"])
                == (("NM07", "A", "A1") if op == "REVOKE" else ("NM08", "B", "B1")),
                "late_mutation_target_changed",
            )
            return ("mutation", case, identity, self.before[case], self.command_identity(command))
        return None

    def post(self, command, row, observation):
        # Select validation from the pre-action ticket. A changed opcode may
        # never turn a late action into the ordinary no-ticket return path.
        if row is None:
            require(
                command["op"] not in {"LATE_OWN_READ", "REVOKE", "ROTATE"}, "late_ticket_missing"
            )
            return
        require(type(row) is tuple and row and row[0] in {"mutation", "read"}, "late_ticket_kind")
        if row[0] == "mutation":
            require(command["op"] in {"REVOKE", "ROTATE"}, "late_ticket_opcode")
            op = command["op"]
            case = "NM07" if op == "REVOKE" else "NM08"
            targets = [
                target
                for target in self.rows.values()
                if target["case"] == case and target["key"].startswith("before_")
            ]
            require(
                len(targets) == 1
                and type(row) is tuple
                and len(row) == 5
                and row[0:2] == ("mutation", case)
                and row[2] == self.target_identity(targets[0])
                and row[3] == self.before[case]
                and row[4] == self.command_identity(command)
                and row[2] == self.before[case][0]
                and self.before[case][2] in self.rows
                and self.rows[self.before[case][2]] is targets[0]
                and targets[0]["permit"] == self.before[case][2]
                and case not in self.mutated,
                "late_mutation_receipt_target",
            )
            self.binding_current(row[2])
            event = (
                "public_native_revoke_observation"
                if op == "REVOKE"
                else "actual_running_public_store_rotation"
            )
            require(
                type(observation) is dict and observation.get("event") == event,
                "late_mutation_actual_receipt",
            )
            self.mutated.add(case)
            return
        require(command["op"] == "LATE_OWN_READ", "late_ticket_opcode")
        require(type(row) is tuple and len(row) == 8 and row[0] == "read", "late_read_ticket")
        (
            _,
            permit,
            identity,
            key,
            command_at_start,
            before_at_start,
            mutated_at_start,
            after_at_start,
        ) = row
        require(
            permit in self.rows
            and permit in self.used
            and self.target_identity(self.rows[permit]) == identity
            and self.rows[permit]["permit"] == permit
            and self.rows[permit]["key"] == key
            and self.command_identity(command) == command_at_start
            and self.before.get(identity[0]) == before_at_start
            and (identity[0] in self.mutated) == mutated_at_start
            and (identity[0] in self.after) == after_at_start,
            "late_read_return_identity_drift",
        )
        self.binding_current(identity)
        require(
            type(observation) is dict
            and observation.get("event") == "actual_pinned_http_observation",
            "late_http_receipt",
        )
        require(
            set(observation)
            == {"event", "status", "rawBodyB64", "contentType", "bodySHA256", "bodyBytes"},
            "late_http_shape",
        )
        require(
            type(observation["status"]) is int
            and type(observation["rawBodyB64"]) is str
            and type(observation["contentType"]) is str
            and type(observation["bodySHA256"]) is str
            and type(observation["bodyBytes"]) is int
            and 0 <= observation["bodyBytes"] <= 65536,
            "late_http_types",
        )
        try:
            body = base64.b64decode(observation["rawBodyB64"], validate=True)
        except (ValueError, binascii.Error) as error:
            raise RefusalError("late_http_base64") from error
        require(
            len(body) == observation["bodyBytes"]
            and hashlib.sha256(body).hexdigest() == observation["bodySHA256"],
            "late_http_body_binding",
        )
        case = identity[0]
        if key.startswith("before_") or key.startswith("control_"):
            require(
                observation.get("status") == 200 and observation.get("contentType") == "image/png",
                "late_positive",
            )
        else:
            require(
                observation.get("status") == (403 if case == "NM07" else 404), "late_after_denial"
            )
        if key.startswith("before_"):
            self.before[case] = (identity, observation["bodySHA256"], permit)
        elif key.startswith("after_"):
            self.after.add(case)


def bounded_value(value, *, depth=0, counter=None):
    """Validate observation shape before JSON allocation; never accept qualification fields."""
    if counter is None:
        counter = [0, 0]
    require(depth <= 10, "receipt_depth")
    counter[0] += 1
    require(counter[0] <= 1024, "receipt_nodes")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        require(-(1 << 63) <= value < (1 << 63), "receipt_integer")
        return
    if type(value) is str:
        counter[1] += len(value.encode("utf-8"))
        require(counter[1] <= 98304, "receipt_strings")
        return
    if type(value) is list:
        require(len(value) <= 128, "receipt_list")
        for item in value:
            bounded_value(item, depth=depth + 1, counter=counter)
        return
    require(type(value) is dict and len(value) <= 32, "receipt_shape")
    for key, item in value.items():
        require(
            type(key) is str
            and key
            not in {
                "qualified",
                "nativePass",
                "runtimeQualified",
                "providerQualified",
                "custodyComplete",
                "sourcePreserved",
            },
            "receipt_authority",
        )
        bounded_value(key, depth=depth + 1, counter=counter)
        bounded_value(item, depth=depth + 1, counter=counter)


def encode_receipt(receipt):
    observation = receipt["observation"]
    bounded_value(observation)
    require(
        receipt["runtimeQualified"] is False and receipt["custodyCertified"] is False,
        "receipt_qualification",
    )
    body = json.dumps(receipt, separators=(",", ":"), ensure_ascii=True).encode("ascii") + b"\n"
    require(len(body) <= RECEIPT_CAP, "receipt_cap")
    return body


class PipeIO:
    """Own inherited nonblocking pipes only. Parent c018 owns named evidence and cleanup."""

    def __init__(self, control_fd, receipt_fd, expected, ledger):
        require(
            type(control_fd) is int
            and type(receipt_fd) is int
            and control_fd > 2
            and receipt_fd > 2
            and control_fd != receipt_fd,
            "channel_fd",
        )
        self.control_fd, self.receipt_fd = control_fd, receipt_fd
        self.ledger = ledger
        self.buffer = bytearray()
        for name, fd in (("control", control_fd), ("receipt", receipt_fd)):
            s = os.fstat(fd)
            require(stat.S_ISFIFO(s.st_mode), "channel_type")
            require(
                (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid) == tuple(expected[name]),
                "channel_identity",
            )
            os.set_blocking(fd, False)

    def read_command(self):
        while b"\n" not in self.buffer:
            self.ledger.tick()
            require(len(self.buffer) <= COMMAND_CAP, "command_cap")
            ready, _, _ = select.select(
                [self.control_fd], [], [], max(0, self.ledger.end - time.monotonic())
            )
            require(ready == [self.control_fd], "control_timeout")
            size = min(1024, COMMAND_CAP + 1 - len(self.buffer))
            self.ledger.charge("read_bytes", size)
            self.ledger.charge("read_calls", 1)
            part = os.read(self.control_fd, size)
            require(type(part) is bytes and len(part) <= size, "control_read")
            if not part:
                require(not self.buffer, "control_partial_eof")
                return None
            self.buffer.extend(part)
        end = self.buffer.index(b"\n")
        body = bytes(self.buffer[:end])
        del self.buffer[: end + 1]
        return decode_command(body)

    def write_receipt(self, receipt):
        body = encode_receipt(receipt)
        self.ledger.charge("written_bytes", len(body))
        view = memoryview(body)
        while view:
            self.ledger.tick()
            _, ready, _ = select.select(
                [], [self.receipt_fd], [], max(0, self.ledger.end - time.monotonic())
            )
            require(ready == [self.receipt_fd], "receipt_timeout")
            self.ledger.charge("write_calls", 1)
            count = os.write(self.receipt_fd, view[:4096])
            require(type(count) is int and 0 < count <= min(4096, len(view)), "receipt_short")
            view = view[count:]


class Dispatcher:
    def __init__(self, spec, ledger):
        require(
            type(spec) is dict and spec.get("format") == "native-media-worker-input-v1",
            "input_format",
        )
        require(spec.get("role") in ACTORS, "input_role")
        require(
            type(spec.get("commandPlan")) is list and 0 < len(spec["commandPlan"]) <= 64,
            "command_plan",
        )
        self.spec, self.ledger = spec, ledger
        self.plan = spec["commandPlan"]
        previous_phase = -1
        for sequence, command in enumerate(self.plan, 1):
            require(
                decode_command(json.dumps(command, separators=(",", ":")).encode()) == command,
                "plan_schema",
            )
            require(
                command["sequence"] == sequence and command["role"] == spec["role"],
                "plan_sequence_role",
            )
            require(PHASES.index(command["phase"]) >= previous_phase, "plan_phase_regression")
            previous_phase = PHASES.index(command["phase"])
        self.index = 0
        self.failed = False
        self.cancelled = False
        self.runtime = None
        self.last_phase = -1
        self.last_observation = None
        self.late = None
        self.in_dispatch = False

    def fail(self):
        self.failed = True

    def bind_runtime(self):
        require(self.runtime is None, "runtime_already_bound")
        require(
            type(self.spec.get("gates")) is dict and set(self.spec["gates"]) == set(GATES),
            "gate_inventory",
        )
        gate_bodies = {}
        for name in GATES:
            require(self.spec["gates"][name] is not None, "unbound_" + name)
            gate_bodies[name] = read_pin(self.spec["gates"][name], self.ledger)
        bootstrap = json.loads(gate_bodies["bootstrap"], object_pairs_hook=unique_object)
        require(bootstrap["format"] == "native-media-bootstrap-v1", "bootstrap_kind")
        require(self.spec["bootstrapPaths"] == bootstrap["paths"], "bootstrap_authority_join")
        require(
            sys.flags.optimize == 0
            and sys.flags.ignore_environment == 1
            and sys.flags.dont_write_bytecode == 1
            and sys.flags.no_site == 1,
            "python_startup",
        )
        require(os.environ.get("HOME") == "/Users/mhedhli", "literal_home")
        require(os.environ == self.spec["environment"], "environment")
        require(
            type(self.spec.get("bootstrapPaths")) is list
            and self.spec["bootstrapPaths"] == self.spec["approvedBootstrapPaths"],
            "bootstrap_paths",
        )
        require(
            not any(
                name in sys.modules
                for name in (
                    "tools",
                    "gateway",
                    "hmp_plugin",
                    "local_media_fixture",
                    "local_media_seed",
                    "local_media_provider_response",
                )
            ),
            "ambient_module",
        )
        self.late = LatePermitGate(gate_bodies["latePermitPlan"], self.spec)
        sys.path[:] = self.spec["bootstrapPaths"]
        self.runtime = NativeRuntime(self.spec, self.ledger)

    async def dispatch(self, command):
        started = False
        command_at_start = None
        try:
            require(not self.in_dispatch, "dispatch_reentry")
            self.in_dispatch = True
            self.ledger.tick()
            bounded_value(command)
            # The same closed decoder validates direct dispatcher calls as well as pipe frames.
            require(
                decode_command(json.dumps(command, separators=(",", ":")).encode()) == command,
                "dispatcher_schema",
            )
            command_at_start = json.dumps(command, sort_keys=True, separators=(",", ":")).encode()
            # Three independent objects: the immutable accepted request,
            # caller/plan input, and the copy passed to the awaited runtime.
            accepted = decode_command(command_at_start)
            runtime_command = decode_command(command_at_start)
            require(command["sequence"] == self.index + 1, "sequence")
            require(not self.failed and not self.cancelled, "worker_sticky_failure")
            require(
                self.index < len(self.plan) and accepted == self.plan[self.index], "plan_binding"
            )
            require(command["role"] == self.spec["role"], "worker_role")
            phase = PHASES.index(accepted["phase"])
            require(phase >= self.last_phase, "phase_regression")
            self.ledger.charge("commands", 1)
            self.last_phase = phase
            self.index += 1
            dispatch_index = self.index
            dispatch_gate = self.late
            if self.runtime is None:
                started = (
                    True  # Native imports can have side effects; never label them writer-free.
                )
                self.bind_runtime()
            dispatch_gate = self.late
            late_row = dispatch_gate.pre(accepted)
            # Source/port/ABI/config evidence pins authorize only these future actions. They
            # do not certify their actual result or any provider/native/custody qualification.
            started = True
            phase_end = self.spec["phaseEnds"][accepted["phase"]]
            require(
                type(phase_end) in (int, float) and time.monotonic() < phase_end <= self.ledger.end,
                "phase_deadline",
            )
            observation = await asyncio.wait_for(
                self.runtime.action(runtime_command), timeout=phase_end - time.monotonic()
            )
            self.ledger.tick()
            require(time.monotonic() < phase_end, "phase_deadline")
            require(not self.failed and not self.cancelled, "late_result_after_cancel")
            # Equality against self.plan alone is insufficient: it can alias
            # the caller's dict, and runtime_command is independently mutable.
            require(
                self.index == dispatch_index
                and self.last_phase == phase
                and self.late is dispatch_gate
                and self._command_bytes(command) == command_at_start
                and self._command_bytes(runtime_command) == command_at_start
                and self._command_bytes(self.plan[dispatch_index - 1]) == command_at_start,
                "post_await_command_drift",
            )
            dispatch_gate.post(accepted, late_row, observation)
            bounded_value(observation)
            self.last_observation = observation
            return {
                "sequence": accepted["sequence"],
                "phase": accepted["phase"],
                "op": accepted["op"],
                "status": "OBSERVATION_ONLY",
                "observation": observation,
                "runtimeQualified": False,
                "custodyCertified": False,
                "pendingActionMayHaveWriters": True,
                "failureSticky": False,
            }
        except BaseException as error:
            self.failed = True
            if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
                self.cancelled = True
            code = str(error) if isinstance(error, RefusalError) else type(error).__name__
            require(len(code) <= 128, "error_code_cap")
            reported = decode_command(command_at_start) if command_at_start is not None else command
            return {
                "sequence": reported.get("sequence"),
                "phase": reported.get("phase"),
                "op": reported.get("op"),
                "status": "FAILED_UNQUALIFIED",
                "observation": {"errorCode": code},
                "runtimeQualified": False,
                "custodyCertified": False,
                "pendingActionMayHaveWriters": started,
                "failureSticky": True,
            }
        finally:
            self.in_dispatch = False

    @staticmethod
    def _command_bytes(command):
        bounded_value(command)
        body = json.dumps(command, sort_keys=True, separators=(",", ":")).encode()
        require(decode_command(body) == command, "post_await_command_schema")
        return body


class NativeRuntime:
    """Actual native/HMP APIs only; unavailable routes stop, never fabricated callbacks."""

    def __init__(self, spec, ledger):
        from gateway.config import Platform, load_gateway_config

        # isort: split
        from gateway.run import GatewayRunner, _profile_runtime_scope

        # isort: split
        from gateway.session import SessionStore

        # isort: split
        from gateway.pairing import PairingStore

        # isort: split
        from hermes_state import SessionDB

        # isort: split
        from hmp_plugin import identity as hmp_identity

        # isort: split
        from hmp_plugin.server import store_path

        # isort: split
        from hmp_plugin.store import Store

        # isort: split
        import local_media_fixture

        # isort: split
        import local_media_seed

        self.spec, self.ledger = spec, ledger
        self.Platform, self.load_config, self.GatewayRunner = (
            Platform,
            load_gateway_config,
            GatewayRunner,
        )
        self.scope, self.SessionStore, self.PairingStore, self.SessionDB = (
            _profile_runtime_scope,
            SessionStore,
            PairingStore,
            SessionDB,
        )
        self.media, self.seed = local_media_fixture, local_media_seed
        self.hmp_identity, self.store_path, self.Store = hmp_identity, store_path, Store
        self.seeded_profiles = set()
        self.runner = self.adapter = self.ctx = None
        self.actors = {}
        self.raw = {}
        self.minted = False
        self.final_read_started = False
        self.routed = set()
        self.home = Path(spec["home"])
        self.runtime_dir = Path(spec["runtimeDir"])
        self.seed.check_environment(self.home, self.runtime_dir)

    def actor(self, command):
        name = command["actor"]
        require(name in ACTORS[self.spec["role"]] and name in self.actors, "actor_unbound")
        return self.actors[name]

    def live(self):
        require(
            self.runner is not None and self.adapter is not None and self.ctx is not None,
            "gateway_not_live",
        )
        require(
            self.adapter.gateway_runner is self.runner
            and self.adapter._session_store is self.runner.session_store,
            "native_object_lineage",
        )
        require(
            type(self.runner) is self.GatewayRunner
            and type(self.runner.session_store) is self.SessionStore,
            "native_object_type",
        )
        require(
            self.adapter._server.ctx is self.ctx
            and self.adapter._server.bound == ("127.0.0.1", self.spec["port"]),
            "listener_continuity",
        )

    def observe_no_independent_union(self, actor, profile):
        """Read actual native union seams in their real auth scope; never alter their answers."""
        self.live()
        require(self.ctx.bridge.instance_wide_grant(profile) is False, "instance_wide_union")
        source = self.adapter.build_source(
            chat_id=self.spec["actorChats"][actor.name][profile],
            chat_type="dm",
            user_id=actor.user_id,
            scope_id=profile,
            guild_id=profile,
        )
        require(
            source.chat_type == "dm"
            and source.is_bot is False
            and source.role_authorized is False
            and source.delivered_via_upstream_relay is False,
            "source_delegation",
        )

        def inspect_union():
            from gateway.authz_mixin import _auth_env, _registry_entry

            entry = _registry_entry(self.Platform("hmp"))
            require(entry is not None, "registry_unknown")
            names = {
                "GATEWAY_ALLOWED_USERS",
                "GATEWAY_ALLOW_ALL_USERS",
                "HMP_ALLOWED_USERS",
                "HMP_ALLOW_ALL_USERS",
            }
            names.update(name for name in (entry.allowed_users_env, entry.allow_all_env) if name)
            require(all(_auth_env(name) == "" for name in names), "env_union")
            adapter_profile = self.runner._adapter_profile_for_source(source)
            require(
                self.runner._chat_scoped_grant(source, adapter_profile, False, True) is False,
                "chat_or_upstream_union",
            )
            own = self.runner._own_policy_authorizes(source, actor.user_id, False, adapter_profile)
            require(own is None or own is False, "own_policy_union")
            require(
                self.runner._adapter_extra_allowlist_authorizes(source, actor.user_id, False)
                is False,
                "adapter_config_union",
            )
            return {"event": "actual_native_union_readback", "noIndependentGrantObserved": True}

        return self.runner._under_authorization_profile(source, inspect_union)

    async def action(self, command):
        op, args = command["op"], command["args"]
        if op == "CHECK_GRAPH":
            return {"event": "native_imported_observation", "versionsQualified": False}
        if op == "CREATE_PROFILES":
            require(self.runner is None, "gateway_must_be_stopped")
            self.seed.prepare_profiles(home=self.home, runtime=self.runtime_dir)
            return {"event": "public_profiles_created"}
        if op == "CHECK_CONFIG":
            require(self.runner is None, "gateway_must_be_stopped")
            pin = self.spec["configPins"][args["variant"]]
            body = read_pin(pin, self.ledger)
            return {"event": "sealed_config_observed", "SHA256": hashlib.sha256(body).hexdigest()}
        if op == "START_GATEWAY":
            require(self.runner is None and not self.minted, "restart_after_mint")
            require(
                self.spec.get("port") is not None and self.spec.get("iid") is not None,
                "unbound_endpoint",
            )
            runner = self.GatewayRunner(self.load_config())
            require(await runner.start() is True, "native_boot_refused")
            adapter = runner.adapters[self.Platform("hmp")]
            self.runner, self.adapter, self.ctx = runner, adapter, adapter._server.ctx
            self.live()
            require(self.ctx.iid == self.spec["iid"], "native_iid")
            return {"event": "actual_library_gateway_started", "iid": self.ctx.iid}
        if op == "STOP_GATEWAY":
            self.live()
            # A final descriptor read can allocate refs before its later image fetch.
            # Even an unknown/JSON result therefore prevents lifecycle cleanup here.
            require(not self.minted and not self.final_read_started, "post_mint_stop")
            await self.runner.stop()
            self.runner = self.adapter = self.ctx = None
            return {"event": "public_library_stop_observation"}
        if op == "BIND_ACTOR":
            self.live()
            require(command["actor"] in ACTORS[self.spec["role"]], "actor_role")
            require(set(args) == {"deviceId", "userId", "bearer", "p4CaptureSHA256"}, "actor_args")
            device = self.ctx.store.get_device(args["deviceId"])
            require(
                device is not None
                and device["state"] == "ACTIVE"
                and device["user_id"] == args["userId"],
                "actual_active_device",
            )
            actor = self.media.Actor(
                command["actor"],
                self.spec["port"],
                self.ctx.iid,
                args["deviceId"],
                args["userId"],
                args["bearer"],
            )
            require(command["actor"] not in self.actors, "actor_rebind")
            self.actors[command["actor"]] = actor
            return {
                "event": "actual_active_device_observed",
                "p4CaptureSHA256": args["p4CaptureSHA256"],
            }
        if op == "PRODUCE":
            require(self.runner is None, "gateway_must_be_stopped")
            self.ledger.charge("produced", 1)
            invocation = args["invocation"]
            require(invocation not in self.raw, "producer_replay")
            raw, observation = await asyncio.to_thread(
                self.seed.produce_once,
                home=self.home,
                runtime=self.runtime_dir,
                profile_home=self.home / "profiles" / command["profile"],
                port=self.spec["providerPort"],
                invocation=invocation,
                factory_path=Path(self.spec["factoryPath"]),
                factory_sha256=self.spec["factorySHA256"],
            )
            self.raw[invocation] = raw
            encoded = base64.b64encode(raw.encode()).decode("ascii")
            return {
                "event": "actual_registered_producer_returned",
                "rawResultB64": encoded,
                **observation,
            }
        if op == "SEED":
            require(self.runner is None, "gateway_must_be_stopped")
            actor = self.actor(command)
            require(command["profile"] not in self.seeded_profiles, "canonical_profile_seed_replay")
            self.ledger.charge("messages", 6)
            custody = self.hmp_identity.resolve_custody(hermes_root=self.home)
            store = self.Store(self.store_path(custody.anchor_dir))
            try:
                store.migrate()
                store.set_chat(actor.user_id, command["profile"], "default", args["chatId"])
            finally:
                store.close()
            result = await asyncio.to_thread(
                self.seed.seed_profile,
                home=self.home,
                runtime=self.runtime_dir,
                profile=command["profile"],
                user_id=actor.user_id,
                chat_id=args["chatId"],
                raw_result=self.raw[args["invocation"]],
                invocation=args["invocation"],
                bot_session_id=args["botSessionId"],
            )
            self.seeded_profiles.add(command["profile"])
            return {"event": "actual_public_native_seed", **result}
        if op == "GRANT":
            require(self.runner is None, "gateway_must_be_stopped")
            actor = self.actor(command)
            pairing = self.PairingStore(profile=command["profile"])
            if pairing.is_approved("hmp", actor.user_id) is False:
                require(
                    pairing.generate_code("hmp", actor.user_id, "native-media-fixture") is not None,
                    "native_grant_pending",
                )
                pending = [
                    row for row in pairing.list_pending("hmp") if row["user_id"] == actor.user_id
                ]
                require(len(pending) == 1, "native_grant_pending_count")
                approved = pairing.approve_request("hmp", pending[0]["request_id"])
                require(
                    type(approved) is dict and approved["user_id"] == actor.user_id,
                    "native_grant_refused",
                )
            require(pairing.is_approved("hmp", actor.user_id) is True, "native_grant_readback")
            return {"event": "public_native_grant_observed"}
        if op in {"OWN_READ", "LATE_OWN_READ", "CROSS_PROBE"}:
            self.live()
            actor = self.actor(command)
            if op in {"OWN_READ", "LATE_OWN_READ"} and command["phase"] != "CLOSED_NONOWNER_CASES":
                self.final_read_started = True
            reply = await asyncio.to_thread(
                self.media.get, actor, args["path"], instance_header=args.get("instanceHeader")
            )
            if reply.status == 200 and reply.content_type == "image/png":
                require(command["phase"] != "CLOSED_NONOWNER_CASES", "closed_phase_image")
                # A text200 never certifies media. Bind the exact actual descriptor-derived
                # route/ref before the fixed PNG body/hash check and any positive state.
                require(
                    re.fullmatch(
                        "/hmp/v1/bots/" + command["profile"] + r"/media/[A-Za-z0-9_-]{43}",
                        args["path"],
                    )
                    is not None,
                    "positive_media_route",
                )
                routes = self.spec["boundMediaRoutes"][command["actor"]][command["profile"]]
                require(
                    type(routes) is list
                    and 0 < len(routes) <= 4
                    and all(type(route) is str for route in routes)
                    and args["path"] in routes,
                    "positive_ref_binding",
                )
                reply.positive()
                if (
                    op in {"OWN_READ", "LATE_OWN_READ"}
                    and command["phase"] != "CLOSED_NONOWNER_CASES"
                ):
                    self.minted = True
                    self.routed.add((command["actor"], command["profile"]))
            require(len(reply.body) <= 65536, "observation_http_receipt_budget")
            return {
                "event": "actual_pinned_http_observation",
                "status": reply.status,
                "rawBodyB64": base64.b64encode(reply.body).decode("ascii"),
                "contentType": reply.content_type,
                "bodySHA256": hashlib.sha256(reply.body).hexdigest(),
                "bodyBytes": len(reply.body),
            }
        if op == "REVOKE":
            self.live()
            actor = self.actor(command)
            # No canary-only authorization-union inference. Exact actual configuration/source
            # union readback must be separately source-qualified before this runtime action.
            require(self.spec.get("authUnionReadbackRoute") is not None, "unbound_auth_union_route")
            read_pin(self.spec["authUnionReadbackRoute"], self.ledger)
            union = self.observe_no_independent_union(actor, command["profile"])
            pairing = self.PairingStore(profile=command["profile"])
            require(pairing.is_approved("hmp", actor.user_id) is True, "grant_before_revoke")
            require(pairing.revoke("hmp", actor.user_id) is True, "actual_revoke_refused")
            require(pairing.is_approved("hmp", actor.user_id) is False, "grant_after_revoke")
            observed = self.ctx.bridge.authz_state(actor.user_id, command["profile"])
            require(observed.value == "pending_operator", "live_native_auth_after_revoke")
            return {
                "event": "public_native_revoke_observation",
                "union": union,
                "actualAuthzAfter": observed.value,
            }
        if op == "ROTATE":
            self.live()
            actor = self.actor(command)
            require(
                (command["actor"], command["profile"]) in self.routed, "rotation_before_positive"
            )
            require(
                args["chatId"] == self.spec["actorChats"][command["actor"]][command["profile"]],
                "rotation_chat_binding",
            )
            key = self.spec["actorSessionKeys"][command["actor"]][command["profile"]]
            before = self.runner.session_store.lookup_by_session_key(key)
            require(
                before is not None
                and before.session_key == key
                and before.session_id == args["oldSessionId"],
                "rotation_old_lookup",
            )
            source = self.adapter.build_source(
                chat_id=args["chatId"],
                chat_type="dm",
                user_id=actor.user_id,
                scope_id=command["profile"],
                guild_id=command["profile"],
            )
            with self.scope(self.home / "profiles" / command["profile"]):
                entry = await self.runner.async_session_store.get_or_create_session(
                    source, force_new=True, touch_activity=True
                )
            self.live()
            require(
                entry.session_key == key and entry.session_id != args["oldSessionId"],
                "rotation_not_changed",
            )
            actual = self.runner.session_store.lookup_by_session_key(entry.session_key)
            require(
                actual is not None and actual.session_id == entry.session_id, "live_rotation_lookup"
            )
            return {
                "event": "actual_running_public_store_rotation",
                "oldSessionId": args["oldSessionId"],
                "newSessionId": entry.session_id,
                "sessionKey": key,
            }
        if op == "OWNED_FAULT":
            raise RefusalError("unimplemented_NM09_owned_action")
        if op == "DART_HANDOFF":
            raise RefusalError("unimplemented_Dart_define_reporter_route")
        if op == "OBSERVE_FINAL":
            raise RefusalError("parent_c018_safe_custody_required_before_named_audit")
        raise RefusalError("unimplemented_operation")


async def serve(spec, io, ledger):
    """Only inherited FD observations. No named evidence or audit inside this worker."""
    dispatcher = Dispatcher(spec, ledger)
    while not dispatcher.failed:
        try:
            command = io.read_command()
        except BaseException:
            dispatcher.fail()
            raise
        if command is None:
            require(dispatcher.index == len(dispatcher.plan), "premature_control_eof")
            return
        receipt = await dispatcher.dispatch(command)
        try:
            io.write_receipt(receipt)
        except BaseException:
            dispatcher.fail()
            raise
        if receipt["failureSticky"]:
            return
    raise RefusalError("failed_worker_no_more_actions")


def main():
    # Concrete root launcher, input pin/channel identities and c018 integration remain
    # unadmitted. This proposal cannot be launched with an arbitrary self-made JSON spec.
    raise RefusalError("ROOT_EXECUTION_LAUNCHER_NOT_ADMITTED")


if __name__ == "__main__":
    main()
