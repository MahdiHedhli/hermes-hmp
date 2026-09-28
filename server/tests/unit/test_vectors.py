"""T020 acceptance: every positive and negative vector from T015 passes against `wire.py` and
`crypto.py` (`docs/architecture/contracts/vectors/hmp_v1_vectors.json`, TR-14).

ECDSA signatures in the vector file are randomized, so they are verified, never byte-compared
(the file's `determinism_note`). The coverage tests at the bottom fail when a new vector group is
added to the file without a test here.
"""

from __future__ import annotations

import datetime
import json
import time
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from hmp_plugin import crypto, wire
from hmp_plugin.contract import (
    HASH_DOMAIN_TAGS,
    TAG_GRACE,
    TRANSCRIPT_TAGS,
    QrOffer,
)

REPO = Path(__file__).resolve().parents[3]
VECTORS: dict[str, Any] = json.loads(
    (REPO / "docs/architecture/contracts/vectors/hmp_v1_vectors.json").read_text(encoding="utf-8")
)
POS = VECTORS["positive"]
NEG = VECTORS["negative"]
KEYS = VECTORS["keys"]
NOW = int(time.time())

# Vector field names -> TR-11 field names (`B64U_DECODED_LENGTHS`).
FIELD_ALIASES = {"s_offer_secret": "s", "refresh_token_raw": "token", "tokens": "token"}


def _field(name: str) -> str:
    return FIELD_ALIASES.get(name, name)


def _qr_wire(body: dict[str, Any]) -> str:
    """Encode a (possibly invalid) QR body the way the generator does, bypassing validation."""
    return "hmp1:" + wire.b64u_encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))


def test_vector_file_is_for_this_contract() -> None:
    assert VECTORS["_meta"]["contract_revision"] == "1.0"
    assert VECTORS["_meta"]["independent"] is True


# --------------------------------------------------------------------------------------------------
# Keys
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(KEYS))
def test_test_keys_derive_their_spki_and_fingerprint(name: str) -> None:
    key = KEYS[name]
    assert key["label"] == "TEST-ONLY"
    priv = ec.derive_private_key(int(key["private_scalar_hex"], 16), ec.SECP256R1())
    spki = crypto.spki_der(priv.public_key())
    assert spki.hex() == key["spki_der_hex"]
    fp = crypto.spki_fingerprint(spki)
    assert fp == key.get("iid", key.get("device_fp"))
    if "device_sas" in key:
        assert crypto.device_sas(fp) == key["device_sas"]


# --------------------------------------------------------------------------------------------------
# Positive
# --------------------------------------------------------------------------------------------------


def test_iid() -> None:
    v = POS["iid"]
    spki = bytes.fromhex(v["instance_spki_der_hex"])
    assert crypto.sha256(spki).hex() == v["sha256_of_spki_hex"]
    assert crypto.spki_fingerprint(spki) == v["iid"]
    assert wire.require_iid(v["iid"]) == v["iid"]


def test_device_fp() -> None:
    v = POS["device_fp"]
    spki = bytes.fromhex(v["device_spki_der_hex"])
    assert crypto.sha256(spki).hex() == v["sha256_of_spki_hex"]
    assert crypto.spki_fingerprint(spki) == v["device_fp"]
    assert wire.require_iid(v["device_fp"]) == v["device_fp"]


def test_device_sas() -> None:
    v = POS["device_sas"]
    assert crypto.device_sas(v["device_fp"]) == v["device_sas"]


@pytest.mark.parametrize("case", POS["b64u"], ids=lambda c: c["field"])
def test_b64u_round_trip_at_exact_length(case: dict[str, Any]) -> None:
    raw = bytes.fromhex(case["raw_hex"])
    assert len(raw) == case["decoded_len"]
    assert wire.b64u_encode(raw) == case["b64u"]
    assert wire.b64u_decode(case["b64u"], length=case["decoded_len"]) == raw
    assert wire.b64u_field(_field(case["field"]), case["b64u"]) == raw


