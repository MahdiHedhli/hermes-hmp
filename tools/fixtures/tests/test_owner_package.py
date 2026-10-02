"""Owner-local package tool: only the packaging risks (unexpected delta, wrong SHA/fingerprint,
refused file kinds, receipt misbinding). Synthetic trees and a tiny git repo; no Hermes import."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

COMPAT = Path(__file__).resolve().parents[2] / "compat"
sys.path.insert(0, str(COMPAT))
import owner_package as op  # noqa: E402

PLUGIN_SRC = Path(__file__).resolve().parents[3] / "server" / "hmp_plugin"
SHA = "a" * 40
FILES = ["gateway/a.py"]


def entry(fingerprint: str = "b" * 64, git_sha: str = SHA) -> dict:
    return op.make_entry(label="l", fingerprint=fingerprint, git_sha=git_sha, source_sha=git_sha,
                         qualified_by="by", qualified_at="2026-10-01T00:00:00+00:00")


def manifest(extra: dict | None = None) -> tuple[int, bytes]:
    return 0o100644, op._dump({"format": 1, "bridge_files": FILES, "builds": [], **(extra or {})})


def source_tree() -> op.Tree:
    return {
        op.APPROVAL: manifest(),
        op.DIRECT: manifest({"requalification_required": [{"label": "old"}]}),
        "server/hmp_plugin/x.py": (0o100644, b"print(1)\n"),
    }


def entries() -> dict:
    return {op.APPROVAL: entry(), op.DIRECT: entry("c" * 64)}


def rewrite(tree: op.Tree, path: str, **changes) -> None:
    raw = json.loads(tree[path][1])
    raw.update(changes)
    tree[path] = (0o100644, op._dump(raw))


def test_apply_changes_only_builds():
    src = source_tree()
    out = op.apply_entries(src, entries())
    assert op.check_delta(src, out, entries()) == sorted(op.MANIFESTS)
    assert "requalification_required" in json.loads(out[op.DIRECT][1])


@pytest.mark.parametrize("mutate", [
    lambda t: t.__setitem__("server/hmp_plugin/x.py", (0o100644, b"print(2)\n")),
    lambda t: t.__setitem__("server/hmp_plugin/new.py", (0o100644, b"")),
    lambda t: t.__setitem__("server/hmp_plugin/x.py", (0o100755, b"print(1)\n")),
    lambda t: t.pop("server/hmp_plugin/x.py"),
    lambda t: rewrite(t, op.APPROVAL, bridge_files=[*FILES, "z.py"]),
    lambda t: rewrite(t, op.DIRECT, requalification_required=[]),
    lambda t: rewrite(t, op.APPROVAL, builds=[{**entry(), "invented": 1}]),
])
def test_unexpected_delta_refused(mutate):
    src = source_tree()
    out = op.apply_entries(src, entries())
    mutate(out)
    with pytest.raises(op.PackageRefusalError):
        op.check_delta(src, out, entries())


def test_prepopulated_or_noncanonical_source_refused():
    src = source_tree()
    rewrite(src, op.APPROVAL, builds=[entry()])
    with pytest.raises(op.PackageRefusalError, match="already lists"):
        op.apply_entries(src, entries())
    src = source_tree()
    src[op.DIRECT] = (0o100644, src[op.DIRECT][1].replace(b"  ", b"    "))
    with pytest.raises(op.PackageRefusalError, match="canonical"):
        op.apply_entries(src, entries())


def test_entry_must_be_exact_git_and_lowercase():
    with pytest.raises(op.PackageRefusalError):
        op.make_entry(label="l", fingerprint="b" * 64, git_sha=SHA, source_sha="d" * 40,
                      qualified_by="x", qualified_at="y")
    with pytest.raises(op.PackageRefusalError):
        entry(fingerprint="B" * 64)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-C", str(repo), *args],
        check=True, capture_output=True, text=True).stdout.strip()


def commit_repo(repo: Path) -> str:
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "x")
    return git(repo, "rev-parse", "HEAD")


def test_symlink_in_source_refused(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "a").write_text("a")
    os.symlink("a", repo / "link")
    commit_repo(repo)
    with pytest.raises(op.PackageRefusalError, match="non-regular"):
        op.read_git_tree(repo, "HEAD")


def test_dirty_or_wrong_head_refused(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "a").write_text("a")
    head = commit_repo(repo)
    op.require_clean_head(repo, head, what="t")
    with pytest.raises(op.PackageRefusalError, match="not the expected"):
        op.require_clean_head(repo, "0" * 40, what="t")
    (repo / "a").write_text("b")
    with pytest.raises(op.PackageRefusalError, match="modified"):
        op.require_clean_head(repo, head, what="t")


@pytest.fixture
def staged(tmp_path):
    """A tiny Hermes git tree plus a plugin copy whose manifests carry its real fingerprint."""
    hermes = tmp_path / "hermes"
    (hermes / "gateway").mkdir(parents=True)
    (hermes / "gateway" / "a.py").write_text("x = 1\n")
    head = commit_repo(hermes)
    plugin = tmp_path / "plugin"
    shutil.copytree(PLUGIN_SRC, plugin / "server" / "hmp_plugin",
                    ignore=shutil.ignore_patterns("__pycache__"))
    parser = op._PackageParser(plugin / "server" / "hmp_plugin")
    try:
        fingerprint = parser.compat.compute_read_bridge_fingerprint(hermes, FILES)
    finally:
        parser.close()
    for rel in op.MANIFESTS:
        path = plugin / rel
        raw = json.loads(path.read_text())
        raw["bridge_files"], raw["builds"] = FILES, [entry(fingerprint, head)]
        path.write_text(json.dumps(raw, indent=2) + "\n")
    return plugin, hermes, head, fingerprint


def run_match(staged, **over):
    plugin, hermes, head, fingerprint = staged
    expected = {p: over.get("fp", fingerprint) for p in op.MANIFESTS}
    return op.check_runtime_match(plugin, hermes, over.get("sha", head), expected)


def test_runtime_match_selects_the_entry(staged):
    assert all(v["matched"] for v in run_match(staged).values())
    assert not list(staged[0].rglob("__pycache__"))


def test_runtime_match_refuses_wrong_sha_fingerprint_and_entry(staged):
    plugin = staged[0]
    with pytest.raises(op.PackageRefusalError):
        run_match(staged, sha="0" * 40)
    with pytest.raises(op.PackageRefusalError, match="fingerprint differs"):
        run_match(staged, fp="d" * 64)
    path = plugin / op.DIRECT
    raw = json.loads(path.read_text())
    raw["builds"][0]["git_sha"] = raw["builds"][0]["source_sha"] = "e" * 40
    path.write_text(json.dumps(raw, indent=2) + "\n")
    with pytest.raises(op.PackageRefusalError, match="match_build"):
        run_match(staged)


def test_runtime_match_refuses_modified_hermes_tree(staged):
    (staged[1] / "gateway" / "a.py").write_text("x = 2\n")
    with pytest.raises(op.PackageRefusalError, match="modified"):
        run_match(staged)


def test_write_package_is_private_and_outside_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    tree = {"a/b.py": (0o100644, b"1"), "t.py": (0o100755, b"2")}
    with pytest.raises(op.PackageRefusalError, match="outside"):
        op.write_package(tree, repo / "sub", repo)
    root = op.write_package(tree, tmp_path, repo)
    assert root.stat().st_mode & 0o777 == 0o700
    assert (root / "plugin" / "a").stat().st_mode & 0o777 == 0o700
    assert (root / "plugin/a/b.py").stat().st_mode & 0o777 == 0o600
    assert (root / "plugin/t.py").stat().st_mode & 0o777 == 0o700
    assert op.read_package_tree(root / "plugin") == tree


def test_package_tree_refuses_link_bytecode_and_loose_modes(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    plugin = op.write_package({"a.py": (0o100644, b"1")}, tmp_path, repo) / "plugin"
    os.link(plugin / "a.py", tmp_path / "outside")
    with pytest.raises(op.PackageRefusalError, match="unlinked"):
        op.read_package_tree(plugin)
    os.unlink(tmp_path / "outside")
    os.chmod(plugin / "a.py", 0o644)
    with pytest.raises(op.PackageRefusalError, match="group/world"):
        op.read_package_tree(plugin)
    os.chmod(plugin / "a.py", 0o600)
    os.symlink("a.py", plugin / "s")
    with pytest.raises(op.PackageRefusalError, match="symlink"):
        op.read_package_tree(plugin)
    os.unlink(plugin / "s")
    (plugin / "__pycache__").mkdir(mode=0o700)
    (plugin / "__pycache__" / "a.pyc").write_bytes(b"")
    os.chmod(plugin / "__pycache__" / "a.pyc", 0o600)
    with pytest.raises(op.PackageRefusalError, match="bytecode"):
        op.read_package_tree(plugin)


def check_receipt(tmp_path, package_digest="2" * 64, **ev):
    base = {"plugin_sha256": "1" * 64, "git_sha": SHA, "source_sha": SHA, "complete": True,
            "not_for_commit": True, "approval_fingerprint": "b" * 64,
            "direct_send_fingerprint": "c" * 64}
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps({"evidence": {**base, **ev}}))
    return op.check_source_receipt(
        path, source_digest="1" * 64, package_digest=package_digest, git_sha=SHA,
        fingerprints={op.APPROVAL: "b" * 64, op.DIRECT: "c" * 64})


def test_receipt_binds_source_and_is_stale_for_package(tmp_path):
    assert check_receipt(tmp_path)["stale_for_package_by_digest"] is True
    before = (tmp_path / "receipt.json").read_bytes()
    check_receipt(tmp_path)
    assert (tmp_path / "receipt.json").read_bytes() == before


@pytest.mark.parametrize("kwargs", [
    {"package_digest": "1" * 64},  # empty delta: package equals the source
    {"plugin_sha256": "9" * 64},   # receipt is not for I at all
    {"git_sha": "f" * 40},
    {"direct_send_fingerprint": "e" * 64},
    {"complete": False},
])
def test_receipt_misbinding_refused(tmp_path, kwargs):
    with pytest.raises(op.PackageRefusalError):
        check_receipt(tmp_path, **kwargs)


# ---- the source receipt is validated by the production validator, for I and never for P ----

APPROVAL_FILES = ["gateway/a.py", "tools/approval_prompt.py", "z.py"]
READ_FILES = ["gateway/a.py", "z.py"]
DIRECT_FILES = ["z.py"]
LABEL = "src-build"


class Receipt:
    """A tiny Hermes git clone, a source tree I with its three bridge lists, and a receipt that the
    real validator accepts. Cases then break exactly one thing."""

    def __init__(self, tmp_path: Path) -> None:
        import _fixture_common as fc
        import approval_fixture as af

        from hmp_plugin.compat import compute_read_bridge_fingerprint as fp
        self.af, self.fc, self.tmp = af, fc, tmp_path
        self.hermes = tmp_path / "hermes"
        for rel in APPROVAL_FILES:
            (self.hermes / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.hermes / rel).write_text(f"# {rel}\n")
        self.head = commit_repo(self.hermes)
        self.source: op.Tree = {
            path: (0o100644, op._dump({"format": 1, "bridge_files": files, "builds": []}))
            for path, files in ((op.APPROVAL, APPROVAL_FILES), (op.READ, READ_FILES),
                                (op.DIRECT, DIRECT_FILES))
        }
        self.root = tmp_path / "plugin"
        for path, (_, data) in self.source.items():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_bytes(data)
        self.evidence = {
            "kind": af.RECEIPT_KIND_GIT, "git_sha": self.head, "source_sha": self.head,
            "complete": True, "not_for_commit": True, "label": LABEL, "upstream_verified": True,
            "approval_fingerprint": fp(self.hermes, APPROVAL_FILES),
            "read_fingerprint": fp(self.hermes, READ_FILES),
            "direct_send_fingerprint": fp(self.hermes, DIRECT_FILES),
            "plugin_sha256": op.plugin_digest(self.root),
            "stages": dict.fromkeys(af.REQUIRED_STAGES, True),
            "required_tests": af.required_test_names(LABEL), "junit_sha256": "c" * 64,
        }
        self.entry = {
            "label": LABEL, "fingerprint": self.evidence["approval_fingerprint"],
            "git_sha": self.head, "source_sha": self.head,
            "qualified_by": "approval_matrix (fixture-only; never a manifest entry)",
            "qualified_at": "2026-09-30T00:00:00+00:00",
        }

    def run(self, evidence: dict | None = None, **top) -> None:
        raw = {"format": 1, "bridge_files": APPROVAL_FILES, "builds": [self.entry],
               "evidence": self.evidence if evidence is None else evidence, **top}
        path = self.tmp / "receipt.json"
        path.write_text(json.dumps(raw))
        op.validate_source_receipt(path, source=self.source, source_plugin_root=self.root,
                                   hermes_src=self.hermes, label=LABEL)


@pytest.fixture
def receipt(tmp_path):
    return Receipt(tmp_path)


def test_validator_accepts_the_genuine_source_receipt(receipt):
    receipt.run()


def test_fabricated_complete_flag_is_not_enough(receipt):
    """The old subset accepted exactly this: digest/SHA/fingerprints/complete, nothing else."""
    ev = receipt.evidence
    fabricated = {k: ev[k] for k in ("plugin_sha256", "git_sha", "source_sha", "complete",
                                     "not_for_commit", "approval_fingerprint",
                                     "direct_send_fingerprint")}
    fabricated["kind"] = ev["kind"]
    with pytest.raises(op.PackageRefusalError, match="validator"):
        receipt.run(fabricated)


@pytest.mark.parametrize("case", ["failed-stage", "missing-stage", "extra-stage",
                                  "missing-case", "reordered-cases", "wrong-label-cases",
                                  "stale-read-boundary", "unverified-upstream",
                                  "no-upstream-key", "wrong-kind", "stale-plugin"])
def test_each_validator_rule_refuses_through_the_tool(receipt, case):
    ev, af = receipt.evidence, receipt.af
    ids = af.required_test_names(LABEL)
    stages = dict(ev["stages"])
    first = next(iter(stages))
    bad = {
        "failed-stage": {"stages": {**stages, first: False}},
        "missing-stage": {"stages": {k: v for k, v in stages.items() if k != first}},
        "extra-stage": {"stages": {**stages, "invented": True}},
        "missing-case": {"required_tests": ids[:-1]},
        "reordered-cases": {"required_tests": ids[::-1]},
        "wrong-label-cases": {"required_tests": af.required_test_names("other")},
        "stale-read-boundary": {"read_fingerprint": "0" * 64},
        "unverified-upstream": {"upstream_verified": False},
        "no-upstream-key": {"upstream_verified": None},
        "wrong-kind": {"kind": af.RECEIPT_KIND},
        "stale-plugin": {"plugin_sha256": "0" * 64},
    }[case]
    with pytest.raises(op.PackageRefusalError, match="validator"):
        receipt.run({**ev, **bad})


def test_wrong_schema_receipt_refused(receipt):
    with pytest.raises(op.PackageRefusalError, match="validator"):
        receipt.run(format=2)
    with pytest.raises(op.PackageRefusalError, match="validator"):
        receipt.run(bridge_files=["other.py"])


def test_validator_is_given_i_not_p(receipt, monkeypatch):
    """The delegate sees I's plugin directory and I's lists, final=True, and nothing of P."""
    seen = {}
    real = receipt.af.validate_approval_receipt

    def spy(path, build, **kw):
        seen.update(kw, label=build.label, src=build.src_dir)
        return real(path, build, **kw)

    monkeypatch.setattr(receipt.af, "validate_approval_receipt", spy)
    receipt.run()
    assert seen["final"] is True and seen["label"] == LABEL and seen["src"] == receipt.hermes
    assert seen["plugin_dir"] == receipt.root / "server" / "hmp_plugin"
    assert (seen["target_files"], seen["read_files"], seen["direct_files"]) == (
        APPROVAL_FILES, READ_FILES, DIRECT_FILES)


def test_receipt_for_i_is_refused_against_a_changed_plugin_and_never_edited(receipt):
    """Applying the entries (P) changes the plugin digest, so the I receipt is stale for P: the
    validator refuses it there, and this tool never relabels or re-validates it for P."""
    receipt.run()
    path = receipt.tmp / "receipt.json"
    before = path.read_bytes()
    package = op.apply_entries(receipt.source, entries())
    pkg_root = receipt.tmp / "p"
    for rel, (_, data) in package.items():
        (pkg_root / rel).parent.mkdir(parents=True, exist_ok=True)
        (pkg_root / rel).write_bytes(data)
    assert op.plugin_digest(pkg_root) != receipt.evidence["plugin_sha256"]
    with pytest.raises(op.PackageRefusalError, match="validator"):
        op.validate_source_receipt(path, source=package, source_plugin_root=pkg_root,
                                   hermes_src=receipt.hermes, label=LABEL)
    assert path.read_bytes() == before
