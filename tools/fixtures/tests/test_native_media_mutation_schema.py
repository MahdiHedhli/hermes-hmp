"""Actual closed receipt validators with synthetic dictionaries; no native authority."""

import copy
import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType

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
BEFORE = "a" * 64
checks = []


def receipt(case):
    union = {"event": "actual_native_union_readback", "noIndependentGrantObserved": True}
    before = {"approved": True, "authz": "authorized", "noIndependentGrant": True}
    if case == "NM07":
        after = {"approved": False, "authz": "pending_operator", "noIndependentGrant": True}
        result = {
            "event": "public_native_revoke_observation",
            "unionBefore": copy.deepcopy(union),
            "unionAfter": copy.deepcopy(union),
            "actualAuthzAfter": "pending_operator",
        }
    else:
        key_hash = w["_opaque_native_hash"]("session-key", "synthetic-key")
        before.update(
            sessionKeySHA256=key_hash,
            sessionIdSHA256=w["_opaque_native_hash"]("session-id", "old"),
        )
        after = {
            **before,
            "sessionIdSHA256": w["_opaque_native_hash"]("session-id", "new"),
        }
        result = {
            "event": "actual_running_public_store_rotation",
            "oldSessionId": "old",
            "newSessionId": "new",
            "sessionKeySHA256": key_hash,
            "unionBefore": copy.deepcopy(union),
            "unionAfter": copy.deepcopy(union),
        }
    evidence = {"case": case, "actorScopeSHA256": "e" * 64, "before": before, "after": after}
    result.update(nativeEvidence=evidence, beforeCaptureSHA256=BEFORE)
    return result


def validate(case, result):
    result["afterNativeSHA256"] = w["native_evidence_hash"](case, BEFORE, result["nativeEvidence"])
    w["validate_mutation_receipt"](case, BEFORE, result, result["event"])


class TestNativeMutationSchema(unittest.TestCase):
    def refuses(self, name, case, result, expected):
        with self.assertRaises(w["RefusalError"]) as error:
            validate(case, result)
        self.assertEqual(str(error.exception), expected)
        checks.append(name)

    def test_valid_known_receipts(self):
        for case in ("NM07", "NM08"):
            value = receipt(case)
            validate(case, value)
            self.assertEqual(value["beforeCaptureSHA256"], BEFORE)
            checks.append("valid_" + case)

    def test_three_formal_probes_refuse(self):
        value = receipt("NM07")
        value["nativeEvidence"]["before"]["approved"] = 1
        value["nativeEvidence"]["after"]["approved"] = 0
        self.refuses("formal_integer_approval", "NM07", value, "native_transition_boolean")
        value = receipt("NM08")
        value["sessionKeySHA256"] = "synthetic-raw-session-key"
        value["nativeEvidence"]["before"]["sessionKeySHA256"] = value["sessionKeySHA256"]
        value["nativeEvidence"]["after"]["sessionKeySHA256"] = value["sessionKeySHA256"]
        self.refuses("formal_non_hash_session_key", "NM08", value, "native_session_key_hash")
        value = receipt("NM07")
        value["unionBefore"]["unexpectedField"] = "synthetic-private-sentinel"
        self.refuses("formal_extra_union_field", "NM07", value, "native_union_receipt_shape")

    def test_boolean_fields_are_strict(self):
        for case in ("NM07", "NM08"):
            for state in ("before", "after"):
                for field in ("approved", "noIndependentGrant"):
                    value = receipt(case)
                    value["nativeEvidence"][state][field] = int(
                        value["nativeEvidence"][state][field]
                    )
                    self.refuses(
                        case + "_" + state + "_" + field,
                        case,
                        value,
                        "native_transition_boolean",
                    )

    def test_both_union_shapes_events_and_flags_are_strict(self):
        for case in ("NM07", "NM08"):
            for key in ("unionBefore", "unionAfter"):
                for name, union in (
                    ("not_dict", []),
                    ("wrong_event", {"event": "invented", "noIndependentGrantObserved": True}),
                    (
                        "extra_key",
                        {
                            "event": "actual_native_union_readback",
                            "noIndependentGrantObserved": True,
                            "extra": "synthetic-private-sentinel",
                        },
                    ),
                    (
                        "integer_flag",
                        {"event": "actual_native_union_readback", "noIndependentGrantObserved": 1},
                    ),
                ):
                    value = receipt(case)
                    value[key] = union
                    self.refuses(
                        case + "_" + key + "_" + name,
                        case,
                        value,
                        "native_union_receipt_shape",
                    )

    def test_all_key_hash_locations_require_canonical_hash(self):
        for location in ("before", "after", "observation"):
            for name, bad in (
                ("uppercase", "A" * 64),
                ("length", "a" * 63),
                ("wrong_type", True),
            ):
                value = receipt("NM08")
                target = value if location == "observation" else value["nativeEvidence"][location]
                target["sessionKeySHA256"] = bad
                self.refuses(
                    "key_hash_" + location + "_" + name,
                    "NM08",
                    value,
                    "native_session_key_hash",
                )
