"""Synthetic SDK files only: declaration checks are not effective runtime qualification."""
from pathlib import Path

import pytest

from .native_sdk_ast import MAX_SOURCE_BYTES, public_class_tree


def write(root, module, text):
    path = root.joinpath(*module.split(".")).with_suffix(".py")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode())
    return path


@pytest.mark.parametrize("export", ("from hermes_cli.owner import PluginContext",
                                   "from .owner import PluginContext",
                                   "from .owner import NativeContext as PluginContext"))
def test_explicit_sdk_reexports_resolve_without_executing_source(tmp_path, export):
    name = "NativeContext" if "as PluginContext" in export else "PluginContext"
    sentinel = tmp_path / "must-not-execute"
    write(tmp_path, "hermes_cli.plugins", export + "\n")
    write(tmp_path, "hermes_cli.owner",
          f"open({str(sentinel)!r}, 'w').write('wrong')\nclass {name}:\n    pass\n")
    tree, owner = public_class_tree(tmp_path, "hermes_cli.plugins", "PluginContext")
    assert owner == name and any(getattr(n, "name", None) == name for n in tree.body)
    assert not sentinel.exists()


def test_local_sdk_class_is_found(tmp_path):
    write(tmp_path, "hermes_cli.plugins", "class PluginContext:\n    pass\n")
    assert public_class_tree(tmp_path, "hermes_cli.plugins", "PluginContext")[1] == "PluginContext"


@pytest.mark.parametrize("damage", ("cycle", "ambiguous", "assignment", "namespace", "escape",
                                    "symlink", "oversized"))
def test_unknown_or_unsafe_export_is_refused(tmp_path, damage):
    entry = write(tmp_path, "hermes_cli.plugins", "from .owner import PluginContext\n")
    target = write(tmp_path, "hermes_cli.owner", "class PluginContext:\n    pass\n")
    if damage == "cycle":
        target.write_text("from .plugins import PluginContext\n")
    elif damage == "ambiguous":
        entry.write_text(entry.read_text() + "class PluginContext:\n    pass\n")
    elif damage == "assignment":
        entry.write_text(entry.read_text() + "PluginContext = object()\n")
    elif damage == "namespace":
        entry.write_text("from external.owner import PluginContext\n")
    elif damage == "escape":
        entry.write_text("from ..outside import PluginContext\n")
    elif damage == "symlink":
        target.unlink()
        target.symlink_to(entry)
    else:
        target.write_bytes(b"#" * (MAX_SOURCE_BYTES + 1))
    with pytest.raises(AssertionError):
        public_class_tree(tmp_path, "hermes_cli.plugins", "PluginContext")
