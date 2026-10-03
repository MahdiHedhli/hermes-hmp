"""Unexecuted future lexical/shape/codec controls, no crypto imports.

Source slice does not authorize running this file. AST extraction keeps pure
controls from importing the checker's crypto/dependency/main/preflight code.
Run only after the source reviewer/root explicitly admits pure test execution.
"""

import ast
import base64
import hashlib
import json
import re
import unittest
from pathlib import Path

PURE = {
    "need",
    "binary",
    "b64",
    "pairs",
    "reject_number",
    "unicode_ok",
    "strict_json",
    "integer",
    "shape",
    "frame",
}
source = ast.parse(Path(__file__).with_name("check.py").read_text())
nodes = [
    n
    for n in source.body
    if (isinstance(n, ast.ClassDef) and n.name in {"RefusalError", "NumericLexeme"})
    or (isinstance(n, ast.FunctionDef) and n.name in PURE)
]
ns = {
    "base64": base64,
    "hashlib": hashlib,
    "json": json,
    "re": re,
    "KID": re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}"),
    "AUD": re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}"),
}
# Fixed, reviewed sibling source only; extract the named pure definitions without
# importing checker dependency/preflight/main code. Execution needs separate admission.
exec(compile(ast.Module(body=nodes, type_ignores=[]), "pure_extracted_checker", "exec"), ns)  # noqa: S102


