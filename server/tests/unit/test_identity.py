"""T022: instance identity custody (ID-2), host binding (HMP1-HOST), clone and backup detection,
rotation (PR7-2, PR7-6) and `k_grace` custody (research R16, CS-13).

Every test uses isolated temporary homes and a synthetic host id; nothing touches a real Hermes
home or reads the real host identifier except `test_detect_host_id_shape`, which asserts the
shape only and never prints the value.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import struct
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from hmp_plugin import crypto, identity
from hmp_plugin.identity import (
    Binding,
    ChangeReason,
    CustodyError,
    HostId,
    HostIdUnavailableError,
    IdentityError,
    NamedProfileError,
)

HOST_A = HostId("test-source", "synthetic-host-a")
HOST_B = HostId("test-source", "synthetic-host-b")


@dataclass
class FakeStore:
    """The `IdentityStore` contract: one call revokes, expires and bumps the epoch together."""

    epoch: int = 0
    devices: dict[str, str] = field(default_factory=dict)
    offers: dict[str, str] = field(default_factory=dict)
    pairings: dict[str, str] = field(default_factory=dict)
    calls: list[int] = field(default_factory=list)
    key_iid_at_call: list[str | None] = field(default_factory=list)
    key_path: Path | None = None
    fail_next: bool = False

    def revocation_epoch(self) -> int:
        return self.epoch

    def revoke_all_for_identity_change(self, now: int) -> int:
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("simulated crash inside the store transaction")
        self.calls.append(now)
        iid = None
        if self.key_path is not None:
            key = identity._read_key(self.key_path)
            iid = identity._iid_of(key) if key is not None else None
        self.key_iid_at_call.append(iid)
        self.devices = dict.fromkeys(self.devices, "REVOKED")
        self.offers = {k: ("expired" if v == "open" else v) for k, v in self.offers.items()}
        self.pairings = {k: ("expired" if v == "pending" else v) for k, v in self.pairings.items()}
        self.epoch += 1
        return self.epoch


@dataclass
class Host:
    """One isolated Hermes root plus a binding root, standing in for a machine."""

    root: Path
    binding_root: Path
    host: HostId = HOST_A

    def kwargs(self, **extra: object) -> dict[str, object]:
        env = {"HERMES_HOME": str(self.root)}
        return {
            "env": env,
            "hermes_root": self.root,
            "binding_root": self.binding_root,
            "host_id": lambda: self.host,
            "now": 1_800_000_000,
            **extra,
        }


def _store_for(h: Host) -> FakeStore:
    store = FakeStore(key_path=h.root.joinpath(*identity.PLUGIN_DATA_PARTS, identity.KEY_FILENAME))
    store.devices = {"dev_1": "ACTIVE", "dev_2": "PENDING"}
    store.offers = {"o1": "open", "o2": "claimed"}
    store.pairings = {"p1": "pending", "p2": "done"}
    return store


@pytest.fixture
def host(tmp_path: Path) -> Host:
    root = tmp_path / "hermes"
    (root / "profiles").mkdir(parents=True)
    return Host(root=root, binding_root=tmp_path / "state" / "hermes-hmp")


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _inside(child: Path, parent: Path) -> bool:
    c, p = Path(os.path.realpath(child)), Path(os.path.realpath(parent))
    return c == p or p in c.parents


# --------------------------------------------------------------------------------------------------
# First run, reload, file modes, locations
# --------------------------------------------------------------------------------------------------


def test_first_run_creates_custody_files(host: Host) -> None:
    store = _store_for(host)
    ident = identity.load_or_create(store, **host.kwargs())
    c = ident.custody
    assert ident.change_reason is ChangeReason.FIRST_RUN
    assert len(store.calls) == 1 and store.epoch == 1
    assert _mode(c.key_path) == 0o600 and _mode(c.binding_path) == 0o600
    assert _mode(c.k_grace_path) == 0o600
    assert _mode(c.anchor_dir) == 0o700 and _mode(c.binding_dir) == 0o700
    assert _inside(c.key_path, host.root / "plugin-data" / "hmp")
    # The binding and k_grace are outside every Hermes home (ID-2, R16).
    for path in (c.binding_path, c.k_grace_path):
        assert not _inside(path, host.root)
    # iid is the fingerprint of the certificate's SPKI (TR-1, TR-2).
    assert crypto.spki_fingerprint(crypto.certificate_spki(ident.certificate_der())) == ident.iid
    assert len(ident.k_grace()) == 32
    binding = Binding.parse(c.binding_path.read_bytes())
    assert binding == Binding(ident.iid, identity.host_hash(HOST_A), 1)
    assert HOST_A.value.encode() not in c.binding_path.read_bytes()  # only the hash is stored


def test_reload_keeps_identity_and_revokes_nothing(host: Host) -> None:
    store = _store_for(host)
    first = identity.load_or_create(store, **host.kwargs())
    k1 = first.k_grace()
    second = identity.load_or_create(store, **host.kwargs())
    assert second.change_reason is ChangeReason.NONE
    assert second.iid == first.iid and second.k_grace() == k1
    assert len(store.calls) == 1
    assert first.still_current() and second.still_current()


def test_loose_key_mode_is_tightened(host: Host) -> None:
    store = _store_for(host)
    ident = identity.load_or_create(store, **host.kwargs())
    os.chmod(ident.custody.key_path, 0o644)
    again = identity.load_or_create(store, **host.kwargs())
    assert again.iid == ident.iid
    assert _mode(ident.custody.key_path) == 0o600


def test_repr_reveals_no_secrets(host: Host) -> None:
    ident = identity.load_or_create(_store_for(host), **host.kwargs())
    text = repr(ident) + repr(HOST_A)
    assert ident.iid not in text and HOST_A.value not in text
    assert ident.k_grace().hex() not in text


def test_production_anchor_uses_hermes_constants(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    """IR-6: with no override, the root comes from `hermes_constants.get_default_hermes_root`."""
    fake = types.ModuleType("hermes_constants")
    fake.get_default_hermes_root = lambda: host.root  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_constants", fake)
    kwargs = host.kwargs()
    del kwargs["hermes_root"]
    ident = identity.load_or_create(_store_for(host), **kwargs)
    assert _inside(ident.custody.key_path, host.root)


# --------------------------------------------------------------------------------------------------
# Host binding
# --------------------------------------------------------------------------------------------------


def test_host_change_revokes_all_and_replaces_key(host: Host) -> None:
    store = _store_for(host)
    old = identity.load_or_create(store, **host.kwargs())
    k_old = old.k_grace()
    host.host = HOST_B
    new = identity.load_or_create(store, **host.kwargs())
    assert new.change_reason is ChangeReason.HOST_CHANGED
    assert new.iid != old.iid and new.k_grace() != k_old
    assert len(store.calls) == 2 and set(store.devices.values()) == {"REVOKED"}
    assert not old.still_current()


def test_host_id_unavailable_fails_closed_and_writes_nothing(host: Host) -> None:
    store = _store_for(host)

    def unavailable() -> HostId:
        raise HostIdUnavailableError("none")

    with pytest.raises(HostIdUnavailableError):
        identity.load_or_create(store, **host.kwargs(host_id=unavailable))
    assert not (host.root / "plugin-data").exists() and not host.binding_root.exists()
    assert store.calls == []


@pytest.mark.parametrize("where", ["inside_root", "equal_root", "contains_root", "relative"])
def test_binding_location_must_be_outside_every_hermes_home(host: Host, where: str) -> None:
    bad = {
        "inside_root": host.root / "profiles" / "x" / "state",
        "equal_root": host.root,
        "contains_root": host.root.parent,
        "relative": Path("relative/state"),
    }[where]
    store = _store_for(host)
    with pytest.raises(CustodyError):
        identity.load_or_create(store, **host.kwargs(binding_root=bad))
    assert store.calls == []


def test_hmp1_host_encoding_is_pinned() -> None:
    """The HMP1-HOST input (T015 EVIDENCE_GAP-HMP1-HOST-INPUT, closed by research R17):
    `u32be(len source) || source || u32be(len value) || value`, hashed with the tag."""
    host = HostId("linux-machine-id", "0123456789abcdef0123456789abcdef")
    expected_input = (
        struct.pack(">I", 16) + b"linux-machine-id" + struct.pack(">I", 32) + host.value.encode()
    )
    assert identity.host_id_input(host) == expected_input
    assert identity.host_hash(host) == hashlib.sha256(b"HMP1-HOST" + expected_input).hexdigest()
    # Known answer, so a change to the encoding cannot pass silently.
    assert (
        identity.host_hash(host)
        == "55196425723d2277bad800b562aa8d9a5049e25ece2e18b81aeab27d3bbd83be"
    )
    # A different source with the same value is a different host.
    assert identity.host_hash(HostId("other", host.value)) != identity.host_hash(host)


def test_linux_machine_id_parsing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    good, zero, bad = tmp_path / "good", tmp_path / "zero", tmp_path / "bad"
    good.write_text("0123456789ABCDEF0123456789ABCDEF\n", encoding="ascii")
    zero.write_text("0" * 32 + "\n", encoding="ascii")
    bad.write_text("not-a-machine-id\n", encoding="ascii")
    monkeypatch.setattr(identity, "_LINUX_MACHINE_ID_FILES", (bad, zero, good))
    got = identity._linux_host_id()
    assert got == HostId(identity.HOST_SOURCE_LINUX, "0123456789abcdef0123456789abcdef")
    monkeypatch.setattr(identity, "_LINUX_MACHINE_ID_FILES", (bad, zero, tmp_path / "absent"))
    assert identity._linux_host_id() is None


def test_darwin_ioreg_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    synthetic = "00000000-1111-2222-3333-444444444444"

    class Done:
        stdout = f'  "IOPlatformUUID" = "{synthetic.upper()}"\n'

    monkeypatch.setattr(identity.subprocess, "run", lambda *a, **k: Done())
    assert identity._darwin_host_id() == HostId(identity.HOST_SOURCE_DARWIN, synthetic)

    def boom(*a: object, **k: object) -> None:
        raise OSError("no ioreg")

    monkeypatch.setattr(identity.subprocess, "run", boom)
    assert identity._darwin_host_id() is None


def test_detect_host_id_shape() -> None:
    """On this machine: either a well-formed id from the expected source, or fail closed."""
    try:
        host = identity.detect_host_id()
    except HostIdUnavailableError:
        pytest.skip("no OS host identifier on this runner (fails closed, as intended)")
    expected = {"darwin": identity.HOST_SOURCE_DARWIN, "win32": identity.HOST_SOURCE_WINDOWS}
    assert host.source == expected.get(sys.platform, identity.HOST_SOURCE_LINUX)
    assert host.value == host.value.strip().lower() and host.value


def test_default_binding_root(tmp_path: Path) -> None:
    if sys.platform == "win32":  # pragma: no cover
        pytest.skip("POSIX layout")
    xdg = tmp_path / "xdg"
    assert identity.default_binding_root({"XDG_STATE_HOME": str(xdg)}) == xdg / "hermes-hmp"
    fallback = Path.home() / ".local" / "state" / "hermes-hmp"
    assert identity.default_binding_root({"XDG_STATE_HOME": "relative"}) == fallback
    assert identity.default_binding_root({}) == fallback


# --------------------------------------------------------------------------------------------------
# Clone and backup
# --------------------------------------------------------------------------------------------------


def test_profile_clone_all_never_serves_the_cloned_key(host: Host) -> None:
    """`hermes profile create --clone-all` copies plugin data into a named profile. HMP refuses to
    run there at all (ID-2), so the copied key is never loaded and no second identity exists."""
    store = _store_for(host)
    original = identity.load_or_create(store, **host.kwargs())
    clone = host.root / "profiles" / "work"
    shutil.copytree(host.root / "plugin-data", clone / "plugin-data")
    before = sorted(p.name for p in host.binding_root.iterdir())
    env = {"HERMES_HOME": str(clone)}
    for fn in (identity.load_or_create, identity.rotate_key):
        with pytest.raises(NamedProfileError):
            fn(store, **host.kwargs(env=env))
    assert sorted(p.name for p in host.binding_root.iterdir()) == before
    assert len(store.calls) == 1
    assert original.still_current()


def test_named_profile_refused_before_any_write(host: Host) -> None:
    store = _store_for(host)
    env = {"HERMES_HOME": str(host.root / "profiles" / "work")}
    with pytest.raises(NamedProfileError):
        identity.load_or_create(store, **host.kwargs(env=env))
    assert not (host.root / "plugin-data").exists() and not host.binding_root.exists()
    assert store.calls == []


def test_home_copied_to_another_path_is_a_clone(host: Host, tmp_path: Path) -> None:
    store = _store_for(host)
    original = identity.load_or_create(store, **host.kwargs())
    copy = Host(root=tmp_path / "hermes-copy", binding_root=host.binding_root)
    shutil.copytree(host.root, copy.root)
    copy_store = _store_for(copy)
    cloned = identity.load_or_create(copy_store, **copy.kwargs())
    assert cloned.change_reason is ChangeReason.CLONE_OR_BACKUP
    assert cloned.iid != original.iid
    assert cloned.k_grace() != original.k_grace()
    assert copy_store.calls and set(copy_store.devices.values()) == {"REVOKED"}
    # The original home is untouched and still loads its own identity.
    again = identity.load_or_create(store, **host.kwargs())
    assert again.change_reason is ChangeReason.NONE and again.iid == original.iid
    assert original.still_current()


def test_home_backup_restored_on_another_host(host: Host, tmp_path: Path) -> None:
    """A home backup carries the key but not the binding, which lives outside every home."""
    store = _store_for(host)
    original = identity.load_or_create(store, **host.kwargs())
    other = Host(root=tmp_path / "other" / "hermes", binding_root=tmp_path / "other" / "state")
    shutil.copytree(host.root, other.root)
    restored_store = _store_for(other)
    restored = identity.load_or_create(restored_store, **other.kwargs(host_id=lambda: HOST_B))
    assert restored.change_reason is ChangeReason.CLONE_OR_BACKUP
    assert restored.iid != original.iid
    assert set(restored_store.devices.values()) == {"REVOKED"}


def test_whole_machine_backup_restored_on_another_host(host: Host) -> None:
    """Home and binding both restored, but the host id differs."""
    store = _store_for(host)
    original = identity.load_or_create(store, **host.kwargs())
    restored = identity.load_or_create(store, **host.kwargs(host_id=lambda: HOST_B))
    assert restored.change_reason is ChangeReason.HOST_CHANGED
    assert restored.iid != original.iid


def test_store_restored_from_backup_on_the_same_host(host: Host) -> None:
    store = _store_for(host)
    identity.load_or_create(store, **host.kwargs())
    rotated = identity.rotate_key(store, **host.kwargs())  # epoch 2 recorded in the binding
    store.epoch = 1  # the store file is rolled back to an older copy
    store.devices["dev_old"] = "ACTIVE"
    restored = identity.load_or_create(store, **host.kwargs())
    assert restored.change_reason is ChangeReason.STORE_RESTORED
    assert restored.iid != rotated.iid
    assert store.devices["dev_old"] == "REVOKED"


def test_store_ahead_repairs_the_binding_upward(host: Host) -> None:
    store = _store_for(host)
    first = identity.load_or_create(store, **host.kwargs())
    store.epoch = 7  # e.g. a crash after the store transaction committed
    again = identity.load_or_create(store, **host.kwargs())
    assert again.change_reason is ChangeReason.NONE and again.iid == first.iid
    assert Binding.parse(again.custody.binding_path.read_bytes()).revocation_epoch == 7
    assert len(store.calls) == 1


def test_replaced_key_is_an_identity_change(host: Host) -> None:
    store = _store_for(host)
    first = identity.load_or_create(store, **host.kwargs())
    foreign = crypto.private_key_to_pem(crypto.generate_private_key())
    identity._write_private(first.custody.key_path, foreign)
    again = identity.load_or_create(store, **host.kwargs())
    assert again.change_reason is ChangeReason.KEY_REPLACED
    assert again.iid not in (first.iid, identity._iid_of(crypto.private_key_from_pem(foreign)))
    assert not first.still_current()


@pytest.mark.parametrize("damage", ["delete", "garbage"])
def test_lost_or_unreadable_key_is_an_identity_change(host: Host, damage: str) -> None:
    store = _store_for(host)
    first = identity.load_or_create(store, **host.kwargs())
    if damage == "delete":
        first.custody.key_path.unlink()
    else:
        first.custody.key_path.write_bytes(b"not a key")
    again = identity.load_or_create(store, **host.kwargs())
    assert again.change_reason is ChangeReason.KEY_LOST
    assert again.iid != first.iid and len(store.calls) == 2


def test_interrupted_change_is_completed_on_next_load(host: Host) -> None:
    store = _store_for(host)
    first = identity.load_or_create(store, **host.kwargs())
    store.fail_next = True
    with pytest.raises(RuntimeError):
        identity.rotate_key(store, **host.kwargs())
    # The binding is marked pending, so the old key is no longer current anywhere.
    assert Binding.parse(first.custody.binding_path.read_bytes()).pending
    assert not first.still_current()
    again = identity.load_or_create(store, **host.kwargs())
    assert again.change_reason is ChangeReason.INTERRUPTED
    assert again.iid != first.iid
    assert not Binding.parse(again.custody.binding_path.read_bytes()).pending


# --------------------------------------------------------------------------------------------------
# rotate-key (PR7-2, PR7-6)
# --------------------------------------------------------------------------------------------------


def test_rotate_key_revokes_and_expires_in_one_store_transaction(host: Host) -> None:
    store = _store_for(host)
    old = identity.load_or_create(store, **host.kwargs())
    store.devices["dev_3"] = "ACTIVE"
    store.offers["o3"] = "open"
    store.pairings["p3"] = "pending"
    calls_before = len(store.calls)
    new = identity.rotate_key(store, **host.kwargs())
    assert new.change_reason is ChangeReason.ROTATED
    assert len(store.calls) == calls_before + 1  # exactly one store transaction
    assert set(store.devices.values()) == {"REVOKED"}
    assert "open" not in store.offers.values() and "pending" not in store.pairings.values()
    # Store first: the transaction ran while the OLD key was still on disk.
    assert store.key_iid_at_call[-1] == old.iid
    assert new.iid != old.iid
    assert Binding.parse(new.custody.binding_path.read_bytes()).revocation_epoch == store.epoch


def test_rotate_key_require_current_succeeds_when_current(host: Host) -> None:
    store = _store_for(host)
    old = identity.load_or_create(store, **host.kwargs())
    new = identity.rotate_key(store, **host.kwargs(require_current=True))
    assert new.change_reason is ChangeReason.ROTATED and new.iid != old.iid


def test_rotate_key_require_current_refuses_a_stale_view(host: Host) -> None:
    """SR-9: the currency check now runs under `rotate_key`'s own custody lock, atomically with
    the rotation -- a caller whose view of the identity is not current (here, a host change) must
    refuse and change nothing, not rotate over it."""
    store = _store_for(host)
    identity.load_or_create(store, **host.kwargs())
    calls_before = len(store.calls)
    with pytest.raises(IdentityError):
        identity.rotate_key(store, **host.kwargs(host_id=lambda: HOST_B, require_current=True))
    assert len(store.calls) == calls_before  # nothing changed: no revoke transaction ran


def test_rotate_key_without_require_current_keeps_its_prior_unchecked_behavior(host: Host) -> None:
    """The default (`require_current=False`) is unchanged: only the CLI's explicit
    `require_current=True` mode adds the SR-9 guard."""
    store = _store_for(host)
    identity.load_or_create(store, **host.kwargs())
    new = identity.rotate_key(store, **host.kwargs(host_id=lambda: HOST_B))
    assert new.change_reason is ChangeReason.ROTATED


def test_old_key_stops_serving_after_rotation(host: Host) -> None:
    store = _store_for(host)
    running = identity.load_or_create(store, **host.kwargs())  # the gateway's copy
    running.server_ssl_context()
    assert running.still_current()
    identity.rotate_key(store, **host.kwargs())  # the operator CLI, a separate load
    assert not running.still_current()
    assert not running.still_current()  # latched
    with pytest.raises(IdentityError):
        running.server_ssl_context()


# --------------------------------------------------------------------------------------------------
# k_grace (research R16, CS-13)
# --------------------------------------------------------------------------------------------------


def test_k_grace_custody(host: Host) -> None:
    store = _store_for(host)
    ident = identity.load_or_create(store, **host.kwargs())
    path = ident.custody.k_grace_path
    assert path.stat().st_size == 32 and _mode(path) == 0o600
    assert not _inside(path, host.root)
    assert not _inside(path, host.root / "profiles")
    k1 = ident.k_grace()
    rotated = identity.rotate_key(store, **host.kwargs())
    k2 = rotated.k_grace()
    assert k2 != k1 and _mode(path) == 0o600
    host.host = HOST_B  # simulated clone/host-change detection
    moved = identity.load_or_create(store, **host.kwargs())
    assert moved.k_grace() not in (k1, k2)


@pytest.mark.parametrize("damage", ["delete", "short", "unreadable"])
def test_k_grace_regenerated_when_missing_or_unreadable(host: Host, damage: str) -> None:
    store = _store_for(host)
    ident = identity.load_or_create(store, **host.kwargs())
    path = ident.custody.k_grace_path
    k1 = ident.k_grace()
    if damage == "delete":
        path.unlink()
    elif damage == "short":
        path.write_bytes(b"x" * 5)
    else:
        os.chmod(path, 0)  # present but unreadable
    again = identity.load_or_create(store, **host.kwargs())
    assert again.change_reason is ChangeReason.NONE and again.iid == ident.iid
    k2 = again.k_grace()
    assert len(k2) == 32 and k2 != k1 and _mode(path) == 0o600
    assert len(store.calls) == 1  # regenerating k_grace alone revokes nothing
    path.unlink()
    assert len(ident.k_grace()) == 32  # also regenerated on demand


def test_k_grace_never_in_the_hermes_root(host: Host) -> None:
    ident = identity.load_or_create(_store_for(host), **host.kwargs())
    secret = ident.k_grace()
    for p in host.root.rglob("*"):
        if p.is_file():
            assert secret not in p.read_bytes()


def test_concurrent_first_runs_create_one_identity(host: Host) -> None:
    """The gateway and the operator CLI may load at the same moment; the custody lock makes the
    second load see the first one's identity instead of creating another."""
    import threading

    store = _store_for(host)
    results: list[identity.LoadedIdentity] = []
    lock = threading.Lock()

    def load() -> None:
        got = identity.load_or_create(store, **host.kwargs())
        with lock:
            results.append(got)

    threads = [threading.Thread(target=load) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len({r.iid for r in results}) == 1
    assert len(store.calls) == 1
