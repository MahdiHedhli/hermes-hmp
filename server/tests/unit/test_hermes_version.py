"""Hermes version parser and per-feature floors (owner policy 2026-10-01).

The parser reads files only: it never imports, executes, evaluates or compiles Hermes code. An
unknown or placeholder version is UNKNOWN, never "below the floor".
"""

from __future__ import annotations

import ast
import builtins
import importlib
import json
import subprocess
from pathlib import Path

import pytest

from hmp_plugin import hermes_version as hv
from hmp_plugin.hermes_version import (
    FEATURE_FLOORS,
    KNOWN_RELEASES,
    FloorStatus,
    Scheme,
    VersionSource,
    classify,
    read_hermes_version,
)

READ = FEATURE_FLOORS["read"]
SEND = FEATURE_FLOORS["send"]


def _init(root: Path, text: str | bytes) -> None:
    pkg = root / "hermes_cli"
    pkg.mkdir(parents=True, exist_ok=True)
    data = text if isinstance(text, bytes) else text.encode("utf-8")
    (pkg / "__init__.py").write_bytes(data)


def _stamp(root: Path, value: object) -> None:
    (root / "install-stamp.json").write_text(json.dumps(value), encoding="utf-8")


def test_v1_semver_literal(tmp_path: Path) -> None:
    _init(tmp_path, '__version__ = "0.21.5"\n__release_date__ = "2026.9.24"\n')
    version = read_hermes_version(tmp_path)
    assert (version.scheme, version.parts, version.source) == (
        Scheme.SEMVER, (0, 21, 5), VersionSource.LITERAL,
    )
    assert version.text == "0.21.5"


def test_v2_annotation_only_version_uses_release_date_and_never_executes(tmp_path: Path) -> None:
    _init(
        tmp_path,
        "raise SystemExit('executed')\n"
        "__version__: str\n"
        '__release_date__ = "2026.9.24"\n'
        "def __getattr__(name):\n    raise AssertionError\n",
    )
    version = read_hermes_version(tmp_path)
    assert (version.scheme, version.parts, version.source) == (
        Scheme.CALVER, (2026, 9, 24, 0), VersionSource.RELEASE_DATE,
    )
    assert version.text == "2026.9.24"


def test_calver_fourth_part(tmp_path: Path) -> None:
    _init(tmp_path, '__release_date__ = "2026.8.16.2"\n')
    version = read_hermes_version(tmp_path)
    assert version.parts == (2026, 8, 16, 2) and version.text == "2026.8.16.2"


def test_v3_placeholder_and_unreadable_inputs_are_unknown_not_old(tmp_path: Path) -> None:
    cases: dict[str, tuple[str | bytes | None, object | None]] = {
        "placeholder literal": ('__version__ = "0.0.0"\n', None),
        "placeholder stamp": ("__version__: str\n", {"baseVersion": "0.0.0"}),
        "missing": (None, None),
        "oversized": ("# " + "x" * (300 * 1024) + '\n__version__ = "0.21.5"\n', None),
        "non-utf8": (b"\xff\xfe__version__ = '0.21.5'\n", None),
        "bad syntax": ("def (:\n", None),
    }
    for label, (init, stamp) in cases.items():
        root = tmp_path / label.replace(" ", "_")
        root.mkdir()
        if init is not None:
            _init(root, init)
        if stamp is not None:
            _stamp(root, stamp)
        version = read_hermes_version(root)
        assert version.scheme is Scheme.UNKNOWN, label
        assert version.source is VersionSource.UNKNOWN, label
        for feature_floor in FEATURE_FLOORS.values():
            assert classify(version, feature_floor) is FloorStatus.UNKNOWN, label