@pytest.mark.parametrize("tag", sorted(POS["secret_hash"]))
def test_secret_hash(tag: str) -> None:
    v = POS["secret_hash"][tag]
    assert tag.encode("ascii") in HASH_DOMAIN_TAGS
    got = crypto.secret_hash(tag.encode("ascii"), bytes.fromhex(v["x_hex"]))
    assert got.hex() == v["secret_hash_hex"]


def _typed(field: dict[str, Any]) -> bytes | str | int:
    kind = field["type"]
    if kind == "str":
        assert field["value"].encode("utf-8").hex() == field["bytes_hex"]
        return str(field["value"])
    if kind == "u64":
        return int(field["value"])
    assert kind == "raw"
    return bytes.fromhex(field["bytes_hex"])


@pytest.mark.parametrize("tag", sorted(POS["transcripts"]))
def test_transcript_bytes_and_signature(tag: str) -> None:
    v = POS["transcripts"][tag]
    assert tag.encode("ascii") in TRANSCRIPT_TAGS
    fields = [_typed(f) for f in v["fields"].values()]
    for f in v["fields"].values():
        assert len(bytes.fromhex(f["bytes_hex"])) == f["len"]
    got = crypto.transcript(tag.encode("ascii"), *fields)
    assert got.hex() == v["transcript_hex"]

    signer = bytes.fromhex(KEYS[v["signer"]]["spki_der_hex"])
    sig = bytes.fromhex(v["sig_der_hex"])
    assert wire.b64u_signature(v["sig_der_b64u"]) == sig
    assert crypto.verify(signer, sig, got)
    # The wrong key, a changed transcript and a changed tag all fail.
    other = next(k for k in KEYS.values() if k["spki_der_hex"] != signer.hex())
    assert not crypto.verify(bytes.fromhex(other["spki_der_hex"]), sig, got)
    assert not crypto.verify(signer, sig, got + b"\x00")
    other_tag = next(t for t in TRANSCRIPT_TAGS if t != tag.encode("ascii"))
    assert not crypto.verify(signer, sig, crypto.transcript(other_tag, *fields))


@pytest.mark.parametrize("tag", sorted(POS["transcripts"]))
def test_our_signature_over_a_vector_transcript_verifies(tag: str) -> None:
    v = POS["transcripts"][tag]
    key = KEYS[v["signer"]]
    priv = ec.derive_private_key(int(key["private_scalar_hex"], 16), ec.SECP256R1())
    msg = bytes.fromhex(v["transcript_hex"])
    sig = crypto.sign(priv, msg)
    assert crypto.verify(bytes.fromhex(key["spki_der_hex"]), sig, msg)


def test_high_s_signature_is_accepted() -> None:
    """TR-13: verifiers accept both low-S and high-S."""
    v = POS["transcripts"]["HMP1-TOKEN"]
    spki = bytes.fromhex(KEYS[v["signer"]]["spki_der_hex"])
    msg = bytes.fromhex(v["transcript_hex"])
    from cryptography.hazmat.primitives.asymmetric.utils import (
        decode_dss_signature,
        encode_dss_signature,
    )

    n = int("FFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551", 16)
    r, s = decode_dss_signature(bytes.fromhex(v["sig_der_hex"]))
    flipped = encode_dss_signature(r, n - s)
    assert crypto.verify(spki, bytes.fromhex(v["sig_der_hex"]), msg)
    assert crypto.verify(spki, flipped, msg)


def test_qr_payload() -> None:
    v = POS["qr_payload"]
    body = v["json"]
    offer = QrOffer(
        v=body["v"],
        iid=body["iid"],
        ep=tuple(body["ep"]),
        oid=body["oid"],
        s=body["s"],
        exp=body["exp"],
    )
    decoded = wire.decode_qr_payload(v["wire"], now=NOW)
    assert decoded == offer
    assert json.loads(wire.b64u_decode_bounded(v["wire"][5:], max_length=2048)) == body
    # Our encoder produces a payload that decodes to the same offer (key order is not significant).
    ours = wire.encode_qr_payload(offer, now=NOW)
    assert ours.startswith("hmp1:")
    assert wire.decode_qr_payload(ours, now=NOW) == offer
    assert wire.b64u_field("oid", offer.oid) and wire.b64u_field("s", offer.s)


