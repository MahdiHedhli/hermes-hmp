#!/usr/bin/env python3
"""Approval process qualification matrix (specs/005-approval-process-matrix).

A sibling of `run_matrix.py`, not a mode of it: read and direct-send qualification stay independent
and an approval receipt never widens them. For ONE extracted, archive-style Hermes build it runs,
in order, stopping at the first failure:

  identity     pinned Python 3.14, extracted tree without .git, public approval manifest empty,
               optional read-only cross-check against the original upstream source and SHA.
  boundary     `bridge_files.py --check` for the direct-send and the approval file lists.
  behavior     `approval_probes.py` against the real Hermes modules (control, exact ID,
               interrupt and timeout waits).
  integration  the explicit required real-gateway tests (fixture receipts installed ONLY in the
               disposable fixture plugin copy) and a machine-checked JUnit selection.
  reconnect    the listener-reconnect harness evidence (real `adapter.open_components`).
  timing       bounded repeated cold/cached qualifier timing (local evidence only).
  stability    source and plugin bytes are unchanged from before the first stage.

The final receipt is written only after every stage passed. It is a fixture-only artifact: never
committed, never a manifest entry, never a device, release or security clearance.

    python3 tools/compat/approval_matrix.py --builds-dir <dir> --label <label> \\
        --expected-source-sha <40 hex> --out <scratch> --receipt-out <scratch>/receipt.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = REPO_ROOT / "server"
COMPAT_DIR = REPO_ROOT / "tools" / "compat"
FIXTURES_DIR = REPO_ROOT / "tools" / "fixtures"
PLUGIN_DIR = SERVER_DIR / "hmp_plugin"
APPROVAL_COMPAT_PATH = PLUGIN_DIR / "approval_supported_builds.json"
DIRECT_COMPAT_PATH = PLUGIN_DIR / "direct_send_supported_builds.json"
READ_COMPAT_PATH = PLUGIN_DIR / "read_compat_builds.json"
INTEGRATION = REPO_ROOT / "server" / "tests" / "integration"

for _path in (str(SERVER_DIR), str(FIXTURES_DIR), str(COMPAT_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import _fixture_common as fc  # noqa: E402
import approval_fixture as af  # noqa: E402
import run_matrix  # noqa: E402

from hmp_plugin.compat import compute_read_bridge_fingerprint  # noqa: E402

PINNED_PYTHON = (3, 14)
LABEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
SHA_RE = re.compile(r"[0-9a-f]{40}")
STAGES = af.REQUIRED_STAGES

# The required-test table, reconnect expectations and label rules live in `approval_fixture` so the
# runner, the final-receipt validator and the tests share one definition (no import cycle).
REQUIRED_TESTS = af.REQUIRED_TESTS
_RECONNECT = af.RECONNECT_SCENARIOS
required_ids = af.required_ids


SERVER_TEST_ROOT = "server"


def node_ids(label: str) -> list[str]:
    """Invocation paths, relative to the repository root where pytest is launched."""
    return [f"{SERVER_TEST_ROOT}/tests/integration/{module}.py::{test}"
            for module, test in required_ids(label)]


def collected_ids(label: str) -> list[str]:
    """Names pytest prints for those same tests. Its rootdir is `server` (server/pyproject), so
    collected IDs are relative to that root, not to the repository root the command ran from.
    Distinct from `node_ids`: those are arguments, these are the reported names."""
    prefix = f"{SERVER_TEST_ROOT}/"
    return [node[len(prefix):] for node in node_ids(label)]


def check_collected(output: str, label: str) -> dict[str, Any]:
    """Compare `pytest --collect-only -q` output with the required collected IDs (server-root
    relative, see `collected_ids`). Matching is exact: full module, test and params, no suffix or
    fuzzy match, no duplicates."""
    wanted = set(collected_ids(label))
    lines = [line.strip() for line in output.splitlines() if "::" in line]
    collected = set(lines)
    return {
        "ok": collected == wanted and len(lines) == len(wanted),
        "missing": sorted(wanted - collected), "unexpected": sorted(collected - wanted),
        "duplicated": sorted({line for line in lines if lines.count(line) > 1}),
    }


_PID_KEYS = ("pid_before", "pid_after")


def _is_pid(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and af.SHA256_RE.fullmatch(value) is not None


def check_lifecycle_evidence(
    swap: dict[str, Any], empty: dict[str, Any], admitted: dict[str, Any],
    reconnect: dict[str, dict[str, Any]],
) -> None:
    """Machine-check the saved lifecycle and reconnect values. Raises RuntimeError. A full gateway
    restart must change the PID; the admitted-start and reconnect proofs stay in one process. Route
    200 after a swap or restore is gate admission only, never full resolution; the full approval
    round trip is proven by the other required cases."""
    for name, data in (("in-place swap", swap), ("empty start", empty)):
        pids = [data.get(k) for k in _PID_KEYS]
        if not all(_is_pid(p) for p in pids) or pids[0] == pids[1]:
            raise RuntimeError(f"{name}: a full restart must yield two distinct gateway PIDs")
    if not _is_pid(admitted.get("pid_before")) or admitted.get("pid_before") != admitted.get(
        "pid_after"
    ):
        raise RuntimeError("admitted start: the removal and restore proof must stay in one process")
    if admitted.get("closed_after_removal") is not True or admitted.get("reopened") is not True:
        raise RuntimeError("admitted start: closed-after-removal and reopened were not both proven")
    if swap.get("swapped_file") != af.SWAP_FILE:
        raise RuntimeError("in-place swap: the swapped file is not the approval-only file")
    fingerprints = {
        key: swap.get(key) for key in (
            "approval_fingerprint_before", "approval_fingerprint_after",
            "read_fingerprint_before", "read_fingerprint_after",
            "direct_send_fingerprint_before", "direct_send_fingerprint_after")
    }
    if not all(_is_sha256(v) for v in fingerprints.values()):
        raise RuntimeError("in-place swap: a fingerprint is missing or malformed")
    if fingerprints["approval_fingerprint_before"] == fingerprints["approval_fingerprint_after"]:
        raise RuntimeError("in-place swap: the approval fingerprint did not change")
    if (
        fingerprints["read_fingerprint_before"] != fingerprints["read_fingerprint_after"]
        or fingerprints["direct_send_fingerprint_before"]
        != fingerprints["direct_send_fingerprint_after"]
    ):
        raise RuntimeError("in-place swap: the read or direct-send fingerprint moved")
    if set(reconnect) != set(af.RECONNECT_EXPECTED):
        raise RuntimeError("reconnect evidence does not cover exactly the required scenarios")
    gateway_pids = {swap["pid_before"], swap["pid_after"], empty["pid_before"], empty["pid_after"],
                    admitted["pid_before"]}
    for scenario, report in reconnect.items():
        steps = report.get("steps")
        expected = af.RECONNECT_EXPECTED[scenario]
        if report.get("scenario") != scenario or not isinstance(steps, list) or [
            (s.get("step"), s.get("open")) for s in steps if isinstance(s, dict)
        ] != list(expected) or len(steps) != len(expected) or any(
            not isinstance(s.get("open"), bool) for s in steps
        ):
            raise RuntimeError(f"reconnect {scenario}: the saved steps differ from the expected")
        if any(s.get("supported") is not True for s in steps):
            raise RuntimeError(f"reconnect {scenario}: a step ran without read compatibility")
        if not _is_pid(report.get("pid")) or report["pid"] in gateway_pids:
            raise RuntimeError(f"reconnect {scenario}: expected one separate harness process")


def check_required_report(path: Path, label: str) -> dict[str, Any]:
    """Machine-check a pytest JUnit report against the explicit required IDs.

    Fails an absent or empty report, a missing, unexpected or duplicated test, and any skipped,
    failed or errored case. `ok` is True only when the selection equals the required set and
    every case passed.
    """
    import xml.etree.ElementTree as ET

    required = set(required_ids(label))
    result: dict[str, Any] = {
        "ok": False, "count": 0, "required": len(required),
        "missing": [], "unexpected": [], "duplicated": [], "not_passed": [],
    }
    if not path.is_file():
        result["error"] = "junit report absent"
        return result
    try:
        cases = list(ET.parse(path).getroot().iter("testcase"))  # noqa: S314 -- local output
    except ET.ParseError:
        result["error"] = "junit report malformed"
        return result
    seen: dict[tuple[str, str], int] = {}
    for case in cases:
        module = str(case.get("classname", "")).rsplit(".", 1)[-1]
        key = (module, str(case.get("name", "")))
        seen[key] = seen.get(key, 0) + 1
        if any(case.find(tag) is not None for tag in ("failure", "error", "skipped")):
            result["not_passed"].append(f"{key[0]}::{key[1]}")
    result["count"] = len(cases)
    result["missing"] = sorted(f"{m}::{t}" for m, t in required - set(seen))
    result["unexpected"] = sorted(f"{m}::{t}" for m, t in set(seen) - required)
    result["duplicated"] = sorted(f"{m}::{t}" for (m, t), n in seen.items() if n > 1)
    result["ok"] = bool(cases) and not (
        result["missing"] or result["unexpected"] or result["duplicated"] or result["not_passed"]
    )
    return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _files(path: Path) -> list[str]:
    return list(json.loads(path.read_text(encoding="utf-8"))["bridge_files"])


def _run(cmd: Sequence[str], log: Path, *, env: dict[str, str] | None = None,
         cwd: Path | None = None, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        list(cmd), capture_output=True, text=True, check=False, env=env,
        cwd=str(cwd) if cwd else None, timeout=timeout,
    )
    log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    return proc


def _python_version(python: Path) -> tuple[int, int] | None:
    try:
        proc = subprocess.run(
            [str(python), "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
            capture_output=True, text=True, check=False, timeout=60,
        )
        major, minor = proc.stdout.split()[:2]
        return int(major), int(minor)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


class Matrix:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.label: str = args.label
        self.out: Path = args.out.resolve()
        self.builds_dir = args.builds_dir.resolve()
        self.src = (self.builds_dir / self.label / "src").resolve()
        self.log_dir = self.out / "logs"
        self.state: dict[str, Any] = {}
        self.stages: dict[str, bool] = {}
        self.errors: dict[str, str] = {}

    # ---- identity -----------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        approval_files, direct_files, read_files = (
            _files(APPROVAL_COMPAT_PATH), _files(DIRECT_COMPAT_PATH), _files(READ_COMPAT_PATH))
        return {
            "approval_files": approval_files, "direct_files": direct_files,
            "read_files": read_files,
            "approval_fingerprint": compute_read_bridge_fingerprint(self.src, approval_files),
            "direct_fingerprint": compute_read_bridge_fingerprint(self.src, direct_files),
            "read_fingerprint": compute_read_bridge_fingerprint(self.src, read_files),
            "plugin_sha256": af.plugin_source_digest(PLUGIN_DIR),
        }

    def stage_identity(self) -> None:
        if not LABEL_RE.fullmatch(self.label):
            raise RuntimeError("unsafe build label")
        if self.label in af.default_build_labels():
            raise RuntimeError("the label collides with a default fixture build; pick a new one")
        if sys.version_info[:2] != PINNED_PYTHON:
            raise RuntimeError(f"the runner needs pinned Python 3.14, not {sys.version_info[:2]}")
        source_sha = self.args.expected_source_sha
        if not SHA_RE.fullmatch(source_sha):
            raise RuntimeError("--expected-source-sha must be a full 40-hex commit")
        fc.assert_outside_real_home(self.out, "--out")
        build = fc.resolve_build(self.builds_dir, self.label)
        if (self.src / ".git").exists():
            raise RuntimeError("qualifies an extracted archive fixture, not a git install")
        if _python_version(build.venv_python) != PINNED_PYTHON:
            raise RuntimeError("the build interpreter must be pinned Python 3.14")
        if json.loads(APPROVAL_COMPAT_PATH.read_text(encoding="utf-8"))["builds"] != []:
            raise RuntimeError("the public approval manifest must stay empty for this tool")
        snap = self.snapshot()
        if None in (snap["approval_fingerprint"], snap["direct_fingerprint"],
                    snap["read_fingerprint"]):
            raise RuntimeError("a listed Hermes source file is missing from the extracted build")
        if not set(snap["direct_files"]) <= set(snap["approval_files"]):
            raise RuntimeError("the approval boundary must cover the direct-send boundary")
        self.state.update(snap, source_sha=source_sha, build=build)
        upstream = self.args.upstream_source
        if upstream is not None:
            proc = subprocess.run(
                ["git", "-C", str(upstream), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=False, timeout=60,
            )
            if proc.returncode != 0 or proc.stdout.strip() != source_sha:
                raise RuntimeError("upstream source HEAD differs from --expected-source-sha")
            if compute_read_bridge_fingerprint(
                upstream.resolve(), snap["approval_files"]
            ) != snap["approval_fingerprint"]:
                raise RuntimeError("extracted build differs from upstream (approval files)")
            self.state["upstream_verified"] = True
        else:
            self.state["upstream_verified"] = False

    # ---- boundary / behavior -------------------------------------------------------------

    def stage_boundary(self) -> None:
        python = self.state["build"].venv_python
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for attr, target in (("DIRECT_SEND_DEPENDENCIES", DIRECT_COMPAT_PATH),
                             ("APPROVAL_DEPENDENCIES", APPROVAL_COMPAT_PATH)):
            proc = _run(
                [str(python), str(COMPAT_DIR / "bridge_files.py"), "--hermes-src", str(self.src),
                 "--dependencies-attr", attr, "--target", str(target), "--check"],
                self.log_dir / f"boundary-{attr}.log", env=env,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"boundary {attr} failed; see logs/boundary-{attr}.log")

    def stage_behavior(self) -> None:
        python = self.state["build"].venv_python
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        proc = _run(
            [str(python), str(COMPAT_DIR / "approval_probes.py"), "--hermes-src", str(self.src)],
            self.log_dir / "behavior.log", env=env,
        )
        try:
            report = json.loads(proc.stdout.strip().splitlines()[-1])
        except (IndexError, ValueError):
            report = {}
        needed = ("control_ok", "exact_id_ok", "interrupt_ok", "timeout_ok")
        if proc.returncode != 0 or not all(report.get(key) is True for key in needed):
            raise RuntimeError("behavior probes failed; see logs/behavior.log")
        self.state["behavior"] = report

    # ---- receipts ------------------------------------------------------------------------

    def _entry(self, fingerprint: str, *, provisional: bool) -> dict[str, Any]:
        entry = run_matrix.direct_send_entry({
            "label": self.label, "fingerprint": fingerprint, "git_sha": None,
            "source_sha": self.state["source_sha"],
        }, provisional=provisional)
        entry["qualified_by"] = (
            "tools/compat/approval_matrix.py (provisional fixture bootstrap; integration pending)"
            if provisional else
            "tools/compat/approval_matrix.py (fixture-only: boundary, behavior, lifecycle, "
            "reconnect and timing passed; never a manifest entry)"
        )
        return entry

    def write_provisional(self) -> tuple[Path, Path]:
        s = self.state
        direct = self.out / "direct-send-provisional-fixture-only.json"
        direct.write_text(json.dumps({
            "format": 1, "bridge_files": s["direct_files"],
            "builds": [run_matrix.direct_send_entry({
                "label": self.label, "fingerprint": s["direct_fingerprint"], "git_sha": None,
                "source_sha": s["source_sha"]}, provisional=True)],
        }, indent=2) + "\n", encoding="utf-8")
        approval = self.out / "approval-provisional-fixture-only.json"
        approval.write_text(json.dumps({
            "format": 1, "bridge_files": s["approval_files"],
            "builds": [self._entry(s["approval_fingerprint"], provisional=True)],
        }, indent=2) + "\n", encoding="utf-8")
        af.validate_approval_receipt(
            approval, s["build"], target_files=s["approval_files"], final=False)
        return direct, approval

    # ---- integration + reconnect ---------------------------------------------------------

    def stage_integration(self) -> None:
        direct, approval = self.write_provisional()
        evidence = self.out / "evidence"
        evidence.mkdir(exist_ok=True)
        for stale in evidence.glob("*.json"):
            stale.unlink()
        report = self.out / "integration.xml"
        report.unlink(missing_ok=True)
        env = dict(os.environ)
        env.update(
            HMP_HERMES_BUILDS_DIR=str(self.builds_dir), HMP_FIXTURE_EXTRA_BUILDS=self.label,
            HMP_DIRECT_SEND_QUALIFICATION=str(direct), HMP_APPROVAL_EVIDENCE_DIR=str(evidence),
            PYTHONDONTWRITEBYTECODE="1",
        )
        env[af.RECEIPT_ENV] = str(approval)
        common = ["-q", "-o", "addopts=", "-p", "no:cacheprovider"]
        # The real parametrized IDs must be exactly the required ones before anything runs.
        collect = _run([sys.executable, "-m", "pytest", "--collect-only", *node_ids(self.label),
                        *common], self.log_dir / "collect.log", env=env, cwd=REPO_ROOT,
                       timeout=600)
        collected = check_collected(collect.stdout, self.label)
        if collect.returncode != 0 or not collected["ok"]:
            detail = json.dumps({k: v for k, v in collected.items() if v})
            raise RuntimeError(
                f"collected pytest IDs differ from the required set: rc={collect.returncode} "
                f"{detail}")
        cmd = [sys.executable, "-m", "pytest", *node_ids(self.label), *common,
               f"--junitxml={report}", f"--basetemp={self.out / 'pytest'}"]
        proc = _run(cmd, self.log_dir / "integration.log", env=env, cwd=REPO_ROOT,
                    timeout=self.args.integration_timeout)
        checked = check_required_report(report, self.label)
        self.state["junit"] = checked
        if proc.returncode != 0 or not checked["ok"]:
            raise RuntimeError(
                f"integration failed or the selection is not exactly the required set: "
                f"rc={proc.returncode} {json.dumps({k: v for k, v in checked.items() if v})}")
        self.state["junit_sha256"] = _sha256(report)

    def stage_reconnect(self) -> None:
        evidence = self.out / "evidence"
        reports = {}
        for scenario in _RECONNECT:
            path = evidence / f"reconnect-{scenario}-{self.label}.json"
            if not path.is_file():
                raise RuntimeError(f"reconnect evidence missing: {path.name}")
            reports[scenario] = json.loads(path.read_text(encoding="utf-8"))
        life: dict[str, dict[str, Any]] = {}
        for key, stem in (("swap", "in-place-swap"), ("empty", "empty-start"),
                          ("admitted", "admitted-start")):
            path = evidence / f"{stem}-{self.label}.json"
            if not path.is_file():
                raise RuntimeError(f"lifecycle evidence missing: {path.name}")
            life[key] = json.loads(path.read_text(encoding="utf-8"))
        try:
            check_lifecycle_evidence(life["swap"], life["empty"], life["admitted"], reports)
        except (AttributeError, KeyError, TypeError) as exc:
            raise RuntimeError(f"lifecycle evidence is malformed: {exc!r}") from exc
        self.state["lifecycle"] = {
            "in_place_swap": life["swap"], "empty_start": life["empty"],
            "admitted_start": life["admitted"], "reconnect": reports,
        }

    # ---- timing --------------------------------------------------------------------------

    def stage_timing(self) -> None:
        python = self.state["build"].venv_python
        approval = self.out / "approval-provisional-fixture-only.json"
        runs = []
        shutil.rmtree(self.out / "timing", ignore_errors=True)  # fresh work dirs every run
        for index in range(self.args.timing_repeats):
            work = self.out / "timing" / str(index)
            (work / "home").mkdir(parents=True)
            (work / "xdg").mkdir()
            env = fc.clean_hermes_env(extra={
                "HERMES_HOME": str(work / "home"), "XDG_STATE_HOME": str(work / "xdg"),
                "PYTHONDONTWRITEBYTECODE": "1",
            })
            proc = _run(
                [str(python), str(COMPAT_DIR / "approval_timing.py"), "--hermes-src", str(self.src),
                 "--work", str(work), "--receipt", str(approval),
                 "--cached-calls", str(self.args.cached_calls)],
                self.log_dir / f"timing-{index}.log", env=env, timeout=600,
            )
            try:
                report = json.loads(proc.stdout.strip().splitlines()[-1])
            except (IndexError, ValueError):
                report = {}
            if proc.returncode != 0 or report.get("all_open") is not True:
                raise RuntimeError(f"timing run {index} failed; see logs/timing-{index}.log")
            runs.append(report)
        colds = [r["cold_first_call_ms"] for r in runs]
        medians = [r["cached"]["median_ms"] for r in runs]
        self.state["timing"] = {
            "note": "local measurement on one host; not a performance guarantee",
            "runs": len(runs), "python": runs[0]["python"],
            "cold_first_call_ms": {"min": min(colds), "median": statistics.median(colds),
                                   "max": max(colds)},
            "cached_median_ms": {"min": min(medians), "median": statistics.median(medians),
                                 "max": max(medians)},
            "cached_p95_ms_max": max(r["cached"]["p95_ms"] for r in runs),
            "cached_calls_per_run": runs[0]["cached"]["n"],
            "factory_ms": [r["factory_ms"] for r in runs],
            "raw": runs,
        }

    # ---- stability + receipt -------------------------------------------------------------

    def stage_stability(self) -> None:
        after = self.snapshot()
        for key in ("approval_fingerprint", "direct_fingerprint", "read_fingerprint",
                    "plugin_sha256", "approval_files", "direct_files", "read_files"):
            if after[key] != self.state[key]:
                raise RuntimeError(f"{key} changed during the matrix")
        if (self.src / ".git").exists():
            raise RuntimeError("a .git appeared in the extracted build during the matrix")
        if json.loads(APPROVAL_COMPAT_PATH.read_text(encoding="utf-8"))["builds"] != []:
            raise RuntimeError("the public approval manifest changed during the matrix")

    def write_final(self, path: Path) -> None:
        s = self.state
        receipt = {
            "format": 1,
            "bridge_files": s["approval_files"],
            "builds": [self._entry(s["approval_fingerprint"], provisional=False)],
            "evidence": {
                "kind": af.RECEIPT_KIND, "not_for_commit": True, "complete": True,
                "label": self.label, "source_sha": s["source_sha"],
                "upstream_verified": s["upstream_verified"],
                "approval_fingerprint": s["approval_fingerprint"],
                "direct_send_fingerprint": s["direct_fingerprint"],
                "read_fingerprint": s["read_fingerprint"],
                "plugin_sha256": s["plugin_sha256"],
                "stages": {name: self.stages.get(name) is True for name in STAGES},
                "required_tests": [f"{m}::{t}" for m, t in required_ids(self.label)],
                "junit_sha256": s["junit_sha256"], "behavior": s["behavior"],
                "lifecycle": s["lifecycle"], "timing": s["timing"],
                "git_lifecycle": "not_covered",
                "limits": [
                    "extracted archive without .git; the git SHA branch has unit coverage only",
                    "no memory attestation; already-imported modules are not re-verified",
                    "not device, release or security clearance; never a committed manifest entry",
                ],
                "generated_at": datetime.now(UTC).isoformat(),
            },
        }
        path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        # A final receipt must survive the same validator every consumer uses.
        af.validate_approval_receipt(
            path, s["build"], target_files=s["approval_files"], final=True,
            plugin_dir=PLUGIN_DIR, read_files=s["read_files"], direct_files=s["direct_files"])

    # ---- driver --------------------------------------------------------------------------

    def run(self, only: Iterable[str] | None) -> bool:
        self.out.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)
        selected = set(only) if only else set(STAGES)
        runners = {
            "identity": self.stage_identity, "boundary": self.stage_boundary,
            "behavior": self.stage_behavior, "integration": self.stage_integration,
            "reconnect": self.stage_reconnect, "timing": self.stage_timing,
            "stability": self.stage_stability,
        }
        ok = True
        for name in STAGES:
            if name not in selected and name != "identity":
                continue  # identity always runs: every other stage needs its state
            print(f"approval_matrix: {self.label}: {name} ...", file=sys.stderr)
            try:
                runners[name]()
                self.stages[name] = True
            except Exception as exc:
                self.stages[name] = False
                self.errors[name] = str(exc)
                print(f"approval_matrix: {name} FAILED: {exc}", file=sys.stderr)
                ok = False
                break
        complete = ok and selected == set(STAGES)
        if complete and self.args.receipt_out:
            try:
                self.write_final(self.args.receipt_out)
            except Exception as exc:
                self.args.receipt_out.unlink(missing_ok=True)
                self.errors["receipt"] = str(exc)
                ok = complete = False
        summary = {
            "format": 1, "label": self.label, "ok": ok, "complete_run": complete,
            "stages": self.stages, "errors": self.errors,
            "junit": self.state.get("junit"), "timing": self.state.get("timing"),
            "receipt_written": bool(complete and self.args.receipt_out),
        }
        (self.out / "matrix.json").write_text(json.dumps(summary, indent=2) + "\n",
                                              encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return ok


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--builds-dir", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--upstream-source", type=Path, default=None,
                        help="read-only original source used to cross-check the SHA and files")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, default=None,
                        help="final fixture-only receipt; must be inside --out")
    parser.add_argument("--only", default=None,
                        help="comma-separated stages (see the module docstring); "
                        "a partial run never writes a receipt")
    parser.add_argument("--timing-repeats", type=int, default=5)
    parser.add_argument("--cached-calls", type=int, default=200)
    parser.add_argument("--integration-timeout", type=float, default=7200.0)
    args = parser.parse_args(argv)
    if not 1 <= args.timing_repeats <= 20:
        parser.error("--timing-repeats must be between 1 and 20")
    only = None
    if args.only:
        only = [item for item in args.only.split(",") if item]
        unknown = sorted(set(only) - set(STAGES))
        if unknown:
            parser.error(f"unknown stages: {unknown}")
    if args.receipt_out is not None:
        if args.upstream_source is None:
            parser.error("--receipt-out needs --upstream-source: a final receipt must be "
                         "upstream-verified (partial or debug runs may omit both)")
        args.receipt_out = args.receipt_out.resolve()
        if not args.receipt_out.is_relative_to(args.out.resolve()):
            parser.error("--receipt-out must be inside --out")
        args.receipt_out.unlink(missing_ok=True)  # a failed run never leaves an older receipt
    return 0 if Matrix(args).run(only) else 1


if __name__ == "__main__":
    sys.exit(main())
