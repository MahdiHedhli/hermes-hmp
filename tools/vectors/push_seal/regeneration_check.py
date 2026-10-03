#!/usr/bin/env python3
"""TEST-ONLY future comparison of two independently executed generation outputs.

Use from admitted isolated runtime only after check.py succeeds on BOTH outputs.
No crypto, package, production imports. Fixed input paths; no command line paths.
Randomized DER signature bytes differ; every signature needs check.py validation.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    if len(sys.argv) != 1:
        raise ValueError
    blobs = []
    for suffix in ("a", "b"):
        name = "regeneration-"+suffix+".json"
        p = ROOT / "out" / name
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 2*1024*1024:
            raise ValueError
        raw = p.read_bytes()
        receipt_path = ROOT / "out" / ("checked-"+suffix+".json")
        if receipt_path.is_symlink() or not receipt_path.is_file() or receipt_path.stat().st_size > 256*1024:
            raise ValueError
        receipt = json.loads(receipt_path.read_bytes())
        if receipt["verdict"] != "PASS_OFFLINE_REFERENCE_ONLY" or receipt["input_sha256"] != hashlib.sha256(raw).hexdigest() or receipt["official_open_count"] != 257 or receipt["case_count"] != 151 or len(receipt["results"]) != 151:
            raise ValueError
        d = json.loads(raw)
        if d["status"] != "GENERATOR_ONLY_NOT_INDEPENDENTLY_VERIFIED" or len(d["cases"]) != 151:
            raise ValueError
        if [r["id"] for r in receipt["results"]] != [r["id"] for r in d["cases"]]:
            raise ValueError
        for row in d["cases"]:
            del row["signature_der_hex"]
        blobs.append(d)
    if blobs[0] != blobs[1]:
        raise ValueError
    print("NON_SIGNATURE_BYTES_REPRODUCED_PENDING_BOTH_SIGNATURE_RECEIPTS")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("REGENERATION_CHECK_FAILED", file=sys.stderr)
        sys.exit(1)
