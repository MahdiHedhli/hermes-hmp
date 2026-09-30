"""The disposable mutation copy must never write through a link into the ORIGINAL build.

Only fresh synthetic trees under pytest's tmp_path are used: no Hermes, no gateway, no network and
nothing outside tmp_path. Each hazard is refused BEFORE any write, and a byte-for-byte snapshot of
the original tree (and of every link target outside it) proves nothing moved.
"""
import os
import shutil
import sys
import venv
from pathlib import Path

import _fixture_common as fc
import approval_fixture as af
import pytest

LABEL = "copy-safety"
FILES = ["gateway/a.py", "tools/approval_prompt.py"]


def snapshot(root: Path) -> dict:
    """Every entry under `root` without following links: bytes, link targets, directories."""
    snap: dict = {}
    for current, dirs, files in os.walk(root, followlinks=False):
        for name in (*dirs, *files):
            path = Path(current, name)
            rel = str(path.relative_to(root))
            if path.is_symlink():
                snap[rel] = ("link", os.readlink(path))
            elif path.is_dir():
                snap[rel] = ("dir",)
            else:
                snap[rel] = ("file", path.read_bytes())
    return snap


def make_original(base: Path) -> Path:
    """`<base>/builds/LABEL/src`, a venv whose interpreter links to an EXTERNAL system file, plus a
    `<base>/victim` directory a hazardous link could point at."""
    src = base / "builds" / LABEL / "src"
    (src / "gateway").mkdir(parents=True)
    (src / "gateway" / "a.py").write_text("# a\n")
    (src / "tools").mkdir()
    (src / "tools" / "approval_prompt.py").write_text("# approval prompt\n")
    system = base / "system"
    system.mkdir()
    interpreter = system / "python3.14"
    interpreter.write_bytes(b"#fake interpreter that mentions " + str(src).encode() + b"\n")
    interpreter.chmod(0o755)
    env = src / ".venv"
    (env / "bin").mkdir(parents=True)
    (env / "bin" / "python3").symlink_to(interpreter)
    (env / "bin" / "hermes").write_text(f"#!{src}/.venv/bin/python3\nprint('hermes')\n")
    (env / "pyvenv.cfg").write_text(f"home = {system}\nsource = {src}\n")
    site = env / "lib" / "python3.14" / "site-packages"
    site.mkdir(parents=True)
    (site / "__editable___hermes_finder.py").write_text(f"MAPPING = {{'tools': '{src}/tools'}}\n")
    (site / "hermes.pth").write_text(f"{src}\n")
    victim = base / "victim"
    (victim / "bin").mkdir(parents=True)
    (victim / "lib" / "python3.14" / "site-packages").mkdir(parents=True)
    (victim / "tools").mkdir()
    (victim / "tools" / "approval_prompt.py").write_text("# victim prompt\n")
    (victim / "pyvenv.cfg").write_text(f"source = {src}\n")
    (victim / "bin" / "tool").write_text(f"#!{src}/.venv/bin/python3\n")
    (victim / "lib" / "python3.14" / "site-packages" / "x.pth").write_text(f"{src}\n")
    return src


def _site(src: Path) -> Path:
    return src / ".venv" / "lib" / "python3.14" / "site-packages"


def _relink(link: Path, target: Path | str) -> None:
    """Replace a real file or directory with a symlink to `target` (its content moves first when
    the target is inside the original, so the link is not dangling)."""
    if isinstance(target, Path) and not target.exists():
        shutil.move(str(link), str(target))
    elif link.is_dir() and not link.is_symlink():
        shutil.rmtree(link)
    else:
        link.unlink()
    link.symlink_to(target)


def venv_dir_link(src, base):  # `.venv` -> an absolute path INSIDE the original
    _relink(src / ".venv", src / "realvenv")


def bin_dir_link(src, base):
    _relink(src / ".venv" / "bin", src / "realbin")


def site_packages_link(src, base):
    _relink(_site(src), src / "realsite")


def tools_dir_link(src, base):
    _relink(src / "tools", src / "realtools")


def relative_escape(src, base):  # `.venv` -> a relative path leaving both trees
    shutil.rmtree(src / ".venv")
    (src / ".venv").symlink_to(os.path.relpath(base / "victim", src))


def dangling_directory(src, base):
    _relink(_site(src), "/nonexistent-hmp-copy-safety/site-packages")


def venv_to_victim(src, base):
    shutil.rmtree(src / ".venv")
    (src / ".venv").symlink_to(base / "victim")


def script_link_into_original(src, base):
    real = src / ".venv" / "bin" / "realtool"
    real.write_text("#!/bin/sh\n")
    (src / ".venv" / "bin" / "hermes").unlink()
    (src / ".venv" / "bin" / "hermes").symlink_to(real)


def pyvenv_cfg_link(src, base):
    _relink(src / ".venv" / "pyvenv.cfg", base / "victim" / "pyvenv.cfg")


def pth_link(src, base):
    _relink(_site(src) / "hermes.pth", base / "victim" / "bin" / "tool")


HAZARDS = [
    venv_dir_link, bin_dir_link, site_packages_link, tools_dir_link, relative_escape,
    dangling_directory, venv_to_victim, script_link_into_original, pyvenv_cfg_link, pth_link,
]


