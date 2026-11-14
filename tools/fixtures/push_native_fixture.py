"""T029 copied-plugin wiring only; no gate overrides or production edits."""

from __future__ import annotations

import base64
from pathlib import Path

import _fixture_common as fc
import direct_send_fixture as dsf
import push_native_observer as observer
import yaml

BOOTSTRAP_SUFFIX = (
    "\n# Disposable T029 fixture observer, never shipped in the plugin.\n"
    "from ._push_native_observer import install as _install_push_observer\n"
    "_install_push_observer()\n"
)


def install_fixture(paths: fc.InstancePaths, relay) -> Path:
    """Add explicit synthetic relay settings to this fixture's own host config.

    Caller passes the fixture CA through the child's clean SSL_CERT_FILE environment.
    The real transport keeps normal CA/hostname verification and an additional leaf pin.
    Reapply after any generic fixture config rewrite, before starting the native child.
    """
    out = paths.out_dir.resolve()
    fc.assert_outside_real_home(out, "push fixture output")
    scratch = dsf.scratch_plugin_dir(paths)
    if scratch != out / "_hmp_plugin" or scratch.is_symlink():
        raise fc.FixtureSafetyError("push observer requires the fresh copied plugin")
    root = out / "push-observation"
    if not root.exists():
        root.mkdir(mode=0o700)
    observer.private_root(root)
    source = Path(observer.__file__).read_bytes()
    destination = scratch / "_push_native_observer.py"
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or destination.read_bytes() != source:
            raise fc.FixtureSafetyError("scratch observer differs from reviewed source")
    else:
        with destination.open("xb") as handle:
            destination.chmod(0o600)
            handle.write(source)
    bootstrap = scratch / "__init__.py"
    if bootstrap.is_symlink():
        raise fc.FixtureSafetyError("scratch bootstrap may not be a symlink")
    text = bootstrap.read_text()
    if BOOTSTRAP_SUFFIX not in text:
        bootstrap.write_text(text + BOOTSTRAP_SUFFIX)
    # Only this isolated fixture config is writable. No user-controlled endpoint or native gate.
    config = paths.home / "config.yaml"
    if config.is_symlink() or out not in config.resolve().parents:
        raise fc.FixtureSafetyError("push config must be within the fixture output")
    value = yaml.safe_load(config.read_text())
    value["gateway"]["platforms"]["hmp"]["extra"]["push"] = {
        "enabled": True, "relay_url": relay.url, "relay_audience": "synthetic-relay",
        "relay_kids": ["fixture-kid"],
        "relay_spki_pins": [base64.urlsafe_b64encode(relay.leaf_pin).rstrip(b"=").decode()],
    }
    config.write_text(yaml.safe_dump(value, sort_keys=False))
    config.chmod(0o600)
    return root


def arm(root: Path) -> None:
    if observer.read_file(root, "release") is not None:
        raise ValueError("fixture barrier already released")
    observer.write_file(root, "armed", b"arm\n")


def release(root: Path) -> None:
    observer.write_file(root, "release", b"release\n")
