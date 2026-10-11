"""Real native bridge check in an isolated child; no HTTP/auth certification."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

CHILD = r"""
import json, sys
from pathlib import Path
from types import SimpleNamespace
source_path=Path(sys.argv[1]).resolve()
tmp_path=Path(sys.argv[2])
home=tmp_path/'home'
import hermes_state
assert Path(hermes_state.__file__).resolve() == source_path/'hermes_state.py'
def check():
    import hermes_state_registry, hermes_constants
    for module in (hermes_state, hermes_state_registry, hermes_constants):
        assert Path(module.__file__).resolve().is_relative_to(source_path)
    from hermes_state import SessionDB
    from hmp_plugin.bridge import HermesReadBridge, StoreDirectory
    from hmp_plugin.contract import ConversationRef
    from hmp_plugin.store import Store

    image = home / "cache" / "images" / "synthetic.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"synthetic selector only; not a raster test")
    db = SessionDB(home / "state.db")
    try:
        db.create_session("synthetic-media", "cli")
        db.set_session_title("synthetic-media", "Bot Chat")
        db.set_session_hidden("synthetic-media", True)
        db.append_message("synthetic-media", "assistant", content="", tool_calls=[{
            "id": "synthetic-call", "type": "function",
            "function": {"name": "image_generate", "arguments": "{}"},
        }])
        tool = db.append_message("synthetic-media", "tool", content=json.dumps({
            "success": True, "image": str(image),
        }), tool_name="image_generate", tool_call_id="synthetic-call")
        db.append_message("synthetic-media", "assistant", content=f"MEDIA:{image}")
        for call_id, payload in (
            ("cross-home-call", {
                "success": True, "image": str(tmp_path / "other/cache/images/image.png"),
            }),
            ("failed-call", {"success": False, "image": str(image)}),
        ):
            db.append_message("synthetic-media", "assistant", content="", tool_calls=[{
                "id": call_id, "type": "function",
                "function": {"name": "image_generate", "arguments": "{}"},
            }])
            db.append_message("synthetic-media", "tool", content=json.dumps(payload),
                              tool_name="image_generate", tool_call_id=call_id)
    finally:
        db.close()
    store = Store(tmp_path / "hmp.db")
    store.migrate()
    try:
        store.insert_user("synthetic-user", "Synthetic", 0)
        runner = SimpleNamespace(_routed_profile_home=lambda profile: home)
        bridge = HermesReadBridge(SimpleNamespace(gateway_runner=runner), StoreDirectory(store))
        result = bridge.latest_with_media(
            ConversationRef("synthetic-user", "default", "synthetic-media"), 10,
        )
        assert [candidate.tool_row_id for candidate in result.candidates] == [tool]
        assert len(result.rows) == 7
        assert result.rows[2].text == f"MEDIA:{image}"
    finally:
        store.close()

check()
"""


def test_native_image_candidate_and_decoy(tmp_path):
    source = os.environ.get("HMP_NATIVE_MEDIA_SOURCE")
    if not source:
        pytest.skip("requires a version-matched native Hermes environment")
    source_path = Path(source).resolve()
    assert (source_path / "hermes_state.py").is_file()
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
           "HOME": os.environ["HOME"], "HERMES_HOME": str(home),
           "HERMES_RUNTIME_DIR": str(runtime), "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONPATH": str(source_path) + os.pathsep + str(Path(__file__).resolve().parents[2])}
    result = subprocess.run([sys.executable, "-B", "-c", CHILD, str(source_path), str(tmp_path)],
                            env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
