"""Tests for tools/fixtures/phone_attachment_primitives.py.

The unit tests need no native build. The `native` tests run the real fixture once against the
pinned native interpreter and skip when it is absent (local-only, like the other build-bound
fixture tests). All data is synthetic.
"""

from __future__ import annotations

import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import phone_attachment_primitives as fx
import pytest

NATIVE_AVAILABLE = fx.native_python(fx.DEFAULT_NATIVE_SRC).is_file()
native = pytest.mark.skipif(not NATIVE_AVAILABLE, reason="pinned native build not present")


# ---- unit tests (no native build) ------------------------------------------------------------


def png_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    out, at = [], 8
    while at < len(data):
        (length,) = struct.unpack(">I", data[at : at + 4])
        kind, body = data[at + 4 : at + 8], data[at + 8 : at + 8 + length]
        (crc,) = struct.unpack(">I", data[at + 8 + length : at + 12 + length])
        assert crc == zlib.crc32(kind + body) & 0xFFFFFFFF
        out.append((kind, body))
        at += 12 + length
    return out


def test_synthetic_png_is_valid_and_sizes_are_exact() -> None:
    plain = fx.synthetic_png()
    assert [k for k, _ in png_chunks(plain)] == [b"IHDR", b"IDAT", b"IEND"]
    for size in (len(plain) + 14, 512, 513):
        padded = fx.synthetic_png(size=size)
        assert len(padded) == size
        assert [k for k, _ in png_chunks(padded)] == [b"IHDR", b"tEXt", b"IDAT", b"IEND"]
    with pytest.raises(ValueError):
        fx.synthetic_png(size=len(plain))


def test_child_environment_is_a_private_allow_list(tmp_path: Path) -> None:
    layout = fx.scratch_layout(tmp_path)
    env = fx.child_environment(layout)
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert "PYTHONPATH" not in env
    assert not [
        k
        for k in env
        if any(t in k.upper() for t in ("KEY", "TOKEN", "SECRET", "PASSWORD", "PROXY"))
    ]
    for name in (
        "HOME",
        "HERMES_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "TMPDIR",
    ):
        assert Path(env[name]).is_relative_to(tmp_path), name
    assert env["PATH"] == "/usr/bin:/bin"


def test_fingerprint_detects_a_one_byte_change(tmp_path: Path) -> None:
    for name in fx.OWNING_FILES:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"original")
    before = fx.fingerprint(tmp_path)
    assert set(before) == set(fx.OWNING_FILES)
    assert fx.fingerprint(tmp_path) == before
    (tmp_path / fx.OWNING_FILES[3]).write_bytes(b"originam")
    after = fx.fingerprint(tmp_path)
    assert [k for k in before if before[k] != after[k]] == [fx.OWNING_FILES[3]]


def test_parse_child_output_takes_the_last_json_object() -> None:
    assert fx.parse_child_output('noise\n{"a": 1}\n{"b": 2}\n') == {"b": 2}
    assert fx.parse_child_output("{broken\n") == {
        "status": "ERROR",
        "reason": "child_output_unparseable",
    }
    assert fx.parse_child_output("") == {"status": "ERROR", "reason": "child_output_unparseable"}


def test_missing_interpreter_is_reported_not_raised(tmp_path: Path) -> None:
    assert fx.run_parent(tmp_path) == {
        "status": "UNAVAILABLE",
        "reason": "native_interpreter_missing",
    }


def test_ip_denial_blocks_ip_and_allows_unix() -> None:
    """Runs in a subprocess so the socket patch cannot leak into the test process."""
    code = (
        "import json, phone_attachment_primitives as fx;"
        "fx.install_ip_denial();"
        "print(json.dumps({'self_test': fx.verify_ip_denial(), 'blocked': fx._BLOCKED_NETWORK}))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(fx.__file__).parent,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=30,
        check=True,
    )
    out = json.loads(proc.stdout)
    assert set(out["self_test"]) == set(fx.DENIAL_KEYS), out
    assert out["self_test"]["denies_connect_ex"] is True
    assert all(out["self_test"].values()), out
    assert out["blocked"] == 0  # the self-test attempts are not counted as native attempts


