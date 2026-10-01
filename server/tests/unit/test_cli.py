"""T032: the operator CLI, and the PR1-4 listener runtime record (coordinator conditions).

Each refusal and each SAS rule has its own test. The record tests cover: mode 0600, next to the
store, written atomically, removed when the server stops, and the CLI refusing a missing, stale,
unsafe or other-key record. An offer's `ep` equals the listener's bound address.

Every value is synthetic. The CLI runs against an isolated home (`hmp_kit.Env`). Its TTY is a fake
stream that says it is a terminal.
"""

from __future__ import annotations

import argparse
import asyncio
import builtins
import io
import json
import os
import shutil
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import cli, crypto, identity, server, wire
from hmp_plugin.compat import BuildEntry, BuildIdentity, CompatResult, CompatStatus
from hmp_plugin.contract import OFFER_TTL_S, SAS_MAX_MISMATCHES, TAG_OFFER, OtherWhy
from hmp_plugin.pairing import PairingService

from . import hmp_kit
from .test_adapter import _Config, _free_port, adapter_module  # noqa: F401 - fixture

TAILNET_HOST = "100\x2e64.0.1"  # Synthetic CGNAT test address.
FP = "f" * 64


class Tty(io.StringIO):
    def __init__(self, tty: bool = True) -> None:
        super().__init__()
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


class FakeQr:
    """Stands in for the `qrcode` module; keeps what it was asked to render."""

    def __init__(self) -> None:
        self.rendered: list[str] = []
        outer = self

        class QRCode:
            def __init__(self, **_kw: Any) -> None:
                self.data = ""

            def add_data(self, data: str) -> None:
                self.data = data

            def make(self, fit: bool = True) -> None:
                del fit

            def print_ascii(self, out: Any = None, tty: bool = False, invert: bool = False) -> None:
                del tty, invert
                outer.rendered.append(self.data)
                out.write("[qr]\n")

        self.QRCode = QRCode


SUPPORTED = CompatResult(
    CompatStatus.SUPPORTED,
    identity=BuildIdentity(fingerprint=FP),
    entry=BuildEntry(
        fingerprint=FP, git_sha=None, label="stock-base", qualified_by="t", qualified_at="d"
    ),
)


class Cli:
    def __init__(self, env: hmp_kit.Env, *, tty: bool = True) -> None:
        self.env = env
        self.qr = FakeQr()
        self.stdout = Tty(tty)
        self.stderr = io.StringIO()
        self.environ: dict[str, str] = dict(env.kwargs["env"])
        self.compat: CompatResult = SUPPORTED
        self.alive: set[int] = {os.getpid()}
        self.qr_missing = False
        # SR-7: the record's records in these tests never correspond to a real listener, so the
        # live liveness/identity check is stubbed "OK" by default; tests exercising it directly
        # flip this or replace `verify_listener_live` in `cli_env()`.
        self.listener_live = True
        self.listener_live_calls: list[Any] = []

    def cli_env(self) -> cli.CliEnv:
        def qr_factory() -> Any:
            if self.qr_missing:
                raise ImportError("qrcode")
            return self.qr

        def verify_listener_live(record: Any, iid: str) -> bool:
            self.listener_live_calls.append((record, iid))
            return self.listener_live

        return cli.CliEnv(
            environ=self.environ,
            stdin=Tty(self.stdout.isatty()),
            stdout=self.stdout,
            stderr=self.stderr,
            clock=self.env.clock,
            compat=lambda: self.compat,
            qr_factory=qr_factory,
            pid_alive=lambda pid: pid in self.alive,
            verify_listener_live=verify_listener_live,
            identity_kwargs=dict(self.env.kwargs),
        )

    def run(self, *argv: str) -> int:
        parser = argparse.ArgumentParser(prog="hermes hmp")
        cli.setup_parser(parser)
        self.stdout.seek(0)
        self.stdout.truncate()
        self.stderr.seek(0)
        self.stderr.truncate()
        return cli.dispatch(parser.parse_args(list(argv)), self.cli_env())

    def confirm(self, pairing_id: str, *rest: str) -> int:
        """`pair confirm` with the id after `--`: a b64u id may start with `-`."""
        return self.run("pair", "confirm", *rest, "--", pairing_id)

    @property
    def out(self) -> str:
        return self.stdout.getvalue()

    @property
    def err(self) -> str:
        return self.stderr.getvalue()

    def record_path(self) -> Path:
        return cli.listener_record_path(self.env.custody.anchor_dir)

    def write_record(
        self,
        host: str = TAILNET_HOST,
        port: int = 18920,
        iid: str | None = None,
        profiles: list[tuple[str, str]] | None = None,
        health_checked_at: int | None = None,
        health: list[tuple[str, str, str, str]] | None = None,
    ) -> None:
        cli.write_listener_record(
            self.record_path(), host=host, port=port, iid=iid or self.env.iid, profiles=profiles,
            health_checked_at=health_checked_at, health=health,
        )


@pytest.fixture
def env(tmp_path: Path) -> hmp_kit.Env:
    return hmp_kit.Env(tmp_path)


@pytest.fixture
def c(env: hmp_kit.Env) -> Cli:
    return Cli(env)


def _count(env: hmp_kit.Env, table: str) -> int:
    with env.store.transaction() as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])  # noqa: S608


def _pending(
    env: hmp_kit.Env, *, user: str | None = None, name: str = "f1-fixture-device-1"
) -> tuple[str, str]:
    """A P2-claimed pairing awaiting the operator. Returns (pairing_id, full SAS)."""
    oid_raw, s = crypto.random_bytes(16), crypto.random_bytes(32)
    oid = wire.b64u_encode(oid_raw)
    env.store.insert_offer(
        oid, crypto.secret_hash(TAG_OFFER, s), env.clock.now + OFFER_TTL_S, intended_user_id=user
    )
    dev = hmp_kit.Device(name=name)
    body = env.p2_body(dev, hmp_kit.Offer(oid, s))
    accepted = PairingService(env.store, env.identity, server.RateLimiter()).request(
        body, peer="127.0.0.1", now=env.clock.now
    )
    return accepted.pairing_id, accepted.device_sas


def test_setup_check_is_read_only_before_first_gateway_start(tmp_path: Path) -> None:
    kw = hmp_kit.identity_kwargs(tmp_path)
    out = io.StringIO()
    cli_env = cli.CliEnv(
        environ=kw["env"], stdout=out, stderr=io.StringIO(),
        compat=lambda: SUPPORTED, identity_kwargs=kw,
    )
    parser = argparse.ArgumentParser(prog="hermes hmp")
    cli.setup_parser(parser)

    assert cli.dispatch(parser.parse_args(["setup", "check"]), cli_env) == cli.EXIT_REFUSED
    assert "not initialized" in out.getvalue()
    assert not kw["hermes_root"].exists()
    assert not kw["binding_root"].exists()


