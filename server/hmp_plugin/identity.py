"""Instance identity and key custody (ID-2): the key anchored in the default profile's plugin data,
a hashed host binding outside every Hermes home, the store revocation epoch, clone and backup
detection (revoke every device), refusal of a second identity under a named profile, and
`rotate-key` per PR7-2 and PR7-6. Also `k_grace` custody (research R16, CS-13).

Hermes access (IR-6, controller ruling (a)): this module may import exactly
`hermes_constants.get_default_hermes_root`, the documented plugin API that anchors the instance
key. That import is accepted on every build, including unsupported ones, because the listener must
serve `/ready` with the instance certificate everywhere. It is the only Hermes import allowed here
(`tools/ci/check_plugin_surface.py` S1). It is imported lazily, so importing this module imports
no Hermes code.

Layout (research R17 records the decisions; the HMP1-HOST encoding closes the T015 evidence gap):

- Anchor, inside the default root: `<root>/plugin-data/hmp/instance/` (0700) holding
  `instance_key.pem` (PKCS#8, 0600) and `instance_cert.pem` (the public certificate).
- Binding, outside every Hermes home: `<binding_root>/<anchor_key>/` (0700) holding
  `binding.json` (0600: `iid`, hashed host id, store revocation epoch, a pending flag) and
  `k_grace` (32 raw bytes, 0600). `<binding_root>` is `$XDG_STATE_HOME/hermes-hmp`, else
  `~/.local/state/hermes-hmp` (POSIX), else `%LOCALAPPDATA%/hermes-hmp` (Windows).
  `anchor_key` is derived from the anchor's real path, so two homes on one host never share a
  binding.
- Host id: `secret_hash("HMP1-HOST", length_prefixed(source, value))`, where `source` names the OS
  identifier and `value` is its normalized text (`host_id_input`). Only the hash is stored.

Detection on every load (store first, then files; a crash at any point is completed on the next
load, never rolled back):

| Situation | Outcome |
|---|---|
| key, binding, host and epoch agree | load; repair the binding epoch upward if the store is ahead |
| no key and no binding | first run: new identity |
| key without a binding (home copied, or restored onto another host) | clone/backup: new identity |
| binding without a key, or an unreadable key | key lost: new identity |
| binding for another key | key replaced: new identity |
| host hash differs | host change: new identity |
| store epoch below the binding's | store restored from a backup: new identity |
| binding marked pending | an interrupted change: completed now |

A new identity always runs `store.revoke_all_for_identity_change` first (every device revoked,
every family revoked, every open offer and pending pairing expired, epoch bumped, in one store
transaction; PR7-2), then writes a new key, a new `k_grace` and the binding. The binding is marked
pending before the store call and cleared last.

SEC-1: all of this holds only up to the Hermes OS-user boundary. Same-user code can read the key
and `k_grace`. Nothing in this module logs; callers log only `change_reason` codes (SEC-4).
"""

from __future__ import annotations

import _ssl
import contextlib
import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from cryptography.hazmat.primitives.asymmetric import ec

from . import crypto
from .contract import TAG_HOST

K_GRACE_BYTES = 32
BINDING_FORMAT = 1

PLUGIN_DATA_PARTS = ("plugin-data", "hmp", "instance")
KEY_FILENAME = "instance_key.pem"
CERT_FILENAME = "instance_cert.pem"
BINDING_FILENAME = "binding.json"
K_GRACE_FILENAME = "k_grace"
BINDING_ROOT_NAME = "hermes-hmp"
LOCK_FILENAME = ".lock"

DIR_MODE = 0o700
FILE_MODE = 0o600

