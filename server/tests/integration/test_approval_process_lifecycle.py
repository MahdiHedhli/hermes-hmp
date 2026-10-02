"""Approval gate PROCESS lifecycle on a real gateway (specs/005-approval-process-matrix).

Same harness as the F2/F3 fixtures: one real Hermes gateway per test, real pairing, a loopback
fake model, synthetic homes. The approval manifest lives ONLY in the disposable fixture plugin
copy; the public manifest stays empty. These tests need both fixture receipts
(`HMP_DIRECT_SEND_QUALIFICATION`, `HMP_APPROVAL_QUALIFICATION`, written by
`tools/compat/approval_matrix.py`). Without the approval receipt they skip, and the matrix
rejects any skip. Collection alone is not execution evidence.

What each test proves, and what it deliberately does not:

- Full gateway restarts (new PID) prove the process-level baseline is fixed per process.
- Listener-only reconnect has no public daemon path; `approval_reconnect_harness.py` drives the
  real `adapter.open_components` twice in one process instead. A full restart is never taken as
  proof of listener-only behavior.
- Archive or git fixture: the build is either an extracted archive without `.git` or, for a git
  receipt (`approval-fixture-qualification-git`), an independent git clone. The SAME required
  tests run for both; the receipt's `git_sha` decides which, and every case asserts the build's
  real `.git` identity equals the receipt's (the gateway's own factory reads it).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
_PLUGIN = REPO_ROOT / "server" / "hmp_plugin"
COMMITTED_APPROVAL_MANIFEST = _PLUGIN / "approval_supported_builds.json"
COMMITTED_READ_MANIFEST = _PLUGIN / "read_compat_builds.json"
COMMITTED_DIRECT_MANIFEST = _PLUGIN / "direct_send_supported_builds.json"
HARNESS = REPO_ROOT / "tools" / "compat" / "approval_reconnect_harness.py"


def _load(name: str):
    path = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(f"approval_lifecycle_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_f2 = _load("test_direct_send_fixture.py")  # puts tools/fixtures on sys.path
_ap = _load("test_approvals_fixture.py")

import _fixture_common as fc  # noqa: E402
import approval_fixture as af  # noqa: E402

DEFAULT_PROFILE = _f2.DEFAULT_PROFILE
pytestmark = _f2.pytestmark


def _receipt() -> Path:
    value = os.environ.get(af.RECEIPT_ENV)
    if not value:
        pytest.skip(f"needs {af.RECEIPT_ENV} (tools/compat/approval_matrix.py fixture receipt)")
    return Path(value)


def _files(path: Path) -> list[str]:
    return list(json.loads(path.read_text(encoding="utf-8"))["bridge_files"])


class Lifecycle:
    def __init__(self, gateway: Any, receipt: Path) -> None:
        self.gw = gateway
        self.receipt = receipt
        self.out: Path = gateway.paths.out_dir

    @property
    def pid(self) -> int:
        return int(self.gw.gateway_proc.pid)

    def manifest_builds(self) -> list[Any]:
        path = af.approval_manifest_path(self.out)
        return list(json.loads(path.read_text(encoding="utf-8"))["builds"])

    def install(self) -> None:
        af.install_approval_fixture_entry(self.gw.build, self.out, self.receipt)

    def remove(self) -> None:
        af.remove_approval_fixture_entry(self.out)


def _assert_identity_matches_receipt(life: Lifecycle) -> str | None:
    """The build's real git identity (None for an archive) equals the receipt's entry, and a git
    fixture is still an independent clone. Returns the HEAD SHA."""
    entry = json.loads(life.receipt.read_text(encoding="utf-8"))["builds"][0]
    src = life.gw.build.src_dir
    head = af.build_git_head(src)
    assert head == entry.get("git_sha"), (head, entry.get("git_sha"))
    if head is not None:
        assert af.assert_git_fixture_clone(src) == head
        assert entry.get("source_sha") == head
    return head


def _evidence(life: Lifecycle, name: str, data: dict[str, Any]) -> None:
    """Optional machine-readable evidence, written only where the matrix runner asks."""
    target = os.environ.get("HMP_APPROVAL_EVIDENCE_DIR")
    if target:
        Path(target).mkdir(parents=True, exist_ok=True)
        (Path(target) / f"{name}-{life.gw.build.label}.json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )


@pytest.fixture(params=_f2.BUILDS)
def lifecycle(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A gateway that STARTS with the shipped empty approval manifest (the receipt is withheld
    from `build_offline`); the direct-send receipt is still installed so reads and sends open."""
    receipt = _receipt()
    monkeypatch.delenv(af.RECEIPT_ENV)
    gen = _f2.gateway.__wrapped__(request, tmp_path, approval_owner_enrollment=True)
    gateway = next(gen)
    try:
        yield Lifecycle(gateway, receipt)
    finally:
        gen.close()


