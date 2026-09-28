#!/usr/bin/env python3
"""The per-run stand-in HMP instance for the acceptance matrix (T079, T083; research R12; CS-6 and
the controller ruling that refines it: the acceptance build pairs only with the per-run test
instance).

NOT a T060 fixture. It is the real `server/hmp_plugin` listener (TLS 1.3 over the instance key,
P2/P3/P4/P5, `/ready`, bearer authentication) around a real instance identity, in an isolated
scratch home, with **no Hermes bridge**: reads have no data behind them. That is enough for the
RV-1 matrix, which measures connections: `pass-then-intercept` forwards the first N connections
to this process, whose `iid` is the pin, and intercepts connection N+1.

Subcommands:

  init   --home H           create the identity (first run) and print {"iid": ...}. The acceptance
                            build is made with this `iid` (`build_release.sh --acceptance-iid`).
  serve  --home H --port P  serve on 127.0.0.1:P and auto-confirm every pending pairing (the
                            operator step, PR3-4) with a CS-22 scannable operator label.
  offer  --home H --endpoint https://<host>:<port>
                            mint a single-use offer registered in this instance's store, whose
                            `ep` is the INTERCEPTOR's endpoint, and print the `hmp1:` text. The
                            interceptor never serves this instance's key; in `pass-then-intercept`
                            it only relays bytes to it.

Custody: `--home` must be outside the repository (like `make_test_ca.py`). Everything under it is
test-only and worthless after the run; delete it afterwards. The host binding uses a synthetic
host id, never the machine's own identifier.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import signal
import sys
import time
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
SERVER_DIR = REPO_ROOT / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from hmp_plugin import crypto, identity, server, wire  # noqa: E402
from hmp_plugin.compat import CompatResult, CompatStatus  # noqa: E402
from hmp_plugin.contract import (  # noqa: E402
    OFFER_TTL_S,
    PROTOCOL_VERSION,
    TAG_OFFER,
    QrOffer,
)
from hmp_plugin.identity import HostId  # noqa: E402
from hmp_plugin.pairing import STATE_AWAITING, confirm_pairing  # noqa: E402
from hmp_plugin.store import Store  # noqa: E402

SYNTHETIC_HOST = HostId("acceptance-standin", "synthetic-standin-host")
OPERATOR_LABEL = "f1-fixture-label-acceptance"  # CS-22 scannable prefix
USER_ID = "hmpu_" + "a" * 32
CONFIRM_POLL_S = 0.2


class ScratchOnlyError(RuntimeError):
    """The home is inside the repository tree (CS-6)."""


def _require_scratch(home: Path) -> Path:
    resolved = Path(home).resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        return resolved
    raise ScratchOnlyError(
        "refusing to create a stand-in home inside the repository tree; pass a scratch directory"
    )


def _identity_kwargs(home: Path) -> dict[str, Any]:
    root = home / "hermes"
    return {
        "env": {"HERMES_HOME": str(root)},
        "hermes_root": root,
        "binding_root": home / "state" / "hermes-hmp",
        "host_id": lambda: SYNTHETIC_HOST,
    }


def open_instance(home: Path) -> tuple[Store, Any]:
    """The stand-in's store and loaded identity (created on the first call)."""
    home = _require_scratch(home)
    kwargs = _identity_kwargs(home)
    (home / "hermes").mkdir(parents=True, exist_ok=True)
    custody = identity.resolve_custody(
        env=kwargs["env"], hermes_root=kwargs["hermes_root"], binding_root=kwargs["binding_root"]
    )
    store_path = server.store_path(custody.anchor_dir)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store = Store(store_path)
    store.migrate()
    ident = identity.load_or_create(store, **kwargs, now=int(time.time()))
    return store, ident


def _ensure_user(store: Store) -> None:
    with store.transaction() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (USER_ID,)).fetchone()
    if row is None:
        store.insert_user(USER_ID, OPERATOR_LABEL, int(time.time()))


def mint_offer(home: Path, endpoint: str) -> tuple[str, str]:
    """Register a single-use offer and return (`hmp1:` text, iid). `endpoint` is the
    interceptor's `https://<host>:<port>`."""
    wire.require_endpoint(endpoint)
    store, ident = open_instance(home)
    try:
        now = int(time.time())
        oid = wire.b64u_encode(crypto.random_bytes(16))
        s = crypto.random_bytes(32)
        exp = now + OFFER_TTL_S
        payload = wire.encode_qr_payload(
            QrOffer(
                v=PROTOCOL_VERSION,
                iid=ident.iid,
                ep=(endpoint,),
                oid=oid,
                s=wire.b64u_encode(s),
                exp=exp,
            ),
            now=now,
        )
        store.insert_offer(oid, crypto.secret_hash(TAG_OFFER, s), exp)
        return payload, ident.iid
    finally:
        store.close()


async def _auto_confirm(store: Store, stop: asyncio.Event) -> None:
    """The operator step (PR3-4) for every pending pairing: this instance exists only for the
    acceptance run, so every P2 that reached it is confirmed."""
    _ensure_user(store)
    while not stop.is_set():
        with store.transaction() as conn:
            rows = conn.execute(
                "SELECT pairing_id FROM pairings WHERE state = ?", (STATE_AWAITING,)
            ).fetchall()
        for row in rows:
            with contextlib.suppress(LookupError):
                confirm_pairing(
                    store,
                    row["pairing_id"],
                    user_id=USER_ID,
                    label=OPERATOR_LABEL,
                    now=int(time.time()),
                )
                with contextlib.suppress(OSError):
                    print(json.dumps({"event": "pairing_confirmed"}), flush=True)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), CONFIRM_POLL_S)


async def serve(home: Path, port: int) -> int:
    store, ident = open_instance(home)
    ctx = server.ServerContext(
        identity=ident,
        store=store,
        compat=CompatResult(CompatStatus.SUPPORTED),
    )
    listener = server.HmpServer(ctx, server.ListenerSettings(bind="127.0.0.1", port=port))
    await listener.start()
    bound = listener.bound
    print(json.dumps({"event": "listening", "iid": ident.iid, "port": bound[1] if bound else None}),
          flush=True)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)
    confirmer = loop.create_task(_auto_confirm(store, stop))
    closed = loop.create_task(listener.closed.wait())
    stopped = loop.create_task(stop.wait())
    await asyncio.wait({closed, stopped}, return_when=asyncio.FIRST_COMPLETED)
    stop.set()
    await confirmer
    await listener.stop(notify=False)
    for t in (closed, stopped):
        t.cancel()
    store.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--home", type=Path, required=True)
    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--home", type=Path, required=True)
    p_serve.add_argument("--port", type=int, default=0)
    p_offer = sub.add_parser("offer")
    p_offer.add_argument("--home", type=Path, required=True)
    p_offer.add_argument("--endpoint", required=True)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "init":
            store, ident = open_instance(args.home)
            store.close()
            print(json.dumps({"iid": ident.iid}))
            return 0
        if args.cmd == "serve":
            return asyncio.run(serve(args.home, args.port))
        text, _iid = mint_offer(args.home, args.endpoint)
        print(text)
        return 0
    except ScratchOnlyError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
