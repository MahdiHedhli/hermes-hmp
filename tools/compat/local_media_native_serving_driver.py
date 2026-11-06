"""Fresh private source materialization/entry for the native serving sample.

No native data operation runs until this controller and the exact copied entry
are independently reviewed. Source snapshots are measurement pins, not HMP
runtime eligibility or permission. Existing live homes/services are never selected.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
import tarfile
from pathlib import Path, PurePosixPath

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "_media_source_retained_commands", Path(__file__).with_name("native_sender_audit_fixture.py"))
commands = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = commands
_SPEC.loader.exec_module(commands)
_FIXTURE = Path(__file__).with_name("local_media_native_serving_fixture.py")
_MAX_ARCHIVE = 160 * 1024 * 1024  # Tar framing is separate from source bytes.
_MAX_SOURCE = 128 * 1024 * 1024
_MAX_REPORT = 64 * 1024 * 1024
_MAX_ENTRIES = 20000
_MAX_TREE = 8 * 1024 * 1024
_EXTENSIONS = frozenset((".py", ".json", ".toml", ".yaml", ".yml"))
_TRUE = frozenset(("native_database", "native_registry", "synthetic_routing_authorization",
    "synthetic_compatibility_result", "exact_authenticated_bytes_headers", "other_device_refused",
    "other_device_positive_control",
    "other_profile_refused", "file_change_after_first_serve_refused",
    "between_phase_authorization_change_refused", "message_change_before_fetch_refused",
    "revoked_device_refused", "listener_closed",
    "workers_joined", "borrowed_native_balanced", "native_database_close_observed",
    "source_unchanged", "selected_source_origins_checked", "synthetic_absent_linux_proc_probes",
    "fixture_public_os_metadata_allowed"))
_FALSE = frozenset(("actual_image_producer", "production_qualified", "t12_qualified"))
_ENTRY = '''import hashlib,importlib.util,json,os,sys
from pathlib import Path
if not (sys.flags.isolated == 1 and sys.flags.optimize == 0 and sys.dont_write_bytecode):
    raise RuntimeError("fixture_entry_flags_refused")
root=Path(sys.argv[1])
os.chdir(root)
path=root/"hmp/tools/compat/local_media_native_serving_fixture.py"
spec=importlib.util.spec_from_file_location("_private_native_media_sample",path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
report=module.run_fixture(root)
data=(json.dumps(report,sort_keys=True)+"\\n").encode()
if len(data)>64*1024*1024: raise RuntimeError("fixture_report_size_refused")
fd=os.open(root/"native-serving-report.json",os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,"wb") as stream: stream.write(data)
print(json.dumps({"schema":1,"completed":True,"report_sha256":hashlib.sha256(data).hexdigest()}))
'''


def _sha(value):
    return type(value) is str and re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value) is not None


def _read_private(path, limit):
    info = path.lstat()
    commands._require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
        info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o600
        and info.st_size <= limit)
    return path.read_bytes()


def extract_sources(archive, destination, commit, literal=None):
    """No extractall: bounded plain files/directories, no links or metadata effects."""
    commands._require(_sha(commit) and not destination.exists())
    _read_private(archive, _MAX_ARCHIVE)  # Refuse size/mode before tar parsing.
    destination.mkdir(mode=0o700)
    names, files, total = set(), {}, 0
    with tarfile.open(archive, "r:") as stream:
        for member in stream:
            commands._require(len(names) < _MAX_ENTRIES and len(member.name) <= 1024)
            name = PurePosixPath(member.name)
            normalized = str(name)
            commands._require(not name.is_absolute() and ".." not in name.parts and
                normalized not in (".", "") and normalized == member.name.rstrip("/") and
                normalized not in names)
            names.add(normalized)
            target = destination.joinpath(*name.parts)
            if member.isdir():
                target.mkdir(mode=0o700, parents=True, exist_ok=True)
                continue
            commands._require(member.isfile() and not member.issparse() and
                target.suffix in _EXTENSIONS and 0 <= member.size <= 4 * 1024 * 1024)
            if literal is not None:
                commands._require(normalized in literal and member.mode ==
                    (0o700 if literal[normalized][0] == "100755" else 0o600))
            total += member.size
            commands._require(total <= _MAX_SOURCE)
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            source = stream.extractfile(member)
            commands._require(source is not None)
            with source:
                data = source.read(member.size + 1)
            commands._require(len(data) == member.size)
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(data)
            files[normalized] = hashlib.sha256(data).hexdigest()
        commands._require(stream.pax_headers.get("comment") == commit)
    commands._require(bool(files))
    return files


def _git(root, repository, arguments, role, receipt, *, tree=False):
    argv = ["/usr/bin/env", "-i", "PATH=/usr/bin:/bin", "LANG=C", "LC_ALL=C",
        "HOME=" + str(root / "tool-home"), "GIT_CONFIG_NOSYSTEM=1",
        "GIT_CONFIG_GLOBAL=/dev/null", "GIT_OPTIONAL_LOCKS=0",
        "GIT_NO_REPLACE_OBJECTS=1", "GIT_NO_LAZY_FETCH=1", "GIT_TERMINAL_PROMPT=0",
        "GIT_ALLOW_PROTOCOL=", "GIT_PROTOCOL_FROM_USER=0", "/usr/bin/git",
        "-c", "protocol.allow=never", "-c", "core.fsmonitor=false", "-c", "tar.umask=0077",
        "-C", str(repository), *arguments]
    return commands._owned(argv, root, role, receipt, stdout_limit=_MAX_TREE if tree else 65536)



def literal_sources(raw, commit):
    """Bound literal tree entries; selected source modes and Git blob identities."""
    commands._require(type(raw) is bytes and 0 < len(raw) <= _MAX_TREE and raw.endswith(b"\0"))
    rows = raw[:-1].split(b"\0")
    commands._require(len(rows) <= 65536)
    selected = {}
    for row in rows:
        header, separator, name = row.partition(b"\t")
        commands._require(separator == b"\t" and 0 < len(name) <= 1024)
        fields = header.split(b" ")
        commands._require(len(fields) == 3)
        mode, kind, oid = fields
        name = name.decode("utf-8", "strict")
        path = PurePosixPath(name)
        commands._require(not path.is_absolute() and ".." not in path.parts and str(path) == name)
        if path.suffix not in _EXTENSIONS:
            continue
        object_id = oid.decode("ascii")
        commands._require(mode in (b"100644", b"100755") and kind == b"blob" and
            _sha(object_id) and len(object_id) == len(commit) and name not in selected and
            len(selected) < _MAX_ENTRIES)
        selected[name] = (mode.decode("ascii"), object_id)
    commands._require(bool(selected))
    return selected


def verify_literal_sources(destination, inventory, expected):
    commands._require(set(inventory) == set(expected))
    for name, (_, object_id) in expected.items():
        data = _read_private(destination / name, 4 * 1024 * 1024)
        payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        digest = (hashlib.sha1(payload, usedforsecurity=False).hexdigest()
                  if len(object_id) == 40 else hashlib.sha256(payload).hexdigest())
        commands._require(digest == object_id)

def _no_custom_tar(root, repository, label, receipt):
    role = label + "_tar_config"
    try:
        _git(root, repository, ["config", "--includes", "--get-all", "tar.tar.command"],
             role, receipt)
    except commands.NativeSenderFixtureError:
        row = receipt["commands"][-1]
        commands._require(row["role"] == role and row.get("wait_known") is True and
            row.get("returncode") == 1 and not row.get("settlement_only_used", False) and
            commands._read(root / (role + ".stdout")) == b"" and
            commands._read(root / (role + ".stderr")) == b"")
        row["expected_absent_config"] = True
        commands._save(root / "receipt.json", receipt)
        return
    raise commands.NativeSenderFixtureError()


def validate_report(report, native, hmp, executable_sha):
    expected = _TRUE | _FALSE | {"schema", "native_acquires", "native_releases",
        "descriptor_records_retained", "audit_denials", "scoped_native_sweep",
        "expected_absent_proc_probes", "os_metadata_sha256", "os_metadata_reads", "own_fd_listings",
        "native_source_hashes", "hmp_source_hashes", "runtime_executable_sha256"}
    commands._require(type(report) is dict and set(report) == expected and
        type(report.get("schema")) is int and
        report["schema"] == 1 and all(report.get(k) is True for k in _TRUE) and
        all(report.get(k) is False for k in _FALSE))
    for key in ("native_acquires", "native_releases", "descriptor_records_retained",
                "audit_denials", "scoped_native_sweep", "expected_absent_proc_probes",
                "os_metadata_reads", "own_fd_listings"):
        commands._require(type(report.get(key)) is int)
    commands._require(type(report.get("os_metadata_sha256")) is str and
        re.fullmatch(r"[0-9a-f]{64}", report["os_metadata_sha256"]) is not None and
        1 <= report["os_metadata_reads"] <= 8 and 1 <= report["own_fd_listings"] <= 4096 and
        report["expected_absent_proc_probes"] > 0 and
        report["native_acquires"] > 0 and
        report["native_acquires"] == report["native_releases"] and
        0 <= report["descriptor_records_retained"] <= 8 and
        report["audit_denials"] == report["scoped_native_sweep"] == 0 and
        report.get("native_source_hashes") == native and report.get("hmp_source_hashes") == hmp and
        report.get("runtime_executable_sha256") == executable_sha)


def run_fixture(root, native_repository, native_commit):
    commands._require(type(root) is type(Path()) and root.is_absolute() and root.resolve() == root)
    info = root.stat()
    commands._require(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700 and
                      not any(root.iterdir()) and _sha(native_commit))
    original_umask = os.umask(0o077)
    try:
        (root / "tool-home").mkdir(mode=0o700)
        receipt = {"schema": 1, "commands": [], "native_commit": native_commit,
                   "production_qualified": False,
                   "fixture_source_sha256": commands._digest(_FIXTURE)}
        commands._save(root / "receipt.json", receipt)
        version = _git(root, _ROOT, ["--version"], "git_version", receipt).decode().strip()
        match = re.fullmatch(r"git version (\d+)\.(\d+)\.(\d+)(?:[ .-].*)?", version)
        commands._require(match is not None and tuple(map(int, match.groups())) >= (2, 54, 0))
        receipt["git_version"] = version
        hmp_commit = _git(root, _ROOT, ["rev-parse", "HEAD"], "hmp_head", receipt).decode().strip()
        commands._require(_sha(hmp_commit))
        receipt["hmp_commit"] = hmp_commit
        copies = {}
        for label, repository, commit in (("native", native_repository, native_commit),
                                           ("hmp", _ROOT, hmp_commit)):
            kind = _git(root, repository, ["cat-file", "-t", commit], label + "_kind", receipt)
            commands._require(kind == b"commit\n")
            _no_custom_tar(root, repository, label, receipt)
            manifest = literal_sources(_git(root, repository,
                ["ls-tree", "-r", "-z", "--full-tree", commit], label + "_tree", receipt,
                tree=True), commit)
            archive = root / (label + ".tar")
            commands._require(not archive.exists())
            _git(root, repository, ["archive", "--format=tar", "--output=" + str(archive), commit,
                "--", "*.py", "*.json", "*.toml", "*.yaml", "*.yml"], label + "_archive", receipt)
            copies[label] = extract_sources(archive, root / label, commit, manifest)
            verify_literal_sources(root / label, copies[label], manifest)
        commands._require({"hermes_state.py", "hermes_state_registry.py"} <= set(copies["native"]))
        commands._require({"server/hmp_plugin/__init__.py", "server/tests/unit/__init__.py",
            "server/tests/unit/test_s5_media_fetch.py", "server/tests/unit/test_s4_descriptors.py",
            "server/tests/unit/hmp_kit.py", "tools/compat/local_media_native_serving_fixture.py"}
            <= set(copies["hmp"]))
        copied_fixture = root / "hmp/tools/compat/local_media_native_serving_fixture.py"
        commands._require(commands._digest(copied_fixture) == receipt["fixture_source_sha256"])
        commands._save(root / "source-manifest.json", copies)
        entry = root / "entry.py"
        fd = os.open(entry, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as output:
            output.write(_ENTRY)
        executable = Path(sys.executable).absolute()  # Preserve the selected venv path.
        executable_sha = commands._digest(executable.resolve())
        raw = commands._owned(["/usr/bin/env", "-i", "PATH=/usr/bin:/bin", "LANG=C", "LC_ALL=C",
            "HOME=" + str(root / "user-home"), "HERMES_HOME=" + str(root / "home"),
            "HERMES_RUNTIME_DIR=" + str(root / "runtime"), str(executable), "-I", "-B", str(entry),
            str(root)], root, "native_serving", receipt)
        marker = json.loads(raw, object_pairs_hook=commands._pairs)
        commands._require(type(marker) is dict and set(marker) ==
                          {"schema", "completed", "report_sha256"} and
                          type(marker["schema"]) is int and marker["schema"] == 1 and
                          marker["completed"] is True)
        data = _read_private(root / "native-serving-report.json", _MAX_REPORT)
        commands._require(hashlib.sha256(data).hexdigest() == marker["report_sha256"])
        report = json.loads(data, object_pairs_hook=commands._pairs)
        validate_report(report, copies["native"], copies["hmp"], executable_sha)
        for label, inventory in copies.items():
            commands._require(all(commands._digest(root / label / name) == value
                                  for name, value in inventory.items()))
        commands._require(commands._digest(executable.resolve()) == executable_sha and
            commands._digest(_FIXTURE) == receipt["fixture_source_sha256"])
        receipt.update(completed=True, report_sha256=marker["report_sha256"],
                       runtime_executable_sha256=executable_sha, observation=report)
        commands._save(root / "receipt.json", receipt)
        return receipt
    finally:
        os.umask(original_umask)
