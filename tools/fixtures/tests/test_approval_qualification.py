"""Approval qualification tooling: receipts, fixture-copy install, required-ID JUnit check, runner.

Everything here uses tiny synthetic trees. No Hermes, no gateway, no network and nothing is
written outside pytest's tmp_path. The real matrix is `tools/compat/approval_matrix.py`.
"""
import json
import shutil
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
import bridge_files  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
FILES = ["gateway/a.py", "tools/approval_prompt.py", "z.py"]
READ_FILES = ["gateway/a.py", "z.py"]
LABEL = "fixture-build"
SHA = "a" * 40


def make_build(tmp_path: Path, label: str = LABEL) -> fc.BuildInfo:
    src = tmp_path / "builds" / label / "src"
    for rel in FILES:
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(f"# {rel}\n")
    (src / ".venv" / "bin").mkdir(parents=True)
    python = src / ".venv" / "bin" / "python3"
    python.touch()
    return fc.BuildInfo(label, src, python)


def make_fixture(tmp_path: Path, files: list[str] = FILES) -> Path:
    plugin = tmp_path / "fixture" / "_hmp_plugin"
    plugin.mkdir(parents=True)
    (plugin / "approval_supported_builds.json").write_text(
        json.dumps({"format": 1, "bridge_files": files, "builds": []}))
    (plugin / "direct_send_supported_builds.json").write_text(
        json.dumps({"format": 1, "bridge_files": ["z.py"], "builds": []}))
    (plugin / "mod.py").write_text("# plugin\n")
    return tmp_path / "fixture"


def entry(build: fc.BuildInfo, **overrides) -> dict:
    base = {
        "label": build.label, "git_sha": None, "source_sha": SHA,
        "fingerprint": compute_read_bridge_fingerprint(build.src_dir, FILES),
        "qualified_by": "approval_matrix (provisional fixture bootstrap; integration pending)",
        "qualified_at": "2026-09-30T00:00:00+00:00",
    }
    return {**base, **overrides}


DIRECT_FILES = ["z.py"]


def evidence(build: fc.BuildInfo, plugin: Path, **overrides) -> dict:
    base = {
        "kind": af.RECEIPT_KIND, "complete": True, "label": build.label,
        "source_sha": SHA, "upstream_verified": True,
        "approval_fingerprint": compute_read_bridge_fingerprint(build.src_dir, FILES),
        "read_fingerprint": compute_read_bridge_fingerprint(build.src_dir, READ_FILES),
        "direct_send_fingerprint": compute_read_bridge_fingerprint(build.src_dir, DIRECT_FILES),
        "plugin_sha256": af.plugin_source_digest(plugin),
        "stages": dict.fromkeys(af.REQUIRED_STAGES, True),
        "required_tests": af.required_test_names(build.label),
        "junit_sha256": "c" * 64,
    }
    return {**base, **overrides}


def write_receipt(path: Path, entries: list, *, files=FILES, extra=None) -> Path:
    data = {"format": 1, "bridge_files": files, "builds": entries, **(extra or {})}
    path.write_text(json.dumps(data))
    return path


def test_good_provisional_receipt_installs_only_into_the_fixture_copy(tmp_path):
    build, out = make_build(tmp_path), make_fixture(tmp_path)
    receipt = write_receipt(tmp_path / "r.json", [entry(build)])
    installed = af.install_approval_fixture_entry(build, out, receipt)
    target = out / "_hmp_plugin" / "approval_supported_builds.json"
    data = json.loads(target.read_text())
    assert data["builds"] == [installed] and data["bridge_files"] == FILES  # order preserved
    assert compat.load_read_compat_list(target).builds[0].label == LABEL
    af.remove_approval_fixture_entry(out)
    assert json.loads(target.read_text())["builds"] == []
    # The committed manifest is never a target and stays empty.
    committed = REPO_ROOT / "server" / "hmp_plugin" / "approval_supported_builds.json"
    assert json.loads(committed.read_text())["builds"] == []