# --------------------------------------------------------------------------------------------------
# Negative
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["compressed_point_spki", "p384_spki", "point_not_on_curve"])
def test_bad_spki_is_rejected(name: str) -> None:
    v = NEG[name]
    der = bytes.fromhex(v["spki_der_hex"])
    with pytest.raises(crypto.CryptoError):
        crypto.check_p256_spki(der)
    with pytest.raises(crypto.CryptoError):
        crypto.spki_fingerprint(der)
    # As a wire field it is rejected by length or by the key check, and never verifies anything.
    try:
        decoded = wire.b64u_field("device_pub", v["spki_der_b64u"])
    except wire.WireError:
        pass
    else:
        assert decoded == der
        with pytest.raises(crypto.CryptoError):
            crypto.check_p256_spki(decoded)
    msg = bytes.fromhex(POS["transcripts"]["HMP1-PAIR-REQ"]["transcript_hex"])
    sig = bytes.fromhex(POS["transcripts"]["HMP1-PAIR-REQ"]["sig_der_hex"])
    assert not crypto.verify(der, sig, msg)


def test_padded_b64u_is_rejected() -> None:
    v = NEG["padded_b64u"]
    raw = bytes.fromhex(v["raw_hex"])
    assert wire.b64u_decode(v["canonical_b64u"], length=len(raw)) == raw
    with pytest.raises(wire.WireError):
        wire.b64u_decode(v["padded_b64u"], length=len(raw))
    with pytest.raises(wire.WireError):
        wire.b64u_decode_bounded(v["padded_b64u"], max_length=64)


@pytest.mark.parametrize(
    "case",
    NEG["wrong_length"]["cases"],
    ids=lambda c: f"{c['expected_decoded_len']}-{c['variant']}",
)
def test_wrong_length_is_rejected(case: dict[str, Any]) -> None:
    raw = bytes.fromhex(case["raw_hex"])
    assert len(raw) == case["actual_decoded_len"]
    for field in case["applies_to_fields"]:
        name = _field(field)
        assert wire.B64U_DECODED_LENGTHS[name] == case["expected_decoded_len"]
        with pytest.raises(wire.WireError):
            wire.b64u_field(name, case["b64u"])


def test_float_ts_is_rejected() -> None:
    v = NEG["float_ts"]
    text = json.dumps(v["bad_request_json"]).encode("utf-8")
    assert b"1800000100.0" in text
    body = wire.parse_body(text)
    with pytest.raises(wire.WireError):
        wire.require_int(body["ts"])
    assert wire.require_int(int(body["ts"])) == 1800000100


def test_boolean_v_is_rejected() -> None:
    v = NEG["boolean_v"]
    assert v["bad_qr_json"]["v"] is True
    with pytest.raises(wire.WireError):
        wire.decode_qr_payload(v["bad_qr_wire"], now=NOW)
    body = wire.parse_body(json.dumps(v["bad_qr_json"]).encode("utf-8"))
    with pytest.raises(wire.WireError):
        wire.require_int(body["v"])
    with pytest.raises(wire.WireError):
        wire.require_int(False)


@pytest.mark.parametrize("case", NEG["ep_validation"]["cases"], ids=lambda c: c["sub_case"])
def test_bad_endpoint_is_rejected(case: dict[str, Any]) -> None:
    with pytest.raises(wire.WireError):
        wire.require_endpoint(case["ep"])
    good = dict(POS["qr_payload"]["json"])
    good["ep"] = [case["ep"]]
    with pytest.raises(wire.WireError):
        wire.decode_qr_payload(_qr_wire(good), now=NOW)
    offer = QrOffer(
        v=1, iid=good["iid"], ep=(case["ep"],), oid=good["oid"], s=good["s"], exp=good["exp"]
    )
    with pytest.raises(wire.WireError):
        wire.encode_qr_payload(offer)


