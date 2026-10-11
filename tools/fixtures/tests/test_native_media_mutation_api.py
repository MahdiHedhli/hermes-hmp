"""Actual worker methods with in-memory native API ports; no native imports/OS IO."""

import importlib.util
import json
import sys
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_worker():
    name = "_hmp_media_mutation_worker"
    path = ROOT / "native_media_worker.py"
    if name in sys.modules:
        module = sys.modules[name]
        assert type(module) is ModuleType
        assert Path(module.__file__) == path
        assert module.__spec__.name == name and module.__spec__.origin == str(path)
        assert module.__name__ == name and module.__spec__.loader is not None
        return module
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


worker = load_worker()
w = vars(worker)
Runtime = w["NativeRuntime"]
RefusalError = w["RefusalError"]
BEFORE = "a" * 64


def run_action(coroutine):
    with patch.object(worker, "read_pin", lambda _pin, _ledger: b"pinned"):
        try:
            coroutine.send(None)
        except StopIteration as result:
            return result.value
        raise AssertionError("unexpected suspension")


class Pairing:
    def __init__(self, approved=True):
        self.profile = "media-alpha"
        self.approved = approved
        self.calls = []

    def is_approved(self, platform, user):
        self.calls.append(("read", platform, user))
        return self.approved

    def revoke(self, platform, user):
        self.calls.append(("revoke", platform, user))
        self.approved = False
        return True


class Store:
    def __init__(self, pairing):
        self.pairing = pairing
        self.current = SimpleNamespace(session_key="key", session_id="old")
        self.calls = []

    def lookup_by_session_key(self, key):
        self.calls.append(("lookup", key))
        return self.current if key == "key" else None

    async def get_or_create_session(self, source, *, force_new, touch_activity):
        self.calls.append(("force_new", force_new, touch_activity))
        self.current = SimpleNamespace(session_key="key", session_id="new")
        return self.current


