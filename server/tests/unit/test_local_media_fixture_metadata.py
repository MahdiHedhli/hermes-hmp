"""Ordinary-CI causal metadata/FD regression tests against actual fixture helper functions.

All FD/metadata/environment operations below are module-local fakes. This does not qualify
native/SDK/TLS/network behavior. Helpers' unused network imports are blocked locally; pytest
or other tests may already have loaded stdlib socket. No global import/sys.path/native tools
alias is changed, and no existing sys.modules entry is overwritten.
"""

from __future__ import annotations

import builtins
import hashlib
import importlib.util
import json
import os
import stat
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_HELPERS = _ROOT / "tools" / "fixtures"
_NAMES = (
    "_hmp_ci_media_metadata_provider",
    "_hmp_ci_media_metadata_fixture",
    "_hmp_ci_media_metadata_seed",
)
_CASES = tuple(f"NM{i:02d}" for i in range(1, 11))
_DESCRIPTOR = json.dumps(
    {
        "format": "native-media-fixture-v1",
        "rootExecutionAdmissionSHA256": "inert-test-input-not-runtime-proof",
        "nativeSourcePreservationSHA256": "inert-test-input-not-runtime-proof",
        "scenarios": {case: {} for case in _CASES},
    }
).encode()
_SOURCE = b"inert source payload for SHA/EOF assertions\n"


class BlockedHelperTransportError(RuntimeError):
    """Distinct from a fake metadata error, and never silently treated as unsupported."""


class _BlockedModule(ModuleType):
    def __getattr__(self, name):
        raise BlockedHelperTransportError("blocked_helper_transport")


@contextmanager
def _load_helpers():
    """Load real, untransformed source with only a module-local dependency import seam."""
    if any(name in sys.modules for name in _NAMES):
        raise RuntimeError("helper_module_collision")
    created = {}
    provider = None
    blocked_http = ModuleType("http")
    blocked_http.client = _BlockedModule("http.client")
    blocked_ssl = _BlockedModule("ssl")
    original_import = builtins.__import__

    def local_import(name, globals_=None, locals_=None, fromlist=(), level=0):
        if level == 0 and name == "local_media_provider_response":
            if provider is None:
                raise RuntimeError("helper_dependency_missing")
            return provider
        if level == 0 and name == "http.client":
            return blocked_http
        if level == 0 and name == "ssl":
            return blocked_ssl
        allowed_stdlib = {
            "__future__",
            "base64",
            "hashlib",
            "json",
            "time",
            "dataclasses",
            "os",
            "re",
            "stat",
            "pathlib",
            "inspect",
            "sys",
            "threading",
            "contextlib",
        }
        if level != 0 or name not in allowed_stdlib:
            raise BlockedHelperTransportError("blocked_helper_import")
        return original_import(name, globals_, locals_, fromlist, level)

    def load(name, filename):
        # Repeat the absent check immediately before registering, with no alias overwrite.
        if name in sys.modules:
            raise RuntimeError("helper_module_collision")
        spec = importlib.util.spec_from_file_location(name, _HELPERS / filename)
        if spec is None or spec.loader is None:
            raise RuntimeError("helper_spec")
        module = importlib.util.module_from_spec(spec)
        module.__dict__["__builtins__"] = {**vars(builtins), "__import__": local_import}
        sys.modules[name] = module
        created[name] = module
        spec.loader.exec_module(module)
        return module

    try:
        provider = load(_NAMES[0], "local_media_provider_response.py")
        fixture = load(_NAMES[1], "local_media_fixture.py")
        seed = load(_NAMES[2], "local_media_seed.py")
        yield SimpleNamespace(provider=provider, fixture=fixture, seed=seed)
    finally:
        changed = False
        for name, module in reversed(tuple(created.items())):
            if sys.modules.get(name) is module:
                del sys.modules[name]
            else:
                # Do not delete a foreign/replaced entry or claim restoration of it.
                changed = True
        if changed:
            raise RuntimeError("helper_module_changed")


def _metadata(size, changes=None):
    values = {
        "st_mode": stat.S_IFREG | 0o600,
        "st_ino": 23,
        "st_dev": 11,
        "st_nlink": 1,
        "st_uid": 501,
        "st_gid": 20,
        "st_size": size,
        "st_atime": 10,
        "st_mtime": 20,
        "st_ctime": 30,
        "st_atime_ns": 10000000000,
        "st_mtime_ns": 20000000000,
        "st_ctime_ns": 30000000000,
    }
    values.update(changes or {})
    sequence = [
        values[key]
        for key in (
            "st_mode",
            "st_ino",
            "st_dev",
            "st_nlink",
            "st_uid",
            "st_gid",
            "st_size",
            "st_atime",
            "st_mtime",
            "st_ctime",
        )
    ]
    return os.stat_result(
        sequence,
        {
            key: values[key]
            for key in (
                "st_atime_ns",
                "st_mtime_ns",
                "st_ctime_ns",
            )
        },
    )


