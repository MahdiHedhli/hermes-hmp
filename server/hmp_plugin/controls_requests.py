"""Store-only request-host Controls protocol. No route or CLI enables this module by itself.

The caller must supply a bearer-authenticated origin and the current server IID, and must
perform the external bridge/config checks before a positive host decision. Those checks are
not SQLite authority. Every operation below serializes on Store.transaction(), including
legacy Controls writers, and refuses schema drift before reading a request.
"""

from __future__ import annotations

import re
import secrets
import sqlite3
import uuid
from dataclasses import dataclass

from .store import Store, _request_schema_valid

_MAX_I64 = (1 << 63) - 1
_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z", re.ASCII)
_IID = re.compile(r"[a-z2-7]{52}\Z", re.ASCII)
_PROFILE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z", re.ASCII)
_REQUEST_ID = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)
_CLIENT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z",
    re.ASCII,
)
_ORIGIN_WHERE = (
    "device_id = ? AND user_id = ? AND family_id = ? AND iid = ? "
    "AND instance_epoch = ? AND store_revocation_epoch = ?"
)


@dataclass(frozen=True)
class RequestOrigin:
    # Constructed only after normal bearer authentication and current server-identity readback.
    device_id: str
    user_id: str
    family_id: str
    iid: str
    instance_epoch: int
    store_revocation_epoch: int

    def values(self) -> tuple[str, str, str, str, int, int]:
        return (
            self.device_id, self.user_id, self.family_id, self.iid,
            self.instance_epoch, self.store_revocation_epoch,
        )


@dataclass(frozen=True)
class RequestStoreResult:
    code: str
    request_id: str | None = None
    state: str | None = None
    expires_at: int | None = None
    # A historical GRANTED state is never an effective entitlement. Only a successful host
    # write carries its committed revision; routes still need fresh effective-readiness proof.
    committed_revision: int | None = None


def _time(now: int) -> None:
    if type(now) is not int or not 0 <= now <= _MAX_I64 - 600:
        raise ValueError("invalid request clock")


def _origin(origin: RequestOrigin) -> None:
    if not isinstance(origin, RequestOrigin):
        raise ValueError("invalid request origin")
    if any(
        not isinstance(value, str) or _ID.fullmatch(value) is None
        for value in (origin.device_id, origin.user_id, origin.family_id)
    ):
        raise ValueError("invalid request origin")
    if not isinstance(origin.iid, str) or _IID.fullmatch(origin.iid) is None:
        raise ValueError("invalid request IID")
    if any(type(v) is not int or not 0 <= v <= _MAX_I64 for v in (
        origin.instance_epoch, origin.store_revocation_epoch
    )):
        raise ValueError("invalid request epoch")


def _client(client_id: str) -> None:
    if not isinstance(client_id, str) or _CLIENT_ID.fullmatch(client_id) is None:
        raise ValueError("invalid client request id")
    if str(uuid.UUID(client_id)) != client_id:
        raise ValueError("noncanonical client request id")


def _body(client_id: str, profile: str, feature: str) -> None:
    _client(client_id)
    if not isinstance(profile, str) or _PROFILE.fullmatch(profile) is None:
        raise ValueError("invalid profile")
    if feature not in ("jobs", "models"):
        raise ValueError("invalid feature")


def _ready(conn: sqlite3.Connection) -> None:
    if not _request_schema_valid(conn):
        raise RuntimeError("request schema unavailable")


def _clock(conn: sqlite3.Connection, now: int) -> bool:
    row = conn.execute("SELECT high_water FROM controls_request_clock WHERE id = 1").fetchone()
    if row is None or type(row["high_water"]) is not int:
        raise RuntimeError("request clock unavailable")
    high = row["high_water"]
    if now < high:
        return False
    if now > high:
        conn.execute("UPDATE controls_request_clock SET high_water = ? WHERE id = 1", (now,))
    return True