def test_setup_check_reports_pinned_listener_without_private_labels(c: Cli) -> None:
    c.write_record(profiles=[("alpha", "private bot label")])
    before_store = c.env.store_path.read_bytes()
    before_binding = c.env.custody.binding_path.read_bytes()

    assert c.run("setup", "check") == cli.EXIT_OK
    assert "read compatibility: supported" in c.out
    assert "expected TLS identity" in c.out
    assert "Served bot count: 1" in c.out
    assert "private bot label" not in c.out
    assert "alpha" not in c.out
    assert c.env.store_path.read_bytes() == before_store
    assert c.env.custody.binding_path.read_bytes() == before_binding


def test_setup_check_fails_closed_on_stale_or_wrong_listener(c: Cli) -> None:
    c.write_record(profiles=[("alpha", "synthetic")])
    c.alive.clear()
    assert c.run("setup", "check") == cli.EXIT_REFUSED
    assert "unavailable or unsafe" in c.out

    c.alive.add(os.getpid())
    c.listener_live = False
    assert c.run("setup", "check") == cli.EXIT_REFUSED
    assert "TLS identity or readiness check failed" in c.out


def test_setup_check_requires_compatible_build_and_served_bot(c: Cli) -> None:
    c.write_record(profiles=[])
    assert c.run("setup", "check") == cli.EXIT_REFUSED
    assert "Served bot count: 0" in c.out

    c.write_record(profiles=[("alpha", "synthetic")])
    c.compat = CompatResult(CompatStatus.UNSUPPORTED, OtherWhy.HERMES_BUILD_UNSUPPORTED)
    assert c.run("setup", "check") == cli.EXIT_REFUSED
    assert "read compatibility: unsupported" in c.out


def test_health_check_fails_for_one_blocked_bot_without_disclosing_endpoint(c: Cli) -> None:
    rows = [
        ("alpha", "ready", "disabled", "disabled"),
        ("beta", "unavailable", "disabled", "disabled"),
    ]
    c.write_record(
        profiles=[("alpha", "Alpha"), ("beta", "Beta")],
        health_checked_at=c.env.clock.now,
        health=rows,
    )
    assert c.run("health", "check") == cli.EXIT_REFUSED
    assert 'Bot "alpha": send=ready' in c.out
    assert 'Bot "beta": send=unavailable' in c.out
    assert c.record_path().stat().st_mode & 0o777 == 0o600
    assert "API_SERVER_KEY" not in c.out
    assert "127.0.0.1" not in c.out


def test_health_check_accepts_disabled_channels_and_rejects_stale_snapshot(c: Cli) -> None:
    rows = [("alpha", "disabled", "disabled", "disabled")]
    c.write_record(
        profiles=[("alpha", "Alpha")], health_checked_at=c.env.clock.now, health=rows
    )
    assert c.run("health", "check") == cli.EXIT_OK
    c.write_record(
        profiles=[("alpha", "Alpha")],
        health_checked_at=c.env.clock.now - cli.HEALTH_MAX_AGE_S - 1,
        health=rows,
    )
    assert c.run("health", "check") == cli.EXIT_REFUSED
    assert "stale" in c.out


def test_health_check_rejects_incomplete_record_and_old_gateway(c: Cli) -> None:
    c.write_record(profiles=[("alpha", "Alpha")])
    assert c.run("health", "check") == cli.EXIT_REFUSED
    assert "unavailable or stale" in c.out
    c.write_record(
        profiles=[("alpha", "Alpha"), ("beta", "Beta")],
        health_checked_at=c.env.clock.now,
        health=[("alpha", "ready", "disabled", "disabled")],
    )
    assert c.run("health", "check") == cli.EXIT_REFUSED
    assert "unavailable or unsafe" in c.out


# --------------------------------------------------------------------------------------------------
# Mutation refusals (PR1-2, PR3-2) and ID-2
# --------------------------------------------------------------------------------------------------

MUTATING = [
    ("pair", "offer"),
    ("pair", "confirm", "pid", "--sas", "S", "--label", "f1-fixture-label-1"),
    ("pair", "deny", "pid"),
    ("devices", "revoke", "dev_x"),
    ("devices", "grant-controls", "dev_x"),
    ("devices", "deny-controls", "dev_x"),
    ("instance", "rotate-key"),
]


def test_mutating_set_matches_the_contract() -> None:
    assert {tuple(a[:2]) for a in MUTATING} == set(cli.MUTATING_COMMANDS)


@pytest.mark.parametrize("argv", MUTATING, ids=lambda a: "-".join(a[:2]))
def test_refused_without_a_tty(env: hmp_kit.Env, argv: tuple[str, ...]) -> None:
    c = Cli(env, tty=False)
    c.write_record()
    before = env.iid
    assert c.run(*argv) == cli.EXIT_REFUSED
    assert "interactive terminal" in c.err
    assert _count(env, "offers") == 0 and env.identity.still_current() and env.iid == before


@pytest.mark.parametrize("argv", MUTATING, ids=lambda a: "-".join(a[:2]))
def test_refused_in_a_hermes_session(c: Cli, argv: tuple[str, ...]) -> None:
    c.write_record()
    c.environ["HERMES_SESSION_ID"] = "x"
    assert c.run(*argv) == cli.EXIT_REFUSED
    assert "Hermes session" in c.err and _count(c.env, "offers") == 0


def test_read_only_commands_need_no_tty(env: hmp_kit.Env) -> None:
    c = Cli(env, tty=False)
    for argv in (("pair", "list"), ("devices", "list"), ("instance", "show"), ("compat",)):
        assert c.run(*argv) == cli.EXIT_OK, argv


def test_named_profile_is_refused(c: Cli, tmp_path: Path) -> None:
    """ID-2: a process whose Hermes home is a named profile gets no identity."""
    named = str(tmp_path / "hermes" / "profiles" / "work")
    c.environ["HERMES_HOME"] = named
    kw = c.env.kwargs
    c.env.kwargs = {**kw, "env": {"HERMES_HOME": named}}
    for argv in (("pair", "list"), ("pair", "offer"), ("instance", "show")):
        assert c.run(*argv) == cli.EXIT_ENVIRONMENT, argv
        assert "default profile" in c.err


# --------------------------------------------------------------------------------------------------
# pair offer (PR1-1..PR1-4)
# --------------------------------------------------------------------------------------------------