class _CloseFailureError(OSError):
    pass


class _FakeOS:
    O_RDONLY = os.O_RDONLY
    O_DIRECTORY = os.O_DIRECTORY
    O_NOFOLLOW = os.O_NOFOLLOW
    O_NONBLOCK = os.O_NONBLOCK

    def __init__(
        self,
        body,
        *,
        route=None,
        changes=None,
        before_changes=None,
        short=False,
        growth=False,
        open_fail=None,
        close_fail=None,
        close_after=False,
        child_close_fail=False,
        cancel=False,
        read_error=False,
        metadata_error=False,
    ):
        self.body = body
        self.offset = 0
        self.before = _metadata(len(body), before_changes)
        self.changed = _metadata(len(body), changes)
        self.route = route
        self.short = short
        self.growth = growth
        self.open_fail = open_fail
        self.close_fail = close_fail
        self.close_after = close_after
        self.child_close_fail = child_close_fail
        self.cancel = cancel
        self.read_error = read_error
        self.metadata_error = metadata_error
        self.open_count = 0
        self.close_count = 0
        self.fstats = 0
        self.counter = 1000
        self.opened = {}
        self.close_ids = []
        self.ambiguous = set()
        self.reads = []
        self.environ = {
            "HOME": "/Users/mhedhli",  # Fake input, never assigned to actual os.environ.
            "HERMES_HOME": "/private/tmp/inert-home",
            "HERMES_RUNTIME_DIR": "/private/tmp/inert-runtime",
            "HMP_MEDIA_FIXTURE_IMAGE_KEY": "fixture-only-never-a-real-openai-key",
        }

    def getuid(self):
        return 501

    def open(self, name, flags, *, dir_fd=None):
        self.open_count += 1
        if self.open_count == self.open_fail:
            raise OSError("inert_open")
        assert flags & self.O_NOFOLLOW
        if dir_fd is not None:
            assert self.opened[dir_fd] == "directory"
        role = "directory" if flags & self.O_DIRECTORY else "leaf"
        if role == "leaf":
            assert flags & self.O_NONBLOCK
        self.counter += 1
        self.opened[self.counter] = role
        return self.counter

    def close(self, fd):
        assert fd in self.opened, "closed/ambiguous numeric FD replay"
        self.close_count += 1
        self.close_ids.append(fd)
        fail = self.close_count == self.close_fail or (
            self.child_close_fail and self.close_count == 2
        )
        if fail:
            self.ambiguous.add(fd)
            if self.close_after:
                del self.opened[fd]
            if self.cancel and self.close_count == self.close_fail:
                raise KeyboardInterrupt()
            raise _CloseFailureError("inert_close")
        del self.opened[fd]

    def fstat(self, fd):
        if self.opened[fd] == "directory":
            return _metadata(0, {"st_mode": stat.S_IFDIR | 0o700, "st_ino": fd})
        self.fstats += 1
        if self.fstats == 1:
            return self.before
        if self.route == "held" and self.metadata_error:
            raise OSError("inert_held")
        return self.changed if self.route == "held" else self.before

    def stat(self, name, *, dir_fd, follow_symlinks):
        assert self.opened[dir_fd] == "directory" and follow_symlinks is False
        assert name in {"descriptor.json", "source.py"}
        if self.route == "named" and self.metadata_error:
            raise OSError("inert_named")
        return self.changed if self.route == "named" else self.before

    def read(self, fd, size):
        assert self.opened[fd] == "leaf" and 0 < size <= 8192
        self.reads.append(size)
        if self.read_error:
            raise OSError("inert_read")
        if self.short:
            return b""
        if self.offset == len(self.body):
            return b"x" if self.growth else b""
        part = self.body[self.offset : self.offset + size]
        self.offset += len(part)
        return part


