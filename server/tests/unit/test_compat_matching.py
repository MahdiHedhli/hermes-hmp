"""CS-19 build identity and matching rule (research R8 steps 3-5; IR-5).

`BuildIdentity` rejects a git SHA without a fingerprint, and `match_build`, the rule the gate
always uses, is tested here over every combination of install kind and entry kind.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from hmp_plugin.compat import (
    BuildEntry,
    BuildIdentity,
    CompatGate,
    CompatStatus,
    ReadCompatList,
    match_build,
)
from hmp_plugin.contract import OtherWhy

SHA_A = "a" * 40
SHA_B = "b" * 40
FP_1 = "f1" * 32
FP_2 = "e2" * 32


def entry(fp: str, sha: str | None, source_sha: str | None = None) -> BuildEntry:
    return BuildEntry(fp, sha, f"{sha}/{fp[:1]}", "run", "2026-01-01", source_sha=source_sha)


GIT_A_1 = entry(FP_1, SHA_A)  # git entry: SHA_A, FP_1
GIT_A_2 = entry(FP_2, SHA_A)  # same SHA, other fingerprint
GIT_B_1 = entry(FP_1, SHA_B)  # other SHA, same fingerprint as GIT_A_1
FPONLY_1 = entry(FP_1, None)  # fingerprint-only entry
FPONLY_1_SRC_A = entry(FP_1, None, source_sha=SHA_A)  # fingerprint-only, provenance SHA_A
FPONLY_2 = entry(FP_2, None)

# --------------------------------------------------------------------------------------------
# BuildIdentity / BuildEntry validation
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "ok"),
    [
        ({"fingerprint": FP_1, "git_sha": SHA_A}, True),  # git install
        ({"fingerprint": FP_1, "git_sha": None}, True),  # no .git
        ({"fingerprint": FP_1}, True),  # git_sha defaults to None
        ({"fingerprint": None, "git_sha": SHA_A}, False),  # git SHA without fingerprint (IR-5)
        ({"fingerprint": None, "git_sha": None}, False),  # nothing
        ({"fingerprint": "", "git_sha": SHA_A}, False),
        ({"fingerprint": FP_1.upper(), "git_sha": SHA_A}, False),  # not lowercase
        ({"fingerprint": FP_1[:-1], "git_sha": SHA_A}, False),  # 63 chars
        ({"fingerprint": FP_1 + "0", "git_sha": SHA_A}, False),  # 65 chars
        ({"fingerprint": "g" * 64, "git_sha": SHA_A}, False),  # not hex
        ({"fingerprint": FP_1, "git_sha": SHA_A[:-1]}, False),  # 39-char SHA
        ({"fingerprint": FP_1, "git_sha": SHA_A.upper()}, False),
        ({"fingerprint": FP_1, "git_sha": ""}, False),  # empty SHA is not "no .git"
        ({"fingerprint": FP_1.encode(), "git_sha": None}, False),  # bytes, not str
    ],
)
def test_build_identity_validation(kwargs: dict[str, object], ok: bool) -> None:
    if ok:
        BuildIdentity(**kwargs)  # type: ignore[arg-type]
    else:
        with pytest.raises((ValueError, TypeError)):
            BuildIdentity(**kwargs)  # type: ignore[arg-type]


def test_build_identity_requires_fingerprint_argument() -> None:
    with pytest.raises(TypeError):
        BuildIdentity(git_sha=SHA_A)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("fp", "sha", "source_sha", "ok"),
    [
        (FP_1, SHA_A, None, True),
        (FP_1, None, None, True),
        (FP_1, None, SHA_A, True),  # fingerprint-only with provenance
        (None, SHA_A, None, False),  # an entry always has a fingerprint
        (FP_1, "x" * 40, None, False),
        (FP_1, None, "short", False),
    ],
)
def test_build_entry_validation(fp: object, sha: object, source_sha: object, ok: bool) -> None:
    def make() -> BuildEntry:
        return BuildEntry(fp, sha, "l", "run", "2026-01-01", source_sha=source_sha)  # type: ignore[arg-type]

    if ok:
        make()
    else:
        with pytest.raises(ValueError):
            make()


# --------------------------------------------------------------------------------------------
# match_build: every combination
# --------------------------------------------------------------------------------------------

GIT_INSTALL_A_1 = BuildIdentity(FP_1, SHA_A)
GIT_INSTALL_A_2 = BuildIdentity(FP_2, SHA_A)
GIT_INSTALL_B_2 = BuildIdentity(FP_2, SHA_B)
NOGIT_INSTALL_1 = BuildIdentity(FP_1)
NOGIT_INSTALL_2 = BuildIdentity(FP_2)

MATCH_TABLE: list[tuple[str, BuildIdentity, tuple[BuildEntry, ...], BuildEntry | None]] = [
    # --- git install ---
    ("git: SHA listed, fingerprint equal -> match", GIT_INSTALL_A_1, (GIT_A_1,), GIT_A_1),
    ("git: SHA listed, fingerprint differs -> none", GIT_INSTALL_A_2, (GIT_A_1,), None),
    ("git: SHA unlisted, other SHA has same fp -> none", GIT_INSTALL_A_1, (GIT_B_1,), None),
    ("git: SHA unlisted, fp-only entry has same fp -> none", GIT_INSTALL_A_1, (FPONLY_1,), None),
    (
        "git: fp-only entry whose source_sha equals the SHA -> none (provenance only)",
        GIT_INSTALL_A_1,
        (FPONLY_1_SRC_A,),
        None,
    ),
    ("git: empty list -> none", GIT_INSTALL_A_1, (), None),
    (
        "git: same SHA listed twice, second fingerprint equal -> second",
        GIT_INSTALL_A_2,
        (GIT_A_1, GIT_A_2),
        GIT_A_2,
    ),
    (
        "git: matching git entry among decoys -> that entry",
        GIT_INSTALL_A_1,
        (FPONLY_1, GIT_B_1, GIT_A_2, GIT_A_1),
        GIT_A_1,
    ),
    ("git: SHA unlisted, nothing shares fp -> none", GIT_INSTALL_B_2, (GIT_A_1, FPONLY_1), None),
    # --- install without .git ---
    ("no-git: fp-only entry, fingerprint equal -> match", NOGIT_INSTALL_1, (FPONLY_1,), FPONLY_1),
    (
        "no-git: fp-only entry with source_sha, fingerprint equal -> match",
        NOGIT_INSTALL_1,
        (FPONLY_1_SRC_A,),
        FPONLY_1_SRC_A,
    ),
    ("no-git: fp-only entry, fingerprint differs -> none", NOGIT_INSTALL_2, (FPONLY_1,), None),
    ("no-git: fp equals only a git entry's -> none", NOGIT_INSTALL_1, (GIT_A_1,), None),
    (
        "no-git: fp equals git entries only -> none",
        NOGIT_INSTALL_1,
        (GIT_A_1, GIT_B_1),
        None,
    ),
    (
        "no-git: fp-only match among git decoys -> that entry",
        NOGIT_INSTALL_1,
        (GIT_A_1, FPONLY_2, FPONLY_1),
        FPONLY_1,
    ),
    ("no-git: empty list -> none", NOGIT_INSTALL_1, (), None),
]


@pytest.mark.parametrize(
    ("identity", "builds", "expected"),
    [row[1:] for row in MATCH_TABLE],
    ids=[row[0] for row in MATCH_TABLE],
)
def test_match_build(
    identity: BuildIdentity, builds: tuple[BuildEntry, ...], expected: BuildEntry | None
) -> None:
    assert match_build(identity, builds) is expected


# --------------------------------------------------------------------------------------------
# The gate applies the rule itself: T023's five CS-19 cases, end to end.
# --------------------------------------------------------------------------------------------


class Reader:
    def __init__(self, identity: BuildIdentity | None) -> None:
        self.identity = identity

    def read(self, hermes_root: Path) -> BuildIdentity | None:
        return self.identity


def _gate(identity: BuildIdentity, *builds: BuildEntry) -> CompatGate:
    def probe() -> Sequence[str]:
        return ()

    return CompatGate(
        Reader(identity),
        ReadCompatList(format=1, bridge_files=(), builds=builds),
        probe,
        root_locator=lambda: Path("/nonexistent-hermes-root"),
    )


@pytest.mark.parametrize(
    ("identity", "builds", "supported"),
    [
        (GIT_INSTALL_A_1, (GIT_A_1,), True),  # git SHA listed + fingerprint match
        (GIT_INSTALL_A_2, (GIT_A_1,), False),  # git SHA listed + fingerprint mismatch
        (GIT_INSTALL_A_1, (FPONLY_1,), False),  # SHA unlisted, fp equals a fp-only entry
        (NOGIT_INSTALL_1, (FPONLY_1,), True),  # no .git + fp-only match
        (NOGIT_INSTALL_1, (GIT_A_1,), False),  # no .git + fp matches only a git entry
    ],
    ids=[
        "git-listed-fp-match",
        "git-listed-fp-mismatch",
        "git-unlisted-fp-only-equal",
        "nogit-fp-only-match",
        "nogit-fp-matches-git-entry-only",
    ],
)
def test_gate_applies_cs19(
    identity: BuildIdentity, builds: tuple[BuildEntry, ...], supported: bool
) -> None:
    result = _gate(identity, *builds).evaluate()
    if supported:
        assert result.status is CompatStatus.SUPPORTED
    else:
        assert (result.status, result.why) == (
            CompatStatus.UNSUPPORTED,
            OtherWhy.HERMES_BUILD_UNSUPPORTED,
        )


def test_gate_revalidates_identity_mutated_after_construction() -> None:
    identity = BuildIdentity(FP_1, SHA_A)
    object.__setattr__(identity, "fingerprint", None)  # a buggy reader bypassing the dataclass
    result = _gate(identity, GIT_A_1).evaluate()
    assert result.why is OtherWhy.HERMES_BUILD_UNSUPPORTED
