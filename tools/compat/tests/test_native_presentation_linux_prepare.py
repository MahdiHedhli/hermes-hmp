"""Synthetic software-archive/setup contracts; no downloads or native execution."""

import hashlib
import importlib.util
import io
import tarfile
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "linux_prepare", Path(__file__).parents[1] / "native_presentation_linux_prepare.py"
)
module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(module)


def archive(tmp_path, entries):
    path = tmp_path / "synthetic.tar.gz"
    with tarfile.open(path, "w:gz") as output:
        for name, kind, content in entries:
            item = tarfile.TarInfo(name)
            item.mode = 0o755
            if kind == "file":
                item.size = len(content)
                output.addfile(item, io.BytesIO(content))
            else:
                item.type = {
                    "symlink": tarfile.SYMTYPE,
                    "hardlink": tarfile.LNKTYPE,
                    "fifo": tarfile.FIFOTYPE,
                }[kind]
                item.linkname = content
                output.addfile(item)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_known_archive_hash_and_inside_symlink_are_preserved(tmp_path):
    path, expected = archive(
        tmp_path,
        [
            ("python/bin/python3", "file", b"synthetic-only"),
            ("python/bin/python", "symlink", "python3"),
        ],
    )
    prefix = module.extract_software(path, tmp_path / "out", "python", expected)
    assert (prefix / "bin/python").is_symlink()
    assert (prefix / "bin/python").resolve() == prefix / "bin/python3"
    assert (prefix / "bin/python3").read_bytes() == b"synthetic-only"
    assert (prefix / "bin/python3").stat().st_mode & 0o111 == 0o111
    assert (prefix / "bin/python3").stat().st_mode & 0o7022 == 0


@pytest.mark.parametrize(
    "name,kind,content",
    [
        ("../outside", "file", b"synthetic"),
        ("/outside", "file", b"synthetic"),
        ("other/file", "file", b"synthetic"),
        ("python/fifo", "fifo", ""),
        ("python/hard", "hardlink", "python/base"),
        ("python/escape", "symlink", "../../outside"),
    ],
)
def test_software_archive_scope_failures_refuse(tmp_path, name, kind, content):
    path, expected = archive(tmp_path, [(name, kind, content)])
    with pytest.raises((module.LinuxPreparationError, tarfile.TarError)):
        module.extract_software(path, tmp_path / "out", "python", expected)
    assert not (tmp_path / "outside").exists()


def test_materialized_parent_symlink_cannot_redirect_later_member(tmp_path):
    # The second built-in filter sees links created by earlier members.
    path, expected = archive(
        tmp_path,
        [
            ("python/link", "symlink", "../../outside"),
            ("python/link/payload", "file", b"synthetic"),
        ],
    )
    with pytest.raises((module.LinuxPreparationError, tarfile.TarError)):
        module.extract_software(path, tmp_path / "out", "python", expected)
    assert not (tmp_path / "outside").exists()


def test_wrong_digest_refuses_before_destination_creation(tmp_path):
    path, _ = archive(tmp_path, [("python/bin/python", "file", b"synthetic")])
    with pytest.raises(module.LinuxPreparationError):
        module.extract_software(path, tmp_path / "out", "python", "a" * 64)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/file",
        "https://github.com.evil.invalid/file",
        "https://user:secret@github.com/file",
        "https://github.com:444/file",
        "file:///synthetic",
        "https://evil.invalid/file",
    ],
)
def test_release_redirect_boundaries_refuse(url):
    with pytest.raises(module.LinuxPreparationError):
        module.release_url(url)


def test_exact_requirements_are_77_closed_pins():
    path = Path(__file__).parents[1] / "native_presentation_linux.requirements.txt"
    assert module.digest(path) == module._REQ_SHA
    packages = module.expected_packages(path.read_text())
    assert len(packages) == 77 and packages["pillow"] == "13.0.0"
    assert packages["cryptography"] == "50.0.2"


