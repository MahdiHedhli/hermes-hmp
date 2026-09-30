"""`hermes hmp routes add <profile>` (specs/005-new-profile-routing).

Every test runs in an isolated temporary home with synthetic profile names. Nothing here touches a
real Hermes home, spawns a process, opens the HMP store or uses the network. The CLI's `hermes`
runner and executable resolver are replaced by fakes that fail the test if they are ever called,
which is how "no approval, no restart, no Hermes contact" is checked.
"""

from __future__ import annotations

import argparse
import io
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from hmp_plugin import cli, routes

from . import hmp_kit

ROOT_YAML = """\
# operator comment (not preserved when the file is re-emitted)
plugins:
  enabled: ["hmp"]
platforms:
  hmp:
    enabled: true
    extra:
      bind: 127.0.0.1
      port: 18741
model:
  default: some-model
  when: 2020-01-01
  flag: "yes"
  ratio: 1.5
  label: "café"
gateway:
  multiplex_profiles: true
  profile_routes:
    - name: alpha-route
      platform: hmp
      profile: alpha
      guild_id: alpha
    - name: other-platform-route
      platform: telegram
      profile: alpha
      guild_id: beta
tail_key: last
"""
ALPHA_YAML = "gateway:\n  multiplex_profiles: true\nagent:\n  name: alpha\n"
BETA_YAML = "agent:\n  name: beta\n"


class Tty(io.StringIO):
    def __init__(self, tty: bool = True) -> None:
        super().__init__()
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


