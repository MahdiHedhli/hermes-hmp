#!/usr/bin/env python3
"""Per-run test-CA generator for the F1 acceptance build (T065; CS-6; research R12).

This is the "per-run test-CA generator used at acceptance build time" named by T065. It has one
job: mint a throwaway P-256 CA, and leaf certificates under it, entirely inside a scratch
directory the caller supplies. It never touches the repository, never reuses a previous run's
key material, and always records the CA's SHA-256 fingerprint next to it so the acceptance
build/run evidence can cite it (CS-6, and later T086's artifact scan for that exact fingerprint).

Two certificate shapes are produced, matching `tools/acceptance/interceptor.py`'s modes:

  * `generate_ca` + `generate_leaf`: a CA (`BasicConstraints(ca=True)`) and a leaf signed by it,
    for a **fresh key distinct from the pin** -- the `trusted-ca` mode, and the intercepted tail
    of `pass-then-intercept`. The one CA this whole acceptance run trusts (baked into the
    `HMP_ACCEPTANCE` build's `SecurityContext`, T079) is generated once here; interceptor.py
    reuses the same CA on disk via `load_or_generate_ca` rather than minting a second one, or the
    build and the interceptor process would trust/present two different CAs.
  * `generate_self_signed_leaf`: a self-signed, non-CA leaf over a fresh key -- the `wrong-key`
    mode. This mirrors the genuine instance's own certificate shape (TR-1: "The certificate is
    self-signed over the instance key"), just over the wrong key. No CA is involved at all.

Both leaf shapes set `keyUsage` (`digitalSignature`) and `extendedKeyUsage` (`serverAuth`)
explicitly. R0-D2b found that a test leaf without them was rejected by `dart:io` outright,
before the pin check under test ever ran; leaving them off here would silently produce a
leaf that some TLS stacks reject for the wrong reason.

**Custody (CS-6).** `generate_ca`, `generate_leaf` and `generate_self_signed_leaf` refuse to
write into any path inside this repository's working tree (`ScratchOnlyError`). Every private
key is written unencrypted (this material is worthless the moment the run ends; there is nothing
to protect it for) with owner-only file permissions where the platform supports it. Nothing here
is ever committed -- callers are responsible for pointing `--out-dir` at a scratch/tmp directory
and for deleting it once a run's evidence has been recorded.

TEST-ONLY. Every key and certificate this script produces is freshly generated per invocation
and is worthless outside the one acceptance run it was made for. Never reuse any key it writes
for anything else, and never point it at a real Hermes instance's key material.

CLI usage:
    python3 tools/acceptance/make_test_ca.py --out-dir /path/to/scratch/dir [--san ADDR ...]

Writes `ca_cert.pem`, `ca_key.pem`, `ca_fingerprint.txt`, `leaf_cert.pem`, `leaf_key.pem` into
`--out-dir`, and prints a JSON summary (including the CA's SHA-256 fingerprint) to stdout.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import datetime as dt
import hashlib
import ipaddress
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent

CA_CERT_FILENAME = "ca_cert.pem"
CA_KEY_FILENAME = "ca_key.pem"
FINGERPRINT_FILENAME = "ca_fingerprint.txt"

# Per-run material; short-lived on purpose. Clock skew tolerance is generous (5 minutes back)
# because these certs are used from a freshly generated `not_valid_before` on a possibly
# not-perfectly-synced test device.
_NOT_BEFORE_SKEW = dt.timedelta(minutes=5)
CA_VALIDITY = dt.timedelta(days=2)
LEAF_VALIDITY = dt.timedelta(days=2)

_DEFAULT_SAN_IPS = ("127.0.0.1", "::1")
_DEFAULT_SAN_DNS = ("localhost",)


class ScratchOnlyError(RuntimeError):
    """Raised when asked to write CA/key material inside the tracked repository tree (CS-6)."""


@dataclass(frozen=True)
class TestCA:
    key: ec.EllipticCurvePrivateKey
    certificate: x509.Certificate
    cert_path: Path
    key_path: Path
    fingerprint_sha256: str  # lowercase hex, no separators


@dataclass(frozen=True)
class TestLeaf:
    key: ec.EllipticCurvePrivateKey
    certificate: x509.Certificate
    cert_path: Path
    key_path: Path


def _require_scratch(out_dir: Path) -> Path:
    """Refuse to touch any path inside this repository's working tree (CS-6)."""
    resolved = Path(out_dir).resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        return resolved  # outside the repo tree: fine
    raise ScratchOnlyError(
        f"refusing to write CA/key material inside the repository tree: {resolved!s} is under "
        f"{REPO_ROOT!s}. Pass a scratch directory outside the repository (CS-6)."
    )


