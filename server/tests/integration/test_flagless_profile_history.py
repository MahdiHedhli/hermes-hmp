"""Specs 005 open item C6: history of a named profile whose own `gateway.multiplex_profiles` flag
is absent or false, under a root that multiplexes, through the real Hermes `SessionStore`,
`SessionDB`, key generation, route matcher and the real `HermesReadBridge`.

Needs an extracted Hermes source with its own interpreter; it skips without it:

    HMP_FLAGLESS_FIXTURE_SOURCE=<hermes source dir containing .venv/bin/python>
    HMP_FLAGLESS_FIXTURE_FINGERPRINT=<expected read-bridge fingerprint>   (optional, checked)
    HMP_FLAGLESS_FIXTURE_REPORT=<path to write a status-only JSON summary>  (optional)

Every child process is fresh: isolated `HERMES_HOME` and `HOME`, no inherited `HERMES_*`/`XDG_*`,
no network (the worker refuses non-local connections and counts attempts), no model turn.
Only synthetic messages and ids are used. The Hermes source is read-only: its read-bridge
fingerprint and a digest of its whole source tree are taken before and after.

Three origins are qualified, each for both own-flag states:

- A: history created by the root multiplexing gateway's shared `SessionStore` for an exact routed
  source (a fresh bot);
- B: history that already existed from a standalone gateway of that profile (no own multiplex),
  then the route helper runs and the root reads it;
- B then A: B exists, then the root gateway starts a conversation for the same chat.

The assertions record what the source does. Nothing here enables a profile flag or rewrites
history to make a read pass.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import routes
from hmp_plugin.compat import compute_read_bridge_fingerprint

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKER = REPO_ROOT / "tools" / "fixtures" / "flagless_history_worker.py"
BRIDGE_FILES = json.loads(
    (REPO_ROOT / "server" / "hmp_plugin" / "read_compat_builds.json").read_text(encoding="utf-8")
)["bridge_files"]

_SOURCE_ENV = os.environ.get("HMP_FLAGLESS_FIXTURE_SOURCE", "")
SOURCE = Path(_SOURCE_ENV) if _SOURCE_ENV else None

pytestmark = pytest.mark.skipif(
    SOURCE is None or not (SOURCE / ".venv" / "bin" / "python").is_file(),
    reason="needs HMP_FLAGLESS_FIXTURE_SOURCE (a Hermes source with .venv/bin/python)",
)

PROFILE = "flagless"
USER = "u-fixture-1"
CHAT = "c-fixture-1"
MESSAGES = 4

FLAG_STATES = {
    "absent": "display:\n  compact: true\n",
    "false": "gateway:\n  multiplex_profiles: false\n",
}
ROOT_CONFIG = "gateway:\n  multiplex_profiles: true\n"

_SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules"}


# --------------------------------------------------------------------------------------------------
# Source binding
# --------------------------------------------------------------------------------------------------


def _tree_digest(root: Path) -> str:
    """SHA-256 over `path \\0 size \\0 bytes` for every file of the source tree, skipping the
    virtualenv and bytecode caches. Read-only."""
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.is_symlink() or not path.is_file():
                continue
            data = path.read_bytes()
            digest.update(str(path.relative_to(root)).encode())
            digest.update(b"\0" + str(len(data)).encode() + b"\0")
            digest.update(data)
    return digest.hexdigest()


def _binding() -> dict[str, str | None]:
    assert SOURCE is not None
    return {
        "read_bridge_fingerprint": compute_read_bridge_fingerprint(SOURCE, BRIDGE_FILES),
        "source_tree_digest": _tree_digest(SOURCE),
    }


@pytest.fixture(scope="module")
def binding() -> Any:
    before = _binding()
    report: dict[str, Any] = {"before": before, "cases": {}}
    yield report
    after = _binding()
    report["after"] = after
    path = os.environ.get("HMP_FLAGLESS_FIXTURE_REPORT")
    if path:
        Path(path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert after == before, "the Hermes source changed while the fixture ran"


def test_source_binding(binding: Any) -> None:
    before = binding["before"]
    assert before["read_bridge_fingerprint"] is not None
    expected = os.environ.get("HMP_FLAGLESS_FIXTURE_FINGERPRINT")
    if expected:
        assert before["read_bridge_fingerprint"] == expected


# --------------------------------------------------------------------------------------------------
# Isolated homes and child processes
# --------------------------------------------------------------------------------------------------


class Home:
    def __init__(self, base: Path, flag_state: str) -> None:
        real_home = Path.home().resolve()
        assert real_home != base.resolve() and real_home not in base.resolve().parents
        self.base = base
        self.root = base / "hermes-root"
        self.profile = self.root / "profiles" / PROFILE
        self.profile.mkdir(parents=True)
        (base / "home").mkdir()
        self.root_config = self.root / "config.yaml"
        self.root_config.write_text(ROOT_CONFIG, encoding="utf-8")
        self.root_config.chmod(0o600)
        self.profile_config = self.profile / "config.yaml"
        self.profile_config.write_text(FLAG_STATES[flag_state], encoding="utf-8")
        self.profile_config.chmod(0o600)
        self.initial_profile_config = self.profile_config.read_bytes()

    def child(self, phase: str) -> dict[str, Any]:
        assert SOURCE is not None
        env = {
            "HOME": str(self.base / "home"),
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(SOURCE),
        }
        proc = subprocess.run(
            [
                str(SOURCE / ".venv" / "bin" / "python"),
                str(WORKER),
                phase,
                "--root-home",
                str(self.root),
                "--profile",
                PROFILE,
                "--user",
                USER,
                "--chat",
                CHAT,
                "--messages",
                str(MESSAGES),
            ],
            cwd=self.base,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert proc.returncode == 0, f"{phase} failed (status only): rc={proc.returncode}"
        out: dict[str, Any] = json.loads(proc.stdout.strip().splitlines()[-1])
        assert out["blocked_network_attempts"] == 0
        assert out["runtime_bootstrap_dir_created"] is False
        return out

    def tree(self, top: Path, skip: tuple[str, ...] = ()) -> dict[str, tuple[Any, ...]]:
        """Every entry under `top`: bytes digest, size, mtime_ns, inode and mode."""
        snap: dict[str, tuple[Any, ...]] = {}
        for path in sorted([top, *top.rglob("*")]):
            rel = str(path.relative_to(top))
            if any(rel == s or rel.startswith(s + os.sep) for s in skip):
                continue
            st = path.lstat()
            body = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            snap[rel] = (body, st.st_size, st.st_mtime_ns, st.st_ino, st.st_mode)
        return snap

    def run_route_helper(self) -> dict[str, Any]:
        """The real route helper. Returns the before/after comparison of both trees."""
        profile_before = self.tree(self.profile)
        root_before = self.tree(self.root, skip=("profiles",))
        outcome = routes.add_route(self.root, PROFILE)
        profile_after = self.tree(self.profile)
        root_after = self.tree(self.root, skip=("profiles",))
        assert outcome.route_added is True
        changed_root = {k for k in root_after if root_before.get(k) != root_after[k]}
        return {
            "profile_tree_identical": profile_before == profile_after,
            "profile_entries": len(profile_before),
            "root_changed_entries": sorted(changed_root),
        }


@pytest.fixture(params=sorted(FLAG_STATES))
def flag_state(request: pytest.FixtureRequest) -> str:
    return str(request.param)


@pytest.fixture
def home(tmp_path: Path, flag_state: str) -> Home:
    return Home(tmp_path, flag_state)


def _record(binding: Any, name: str, flag_state: str, **values: Any) -> None:
    binding["cases"].setdefault(name, {})[flag_state] = values


# --------------------------------------------------------------------------------------------------
# Origin A: the root multiplexing gateway's own shared store, exact routed source
# --------------------------------------------------------------------------------------------------


def test_origin_a_routed_shared_store_is_readable(
    home: Home, flag_state: str, binding: Any
) -> None:
    helper = home.run_route_helper()
    assert helper["profile_tree_identical"] is True
    assert helper["root_changed_entries"] == [".", "config.yaml", "config.yaml.hmp-bak"]

    seeded = home.child("seed-routed")
    assert seeded["root_multiplex"] is True
    assert seeded["source_profile_matches"] is True
    assert seeded["route_rejected"] is False
    assert seeded["key_namespace"] == PROFILE  # the profile namespace, not agent:main

    read = home.child("read")
    assert read["profile_served"] is True
    assert read["route_count"] == 1
    # Surface 1, canonical conversation: snapshot, history and lineage.
    assert read["canonical_ref_resolved"] is True
    assert read["canonical_session_digest"] == seeded["session_digest"]
    assert read["canonical_snapshot_rows"] == MESSAGES
    assert read["canonical_history_rows"] == MESSAGES
    assert read["canonical_active_rows"] == MESSAGES
    assert read["canonical_head_is_newest"] is True
    assert read["canonical_roles"] == ["user", "assistant", "user", "assistant"]
    # Surface 2, id-addressed session read.
    assert read["browse"] == [
        {
            "session_digest": seeded["session_digest"],
            "resolved": True,
            "rows": MESSAGES,
            "message_count": MESSAGES,
            "phone_list_visible": True,
        }
    ]
    # Reading and seeding never rewrote the profile's own config.
    assert home.profile_config.read_bytes() == home.initial_profile_config
    _record(binding, "origin_a", flag_state, helper=helper, seeded=seeded, read=read)


# --------------------------------------------------------------------------------------------------
# Origin B: pre-existing history from a standalone gateway of the profile (no own multiplex)
# --------------------------------------------------------------------------------------------------


def test_origin_b_standalone_history_differs_by_surface(
    home: Home, flag_state: str, binding: Any
) -> None:
    seeded = home.child("seed-standalone")
    assert seeded["own_multiplex_flag_as_loaded"] in (None, False)
    assert seeded["key_namespace"] == "main"  # a standalone gateway keys in the legacy namespace
    config_after_seed = home.profile_config.read_bytes()

    helper = home.run_route_helper()
    # The helper changes neither the profile's config nor its history, nor any metadata.
    assert helper["profile_tree_identical"] is True
    assert helper["profile_entries"] > 1
    assert helper["root_changed_entries"] == [".", "config.yaml", "config.yaml.hmp-bak"]
    assert home.profile_config.read_bytes() == config_after_seed

    read = home.child("read")
    assert read["profile_served"] is True
    assert read["route_count"] == 1
    # Surface 1, canonical conversation: the routed lookup key is in the profile namespace and the
    # standalone history sits under the legacy one, so the Phone sees an empty conversation.
    assert read["canonical_ref_resolved"] is False
    assert read["canonical_ref_error"] is None
    assert read["canonical_snapshot_rows"] == 0
    assert read["canonical_history_rows"] == 0
    # Surface 2, id-addressed read: the session is listed, resolves and reads in full, but the
    # Phone's list filter (own canonical session or the hidden "Bot Chat") does not show it.
    assert read["browse"] == [
        {
            "session_digest": seeded["session_digest"],
            "resolved": True,
            "rows": MESSAGES,
            "message_count": MESSAGES,
            "phone_list_visible": False,
        }
    ]
    _record(binding, "origin_b", flag_state, helper=helper, seeded=seeded, read=read)


def test_origin_b_then_routed_conversation_starts_a_new_session(
    home: Home, flag_state: str, binding: Any
) -> None:
    standalone = home.child("seed-standalone")
    home.run_route_helper()
    routed = home.child("seed-routed")
    assert routed["key_namespace"] == PROFILE
    assert routed["session_digest"] != standalone["session_digest"]

    read = home.child("read")
    # The canonical conversation is the new routed session only.
    assert read["canonical_ref_resolved"] is True
    assert read["canonical_session_digest"] == routed["session_digest"]
    assert read["canonical_snapshot_rows"] == MESSAGES
    assert read["canonical_history_rows"] == MESSAGES
    # The earlier standalone session stays in the profile's database, reachable only by id.
    by_digest = {item["session_digest"]: item for item in read["browse"]}
    assert set(by_digest) == {routed["session_digest"], standalone["session_digest"]}
    old = by_digest[standalone["session_digest"]]
    assert (old["resolved"], old["rows"], old["message_count"]) == (True, MESSAGES, MESSAGES)
    assert old["phone_list_visible"] is False
    assert by_digest[routed["session_digest"]]["phone_list_visible"] is True
    assert home.profile_config.read_bytes() == home.initial_profile_config
    _record(binding, "origin_b_then_a", flag_state, standalone=standalone, routed=routed, read=read)
