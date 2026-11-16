"""Evidence scope and actual CMS roundtrip with fresh test-only recipient keys."""

import datetime
import hashlib
import importlib.util
import io
import os
import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509.oid import NameOID

_SPEC = importlib.util.spec_from_file_location(
    "linux_evidence", Path(__file__).parents[1] / "native_presentation_linux_evidence.py"
)
module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(module)


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "private"
    path.mkdir(mode=0o700)
    report = path / "private-failure.json"
    report.write_text('{"synthetic":"private-fixture-only"}')
    report.chmod(0o600)
    return path


def test_allowlist_excludes_native_home_keys_and_arbitrary_files(root):
    (root / "unrelated.txt").write_text("synthetic-excluded")
    (root / "home").mkdir()
    (root / "home/key.pem").write_text("synthetic-excluded-key")
    assert module.selected(root) == [root / "private-failure.json"]


@pytest.mark.parametrize("fault", ["symlink", "hardlink", "public-mode"])
def test_selected_file_boundary_failures_refuse(root, fault):
    report = root / "private-failure.json"
    if fault == "symlink":
        other = root.parent / "outside"
        other.write_text("synthetic-outside")
        report.unlink()
        report.symlink_to(other)
    elif fault == "hardlink":
        os.link(report, root / "alias")
    else:
        report.chmod(0o644)
    with pytest.raises(RuntimeError, match="synthetic_evidence_scope_refused"):
        module.selected(root)


def test_directories_are_not_recursed_and_receipt_is_unique(root):
    source = root / "sources"
    source.mkdir(mode=0o700)
    path = source / "receipt.json"
    path.write_text("{}")
    path.chmod(0o600)
    (source / "nested").mkdir()
    (source / "nested/private.stderr").write_text("synthetic-excluded")
    assert module.selected(root).count(path) == 1
    assert len(module.selected(root)) == 2


def test_actual_cms_roundtrip_exports_only_ciphertext_and_decrypts_selected_bytes(
    root, tmp_path, monkeypatch
):
    # Exercise crypto only under explicit simulated bootstrap flags; not isolation qualification.
    monkeypatch.setattr(
        module,
        "sys",
        SimpleNamespace(flags=SimpleNamespace(isolated=1, optimize=0), dont_write_bytecode=True),
    )
    # Fresh unrelated test key; production evidence recipient private key is never read.
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic Test Only")])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    directory = tmp_path / "tools"
    directory.mkdir(mode=0o700)
    certificate = directory / "native_presentation_fixture_evidence.crt"
    certificate.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    shutil.copyfile(
        Path(module.__file__).with_name("native_sender_audit_fixture.py"),
        directory / "native_sender_audit_fixture.py",
    )
    monkeypatch.setattr(
        module, "__file__", str(directory / "native_presentation_linux_evidence.py")
    )
    monkeypatch.setattr(module, "_CERT_SHA", hashlib.sha256(certificate.read_bytes()).hexdigest())
    github_output = tmp_path / "synthetic-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))
    result = module.encrypt(root)
    cipher = root / "synthetic-diagnostics.cms"
    assert result["encrypted"] is True and result["rawUploaded"] is False
    assert cipher.stat().st_mode & 0o777 == 0o600
    assert github_output.read_text() == "ciphertext=" + str(cipher) + "\n"
    plaintext = pkcs7.pkcs7_decrypt_der(cipher.read_bytes(), cert, key, [])
    with zipfile.ZipFile(io.BytesIO(plaintext)) as bundle:
        assert bundle.namelist() == ["private-failure.json"]
        assert bundle.read("private-failure.json") == b'{"synthetic":"private-fixture-only"}'


def test_wrong_public_certificate_pin_refuses_before_bundle(root, monkeypatch):
    monkeypatch.setattr(
        module,
        "sys",
        SimpleNamespace(flags=SimpleNamespace(isolated=1, optimize=0), dont_write_bytecode=True),
    )
    monkeypatch.setattr(module, "_CERT_SHA", "a" * 64)
    with pytest.raises(RuntimeError, match="synthetic_evidence_scope_refused"):
        module.encrypt(root)
    assert not (root / "private-diagnostics.zip").exists()
