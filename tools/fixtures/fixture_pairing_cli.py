#!/usr/bin/env python3
"""Fixture-mode HMP device-pairing (P1-P4) operator wrapper. TEST TOOLING ONLY.

`server/hmp_plugin/cli.py` (T032, "the operator CLI") refuses every mutating command without an
interactive TTY on both stdin and stdout (PR1-2, PR3-2) -- correct for a real operator, useless for
an unattended test process. This script exists so the real-server Dart tests (T052-T054,
`mobile/packages/hmp_client/test/fixture/fixture_server_test.dart`) can drive real P1-P4 pairing
against a fixture instance without a human at a terminal. It lives under `tools/fixtures/`, never
under `server/hmp_plugin/`, and `tools/ci/check_plugin_surface.py` (T013) is what makes that a
checked invariant, not just a convention: the plugin package must never import anything from here.

`confirm` and `deny` run the REAL `hermes hmp pair confirm` / `pair deny` (T032) -- the actual
state transition (SAS verification, the mismatch counter, `confirm_pairing`/`deny_pairing`) is
production code, not a fixture shortcut. They only need a way around the TTY gate, so they run it
under a real pseudo-terminal (`pty.openpty`, both stdin and stdout attached to the slave end):
`isatty()` is genuinely true, nothing about the check is bypassed or faked, and every other
refusal in `cli.py` (label shape, `--user`/`--yes-share`, SAS mismatch counting, "no such pending
pairing") still applies exactly as it would for a human operator. Finding *which* pending pairing
matches a given SAS or SAS group is done here with a short-lived read-only connection to the same
store (`server/hmp_plugin/store.py` is the only module that WRITES it; a human operator gets the
same list from `hermes hmp pair list`, which shows only the first SAS group -- full-SAS matching
needs the read this script does).

`offer` is the one operator step the real CLI can never do for a loopback fixture: `_cmd_offer`
(cli.py) calls `wire.require_endpoint`, which enforces CS-10 (an offer's `ep` must be a `*.ts.net`
name or a tailnet address -- never loopback), because a REAL offer must never point at 127.0.0.1.
A fixture instance's listener only ever binds loopback (T060's isolation rules), so `offer` here
builds the same `hmp1:` wire payload by hand, deliberately skipping that one production-only
check, and nothing else: `secret_hash`, the offer's storage and the instance identity it embeds
are all exactly what the real CLI would use (`identity.load_existing`, load-only, same as
`cli.py` -- the identity must already exist, which only the live gateway creates; see
`build_fixture.py`'s `--serve`).

Run under the target build's own venv python with `server/` on `PYTHONPATH`
(`_fixture_common.run_seed_script`); it never relies on an inherited environment, since the run
descriptor's `offer_cmd`/`confirm_cmd`/`deny_cmd` are re-invoked later, unattended, from Dart.
"""

from __future__ import annotations

import argparse
import json
import os
import pty
import selectors
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SERVER_DIR = REPO_ROOT / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))


def _fail(message: str) -> None:
    print(json.dumps({"ok": False, "error": message}), file=sys.stderr)
    sys.exit(1)


def _clean_env(home: str, xdg_state: str) -> dict[str, str]:
    """See the module docstring: `XDG_STATE_HOME` is set and `binding_root` is otherwise left for
    `identity.default_binding_root()` to derive, so every identity lookup here reaches the SAME
    custody location the live gateway does (never pass `xdg_state` straight through as a
    `binding_root=` kwarg -- that silently creates a second, sibling identity the running listener
    never sees)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("HERMES_", "XDG_"))}
    env["HERMES_HOME"] = home
    env["XDG_STATE_HOME"] = xdg_state
    return env


def _open_store(home: str, xdg_state: str):
    for key in list(os.environ):
        if key.startswith(("HERMES_", "XDG_")):
            del os.environ[key]
    os.environ["HERMES_HOME"] = home
    os.environ["XDG_STATE_HOME"] = xdg_state

    from hmp_plugin import identity
    from hmp_plugin import server as hmp_server
    from hmp_plugin.store import Store

    custody = identity.resolve_custody(hermes_root=Path(home))
    store = Store(hmp_server.store_path(custody.anchor_dir))
    store.migrate()
    return store, custody


def _mint_offer(
    home: str, xdg_state: str, *, endpoint: str, user: str | None, label: str | None
) -> tuple[str, str]:
    """Returns (`hmp1:` wire text, instance `iid`). See the module docstring's `offer` section."""
    from hmp_plugin import (
        contract,
        crypto,
        identity,
        wire,
    )

    del label  # advisory only, matches the real CLI's `--label` (not stored on the offer)
    store, _custody = _open_store(home, xdg_state)
    try:
        # Load-only, same as the real CLI (`_load_identity` in cli.py): the identity must already
        # exist. Only the live gateway's adapter creates or re-keys it (`--serve` first).
        try:
            ident = identity.load_existing(store, hermes_root=Path(home))
        except identity.IdentityError as exc:
            raise RuntimeError(
                "no current HMP instance identity here -- start the gateway with the hmp "
                "platform enabled first (build_fixture.py --serve)"
            ) from exc
        oid_raw = crypto.random_bytes(16)
        secret = crypto.random_bytes(32)
        now = int(time.time())
        exp = now + contract.OFFER_TTL_S
        oid = wire.b64u_encode(oid_raw)
        store.insert_offer(
            oid, crypto.secret_hash(contract.TAG_OFFER, secret), exp, intended_user_id=user
        )
        # PR1-3's shape, built by hand (see module docstring): a real offer's `ep` may never be
        # loopback (CS-10), but a fixture instance never binds anything else.
        body = {
            "v": contract.PROTOCOL_VERSION,
            "iid": ident.iid,
            "ep": [endpoint],
            "oid": oid,
            "s": wire.b64u_encode(secret),
            "exp": exp,
        }
        text = "hmp1:" + wire.b64u_encode(wire.dump_json(body))
    finally:
        store.close()
    return text, ident.iid


