#!/usr/bin/env python3
"""TEST-ONLY independent reader. SOURCE ONLY until separate execution admission.

Imports no generator, server, app or native fixture. Uses distinct HPKE/JCS
libraries. Fixed local paths, no provider code/network, closed output vocabulary.
This reference checker does not prove production relay ordering/atomic limits.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
INFO = b"HMP push seal v1"
OFFICIAL_SHA = "61fc662f01996cd06d713dacf5e133167bd309a1f329442d53f1e21a47b3ede6"
CONTRACT_SHA = "7c7cb585b8513cd25122fe532a03d3cefa7b0213bea831c1891c28af5d9720a3"
ORDER = int("ffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551", 16)
KID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
AUD = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
IID = re.compile(r"[a-z2-7]{52}")
NOW = 1700000000
CASE_COUNT = 151
ROW_KEYS = {
    "id",
    "expected",
    "synthetic_only",
    "recipient_test_public_hex",
    "recipient_test_private_hex",
    "seal_mode",
    "seal_aead_id",
    "tag_bytes",
    "test_ekm_hex",
    "seal_info_hex",
    "seal_aad_hex",
    "plaintext_hex",
    "plaintext_bytes",
    "enc_hex",
    "ct_hex",
    "raw_sealed_hex",
    "sealed_sha256",
    "request_body_hex",
    "signed_transcript_hex",
    "signature_der_hex",
    "expected_opener_calls",
    "provider_calls",
}
TOP_KEYS = {
    "format",
    "synthetic_only",
    "status",
    "contract_sha256",
    "info_hex",
    "suite",
    "official_sha256",
    "cases_sha256",
    "source_pins_sha256",
    "dependency_lock_sha256",
    "runtime",
    "official_counts",
    "api_coverage",
    "signature_policy",
    "cases",
}


class RefusalError(Exception):
    def __init__(self, code: str):
        self.code = code


class NumericLexeme:
    """Opaque outer JSON number token; never coerced or used as authority.

    Known integer fields require exact int type. Fraction/exponent tokens are
    retained only so ignored members cannot overflow into Python infinity.
    This does not certify IEEE754 representability recommendations for them.
    """

    def __init__(self, raw: str):
        self.raw = raw


def need(ok: bool, code: str = "CHECK_FAILED") -> None:
    if not ok:
        raise RefusalError(code)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read(path: Path, cap: int) -> bytes:
    if path.is_relative_to(ROOT):
        for parent in (path, *path.parents):
            if parent == ROOT.parent:
                break
            need(not parent.is_symlink())
    need(not path.is_symlink() and path.is_file() and path.stat().st_size <= cap)
    return path.read_bytes()


def load(name: str, cap: int = 8 * 1024 * 1024):
    return json.loads(read(HERE / name, cap))


def preflight() -> None:
    need(len(sys.argv) == 1 and sys.version_info[:3] == (3, 14, 6))
    need(sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.dont_write_bytecode == 1)
    need(Path.cwd() == HERE and Path(sys.prefix).resolve() == ROOT / "venv")
    allowed = {"PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "TZ", "PYCRYPTODOME_DISABLE_GMP"}
    need(set(os.environ) == allowed)
    need(
        os.environ.get("HOME") == str(ROOT / "home")
        and os.environ.get("TMPDIR") == str(ROOT / "tmp")
    )
    need(os.environ.get("TZ") == "UTC" and os.environ.get("PYCRYPTODOME_DISABLE_GMP") == "1")
    need(os.environ.get("LANG") == "C.UTF-8" and os.environ.get("LC_ALL") == "C.UTF-8")
    pins = load("source-pins.json")
    for name, h in pins["hashes"].items():
        need(sha(read(HERE / name, 8 * 1024 * 1024)) == h)
    need(
        len(INFO) == 16
        and sha(read(HERE / "data/rfc9180-test-vectors.json", 6 * 1024 * 1024)) == OFFICIAL_SHA
    )
    # Root must use the pinned wheel artifacts with --no-deps, --no-index.
    # Assert installed library bytes before importing native/third-party code.
    lib = ROOT / "venv/lib/python3.14/site-packages"
    lock = load("dependencies.lock.json")
    need(len(lock["packages"]) == 5)
    for pkg in lock["packages"]:
        if pkg["ecosystem"] != "pypi":
            continue
        for f in pkg["files"]:
            if ".dist-info/" not in f["path"]:
                need(sha(read(lib / f["path"], 4 * 1024 * 1024)) == f["sha256"])
    expected = {
        f["path"]
        for p in lock["packages"]
        if p["ecosystem"] == "pypi"
        for f in p["files"]
        if ".dist-info/" not in f["path"]
    }
    actual = set()
    for prefix in ("Crypto", "rfc8785"):
        for p in (lib / prefix).rglob("*"):
            need(not p.is_symlink())
            if p.is_file():
                actual.add(p.relative_to(lib).as_posix())
    need(actual == expected)


def unhex(s: str, cap: int = 8192) -> bytes:
    need(type(s) is str and len(s) <= cap * 2 and re.fullmatch(r"(?:[0-9a-f]{2})*", s) is not None)
    return bytes.fromhex(s)


def b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def binary(s, low: int, high: int, code: str) -> bytes:
    need(
        type(s) is str
        and len(s) <= (high * 4 + 2) // 3
        and re.fullmatch(r"[A-Za-z0-9_-]+", s) is not None,
        code,
    )
    try:
        b = base64.b64decode(s + "=" * (-len(s) % 4), altchars=b"-_", validate=True)
    except (ValueError, TypeError):
        raise RefusalError(code) from None
    need(low <= len(b) <= high and b64(b) == s, code)
    return b


def pairs(xs):
    d = {}
    for k, v in xs:
        need(k not in d, "JSON_INVALID")
        d[k] = v
    return d


def reject_number(_):
    raise RefusalError("JSON_INVALID")


def unicode_ok(x):
    if type(x) is str:
        need(not any(0xD800 <= ord(c) <= 0xDFFF for c in x), "JSON_INVALID")
    elif type(x) is dict:
        for k, v in x.items():
            unicode_ok(k)
            unicode_ok(v)
    elif type(x) is list:
        for v in x:
            unicode_ok(v)


def strict_json(b: bytes, cap: int, floats: bool = False):
    need(0 < len(b) <= cap and not b.startswith(b"\xef\xbb\xbf"), "JSON_INVALID")
    try:
        obj = json.loads(
            b.decode("utf8", "strict"),
            object_pairs_hook=pairs,
            parse_float=NumericLexeme if floats else reject_number,
            parse_constant=reject_number,
        )
        unicode_ok(obj)
        return obj
    except (UnicodeError, ValueError, RecursionError):
        raise RefusalError("JSON_INVALID") from None


def integer(n, low: int, high: int) -> bool:
    return type(n) is int and low <= n <= high


def shape(body: bytes):
    try:
        o = strict_json(body, 4096, floats=True)
    except RefusalError:
        raise RefusalError("shape400") from None
    need(type(o) is dict, "shape400")
    required = {
        "v",
        "kind",
        "aud",
        "iid_spki",
        "ts",
        "nonce",
        "kid",
        "platform",
        "addr_kind",
        "sealed",
        "route",
        "hint",
        "collapse",
        "ttl_s",
    }
    # Frozen PR-3: unknown outer members carry no authority and are ignored.
    need(required <= set(o), "shape400")
    need(type(o["v"]) is int and o["v"] == 1 and o["kind"] == "approval", "shape400")
    need(type(o["aud"]) is str and AUD.fullmatch(o["aud"]) is not None, "shape400")
    need(type(o["kid"]) is str and KID.fullmatch(o["kid"]) is not None, "shape400")
    need(integer(o["ts"], 0, 2**53 - 1) and integer(o["ttl_s"], 60, 900), "shape400")
    need(o["platform"] in ("apns", "fcm"), "shape400")
    need(
        type(o["addr_kind"]) is str and o["addr_kind"] in ("apns_token", "fcm_token", "fcm_fid"),
        "shape400",
    )
    need(
        (o["platform"] == "apns" and o["addr_kind"] == "apns_token")
        or (o["platform"] == "fcm" and o["addr_kind"] in ("fcm_token", "fcm_fid")),
        "shape400",
    )
    if o["platform"] == "apns":
        need(o.get("env") in ("production", "sandbox"), "shape400")
    else:
        need("env" not in o, "shape400")
    spki = binary(o["iid_spki"], 91, 91, "shape400")
    for field, size in (("nonce", 16), ("route", 32), ("hint", 32), ("collapse", 24)):
        binary(o[field], size, size, "shape400")
    sealed = binary(o["sealed"], 82, 1105, "shape400")
    return o, spki, sealed


def frame(o, iid: str) -> bytes:
    fields = [
        o["aud"].encode(),
        iid.encode(),
        o["ts"].to_bytes(8, "big"),
        binary(o["nonce"], 16, 16, "shape400"),
        o["kid"].encode(),
        o["platform"].encode(),
        o["addr_kind"].encode(),
        o.get("env", "").encode(),
        hashlib.sha256(binary(o["sealed"], 82, 1105, "shape400")).digest(),
        binary(o["route"], 32, 32, "shape400"),
        binary(o["hint"], 32, 32, "shape400"),
        binary(o["collapse"], 24, 24, "shape400"),
        o["ttl_s"].to_bytes(8, "big"),
        o["kind"].encode(),
    ]
    return b"HMP1-PUSH-RELAY" + b"".join(len(f).to_bytes(4, "big") + f for f in fields)


def der_scalars(sig: bytes, der_sequence):
    need(8 <= len(sig) <= 72, "shape400")
    try:
        seq = der_sequence().decode(sig, strict=True, nr_elements=2, only_ints_expected=True)
        r, s = seq
        need(type(r) is int and type(s) is int and 1 <= r < ORDER and 1 <= s < ORDER, "shape400")
        need(der_sequence([r, s]).encode() == sig, "shape400")
        return r, s
    except (ValueError, TypeError, IndexError):
        raise RefusalError("shape400") from None


def plaintext(b: bytes, rfc8785):
    try:
        o = strict_json(b, 1024)
        need(type(o) is dict, "JSON_INVALID")
        required = {"addr", "addr_kind", "app", "iid", "n", "not_after", "platform", "v"}
        if o.get("platform") == "apns":
            required.add("env")
        need(set(o) == required, "JSON_INVALID")
        need(
            type(o["v"]) is int and o["v"] == 1 and integer(o["not_after"], 0, 2**53 - 1),
            "JSON_INVALID",
        )
        for k in required - {"v", "not_after"}:
            need(type(o[k]) is str, "JSON_INVALID")
        need(IID.fullmatch(o["iid"]) is not None, "JSON_INVALID")
        need(
            (o["platform"] == "apns" and o["addr_kind"] == "apns_token")
            or (o["platform"] == "fcm" and o["addr_kind"] in ("fcm_token", "fcm_fid")),
            "JSON_INVALID",
        )
        if o["platform"] == "apns":
            need(o["env"] in ("production", "sandbox"), "JSON_INVALID")
        binary(o["n"], 16, 16, "JSON_INVALID")
        need(rfc8785.dumps(o) == b, "JSON_INVALID")
        return o
    except (RefusalError, ValueError, TypeError, OverflowError):
        raise RefusalError("plain422") from None


def model(row, definition, receivers, ecc, hpke, dss, sha256, der_sequence, rfc8785):
    opened = 0
    try:
        o, spki, raw = shape(unhex(row["request_body_hex"]))
        try:
            public = ecc.import_key(spki)
            need(
                not public.has_private()
                and public.curve == "NIST P-256"
                and public.export_key(format="DER") == spki,
                "shape400",
            )
        except (ValueError, TypeError, IndexError):
            raise RefusalError("shape400") from None
        iid = base64.b32encode(hashlib.sha256(spki).digest()).decode().lower().rstrip("=")
        sig = unhex(row["signature_der_hex"], 72)
        r, s = der_scalars(sig, der_sequence)
        tr = frame(o, iid)
        if definition["id"].startswith("unknown_outer_"):
            without = {k: v for k, v in o.items() if k != "unknown_test_field"}
            need(frame(without, iid) == tr, "CHECK_FAILED")
            if definition["id"] == "unknown_outer_fraction_ignored":
                need(
                    type(o["unknown_test_field"]) is NumericLexeme
                    and o["unknown_test_field"].raw == "3.14"
                )
            if definition["id"] == "unknown_outer_exponent_ignored":
                need(
                    type(o["unknown_test_field"]) is NumericLexeme
                    and o["unknown_test_field"].raw == "1e400"
                )
        try:
            dss.new(public, "fips-186-3", encoding="der").verify(sha256.new(tr), sig)
        except ValueError:
            raise RefusalError("auth401") from None
        # Each signature-authenticated case must independently verify both S forms.
        dss.new(public, "fips-186-3", encoding="der").verify(
            sha256.new(tr), der_sequence([r, ORDER - s]).encode()
        )
        need(tr == unhex(row["signed_transcript_hex"]), "CHECK_FAILED")
        need(o["aud"] == definition.get("aud_config", "TestAudience"), "auth401")
        need(o["ts"] + 120 > NOW and o["ts"] <= NOW + 120, "auth401")
        need(
            o["kid"] in receivers
            and definition.get("kid_config", True)
            and definition.get("iid_allowlisted", True),
            "auth401",
        )
        # No replay/limits/provider implementation is present. This is an offline
        # primitive/schema reference: the receiver map uses this public TEST key.
        opened += 1
        try:
            need(len(raw[:65]) == 65 and raw[0] == 4, "hpke422")
            context = hpke.new(
                receiver_key=receivers[o["kid"]],
                aead_id=hpke.AEAD.AES128_GCM,
                enc=raw[:65],
                info=INFO,
            )
            pt = context.unseal(raw[65:], auth_data=o["kid"].encode("ascii"))
        except (ValueError, TypeError, IndexError):
            raise RefusalError("hpke422") from None
        need(pt == unhex(row["plaintext_hex"], 1025), "CHECK_FAILED")
        p = plaintext(pt, rfc8785)
        if definition["expected"] == "domain_ok":
            return "domain_ok", opened
        need(p["iid"] == iid and p["app"] == "test.example", "binding422")
        need(p["platform"] == o["platform"] and p["addr_kind"] == o["addr_kind"], "binding422")
        need(NOW < p["not_after"] <= NOW + 14 * 86400, "binding422")
        if p["platform"] == "apns":
            need(
                p["env"] == o["env"]
                and (p["env"] != "production" or definition.get("allow_production", True)),
                "binding422",
            )
        return "eligible", opened
    except RefusalError as e:
        return e.code, opened


def main() -> None:
    preflight()
    # -I -S avoids owner PYTHONPATH and .pth/sitecustomize execution; add only
    # exact, already checked wheel directory after byte verification.
    sys.path.insert(0, str(ROOT / "venv/lib/python3.14/site-packages"))
    import Crypto
    import rfc8785
    from Crypto.Hash import SHA256
    from Crypto.Protocol import HPKE
    from Crypto.PublicKey import ECC
    from Crypto.Signature import DSS
    from Crypto.Util.asn1 import DerSequence

    need(Path(Crypto.__file__).resolve().is_relative_to(ROOT / "venv"))
    need(Path(rfc8785.__file__).resolve().is_relative_to(ROOT / "venv"))
    all_vectors = load("data/rfc9180-test-vectors.json")
    selected = [
        v
        for v in all_vectors
        if (v["mode"], v["kem_id"], v["kdf_id"], v["aead_id"]) == (0, 16, 1, 1)
    ]
    need(len(selected) == 1)
    v = selected[0]
    need(len(v["encryptions"]) == 257 and len(v["exports"]) == 3)
    receiver = ECC.construct(curve="p256", d=int.from_bytes(unhex(v["skRm"]), "big"))
    need(receiver.public_key().export_key(format="SEC1") == unhex(v["pkRm"]))
    ctx = HPKE.new(
        receiver_key=receiver,
        aead_id=HPKE.AEAD.AES128_GCM,
        enc=unhex(v["enc"]),
        info=unhex(v["info"]),
    )
    for x in v["encryptions"]:
        need(ctx.unseal(unhex(x["ct"]), auth_data=unhex(x["aad"])) == unhex(x["pt"]))
    alternate = next(
        x for x in all_vectors if x["mode"] == 0 and x["kem_id"] == 16 and x["pkRm"] != v["pkRm"]
    )
    other = ECC.construct(curve="p256", d=int.from_bytes(unhex(alternate["skRm"]), "big"))
    need(other.public_key().export_key(format="SEC1") == unhex(alternate["pkRm"]))
    receivers = {
        "TestKidA": receiver,
        "TestKidB": receiver,
        "TestKidC": other,
        "A": receiver,
        "A" + "z" * 63: receiver,
    }
    tags = load("data/tag-domains.json")["tags"]
    need(
        len(tags) == len(set(tags))
        and all(not a.startswith(b) for a in tags for b in tags if a != b)
    )
    defs = load("cases.json")["cases"]
    corpus_bytes = read(ROOT / "out/generated.json", 2 * 1024 * 1024)
    corpus = json.loads(corpus_bytes, object_pairs_hook=pairs, parse_constant=reject_number)
    need(type(corpus) is dict and set(corpus) == TOP_KEYS)
    need(
        corpus["format"] == "hmp-push-seal-vectors-v1"
        and corpus["synthetic_only"] is True
        and corpus["status"] == "GENERATOR_ONLY_NOT_INDEPENDENTLY_VERIFIED"
    )
    need(
        corpus["contract_sha256"] == CONTRACT_SHA
        and corpus["official_sha256"] == OFFICIAL_SHA
        and corpus["info_hex"] == INFO.hex()
    )
    need(
        corpus["suite"] == {"mode": 0, "kem_id": 16, "kdf_id": 1, "aead_id": 1}
        and all(type(x) is int for x in corpus["suite"].values())
        and corpus["runtime"] == "v22.22.3"
    )
    for name, key in (
        ("cases.json", "cases_sha256"),
        ("source-pins.json", "source_pins_sha256"),
        ("dependencies.lock.json", "dependency_lock_sha256"),
    ):
        need(sha(read(HERE / name, 1024 * 1024)) == corpus[key])
    need(
        corpus["official_counts"] == {"encryptions": 257, "exports": 3}
        and all(type(x) is int for x in corpus["official_counts"].values())
    )
    need(
        corpus["api_coverage"]
        == {
            "pkRm": "compared",
            "skRm": "compared",
            "pkEm": "compared",
            "skEm": "compared",
            "enc": "compared",
            "shared_secret": "compared",
            "ct": "257 compared",
            "exports": "3 compared",
            "key_schedule_context": "not exposed",
            "secret": "not exposed",
            "key": "not exposed",
            "base_nonce": "not exposed",
            "exporter_secret": "not exposed",
            "nonce": "not exposed",
        }
    )
    need(
        corpus["signature_policy"]
        == "randomized DER; regenerate other bytes exactly; independently verify every signature"
    )
    rows = corpus["cases"]
    need(
        type(rows) is list
        and len(rows) == len(defs) == CASE_COUNT
        and [r["id"] for r in rows] == [d["id"] for d in defs]
    )
    results = []
    for row, d in zip(rows, defs, strict=True):
        need(type(row) is dict and set(row) == ROW_KEYS and row["expected"] == d["expected"])
        fixture = alternate if d.get("recipient") == "alternate" else v
        need(
            row["synthetic_only"] is True
            and row["recipient_test_public_hex"] == fixture["pkRm"]
            and row["recipient_test_private_hex"] == fixture["skRm"]
        )
        need(
            row["seal_mode"] == d.get("seal_mode", "base")
            and type(row["seal_aead_id"]) is int
            and row["seal_aead_id"] == (2 if d.get("seal_suite") == "aead256" else 1)
        )
        need(type(row["tag_bytes"]) is int and row["tag_bytes"] == 16)
        for name in (k for k in ROW_KEYS if k.endswith("_hex")):
            unhex(row[name])
        need(
            integer(row["plaintext_bytes"], 0, 1025)
            and row["plaintext_bytes"] == len(unhex(row["plaintext_hex"]))
        )
        need(
            integer(row["expected_opener_calls"], 0, 1)
            and type(row["provider_calls"]) is int
            and row["provider_calls"] == 0
        )
        need(
            len(unhex(row["test_ekm_hex"])) == 32
            and len(unhex(row["enc_hex"])) == 65
            and len(unhex(row["ct_hex"])) == row["plaintext_bytes"] + 16
        )
        need(
            hashlib.sha256(("HMP-TEST-ONLY-EKM/" + d["id"]).encode()).digest()
            == unhex(row["test_ekm_hex"])
        )
        raw = unhex(row["raw_sealed_hex"])
        need(
            raw == unhex(row["enc_hex"]) + unhex(row["ct_hex"]) and sha(raw) == row["sealed_sha256"]
        )
        need(row["seal_info_hex"] == d.get("seal_info", "HMP push seal v1").encode().hex())
        need(
            row["seal_aad_hex"]
            == d.get("seal_aad", d.get("outer_patch", {}).get("kid", "TestKidA")).encode().hex()
        )
        outcome, opened = model(row, d, receivers, ECC, HPKE, DSS, SHA256, DerSequence, rfc8785)
        need(outcome == row["expected"] and opened == row["expected_opener_calls"])
        results.append(
            {
                "id": row["id"],
                "outcome": outcome,
                "actual_reference_opener_calls": opened,
                "provider_calls": 0,
            }
        )
    receipt = {
        "format": "hmp-push-seal-check-v1",
        "verdict": "PASS_OFFLINE_REFERENCE_ONLY",
        "synthetic_only": True,
        "input_sha256": sha(corpus_bytes),
        "official_open_count": 257,
        "python_exports": "not exposed by public API",
        "case_count": CASE_COUNT,
        "results": results,
        "limits": (
            "No actual relay/server/app/provider/replay/concurrency/transport/native/device proof"
        ),
    }
    target = ROOT / "out/checked.json"
    with target.open("x", encoding="utf8") as f:
        os.chmod(target, 0o600)
        f.write(json.dumps(receipt, indent=2) + "\n")
    print("CHECKED_OFFLINE_REFERENCE_ONLY_151")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("VECTOR_CHECK_FAILED", file=sys.stderr)
        sys.exit(1)
