"""Protocol cryptography: P-256 SPKI checks (TR-12), `HMP1-*` transcripts (TR-13), sign and
verify, `secret_hash`, SAS, `iid` / `device_fp`, and the self-signed instance certificate (TR-1).
Must pass every positive and negative vector from T015 (`server/tests/unit/test_vectors.py`).

Private keys never leave this module in any form other than the `cryptography` key object and the
PEM that `identity.py` writes to its 0600 key file. Nothing here logs.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
import secrets
import struct

from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from .contract import HASH_DOMAIN_TAGS, TAG_GRACE, TRANSCRIPT_TAGS

# The tags `transcript()` accepts: the V-1 signature transcripts plus the server-internal grace
# derivation (research R16), which reuses the TR-13 encoding but never appears on the wire.
_TRANSCRIPT_TAGS_ALLOWED: frozenset[bytes] = frozenset((*TRANSCRIPT_TAGS, TAG_GRACE))

_U32_MAX = 2**32 - 1
_U64_MAX = 2**64 - 1

# DER prefix of every P-256 SPKI with an uncompressed point (TR-12):
# SEQUENCE(89) { SEQUENCE(19) { OID id-ecPublicKey, OID prime256v1 }, BIT STRING(66) 0x00 }.
P256_SPKI_PREFIX = bytes.fromhex("3059301306072a8648ce3d020106082a8648ce3d030107034200")
P256_SPKI_LENGTH = 91
_UNCOMPRESSED_POINT = 0x04

# Self-signed certificate: the client pins the SPKI (TR-2), never the name or the chain.
CERT_COMMON_NAME = "hmp-instance"
CERT_VALIDITY = datetime.timedelta(days=3650)
CERT_BACKDATE = datetime.timedelta(days=1)


class CryptoError(ValueError):
    """Invalid key material or an input that violates TR-12 / TR-13."""


# --------------------------------------------------------------------------------------------------
# Hashing and transcripts (TR-12, TR-13)
# --------------------------------------------------------------------------------------------------


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(bytes(data)).digest()


def secret_hash(tag: bytes, data: bytes) -> bytes:
    """`SHA-256(tag || x)` over raw bytes (TR-12)."""
    if tag not in HASH_DOMAIN_TAGS:
        raise CryptoError("unknown hash domain tag")
    if not isinstance(data, bytes | bytearray):
        raise CryptoError("secret_hash input must be raw bytes")
    return hashlib.sha256(tag + bytes(data)).digest()


def _field_bytes(field: bytes | str | int) -> bytes:
    if isinstance(field, bytes | bytearray):
        return bytes(field)
    if isinstance(field, str):
        return field.encode("utf-8", errors="strict")
    if type(field) is int:  # bool excluded on purpose (TR-10)
        if not 0 <= field <= _U64_MAX:
            raise CryptoError("integer transcript field outside u64")
        return struct.pack(">Q", field)
    raise CryptoError("unsupported transcript field type")


def length_prefixed(*fields: bytes | str | int) -> bytes:
    """`sum(u32be(len fi) || fi)`: the TR-13 field encoding without a tag."""
    out = bytearray()
    for field in fields:
        data = _field_bytes(field)
        if len(data) > _U32_MAX:
            raise CryptoError("transcript field too long")
        out += struct.pack(">I", len(data))
        out += data
    return bytes(out)


def transcript(tag: bytes, *fields: bytes | str | int) -> bytes:
    """`tag || sum(u32be(len fi) || fi)`; ints are u64be, strings UTF-8, bytes raw (TR-13)."""
    if tag not in _TRANSCRIPT_TAGS_ALLOWED:
        raise CryptoError("unknown transcript tag")
    return tag + length_prefixed(*fields)


def constant_time_equal(a: bytes | str, b: bytes | str) -> bool:
    """Constant-time comparison for secrets, digests and SAS strings."""
    if isinstance(a, str):
        a = a.encode("utf-8")
    if isinstance(b, str):
        b = b.encode("utf-8")
    return hmac.compare_digest(a, b)


def random_bytes(n: int) -> bytes:
    return secrets.token_bytes(n)


# --------------------------------------------------------------------------------------------------
# Keys (TR-12)
# --------------------------------------------------------------------------------------------------


def load_p256_spki(der: bytes) -> ec.EllipticCurvePublicKey:
    """Parse a P-256 SPKI with an uncompressed, on-curve point; anything else raises (TR-12).

    The byte-exact prefix check rejects other curves, compressed points, trailing data and
    non-canonical DER before the library parses anything. The library then rejects points that
    are not on the curve.
    """
    if not isinstance(der, bytes | bytearray):
        raise CryptoError("SPKI must be bytes")
    der = bytes(der)
    if len(der) != P256_SPKI_LENGTH or not der.startswith(P256_SPKI_PREFIX):
        raise CryptoError("not a P-256 SPKI with an uncompressed point")
    point = der[len(P256_SPKI_PREFIX) :]
    if point[0] != _UNCOMPRESSED_POINT:
        raise CryptoError("not a P-256 SPKI with an uncompressed point")
    try:
        key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), point)
    except (ValueError, UnsupportedAlgorithm) as exc:
        raise CryptoError("point is not on P-256") from exc
    if spki_der(key) != der:
        raise CryptoError("SPKI does not round-trip")
    return key


def check_p256_spki(der: bytes) -> None:
    """Reject anything but a P-256 SPKI with an uncompressed point (TR-12)."""
    load_p256_spki(der)


def spki_der(public_key: ec.EllipticCurvePublicKey) -> bytes:
    """SPKI DER of a P-256 public key (always the uncompressed point)."""
    if not isinstance(public_key, ec.EllipticCurvePublicKey) or not isinstance(
        public_key.curve, ec.SECP256R1
    ):
        raise CryptoError("not a P-256 public key")
    return public_key.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )


def generate_private_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


def _require_p256_private(private_key: object) -> ec.EllipticCurvePrivateKey:
    if not isinstance(private_key, ec.EllipticCurvePrivateKey) or not isinstance(
        private_key.curve, ec.SECP256R1
    ):
        raise CryptoError("not a P-256 private key")
    return private_key


def private_key_to_pem(private_key: ec.EllipticCurvePrivateKey) -> bytes:
    """PKCS#8 PEM, unencrypted: the key file's protection is its 0600 mode (SEC-1 boundary)."""
    return _require_p256_private(private_key).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def private_key_from_pem(pem: bytes) -> ec.EllipticCurvePrivateKey:
    try:
        key = serialization.load_pem_private_key(pem, password=None)
    except (ValueError, TypeError, UnsupportedAlgorithm) as exc:
        raise CryptoError("unreadable private key") from exc
    return _require_p256_private(key)