def _invoke(helpers, monkeypatch, function, fake, *, wrong_hash=False):
    module = helpers.fixture if function == "read_descriptor" else helpers.seed
    monkeypatch.setattr(module, "os", fake)
    if function == "read_descriptor":
        return module.read_descriptor(Path("/private/tmp/inert-meta/descriptor.json"))
    if function == "source_pin":
        monkeypatch.setattr(
            module,
            "inspect",
            SimpleNamespace(
                getsourcefile=lambda _: "/private/tmp/inert-meta/source.py",
            ),
        )
        return module.source_pin(
            object(),
            Path("/private/tmp/inert-meta/source.py"),
            "0" * 64 if wrong_hash else hashlib.sha256(fake.body).hexdigest(),
        )
    return module.check_environment(
        Path("/private/tmp/inert-home"), Path("/private/tmp/inert-runtime")
    )


def _fake(function, **kwargs):
    return _FakeOS(_DESCRIPTOR if function == "read_descriptor" else _SOURCE, **kwargs)


def _known_closed(fake):
    assert not fake.ambiguous and fake.opened == {}
    assert all(count == 1 for count in Counter(fake.close_ids).values())


@pytest.mark.parametrize("function", ["read_descriptor", "source_pin"])
@pytest.mark.parametrize("route", ["held", "named"])
def test_atime_only_read_change_is_not_identity_drift(monkeypatch, function, route):
    fake = _fake(function, route=route, changes={"st_atime": 11, "st_atime_ns": 11000000000})
    with _load_helpers() as helpers:
        _invoke(helpers, monkeypatch, function, fake)
    _known_closed(fake)


@pytest.mark.parametrize("function", ["read_descriptor", "source_pin"])
@pytest.mark.parametrize("route", ["held", "named"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("st_mtime_ns", 20000000001),
        ("st_ctime_ns", 30000000001),
        ("st_dev", 12),
        ("st_ino", 24),
        ("st_mode", stat.S_IFREG | 0o640),
        ("st_uid", 502),
        ("st_gid", 21),
        ("st_nlink", 2),
        ("st_size", 12345),
        ("st_mode", stat.S_IFIFO | 0o600),
    ],
)
def test_held_and_named_stable_metadata_drift_refuses(monkeypatch, function, route, field, value):
    fake = _fake(function, route=route, changes={field: value})
    code = "descriptor_drift" if function == "read_descriptor" else "factory_drift"
    with _load_helpers() as helpers, pytest.raises(RuntimeError, match=r"^" + code + "$"):
        _invoke(helpers, monkeypatch, function, fake)
    _known_closed(fake)


@pytest.mark.parametrize("function", ["read_descriptor", "source_pin"])
@pytest.mark.parametrize(
    "change",
    [
        {"st_mode": stat.S_IFIFO | 0o600},
        {"st_nlink": 2},
        {"st_mtime_ns": None},
    ],
)
def test_unqualified_leaf_metadata_refuses_before_read(monkeypatch, function, change):
    fake = _fake(function, before_changes=change)
    with _load_helpers() as helpers, pytest.raises(RuntimeError):
        _invoke(helpers, monkeypatch, function, fake)
    assert fake.reads == []
    _known_closed(fake)


@pytest.mark.parametrize("function", ["read_descriptor", "source_pin"])
@pytest.mark.parametrize("fault", ["short", "growth", "read_error"])
def test_body_eof_and_read_errors_preserve_known_fd_cleanup(monkeypatch, function, fault):
    fake = _fake(function, **{fault: True})
    with _load_helpers() as helpers, pytest.raises((RuntimeError, OSError)):
        _invoke(helpers, monkeypatch, function, fake)
    _known_closed(fake)


def test_source_hash_mismatch_is_not_metadata_success(monkeypatch):
    fake = _fake("source_pin")
    with _load_helpers() as helpers, pytest.raises(RuntimeError, match=r"^factory_body$"):
        _invoke(helpers, monkeypatch, "source_pin", fake, wrong_hash=True)
    _known_closed(fake)


@pytest.mark.parametrize("function", ["read_descriptor", "source_pin"])
@pytest.mark.parametrize("route", ["held", "named"])
def test_final_metadata_error_closes_known_descriptors(monkeypatch, function, route):
    fake = _fake(function, route=route, metadata_error=True)
    with _load_helpers() as helpers, pytest.raises(OSError):
        _invoke(helpers, monkeypatch, function, fake)
    _known_closed(fake)


@pytest.mark.parametrize("function", ["read_descriptor", "source_pin", "check_environment"])
def test_all_three_walkers_healthy_own_fd_census(monkeypatch, function):
    fake = _fake(function)
    with _load_helpers() as helpers:
        _invoke(helpers, monkeypatch, function, fake)
    _known_closed(fake)


