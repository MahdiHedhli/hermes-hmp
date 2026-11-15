"""Composed fixed-install synthetic harness; fixture manifests are test oracles."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "server" / "hmp_plugin"
INVENTORY = ROOT / "tools" / "compat" / "presentation_broker_install_inventory.py"
ENV = {"LANG": "C", "LC_ALL": "C"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


@pytest.fixture
def install(tmp_path):
    if os.name != "posix" or os.geteuid() <= 0 or sys.platform not in ("darwin", "linux"):
        pytest.skip("non-root supported POSIX synthetic harness")
    original_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # keep this fixture's runtime generation stable
    plugin, parser = tmp_path / "plugin", tmp_path / "yaml"
    plugin.mkdir(mode=0o700)
    parser.mkdir(mode=0o700)
    for path in PACKAGE.glob("*.py"):
        shutil.copyfile(path, plugin / path.name)
    for path in Path(yaml.__file__).parent.glob("*.py"):
        shutil.copyfile(path, parser / path.name)
    tripwire = "raise RuntimeError('SYNTHETIC_INITIALIZER_MUST_NOT_EXECUTE')\n"
    (plugin / "__init__.py").write_text(tripwire)
    (parser / "__init__.py").write_text(tripwire)
    (plugin / "sitecustomize.py").write_text(tripwire)
    manifest = tmp_path / "external-expected.json"
    python = str(Path(sys.executable).resolve(strict=True))

    def build(python_override=None):
        if manifest.exists():
            manifest.unlink()
        result = subprocess.run(
            [python_override or python, "-I", "-B", "-S", str(INVENTORY), str(plugin), str(parser),
             "d" * 64, str(manifest)],
            env=ENV, stdin=subprocess.DEVNULL, capture_output=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr[-1000:]
        assert json.loads(result.stdout)["candidate_only"] is True
        raw = manifest.read_bytes()
        assert manifest.stat().st_mode & 0o777 == 0o600
        return raw

    def run(
        raw=None, expected=None, flags=None, environment=None, timeout=30, python_override=None
    ):
        if raw is not None:
            manifest.write_bytes(raw)
        digest = expected or hashlib.sha256(manifest.read_bytes()).hexdigest()
        args = [python_override or python, *(flags if flags is not None else ["-I", "-B", "-S"]),
                str(plugin / "presentation_broker_bootstrap.py"),
                "--manifest", str(manifest), "--expected-sha256", digest]
        process = subprocess.Popen(
            args, env=ENV if environment is None else environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return process.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            # Signal only with the owned leader still unreaped: no post-wait
            # numeric-group signaling and no production closure inference.
            assert process.returncode is None
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)
            raise

    yield plugin, parser, manifest, build, run
    sys.dont_write_bytecode = original_bytecode


def refused(result):
    code, stdout, stderr = result
    assert code == 1
    assert stdout == b""
    assert stderr == b"BI1_BROKER_BOOTSTRAP_REFUSED\n"


def test_actual_retained_registry_empty_input_no_go(install):
    _, _, _, build, run = install
    build()
    code, stdout, stderr = run()
    assert code == 0, stderr
    assert stderr == b""
    assert json.loads(stdout) == {
        "schema": 1, "mode": "synthetic_no_go", "registry_retained": True,
        "local_drain_observed": True, "registry_pending": True,
        "production_qualified": False,
    }


@pytest.mark.parametrize("change", ["plugin", "parser", "pyc", "cache", "symlink", "archive"])
def test_source_or_executable_inventory_substitution_refused(install, change):
    plugin, parser, _, build, run = install
    raw = build()
    if change == "plugin":
        (plugin / "presentation_jobs.py").write_text("raise RuntimeError('changed')\n")
    elif change == "parser":
        (parser / "tokens.py").write_text("raise RuntimeError('changed')\n")
    elif change == "pyc":
        (plugin / "legacy.pyc").write_bytes(b"synthetic")
    elif change == "cache":
        (parser / "__pycache__").mkdir()
    elif change == "archive":
        (plugin / "injected.zip").write_bytes(b"synthetic")
    else:
        (plugin / "alias.py").symlink_to("presentation_jobs.py")
    refused(run(raw))


@pytest.mark.parametrize(
    "change", ["path", "prefix", "version", "native", "interpreter", "overlap"]
)
def test_runtime_and_root_mismatch_refused(install, change):
    plugin, _, _, build, run = install
    document = json.loads(build())
    runtime = document["runtime"]
    if change == "path":
        runtime["sys_path"].append({"path": str(plugin), "exists": True})
    elif change == "prefix":
        runtime["base_prefix"] = str(plugin)
    elif change == "version":
        runtime["version"][1] += 1
    elif change == "native":
        runtime["os_library_locations"].append("/usr/local/lib")
    elif change == "interpreter":
        runtime["executable_sha256"] = "0" * 64
    else:
        document["trees"][2]["root"] = str(plugin)
    refused(run(canonical(document)))


@pytest.mark.parametrize("change", ["digest", "noncanonical", "duplicate", "schema", "entry"])
def test_manifest_refusals_before_broker_import(install, change):
    _, _, _, build, run = install
    raw = build()
    if change == "digest":
        refused(run(raw, expected="0" * 64))
        return
    document = json.loads(raw)
    if change == "noncanonical":
        raw += b"\n"
    elif change == "duplicate":
        raw = raw.replace(b'"schema":1', b'"schema":1,"schema":1')
    elif change == "schema":
        document["schema"] = True
        raw = canonical(document)
    else:
        document["trees"][1]["entries"].append(document["trees"][1]["entries"][0])
        raw = canonical(document)
    refused(run(raw))


def test_missing_isolation_flag_refused(install):
    _, _, _, build, run = install
    build()
    refused(run(flags=["-I", "-B"]))


def test_loader_environment_refused(install):
    _, _, _, build, run = install
    build()
    refused(run(environment={**ENV, "PYTHONPATH": "/synthetic-unused"}))


def test_inventory_tool_does_not_execute_candidate_bootstrap(install):
    plugin, _, _, build, _ = install
    candidate = plugin / "presentation_broker_bootstrap.py"
    candidate.write_text("raise RuntimeError('CANDIDATE_MUST_NOT_EXECUTE_DURING_INVENTORY')\n")
    document = json.loads(build())
    row = next(r for r in document["trees"][1]["entries"]
               if r["path"] == candidate.name)
    assert row["sha256"] == hashlib.sha256(candidate.read_bytes()).hexdigest()


@pytest.mark.parametrize("fault", ["mutation", "deadline", "final_mutation"])
def test_phase_generation_and_original_deadline_fences_prevent_publication(install, fault):
    plugin, _, manifest, build, run = install
    bootstrap = plugin / "presentation_broker_bootstrap.py"
    content = bootstrap.read_text()
    marker = manifest.parent / "popen-attempted"
    child = plugin / "presentation_broker_child.py"
    child_text = child.read_text().replace("import os\n", "import os\nfrom pathlib import Path\n")
    child_text = child_text.replace(
        "    def start(self) -> None:\n",
        "    def start(self) -> None:\n"
        + f"        Path({str(marker)!r}).write_text('attempted')\n",
    )
    child.write_text(child_text)
    if fault == "mutation":
        content = content.replace(
            "        installation.fence(deadline)",
            "        (Path(plugin) / 'unexpected.py').write_text('# synthetic')\n"
            "        installation.fence(deadline)",
        )
    elif fault == "deadline":
        content = content.replace("        installation.fence(deadline)",
                                  "        time.sleep(1.95)\n        installation.fence(deadline)")
    else:
        content = content.replace(
            "    installation.fence()  # diagnostic",
            "    (Path(plugin) / 'unexpected.py').write_text('# synthetic')\n"
            "    installation.fence()  # diagnostic",
        )
    bootstrap.write_text(content)
    build()  # explicit faulted synthetic oracle, NOT candidate qualification
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        run(timeout=5)
    assert caught.value.stderr == b"BI1_BROKER_BOOTSTRAP_REFUSED\n"
    assert marker.exists() is (fault == "final_mutation")


@pytest.mark.parametrize("change", ["absent_zip", "runtime_file"])
def test_actual_private_runtime_generation_change_refused(install, tmp_path, change):
    _, _, _, build, run = install
    original = Path(sys.base_prefix).resolve()
    copied = tmp_path / "private-runtime"
    try:
        shutil.copytree(original, copied, symlinks=True)
        executable = copied / Path(sys.executable).resolve().relative_to(original)
        document = json.loads(build(str(executable)))
        if change == "absent_zip":
            absent = next(r["path"] for r in document["runtime"]["sys_path"]
                          if r["path"].endswith(".zip") and r["exists"] is False)
            Path(absent).write_bytes(b"SYNTHETIC_INERT_ARCHIVE")
        else:
            row = next(r for r in document["trees"][0]["entries"]
                       if r["kind"] == "file" and "/xml/" in r["path"]
                       and r["path"].endswith(".py"))
            with (copied / row["path"]).open("ab") as stream:
                stream.write(b"\n# SYNTHETIC_RUNTIME_CHANGE\n")
        refused(run(python_override=str(executable)))
    finally:
        if copied.exists():
            shutil.rmtree(copied)  # only this test's new private runtime copy


def test_directory_enumeration_stops_at_cap_before_consuming_more(tmp_path, monkeypatch):
    from hmp_plugin import presentation_broker_bootstrap as module

    consumed = []

    class Entry:
        def __init__(self, name):
            self.name = name

    class Scan:
        def __enter__(self):
            def entries():
                for i in range(4):
                    consumed.append(i)
                    yield Entry(str(i))
                pytest.fail("enumerated past cap")
            return entries()

        def __exit__(self, *args):
            return False

    with monkeypatch.context() as patch:
        patch.setattr(module, "_MAX_ENTRIES", 3)
        patch.setattr(module.os, "scandir", lambda p: Scan())
        with pytest.raises(module.BootstrapError):
            module.inventory(str(tmp_path), source_only=True, budget=[0, 0])
    assert consumed == [0, 1, 2, 3]


@pytest.mark.parametrize("encoding", ["wrong_uid", "0x1:xxx:xxx", "0x1:0x:0", "0x1:-1:0",
                                       "0x1:0x100000000:0", "0x1:00:0"])
def test_darwin_encoding_strict_grammar_and_uid(monkeypatch, encoding):
    from hmp_plugin import presentation_broker_bootstrap as module

    if encoding == "wrong_uid":
        encoding = f"0x{os.geteuid() + 1:x}:0x0:0x0"
    with monkeypatch.context() as patch:
        patch.setattr(module.sys, "platform", "darwin")
        patch.setattr(module.os, "environ", {**ENV, "__CF_USER_TEXT_ENCODING": encoding})
        with pytest.raises(module.BootstrapError):
            module._environment_current()


def test_darwin_encoding_accepted_only_on_darwin(monkeypatch):
    from hmp_plugin import presentation_broker_bootstrap as module

    environment = {**ENV, "__CF_USER_TEXT_ENCODING": f"0x{os.geteuid():x}:0x0:0"}
    with monkeypatch.context() as patch:
        patch.setattr(module.sys, "platform", "darwin")
        patch.setattr(module.os, "environ", environment)
        module._environment_current()
        patch.setattr(module.sys, "platform", "linux")
        with pytest.raises(module.BootstrapError):
            module._environment_current()


@pytest.mark.parametrize("alias", ["same_source", "symlink"])
def test_inventory_trust_source_cannot_alias_candidate(tmp_path, alias):
    trusted = tmp_path / "trusted"
    tool = trusted / "tools" / "compat" / INVENTORY.name
    verifier = trusted / "server" / "hmp_plugin" / "presentation_broker_bootstrap.py"
    tool.parent.mkdir(parents=True)
    verifier.parent.mkdir(parents=True)
    shutil.copyfile(INVENTORY, tool)
    plugin = verifier.parent if alias == "same_source" else tmp_path / "candidate"
    plugin.mkdir(exist_ok=True)
    parser = tmp_path / "yaml"
    parser.mkdir()
    marker = tmp_path / "candidate-executed"
    candidate = plugin / verifier.name
    candidate.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n")
    if alias == "symlink":
        verifier.symlink_to(candidate)
    manifest = tmp_path / "must-not-exist.json"
    result = subprocess.run(
        [str(Path(sys.executable).resolve()), "-I", "-B", "-S", str(tool),
         str(plugin), str(parser), "d" * 64, str(manifest)],
        env=ENV, stdin=subprocess.DEVNULL, capture_output=True, timeout=10,
    )
    assert result.returncode == 1
    assert result.stdout == b""
    assert result.stderr == b"BI1_CANDIDATE_INVENTORY_REFUSED\n"
    assert not manifest.exists()
    assert not marker.exists()
