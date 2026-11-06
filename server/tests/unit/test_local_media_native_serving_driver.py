"""Source materializer/entry models; no Git command or native DB is executed."""
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[3] / "tools/compat/local_media_native_serving_driver.py"
_SPEC = importlib.util.spec_from_file_location("_native_media_driver_test", _PATH)
driver = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = driver
_SPEC.loader.exec_module(driver)
COMMIT = "a" * 40


def archive(path, files, commit=COMMIT):
    with tarfile.open(path, "w", format=tarfile.PAX_FORMAT,
                      pax_headers={"comment": commit}) as output:
        for name, payload in files.items():
            info = tarfile.TarInfo(name)
            info.mode = 0o600
            if isinstance(payload, tuple):
                info.type, info.linkname = payload
                output.addfile(info)
            else:
                info.size = len(payload)
                output.addfile(info, io.BytesIO(payload))
    os.chmod(path, 0o600)


def good(native=None, hmp=None, executable="e" * 64):
    report = dict.fromkeys(driver._TRUE, True)
    report.update(dict.fromkeys(driver._FALSE, False))
    report.update(schema=1, native_acquires=2, native_releases=2,
        descriptor_records_retained=1, audit_denials=0, scoped_native_sweep=0,
        expected_absent_proc_probes=2, os_metadata_sha256="d" * 64,
        os_metadata_reads=2, own_fd_listings=2, native_cache_materializations=3,
        native_source_hashes=native or {"hermes_state.py": "a" * 64},
        hmp_source_hashes=hmp or {"server/hmp_plugin/__init__.py": "b" * 64},
        runtime_executable_sha256=executable)
    return report


def test_plain_sources_are_materialized_privately(tmp_path):
    bundle = tmp_path / "source.tar"
    archive(bundle, {"package/code.py": b"# source\n", "schema.json": b"{}"})
    result = driver.extract_sources(bundle, tmp_path / "source", COMMIT)
    assert result["package/code.py"] == hashlib.sha256(b"# source\n").hexdigest()
    assert (tmp_path / "source/package/code.py").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("kind", ["absolute", "traversal", "symlink", "hardlink", "fifo",
                                 "bytecode", "zip", "wrong_commit"])
def test_unsafe_archive_refuses_before_native_entry(tmp_path, kind):
    bundle = tmp_path / "source.tar"
    name, payload = "bad.py", b"not executed"
    commit = COMMIT
    if kind == "absolute":
        name = str(tmp_path / "escape.py")
    elif kind == "traversal":
        name = "../escape.py"
    elif kind == "symlink":
        payload = (tarfile.SYMTYPE, "../escape.py")
    elif kind == "hardlink":
        payload = (tarfile.LNKTYPE, "elsewhere.py")
    elif kind == "fifo":
        payload = (tarfile.FIFOTYPE, "")
    elif kind in ("bytecode", "zip"):
        name = "bad.pyc" if kind == "bytecode" else "bad.zip"
    else:
        commit = "b" * 40
    archive(bundle, {name: payload}, commit)
    with pytest.raises(driver.commands.NativeSenderFixtureError):
        driver.extract_sources(bundle, tmp_path / "source", COMMIT)
    assert not (tmp_path / "escape.py").exists()


def test_member_count_stops_before_second_write(tmp_path, monkeypatch):
    bundle = tmp_path / "source.tar"
    archive(bundle, {"first.py": b"", "second.py": b""})
    monkeypatch.setattr(driver, "_MAX_ENTRIES", 1)
    with pytest.raises(driver.commands.NativeSenderFixtureError):
        driver.extract_sources(bundle, tmp_path / "source", COMMIT)
    assert (tmp_path / "source/first.py").exists()
    assert not (tmp_path / "source/second.py").exists()


@pytest.mark.parametrize("field,value", [("schema", True), ("production_qualified", True),
    ("audit_denials", 1), ("scoped_native_sweep", False), ("native_releases", 1),
    ("unexpected", "refused"), ("native_database_close_observed", False)])
def test_unqualified_or_coerced_report_refuses(field, value):
    report = good()
    report[field] = value
    with pytest.raises(driver.commands.NativeSenderFixtureError):
        driver.validate_report(report, {"hermes_state.py": "a" * 64},
            {"server/hmp_plugin/__init__.py": "b" * 64}, "e" * 64)


def test_complete_controller_model_never_executes_commands(tmp_path, monkeypatch):
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    roles = []
    fixture_bytes = driver._FIXTURE.read_bytes()

    def model(argv, directory, role, receipt, **kwargs):
        roles.append(role)
        row = {"role": role, "wait_known": True, "returncode": 0, "model_only": True}
        receipt["commands"].append(row)
        if role == "git_version":
            return b"git version 2.54.0\n"
        if role == "hmp_head":
            return ("b" * 40 + "\n").encode()
        if role.endswith("_kind"):
            return b"commit\n"
        if role.endswith("_tar_config"):
            row["returncode"] = 1
            for suffix in ("stdout", "stderr"):
                path = directory / (role + "." + suffix)
                path.write_bytes(b"")
            raise driver.commands.NativeSenderFixtureError()
        if role.endswith(("_archive", "_tree")):
            if role.startswith("native_"):
                files = {"hermes_state.py": b"# model", "hermes_state_registry.py": b"# model"}
                commit = COMMIT
            else:
                files = {"tools/compat/local_media_native_serving_fixture.py": fixture_bytes,
                    "server/hmp_plugin/__init__.py": b"", "server/tests/unit/__init__.py": b"",
                    "server/tests/unit/test_s5_media_fetch.py": b"# model",
                    "server/tests/unit/test_s4_descriptors.py": b"# model",
                    "server/tests/unit/hmp_kit.py": b"# model"}
                commit = "b" * 40
            if role.endswith("_tree"):
                return b"".join(b"100644 blob " + hashlib.sha1(
                    b"blob " + str(len(data)).encode() + b"\0" + data,
                    usedforsecurity=False).hexdigest().encode() + b"\t" + name.encode() + b"\0"
                    for name, data in files.items())
            archive(directory / role.replace("_archive", ".tar"), files, commit)
            return b""
        assert role == "native_serving"
        copies = json.loads((directory / "source-manifest.json").read_text())
        report = good(copies["native"], copies["hmp"],
                      driver.commands._digest(Path(sys.executable).resolve()))
        data = json.dumps(report).encode()
        (directory / "native-serving-report.json").write_bytes(data)
        return json.dumps({"schema": 1, "completed": True,
                           "report_sha256": hashlib.sha256(data).hexdigest()}).encode()

    monkeypatch.setattr(driver.commands, "_owned", model)
    result = driver.run_fixture(root, tmp_path / "never-executed-native-repo", COMMIT)
    assert result["completed"] is True and result["production_qualified"] is False
    assert roles == ["git_version", "hmp_head", "native_kind", "native_tar_config",
                     "native_tree", "native_archive", "hmp_kind", "hmp_tar_config",
                     "hmp_tree", "hmp_archive", "native_serving"]
    assert all(row["model_only"] is True for row in result["commands"])


