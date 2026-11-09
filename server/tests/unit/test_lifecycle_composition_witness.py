"""Historical byte gates remain fixed; composition is an exact, test-only quotient."""
import hashlib
from pathlib import Path

import pytest

from . import approved_lifecycle_composition_witness as witness

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"
CASES = (
    ("adapter.py", witness.ADAPTER_EDITS, witness.ADAPTER_BASE_SHA256),
    ("server.py", witness.SERVER_EDITS, witness.SERVER_BASE_SHA256),
    ("local_media_registry.py", witness.REGISTRY_EDITS, witness.REGISTRY_BASE_SHA256),
)


@pytest.mark.parametrize("name,edits,old_hash", CASES)
def test_exact_reviewed_inverse_preserves_original_hash(name, edits, old_hash):
    restored = witness._reverse((PACKAGE / name).read_text(), edits)
    assert hashlib.sha256(restored.encode()).hexdigest() == old_hash


@pytest.mark.parametrize("name,edits,old_hash", CASES)
def test_unrelated_dynamic_lookup_survives_inverse_and_fails_original_hash(name, edits, old_hash):
    marker = '\n\ndef outside_composition():\n    return __import__("unexpected")\n'
    restored = witness._reverse((PACKAGE / name).read_text() + marker, edits)
    assert restored.endswith(marker)
    assert hashlib.sha256(restored.encode()).hexdigest() != old_hash


@pytest.mark.parametrize("name,edits,old_hash", CASES)
def test_unknown_edit_inside_composition_delta_is_refused(name, edits, old_hash):
    source = (PACKAGE / name).read_text()
    current = edits[0][0]
    middle = len(current) // 2
    damaged = current[:middle] + "UNREVIEWED_MUTATION" + current[middle:]
    with pytest.raises(AssertionError):
        witness._reverse(source.replace(current, damaged, 1), edits)
