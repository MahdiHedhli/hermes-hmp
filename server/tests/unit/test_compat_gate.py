"""Compat gate ordering (GU-2c, ERR-2a; controller ruling on T013).

An unlisted or unidentifiable build returns UNSUPPORTED before any Hermes import: the dependency
probe never runs, and `sys.modules` gains no module from the Hermes tree. Identity reading and the
list match are injected here; their real implementations are T023's.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest

from hmp_plugin.compat import (
    BuildEntry,
    BuildIdentity,
    CompatGate,
    CompatStatus,
    ReadCompatList,
    locate_hermes_root,
)
from hmp_plugin.contract import OtherWhy

SHA = "a" * 40
FP = "b" * 64
OTHER_SHA = "c" * 40
ENTRY = BuildEntry(FP, SHA, "synthetic", "test-run", "2026-01-01")
GIT_ID = BuildIdentity(fingerprint=FP, git_sha=SHA)
HERMES_TOP_LEVEL = ("hermes_constants", "gateway", "hermes_state")


@pytest.fixture()
def fake_hermes(tmp_path: Path) -> Iterator[Path]:
    """A synthetic, importable Hermes tree on sys.path."""
    root = tmp_path / "hermes-src"
    (root / "gateway").mkdir(parents=True)
    stub = "LOADED = True\n"
    (root / "hermes_constants.py").write_text(stub)
    (root / "hermes_state.py").write_text(stub)
    (root / "gateway" / "__init__.py").write_text(stub)
    (root / "gateway" / "run.py").write_text(stub)
    sys.path.insert(0, str(root))
    for name in HERMES_TOP_LEVEL:
        sys.modules.pop(name, None)
    try:
        yield root
    finally:
        sys.path.remove(str(root))
        for name in list(sys.modules):
            if name.split(".")[0] in HERMES_TOP_LEVEL:
                del sys.modules[name]


class Reader:
    def __init__(self, identity: BuildIdentity | None) -> None:
        self.identity = identity
        self.roots: list[Path] = []

    def read(self, hermes_root: Path) -> BuildIdentity | None:
        self.roots.append(hermes_root)
        return self.identity


def listed(*entries: BuildEntry) -> ReadCompatList:
    return ReadCompatList(format=1, bridge_files=(), builds=entries)


# Entries that do NOT qualify GIT_ID under CS-19: another SHA with the same fingerprint, and a
# fingerprint-only entry with the same fingerprint (a git install never matches those).
NON_MATCHING = listed(
    BuildEntry(FP, OTHER_SHA, "other sha", "run", "2026-01-01"),
    BuildEntry(FP, None, "fingerprint-only", "run", "2026-01-01", source_sha=SHA),
)


class Probe:
    """Imports a Hermes module, as the real probe would."""

    def __init__(self, missing: Sequence[str] = ()) -> None:
        self.calls = 0
        self.missing = missing

    def __call__(self) -> Sequence[str]:
        self.calls += 1
        importlib.import_module("gateway.run")
        importlib.import_module("hermes_state")
        return self.missing


def _hermes_modules() -> set[str]:
    return {m for m in sys.modules if m.split(".")[0] in HERMES_TOP_LEVEL}


def test_locate_root_imports_nothing(fake_hermes: Path) -> None:
    before = set(sys.modules)
    assert locate_hermes_root() == fake_hermes
    assert set(sys.modules) == before


def test_unlisted_build_imports_no_hermes_module(fake_hermes: Path) -> None:
    before = set(sys.modules)
    reader, probe = Reader(GIT_ID), Probe()
    result = CompatGate(reader, NON_MATCHING, probe).evaluate()
    assert result.status is CompatStatus.UNSUPPORTED
    assert result.why is OtherWhy.HERMES_BUILD_UNSUPPORTED
    assert reader.roots == [fake_hermes]  # the real root locator ran
    assert probe.calls == 0
    assert _hermes_modules() == set()
    assert set(sys.modules) - before == set()


class GitOnly:
    """Not a BuildIdentity: a reader bug handing back a git SHA without a fingerprint."""

    git_sha = SHA
    fingerprint = None


@pytest.mark.parametrize("identity", [None, GitOnly()])
def test_unidentifiable_build_imports_nothing(fake_hermes: Path, identity: object) -> None:
    probe = Probe()
    result = CompatGate(Reader(identity), listed(ENTRY), probe).evaluate()  # type: ignore[arg-type]
    assert (result.status, result.why) == (
        CompatStatus.UNSUPPORTED,
        OtherWhy.HERMES_BUILD_UNSUPPORTED,
    )
    assert probe.calls == 0
    assert _hermes_modules() == set()


def test_no_hermes_root_is_unsupported() -> None:
    reader, probe = Reader(GIT_ID), Probe()
    result = CompatGate(reader, listed(ENTRY), probe, root_locator=lambda: None).evaluate()
    assert result.why is OtherWhy.HERMES_BUILD_UNSUPPORTED
    assert reader.roots == [] and probe.calls == 0


def test_reader_failure_fails_closed(fake_hermes: Path) -> None:
    class Broken:
        def read(self, hermes_root: Path) -> BuildIdentity | None:
            raise OSError("unreadable")

    probe = Probe()
    result = CompatGate(Broken(), listed(ENTRY), probe).evaluate()
    assert result.why is OtherWhy.HERMES_BUILD_UNSUPPORTED
    assert probe.calls == 0


def test_listed_build_runs_probe_then_supported(fake_hermes: Path) -> None:
    probe = Probe()
    result = CompatGate(Reader(GIT_ID), listed(ENTRY), probe).evaluate()
    assert result.supported and result.why is None and result.entry == ENTRY
    assert probe.calls == 1
    # The probe really imports; this is what the unlisted-build tests prove never happens.
    assert {"gateway", "gateway.run", "hermes_state"} <= _hermes_modules()


def test_listed_build_missing_dependency(fake_hermes: Path) -> None:
    probe = Probe(missing=["gateway.run:GatewayRunner"])
    result = CompatGate(Reader(GIT_ID), listed(ENTRY), probe).evaluate()
    assert (result.status, result.why) == (
        CompatStatus.UNSUPPORTED,
        OtherWhy.HERMES_READ_DEPENDENCY_MISSING,
    )


def test_probe_exception_is_missing_dependency(fake_hermes: Path) -> None:
    def probe() -> Sequence[str]:
        raise ImportError("gone")

    result = CompatGate(Reader(GIT_ID), listed(ENTRY), probe).evaluate()
    assert result.why is OtherWhy.HERMES_READ_DEPENDENCY_MISSING


def test_compat_module_source_never_names_bridge() -> None:
    src = (Path(__file__).resolve().parents[2] / "hmp_plugin" / "compat.py").read_text()
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith(("#", '"')))
    assert "import bridge" not in code and ".bridge" not in code