def _write_private_key(key: ec.EllipticCurvePrivateKey, path: Path) -> None:
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    with contextlib.suppress(OSError):
        path.chmod(0o600)  # best-effort; not every filesystem honours POSIX permissions


def _write_cert(cert: x509.Certificate, path: Path) -> None:
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def _fingerprint_sha256(cert: x509.Certificate) -> str:
    """Lowercase hex SHA-256 fingerprint of the whole DER certificate (CS-6 custody record;
    what T086's artifact scan later greps built artifacts for)."""
    return cert.fingerprint(hashes.SHA256()).hex()


def spki_sha256_fingerprint(cert: x509.Certificate) -> str:
    """52-char lowercase unpadded base32 of SHA-256(SPKI DER) -- the same construction as
    `iid`/`device_fp` (HMP_V1.md sec.2). Used by tests (and by evidence tooling) to compute the
    'pin' a given certificate's key would present, so a test can assert a leaf's key equals or
    differs from a chosen pin without hand-rolling the encoding again."""
    spki = cert.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    digest = hashlib.sha256(spki).digest()
    return base64.b32encode(digest).decode("ascii").lower().rstrip("=")


def _san_list(sans: Sequence[str] | None) -> x509.SubjectAlternativeName:
    names: list[x509.GeneralName] = []
    for value in sans or ():
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(value)))
        except ValueError:
            names.append(x509.DNSName(value))
    for ip in _DEFAULT_SAN_IPS:
        parsed = ipaddress.ip_address(ip)
        if not any(isinstance(n, x509.IPAddress) and n.value == parsed for n in names):
            names.append(x509.IPAddress(parsed))
    for dns in _DEFAULT_SAN_DNS:
        if not any(isinstance(n, x509.DNSName) and n.value == dns for n in names):
            names.append(x509.DNSName(dns))
    return x509.SubjectAlternativeName(names)


def _leaf_key_usage() -> x509.KeyUsage:
    # Explicit per R0-D2b: dart:io rejected a test leaf outright without these.
    return x509.KeyUsage(
        digital_signature=True,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=False,
        crl_sign=False,
        encipher_only=False,
        decipher_only=False,
    )


def generate_ca(out_dir: Path, *, common_name: str = "hmp-f1-acceptance-test-ca") -> TestCA:
    """Generate a fresh per-run test CA (P-256) into `out_dir` (scratch only; CS-6). Also writes
    `ca_fingerprint.txt` next to it."""
    resolved = _require_scratch(out_dir)
    resolved.mkdir(parents=True, exist_ok=True)

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = dt.datetime.now(dt.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _NOT_BEFORE_SKEW)
        .not_valid_after(now + CA_VALIDITY)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256())
    )

    cert_path = resolved / CA_CERT_FILENAME
    key_path = resolved / CA_KEY_FILENAME
    _write_cert(cert, cert_path)
    _write_private_key(key, key_path)

    fingerprint = _fingerprint_sha256(cert)
    (resolved / FINGERPRINT_FILENAME).write_text(fingerprint + "\n", encoding="ascii")

    return TestCA(
        key=key, certificate=cert, cert_path=cert_path, key_path=key_path,
        fingerprint_sha256=fingerprint,
    )


def load_ca(out_dir: Path) -> TestCA:
    """Load a previously generated test CA from `out_dir`. Reading does not require `out_dir` to
    be outside the repo (only *writing* new CA material does); a caller that already has one on
    disk in scratch is simply pointed back at it."""
    resolved = Path(out_dir).resolve()
    cert_path = resolved / CA_CERT_FILENAME
    key_path = resolved / CA_KEY_FILENAME
    cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise TypeError(f"{key_path}: expected a P-256 (EC) private key")
    return TestCA(
        key=key, certificate=cert, cert_path=cert_path, key_path=key_path,
        fingerprint_sha256=_fingerprint_sha256(cert),
    )


