"""Launch-policy and real isolated interpreter checks; no worker/profile access."""

import json
import os
import subprocess
import sys

import pytest

from hmp_plugin.presentation_child_launch import child_launch, worker_environment


def test_launch_is_fixed_isolated_and_closes_unrelated_descriptors(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-not-inherited")
    monkeypatch.setenv("HMP_ACCESS_TOKEN", "synthetic-not-inherited")
    launch = child_launch()
    assert launch.argv[0] == sys.executable
    assert launch.argv[1:3] == ("-I", "-B")
    assert launch.argv[-1].endswith("/presentation_child.py")
    assert dict(launch.environment) == {"LANG": "C", "LC_ALL": "C"}
    assert launch.close_fds and launch.pass_fds == () and launch.start_new_session
    with pytest.raises(TypeError):
        launch.environment["EXTRA"] = "value"


def test_real_child_does_not_receive_synthetic_provider_or_bearer(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-not-inherited")
    monkeypatch.setenv("HMP_ACCESS_TOKEN", "synthetic-not-inherited")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            "import os,json,sys;print(json.dumps([sys.flags.isolated,sys.dont_write_bytecode,"
            'os.getenv("OPENAI_API_KEY"),os.getenv("HMP_ACCESS_TOKEN")]))',
        ],
        env=worker_environment(),
        close_fds=True,
        pass_fds=(),
        start_new_session=True,
        capture_output=True,
        check=True,
        timeout=5,
    )
    assert json.loads(result.stdout) == [1, True, None, None]


def test_real_child_does_not_inherit_parent_owned_pipe():
    read, write = os.pipe()
    os.set_inheritable(read, True)
    original = os.fstat(read)
    program = (
        "import os,json,sys\n"
        "try:\n r=os.fstat(int(sys.argv[1]))\n"
        " same=[r.st_dev,r.st_ino]==[int(sys.argv[2]),int(sys.argv[3])]\n"
        "except OSError:\n same=False\n"
        "print(json.dumps([same,os.getsid(0)==os.getpid()]))"
    )
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                "-c",
                program,
                str(read),
                str(original.st_dev),
                str(original.st_ino),
            ],
            env=worker_environment(),
            close_fds=True,
            pass_fds=(),
            start_new_session=True,
            capture_output=True,
            check=True,
            timeout=5,
        )
        assert json.loads(result.stdout) == [False, True]
    finally:
        os.close(write)
        os.close(read)