def test_direct_send_receipt_never_opens_the_approval_manifest(tmp_path):
    build, out = make_build(tmp_path), make_fixture(tmp_path)
    approval = out / "_hmp_plugin" / "approval_supported_builds.json"
    before = approval.read_bytes()
    direct = {"label": LABEL, "git_sha": None, "qualified_by": "unit", "qualified_at": "x",
              "fingerprint": compute_read_bridge_fingerprint(build.src_dir, ["z.py"])}
    receipt = tmp_path / "direct.json"
    receipt.write_text(json.dumps({"format": 1, "bridge_files": ["z.py"], "builds": [direct]}))
    dsf.install_fixture_qualification(build, out, receipt)
    assert approval.read_bytes() == before
    assert json.loads(approval.read_text())["builds"] == []
    # And the approval installer refuses a direct-send-shaped receipt (different boundary).
    with pytest.raises(fc.FixtureSafetyError, match="boundary"):
        af.install_approval_fixture_entry(build, out, receipt)


def test_plugin_runtime_never_names_the_fixture_receipt_variables():
    for path in (REPO_ROOT / "server" / "hmp_plugin").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "HMP_APPROVAL_QUALIFICATION" not in text, path.name
        assert "HMP_DIRECT_SEND_QUALIFICATION" not in text, path.name


def test_build_offline_hook_is_fixture_tooling_only(tmp_path):
    build, out = make_build(tmp_path), make_fixture(tmp_path)
    assert af.install_from_env(build, out, None) is None
    assert af.install_from_env(build, out, "") is None
    receipt = write_receipt(tmp_path / "r.json", [entry(build)])
    assert af.install_from_env(build, out, str(receipt))["label"] == LABEL


@pytest.mark.parametrize("case", [
    "absent", "not-json", "not-object", "bad-schema", "reordered-boundary", "shorter-boundary",
    "two-builds", "no-builds", "other-label", "stale-source", "git-sha-set",
    "final-without-provisional-text", "provisional-text-missing",
])
def test_receipt_validation_rejects(tmp_path, case):
    build, out = make_build(tmp_path), make_fixture(tmp_path)
    path = tmp_path / "r.json"
    good = entry(build)
    if case == "absent":
        pass
    elif case == "not-json":
        path.write_text("{")
    elif case == "not-object":
        path.write_text("[]")
    elif case == "bad-schema":
        write_receipt(path, [{k: v for k, v in good.items() if k != "qualified_at"}])
    elif case == "reordered-boundary":
        write_receipt(path, [good], files=list(reversed(FILES)))
    elif case == "shorter-boundary":
        write_receipt(path, [good], files=FILES[:2])
    elif case == "two-builds":
        write_receipt(path, [good, entry(build, label="other")])
    elif case == "no-builds":
        write_receipt(path, [])
    elif case == "other-label":
        write_receipt(path, [entry(build, label="another-build")])
    elif case == "stale-source":
        write_receipt(path, [good])
        (build.src_dir / "z.py").write_text("# changed after the receipt\n")
    elif case == "git-sha-set":
        write_receipt(path, [entry(build, git_sha="b" * 40)])
    elif case == "final-without-provisional-text":
        write_receipt(path, [entry(build, qualified_by="final")])  # provisional text required
    else:
        write_receipt(path, [entry(build, qualified_by="qualified for real")])
    target = out / "_hmp_plugin" / "approval_supported_builds.json"
    before = target.read_bytes()
    with pytest.raises(fc.FixtureSafetyError):
        af.install_approval_fixture_entry(build, out, path)
    assert target.read_bytes() == before  # a rejected receipt changes nothing


def final_entry(build: fc.BuildInfo) -> dict:
    return entry(build, qualified_by="approval_matrix (fixture-only; never a manifest entry)")