class PureBoundaryControls(unittest.TestCase):
    def test_duplicate_equivalent_names_and_integer_lexemes(self):
        for bad in [
            b'{"v":1,"v":1}',
            b'{"v":1,"\\u0076":1}',
            b'{"v":1.0}',
            b'{"v":1e0}',
            b'{"v":NaN}',
            b"\xef\xbb\xbf{}",
            b'{"x":"\\ud800"}',
            b"\xff",
        ]:
            with self.subTest(bad=bad), self.assertRaises(ns["RefusalError"]):
                ns["strict_json"](bad, 1024)
        self.assertEqual(ns["strict_json"](b'{"x":"e\\u0301"}', 1024), {"x": "e\u0301"})
        self.assertFalse(ns["integer"](True, 0, 2**53 - 1))
        self.assertTrue(ns["integer"](2**53 - 1, 0, 2**53 - 1))
        self.assertFalse(ns["integer"](2**53, 0, 2**53 - 1))

    def test_canonical_binary_and_byte_caps(self):
        self.assertEqual(ns["binary"]("AAAAAAAAAAAAAAAAAAAAAA", 16, 16, "bad"), bytes(16))
        for bad in [
            "AAAAAAAAAAAAAAAAAAAAAB",
            "AAAAAAAAAAAAAAAAAAAAAA=",
            "AAAAAAAAAAAAAAAAAAAAAA ",
            "+AAAAAAAAAAAAAAAAAAAAA",
            "A",
        ]:
            with self.subTest(bad=bad), self.assertRaises(ns["RefusalError"]):
                ns["binary"](bad, 16, 16, "bad")
        for length in (82, 1105):
            b = bytes(length)
            self.assertEqual(ns["binary"](ns["b64"](b), 82, 1105, "bad"), b)
        for length in (81, 1106, 2048):
            with self.subTest(length=length), self.assertRaises(ns["RefusalError"]):
                ns["binary"](ns["b64"](bytes(length)), 82, 1105, "bad")
        with self.assertRaises(ns["RefusalError"]):
            ns["strict_json"](b" " * 1025, 1024)

    def request(self):
        return {
            "v": 1,
            "kind": "approval",
            "aud": "TestAudience",
            "iid_spki": ns["b64"](bytes(91)),
            "ts": 1700000000,
            "nonce": ns["b64"](bytes(16)),
            "kid": "TestKidA",
            "platform": "fcm",
            "addr_kind": "fcm_token",
            "sealed": ns["b64"](bytes(82)),
            "route": ns["b64"](bytes([1]) * 32),
            "hint": ns["b64"](bytes([2]) * 32),
            "collapse": ns["b64"](bytes([3]) * 24),
            "ttl_s": 60,
        }

    def test_identifier_fullmatch_unknown_outer_and_known_type(self):
        o = self.request()
        o["unknown"] = 3.14
        self.assertEqual(ns["shape"](json.dumps(o).encode())[0]["unknown"].raw, "3.14")
        for field, value in [
            ("aud", "A" * 129),
            ("aud", "A\n"),
            ("aud", "-A"),
            ("kid", "A" * 65),
            ("kid", "A "),
            ("v", True),
            ("ts", 1.0),
            ("ttl_s", True),
        ]:
            mutated = {**o, field: value}
            with self.subTest(field=field, value=value), self.assertRaises(ns["RefusalError"]):
                ns["shape"](json.dumps(mutated).encode())
        for field, value in [("aud", "A" * 128), ("kid", "A" * 64)]:
            self.assertEqual(ns["shape"](json.dumps({**o, field: value}).encode())[0][field], value)
        missing = {k: v for k, v in o.items() if k != "kind"}
        with self.assertRaises(ns["RefusalError"]):
            ns["shape"](json.dumps(missing).encode())

    def test_outer_platform_kind_pairing_before_open(self):
        for platform, kind in [("apns", "fcm_token"), ("apns", "fcm_fid"), ("fcm", "apns_token")]:
            o = {**self.request(), "platform": platform, "addr_kind": kind}
            if platform == "apns":
                o["env"] = "sandbox"
            with (
                self.subTest(platform=platform, kind=kind),
                self.assertRaises(ns["RefusalError"]) as refused,
            ):
                ns["shape"](json.dumps(o).encode())
            self.assertEqual(refused.exception.code, "shape400")
        for platform, kind in [("apns", "apns_token"), ("fcm", "fcm_token"), ("fcm", "fcm_fid")]:
            o = {**self.request(), "platform": platform, "addr_kind": kind}
            if platform == "apns":
                o["env"] = "sandbox"
            with self.subTest(platform=platform, kind=kind):
                self.assertEqual(ns["shape"](json.dumps(o).encode())[0]["addr_kind"], kind)

    def test_unknown_numeric_lexemes_have_no_authority(self):
        baseline = self.request()
        frame = ns["frame"](baseline, "a" * 52)
        for token in ("3.14", "1e400", "-1e400", "1e-400"):
            raw = (
                json.dumps({**baseline, "unknown": 0})
                .replace('"unknown": 0', '"unknown": ' + token)
                .encode()
            )
            o = ns["shape"](raw)[0]
            self.assertEqual(o["unknown"].raw, token)
            self.assertEqual(ns["frame"](o, "a" * 52), frame)
        for token in ("NaN", "Infinity", "-Infinity"):
            raw = (
                json.dumps({**baseline, "unknown": 0})
                .replace('"unknown": 0', '"unknown": ' + token)
                .encode()
            )
            with self.subTest(token=token), self.assertRaises(ns["RefusalError"]):
                ns["shape"](raw)

    def test_transcript_raw_binary_and_explicit_empty_environment(self):
        o = self.request()
        tr = ns["frame"](o, "a" * 52)
        self.assertTrue(tr.startswith(b"HMP1-PUSH-RELAY"))
        remaining = tr[len(b"HMP1-PUSH-RELAY") :]
        fields = []
        while remaining:
            n = int.from_bytes(remaining[:4], "big")
            fields.append(remaining[4 : 4 + n])
            remaining = remaining[4 + n :]
        self.assertEqual(len(fields), 14)
        self.assertEqual(fields[7], b"")
        self.assertEqual(fields[8], hashlib.sha256(bytes(82)).digest())
        self.assertEqual(fields[9], bytes([1]) * 32)
        self.assertEqual(fields[10], bytes([2]) * 32)
        self.assertEqual(fields[11], bytes([3]) * 24)
        self.assertEqual(fields[12], (60).to_bytes(8, "big"))
        self.assertEqual(ns["frame"]({**o, "unknown": "ignored"}, "a" * 52), tr)


if __name__ == "__main__":
    unittest.main()