def test_offer_renders_only_a_qr_and_stores_only_the_hash(c: Cli) -> None:
    c.write_record()
    args = ("pair", "offer", "--label", "f1-fixture-label-1", "--no-wait")
    assert c.run(*args) == cli.EXIT_OK, c.err
    (payload,) = c.qr.rendered
    offer = wire.decode_qr_payload(payload, now=c.env.clock.now)
    assert offer.iid == c.env.iid
    assert offer.ep == (f"https://{TAILNET_HOST}:18920",)  # PR1-4: from the record only
    assert offer.exp == c.env.clock.now + OFFER_TTL_S
    row = c.env.store.get_offer(offer.oid)
    s = wire.b64u_decode(offer.s, length=32)
    assert bytes(row["secret_hash"]) == crypto.secret_hash(TAG_OFFER, s)
    assert row["state"] == "open" and row["intended_user_id"] is None
    # S and the payload never appear as text (PR1-2).
    assert "hmp1:" not in c.out + c.err and offer.s not in c.out + c.err


def test_offer_with_the_real_qrcode_library(c: Cli) -> None:
    pytest.importorskip("qrcode")
    c.write_record()
    env = c.cli_env()
    env.qr_factory = cli._default_qr_factory
    parser = argparse.ArgumentParser()
    cli.setup_parser(parser)
    argv = parser.parse_args(["pair", "offer", "--no-wait"])
    assert cli.dispatch(argv, env) == cli.EXIT_OK, c.err
    assert "hmp1:" not in c.out and len(c.out.splitlines()) > 20


# Hermes pins qrcode==7.4.2 for its core extras (dingtalk, feishu, messaging). Hermes PM locks every
# plugin's declared dependencies against the union of core extras, so the plugin's range must admit
# that exact version or `hermes plugins enable hmp` fails with a dependency conflict
# (reviews/dependencies.md, `qrcode`).
HERMES_CORE_QRCODE_PIN = "7.4.2"
PLUGIN_DIR = Path(cli.__file__).resolve().parent


def _manifest_python_dependencies() -> list[str]:
    """`python_dependencies` from plugin.yaml: the block-list form this manifest uses."""
    deps: list[str] = []
    in_block = False
    for line in (PLUGIN_DIR / "plugin.yaml").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[:1].isspace():
            in_block = line.split(":", 1)[0].strip() == "python_dependencies"
            continue
        if in_block and line.strip().startswith("- "):
            deps.append(line.strip()[2:].strip().strip("'\""))
    return deps


def test_qrcode_declaration_admits_the_hermes_core_pin() -> None:
    """reviews/dependencies.md, `qrcode` condition 3: no `[pil]`/`[png]` extras are requested
    anywhere the dependency is declared. Comparing specifier strings alone would let
    `qrcode[pil]>=7.4.2,<9` pass; `packaging.requirements.Requirement.extras` closes that gap."""
    requirements = pytest.importorskip("packaging.requirements")
    declared = [requirements.Requirement(d) for d in _manifest_python_dependencies()]
    assert [r.name for r in declared] == ["qrcode"]
    assert declared[0].specifier.contains(HERMES_CORE_QRCODE_PIN)
    assert declared[0].extras == set()  # plugin.yaml: no extras
    # server/pyproject.toml (development and tests) declares the same range as the manifest.
    import tomllib

    pyproject = tomllib.loads((PLUGIN_DIR.parent / "pyproject.toml").read_text(encoding="utf-8"))
    dev = [requirements.Requirement(d) for d in pyproject["project"]["dependencies"]]
    (pyproject_qrcode,) = [r for r in dev if r.name == "qrcode"]
    assert str(pyproject_qrcode.specifier) == str(declared[0].specifier)
    assert pyproject_qrcode.extras == set()  # pyproject.toml: no extras either


def test_real_qrcode_library_is_within_the_declared_range() -> None:
    """The real-library offer test above exercises whichever qrcode is installed; this pins that
    version to the declared range, so running the suite on the floor (7.4.2) is a real check."""
    pytest.importorskip("qrcode")
    requirements = pytest.importorskip("packaging.requirements")
    from importlib.metadata import version

    (declared,) = [requirements.Requirement(d) for d in _manifest_python_dependencies()]
    assert declared.specifier.contains(version("qrcode"))


_QR_FAMILY = ("qrcode", "png", "PIL")

# (review item 2c) Modes that can create, truncate or append to a file. Read-only modes ('r',
# 'rb', 'rt', ...) never contain any of these characters.
_WRITE_MODE_CHARS = frozenset("wax+")


def _qr_family(name: str) -> bool:
    return name.split(".", 1)[0] in _QR_FAMILY


def _forbid_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """(review item 2c) The offer path must never open any file for writing -- it renders to the
    given `out` stream only. Guard `builtins.open`/`io.open` (the same underlying function, and
    what `pathlib.Path.open`/`write_text`/`write_bytes` call into) so any write-capable mode raises,
    while reads pass through untouched."""
    real_open = builtins.open

    def guarded_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if isinstance(mode, str) and any(ch in _WRITE_MODE_CHARS for ch in mode):
            raise AssertionError(
                f"the offer path must never open a file for writing (file={file!r}, mode={mode!r})"
            )
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(io, "open", guarded_open)