def cmd_offer(args: argparse.Namespace) -> None:
    text, _iid = _mint_offer(
        args.home, args.xdg_state, endpoint=args.endpoint, user=args.user, label=args.label
    )
    print(text)


def _pending_pairings(store_path: Path) -> list[sqlite3.Row]:
    """Read-only: enumerate pending pairings to find one by SAS. `store.py` is the only module
    that WRITES the store (its own docstring); this only reads, over its own short-lived
    connection, alongside the live gateway's WAL-mode connection."""
    uri = f"file:{store_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            "SELECT pairing_id, device_pub FROM pairings WHERE state = 'awaiting_operator'"
        ).fetchall()
    finally:
        conn.close()


def _find_pairing_id_by_sas(
    store_path: Path, crypto_mod, *, sas: str | None, sas_group: str | None
) -> str:
    sas_norm = sas.strip().upper() if sas else None
    group_norm = sas_group.strip().upper() if sas_group else None
    for row in _pending_pairings(store_path):
        device_fp = crypto_mod.spki_fingerprint(bytes(row["device_pub"]))
        candidate = crypto_mod.device_sas(device_fp)
        if sas_norm and candidate == sas_norm:
            return str(row["pairing_id"])
        if group_norm and candidate.split("-")[0] == group_norm:
            return str(row["pairing_id"])
    raise LookupError(f"no pending pairing matches sas={sas!r} sas_group={sas_group!r}")


def _pairing_id_for(args: argparse.Namespace) -> str:
    from hmp_plugin import crypto

    store, _custody = _open_store(args.home, args.xdg_state)
    try:
        store_path = store._path
    finally:
        store.close()
    return _find_pairing_id_by_sas(store_path, crypto, sas=args.sas, sas_group=args.sas_group)


