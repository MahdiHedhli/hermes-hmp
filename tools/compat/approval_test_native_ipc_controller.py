"""Run the AT1 synthetic macOS IPC/TLS fixture against a content-bound export.

No live Hermes home, automatic dependency installation, provider setup, retries,
process termination, store publication or physical device action is performed.
A caller must review the export's provenance and supply its exact manifest hash.
Observation timeouts retain the same child; they do not restart or kill it.
"""

import argparse
import hashlib
import json
import os
import pwd
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--python", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("this fixture currently qualifies macOS only")
    os.umask(0o077)
    sample = args.sample.resolve()
    # Keep the venv launcher path: resolving its symlink can discard pyvenv.cfg.
    if not args.python.is_absolute():
        parser.error("absolute prepared interpreter path required")
    python = args.python.absolute()
    homes = {
        (Path.home() / ".hermes").resolve(),
        (Path(pwd.getpwuid(os.geteuid()).pw_dir) / ".hermes").resolve(),
    }
    if any(sample == home or home in sample.parents for home in homes):
        parser.error("refusing a live-home source")
    manifest_path = sample / "source-manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        parser.error("regular exported source manifest required")
    if digest(manifest_path) != args.manifest_sha256:
        parser.error("source manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text())
    if set(manifest) != {"native", "hmp"}:
        parser.error("native/hmp source groups required")
    if not python.is_file():
        parser.error("prepared interpreter required; no install fallback")
    fixture = Path(__file__).with_name("approval_test_native_ipc_fixture.py")
    fixture_hash = digest(fixture)
    controller_hash = digest(Path(__file__))

    def verify():
        count = 0
        for group, files in manifest.items():
            for name, expected in files.items():
                relative = Path(name)
                if (
                    relative.is_absolute()
                    or not relative.parts
                    or any(part in ("", ".", "..") for part in relative.parts)
                ):
                    raise ValueError("unsafe manifest path")
                path = sample / group / relative
                if (
                    not path.resolve().is_relative_to(sample / group)
                    or not stat.S_ISREG(path.lstat().st_mode)
                    or path.is_symlink()
                    or digest(path) != expected
                ):
                    raise ValueError("exported source mismatch")
                count += 1
        if digest(manifest_path) != args.manifest_sha256 or digest(fixture) != fixture_hash:
            raise ValueError("fixture or manifest changed")
        return count

    count = verify()
    root = Path(tempfile.mkdtemp(prefix="at1ipc-", dir="/private/tmp"))
    root.chmod(0o700)
    (root / "tmp").mkdir(mode=0o700)
    script = root / "fixture.py"
    shutil.copyfile(fixture, script)
    script.chmod(0o600)
    if digest(script) != fixture_hash:
        raise ValueError("executed fixture copy mismatch")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    receipt_path = root / "controller.json"
    receipt = {
        "stage": "prepared",
        "root": str(root),
        "startedUTC": datetime.now(UTC).isoformat(),
        "sourceCount": count,
        "manifestSHA256": args.manifest_sha256,
        "fixtureSHA256": fixture_hash,
        "controllerSHA256": controller_hash,
        "pythonSHA256": digest(python.resolve()),
        "pythonLauncher": str(python),
        "platform": sys.platform,
        "productionQualified": False,
        "physicalQualified": False,
        "nativeSource": "ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df",
        "hmpSource": "6796bfbb45177f86125635ff801fbc80b034a226",
        "sourceIdentityNote": (
            "commit labels require independent export provenance; file hashes are verified here"
        ),
    }

    def save():
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        receipt_path.chmod(0o600)

    save()
    print(json.dumps({"root": str(root), "receipt": str(receipt_path)}), flush=True)
    env = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "HOME": str(root / "user-home"),
        "TMPDIR": str(root / "tmp"),
        "HERMES_HOME": str(root / "home"),
        "HERMES_RUNTIME_DIR": str(root / "runtime"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "HERMES_DISABLE_LAZY_INSTALLS": "1",
        "CI": "true",
    }
    with (root / "child.log").open("w") as log:
        (root / "child.log").chmod(0o600)
        child = subprocess.Popen(
            [str(python), "-I", "-B", str(script), str(root), str(sample), str(port), "matrix"],
            cwd=root,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            receipt.update(stage="running", pid=child.pid)
            save()
            while True:
                try:
                    code = child.wait(timeout=30)
                    break
                except subprocess.TimeoutExpired:
                    receipt.update(
                        stage="observing-same-child", observedUTC=datetime.now(UTC).isoformat()
                    )
                    save()
                    print(json.dumps({"stage": receipt["stage"], "pid": child.pid}), flush=True)
        finally:
            # Diagnostic/observer failure never abandons the real child or
            # turns an observation timeout into a restart/termination.
            code = child.wait()
    if digest(script) != fixture_hash or digest(Path(__file__)) != controller_hash:
        raise ValueError("executed fixture or controller changed")
    receipt.update(
        stage="terminal",
        exitCode=code,
        finishedUTC=datetime.now(UTC).isoformat(),
        sourcesUnchanged=verify() == count,
        childLogSHA256=digest(root / "child.log"),
    )
    if (root / "report.json").is_file():
        report = json.loads((root / "report.json").read_text())
        receipt.update(
            reportSHA256=digest(root / "report.json"),
            observedPhase=report.get("phase"),
            boundedIntegrationPassed=code == 0 and report.get("phase") == "complete",
        )
    save()
    print(
        json.dumps(
            {
                "receipt": str(receipt_path),
                "exitCode": code,
                "passed": receipt.get("boundedIntegrationPassed", False),
            }
        ),
        flush=True,
    )
    return 0 if receipt.get("boundedIntegrationPassed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
