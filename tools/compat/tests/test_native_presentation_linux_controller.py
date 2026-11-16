"""Controller contracts only; no Docker/native process or credential access."""

import copy
import importlib.util
import json
import os
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "native_linux_controller", Path(__file__).parents[1] / "native_presentation_linux_controller.py"
)
module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(module)


@pytest.fixture
def setup():
    root, source, prefix, venv, entry = map(
        Path, ("/test/root", "/test/source", "/test/python", "/test/venv", "/test/entry.py")
    )
    name = "hmp-native-" + "a" * 32
    arguments, mounts = module.create_arguments(
        name, root, source, prefix, venv, entry, "matrix", 1001, 1001
    )
    item = {
        "Name": "/" + name,
        "Id": "b" * 64,
        "Config": {
            "Labels": {module._LABEL: name},
            "Image": module._IMAGE,
            "User": "1001:1001",
            "WorkingDir": str(root),
            "Entrypoint": [str(venv / "bin/python")],
            "Cmd": ["-I", "-B", str(entry), str(root), str(source), "18443", "matrix"],
            "Env": [k + "=" + v for k, v in module.environment(root).items()],
            "OpenStdin": False,
            "Tty": False,
        },
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "Privileged": False,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"],
            "IpcMode": "private",
            "CgroupnsMode": "private",
            "PidMode": "",
            "UTSMode": "",
            "RestartPolicy": {"Name": "no"},
            "LogConfig": {"Type": "local", "Config": {"max-size": "1m", "max-file": "1"}},
            "PidsLimit": 128,
            "Memory": 2 * 1024**3,
            "MemorySwap": 2 * 1024**3,
            "NanoCpus": 2_000_000_000,
            "ShmSize": 1024**2,
        },
        "Mounts": [
            {"Source": str(p), "Destination": str(p), "RW": not ro, "Type": "bind"}
            for p, ro in mounts
        ],
        "NetworkSettings": {"Networks": {}},
    }
    return name, root, venv, entry, mounts, arguments, item


def check(setup, item):
    name, root, venv, entry, mounts, _, _ = setup
    return module.verify_container(item, name, root, venv, entry, "matrix", 1001, 1001, mounts)