@pytest.mark.parametrize("hazard", HAZARDS, ids=lambda fn: fn.__name__)
def test_hazardous_links_are_refused_before_any_write(tmp_path, monkeypatch, hazard):
    base = tmp_path.resolve()
    src = make_original(base)
    hazard(src, base)

    def not_reached(*args, **kwargs):
        raise AssertionError("the copy was used after a link hazard; refusal must come first")

    monkeypatch.setattr(af, "verify_copy_isolation", not_reached)
    before = (snapshot(base / "builds"), snapshot(base / "victim"), snapshot(base / "system"))
    with pytest.raises(fc.FixtureSafetyError):
        af.copy_build_for_mutation(base / "builds", LABEL, base / "copies", files=FILES)
    after = (snapshot(base / "builds"), snapshot(base / "victim"), snapshot(base / "system"))
    assert after == before  # the original and every link target are byte-for-byte unchanged
    assert not (base / "copies" / LABEL / "src").exists()  # the refused copy is removed


def test_external_interpreter_link_is_allowed_and_never_written(tmp_path, monkeypatch):
    base = tmp_path.resolve()
    src = make_original(base)
    monkeypatch.setattr(af, "verify_copy_isolation", lambda build, original_src: None)
    system_before = snapshot(base / "system")
    original_before = snapshot(base / "builds")
    copy = af.copy_build_for_mutation(base / "builds", LABEL, base / "copies", files=FILES)
    new = copy.src_dir
    link = new / ".venv" / "bin" / "python3"
    assert link.is_symlink() and link.resolve() == (base / "system" / "python3.14").resolve()
    assert copy.venv_python.exists()
    assert snapshot(base / "system") == system_before  # the interpreter was only ever read
    assert snapshot(base / "builds") == original_before  # the original is untouched too
    # Everything that may carry the original path was retargeted; the link was not rewritten.
    assert str(src) not in (new / ".venv" / "pyvenv.cfg").read_text()
    assert (new / ".venv" / "bin" / "hermes").read_text().startswith(f"#!{new}/.venv/bin/python3")
    assert (_site(new) / "hermes.pth").read_text().strip() == str(new)


def test_swap_write_paths_must_resolve_inside_the_copy(tmp_path):
    base = tmp_path.resolve()
    make_original(base)
    victim_file = base / "victim" / "tools" / "approval_prompt.py"
    before = snapshot(base / "victim")
    lanes = ([af.SWAP_FILE], ["gateway/a.py"], ["gateway/a.py"])

    linked_tools = base / "swap-dir" / LABEL / "src"
    linked_tools.mkdir(parents=True)
    (linked_tools / "tools").symlink_to(base / "victim" / "tools")  # an ancestor directory link
    with pytest.raises(fc.FixtureSafetyError, match=r"outside|missing"):
        af.mutate_swap_file(fc.BuildInfo(LABEL, linked_tools, linked_tools / "py"), *lanes)

    linked_file = base / "swap-file" / LABEL / "src"
    (linked_file / "tools").mkdir(parents=True)
    (linked_file / af.SWAP_FILE).symlink_to(victim_file)  # the file itself is a link
    with pytest.raises(fc.FixtureSafetyError):
        af.mutate_swap_file(fc.BuildInfo(LABEL, linked_file, linked_file / "py"), *lanes)
    assert snapshot(base / "victim") == before

    # Defense in depth: the low-level writer refuses any path outside the copy as well.
    with pytest.raises(fc.FixtureSafetyError, match="outside the copy"):
        af._retarget_file(victim_file, linked_file, b"victim", b"changed")
    assert snapshot(base / "victim") == before


def test_plain_pth_source_entries_are_retargeted_and_imports_come_from_the_copy(tmp_path):
    """A real venv with an editable-style plain `.pth` (an absolute source directory). Without
    retargeting, the copy imports the ORIGINAL tree; with it, only the copy. Real interpreter,
    real isolation check, no monkeypatching."""
    base = tmp_path.resolve()
    src = base / "builds" / LABEL / "src"
    for rel in ("gateway/pairing.py", "tools/approval.py"):
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text("MARK = 'hermes'\n")
    venv.EnvBuilder(with_pip=False, symlinks=True).create(src / ".venv")
    sites = list((src / ".venv").glob("lib/python*/site-packages"))
    assert len(sites) == 1, sites
    pth = sites[0] / "_hermes_source.pth"
    pth.write_text(f"{src}\n")  # a plain path entry, not an `__editable__*` finder
    assert Path(sys.executable).exists()

    # Negative control: a verbatim copy (links kept, nothing retargeted) imports the original.
    raw = base / "raw" / LABEL / "src"
    shutil.copytree(src, raw, symlinks=True)
    raw_build = fc.resolve_build(base / "raw", LABEL)
    with pytest.raises(fc.FixtureSafetyError, match=r"imports? from itself"):
        af.verify_copy_isolation(raw_build, src)

    original_before = snapshot(base / "builds")
    copy = af.copy_build_for_mutation(base / "builds", LABEL, base / "copies")
    new = copy.src_dir
    copied_pth = next(new.glob(".venv/lib/python*/site-packages/_hermes_source.pth"))
    assert copied_pth.read_text().strip() == str(new)
    assert snapshot(base / "builds") == original_before
