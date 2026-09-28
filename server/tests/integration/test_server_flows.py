"""T035: server integration suite on a real gateway, two instances, both builds.

The first pass (`feat(f1): T035 server integration suite (partial)`) covered the acceptance items
testable through `tools/fixtures/build_fixture.py --serve`'s BUILT-IN reference device (its access
token, issued at build time) alone:

- **Cross-instance rejection** (TR-5 `auth.py`): instance A's `HMP-Instance` header/bearer token
  presented to instance B's listener, both the header-mismatch case (`401 wrong_instance`, before
  any token lookup) and the token-not-found case (B's own `iid` header, A's token: `401
  unauthenticated`, since A's token hash was never written to B's store).
- **413 at the wire** (`MAX_BODY_BYTES`, TR-9): a request body over the limit is refused `413
  too_large` by the real `aiohttp` listener, not merely by a unit-level `wire.py` check.
- **Zero hand-off on write paths** (FR-053): the F1 route table has no submit/write route at all.
  `POST`/`PUT`/`DELETE` against every read path answer `404`/`405`, confirmed against the real,
  running listener rather than only the static `F1_ROUTES` table.

This pass finishes the EVIDENCE_GAP that left open: the items that need a device that keeps its
own signing key across several signed requests, which the built-in reference device (a throwaway
key, discarded the moment it is paired) cannot do. `refclient.py`'s `ReferenceDevice` supplies
that. Added here, via the `gateway` fixture (a second, independent fixture from `two_instances`
above so the already-passing tests above are untouched):

- the full P1 -> P7 flow (`test_full_p1_to_p7_flow`), ending in self-revoke and the `401 revoked`
  that follows it;
- the wrong-pin abort (`test_wrong_pin_abort_sends_zero_application_bytes`), with server-side
  evidence (the offer row is untouched) that the P2 body never reached the application layer;
- pairing-code non-relay through a real `hermes -p <profile> pairing approve hmp <id>`
  (`test_pairing_code_never_relayed`): the code never appears in the HMP response or in either log;
- operator revoke (`test_operator_revoke_device`);
- PR7-6 instance-key rotation under a pty (`test_rotate_key_pre_rotation_device_sees_no_200`): a
  pre-rotation device sees a pin mismatch or a connection failure, never `200`;
- P5 rotation plus the PR5-5 grace retry across a gateway restart
  (`test_p5_grace_retry_survives_gateway_restart`).

Roster, snapshot and history are already covered end-to-end by `test_reads_fixture.py` (T030) and
are not duplicated here.

`family-revoke stream close` (this task's T035 line item) does not apply to F1: F1 serves no live
tail at all (`reads.py`: "F1 serves no live tail (FR-053)"), and the real route table below has no
streaming route to close. There is nothing to test.

At most one gateway runs at a time (host load); every test stops its gateway.
"""

from __future__ import annotations

import hashlib
import http.client
import importlib.util
import json
import os
import ssl
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BUILD_FIXTURE = REPO_ROOT / "tools" / "fixtures" / "build_fixture.py"
FIXTURES_DIR = REPO_ROOT / "tools" / "fixtures"
CI_DIR = REPO_ROOT / "tools" / "ci"
BUILDS = ("stock-base", "experimental")

for _p in (FIXTURES_DIR,):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import _fixture_common as fc  # noqa: E402

from . import refclient  # noqa: E402

# `tools/ci/scan_logs.py` is not a package (it lives outside every `__init__.py`-rooted package
# this test could import with a dotted name), so it is loaded by file path, exactly once, the same
# way `tools/ci/check_all.sh`'s own generic checker loop treats every `tools/ci/*.py` script: a
# standalone module, never imported as part of `hmp_plugin` or `tests`.
_scan_logs_spec = importlib.util.spec_from_file_location("_t035_scan_logs", CI_DIR / "scan_logs.py")
assert _scan_logs_spec is not None and _scan_logs_spec.loader is not None
scan_logs = importlib.util.module_from_spec(_scan_logs_spec)
_scan_logs_spec.loader.exec_module(scan_logs)