def test_ip_denial_self_test_counts_all_four_attempts_and_catches_omission() -> None:
    code = (
        "import json, socket, phone_attachment_primitives as fx;"
        "fx.install_ip_denial();"
        "socket.socket.connect_ex = lambda self, *a, **k: 0;"
        "print(json.dumps(fx.verify_ip_denial()))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(fx.__file__).parent,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=30,
        check=True,
    )
    broken = json.loads(proc.stdout)
    # An un-denied connect_ex is reported, and the attempt count no longer matches four.
    assert fx.SELF_TEST_ATTEMPTS == 4
    assert broken["denies_connect_ex"] is False
    assert broken["self_test_attempts_counted"] is False
    assert broken["denies_connect"] is True


def valid_report() -> dict:
    return {
        "status": "PASS_WITH_EVIDENCE_GAP",
        "child_exit_code": 0,
        "imports_from_native_src": True,
        "hermes_home_resolves_to_scratch": True,
        "isolation": dict.fromkeys(fx.ISOLATION_KEYS, True),
        "ip_denial_self_test": dict.fromkeys(fx.DENIAL_KEYS, True),
        "source_unchanged": True,
        "scratch_removed": True,
        "blocked_ip_attempts_during_run": 0,
        "child_stderr_lines": 0,
        "child_stderr_mentions_scratch": False,
        "native_log_records_mentioning_cache_paths": 0,
    }


def test_valid_report_passes_with_gap_status_kept() -> None:
    assert fx.boundary_failure(valid_report()) is None
    out, code = fx.disposition(valid_report())
    assert code == 0 and out["status"] == "PASS_WITH_EVIDENCE_GAP"


@pytest.mark.parametrize("name", [n for n, _ in fx.BOUNDARY_CHECKS])
def test_each_boundary_fails_closed_when_missing_false_or_malformed(name: str) -> None:
    for mutate in ("missing", "bad"):
        report = valid_report()
        if mutate == "missing":
            del report[name]
        else:
            report[name] = "SECRET-LEAK" if name != "child_exit_code" else 1
        out, code = fx.disposition(report)
        assert code == 1, (name, mutate)
        assert out["status"] == "ERROR" and out["reason"] == "run_boundary_not_held"
        assert out["failed_boundary"] == name
        assert "SECRET-LEAK" not in json.dumps(out)


def test_nested_isolation_and_denial_members_and_bool_int_confusion() -> None:
    for group, keys in (("isolation", fx.ISOLATION_KEYS), ("ip_denial_self_test", fx.DENIAL_KEYS)):
        for key in keys:
            for bad in (False, None, 1):
                report = valid_report()
                report[group][key] = bad
                assert fx.boundary_failure(report) == group, (group, key, bad)
            report = valid_report()
            del report[group][key]
            assert fx.boundary_failure(report) == group
        report = valid_report()
        report[group] = {}
        assert fx.boundary_failure(report) == group
    for name in ("blocked_ip_attempts_during_run", "child_exit_code"):
        report = valid_report()
        report[name] = False  # bool is not an int zero
        assert fx.boundary_failure(report) == name


def test_non_pass_statuses_keep_their_own_disposition() -> None:
    for status in ("UNAVAILABLE", "FAIL", "ERROR"):
        out, code = fx.disposition({"status": status, "reason": "x"})
        assert code == 1 and out["status"] == status and out["reason"] == "x"


def test_subcase_status_rules() -> None:
    sc = fx.Subcase("x")
    assert sc.status() == "PASS"
    sc.check("a", True)
    sc.gap("g", "reason")
    assert sc.status() == "PASS_WITH_EVIDENCE_GAP"
    sc.check("b", False)
    assert sc.status() == "FAIL"
    assert sc.report()["failed_checks"] == ["b"]
    sc.error = "ValueError"
    assert sc.status() == "ERROR"


# ---- native tests (real imports under the pinned interpreter) ---------------------------------


@pytest.fixture(scope="module")
def result() -> dict:
    return fx.run_parent(fx.DEFAULT_NATIVE_SRC)


