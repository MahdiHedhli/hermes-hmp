"""Fixed-install synthetic broker harness, NOT a production admission token.

The verifier/interpreter origin and expected manifest digest are trusted startup
inputs. The OS loader/system-library policy and absence of concurrent installation
mutation are explicit premises, not measured loaded-library or sandbox claims.
This entry never installs a service, connects, stages input, sends GO or releases
started reservations. An unknown started owner stays retained until supervision.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import json
import os
import stat
import sys
import time
import types
from pathlib import Path

_MAX_MANIFEST = 8 * 1024 * 1024
_MAX_ENTRIES = 20_000
_MAX_FILE = 128 * 1024 * 1024
_MAX_TOTAL = 2 * 1024 * 1024 * 1024
_NAMESPACE = "_hmp_presentation_broker"
_NATIVE_POLICIES = {
    "darwin": ("darwin-system-loader-trust", ["/usr/lib", "/System/Library"]),
    "linux": ("linux-system-loader-trust", ["/lib", "/lib64", "/usr/lib", "/usr/lib64"]),
}
_RETAINED: list[object] = []


class BootstrapError(Exception):
    def __init__(self):
        super().__init__("BI1_BROKER_BOOTSTRAP_REFUSED")


def _require(value: bool) -> None:
    if value is not True:
        raise BootstrapError


def _hex(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _environment_current() -> None:
    allowed = {"LANG", "LC_ALL", "LC_CTYPE"}
    if sys.platform == "darwin":
        allowed.add("__CF_USER_TEXT_ENCODING")
        value = os.environ.get("__CF_USER_TEXT_ENCODING")
        if value is not None:
            _require(0 < len(value) <= 128)
            parts = value.split(":")
            _require(len(parts) == 3 and all(p and len(p) <= 16 for p in parts))
            numbers = []
            for part in parts:
                if part.startswith("0x"):
                    digits = part[2:]
                    _require(0 < len(digits) <= 8
                             and all(c in "0123456789abcdefABCDEF" for c in digits))
                    number = int(digits, 16)
                else:
                    _require(part == "0" or (part[0] in "123456789"
                             and all(c in "0123456789" for c in part)))
                    number = int(part, 10)
                _require(0 <= number < (1 << 32))
                numbers.append(number)
            _require(numbers[0] == os.geteuid())
    _require(set(os.environ) <= allowed)
    _require(os.environ.get("LANG") == "C" and os.environ.get("LC_ALL") == "C")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _pairs(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _keys(value: object, keys: set[str]) -> None:
    _require(type(value) is dict and set(value) == keys)


def _absolute(value: object, *, exists: bool = True) -> str:
    _require(type(value) is str and 1 <= len(value.encode("utf-8")) <= 4096)
    _require(value.startswith("/") and all(ord(c) >= 32 and ord(c) != 127 for c in value))
    path = Path(value)
    _require(str(path) == value and str(path.resolve(strict=exists)) == value)
    return value


def _inside(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def _file_hash(path: Path, size: int) -> str:
    _require(type(size) is int and 0 <= size <= _MAX_FILE)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        _require(stat.S_ISREG(before.st_mode) and before.st_size == size)
        digest = hashlib.sha256()
        remaining = size
        while remaining:
            data = os.read(descriptor, min(remaining, 1024 * 1024))
            _require(bool(data))
            digest.update(data)
            remaining -= len(data)
        _require(os.read(descriptor, 1) == b"")
        after = os.fstat(descriptor)
        def fields(r):
            return (r.st_dev, r.st_ino, r.st_mode, r.st_uid, r.st_gid,
                    r.st_size, r.st_mtime_ns, r.st_ctime_ns)
        _require(fields(before) == fields(after))
        return digest.hexdigest()
    finally:
        # Startup only, before child construction. Failure never supplies admission.
        os.close(descriptor)


def inventory(
    root: str, *, source_only: bool, budget: list[int], fingerprint: bool = False
) -> list[dict]:
    """Candidate inventory only. Its output cannot authorize itself."""
    root = _absolute(root)
    _require(Path(root).is_dir())
    entries = []

    def walk(directory: Path) -> None:
        before = directory.stat(follow_symlinks=False)
        _require(stat.S_ISDIR(before.st_mode) and not before.st_mode & 0o022)
        with os.scandir(directory) as scan:
            names = []
            for item in scan:
                budget[0] += 1
                _require(budget[0] <= _MAX_ENTRIES)
                names.append(item.name)
            names.sort()
        for name in names:
            path = directory / name
            relative = path.relative_to(root).as_posix()
            _require(len(relative.encode("utf-8")) <= 1024)
            _require(all(ord(c) >= 32 and ord(c) != 127 for c in relative))
            row = path.lstat()
            if not stat.S_ISLNK(row.st_mode):
                _require(not row.st_mode & (0o022 | stat.S_ISUID | stat.S_ISGID))
            entry = {"path": relative, "kind": "directory", "size": 0,
                     "sha256": None, "target": None}
            if fingerprint:
                entry["identity"] = [row.st_dev, row.st_ino, row.st_mode, row.st_uid,
                                     row.st_gid, row.st_size, row.st_mtime_ns, row.st_ctime_ns]
            if stat.S_ISDIR(row.st_mode):
                _require(not source_only or name != "__pycache__")
                entries.append(entry)
                walk(path)
                continue
            if stat.S_ISLNK(row.st_mode):
                _require(not source_only)
                target = os.readlink(path)
                _require(type(target) is str and 0 < len(target.encode("utf-8")) <= 1024)
                _require(not target.startswith("/"))
                _require(_inside(str(path.resolve(strict=True)), root))
                entry.update(kind="symlink", target=target)
            else:
                _require(stat.S_ISREG(row.st_mode))
                _require(not source_only or name.endswith(".py"))
                budget[1] += row.st_size
                _require(budget[1] <= _MAX_TOTAL)
                _require(0 <= row.st_size <= _MAX_FILE)
                digest = None if fingerprint else _file_hash(path, row.st_size)
                entry.update(kind="file", size=row.st_size, sha256=digest)
            entries.append(entry)
        after = directory.stat(follow_symlinks=False)
        _require((before.st_dev, before.st_ino, before.st_mtime_ns, before.st_ctime_ns)
                 == (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_ctime_ns))

    walk(Path(root))
    return sorted(entries, key=lambda row: row["path"])


def runtime_description(*, hash_executable: bool = True) -> dict:
    """Observed candidate configuration, not an independent trust origin."""
    _require(sys.platform in _NATIVE_POLICIES)
    policy, locations = _NATIVE_POLICIES[sys.platform]
    executable = str(Path(sys.executable).resolve(strict=True))
    root = str(Path(sys.base_prefix).resolve(strict=True))
    _require(root not in ("/", "/usr", "/usr/local") and _inside(executable, root))
    paths = []
    for value in sys.path:
        path = _absolute(value, exists=False)
        _require(_inside(path, root))
        paths.append({"path": path, "exists": os.path.lexists(path)})
    return {
        "executable": executable,
        "executable_sha256": (
            _file_hash(Path(executable), Path(executable).stat().st_size)
            if hash_executable else None
        ),
        "prefix": str(Path(sys.prefix).resolve(strict=True)),
        "base_prefix": root,
        "implementation": sys.implementation.name,
        "version": list(sys.version_info[:3]),
        "cache_tag": sys.implementation.cache_tag,
        "sys_path": paths,
        "platform": sys.platform,
        "native_policy": policy,
        "os_library_locations": locations,
    }


def candidate_manifest(plugin: str, parser: str, generation: str) -> bytes:
    """Inventory generator for an external review/test oracle; never run approval."""
    _require(_hex(generation))
    _require(Path(_absolute(parser)).name == "yaml")
    runtime = runtime_description()
    roots = [("runtime", runtime["base_prefix"]), ("plugin", _absolute(plugin)),
             ("parser", _absolute(parser))]
    _require(all(not _inside(a, b) and not _inside(b, a)
                 for i, (_, a) in enumerate(roots) for _, b in roots[i + 1:]))
    budget = [0, 0]
    trees = [{"role": role, "root": root,
              "entries": inventory(root, source_only=role != "runtime", budget=budget)}
             for role, root in roots]
    result = _canonical({"schema": 1, "mode": "synthetic_no_go", "generation": generation,
                         "runtime": runtime, "trees": trees})
    _require(len(result) <= _MAX_MANIFEST)
    return result


class VerifiedInstall:
    """Synthetic-harness generation only; never production-ready authority."""

    def __init__(self, raw: bytes, expected_sha256: str):
        self._raw = self._raw_snapshot = raw
        self._expected = self._expected_snapshot = expected_sha256
        self._refused = False
        self._selection = self._verify()
        self._selection_snapshot = self._selection
        self._roots = self._roots_snapshot = self._root_identities()
        self._fence_data = self._fence_snapshot = self._fingerprint()

    def _verify(self) -> tuple[str, str, str]:
        try:
            _require(type(self._raw) is bytes and 0 < len(self._raw) <= _MAX_MANIFEST)
            _require(_hex(self._expected))
            _require(hashlib.sha256(self._raw).hexdigest() == self._expected)
            _require(sys.flags.isolated == 1 and sys.flags.no_site == 1
                     and sys.flags.ignore_environment == 1 and sys.dont_write_bytecode is True)
            _environment_current()
            document = json.loads(self._raw, object_pairs_hook=_pairs)
            _require(_canonical(document) == self._raw)
            _keys(document, {"schema", "mode", "generation", "runtime", "trees"})
            _require(type(document["schema"]) is int and document["schema"] == 1)
            _require(document["mode"] == "synthetic_no_go" and _hex(document["generation"]))
            trees = document["trees"]
            _require(type(trees) is list and len(trees) == 3)
            roots = []
            for tree, role in zip(trees, ("runtime", "plugin", "parser"), strict=True):
                _keys(tree, {"role", "root", "entries"})
                _require(tree["role"] == role)
                roots.append(_absolute(tree["root"]))
            _require(roots[0] == runtime_description()["base_prefix"])
            _require(document["runtime"] == runtime_description())
            _require(str(Path(__file__).resolve(strict=True))
                     == roots[1] + "/presentation_broker_bootstrap.py")
            # Recompute the full bounded candidate from the independently expected
            # bytes. This comparison also rejects unknown/duplicate entry shapes,
            # changed source/cache/archive inventories and absent-path appearance.
            observed = candidate_manifest(roots[1], roots[2], document["generation"])
            _require(observed == self._raw)
            return roots[1], roots[2], document["generation"]
        except BaseException:
            self._refused = True
            raise BootstrapError from None

    def _root_identities(self) -> tuple:
        roots = (runtime_description(hash_executable=False)["base_prefix"],
                 *self._selection_snapshot[:2])
        return tuple((r.st_dev, r.st_ino, r.st_mode, r.st_uid, r.st_gid,
                      r.st_mtime_ns, r.st_ctime_ns)
                     for r in (Path(p).stat(follow_symlinks=False) for p in roots))

    def _fingerprint(self) -> bytes:
        configuration = runtime_description(hash_executable=False)
        roots = (configuration["base_prefix"], *self._selection_snapshot[:2])
        budget = [0, 0]
        entries = [inventory(root, source_only=i != 0, budget=budget, fingerprint=True)
                   for i, root in enumerate(roots)]
        return _canonical({"runtime": configuration, "entries": entries})

    def fence(self, deadline_ns: int | None = None) -> bool:
        """Observed metadata fence, not atomic mutation protection or permission.

        The launch caller preserves its original deadline. Final diagnostics do
        not revive work, renew cleanup or free any retained reservation.
        """
        try:
            _require(self._refused is False)
            _require(type(self._raw) is bytes and self._raw is self._raw_snapshot)
            _require(type(self._expected) is str and self._expected is self._expected_snapshot)
            _require(type(self._roots_snapshot) is tuple and len(self._roots_snapshot) == 3
                     and all(type(r) is tuple and len(r) == 7
                             and all(type(v) is int for v in r) for r in self._roots_snapshot))
            _require(self._roots is self._roots_snapshot)
            _require(type(self._selection_snapshot) is tuple and len(self._selection_snapshot) == 3
                     and all(type(v) is str for v in self._selection_snapshot))
            _require(self._selection is self._selection_snapshot)
            _require(type(self._fence_data) is bytes and self._fence_data is self._fence_snapshot)
            _require(deadline_ns is None or (type(deadline_ns) is int and deadline_ns > 0))
            _require(deadline_ns is None or time.monotonic_ns() < deadline_ns)
            _environment_current()
            _require(self._fingerprint() == self._fence_snapshot)
            _require(self._root_identities() == self._roots_snapshot)
            _require(deadline_ns is None or time.monotonic_ns() < deadline_ns)
            return True
        except BaseException:
            self._refused = True
            raise BootstrapError from None

    def current(self) -> bool:
        try:
            _require(type(self._raw) is bytes and self._raw is self._raw_snapshot)
            _require(type(self._expected) is str and self._expected is self._expected_snapshot)
            _require(self._refused is False)
            _require(type(self._selection_snapshot) is tuple and len(self._selection_snapshot) == 3
                     and all(type(v) is str for v in self._selection_snapshot))
            _require(self._selection is self._selection_snapshot)
            _require(type(self._roots_snapshot) is tuple and len(self._roots_snapshot) == 3
                     and all(type(r) is tuple and len(r) == 7
                             and all(type(v) is int for v in r) for r in self._roots_snapshot))
            _require(self._roots is self._roots_snapshot)
            _require(self._root_identities() == self._roots_snapshot)
            _require(self._verify() == self._selection_snapshot)
            _require(self._root_identities() == self._roots_snapshot)
            _require(self._fingerprint() == self._fence_snapshot)
            return True
        except BaseException:
            self._refused = True
            raise BootstrapError from None


def _namespace(plugin: str) -> None:
    global __package__
    _require(not any(n == _NAMESPACE or n.startswith(_NAMESPACE + ".") for n in sys.modules))
    package = types.ModuleType(_NAMESPACE)
    package.__package__ = _NAMESPACE
    package.__path__ = [plugin]
    package.__spec__ = importlib.machinery.ModuleSpec(_NAMESPACE, loader=None, is_package=True)
    package.__spec__.submodule_search_locations = [plugin]
    sys.modules[_NAMESPACE] = package
    __package__ = _NAMESPACE


def run_synthetic(installation: VerifiedInstall) -> dict:
    """One retained, empty-input/no-GO cancellation; not a production backend."""
    _require(type(installation) is VerifiedInstall)
    installation.current()  # before any broker import or child reservation
    plugin, parser, _ = installation._selection_snapshot
    _namespace(plugin)
    # The literal private namespace never executes plugin __init__.py.
    from .presentation_broker_codec import BrokerBinding
    from .presentation_broker_lifecycle import operation_id
    from .presentation_broker_registry import BrokerRegistry, RegistryStatus

    scope = BrokerBinding("a" * 52, "b" * 32, os.urandom(32).hex(), "c" * 64, operation_id(1))
    registry = BrokerRegistry.__new__(BrokerRegistry)
    _RETAINED.append(registry)  # before constructor/start effects; never ACK/drop
    registry.__init__(scope, parser_package=parser)
    installation.current()  # full verification before issuing the original deadline
    deadline = time.monotonic_ns() + 1_900_000_000
    ticket = registry.reserve(scope, "default", "METADATA", deadline)
    try:
        installation.fence(deadline)  # no reissued/extended work budget
        registry.start_resources(ticket)
    finally:
        # No input, GO, native root/profile, result publication or permission.
        end = time.monotonic_ns() + 250_000_000
        registry.abort_resources(ticket)
    drained = False
    while time.monotonic_ns() < end:
        if registry.poll_resource_cleanup(ticket):
            drained = True
            break
        time.sleep(0.001)
    installation.fence()  # diagnostic only; no work/closure authority is restored
    pending = registry.status(scope) is RegistryStatus.PENDING
    return {"schema": 1, "mode": "synthetic_no_go", "registry_retained": True,
            "local_drain_observed": drained, "registry_pending": pending,
            "production_qualified": False}


def main() -> int:
    try:
        _require(len(sys.argv) == 5 and sys.argv[1] == "--manifest"
                 and sys.argv[3] == "--expected-sha256")
        path = Path(_absolute(sys.argv[2]))
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            row = os.fstat(descriptor)
            _require(stat.S_ISREG(row.st_mode) and 0 < row.st_size <= _MAX_MANIFEST)
            chunks = []
            remaining = row.st_size
            while remaining:
                part = os.read(descriptor, min(remaining, 1024 * 1024))
                _require(bool(part))
                chunks.append(part)
                remaining -= len(part)
            _require(os.read(descriptor, 1) == b"")
            raw = b"".join(chunks)
        finally:
            os.close(descriptor)
        installation = VerifiedInstall(raw, sys.argv[4])
        roots = (runtime_description()["base_prefix"], *installation._selection[:2])
        _require(not any(_inside(str(path), root) for root in roots))
        report = run_synthetic(installation)
        sys.stdout.buffer.write(_canonical(report) + b"\n")
        sys.stdout.buffer.flush()
        if report["local_drain_observed"] is True and report["registry_pending"] is True:
            return 0
    except BaseException:
        try:
            sys.stderr.buffer.write(b"BI1_BROKER_BOOTSTRAP_REFUSED\n")
            sys.stderr.buffer.flush()
        except BaseException:
            if not _RETAINED:
                return 1  # otherwise retain debt despite diagnostic failure
        if not _RETAINED:
            return 1
    # Do not exit normally and drop a started/partial owner with uncertain debt.
    # The externally owned synthetic supervisor must inspect/retire this process.
    while True:
        time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(main())
