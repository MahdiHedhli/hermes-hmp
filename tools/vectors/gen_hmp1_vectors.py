#!/usr/bin/env python3
"""Independent HMP1 known-answer vector generator (TR-14).

This generator is written from `docs/architecture/contracts/HMP_V1.md` alone. It
imports no server code, no client code, and no spike code (`worktrees/e-hmp-spike`,
`worktrees/d-platform-spike`) of any kind. The only non-stdlib dependency is
`cryptography` (for P-256/P-384 EC keys and ECDSA sign/verify); hashing uses only
`hashlib`. Everything else is Python standard library (base64, json, struct-free
manual big-endian packing, argparse).

TEST-ONLY. Every private key, secret, token and pairing value produced by this
script is a fixed, publicly-known test constant derived deterministically from
this file's own source text. None of it is derived from, or resembles, any real
Hermes deployment, instance, device or user. Do not use any key in this file for
anything other than conformance testing.

Determinism. All fields are byte-for-byte reproducible across re-runs, with one
documented exception: ECDSA signature bytes (`*_sig_der_b64u`). This script does
not use RFC 6979 deterministic-k ECDSA; `cryptography`'s default ECDSA signing
draws a fresh random nonce `k` per signature, so the exact signature bytes differ
between runs even for the same key and message (both a low-S and a high-S
encoding are valid and MUST be accepted per TR-13). Consumers of this vector file
MUST treat every signature vector by verification against the given public key
and transcript bytes, never by byte-equality against a previously recorded
signature. This is stated once here and repeated in the output file's `_meta`.

Usage:
    python tools/vectors/gen_hmp1_vectors.py \
        --out docs/architecture/contracts/vectors/hmp_v1_vectors.json
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

# --------------------------------------------------------------------------
# Contract revision this vector file targets (HMP_V1.md front matter).
# --------------------------------------------------------------------------
CONTRACT_REVISION = "1.0"
SCHEMA_VERSION = 1

TEST_ONLY_WARNING = (
    "TEST-ONLY. Every key, secret, token and pairing value in this file is a "
    "fixed, publicly-known constant generated for conformance testing only. "
    "Never use any value from this file in a real deployment."
)

DETERMINISM_NOTE = (
    "All fields are byte-for-byte reproducible across regenerations of this "
    "file, with one exception: '*_sig_der_b64u' / '*_sig_der_hex' fields. "
    "ECDSA signing here uses a randomized nonce (no RFC 6979), so signature "
    "bytes differ run to run even for an identical key and message; both "
    "low-S and high-S encodings are valid (TR-13). A conforming test MUST "
    "verify these signatures against the accompanying public key and "
    "transcript bytes, and MUST NOT compare signature bytes for equality."
)

INDEPENDENCE_NOTE = (
    "Generated from docs/architecture/contracts/HMP_V1.md alone. Imports no "
    "server code, no client code and no spike code. Non-stdlib dependencies: "
    "cryptography only (hashing uses hashlib only)."
)


# --------------------------------------------------------------------------
# Deterministic filler bytes (TEST-ONLY). Not a KDF; just an auditable,
# reproducible way to avoid hand-typed "random-looking" hex constants.
# --------------------------------------------------------------------------
def det_bytes(label: str, n: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(f"HMP1-VECTOR-TEST-ONLY:{label}:{counter}".encode()).digest()
        counter += 1
    return out[:n]


# Well-known public curve orders (NIST SP 800-186 / SEC2), used only to fold a
# deterministic filler value into a valid EC private scalar. Not secret.
P256_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
# E501 suppressed below: a published NIST constant, kept as one literal rather than split
# across lines -- an unverified manual line-break in the middle of a 96-hex-digit curve order
# is a real transcription-error risk with no test here to catch it (unlike P256_B above),
# while splitting it changes nothing about readability or correctness.
P384_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFC7634D81F4372DDF581A0DB248B0A77AECEC196ACCC52973  # noqa: E501

# Well-known P-256 (secp256r1) field prime and curve-equation coefficients
# (SEC2 / FIPS 186-4), used only to construct one "point not on the curve"
# negative vector. Not secret. `p` is computed from its public closed form
# rather than a hand-typed hex constant to remove one source of typos; `b` is
# self-checked below against a real point from `cryptography` before use.
P256_FIELD_PRIME = 2**256 - 2**224 + 2**192 + 2**96 - 1
P256_A = P256_FIELD_PRIME - 3  # a = -3 mod p, per SEC2
P256_B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B


def det_private_key(label: str, curve: ec.EllipticCurve, order: int) -> ec.EllipticCurvePrivateKey:
    raw = int.from_bytes(det_bytes(f"privkey:{label}", 64), "big")
    scalar = (raw % (order - 1)) + 1  # land in [1, order-1]
    return ec.derive_private_key(scalar, curve)


# --------------------------------------------------------------------------
# base64url (TR-11): canonical, unpadded, RFC 4648 section 5 alphabet.
# --------------------------------------------------------------------------
def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64u_decode_canonical(s: str) -> bytes:
    """Strict reference decoder used only for this script's own self-checks.

    Rejects padding, to mirror TR-11's "unpadded only" rule -- this is NOT the
    codec under test (that is T017/T020's job); it exists so this generator
    can assert its own positive vectors round-trip before writing them out.
    """
    if "=" in s:
        raise ValueError("padded base64url is not canonical (TR-11)")
    pad = (-len(s)) % 4
    return base64.urlsafe_b64decode(s + ("=" * pad))


B64U_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def corrupt_trailing_padding_bits(raw: bytes) -> dict[str, Any]:
    """Build a base64url string that decodes (leniently) to `raw` but is NOT
    the canonical encoding of `raw`, because its trailing padding bits are
    non-zero. TR-11 requires "round-trip exact"; a decoder that only checks
    length and alphabet (not these bits) would accept this non-canonical
    string and silently normalize it away, which is exactly the gap IR-16
    flags. Only applies when len(raw) % 3 != 0 (there is a partial tail
    group); every TR-11 field length (16, 32, 91) qualifies.
    """
    rem = len(raw) % 3
    if rem == 0:
        raise ValueError("no partial tail group; nothing to corrupt")
    padding_bits = 4 if rem == 1 else 2  # bits of the final base64 char that MUST be zero
    canonical = b64u(raw)
    last_char = canonical[-1]
    idx = B64U_ALPHABET.index(last_char)
    mask = (1 << padding_bits) - 1
    corrupted_idx = idx ^ mask  # flips exactly the padding bits; always nonzero afterwards
    corrupted = canonical[:-1] + B64U_ALPHABET[corrupted_idx]
    assert corrupted != canonical
    # A lenient decoder (ignores trailing bits) still accepts it and returns the same bytes:
    assert b64u_decode_canonical(corrupted) == raw
    return {
        "decoded_len": len(raw),
        "raw_hex": hexs(raw),
        "canonical_b64u": canonical,
        "non_canonical_b64u": corrupted,
        "padding_bit_count": padding_bits,
    }


# --------------------------------------------------------------------------
# base32 (iid, device_fp): RFC 4648, lowercase, unpadded.
# --------------------------------------------------------------------------
def b32_lower_unpadded(data: bytes) -> str:
    return base64.b32encode(data).rstrip(b"=").decode("ascii").lower()


# --------------------------------------------------------------------------
# Minimal DER TLV helpers, used only to hand-build one malformed
# (compressed-point) SPKI negative vector from a real uncompressed SPKI.
# --------------------------------------------------------------------------
def der_len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    body = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(body)]) + body


def der_tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + der_len(len(value)) + value


def der_parse_tlv(data: bytes, offset: int) -> tuple[int, bytes, int]:
    """Returns (tag, value_bytes, offset_after_this_tlv). Short/long form only."""
    tag = data[offset]
    first_len = data[offset + 1]
    if first_len & 0x80 == 0:
        length = first_len
        value_start = offset + 2
    else:
        n = first_len & 0x7F
        length = int.from_bytes(data[offset + 2 : offset + 2 + n], "big")
        value_start = offset + 2 + n
    value_end = value_start + length
    return tag, data[value_start:value_end], value_end


def spki_der(pub: ec.EllipticCurvePublicKey) -> bytes:
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    return pub.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)


def compressed_point_spki_der(pub: ec.EllipticCurvePublicKey) -> bytes:
    """Hand-build a syntactically valid SPKI DER wrapping a COMPRESSED EC
    point, reusing the real AlgorithmIdentifier bytes from a genuine
    uncompressed SPKI for the same key. `cryptography` has no public API to
    emit a compressed-point SPKI directly, so the BIT STRING is rebuilt here.
    This value MUST be rejected per TR-12 (uncompressed only).
    """
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    uncompressed_spki = spki_der(pub)
    outer_tag, outer_value, _ = der_parse_tlv(uncompressed_spki, 0)
    assert outer_tag == 0x30, "expected outer SEQUENCE"
    alg_tag, _alg_value, alg_end = der_parse_tlv(outer_value, 0)
    assert alg_tag == 0x30, "expected AlgorithmIdentifier SEQUENCE"
    alg_id_full_tlv = outer_value[0:alg_end]  # tag+len+value, reused verbatim

    compressed_point = pub.public_bytes(Encoding.X962, PublicFormat.CompressedPoint)
    assert compressed_point[0] in (0x02, 0x03), "expected a compressed point prefix"
    bitstring_value = b"\x00" + compressed_point  # 0 unused bits + point
    bitstring_tlv = der_tlv(0x03, bitstring_value)

    return der_tlv(0x30, alg_id_full_tlv + bitstring_tlv)


def _p256_on_curve(x: int, y: int) -> bool:
    p = P256_FIELD_PRIME
    return (y * y - (x**3 + P256_A * x + P256_B)) % p == 0


def off_curve_point_spki_der(pub: ec.EllipticCurvePublicKey) -> bytes:
    """Hand-build a syntactically valid, correctly-shaped (65 B, leading
    0x04) uncompressed-point SPKI DER whose (x, y) does NOT satisfy the P-256
    curve equation. Reuses the real AlgorithmIdentifier bytes from a genuine
    SPKI for the same key, like `compressed_point_spki_der`. This MUST be
    rejected: it is the right length and prefix, but not a point on the
    curve, so it names no valid public key at all.
    """
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    numbers = pub.public_numbers()
    x, y = numbers.x, numbers.y
    # Self-check: our hardcoded (p, a, b) must agree with a REAL point before
    # we trust them to build a deliberately-invalid one.
    assert _p256_on_curve(x, y), "P256_A/P256_B/P256_FIELD_PRIME do not match a real curve point"

    bad_y = y ^ 1  # flip the low bit; astronomically unlikely to land back on the curve
    assert bad_y < P256_FIELD_PRIME
    assert not _p256_on_curve(x, bad_y), "unlucky: corrupted point landed back on the curve"

    uncompressed_spki = spki_der(pub)
    outer_tag, outer_value, _ = der_parse_tlv(uncompressed_spki, 0)
    assert outer_tag == 0x30
    alg_tag, _alg_value, alg_end = der_parse_tlv(outer_value, 0)
    assert alg_tag == 0x30
    alg_id_full_tlv = outer_value[0:alg_end]

    real_point = pub.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    assert len(real_point) == 65 and real_point[0] == 0x04
    bad_point = b"\x04" + x.to_bytes(32, "big") + bad_y.to_bytes(32, "big")
    assert len(bad_point) == 65

    bitstring_value = b"\x00" + bad_point
    bitstring_tlv = der_tlv(0x03, bitstring_value)
    return der_tlv(0x30, alg_id_full_tlv + bitstring_tlv)


# --------------------------------------------------------------------------
# TR-13 transcript construction: transcript(tag, f1..fn) = tag || Sum(u32be(len fi) || fi)
# --------------------------------------------------------------------------
def u32be(n: int) -> bytes:
    return n.to_bytes(4, "big")


def u64be(n: int) -> bytes:
    return n.to_bytes(8, "big")


def field_bytes(value: Any, ftype: str) -> bytes:
    if ftype == "str":
        assert isinstance(value, str)
        return value.encode("utf-8")
    if ftype == "u64":
        assert isinstance(value, int) and not isinstance(value, bool)
        return u64be(value)
    if ftype == "raw":
        assert isinstance(value, (bytes, bytearray))
        return bytes(value)
    raise ValueError(f"unknown transcript field type {ftype!r}")


def build_transcript(tag: str, fields: list[tuple[Any, str]]) -> bytes:
    out = tag.encode("ascii")
    for value, ftype in fields:
        fb = field_bytes(value, ftype)
        out += u32be(len(fb)) + fb
    return out


def sign(priv: ec.EllipticCurvePrivateKey, transcript: bytes) -> bytes:
    return priv.sign(transcript, ec.ECDSA(hashes.SHA256()))


def verify_or_die(pub: ec.EllipticCurvePublicKey, sig: bytes, transcript: bytes, what: str) -> None:
    try:
        pub.verify(sig, transcript, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as exc:  # pragma: no cover - self-check
        raise AssertionError(f"self-check failed: {what} does not verify") from exc


# --------------------------------------------------------------------------
# secret_hash (TR-12): secret_hash(tag, x) = SHA-256(tag || x), over raw bytes.
# --------------------------------------------------------------------------
def secret_hash(tag: str, x: bytes) -> bytes:
    return hashlib.sha256(tag.encode("ascii") + x).digest()


def hexs(b: bytes) -> str:
    return b.hex()


# ==========================================================================
# Vector construction
# ==========================================================================
def build_vectors() -> dict[str, Any]:
    evidence_gaps: list[dict[str, str]] = []

    # ---- Keys (all TEST-ONLY, deterministic) ---------------------------
    ik_priv = det_private_key("instance-key-ik", ec.SECP256R1(), P256_ORDER)
    ik_pub = ik_priv.public_key()
    ik_spki = spki_der(ik_pub)
    iid = b32_lower_unpadded(hashlib.sha256(ik_spki).digest())
    assert len(iid) == 52, f"iid must be 52 chars, got {len(iid)}"

    dk_priv = det_private_key("device-key-dk", ec.SECP256R1(), P256_ORDER)
    dk_pub = dk_priv.public_key()
    dk_spki = spki_der(dk_pub)
    device_fp = b32_lower_unpadded(hashlib.sha256(dk_spki).digest())
    assert len(device_fp) == 52, f"device_fp must be 52 chars, got {len(device_fp)}"

    device_sas_core = device_fp[0:20].upper()
    device_sas = "-".join(device_sas_core[i : i + 5] for i in range(0, 20, 5))
    assert len(device_sas) == 23  # 4 groups of 5 + 3 hyphens

    keys: dict[str, Any] = {
        "instance_key_ik": {
            "label": "TEST-ONLY",
            "role": (
                "instance key (IK); signs HMP1-PAIR-RESP (isig); self-signed TLS cert key (TR-1, "
                "TR-8)"
            ),
            "curve": "P-256",
            "private_scalar_hex": format(ik_priv.private_numbers().private_value, "064x"),
            "spki_der_hex": hexs(ik_spki),
            "iid": iid,
        },
        "device_key_dk": {
            "label": "TEST-ONLY",
            "role": (
                "device key (DK); signs HMP1-PAIR-REQ, HMP1-PAIR-DONE, HMP1-TOKEN, "
                "HMP1-SELF-REVOKE"
            ),
            "curve": "P-256",
            "private_scalar_hex": format(dk_priv.private_numbers().private_value, "064x"),
            "spki_der_hex": hexs(dk_spki),
            "device_fp": device_fp,
            "device_sas": device_sas,
        },
    }

    # ---- Positive: iid / device_fp / device_sas -------------------------
    positive_iid = {
        "label": "TEST-ONLY",
        "clause": "ID-2 identities table (iid)",
        "instance_spki_der_hex": hexs(ik_spki),
        "sha256_of_spki_hex": hexs(hashlib.sha256(ik_spki).digest()),
        "iid": iid,
        "note": (
            "iid = base32(lowercase, unpadded, RFC4648) of SHA-256(SPKI DER of the P-256 instance "
            "key, uncompressed point)."
        ),
    }
    positive_device_fp = {
        "label": "TEST-ONLY",
        "clause": "ID-2 identities table (device_fp)",
        "device_spki_der_hex": hexs(dk_spki),
        "sha256_of_spki_hex": hexs(hashlib.sha256(dk_spki).digest()),
        "device_fp": device_fp,
        "note": "Same construction as iid, over the device SPKI.",
    }
    positive_device_sas = {
        "label": "TEST-ONLY",
        "clause": "ID-2 identities table (device_sas)",
        "device_fp": device_fp,
        "device_sas": device_sas,
        "note": (
            "device_sas = upper(device_fp[0:20]) grouped XXXXX-XXXXX-XXXXX-XXXXX (100 bits; a "
            "string-level slice of the base32 device_fp, not a re-encoding of raw hash bits)."
        ),
    }

    # ---- Positive: b64u known-answer pairs -------------------------------
    b64u_cases = []
    for name, n in [
        ("oid", 16),
        ("s_offer_secret", 32),
        ("nd", 32),
        ("ni", 32),
        ("nonce", 16),
        ("refresh_token_raw", 32),
        ("pairing_id", 16),
    ]:
        raw = det_bytes(f"b64u-sample:{name}", n)
        enc = b64u(raw)
        assert b64u_decode_canonical(enc) == raw, f"b64u round-trip failed for {name}"
        assert "=" not in enc, "canonical b64u must be unpadded"
        b64u_cases.append({"field": name, "decoded_len": n, "raw_hex": hexs(raw), "b64u": enc})
    # device_pub is 91 bytes (P-256 SPKI DER) -- use the real DK SPKI itself.
    assert len(dk_spki) == 91, f"expected 91-byte P-256 SPKI, got {len(dk_spki)}"
    dk_spki_b64u = b64u(dk_spki)
    assert b64u_decode_canonical(dk_spki_b64u) == dk_spki
    b64u_cases.append(
        {"field": "device_pub", "decoded_len": 91, "raw_hex": hexs(dk_spki), "b64u": dk_spki_b64u}
    )

    # ---- Positive: secret_hash(HMP1-OFFER, S) and the *different*
    # plain SHA-256(S) that appears inside the PAIR-REQ transcript field.
    S = det_bytes("offer-secret-S", 32)  # noqa: N806 -- matches HMP_V1.md's secret_hash(tag, S)
    secret_hash_offer = secret_hash("HMP1-OFFER", S)
    plain_sha256_S = hashlib.sha256(S).digest()  # noqa: N806 -- see `S` above
    assert secret_hash_offer != plain_sha256_S, "sanity: these two hashes of S must differ"

    host_id_placeholder = det_bytes("host-id-placeholder", 24)
    secret_hash_host = secret_hash("HMP1-HOST", host_id_placeholder)
    evidence_gaps.append(
        {
            "id": "EVIDENCE_GAP-HMP1-HOST-INPUT",
            "clause": (
                "V-1 (hash domain tags table), ID-2 (\"bound to a hashed host id held outside "
                "every Hermes home\")"
            ),
            "note": (
                "HMP_V1.md names HMP1-HOST as a valid secret_hash domain tag (V-1) and "
                "states the instance key is bound to a 'hashed host id' (ID-2), but does "
                "not specify the exact byte encoding of the host id that is hashed (source "
                "string, length, normalization). This vector therefore tests only the "
                "generic secret_hash(tag, x) = SHA-256(tag || x) construction (TR-12) for "
                "the HMP1-HOST tag, using an arbitrary fixed-length TEST-ONLY placeholder "
                "for x. It is NOT a claim about the real host-id encoding used by ID-2's "
                "instance-key custody; that encoding is server-implementation scope not "
                "fixed by the contract text, and no vector here guesses at it."
            ),
        }
    )

    positive_secret_hash = {
        "HMP1-OFFER": {
            "label": "TEST-ONLY",
            "clause": "PR1-1, TR-12",
            "tag": "HMP1-OFFER",
            "x_field": "S (32-byte offer secret)",
            "x_hex": hexs(S),
            "secret_hash_hex": hexs(secret_hash_offer),
            "note": (
                "secret_hash('HMP1-OFFER', S) = SHA-256('HMP1-OFFER' || S), stored server-side "
                "per PR1-1. This is DIFFERENT from the plain SHA-256(S) used as the third field "
                "of the HMP1-PAIR-REQ transcript below (TR-13) -- see plain_sha256_of_S_hex there."
            ),
        },
        "HMP1-HOST": {
            "label": "TEST-ONLY",
            "clause": "V-1, ID-2",
            "tag": "HMP1-HOST",
            "x_field": (
                "TEST-ONLY placeholder host-id bytes (contract does not define the real encoding)"
            ),
            "x_hex": hexs(host_id_placeholder),
            "secret_hash_hex": hexs(secret_hash_host),
            "evidence_gap": "EVIDENCE_GAP-HMP1-HOST-INPUT",
            "note": (
                "Tests only the generic secret_hash(tag, x) construction for this tag. See "
                "_meta.evidence_gaps."
            ),
        },
    }

    # ---- Positive: the five HMP1-* transcripts, as one coherent walkthrough ----
    oid = det_bytes("pairing-oid", 16)
    device_name = "Test Device #1​"  # includes a U+200B (Cf) char: PR2-3 strips it on sanitize,
    # but the signature transcript covers the exact pre-sanitization wire value (TR-13).
    nd = det_bytes("nd", 32)
    ni = det_bytes("ni", 32)
    pairing_id = det_bytes("pairing-id", 16)
    confirm_by = 1_800_000_000  # fixed test unix time (u64 field)
    ts_pair_done = 1_800_000_100
    device_id = "dev_" + b64u(det_bytes("device-id", 16))
    refresh_raw = det_bytes("refresh-token-raw", 32)
    refresh_hash = hashlib.sha256(refresh_raw).digest()
    token_nonce = det_bytes("token-nonce", 16)
    ts_token = 1_800_000_200
    ts_self_revoke = 1_800_000_300

    pair_req_fields: list[tuple[Any, str]] = [
        (iid, "str"),
        (oid, "raw"),
        (plain_sha256_S, "raw"),
        (dk_spki, "raw"),
        (device_name, "str"),
        (nd, "raw"),
    ]
    pair_req_transcript = build_transcript("HMP1-PAIR-REQ", pair_req_fields)
    pair_req_sig = sign(dk_priv, pair_req_transcript)
    verify_or_die(dk_pub, pair_req_sig, pair_req_transcript, "HMP1-PAIR-REQ")

    pair_resp_fields: list[tuple[Any, str]] = [
        (iid, "str"),
        (oid, "raw"),
        (dk_spki, "raw"),
        (nd, "raw"),
        (ni, "raw"),
        (pairing_id, "raw"),
        (device_sas, "str"),
        (confirm_by, "u64"),
    ]
    pair_resp_transcript = build_transcript("HMP1-PAIR-RESP", pair_resp_fields)
    pair_resp_sig = sign(ik_priv, pair_resp_transcript)
    verify_or_die(ik_pub, pair_resp_sig, pair_resp_transcript, "HMP1-PAIR-RESP")

    pair_done_fields: list[tuple[Any, str]] = [
        (iid, "str"),
        (pairing_id, "raw"),
        (nd, "raw"),
        (ni, "raw"),
        (ts_pair_done, "u64"),
    ]
    pair_done_transcript = build_transcript("HMP1-PAIR-DONE", pair_done_fields)
    pair_done_sig = sign(dk_priv, pair_done_transcript)
    verify_or_die(dk_pub, pair_done_sig, pair_done_transcript, "HMP1-PAIR-DONE")

    token_fields: list[tuple[Any, str]] = [
        (iid, "str"),
        (device_id, "str"),
        (refresh_hash, "raw"),
        (ts_token, "u64"),
        (token_nonce, "raw"),
    ]
    token_transcript = build_transcript("HMP1-TOKEN", token_fields)
    token_sig = sign(dk_priv, token_transcript)
    verify_or_die(dk_pub, token_sig, token_transcript, "HMP1-TOKEN")

    self_revoke_fields: list[tuple[Any, str]] = [
        (iid, "str"),
        (device_id, "str"),
        (ts_self_revoke, "u64"),
    ]
    self_revoke_transcript = build_transcript("HMP1-SELF-REVOKE", self_revoke_fields)
    self_revoke_sig = sign(dk_priv, self_revoke_transcript)
    verify_or_die(dk_pub, self_revoke_sig, self_revoke_transcript, "HMP1-SELF-REVOKE")

    def field_dump(fields: list[tuple[Any, str]], names: list[str]) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for (value, ftype), name in zip(fields, names, strict=True):
            fb = field_bytes(value, ftype)
            entry: dict[str, Any] = {"type": ftype, "len": len(fb), "bytes_hex": hexs(fb)}
            if ftype == "str" or ftype == "u64":
                entry["value"] = value
            d[name] = entry
        return d

    transcripts = {
        "HMP1-PAIR-REQ": {
            "clause": "TR-13, PR2-1",
            "signer": "device_key_dk",
            "fields": field_dump(
                pair_req_fields, ["iid", "oid", "sha256_of_S", "device_pub", "device_name", "nd"]
            ),
            "transcript_hex": hexs(pair_req_transcript),
            "sig_der_hex": hexs(pair_req_sig),
            "sig_der_b64u": b64u(pair_req_sig),
        },
        "HMP1-PAIR-RESP": {
            "clause": "TR-13, PR2-4",
            "signer": "instance_key_ik",
            "fields": field_dump(
                pair_resp_fields,
                ["iid", "oid", "device_pub", "nd", "ni", "pairing_id", "device_sas", "confirm_by"],
            ),
            "transcript_hex": hexs(pair_resp_transcript),
            "sig_der_hex": hexs(pair_resp_sig),
            "sig_der_b64u": b64u(pair_resp_sig),
        },
        "HMP1-PAIR-DONE": {
            "clause": "TR-13, PR4-1",
            "signer": "device_key_dk",
            "fields": field_dump(pair_done_fields, ["iid", "pairing_id", "nd", "ni", "ts"]),
            "transcript_hex": hexs(pair_done_transcript),
            "sig_der_hex": hexs(pair_done_sig),
            "sig_der_b64u": b64u(pair_done_sig),
        },
        "HMP1-TOKEN": {
            "clause": "TR-13, PR5-1",
            "signer": "device_key_dk",
            "fields": field_dump(
                token_fields, ["iid", "device_id", "sha256_of_refresh_raw", "ts", "nonce"]
            ),
            "transcript_hex": hexs(token_transcript),
            "sig_der_hex": hexs(token_sig),
            "sig_der_b64u": b64u(token_sig),
            "refresh_token_raw_hex": hexs(refresh_raw),
            "note": (
                "sha256_of_refresh_raw is SHA-256 of the RAW decoded refresh-token bytes (PR4-4, "
                "TR-12), never of its base64url text."
            ),
        },
        "HMP1-SELF-REVOKE": {
            "clause": "TR-13, PR7-3",
            "signer": "device_key_dk",
            "fields": field_dump(self_revoke_fields, ["iid", "device_id", "ts"]),
            "transcript_hex": hexs(self_revoke_transcript),
            "sig_der_hex": hexs(self_revoke_sig),
            "sig_der_b64u": b64u(self_revoke_sig),
        },
    }

    # ---- Positive: QR payload (PR1-3) -----------------------------------
    qr_exp = 1_900_000_000  # fixed test unix time, far in the future
    qr_oid = det_bytes("qr-oid", 16)
    qr_s = det_bytes("qr-s", 32)
    # NOTE: ep values below are synthetic placeholders chosen only to match the
    # required address shapes (PR1-5): a *.ts.net name that cannot resolve to
    # any real tailnet ("example-test-instance"), and the CGNAT network base
    # address +1. Neither corresponds to any real host, device or tailnet.
    qr_payload_obj = {
        "v": 1,
        "iid": iid,
        "ep": ["https://example-test-instance\x2ets.net:8443", "https://100\x2e64.0.1:8443"],
        "oid": b64u(qr_oid),
        "s": b64u(qr_s),
        "exp": qr_exp,
    }
    qr_json = json.dumps(qr_payload_obj, separators=(",", ":"), sort_keys=False)
    qr_wire = "hmp1:" + b64u(qr_json.encode("utf-8"))
    positive_qr = {
        "label": "TEST-ONLY",
        "clause": "PR1-3",
        "json": qr_payload_obj,
        "json_text": qr_json,
        "wire": qr_wire,
        "note": (
            "wire = 'hmp1:' + b64u(UTF-8 JSON bytes). JSON key order is not wire-significant "
            "(a conforming client parses the JSON object; it does not byte-compare it), so "
            "json_text here is illustrative, not a canonicalization requirement."
        ),
    }

    positive: dict[str, Any] = {
        "iid": positive_iid,
        "device_fp": positive_device_fp,
        "device_sas": positive_device_sas,
        "b64u": b64u_cases,
        "secret_hash": positive_secret_hash,
        "transcripts": transcripts,
        "qr_payload": positive_qr,
    }

    def make_bad_qr(**overrides: Any) -> dict[str, Any]:
        obj = dict(qr_payload_obj)
        obj.update(overrides)
        wire = "hmp1:" + b64u(json.dumps(obj, separators=(",", ":")).encode("utf-8"))
        return {"bad_qr_json": obj, "bad_qr_wire": wire}

    # ======================================================================
    # Negative vectors (TR-14 + T015 + IR-16): every conforming implementation
    # MUST reject each of these.
    # ======================================================================
    negative: dict[str, Any] = {}

    # -- compressed-point SPKI (TR-12: uncompressed only) ------------------
    compressed_spki = compressed_point_spki_der(dk_pub)
    negative["compressed_point_spki"] = {
        "clause": "TR-12",
        "curve": "P-256",
        "spki_der_hex": hexs(compressed_spki),
        "spki_der_b64u": b64u(compressed_spki),
        "reason": (
            "Device/instance keys MUST be an uncompressed SEC1 point (65 B, leading 0x04) inside "
            "SPKI; a compressed point (leading 0x02/0x03) MUST be rejected even though it encodes "
            "a valid, verifiable public key."
        ),
    }

    # -- P-384 SPKI (wrong curve; still a valid uncompressed point) --------
    p384_priv = det_private_key("wrong-curve-p384", ec.SECP384R1(), P384_ORDER)
    p384_spki = spki_der(p384_priv.public_key())
    negative["p384_spki"] = {
        "clause": "TR-12",
        "curve": "P-384",
        "spki_der_hex": hexs(p384_spki),
        "spki_der_b64u": b64u(p384_spki),
        "reason": (
            "Only P-256 is accepted for device/instance keys; a syntactically valid "
            "uncompressed-point SPKI on another curve MUST be rejected."
        ),
    }

    # -- padded b64u (TR-11: canonical is unpadded only) --------------------
    padded_sample_raw = det_bytes("padded-sample", 16)
    canonical = b64u(padded_sample_raw)
    padded = base64.urlsafe_b64encode(padded_sample_raw).decode("ascii")  # keeps '=' padding
    assert padded != canonical and padded.rstrip("=") == canonical
    negative["padded_b64u"] = {
        "clause": "TR-11",
        "raw_hex": hexs(padded_sample_raw),
        "canonical_b64u": canonical,
        "padded_b64u": padded,
        "reason": (
            "base64url is canonical only when unpadded (RFC 4648 §5 alphabet, no '='). The padded "
            "form decodes to the same bytes but MUST be rejected as non-canonical wire input."
        ),
    }

    # -- wrong lengths, one case per decoded-length class in TR-11's table --
    wrong_length_cases = []
    for correct_len in [16, 32, 91]:
        good = det_bytes(f"wronglen-{correct_len}", correct_len)
        for delta, tag in [(-1, "short"), (1, "long")]:
            bad_len = correct_len + delta
            bad = (
                good[:bad_len]
                if delta < 0
                else good + det_bytes(f"wronglen-pad-{correct_len}", delta)
            )
            wrong_length_cases.append(
                {
                    "applies_to_fields": {
                        16: ["oid", "nonce", "pairing_id"],
                        32: ["s", "nd", "ni", "tokens"],
                        91: ["device_pub"],
                    }[correct_len],
                    "expected_decoded_len": correct_len,
                    "actual_decoded_len": bad_len,
                    "variant": tag,
                    "raw_hex": hexs(bad),
                    "b64u": b64u(bad),
                }
            )
    negative["wrong_length"] = {
        "clause": "TR-11",
        "cases": wrong_length_cases,
        "reason": (
            "TR-11 fixes an exact decoded byte length per field. A value that base64url-decodes "
            "cleanly but to the wrong length MUST be rejected."
        ),
    }

    # -- float ts (ID-1 / TR-10: protocol-minted integers only) -------------
    negative["float_ts"] = {
        "clause": "ID-1, TR-10",
        "example_route": "POST /hmp/v1/pair/complete (P4)",
        "bad_request_json": {
            "pairing_id": b64u(pairing_id),
            "ts": 1800000100.0,
            "sig_der_b64u": b64u(pair_done_sig),
        },
        "reason": (
            "Every protocol-minted timestamp (ts, exp, confirm_by, access_expires_at, served_at, "
            "turn.since, sent_at) is a JSON integer. A JSON float (even one with a zero fractional "
            "part, e.g. 1800000100.0) MUST be rejected, not coerced."
        ),
        "note": (
            "The signature field here is named sig_der_b64u (not the wire name 'sig', per PR4-1) "
            "so every randomized-signature leaf in this file matches one glob for CI regeneration "
            "comparison (IR-16); it is the same HMP1-PAIR-DONE signature produced above."
        ),
    }

    # -- boolean v (TR-10 / V-1: v is an integer) ----------------------------
    bad_v_qr = dict(qr_payload_obj)
    bad_v_qr["v"] = True
    negative["boolean_v"] = {
        "clause": "TR-10, V-1",
        "example_route": "hmp1: QR payload 'v', also POST body 'v' and /ready 'versions' entries",
        "bad_qr_json": bad_v_qr,
        "bad_qr_wire": "hmp1:" + b64u(json.dumps(bad_v_qr, separators=(",", ":")).encode("utf-8")),
        "reason": (
            "v MUST be a JSON integer (1 in v1). A JSON boolean MUST be rejected, not treated as "
            "1/0 (JSON true/false are a distinct type from integers per TR-10)."
        ),
    }

    # -- ep validation: scheme/host/form (FR-002, PR1-5, CS-10) --------------
    # FR-002/CS-10 fixes the exact ep grammar: `https://<host>:<port>` only --
    # no userinfo, path, query or fragment -- where <host> is either a
    # lowercase, non-trailing-dot name ending in .ts.net, or a literal address
    # in 100\x2e64.0.0/10 or fd7a:115c:a1e0::/48. Every clause below is one way
    # to violate that grammar while still superficially "looking like" a URL.
    negative["ep_validation"] = {
        "clause": "FR-002, PR1-5, CS-10",
        "cases": [
            {"sub_case": "http_scheme", "ep": "http://100\x2e64.0.1:8443",
             "reason": "scheme is http, not https"},
            {"sub_case": "https_but_host_not_allowed", "ep": "https://evil-example.invalid:8443",
             "reason": (
                 "https, but host is neither *.ts.net, 100\x2e64.0.0/10, nor fd7a:115c:a1e0::/48"
             )},
            {"sub_case": "userinfo", "ep": "https://user:pass@100\x2e64.0.1:8443",
             "reason": "CS-10 forbids userinfo in ep"},
            {"sub_case": "path", "ep": "https://100\x2e64.0.1:8443/path",
             "reason": "CS-10 forbids a path in ep"},
            {"sub_case": "query", "ep": "https://100\x2e64.0.1:8443?q=1",
             "reason": "CS-10 forbids a query string in ep"},
            {"sub_case": "fragment", "ep": "https://100\x2e64.0.1:8443#frag",
             "reason": "CS-10 forbids a fragment in ep"},
            {"sub_case": "uppercase_host", "ep": "https://EXAMPLE-TEST-INSTANCE.TS.NET:8443",
             "reason": (
                 "CS-10 requires <host> to be a lowercase DNS name; uppercase is non-canonical"
             )},
            {"sub_case": "trailing_dot_host", "ep": "https://example-test-instance\x2ets.net.:8443",
             "reason": "CS-10 forbids a trailing dot on the .ts.net name"},
            {"sub_case": "ipv4_just_below_range", "ep": "https://100.63.255.255:8443",
             "reason": "one address below the 100\x2e64.0.0/10 lower bound"},
            {"sub_case": "ipv4_just_above_range", "ep": "https://100.128.0.0:8443",
             "reason": "one address past the top of the 100\x2e64.0.0/10 block"},
            {"sub_case": "ipv6_outside_range", "ep": "https://[fd7a:115c:a1e1::1]:8443",
             "reason": "differs from the required fd7a:115c:a1e0::/48 prefix in the 48th bit"},
            {"sub_case": "missing_port", "ep": "https://100\x2e64.0.1",
             "reason": "CS-10 requires ep to be exactly https://<host>:<port>; no port is present"},
        ],
        "reason": (
            "FR-002/CS-10 fixes the exact ep grammar (scheme, host form, no "
            "userinfo/path/query/fragment, mandatory port). Every case above is syntactically "
            "URL-shaped but violates exactly one requirement."
        ),
        "note": (
            "Addresses used here are synthetic placeholders (see qr_payload note); none correspond "
            "to a real host, device or tailnet."
        ),
    }

    # -- unknown/future version v (PR1-5: "rejects ... an unknown v") -------
    negative["unknown_version_v"] = {
        "clause": "PR1-5, V-2",
        **make_bad_qr(v=2),
        "reason": (
            "A v1 client understands only v=1. PR1-5 requires rejecting an unknown v; v=2 is a "
            "syntactically valid integer but is not the v1 client's version."
        ),
    }

    # -- malformed / non-canonical iid inside a QR payload (PR1-5) -----------
    iid_too_short = iid[:-1]
    iid_too_long = iid + "a"
    iid_bad_alphabet = iid[:-1] + "1"  # '1' is not in RFC4648 base32's [A-Z2-7]
    iid_uppercase = iid.upper()  # ID-2 fixes iid as lowercase; uppercase is non-canonical
    iid_padded = iid + "="
    assert len(iid_bad_alphabet) == len(iid)
    malformed_iid_cases = []
    for sub_case, bad_iid, reason in [
        ("wrong_length_short", iid_too_short, f"{len(iid_too_short)} chars, not 52"),
        ("wrong_length_long", iid_too_long, f"{len(iid_too_long)} chars, not 52"),
        (
            "invalid_alphabet_char",
            iid_bad_alphabet,
            "contains '1', which is outside RFC4648 base32's [A-Z2-7] digit set",
        ),
        (
            "uppercase",
            iid_uppercase,
            "iid is fixed as lowercase (ID-2); uppercase is non-canonical",
        ),
        (
            "padded",
            iid_padded,
            "iid is unpadded (ID-2/TR-11 style); a trailing '=' is non-canonical",
        ),
    ]:
        qr = make_bad_qr(iid=bad_iid)
        malformed_iid_cases.append({"sub_case": sub_case, "iid": bad_iid, "reason": reason, **qr})
    negative["malformed_iid"] = {
        "clause": "PR1-5, ID-2",
        "cases": malformed_iid_cases,
        "reason": (
            "PR1-5 requires rejecting a malformed iid in the QR payload. Each case is embedded in "
            "an otherwise-valid QR payload so the whole ingestion path can be tested, not just an "
            "isolated string check."
        ),
    }

    # -- wrong-length oid/s embedded inside a full QR payload (PR1-5) --------
    qr_oid_short = det_bytes("qr-oid-short", 15)
    qr_s_long = det_bytes("qr-s-long", 33)
    negative["qr_wrong_length"] = {
        "clause": "PR1-5, TR-11",
        "cases": [
            {
                "sub_case": "oid_15_bytes",
                "field": "oid",
                "decoded_len": 15,
                **make_bad_qr(oid=b64u(qr_oid_short)),
                "reason": (
                    "oid MUST decode to exactly 16 bytes (TR-11); this QR's oid decodes to 15"
                ),
            },
            {
                "sub_case": "s_33_bytes",
                "field": "s",
                "decoded_len": 33,
                **make_bad_qr(s=b64u(qr_s_long)),
                "reason": "s MUST decode to exactly 32 bytes (TR-11); this QR's s decodes to 33",
            },
        ],
        "reason": (
            "PR1-5 requires rejecting a wrong-length oid or s. These are the generic wrong_length "
            "cases above, re-embedded inside a full QR payload so the QR-ingestion path itself is "
            "exercised."
        ),
    }

    # -- non-zero trailing bits in b64u (TR-11: "round-trip exact") ---------
    negative["non_canonical_trailing_bits"] = {
        "clause": "TR-11",
        "cases": [
            {
                "field_length_class": 16,
                **corrupt_trailing_padding_bits(det_bytes("trailbits-16", 16)),
            },
            {
                "field_length_class": 32,
                **corrupt_trailing_padding_bits(det_bytes("trailbits-32", 32)),
            },
        ],
        "reason": (
            "TR-11 requires base64url to round-trip exactly. For a decoded length not a "
            "multiple of 3 bytes, the final base64 character carries unused 'padding' bits "
            "that a canonical encoder always sets to zero. non_canonical_b64u sets those bits "
            "to a non-zero pattern: a lenient decoder (Python's stdlib included) still decodes "
            "it to the identical raw bytes as canonical_b64u, but re-encoding those bytes never "
            "reproduces non_canonical_b64u -- so it MUST be rejected as non-canonical input, not "
            "silently accepted as an alternate spelling of the same value."
        ),
    }

    # -- P-256 point not on the curve (TR-12) --------------------------------
    off_curve_spki = off_curve_point_spki_der(dk_pub)
    negative["point_not_on_curve"] = {
        "clause": "TR-12",
        "curve": "P-256",
        "spki_der_hex": hexs(off_curve_spki),
        "spki_der_b64u": b64u(off_curve_spki),
        "reason": (
            "Right length (91 B), right prefix (0x04, uncompressed), right curve OID -- but "
            "(x, y) does not satisfy y^2 = x^3 - 3x + b mod p, so it is not a point on P-256 at "
            "all and names no valid public key. A conforming implementation MUST reject this at "
            "key-load time (or the first signature verification against it MUST fail), not treat "
            "it as an unusual-but-valid key."
        ),
    }

    # -- past exp (PR1-5) ----------------------------------------------------
    negative["past_exp"] = {
        "clause": "PR1-5",
        **make_bad_qr(exp=946_684_800),  # 2000-01-01T00:00:00Z: always in the past
        "reason": (
            "The client MUST reject a QR whose exp has already passed. 946684800 "
            "(2000-01-01T00:00:00Z) is used so this vector stays in the past at any future "
            "verification time."
        ),
    }

    out: dict[str, Any] = {
        "_meta": {
            "schema_version": SCHEMA_VERSION,
            "contract_revision": CONTRACT_REVISION,
            "contract_file": "docs/architecture/contracts/HMP_V1.md",
            "generator": "tools/vectors/gen_hmp1_vectors.py",
            "independent": True,
            "independent_note": INDEPENDENCE_NOTE,
            "key_warning": TEST_ONLY_WARNING,
            "determinism_note": DETERMINISM_NOTE,
            "evidence_gaps": evidence_gaps,
        },
        "keys": keys,
        "positive": positive,
        "negative": negative,
    }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/architecture/contracts/vectors/hmp_v1_vectors.json"),
        help="Output path for the vector JSON file.",
    )
    args = parser.parse_args()

    vectors = build_vectors()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(vectors, f, indent=2, sort_keys=False, ensure_ascii=True)
        f.write("\n")

    gap_count = len(vectors["_meta"]["evidence_gaps"])
    print(
        f"wrote {args.out} ({gap_count} EVIDENCE_GAP note(s); see _meta.evidence_gaps)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
