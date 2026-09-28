#!/usr/bin/env python3
"""Independent server-side verifier for a `hmp_device_key` P-256 signature.

Verifies a DER ECDSA P-256/SHA-256 signature against a 91-byte uncompressed
P-256 SPKI public key, using `cryptography` only (tools/acceptance/
requirements.txt) — no code from `mobile/packages/hmp_device_key` or
`hmp_client`. This is what closes "a signature verifies server-side" in
T045's and T082/T084's physical-device acceptance evidence
(docs/research/f1-acceptance/android/): produce `spkiDer`/message/
`derSignature` on the device (a plugin test, or the HMP v1 P2 handshake
itself), then check them here, independently, the way the real HMP v1
server-side verifier does.

Install:
  python3 -m venv <scratch venv>
  <scratch venv>/bin/pip install -r tools/acceptance/requirements.txt
Run:
  <scratch venv>/bin/python tools/acceptance/verify_p256_signature.py \
      <spkiDerB64> <messageB64> <signatureB64>
"""

import base64
import sys

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

P256_SPKI_LENGTH = 91


def verify(spki_der_b64: str, message_b64: str, signature_b64: str) -> bool:
    spki_der = base64.b64decode(spki_der_b64)
    message = base64.b64decode(message_b64)
    signature = base64.b64decode(signature_b64)

    if len(spki_der) != P256_SPKI_LENGTH:
        raise ValueError(
            f"spkiDer must be {P256_SPKI_LENGTH} bytes (P-256 uncompressed SPKI), "
            f"got {len(spki_der)}"
        )

    public_key = serialization.load_der_public_key(spki_der)
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise ValueError("not an EC public key")
    if not isinstance(public_key.curve, ec.SECP256R1):
        raise ValueError(f"not P-256, got {public_key.curve.name}")

    try:
        public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: verify_p256_signature.py <spkiDerB64> <messageB64> <signatureB64>",
            file=sys.stderr,
        )
        return 2
    ok = verify(argv[0], argv[1], argv[2])
    print("VALID" if ok else "INVALID")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
