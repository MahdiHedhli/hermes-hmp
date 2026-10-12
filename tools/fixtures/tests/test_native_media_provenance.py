"""Collected receipt forwarding tests; actual worker action with in-memory ports."""

import copy
import hashlib
import importlib.util
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    path = ROOT / filename
    if name in sys.modules:
        module = sys.modules[name]
        assert Path(module.__file__) == path
        return module
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


provider = load("local_media_provider_response", "local_media_provider_response.py")
seed_module = load("local_media_seed", "local_media_seed.py")
worker = load("_hmp_media_provenance_worker", "native_media_worker.py")
Runtime, RefusalError = (worker.NativeRuntime, worker.RefusalError)
models = SimpleNamespace(
    **runpy.run_path(str(ROOT / "tests/process_window_models.py"), run_name="_inert_window_models")
)
validator = seed_module._producer_receipt
raw = json.dumps({"success": True, "provider": "openai", "image": "/fixture/media.png"})
receipt = {
    "schema": "native-media-producer-v1",
    "profile": "media-alpha",
    "invocation": "P01",
    "toolCallId": "media-fixture-P01",
    "factorySourceSHA256": seed_module._NATIVE_FACTORY_SHA256,
    "toolResultBytes": len(raw.encode()),
    "toolResultSHA256": hashlib.sha256(raw.encode()).hexdigest(),
    "actualFactoryReturns": 1,
    "customHttpx": True,
    "redirects": False,
    "sdkMaxRetries": 2,
    "effectiveURL": "http://127.0.0.1:54321/v1/",
    "dummyAuth": True,
}


async def to_thread(fn, *args, **kwargs):
    return fn(*args, **kwargs)


def finish(coroutine):
    runtime = coroutine.cr_frame.f_locals["self"]
    command = coroutine.cr_frame.f_locals["command"]
    with runtime._inert_scope as scope:
        try:
            ticket = scope.begin(runtime, command)
        except BaseException:
            # This test-owned coroutine was never advanced or transferred.
            coroutine.close()
            raise
        try:
            coroutine.send(None)
        except StopIteration as result:
            runtime.window.complete(ticket, result.value)
            return result.value
        raise AssertionError("unexpected suspension")


def exercise():
    checks = []

    def fresh(commands):
        runtime = Runtime.__new__(Runtime)
        writes, seeded = ([], [])

        class Store:
            def __init__(self, _path):
                writes.append("open")

            def migrate(self):
                writes.append("migrate")

            def set_chat(self, *args):
                writes.append("chat")

            def close(self):
                writes.append("close")

        def seed_profile(**kwargs):
            seeded.append(kwargs)
            return {"nativeSeed": "inert"}

        runtime.runner = None
        runtime.raw, runtime.producer_receipts, runtime.seeded_profiles = ({}, {}, set())
        runtime.home, runtime.runtime_dir = (Path("/fixture"), Path("/runtime"))
        runtime.spec = {
            "providerPort": 54321,
            "factoryPath": "/fixture/f.py",
            "factorySHA256": "0" * 64,
        }
        runtime.ledger = SimpleNamespace(charge=lambda *args: None)
        runtime.seed = SimpleNamespace(
            produce_once=lambda **kwargs: (raw, copy.deepcopy(receipt)),
            _producer_receipt=validator,
            seed_profile=seed_profile,
        )
        runtime.actor = lambda command: SimpleNamespace(user_id="synthetic")
        runtime.hmp_identity = SimpleNamespace(
            resolve_custody=lambda **kwargs: SimpleNamespace(anchor_dir=Path("/fixture"))
        )
        runtime.Store, runtime.store_path = (Store, lambda path: path)
        scope = models.InertScope()
        with scope:
            scope.attach(runtime, commands)
        return (runtime, writes, seeded)

    produce = {"op": "PRODUCE", "profile": "media-alpha", "args": {"invocation": "P01"}}
    seed = {
        "op": "SEED",
        "profile": "media-alpha",
        "args": {"invocation": "P01", "chatId": "synthetic", "botSessionId": "synthetic-session"},
    }
    produce = models.command(produce, sequence=1)
    seed = models.command(seed, sequence=2)
    r, writes, seeded = fresh([produce, seed])
    out = finish(r.action(copy.deepcopy(produce)))
    assert r.producer_receipts["P01"] == receipt and r.producer_receipts["P01"] is not receipt
    out["profile"] = "media-beta"
    assert r.producer_receipts["P01"]["profile"] == "media-alpha"
    checks.append("validated_detached_retention")
    finish(r.action(copy.deepcopy(seed)))
    assert len(seeded) == 1 and seeded[0]["producer_receipt"] == receipt
    assert seeded[0]["producer_receipt"] is not r.producer_receipts["P01"]
    checks.append("mandatory_receipt_forwarded")
    for fault in ("missing", "profile", "raw"):
        r, writes, seeded = fresh([seed] if fault == "missing" else [produce, seed])
        if fault != "missing":
            finish(r.action(copy.deepcopy(produce)))
        command = copy.deepcopy(seed)
        if fault == "profile":
            command["profile"] = "media-beta"
        if fault == "raw":
            r.raw["P01"] = raw + " "
        try:
            finish(r.action(command))
        except Exception as error:
            assert type(error) in (RefusalError, models.windows.WindowRefusedError)
            assert str(error) in ("native_action_refused", "WINDOW_UNAVAILABLE")
            assert r.window._journal.first_failure is not None
            if fault == "missing":
                assert not r.window._journal.producers
            elif fault == "profile":
                assert command["profile"] != r.window._journal.producers["P01"].profile
            else:
                assert r.raw["P01"] != r.window._journal.producers["P01"].raw
        else:
            raise AssertionError(fault)
        assert writes == [] and seeded == []
        checks.append("reject_before_writes_" + fault)
    print(json.dumps({"checks": checks, "count": len(checks), "runtimeQualified": False}))


def test_producer_receipt_worker_forwarding():
    with patch.object(worker, "asyncio", SimpleNamespace(to_thread=to_thread)):
        exercise()


def test_native_seed_uses_observed_ids_and_rejects_drift():
    class DB:
        def __init__(self, fault=None):
            self.rows = []
            self.fault = fault
            self.appended = 0

        def get_messages(self, session_id, *, include_inactive, limit):
            assert session_id == "synthetic-session" and include_inactive is True
            return copy.deepcopy(self.rows[:limit])

        def append_messages_batch(self, session_id, messages):
            self.appended += 1
            self.rows = [
                {**copy.deepcopy(message), "id": row_id, "session_id": session_id, "active": 1}
                for message, row_id in zip(messages, (101, 113), strict=True)
            ]
            if self.fault == "extra":
                self.rows.append(copy.deepcopy(self.rows[-1]))
            elif self.fault == "scope":
                self.rows[1]["session_id"] = "other"
            elif self.fault == "id":
                self.rows[1]["id"] = True
            elif self.fault == "tool":
                self.rows[1]["tool_call_id"] = "other"
            return len(messages)

    database = DB()
    rows = seed_module.seed_tool_row(database, "synthetic-session", raw, "P01")
    assert [row["id"] for row in rows] == [101, 113] and database.appended == 1
    for fault, label in (
        ("extra", "native_rows_count"),
        ("scope", "native_row_scope"),
        ("id", "native_row_id"),
        ("tool", "native_row_body"),
    ):
        database = DB(fault)
        try:
            seed_module.seed_tool_row(database, "synthetic-session", raw, "P01")
        except provider.FixtureRefusalError as error:
            assert str(error) == label
        else:
            raise AssertionError(fault)
        assert database.appended == 1