@pytest.mark.parametrize("function", ["read_descriptor", "source_pin", "check_environment"])
@pytest.mark.parametrize("stage", [1, 2, 3])
def test_open_failure_closes_only_known_parent(monkeypatch, function, stage):
    fake = _fake(function, open_fail=stage)
    with _load_helpers() as helpers, pytest.raises(OSError, match=r"^inert_open$"):
        _invoke(helpers, monkeypatch, function, fake)
    _known_closed(fake)


@pytest.mark.parametrize("function", ["read_descriptor", "source_pin", "check_environment"])
@pytest.mark.parametrize("after_effect", [False, True])
def test_parent_close_failure_closes_new_child_never_retries_parent(
    monkeypatch,
    function,
    after_effect,
):
    fake = _fake(function, close_fail=1, close_after=after_effect)
    with _load_helpers() as helpers, pytest.raises(_CloseFailureError):
        _invoke(helpers, monkeypatch, function, fake)
    assert fake.close_ids == [1001, 1002]
    assert fake.ambiguous == {1001} and 1002 not in fake.opened
    assert set(fake.opened) <= fake.ambiguous
    # Even after-effect fake.opened == {} does NOT prove an errored close's actual result.


@pytest.mark.parametrize("function", ["read_descriptor", "source_pin", "check_environment"])
@pytest.mark.parametrize("after_effect", [False, True])
def test_child_cleanup_failure_retains_both_unknowns(monkeypatch, function, after_effect):
    fake = _fake(function, close_fail=1, close_after=after_effect, child_close_fail=True)
    with _load_helpers() as helpers, pytest.raises(_CloseFailureError) as error:
        _invoke(helpers, monkeypatch, function, fake)
    assert isinstance(error.value.__cause__, _CloseFailureError)
    assert fake.close_ids == [1001, 1002] and fake.ambiguous == {1001, 1002}
    assert set(fake.opened) <= fake.ambiguous


@pytest.mark.parametrize("function", ["read_descriptor", "source_pin", "check_environment"])
def test_parent_close_cancellation_propagates_and_closes_new_child_once(monkeypatch, function):
    fake = _fake(function, close_fail=1, cancel=True)
    with _load_helpers() as helpers, pytest.raises(KeyboardInterrupt):
        _invoke(helpers, monkeypatch, function, fake)
    assert fake.close_ids == [1001, 1002] and fake.ambiguous == {1001}
    assert set(fake.opened) <= fake.ambiguous


def test_loader_restores_created_names_on_success_error_and_cancellation():
    for error in (None, ValueError("inert"), KeyboardInterrupt()):
        assert not any(name in sys.modules for name in _NAMES)
        try:
            with _load_helpers():
                if error is not None:
                    raise error
        except BaseException as caught:
            assert caught is error
        assert not any(name in sys.modules for name in _NAMES)


def test_loader_never_overwrites_existing_module(monkeypatch):
    existing = ModuleType("existing-inert-module")
    monkeypatch.setitem(sys.modules, _NAMES[0], existing)
    with pytest.raises(RuntimeError, match=r"^helper_module_collision$"), _load_helpers():
        raise AssertionError("colliding loader entered")
    assert sys.modules[_NAMES[0]] is existing
    assert all(name not in sys.modules for name in _NAMES[1:])


def test_unused_helper_network_and_native_imports_are_distinctly_blocked():
    with _load_helpers() as helpers:
        with pytest.raises(BlockedHelperTransportError, match=r"^blocked_helper_transport$"):
            _ = helpers.fixture.http.client.HTTPSConnection
        with pytest.raises(BlockedHelperTransportError, match=r"^blocked_helper_transport$"):
            _ = helpers.fixture.ssl.SSLContext
        local_import = helpers.seed.__dict__["__builtins__"]["__import__"]
        for name in (
            "socket",
            "openai",
            "gateway.session",
            "hermes_state",
            "model_tools",
            "urllib.request",
            "requests",
            "aiohttp",
            "unknown_dependency",
        ):
            with pytest.raises(BlockedHelperTransportError, match=r"^blocked_helper_import$"):
                local_import(name)


@pytest.mark.parametrize("function", ["read_descriptor", "source_pin", "check_environment"])
def test_terminal_parent_close_failure_is_unknown_not_success(monkeypatch, function):
    fake = _fake(function, close_fail=4 if function == "check_environment" else 5)
    with _load_helpers() as helpers, pytest.raises(_CloseFailureError):
        _invoke(helpers, monkeypatch, function, fake)
    assert len(fake.ambiguous) == 1 and set(fake.opened) <= fake.ambiguous
    assert all(count == 1 for count in Counter(fake.close_ids).values())


