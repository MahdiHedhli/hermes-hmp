"""Fixed synthetic provider response; never a provider/model qualification.

The separately admitted executor supplies one already-owned connected socket and exact port.
This module does not bind, accept, spawn, discover ports, retry or clean up a listener.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass, field

DUMMY_KEY = "fixture-only-never-a-real-openai-key"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mMQMgn7DwAClAGc"
    "wgVUTwAAAABJRU5ErkJggg=="
)
PNG_SHA256 = "fdde404f4138c9fc441564a4272169f9d288545b96b7cb2bb3b7e3d548376db1"
RESPONSE = (
    json.dumps(
        {"created": 0, "data": [{"b64_json": base64.b64encode(PNG).decode("ascii")}]},
        separators=(",", ":"),
    ).encode("ascii")
    + b"\n"
)
RESPONSE_SHA256 = "7dfdbc375a8d5cbcae421d5d7c0e835e45b90aaecc04d9eb7d5c1975dbf8a209"
EXPECTED_REQUEST = {
    "model": "gpt-image-2",
    "prompt": "[media-fixture] fixed raster",
    "size": "1024x1024",
    "n": 1,
    "quality": "medium",
}
HEADER_CAP = 8192
BODY_CAP = 4096
# Derived continuous per-connection credit, including one post-response EOF byte reservation.
READ_BYTES_CAP = HEADER_CAP + BODY_CAP + 1
READ_CALLS_CAP = HEADER_CAP + BODY_CAP + 1


class FixtureRefusalError(RuntimeError):
    """Opaque, closed fixture failure; never include request/credential/path text."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise FixtureRefusalError(code)


def exact_port(port: int) -> None:
    require(type(port) is int and 1024 <= port <= 65535, "port")


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, "json_duplicate")
        obj[key] = value
    return obj


def validate_request(header: bytes, body: bytes, port: int) -> dict[str, object]:
    """Validate bounded original bytes, not a permissively repaired HTTP request."""
    exact_port(port)
    require(0 < len(header) <= HEADER_CAP and len(body) <= BODY_CAP, "request_cap")
    require(header.endswith(b"\r\n\r\n"), "header_end")
    try:
        lines = header[:-4].decode("ascii").split("\r\n")
    except UnicodeError as exc:
        raise FixtureRefusalError("header_ascii") from exc
    require(lines.pop(0) == "POST /v1/images/generations HTTP/1.1", "request_line")
    headers = {}
    for line in lines:
        require(":" in line and not line.startswith((" ", "\t")), "header_shape")
        key, value = line.split(":", 1)
        require(key and all(c.isalnum() or c == "-" for c in key), "header_key")
        key = key.lower()
        require(key not in headers, "header_duplicate")
        headers[key] = value.strip(" \t")
    require(headers.get("host") == f"127.0.0.1:{port}", "host")
    require(headers.get("authorization") == f"Bearer {DUMMY_KEY}", "auth")
    require(headers.get("content-type") == "application/json", "content_type")
    require("transfer-encoding" not in headers and "expect" not in headers, "framing")
    require(headers.get("content-length") == str(len(body)), "content_length")
    require(headers.get("x-stainless-retry-count") == "0", "retry")
    require(headers.get("openai-project", "") == "", "project")
    require("openai-organization" not in headers, "organization")
    try:
        parsed = json.loads(body, object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError) as exc:
        raise FixtureRefusalError("request_json") from exc
    require(parsed == EXPECTED_REQUEST and type(parsed.get("n")) is int, "request_body")
    return {"requestSHA256": hashlib.sha256(header + body).hexdigest(), "retryCount": 0}


@dataclass
class ResponseLedger:
    """One fixed response per producer invocation; any fault poisons the lane."""

    armed: str | None = None
    rows: list[dict[str, object]] = field(default_factory=list)
    failed: bool = False

    def arm(self, invocation: str) -> None:
        require(not self.failed and self.armed is None and len(self.rows) < 4, "ledger_state")
        require(invocation in {"P01", "P02", "P03", "P04"}, "invocation")
        require(all(row["invocation"] != invocation for row in self.rows), "duplicate_invocation")
        self.armed = invocation

    def finish(self, invocation: str) -> dict[str, object]:
        require(not self.failed and self.armed is None, "ledger_incomplete")
        matching = [row for row in self.rows if row["invocation"] == invocation]
        require(len(matching) == 1, "post_count")
        require(
            matching[0].get("peerEOF") is True and matching[0].get("completionReadRequested") == 1,
            "completion_missing",
        )
        return dict(matching[0])