class Home:
    """An isolated default root with an `alpha` profile already routed and a `beta` profile that
    was created afterwards (no route)."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self.kw = hmp_kit.identity_kwargs(base)
        self.root: Path = self.kw["hermes_root"]
        self.root.mkdir(mode=0o700)
        (self.root / "profiles").mkdir(mode=0o700)
        self.calls: list[str] = []
        self.write("config.yaml", ROOT_YAML)
        self.make_profile("alpha", ALPHA_YAML)
        self.make_profile("beta", BETA_YAML)

    # ---- files ----------------------------------------------------------------------------------

    def path(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    def write(self, rel: str, text: str | bytes, mode: int = 0o600) -> Path:
        p = self.path(*rel.split("/"))
        p.write_bytes(text.encode() if isinstance(text, str) else text)
        p.chmod(mode)
        return p

    def make_profile(self, name: str, config: str | None) -> Path:
        home = self.path("profiles", name)
        home.mkdir(mode=0o700)
        if config is not None:
            self.write(f"profiles/{name}/config.yaml", config)
        return home

    def load(self, rel: str) -> Any:
        return yaml.safe_load(self.path(*rel.split("/")).read_text(encoding="utf-8"))

    def snapshot(self) -> dict[str, tuple[bytes, int, int, int]]:
        """Every file under the root: bytes, mode, inode, mtime. Equal snapshots = nothing was
        touched."""
        out: dict[str, tuple[bytes, int, int, int]] = {}
        for p in sorted(self.root.rglob("*")):
            if p.is_file() and not p.is_symlink():
                st = p.stat()
                rel = str(p.relative_to(self.root))
                out[rel] = (p.read_bytes(), stat.S_IMODE(st.st_mode), st.st_ino, st.st_mtime_ns)
        return out

    # ---- running the CLI ------------------------------------------------------------------------

    def env(self, *, tty: bool = True, environ: dict[str, str] | None = None) -> cli.CliEnv:
        def no_hermes(*_a: Any, **_k: Any) -> Any:
            self.calls.append("hermes")
            raise AssertionError("routes add must never run the hermes CLI")

        def no_exe() -> str | None:
            self.calls.append("exe")
            raise AssertionError("routes add must never resolve the hermes executable")

        self.stdout, self.stderr = Tty(tty), io.StringIO()
        return cli.CliEnv(
            environ=environ if environ is not None else dict(self.kw["env"]),
            stdin=Tty(tty),
            stdout=self.stdout,
            stderr=self.stderr,
            identity_kwargs={**self.kw, **({"env": environ} if environ is not None else {})},
            hermes_executable=no_exe,
            run_hermes_cli=no_hermes,
        )

    def run(self, *argv: str, **env_kw: Any) -> int:
        parser = argparse.ArgumentParser(prog="hermes hmp")
        cli.setup_parser(parser)
        return cli.dispatch(parser.parse_args(["routes", "add", *argv]), self.env(**env_kw))

    @property
    def out(self) -> str:
        return self.stdout.getvalue()

    @property
    def err(self) -> str:
        return self.stderr.getvalue()


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Home:
    def no_process(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("no subprocess may be started")

    monkeypatch.setattr(subprocess, "Popen", no_process)
    return Home(tmp_path)


def routes_of(doc: Any) -> list[dict[str, Any]]:
    return doc["gateway"]["profile_routes"]


BETA_ROUTE = {"name": "beta-route", "platform": "hmp", "profile": "beta", "guild_id": "beta"}


# --------------------------------------------------------------------------------------------------
# The repair: a bot created after installation
# --------------------------------------------------------------------------------------------------


def test_new_bot_created_after_initial_routing(home: Home) -> None:
    home.path("config.yaml").chmod(0o640)
    before_root = home.load("config.yaml")
    alpha_before = home.snapshot()["profiles/alpha/config.yaml"]
    beta_before = home.snapshot()["profiles/beta/config.yaml"]

    assert home.run("beta") == cli.EXIT_OK, home.err
    after_root = home.load("config.yaml")

    assert routes_of(after_root) == [*routes_of(before_root), BETA_ROUTE]
    expected = dict(before_root)
    expected["gateway"] = {**before_root["gateway"], "profile_routes": routes_of(after_root)}
    assert after_root == expected  # every other value preserved, in the same key order
    assert list(after_root) == list(before_root)
    assert home.snapshot()["profiles/beta/config.yaml"] == beta_before  # never touched
    assert home.path("profiles", "beta", "config.yaml").read_bytes() == BETA_YAML.encode()
    assert home.snapshot()["profiles/alpha/config.yaml"] == alpha_before  # untouched, same inode
    assert stat.S_IMODE(home.path("config.yaml").stat().st_mode) == 0o640

    # One private backup of the original root, and nothing else new (no profile backup).
    assert home.path("config.yaml.hmp-bak").read_text(encoding="utf-8") == ROOT_YAML
    assert stat.S_IMODE(home.path("config.yaml.hmp-bak").stat().st_mode) == 0o600
    assert sorted(home.snapshot()) == [
        "config.yaml",
        "config.yaml.hmp-bak",
        "profiles/alpha/config.yaml",
        "profiles/beta/config.yaml",
    ]
    assert not list(home.root.rglob("*.tmp"))


def test_output_states_the_sequence_and_the_limits(home: Home) -> None:
    assert home.run("beta") == cli.EXIT_OK
    out = home.out
    assert "hermes gateway restart" in out
    assert "request access to beta" in out
    assert "hermes -p beta pairing approve hmp <request_id>" in out
    assert "did not restart the gateway, authorize any phone" in out
    assert "on disk only" in out
    assert "did not activate it" in out
    assert "not served or send-ready" not in out
    assert "(manual)" in out
    assert "multiplex" not in out.lower()  # no claim about a profile setting
    assert str(home.root) not in out and str(home.base) not in out  # no absolute paths


def test_second_run_is_a_successful_no_op(home: Home) -> None:
    assert home.run("beta") == cli.EXIT_OK
    first = home.snapshot()
    assert home.run("beta") == cli.EXIT_OK
    assert "already in the root config.yaml; nothing was changed" in home.out
    assert "hermes gateway restart" in home.out
    assert home.snapshot() == first  # same bytes, modes, inodes: nothing rewritten, no backup


def test_a_profile_that_is_already_prepared_is_not_rewritten(home: Home) -> None:
    # alpha is already routed by the fixture's initial state.
    before = home.snapshot()
    assert home.run("alpha") == cli.EXIT_OK
    assert "already in the root config.yaml" in home.out
    assert home.snapshot() == before


@pytest.mark.parametrize("shape", ["absent", "no-gateway"])
def test_root_multiplex_is_never_turned_on(home: Home, shape: str) -> None:
    doc = home.load("config.yaml")
    if shape == "absent":
        del doc["gateway"]["multiplex_profiles"]
    else:
        del doc["gateway"]
    home.write("config.yaml", yaml.safe_dump(doc, sort_keys=False))
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert "does not turn on multiplexing" in home.err
    assert "DEPLOYMENT.md" in home.err
    assert home.snapshot() == before  # no write, no backup


PROFILE_FLAG_SHAPES = {
    "absent": BETA_YAML,
    "no-gateway-mapping": "gateway:\n",
    "nested-false": "gateway:\n  multiplex_profiles: false\n",
    "nested-true": "gateway:\n  multiplex_profiles: true\n",
    "nested-string": "gateway:\n  multiplex_profiles: 'true'\n",
    "nested-null": "gateway:\n  multiplex_profiles:\n",
    "top-false": "multiplex_profiles: false\n",
    "top-true": "multiplex_profiles: true\n",
    "top-string": "multiplex_profiles: 'yes'\n",
    "top-true-nested-false": "multiplex_profiles: true\ngateway:\n  multiplex_profiles: false\n",
    "comment-only": "# only a comment\n",
    "empty": "",
}


@pytest.mark.parametrize("shape", sorted(PROFILE_FLAG_SHAPES))
def test_profile_config_is_never_touched_whatever_its_flag(home: Home, shape: str) -> None:
    """Root route only: the profile's own flag is not read, required, refused or written. Bytes,
    mode, inode and mtime are identical, and no profile backup appears."""
    home.write("profiles/beta/config.yaml", PROFILE_FLAG_SHAPES[shape])
    os.utime(home.path("profiles", "beta", "config.yaml"), ns=(1_000_000_000, 1_000_000_000))
    before = home.snapshot()["profiles/beta/config.yaml"]
    assert home.run("beta") == cli.EXIT_OK, home.err
    assert BETA_ROUTE in routes_of(home.load("config.yaml"))
    assert home.snapshot()["profiles/beta/config.yaml"] == before
    assert not home.path("profiles", "beta", "config.yaml.hmp-bak").exists()
    assert not list((home.root / "profiles").rglob("*.hmp-bak"))
    assert not list(home.root.rglob("*.tmp"))


def test_profile_with_existing_sessions_is_allowed_and_untouched(home: Home) -> None:
    """Nonzero history is not a reason to refuse, and nothing under the profile moves."""
    sessions = home.path("profiles", "beta", "sessions")
    sessions.mkdir(mode=0o700)
    (sessions / "s1.json").write_bytes(b'{"fixture": "history"}')
    (sessions / "s1.json").chmod(0o600)
    home.write("profiles/beta/state.db", b"not-a-real-db")
    home.write("profiles/beta/config.yaml", PROFILE_FLAG_SHAPES["nested-false"])
    before = {k: v for k, v in home.snapshot().items() if k.startswith("profiles/beta/")}
    assert home.run("beta") == cli.EXIT_OK, home.err
    after = {k: v for k, v in home.snapshot().items() if k.startswith("profiles/beta/")}
    assert after == before
    assert "sessions" not in home.out.lower()  # no history warning or refusal


def test_null_gateway_and_null_routes_are_treated_as_unset(home: Home) -> None:
    home.write(
        "config.yaml",
        "gateway:\n  multiplex_profiles: true\n  profile_routes:\nplugins:\n  enabled: [hmp]\n",
    )
    home.write("profiles/beta/config.yaml", "gateway:\n")
    before = home.snapshot()["profiles/beta/config.yaml"]
    assert home.run("beta") == cli.EXIT_OK, home.err
    assert home.load("config.yaml")["gateway"] == {
        "multiplex_profiles": True,
        "profile_routes": [BETA_ROUTE],
    }
    assert home.snapshot()["profiles/beta/config.yaml"] == before


def test_route_for_another_platform_with_same_guild_is_not_a_conflict(home: Home) -> None:
    # ROOT_YAML already carries `platform: telegram, guild_id: beta`.
    assert home.run("beta") == cli.EXIT_OK
    assert any(r.get("platform") == "telegram" for r in routes_of(home.load("config.yaml")))


def test_backup_is_one_rolling_file(home: Home) -> None:
    home.make_profile("gamma", BETA_YAML)
    assert home.run("beta") == cli.EXIT_OK
    after_beta = home.path("config.yaml").read_bytes()
    assert home.run("gamma") == cli.EXIT_OK
    backups = sorted(p.name for p in home.root.glob("*.hmp-bak"))
    assert backups == ["config.yaml.hmp-bak"]  # replaced, not accumulated
    assert home.path("config.yaml.hmp-bak").read_bytes() == after_beta
    assert stat.S_IMODE(home.path("config.yaml.hmp-bak").stat().st_mode) == 0o600


# --------------------------------------------------------------------------------------------------
# No side effect beyond the root config and its backup
# --------------------------------------------------------------------------------------------------


def test_no_hermes_call_no_store_no_identity_no_listener_state(home: Home) -> None:
    assert home.run("beta") == cli.EXIT_OK
    assert home.calls == []  # no `hermes pairing ...`, no gateway restart, no executable lookup
    assert not home.path("plugin-data").exists()  # no HMP store, identity, or listener record
    assert not (home.base / "state").exists()  # no binding
    assert not list(home.root.rglob("*.db")) and not list(home.root.rglob("approved*"))


# --------------------------------------------------------------------------------------------------
# Guards shared with the other mutating commands
# --------------------------------------------------------------------------------------------------


def test_refuses_without_a_terminal(home: Home) -> None:
    before = home.snapshot()
    assert home.run("beta", tty=False) == cli.EXIT_REFUSED
    assert "interactive terminal" in home.err
    assert home.snapshot() == before


def test_refuses_inside_a_hermes_session(home: Home) -> None:
    before = home.snapshot()
    environ = {**home.kw["env"], "HERMES_SESSION_ID": "x"}
    assert home.run("beta", environ=environ) == cli.EXIT_REFUSED
    assert "not a Hermes session" in home.err
    assert home.snapshot() == before


def test_refuses_under_a_named_profile(home: Home) -> None:
    before = home.snapshot()
    environ = {"HERMES_HOME": str(home.path("profiles", "beta"))}
    assert home.run("beta", environ=environ) == cli.EXIT_ENVIRONMENT
    assert "default profile" in home.err
    assert home.snapshot() == before


def test_routes_add_is_registered_as_mutating() -> None:
    assert ("routes", "add") in cli.MUTATING_COMMANDS


# --------------------------------------------------------------------------------------------------
# Wrong profile and unsafe paths
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name", ["../beta", "Beta", "", "a" * 65, "default", "be ta", "beta/x", ".beta", "beta\n"]
)
def test_invalid_profile_names_are_refused(home: Home, name: str) -> None:
    before = home.snapshot()
    assert home.run(name) == cli.EXIT_REFUSED
    assert home.snapshot() == before


def test_unknown_profile_is_refused_and_not_created(home: Home) -> None:
    before = home.snapshot()
    assert home.run("nosuch") == cli.EXIT_REFUSED
    assert "does not exist" in home.err
    assert home.snapshot() == before
    assert not home.path("profiles", "nosuch").exists()


def test_profile_without_config_is_refused_and_not_created(home: Home) -> None:
    home.make_profile("bare", None)
    before = home.snapshot()
    assert home.run("bare") == cli.EXIT_REFUSED
    assert not home.path("profiles", "bare", "config.yaml").exists()
    assert home.snapshot() == before


def test_missing_root_config_is_refused_and_not_created(home: Home) -> None:
    home.path("config.yaml").unlink()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert not home.path("config.yaml").exists()


def test_symlinked_profile_directory_is_refused(home: Home) -> None:
    elsewhere = home.base / "elsewhere"
    elsewhere.mkdir(mode=0o700)
    (elsewhere / "config.yaml").write_text(BETA_YAML)
    (elsewhere / "config.yaml").chmod(0o600)
    home.path("profiles", "linked").symlink_to(elsewhere)
    assert home.run("linked") == cli.EXIT_REFUSED
    assert (elsewhere / "config.yaml").read_text() == BETA_YAML


def test_symlinked_profile_config_is_refused(home: Home) -> None:
    target = home.base / "real.yaml"
    target.write_text(BETA_YAML)
    target.chmod(0o600)
    cfg = home.path("profiles", "beta", "config.yaml")
    cfg.unlink()
    cfg.symlink_to(target)
    assert home.run("beta") == cli.EXIT_REFUSED
    assert target.read_text() == BETA_YAML and cfg.is_symlink()


def test_symlinked_root_config_is_refused(home: Home) -> None:
    target = home.base / "real-root.yaml"
    target.write_text(ROOT_YAML)
    target.chmod(0o600)
    home.path("config.yaml").unlink()
    home.path("config.yaml").symlink_to(target)
    assert home.run("beta") == cli.EXIT_REFUSED
    assert target.read_text() == ROOT_YAML


def test_symlinked_profiles_directory_is_refused(home: Home) -> None:
    real = home.base / "real-profiles"
    home.path("profiles").rename(real)
    home.path("profiles").symlink_to(real)
    assert home.run("beta") == cli.EXIT_REFUSED
    assert (real / "beta" / "config.yaml").read_text() == BETA_YAML


@pytest.mark.parametrize("bad_mode", [0o660, 0o666, 0o620, 0o602])
def test_group_or_world_writable_config_is_refused(home: Home, bad_mode: int) -> None:
    home.path("profiles", "beta", "config.yaml").chmod(bad_mode)
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert "not group- or world-writable" in home.err
    assert home.snapshot() == before


def test_world_writable_profile_directory_is_refused(home: Home) -> None:
    home.path("profiles", "beta").chmod(0o777)
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert home.snapshot() == before


def test_unsafe_root_directory_is_refused(home: Home) -> None:
    home.root.chmod(0o775)
    assert home.run("beta") == cli.EXIT_REFUSED


def test_non_regular_config_is_refused(home: Home) -> None:
    cfg = home.path("profiles", "beta", "config.yaml")
    cfg.unlink()
    cfg.mkdir()
    assert home.run("beta") == cli.EXIT_REFUSED


def test_oversize_config_is_refused(home: Home) -> None:
    home.write("profiles/beta/config.yaml", b"#" * (routes.MAX_CONFIG_BYTES + 1))
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert "larger than" in home.err
    assert home.snapshot() == before


def test_backup_location_that_is_not_a_regular_file_is_refused(home: Home) -> None:
    home.path("config.yaml.hmp-bak").mkdir()
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert home.snapshot() == before


def test_backup_symlink_is_not_followed(home: Home) -> None:
    victim = home.base / "victim.txt"
    victim.write_text("keep")
    home.path("config.yaml.hmp-bak").symlink_to(victim)
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert victim.read_text() == "keep"
    assert home.snapshot() == before


# --------------------------------------------------------------------------------------------------
# YAML that cannot be edited safely
# --------------------------------------------------------------------------------------------------

BAD_YAML = {
    "duplicate-key": "gateway:\n  multiplex_profiles: true\ngateway:\n  x: 1\n",
    "duplicate-nested": "gateway:\n  a: 1\n  a: 2\n",
    "alias": "a: &x [1, 2]\nb: *x\n",
    "merge-key": "base: &b {x: 1}\nother:\n  <<: *b\n",
    "merge-inline": "other:\n  <<: {x: 1}\n",
    "malformed": "gateway: [unclosed\n",
    "two-documents": "a: 1\n---\nb: 2\n",
    "python-tag": "x: !!python/object/apply:os.getcwd []\n",
    "list-document": "- a\n- b\n",
    "scalar-document": "just text\n",
    "unhashable-key": "? [1, 2]\n: v\n",
    "not-utf8": b"\xff\xfe\x00bad",
    "deep": "a: " + "[" * 6000 + "]" * 6000 + "\n",
}


@pytest.mark.parametrize("which", ["root", "profile"])
@pytest.mark.parametrize("case", sorted(BAD_YAML))
def test_unsafe_yaml_is_refused_and_nothing_changes(home: Home, which: str, case: str) -> None:
    rel = "config.yaml" if which == "root" else "profiles/beta/config.yaml"
    home.write(rel, BAD_YAML[case])
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert "safely edit" in home.err or "mapping" in home.err
    assert home.snapshot() == before


# --------------------------------------------------------------------------------------------------
# Never widen: route overlaps and multiplex conflicts are refused
# --------------------------------------------------------------------------------------------------

OVERLAPPING_ROUTES = {
    "broad-no-platform-no-guild": {"name": "any", "profile": "alpha"},
    "hmp-no-guild": {"name": "all-hmp", "platform": "hmp", "profile": "alpha"},
    "hmp-empty-guild": {"platform": "hmp", "guild_id": "", "profile": "alpha"},
    "no-platform-same-guild": {"guild_id": "beta", "profile": "alpha"},
    "other-profile-same-guild": {"platform": "hmp", "guild_id": "beta", "profile": "alpha"},
    "user-specific": {"platform": "hmp", "guild_id": "beta", "profile": "beta", "user_id": "u1"},
    "chat-specific": {"platform": "hmp", "guild_id": "beta", "profile": "beta", "chat_id": "c1"},
    "disabled": {"platform": "hmp", "guild_id": "beta", "profile": "beta", "enabled": False},
    "enabled-zero": {"platform": "hmp", "guild_id": "beta", "profile": "beta", "enabled": 0},
    "bot-profile-set": {**BETA_ROUTE, "bot_profile": "x"},
    "extra-narrowing-key": {**BETA_ROUTE, "thread": "t"},
    "case-variant-platform": {"platform": "HMP", "guild_id": "beta", "profile": "beta"},
    "case-variant-guild": {"platform": "hmp", "guild_id": " Beta ", "profile": "beta"},
    "glob-guild": {"platform": "hmp", "guild_id": "b*", "profile": "alpha"},
    "glob-platform": {"platform": "h*", "guild_id": "beta", "profile": "alpha"},
    "list-platform": {"platform": ["hmp", "x"], "guild_id": "beta", "profile": "alpha"},
    "list-guild": {"platform": "hmp", "guild_id": ["beta"], "profile": "alpha"},
    "numeric-guild": {"platform": "hmp", "guild_id": 5, "profile": "alpha"},
    "enabled-null": {**BETA_ROUTE, "enabled": None},
    "user-id-null": {**BETA_ROUTE, "user_id": None},
    "chat-id-null": {**BETA_ROUTE, "chat_id": None},
    "extra-key-null": {**BETA_ROUTE, "bot_profile": None},
    "name-collision": {"name": "beta-route", "platform": "telegram", "guild_id": "zzz"},
}


@pytest.mark.parametrize("case", sorted(OVERLAPPING_ROUTES))
def test_overlapping_route_is_refused_not_widened(home: Home, case: str) -> None:
    doc = home.load("config.yaml")
    routes_of(doc).append(OVERLAPPING_ROUTES[case])
    home.write("config.yaml", yaml.safe_dump(doc, sort_keys=False))
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert "overlap" in home.err or "already exists" in home.err
    assert home.snapshot() == before


def test_exact_route_next_to_a_conflicting_one_is_still_refused(home: Home) -> None:
    doc = home.load("config.yaml")
    routes_of(doc).extend([BETA_ROUTE, OVERLAPPING_ROUTES["user-specific"]])
    home.write("config.yaml", yaml.safe_dump(doc, sort_keys=False))
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert home.snapshot() == before


def test_existing_exact_route_is_a_no_op(home: Home) -> None:
    doc = home.load("config.yaml")
    routes_of(doc).append({**BETA_ROUTE, "enabled": True})
    home.write("config.yaml", yaml.safe_dump(doc, sort_keys=False))
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_OK
    assert home.snapshot() == before  # nothing written, no backup, profile untouched


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.__setitem__("profile_routes", []),
        lambda d: d["gateway"].__setitem__("profile_routes", {"beta": "x"}),
        lambda d: d["gateway"]["profile_routes"].append("x"),
        lambda d: d.__setitem__("gateway", ["not", "a", "mapping"]),
    ],
    ids=["top-level-routes", "routes-not-a-list", "route-not-a-mapping", "gateway-not-a-mapping"],
)
def test_malformed_route_shapes_are_refused(home: Home, mutate: Any) -> None:
    doc = home.load("config.yaml")
    mutate(doc)
    home.write("config.yaml", yaml.safe_dump(doc, sort_keys=False))
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert home.snapshot() == before


@pytest.mark.parametrize(
    "text",
    [
        "gateway:\n  multiplex_profiles: false\n",
        "gateway:\n  multiplex_profiles: 'true'\n",
        "gateway:\n  multiplex_profiles: 1\n",
        "gateway:\n  multiplex_profiles:\n",
        "multiplex_profiles: false\n",
        "multiplex_profiles: true\ngateway:\n  multiplex_profiles: false\n",
        "multiplex_profiles: false\ngateway:\n  multiplex_profiles: true\n",
    ],
    ids=[
        "nested-false",
        "nested-string",
        "nested-int",
        "nested-null",
        "top-false",
        "top-true-nested-false",
        "top-false-nested-true",
    ],
)
def test_root_multiplex_conflicts_are_refused(home: Home, text: str) -> None:
    doc = yaml.safe_load(text)
    doc["gateway"] = {**(doc.get("gateway") or {}), "profile_routes": []}
    home.write("config.yaml", yaml.safe_dump(doc, sort_keys=False))
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert "multiplex_profiles" in home.err
    assert home.snapshot() == before


# --------------------------------------------------------------------------------------------------
# Write protocol: unchanged-check, ordering, rollback reporting
# --------------------------------------------------------------------------------------------------


def test_file_changed_between_read_and_write_is_refused(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = routes._verified_emit

    def emit_then_edit(doc: Any, snap: Any) -> bytes:
        data = original(doc, snap)
        if snap.label == "root config.yaml":  # a concurrent editor, after planning
            home.write("config.yaml", ROOT_YAML + "concurrent: edit\n")
        return data

    monkeypatch.setattr(routes, "_verified_emit", emit_then_edit)
    before_profile = home.snapshot()["profiles/beta/config.yaml"]
    assert home.run("beta") == cli.EXIT_REFUSED
    assert "changed while this command ran" in home.err
    assert "concurrent: edit" in home.path("config.yaml").read_text()  # their edit survives
    assert home.snapshot()["profiles/beta/config.yaml"] == before_profile
    assert not list(home.root.rglob("*.hmp-bak"))  # refused before any backup


def _root_write_hook(monkeypatch: pytest.MonkeyPatch, home: Home, hook: Any) -> None:
    """Route only the root config's own write through `hook(real_write, data, mode)`."""
    real = routes._atomic_write
    root_cfg = home.path("config.yaml")

    def wrapped(path: Path, data: bytes, mode: int) -> None:
        if path == root_cfg:
            hook(lambda: real(path, data, mode), data, mode)
        else:
            real(path, data, mode)

    monkeypatch.setattr(routes, "_atomic_write", wrapped)