def test_final_receipt_accepts_only_complete_bound_evidence(tmp_path):
    build = make_build(tmp_path)
    plugin = make_fixture(tmp_path) / "_hmp_plugin"
    path = tmp_path / "final.json"

    def check(**overrides):
        write_receipt(path, [final_entry(build)],
                      extra={"evidence": evidence(build, plugin, **overrides)})
        return af.validate_approval_receipt(
            path, build, target_files=FILES, final=True, plugin_dir=plugin,
            read_files=READ_FILES, direct_files=DIRECT_FILES)

    assert check()["label"] == LABEL
    ids = af.required_test_names(LABEL)
    cases = {
        "no-source-sha": {"source_sha": None},
        "short-source-sha": {"source_sha": "a" * 39},
        "other-source-sha": {"source_sha": "b" * 40},
        "unverified-upstream": {"upstream_verified": False},
        "missing-required-test": {"required_tests": ids[:-1]},
        "extra-required-test": {"required_tests": [*ids, "x::y[z]"]},
        "duplicate-required-test": {"required_tests": [*ids[:-1], ids[0]]},
        "reordered-required-tests": {"required_tests": list(reversed(ids))},
        "other-build-tests": {"required_tests": af.required_test_names("another-build")},
        "no-junit-digest": {"junit_sha256": None},
        "bad-junit-digest": {"junit_sha256": "abc"},
        "stale-direct": {"direct_send_fingerprint": "0" * 64},
        "stage-truthy-not-true": {"stages": dict.fromkeys(af.REQUIRED_STAGES, 1)},
        "incomplete": {"complete": False},
        "stage-failed": {"stages": {**dict.fromkeys(af.REQUIRED_STAGES, True), "timing": False}},
        "stage-missing": {"stages": {"identity": True}},
        "wrong-kind": {"kind": "something-else"},
        "other-build": {"label": "another-build"},
        "other-fingerprint": {"approval_fingerprint": "0" * 64},
        "stale-plugin": {"plugin_sha256": "0" * 64},
        "stale-read": {"read_fingerprint": "0" * 64},
    }
    for name, override in cases.items():
        with pytest.raises(fc.FixtureSafetyError):
            check(**override)
        assert name  # each rejection is independently attributable
    # A missing key is as invalid as a wrong one.
    for key in ("source_sha", "required_tests", "junit_sha256", "upstream_verified",
                "direct_send_fingerprint", "read_fingerprint"):
        stripped = evidence(build, plugin)
        del stripped[key]
        write_receipt(path, [final_entry(build)], extra={"evidence": stripped})
        with pytest.raises(fc.FixtureSafetyError):
            af.validate_approval_receipt(
                path, build, target_files=FILES, final=True, plugin_dir=plugin,
                read_files=READ_FILES, direct_files=DIRECT_FILES)
    # An entry whose source_sha differs from the evidence's is refused.
    write_receipt(path, [entry(build, qualified_by="final", source_sha="d" * 40)],
                  extra={"evidence": evidence(build, plugin)})
    with pytest.raises(fc.FixtureSafetyError, match="source_sha"):
        af.validate_approval_receipt(
            path, build, target_files=FILES, final=True, plugin_dir=plugin,
            read_files=READ_FILES, direct_files=DIRECT_FILES)
    # Every consumer path (no explicit lists) rechecks the plugin's own read and direct manifests.
    (plugin / "read_compat_builds.json").write_text(
        json.dumps({"format": 1, "bridge_files": READ_FILES, "builds": []}))
    write_receipt(path, [final_entry(build)], extra={"evidence": evidence(build, plugin)})
    assert af.validate_approval_receipt(
        path, build, target_files=FILES, final=True, plugin_dir=plugin)["label"] == LABEL
    # A consumer with no boundary at all (manifest unreadable) refuses instead of skipping.
    (plugin / "read_compat_builds.json").unlink()
    write_receipt(path, [final_entry(build)], extra={"evidence": evidence(build, plugin)})
    with pytest.raises(fc.FixtureSafetyError, match="boundary"):
        af.validate_approval_receipt(path, build, target_files=FILES, final=True, plugin_dir=plugin)
    # Missing evidence, or provisional provenance on a final receipt, is refused.
    write_receipt(path, [final_entry(build)])
    with pytest.raises(fc.FixtureSafetyError):
        af.validate_approval_receipt(path, build, target_files=FILES, final=True, plugin_dir=plugin)
    write_receipt(path, [entry(build)], extra={"evidence": evidence(build, plugin)})
    with pytest.raises(fc.FixtureSafetyError, match="provisional"):
        af.validate_approval_receipt(path, build, target_files=FILES, plugin_dir=plugin)
    # A plugin change after issue makes the receipt stale.
    write_receipt(path, [final_entry(build)], extra={"evidence": evidence(build, plugin)})
    (plugin / "mod.py").write_text("# plugin changed\n")
    with pytest.raises(fc.FixtureSafetyError, match="stale"):
        af.validate_approval_receipt(path, build, target_files=FILES, plugin_dir=plugin)


