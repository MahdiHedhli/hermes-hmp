"""T035: a standalone Python HMP wire reference client. TEST TOOLING ONLY -- never imported by
`server/hmp_plugin` (`tools/ci/check_plugin_surface.py`, T013).

This is the piece the previous T035 pass (`feat(f1): T035 server integration suite (partial)`)
flagged as missing: `tools/fixtures/build_fixture.py --serve`'s built-in reference device only
ever hands out its ALREADY-ISSUED access token (`fixture_pairing_cli.py`'s
`pair-reference-client`, which mints and immediately discards a throwaway device key inside one
subprocess). A device that KEEPS its own P-256 keypair for the life of the test is needed to drive
P2/P4/P5/P7 with fresh, correctly-signed `HMP1-*` transcripts on demand: the wrong-pin abort, P5
rotation and its grace retry, and self-revoke all need more than one signed request from the SAME
device identity.

Design (contracts/HMP_V1.md `docs/architecture/contracts/HMP_V1.md` §5, §3 TR-2/TR-13):

- `ReferenceDevice` keeps the keypair and drives P2 (`pair_request`), P4 (`pair_complete`), P5
  (`token_exchange`/`refresh`) and P7 self-revoke (`self_revoke`). It reuses
  `hmp_plugin.crypto`/`contract`/`wire` for every transcript, signature and b64u operation --
  never reimplementing them (the module docstring of `crypto.py`: "Must pass every ... vector").
- `PinnedConnection` (TR-2) does the client's own unconditional post-handshake SPKI pin check by
  hand: an empty-trust-store, platform-verification-disabled `SSLContext` (so the pin compare is
  the ONLY thing that can ever reject a bad peer), and a `connect()` override that raises
  `PinMismatchError` -- closing the socket -- strictly before `HTTPConnection.request()` is ever
  called, so a mismatch writes zero HTTP bytes. This is intentionally a separate, minimal
  implementation from the Dart `PinnedConnector` (T041): this module is Python test tooling
  exercising the wire contract from the outside, not a copy of the mobile client under test.
- P1 (offer minting) and P3 (operator confirmation) are NOT reimplemented here: they run through
  the existing, unedited `tools/fixtures/fixture_pairing_cli.py` script as a subprocess (`offer`/
  `confirm`, plus this task's additive `rotate-key`/`devices-revoke`/`get-offer-state`
  subcommands), exactly as `build_fixture.py` and the Dart real-server tests already do -- never
  duplicated in this module.

Every device name this module sends in P2 starts with `f1-fixture-device-`
(`contracts/fixture-format.md` rule 7, CS-22) so the log scanner's fixture-prefix check can catch
it if it ever leaked.
"""

from __future__ import annotations

