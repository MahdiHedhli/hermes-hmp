"""Git-install fixture mode (specs/005 amendment 2): real git repositories, synthetic trees only.

Everything lives under pytest's tmp_path with git's own configuration isolated from the real home:
no Hermes, no gateway, no network and no live home. The positive cases run the ACTUAL runtime
identity reader and baseline capture (`hmp_plugin.compat`) over a real `.git`; the negative cases
each break exactly one binding (kind, git SHA, source, clone independence) and must be refused.
The production manifest stays empty throughout.

Run with the repo's pytest config: `pytest -c server/pyproject.toml --rootdir server
tools/fixtures/tests` (see amendment 2, G5).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import _fixture_common as fc
import approval_fixture as af
import direct_send_fixture as dsf
import pytest

from hmp_plugin import compat
from hmp_plugin.compat import compute_read_bridge_fingerprint

COMPAT = Path(__file__).resolve().parents[2] / "compat"
sys.path.insert(0, str(COMPAT))
import approval_matrix  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
FILES = ["gateway/a.py", "tools/approval_prompt.py", "z.py"]
READ_FILES = ["gateway/a.py", "z.py"]
DIRECT_FILES = ["z.py"]
LABEL = "git-fixture-build"


def git(cwd: Path, *args: str, home: Path) -> str:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home),
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    done = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args], cwd=cwd, env=env, check=True,
        capture_output=True, text=True,
    )
    return done.stdout.strip()


class World:
    """`upstream/` (the original, only ever read) and `builds/LABEL/src` (an independent clone)."""

    def __init__(self, base: Path) -> None:
        self.base = base.resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.upstream = self.base / "upstream"
        for rel in FILES:
            (self.upstream / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.upstream / rel).write_text(f"# {rel}\n")
        git(self.upstream, "init", "-q", "-b", "main", home=self.home)
        git(self.upstream, "add", "-A", home=self.home)
        git(self.upstream, "commit", "-q", "-m", "base", home=self.home)
        self.sha = git(self.upstream, "rev-parse", "HEAD", home=self.home)
        self.src = self.base / "builds" / LABEL / "src"

    def clone(self, *extra: str, keep_remote: bool = False) -> fc.BuildInfo:
        self.src.parent.mkdir(parents=True, exist_ok=True)
        git(self.base, "clone", "-q", *(extra or ("--no-local",)), str(self.upstream),
            str(self.src), home=self.home)
        if not keep_remote:
            git(self.src, "remote", "remove", "origin", home=self.home)
        return self.build()

    def build(self) -> fc.BuildInfo:
        (self.src / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
        python = self.src / ".venv" / "bin" / "python3"
        python.touch()
        return fc.BuildInfo(LABEL, self.src, python)


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


@pytest.fixture
def gitbuild(world):
    return world.clone()


def snapshot(root: Path) -> dict:
    snap: dict = {}
    for current, dirs, files in os.walk(root, followlinks=False):
        for name in (*dirs, *files):
            path = Path(current, name)
            rel = str(path.relative_to(root))
            if path.is_symlink():
                snap[rel] = ("link", os.readlink(path))
            elif path.is_dir():
                snap[rel] = ("dir",)
            else:
                snap[rel] = ("file", path.read_bytes())
    return snap


def make_fixture(tmp_path: Path) -> Path:
    plugin = tmp_path / "fixture" / "_hmp_plugin"
    plugin.mkdir(parents=True)
    (plugin / "approval_supported_builds.json").write_text(
        json.dumps({"format": 1, "bridge_files": FILES, "builds": []}))
    (plugin / "direct_send_supported_builds.json").write_text(
        json.dumps({"format": 1, "bridge_files": DIRECT_FILES, "builds": []}))
    (plugin / "read_compat_builds.json").write_text(
        json.dumps({"format": 1, "bridge_files": READ_FILES, "builds": []}))
    (plugin / "mod.py").write_text("# plugin\n")
    return tmp_path / "fixture"


def entry(build: fc.BuildInfo, sha: str | None, **overrides) -> dict:
    base = {
        "label": build.label, "git_sha": sha, "source_sha": sha or "a" * 40,
        "fingerprint": compute_read_bridge_fingerprint(build.src_dir, FILES),
        "qualified_by": "approval_matrix (provisional fixture bootstrap; integration pending)",
        "qualified_at": "2026-09-30T00:00:00+00:00",
    }
    return {**base, **overrides}


def write_receipt(path: Path, entries: list, *, extra=None) -> Path:
    path.write_text(json.dumps(
        {"format": 1, "bridge_files": FILES, "builds": entries, **(extra or {})}))
    return path


def evidence(build: fc.BuildInfo, plugin: Path, sha: str | None, **overrides) -> dict:
    base = {
        "kind": af.RECEIPT_KIND_GIT if sha else af.RECEIPT_KIND, "git_sha": sha,
        "complete": True, "label": build.label, "source_sha": sha or "a" * 40,
        "upstream_verified": True,
        "approval_fingerprint": compute_read_bridge_fingerprint(build.src_dir, FILES),
        "read_fingerprint": compute_read_bridge_fingerprint(build.src_dir, READ_FILES),
        "direct_send_fingerprint": compute_read_bridge_fingerprint(build.src_dir, DIRECT_FILES),
        "plugin_sha256": af.plugin_source_digest(plugin),
        "stages": dict.fromkeys(af.REQUIRED_STAGES, True),
        "required_tests": af.required_test_names(build.label),
        "junit_sha256": "c" * 64,
    }
    return {**base, **overrides}


def validate_final(path: Path, build: fc.BuildInfo, plugin: Path):
    return af.validate_approval_receipt(
        path, build, target_files=FILES, final=True, plugin_dir=plugin,
        read_files=READ_FILES, direct_files=DIRECT_FILES)


def final_entry(build: fc.BuildInfo, sha: str | None, **overrides) -> dict:
    return entry(build, sha, qualified_by="approval_matrix (fixture-only; never a manifest entry)",
                 **overrides)


# ---- the clone itself ---------------------------------------------------------------------


def test_independent_clone_is_accepted_and_reports_its_full_head(world, gitbuild):
    assert af.build_git_head(gitbuild.src_dir) == world.sha
    assert af.assert_git_fixture_clone(gitbuild.src_dir, original=world.upstream) == world.sha
    assert len(world.sha) == 40


def test_an_archive_has_no_git_head(tmp_path):
    (tmp_path / "x").mkdir()
    assert af.build_git_head(tmp_path / "x") is None
    with pytest.raises(fc.FixtureSafetyError, match=r"real \.git"):
        af.assert_git_fixture_clone(tmp_path / "x")


def break_hardlink(world, src):
    target = next(p for p in (src / ".git" / "objects").rglob("*") if p.is_file())
    os.link(target, world.base / "shared-object")


def break_remote(world, src):
    git(src, "remote", "add", "origin", str(world.upstream), home=world.home)


def break_alternates(world, src):
    info = src / ".git" / "objects" / "info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "alternates").write_text(f"{world.upstream}/.git/objects\n")


def break_commondir(world, src):
    (src / ".git" / "commondir").write_text(f"{world.upstream}/.git\n")


def break_symlink(world, src):
    (src / ".git" / "hooks-link").symlink_to(world.upstream)


def break_include(world, src):
    with (src / ".git" / "config").open("a") as handle:
        handle.write(f"[include]\n\tpath = {world.upstream}/.git/config\n")


def break_pointer_file(world, src):
    shutil.rmtree(src / ".git")
    (src / ".git").write_text(f"gitdir: {world.upstream}/.git\n")


def break_dir_link(world, src):
    shutil.rmtree(src / ".git")
    (src / ".git").symlink_to(world.upstream / ".git")


def break_bad_head(world, src):
    (src / ".git" / "HEAD").write_text("not a commit\n")


def break_short_head(world, src):
    (src / ".git" / "HEAD").write_text("a" * 39 + "\n")


HAZARDS = [break_hardlink, break_remote, break_alternates, break_commondir, break_symlink,
           break_include, break_pointer_file, break_dir_link, break_bad_head, break_short_head]


@pytest.mark.parametrize("hazard", HAZARDS, ids=lambda fn: fn.__name__)
def test_a_clone_that_is_not_independent_or_resolvable_is_refused(world, gitbuild, hazard):
    hazard(world, gitbuild.src_dir)
    before = snapshot(world.upstream)
    with pytest.raises(fc.FixtureSafetyError):
        af.assert_git_fixture_clone(gitbuild.src_dir, original=world.upstream)
    assert snapshot(world.upstream) == before  # only ever read


def test_local_hardlink_clone_is_refused_but_no_local_is_not(world):
    world.clone("--local")  # the default local clone: objects share inodes with the original
    with pytest.raises(fc.FixtureSafetyError, match="hard-linked"):
        af.assert_git_fixture_clone(world.src)
    shutil.rmtree(world.src)
    world.clone("--no-local")
    assert af.assert_git_fixture_clone(world.src) == world.sha


def test_the_clone_nested_in_or_around_the_original_is_refused(world, gitbuild):
    with pytest.raises(fc.FixtureSafetyError, match="resolves into the original"):
        af.assert_git_fixture_clone(gitbuild.src_dir, original=world.base)  # original contains it
    with pytest.raises(fc.FixtureSafetyError, match="resolves into the original"):
        af.assert_git_fixture_clone(gitbuild.src_dir, original=gitbuild.src_dir)


def test_identity_digest_moves_with_head_and_ignores_the_index(world, gitbuild):
    before = af.git_identity_digest(gitbuild.src_dir)
    (gitbuild.src_dir / "untracked.txt").write_text("x")
    git(gitbuild.src_dir, "status", "--short", home=world.home)  # may rewrite the index
    assert af.git_identity_digest(gitbuild.src_dir) == before
    (gitbuild.src_dir / "z.py").write_text("# moved\n")
    git(gitbuild.src_dir, "commit", "-q", "-am", "move", home=world.home)
    assert af.git_identity_digest(gitbuild.src_dir) != before
    assert af.build_git_head(gitbuild.src_dir) != world.sha


# ---- copy for mutation --------------------------------------------------------------------


def test_git_copy_is_independent_keeps_metadata_and_a_swap_moves_only_the_fingerprint(
        world, gitbuild, tmp_path, monkeypatch):
    monkeypatch.setattr(af, "verify_copy_isolation", lambda build, original_src: None)
    original_before = snapshot(world.base / "builds")
    upstream_before = snapshot(world.upstream)
    copy = af.copy_build_for_mutation(
        world.base / "builds", LABEL, tmp_path / "copies", files=FILES)
    assert snapshot(world.base / "builds") == original_before
    assert af.build_git_head(copy.src_dir) == world.sha
    assert af.git_identity_digest(copy.src_dir) == af.git_identity_digest(gitbuild.src_dir)
    assert af.assert_git_fixture_clone(copy.src_dir, original=gitbuild.src_dir) == world.sha
    # Independent objects: every copied .git file is its own inode, and no link leads back.
    for path in (copy.src_dir / ".git").rglob("*"):
        if path.is_file():
            twin = gitbuild.src_dir / path.relative_to(copy.src_dir)
            assert not twin.exists() or not os.path.samefile(path, twin)
    # A source swap in the copy: the fingerprint moves, the git identity and the original do not.
    fingerprint = compute_read_bridge_fingerprint(copy.src_dir, FILES)
    digest = af.git_identity_digest(copy.src_dir)
    af.mutate_swap_file(copy, FILES, READ_FILES)
    assert compute_read_bridge_fingerprint(copy.src_dir, FILES) != fingerprint
    assert af.build_git_head(copy.src_dir) == world.sha
    assert af.git_identity_digest(copy.src_dir) == digest
    assert snapshot(world.base / "builds") == original_before
    assert snapshot(world.upstream) == upstream_before


@pytest.mark.parametrize("hazard", [break_hardlink, break_remote, break_alternates,
                                    break_symlink, break_dir_link, break_pointer_file,
                                    break_commondir, break_include], ids=lambda f: f.__name__)
def test_git_copy_of_a_non_independent_original_is_refused_before_any_mutation(
        world, gitbuild, tmp_path, monkeypatch, hazard):
    hazard(world, gitbuild.src_dir)
    monkeypatch.setattr(af, "verify_copy_isolation", lambda build, original_src: None)

    def never(*args, **kwargs):
        raise AssertionError("an unsafe source reached the copy or the repoint")

    monkeypatch.setattr(af.shutil, "copytree", never)
    monkeypatch.setattr(af, "_retarget_venv", never)
    before = (snapshot(world.base / "builds"), snapshot(world.upstream))
    with pytest.raises(fc.FixtureSafetyError):
        af.copy_build_for_mutation(world.base / "builds", LABEL, tmp_path / "copies")
    assert (snapshot(world.base / "builds"), snapshot(world.upstream)) == before
    assert not (tmp_path / "copies").exists()  # not even the destination parent was created


def test_archive_copy_that_grew_a_git_is_refused(tmp_path, world, monkeypatch):
    (world.src / "gateway").mkdir(parents=True)
    (world.src / "gateway" / "a.py").write_text("# a\n")
    world.build()
    monkeypatch.setattr(af, "verify_copy_isolation", lambda build, original_src: None)
    dest = tmp_path / "copies" / LABEL / "src"
    real_check = af.assert_copy_contained

    def grown(dest_dir, original):
        real_check(dest_dir, original)
        (Path(dest_dir) / ".git").mkdir()  # a .git that the original never had

    monkeypatch.setattr(af, "assert_copy_contained", grown)
    with pytest.raises(fc.FixtureSafetyError, match=r"unexpectedly contains a \.git"):
        af.copy_build_for_mutation(world.base / "builds", LABEL, tmp_path / "copies")
    assert not dest.exists()


# ---- receipts: kind, SHA and source binding -----------------------------------------------


def test_good_git_provisional_receipt_installs_with_its_sha(world, gitbuild, tmp_path):
    out = make_fixture(tmp_path)
    receipt = write_receipt(tmp_path / "r.json", [entry(gitbuild, world.sha)])
    installed = af.install_approval_fixture_entry(gitbuild, out, receipt)
    assert installed["git_sha"] == world.sha == installed["source_sha"]
    target = out / "_hmp_plugin" / "approval_supported_builds.json"
    assert compat.load_read_compat_list(target).builds[0].git_sha == world.sha
    committed = REPO_ROOT / "server" / "hmp_plugin" / "approval_supported_builds.json"
    assert json.loads(committed.read_text())["builds"] == []  # production stays empty


@pytest.mark.parametrize("case", [
    "archive-entry-on-git-build", "other-sha", "source-sha-differs", "short-sha", "uppercase-sha",
    "head-moved", "git-removed", "stale-source", "git-entry-on-archive",
])
def test_git_receipt_refusals(world, gitbuild, tmp_path, case):
    out = make_fixture(tmp_path)
    path = tmp_path / "r.json"
    build, sha = gitbuild, world.sha
    if case == "archive-entry-on-git-build":
        write_receipt(path, [entry(build, None)])
    elif case == "other-sha":
        write_receipt(path, [entry(build, "b" * 40)])
    elif case == "source-sha-differs":
        write_receipt(path, [entry(build, sha, source_sha="d" * 40)])
    elif case == "short-sha":
        write_receipt(path, [entry(build, sha[:39])])
    elif case == "uppercase-sha":
        write_receipt(path, [entry(build, sha.upper())])
    elif case == "head-moved":
        write_receipt(path, [entry(build, sha)])
        (build.src_dir / "docs.txt").write_text("x")
        git(build.src_dir, "add", "docs.txt", home=world.home)
        git(build.src_dir, "commit", "-q", "-m", "drift", home=world.home)
    elif case == "git-removed":
        write_receipt(path, [entry(build, sha)])
        shutil.rmtree(build.src_dir / ".git")
    elif case == "stale-source":
        write_receipt(path, [entry(build, sha)])
        (build.src_dir / "z.py").write_text("# changed after the receipt\n")
    else:  # a git SHA on a tree that has no .git at all
        shutil.rmtree(build.src_dir / ".git")
        write_receipt(path, [entry(build, sha)])
    target = out / "_hmp_plugin" / "approval_supported_builds.json"
    before = target.read_bytes()
    with pytest.raises(fc.FixtureSafetyError):
        af.install_approval_fixture_entry(build, out, path)
    assert target.read_bytes() == before


def test_archive_entry_on_archive_build_still_installs(tmp_path):
    src = tmp_path / "builds" / LABEL / "src"
    for rel in FILES:
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(f"# {rel}\n")
    (src / ".venv" / "bin").mkdir(parents=True)
    (src / ".venv" / "bin" / "python3").touch()
    build = fc.BuildInfo(LABEL, src, src / ".venv" / "bin" / "python3")
    out = make_fixture(tmp_path)
    receipt = write_receipt(tmp_path / "r.json", [entry(build, None)])
    assert af.install_approval_fixture_entry(build, out, receipt)["git_sha"] is None


def test_final_git_receipt_binds_kind_and_sha_exactly(world, gitbuild, tmp_path):
    plugin = make_fixture(tmp_path) / "_hmp_plugin"
    path = tmp_path / "final.json"
    sha = world.sha

    def check(entry_sha=sha, **overrides):
        write_receipt(path, [final_entry(gitbuild, entry_sha)],
                      extra={"evidence": evidence(gitbuild, plugin, sha, **overrides)})
        return validate_final(path, gitbuild, plugin)

    assert check()["git_sha"] == sha
    cases = {
        "archive-kind": {"kind": af.RECEIPT_KIND},
        "unknown-kind": {"kind": "something-else"},
        "missing-evidence-sha": {"git_sha": None},
        "other-evidence-sha": {"git_sha": "b" * 40},
        "short-evidence-sha": {"git_sha": sha[:39]},
        "source-sha-differs": {"source_sha": "d" * 40},
        "unverified-upstream": {"upstream_verified": False},
        "stale-read": {"read_fingerprint": "0" * 64},
        "stale-direct": {"direct_send_fingerprint": "0" * 64},
        "other-tests": {"required_tests": af.required_test_names("another-build")},
    }
    for name, override in cases.items():
        with pytest.raises(fc.FixtureSafetyError):
            check(**override)
        assert name
    # Evidence whose sha disagrees with the entry is refused even when evidence matches HEAD.
    with pytest.raises(fc.FixtureSafetyError):
        check(entry_sha="b" * 40)


def test_archive_and_git_receipts_are_never_interchangeable(world, gitbuild, tmp_path):
    plugin = make_fixture(tmp_path) / "_hmp_plugin"
    path = tmp_path / "final.json"
    # A valid archive-kind receipt (git_sha None) presented for the git build.
    write_receipt(path, [final_entry(gitbuild, None)],
                  extra={"evidence": evidence(gitbuild, plugin, None)})
    with pytest.raises(fc.FixtureSafetyError):
        validate_final(path, gitbuild, plugin)
    # A valid git-kind receipt presented for an archive copy of the same files.
    archive = tmp_path / "archive" / LABEL / "src"
    for rel in FILES:
        (archive / rel).parent.mkdir(parents=True, exist_ok=True)
        (archive / rel).write_text(f"# {rel}\n")
    build = fc.BuildInfo(LABEL, archive, archive / ".venv" / "bin" / "python3")
    write_receipt(path, [final_entry(build, world.sha)],
                  extra={"evidence": evidence(build, plugin, world.sha)})
    with pytest.raises(fc.FixtureSafetyError, match=r"no \.git|git_sha"):
        validate_final(path, build, plugin)
    # Same files, git kind evidence on an archive entry: kind mismatch.
    write_receipt(path, [final_entry(build, None)], extra={
        "evidence": evidence(build, plugin, None, kind=af.RECEIPT_KIND_GIT)})
    with pytest.raises(fc.FixtureSafetyError, match="kind"):
        validate_final(path, build, plugin)
    # An archive receipt that smuggles a git_sha in its evidence is refused.
    write_receipt(path, [final_entry(build, None)], extra={
        "evidence": evidence(build, plugin, None, git_sha=world.sha)})
    with pytest.raises(fc.FixtureSafetyError, match="git_sha"):
        validate_final(path, build, plugin)


def test_direct_send_fixture_entry_binds_the_git_head(world, gitbuild, tmp_path):
    out = make_fixture(tmp_path)
    direct = {"label": LABEL, "git_sha": world.sha, "source_sha": world.sha,
              "qualified_by": "unit", "qualified_at": "x",
              "fingerprint": compute_read_bridge_fingerprint(gitbuild.src_dir, DIRECT_FILES)}
    receipt = tmp_path / "direct.json"
    receipt.write_text(json.dumps({"format": 1, "bridge_files": DIRECT_FILES, "builds": [direct]}))
    dsf.install_fixture_qualification(gitbuild, out, receipt)
    target = out / "_hmp_plugin" / "direct_send_supported_builds.json"
    assert json.loads(target.read_text())["builds"][0]["git_sha"] == world.sha
    # A fingerprint-only (archive) direct-send entry never installs onto a git build.
    receipt.write_text(json.dumps(
        {"format": 1, "bridge_files": DIRECT_FILES, "builds": [{**direct, "git_sha": None}]}))
    with pytest.raises(fc.FixtureSafetyError, match="no exact"):
        dsf.install_fixture_qualification(gitbuild, out, receipt)


def test_rebind_keeps_the_git_sha_and_refuses_a_moved_head(world, gitbuild, tmp_path):
    out = make_fixture(tmp_path)
    receipt = write_receipt(tmp_path / "r.json", [entry(gitbuild, world.sha)])
    af.install_approval_fixture_entry(gitbuild, out, receipt)
    before = compute_read_bridge_fingerprint(gitbuild.src_dir, FILES)
    (gitbuild.src_dir / af.SWAP_FILE).write_text("# swapped\n")  # worktree change, HEAD unchanged
    old, new = af.rebind_fixture_entry(gitbuild, out, note="in-place swap")
    assert old == before != new
    rebound = json.loads((out / "_hmp_plugin" / "approval_supported_builds.json").read_text())
    assert rebound["builds"][0]["git_sha"] == world.sha
    git(gitbuild.src_dir, "commit", "-q", "-am", "moved", home=world.home)
    with pytest.raises(fc.FixtureSafetyError, match="git HEAD"):
        af.rebind_fixture_entry(gitbuild, out, note="moved head")


# ---- the real runtime reader and baseline over a real .git ---------------------------------


def runtime_baseline(build: fc.BuildInfo, out: Path, tmp_path: Path):
    """The real factory's baseline capture (`compat._capture_approval_baseline`) over the fixture
    manifests, with the read entry bootstrapped exactly as `build_fixture` does."""
    plugin = out / "_hmp_plugin"
    read_files = json.loads((plugin / "read_compat_builds.json").read_text())["bridge_files"]
    identity = compat.GitFingerprintReader(read_files).read(build.src_dir)
    assert identity is not None
    return identity, compat._capture_approval_baseline(
        identity, build.src_dir, plugin / "approval_supported_builds.json",
        plugin / "read_compat_builds.json")


def test_runtime_factory_admits_only_the_exact_git_entry(world, gitbuild, tmp_path):
    out = make_fixture(tmp_path)
    identity, closed = runtime_baseline(gitbuild, out, tmp_path)
    assert identity.git_sha == world.sha and closed is None  # empty manifest: never admitted
    read = out / "_hmp_plugin" / "read_compat_builds.json"
    read.write_text(json.dumps({"format": 1, "bridge_files": READ_FILES, "builds": [{
        **entry(gitbuild, world.sha), "fingerprint": identity.fingerprint,
        "qualified_by": "unit bootstrap"}]}))
    # An archive-style (fingerprint-only) entry never matches a git install.
    af_path = out / "_hmp_plugin" / "approval_supported_builds.json"
    archive = write_receipt(tmp_path / "a.json", [entry(gitbuild, None)])
    shutil.copy(archive, af_path)
    assert runtime_baseline(gitbuild, out, tmp_path)[1] is None
    # The exact git entry admits, carrying the same full SHA.
    shutil.copy(write_receipt(tmp_path / "g.json", [entry(gitbuild, world.sha)]), af_path)
    baseline = runtime_baseline(gitbuild, out, tmp_path)[1]
    assert baseline is not None and baseline.git_sha == world.sha
    # A different SHA on an otherwise identical entry stays closed.
    shutil.copy(write_receipt(tmp_path / "w.json", [entry(gitbuild, "b" * 40)]), af_path)
    assert runtime_baseline(gitbuild, out, tmp_path)[1] is None


def test_source_mutation_keeps_the_sha_and_closes_the_gate(world, gitbuild, tmp_path):
    out = make_fixture(tmp_path)
    identity, _ = runtime_baseline(gitbuild, out, tmp_path)
    read = out / "_hmp_plugin" / "read_compat_builds.json"
    read.write_text(json.dumps({"format": 1, "bridge_files": READ_FILES, "builds": [{
        **entry(gitbuild, world.sha), "fingerprint": identity.fingerprint,
        "qualified_by": "unit bootstrap"}]}))
    receipt = write_receipt(tmp_path / "g.json", [entry(gitbuild, world.sha)])
    af.install_approval_fixture_entry(gitbuild, out, receipt)
    assert runtime_baseline(gitbuild, out, tmp_path)[1] is not None
    sha_before = af.build_git_head(gitbuild.src_dir)
    (gitbuild.src_dir / af.SWAP_FILE).write_text("# approval-only swap\n")
    assert af.build_git_head(gitbuild.src_dir) == sha_before  # SHA unchanged ...
    assert runtime_baseline(gitbuild, out, tmp_path)[1] is None  # ... but the gate is closed
    af.rebind_fixture_entry(gitbuild, out, note="requalified fixture")
    assert runtime_baseline(gitbuild, out, tmp_path)[1] is not None  # only a re-issued entry opens


# ---- matrix driver: the git mode ----------------------------------------------------------


def matrix_args(world: World, tmp_path: Path, *extra: str, sha: str | None = None) -> list[str]:
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    return ["--builds-dir", str(world.base / "builds"), "--label", LABEL,
            "--expected-source-sha", sha or world.sha, "--out", str(out), *extra]


def run_identity(world: World, tmp_path: Path, *extra: str, sha: str | None = None):
    parser_args = matrix_args(world, tmp_path, "--only", "identity", *extra, sha=sha)
    code = approval_matrix.main(parser_args)
    summary = json.loads((tmp_path / "out" / "matrix.json").read_text())
    return code, summary


@pytest.fixture
def git_identity_env(monkeypatch):
    """The synthetic trees have no real venv or Hermes: stub only the interpreter version and the
    three boundary lists identity reads, never the git checks under test."""
    lists = {approval_matrix.APPROVAL_COMPAT_PATH: FILES,
             approval_matrix.DIRECT_COMPAT_PATH: DIRECT_FILES,
             approval_matrix.READ_COMPAT_PATH: READ_FILES}
    monkeypatch.setattr(approval_matrix, "_python_version",
                        lambda python: approval_matrix.PINNED_PYTHON)
    monkeypatch.setattr(approval_matrix, "_files", lambda path: list(lists[path]))


def test_git_mode_identity_accepts_an_independent_clone_at_the_expected_sha(
        world, gitbuild, tmp_path, git_identity_env):
    code, summary = run_identity(world, tmp_path, "--git-install",
                                 "--upstream-source", str(world.upstream))
    assert code == 0 and summary["stages"] == {"identity": True}, summary


def test_archive_mode_refuses_a_git_build_and_git_mode_refuses_an_archive(
        world, gitbuild, tmp_path, git_identity_env):
    code, summary = run_identity(world, tmp_path)
    assert code == 1 and "--git-install" in summary["errors"]["identity"]
    shutil.rmtree(gitbuild.src_dir / ".git")
    code, summary = run_identity(world, tmp_path, "--git-install")
    assert code == 1 and "no .git" in summary["errors"]["identity"]


@pytest.mark.parametrize(
    "case", ["wrong-sha", "short-sha", "hardlinked", "remote", "shared-with-upstream"])
def test_git_mode_identity_refusals(world, tmp_path, git_identity_env, case):
    build = world.clone("--local" if case == "hardlinked" else "--no-local",
                        keep_remote=case == "remote")
    sha = "b" * 40 if case == "wrong-sha" else world.sha[:39] if case == "short-sha" else None
    extra = ["--git-install"]
    if case == "shared-with-upstream":
        shutil.rmtree(build.src_dir / ".git")
        (build.src_dir / ".git").symlink_to(world.upstream / ".git")
        extra += ["--upstream-source", str(world.upstream)]
    code, summary = run_identity(world, tmp_path, *extra, sha=sha)
    assert code == 1 and summary["stages"] == {"identity": False}, summary
    assert not (tmp_path / "out" / "receipt.json").exists()


def test_git_mode_identity_needs_the_upstream_head_to_agree(world, gitbuild, tmp_path,
                                                            git_identity_env):
    (world.upstream / "later.txt").write_text("x")
    git(world.upstream, "add", "later.txt", home=world.home)
    git(world.upstream, "commit", "-q", "-m", "later", home=world.home)
    code, summary = run_identity(world, tmp_path, "--git-install",
                                 "--upstream-source", str(world.upstream))
    assert code == 1 and "upstream" in summary["errors"]["identity"], summary


def test_stability_closes_on_source_drift_or_a_moved_head(world, gitbuild, tmp_path,
                                                          git_identity_env):
    args = approval_matrix.argparse.Namespace(
        builds_dir=world.base / "builds", label=LABEL, expected_source_sha=world.sha,
        out=tmp_path / "out", upstream_source=None, git_install=True)
    (tmp_path / "out").mkdir()
    matrix = approval_matrix.Matrix(args)
    matrix.stage_identity()
    matrix.stage_stability()  # unchanged: passes
    (gitbuild.src_dir / "z.py").write_text("# source drift\n")
    with pytest.raises(RuntimeError, match="fingerprint changed"):
        matrix.stage_stability()
    (gitbuild.src_dir / "z.py").write_text("# z.py\n")
    matrix.stage_stability()
    git(gitbuild.src_dir, "commit", "-q", "--allow-empty", "-m", "moved", home=world.home)
    with pytest.raises(RuntimeError, match="git_head changed"):
        matrix.stage_stability()


def test_git_mode_is_documented_and_the_production_manifest_is_empty():
    assert "--git-install" in approval_matrix.__doc__
    committed = REPO_ROOT / "server" / "hmp_plugin" / "approval_supported_builds.json"
    assert json.loads(committed.read_text())["builds"] == []


# ---- standalone helpers never borrow a HEAD -------------------------------------------------


def test_independent_git_head_is_none_for_an_archive_and_refuses_a_dangling_link(tmp_path, world):
    (world.src).mkdir(parents=True)
    assert af.independent_git_head(world.src) is None
    (world.src / ".git").symlink_to(tmp_path / "nowhere")
    with pytest.raises(fc.FixtureSafetyError):
        af.independent_git_head(world.src)


@pytest.mark.parametrize("hazard", [break_pointer_file, break_commondir, break_alternates,
                                    break_include], ids=lambda f: f.__name__)
def test_direct_send_install_refuses_a_borrowed_head(world, gitbuild, tmp_path, hazard):
    out = make_fixture(tmp_path)
    direct = {"label": LABEL, "git_sha": world.sha, "source_sha": world.sha,
              "qualified_by": "unit", "qualified_at": "x",
              "fingerprint": compute_read_bridge_fingerprint(gitbuild.src_dir, DIRECT_FILES)}
    receipt = tmp_path / "direct.json"
    receipt.write_text(json.dumps({"format": 1, "bridge_files": DIRECT_FILES, "builds": [direct]}))
    target = out / "_hmp_plugin" / "direct_send_supported_builds.json"
    before = target.read_bytes()
    hazard(world, gitbuild.src_dir)
    with pytest.raises(fc.FixtureSafetyError):
        dsf.install_fixture_qualification(gitbuild, out, receipt)
    assert target.read_bytes() == before


@pytest.mark.parametrize("hazard", [break_pointer_file, break_commondir, break_alternates,
                                    break_include], ids=lambda f: f.__name__)
def test_rebind_refuses_a_borrowed_head(world, gitbuild, tmp_path, hazard):
    out = make_fixture(tmp_path)
    receipt = write_receipt(tmp_path / "r.json", [entry(gitbuild, world.sha)])
    af.install_approval_fixture_entry(gitbuild, out, receipt)
    target = out / "_hmp_plugin" / "approval_supported_builds.json"
    before = target.read_bytes()
    hazard(world, gitbuild.src_dir)
    with pytest.raises(fc.FixtureSafetyError):
        af.rebind_fixture_entry(gitbuild, out, note="borrowed head")
    assert target.read_bytes() == before


def _bootstrap(build, plugin_dir, monkeypatch, *, fingerprint, git_sha):
    import build_fixture as bf
    fake = subprocess.CompletedProcess(
        [], 0, json.dumps({"fingerprint": fingerprint, "git_sha": git_sha}), "")
    monkeypatch.setattr(bf.fc, "run_seed_script", lambda *a, **k: fake)
    bf.bootstrap_compat_entry(build, plugin_dir)
    return json.loads((plugin_dir / "read_compat_builds.json").read_text())["builds"]


def test_bootstrap_binds_only_an_independent_head(world, gitbuild, tmp_path, monkeypatch):
    plugin = make_fixture(tmp_path) / "_hmp_plugin"
    (plugin / "read_compat_builds.json").write_text(
        json.dumps({"format": 1, "bridge_files": READ_FILES, "builds": []}))
    builds = _bootstrap(gitbuild, plugin, monkeypatch, fingerprint="f" * 64, git_sha=world.sha)
    assert builds[0]["git_sha"] == world.sha == builds[0]["source_sha"]


@pytest.mark.parametrize("hazard", [break_pointer_file, break_commondir, break_include],
                         ids=lambda f: f.__name__)
def test_bootstrap_refuses_a_borrowed_head(world, gitbuild, tmp_path, monkeypatch, hazard):
    plugin = make_fixture(tmp_path) / "_hmp_plugin"
    target = plugin / "read_compat_builds.json"
    target.write_text(json.dumps({"format": 1, "bridge_files": READ_FILES, "builds": []}))
    before = target.read_bytes()
    hazard(world, gitbuild.src_dir)
    with pytest.raises(fc.FixtureSafetyError):
        _bootstrap(gitbuild, plugin, monkeypatch, fingerprint="f" * 64, git_sha=world.sha)
    assert target.read_bytes() == before