def test_rebind_reissues_the_entry_for_the_current_fingerprint(tmp_path):
    build, out = make_build(tmp_path), make_fixture(tmp_path)
    with pytest.raises(fc.FixtureSafetyError, match="exactly one"):
        af.rebind_fixture_entry(build, out, note="x")
    receipt = write_receipt(tmp_path / "r.json", [entry(build)])
    af.install_approval_fixture_entry(build, out, receipt)
    before = compute_read_bridge_fingerprint(build.src_dir, FILES)
    (build.src_dir / af.SWAP_FILE).write_text("# swapped\n")
    old, new = af.rebind_fixture_entry(build, out, note="in-place swap")
    assert old == before and new == compute_read_bridge_fingerprint(build.src_dir, FILES) != old
    target = out / "_hmp_plugin" / "approval_supported_builds.json"
    parsed = compat.load_read_compat_list(target)
    assert parsed.builds[0].fingerprint == new and "provisional" in parsed.builds[0].qualified_by


def test_mutation_copy_is_disjoint_retargeted_and_leaves_the_original_alone(tmp_path, monkeypatch):
    build = make_build(tmp_path)
    original = build.src_dir
    site = original / ".venv" / "lib" / "python3.14" / "site-packages"
    site.mkdir(parents=True)
    finder = site / "__editable___hermes_agent_finder.py"
    finder.write_text(f"MAPPING = {{'tools': '{original}/tools'}}\n")
    script = original / ".venv" / "bin" / "hermes"
    script.write_text(f"#!{original}/.venv/bin/python3\nprint('hermes')\n")
    monkeypatch.setattr(af, "verify_copy_isolation", lambda build, original_src: None)
    before = (finder.read_bytes(), script.read_bytes())
    dest_builds = tmp_path / "copies"
    copy = af.copy_build_for_mutation(tmp_path / "builds", LABEL, dest_builds, files=FILES)
    new_root = (dest_builds / LABEL / "src").resolve()
    assert copy.src_dir == new_root and copy.venv_python.exists()
    copied_finder = new_root / ".venv/lib/python3.14/site-packages" / finder.name
    assert str(original).encode() not in copied_finder.read_bytes()
    assert str(new_root) in copied_finder.read_text()
    assert (new_root / ".venv/bin/hermes").read_text().startswith(f"#!{new_root}/.venv/bin/python3")
    assert (finder.read_bytes(), script.read_bytes()) == before  # original untouched

    swapped = af.mutate_swap_file(copy, FILES, READ_FILES)
    assert swapped == af.SWAP_FILE
    assert compute_read_bridge_fingerprint(new_root, FILES) != compute_read_bridge_fingerprint(
        original, FILES)
    assert compute_read_bridge_fingerprint(new_root, READ_FILES) == compute_read_bridge_fingerprint(
        original, READ_FILES)
    assert "swap" not in (original / af.SWAP_FILE).read_text()
    with pytest.raises(fc.FixtureSafetyError, match="approval-only"):
        af.mutate_swap_file(copy, FILES, [*READ_FILES, af.SWAP_FILE])
    with pytest.raises(fc.FixtureSafetyError, match="approval-only"):
        af.mutate_swap_file(copy, FILES, READ_FILES, [af.SWAP_FILE])  # a direct-send list
    # A second copy to the same place, or a copy into the original, is refused.
    with pytest.raises(fc.FixtureSafetyError, match="fresh"):
        af.copy_build_for_mutation(tmp_path / "builds", LABEL, dest_builds)
    with pytest.raises(fc.FixtureSafetyError, match="fresh"):
        af.copy_build_for_mutation(tmp_path / "builds", LABEL, original / "inside")
    shutil.rmtree(dest_builds)