def _revision(conn: sqlite3.Connection, device_id: str) -> tuple[int, int | None]:
    rev = conn.execute(
        "SELECT revision FROM device_owner_controls_revision WHERE device_id = ?",
        (device_id,),
    ).fetchone()
    number = 0 if rev is None else rev["revision"]
    if type(number) is not int or not 0 <= number <= _MAX_I64:
        raise RuntimeError("invalid Controls revision")
    explicit = conn.execute(
        "SELECT allowed FROM device_owner_controls WHERE device_id = ?", (device_id,)
    ).fetchone()
    allowed = None if explicit is None else explicit["allowed"]
    if allowed is not None and (type(allowed) is not int or allowed not in (0, 1)):
        raise RuntimeError("invalid Controls row")
    if allowed is not None and number == 0:
        raise RuntimeError("unversioned Controls row")
    return number, allowed


def _current_origin(conn: sqlite3.Connection, origin: RequestOrigin) -> bool:
    row = conn.execute(
        "SELECT d.user_id,d.state,f.device_id,f.revoked_at,"
        "m.instance_epoch,m.store_revocation_epoch "
        "FROM devices AS d JOIN token_families AS f ON f.device_id = d.device_id "
        "JOIN meta AS m ON m.id = 1 WHERE d.device_id = ? AND f.family_id = ?",
        (origin.device_id, origin.family_id),
    ).fetchone()
    return bool(
        row is not None and row["user_id"] == origin.user_id
        and row["state"] == "ACTIVE" and row["device_id"] == origin.device_id
        and row["revoked_at"] is None
        and row["instance_epoch"] == origin.instance_epoch
        and row["store_revocation_epoch"] == origin.store_revocation_epoch
    )


def _result(row: sqlite3.Row, code: str = "ok") -> RequestStoreResult:
    return RequestStoreResult(
        code, row["request_id"], row["state"], row["expires_at"],
    )


def _settle(
    conn: sqlite3.Connection, row: sqlite3.Row, *, now: int, current_iid: str,
    clock_ok: bool = True,
) -> sqlite3.Row:
    if row["state"] != "PENDING":
        return row
    origin = RequestOrigin(
        row["device_id"], row["user_id"], row["family_id"], row["iid"],
        row["instance_epoch"], row["store_revocation_epoch"],
    )
    state: str | None = None
    if not _current_origin(conn, origin) or current_iid != row["iid"]:
        state = "REVOKED"
    else:
        revision, allowed = _revision(conn, row["device_id"])
        if revision != row["controls_revision"] or (allowed is None) != (
            row["controls_present"] == 0
        ) or allowed != row["controls_allowed"]:
            state = "CONFLICT"
        elif clock_ok and now >= row["expires_at"]:
            state = "EXPIRED"
    if state is None:
        return row
    changed = conn.execute(
        "UPDATE controls_requests SET state = ?,decided_at = ? "
        "WHERE request_id = ? AND state = 'PENDING'",
        (state, now, row["request_id"]),
    )
    if changed.rowcount != 1:
        raise RuntimeError("request settlement raced")
    return conn.execute(
        "SELECT * FROM controls_requests WHERE request_id = ?", (row["request_id"],)
    ).fetchone()


