"""Bounded actual-helper probe against an exported Hermes tree, never a live home.

Run with -I -B -S, explicit --hermes-src/--dependencies-dir, and HERMES_HOME
pointing to a new empty private directory. No .pth activation or model/tool call
is used. Instrumented Python network/process entry points refuse effects, but
this is not an OS sandbox. The caller must impose an external process timeout.
Only producer/helper compatibility is sampled: no operator IPC or phone result.
"""

import argparse
import asyncio
import json
import os
import pathlib
import pwd
import socket
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--hermes-src", type=pathlib.Path, required=True)
parser.add_argument("--dependencies-dir", type=pathlib.Path, required=True)
args = parser.parse_args()
source_path = args.hermes_src.resolve()
real_homes = {
    (pathlib.Path.home() / ".hermes").resolve(),
    (pathlib.Path(pwd.getpwuid(os.geteuid()).pw_dir) / ".hermes").resolve(),
}
home_text = os.environ.get("HERMES_HOME", "")
if sys.flags.optimize:
    parser.error("probe assertions must be enabled")
if not home_text or not (
    sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
):
    parser.error("require -I -B -S and an explicit empty private HERMES_HOME")
home_path = pathlib.Path(home_text).resolve()
if (
    any(root == source_path or root in source_path.parents for root in real_homes)
    or any(root == home_path or root in home_path.parents for root in real_homes)
    or not home_path.is_dir()
    or any(home_path.iterdir())
    or home_path.stat().st_mode & 0o077
    or home_path.stat().st_uid != os.geteuid()
):
    parser.error("refusing live source/home or nonempty/nonprivate fixture home")
if (
    not (source_path / "tools/approval.py").is_file()
    or not args.dependencies_dir.is_dir()
):
    parser.error("exported source or dependency directory unavailable")
source, site = str(source_path), str(args.dependencies_dir.resolve())
plugin = str(pathlib.Path(__file__).resolve().parents[2] / "server")
sys.path[:0] = [source, site, plugin]
blocked = []


def refuse(*a, **k):
    blocked.append(True)
    raise AssertionError("external effect refused")


subprocess.Popen = refuse
os.system = refuse
if hasattr(os, "fork"):
    os.fork = refuse
if hasattr(os, "posix_spawn"):
    os.posix_spawn = refuse
if hasattr(os, "posix_spawnp"):
    os.posix_spawnp = refuse
for name in (
    "execv",
    "execve",
    "execl",
    "execlp",
    "execvp",
    "execvpe",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
):
    if hasattr(os, name):
        setattr(os, name, refuse)
socket.create_connection = refuse
socket.getaddrinfo = refuse
socket.socket.connect = refuse
socket.socket.connect_ex = refuse
socket.socket.sendto = refuse
if hasattr(socket.socket, "sendmsg"):
    socket.socket.sendmsg = refuse
from hmp_plugin.approval_test_producer import (  # noqa: E402
    ApprovalTestProducer,
    NativeApprovalBindings,
    TargetBinding,
    TestBeginReceipt,
    _ProcessSlot,
)
from tools import approval, approval_gateway_wait, interrupt  # noqa: E402 — guarded exported source

assert all(
    pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path(source))
    for m in (approval, approval_gateway_wait, interrupt)
)
native = NativeApprovalBindings(
    waiter_module=approval_gateway_wait,
    approval_module=approval,
    interrupt_module=interrupt,
)


async def main():
    results = []
    for choice in ("once", "deny", "cancel", "expiry"):
        rows = {}

        def publish(n, rows=rows):
            rows[n.request_id] = n
            return True

        def remove(n, rows=rows):
            if rows.get(n.request_id) is n:
                rows.pop(n.request_id)
            return n.request_id not in rows

        slot = _ProcessSlot()
        service = ApprovalTestProducer(
            loop=asyncio.get_running_loop(),
            native=native,
            publish=publish,
            remove=remove,
            slot=slot,
        )
        target = TargetBinding(
            "synthetic-instance",
            "synthetic-user",
            "default",
            "synthetic-session",
            "synthetic-device",
        )
        begun = await service.begin_test(target, 2000)
        assert type(begun) is TestBeginReceipt
        route = service._owned_operation.route_key
        limit = asyncio.get_running_loop().time() + 1.5
        while not rows:
            assert asyncio.get_running_loop().time() < limit
            await asyncio.sleep(0.005)
        if choice in ("once", "deny"):
            control = await service.answer_test(begun.handle, target.device_id, choice)
            assert control.admission == "accepted"
        elif choice == "cancel":
            control = await service.cancel_test(begun.handle, target.device_id)
            assert control.admission == "accepted"
        outcome = await service.wait_outcome(begun.handle, target.device_id, timeout=5)
        cleaned = await asyncio.wait_for(service.close_and_join(), timeout=5)
        expected = {
            "once": "once_acknowledged",
            "deny": "denied",
            "cancel": "cancelled",
            "expiry": "expired",
        }
        assert outcome.status.value == expected[choice]
        assert cleaned.joined and not rows and slot.operation is None
        assert not approval.list_gateway_approvals(route)
        results.append(
            {
                "choice": choice,
                "outcome": outcome.status.value,
                "cleanup_joined": cleaned.joined,
                "rows_empty": not rows,
                "native_queue_empty": not approval.list_gateway_approvals(route),
                "slot_released": slot.operation is None,
            }
        )
    assert not blocked
    print(
        json.dumps(
            {
                "actual_exported_native_origins": True,
                "cases": results,
                "attempts_through_instrumented_apis": len(blocked),
            }
        )
    )


asyncio.run(main())