def test_copy_that_imports_the_original_is_refused(tmp_path, monkeypatch):
    build = make_build(tmp_path)
    from types import SimpleNamespace

    def fake_run(cmd, **kwargs):
        # The copy's interpreter reports paths inside the ORIGINAL tree.
        return SimpleNamespace(
            returncode=0, stdout=f"{build.src_dir}/gateway/pairing.py\n{build.src_dir}/x.py\n",
            stderr="")

    monkeypatch.setattr(af.subprocess, "run", fake_run)
    copy_src = tmp_path / "copy" / "src"
    (copy_src / ".venv/bin").mkdir(parents=True)
    (copy_src / ".venv/bin/python3").touch()
    copy = fc.BuildInfo(LABEL, copy_src, copy_src / ".venv/bin/python3")
    with pytest.raises(fc.FixtureSafetyError, match=r"imports? from itself"):
        af.verify_copy_isolation(copy, build.src_dir)


def test_boundary_tool_probes_read_send_and_approval_dependencies(tmp_path, monkeypatch):
    probed = {}
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))  # restored after; compute() rewrites it
    monkeypatch.setattr(bridge_files, "ast_set", lambda *a, **k: set())
    monkeypatch.setattr(bridge_files, "probe_set", lambda src, specs: probed.setdefault(
        "specs", {(s.module, s.qualname) for s in specs}) and set())
    for attr in ("READ_DEPENDENCIES", "DIRECT_SEND_DEPENDENCIES", "APPROVAL_DEPENDENCIES"):
        probed.clear()
        bridge_files.compute(tmp_path, ast_only=False, dependencies_attr=attr)
        expected = {(s.module, s.qualname) for s in compat.READ_DEPENDENCIES}
        if attr != "READ_DEPENDENCIES":
            expected |= {(s.module, s.qualname) for s in compat.DIRECT_SEND_DEPENDENCIES}
        if attr == "APPROVAL_DEPENDENCIES":
            expected |= {(s.module, s.qualname) for s in compat.APPROVAL_DEPENDENCIES}
        assert probed["specs"] == expected, attr


# ---- required-ID JUnit selection ------------------------------------------------------------


def junit(path: Path, ids: list[tuple[str, str]], *, outcome: str = "", drop=None,
          extra=()) -> Path:
    cases = []
    head = 'testcase classname="tests.integration.{}" name="{}"'
    for index, (module, test) in enumerate(ids):
        if test == drop:
            continue
        body = outcome if index == 0 else ""
        cases.append(f"<{head.format(module, test)}>{body}</testcase>")
    for module, test in extra:
        cases.append(f"<{head.format(module, test)}/>")
    path.write_text(f"<testsuites><testsuite>{''.join(cases)}</testsuite></testsuites>")
    return path