def test_valid_endpoints_are_accepted() -> None:
    for ep in (*POS["qr_payload"]["json"]["ep"], "https://[fd7a\x3a115c:a1e0::1]:443"):
        assert wire.require_endpoint(ep) == ep


def test_unknown_version_is_rejected() -> None:
    v = NEG["unknown_version_v"]
    with pytest.raises(wire.WireError):
        wire.decode_qr_payload(v["bad_qr_wire"], now=NOW)


@pytest.mark.parametrize("case", NEG["malformed_iid"]["cases"], ids=lambda c: c["sub_case"])
def test_malformed_iid_is_rejected(case: dict[str, Any]) -> None:
    with pytest.raises(wire.WireError):
        wire.require_iid(case["iid"])
    with pytest.raises(wire.WireError):
        wire.decode_qr_payload(case["bad_qr_wire"], now=NOW)


@pytest.mark.parametrize("case", NEG["qr_wrong_length"]["cases"], ids=lambda c: c["sub_case"])
def test_qr_wrong_length_is_rejected(case: dict[str, Any]) -> None:
    with pytest.raises(wire.WireError):
        wire.decode_qr_payload(case["bad_qr_wire"], now=NOW)
    with pytest.raises(wire.WireError):
        wire.b64u_field(case["field"], case["bad_qr_json"][case["field"]])


@pytest.mark.parametrize(
    "case", NEG["non_canonical_trailing_bits"]["cases"], ids=lambda c: str(c["decoded_len"])
)
def test_non_canonical_trailing_bits_are_rejected(case: dict[str, Any]) -> None:
    raw = bytes.fromhex(case["raw_hex"])
    assert wire.b64u_decode(case["canonical_b64u"], length=case["decoded_len"]) == raw
    with pytest.raises(wire.WireError):
        wire.b64u_decode(case["non_canonical_b64u"], length=case["decoded_len"])


def test_past_exp_is_rejected() -> None:
    v = NEG["past_exp"]
    with pytest.raises(wire.WireError):
        wire.decode_qr_payload(v["bad_qr_wire"], now=NOW)
    body = v["bad_qr_json"]
    offer = QrOffer(
        v=1, iid=body["iid"], ep=tuple(body["ep"]), oid=body["oid"], s=body["s"], exp=body["exp"]
    )
    with pytest.raises(wire.WireError):
        wire.encode_qr_payload(offer, now=NOW)


# --------------------------------------------------------------------------------------------------
# Coverage: a vector group added to the file without a test here fails the suite.
# --------------------------------------------------------------------------------------------------

POSITIVE_COVERED = {
    "iid",
    "device_fp",
    "device_sas",
    "b64u",
    "secret_hash",
    "transcripts",
    "qr_payload",
}
NEGATIVE_COVERED = {
    "compressed_point_spki",
    "p384_spki",
    "padded_b64u",
    "wrong_length",
    "float_ts",
    "boolean_v",
    "ep_validation",
    "unknown_version_v",
    "malformed_iid",
    "qr_wrong_length",
    "non_canonical_trailing_bits",
    "point_not_on_curve",
    "past_exp",
}


def test_every_positive_group_is_covered() -> None:
    assert set(POS) == POSITIVE_COVERED


def test_every_negative_group_is_covered() -> None:
    assert set(NEG) == NEGATIVE_COVERED


def test_every_transcript_tag_has_a_vector() -> None:
    assert {t.encode("ascii") for t in POS["transcripts"]} == set(TRANSCRIPT_TAGS)


# --------------------------------------------------------------------------------------------------
# Beyond the vector file: I-JSON limits, typing and the certificate
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1,"a":2}',  # duplicate member
        b'{"a":"\\ud800"}',  # lone surrogate escape
        b'{"\\udfff":1}',  # lone surrogate in a name
        b'{"a":\xff}',  # not UTF-8
        b'{"a":"\xed\xa0\x80"}',  # UTF-8-encoded surrogate
        b'{"a":NaN}',
        b'{"a":Infinity}',
        b"[1,2]",  # top level is not an object
        b'"x"',
        b"",
        b"{",
        b'\xef\xbb\xbf{"a":1}',  # BOM
    ],
)
def test_ijson_violations_are_bad_request(raw: bytes) -> None:
    with pytest.raises(wire.WireError) as info:
        wire.parse_body(raw)
    assert not isinstance(info.value, wire.TooLargeError)


