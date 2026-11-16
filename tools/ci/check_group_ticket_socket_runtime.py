"""Capture exact Linux synthetic-component evidence; never import native Hermes."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import socket
import stat
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
FILES = tuple(
    f"server/{folder}/{name}.py"
    for name in ("group_operation_ledger", "group_ticket_codec", "group_ticket_socket")
    for folder in ("hmp_plugin", "tests/unit")
)
# Test files have their normal test_ prefix, unlike the production modules.
FILES = tuple(path.replace("tests/unit/", "tests/unit/test_") for path in FILES)
EXPECTED = {
    "test_group_operation_ledger": 67,
    "test_group_ticket_codec": 85,
    "test_group_ticket_socket": 53,
}


def require(value: bool) -> None:
    if not value:
        raise SystemExit("group socket component evidence refused")


def hashes() -> dict[str, str]:
    result = {}
    for name in FILES:
        path = ROOT / name
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_size <= 1_048_576)
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def save(path: Path, value: dict) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def coverage(result: Path) -> tuple[dict[str, int], str]:
    info = result.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_size <= 4 * 1024 * 1024)
    cases = ET.parse(result).findall(".//testcase")
    counts = dict.fromkeys(EXPECTED, 0)
    kernel_case = False
    identities = set()
    for case in cases:
        identity = (case.attrib.get("classname", ""), case.attrib.get("name", ""))
        require(all(identity) and identity not in identities)
        identities.add(identity)
        name = case.attrib.get("classname", "").rsplit(".", 1)[-1]
        require(
            name in counts
            and all(case.find(tag) is None for tag in ("failure", "error", "skipped"))
        )
        counts[name] += 1
        kernel_case |= (
            name == "test_group_ticket_socket"
            and case.attrib.get("name")
            == "test_actual_kernel_peer_uid_fixed_request_and_known_close"
        )
    require(counts == EXPECTED and kernel_case)
    return counts, hashlib.sha256(result.read_bytes()).hexdigest()


def main() -> None:
    require(len(sys.argv) == 4 and sys.argv[1] in {"before", "after"})
    phase, minor, output = sys.argv[1:]
    require(sys.platform == "linux" and hasattr(socket, "SO_PEERCRED"))
    require(platform.python_implementation() == "CPython" and sys.flags.optimize == 0)
    require(
        minor in {"3.11", "3.14"} and ".".join(map(str, sys.version_info[:2])) == minor
    )
    head = os.environ.get("GITHUB_SHA", "")
    require(re.fullmatch("[a-f0-9]{40}", head) is not None)
    directory = Path(output)
    require(directory.is_absolute())
    if phase == "before":
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        (directory / "home").mkdir(mode=0o700)
        (directory / "runtime").mkdir(mode=0o700)
    require(directory.is_dir() and not directory.is_symlink())
    record = {
        "phase": phase,
        "head": head,
        "python": sys.version,
        "minor": minor,
        "platform": sys.platform,
        "machine": platform.machine(),
        "kernelPeerAPI": "SO_PEERCRED",
        "sourceHashes": hashes(),
        "scope": "Synthetic component only; no native gateway/real ticket/phone qualification",
        "physicalQualified": False,
        "releaseQualified": False,
    }
    if phase == "after":
        before = json.loads((directory / "before.json").read_text())
        require(
            before["head"] == head
            and before["minor"] == minor
            and before["sourceHashes"] == record["sourceHashes"]
        )
        counts, junit_digest = coverage(directory / "result.xml")
        record.update(
            testCounts=counts,
            sourceUnchanged=True,
            kernelCasePassed=True,
            junitSHA256=junit_digest,
        )
    save(directory / (phase + ".json"), record)
    print(
        json.dumps(
            {
                "phase": phase,
                "head": head,
                "minor": minor,
                "platform": sys.platform,
                "sourceFiles": len(FILES),
                "cases": record.get("testCounts"),
                "nativeGatewayTested": False,
            }
        )
    )


if __name__ == "__main__":
    main()