def test_required_selection_is_explicit_and_complete():
    ids = approval_matrix.required_ids(LABEL)
    assert len(ids) == len(set(ids)) == 27
    names = {test for _, test in ids}
    for needed in (
        f"test_empty_start_stays_closed_until_full_restart[{LABEL}]",
        f"test_in_place_swap_stays_closed_until_full_restart[{LABEL}]",
        f"test_admitted_start_entry_removal_closes_and_restore_reopens[{LABEL}]",
        f"test_direct_send_receipt_never_opens_approvals[{LABEL}]",
        f"test_t7_bot_chat_exact_id_deny_blocks_command[{LABEL}]",
        f"test_t8_cross_profile_exact_id_answer_is_refused[{LABEL}]",
        f"test_approvals_fixture_fails_closed[{LABEL}-owner]",
        f"test_approvals_fixture_fails_closed[{LABEL}-approval-list]",
        "test_listener_reconnect_never_reopens_a_closed_baseline"
        f"[{LABEL}-closed_start_stays_closed]",
    ):
        assert needed in names
    nodes = approval_matrix.node_ids(LABEL)
    assert len(nodes) == 27 and all(n.startswith("server/tests/integration/") for n in nodes)


def test_required_selection_check_rejects_partial_skipped_failed_or_extra(tmp_path):
    ids = approval_matrix.required_ids(LABEL)
    report = tmp_path / "r.xml"
    assert approval_matrix.check_required_report(junit(report, ids), LABEL)["ok"] is True
    for outcome in ("<skipped/>", "<failure/>", "<error/>"):
        checked = approval_matrix.check_required_report(junit(report, ids, outcome=outcome), LABEL)
        assert not checked["ok"] and checked["not_passed"], outcome
    checked = approval_matrix.check_required_report(junit(report, ids, drop=ids[3][1]), LABEL)
    assert not checked["ok"] and len(checked["missing"]) == 1
    extra = [("test_other", "test_unrelated[x]")]
    checked = approval_matrix.check_required_report(junit(report, ids, extra=extra), LABEL)
    assert not checked["ok"] and checked["unexpected"]
    duplicate = junit(report, ids, extra=[ids[0]])
    assert not approval_matrix.check_required_report(duplicate, LABEL)["ok"]
    report.write_text("<testsuites/>")
    assert not approval_matrix.check_required_report(report, LABEL)["ok"]
    report.write_text("<not-xml")
    assert not approval_matrix.check_required_report(report, LABEL)["ok"]
    assert not approval_matrix.check_required_report(tmp_path / "absent.xml", LABEL)["ok"]
    # Another build's report is not this build's evidence.
    other = junit(report, approval_matrix.required_ids("another-build"))
    assert not approval_matrix.check_required_report(other, LABEL)["ok"]


# ---- runner driver: a receipt exists only after EVERY stage passed --------------------------


def run_driver(tmp_path, monkeypatch, *, failing=None, only=None):
    calls = []
    stage_names = list(af.REQUIRED_STAGES)
    for name in stage_names:
        def stage(self, name=name):
            calls.append(name)
            if name == failing:
                raise RuntimeError("boom")
        monkeypatch.setattr(approval_matrix.Matrix, f"stage_{name}", stage)
    monkeypatch.setattr(approval_matrix.Matrix, "write_final",
                        lambda self, path: (calls.append("final"), path.write_text("{}")))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    receipt = out / "receipt.json"
    receipt.write_text("{}")  # a stale receipt from an earlier run
    argv = ["--builds-dir", str(tmp_path / "b"), "--label", LABEL, "--expected-source-sha", SHA,
            "--out", str(out), "--receipt-out", str(receipt),
            "--upstream-source", str(tmp_path / "upstream")]
    if only:
        argv += ["--only", only]
    return approval_matrix.main(argv), calls, receipt


def test_receipt_is_written_only_after_every_stage_passes(tmp_path, monkeypatch):
    code, calls, receipt = run_driver(tmp_path, monkeypatch)
    assert code == 0 and calls == [*af.REQUIRED_STAGES, "final"] and receipt.exists()


@pytest.mark.parametrize("failing", list(af.REQUIRED_STAGES))
def test_any_failing_stage_leaves_no_receipt_and_stops(tmp_path, monkeypatch, failing):
    code, calls, receipt = run_driver(tmp_path, monkeypatch, failing=failing)
    assert code == 1 and "final" not in calls and not receipt.exists()
    assert calls[-1] == failing  # nothing runs after the first failure