def test_offer_never_exercises_png_or_pil(c: Cli, monkeypatch: pytest.MonkeyPatch) -> None:
    """reviews/dependencies.md, `qrcode` condition 3: the offer is rendered as terminal text only.
    `import qrcode` itself may load pypng (7.x: `qrcode.main` -> `qrcode.image.pure` -> `png`) and,
    when Pillow is installed, PIL (`qrcode.image.styles`), so the invariant is that nothing PNG- or
    PIL-based ever runs and nothing more is loaded to render, not that those modules are absent.
    The qrcode, png and PIL modules are dropped from `sys.modules` and restored afterwards, so a
    real import happens here whatever other tests imported first.

    The png/PIL stubs are installed by explicitly trying to import those modules ourselves, not
    only when qrcode's own import chain happens to have already loaded them -- otherwise a floor
    where the chain does not incidentally load one of them (e.g. Pillow present but qrcode 7.x's
    default chain never touching it) would leave that stub uninstalled. When a module is not
    importable at all, its absence from `sys.modules` is asserted directly instead. This also
    checks that the offer path never opens a file for writing, and that the `hmp1:` payload marker
    never appears on stderr either, not just stdout."""
    pytest.importorskip("qrcode")
    saved = {name: mod for name, mod in sys.modules.items() if _qr_family(name)}
    for name in saved:
        del sys.modules[name]
    calls: list[str] = []

    def stub(label: str) -> Any:
        def refuse(*_args: Any, **_kwargs: Any) -> Any:
            calls.append(label)
            raise AssertionError(f"{label} must never run in `hmp pair offer`")

        return refuse

    try:
        import qrcode  # noqa: F401 - a fresh import, under this test's control
        import qrcode.image.pure as pure

        for method in ("__init__", "new_image", "save"):
            monkeypatch.setattr(pure.PyPNGImage, method, stub(f"PyPNGImage.{method}"))

        try:
            import png as png_module
        except ImportError:
            png_module = None
        if png_module is not None:  # importable: stub it whether or not qrcode already loaded it
            monkeypatch.setattr(png_module, "Writer", stub("png.Writer"))
        else:  # not installed at all: it must never appear, not even transitively
            assert "png" not in sys.modules

        try:
            from PIL import Image as pil_image_module  # noqa: N813 - a module handle, not a class
        except ImportError:
            pil_image_module = None
        if pil_image_module is not None:
            monkeypatch.setattr(pil_image_module, "new", stub("PIL.Image.new"))
            monkeypatch.setattr(pil_image_module.Image, "save", stub("PIL.Image.Image.save"))
        else:
            assert "PIL" not in sys.modules and "PIL.Image" not in sys.modules

        loaded_before_offer = {name for name in sys.modules if _qr_family(name)}

        c.write_record()
        env = c.cli_env()
        env.qr_factory = cli._default_qr_factory
        parser = argparse.ArgumentParser()
        cli.setup_parser(parser)
        _forbid_writes(monkeypatch)
        argv = parser.parse_args(["pair", "offer", "--no-wait"])
        assert cli.dispatch(argv, env) == cli.EXIT_OK, c.err

        assert calls == []
        # Nothing was imported to render (`qrcode.image.pil`, a PIL or png module, ...).
        assert {name for name in sys.modules if _qr_family(name)} == loaded_before_offer
        assert "\x89PNG" not in c.out and "hmp1:" not in c.out and len(c.out.splitlines()) > 20
        assert "hmp1:" not in c.err  # the payload marker must be absent from stderr too
    finally:
        for name in [name for name in sys.modules if _qr_family(name)]:
            del sys.modules[name]
        sys.modules.update(saved)


def test_offer_refused_on_an_unsupported_build(c: Cli) -> None:
    c.write_record()
    c.compat = CompatResult(CompatStatus.UNSUPPORTED, OtherWhy.HERMES_READ_DEPENDENCY_MISSING)
    assert c.run("pair", "offer") == cli.EXIT_REFUSED
    assert "hermes_read_dependency_missing" in c.err
    assert _count(c.env, "offers") == 0 and c.qr.rendered == []


def test_offer_refused_without_a_qr_renderer(c: Cli) -> None:
    c.write_record()
    c.qr_missing = True
    assert c.run("pair", "offer") == cli.EXIT_REFUSED
    assert "qrcode" in c.err and _count(c.env, "offers") == 0


def test_offer_refused_for_a_loopback_listener(c: Cli) -> None:
    c.write_record(host="127.0.0.1")
    assert c.run("pair", "offer") == cli.EXIT_REFUSED
    assert "tailnet" in c.err and _count(c.env, "offers") == 0


def test_offer_for_an_intended_user(c: Cli) -> None:
    c.write_record()
    assert c.run("pair", "offer", "--user", "hmpu_" + "0" * 32) == cli.EXIT_REFUSED  # unknown
    assert c.run("pair", "offer", "--user", "bob") == cli.EXIT_REFUSED  # bad format
    user = "hmpu_" + "1" * 32
    c.env.store.insert_user(user, "f1-fixture-label-1", c.env.clock.now)
    assert c.run("pair", "offer", "--user", user, "--no-wait") == cli.EXIT_OK
    offer = wire.decode_qr_payload(c.qr.rendered[-1], now=None)
    assert c.env.store.get_offer(offer.oid)["intended_user_id"] == user


# --------------------------------------------------------------------------------------------------
# The runtime record (PR1-4; coordinator conditions)
# --------------------------------------------------------------------------------------------------


def test_record_is_0600_next_to_the_store_and_atomic(c: Cli) -> None:
    path = c.record_path()
    assert path.parent == server.store_path(c.env.custody.anchor_dir).parent
    c.write_record(port=1)
    c.write_record(port=2)  # replaced by rename, never edited in place
    assert (path.stat().st_mode & 0o777) == 0o600
    assert json.loads(path.read_text())["port"] == 2
    assert [p.name for p in path.parent.iterdir() if p.name.endswith(".tmp")] == []


def test_record_round_trips_profiles(c: Cli) -> None:
    """OD-F8 (2026-09-27): `profiles` round-trips through the listener record exactly."""
    c.write_record(profiles=[("default", "Default Bot"), ("netmin", "Net Admin")])
    record = cli.read_listener_record(
        c.record_path(), iid=c.env.iid, pid_alive=lambda pid: pid in c.alive
    )
    assert record.profiles == (("default", "Default Bot"), ("netmin", "Net Admin"))


def test_record_without_profiles_is_none_not_empty(c: Cli) -> None:
    """An older gateway's record (or one written with no bridge) never had this field: `None`,
    not an empty tuple, so the CLI can tell "nothing to offer" apart from "doesn't know how"."""
    c.write_record()
    record = cli.read_listener_record(
        c.record_path(), iid=c.env.iid, pid_alive=lambda pid: pid in c.alive
    )
    assert record.profiles is None


def test_record_with_malformed_profiles_is_refused(c: Cli) -> None:
    c.write_record(profiles=[("default", "Default Bot")])
    path = c.record_path()
    data = json.loads(path.read_text())
    data["profiles"] = [["default"]]  # missing the display name
    path.write_text(json.dumps(data))
    path.chmod(0o600)
    with pytest.raises(cli.ListenerRecordError):
        cli.read_listener_record(path, iid=c.env.iid, pid_alive=lambda pid: pid in c.alive)


