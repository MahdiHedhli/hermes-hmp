"""Explicit dependency closure; synthetic fixtures only, no native home or authority."""

import dataclasses
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from hmp_plugin.presentation_child_launch import child_launch, parser_package_path
from hmp_plugin.presentation_jobs import FrameError
from hmp_plugin.presentation_process import PresentationProcessOwner


@pytest.fixture
def parser(tmp_path):
    root = tmp_path.resolve() / "dependencies"
    root.mkdir()
    package = root / "yaml"
    shutil.copytree(Path(yaml.__file__).resolve().parent, package)
    return package


def test_bare_isolated_interpreter_has_no_implicit_yaml():
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-S",
            "-c",
            "import importlib.util;assert importlib.util.find_spec('yaml') is None",
        ],
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0 and result.stderr == b""


def test_explicit_package_does_not_activate_site_or_unrelated_paths(parser):
    marker = parser.parent / "should-not-exist"
    code = f"open({str(marker)!r}, 'w').write('activated')"
    (parser.parent / "evil.pth").write_text("import builtins;" + code)
    (parser.parent / "sitecustomize.py").write_text(code)
    (parser.parent / "unrelated.py").write_text(code)
    # Even the package initializer must not execute in the worker namespace.
    (parser / "__init__.py").write_text(code)
    launch = child_launch(str(parser))
    script = launch.argv[4]
    program = (
        "import runpy,sys,json; original=list(sys.path); "
        "m=runpy.run_path(sys.argv[1]);m['bootstrap']();"
        "m['bind_parser_namespace'](sys.argv[2]);"
        "from yaml.loader import SafeLoader;import yaml.loader;"
        "loader=SafeLoader('value: 1');event=type(loader.get_event()).__name__;loader.dispose();"
        "print(json.dumps([yaml.loader.__file__,event,"
        "sys.path==original,'site' in sys.modules,'unrelated' in sys.modules,"
        "'yaml._yaml' in sys.modules]))"
    )
    result = subprocess.run(
        [launch.argv[0], "-I", "-B", "-S", "-c", program, script, str(parser)],
        env=dict(launch.environment),
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [
        str(parser / "loader.py"),
        "StreamStartEvent",
        True,
        False,
        False,
        False,
    ]
    assert not marker.exists()


@pytest.mark.parametrize(
    "value", [None, True, 1, [], "yaml", "", "/not-a-parser/../yaml", "bad\0path", "\ud800"]
)
def test_malformed_startup_path_is_refused(value):
    with pytest.raises(FrameError):
        parser_package_path(value)


def test_symlink_package_ancestor_and_entry_are_refused(parser, tmp_path):
    alias = tmp_path / "alias"
    alias.symlink_to(parser.parent, target_is_directory=True)
    with pytest.raises(FrameError):
        child_launch(str(alias / "yaml"))
    package_alias = tmp_path / "yaml"
    package_alias.symlink_to(parser, target_is_directory=True)
    with pytest.raises(FrameError):
        child_launch(str(package_alias))
    entry = parser / "__init__.py"
    entry.rename(parser / "real.py")
    entry.symlink_to(parser / "real.py")
    with pytest.raises(FrameError):
        child_launch(str(parser))


@pytest.mark.parametrize("extra", [[], ["extra"], ["--parser-package", "extra"]])
def test_child_refuses_missing_or_extra_arguments_before_parser_import(parser, extra):
    launch = child_launch(str(parser))
    argv = launch.argv[:5] if not extra else (*launch.argv, *extra)
    result = subprocess.run(
        argv, input=b"", env=dict(launch.environment), capture_output=True, timeout=5, check=False
    )
    assert result.returncode == 1 and result.stdout == b""
    assert result.stderr == b"BI1_CHILD_REFUSED\n"


def test_preexisting_parser_namespace_collision_is_refused(parser):
    script = child_launch(str(parser)).argv[4]
    for name in ("yaml", "yaml.events"):
        program = (
            "import sys,types,runpy; m=runpy.run_path(sys.argv[1]);"
            "sys.modules[sys.argv[3]]=types.ModuleType(sys.argv[3]);"
            "m['bind_parser_namespace'](sys.argv[2])"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-S", "-c", program, script, str(parser), name],
            capture_output=True,
            timeout=5,
        )
        assert result.returncode != 0
        assert b"BI1_PARSER_NAMESPACE_REFUSED" in result.stderr


def test_owner_freezes_recipe_without_later_factory_or_environment_selection(parser, monkeypatch):
    owner = PresentationProcessOwner(parser_package=str(parser))
    with pytest.raises(dataclasses.FrozenInstanceError):
        owner._launch.argv = ("other-program",)
    with pytest.raises(TypeError):
        owner._launch.environment["PYTHONPATH"] = str(parser.parent)
    monkeypatch.setenv("PYTHONPATH", str(parser.parent))
    assert owner._launch.argv[-1] == str(parser)
    assert "PYTHONPATH" not in owner._launch.environment


@pytest.mark.parametrize("flags", [("-I", "-B"), ("-B", "-S"), ("-I", "-S")])
def test_required_flags_refuse_before_parser_code_runs(parser, flags):
    marker = parser.parent / "parser-was-imported"
    (parser / "loader.py").write_text(f"open({str(marker)!r}, 'w').write('unexpected')\n")
    launch = child_launch(str(parser))
    result = subprocess.run(
        [launch.argv[0], *flags, *launch.argv[4:]],
        env=dict(launch.environment),
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 1 and result.stdout == b""
    assert result.stderr == b"BI1_CHILD_REFUSED\n"
    assert not marker.exists()