def test_partial_run_never_writes_a_receipt(tmp_path, monkeypatch):
    code, calls, receipt = run_driver(tmp_path, monkeypatch, only="boundary,behavior")
    assert code == 0 and calls == ["identity", "boundary", "behavior"] and not receipt.exists()


def test_receipt_must_live_inside_out(tmp_path):
    with pytest.raises(SystemExit):
        approval_matrix.main([
            "--builds-dir", str(tmp_path), "--label", LABEL, "--expected-source-sha", SHA,
            "--out", str(tmp_path / "out"), "--receipt-out", str(tmp_path / "elsewhere.json"),
            "--upstream-source", str(tmp_path / "upstream")])


def test_real_identity_failures_close_the_run(tmp_path):
    receipt = tmp_path / "out" / "r.json"
    receipt.parent.mkdir()
    receipt.write_text("{}")
    code = approval_matrix.main([
        "--builds-dir", str(tmp_path / "missing"), "--label", LABEL, "--expected-source-sha", SHA,
        "--out", str(receipt.parent), "--receipt-out", str(receipt),
        "--upstream-source", str(tmp_path / "upstream")])
    assert code == 1 and not receipt.exists()
    summary = json.loads((receipt.parent / "matrix.json").read_text())
    assert summary["ok"] is False and summary["stages"] == {"identity": False}