def test_record_write_failure_leaves_no_temp_file(c: Cli, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_a: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        c.write_record()
    assert list(c.record_path().parent.glob("*.tmp")) == []
    assert not c.record_path().exists()


@pytest.mark.parametrize(
    "problem",
    [
        "missing",
        "mode",
        "symlink",
        "stale",
        "other_iid",
        "malformed",
        "no_nonce",
        "unsafe_dir",
        "not_live",
    ],
)
def test_cli_refuses_a_bad_record(c: Cli, problem: str) -> None:
    path = c.record_path()
    if problem != "missing":
        c.write_record()
    if problem == "mode":
        path.chmod(0o644)
    elif problem == "symlink":
        real = path.with_name("real.json")
        path.rename(real)
        path.symlink_to(real)
    elif problem == "stale":
        c.alive = set()
    elif problem == "other_iid":
        c.write_record(iid="a" * 52)
    elif problem == "malformed":
        path.write_text('{"format": 1, "host": "not-an-ip"}')
    elif problem == "no_nonce":  # SR-7: nonce is required, not merely optional
        path.write_text(
            json.dumps(
                {
                    "format": 1,
                    "host": TAILNET_HOST,
                    "port": 18920,
                    "iid": c.env.iid,
                    "pid": os.getpid(),
                }
            )
        )
    elif problem == "unsafe_dir":  # SR-7: the record directory itself must be safe
        path.parent.chmod(0o777)
    elif problem == "not_live":  # SR-7: the live liveness/identity check refuses too
        c.listener_live = False
    assert c.run("pair", "offer") == cli.EXIT_REFUSED
    assert _count(c.env, "offers") == 0 and c.qr.rendered == []
    if problem == "unsafe_dir":
        path.parent.chmod(0o700)  # leave the fixture directory in a sane state


def test_offer_refused_when_liveness_check_never_runs_for_other_refusals(c: Cli) -> None:
    """SR-7: the live check only matters once the local record has already passed every other
    check -- a record that is stale by pid must refuse for THAT reason, without ever needing (or
    reaching) the network round trip."""
    c.write_record()
    c.alive = set()  # stale by pid
    assert c.run("pair", "offer") == cli.EXIT_REFUSED
    assert c.listener_live_calls == []


def test_default_verify_listener_live_checks_pin_and_iid(
    adapter_module: types.ModuleType,  # noqa: F811
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SR-7: the production liveness check, against a REAL running listener: it must succeed for
    this instance's own `iid`, and refuse for any other -- the same failure mode a reused pid
    serving something else (or nothing) would produce. Run through `asyncio.to_thread`: the check
    itself is a blocking, synchronous TLS client call (the CLI is its own OS process in
    production, never sharing an event loop with the gateway it is calling out to), so calling it
    directly from this same test's event loop would starve the adapter's own listener of the loop
    time it needs to complete the TLS handshake it is being asked to answer."""
    env = hmp_kit.Env(tmp_path)
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": _free_port()}))
    path = cli.listener_record_path(env.custody.anchor_dir)

    async def main() -> None:
        assert await adapter.connect() is True
        record = cli.read_listener_record(path, iid=env.iid)
        assert record.nonce  # SR-7: a per-start nonce is always present
        assert await asyncio.to_thread(cli._default_verify_listener_live, record, env.iid) is True
        assert await asyncio.to_thread(cli._default_verify_listener_live, record, "z" * 52) is False
        await adapter.disconnect()
        # Nothing is listening anymore: a network failure also answers False, never raises.
        assert await asyncio.to_thread(cli._default_verify_listener_live, record, env.iid) is False

    asyncio.run(main())


def test_remove_record_leaves_another_processes_record(c: Cli) -> None:
    path = c.record_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"format": 1, "pid": os.getpid() + 100000}))
    cli.remove_listener_record(path)
    assert path.exists()
    c.write_record()
    cli.remove_listener_record(path)
    assert not path.exists()


def test_remove_record_skips_a_symlink(c: Cli) -> None:
    """SR-7: `remove_listener_record` opens with `O_NOFOLLOW` too, so it never follows a symlink
    planted at the record path into removing (or reading) an arbitrary target file."""
    path = c.record_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    real = path.with_name("real.json")
    real.write_text(json.dumps({"format": 1, "pid": os.getpid()}))
    path.symlink_to(real)
    cli.remove_listener_record(path)
    assert path.is_symlink() and real.exists()


def test_remove_record_skips_when_the_path_was_replaced_since_the_check(
    c: Cli, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SR-7 race safety: `remove_listener_record` reads the pid from an already-open descriptor,
    then re-`lstat`s the PATH right before unlinking. If a fresh writer's atomic `os.replace`
    lands in that narrow window -- simulated here by making the re-`lstat` itself observe a
    replaced file, exactly what a real race would produce -- the inode compare must fail and the
    removal must not go through."""
    path = c.record_path()
    c.write_record()  # this process's own record
    real_lstat = os.lstat
    replaced = {"done": False}

    def sneaky_lstat(target: Any, *a: Any, **k: Any) -> Any:
        if str(target) == str(path) and not replaced["done"]:
            replaced["done"] = True
            other = path.with_name(".other.tmp")
            other.write_text(json.dumps({"format": 1, "pid": os.getpid() + 555}))
            os.chmod(other, 0o600)
            os.replace(other, path)  # a fresh writer's own atomic PR1-4 write
        return real_lstat(target, *a, **k)

    monkeypatch.setattr(os, "lstat", sneaky_lstat)
    cli.remove_listener_record(path)
    # The record present now is the "fresh writer's own", untouched by this call.
    assert json.loads(path.read_text())["pid"] == os.getpid() + 555


def test_endpoint_for() -> None:
    assert cli.endpoint_for(TAILNET_HOST, 443) == f"https://{TAILNET_HOST}:443"
    assert cli.endpoint_for("fd7a\x3a115c:a1e0:0:0:0:0:1", 8) == "https://[fd7a\x3a115c:a1e0::1]:8"


def test_adapter_writes_the_bound_address_and_removes_it(
    adapter_module: types.ModuleType,  # noqa: F811
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = hmp_kit.Env(tmp_path)
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    port = _free_port()
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": port}))
    path = cli.listener_record_path(env.custody.anchor_dir)

    async def main() -> None:
        assert await adapter.connect() is True
        bound = adapter._server.bound
        record = cli.read_listener_record(path, iid=env.iid)
        assert (record.host, record.port) == bound == ("127.0.0.1", port)
        assert cli.endpoint_for(record.host, record.port) == f"https://127.0.0.1:{port}"
        assert (path.stat().st_mode & 0o777) == 0o600
        await adapter.disconnect()
        assert not path.exists()

    asyncio.run(main())


def test_record_removed_when_the_key_changes(
    adapter_module: types.ModuleType,  # noqa: F811
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from hmp_plugin import identity

    env = hmp_kit.Env(tmp_path)
    monkeypatch.setattr(adapter_module, "open_components", lambda _adapter: env.ctx)
    adapter = adapter_module.HmpAdapter(_Config({"bind": "127.0.0.1", "port": _free_port()}))
    path = cli.listener_record_path(env.custody.anchor_dir)

    async def main() -> None:
        assert await adapter.connect() is True
        srv = adapter._server
        assert path.exists()
        new = identity.rotate_key(env.store, **env.kwargs)
        await asyncio.wait_for(srv.closed.wait(), timeout=10)
        await asyncio.sleep(0)
        assert not path.exists()
        with pytest.raises(cli.ListenerRecordError):
            cli.read_listener_record(path, iid=new.iid)

    asyncio.run(main())


# --------------------------------------------------------------------------------------------------
# pair list (PR3-1)
# --------------------------------------------------------------------------------------------------


def test_list_shows_only_the_first_sas_group(c: Cli) -> None:
    pairing_id, sas = _pending(c.env, name="f1-fixture-device-1")
    assert c.run("pair", "list") == cli.EXIT_OK
    first, rest = sas.split("-", 1)
    assert pairing_id in c.out and first in c.out
    assert rest not in c.out and sas not in c.out
    assert '"f1-fixture-device-1" (unverified' in c.out


# --------------------------------------------------------------------------------------------------
# pair confirm / deny (PR3-2..PR3-4)
# --------------------------------------------------------------------------------------------------


def _device_state(env: hmp_kit.Env, pairing_id: str) -> str | None:
    from hmp_plugin.pairing import device_id_for_pairing

    row = env.store.get_device(device_id_for_pairing(pairing_id))
    return None if row is None else str(row["state"])


def test_confirm_new_user(c: Cli) -> None:
    pairing_id, sas = _pending(c.env)
    typed = " ".join(sas.lower().split("-"))  # spacing and case do not matter
    assert c.confirm(pairing_id, "--sas", typed, "--label", "f1-fixture-label-1") == 0
    assert _device_state(c.env, pairing_id) == "ACTIVE"
    assert c.env.store.get_pairing(pairing_id)["state"] == "confirmed"
    assert _count(c.env, "users") == 1


def test_three_sas_mismatches_deny(c: Cli) -> None:
    pairing_id, sas = _pending(c.env)
    wrong = "AAAAA-AAAAA-AAAAA-AAAAA"
    assert wrong != sas
    for n in range(1, SAS_MAX_MISMATCHES + 1):
        assert c.confirm(pairing_id, "--sas", wrong, "--label", "f1-fixture-label-1") == 1
        assert sas not in c.out + c.err  # the expected SAS is never printed
        if n < SAS_MAX_MISMATCHES:
            assert f"{n} of {SAS_MAX_MISMATCHES}" in c.err
    assert "denied" in c.err
    assert c.env.store.get_pairing(pairing_id)["state"] == "denied"
    # Even the right SAS cannot confirm it now.
    assert c.confirm(pairing_id, "--sas", sas, "--label", "f1-fixture-label-1") == 1
    assert _device_state(c.env, pairing_id) is None and _count(c.env, "users") == 0


def test_sas_mismatches_survive_a_restart(c: Cli) -> None:
    pairing_id, _sas = _pending(c.env)
    for _ in range(SAS_MAX_MISMATCHES - 1):
        c.confirm(pairing_id, "--sas", "AAAAA-AAAAA-AAAAA-AAAAA", "--label", "f1-fixture-label-1")
    c.env.restart()
    c.confirm(pairing_id, "--sas", "AAAAA-AAAAA-AAAAA-AAAAA", "--label", "f1-fixture-label-1")
    assert c.env.store.get_pairing(pairing_id)["state"] == "denied"


def test_confirm_new_user_cleans_up_orphan_row_on_any_failure(
    c: Cli, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SR-8: cleanup of the freshly-minted `hmpu_` row must not be limited to the `LookupError`
    ("no longer pending") case -- any other failure while attaching the device must not leave an
    orphan user row either."""
    from hmp_plugin import pairing as pairing_module

    pairing_id, sas = _pending(c.env)

    def boom(*_a: Any, **_k: Any) -> str:
        raise RuntimeError("device insert exploded")

    monkeypatch.setattr(pairing_module, "confirm_pairing", boom)
    with pytest.raises(RuntimeError):
        c.confirm(pairing_id, "--sas", sas, "--label", "f1-fixture-label-1")
    assert _count(c.env, "users") == 0


def test_sas_mismatch_increment_and_deny_are_one_transaction(
    monkeypatch: pytest.MonkeyPatch, c: Cli
) -> None:
    """SR-2: the increment and the conditional deny must commit together. Simulate a crash right
    after the third increment committed but before the (old, separate) deny call ran, by writing
    that exact state directly, then confirm with the CORRECT SAS and require it still denies
    rather than activating a device past the limit."""
    pairing_id, sas = _pending(c.env)
    with c.env.store.transaction() as conn:
        conn.execute(
            "UPDATE pairings SET sas_mismatches = ? WHERE pairing_id = ?",
            (SAS_MAX_MISMATCHES, pairing_id),
        )
    assert c.env.store.get_pairing(pairing_id)["state"] == "awaiting_operator"  # still pending
    assert c.confirm(pairing_id, "--sas", sas, "--label", "f1-fixture-label-1") == 1
    assert "denied" in c.err
    assert c.env.store.get_pairing(pairing_id)["state"] == "denied"
    assert _device_state(c.env, pairing_id) is None


def test_sas_compare_is_constant_time(monkeypatch: pytest.MonkeyPatch, c: Cli) -> None:
    calls: list[tuple[Any, Any]] = []
    real = crypto.constant_time_equal

    def spy(a: Any, b: Any) -> bool:
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr(crypto, "constant_time_equal", spy)
    pairing_id, sas = _pending(c.env)
    c.confirm(pairing_id, "--sas", sas, "--label", "f1-fixture-label-1")
    flat = sas.replace("-", "")
    assert (flat, flat) in calls


@pytest.mark.parametrize("label", ["", "x" * 65, "bad\x1b[31m", "zero​width", "   "])
def test_confirm_refuses_bad_labels(c: Cli, label: str) -> None:
    pairing_id, sas = _pending(c.env)
    assert c.confirm(pairing_id, "--sas", sas, "--label", label) == 1
    assert _device_state(c.env, pairing_id) is None


def test_confirm_refuses_an_expired_pairing(c: Cli) -> None:
    pairing_id, sas = _pending(c.env)
    c.env.clock.now += 10_000
    assert c.confirm(pairing_id, "--sas", sas, "--label", "f1-fixture-label-1") == 1
    assert _count(c.env, "users") == 0


def test_confirm_existing_user_rules(c: Cli) -> None:
    """PR3-3: format, existence, the offer's intended user, the share preview, --yes-share."""
    user = "hmpu_" + "1" * 32
    c.env.store.insert_user(user, "f1-fixture-label-0", c.env.clock.now)
    c.env.store.set_chat(user, "alpha", "default", "c_" + "2" * 32)
    c.environ["GATEWAY_ALLOWED_USERS"] = f"someone,{user}"
    label = ("--label", "f1-fixture-label-1")

    pairing_id, sas = _pending(c.env)  # an offer with no intended user
    assert c.confirm(pairing_id, "--sas", sas, *label, "--user", user, "--yes-share") == 1
    assert "does not match" in c.err

    pairing_id, sas = _pending(c.env, user=user)
    assert c.confirm(pairing_id, "--sas", sas, *label, "--user", "hmpu_bad") == 1
    assert c.confirm(pairing_id, "--sas", sas, *label) == 1  # --new-user default
    assert "pass --user" in c.err
    assert c.confirm(pairing_id, "--sas", sas, *label, "--user", user) == 1
    assert "--yes-share" in c.err
    assert "requested access to bot alpha" in c.out and "INSTANCE-WIDE" in c.out
    assert "NOT CHECKED" in c.out and "platforms.hmp.extra.allow_from" in c.out
    assert _device_state(c.env, pairing_id) is None
    assert c.confirm(pairing_id, "--sas", sas, *label, "--user", user, "--yes-share") == 0
    assert _device_state(c.env, pairing_id) == "ACTIVE" and _count(c.env, "users") == 1


def test_env_allowlist_json_list_literal_form(c: Cli) -> None:
    """SR-1: `hermes config set` writes a JSON list literal (e.g. `'["hmpu_…"]'`), which Hermes's
    `_coerce_allow_set` parses as a list, not a single comma-free member. A naive comma split
    finds no member in such a value and would under-report the instance-wide grant."""
    user = "hmpu_" + "5" * 32
    c.env.store.insert_user(user, "f1-fixture-label-0", c.env.clock.now)
    c.environ["GATEWAY_ALLOWED_USERS"] = f'["someone", "{user}"]'
    label = ("--label", "f1-fixture-label-1")
    pairing_id, sas = _pending(c.env, user=user)
    assert c.confirm(pairing_id, "--sas", sas, *label, "--user", user) == 1
    assert "INSTANCE-WIDE" in c.out
    # A malformed / unrelated JSON-shaped value falls back to the comma-split path, never crashes.
    c.environ["GATEWAY_ALLOWED_USERS"] = "[not valid json"
    pairing_id2, sas2 = _pending(c.env, user=user)
    assert c.confirm(pairing_id2, "--sas", sas2, *label, "--user", user) == 1
    assert "INSTANCE-WIDE" not in c.out


def test_revoke_last_device_always_shows_the_not_checked_note(c: Cli) -> None:
    """SR-1: even with no HMP-requested profiles and no env allowlist hit, the operator must
    never see silence where 'nothing to disclose' and 'not checked' look the same."""
    pairing_id, sas = _pending(c.env)
    c.confirm(pairing_id, "--sas", sas, "--label", "f1-fixture-label-1")
    device = _device_id(pairing_id)
    assert c.run("devices", "revoke", device) == 0
    assert "NOT CHECKED" in c.out and "platforms.hmp.extra.allow_from" in c.out


def test_deny(c: Cli) -> None:
    pairing_id, _ = _pending(c.env)
    assert c.run("pair", "deny", "--", pairing_id) == 0
    assert c.env.store.get_pairing(pairing_id)["state"] == "denied"
    assert c.run("pair", "deny", "--", pairing_id) == 1


# --------------------------------------------------------------------------------------------------
# devices, instance, compat
# --------------------------------------------------------------------------------------------------


def test_devices_list_and_revoke_last_device_hint(c: Cli) -> None:
    pairing_id, sas = _pending(c.env)
    c.confirm(pairing_id, "--sas", sas, "--label", "f1-fixture-label-1")
    device = _device_id(pairing_id)
    user = c.env.store.get_device(device)["user_id"]
    c.env.store.set_chat(user, "alpha", "default", "c_" + "3" * 32)
    assert c.run("devices", "list") == 0 and device in c.out and "ACTIVE" in c.out
    assert c.run("devices", "revoke", device) == 0
    assert c.env.store.get_device(device)["state"] == "REVOKED"
    assert f"hermes -p alpha pairing revoke hmp {user}" in c.out
    assert c.run("devices", "revoke", "dev_missing") == 1


def test_host_can_change_owner_controls_for_one_active_device(c: Cli) -> None:
    pairing_id, sas = _pending(c.env)
    assert c.confirm(pairing_id, "--sas", sas, "--label", "f1-fixture-label-1") == 0
    device = _device_id(pairing_id)
    assert c.env.store.owner_controls_decision(device) is False  # EOF defaults to no grant
    assert c.run("devices", "grant-controls", device) == 0
    assert c.env.store.owner_controls_decision(device) is True
    assert c.run("devices", "deny-controls", device) == 0
    assert c.env.store.owner_controls_decision(device) is False
    assert c.run("devices", "revoke", device) == 0
    assert c.run("devices", "grant-controls", device) == 1
    assert c.env.store.owner_controls_decision(device) is False


def _device_id(pairing_id: str) -> str:
    from hmp_plugin.pairing import device_id_for_pairing

    return device_id_for_pairing(pairing_id)


def test_instance_show_prints_no_secret(c: Cli) -> None:
    assert c.run("instance", "show") == 0
    assert c.env.iid in c.out
    key_pem = c.env.custody.key_path.read_text()
    assert "PRIVATE" not in c.out and key_pem.splitlines()[1] not in c.out
    assert "not available" in c.out  # no listener record
    c.write_record()
    assert c.run("instance", "show") == 0 and f"https://{TAILNET_HOST}:18920" in c.out


def test_rotate_key(c: Cli) -> None:
    pairing_id, sas = _pending(c.env)
    c.confirm(pairing_id, "--sas", sas, "--label", "f1-fixture-label-1")
    before = c.env.iid
    assert c.run("instance", "rotate-key") == 0
    assert not c.env.identity.still_current()
    assert c.env.store.get_device(_device_id(pairing_id))["state"] == "REVOKED"
    assert "New instance fingerprint" in c.out and before not in c.out


def test_rotate_key_checks_currency_under_the_custody_lock(
    c: Cli, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SR-9: `instance rotate-key` must ask `identity.rotate_key` to check currency itself
    (`require_current=True`), under its own custody lock, rather than the CLI doing a separate,
    unlocked check first."""
    calls: list[dict[str, Any]] = []
    real_rotate = identity.rotate_key

    def spy(store: Any, **kw: Any) -> Any:
        calls.append(kw)
        return real_rotate(store, **kw)

    monkeypatch.setattr(identity, "rotate_key", spy)
    assert c.run("instance", "rotate-key") == 0
    assert calls and calls[0]["require_current"] is True


def test_compat_output(c: Cli) -> None:
    assert c.run("compat") == 0
    assert "supported" in c.out and FP in c.out and "stock-base" in c.out and "passed" in c.out
    assert "Guarded send qualification:" in c.out
    c.compat = CompatResult(CompatStatus.UNSUPPORTED, OtherWhy.HERMES_BUILD_UNSUPPORTED)
    assert c.run("compat") == 0
    assert "hermes_build_unsupported" in c.out and "unidentifiable" in c.out
    assert "not run" in c.out


def test_no_subcommand_is_usage(c: Cli) -> None:
    assert c.run() == cli.EXIT_ENVIRONMENT


# --------------------------------------------------------------------------------------------------
# The CLI never creates or re-keys the identity (load only; coordinator ruling)
# --------------------------------------------------------------------------------------------------


def _disk(root: Path) -> dict[str, tuple[int, int, int]]:
    """Every path under `root` with its mode, size and mtime. The SQLite files are compared by
    content instead (opening a WAL database touches its side files)."""
    out = {}
    for p in sorted(root.rglob("*")):
        if p.name.startswith(server.STORE_FILENAME):
            continue
        st = p.lstat()
        out[str(p.relative_to(root))] = (st.st_mode, st.st_size, st.st_mtime_ns)
    return out


def _store_dump(env: hmp_kit.Env) -> dict[str, list[tuple[Any, ...]]]:
    tables = ("meta", "offers", "pairings", "users", "devices", "token_families", "audit")
    with env.store.transaction() as conn:
        return {
            t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY rowid")]  # noqa: S608
            for t in tables
        }


def _mismatch(c: Cli, tmp_path: Path, kind: str) -> None:
    kw = dict(c.env.kwargs)
    if kind == "host":
        kw["host_id"] = lambda: identity.HostId("test-source", "synthetic-host-b")
    elif kind == "clone":  # the same home, but no binding for it here (a copied home)
        kw["binding_root"] = tmp_path / "other-state" / "hermes-hmp"
    elif kind == "copied_root":  # the whole Hermes root copied elsewhere, store included
        copy = tmp_path / "hermes-copy"
        shutil.copytree(kw["hermes_root"], copy)
        kw["hermes_root"] = copy
        kw["env"] = {"HERMES_HOME": str(copy)}
    elif kind == "fresh_root":  # a root where the gateway never ran
        fresh = tmp_path / "hermes-fresh"
        fresh.mkdir()
        kw["hermes_root"] = fresh
        kw["env"] = {"HERMES_HOME": str(fresh)}
    c.env.kwargs = kw
    c.environ = dict(kw["env"])


@pytest.mark.parametrize("kind", ["host", "clone", "copied_root", "fresh_root"])
@pytest.mark.parametrize(
    "argv",
    [("pair", "offer"), ("instance", "rotate-key"), ("instance", "show")],
    ids=lambda a: "-".join(a),
)
def test_cli_in_another_environment_changes_nothing(
    c: Cli, tmp_path: Path, kind: str, argv: tuple[str, ...]
) -> None:
    c.write_record()  # a live listener for the real identity
    iid = c.env.iid
    _mismatch(c, tmp_path, kind)
    disk, store = _disk(tmp_path), _store_dump(c.env)
    assert c.run(*argv) == cli.EXIT_ENVIRONMENT
    assert "start the Hermes gateway with HMP once, then retry" in c.err
    assert _disk(tmp_path) == disk and _store_dump(c.env) == store
    assert c.env.identity.still_current() and c.env.identity.iid == iid
    assert c.qr.rendered == []


def test_load_existing_is_load_only(env: hmp_kit.Env, tmp_path: Path) -> None:
    kw = {k: env.kwargs[k] for k in ("env", "hermes_root", "binding_root", "host_id")}
    env.custody.key_path.chmod(0o400)  # `load_or_create` would tighten this; load-only must not
    env.custody.k_grace_path.unlink()  # and must not re-create it
    disk, store = _disk(tmp_path), _store_dump(env)
    loaded = identity.load_existing(env.store, **kw)
    assert loaded.iid == env.iid
    assert _disk(tmp_path) == disk and _store_dump(env) == store


def test_load_existing_refuses_a_first_run(tmp_path: Path) -> None:
    from hmp_plugin.store import Store

    root, state = tmp_path / "hermes", tmp_path / "state"
    root.mkdir()
    store = Store(tmp_path / "s.sqlite3")
    store.migrate()
    with pytest.raises(identity.IdentityNotReadyError):
        identity.load_existing(
            store,
            env={"HERMES_HOME": str(root)},
            hermes_root=root,
            binding_root=state,
            host_id=lambda: hmp_kit.HOST,
        )
    assert list(root.iterdir()) == [] and not state.exists()
    assert store.revocation_epoch() == 0


def test_list_prints_the_exact_dash_safe_commands(c: Cli) -> None:
    pairing_id, _sas = _pending(c.env)
    assert c.run("pair", "list") == cli.EXIT_OK
    assert f"hermes hmp pair confirm --sas <full SAS> --label <label> -- {pairing_id}" in c.out
    assert f"hermes hmp pair deny -- {pairing_id}" in c.out


def test_identity_precheck_with_the_gateway_stopped(c: Cli, tmp_path: Path) -> None:
    """No WAL file: the read-only precheck uses an immutable read and creates no file."""
    c.env.store.close()
    store_path = server.store_path(c.env.custody.anchor_dir)
    assert not store_path.with_name(store_path.name + "-wal").exists()
    epoch = cli._ReadOnlyEpoch(store_path).revocation_epoch()
    assert epoch == c.env.identity._binding.revocation_epoch
    assert sorted(p.name for p in store_path.parent.iterdir() if p.name.startswith("hmp.")) == [
        store_path.name
    ]
    c.env.kwargs = {**c.env.kwargs, "host_id": lambda: identity.HostId("t", "other-host")}
    before = _disk(tmp_path)
    assert c.run("instance", "show") == cli.EXIT_ENVIRONMENT
    assert _disk(tmp_path) == before
    assert not store_path.with_name(store_path.name + "-wal").exists()
