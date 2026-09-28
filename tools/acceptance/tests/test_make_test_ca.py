"""Tests for tools/acceptance/make_test_ca.py (T065)."""

from __future__ import annotations

from pathlib import Path

import make_test_ca
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID


def test_generate_ca_writes_files_and_fingerprint(tmp_path: Path) -> None:
    ca = make_test_ca.generate_ca(tmp_path)

    assert ca.cert_path.is_file()
    assert ca.key_path.is_file()
    fingerprint_file = tmp_path / make_test_ca.FINGERPRINT_FILENAME
    assert fingerprint_file.is_file()
    assert fingerprint_file.read_text().strip() == ca.fingerprint_sha256

    # A SHA-256 fingerprint is 32 bytes -> 64 lowercase hex chars.
    assert len(ca.fingerprint_sha256) == 64
    assert ca.fingerprint_sha256 == ca.fingerprint_sha256.lower()
    int(ca.fingerprint_sha256, 16)  # raises if not valid hex

    # basicConstraints CA:true.
    from cryptography import x509

    bc = ca.certificate.extensions.get_extension_for_class(x509.BasicConstraints).value
    assert bc.ca is True


def test_generate_ca_refuses_inside_repo() -> None:
    inside_repo = make_test_ca.REPO_ROOT / "tools" / "acceptance" / "_should_never_exist"
    with pytest.raises(make_test_ca.ScratchOnlyError):
        make_test_ca.generate_ca(inside_repo)
    assert not inside_repo.exists()


def test_generate_leaf_refuses_inside_repo(tmp_path: Path) -> None:
    ca = make_test_ca.generate_ca(tmp_path)
    inside_repo = make_test_ca.REPO_ROOT / "tools" / "acceptance" / "_should_never_exist_leaf"
    with pytest.raises(make_test_ca.ScratchOnlyError):
        make_test_ca.generate_leaf(ca, inside_repo)
    assert not inside_repo.exists()


def test_generate_self_signed_leaf_refuses_inside_repo() -> None:
    inside_repo = make_test_ca.REPO_ROOT / "tools" / "acceptance" / "_should_never_exist_wrongkey"
    with pytest.raises(make_test_ca.ScratchOnlyError):
        make_test_ca.generate_self_signed_leaf(inside_repo)
    assert not inside_repo.exists()


def test_generate_leaf_is_signed_by_ca_with_required_extensions(tmp_path: Path) -> None:
    from cryptography import x509

    ca = make_test_ca.generate_ca(tmp_path)
    leaf = make_test_ca.generate_leaf(ca, tmp_path, sans=["203.0.113.5", "leaf.example.invalid"])

    assert leaf.certificate.issuer == ca.certificate.subject

    # The leaf's key must differ from the CA's key (never sign with, or reuse, the CA's own key
    # as a "leaf" -- these are deliberately distinct keys).
    ca_pub = ca.key.public_key().public_numbers()
    leaf_pub = leaf.key.public_key().public_numbers()
    assert (ca_pub.x, ca_pub.y) != (leaf_pub.x, leaf_pub.y)

    # Signature verifies under the CA's public key (R0-D2b: this is a genuine chain, not just
    # two unrelated self-signed certs).
    ca.key.public_key().verify(
        leaf.certificate.signature,
        leaf.certificate.tbs_certificate_bytes,
        ec.ECDSA(leaf.certificate.signature_hash_algorithm),
    )

    bc = leaf.certificate.extensions.get_extension_for_class(x509.BasicConstraints).value
    assert bc.ca is False

    ku = leaf.certificate.extensions.get_extension_for_class(x509.KeyUsage).value
    assert ku.digital_signature is True
    assert ku.key_encipherment is False
    assert ku.key_agreement is False

    eku = leaf.certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    assert ExtendedKeyUsageOID.SERVER_AUTH in list(eku)

    san = leaf.certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    dns_names = san.get_values_for_type(x509.DNSName)
    assert "leaf.example.invalid" in dns_names
    assert "localhost" in dns_names  # default always included


def test_generate_self_signed_leaf_is_self_issued_with_required_extensions(tmp_path: Path) -> None:
    from cryptography import x509

    leaf = make_test_ca.generate_self_signed_leaf(tmp_path)

    assert leaf.certificate.issuer == leaf.certificate.subject

    leaf.key.public_key().verify(
        leaf.certificate.signature,
        leaf.certificate.tbs_certificate_bytes,
        ec.ECDSA(leaf.certificate.signature_hash_algorithm),
    )

    bc = leaf.certificate.extensions.get_extension_for_class(x509.BasicConstraints).value
    assert bc.ca is False

    ku = leaf.certificate.extensions.get_extension_for_class(x509.KeyUsage).value
    assert ku.digital_signature is True

    eku = leaf.certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    assert ExtendedKeyUsageOID.SERVER_AUTH in list(eku)


def test_load_or_generate_ca_reuses_existing(tmp_path: Path) -> None:
    first = make_test_ca.load_or_generate_ca(tmp_path)
    second = make_test_ca.load_or_generate_ca(tmp_path)
    assert first.fingerprint_sha256 == second.fingerprint_sha256
    assert first.certificate.public_bytes(encoding=make_test_ca.serialization.Encoding.DER) == (
        second.certificate.public_bytes(encoding=make_test_ca.serialization.Encoding.DER)
    )


def test_load_or_generate_ca_generates_fresh_each_time_in_a_new_dir(tmp_path: Path) -> None:
    a = make_test_ca.load_or_generate_ca(tmp_path / "run-a")
    b = make_test_ca.load_or_generate_ca(tmp_path / "run-b")
    assert a.fingerprint_sha256 != b.fingerprint_sha256


def test_spki_sha256_fingerprint_matches_iid_construction(tmp_path: Path) -> None:
    import base64
    import hashlib

    from cryptography.hazmat.primitives import serialization

    leaf = make_test_ca.generate_self_signed_leaf(tmp_path)
    fp = make_test_ca.spki_sha256_fingerprint(leaf.certificate)

    # 52-char lowercase unpadded base32 (HMP_V1.md sec.2: iid/device_fp construction).
    assert len(fp) == 52
    assert fp == fp.lower()
    assert "=" not in fp

    spki = leaf.key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    expected = base64.b32encode(hashlib.sha256(spki).digest()).decode("ascii").lower().rstrip("=")
    assert fp == expected


def test_different_keys_give_different_fingerprints(tmp_path: Path) -> None:
    leaf_a = make_test_ca.generate_self_signed_leaf(tmp_path, filename_prefix="a")
    leaf_b = make_test_ca.generate_self_signed_leaf(tmp_path, filename_prefix="b")
    assert make_test_ca.spki_sha256_fingerprint(leaf_a.certificate) != (
        make_test_ca.spki_sha256_fingerprint(leaf_b.certificate)
    )
