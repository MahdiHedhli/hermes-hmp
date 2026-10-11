"""Finite media fixture assertions; no gateway/process/port lifecycle hidden here.

The root c018 coordinator must prepare and qualify the three exact listeners, native APIs,
source/runtime graph and phase receipts before publishing the private run descriptor.
Descriptors are test input, not independent runtime/provenance authority. Their final joins
remain the root independent actual review's responsibility.
"""

from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import re
import ssl
import stat
from dataclasses import dataclass
from pathlib import Path

from local_media_provider_response import PNG, PNG_SHA256, exact_port, require

CASES = tuple(f"NM{i:02d}" for i in range(1, 11))
_REF = re.compile(r"[A-Za-z0-9_-]{43}\Z")
_IID = re.compile(r"[a-z2-7]{51}[aq]\Z")
_PROFILES = {"media-alpha", "media-beta"}


def read_descriptor(path: Path) -> dict:
    """Private regular input; exact scope/custody/pins are a later admission prerequisite."""
    require(
        path.is_absolute() and str(path).startswith("/private/tmp/") and ".." not in path.parts,
        "descriptor_path",
    )
    parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        leaf = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            before = os.fstat(leaf)
            require(
                stat.S_ISREG(before.st_mode)
                and before.st_uid == os.getuid()
                and before.st_nlink == 1
                and stat.S_IMODE(before.st_mode) == 0o600
                and 0 < before.st_size <= 131072,
                "descriptor_leaf",
            )
            data = bytearray()
            while len(data) < before.st_size:
                part = os.read(leaf, min(8192, before.st_size - len(data)))
                require(bool(part), "descriptor_short")
                data.extend(part)
            require(not os.read(leaf, 1), "descriptor_growth")
            require(
                os.fstat(leaf) == before
                and os.stat(path.name, dir_fd=parent, follow_symlinks=False) == before,
                "descriptor_drift",
            )
        finally:
            os.close(leaf)
    finally:
        os.close(parent)
    document = json.loads(data)
    require(document.get("format") == "native-media-fixture-v1", "descriptor_kind")
    require(
        document.get("rootExecutionAdmissionSHA256") is not None
        and document.get("nativeSourcePreservationSHA256") is not None,
        "unadmitted",
    )
    require(set(document["scenarios"]) == set(CASES), "scenario_inventory")
    return document


@dataclass(frozen=True, repr=False)
class Actor:
    name: str
    port: int
    iid: str
    device_id: str
    user_id: str
    bearer: str

    @classmethod
    def parse(cls, obj: dict):
        require(set(obj) == {"name", "port", "iid", "deviceId", "userId", "bearer"}, "actor_shape")
        require(obj["name"] in {"A1", "A2", "B1"}, "actor_name")
        exact_port(obj["port"])
        require(type(obj["iid"]) is str and _IID.fullmatch(obj["iid"]) is not None, "iid")
        require(
            all(
                type(obj[k]) is str
                and 0 < len(obj[k]) <= 4096
                and "\r" not in obj[k]
                and "\n" not in obj[k]
                for k in ("deviceId", "userId", "bearer")
            ),
            "actor_fields",
        )
        return cls(
            obj["name"], obj["port"], obj["iid"], obj["deviceId"], obj["userId"], obj["bearer"]
        )


@dataclass(frozen=True, repr=False)
class Reply:
    status: int
    content_type: str
    body: bytes

    def error(self) -> str:
        require(not self.content_type.startswith("image/"), "negative_image")
        require(len(self.body) <= 4096, "error_cap")
        obj = json.loads(self.body)
        require(type(obj) is dict and type(obj.get("error")) is str, "error_shape")
        return obj["error"]

    def positive(self) -> None:
        require(self.status == 200 and self.content_type == "image/png", "positive_status")
        require(
            self.body == PNG and hashlib.sha256(self.body).hexdigest() == PNG_SHA256,
            "positive_body",
        )


