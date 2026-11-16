"""Owned Linux-only Docker runtime for the complete synthetic native journey.

Setup/downloads are separate. Caller exclusively owns these prepared public inputs,
interpreter/environment and fresh private output root throughout. No live homes,
credentials, daemon socket mounts, auto-retry, stop/kill, or container deletion.
The trusted local Docker daemon enforces OS isolation; the Python audit is additive.
A timeout records failure and continues observing the SAME actor until terminal.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import sys
import time
import uuid
from pathlib import Path

_IMAGE = (
    "docker.io/library/ubuntu@sha256:"
    "77eb101c607d6e3d4f5ad0c8a02c2136c689b98aba1f359e6502ba517e5c57ec"
)
_ENTRY_SHA = "6c2640470c3489f7e2cea7ae8c699e8e7204a80de74247e2f006952d04b12698"
_FD_SHA = "692ae20b7bf86016dc7d7f27a678798cf3eb54dad1d601a4376e77b058554056"
_MANIFEST_SHA = "28f13dcb4a90fce810bc0cf8aecb35b33584f5095e5e427a1887637135bcc702"
_LABEL = "app.hermesbot.native-presentation-fixture"


class LinuxJourneyError(RuntimeError):
    """Fixed refusal; raw private fixture diagnostics are never copied here."""


def require(value):
    if value is not True:
        raise LinuxJourneyError("native_linux_controller_refused")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(path, *, directory):
    require(type(path) is type(Path()) and path.is_absolute())
    require(path.resolve(strict=True) == path)
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
    require(info.st_uid == os.geteuid() and not info.st_mode & 0o022)
    require(not any(c in str(path) for c in (",", "\n", "\r", "\x00")))
    return path


def save(path, value):
    # Exclusively owned root, same-directory replacement; private from first write.
    temporary = path.with_name(path.name + ".pending")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    os.replace(temporary, path)


def verify_sources(source):
    canonical(source, directory=True)
    require(digest(source / "source-manifest.json") == _MANIFEST_SHA)
    document = json.loads((source / "source-manifest.json").read_text())
    count = 0
    for label, commit, size in (
        ("native", "ed1afb082eb3e46cf2edae9d8f68fb67b09ee4df", 12185),
        ("hmp", "a4a157a5d04a20f23dddc6d614d462b758a947f4", 1021),
    ):
        item = document["sources"][label]
        require(item["commit"] == commit and len(item["files"]) == size)
        base = canonical(source / label, directory=True)
        actual = set()
        for path in base.rglob("*"):
            require(not path.is_symlink())
            if path.is_dir():
                continue
            canonical(path, directory=False)
            name = path.relative_to(base).as_posix()
            require(name in item["files"] and digest(path) == item["files"][name])
            actual.add(name)
        require(actual == set(item["files"]))
        count += size
    return count


def runtime_inventory(prefix, venv):
    """Measure trusted prepared wheels/interpreter; does not authenticate a preparer.

    Setup must independently establish downloads/version/lock. Complete inventories
    prevent later mutation under caller custody; mounted trees are read-only.
    """
    files = {}
    for label, base in (("prefix", prefix), ("venv", venv)):
        canonical(base, directory=True)
        files[label + "/"] = {"directory": True, "mode": stat.S_IMODE(base.lstat().st_mode)}
        for path in sorted(base.rglob("*")):
            info = path.lstat()
            require(info.st_uid == os.geteuid())
            if not stat.S_ISLNK(info.st_mode):
                require(not info.st_mode & 0o022)
            # Linux symlink0777 is not an access grant; target stays within owned
            # inventoried trees. Real files/directories still reject group/other writes.
            name = label + "/" + path.relative_to(base).as_posix()
            if stat.S_ISLNK(info.st_mode):
                target = path.resolve(strict=True)
                require(target.is_relative_to(prefix) or target.is_relative_to(venv))
                files[name] = {"link": os.readlink(path)}
            elif stat.S_ISDIR(info.st_mode):
                files[name] = {"directory": True, "mode": stat.S_IMODE(info.st_mode)}
            else:
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1)
                files[name] = {
                    "sha256": digest(path),
                    "bytes": info.st_size,
                    "mode": stat.S_IMODE(info.st_mode),
                }
    require(0 < len(files) <= 100000)
    return files


def verify_runtime(prefix, venv, manifest, expected):
    canonical(manifest, directory=False)
    require(re.fullmatch(r"[0-9a-f]{64}", expected) is not None and digest(manifest) == expected)
    require(manifest.stat().st_size <= 32 * 1024**2)
    item = json.loads(manifest.read_text())
    require(item["schema"] == 2 and item["pythonVersion"] == [3, 14, 9])
    require(
        item["requirementsSHA256"]
        == "9edcfc564b10ad1ffca7a3d7a02d1a855a5d203cb807d566b85ce5598eb9df94"
    )
    require(item["prefix"] == str(prefix) and item["venv"] == str(venv))
    require(item["files"] == runtime_inventory(prefix, venv))
    return expected


def environment(root):
    return {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "HOME": str(root / "user-home"),
        "USER": "synthetic-fixture",
        "LOGNAME": "synthetic-fixture",
        "HERMES_HOME": str(root / "home"),
        "HERMES_RUNTIME_DIR": str(root / "runtime"),
        "TMPDIR": str(root / "tmp"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "HERMES_DISABLE_LAZY_INSTALLS": "1",
    }


def create_arguments(name, root, source, prefix, venv, entry, mode, uid, gid):
    require(mode in ("matrix", "mutation", "historic") and type(uid) is int and uid > 0)
    require(
        type(gid) is int and gid >= 0 and re.fullmatch(r"hmp-native-[0-9a-f]{32}", name) is not None
    )
    mounts = [
        (source / "native", True),
        (source / "hmp", True),
        (prefix, True),
        (venv, True),
        (entry, True),
        (root, False),
    ]
    arguments = [
        "container",
        "create",
        "--name",
        name,
        "--label",
        _LABEL + "=" + name,
        "--platform",
        "linux/amd64",
        "--pull",
        "never",
        "--network",
        "none",
        "--user",
        f"{uid}:{gid}",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--read-only",
        "--ipc",
        "private",
        "--cgroupns",
        "private",
        "--pids-limit",
        "128",
        "--memory",
        "2g",
        "--memory-swap",
        "2g",
        "--cpus",
        "2",
        "--shm-size",
        "1m",
        "--restart",
        "no",
        "--no-healthcheck",
        "--log-driver",
        "local",
        "--log-opt",
        "max-size=1m",
        "--log-opt",
        "max-file=1",
        "--log-opt",
        "compress=false",
        "--workdir",
        str(root),
        "--entrypoint",
        str(venv / "bin/python"),
    ]
    for path, readonly in mounts:
        arguments += [
            "--mount",
            f"type=bind,src={path},dst={path}" + (",readonly" if readonly else ""),
        ]
    for key, value in sorted(environment(root).items()):
        arguments += ["--env", key + "=" + value]
    arguments += [_IMAGE, "-I", "-B", str(entry), str(root), str(source), "18443", mode]
    return arguments, mounts


def verify_container(item, name, root, venv, entry, mode, uid, gid, mounts):
    require(item["Name"] == "/" + name and re.fullmatch(r"[0-9a-f]{64}", item["Id"]) is not None)
    config, host = item["Config"], item["HostConfig"]
    require(config["Labels"].get(_LABEL) == name and config["Image"] == _IMAGE)
    require(config["User"] == f"{uid}:{gid}" and config["WorkingDir"] == str(root))
    require(config["Entrypoint"] == [str(venv / "bin/python")])
    require(
        config["Cmd"]
        == ["-I", "-B", str(entry), str(root), str(mounts[0][0].parent), "18443", mode]
    )
    require(set(config["Env"]) == {k + "=" + v for k, v in environment(root).items()})
    require(len(config["Env"]) == len(environment(root)))
    require(not config.get("OpenStdin") and not config.get("Tty"))
    require(host["NetworkMode"] == "none" and host["ReadonlyRootfs"] is True)
    require(host["Privileged"] is False and host["CapDrop"] == ["ALL"] and not host.get("CapAdd"))
    require(host["SecurityOpt"] == ["no-new-privileges:true"])
    require(host["IpcMode"] == "private" and host["CgroupnsMode"] == "private")
    require(host["PidMode"] == "" and host["UTSMode"] == "" and not host.get("UsernsMode"))
    require(
        not host.get("Devices") and not host.get("DeviceRequests") and not host.get("VolumesFrom")
    )
    require(
        not host.get("PortBindings") and not host.get("PublishAllPorts") and not host.get("Links")
    )
    require(host["RestartPolicy"]["Name"] == "no" and not host.get("AutoRemove"))
    require(
        host["LogConfig"]
        == {"Type": "local", "Config": {"max-size": "1m", "max-file": "1", "compress": "false"}}
    )
    require(host["PidsLimit"] == 128 and host["Memory"] == 2 * 1024**3)
    require(host["MemorySwap"] == 2 * 1024**3 and host["NanoCpus"] == 2_000_000_000)
    require(host["ShmSize"] == 1024**2 and not host.get("Binds") and not host.get("Tmpfs"))
    observed = {(x["Source"], x["Destination"], x["RW"], x["Type"]) for x in item["Mounts"]}
    expected = {(str(p), str(p), not ro, "bind") for p, ro in mounts}
    require(observed == expected and len(item["Mounts"]) == len(expected))
    require(set(item["NetworkSettings"]["Networks"]) <= {"none"})
    return item["Id"]


def report_acceptance(report, mode):
    require(report["phase"] == "complete" and report["scenario"] == mode)
    keys = [
        "nativePresentationServiceBound",
        "nativePresentationMetadataObserved",
        "nativePresentationForeignRevisionRefused",
        "nativePresentationAvatarRevisionChangeRefusedThenReadBack",
        "nativePresentationCharacterNameParityObserved",
        "earlyNativePresentationRevocationAndRestorationObserved",
        "presentationDrained",
        "dependenciesClosedByAdapter",
        "nativeMediaRegrantOldRefRefusedNewRefWorks",
        "nativeStoredForeignInstanceTokenRefused",
        "nativeRunnerResourcesReleased",
        "nativeLoaderWorkersSettled",
        "storeClosed",
        "unloadResult",
        "registrationsCleared",
        "nativeBotRevocationIsProfileScoped"
        if mode == "matrix"
        else "nativeChangedFileRefusedOtherProfileUnaffected",
    ]
    if mode == "matrix":
        keys.append("nativePresentationAvatarBotRevocationIsProfileScoped")
    require(all(report.get(key) is True for key in keys))
    require(report["presentationWorkerDebt"] is False and report["lifecycleCleanupErrors"] == [])
    require(report.get("cleanupErrors", []) == [] and report["observedNetworkInterfaces"] == ["lo"])
    require(report["nativeReapprovalCooldownElapsedSeconds"] >= 602)
    if mode == "historic":
        require(report.get("nativeHistoricCacheTLSAndRegrantObserved") is True)
        require(report.get("historicCanonicalToolRowsAreSynthetic") is True)
        require(report.get("historicProviderGenerationQualified") is False)
        require(report.get("historicCacheHelper") == "gateway.platforms.base.cache_image_from_bytes")
        historic = report.get("nativeHistoricCacheProfiles")
        require(type(historic) is list and len(historic) == 2)
        require({x.get("profileHomeName") for x in historic} == {"home", "beta"})
        require(all(x.get("exactHistoricRoot") is True and x.get("bytesMatched") is True for x in historic))
    require(
        [(x["profile"], x["status"]) for x in report["nativePresentationCases"]]
        == [("default", 200), ("beta", 200)]
    )
    require(len(report["nativePresentationAvatarCases"]) == 4)
    require(
        all(
            x["status"] == 200 and x["peerPinnedBeforeRequest"] is True
            for x in report["nativePresentationAvatarCases"]
        )
    )
    require(len(report["earlyNativePresentationRevocationCases"]) == 4)
    require(
        len(report["nativeIsolationPositiveCells"]) == 4
        and len(report["nativeIsolationCases"]) == 12
    )


class DockerOwner:
    """Reuse the reviewed pre-owned CLI helper; never execute its native C fixture."""

    def __init__(self, docker, root):
        self.docker, self.root = docker, root
        self.config = root / "docker-config"
        self.config.mkdir(mode=0o700)
        self.cli = root / "docker-cli"
        self.cli.mkdir(mode=0o700)
        self.receipt = {"commands": []}
        path = Path(__file__).with_name("native_sender_audit_fixture.py")
        require(digest(path) == "e6ce104449c277bdd3a9dafe83a609dd9a8bc45f22e618b863022059704253a1")
        spec = importlib.util.spec_from_file_location("_native_linux_owned_cli", path)
        self.commands = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.commands)

    def call(self, arguments):
        role = "docker-" + str(len(self.receipt["commands"]))
        return self.commands._owned(
            [
                str(self.docker),
                "--config",
                str(self.config),
                "--host",
                "unix:///var/run/docker.sock",
                *arguments,
            ],
            self.cli,
            role,
            self.receipt,
            stdout_limit=4 * 1024**2,
        )

    def inspect(self, identity):
        document = json.loads(self.call(["container", "inspect", identity]))
        require(type(document) is list and len(document) == 1)
        return document[0]


def public_progress(receipt, payload):
    """Best-effort fixed metadata; console failure never releases an actor."""
    try:
        print(json.dumps(payload), flush=True)
    except BaseException:
        receipt["publicOutputFailed"] = True


def checkpoint(root, receipt):
    """Diagnostics must not release an actor when storage is temporarily unavailable."""
    try:
        save(root / "receipt.json", receipt)
    except OSError:
        receipt["diagnosticWriteFailed"] = True


def reconcile(owner, name, identity, row, receipt):
    """After failure observe the SAME intent/actor, never create/start/kill/remove.

    An absent or inaccessible object after an ambiguous create/start is unknown,
    not proof of no effect. Stay pending until that original actor is observed.
    An owned created object is inert only if no start was ever attempted.
    """
    row["reconciliationActive"] = True
    checkpoint(owner.root, receipt)
    while True:
        try:
            item = owner.inspect(identity or name)
            require(item["Name"] == "/" + name and item["Config"]["Labels"].get(_LABEL) == name)
            require(re.fullmatch(r"[0-9a-f]{64}", item["Id"]) is not None)
            require(identity is None or item["Id"] == identity)
            identity = item["Id"]
            row["containerId"] = identity
            state = item["State"]
            row.update(reconciliationState=state["Status"], reconciliationPID=state["Pid"])
            if (
                state["Status"] in ("exited", "dead")
                and state["Running"] is False
                and state["Pid"] == 0
            ):
                row.update(reconciliationActive=False, terminalAfterFailure=True)
                checkpoint(owner.root, receipt)
                return
            if state["Status"] == "created" and not row.get("startAttempted", False):
                row.update(reconciliationActive=False, retainedInertNeverStarted=True)
                checkpoint(owner.root, receipt)
                return
        except BaseException as exc:
            # Read-only observation can repeat; mutating commands never replay.
            row["reconciliationObservationErrorType"] = type(exc).__name__
        checkpoint(owner.root, receipt)
        time.sleep(2)


def run(root, source, prefix, venv, docker, runtime_manifest, runtime_sha256):
    require(
        sys.platform == "linux"
        and sys.flags.isolated == 1
        and sys.dont_write_bytecode
        and sys.flags.optimize == 0
    )
    require(os.geteuid() > 0)
    os.umask(0o077)
    for path in (root, source, prefix, venv):
        canonical(path, directory=True)
    require(stat.S_IMODE(root.stat().st_mode) == 0o700 and not any(root.iterdir()))
    require(len({str(p) for p in (root, source, prefix, venv)}) == 4)
    for first in (root, source, prefix, venv):
        for second in (root, source, prefix, venv):
            require(first == second or not first.is_relative_to(second))
    require(docker.is_absolute() and docker.resolve(strict=True).is_file())
    entry = canonical(
        Path(__file__).with_name("native_presentation_journey_entry.py"), directory=False
    )
    helper = canonical(Path(__file__).parents[1] / "fixtures/native_fd_scope.py", directory=False)
    require(digest(entry) == _ENTRY_SHA and digest(helper) == _FD_SHA)
    require((venv / "bin/python").resolve(strict=True).is_relative_to(prefix))
    verify_runtime(prefix, venv, runtime_manifest, runtime_sha256)
    count = verify_sources(source)
    owner = DockerOwner(docker, root)
    receipt = {
        "stage": "prepared",
        "sourceFiles": count,
        "scenarios": [],
        "fullJourneyPassed": False,
        "physicalQualified": False,
        "releaseQualified": False,
        "macOSScannerQualified": False,
    }
    save(root / "receipt.json", receipt)
    row = None
    container = None
    try:
        for mode in ("matrix", "mutation", "historic"):
            container = None
            fixture = root / mode
            fixture.mkdir(mode=0o700)
            (fixture / "tmp").mkdir(mode=0o700)
            shutil.copyfile(helper, fixture / "_fixture_fd_scope.py")
            (fixture / "_fixture_fd_scope.py").chmod(0o600)
            name = "hmp-native-" + uuid.uuid4().hex
            arguments, mounts = create_arguments(
                name, fixture, source, prefix, venv, entry, mode, os.geteuid(), os.getegid()
            )
            row = {"scenario": mode, "name": name, "stage": "create-intent", "retryAllowed": False}
            receipt["scenarios"].append(row)
            save(root / "receipt.json", receipt)
            # This mutates the local test daemon once. Never replay after uncertain output.
            row["createAttempted"] = True
            container = owner.call(arguments).decode("ascii").strip()
            require(re.fullmatch(r"[0-9a-f]{64}", container) is not None)
            item = owner.inspect(container)
            require(item["State"]["Status"] == "created")
            require(
                verify_container(
                    item, name, fixture, venv, entry, mode, os.geteuid(), os.getegid(), mounts
                )
                == container
            )
            row.update(containerId=container, stage="start-intent")
            save(root / "receipt.json", receipt)
            row["startAttempted"] = True
            require(
                owner.call(["container", "start", container]).decode("ascii").strip() == container
            )
            started = time.monotonic()
            overdue = False
            public_state = None
            while True:
                item = owner.inspect(container)
                require(
                    verify_container(
                        item, name, fixture, venv, entry, mode, os.geteuid(), os.getegid(), mounts
                    )
                    == container
                )
                state = item["State"]
                if state["Status"] in ("running", "exited") and state["Status"] != public_state:
                    public_state = state["Status"]
                    public_progress(
                        receipt,
                        {"stage": "native-container", "scenario": mode, "state": public_state},
                    )
                row.update(
                    stage="observing-same-container", state=state["Status"], pid=state["Pid"]
                )
                if time.monotonic() - started > 900:
                    overdue = True
                    row["deadlineExceeded"] = True
                save(root / "receipt.json", receipt)
                if state["Status"] == "exited" and state["Running"] is False and state["Pid"] == 0:
                    break
                require(state["Status"] == "running" and state["Running"] is True)
                time.sleep(2)
            row.update(stage="terminal", exitCode=state["ExitCode"], oomKilled=state["OOMKilled"])
            save(root / "receipt.json", receipt)
            owner.call(["container", "logs", container])  # Private bounded synthetic logs only.
            require(
                not overdue
                and state["ExitCode"] == 0
                and state["OOMKilled"] is False
                and not state["Error"]
            )
            require(verify_sources(source) == count)
            verify_runtime(prefix, venv, runtime_manifest, runtime_sha256)
            report = json.loads((fixture / "report.json").read_text())
            report_acceptance(report, mode)
            row.update(accepted=True, reportSHA256=digest(fixture / "report.json"))
            save(root / "receipt.json", receipt)
    except BaseException as exc:
        public_progress(receipt, {"stage": "native-refused-or-unresolved", "retryAllowed": False})
        receipt.update(
            stage="refused-or-unresolved",
            failureType=type(exc).__name__,
            retryAllowed=False,
            actorReleaseClaimed=False,
        )
        checkpoint(root, receipt)
        if row is not None and row.get("createAttempted", False) and row.get("stage") != "terminal":
            # If create output was malformed, retain its pre-owned unique name.
            known = (
                container
                if type(container) is str and re.fullmatch(r"[0-9a-f]{64}", container)
                else None
            )
            reconcile(owner, row["name"], known, row, receipt)
        raise
    receipt.update(stage="complete", fullJourneyPassed=True)
    save(root / "receipt.json", receipt)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("root", "source", "prefix", "venv", "docker"):
        parser.add_argument("--" + argument, type=Path, required=True)
    parser.add_argument("--runtime-manifest", type=Path, required=True)
    parser.add_argument("--runtime-sha256", required=True)
    args = parser.parse_args()
    result = run(
        args.root,
        args.source,
        args.prefix,
        args.venv,
        args.docker,
        args.runtime_manifest,
        args.runtime_sha256,
    )
    print(
        json.dumps(
            {
                "stage": result["stage"],
                "fullJourneyPassed": result["fullJourneyPassed"],
                "physicalQualified": False,
                "releaseQualified": False,
            }
        )
    )
