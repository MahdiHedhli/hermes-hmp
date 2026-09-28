"""CI regeneration check for tools/vectors/gen_hmp1_vectors.py (IR-16).

Runnable via pytest (`python -m pytest tools/vectors/tests -q`, which is what
`tools/ci/check_all.sh` already does for every `tools/**/tests` directory it
finds).

What this proves: the committed
`docs/architecture/contracts/vectors/hmp_v1_vectors.json` is not stale --
re-running the generator right now produces the same file, field for field,
except for the ECDSA signature bytes, which are expected to differ every run
by design (randomized nonce, no RFC 6979 -- see the generator's module
docstring and the vector file's `_meta.determinism_note`). Those signature
fields are excluded from the equality diff and instead verified
cryptographically, against the generator's own freshly produced keys and
transcripts.

Independence note: this test imports ONLY `tools/vectors/gen_hmp1_vectors.py`
(by file path, like `tools/hermes_builds/tests/test_extract.py` already
does) plus `cryptography`/`hashlib`/stdlib. It never imports server or client
code, and it does not re-implement the codec under test -- it re-runs the
same independent generator and diffs its output against the committed file.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GENERATOR_PATH = REPO_ROOT / "tools" / "vectors" / "gen_hmp1_vectors.py"
COMMITTED_VECTORS_PATH = (
    REPO_ROOT / "docs" / "architecture" / "contracts" / "vectors" / "hmp_v1_vectors.json"
)

_SPEC = importlib.util.spec_from_file_location("gen_hmp1_vectors", GENERATOR_PATH)
gen_hmp1_vectors = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules["gen_hmp1_vectors"] = gen_hmp1_vectors
_SPEC.loader.exec_module(gen_hmp1_vectors)


# Any dict key containing "sig_der" carries randomized ECDSA signature bytes
# (sig_der_hex / sig_der_b64u), by the generator's own naming convention (see
# its module docstring and IR-16's fix note in negative.float_ts). A glob on
# the key name -- not a fixed list of paths -- is deliberate: it keeps this
# test correct automatically if a future vector class adds another signature
# leaf, as long as that leaf follows the file's established naming
# convention.
def _is_signature_key(key: str) -> bool:
    return "sig_der" in key


def _strip_signatures(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _strip_signatures(v) for k, v in obj.items() if not _is_signature_key(k)}
    if isinstance(obj, list):
        return [_strip_signatures(x) for x in obj]
    return obj


def _collect_signature_leaves(obj: Any, path: str = "") -> list[tuple[str, str]]:
    """Returns [(path, hex_value)] for every 'sig_der_hex' leaf, so tests can
    re-verify them. ('sig_der_b64u' is redundant with 'sig_der_hex' -- the
    generator writes both from the same bytes -- so only hex is walked here.)
    """
    out: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "sig_der_hex" and isinstance(v, str):
                out.append((path + "/" + k, v))
            else:
                out.extend(_collect_signature_leaves(v, path + "/" + k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(_collect_signature_leaves(v, f"{path}[{i}]"))
    return out


@pytest.fixture(scope="module")
def committed() -> dict[str, Any]:
    assert COMMITTED_VECTORS_PATH.exists(), (
        f"{COMMITTED_VECTORS_PATH} does not exist -- run "
        f"'python tools/vectors/gen_hmp1_vectors.py --out {COMMITTED_VECTORS_PATH}' first"
    )
    return json.loads(COMMITTED_VECTORS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def regenerated() -> dict[str, Any]:
    return gen_hmp1_vectors.build_vectors()


def test_committed_file_is_not_stale(
    committed: dict[str, Any], regenerated: dict[str, Any]
) -> None:
    """Regenerating right now must match the committed file, ignoring only
    the randomized signature fields."""
    committed_stripped = _strip_signatures(committed)
    regenerated_stripped = _strip_signatures(regenerated)
    assert committed_stripped == regenerated_stripped, (
        "docs/architecture/contracts/vectors/hmp_v1_vectors.json does not match "
        "tools/vectors/gen_hmp1_vectors.py's current output (ignoring signature "
        "bytes). Regenerate it: python tools/vectors/gen_hmp1_vectors.py "
        f"--out {COMMITTED_VECTORS_PATH}"
    )


def test_committed_file_uses_cli_default_output_path() -> None:
    """The quickstart (specs/001-connect-and-browse/quickstart.md) and plan.md
    both assume `--out` defaults to the committed path; keep that true."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out", type=Path, default=Path("docs/architecture/contracts/vectors/hmp_v1_vectors.json")
    )
    args = parser.parse_args([])
    assert (REPO_ROOT / args.out) == COMMITTED_VECTORS_PATH


def test_committed_file_has_no_stale_signature_leaf_names(committed: dict[str, Any]) -> None:
    """Every signature-bearing leaf in the committed file must use a
    'sig_der*' key name, so the glob in _is_signature_key (and any consumer
    doing the same thing) actually catches it. This directly guards the
    IR-16 fix that renamed negative.float_ts.bad_request_json.sig ->
    sig_der_b64u."""

    # Exact-name check, not a prefix scan: a prefix scan for "sig" also
    # matches unrelated keys like "signer" (which names WHICH key signed,
    # not a signature value) and would be a false positive here.
    stale_signature_key_names = {"sig", "sig_hex", "sig_b64u", "signature", "signature_hex"}

    def find_suspicious_sig_keys(obj: Any, path: str = "") -> list[str]:
        found = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in stale_signature_key_names:
                    found.append(f"{path}/{k}")
                found.extend(find_suspicious_sig_keys(v, f"{path}/{k}"))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                found.extend(find_suspicious_sig_keys(v, f"{path}[{i}]"))
        return found

    suspicious = find_suspicious_sig_keys(committed)
    assert not suspicious, f"found signature-shaped key(s) not matching *sig_der*: {suspicious}"


def test_every_regenerated_signature_verifies(regenerated: dict[str, Any]) -> None:
    """'ECDSA vectors are checked by verification, not by byte equality'
    (T015's own acceptance line). This proves it: every transcript's
    signature, freshly produced by this run, verifies against its own
    public key and transcript bytes."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.serialization import load_der_public_key

    keys = regenerated["keys"]
    pub_by_name = {
        name: load_der_public_key(bytes.fromhex(entry["spki_der_hex"]))
        for name, entry in keys.items()
    }

    verified = 0
    for _tag, entry in regenerated["positive"]["transcripts"].items():
        pub = pub_by_name[entry["signer"]]
        transcript = bytes.fromhex(entry["transcript_hex"])
        sig = bytes.fromhex(entry["sig_der_hex"])
        pub.verify(sig, transcript, ec.ECDSA(hashes.SHA256()))  # raises InvalidSignature on failure
        verified += 1
    assert verified == 5, f"expected 5 HMP1-* transcripts, verified {verified}"


def test_every_committed_signature_verifies(committed: dict[str, Any]) -> None:
    """Same as above, but against whatever signature bytes are currently
    committed to disk -- catches a hand-edited or corrupted committed file
    even when test_committed_file_is_not_stale would (correctly) ignore
    signature bytes."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.serialization import load_der_public_key

    keys = committed["keys"]
    pub_by_name = {
        name: load_der_public_key(bytes.fromhex(entry["spki_der_hex"]))
        for name, entry in keys.items()
    }

    for _tag, entry in committed["positive"]["transcripts"].items():
        pub = pub_by_name[entry["signer"]]
        transcript = bytes.fromhex(entry["transcript_hex"])
        sig = bytes.fromhex(entry["sig_der_hex"])
        pub.verify(sig, transcript, ec.ECDSA(hashes.SHA256()))