def test_depth_and_size_limits_are_too_large() -> None:
    assert wire.parse_body(b'{"a":' + b"[" * 7 + b"1" + b"]" * 7 + b"}")  # depth 8
    with pytest.raises(wire.TooLargeError):
        wire.parse_body(b'{"a":' + b"[" * 8 + b"1" + b"]" * 8 + b"}")  # depth 9
    with pytest.raises(wire.TooLargeError):
        wire.parse_body(b'{"a":' + b"[" * 5000 + b"]" * 5000 + b"}", max_bytes=20_000)
    with pytest.raises(wire.TooLargeError):
        wire.parse_body(b'{"a":"' + b"x" * 8200 + b'"}')
    assert wire.parse_body(b'{"a":"[[[[[[[[[["}') == {"a": "[[[[[[[[[["}  # brackets in strings


@pytest.mark.parametrize("value", [True, False, 1.0, 1e3, "1", None, 2**53, -(2**53)])
def test_require_int_rejects(value: Any) -> None:
    with pytest.raises(wire.WireError):
        wire.require_int(value)


def test_require_int_bounds() -> None:
    assert wire.require_int(0, minimum=0) == 0
    with pytest.raises(wire.WireError):
        wire.require_int(-1, minimum=0)
    with pytest.raises(wire.WireError):
        wire.require_int(11, maximum=10)


def test_transcript_rejects_unknown_tags_and_bad_fields() -> None:
    with pytest.raises(crypto.CryptoError):
        crypto.transcript(b"HMP0-PAIR-REQ", "x")
    with pytest.raises(crypto.CryptoError):
        crypto.transcript(b"HMP1-TOKEN", True)
    with pytest.raises(crypto.CryptoError):
        crypto.transcript(b"HMP1-TOKEN", -1)
    with pytest.raises(crypto.CryptoError):
        crypto.transcript(b"HMP1-TOKEN", 2**64)
    with pytest.raises(crypto.CryptoError):
        crypto.secret_hash(b"HMP1-TOKEN", b"x")
    # The server-internal grace tag reuses the TR-13 encoding (research R16).
    assert crypto.transcript(TAG_GRACE, b"\x01", "f", "refresh").startswith(TAG_GRACE)


def test_verify_never_raises_on_garbage() -> None:
    spki = bytes.fromhex(KEYS["device_key_dk"]["spki_der_hex"])
    assert not crypto.verify(spki, b"", b"m")
    assert not crypto.verify(spki, b"\x30\x00", b"m")
    assert not crypto.verify(b"", b"\x30\x00", b"m")


def test_self_signed_certificate_pins_to_iid() -> None:
    priv = ec.derive_private_key(
        int(KEYS["instance_key_ik"]["private_scalar_hex"], 16), ec.SECP256R1()
    )
    now = datetime.datetime(2026, 9, 25, tzinfo=datetime.UTC)
    cert = crypto.self_signed_certificate(priv, now=now)
    spki = crypto.certificate_spki(cert)
    assert spki.hex() == KEYS["instance_key_ik"]["spki_der_hex"]
    assert crypto.spki_fingerprint(spki) == KEYS["instance_key_ik"]["iid"]
    from cryptography import x509

    parsed = x509.load_der_x509_certificate(cert)
    assert parsed.issuer == parsed.subject
    parsed.public_key().verify(  # self-signed by the instance key
        parsed.signature, parsed.tbs_certificate_bytes, ec.ECDSA(parsed.signature_hash_algorithm)
    )
    assert parsed.not_valid_before_utc < now < parsed.not_valid_after_utc
    with pytest.raises(x509.ExtensionNotFound):
        parsed.extensions.get_extension_for_class(x509.SubjectAlternativeName)