def get(actor: Actor, path: str, *, instance_header: str | None = None) -> Reply:
    """TLS1.3 + exact SPKI pin before bearer bytes; numeric exact owned listener only.

    The future network sandbox, not these source assertions alone, contains transport effects.
    cryptography is a lazy runtime dependency needing a pinned graph, not an author import.
    """
    require(
        path.startswith("/hmp/v1/") and "\r" not in path and "\n" not in path and len(path) <= 1024,
        "request_path",
    )
    require(
        re.fullmatch(
            r"/hmp/v1/bots/media-(alpha|beta)/(media/[A-Za-z0-9_-]{43}|"
            r"conversations/default\?limit=64|conversations/default/messages\?after=0&limit=64|"
            r"sessions/ses1_[A-Za-z0-9_-]{22}/messages\?after=0&limit=64|"
            r"sessions/ses1_[A-Za-z0-9_-]{22}/messages/from-start\?limit=64)",
            path,
        )
        is not None,
        "request_route",
    )
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # Exact SPKI verification precedes every request.
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    connection = http.client.HTTPSConnection("127.0.0.1", actor.port, context=context, timeout=15)
    try:
        connection.connect()
        cert = x509.load_der_x509_certificate(connection.sock.getpeercert(binary_form=True))
        spki = cert.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        pin = base64.b32encode(hashlib.sha256(spki).digest()).decode("ascii").lower().rstrip("=")
        require(pin == actor.iid, "tls_pin")
        header = actor.iid if instance_header is None else instance_header
        require(_IID.fullmatch(header) is not None, "instance_header")
        connection.request(
            "GET", path, headers={"Authorization": f"Bearer {actor.bearer}", "HMP-Instance": header}
        )
        response = connection.getresponse()
        body = response.read(8 * 1024 * 1024 + 1)
        require(len(body) <= 8 * 1024 * 1024, "response_cap")
        return Reply(response.status, response.getheader("Content-Type", ""), body)
    finally:
        connection.close()


def media_path(profile: str, ref: str) -> str:
    require(
        profile in _PROFILES and type(ref) is str and _REF.fullmatch(ref) is not None, "media_scope"
    )
    return f"/hmp/v1/bots/{profile}/media/{ref}"


def validate_nm06_preconditions(own: dict[tuple[str, str], Reply], refs: dict[str, str]) -> None:
    require(
        set(own)
        == {
            ("A1", "media-alpha"),
            ("A2", "media-alpha"),
            ("A1", "media-beta"),
            ("B1", "media-alpha"),
        },
        "nm06_own_inventory",
    )
    require(set(refs) == {"A1-alpha", "A2-alpha", "A1-beta", "B1-alpha"}, "nm06_refs")
    require(
        len(set(refs.values())) == 4 and all(_REF.fullmatch(ref) for ref in refs.values()),
        "nm06_ref_distinct",
    )
    for reply in own.values():
        # Each actual own200 traverses the preceding active/owner/profile/native-grant/feature
        # gates on that exact actor/profile. An asserted boolean or arbitrary404 cannot replace it.
        reply.positive()


def run_nm06(actors: dict[str, Actor], refs: dict[str, str]) -> list[dict]:
    require(set(actors) == {"A1", "A2", "B1"}, "nm06_actors")
    require(actors["A1"].iid == actors["A2"].iid != actors["B1"].iid, "nm06_instances")
    require(actors["A1"].port == actors["A2"].port != actors["B1"].port, "nm06_ports")
    require(actors["A1"].device_id != actors["A2"].device_id, "nm06_devices")
    own = {
        ("A1", "media-alpha"): get(actors["A1"], media_path("media-alpha", refs["A1-alpha"])),
        ("A2", "media-alpha"): get(actors["A2"], media_path("media-alpha", refs["A2-alpha"])),
        ("A1", "media-beta"): get(actors["A1"], media_path("media-beta", refs["A1-beta"])),
        ("B1", "media-alpha"): get(actors["B1"], media_path("media-alpha", refs["B1-alpha"])),
    }
    validate_nm06_preconditions(own, refs)
    arms = [
        ("NM06-D", actors["A2"], "media-alpha", None, 404, "not_found"),
        ("NM06-P", actors["A1"], "media-beta", None, 404, "not_found"),
        ("NM06-I", actors["B1"], "media-alpha", None, 404, "not_found"),
        ("NM06-H", actors["B1"], "media-alpha", actors["A1"].iid, 401, "wrong_instance"),
    ]
    rows = []
    for code, actor, profile, header, status, error in arms:
        reply = get(actor, media_path(profile, refs["A1-alpha"]), instance_header=header)
        require(reply.status == status and reply.error() == error, "nm06_exact_refusal")
        rows.append(
            {
                "case": code,
                "status": status,
                "error": error,
                "imageBytes": 0,
                "bodySHA256": hashlib.sha256(reply.body).hexdigest(),
            }
        )
    return rows