def _run_real_cli_pty(home: str, xdg_state: str, argv: list[str], *, timeout: float = 30.0) -> str:
    """`hermes hmp <argv...>` (T032) under a real pseudo-terminal, both stdin and stdout attached
    to the slave end, so `CliEnv.interactive()` (`stdin.isatty() and stdout.isatty()`) is
    genuinely true -- see the module docstring. `hermes` here is `sys.executable`'s own venv
    entry point (this script always runs under the target build's venv python)."""
    hermes_bin = Path(sys.executable).parent / "hermes"
    master_fd, slave_fd = pty.openpty()
    try:
        proc = subprocess.Popen(
            [str(hermes_bin), "hmp", *argv],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=_clean_env(home, xdg_state),
            close_fds=True,
        )
        os.close(slave_fd)
        slave_fd = -1
        chunks: list[bytes] = []
        sel = selectors.DefaultSelector()
        sel.register(master_fd, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                proc.kill()
                raise TimeoutError(f"hermes hmp {' '.join(argv)} timed out after {timeout}s")
            if not sel.select(timeout=min(1.0, remaining)):
                if proc.poll() is not None:
                    break
                continue
            try:
                data = os.read(master_fd, 4096)
            except OSError:  # PTY closed (EIO on Linux at EOF)
                break
            if not data:
                break
            chunks.append(data)
        returncode = proc.wait(timeout=timeout)
    finally:
        if slave_fd != -1:
            os.close(slave_fd)
        os.close(master_fd)
    output = b"".join(chunks).decode("utf-8", errors="replace")
    if returncode != 0:
        raise RuntimeError(f"hermes hmp {' '.join(argv)} failed (exit {returncode}):\n{output}")
    return output


def cmd_confirm(args: argparse.Namespace) -> None:
    pairing_id = _pairing_id_for(args)
    output = _run_real_cli_pty(
        args.home,
        args.xdg_state,
        [
            "pair", "confirm",
            "--sas", args.sas or args.sas_group or "",
            "--label", args.label,
            "--user", args.user,
            "--yes-share",
            "--",
            pairing_id,
        ],
    )
    print(json.dumps({"ok": True, "pairing_id": pairing_id, "output": output}))


def cmd_deny(args: argparse.Namespace) -> None:
    pairing_id = _pairing_id_for(args)
    output = _run_real_cli_pty(args.home, args.xdg_state, ["pair", "deny", "--", pairing_id])
    print(json.dumps({"ok": True, "pairing_id": pairing_id, "output": output}))


def cmd_list(args: argparse.Namespace) -> None:
    """Not part of the run descriptor interface; a small debugging aid (mirrors `hermes hmp pair
    list`, run non-interactively -- `pair list` is not in `cli.py`'s `MUTATING_COMMANDS`)."""
    output = _run_real_cli_pty(args.home, args.xdg_state, ["pair", "list"])
    print(output)


def cmd_rotate_key(args: argparse.Namespace) -> None:
    """T035: `hermes hmp instance rotate-key` (PR7-2/PR7-6), under a real pty -- same mechanism as
    `confirm`/`deny` above (module docstring). Used by the reference-client integration test to
    exercise PR7-6's device-visible sequence (a pin mismatch or a connection failure for a
    pre-rotation device, never a promised HTTP status) against a REAL rotation."""
    output = _run_real_cli_pty(args.home, args.xdg_state, ["instance", "rotate-key"])
    print(json.dumps({"ok": True, "output": output}))


def cmd_devices_revoke(args: argparse.Namespace) -> None:
    """T035: `hermes hmp devices revoke <device_id>` (PR7-1), under a real pty."""
    output = _run_real_cli_pty(args.home, args.xdg_state, ["devices", "revoke", args.device_id])
    print(json.dumps({"ok": True, "device_id": args.device_id, "output": output}))


def cmd_get_offer_state(args: argparse.Namespace) -> None:
    """T035: read-only peek at one offer's `state`/`failures` (`_open_store`, reused unchanged),
    used as server-side evidence that a wrong-pin abort never reached the application layer at
    all -- the offer this reads is untouched (still `open`, `failures` still 0), not merely
    inferred "probably fine" from the client raising an exception."""
    store, _custody = _open_store(args.home, args.xdg_state)
    try:
        row = store.get_offer(args.oid)
    finally:
        store.close()
    if row is None:
        print(json.dumps({"ok": True, "found": False}))
    else:
        print(
            json.dumps(
                {"ok": True, "found": True, "state": row["state"], "failures": row["failures"]}
            )
        )


def cmd_pair_reference_client(args: argparse.Namespace) -> None:
    """Full P1-P4 for one throwaway reference device: mint an offer (`offer`), P2 over real TLS,
    confirm through the real CLI (`confirm`'s `_run_real_cli_pty`), P4 over real TLS. Used by
    `build_fixture.py --serve` to hand each instance a ready-to-use bearer token (the "reference-
    client state" `server/tests/integration/test_reads_fixture.py` needs) -- not part of the run
    descriptor `fixture_server_test.dart` documents, which drives its OWN P1-P4 through
    `offer`/`confirm`/`deny` instead."""
    import http.client
    import ssl

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    from hmp_plugin import contract, crypto, wire

    text, iid = _mint_offer(
        args.home, args.xdg_state, endpoint=args.endpoint, user=args.user, label=args.label
    )
    raw = wire.b64u_decode_bounded(text[len("hmp1:"):], max_length=4000)
    offer = json.loads(raw)

    device_priv = ec.generate_private_key(ec.SECP256R1())
    device_pub_der = device_priv.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    oid_raw = wire.b64u_decode(offer["oid"], length=16)
    secret = wire.b64u_decode(offer["s"], length=32)
    nd = crypto.random_bytes(32)
    device_name = "f1-fixture-device-reference-client"

    p2_message = crypto.transcript(
        contract.TAG_PAIR_REQ, offer["iid"], oid_raw, crypto.sha256(secret),
        device_pub_der, device_name, nd,
    )
    p2_body = {
        "v": contract.PROTOCOL_VERSION,
        "oid": offer["oid"],
        "s": offer["s"],
        "device_name": device_name,
        "device_pub": wire.b64u_encode(device_pub_der),
        "nd": wire.b64u_encode(nd),
        "sig": wire.b64u_encode(crypto.sign(device_priv, p2_message)),
    }

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # the pin is T041's job; this is seeding, not a pin test
    host, port = args.endpoint.removeprefix("https://").split(":")
    conn = http.client.HTTPSConnection(host, int(port), context=ctx, timeout=15)
    conn.request(
        "POST", "/hmp/v1/pair/request",
        body=json.dumps(p2_body).encode(), headers={"Content-Type": "application/json"},
    )
    resp = conn.getresponse()
    p2 = json.loads(resp.read())
    conn.close()
    if resp.status != 202:
        raise RuntimeError(f"P2 pair/request failed: {resp.status} {p2}")

    _run_real_cli_pty(
        args.home, args.xdg_state,
        [
            "pair", "confirm",
            "--sas", p2["device_sas"],
            "--label", args.label or "fixture-reference-client",
            "--user", args.user,
            "--yes-share",
            "--",
            p2["pairing_id"],
        ],
    )

    pairing_raw = wire.b64u_decode(p2["pairing_id"], length=16)
    ts = int(time.time())
    p4_message = crypto.transcript(
        contract.TAG_PAIR_DONE, iid, pairing_raw, nd, wire.b64u_decode(p2["ni"], length=32), ts
    )
    p4_body = {
        "pairing_id": p2["pairing_id"],
        "ts": ts,
        "sig": wire.b64u_encode(crypto.sign(device_priv, p4_message)),
    }

    conn = http.client.HTTPSConnection(host, int(port), context=ctx, timeout=15)
    conn.request(
        "POST", "/hmp/v1/pair/complete",
        body=json.dumps(p4_body).encode(), headers={"Content-Type": "application/json"},
    )
    resp = conn.getresponse()
    p4 = json.loads(resp.read())
    conn.close()
    if resp.status != 200:
        raise RuntimeError(f"P4 pair/complete failed: {resp.status} {p4}")

    print(json.dumps({"ok": True, "iid": iid, "device": p4}))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("offer")
    p.add_argument("--home", required=True)
    p.add_argument("--xdg-state", required=True)
    p.add_argument("--endpoint", required=True, help="https://127.0.0.1:<port> of this instance")
    p.add_argument("--user", default=None, help="intended HMP user id (hmpu_...); required if "
                   "the confirming --user must match)")
    p.add_argument("--label", default=None)
    p.set_defaults(func=cmd_offer)

    p = sub.add_parser("confirm")
    p.add_argument("--home", required=True)
    p.add_argument("--xdg-state", required=True)
    p.add_argument("--sas", default=None)
    p.add_argument("--sas-group", default=None)
    p.add_argument("--label", required=True)
    p.add_argument("--user", required=True, help="HMP user id to activate the device under "
                   "(must match the offer's --user)")
    p.set_defaults(func=cmd_confirm)

    p = sub.add_parser("deny")
    p.add_argument("--home", required=True)
    p.add_argument("--xdg-state", required=True)
    p.add_argument("--sas", default=None)
    p.add_argument("--sas-group", default=None)
    p.set_defaults(func=cmd_deny)

    p = sub.add_parser("list")
    p.add_argument("--home", required=True)
    p.add_argument("--xdg-state", required=True)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("rotate-key")
    p.add_argument("--home", required=True)
    p.add_argument("--xdg-state", required=True)
    p.set_defaults(func=cmd_rotate_key)

    p = sub.add_parser("devices-revoke")
    p.add_argument("--home", required=True)
    p.add_argument("--xdg-state", required=True)
    p.add_argument("device_id")
    p.set_defaults(func=cmd_devices_revoke)

    p = sub.add_parser("get-offer-state")
    p.add_argument("--home", required=True)
    p.add_argument("--xdg-state", required=True)
    p.add_argument("--oid", required=True)
    p.set_defaults(func=cmd_get_offer_state)

    p = sub.add_parser("pair-reference-client")
    p.add_argument("--home", required=True)
    p.add_argument("--xdg-state", required=True)
    p.add_argument("--endpoint", required=True)
    p.add_argument("--user", required=True, help="HMP user id to activate the device under")
    p.add_argument("--label", default=None)
    p.set_defaults(func=cmd_pair_reference_client)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as exc:
        _fail(f"{type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