# --------------------------------------------------------------------------------------------------
# Fingerprints and SAS (§2)
# --------------------------------------------------------------------------------------------------


def spki_fingerprint(der: bytes) -> str:
    """52-char lowercase unpadded base32 of SHA-256(SPKI DER): `iid` and `device_fp` (§2)."""
    check_p256_spki(der)
    return base64.b32encode(sha256(der)).decode("ascii").rstrip("=").lower()


def device_sas(device_fp: str) -> str:
    """`upper(device_fp[0:20])` grouped `XXXXX-XXXXX-XXXXX-XXXXX` (§2)."""
    if not isinstance(device_fp, str) or len(device_fp) != 52:
        raise CryptoError("malformed device fingerprint")
    head = device_fp[:20].upper()
    return "-".join(head[i : i + 5] for i in range(0, 20, 5))


# --------------------------------------------------------------------------------------------------
# Signatures (TR-13)
# --------------------------------------------------------------------------------------------------


def verify(spki_der: bytes, signature_der: bytes, message: bytes) -> bool:
    """ECDSA P-256 / SHA-256 over the transcript bytes; low-S and high-S accepted (TR-13).

    Returns False for a bad signature, a malformed signature, or an invalid key; it never raises
    on attacker-controlled input.
    """
    try:
        key = load_p256_spki(spki_der)
    except CryptoError:
        return False
    if not isinstance(signature_der, bytes | bytearray) or not isinstance(
        message, bytes | bytearray
    ):
        return False
    try:
        key.verify(bytes(signature_der), bytes(message), ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, ValueError):
        return False
    return True


def sign(private_key: ec.EllipticCurvePrivateKey, message: bytes) -> bytes:
    """DER ECDSA P-256 / SHA-256 over the transcript bytes (not prehashed; TR-13)."""
    return _require_p256_private(private_key).sign(bytes(message), ec.ECDSA(hashes.SHA256()))


# --------------------------------------------------------------------------------------------------
# Instance certificate (TR-1, TR-8)
# --------------------------------------------------------------------------------------------------


def self_signed_certificate(
    private_key: ec.EllipticCurvePrivateKey, *, now: datetime.datetime | None = None
) -> bytes:
    """The instance certificate over the instance key (TR-1, TR-8), as DER.

    It carries no host name, address or other host detail: clients pin its SPKI to `iid` (TR-2)
    and ignore the name and chain.
    """
    key = _require_p256_private(private_key)
    issued = (now or datetime.datetime.now(datetime.UTC)) - CERT_BACKDATE
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, CERT_COMMON_NAME)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(issued)
        .not_valid_after(issued + CERT_VALIDITY)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.DER)


def certificate_spki(cert_der: bytes) -> bytes:
    """The SPKI DER inside a DER certificate (the value a client pins against `iid`)."""
    cert = x509.load_der_x509_certificate(bytes(cert_der))
    return cert.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