def test_final_receipt_needs_upstream_source_but_a_debug_run_does_not(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    base = ["--builds-dir", str(tmp_path / "b"), "--label", LABEL, "--expected-source-sha", SHA,
            "--out", str(out)]
    with pytest.raises(SystemExit):
        approval_matrix.main([*base, "--receipt-out", str(out / "r.json")])
    for name in af.REQUIRED_STAGES:
        monkeypatch.setattr(approval_matrix.Matrix, f"stage_{name}", lambda self: None)
    assert approval_matrix.main([*base, "--only", "boundary"]) == 0  # no receipt, no upstream


@pytest.mark.parametrize("label", ["stock-base", "experimental", "owner-local", "upstream"])
def test_default_fixture_build_labels_are_refused(tmp_path, label):
    assert label in af.default_build_labels() and LABEL not in af.default_build_labels()
    out = tmp_path / "out"
    code = approval_matrix.main([
        "--builds-dir", str(tmp_path / "b"), "--label", label, "--expected-source-sha", SHA,
        "--out", str(out)])
    summary = json.loads((out / "matrix.json").read_text())
    assert code == 1 and "collides" in summary["errors"]["identity"]


def test_collect_only_output_must_be_exactly_the_required_node_ids():
    nodes = approval_matrix.collected_ids(LABEL)
    good = "\n".join(nodes) + "\n\n27 tests collected in 0.5s\n"
    assert approval_matrix.check_collected(good, LABEL)["ok"] is True
    short = approval_matrix.check_collected("\n".join(nodes[1:]), LABEL)
    assert not short["ok"] and short["missing"] == [nodes[0]]
    suffixed = nodes[0].replace(f"[{LABEL}]", f"[{LABEL}-2]")
    drifted = approval_matrix.check_collected("\n".join([suffixed, *nodes[1:]]), LABEL)
    assert not drifted["ok"] and drifted["unexpected"] == [suffixed]
    doubled = approval_matrix.check_collected("\n".join([*nodes, nodes[0]]), LABEL)
    assert not doubled["ok"] and doubled["duplicated"] == [nodes[0]]
    assert not approval_matrix.check_collected("", LABEL)["ok"]


def test_invocation_paths_differ_from_server_root_collected_ids():
    invoked, collected = approval_matrix.node_ids(LABEL), approval_matrix.collected_ids(LABEL)
    assert all(n.startswith("server/tests/integration/") for n in invoked)
    assert all(c.startswith("tests/integration/") for c in collected)
    assert [f"server/{c}" for c in collected] == invoked


def test_real_server_root_collect_log_is_accepted_but_repo_root_names_are_not():
    # Verbatim `pytest --collect-only -q` output from a real run (matrix 6), label substituted.
    real = (Path(__file__).parent / "data" / "pytest_collect_only_server_root.log").read_text()
    assert "27 tests collected" in real
    assert approval_matrix.check_collected(real, LABEL)["ok"] is True
    repo_rooted = real.replace("tests/integration/", "server/tests/integration/")
    assert not approval_matrix.check_collected(repo_rooted, LABEL)["ok"]
    dup = real.replace("27 tests collected", real.splitlines()[0] + "\n27 tests collected")
    assert not approval_matrix.check_collected(dup, LABEL)["ok"]


# ---- lifecycle and reconnect evidence is machine-checked ------------------------------------


def lifecycle_evidence():
    fp = "1" * 64
    swap = {
        "swapped_file": af.SWAP_FILE, "pid_before": 10, "pid_after": 11,
        "approval_fingerprint_before": "2" * 64, "approval_fingerprint_after": "3" * 64,
        "read_fingerprint_before": fp, "read_fingerprint_after": fp,
        "direct_send_fingerprint_before": fp, "direct_send_fingerprint_after": fp,
    }
    empty = {"pid_before": 20, "pid_after": 21}
    admitted = {"pid_before": 30, "pid_after": 30, "closed_after_removal": True, "reopened": True}
    reconnect = {
        scenario: {
            "scenario": scenario, "pid": 99,
            "steps": [{"step": s, "supported": True, "open": o} for s, o in steps],
        } for scenario, steps in af.RECONNECT_EXPECTED.items()
    }
    return swap, empty, admitted, reconnect


def test_lifecycle_evidence_accepts_the_expected_shape():
    approval_matrix.check_lifecycle_evidence(*lifecycle_evidence())


@pytest.mark.parametrize("mutate", [
    lambda s, e, a, r: s.update(pid_after=s["pid_before"]),
    lambda s, e, a, r: e.update(pid_after=e["pid_before"]),
    lambda s, e, a, r: e.update(pid_before=True),
    lambda s, e, a, r: a.update(pid_after=31),
    lambda s, e, a, r: a.update(reopened=False),
    lambda s, e, a, r: a.pop("closed_after_removal"),
    lambda s, e, a, r: s.update(swapped_file="tools/other.py"),
    lambda s, e, a, r: s.update(approval_fingerprint_after=s["approval_fingerprint_before"]),
    lambda s, e, a, r: s.update(read_fingerprint_after="4" * 64),
    lambda s, e, a, r: s.update(direct_send_fingerprint_after="4" * 64),
    lambda s, e, a, r: s.pop("direct_send_fingerprint_before"),
    lambda s, e, a, r: s.update(approval_fingerprint_before="short"),
    lambda s, e, a, r: r.pop("closed_start_stays_closed"),
    lambda s, e, a, r: r["closed_start_stays_closed"]["steps"][1].update(open=True),
    lambda s, e, a, r: r["admitted_start_close_and_restore"]["steps"].pop(),
    lambda s, e, a, r: r["admitted_start_close_and_restore"]["steps"].reverse(),
    lambda s, e, a, r: r["admitted_start_close_and_restore"]["steps"][2].update(supported=False),
    lambda s, e, a, r: r["admitted_start_close_and_restore"].update(scenario="other"),
    lambda s, e, a, r: r["closed_start_stays_closed"].update(pid=s["pid_before"]),
    lambda s, e, a, r: r["closed_start_stays_closed"].pop("pid"),
    lambda s, e, a, r: r["closed_start_stays_closed"]["steps"][0].update(open=0),
    lambda s, e, a, r: r["admitted_start_close_and_restore"]["steps"][0].update(open=1),
])
def test_lifecycle_evidence_rejects_a_wrong_shape(mutate):
    evidence_set = lifecycle_evidence()
    mutate(*evidence_set)
    with pytest.raises(RuntimeError):
        approval_matrix.check_lifecycle_evidence(*evidence_set)