def test_pyproject_alone_is_never_authoritative(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.0.0"\n', encoding="utf-8")
    assert read_hermes_version(tmp_path).scheme is Scheme.UNKNOWN
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.21.5"\n', encoding="utf-8")
    assert read_hermes_version(tmp_path).scheme is Scheme.UNKNOWN


def test_v4_stamp_base_version_with_lazy_version(tmp_path: Path) -> None:
    _init(tmp_path, "__version__: str\n__release_date__ = '2026.9.24'\n")
    _stamp(tmp_path, {"baseVersion": "0.21.6"})
    version = read_hermes_version(tmp_path)
    assert (version.parts, version.source) == ((0, 21, 6), VersionSource.STAMP)
    for broken in ("{not json", json.dumps({"baseVersion": 5}), json.dumps(["x"])):
        (tmp_path / "install-stamp.json").write_text(broken, encoding="utf-8")
        assert read_hermes_version(tmp_path).source is VersionSource.RELEASE_DATE
    (tmp_path / "install-stamp.json").write_text(
        json.dumps({"baseVersion": "0.21.6", "pad": "x" * 70_000}), encoding="utf-8"
    )
    assert read_hermes_version(tmp_path).source is VersionSource.RELEASE_DATE


@pytest.mark.parametrize(
    ("value", "scheme", "read_status", "send_status"),
    [
        ("0.21.3", Scheme.SEMVER, FloorStatus.BELOW_FLOOR, FloorStatus.BELOW_FLOOR),
        ("0.21.4", Scheme.SEMVER, FloorStatus.AT_OR_ABOVE, FloorStatus.BELOW_FLOOR),
        ("0.21.5", Scheme.SEMVER, FloorStatus.AT_OR_ABOVE, FloorStatus.AT_OR_ABOVE),
        ("0.22.0", Scheme.SEMVER, FloorStatus.AT_OR_ABOVE, FloorStatus.AT_OR_ABOVE),
        ("1.0.0", Scheme.SEMVER, FloorStatus.AT_OR_ABOVE, FloorStatus.AT_OR_ABOVE),
    ],
)
def test_v5_semver_floor_table(
    tmp_path: Path, value: str, scheme: Scheme, read_status: FloorStatus, send_status: FloorStatus
) -> None:
    _init(tmp_path, f'__version__ = "{value}"\n')
    version = read_hermes_version(tmp_path)
    assert version.scheme is scheme
    assert classify(version, READ) is read_status
    assert classify(version, SEND) is send_status


@pytest.mark.parametrize(
    ("value", "read_status", "send_status"),
    [
        ("2026.8.16.2", FloorStatus.BELOW_FLOOR, FloorStatus.BELOW_FLOOR),
        ("2026.9.14", FloorStatus.BELOW_FLOOR, FloorStatus.BELOW_FLOOR),
        ("2026.9.21", FloorStatus.AT_OR_ABOVE, FloorStatus.BELOW_FLOOR),
        ("2026.9.24", FloorStatus.AT_OR_ABOVE, FloorStatus.AT_OR_ABOVE),
        ("2027.1.1", FloorStatus.AT_OR_ABOVE, FloorStatus.AT_OR_ABOVE),
    ],
)
def test_v5_calver_floor_table(
    tmp_path: Path, value: str, read_status: FloorStatus, send_status: FloorStatus
) -> None:
    _init(tmp_path, f'__release_date__ = "{value}"\n')
    version = read_hermes_version(tmp_path)
    assert version.scheme is Scheme.CALVER
    assert classify(version, READ) is read_status
    assert classify(version, SEND) is send_status


@pytest.mark.parametrize("value", ["0.21.4rc1", "0.21.4+local", "0.21.4-dev", "v0.21.5", "0.21"])
def test_v6_non_plain_semver_is_unknown(tmp_path: Path, value: str) -> None:
    _init(tmp_path, f'__version__ = "{value}"\n')
    assert read_hermes_version(tmp_path).scheme is Scheme.UNKNOWN


def test_v7_precedence_stamp_then_literal_then_release_date(tmp_path: Path) -> None:
    _init(tmp_path, '__version__ = "0.21.5"\n__release_date__ = "2026.9.21"\n')
    _stamp(tmp_path, {"baseVersion": "0.21.4"})
    assert read_hermes_version(tmp_path).source is VersionSource.STAMP
    (tmp_path / "install-stamp.json").unlink()
    assert read_hermes_version(tmp_path).source is VersionSource.LITERAL
    _init(tmp_path, '__release_date__ = "2026.9.21"\n')
    assert read_hermes_version(tmp_path).source is VersionSource.RELEASE_DATE


def test_n1_the_stamp_is_authoritative_not_the_larger_value(tmp_path: Path) -> None:
    """Root decision: a valid stamp wins even when it is older than the literal, and a newer
    stamp wins over an older literal. It is never `max(literal, stamp)`."""
    _init(tmp_path, '__version__ = "0.21.5"\n')
    _stamp(tmp_path, {"baseVersion": "0.21.4"})
    older_stamp = read_hermes_version(tmp_path)
    assert (older_stamp.parts, older_stamp.source) == ((0, 21, 4), VersionSource.STAMP)
    _init(tmp_path, '__version__ = "0.21.4"\n')
    _stamp(tmp_path, {"baseVersion": "0.21.5"})
    newer_stamp = read_hermes_version(tmp_path)
    assert (newer_stamp.parts, newer_stamp.source) == ((0, 21, 5), VersionSource.STAMP)


def test_n1_invalid_or_malformed_stamp_falls_back_to_the_literal(tmp_path: Path) -> None:
    _init(tmp_path, '__version__ = "0.21.5"\n__release_date__ = "2026.9.21"\n')
    stamp = tmp_path / "install-stamp.json"
    for broken in (
        b"{not json",
        b'{"baseVersion": 5}',
        b'["x"]',
        b'{"baseVersion": "0.0.0"}',
        b'{"baseVersion": "0.21.5-rc1"}',
        b'{"baseVersion": "0.21.4"' + b', "pad": "' + b"x" * 70_000 + b'"}',
        b"\xff\xfe\x00",
    ):
        stamp.write_bytes(broken)
        version = read_hermes_version(tmp_path)
        assert (version.parts, version.source) == ((0, 21, 5), VersionSource.LITERAL), broken
    _init(tmp_path, '__release_date__ = "2026.9.21"\n')
    stamp.write_bytes(b'{"baseVersion": "0.0.0"}')
    assert read_hermes_version(tmp_path).source is VersionSource.RELEASE_DATE


def test_n1_a_utf8_bom_stamp_is_read(tmp_path: Path) -> None:
    _init(tmp_path, '__release_date__ = "2026.9.21"\n')
    (tmp_path / "install-stamp.json").write_bytes(
        b"\xef\xbb\xbf" + json.dumps({"baseVersion": "0.21.6"}).encode()
    )
    version = read_hermes_version(tmp_path)
    assert (version.parts, version.source) == ((0, 21, 6), VersionSource.STAMP)


def test_only_module_level_plain_assignments_count(tmp_path: Path) -> None:
    _init(
        tmp_path,
        "def f():\n    __version__ = '0.21.5'\n"
        "class C:\n    __version__ = '0.21.5'\n"
        "__version__ = compute()\n"
        "__version__, other = '0.21.5', 1\n",
    )
    assert read_hermes_version(tmp_path).scheme is Scheme.UNKNOWN


def test_v8_no_import_exec_or_subprocess(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init(tmp_path, '__version__ = "0.21.5"\n')
    _stamp(tmp_path, {"baseVersion": "0.21.5"})

    def boom(*_a: object, **_k: object) -> None:
        raise AssertionError("forbidden call")

    monkeypatch.setattr(importlib, "import_module", boom)
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(builtins, "exec", boom)
    monkeypatch.setattr(builtins, "eval", boom)
    assert read_hermes_version(tmp_path).parts == (0, 21, 5)
    tree = ast.parse(Path(hv.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not imported & {"importlib", "subprocess", "os", "runpy", "socket"}
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not called & {"exec", "eval", "compile", "__import__", "open"}


def test_v9_known_releases_are_increasing_and_floors_are_rows() -> None:
    semvers = [r.semver for r in KNOWN_RELEASES]
    calvers = [r.calver for r in KNOWN_RELEASES]
    assert semvers == sorted(set(semvers))
    assert calvers == sorted(set(calvers))
    for floor in FEATURE_FLOORS.values():
        assert floor in KNOWN_RELEASES
    assert FEATURE_FLOORS["read"].semver == (0, 21, 4)
    assert FEATURE_FLOORS["session_browsing"] == FEATURE_FLOORS["read"]
    # Spec 034: both approval members sit exactly at the send floor. No notifier floor exists.
    for name in ("send", "jobs", "model", "approvals", "phone_chat"):
        assert FEATURE_FLOORS[name].semver == (0, 21, 5)
        assert FEATURE_FLOORS[name].calver == (2026, 9, 24, 0)
    assert FEATURE_FLOORS["approvals"] == FEATURE_FLOORS["send"]
    assert FEATURE_FLOORS["phone_chat"] == FEATURE_FLOORS["send"]
    assert set(FEATURE_FLOORS) == {
        "read", "session_browsing", "send", "jobs", "model", "approvals", "phone_chat"
    }