def load_or_generate_ca(out_dir: Path, *, common_name: str = "hmp-f1-acceptance-test-ca") -> TestCA:
    """Reuse the CA already in `out_dir` if one exists, else generate a fresh one there. This is
    what `interceptor.py` calls: the acceptance build bakes in the CA `make_test_ca.py` generated
    once at build time (T079), and the interceptor process started later for the same run must
    sign its `trusted-ca` leaf with that *same* CA, not mint a second, untrusted one."""
    out_dir = Path(out_dir)
    if (out_dir / CA_CERT_FILENAME).is_file() and (out_dir / CA_KEY_FILENAME).is_file():
        return load_ca(out_dir)
    return generate_ca(out_dir, common_name=common_name)


def generate_leaf(
    ca: TestCA,
    out_dir: Path,
    *,
    common_name: str = "hmp-f1-acceptance-test-leaf",
    sans: Sequence[str] | None = None,
    filename_prefix: str = "leaf",
) -> TestLeaf:
    """Generate a leaf certificate signed by `ca`, over a **fresh key distinct from the pin**
    (`trusted-ca` mode, and the intercepted tail of `pass-then-intercept`). `keyUsage` and
    `extendedKeyUsage` are set explicitly (R0-D2b)."""
    resolved = _require_scratch(out_dir)
    resolved.mkdir(parents=True, exist_ok=True)

    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = dt.datetime.now(dt.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca.certificate.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _NOT_BEFORE_SKEW)
        .not_valid_after(now + LEAF_VALIDITY)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(_leaf_key_usage(), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(_san_list(sans), critical=False)
        .sign(ca.key, hashes.SHA256())
    )

    cert_path = resolved / f"{filename_prefix}_cert.pem"
    key_path = resolved / f"{filename_prefix}_key.pem"
    _write_cert(cert, cert_path)
    _write_private_key(key, key_path)
    return TestLeaf(key=key, certificate=cert, cert_path=cert_path, key_path=key_path)


def generate_self_signed_leaf(
    out_dir: Path,
    *,
    common_name: str = "hmp-f1-acceptance-wrong-key-leaf",
    sans: Sequence[str] | None = None,
    filename_prefix: str = "wrongkey",
) -> TestLeaf:
    """A self-signed leaf over a fresh, wrong P-256 key (`wrong-key` mode). This mirrors TR-1's
    "self-signed over the instance key" shape exactly, just with a key that is not the pin. No CA
    is generated or consulted for this mode."""
    resolved = _require_scratch(out_dir)
    resolved.mkdir(parents=True, exist_ok=True)

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = dt.datetime.now(dt.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _NOT_BEFORE_SKEW)
        .not_valid_after(now + LEAF_VALIDITY)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(_leaf_key_usage(), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(_san_list(sans), critical=False)
        .sign(key, hashes.SHA256())
    )

    cert_path = resolved / f"{filename_prefix}_cert.pem"
    key_path = resolved / f"{filename_prefix}_key.pem"
    _write_cert(cert, cert_path)
    _write_private_key(key, key_path)
    return TestLeaf(key=key, certificate=cert, cert_path=cert_path, key_path=key_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--out-dir", required=True, type=Path,
        help="Scratch directory to write CA/leaf material into. Must be outside the repository "
             "working tree (CS-6); refused otherwise.",
    )
    parser.add_argument(
        "--san", action="append", default=[],
        help="Additional SAN entry (IP or hostname) for the leaf, e.g. a tailnet address passed "
             "at run time. Repeatable. Loopback and 'localhost' are always included too.",
    )
    parser.add_argument("--common-name", default="hmp-f1-acceptance-test-ca")
    args = parser.parse_args(argv)

    try:
        ca = generate_ca(args.out_dir, common_name=args.common_name)
        leaf = generate_leaf(ca, args.out_dir, sans=args.san)
    except ScratchOnlyError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    summary = {
        "ca_cert": str(ca.cert_path),
        "ca_key": str(ca.key_path),
        "ca_fingerprint_sha256": ca.fingerprint_sha256,
        "leaf_cert": str(leaf.cert_path),
        "leaf_key": str(leaf.key_path),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