class ControlsRequestStore:
    """Private primitive. Routing and TTY presentation must independently enforce their gates."""

    def __init__(self, store: Store) -> None:
        self._store = store

    def create(
        self, origin: RequestOrigin, *, client_id: str, profile: str,
        feature: str, now: int, current_iid: str,
    ) -> RequestStoreResult:
        _origin(origin)
        _body(client_id, profile, feature)
        _time(now)
        if current_iid != origin.iid:
            return RequestStoreResult("unavailable")
        with self._store.transaction() as conn:
            _ready(conn)
            if not _clock(conn, now):
                return RequestStoreResult("clock_unknown")
            existing = conn.execute(
                "SELECT * FROM controls_requests WHERE " + _ORIGIN_WHERE + " AND client_id = ?",
                (*origin.values(), client_id),
            ).fetchone()
            if existing is not None:
                if existing["bot_profile"] != profile or existing["feature"] != feature:
                    return RequestStoreResult("conflict")
                return _result(_settle(conn, existing, now=now, current_iid=current_iid))
            if not _current_origin(conn, origin):
                return RequestStoreResult("unavailable")
            # Expired/stale rows cannot consume pending capacity forever. At most 64 are
            # inspectable because insertion itself enforces that global cap.
            for pending in conn.execute(
                "SELECT * FROM controls_requests WHERE state = 'PENDING'"
            ).fetchall():
                _settle(conn, pending, now=now, current_iid=current_iid)
            revision, allowed = _revision(conn, origin.device_id)
            checks = (
                ("SELECT COUNT(*) FROM controls_requests", (), 8192),
                ("SELECT COUNT(*) FROM controls_requests WHERE state = 'PENDING'", (), 64),
                ("SELECT COUNT(*) FROM controls_requests WHERE device_id = ? AND created_at > ?",
                 (origin.device_id, now - 86400), 4),
                ("SELECT COUNT(*) FROM controls_requests WHERE created_at > ?",
                 (now - 600,), 64),
                ("SELECT COUNT(*) FROM controls_requests WHERE device_id = ? AND state = 'PENDING'",
                 (origin.device_id,), 1),
            )
            for sql, args, cap in checks:
                if conn.execute(sql, args).fetchone()[0] >= cap:
                    return RequestStoreResult("quota")
            for _ in range(3):
                request_id = secrets.token_hex(16)
                if conn.execute(
                    "SELECT 1 FROM controls_requests WHERE request_id = ?", (request_id,)
                ).fetchone() is not None:
                    continue
                conn.execute(
                    "INSERT INTO controls_requests (request_id,device_id,user_id,family_id,iid,"
                    "instance_epoch,store_revocation_epoch,client_id,bot_profile,feature,"
                    "created_at,expires_at,controls_revision,controls_present,controls_allowed,"
                    "state) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'PENDING')",
                    (request_id, *origin.values(), client_id, profile, feature,
                     now, now + 600, revision, int(allowed is not None), allowed),
                )
                return RequestStoreResult(
                    "created", request_id, "PENDING", now + 600,
                )
            return RequestStoreResult("unavailable")

    def status(
        self, origin: RequestOrigin, *, client_id: str, now: int, current_iid: str
    ) -> RequestStoreResult:
        _origin(origin)
        _client(client_id)
        _time(now)
        with self._store.transaction() as conn:
            _ready(conn)
            clock_ok = _clock(conn, now)
            row = conn.execute(
                "SELECT * FROM controls_requests WHERE " + _ORIGIN_WHERE + " AND client_id = ?",
                (*origin.values(), client_id),
            ).fetchone()
            if row is None:
                return RequestStoreResult("not_found")
            row = _settle(
                conn, row, now=now, current_iid=current_iid, clock_ok=clock_ok
            )
            if not clock_ok and row["state"] == "PENDING":
                return RequestStoreResult("clock_unknown")
            return _result(row)

    def cancel(
        self, origin: RequestOrigin, *, client_id: str, now: int, current_iid: str
    ) -> RequestStoreResult:
        _origin(origin)
        _client(client_id)
        _time(now)
        with self._store.transaction() as conn:
            _ready(conn)
            clock_ok = _clock(conn, now)
            row = conn.execute(
                "SELECT * FROM controls_requests WHERE " + _ORIGIN_WHERE + " AND client_id = ?",
                (*origin.values(), client_id),
            ).fetchone()
            if row is None:
                return RequestStoreResult("not_found")
            row = _settle(conn, row, now=now, current_iid=current_iid, clock_ok=clock_ok)
            if row["state"] == "CANCELLED":
                return _result(row)
            if row["state"] != "PENDING":
                return RequestStoreResult("already_decided")
            conn.execute(
                "UPDATE controls_requests SET state = 'CANCELLED',decided_at = ? "
                "WHERE request_id = ? AND state = 'PENDING'", (now, row["request_id"])
            )
            return RequestStoreResult("cancelled", row["request_id"], "CANCELLED")

    def decide(
        self, request_id: str, *, allow: bool, now: int, current_iid: str,
        precommit_external_verified: bool,
    ) -> RequestStoreResult:
        """Called only by a TTY-confirmed host path after fresh bridge/config verification.

        A GRANTED row records the transaction, not an effective entitlement. The caller must
        perform a fresh effective-readiness readback and report unknown on failure, without
        replaying this mutation.
        """
        if not isinstance(request_id, str) or _REQUEST_ID.fullmatch(request_id) is None:
            raise ValueError("invalid request id")
        if type(allow) is not bool or type(precommit_external_verified) is not bool:
            raise ValueError("invalid decision flags")
        _time(now)
        if allow and not precommit_external_verified:
            return RequestStoreResult("unavailable")
        with self._store.transaction() as conn:
            _ready(conn)
            clock_ok = _clock(conn, now)
            if allow and not clock_ok:
                return RequestStoreResult("clock_unknown")
            row = conn.execute(
                "SELECT * FROM controls_requests WHERE request_id = ?", (request_id,)
            ).fetchone()
            if row is None:
                return RequestStoreResult("not_found")
            row = _settle(conn, row, now=now, current_iid=current_iid, clock_ok=clock_ok)
            if row["state"] != "PENDING":
                return RequestStoreResult("already_decided", request_id, row["state"])
            if allow:
                # Recheck the full origin and captured Controls state under the lock, after
                # external checks. The host has approved device-wide scope, not this bot alone.
                origin = RequestOrigin(
                    row["device_id"], row["user_id"], row["family_id"], row["iid"],
                    row["instance_epoch"], row["store_revocation_epoch"],
                )
                if not _current_origin(conn, origin) or current_iid != origin.iid:
                    return RequestStoreResult("unavailable")
                before, explicit = _revision(conn, origin.device_id)
                if before != row["controls_revision"] or explicit != row["controls_allowed"]:
                    return RequestStoreResult("conflict")
                conn.execute(
                    "INSERT INTO device_owner_controls (device_id,allowed,decided_at) "
                    "VALUES (?,1,?) ON CONFLICT(device_id) DO UPDATE SET "
                    "allowed = 1,decided_at = excluded.decided_at",
                    (origin.device_id, now),
                )
                after, value = _revision(conn, origin.device_id)
                if after != before + 1 or value != 1:
                    raise RuntimeError("Controls write readback failed")
                conn.execute(
                    "UPDATE controls_requests SET state = 'GRANTED',decided_at = ?,"
                    "decision_revision = ? WHERE request_id = ? AND state = 'PENDING'",
                    (now, after, request_id),
                )
                return RequestStoreResult(
                    "committed_needs_effective_readback", request_id, "GRANTED",
                    row["expires_at"], after,
                )
            conn.execute(
                "UPDATE controls_requests SET state = 'DENIED',decided_at = ? "
                "WHERE request_id = ? AND state = 'PENDING'", (now, request_id)
            )
            return RequestStoreResult("denied", request_id, "DENIED")

    def host_show(self, request_id: str, *, now: int, current_iid: str) -> RequestStoreResult:
        if not isinstance(request_id, str) or _REQUEST_ID.fullmatch(request_id) is None:
            raise ValueError("invalid request id")
        _time(now)
        with self._store.transaction() as conn:
            _ready(conn)
            clock_ok = _clock(conn, now)
            row = conn.execute(
                "SELECT * FROM controls_requests WHERE request_id = ?", (request_id,)
            ).fetchone()
            if row is None:
                return RequestStoreResult("not_found")
            row = _settle(
                conn, row, now=now, current_iid=current_iid, clock_ok=clock_ok
            )
            if not clock_ok and row["state"] == "PENDING":
                return RequestStoreResult("clock_unknown")
            return _result(row)