def test_root_write_failure_before_rename_is_confirmed_unchanged(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(_write: Any, _data: bytes, _mode: int) -> None:
        raise OSError("disk full secret-detail")

    _root_write_hook(monkeypatch, home, fail)
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert "root config.yaml was not changed by this command" in home.err
    assert "profile config.yaml was not changed by this command" in home.err
    assert "secret-detail" not in home.err + home.out
    snap = home.snapshot()
    assert snap["config.yaml"] == before["config.yaml"]
    assert snap["profiles/beta/config.yaml"] == before["profiles/beta/config.yaml"]
    assert not list(home.root.rglob("*.tmp"))


def test_failure_after_rename_is_reported_as_updated_on_disk(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    def rename_then_fail(write: Any, _data: bytes, _mode: int) -> None:
        write()
        raise OSError("directory sync failed secret-detail")

    _root_write_hook(monkeypatch, home, rename_then_fail)
    assert home.run("beta") == cli.EXIT_ENVIRONMENT  # partial state: distinct exit code
    assert "root config.yaml now holds the new route" in home.err
    assert "running gateway is unchanged" in home.err
    assert "config.yaml.hmp-bak" in home.err
    assert "secret-detail" not in home.err + home.out
    assert BETA_ROUTE in routes_of(home.load("config.yaml"))
    assert home.path("profiles", "beta", "config.yaml").read_bytes() == BETA_YAML.encode()


def test_failure_then_external_edit_is_unconfirmed_and_never_restored(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    def edit_then_fail(_write: Any, _data: bytes, _mode: int) -> None:
        home.write("config.yaml", ROOT_YAML + "someone: else\n")
        raise OSError("boom")

    _root_write_hook(monkeypatch, home, edit_then_fail)
    assert home.run("beta") == cli.EXIT_ENVIRONMENT
    assert "state could not be confirmed" in home.err
    assert "config.yaml.hmp-bak" in home.err
    assert "someone: else" in home.path("config.yaml").read_text()  # their edit is left alone
    assert home.path("profiles", "beta", "config.yaml").read_bytes() == BETA_YAML.encode()


def test_the_only_config_write_is_the_root(home: Home, monkeypatch: pytest.MonkeyPatch) -> None:
    real = routes._atomic_write
    written: list[Path] = []

    def spy(path: Path, data: bytes, mode: int) -> None:
        written.append(path)
        real(path, data, mode)

    monkeypatch.setattr(routes, "_atomic_write", spy)
    assert home.run("beta") == cli.EXIT_OK
    # the private backup, then the root itself; never anything under the profile
    assert written == [home.path("config.yaml.hmp-bak"), home.path("config.yaml")]


def test_written_root_keeps_its_mode(home: Home) -> None:
    home.path("config.yaml").chmod(0o644)
    assert home.run("beta") == cli.EXIT_OK
    assert stat.S_IMODE(home.path("config.yaml").stat().st_mode) == 0o644
    assert stat.S_IMODE(home.path("config.yaml.hmp-bak").stat().st_mode) == 0o600


# --------------------------------------------------------------------------------------------------
# Module-level checks
# --------------------------------------------------------------------------------------------------


def test_route_shape_matches_the_documented_deployment_shape() -> None:
    result = routes.plan({"gateway": {"multiplex_profiles": True}}, "beta")
    assert result.root_doc == {
        "gateway": {"multiplex_profiles": True, "profile_routes": [BETA_ROUTE]}
    }
    assert result.route_added


def test_plan_does_not_mutate_its_inputs() -> None:
    root = {"gateway": {"multiplex_profiles": True, "profile_routes": []}}
    routes.plan(root, "beta")
    assert root == {"gateway": {"multiplex_profiles": True, "profile_routes": []}}


def test_environment_is_not_printed_or_needed(home: Home) -> None:
    secret = {**home.kw["env"], "SOME_TOKEN": "s3cret-value"}
    assert home.run("beta", environ=secret) == cli.EXIT_OK
    assert "s3cret-value" not in home.out + home.err
    assert os.environ.get("SOME_TOKEN") != "s3cret-value"


# --------------------------------------------------------------------------------------------------
# Review repair: both snapshots checked, interrupts reported, clean pre-write refusals
# --------------------------------------------------------------------------------------------------


def test_file_changed_between_read_and_write_is_refused_for_the_profile_too(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The profile config is only inspected, but drift in it since the read still refuses."""
    original = routes._verified_emit

    def emit_then_edit_profile(doc: Any, snap: Any) -> bytes:
        data = original(doc, snap)
        home.write("profiles/beta/config.yaml", BETA_YAML + "concurrent: edit\n")
        return data

    monkeypatch.setattr(routes, "_verified_emit", emit_then_edit_profile)
    root_before = home.snapshot()["config.yaml"]
    assert home.run("beta") == cli.EXIT_REFUSED
    assert "changed while this command ran" in home.err
    assert home.snapshot()["config.yaml"] == root_before
    assert "concurrent: edit" in home.path("profiles", "beta", "config.yaml").read_text()
    assert not list(home.root.rglob("*.hmp-bak"))


def test_edit_during_backup_write_is_caught_before_the_rename(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = routes._write_backup

    def backup_then_edit(snap: Any, target: Path) -> str:
        label = real(snap, target)
        home.write("config.yaml", ROOT_YAML + "concurrent: edit\n")
        return label

    monkeypatch.setattr(routes, "_write_backup", backup_then_edit)
    profile_before = home.snapshot()["profiles/beta/config.yaml"]
    assert home.run("beta") == cli.EXIT_REFUSED
    assert "no config file was changed by this command" in home.err
    assert home.snapshot()["profiles/beta/config.yaml"] == profile_before
    assert "concurrent: edit" in home.path("config.yaml").read_text()
    assert "beta-route" not in home.path("config.yaml").read_text()


def test_profile_edited_during_backup_write_is_caught_before_the_rename(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = routes._write_backup

    def backup_then_edit(snap: Any, target: Path) -> str:
        label = real(snap, target)
        home.write("profiles/beta/config.yaml", BETA_YAML + "concurrent: edit\n")
        return label

    monkeypatch.setattr(routes, "_write_backup", backup_then_edit)
    root_before = home.path("config.yaml").read_bytes()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert home.path("config.yaml").read_bytes() == root_before


def _interrupt_root_write(
    monkeypatch: pytest.MonkeyPatch, home: Home, *, after: bool, exc: BaseException
) -> None:
    def hook(write: Any, _data: bytes, _mode: int) -> None:
        if after:
            write()
        raise exc

    _root_write_hook(monkeypatch, home, hook)


@pytest.mark.parametrize("exc", [KeyboardInterrupt(), SystemExit(2)], ids=["ctrl-c", "exit"])
def test_interrupt_before_root_rename_changes_nothing_and_says_so(
    home: Home, monkeypatch: pytest.MonkeyPatch, exc: BaseException
) -> None:
    _interrupt_root_write(monkeypatch, home, after=False, exc=exc)
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_INTERRUPTED
    assert "interrupted" in home.err
    assert "root config.yaml was not changed by this command" in home.err
    assert "profile config.yaml was not changed by this command" in home.err
    snap = home.snapshot()
    assert snap["config.yaml"] == before["config.yaml"]
    assert snap["profiles/beta/config.yaml"] == before["profiles/beta/config.yaml"]
    assert home.calls == []


@pytest.mark.parametrize("exc", [KeyboardInterrupt(), SystemExit(2)], ids=["ctrl-c", "exit"])
def test_interrupt_after_root_rename_reports_route_on_disk(
    home: Home, monkeypatch: pytest.MonkeyPatch, exc: BaseException
) -> None:
    _interrupt_root_write(monkeypatch, home, after=True, exc=exc)
    assert home.run("beta") == cli.EXIT_INTERRUPTED
    assert "interrupted" in home.err
    assert "root config.yaml now holds the new route" in home.err
    assert "profile config.yaml was not changed by this command" in home.err
    assert BETA_ROUTE in routes_of(home.load("config.yaml"))
    assert home.path("profiles", "beta", "config.yaml").read_bytes() == BETA_YAML.encode()
    assert home.calls == []


def test_interrupt_inside_the_real_rename_window_is_reported_from_file_content(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Interrupt in the directory sync that follows the real rename (keyed on content: the backup
    phase also syncs a directory, before the root changes)."""
    root_cfg = home.path("config.yaml")

    def fsync_then_interrupt(_path: Path) -> None:
        if "beta-route" in root_cfg.read_text():
            raise KeyboardInterrupt

    monkeypatch.setattr(routes, "_fsync_dir", fsync_then_interrupt)
    assert home.run("beta") == cli.EXIT_INTERRUPTED
    assert "root config.yaml now holds the new route" in home.err
    assert BETA_ROUTE in routes_of(home.load("config.yaml"))
    assert home.calls == []


def test_interrupt_at_the_real_replace_leaves_root_unchanged(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    root_cfg = home.path("config.yaml")
    real = os.replace

    def replace(src: Any, dst: Any, *a: Any, **k: Any) -> None:
        if Path(dst) == root_cfg:
            raise KeyboardInterrupt
        real(src, dst, *a, **k)

    monkeypatch.setattr(routes.os, "replace", replace)
    before_root = root_cfg.read_bytes()
    assert home.run("beta") == cli.EXIT_INTERRUPTED
    assert "root config.yaml was not changed by this command" in home.err
    assert root_cfg.read_bytes() == before_root
    assert not list(home.root.rglob("*.tmp"))
    assert home.calls == []


@pytest.mark.parametrize(
    "failure",
    [
        PermissionError("secret-detail"),
        RecursionError("secret-detail"),
        ImportError("secret-detail"),
    ],
    ids=["oserror", "recursion", "import"],
)
def test_unexpected_pre_write_failure_is_a_clean_status_only_refusal(
    home: Home, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    def boom(*_a: Any, **_k: Any) -> Any:
        raise failure

    monkeypatch.setattr(routes, "plan", boom)
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert "nothing was changed" in home.err
    assert "secret-detail" not in home.err + home.out
    assert "Traceback" not in home.err
    assert home.snapshot() == before


def test_backup_target_stat_failure_is_a_clean_refusal(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(_snap: Any) -> Path:
        raise PermissionError("secret-detail")

    monkeypatch.setattr(routes, "_backup_target", boom)
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert "nothing was changed" in home.err and "secret-detail" not in home.err
    assert home.snapshot() == before


def test_emission_failure_before_any_write_is_a_status_only_refusal(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(_doc: Any) -> bytes:
        raise RecursionError("secret-detail")

    monkeypatch.setattr(routes, "_emit", boom)
    before = home.snapshot()
    assert home.run("beta") == cli.EXIT_REFUSED
    assert "nothing was changed" in home.err
    assert "secret-detail" not in home.err + home.out
    assert "Traceback" not in home.err
    assert home.snapshot() == before