pytestmark = [
    pytest.mark.skipif(
        not BUILD_FIXTURE.is_file(),
        reason="needs T060 tools/fixtures/build_fixture.py (fixture builder not landed yet)",
    ),
    pytest.mark.skipif(
        not os.environ.get("HMP_HERMES_BUILDS_DIR"),
        reason="needs HMP_HERMES_BUILDS_DIR with extracted builds and venvs (T004)",
    ),
]


class Served:
    def __init__(self, proc: subprocess.Popen[str], info: dict[str, Any]) -> None:
        self.proc = proc
        self.info = info

    def request(
        self,
        method: str,
        path: str,
        *,
        iid: str | None = None,
        token: str | None = None,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Any]:
        """A raw request over real TLS (no cert verification -- the pin is T041's job, not what
        is under test here). Returns `(status, parsed-json-or-None)`."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        conn = http.client.HTTPSConnection("127.0.0.1", self.info["port"], context=ctx, timeout=10)
        hdrs = dict(headers or {})
        if iid is not None:
            hdrs["HMP-Instance"] = iid
        if token is not None:
            hdrs["Authorization"] = f"Bearer {token}"
        try:
            conn.request(method, path, body=body, headers=hdrs)
            resp = conn.getresponse()
            raw = resp.read()
            parsed = json.loads(raw) if raw else None
            return resp.status, parsed
        finally:
            conn.close()

    def stop(self) -> None:
        self.proc.terminate()
        self.proc.wait(timeout=30)


def _serve(label: str, out: Path) -> dict[str, Served]:
    proc = subprocess.Popen(
        [sys.executable, str(BUILD_FIXTURE), "--build", label, "--out", str(out), "--serve"],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    served: dict[str, Served] = {}
    for _ in range(2):
        info = json.loads(proc.stdout.readline())
        served[info["key"]] = Served(proc, info)
    return served


def _stop(served: dict[str, Served]) -> None:
    next(iter(served.values())).stop()


@pytest.fixture(params=BUILDS)
def two_instances(
    request: pytest.FixtureRequest, tmp_path: Path
) -> Iterator[dict[str, Served]]:
    out = tmp_path / "fixture"
    served = _serve(request.param, out)
    try:
        yield served
    finally:
        _stop(served)


# --------------------------------------------------------------------------------------------------
# Cross-instance rejection (TR-5)
# --------------------------------------------------------------------------------------------------


def test_wrong_instance_header_rejected_before_token_lookup(
    two_instances: dict[str, Served],
) -> None:
    """A's own (header, token) pair, sent to B: the header names A's `iid`, which never equals
    B's real `iid`, so `auth.py` refuses `401 wrong_instance` at step 1 -- before it ever looks up
    A's token in B's store."""
    a, b = two_instances["A"], two_instances["B"]
    status, body = b.request(
        "GET", "/hmp/v1/bots", iid=a.info["iid"], token=a.info["device"]["access_token"]
    )
    assert status == 401, body
    assert body["error"]["code"] == "wrong_instance"


def test_foreign_token_rejected_under_the_right_instance_header(
    two_instances: dict[str, Served],
) -> None:
    """B's own `iid` (so step 1 passes) with A's token: A's token hash was never written to B's
    store (each instance has its own isolated store, `contracts/fixture-format.md` rule 1), so the
    lookup at step 3 finds nothing -- `401 unauthenticated`, never treated as if it were B's own
    revoked or expired token."""
    a, b = two_instances["A"], two_instances["B"]
    status, body = b.request(
        "GET", "/hmp/v1/bots", iid=b.info["iid"], token=a.info["device"]["access_token"]
    )
    assert status == 401, body
    assert body["error"]["code"] == "unauthenticated"


def test_each_instances_own_token_is_accepted(two_instances: dict[str, Served]) -> None:
    """Sanity check for the two tests above: each instance's OWN (iid, token) pair still works,
    so the rejections above are really about the cross-instance mismatch, not a broken fixture."""
    for served in two_instances.values():
        token = served.info["device"]["access_token"]
        status, body = served.request("GET", "/hmp/v1/bots", iid=served.info["iid"], token=token)
        assert status == 200, body


# --------------------------------------------------------------------------------------------------
# 413 at the wire (TR-9, MAX_BODY_BYTES)
# --------------------------------------------------------------------------------------------------


def test_oversized_body_is_413_at_the_real_listener(two_instances: dict[str, Served]) -> None:
    a = two_instances["A"]
    # MAX_BODY_BYTES is 8192 (contract.py §13); one byte over it, on a real POST route.
    oversized = b"x" * (8_192 + 1)
    status, body = a.request(
        "POST",
        "/hmp/v1/bots/f1-alpha/authorize",
        iid=a.info["iid"],
        token=a.info["device"]["access_token"],
        body=oversized,
        headers={"Content-Type": "application/json", "Content-Length": str(len(oversized))},
    )
    assert status == 413, body
    assert body["error"]["code"] == "too_large"


def test_declared_content_length_over_limit_is_413_without_reading_body(
    two_instances: dict[str, Served],
) -> None:
    """The `Content-Length` header alone, over the limit, is refused before the body is even
    read (`server.py`'s `_json_body`): a slow-body attacker cannot hold the connection open past
    the point of refusal."""
    a = two_instances["A"]
    status, body = a.request(
        "POST",
        "/hmp/v1/bots/f1-alpha/authorize",
        iid=a.info["iid"],
        token=a.info["device"]["access_token"],
        body=b"{}",
        headers={"Content-Type": "application/json", "Content-Length": str(8_192 + 1)},
    )
    assert status == 413, body
    assert body["error"]["code"] == "too_large"


# --------------------------------------------------------------------------------------------------
# Zero hand-off on write paths (FR-053): no submit route exists, confirmed live
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/hmp/v1/bots/f1-alpha/conversations/default/messages"),
        ("PUT", "/hmp/v1/bots/f1-alpha/conversations/default/messages"),
        ("DELETE", "/hmp/v1/bots/f1-alpha/conversations/default/messages"),
        ("POST", "/hmp/v1/bots/f1-alpha/conversations/default"),
        ("PUT", "/hmp/v1/bots/f1-alpha/conversations/default"),
        ("POST", "/hmp/v1/bots"),
        ("PUT", "/hmp/v1/bots/f1-alpha/authorize"),
    ],
)
def test_no_write_route_exists_on_the_real_listener(
    two_instances: dict[str, Served], method: str, path: str
) -> None:
    """F1 registers reads, pairing/auth and the P6 authorize trigger only (`server.py`'s
    `F1_ROUTES`) -- never a route that could hand conversation content to Hermes for a write. Every
    method/path combination outside that fixed table is refused `404 not_found` by
    `error_middleware` (server.py: "Write paths are not registered and answer 404 (FR-053)" --
    deliberately never `405`, so a probe cannot learn which methods exist on a path that IS
    registered for a different one)."""
    a = two_instances["A"]
    status, body = a.request(
        method, path, iid=a.info["iid"], token=a.info["device"]["access_token"], body=b"{}"
    )
    assert status == 404, f"{method} {path} unexpectedly answered {status}: {body}"
    assert body["error"]["code"] == "not_found"


# ------------------------------------------------------------------------------------------------
# T035 EVIDENCE_GAP close-out: tests below need a device that keeps its own signing key across
# several signed requests (`refclient.ReferenceDevice`), not just the built-in reference device's
# already-issued token. They share the `gateway` fixture, independent of `two_instances` above.
# ------------------------------------------------------------------------------------------------


@dataclass
class Gateway:
    """One `--serve` run's full context: the running instances (`served`, from `_serve`, reused
    unchanged) plus what the tests below additionally need that `Served.info` does not carry --
    each instance's isolated `home`/`xdg_state` (`fixture_meta.json`, written by `build_fixture.py`
    BEFORE it starts serving, so it is stable by the time `_serve` returns) and the target build's
    own venv python (`_fixture_common.resolve_build`, the same resolver `build_fixture.py` itself
    uses)."""

    label: str
    out: Path
    served: dict[str, Served]

    def meta(self) -> dict[str, Any]:
        return json.loads((self.out / "fixture_meta.json").read_text(encoding="utf-8"))

    def instance_meta(self, key: str) -> dict[str, Any]:
        return next(i for i in self.meta()["instances"] if i["key"] == key)

    def venv_python(self) -> str:
        build = fc.resolve_build(os.environ["HMP_HERMES_BUILDS_DIR"], self.label)
        return str(build.venv_python)

    def instance_paths(self, key: str) -> fc.InstancePaths:
        meta = self.instance_meta(key)
        return fc.InstancePaths(
            home=Path(meta["home"]), xdg_state=Path(meta["xdg_state"]), out_dir=self.out
        )

    def restart(self) -> None:
        """Stops and re-`_serve()`s the SAME `--out` directory (test_reads_fixture.py's own
        restart pattern): the store, profiles and instance identity survive; the port may change
        (`serve_instances` picks a fresh free port every call), so callers must re-read
        `self.served` afterwards."""
        _stop(self.served)
        self.served = _serve(self.label, self.out)

    def log_path(self, key: str) -> Path:
        return self.out / "gateway_logs" / f"{key}.log"


@pytest.fixture(params=BUILDS)
def gateway(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[Gateway]:
    label = request.param
    out = tmp_path / "fixture"
    gw = Gateway(label=label, out=out, served=_serve(label, out))
    try:
        yield gw
    finally:
        # `gw.served`, not a `served` local captured at setup: `Gateway.restart()` (used by
        # `test_p5_grace_retry_survives_gateway_restart`) reassigns `gw.served` to a NEW `_serve()`
        # result, and stopping only the pre-restart dict here would leak the post-restart gateway
        # processes forever (found by real orphaned `hermes gateway run` processes during this
        # task's own test runs -- fixed here, not worked around).
        _stop(gw.served)


def _authorized_profile(meta: dict[str, Any]) -> dict[str, Any]:
    return next(p for p in meta["profiles"] if p["authorized"])


def _pending_profile(meta: dict[str, Any]) -> dict[str, Any]:
    return next(p for p in meta["profiles"] if not p["authorized"])


def _pair_fresh_device(
    gw: Gateway, *, key: str = "A", label: str
) -> tuple[refclient.ReferenceDevice, dict[str, Any], str]:
    """P1-P4 with a `ReferenceDevice`, via the real offer/confirm scripts. Returns
    `(device, instance_meta, venv_python)`."""
    served = gw.served[key]
    meta = gw.instance_meta(key)
    venv_python = gw.venv_python()
    profile = _authorized_profile(meta)
    user_id = profile["user_id"]
    endpoint = f"https://127.0.0.1:{served.info['port']}"

    offer = refclient.mint_offer(
        venv_python, meta["home"], meta["xdg_state"], endpoint=endpoint, user=user_id, label=label
    )
    device = refclient.ReferenceDevice(
        host="127.0.0.1", port=served.info["port"], iid=offer["iid"]
    )
    p2 = device.pair_request(offer)
    refclient.confirm_pairing(
        venv_python,
        meta["home"],
        meta["xdg_state"],
        sas=p2["device_sas"],
        label=label,
        user=user_id,
    )
    device.pair_complete()
    return device, meta, venv_python


def test_full_p1_to_p7_flow(gateway: Gateway) -> None:
    """P1 (offer) -> P2 (pair/request) -> P3 (operator confirm) -> P4 (pair/complete) -> an
    authenticated read with the issued access token -> P5 (auth/token refresh) -> another
    authenticated read with the rotated access token -> P7 self-revoke -> the next request is
    `401 revoked` (ERR-2)."""
    device, meta, _venv = _pair_fresh_device(gateway, label="f1-fixture-label-t035-full-flow")
    profile = _authorized_profile(meta)

    assert device.device_id is not None
    assert device.access_token is not None

    status, body = device.authed_request("GET", "/hmp/v1/bots")
    assert status == 200, body
    assert any(b["profile"] == profile["name"] for b in body["bots"]), body

    before_access = device.access_token
    before_refresh = device.refresh_token
    refreshed = device.refresh()
    assert refreshed["access_token"] != before_access
    assert refreshed["refresh_token"] != before_refresh

    status, body = device.authed_request("GET", "/hmp/v1/bots")
    assert status == 200, body

    status, body = device.self_revoke()
    assert status == 200, body

    status, body = device.authed_request("GET", "/hmp/v1/bots")
    assert status == 401, body
    assert body["error"]["code"] == "revoked", body


def test_wrong_pin_abort_sends_zero_application_bytes(gateway: Gateway) -> None:
    """TR-2: a device correctly pinned to instance A's real `iid` (from a real offer A minted --
    exactly what a real device pins from a real QR code), but whose connection actually reaches
    instance B's listener (a genuinely different, independently running instance's real
    certificate -- not a fabricated fingerprint), aborts before sending a single P2 byte. Evidence
    is server-side, not just "the client raised": A's offer row is unchanged -- still `open`,
    `failures` still 0 -- proving the P2 body reached neither A (never sent there) nor, through
    the pin, B either."""
    a = gateway.served["A"]
    b = gateway.served["B"]
    meta_a = gateway.instance_meta("A")
    venv_python = gateway.venv_python()
    endpoint_a = f"https://127.0.0.1:{a.info['port']}"
    user_id = _authorized_profile(meta_a)["user_id"]

    offer = refclient.mint_offer(
        venv_python,
        meta_a["home"],
        meta_a["xdg_state"],
        endpoint=endpoint_a,
        user=user_id,
        label="f1-fixture-label-t035-wrong-pin",
    )
    before = refclient.get_offer_state(
        venv_python, meta_a["home"], meta_a["xdg_state"], offer["oid"]
    )
    assert before == {"ok": True, "found": True, "state": "open", "failures": 0}, before

    assert b.info["iid"] != a.info["iid"]  # a genuine mismatch, not a synthetic one
    # Pinned to A's real iid (from A's real offer), but connecting to B's real listener: a
    # genuine SPKI mismatch, the same shape TR-2 defends against (the peer is not who the pin
    # says it should be), without fabricating a fingerprint that no running instance actually has.
    device = refclient.ReferenceDevice(host="127.0.0.1", port=b.info["port"], iid=offer["iid"])
    with pytest.raises(refclient.PinMismatchError) as exc_info:
        device.pair_request(offer)
    assert exc_info.value.reason == "spki_mismatch"

    after = refclient.get_offer_state(
        venv_python, meta_a["home"], meta_a["xdg_state"], offer["oid"]
    )
    assert after == before, "the offer changed -- the P2 body reached the application layer"


def _candidate_pairing_codes(text: str) -> list[str]:
    """Every 8-character substring shaped like a Hermes pairing code (`scan_logs.py`'s own
    case-insensitive `HERMES_PAIRING_CODE_RE`, deliberately WITHOUT its digit filter): the
    maximal-recall candidate set for `_assert_exact_code_absent` below to hash-check, since the
    digit filter itself has an accepted ~10% blind spot for a genuinely all-letter code (see
    `scan_logs.py`'s HERMES_PAIRING_CODE docstring) that this exact-match check must not share."""
    return [m.group(0) for m in scan_logs.HERMES_PAIRING_CODE_RE.finditer(text)]


def _assert_exact_code_absent(
    text: str, *, code_hash: str, code_salt_hex: str, where: str
) -> None:
    """Confirms none of `text`'s pairing-code-shaped candidates IS the exact code issued for a
    given request -- by hashing each candidate with the request's own salt
    (`gateway/pairing.py` `PairingStore._hash_code`: `sha256(salt + code.upper())`) and comparing
    against its stored hash, the same compare `approve_code` itself does. This is a precise,
    false-positive-free check (unlike the generic HERMES_PAIRING_CODE scan kept below as a
    secondary, defense-in-depth check): it never needs to know or guess the plaintext code, only
    whether a given candidate hashes to the one that was actually issued."""
    salt = bytes.fromhex(code_salt_hex)
    for candidate in _candidate_pairing_codes(text):
        normalized = "".join(candidate.upper().split())
        digest = hashlib.sha256(salt + normalized.encode("utf-8")).hexdigest()
        assert digest != code_hash, (
            f"the exact issued Hermes pairing code was relayed in {where}: {candidate!r}"
        )


def test_pairing_code_never_relayed(gateway: Gateway) -> None:
    """PR6-2: a live P6 trigger against a not-yet-authorized profile mints a real Hermes pairing
    code (`gateway/pairing.py`), and the operator approves it through the real
    `hermes -p <profile> pairing approve hmp <request_id>` CLI. The code itself never appears in
    the HMP response body, the gateway log, or the CLI's own stdout/stderr.

    Two layers, per this task's fix for the SEC-11 regression where the generic scan alone
    started flagging ordinary English words ("embedded", "database", ...) in Hermes's own log
    boilerplate as false positives:

    - Primary: `_assert_exact_code_absent` hashes every pairing-code-shaped candidate string
      found in each surface with the SPECIFIC request's own salt (fetched read-only from the
      Hermes pairing store, before it is approved and the entry is deleted) and confirms none
      hashes to the code that was actually issued. This is exact -- it cannot be fooled by an
      unrelated dictionary word, and it cannot miss the real code regardless of its shape.
    - Secondary: the same scanner (`tools/ci/scan_logs.py`, T033) `check_all.sh` runs over CI
      evidence, `find_hermes_pairing_code`, as defense in depth against a leak that is
      pairing-code-shaped but did not happen to be caught above (e.g. a differently-encoded
      rendering) -- not a bespoke regex here.
    """
    meta = gateway.instance_meta("A")
    venv_python = gateway.venv_python()
    pending = _pending_profile(meta)

    device, _meta, _venv = _pair_fresh_device(gateway, label="f1-fixture-label-t035-p6")
    user_id = device.user_ref  # the caller's own HMP user, from P4's issued `user_ref`

    status, body = device.authed_request(
        "POST", f"/hmp/v1/bots/{pending['name']}/authorize", body=b"{}"
    )
    assert status == 202, body
    assert body["authz"] == "pending_operator", body
    assert body["user_id"] == user_id, body
    assert "instruction" in body
    # approve_command (owner requirement, 2026-09-27): additive 202 field, same no-code-relay
    # contract as `instruction` -- covered by the whole-body scan below, and also names the
    # profile and user_id explicitly here.
    assert "approve_command" in body
    assert pending["name"] in body["approve_command"]
    assert user_id in body["approve_command"]
    body_text = json.dumps(body, sort_keys=True)
    assert scan_logs.find_hermes_pairing_code(body_text) == [], body

    request_id = refclient.find_pending_p6_request(
        venv_python, meta["home"], profile=pending["name"], user_id=user_id
    )
    # Read-only, and BEFORE approval: approving the request deletes its pending entry.
    code_hash = refclient.get_pending_code_hash(
        venv_python, meta["home"], profile=pending["name"], request_id=request_id
    )
    _assert_exact_code_absent(
        body_text, code_hash=code_hash["hash"], code_salt_hex=code_hash["salt"],
        where="the HMP authorize response",
    )

    build_info = fc.resolve_build(os.environ["HMP_HERMES_BUILDS_DIR"], gateway.label)
    approve = fc.run_hermes_cli(
        build_info,
        gateway.instance_paths("A"),
        "-p",
        pending["name"],
        "pairing",
        "approve",
        "hmp",
        request_id,
    )
    assert approve.returncode == 0, approve.stdout + approve.stderr
    assert scan_logs.find_hermes_pairing_code(approve.stdout) == [], approve.stdout
    assert scan_logs.find_hermes_pairing_code(approve.stderr) == [], approve.stderr
    _assert_exact_code_absent(
        approve.stdout, code_hash=code_hash["hash"], code_salt_hex=code_hash["salt"],
        where="the pairing approve CLI's stdout",
    )
    _assert_exact_code_absent(
        approve.stderr, code_hash=code_hash["hash"], code_salt_hex=code_hash["salt"],
        where="the pairing approve CLI's stderr",
    )

    status, body = device.authed_request(
        "POST", f"/hmp/v1/bots/{pending['name']}/authorize", body=b"{}"
    )
    assert status == 200 and body["authz"] == "authorized", body

    # PR6-2's own claim is specifically about the Hermes pairing CODE (never the broader
    # "the log has no findings of any kind" -- `tools/ci/scan_logs.py`'s other signal classes
    # cover unrelated wire secrets, and this task's final report notes a known false-positive
    # interaction between its generic TOKEN_B64U heuristic and this CI environment's own
    # deeply-nested scratch paths, which is not an HMP secret and out of this task's scope to
    # change in a shared, security-reviewed file). Use the scanner's own code-matching function
    # directly against the full log text, precisely scoped to what this test actually claims.
    log_text = gateway.log_path("A").read_text(encoding="utf-8", errors="replace")
    assert scan_logs.find_hermes_pairing_code(log_text) == []
    _assert_exact_code_absent(
        log_text, code_hash=code_hash["hash"], code_salt_hex=code_hash["salt"],
        where="the gateway log",
    )


def test_operator_revoke_device(gateway: Gateway) -> None:
    """PR7-1: `hermes hmp devices revoke <device_id>` (real CLI, under a pty) revokes only the
    named device; the next request from it is `401 revoked`."""
    device, meta, venv_python = _pair_fresh_device(gateway, label="f1-fixture-label-t035-revoke")

    status, body = device.authed_request("GET", "/hmp/v1/bots")
    assert status == 200, body

    refclient.devices_revoke(venv_python, meta["home"], meta["xdg_state"], device.device_id)

    status, body = device.authed_request("GET", "/hmp/v1/bots")
    assert status == 401, body
    assert body["error"]["code"] == "revoked", body


def test_rotate_key_pre_rotation_device_sees_no_200(gateway: Gateway) -> None:
    """PR7-6: after `hermes hmp instance rotate-key` (real CLI, under a pty), a pre-rotation
    device polling with its OLD pin sees either a pin mismatch (the listener restarted under the
    new key) or a connection failure (the listener stayed closed) -- and, per PR7-6 step 5, is
    never promised any particular HTTP status; this only asserts it never sees `200`."""
    device, meta, venv_python = _pair_fresh_device(gateway, label="f1-fixture-label-t035-rotate")

    status, body = device.authed_request("GET", "/hmp/v1/bots")
    assert status == 200, body

    refclient.rotate_instance_key(venv_python, meta["home"], meta["xdg_state"])

    deadline = time.monotonic() + 20.0
    outcome: str | None = None
    while time.monotonic() < deadline:
        try:
            status, body = device.authed_request("GET", "/hmp/v1/bots")
        except refclient.PinMismatchError:
            outcome = "pin_mismatch"
            break
        except OSError:
            outcome = "connection_failure"
            break
        else:
            assert status != 200, f"pre-rotation device got 200 after rotate-key: {body}"
            time.sleep(1.0)
    assert outcome in ("pin_mismatch", "connection_failure"), (
        "the gateway never rotated (pin mismatch or connection failure) within 20s"
    )


def test_p5_grace_retry_survives_gateway_restart(gateway: Gateway) -> None:
    """PR5-5: presenting the SAME (now-superseded) refresh token again, while its successor is
    unused, returns that SAME successor again -- and this "MUST survive a gateway restart"
    (PR5-5, research R16's durable `k_grace` derivation, replacing the spike's in-memory grace
    state). The device's connection target is re-read after the restart because `serve_instances`
    may pick a fresh port; the instance identity (`iid`) is unaffected by an ordinary restart."""
    device, _meta, _venv = _pair_fresh_device(gateway, label="f1-fixture-label-t035-grace")

    original_refresh = device.refresh_token
    first = device.refresh()  # rotates: original_refresh's successor, now unused

    gateway.restart()
    device.port = gateway.served["A"].info["port"]

    status, retried = device.token_exchange(original_refresh)
    assert status == 200, retried
    assert retried["access_token"] == first["access_token"], retried
    assert retried["refresh_token"] == first["refresh_token"], retried