def test_actual_entry_selects_private_cwd_before_fixture_import(tmp_path):
    """Execute only the fixed stdlib entry and a stub; never native DB/modules."""
    root = tmp_path / "owned-entry"
    fixture = root / "hmp/tools/compat/local_media_native_serving_fixture.py"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("from pathlib import Path\n"
        "def run_fixture(root):\n"
        "    assert Path.cwd() == root\n"
        "    return {'stub_only': True}\n")
    entry = root / "entry.py"
    entry.write_text(driver._ENTRY)
    result = subprocess.run([sys.executable, "-I", "-B", str(entry), str(root)],
        cwd=tmp_path, capture_output=True, check=True, timeout=10)
    marker = json.loads(result.stdout)
    data = (root / "native-serving-report.json").read_bytes()
    assert json.loads(data) == {"stub_only": True}
    assert marker == {"schema": 1, "completed": True,
                      "report_sha256": hashlib.sha256(data).hexdigest()}
    assert (root / "native-serving-report.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("state", ["configured", "timeout", "error", "diagnostic"])
def test_tar_filter_probe_accepts_only_known_absent_key(tmp_path, monkeypatch, state):
    receipt = {"commands": []}
    role = "native_tar_config"

    def probe(root, repository, arguments, actual_role, records):
        assert actual_role == role
        row = {"role": role, "wait_known": True, "returncode": 1}
        records["commands"].append(row)
        if state == "configured":
            return b"unapproved-filter\n"
        row.update(settlement_only_used=state == "timeout",
                   returncode=2 if state == "error" else 1)
        for suffix in ("stdout", "stderr"):
            path = root / (role + "." + suffix)
            path.write_bytes(b"failure" if state == "diagnostic" else b"")
            path.chmod(0o600)
        raise driver.commands.NativeSenderFixtureError()

    monkeypatch.setattr(driver, "_git", probe)
    with pytest.raises(driver.commands.NativeSenderFixtureError):
        driver._no_custom_tar(tmp_path, tmp_path / "not-executed", "native", receipt)
    assert len(receipt["commands"]) == 1
    assert "expected_absent_config" not in receipt["commands"][0]


@pytest.mark.parametrize("change", ["missing", "extra", "substituted", "symlink"])
def test_literal_commit_binding_refuses_archive_attribute_changes(tmp_path, change):
    original = b"# exact committed bytes\n"
    oid = hashlib.sha1(b"blob " + str(len(original)).encode() + b"\0" + original,
                       usedforsecurity=False).hexdigest()
    mode = b"120000" if change == "symlink" else b"100644"
    raw = mode + b" blob " + oid.encode() + b"\tcode.py\0"
    if change == "symlink":
        with pytest.raises(driver.commands.NativeSenderFixtureError):
            driver.literal_sources(raw, COMMIT)
        return
    expected = driver.literal_sources(raw, COMMIT)
    source = tmp_path / "source"
    source.mkdir()
    path = source / "code.py"
    path.write_bytes(original if change != "substituted" else b"# export-subst changed\n")
    path.chmod(0o600)
    inventory = {} if change == "missing" else {"code.py": "not-used-as-blob-authority"}
    if change == "extra":
        inventory["extra.py"] = "not-authorized"
    with pytest.raises(driver.commands.NativeSenderFixtureError):
        driver.verify_literal_sources(source, inventory, expected)


def test_exported_executable_mode_must_match_literal_tree(tmp_path):
    bundle = tmp_path / "source.tar"
    archive(bundle, {"code.py": b"# plain"})
    with pytest.raises(driver.commands.NativeSenderFixtureError):
        driver.extract_sources(bundle, tmp_path / "source", COMMIT,
                               {"code.py": ("100755", "a" * 40)})


def test_archive_framing_does_not_expand_extracted_source_budget(tmp_path, monkeypatch):
    bundle = tmp_path / "source.tar"
    archive(bundle, {"code.py": b"12"})
    monkeypatch.setattr(driver, "_MAX_SOURCE", 1)
    with pytest.raises(driver.commands.NativeSenderFixtureError):
        driver.extract_sources(bundle, tmp_path / "refused", COMMIT)
    assert not (tmp_path / "refused/code.py").exists()
    monkeypatch.setattr(driver, "_MAX_SOURCE", 2)
    assert driver.extract_sources(bundle, tmp_path / "accepted", COMMIT)