def test_duplicate_or_unpinned_requirement_set_refuses():
    with pytest.raises(module.LinuxPreparationError):
        module.expected_packages("a==1\na==2\n")


def test_prepare_refuses_ordinary_test_process_before_root_effects(tmp_path):
    root = tmp_path / "never-created"
    with pytest.raises(module.LinuxPreparationError):
        module.prepare(root, root, root)
    assert not root.exists()


@pytest.mark.parametrize("wait_timeout", [12, 600])
def test_generic_helper_records_explicit_setup_wait_without_native_deadline_change(
    tmp_path, wait_timeout
):
    import subprocess

    controller = module.module("prepare_test_controller", "native_presentation_linux_controller.py")
    owner = controller.DockerOwner(Path("/usr/bin/true"), tmp_path)
    waits = []

    class ObservedWait(subprocess.Popen):
        def wait(self, timeout=None):
            waits.append(timeout)
            return super().wait(timeout=timeout)

    owner.commands._POPEN = ObservedWait
    result = owner.commands._owned(
        ["/usr/bin/true"], owner.cli, "synthetic", owner.receipt, wait_timeout=wait_timeout
    )
    assert result == b"" and waits == [wait_timeout]
    assert owner.receipt["commands"][0]["wait_timeout_seconds"] == wait_timeout
    assert owner.receipt["commands"][0]["wait_known"] is True
    assert owner.commands._RETAINED == []


@pytest.mark.parametrize("value", [11, 601, True, "600"])
def test_bad_setup_wait_refuses_before_child_or_receipt(tmp_path, value):
    controller = module.module(
        "prepare_bad_wait_controller", "native_presentation_linux_controller.py"
    )
    owner = controller.DockerOwner(Path("/usr/bin/true"), tmp_path)
    with pytest.raises(owner.commands.NativeSenderFixtureError):
        owner.commands._owned(
            ["/usr/bin/true"], owner.cli, "synthetic", owner.receipt, wait_timeout=value
        )
    assert owner.receipt["commands"] == [] and not any(owner.cli.iterdir())


def test_measured_python_library_exception_is_exact_and_hash_bound():
    name = "python/lib/libpython3.14.so.1.0"
    pin = module._PINS["python"]["sha256"]
    assert module.member_size_allowed(name, 136993528, pin) is True
    assert module.member_size_allowed(name, 136993528, "a" * 64) is False
    assert module.member_size_allowed("python/other.so", 136993528, pin) is False
    assert module.member_size_allowed(name, 136993529, pin) is False
    assert module.member_size_allowed(name, 136993527, pin) is False
    assert module.member_size_allowed("uv/file", 128 * 1024**2 + 1, pin) is False
    assert module.member_size_allowed("uv/file", 128 * 1024**2, pin) is True
    assert module.member_size_allowed("uv/file", -1, pin) is False
    assert module.member_size_allowed("uv/file", True, pin) is False


def test_actual_filesystem_case_behavior_is_checked_and_own_probe_is_cleaned(tmp_path):
    lower = tmp_path / "case-observer"
    lower.write_bytes(b"observer")
    insensitive = (tmp_path / "CASE-OBSERVER").exists()
    root = tmp_path / "fresh"
    root.mkdir(mode=0o700)
    if insensitive:
        with pytest.raises(module.LinuxPreparationError):
            module.require_case_sensitive(root)
    else:
        assert module.require_case_sensitive(root) is True
    assert list(root.iterdir()) == []


def test_wheel_sync_retains_hash_binary_copy_contract_without_conflicting_flag():
    args = module.wheel_sync_arguments(
        Path("/synthetic/uv"), Path("/synthetic/python"), Path("/synthetic/requirements")
    )
    assert args[args.index("--only-binary") + 1] == ":all:"
    assert "--require-hashes" in args and "--no-build" not in args
    assert args[args.index("--link-mode") + 1] == "copy"
    assert "--no-config" in args and "--no-python-downloads" in args