def test_restricted_plan_and_exact_inspection_contract(setup, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-poison-never-propagated")
    monkeypatch.setenv("DOCKER_HOST", "tcp://synthetic.invalid:1234")
    arguments, item = setup[-2:]
    assert check(setup, item) == "b" * 64
    assert "--pull" in arguments and arguments[arguments.index("--pull") + 1] == "never"
    assert "--rm" not in arguments and "--privileged" not in arguments
    assert not any("synthetic-poison" in x or "synthetic.invalid" in x for x in arguments)
    assert [x["RW"] for x in item["Mounts"]] == [False] * 5 + [True]


@pytest.mark.parametrize(
    "key,value",
    [
        ("NetworkMode", "host"),
        ("ReadonlyRootfs", False),
        ("Privileged", True),
        ("CapAdd", ["SYS_ADMIN"]),
        ("CapDrop", []),
        ("SecurityOpt", []),
        ("PidMode", "host"),
        ("IpcMode", "host"),
        ("CgroupnsMode", "host"),
        ("Devices", [{"PathOnHost": "/synthetic-device"}]),
        ("DeviceRequests", [{"Driver": "synthetic"}]),
        ("AutoRemove", True),
        ("PortBindings", {"18443/tcp": [{"HostPort": "18443"}]}),
        ("RestartPolicy", {"Name": "always"}),
        ("Binds", ["/:/host"]),
        ("Tmpfs", {"/synthetic-tmp": "rw"}),
        ("LogConfig", {"Type": "json-file"}),
        ("Memory", 0),
        ("PidsLimit", -1),
    ],
)
def test_broadened_daemon_inspection_refuses(setup, key, value):
    item = copy.deepcopy(setup[-1])
    item["HostConfig"][key] = value
    with pytest.raises(module.LinuxJourneyError):
        check(setup, item)


@pytest.mark.parametrize(
    "fault",
    [
        "writable-source",
        "extra-mount",
        "credentials",
        "foreign-owner",
        "wrong-entry",
        "foreign-network",
    ],
)
def test_scope_and_identity_mutations_refuse(setup, fault):
    item = copy.deepcopy(setup[-1])
    if fault == "writable-source":
        item["Mounts"][0]["RW"] = True
    elif fault == "extra-mount":
        item["Mounts"].append(
            {
                "Source": "/var/run/docker.sock",
                "Destination": "/var/run/docker.sock",
                "RW": True,
                "Type": "bind",
            }
        )
    elif fault == "credentials":
        item["Config"]["Env"].append("TOKEN=synthetic")
    elif fault == "foreign-owner":
        item["Config"]["Labels"][module._LABEL] = "foreign"
    elif fault == "wrong-entry":
        item["Config"]["Cmd"][2] = "/other.py"
    else:
        item["NetworkSettings"]["Networks"] = {"bridge": {}}
    with pytest.raises(module.LinuxJourneyError):
        check(setup, item)


@pytest.mark.parametrize("mode,uid", [("other", 1001), ("matrix", 0), ("mutation", True)])
def test_root_or_unknown_scenario_is_not_admitted(setup, mode, uid):
    name, root, venv, entry, _, _, _ = setup
    with pytest.raises(module.LinuxJourneyError):
        module.create_arguments(
            name, root, Path("/test/source"), Path("/test/python"), venv, entry, mode, uid, 1001
        )


def test_runtime_measurement_detects_byte_and_link_mutation(tmp_path):
    prefix, venv = tmp_path / "prefix", tmp_path / "venv"
    prefix.mkdir(mode=0o700)
    venv.mkdir(mode=0o700)
    (prefix / "python").write_bytes(b"synthetic-interpreter")
    (venv / "python").symlink_to(prefix / "python")
    if hasattr(os, "lchmod"):
        os.lchmod(venv / "python", 0o777)  # Actual Linux links report0777.
    assert (venv / "python").lstat().st_mode & 0o777 == 0o777
    before = module.runtime_inventory(prefix, venv)
    (prefix / "python").write_bytes(b"changed-interpreter")
    assert before != module.runtime_inventory(prefix, venv)
    (venv / "python").unlink()
    (venv / "python").symlink_to(Path("/bin/sh"))
    with pytest.raises(module.LinuxJourneyError):
        module.runtime_inventory(prefix, venv)


def test_source_hash_mismatch_refuses_without_native_execution(tmp_path):
    (tmp_path / "source-manifest.json").write_bytes(b"synthetic wrong manifest")
    with pytest.raises(module.LinuxJourneyError):
        module.verify_sources(tmp_path)


def test_receipt_is_private_from_creation(tmp_path):
    path = tmp_path / "receipt.json"
    module.save(path, {"status": "synthetic-only"})
    assert path.stat().st_mode & 0o777 == 0o600
    assert json.loads(path.read_text()) == {"status": "synthetic-only"}
    assert not path.with_name("receipt.json.pending").exists()


def test_mac_run_refuses_before_root_effects(tmp_path):
    # The controller's Linux+isolated gates also reject ordinary unit-test imports.
    root = tmp_path / "must-not-be-created"
    with pytest.raises(module.LinuxJourneyError):
        module.run(root, root, root, root, Path("/synthetic/docker"), root, "a" * 64)
    assert not root.exists()


def test_partial_cli_constructor_return_is_owned_and_joined(tmp_path, monkeypatch):
    import subprocess

    owner = module.DockerOwner(Path("/usr/bin/true"), tmp_path)
    actors = []

    class LostReturn(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            actors.append(self)
            super().__init__(*args, **kwargs)
            raise RuntimeError("synthetic constructor return lost")

    monkeypatch.setattr(owner.commands, "_POPEN", LostReturn)
    with pytest.raises(RuntimeError, match="synthetic constructor return lost"):
        owner.call(["synthetic-only-no-daemon"])
    assert len(actors) == 1 and actors[0].returncode == 0
    assert owner.commands._RETAINED == []
    record = owner.receipt["commands"][0]
    assert record["wait_known"] is True and record["settlement_only_used"] is True


@pytest.mark.parametrize("fault", ["inspect-error", "foreign-observation", "receipt-error"])
def test_failure_reconciliation_retains_same_actor_until_terminal(tmp_path, monkeypatch, fault):
    name, identity = "hmp-native-" + "a" * 32, "b" * 64
    seen = []
    receipt, row = {}, {"startAttempted": True}

    class Owner:
        root = tmp_path

        def inspect(self, target):
            seen.append(target)
            if len(seen) == 1 and fault == "inspect-error":
                raise OSError("synthetic observation failed")
            state = "running" if len(seen) < 3 else "exited"
            return {
                "Name": "/" + name,
                "Id": identity,
                "Config": {
                    "Labels": {
                        module._LABEL: "foreign"
                        if len(seen) == 1 and fault == "foreign-observation"
                        else name
                    }
                },
                "State": {
                    "Status": state,
                    "Running": state == "running",
                    "Pid": 77 if state == "running" else 0,
                },
            }

    original_save = module.save
    writes = []

    def fail_once(path, value):
        writes.append(path)
        if len(writes) == 1 and fault == "receipt-error":
            raise OSError("synthetic private receipt unavailable")
        original_save(path, value)

    monkeypatch.setattr(module, "save", fail_once)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    module.reconcile(Owner(), name, identity, row, receipt)
    assert len(seen) == 3 and set(seen) == {identity}
    assert row["terminalAfterFailure"] is True and row["reconciliationActive"] is False
    if fault == "receipt-error":
        assert receipt["diagnosticWriteFailed"] is True


def test_uncertain_create_reconciles_name_without_replaying_create(tmp_path, monkeypatch):
    name, identity = "hmp-native-" + "a" * 32, "b" * 64
    observed = []

    class Owner:
        root = tmp_path

        def inspect(self, target):
            observed.append(target)
            if len(observed) == 1:
                raise OSError("synthetic no observation yet")
            return {
                "Name": "/" + name,
                "Id": identity,
                "Config": {"Labels": {module._LABEL: name}},
                "State": {"Status": "created", "Running": False, "Pid": 0},
            }

    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    row = {"createAttempted": True}
    module.reconcile(Owner(), name, None, row, {})
    assert observed == [name, name]
    assert row["containerId"] == identity and row["retainedInertNeverStarted"] is True
    assert "terminalAfterFailure" not in row


@pytest.mark.parametrize("boundary", ["receipt-before-start", "lost-start-response"])
def test_outer_failure_reconciles_original_actor_and_never_advances(
    tmp_path, monkeypatch, boundary
):
    from types import SimpleNamespace

    root, source, prefix, venv = [tmp_path / name for name in ("out", "source", "prefix", "venv")]
    for path in (root, source, prefix, venv):
        path.mkdir(mode=0o700)
    (prefix / "python").write_bytes(b"synthetic-not-executable")
    (venv / "bin").mkdir(mode=0o700)
    (venv / "bin/python").symlink_to(prefix / "python")
    calls, inspections = [], []
    identity = "b" * 64
    # Pure orchestration fault injection: no platform/native/Docker execution.
    monkeypatch.setattr(
        module,
        "sys",
        SimpleNamespace(
            platform="linux",
            flags=SimpleNamespace(isolated=1, optimize=0),
            dont_write_bytecode=True,
        ),
    )
    monkeypatch.setattr(module, "verify_sources", lambda _: 13201)
    monkeypatch.setattr(module, "verify_runtime", lambda *args: "synthetic-prepared-input")
    monkeypatch.setattr(module, "verify_container", lambda *args: identity)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)

    class Owner:
        def __init__(self, docker, output):
            self.root = output
            self.name = None

        def call(self, arguments):
            calls.append(arguments)
            if arguments[:2] == ["container", "create"]:
                self.name = arguments[arguments.index("--name") + 1]
                return identity.encode()
            assert arguments == ["container", "start", identity]
            raise RuntimeError("synthetic lost start response")

        def inspect(self, target):
            inspections.append(target)
            started = any(x[:2] == ["container", "start"] for x in calls)
            state = (
                "exited"
                if started and len(inspections) >= 3
                else ("running" if started else "created")
            )
            return {
                "Id": identity,
                "Name": "/" + self.name,
                "Config": {"Labels": {module._LABEL: self.name}},
                "State": {
                    "Status": state,
                    "Running": state == "running",
                    "Pid": 1 if state == "running" else 0,
                },
            }

    monkeypatch.setattr(module, "DockerOwner", Owner)
    original_save = module.save
    failed = []

    def save_boundary(path, value):
        if (
            boundary == "receipt-before-start"
            and not failed
            and value.get("scenarios")
            and value["scenarios"][-1]["stage"] == "start-intent"
        ):
            failed.append(True)
            raise OSError("synthetic receipt write failed after create")
        original_save(path, value)

    monkeypatch.setattr(module, "save", save_boundary)
    with pytest.raises((RuntimeError, OSError)):
        module.run(
            root,
            source,
            prefix,
            venv,
            Path("/usr/bin/true"),
            tmp_path / "synthetic-manifest",
            "a" * 64,
        )
    assert sum(x[:2] == ["container", "create"] for x in calls) == 1
    assert sum(x[:2] == ["container", "start"] for x in calls) == (
        1 if boundary == "lost-start-response" else 0
    )
    assert len(inspections) == (3 if boundary == "lost-start-response" else 2)
    assert set(inspections) == {identity}
    receipt = json.loads((root / "receipt.json").read_text())
    assert len(receipt["scenarios"]) == 1 and receipt["stage"] == "refused-or-unresolved"
    result = receipt["scenarios"][0]
    assert result["reconciliationActive"] is False
    assert (
        result.get("terminalAfterFailure") is True
        if boundary == "lost-start-response"
        else result.get("retainedInertNeverStarted") is True
    )
