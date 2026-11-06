"""Real Darwin owned-child proof and refusal observations; no production issuer."""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "tools/compat/presentation_peer_lifetime_probe.py"
_SPEC = importlib.util.spec_from_file_location("peer_lifetime_probe_test", _SCRIPT)
probe = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = probe
_SPEC.loader.exec_module(probe)


@pytest.mark.skipif(sys.platform != "darwin" or os.geteuid() == 0,
                    reason="actual nonroot Darwin lifetime observer")
@pytest.mark.parametrize("mode", sorted(probe._MODES))
def test_actual_owned_child_lifetime_and_postregistration_possession(tmp_path, monkeypatch, mode):
    # Keep the AF_UNIX pathname short; unknown cleanup must retain the directory,
    # so a TemporaryDirectory auto-remover would be inappropriate here.
    root = Path(tempfile.mkdtemp(prefix="hmp-life-", dir="/private/tmp"))
    if mode == "prequeued":
        monkeypatch.setattr(probe, "_RANDOM", lambda _: pytest.fail("nonce before predrain"))
    row = None
    try:
        row = probe.run_owned_case(root, mode,
            admission_ns=200_000_000 if mode == "silent" else 2_000_000_000)
    finally:
        if row is None:
            row = {"no_completed_receipt": True, "retained_directory": str(root)}
        elif row["cleanup_known"]:
            root.rmdir()
            row["temporary_directory_removed"] = True
        else:
            row["retained_directory"] = str(root)
        descriptor = os.open(tmp_path / "observation.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                             0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(row, stream, sort_keys=True)
    assert row["attempts"] == 1
    assert row["exchange_observed"] is (mode == "echo"), row
    assert row["production_qualified"] is False
    assert row["child_wait_known"] is True, row
    assert row["cleanup_known"] is True, row
    assert row["child_output_empty"] is True, row
    if row["observer_registered"]:
        assert row["observer_close_known"] is True, row
    assert not (root / "s").exists()
    if mode == "echo":
        assert row["observer_pending_after_response"] is True
        assert row["challenge_bytes_sent"] == len(probe._CHALLENGE) + 64
        assert row["response_bytes_received"] == len(probe._RESPONSE) + 64
    else:
        assert row["refused"] is True, row
    if mode == "prequeued":
        assert row["stage"] == "predrain" and row["challenge_bytes_sent"] == 0
    if mode == "delegated":
        assert row["original_peer_exit_observed"] is True, row
        assert row["bare_echo_after_original_exit"] is True, row


@pytest.mark.parametrize("mode", [None, True, "arbitrary", b"echo"])
def test_invalid_mode_has_no_process_or_socket_effect(tmp_path, monkeypatch, mode):
    monkeypatch.setattr(probe.sys, "platform", "darwin")
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *a, **kw: pytest.fail("child created"))
    monkeypatch.setattr(probe.socket, "socket", lambda *a, **kw: pytest.fail("socket created"))
    with pytest.raises(probe.ProbeRefusedError):
        probe.run_owned_case(tmp_path, mode)


def test_preexisting_path_is_refused_without_unlink_or_process(tmp_path, monkeypatch):
    monkeypatch.setattr(probe.sys, "platform", "darwin")
    path = tmp_path / "s"
    path.write_bytes(b"unrelated fixture sentinel")
    before = len(probe._RETAINED)
    monkeypatch.setattr(probe.socket, "socket", lambda *a, **kw: pytest.fail("socket created"))
    row = probe.run_owned_case(tmp_path, "echo")
    assert row["refused"] is True and row["cleanup_known"] is True
    assert path.read_bytes() == b"unrelated fixture sentinel"
    assert len(probe._RETAINED) == before


@pytest.mark.parametrize("admission", [True, 0, -1, 99_999_999, 2_000_000_001, "200000000"])
def test_invalid_admission_never_allocates(tmp_path, monkeypatch, admission):
    monkeypatch.setattr(probe.sys, "platform", "darwin")
    monkeypatch.setattr(probe.socket, "socket", lambda *a, **kw: pytest.fail("socket created"))
    with pytest.raises(probe.ProbeRefusedError):
        probe.run_owned_case(tmp_path, "echo", admission_ns=admission)
