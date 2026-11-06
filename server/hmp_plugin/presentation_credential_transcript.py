"""Pure transcript consistency checks, not runtime enrollment or native authority.

The owning startup path must supply installation-pinned public keys and locally
held original context. This module performs no I/O, key discovery or signing and
cannot prove completed local writes, clock qualification or process custody.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .presentation_credential_codec import decode_record
from .presentation_jobs import FrameError

_COMMON_CONTEXT = frozenset(
    ["iid", "listener", "generation", "clock_domain", "operation_id", "work_end_ns"]
)


def _refuse():
    raise FrameError("BI1_CREDENTIAL_TRANSCRIPT_REFUSED")


def channel_digest(hello: bytes, challenge: bytes) -> str:
    """Hash exact records; the result itself makes no authentication claim."""
    for raw in (hello, challenge):
        decode_record(raw)
    return hashlib.sha256(b"HMP-BI1-CHANNEL-1\0" + hello + challenge).hexdigest()


@dataclass(frozen=True)
class ConsistentTranscript:
    """Cryptographic data consistency only; never an enrolled channel token."""

    channel: str
    transcript_sha256: str
    gateway_boot: str
    broker_boot: str


def check_transcript(
    records: tuple[bytes, bytes, bytes, bytes],
    *,
    gateway_public: bytes,
    broker_public: bytes,
    expected_context: dict,
) -> ConsistentTranscript:
    if type(records) is not tuple or len(records) != 4:
        _refuse()
    if type(expected_context) is not dict:
        _refuse()
    if any(type(key) is not str for key in expected_context):
        _refuse()
    if expected_context.keys() != _COMMON_CONTEXT:
        _refuse()
    for name, item in expected_context.items():
        if type(item) is not (int if name == "work_end_ns" else str):
            _refuse()
    if any(type(key) is not bytes or len(key) != 32 for key in (gateway_public, broker_public)):
        _refuse()
    if gateway_public == broker_public:
        _refuse()
    public = {"gateway": gateway_public, "broker": broker_public}
    ids = {role: hashlib.sha256(key).hexdigest() for role, key in public.items()}
    claims = []
    for raw, phase, role in zip(
        records,
        ("HELLO", "CHALLENGE", "FINISH", "ACCEPT"),
        ("gateway", "broker", "gateway", "broker"),
        strict=True,
    ):
        parsed = decode_record(raw)
        value = json.loads(parsed.canonical_json)
        if value["family"] != "handshake" or value["phase"] != phase or value["role"] != role:
            _refuse()
        if any(value[name] != item for name, item in expected_context.items()):
            _refuse()
        peer = "broker" if role == "gateway" else "gateway"
        if value["key_id"] != ids[role] or value["peer_key_id"] != ids[peer]:
            _refuse()
        try:
            Ed25519PublicKey.from_public_bytes(public[role]).verify(
                parsed.signature, parsed.signing_data
            )
        except (InvalidSignature, ValueError):
            _refuse()
        claims.append(value)
    hello, challenge, finish, accept = claims
    digests = [hashlib.sha256(raw).hexdigest() for raw in records]
    channel = channel_digest(records[0], records[1])
    if (
        challenge["gateway_boot"] != hello["gateway_boot"]
        or challenge["gateway_nonce"] != hello["gateway_nonce"]
        or challenge["hello_sha256"] != digests[0]
        or finish["hello_sha256"] != digests[0]
        or finish["challenge_sha256"] != digests[1]
        or accept["finish_sha256"] != digests[2]
    ):
        _refuse()
    for value in (finish, accept):
        if (
            value["gateway_boot"] != hello["gateway_boot"]
            or value["broker_boot"] != challenge["broker_boot"]
            or value["channel"] != channel
        ):
            _refuse()
    # Freshness is generated and retained by real owners, not inferred from
    # signatures. Distinct role/channel random inputs must not be aliased.
    nonces = (
        hello["gateway_boot"],
        hello["gateway_nonce"],
        challenge["broker_boot"],
        challenge["broker_nonce"],
    )
    if len(set(nonces)) != 4:
        _refuse()
    digest = hashlib.sha256(b"HMP-BI1-TRANSCRIPT-1\0" + b"".join(records)).hexdigest()
    return ConsistentTranscript(channel, digest, hello["gateway_boot"], challenge["broker_boot"])