def validate_case(case: str, record: dict) -> None:
    """Closed root phase evidence shape; actual provenance is an independent join prerequisite."""
    require(case in CASES and record.get("case") == case, "case_scope")
    require(record.get("nativeAPI") == "SessionDB/SessionStore/PairingStore", "native_api")
    require(
        record.get("producerEntry") == "model_tools.handle_function_call:image_generate",
        "producer_entry",
    )
    for key in ("rootCustodyCaptureSHA256", "sourcePreservationSHA256", "rawToolResultSHA256"):
        require(
            type(record.get(key)) is str and re.fullmatch(r"[a-f0-9]{64}", record[key]),
            "evidence_hash",
        )
    require(
        record.get("posts") == 1
        and record.get("retryCount") == 0
        and record.get("actualFactoryReturns") == 1,
        "producer_observation",
    )
    require(
        record.get("customHttpx") is True
        and record.get("redirects") is False
        and record.get("sdkMaxRetries") == 2,
        "producer_client",
    )
    require(
        record.get("rawToolResultSHA256") is not None
        and record.get("nativeToolRowId") is not None
        and record.get("liveTipId") is not None,
        "native_row_binding",
    )


def assert_refusal(reply: Reply, status: int, code: str) -> None:
    require(reply.status == status and reply.error() == code, "exact_refusal")


def read_descriptors(actor: Actor, path: str, tool_row_id: int) -> tuple[list, list]:
    reply = get(actor, path)
    require(reply.status == 200 and reply.content_type == "application/json", "read_status")
    require(len(reply.body) <= 1048576, "read_cap")
    obj = json.loads(reply.body)
    require(type(obj) is dict and type(obj.get("messages")) is list, "read_shape")
    require(len(obj["messages"]) <= 64, "read_rows_cap")
    media = []
    for row in obj["messages"]:
        require(type(row) is dict, "read_row")
        if row.get("media") is not None:
            require(
                row.get("id") == tool_row_id
                and row.get("role") == "tool"
                and row.get("tool_name") == "image_generate",
                "media_native_row",
            )
            descriptor = row["media"]
            require(
                type(descriptor) is dict
                and descriptor.get("kind") == "image"
                and type(descriptor.get("ref")) is str
                and _REF.fullmatch(descriptor["ref"]),
                "media_descriptor",
            )
            media.append(descriptor)
    return media, obj["messages"]


def expected_read_paths(profile: str, session_ref: str, *, bot: bool) -> list[str]:
    require(
        profile in _PROFILES and re.fullmatch(r"ses1_[A-Za-z0-9_-]{22}", session_ref),
        "session_scope",
    )
    base = f"/hmp/v1/bots/{profile}"
    session = [
        f"{base}/sessions/{session_ref}/messages?after=0&limit=64",
        f"{base}/sessions/{session_ref}/messages/from-start?limit=64",
    ]
    # RO3/RO6 resolve only the actual routed default Phone conversation. Canonical Bot uses SES.
    return (
        session
        if bot
        else [
            f"{base}/conversations/default?limit=64",
            f"{base}/conversations/default/messages?after=0&limit=64",
            *session,
        ]
    )