@pytest.fixture(params=_f2.BUILDS)
def admitted(request: pytest.FixtureRequest, tmp_path: Path):
    """A gateway that STARTS admitted: `build_offline` installs the approval receipt."""
    receipt = _receipt()
    gen = _f2.gateway.__wrapped__(request, tmp_path, approval_owner_enrollment=True)
    gateway = next(gen)
    try:
        yield Lifecycle(gateway, receipt)
    finally:
        gen.close()


@pytest.fixture(params=_f2.BUILDS)
def swap(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Admitted gateway running from a fresh COPY of the extracted build, so a source swap never
    touches the original. The copy's venv is re-pointed at itself and verified before use."""
    receipt = _receipt()
    original = Path(_f2.BUILDS_DIR_ENV)
    label = request.param
    if not (original / label / "src").is_dir():
        pytest.skip(f"build {label!r} not extracted on this host")
    copies = tmp_path / "mutation-builds"
    af.copy_build_for_mutation(
        original, label, copies, files=_files(COMMITTED_APPROVAL_MANIFEST)
    )
    monkeypatch.setattr(_f2, "BUILDS_DIR_ENV", str(copies))
    gen = _f2.gateway.__wrapped__(request, tmp_path, approval_owner_enrollment=True)
    gateway = next(gen)
    try:
        yield Lifecycle(gateway, receipt)
    finally:
        gen.close()


def _assert_approvals_closed(life: Lifecycle) -> None:
    gw = life.gw
    before = len(gw.fake_model.main_requests())
    for status, body in (
        _ap._prompts(gw.client),
        _ap._phone(gw.client, cmid=str(uuid.uuid7()), text="a closed lane must refuse"),
        _ap._answer(gw.client, "missing-request", {"choice": "once"}),
    ):
        assert status == 503, (status, body)
        assert body["error"]["code"] == "write_gate_closed", body
    assert len(gw.fake_model.main_requests()) == before, "a closed lane reached the model"
    status, body = gw.client.get(f"/hmp/v1/bots/{DEFAULT_PROFILE}/conversations/default")
    assert status == 200, body
    assert not body.get("open_requests"), body


def _assert_reads_and_send_available(life: Lifecycle, text: str) -> None:
    """Reads and an ordinary guarded Bot Chat send stay available, independent of approvals."""
    client = life.gw.client
    status, body = client.get("/hmp/v1/bots")
    assert status == 200, body
    assert any(bot["profile"] == DEFAULT_PROFILE for bot in body["bots"]), body
    ref = _f2.bot_chat_ref(client, DEFAULT_PROFILE)
    head = _f2.bot_chat_head(client, DEFAULT_PROFILE, ref)
    status, body = _f2.send(
        client, DEFAULT_PROFILE, cmid=str(uuid.uuid7()), expected_head=head, text=text
    )
    assert status == 200, body
    assert body["state"] == "accepted", body


def _assert_approvals_open(life: Lifecycle) -> None:
    """Gate admission only: the prompt-list route answers 200. This is NOT a full approval
    resolution. The round trip is proven by the empty-start and T7/T8 cases; "reopens after the
    swap restart" and "restore reopens" are route admission evidence, a documented limit."""
    status, body = _ap._prompts(life.gw.client)
    assert status == 200, (status, body)


def test_direct_send_receipt_never_opens_approvals(lifecycle: Lifecycle) -> None:
    """A gateway with the direct-send receipt installed and NO approval entry keeps AP-3/4/6
    closed while reads and ordinary guarded sends work."""
    assert lifecycle.manifest_builds() == []
    _assert_identity_matches_receipt(lifecycle)
    direct = json.loads(
        (lifecycle.out / "_hmp_plugin" / "direct_send_supported_builds.json").read_text()
    )
    assert direct["builds"], "the direct-send receipt must be installed for this proof"
    _assert_reads_and_send_available(lifecycle, "send lane open, approval lane closed")
    _assert_approvals_closed(lifecycle)


def test_empty_start_stays_closed_until_full_restart(lifecycle: Lifecycle) -> None:
    """Empty approval manifest at gateway start: reads and sends work, AP-3/4/6 closed.
    Installing the correct entry while the same process runs stays closed. Only a full restart
    (new PID) opens AP-3 and a real approval round trip works."""
    gw = lifecycle.gw
    pid_before = lifecycle.pid
    assert lifecycle.manifest_builds() == []
    _assert_identity_matches_receipt(lifecycle)
    _assert_reads_and_send_available(lifecycle, "empty start read and send")
    _assert_approvals_closed(lifecycle)

    lifecycle.install()  # correct fixture-only entry, same running process
    assert lifecycle.manifest_builds(), "the fixture entry was not installed"
    assert gw.gateway_proc.poll() is None and lifecycle.pid == pid_before
    _assert_approvals_closed(lifecycle)
    _assert_reads_and_send_available(lifecycle, "same process, entry installed, still closed")
    assert lifecycle.pid == pid_before

    gw.restart_gateway()  # the WHOLE gateway process, not a listener restart
    pid_after = lifecycle.pid
    assert pid_after != pid_before
    _assert_approvals_open(lifecycle)

    model = gw.fake_model_module
    command, target = _ap._probe_command(gw)
    gw.fake_model.push(
        model.ToolCall(name="terminal", args={"command": command}), model.Text("round trip done")
    )
    client = gw.client
    ref = _f2.bot_chat_ref(client, DEFAULT_PROFILE)
    head = _f2.bot_chat_head(client, DEFAULT_PROFILE, ref)
    status, body = _f2.send(
        client, DEFAULT_PROFILE, cmid=str(uuid.uuid7()), expected_head=head, text="round trip"
    )
    assert status == 202, body
    prompt = _f2.wait_for(lambda: _ap._pending_approval(client), timeout=30)
    assert prompt, _ap._prompts(client)
    assert (target / "sentinel").exists(), "command ran before an answer"
    status, body = _ap._answer(client, prompt["request_id"], {"choice": "once"})
    assert status == 200 and body["applied"] is True, body
    assert _f2.wait_for(lambda: not target.exists(), timeout=30), "approval did not unblock"
    _evidence(lifecycle, "empty-start", {"pid_before": pid_before, "pid_after": pid_after})


def test_admitted_start_entry_removal_closes_and_restore_reopens(admitted: Lifecycle) -> None:
    """Fresh gateway admitted at start. With a cached successful probe, removing the entry closes
    the very next request; restoring the same startup entry can reopen, in the same process."""
    pid = admitted.pid
    assert admitted.manifest_builds(), "the gateway must start with the fixture entry"
    head = _assert_identity_matches_receipt(admitted)
    assert [b.get("git_sha") for b in admitted.manifest_builds()] == [head]
    _assert_approvals_open(admitted)  # a successful probe is now cached in this process
    _assert_approvals_open(admitted)

    admitted.remove()
    _assert_approvals_closed(admitted)
    _assert_reads_and_send_available(admitted, "removed entry, sends stay ordinary")

    admitted.install()  # the SAME startup entry
    _assert_approvals_open(admitted)
    assert admitted.gw.gateway_proc.poll() is None and admitted.pid == pid
    # Written only after every assertion above held; one process throughout (no restart).
    _evidence(admitted, "admitted-start", {
        "pid_before": pid, "pid_after": admitted.pid,
        "closed_after_removal": True, "reopened": True,
    })


def test_in_place_swap_stays_closed_until_full_restart(swap: Lifecycle) -> None:
    """In a disposable COPY: swap an approval-only source file (outside the read fingerprint) and
    install the matching new entry. The running process stays closed; only a full restart opens."""
    build = swap.gw.build
    approval_files = _files(af.approval_manifest_path(swap.out))
    read_files = _files(COMMITTED_READ_MANIFEST)
    direct_files = _files(COMMITTED_DIRECT_MANIFEST)
    compute = af.compat.compute_read_bridge_fingerprint
    approval_before = compute(build.src_dir, approval_files)
    read_before = compute(build.src_dir, read_files)
    direct_before = compute(build.src_dir, direct_files)
    pid_before = swap.pid
    git_sha = _assert_identity_matches_receipt(swap)
    git_before = af.git_identity_digest(build.src_dir) if git_sha else None
    _assert_approvals_open(swap)  # admitted at start; probe cached

    swapped = af.mutate_swap_file(build, approval_files, read_files, direct_files)
    approval_after = compute(build.src_dir, approval_files)
    read_after = compute(build.src_dir, read_files)
    assert approval_after != approval_before, "the swap did not change the approval fingerprint"
    assert read_after == read_before, "the swap file must lie outside the read fingerprint"
    # Guarded send stays qualified, so a closed approval lane is attributable to the approval gate.
    direct_after = compute(build.src_dir, direct_files)
    assert direct_after == direct_before
    old, new = af.rebind_fixture_entry(build, swap.out, note="in-place swap")
    assert (old, new) == (approval_before, approval_after)
    if git_sha:  # a source swap moves the fingerprint, never the git identity
        assert af.build_git_head(build.src_dir) == git_sha
        assert af.git_identity_digest(build.src_dir) == git_before
        assert [b.get("git_sha") for b in swap.manifest_builds()] == [git_sha]

    assert swap.gw.gateway_proc.poll() is None and swap.pid == pid_before
    _assert_approvals_closed(swap)
    _assert_reads_and_send_available(swap, "swapped in place, reads and sends unaffected")
    assert swap.pid == pid_before

    swap.gw.restart_gateway()
    pid_after = swap.pid
    assert pid_after != pid_before
    _assert_approvals_open(swap)
    if git_sha:
        assert af.assert_git_fixture_clone(build.src_dir) == git_sha
        assert af.git_identity_digest(build.src_dir) == git_before
    _evidence(swap, "in-place-swap", {
        "swapped_file": swapped, "pid_before": pid_before, "pid_after": pid_after,
        "git_sha_before": git_sha, "git_sha_after": af.build_git_head(build.src_dir),
        "git_identity_before": git_before,
        "git_identity_after": af.git_identity_digest(build.src_dir) if git_sha else None,
        "approval_fingerprint_before": approval_before,
        "approval_fingerprint_after": approval_after,
        "read_fingerprint_before": read_before, "read_fingerprint_after": read_after,
        "direct_send_fingerprint_before": direct_before,
        "direct_send_fingerprint_after": direct_after,
    })


@pytest.fixture(params=_f2.BUILDS)
def label(request: pytest.FixtureRequest) -> str:
    if not (Path(_f2.BUILDS_DIR_ENV) / request.param / "src").is_dir():
        pytest.skip(f"build {request.param!r} not extracted on this host")
    return str(request.param)


@pytest.mark.parametrize(
    "scenario", ["closed_start_stays_closed", "admitted_start_close_and_restore"]
)
def test_listener_reconnect_never_reopens_a_closed_baseline(
    label: str, scenario: str, tmp_path: Path
) -> None:
    """Real `adapter.open_components` twice in ONE process (no gateway): a baseline that started
    closed never reopens on reconnect, and an admitted baseline closes on a removed or wrong
    entry and reopens only for the exact startup entry."""
    receipt = _receipt()
    build = fc.resolve_build(Path(_f2.BUILDS_DIR_ENV), label)
    entry = json.loads(receipt.read_text(encoding="utf-8"))["builds"][0]
    assert af.build_git_head(build.src_dir) == entry.get("git_sha")  # archive: both None
    work = tmp_path / "reconnect"
    (work / "home" / "plugin-data" / "hmp" / "instance").mkdir(parents=True)
    (work / "xdg").mkdir()
    env = fc.clean_hermes_env(extra={
        "HERMES_HOME": str(work / "home"), "XDG_STATE_HOME": str(work / "xdg"),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    proc = subprocess.run(
        [str(build.venv_python), str(HARNESS), "--hermes-src", str(build.src_dir),
         "--work", str(work), "--receipt", str(receipt), "--scenario", scenario],
        env=env, capture_output=True, text=True, timeout=300, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    # `supported` comes from each step's originating live context, so this is not vacuous.
    assert all(step["supported"] is True for step in report["steps"]), report
    assert report["scenario"] == scenario and report["pid"] != os.getpid(), report
    observed = [(step["step"], step["open"]) for step in report["steps"]]
    assert observed == list(af.RECONNECT_EXPECTED[scenario]), report
    _evidence_dir = os.environ.get("HMP_APPROVAL_EVIDENCE_DIR")
    if _evidence_dir:
        Path(_evidence_dir).mkdir(parents=True, exist_ok=True)
        (Path(_evidence_dir) / f"reconnect-{scenario}-{label}.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