import http.client
import json
import socket
import ssl
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_DIR = REPO_ROOT / "server"
FIXTURES_DIR = REPO_ROOT / "tools" / "fixtures"
FIXTURE_PAIRING_CLI = FIXTURES_DIR / "fixture_pairing_cli.py"
for _p in (SERVER_DIR, FIXTURES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from hmp_plugin import contract, crypto, wire  # noqa: E402

DEVICE_NAME_PREFIX = "f1-fixture-device-"  # contracts/fixture-format.md rule 7 (CS-22)


class RefClientError(Exception):
    """Base class for reference-client errors: protocol violations the client itself detects.
    Ordinary HTTP error responses are never raised -- callers see them as `(status, body)`."""


class PinMismatchError(RefClientError):
    """TR-2: the peer certificate's SPKI does not match the pinned `iid`. Raised by
    `PinnedConnection.connect()` BEFORE any HTTP request line or header is written."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ProtocolError(RefClientError):
    """A response failed a client-side protocol check: a bad `isig`, or a `device_sas` mismatch
    (PR2-4: "it aborts and destroys DK")."""


class PinnedConnection(http.client.HTTPSConnection):
    """TR-2's unconditional post-handshake SPKI pin check, done by hand. The TLS context below
    carries no trusted roots and disables platform verification entirely (`verify_mode =
    CERT_NONE`), so the pin compare in `connect()` is the ONLY thing that can ever reject a bad
    peer -- matching TR-2's "empty trust store (configuration requirement)" plus its own
    unconditional check, not relying on the trust store to do any rejecting.

    `connect()` performs the raw TCP connect and TLS handshake itself, extracts the peer
    certificate's SPKI, and compares its fingerprint with the pinned `iid`. On a mismatch it
    closes the socket and raises `PinMismatchError` WITHOUT ever calling `putrequest`/`send`: since
    `HTTPConnection.request()` only calls `self.connect()` when `self.sock is None`, and this
    override either sets `self.sock` (match) or raises (mismatch, `self.sock` left `None`), a
    caller that lets this exception propagate is guaranteed to have written zero request bytes --
    the "abort must send zero application bytes" property is structural, not a timing race."""

    def __init__(self, host: str, port: int, *, pinned_iid: str, timeout: float = 15.0) -> None:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # TR-2: empty trust store -- the pin below is what gates
        super().__init__(host, port, timeout=timeout, context=ctx)
        self._pinned_iid = pinned_iid
        self.verified_spki_der: bytes | None = None

    def connect(self) -> None:
        raw_sock = socket.create_connection((self.host, self.port), self.timeout)
        try:
            ssl_sock = self._context.wrap_socket(raw_sock, server_hostname=None)
        except Exception:
            raw_sock.close()
            raise
        der_cert = ssl_sock.getpeercert(binary_form=True)
        if not der_cert:
            ssl_sock.close()
            raise PinMismatchError("no_peer_certificate")
        try:
            spki = crypto.certificate_spki(der_cert)
            fingerprint = crypto.spki_fingerprint(spki)
        except Exception:
            ssl_sock.close()
            raise PinMismatchError("unparseable_certificate") from None
        if not crypto.constant_time_equal(fingerprint, self._pinned_iid):
            ssl_sock.close()  # TR-2: closed before any application byte is written
            raise PinMismatchError("spki_mismatch")
        self.verified_spki_der = spki
        self.sock = ssl_sock


class ReferenceDevice:
    """The device side of P1-P5 and P7 self-revoke. Generates and keeps a P-256 keypair for the
    life of the object (unlike `fixture_pairing_cli.py`'s throwaway `pair-reference-client`)."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        iid: str,
        device_name: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.host = host
        self.port = port
        self.iid = iid
        self.timeout = timeout
        self.device_name = device_name or (
            DEVICE_NAME_PREFIX + "refclient-" + wire.b64u_encode(crypto.random_bytes(6))
        )
        if not self.device_name.startswith(DEVICE_NAME_PREFIX):
            raise ValueError(f"device_name must start with {DEVICE_NAME_PREFIX!r} (CS-22)")

        self.device_priv = crypto.generate_private_key()
        self.device_pub_der = crypto.spki_der(self.device_priv.public_key())
        self.device_fp = crypto.spki_fingerprint(self.device_pub_der)

        # Filled in as pairing/token exchange proceeds:
        self.pairing_id: str | None = None
        self.nd: bytes | None = None
        self.ni: bytes | None = None
        self.device_id: str | None = None
        self.user_ref: str | None = None
        self.access_token: str | None = None
        self.access_expires_at: int | None = None
        self.refresh_token: str | None = None  # current raw refresh token, canonical b64u text

    # -- transport (TR-2) --------------------------------------------------------------------

    def _connect(self) -> PinnedConnection:
        conn = PinnedConnection(self.host, self.port, pinned_iid=self.iid, timeout=self.timeout)
        conn.connect()  # raises PinMismatchError, sending nothing, before any request is built
        return conn

    def raw_request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Any, bytes]:
        """A single request over a fresh, pin-checked connection (TR-2: "on every connection").
        Returns `(status, parsed_json_or_None, verified_peer_spki_der)`. Raises `PinMismatchError`
        before sending anything if the pin fails."""
        conn = self._connect()
        try:
            hdrs = dict(headers or {})
            if body is not None:
                hdrs.setdefault("Content-Type", "application/json")
            conn.request(method, path, body=body, headers=hdrs)
            resp = conn.getresponse()
            raw = resp.read()
            parsed = json.loads(raw) if raw else None
            return resp.status, parsed, conn.verified_spki_der or b""
        finally:
            conn.close()

    def authed_request(
        self, method: str, path: str, *, body: bytes | None = None
    ) -> tuple[int, Any]:
        if self.access_token is None:
            raise RefClientError("no access token yet -- pair and complete P4 first")
        status, parsed, _ = self.raw_request(
            method,
            path,
            body=body,
            headers={"Authorization": f"Bearer {self.access_token}", "HMP-Instance": self.iid},
        )
        return status, parsed

    # -- P2: pair/request (PR2-1..PR2-5) ------------------------------------------------------

    def pair_request(self, offer: dict[str, Any]) -> dict[str, Any]:
        """`offer` is the parsed `hmp1:` JSON body (`{"v","iid","ep","oid","s","exp"}`). Verifies
        `isig` under the SPKI the pin just checked (TR-2 + TR-13), then verifies the server's
        `device_sas` equals this device's own locally computed SAS (PR2-4: "displays the SAS
        only if it equals its own locally computed sas(fingerprint(DK))"). Raises
        `ProtocolError` on either failure and does not store pairing state -- PR2-4: "otherwise it
        aborts and destroys DK" (the caller should discard this `ReferenceDevice`)."""
        if offer["iid"] != self.iid:
            raise RefClientError("offer iid does not match this device's pinned iid")
        oid_raw = wire.b64u_decode(offer["oid"], length=16)
        secret = wire.b64u_decode(offer["s"], length=32)
        nd = crypto.random_bytes(32)
        message = crypto.transcript(
            contract.TAG_PAIR_REQ,
            offer["iid"],
            oid_raw,
            crypto.sha256(secret),
            self.device_pub_der,
            self.device_name,
            nd,
        )
        body = {
            "v": contract.PROTOCOL_VERSION,
            "oid": offer["oid"],
            "s": offer["s"],
            "device_name": self.device_name,
            "device_pub": wire.b64u_encode(self.device_pub_der),
            "nd": wire.b64u_encode(nd),
            "sig": wire.b64u_encode(crypto.sign(self.device_priv, message)),
        }
        status, parsed, peer_spki = self.raw_request(
            "POST", "/hmp/v1/pair/request", body=json.dumps(body).encode()
        )
        if status != 202:
            raise RefClientError(f"P2 pair/request failed: {status} {parsed}")

        ni_raw = wire.b64u_decode(parsed["ni"], length=32)
        pairing_raw = wire.b64u_decode(parsed["pairing_id"], length=16)
        isig_message = crypto.transcript(
            contract.TAG_PAIR_RESP,
            offer["iid"],
            oid_raw,
            self.device_pub_der,
            nd,
            ni_raw,
            pairing_raw,
            parsed["device_sas"],
            parsed["confirm_by"],
        )
        if not crypto.verify(peer_spki, wire.b64u_signature(parsed["isig"]), isig_message):
            raise ProtocolError("isig did not verify under the pinned instance key")
        local_sas = crypto.device_sas(self.device_fp)
        if not crypto.constant_time_equal(local_sas, parsed["device_sas"]):
            raise ProtocolError("server device_sas does not match the locally computed SAS")

        self.pairing_id = parsed["pairing_id"]
        self.nd = nd
        self.ni = ni_raw
        return parsed

    # -- P4: pair/complete (PR4-1..PR4-4) -----------------------------------------------------

    def pair_complete_once(self) -> tuple[int, Any]:
        if self.pairing_id is None or self.nd is None or self.ni is None:
            raise RefClientError("call pair_request() first")
        ts = int(time.time())
        pairing_raw = wire.b64u_decode(self.pairing_id, length=16)
        message = crypto.transcript(
            contract.TAG_PAIR_DONE, self.iid, pairing_raw, self.nd, self.ni, ts
        )
        body = {
            "pairing_id": self.pairing_id,
            "ts": ts,
            "sig": wire.b64u_encode(crypto.sign(self.device_priv, message)),
        }
        status, parsed, _ = self.raw_request(
            "POST", "/hmp/v1/pair/complete", body=json.dumps(body).encode()
        )
        if status == 200:
            self.device_id = parsed["device_id"]
            self.user_ref = parsed["user_ref"]
            self.access_token = parsed["access_token"]
            self.access_expires_at = parsed["access_expires_at"]
            self.refresh_token = parsed["refresh_token"]
        return status, parsed

    def pair_complete(self, *, poll_interval: float = 2.0, timeout: float = 30.0) -> dict[str, Any]:
        """Polls P4 at >= 2 s intervals (PR4-1) until issued, denied or expired, or *timeout*
        elapses."""
        deadline = time.monotonic() + timeout
        while True:
            status, parsed = self.pair_complete_once()
            if status == 200:
                return parsed
            if status != 202:
                raise RefClientError(f"P4 pair/complete ended: {status} {parsed}")
            if time.monotonic() + poll_interval > deadline:
                raise TimeoutError("P4 polling timed out waiting for operator confirmation")
            time.sleep(poll_interval)

    # -- P5: auth/token (PR5-1..PR5-8) --------------------------------------------------------

    def token_exchange(self, refresh_token_b64u: str | None = None) -> tuple[int, Any]:
        """Does NOT mutate `self.access_token`/`self.refresh_token` -- callers that want the
        ordinary "rotate and adopt" flow use `refresh()`. This lower-level method lets a test
        present an arbitrary (including stale, for the PR5-5 grace-retry case) refresh token and
        inspect the raw response."""
        if self.device_id is None:
            raise RefClientError("not paired yet")
        raw_refresh = wire.b64u_decode(refresh_token_b64u or self.refresh_token, length=32)
        ts = int(time.time())
        nonce = crypto.random_bytes(16)
        message = crypto.transcript(
            contract.TAG_TOKEN, self.iid, self.device_id, crypto.sha256(raw_refresh), ts, nonce
        )
        body = {
            "device_id": self.device_id,
            "refresh_token": wire.b64u_encode(raw_refresh),
            "ts": ts,
            "nonce": wire.b64u_encode(nonce),
            "sig": wire.b64u_encode(crypto.sign(self.device_priv, message)),
        }
        status, parsed, _ = self.raw_request(
            "POST", "/hmp/v1/auth/token", body=json.dumps(body).encode()
        )
        return status, parsed

    def refresh(self) -> dict[str, Any]:
        status, parsed = self.token_exchange()
        if status != 200:
            raise RefClientError(f"P5 auth/token failed: {status} {parsed}")
        self.access_token = parsed["access_token"]
        self.access_expires_at = parsed["access_expires_at"]
        self.refresh_token = parsed["refresh_token"]
        return parsed

    # -- P7: devices/self/revoke (PR7-3) ------------------------------------------------------

    def self_revoke(self) -> tuple[int, Any]:
        if self.device_id is None:
            raise RefClientError("not paired yet")
        ts = int(time.time())
        message = crypto.transcript(contract.TAG_SELF_REVOKE, self.iid, self.device_id, ts)
        body = {"ts": ts, "sig": wire.b64u_encode(crypto.sign(self.device_priv, message))}
        return self.authed_request(
            "POST", "/hmp/v1/devices/self/revoke", body=json.dumps(body).encode()
        )


# --------------------------------------------------------------------------------------------------
# Operator-side helpers (P1, P3, P7 operator actions): subprocess wrappers around the existing,
# unedited `fixture_pairing_cli.py` (reused, never duplicated).
# --------------------------------------------------------------------------------------------------


def _run_pairing_cli(venv_python: str, *args: str, timeout: float = 30.0) -> str:
    result = subprocess.run(
        [venv_python, str(FIXTURE_PAIRING_CLI), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise RefClientError(
            f"fixture_pairing_cli.py {args[0]} failed (exit {result.returncode}): "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    return result.stdout


def mint_offer(
    venv_python: str, home: str, xdg_state: str, *, endpoint: str, user: str, label: str
) -> dict[str, Any]:
    """P1, via `fixture_pairing_cli.py offer`."""
    out = _run_pairing_cli(
        venv_python,
        "offer",
        "--home",
        home,
        "--xdg-state",
        xdg_state,
        "--endpoint",
        endpoint,
        "--user",
        user,
        "--label",
        label,
    )
    text = out.strip()
    if not text.startswith("hmp1:"):
        raise RefClientError(f"unexpected offer output: {text!r}")
    raw = wire.b64u_decode_bounded(text[len("hmp1:") :], max_length=4000)
    return json.loads(raw)


def confirm_pairing(
    venv_python: str, home: str, xdg_state: str, *, sas: str, label: str, user: str
) -> str:
    """P3, via `fixture_pairing_cli.py confirm` -- the REAL `hermes hmp pair confirm` under a
    pty (see that script's module docstring)."""
    return _run_pairing_cli(
        venv_python,
        "confirm",
        "--home",
        home,
        "--xdg-state",
        xdg_state,
        "--sas",
        sas,
        "--label",
        label,
        "--user",
        user,
    )


def rotate_instance_key(venv_python: str, home: str, xdg_state: str) -> str:
    """PR7-2/PR7-6, via `fixture_pairing_cli.py rotate-key` (this task's additive subcommand)."""
    return _run_pairing_cli(venv_python, "rotate-key", "--home", home, "--xdg-state", xdg_state)


def devices_revoke(venv_python: str, home: str, xdg_state: str, device_id: str) -> str:
    """PR7-1, via `fixture_pairing_cli.py devices-revoke` (this task's additive subcommand)."""
    return _run_pairing_cli(
        venv_python, "devices-revoke", "--home", home, "--xdg-state", xdg_state, device_id
    )


def get_offer_state(venv_python: str, home: str, xdg_state: str, oid: str) -> dict[str, Any]:
    """Read-only evidence for the wrong-pin-abort test (this task's additive subcommand)."""
    out = _run_pairing_cli(
        venv_python, "get-offer-state", "--home", home, "--xdg-state", xdg_state, "--oid", oid
    )
    return json.loads(out)


def find_pending_p6_request(
    venv_python: str, home: str, *, profile: str, user_id: str
) -> str:
    """T035: the `request_id` of a live P6-triggered "hmp" pairing request, via
    `fixture_seed.py find-pending-request` (this task's additive subcommand -- the read-only half
    of `cmd_p6_generate`, without minting a fresh code)."""
    fixture_seed = FIXTURES_DIR / "fixture_seed.py"
    result = subprocess.run(
        [
            venv_python,
            str(fixture_seed),
            "find-pending-request",
            "--home",
            home,
            "--profile",
            profile,
            "--user-id",
            user_id,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RefClientError(
            f"find-pending-request failed (exit {result.returncode}): "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    return json.loads(result.stdout)["request_id"]


def get_pending_code_hash(
    venv_python: str, home: str, *, profile: str, request_id: str
) -> dict[str, str]:
    """T035 (SEC-11 regression fix): `{"hash": ..., "salt": ...}` for a pending "hmp" pairing
    request, via `fixture_seed.py get-pending-code-hash` -- read-only, never the plaintext code
    (see that subcommand's docstring). Must be called before the request is approved or denied;
    approval deletes the pending entry. Lets a caller check whether a specific string IS the
    exact code that was issued, by hashing it with the same salt, without ever knowing the code
    itself."""
    fixture_seed = FIXTURES_DIR / "fixture_seed.py"
    result = subprocess.run(
        [
            venv_python,
            str(fixture_seed),
            "get-pending-code-hash",
            "--home",
            home,
            "--profile",
            profile,
            "--request-id",
            request_id,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RefClientError(
            f"get-pending-code-hash failed (exit {result.returncode}): "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    payload = json.loads(result.stdout)
    return {"hash": payload["hash"], "salt": payload["salt"]}
