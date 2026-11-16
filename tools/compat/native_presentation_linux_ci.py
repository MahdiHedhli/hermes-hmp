"""One owned disposable Linux CI preparation and full synthetic native journey.

Only fixed public inputs and fresh private roots. No raw diagnostics in CI output
or uploaded artifacts, no live home, credentials, deployment or release action.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path


def run(workspace, temporary):
    if (
        sys.platform != "linux"
        or os.uname().machine != "x86_64"
        or not sys.flags.isolated
        or not sys.dont_write_bytecode
        or sys.flags.optimize
        or os.geteuid() <= 0
    ):
        raise SystemExit("native_linux_ci_flags_or_platform_refused")
    os.umask(0o077)
    temporary = temporary.resolve(strict=True)
    root = Path(tempfile.mkdtemp(prefix="hmp-native-linux-", dir=temporary))
    status_output = os.environ.get("GITHUB_OUTPUT")
    if status_output:
        with open(status_output, "a", encoding="utf-8") as output:
            output.write("evidence_root=" + str(root) + "\n")
    stage = "load-preparer"
    try:
        script = Path(__file__).with_name("native_presentation_linux_prepare.py")
        spec = importlib.util.spec_from_file_location("_native_ci_preparer", script)
        prepare = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = prepare
        spec.loader.exec_module(prepare)
        stage = "prepare-pinned-software"
        inputs = prepare.prepare(
            root,
            (workspace / "native-reference").resolve(strict=True),
            (workspace / "hmp").resolve(strict=True),
        )
        print(
            json.dumps({"stage": "software-prepared", "nativeJourneyQualified": False}), flush=True
        )
        controller = prepare.module(
            "_native_ci_controller", "native_presentation_linux_controller.py"
        )
        commands = prepare.module("_native_ci_commands", "native_sender_audit_fixture.py")
        docker = Path(shutil.which("docker") or "/missing-docker").resolve(strict=True)
        command_root = root / "image-commands"
        command_root.mkdir(mode=0o700)
        config = root / "image-docker-config"
        config.mkdir(mode=0o700)
        receipt = {"commands": []}
        stage = "pull-pinned-test-image"
        commands._owned(
            [
                str(docker),
                "--config",
                str(config),
                "--host",
                "unix:///var/run/docker.sock",
                "image",
                "pull",
                "--platform",
                "linux/amd64",
                controller._IMAGE,
            ],
            command_root,
            "image-pull",
            receipt,
            wait_timeout=300,
        )
        stage = "full-native-matrix-and-mutation"
        result = controller.run(
            Path(inputs["root"]),
            Path(inputs["source"]),
            Path(inputs["prefix"]),
            Path(inputs["venv"]),
            docker,
            Path(inputs["runtimeManifest"]),
            inputs["runtimeSHA256"],
        )
        summary = {
            "stage": result["stage"],
            "fullJourneyPassed": result["fullJourneyPassed"],
            "scenarios": [
                {
                    "scenario": x["scenario"],
                    "accepted": x.get("accepted", False),
                    "reportSHA256": x.get("reportSHA256"),
                }
                for x in result["scenarios"]
            ],
            "physicalQualified": False,
            "releaseQualified": False,
            "macOSScannerQualified": False,
        }
        controller.save(root / "curated-summary.json", summary)
        print(json.dumps(summary), flush=True)
        return 0
    except BaseException as exc:
        # Never print error strings/traceback/raw reports; they may include fixture state.
        diagnostic_failed = False
        try:
            path = root / "private-failure.json"
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "w") as output:
                json.dump(
                    {
                        "stage": stage,
                        "errorType": type(exc).__name__,
                        "traceback": traceback.format_exc(),
                        "fixtureContext": getattr(exc, "fixture_context", None),
                        "retryAllowed": False,
                    },
                    output,
                )
        except BaseException:
            diagnostic_failed = True
        try:
            print(
                json.dumps(
                    {
                        "stage": stage,
                        "errorType": type(exc).__name__,
                        "fullJourneyPassed": False,
                        "retryAllowed": False,
                        "diagnosticWriteFailed": diagnostic_failed,
                        "physicalQualified": False,
                        "releaseQualified": False,
                    }
                ),
                flush=True,
            )
        except OSError:
            return 1
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--temporary", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.workspace, args.temporary))
