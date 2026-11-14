"""PN-ISS-1/5 and PN-KEY: isolated derivation and read-only custody, no live homes."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import stat
import threading
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from hmp_plugin import contract, crypto, identity, push_issuer, wire

KEY = bytes(range(32))
INPUTS = push_issuer.RouteInputs("test-iid", 3, "test-device", "test-family", 5, bytes(range(32)))


def test_v1_domains_stay_unchanged_and_every_domain_is_prefix_free() -> None:
    assert contract.TRANSCRIPT_TAGS == (
        b"HMP1-PAIR-REQ",
        b"HMP1-PAIR-RESP",
        b"HMP1-PAIR-DONE",
        b"HMP1-TOKEN",
        b"HMP1-SELF-REVOKE",
    )
    assert contract.HASH_DOMAIN_TAGS == (b"HMP1-OFFER", b"HMP1-HOST")
    tags = (
        *contract.TRANSCRIPT_TAGS,
        *contract.HASH_DOMAIN_TAGS,
        contract.TAG_GRACE,
        contract.TAG_PUSH_ROUTE,
        contract.TAG_PUSH_COLLAPSE,
        contract.TAG_PUSH_RELAY,
    )
    assert len(tags) == len(set(tags))
    assert all(not a.startswith(b) for a in tags for b in tags if a != b)
    for tag in (contract.TAG_PUSH_ROUTE, contract.TAG_PUSH_COLLAPSE, contract.TAG_PUSH_RELAY):
        with pytest.raises(crypto.CryptoError):
            crypto.transcript(tag, "not-a-v1-transcript")


@pytest.mark.parametrize(
    "changes",
    [
        {"iid": "test-iid-other"},
        {"host_generation": 4},
        {"device_id": "test-device-other"},
        {"family_id": "test-family-other"},
        {"generation": 6},
        {"salt": b"x" * 32},
    ],
)
def test_every_bound_field_changes_route_and_fails_saved_hash(changes: dict) -> None:
    route = push_issuer.derive_route(KEY, INPUTS)
    other = replace(INPUTS, **changes)
    assert push_issuer.derive_route(KEY, other) != route
    assert push_issuer.rederive_route(KEY, other, hashlib.sha256(route).digest()) is None


def test_rerivation_loss_and_recreated_secret() -> None:
    route = push_issuer.derive_route(KEY, INPUTS)
    saved_hash = hashlib.sha256(route).digest()
    assert push_issuer.rederive_route(KEY, INPUTS, saved_hash) == route
    assert push_issuer.rederive_route(None, INPUTS, saved_hash) is None
    assert push_issuer.rederive_route(b"k" * 32, INPUTS, saved_hash) is None
    assert push_issuer.rederive_route(KEY, INPUTS, route) is None
    assert push_issuer.rederive_route(KEY, INPUTS, saved_hash.hex()) is None
    assert push_issuer.rederive_route(KEY, INPUTS, b"short") is None
    text = push_issuer.route_text(route)
    assert len(route) == 32 and len(text) == 43 and "=" not in text
    assert wire.b64u_decode(text, length=32) == route
    assert hashlib.sha256(text.encode()).digest() != saved_hash


def test_collapse_is_raw24_exact_scope_and_stable_per_route() -> None:
    route = push_issuer.derive_route(KEY, INPUTS)
    scope = "test-profile-é"
    collapse = push_issuer.derive_collapse(KEY, route, scope)
    assert len(collapse) == 24 and len(wire.b64u_encode(collapse)) == 32
    assert push_issuer.derive_collapse(KEY, route, scope) == collapse
    for changed_scope in ("test-profile-e\u0301", scope.upper(), " " + scope, scope + " "):
        assert push_issuer.derive_collapse(KEY, route, changed_scope) != collapse
    assert push_issuer.derive_collapse(KEY, b"r" * 32, scope) != collapse
    assert push_issuer.derive_collapse(b"k" * 32, route, scope) != collapse


@pytest.mark.parametrize(
    "field,value",
    [
        ("iid", ""),
        ("iid", b"iid"),
        ("device_id", None),
        ("family_id", 1),
        ("host_generation", True),
        ("host_generation", -1),
        ("host_generation", 2**64),
        ("generation", False),
        ("generation", 0),
        ("generation", -1),
        ("generation", 2**53),
        ("salt", bytearray(32)),
        ("salt", b"x" * 31),
        ("salt", b"x" * 33),
    ],
)
def test_binding_refuses_invalid_types_and_bounds(field: str, value: object) -> None:
    with pytest.raises(crypto.CryptoError):
        replace(INPUTS, **{field: value})


@pytest.mark.parametrize("key", [None, b"x" * 31, b"x" * 33, bytearray(32), "x" * 32])
def test_invalid_secret_never_derives(key: object) -> None:
    with pytest.raises(crypto.CryptoError):
        push_issuer.derive_route(key, INPUTS)
    with pytest.raises(crypto.CryptoError):
        push_issuer.derive_collapse(key, b"r" * 32, "test-profile")


@pytest.mark.parametrize(
    "route,scope",
    [(b"r" * 31, "p"), (b"r" * 33, "p"), ("r" * 32, "p"), (b"r" * 32, ""), (b"r" * 32, b"p")],
)
def test_collapse_rejects_wrong_bound_values(route: object, scope: object) -> None:
    with pytest.raises(crypto.CryptoError):
        push_issuer.derive_collapse(KEY, route, scope)


def test_route_inputs_repr_and_error_never_contain_values() -> None:
    assert not any(v in repr(INPUTS) for v in (INPUTS.iid, INPUTS.device_id, INPUTS.family_id))
    with pytest.raises(crypto.CryptoError) as exc:
        replace(INPUTS, salt=b"test-private-invalid-salt")
    assert "test-private-invalid-salt" not in str(exc.value)


@pytest.fixture
def loaded(tmp_path: Path) -> identity.LoadedIdentity:
    custody = identity.Custody(
        tmp_path / "synthetic-home", tmp_path / "anchor", tmp_path / "binding"
    )
    custody.binding_dir.mkdir()
    return identity.LoadedIdentity(
        custody,
        ec.generate_private_key(ec.SECP256R1()),
        identity.Binding("test-iid", "test-host-hash", 3),
        identity.ChangeReason.NONE,
    )


def forbid_repair(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("read-only push key access attempted a write/repair")

    monkeypatch.setattr(identity, "_read_or_create_k_grace", forbidden)
    monkeypatch.setattr(identity, "_write_private", forbidden)
    monkeypatch.setattr(identity, "_private_dir", forbidden)
    monkeypatch.setattr(identity.os, "chmod", forbidden)
    monkeypatch.setattr(identity.crypto, "random_bytes", forbidden)


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [0, 1, 31, 33, 1_048_576])
async def test_wrong_length_read_never_repairs(loaded, monkeypatch, size: int) -> None:
    path = loaded.custody.k_grace_path
    path.write_bytes(b"x" * size)
    before = path.stat()
    forbid_repair(monkeypatch)
    assert await loaded.read_k_grace_for_push() is None
    after = path.stat()
    assert (after.st_ino, after.st_size, after.st_mtime_ns, after.st_mode) == (
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_mode,
    )
    assert path.read_bytes() == b"x" * size


@pytest.mark.asyncio
async def test_missing_key_and_parent_are_not_created(loaded, monkeypatch) -> None:
    loaded.custody.binding_dir.rmdir()
    forbid_repair(monkeypatch)
    assert await loaded.read_k_grace_for_push() is None
    assert not loaded.custody.binding_dir.exists()


@pytest.mark.asyncio
async def test_read_once_off_loop_and_no_mode_change(loaded, monkeypatch) -> None:
    path = loaded.custody.k_grace_path
    path.write_bytes(KEY)
    path.chmod(0o640)
    original = identity._read_k_grace_for_push
    calls = []
    main_thread = threading.get_ident()

    def observed(target):
        calls.append(threading.get_ident())
        return original(target)

    monkeypatch.setattr(identity, "_read_k_grace_for_push", observed)
    forbid_repair(monkeypatch)
    assert await loaded.read_k_grace_for_push() == KEY
    assert len(calls) == 1 and calls[0] != main_thread
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert path.read_bytes() == KEY


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [PermissionError, FileNotFoundError, OSError])
async def test_transient_open_failure_does_not_cache_or_destroy(
    loaded, monkeypatch, exception
) -> None:
    path = loaded.custody.k_grace_path
    path.write_bytes(KEY)
    original = identity.os.open
    calls = 0

    def interrupted(target, flags, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise exception("synthetic read failure")
        return original(target, flags, *args, **kwargs)

    monkeypatch.setattr(identity.os, "open", interrupted)
    forbid_repair(monkeypatch)
    assert await loaded.read_k_grace_for_push() is None
    assert await loaded.read_k_grace_for_push() == KEY
    assert path.read_bytes() == KEY


@pytest.mark.asyncio
async def test_metadata_failure_closes_descriptor(loaded, monkeypatch) -> None:
    path = loaded.custody.k_grace_path
    path.write_bytes(KEY)
    original = identity.os.open
    descriptors = []

    def observed(*args, **kwargs):
        fd = original(*args, **kwargs)
        descriptors.append(fd)
        return fd

    def failed_stat(fd):
        raise OSError("synthetic metadata failure")

    monkeypatch.setattr(identity.os, "open", observed)
    monkeypatch.setattr(identity.os, "fstat", failed_stat)
    forbid_repair(monkeypatch)
    assert await loaded.read_k_grace_for_push() is None
    assert len(descriptors) == 1
    with pytest.raises(OSError):
        os.read(descriptors[0], 1)


@pytest.mark.asyncio
async def test_nonregular_directory_refused(loaded, monkeypatch) -> None:
    loaded.custody.k_grace_path.mkdir()
    forbid_repair(monkeypatch)
    assert await loaded.read_k_grace_for_push() is None


@pytest.mark.asyncio
@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="OS has no no-follow open flag")
async def test_symlink_secret_refused_without_touching_target(
    loaded, monkeypatch, tmp_path
) -> None:
    target = tmp_path / "other-synthetic-key"
    target.write_bytes(KEY)
    loaded.custody.k_grace_path.symlink_to(target)
    before = target.stat()
    forbid_repair(monkeypatch)
    assert await loaded.read_k_grace_for_push() is None
    assert target.read_bytes() == KEY
    assert target.stat().st_mode == before.st_mode


@pytest.mark.asyncio
@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="OS has no FIFO")
async def test_fifo_does_not_block_worker(loaded, monkeypatch) -> None:
    os.mkfifo(loaded.custody.k_grace_path)
    forbid_repair(monkeypatch)
    assert await asyncio.wait_for(loaded.read_k_grace_for_push(), timeout=2) is None


VECTORS = json.loads(
    (
        Path(__file__).resolve().parents[3]
        / "docs/architecture/contracts/vectors/hmp_push_issuer_vectors.json"
    ).read_text()
)


@pytest.mark.parametrize("v", VECTORS["vectors"], ids=lambda v: v["label"])
def test_independent_static_vectors(v: dict) -> None:
    assert VECTORS["key_is_synthetic_test_material"] is True
    key = bytes.fromhex(VECTORS["key_grace_hex"])
    values = v["inputs"]
    inputs = push_issuer.RouteInputs(
        values["iid"],
        values["H"],
        values["device_id"],
        values["family_id"],
        values["G"],
        bytes.fromhex(values["salt_hex"]),
    )
    route = push_issuer.derive_route(key, inputs)
    assert route.hex() == v["route_raw_hex"]
    assert push_issuer.route_text(route) == v["route_b64u"]
    assert hashlib.sha256(route).hexdigest() == v["route_sha256_hex"]
    collapse = push_issuer.derive_collapse(key, route, values["scope_exact"])
    assert collapse.hex() == v["collapse_raw24_hex"]
    assert wire.b64u_encode(collapse) == v["collapse_b64u_32"]
    assert wire.b64u_encode(collapse) == v["collapse_full_hmac_b64u"][:32]


@pytest.mark.asyncio
async def test_read_error_closes_fd_and_never_repairs(loaded, monkeypatch) -> None:
    path = loaded.custody.k_grace_path
    path.write_bytes(KEY)
    original = identity.os.read
    descriptors = []

    def failing(fd, count):
        descriptors.append(fd)
        raise OSError("synthetic read failure")

    monkeypatch.setattr(identity.os, "read", failing)
    forbid_repair(monkeypatch)
    assert await loaded.read_k_grace_for_push() is None
    assert len(descriptors) == 1
    with pytest.raises(OSError):
        original(descriptors[0], 1)
    monkeypatch.setattr(identity.os, "read", original)
    assert await loaded.read_k_grace_for_push() == KEY


@pytest.mark.parametrize("field", ["iid", "device_id", "family_id"])
def test_invalid_utf8_binding_has_fixed_error(field: str) -> None:
    with pytest.raises(crypto.CryptoError) as exc:
        replace(INPUTS, **{field: "synthetic-private\ud800"})
    assert str(exc.value) == "invalid push route binding"
    assert exc.value.__suppress_context__ is True


def test_invalid_utf8_scope_has_fixed_error() -> None:
    with pytest.raises(crypto.CryptoError) as exc:
        push_issuer.derive_collapse(KEY, b"r" * 32, "synthetic-private\ud800")
    assert str(exc.value) == "invalid push collapse binding"
    assert exc.value.__suppress_context__ is True
