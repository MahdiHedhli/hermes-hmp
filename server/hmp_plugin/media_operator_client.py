"""Unwired host IPC client. Caller must verify live TLS/listener and typed consent.

Same UID plus a challenge binds one exchange; neither proves human approval. The
client never retries, writes Store directly, launches a service or changes flags.
"""

from __future__ import annotations

import os
import socket
import stat
import time
from pathlib import Path

from . import wire
from .media_operator_protocol import MediaReadMutation, decode_reply
from .operator_read import _entry, _parent_fd, _peer_uid

_SOCKET_NAME = "media-operator.sock"
_HELLO_KEYS = frozenset(
    {
        "protocol",
        "operation",
        "iid",
        "nonce",
        "generation",
        "challenge",
        "expires_ms",
    }
)


class MediaOperatorUnavailableError(RuntimeError):
    def __init__(self):
        super().__init__("media operator unavailable; no decision submitted")


class MediaOperatorOutcomeUnknownError(RuntimeError):
    def __init__(self):
        super().__init__("media decision outcome unknown; inspect; do not replay")


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError
    return remaining


def _line(client, *, maximum, deadline):
    data = bytearray()
    while len(data) < maximum:
        client.settimeout(_remaining(deadline))
        block = client.recv(min(4096, maximum - len(data)))
        if not block:
            raise ValueError("missing frame")
        data.extend(block)
        if b"\n" in block:
            if data.count(b"\n") != 1 or not data.endswith(b"\n"):
                raise ValueError("invalid frame")
            return bytes(data[:-1])
    raise ValueError("oversize frame")


def _binding(fd, path, parent, before):
    held, named_parent = os.fstat(fd), os.lstat(path.parent)
    entry, named = _entry(fd, name=_SOCKET_NAME), os.lstat(path)
    if (
        (held.st_dev, held.st_ino) != (parent.st_dev, parent.st_ino)
        or (named_parent.st_dev, named_parent.st_ino) != (parent.st_dev, parent.st_ino)
        or not stat.S_ISDIR(named_parent.st_mode)
        or named_parent.st_uid != os.getuid()
        or stat.S_IMODE(named_parent.st_mode) != 0o700
        or any(
            (item.st_dev, item.st_ino) != (before.st_dev, before.st_ino)
            or not stat.S_ISSOCK(item.st_mode)
            or item.st_uid != os.getuid()
            or stat.S_IMODE(item.st_mode) & 0o077
            for item in (entry, named)
        )
    ):
        raise ValueError("binding changed")


def exchange_media_decision(path: Path, request: MediaReadMutation):
    """ONE exact exchange after caller consent; no retry or cross-process SQL fallback."""
    fd = None
    submitted = False
    try:
        if type(request) is not MediaReadMutation or path.name != _SOCKET_NAME:
            raise ValueError("invalid request")
        request.validate()
        body = wire.parse_body(request.encode(), max_bytes=2048, max_depth=3)
        deadline = time.monotonic() + 2.0
        fd, parent = _parent_fd(path)
        before = _entry(fd, name=_SOCKET_NAME)
        _binding(fd, path, parent, before)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(_remaining(deadline))
            client.connect(str(path))
            if _peer_uid(client) != os.getuid():
                raise ValueError("peer unavailable")
            _binding(fd, path, parent, before)
            hello = wire.parse_body(
                _line(client, maximum=512, deadline=deadline), max_bytes=511, max_depth=2
            )
            if (
                frozenset(hello) != _HELLO_KEYS
                or type(hello["protocol"]) is not int
                or hello["protocol"] != 1
                or hello["operation"] != "host_media_read_challenge"
                or hello["iid"] != request.iid
                or hello["nonce"] != request.nonce
                or hello["generation"] != request.generation
                or type(hello["challenge"]) is not str
                or len(hello["challenge"]) != 32
                or any(c not in "0123456789abcdef" for c in hello["challenge"])
                or type(hello["expires_ms"]) is not int
                or not int(time.monotonic() * 1000) < hello["expires_ms"] <= int(deadline * 1000)
            ):
                raise ValueError("challenge unavailable")
            deadline = min(deadline, hello["expires_ms"] / 1000)
            frame = wire.dump_json({"challenge": hello["challenge"], "mutation": body}) + b"\n"
            if len(frame) > 4096:
                raise ValueError("frame unavailable")
            _binding(fd, path, parent, before)
            client.settimeout(_remaining(deadline))
            submitted = True  # BEFORE sendall: partial writes have an unknown outcome
            client.sendall(frame)
            raw = _line(client, maximum=2049, deadline=deadline)
            reply = decode_reply(raw, request=request)
            _binding(fd, path, parent, before)
            _remaining(deadline)
            return reply
    except BaseException:
        if submitted:
            raise MediaOperatorOutcomeUnknownError() from None
        raise MediaOperatorUnavailableError() from None
    finally:
        if fd is not None:
            os.close(fd)