def sub(result: dict, name: str) -> dict:
    return result["subcases"][name]


@native
def test_run_boundaries(result: dict) -> None:
    assert result["child_exit_code"] == 0
    assert result["source_unchanged"] is True
    assert result["scratch_removed"] is True
    assert result["blocked_ip_attempts_during_run"] == 0
    assert result["imports_from_native_src"] is True
    assert result["hermes_home_resolves_to_scratch"] is True
    assert all(result["isolation"].values()), result["isolation"]
    assert all(result["ip_denial_self_test"].values())
    assert result["child_stderr_mentions_scratch"] is False
    assert result["native_log_records_mentioning_cache_paths"] == 0
    assert result["runtime_bootstrap_dir_created"] is False
    assert set(result["source_fingerprints_before"]) == set(fx.OWNING_FILES)
    assert "python_level_socket_patch_not_os_sandbox" in result["instrumentation_limits"]


@native
def test_no_subcase_failed_and_every_gap_is_named(result: dict) -> None:
    assert result["status"] == "PASS_WITH_EVIDENCE_GAP"
    assert set(result["subcases"]) == {name for name, _ in fx.SUBCASES}
    for name, report in result["subcases"].items():
        assert report["status"] in {"PASS", "PASS_WITH_EVIDENCE_GAP"}, (
            name,
            report["failed_checks"],
        )
        assert report["checks_total"] > 0 and report["checks_passed"] == report["checks_total"]
    assert set(sub(result, "inbound_preparation")["evidence_gaps"]) == {
        "text_mode_image_enrichment",
        "audio_video_notes",
    }
    assert set(sub(result, "busy_handling")["evidence_gaps"]) == {
        "runner_busy_handler_entry",
        "hmp_defer_policy_reject",
    }
    assert "agent_turn_flush_stage" in sub(result, "durable_rows")["evidence_gaps"]


@native
def test_summary_carries_no_content_ids_or_paths(result: dict) -> None:
    text = json.dumps(result)
    for needle in (
        fx.SENTINEL,
        "hmp-att-",
        "/hermes/profiles",
        "client-doc",
        "synthetic caption",
        "chat-synthetic",
    ):
        assert needle not in text, needle


@native
def test_cache_helpers_outcomes(result: dict) -> None:
    report = sub(result, "cache_helpers")
    assert report["status"] == "PASS"
    obs = report["observations"]
    # The native document path has no size bound and no private mode; these are observations
    # about this build, not permission for unbounded product input.
    assert obs["document_above_image_cap_is_cached"] is True
    assert obs["native_applies_no_private_chmod"] is True
    assert obs["magic_prefix_alone_is_accepted_without_decode"] is True
    assert obs["cap_negative_rejects_any_positive_size"] is True
    assert obs["cap_unparseable_falls_back_to_default"] is True
    assert obs["posix_backslash_not_treated_as_separator"] is True
    assert obs["newline_in_name_kept_in_cache_path"] is True


@native
def test_inline_flag_changes_only_the_claim_not_the_content(result: dict) -> None:
    report = sub(result, "inbound_preparation")
    assert report["status"] == "PASS_WITH_EVIDENCE_GAP"
    obs = report["observations"]
    assert obs["preparation_accepts_path_outside_cache"] is True
    assert obs["filename_newline_reaches_note_text_via_path"] is True


@native
def test_busy_policy_distinguishes_photo_merge_from_document_fifo(result: dict) -> None:
    obs = sub(result, "busy_handling")["observations"]
    # The base adapter fallback merges any media; the runner's policy does not.
    assert obs["base_photo_then_document_merged_into_one"] is True
    assert obs["base_document_then_document_merged_into_one"] is True


@native
def test_durable_row_projection_and_ids(result: dict) -> None:
    obs = sub(result, "durable_rows")["observations"]
    assert obs["string_override_did_not_replace_part_list"] is True
    assert obs["image_row_placeholder_joined_with_caption"] is True
    assert not [
        k for k in obs["row_field_names"] if any(w in k for w in ("media", "attach", "path", "url"))
    ]
    assert "platform_message_id" in obs["row_field_names"]