class TestNativeMutationReceipts(unittest.TestCase):
    def make(self, op):
        pairing = Pairing()
        store = Store(pairing)
        actor_name = "A1" if op == "REVOKE" else "B1"
        role = "A" if op == "REVOKE" else "B"
        actor = SimpleNamespace(
            name=actor_name,
            iid="iid-1",
            port=21111,
            device_id="device-secret",
            user_id="user-secret",
            bearer="bearer-private",
        )
        runtime = object.__new__(Runtime)
        runtime.spec = {
            "role": role,
            "iid": "iid-1",
            "port": 21111,
            "authUnionReadbackRoute": {"sealed": True},
            "actorChats": {actor_name: {"media-alpha": "chat"}},
            "actorSessionKeys": {actor_name: {"media-alpha": "key"}},
        }
        runtime.home = Path("/inert-home")
        runtime.ledger = object()
        runtime.actors = {actor_name: actor}
        runtime.runner = SimpleNamespace(session_store=store, async_session_store=store)
        runtime.adapter = SimpleNamespace(build_source=lambda **kwargs: SimpleNamespace(**kwargs))
        runtime.ctx = SimpleNamespace(
            iid="iid-1",
            store=SimpleNamespace(
                get_device=lambda _id: {"state": "ACTIVE", "user_id": actor.user_id}
            ),
            bridge=SimpleNamespace(
                authz_state=lambda _user, _profile: SimpleNamespace(
                    value="authorized" if pairing.approved else "pending_operator"
                )
            ),
        )
        runtime.PairingStore = lambda **kwargs: pairing
        runtime.observe_no_independent_union = lambda _actor, _profile: {
            "event": "actual_native_union_readback",
            "noIndependentGrantObserved": True,
        }
        runtime.live = lambda: None
        runtime.scope = lambda _home: nullcontext()
        runtime.routed = {(actor_name, "media-alpha")}
        command = {
            "op": op,
            "role": role,
            "actor": actor_name,
            "profile": "media-alpha",
            "args": {} if op == "REVOKE" else {"chatId": "chat", "oldSessionId": "old"},
        }
        return runtime, command, pairing, store

    def assert_receipt(self, case, result):
        self.assertEqual(result["beforeCaptureSHA256"], BEFORE)
        self.assertEqual(result["nativeEvidence"]["case"], case)
        self.assertEqual(
            result["afterNativeSHA256"],
            w["native_evidence_hash"](case, BEFORE, result["nativeEvidence"]),
        )
        w["validate_native_evidence"](case, result)
        self.assertNotIn("bearer-private", json.dumps(result))
        self.assertNotIn("device-secret", json.dumps(result))
        self.assertNotIn("user-secret", json.dumps(result))
        self.assertNotIn('"sessionKey": "key"', json.dumps(result))

    def test_revoke_uses_actual_pairing_and_auth_before_after(self):
        runtime, command, pairing, _store = self.make("REVOKE")
        result = run_action(runtime.action(command, before_capture_sha=BEFORE))
        self.assert_receipt("NM07", result)
        self.assertEqual(
            pairing.calls,
            [
                ("read", "hmp", "user-secret"),
                ("revoke", "hmp", "user-secret"),
                ("read", "hmp", "user-secret"),
            ],
        )
        self.assertEqual(result["nativeEvidence"]["before"]["authz"], "authorized")
        self.assertEqual(result["nativeEvidence"]["after"]["authz"], "pending_operator")

    def test_rotate_uses_running_session_store_and_new_id(self):
        runtime, command, pairing, store = self.make("ROTATE")
        result = run_action(runtime.action(command, before_capture_sha=BEFORE))
        self.assert_receipt("NM08", result)
        self.assertEqual((result["oldSessionId"], result["newSessionId"]), ("old", "new"))
        self.assertEqual(result["sessionKeySHA256"], w["_opaque_native_hash"]("session-key", "key"))
        self.assertEqual(
            store.calls, [("lookup", "key"), ("force_new", True, True), ("lookup", "key")]
        )
        self.assertEqual(
            pairing.calls, [("read", "hmp", "user-secret"), ("read", "hmp", "user-secret")]
        )

    def test_missing_before_seal_refuses_before_mutation(self):
        for op in ("REVOKE", "ROTATE"):
            runtime, command, pairing, store = self.make(op)
            with self.assertRaisesRegex(RefusalError, "mutation_before_unsealed"):
                run_action(runtime.action(command))
            self.assertFalse(any(call[0] == "revoke" for call in pairing.calls))
            self.assertFalse(any(call[0] == "force_new" for call in store.calls))

    def test_changed_actor_device_or_auth_refuses_receipt(self):
        runtime, command, pairing, _store = self.make("REVOKE")
        runtime.ctx.store.get_device = lambda _id: {"state": "REVOKED", "user_id": "user-secret"}
        with self.assertRaisesRegex(RefusalError, "native_actor_device_current"):
            run_action(runtime.action(command, before_capture_sha=BEFORE))
        self.assertTrue(pairing.approved)
        runtime, command, pairing, _store = self.make("REVOKE")
        pairing.approved = False
        with self.assertRaisesRegex(RefusalError, "grant_before_revoke"):
            run_action(runtime.action(command, before_capture_sha=BEFORE))

    def test_revoke_must_change_native_approval_and_auth_readback(self):
        runtime, command, pairing, _store = self.make("REVOKE")
        pairing.revoke = lambda _platform, _user: True
        with self.assertRaisesRegex(RefusalError, "live_native_auth_after_revoke"):
            run_action(runtime.action(command, before_capture_sha=BEFORE))

    def test_rotation_must_change_persisted_session_id(self):
        runtime, command, _pairing, store = self.make("ROTATE")

        async def unchanged(_source, *, force_new, touch_activity):
            store.calls.append(("force_new", force_new, touch_activity))
            return store.current

        store.get_or_create_session = unchanged
        with self.assertRaisesRegex(RefusalError, "rotation_not_changed"):
            run_action(runtime.action(command, before_capture_sha=BEFORE))

    def test_rotation_replaced_actor_after_native_await_refuses(self):
        runtime, command, _pairing, store = self.make("ROTATE")
        previous = store.get_or_create_session

        async def replace_actor(source, *, force_new, touch_activity):
            result = await previous(source, force_new=force_new, touch_activity=touch_activity)
            runtime.actors[command["actor"]] = SimpleNamespace(
                name="B1",
                iid="iid-1",
                port=21111,
                device_id="device-secret",
                user_id="user-secret",
                bearer="bearer-private",
            )
            return result

        store.get_or_create_session = replace_actor
        with self.assertRaisesRegex(RefusalError, "native_actor_replaced"):
            run_action(runtime.action(command, before_capture_sha=BEFORE))

    def test_native_evidence_cannot_substitute_label_or_digest(self):
        runtime, command, _pairing, _store = self.make("ROTATE")
        result = run_action(runtime.action(command, before_capture_sha=BEFORE))
        for edit in (
            {"afterNativeSHA256": "0" * 64},
            {"beforeCaptureSHA256": "0" * 64},
            {"newSessionId": "fabricated"},
            {"nativeEvidence": {**result["nativeEvidence"], "actorScopeSHA256": "0" * 64}},
        ):
            bad = {**result, **edit}
            with self.assertRaises(RefusalError):
                w["validate_mutation_receipt"](
                    "NM08", BEFORE, bad, "actual_running_public_store_rotation"
                )