def respond_once(connection, port: int, ledger: ResponseLedger, deadline: float) -> None:
    """Real socket implementation for future admitted execution, bounded on every receive.

    No socket close/cleanup is hidden here; its exact parent owns the connection and custody.
    The response is provisional until a bounded read proves peer EOF with no later bytes.
    Connection:close is expected to make the actual nonstreaming HTTPX/h11 path close the
    client stream, but source expectation alone is not EOF evidence. Missing EOF/timeout,
    later fragments, duplicate/pipelined request or any failed response poisons the lane.
    """
    try:
        exact_port(port)
        require(ledger.armed is not None and not ledger.failed, "unarmed")
        credit = {"bytes": READ_BYTES_CAP, "calls": READ_CALLS_CAP}

        def receive(limit: int, code: str) -> bytes:
            # Reserve capacity and one operation BEFORE I/O, never reset this connection's
            # credit. Actual bytes consume the reserved capacity; unused capacity is not a
            # received byte. A hostile/fake over-return refuses before it can grow a buffer.
            remaining = deadline - time.monotonic()
            require(remaining > 0 and 0 < limit <= credit["bytes"] and credit["calls"] > 0, code)
            credit["calls"] -= 1
            connection.settimeout(remaining)
            chunk = connection.recv(limit)
            require(type(chunk) is bytes and len(chunk) <= limit, "receive_shape")
            credit["bytes"] -= len(chunk)
            require(deadline > time.monotonic(), code)
            return chunk

        data = bytearray()
        while b"\r\n\r\n" not in data:
            require(len(data) < HEADER_CAP, "header_deadline_cap")
            chunk = receive(min(1024, HEADER_CAP - len(data)), "header_deadline_cap")
            require(bool(chunk), "header_eof")
            data.extend(chunk)
        end = data.index(b"\r\n\r\n") + 4
        header, body = bytes(data[:end]), bytearray(data[end:])
        # Parse framing before reading an attacker-declared body. Full validation follows.
        lengths = [
            line.split(b":", 1)[1].strip()
            for line in header[:-4].split(b"\r\n")[1:]
            if line.lower().startswith(b"content-length:")
        ]
        require(len(lengths) == 1 and lengths[0].isdigit(), "length_header")
        length = int(lengths[0])
        require(length <= BODY_CAP and len(body) <= length, "body_cap_pipeline")
        while len(body) < length:
            chunk = receive(min(1024, length - len(body)), "body_deadline")
            require(bool(chunk), "body_eof")
            body.extend(chunk)
        row = validate_request(header, bytes(body), port)
        require(len(PNG) == 70 and hashlib.sha256(PNG).hexdigest() == PNG_SHA256, "png_pin")
        require(
            len(RESPONSE) == 135 and hashlib.sha256(RESPONSE).hexdigest() == RESPONSE_SHA256,
            "response_pin",
        )
        require(deadline > time.monotonic(), "response_deadline")
        connection.settimeout(deadline - time.monotonic())
        connection.sendall(
            b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 135\r\n"
            b"X-Should-Retry: false\r\nConnection: close\r\n\r\n" + RESPONSE
        )
        # No positive row, invocation release or finish() success before full peer completion.
        # One bounded blocking read waits for EOF; an empty nonblocking peek is not used.
        require(receive(1, "completion_deadline") == b"", "completion_extra")
        ledger.rows.append(
            {
                "invocation": ledger.armed,
                **row,
                "posts": 1,
                "providerPort": port,
                "responseBytes": len(RESPONSE),
                "pngSHA256": PNG_SHA256,
                "responseSHA256": RESPONSE_SHA256,
                "peerEOF": True,
                "completionReadRequested": 1,
                "receivedBytes": READ_BYTES_CAP - credit["bytes"],
                "readCalls": READ_CALLS_CAP - credit["calls"],
            }
        )
        ledger.armed = None
    except BaseException:
        ledger.failed = True
        raise
