"""Closed credential record data codec; no signer, authentication or authority.

Signature bytes are opaque here. Role owners must verify pinned keys and retained
native context before any effect. Parsing never creates a runtime permission.
"""
from __future__ import annotations

import json
import re
import struct
from dataclasses import dataclass

from . import wire
from .presentation_jobs import FrameError
from .presentation_broker_codec import FRAME_LIMIT

MAGIC = b"HBA1"
JSON_LIMIT = 1976
RECORD_LIMIT = 2048
_COMMON = frozenset("v family alg phase role direction iid listener key_id peer_key_id generation operation_id work_end_ns".split())
_HANDSHAKE = {
    "HELLO": frozenset("gateway_boot gateway_nonce".split()),
    "CHALLENGE": frozenset("gateway_boot gateway_nonce broker_boot broker_nonce hello_sha256".split()),
    "FINISH": frozenset("gateway_boot broker_boot channel hello_sha256 challenge_sha256".split()),
    "ACCEPT": frozenset("gateway_boot broker_boot channel finish_sha256".split()),
}
_PHASES = frozenset("BEGIN READY GO RESULT CANCEL TERMINAL ACK".split())
_PHASE = frozenset("gateway_boot broker_boot channel transcript_sha256 sequence input_sha256 scope_sha256 frame_sha256 frame_length".split())
_HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_LISTENER = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)
_DOMAINS = {
    "handshake": b"HMP-BI1-CREDENTIAL-HANDSHAKE-1\x00",
    "phase": b"HMP-BI1-CREDENTIAL-PHASE-1\x00",
}


def _refuse():
    raise FrameError("BI1_CREDENTIAL_RECORD_REFUSED")


def _validate(value):
    if type(value) is not dict:
        _refuse()
    if any(type(key) is not str for key in value):
        _refuse()
    if any(type(item) is not (int if key in ("v", "sequence", "frame_length", "work_end_ns") else str)
           for key, item in value.items()):
        _refuse()
    family, phase = value.get("family"), value.get("phase")
    if type(family) is not str or type(phase) is not str:
        _refuse()
    if family == "handshake" and phase in _HANDSHAKE:
        keys = _COMMON | {"clock_domain"} | _HANDSHAKE[phase]
        sender = "gateway" if phase in ("HELLO", "FINISH") else "broker"
    elif family == "phase" and phase in _PHASES:
        keys = _COMMON | _PHASE
        sender = None
    else:
        _refuse()
    if value.keys() != keys or type(value["v"]) is not int or value["v"] != 1:
        _refuse()
    if type(value["alg"]) is not str or value["alg"] != "Ed25519":
        _refuse()
    role = value["role"]
    if type(role) is not str or role not in ("gateway", "broker"):
        _refuse()
    if sender is not None and role != sender:
        _refuse()
    if value["direction"] != ("g2b" if role == "gateway" else "b2g"):
        _refuse()
    if type(value["iid"]) is not str:
        _refuse()
    try:
        wire.require_iid(value["iid"])
    except wire.WireError:
        _refuse()
    if type(value["listener"]) is not str or not _LISTENER.fullmatch(value["listener"]):
        _refuse()
    for key, item in value.items():
        if key not in ("v", "sequence", "frame_length", "work_end_ns") and type(item) is not str:
            _refuse()
        if key in ("v", "sequence", "frame_length", "work_end_ns"):
            upper = 3 if key == "sequence" else (FRAME_LIMIT if key == "frame_length" else 2**63 - 1)
            lower = 8 if key == "frame_length" else (1 if key == "work_end_ns" else 0)
            if type(item) is not int or not lower <= item <= upper:
                _refuse()
        elif key not in ("family", "phase", "alg", "role", "direction", "iid", "listener"):
            if type(item) is not str or not _HEX.fullmatch(item):
                _refuse()


def _canonical(value):
    _validate(value)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    if not 1 <= len(raw) <= JSON_LIMIT:
        _refuse()
    return raw


def signing_bytes(value: dict) -> bytes:
    """Return domain-separated data, never a signature or permission."""
    raw = _canonical(value)
    return _DOMAINS[value["family"]] + struct.pack(">I", len(raw)) + raw


def encode_record(value: dict, signature: bytes) -> bytes:
    raw = _canonical(value)
    if type(signature) is not bytes or len(signature) != 64:
        _refuse()
    return MAGIC + struct.pack(">I", len(raw)) + raw + signature


def payload_size(prefix: bytes) -> int:
    """Validate the bounded prefix before a caller allocates the record payload."""
    if type(prefix) is not bytes or len(prefix) != 8 or prefix[:4] != MAGIC:
        _refuse()
    size = struct.unpack(">I", prefix[4:])[0]
    if not 1 <= size <= JSON_LIMIT:
        _refuse()
    return size + 64


@dataclass(frozen=True)
class UnverifiedRecord:
    """Immutable wire data only; deliberately not a verified-owner receipt."""
    canonical_json: bytes
    signature: bytes
    signing_data: bytes


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _refuse()
        result[key] = value
    return result


def decode_record(raw: bytes) -> UnverifiedRecord:
    if type(raw) is not bytes or not 73 <= len(raw) <= RECORD_LIMIT:
        _refuse()
    size = payload_size(raw[:8])
    if len(raw) != 8 + size:
        _refuse()
    body = raw[8:-64]
    try:
        value = json.loads(body.decode("ascii"), object_pairs_hook=_pairs)
    except (ValueError, UnicodeError, RecursionError):
        _refuse()
    if _canonical(value) != body:
        _refuse()
    return UnverifiedRecord(body, raw[-64:], signing_bytes(value))
