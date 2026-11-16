"""Encrypt only allowlisted synthetic CI diagnostics; never upload raw artifacts.

The one-purpose recipient certificate is public. Its private key remains on the
coordinator's machine. This certificate is not used for TLS/authentication/grants.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
import sys
import zipfile
from pathlib import Path

_CERT_SHA = "9628b0c4697faf81d375974ae4fbebe01cc9ffa3794eba1824f4936ff744138e"
_FILES = (
    "permission-normalization.json",
    "preparation-receipt.json",
    "private-failure.json",
    "prepared.json",
    "runtime-manifest.json",
    "sources/receipt.json",
    "sources/source-manifest.json",
    "run/receipt.json",
    "run/curated-summary.json",
    "run/matrix/report.json",
    "run/matrix/settlement.json",
    "run/matrix/unresolved-teardown.json",
    "run/matrix/progress.json",
    "run/mutation/report.json",
    "run/mutation/settlement.json",
    "run/mutation/unresolved-teardown.json",
    "run/mutation/progress.json",
)
_DIRECTORIES = ("sources", "preparation-commands", "image-commands", "run/docker-cli")


def require(value):
    if value is not True:
        raise RuntimeError("synthetic_evidence_scope_refused")


def selected(root):
    require(root.is_absolute() and root.resolve(strict=True) == root)
    info = root.lstat()
    require(
        stat.S_ISDIR(info.st_mode)
        and info.st_uid == os.geteuid()
        and stat.S_IMODE(info.st_mode) == 0o700
    )
    paths = [root / name for name in _FILES if (root / name).exists()]
    for name in _DIRECTORIES:
        directory = root / name
        if directory.exists():
            require(directory.resolve(strict=True) == directory and directory.is_dir())
            for item in directory.iterdir():
                if item.name == "receipt.json" or item.suffix in (".stdout", ".stderr"):
                    paths.append(item)
    total = 0
    require(len(paths) <= 4000)
    for path in paths:
        info = path.lstat()
        require(path.resolve(strict=True) == path and path.is_relative_to(root))
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid())
        require(stat.S_IMODE(info.st_mode) == 0o600 and info.st_size <= 32 * 1024**2)
        total += info.st_size
        require(total <= 128 * 1024**2)
    require(bool(paths))
    return sorted(set(paths))


def encrypt(root):
    require(sys.flags.isolated == 1 and sys.dont_write_bytecode and sys.flags.optimize == 0)
    os.umask(0o077)
    files = selected(root)
    certificate = Path(__file__).with_name("native_presentation_fixture_evidence.crt")
    require(hashlib.sha256(certificate.read_bytes()).hexdigest() == _CERT_SHA)
    bundle = root / "private-diagnostics.zip"
    with zipfile.ZipFile(bundle, "x", compression=zipfile.ZIP_DEFLATED) as output:
        for path in files:
            output.write(path, path.relative_to(root).as_posix())
    bundle.chmod(0o600)
    script = Path(__file__).with_name("native_sender_audit_fixture.py")
    spec = importlib.util.spec_from_file_location("_evidence_owned_cli", script)
    commands = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(commands)
    directory = root / "encryption-command"
    directory.mkdir(mode=0o700)
    cipher = root / "synthetic-diagnostics.cms"
    commands._owned(
        [
            "/usr/bin/openssl",
            "cms",
            "-encrypt",
            "-binary",
            "-aes256",
            "-outform",
            "DER",
            "-in",
            str(bundle),
            "-out",
            str(cipher),
            str(certificate),
        ],
        directory,
        "encrypt",
        {"commands": []},
        wait_timeout=120,
    )
    info = cipher.lstat()
    require(
        stat.S_ISREG(info.st_mode)
        and info.st_uid == os.geteuid()
        and 0 < info.st_size <= 129 * 1024**2
    )
    require(stat.S_IMODE(info.st_mode) == 0o600)
    result = {
        "encrypted": True,
        "selectedFiles": len(files),
        "certificateSHA256": _CERT_SHA,
        "ciphertextSHA256": hashlib.sha256(cipher.read_bytes()).hexdigest(),
        "rawUploaded": False,
        "qualificationClaimed": False,
    }
    (root / "encryption-receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    destination = os.environ.get("GITHUB_OUTPUT")
    if destination:
        with open(destination, "a", encoding="utf-8") as stream:
            stream.write("ciphertext=" + str(cipher) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(encrypt(args.root)), flush=True)
    except BaseException as exc:
        print(
            json.dumps({"encrypted": False, "errorType": type(exc).__name__, "rawUploaded": False}),
            flush=True,
        )
        raise SystemExit(1) from None