@pytest.mark.parametrize("function", ["read_descriptor", "source_pin"])
@pytest.mark.parametrize("fault", ["open", "close"])
def test_leaf_open_or_close_failure_does_not_replay_or_lose_parent(monkeypatch, function, fault):
    fake = _fake(function, **({"open_fail": 5} if fault == "open" else {"close_fail": 4}))
    with _load_helpers() as helpers, pytest.raises(OSError):
        _invoke(helpers, monkeypatch, function, fake)
    if fault == "open":
        _known_closed(fake)
    else:
        assert len(fake.ambiguous) == 1 and set(fake.opened) <= fake.ambiguous
        assert all(count == 1 for count in Counter(fake.close_ids).values())


@pytest.mark.parametrize("change", [{"st_mode": stat.S_IFREG | 0o640}, {"st_uid": 502}])
def test_descriptor_initial_owner_and_permission_guards_survive(monkeypatch, change):
    fake = _fake("read_descriptor", before_changes=change)
    with _load_helpers() as helpers, pytest.raises(RuntimeError, match=r"^descriptor_leaf$"):
        _invoke(helpers, monkeypatch, "read_descriptor", fake)
    assert fake.reads == []
    _known_closed(fake)


@pytest.mark.parametrize("function,limit", [("read_descriptor", 131072), ("source_pin", 65536)])
def test_reader_size_caps_refuse_before_any_read(monkeypatch, function, limit):
    fake = _fake(function, before_changes={"st_size": limit + 1})
    with _load_helpers() as helpers, pytest.raises(RuntimeError):
        _invoke(helpers, monkeypatch, function, fake)
    assert fake.reads == []
    _known_closed(fake)


@pytest.mark.parametrize("cancel", [False, True])
def test_partial_helper_import_error_restores_created_names_only(monkeypatch, cancel):
    original_spec = importlib.util.spec_from_file_location
    original_module = importlib.util.module_from_spec

    class FailingLoader:
        def create_module(self, spec):
            return None

        def exec_module(self, module):
            if cancel:
                raise KeyboardInterrupt()
            raise ValueError("inert_helper_load")

    def local_spec(name, path):
        spec = original_spec(name, path)
        assert spec is not None
        if name == _NAMES[1]:
            spec.loader = FailingLoader()
        return spec

    # Replace this test module's reference, never importlib's global functions/builtins.
    monkeypatch.setattr(
        sys.modules[__name__],
        "importlib",
        SimpleNamespace(
            util=SimpleNamespace(
                spec_from_file_location=local_spec,
                module_from_spec=original_module,
            )
        ),
    )
    with pytest.raises(KeyboardInterrupt if cancel else ValueError), _load_helpers():
        raise AssertionError("failed helper load entered body")
    assert not any(name in sys.modules for name in _NAMES)


def test_loader_does_not_delete_a_foreign_replacement():
    foreign = ModuleType("inert-foreign-replacement")
    try:
        with pytest.raises(RuntimeError, match=r"^helper_module_changed$"), _load_helpers():
            sys.modules[_NAMES[1]] = foreign  # Only a newly created test name, no native alias.
        assert sys.modules[_NAMES[1]] is foreign
        assert _NAMES[0] not in sys.modules and _NAMES[2] not in sys.modules
    finally:
        # This test owns that exact object; the loader deliberately refused to delete it.
        if sys.modules.get(_NAMES[1]) is foreign:
            del sys.modules[_NAMES[1]]


def test_loader_preserves_sys_path_global_import_and_native_tools_alias():
    previous_path = tuple(sys.path)
    previous_import = builtins.__import__
    missing = object()
    previous_tools = sys.modules.get("tools", missing)
    previous_bare = sys.modules.get("local_media_provider_response", missing)
    with _load_helpers():
        assert tuple(sys.path) == previous_path
        assert builtins.__import__ is previous_import
        assert sys.modules.get("tools", missing) is previous_tools
        assert sys.modules.get("local_media_provider_response", missing) is previous_bare
    assert tuple(sys.path) == previous_path and builtins.__import__ is previous_import
    assert sys.modules.get("tools", missing) is previous_tools
    assert sys.modules.get("local_media_provider_response", missing) is previous_bare