# Host-id sources (the `source` field of the HMP1-HOST input).
HOST_SOURCE_DARWIN = "darwin-ioplatformuuid"
HOST_SOURCE_LINUX = "linux-machine-id"
HOST_SOURCE_WINDOWS = "windows-machineguid"
_IOREG = "/usr/sbin/ioreg"
_IOREG_UUID = re.compile(r'"IOPlatformUUID"\s*=\s*"([0-9A-Fa-f-]{36})"')
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_MACHINE_ID = re.compile(r"[0-9a-f]{32}")
_LINUX_MACHINE_ID_FILES = (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id"))


class IdentityError(RuntimeError):
    """The identity cannot be loaded or created. The listener must not start (fail closed)."""


class NamedProfileError(IdentityError):
    """ID-2: HMP runs under a named profile. A second identity is refused; so is sharing one."""


class HostIdUnavailableError(IdentityError):
    """No OS host identifier: the host binding cannot be checked, so nothing is served."""


class CustodyError(IdentityError):
    """A custody location violates ID-2 (for example, the binding inside a Hermes home)."""


class IdentityNotReadyError(IdentityError):
    """`load_existing`: there is no current identity to load here. Only the gateway's adapter
    (`load_or_create`) may create one or re-key one; a load-only caller refuses instead."""


class ChangeReason(StrEnum):
    """Why a load produced a new identity. Safe to log (an outcome code, no values)."""

    NONE = "none"
    FIRST_RUN = "first_run"
    CLONE_OR_BACKUP = "clone_or_backup"  # key present, no binding for this anchor on this host
    KEY_LOST = "key_lost"
    KEY_REPLACED = "key_replaced"
    HOST_CHANGED = "host_changed"
    STORE_RESTORED = "store_restored"
    INTERRUPTED = "interrupted"
    ROTATED = "rotated"


class IdentityStore(Protocol):
    """What identity custody needs from `store.py` (T021).

    `revoke_all_for_identity_change` runs ONE transaction: every device REVOKED, every token
    family revoked (its access tokens unusable), every open offer and every pending pairing
    expired, `meta.store_revocation_epoch` incremented (even when nothing else changed), and one
    audit row. It returns the new epoch (PR7-2, PR7-6, ID-2).
    """

    def revocation_epoch(self) -> int: ...

    def revoke_all_for_identity_change(self, now: int) -> int: ...


class InstanceIdentity(Protocol):
    @property
    def iid(self) -> str: ...

    def private_key(self) -> Any: ...

    def certificate_der(self) -> bytes: ...

    def k_grace(self) -> bytes:
        """The 32-byte retry-grace key (research R16, CS-13): its own file, mode 0600, outside
        every Hermes home, never in SQLite, never logged or printed. Regenerated on `rotate-key`,
        on clone/backup/host-change detection, and when missing or unreadable. Consumed by T026."""
        ...

    def still_current(self) -> bool:
        """False once the key was rotated or the binding broke (PR7-6 step 1)."""
        ...


# --------------------------------------------------------------------------------------------------
# Host id (HMP1-HOST; research R17)
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class HostId:
    source: str
    value: str

    def __repr__(self) -> str:  # never print the raw identifier
        return f"HostId(source={self.source!r})"


def host_id_input(host: HostId) -> bytes:
    """The HMP1-HOST hash input: `u32be(len source) || source || u32be(len value) || value`."""
    return crypto.length_prefixed(host.source, host.value)


def host_hash(host: HostId) -> str:
    """`secret_hash("HMP1-HOST", host_id_input)` as lowercase hex: the only stored form."""
    return crypto.secret_hash(TAG_HOST, host_id_input(host)).hex()


def _darwin_host_id() -> HostId | None:
    try:
        out = subprocess.run(  # noqa: S603 - fixed absolute path and arguments, no input
            [_IOREG, "-rd1", "-c", "IOPlatformExpertDevice"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = _IOREG_UUID.search(out)
    return HostId(HOST_SOURCE_DARWIN, match.group(1).lower()) if match else None


def _linux_host_id() -> HostId | None:
    for path in _LINUX_MACHINE_ID_FILES:
        try:
            value = path.read_text(encoding="ascii").strip().lower()
        except (OSError, UnicodeDecodeError):
            continue
        if _MACHINE_ID.fullmatch(value) and value != "0" * 32:
            return HostId(HOST_SOURCE_LINUX, value)
    return None


def _windows_host_id() -> HostId | None:  # pragma: no cover - exercised on Windows only
    try:
        import winreg

        with winreg.OpenKey(  # type: ignore[attr-defined]
            winreg.HKEY_LOCAL_MACHINE,  # type: ignore[attr-defined]
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,  # type: ignore[attr-defined]
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")  # type: ignore[attr-defined]
    except (ImportError, OSError):
        return None
    value = str(value).strip().lower()
    return HostId(HOST_SOURCE_WINDOWS, value) if _UUID.fullmatch(value) else None


def detect_host_id() -> HostId:
    """The OS host identifier. Raises `HostIdUnavailableError` rather than guessing."""
    if sys.platform == "darwin":
        host = _darwin_host_id()
    elif sys.platform == "win32":
        host = _windows_host_id()
    else:
        host = _linux_host_id()
    if host is None:
        raise HostIdUnavailableError("no OS host identifier is available")
    return host


# --------------------------------------------------------------------------------------------------
# Locations
# --------------------------------------------------------------------------------------------------


def _default_hermes_root() -> Path:
    # IR-6 ruling (a): the one Hermes import this module may make, lazily.
    from hermes_constants import get_default_hermes_root

    return Path(get_default_hermes_root())


def _expand(path: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(path)))


def _native_hermes_home(env: Mapping[str, str]) -> Path:
    """Hermes's documented platform default home (`~/.hermes`; `%LOCALAPPDATA%/hermes`)."""
    if sys.platform == "win32":  # pragma: no cover - Windows only
        base = env.get("LOCALAPPDATA", "").strip()
        return (Path(base) if base else Path.home() / "AppData" / "Local") / "hermes"
    return Path.home() / ".hermes"


def default_binding_root(env: Mapping[str, str]) -> Path:
    """`$XDG_STATE_HOME/hermes-hmp`, else `~/.local/state/hermes-hmp`; Windows:
    `%LOCALAPPDATA%/hermes-hmp`."""
    if sys.platform == "win32":  # pragma: no cover - Windows only
        base = env.get("LOCALAPPDATA", "").strip()
        return (Path(base) if base else Path.home() / "AppData" / "Local") / BINDING_ROOT_NAME
    xdg = env.get("XDG_STATE_HOME", "").strip()
    base = Path(xdg) if xdg and Path(xdg).is_absolute() else Path.home() / ".local" / "state"
    return base / BINDING_ROOT_NAME


def anchor_key(anchor_dir: Path) -> str:
    """Directory name of an anchor's binding: 32 hex chars over the anchor's real path."""
    real = os.path.realpath(anchor_dir)
    return hashlib.sha256(crypto.length_prefixed("hmp-anchor-v1", real)).hexdigest()[:32]


def _overlaps(a: Path, b: Path) -> bool:
    ra, rb = Path(os.path.realpath(a)), Path(os.path.realpath(b))
    return ra == rb or ra in rb.parents or rb in ra.parents


@dataclass(frozen=True)
class Custody:
    """Resolved custody locations for one identity load."""

    hermes_root: Path
    anchor_dir: Path
    binding_dir: Path

    @property
    def key_path(self) -> Path:
        return self.anchor_dir / KEY_FILENAME

    @property
    def cert_path(self) -> Path:
        return self.anchor_dir / CERT_FILENAME

    @property
    def binding_path(self) -> Path:
        return self.binding_dir / BINDING_FILENAME

    @property
    def k_grace_path(self) -> Path:
        return self.binding_dir / K_GRACE_FILENAME


def resolve_custody(
    *,
    env: Mapping[str, str] | None = None,
    hermes_root: Path | None = None,
    binding_root: Path | None = None,
) -> Custody:
    """Resolve and check every custody location (ID-2). Writes nothing.

    Raises `NamedProfileError` when the process's Hermes home is not the default root, and
    `CustodyError` when the binding location overlaps any Hermes home.
    """
    env = os.environ if env is None else env
    root = Path(hermes_root) if hermes_root is not None else _default_hermes_root()
    raw_home = env.get("HERMES_HOME", "").strip()
    process_home = _expand(raw_home) if raw_home else root
    if os.path.realpath(process_home) != os.path.realpath(root):
        raise NamedProfileError(
            "HMP runs only under the default profile; a named profile gets no identity"
        )
    anchor = root.joinpath(*PLUGIN_DATA_PARTS)
    b_root = Path(binding_root) if binding_root is not None else default_binding_root(env)
    if not b_root.is_absolute():
        raise CustodyError("the binding location must be an absolute path")
    for home in (root, process_home, _native_hermes_home(env)):
        if _overlaps(b_root, home):
            raise CustodyError("the binding location overlaps a Hermes home")
    return Custody(hermes_root=root, anchor_dir=anchor, binding_dir=b_root / anchor_key(anchor))


# --------------------------------------------------------------------------------------------------
# Files: private directories and atomic 0600 writes
# --------------------------------------------------------------------------------------------------


def _private_dir(path: Path) -> None:
    path.mkdir(mode=DIR_MODE, parents=True, exist_ok=True)
    os.chmod(path, DIR_MODE)


def _write_private(path: Path, data: bytes) -> None:
    """Write `data` to `path` atomically, mode 0600 from creation (never world-readable)."""
    _private_dir(path.parent)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{crypto.random_bytes(4).hex()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(tmp, flags, FILE_MODE)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, FILE_MODE)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _read_private(path: Path) -> bytes | None:
    """Read a custody file, tightening its mode to 0600. None when absent or unreadable."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return None
    try:
        with os.fdopen(fd, "rb") as fh:
            data = fh.read()
    except OSError:
        return None
    try:
        os.chmod(path, FILE_MODE)
    except OSError:
        return None
    return data


@contextlib.contextmanager
def _custody_lock(custody: Custody) -> Iterator[None]:
    """Serialize loads and rotations across processes (the gateway and the operator CLI).

    An advisory `flock` on a file in the binding directory; a no-op where `fcntl` is missing."""
    _private_dir(custody.binding_dir)
    try:
        import fcntl
    except ImportError:  # pragma: no cover - Windows
        yield
        return
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(custody.binding_dir / LOCK_FILENAME, flags, FILE_MODE)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)  # releases the lock


def _stat_sig(path: Path) -> tuple[int, int, int] | None:
    try:
        st = os.stat(path, follow_symlinks=False)
    except OSError:
        return None
    return (st.st_ino, st.st_mtime_ns, st.st_size)


# --------------------------------------------------------------------------------------------------
# Binding record
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Binding:
    iid: str
    host_hash: str
    revocation_epoch: int
    pending: bool = False

    def to_bytes(self) -> bytes:
        return json.dumps(
            {
                "format": BINDING_FORMAT,
                "iid": self.iid,
                "host_hash": self.host_hash,
                "revocation_epoch": self.revocation_epoch,
                "pending": self.pending,
            },
            sort_keys=True,
        ).encode("utf-8")

    @staticmethod
    def parse(data: bytes | None) -> Binding | None:
        if data is None:
            return None
        try:
            obj = json.loads(data.decode("utf-8"))
            if obj.get("format") != BINDING_FORMAT:
                return None
            epoch = obj["revocation_epoch"]
            if type(epoch) is not int or epoch < 0:
                return None
            binding = Binding(
                iid=str(obj["iid"]),
                host_hash=str(obj["host_hash"]),
                revocation_epoch=epoch,
                pending=obj.get("pending") is True,
            )
        except (ValueError, KeyError, TypeError, AttributeError):
            return None
        return binding


def _read_key(path: Path) -> ec.EllipticCurvePrivateKey | None:
    data = _read_private(path)
    if data is None:
        return None
    try:
        return crypto.private_key_from_pem(data)
    except crypto.CryptoError:
        return None


def _iid_of(key: ec.EllipticCurvePrivateKey) -> str:
    return crypto.spki_fingerprint(crypto.spki_der(key.public_key()))


def _read_or_create_k_grace(path: Path) -> bytes:
    data = _read_private(path)
    if data is not None and len(data) == K_GRACE_BYTES:
        return data
    fresh = crypto.random_bytes(K_GRACE_BYTES)
    _write_private(path, fresh)
    return fresh


# --------------------------------------------------------------------------------------------------
# The loaded identity
# --------------------------------------------------------------------------------------------------


class LoadedIdentity:
    """One loaded instance identity. Implements `InstanceIdentity`."""

    def __init__(
        self,
        custody: Custody,
        key: ec.EllipticCurvePrivateKey,
        binding: Binding,
        change_reason: ChangeReason,
    ) -> None:
        self._custody = custody
        self._key = key
        self._iid = _iid_of(key)
        self._binding = binding
        self._cert = crypto.self_signed_certificate(key)
        self.change_reason = change_reason
        self._sigs = self._current_sigs()
        self._current = True

    def __repr__(self) -> str:  # never print key material
        return f"LoadedIdentity(iid={self._iid[:8]}…, change_reason={self.change_reason.value})"

    @property
    def iid(self) -> str:
        return self._iid

    @property
    def custody(self) -> Custody:
        return self._custody

    def private_key(self) -> ec.EllipticCurvePrivateKey:
        return self._key

    def certificate_der(self) -> bytes:
        return self._cert

    def k_grace(self) -> bytes:
        return _read_or_create_k_grace(self._custody.k_grace_path)

    def _current_sigs(self) -> tuple[object, object]:
        return (_stat_sig(self._custody.key_path), _stat_sig(self._custody.binding_path))

    def still_current(self) -> bool:
        """PR7-6 step 1. Cheap when nothing changed (two `stat` calls). Once False, stays False:
        the process must stop terminating TLS and signing with this key."""
        if not self._current:
            return False
        sigs = self._current_sigs()
        if sigs == self._sigs:
            return True
        key = _read_key(self._custody.key_path)
        binding = Binding.parse(_read_private(self._custody.binding_path))
        ok = (
            key is not None
            and _iid_of(key) == self._iid
            and binding is not None
            and not binding.pending
            and binding.iid == self._iid
            and binding.host_hash == self._binding.host_hash
        )
        if ok:
            self._sigs = sigs
        else:
            self._current = False
        return self._current

    def server_ssl_context(self) -> ssl.SSLContext:
        """TLS 1.3 only, with the self-signed certificate over the instance key (TR-1, TR-8).

        The key is loaded from its 0600 file; no second copy is written. If the key was rotated
        after this identity loaded, the certificate and key disagree and this raises (fail
        closed)."""
        if not self.still_current():
            raise IdentityError("the instance identity changed; reload it")
        cert_pem = ssl.DER_cert_to_PEM_cert(self._cert).encode("ascii")
        _write_private(self._custody.cert_path, cert_pem)
        ctx = new_stdlib_ssl_context(ssl.PROTOCOL_TLS_SERVER)
        set_ssl_context_attr(ctx, "minimum_version", ssl.TLSVersion.TLSv1_3)
        set_ssl_context_attr(ctx, "maximum_version", ssl.TLSVersion.TLSv1_3)
        ctx.load_cert_chain(str(self._custody.cert_path), str(self._custody.key_path))
        return ctx


# --------------------------------------------------------------------------------------------------
# The listener's TLS context, immune to a host's process-wide client-trust injection (TR-1)
#
# A host process may replace the `ssl.SSLContext` module global for the whole process with a
# client-trust class (for example `truststore.inject_into_ssl()`, which some Hermes builds call at
# startup). Such a class verifies the peer against the platform trust store on every handshake,
# including the server side, where there is no client certificate: on macOS every handshake then
# fails. The listener context is therefore always an instance of the standard library's own class,
# found by its identity rather than through the replaceable global. While such an injection is
# active, the stdlib property setters recurse (they call `super(SSLContext, SSLContext)`, which
# resolves the replaced global), so the listener's settings are written through the C-level
# `_ssl._SSLContext` descriptors, which are exactly what those setters delegate to.
# --------------------------------------------------------------------------------------------------


def _stdlib_ssl_context_class() -> type[ssl.SSLContext]:
    """The standard library's `ssl.SSLContext` class, whatever the `ssl.SSLContext` global is now.

    It is the class defined in `ssl` as `SSLContext` directly over `_ssl._SSLContext`, in the
    current global's MRO (an injected class subclasses it). Fails closed if it is not there."""
    for cls in ssl.SSLContext.__mro__:
        if (
            cls.__module__ == "ssl"
            and cls.__qualname__ == "SSLContext"
            and cls.__bases__ == (_ssl._SSLContext,)
        ):
            return cls
    raise IdentityError("the standard library TLS context class is unavailable")


def new_stdlib_ssl_context(protocol: ssl._SSLMethod) -> ssl.SSLContext:
    """A context of exactly the standard library's own class (never an injected subclass)."""
    cls = _stdlib_ssl_context_class()
    ctx = cls(protocol)
    if type(ctx) is not cls:
        raise IdentityError("the standard library TLS context class is unavailable")
    return ctx


def set_ssl_context_attr(ctx: ssl.SSLContext, name: str, value: Any) -> None:
    """Set one `SSLContext` setting through its C-level descriptor (see the section comment)."""
    getattr(_ssl._SSLContext, name).__set__(ctx, value)


# --------------------------------------------------------------------------------------------------
# Load, create, rotate
# --------------------------------------------------------------------------------------------------


def _now() -> int:
    return int(time.time())


def _new_identity(
    custody: Custody,
    store: IdentityStore,
    host: str,
    reason: ChangeReason,
    previous: Binding | None,
    now: int,
) -> LoadedIdentity:
    """Store first, then files. Every step is completed by the next load if interrupted."""
    _private_dir(custody.anchor_dir)
    _private_dir(custody.binding_dir)
    marker = Binding(
        iid=previous.iid if previous else "",
        host_hash=host,
        revocation_epoch=previous.revocation_epoch if previous else 0,
        pending=True,
    )
    _write_private(custody.binding_path, marker.to_bytes())
    epoch = store.revoke_all_for_identity_change(now)
    key = crypto.generate_private_key()
    _write_private(custody.key_path, crypto.private_key_to_pem(key))
    _write_private(custody.k_grace_path, crypto.random_bytes(K_GRACE_BYTES))
    binding = Binding(iid=_iid_of(key), host_hash=host, revocation_epoch=epoch)
    _write_private(custody.binding_path, binding.to_bytes())
    return LoadedIdentity(custody, key, binding, reason)


def _classify(
    key: ec.EllipticCurvePrivateKey | None,
    key_file_present: bool,
    binding: Binding | None,
    host: str,
    store_epoch: int,
) -> ChangeReason:
    if binding is not None and binding.pending:
        return ChangeReason.INTERRUPTED
    if key is None:
        if binding is None and not key_file_present:
            return ChangeReason.FIRST_RUN
        return ChangeReason.KEY_LOST
    if binding is None:
        return ChangeReason.CLONE_OR_BACKUP
    if binding.host_hash != host:
        return ChangeReason.HOST_CHANGED
    if binding.iid != _iid_of(key):
        return ChangeReason.KEY_REPLACED
    if store_epoch < binding.revocation_epoch:
        return ChangeReason.STORE_RESTORED
    return ChangeReason.NONE


def load_or_create(
    store: IdentityStore,
    *,
    env: Mapping[str, str] | None = None,
    hermes_root: Path | None = None,
    binding_root: Path | None = None,
    host_id: Callable[[], HostId] = detect_host_id,
    now: int | None = None,
) -> LoadedIdentity:
    """Load the instance identity, creating a new one (and revoking every device) whenever the
    custody checks in the module docstring find a first run, a clone, a backup or a host change.

    The keyword arguments exist for tests; production passes only `store`.
    """
    custody = resolve_custody(env=env, hermes_root=hermes_root, binding_root=binding_root)
    host = host_hash(host_id())
    with _custody_lock(custody):
        return _load_locked(custody, store, host, _now() if now is None else now)


def _load_locked(custody: Custody, store: IdentityStore, host: str, now: int) -> LoadedIdentity:
    key = _read_key(custody.key_path)
    binding = Binding.parse(_read_private(custody.binding_path))  # unreadable counts as missing
    store_epoch = store.revocation_epoch()
    reason = _classify(key, custody.key_path.exists(), binding, host, store_epoch)
    if reason is not ChangeReason.NONE:
        return _new_identity(custody, store, host, reason, binding, now)
    if key is None or binding is None:  # pragma: no cover - excluded by _classify
        raise IdentityError("inconsistent custody state")
    if store_epoch > binding.revocation_epoch:
        # The store is ahead: a crash after its revoke committed. Repair upward, never down.
        binding = Binding(iid=binding.iid, host_hash=host, revocation_epoch=store_epoch)
        _write_private(custody.binding_path, binding.to_bytes())
    _read_or_create_k_grace(custody.k_grace_path)
    return LoadedIdentity(custody, key, binding, ChangeReason.NONE)


def _read_only(path: Path) -> bytes | None:
    """Read a custody file without touching it (no mode change, no symlink). None if absent."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return None
    try:
        with os.fdopen(fd, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def load_existing(
    store: IdentityStore,
    *,
    env: Mapping[str, str] | None = None,
    hermes_root: Path | None = None,
    binding_root: Path | None = None,
    host_id: Callable[[], HostId] = detect_host_id,
) -> LoadedIdentity:
    """Load the current instance identity, or refuse. Load only: this never creates, re-keys,
    rotates, repairs or writes anything, and never revokes a device.

    The operator CLI uses this. Any situation in which `load_or_create` would make a new
    identity (first run, clone or backup, a lost or replaced key, a host change, a restored store,
    an interrupted change), or would repair the binding, raises `IdentityNotReadyError`. A CLI
    run in a different environment (another root, host or binding location) therefore changes
    nothing. Only the gateway's adapter creates or re-keys the identity.
    """
    custody = resolve_custody(env=env, hermes_root=hermes_root, binding_root=binding_root)
    host = host_hash(host_id())
    data = _read_only(custody.key_path)
    key = None
    if data is not None:
        try:
            key = crypto.private_key_from_pem(data)
        except crypto.CryptoError:
            key = None
    binding = Binding.parse(_read_only(custody.binding_path))
    store_epoch = store.revocation_epoch()
    reason = _classify(key, custody.key_path.exists(), binding, host, store_epoch)
    if (
        reason is not ChangeReason.NONE
        or key is None
        or binding is None
        or store_epoch != binding.revocation_epoch
    ):
        raise IdentityNotReadyError("no current instance identity here")
    return LoadedIdentity(custody, key, binding, ChangeReason.NONE)


def rotate_key(
    store: IdentityStore,
    *,
    env: Mapping[str, str] | None = None,
    hermes_root: Path | None = None,
    binding_root: Path | None = None,
    host_id: Callable[[], HostId] = detect_host_id,
    now: int | None = None,
    require_current: bool = False,
) -> LoadedIdentity:
    """New key; every device revoked; every open offer and pending pairing expired (PR7-2).

    A running gateway sees `still_current()` turn False on its next watchdog tick or request and
    stops serving the old key (PR7-6). `k_grace` is regenerated too (R16).

    `require_current=True` (the operator CLI, SR-9): the same classification `load_existing`
    uses runs under THIS call's own custody lock, atomically with the rotation itself -- not as a
    separate, unlocked check beforehand. A caller that checked `load_existing` and then called
    `rotate_key` separately left a window in which a concurrent gateway re-key (or any other
    custody change) between the two could be silently rotated over. Refuses exactly when
    `load_existing` would (`IdentityNotReadyError`), and changes nothing on refusal.
    """
    custody = resolve_custody(env=env, hermes_root=hermes_root, binding_root=binding_root)
    host = host_hash(host_id())
    with _custody_lock(custody):
        previous = Binding.parse(_read_private(custody.binding_path))
        if require_current:
            key = _read_key(custody.key_path)
            store_epoch = store.revocation_epoch()
            reason = _classify(key, custody.key_path.exists(), previous, host, store_epoch)
            if (
                reason is not ChangeReason.NONE
                or key is None
                or previous is None
                or store_epoch != previous.revocation_epoch
            ):
                raise IdentityNotReadyError("no current instance identity here")
        return _new_identity(
            custody, store, host, ChangeReason.ROTATED, previous, _now() if now is None else now
        )
